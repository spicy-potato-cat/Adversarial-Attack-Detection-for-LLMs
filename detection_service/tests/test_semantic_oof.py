"""Synthetic fold control, exact recipe, coverage, metrics, and read-only gates."""

import copy
from dataclasses import replace
import json
import math
import os
from types import SimpleNamespace

import numpy as np
import pytest
import torch

from detection_service.analysis.semantic_oof import (
    FOLD_SHA256, RECIPE_SHA256, REVISION, bucket, characterize, confidence, interval,
    probability_metrics, recommendations, run_folds, schema_projection, truncation_analysis,
    validate_predictions, validate_recipe, predict,
)
from detection_service.analysis.statistical_oof import check_membership, fixed_fpr, stability
from detection_service.app.detectors.semantic_finetuned.config import FineTunedConfig, MANIFEST_SHA256
from detection_service.quality.development_fixture import ROOT, file_hash, verify
from detection_service.quality.policy import FOLD_PATH, MANIFEST_PATH
from detection_service.scripts.semantic_oof_baseline import (
    CODE, CSV_FIELDS, baseline_check, csv_bytes, load_base_texts, payload_policy,
    selected_rows, validate_schema, verify_hashes,
)


def config():
    return FineTunedConfig(upstream_model="distilbert/distilroberta-base", upstream_revision=REVISION, tokenizer_revision=REVISION)


def fixture():
    rows = [{"sample_id": f"synthetic-{i:03}", "partition": "BASE_TRAIN", "label": str(i % 2),
             "source_name": "synthetic", "source_revision": "synthetic-not-upstream",
             "lineage_group": "LG-N1-" + f"{i:024x}", "outer_fold": str(i % 5)} for i in range(40)]
    return rows, [f"synthetic text {i}" for i in range(40)]


def observation(score=.7, count=20):
    return {"raw_score": score, "logit_margin": math.log(score / (1 - score)),
            "input_tokens": count, "tokens_analyzed": min(count, 256), "tokens_excluded": max(0, count - 256),
            "truncated": count > 256, "max_input_tokens": 256, "latency_ms": .1,
            "payload_position_status": "NOT_AVAILABLE_NOT_INFERRED"}


def fake_build(c, p):
    return object(), SimpleNamespace(trained=False), "same-upstream-and-seeded-head"


def fake_fit(model, tokenizer, texts, labels, c, weights):
    assert not model.trained
    model.trained = True
    return [{"epoch": i + 1, "batches": math.ceil(len(texts) / 8)} for i in range(3)]


def fake_score(tokenizer, model, texts, c):
    assert model.trained
    result = []
    for text in texts:
        i = int(text.rsplit(" ", 1)[1])
        # Both correct/error classes and coverage/confidence patterns.
        result.append(observation((.05, .95, .7, .3, .55, .45)[i % 6], (20, 256, 257, 600)[i % 4]))
    return result


@pytest.fixture(scope="module")
def completed():
    rows, texts = fixture()
    return run_folds(rows, texts, config(), {}, build=fake_build, fit=fake_fit, score=fake_score)


def test_frozen_fixture_without_regeneration():
    result = verify()
    assert result["fold_sha256"] == FOLD_SHA256
    assert file_hash(ROOT / FOLD_PATH) == FOLD_SHA256
    assert file_hash(ROOT / MANIFEST_PATH) == MANIFEST_SHA256
    rows, sources = selected_rows()
    assert len(rows) == len(sources) == 1135
    assert sum(int(r["label"]) for r in rows) == 183
    assert len({r["lineage_group"] for r in rows}) == 1134


def test_exact_frozen_recipe():
    assert file_hash(ROOT / "detection_service/configs/dm_b_v1_training.json") == RECIPE_SHA256
    frozen = json.loads((ROOT / "detection_service/configs/dm_b_v1_training.json").read_text())
    assert frozen == config().to_dict()
    validate_recipe(config())


@pytest.mark.parametrize("change", [{"max_sequence_length": 512}, {"epochs": 2}, {"batch_size": 4},
    {"learning_rate": 3e-5}, {"upstream_revision": "a" * 40, "tokenizer_revision": "a" * 40},
    {"weight_decay": .02}, {"warmup_ratio": .2}, {"gradient_clip": .5}, {"cpu_threads": 4}])
def test_recipe_drift_rejected(change):
    with pytest.raises(ValueError):
        validate_recipe(replace(config(), **change))


def test_once_ordered_and_no_calibration(completed):
    records, reports = completed
    assert len(records) == len({r["sample_id"] for r in records}) == 40
    assert [r["sample_id"] for r in records] == sorted(r["sample_id"] for r in records)
    assert len(reports) == 5
    assert all(r["calibrated_probability"] is None and r["max_input_tokens"] == 256 for r in records)
    assert all(r["identity_leakage"] == r["lineage_leakage"] == 0 for r in reports)


def test_actual_fold_train_and_score_inputs_disjoint():
    rows, texts = fixture()
    fits, scores, models = [], [], []

    def build(c, p):
        tokenizer, model, initial = fake_build(c, p)
        models.append(model)
        return tokenizer, model, initial

    def fit(m, t, supplied, labels, c, weights):
        fold = len(fits)
        expected = [i for i, r in enumerate(rows) if int(r["outer_fold"]) != fold]
        assert supplied == [texts[i] for i in expected]
        assert labels == [int(rows[i]["label"]) for i in expected]
        assert weights == [len(expected) / (2 * labels.count(k)) for k in (0, 1)]
        fits.append(set(supplied))
        return fake_fit(m, t, supplied, labels, c, weights)

    def score(t, m, supplied, c):
        fold = len(scores)
        assert supplied == [texts[i] for i, r in enumerate(rows) if int(r["outer_fold"]) == fold]
        scores.append(set(supplied))
        assert not fits[fold] & scores[fold]
        return fake_score(t, m, supplied, c)

    run_folds(rows, texts, config(), {}, build=build, fit=fit, score=score)
    assert len({id(m) for m in models}) == 5
    assert len(set.union(*scores)) == 40


def test_seed_reset_before_each_initialization():
    rows, texts = fixture()
    draws = []

    def build(c, p):
        draws.append(float(torch.rand(1)))
        return fake_build(c, p)

    run_folds(rows, texts, config(), {}, build=build, fit=fake_fit, score=fake_score)
    assert len(set(draws)) == 1 and len(draws) == 5


def test_upstream_initialization_mismatch_rejected():
    rows, texts = fixture()
    calls = []

    def build(c, p):
        calls.append(1)
        t, m, initial = fake_build(c, p)
        return t, m, str(len(calls))

    with pytest.raises(ValueError, match="initialization"):
        run_folds(rows, texts, config(), {}, build=build, fit=fake_fit, score=fake_score)


@pytest.mark.parametrize("partition", ["CALIBRATION", "VALIDATION", "EXTERNAL_BENCHMARK", "PROTECTED"])
def test_reserved_partition_never_loaded(partition, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("reserved loader was called")
    monkeypatch.setattr("detection_service.app.detectors.semantic_finetuned.data.load_texts", forbidden)
    with pytest.raises(ValueError, match="reserved/mixed"):
        load_base_texts([{"partition": partition}], {})
    rows, texts = fixture()
    rows[0]["partition"] = partition
    with pytest.raises(ValueError):
        run_folds(rows, texts, config(), {}, build=forbidden)


def test_lineage_split_rejected():
    rows, _ = fixture()
    rows[1]["lineage_group"] = rows[0]["lineage_group"]
    with pytest.raises(ValueError, match="lineage"):
        check_membership(rows)


def test_duplicate_and_missing_score_rejected():
    rows, texts = fixture()
    rows[1]["sample_id"] = rows[0]["sample_id"]
    with pytest.raises(ValueError):
        run_folds(rows, texts, config(), {})
    rows, texts = fixture()
    with pytest.raises(ValueError, match="missing held-out"):
        run_folds(rows, texts, config(), {}, build=fake_build, fit=fake_fit, score=lambda *args: [])


@pytest.mark.parametrize("mutation", [{"raw_score": float("nan")}, {"tokens_analyzed": 257},
    {"truncated": None}, {"calibrated_probability": .2}, {"fold": 7}, {"threshold_distance": 99}])
def test_output_corruption_rejected(completed, mutation):
    records = copy.deepcopy(completed[0])
    records[0].update(mutation)
    with pytest.raises(ValueError):
        validate_predictions(records, fixture()[0])


def test_metric_hand_example():
    m = probability_metrics([0, 0, 1, 1], [.1, .8, .2, .9])
    assert m["confusion_matrix"] == {"tn": 1, "fp": 1, "fn": 1, "tp": 1}
    assert m["accuracy"] == m["fpr"] == m["fnr"] == m["recall"] == .5
    assert m["roc_auc"] == .75
    assert m["pr_auc"] == pytest.approx(5 / 6)
    assert "softmax" in m["comparison_rule"] and "LR" not in m["comparison_rule"]


def test_fixed_fpr_inclusive_ties_and_no_positive_point():
    labels = [0] * 100 + [1] * 3
    scores = [.1] * 99 + [.9] + [.95, .9, .05]
    points = fixed_fpr(labels, scores)
    assert [p["recall"] for p in points] == [2 / 3] * 3
    assert all(p["attained_fpr"] <= p["budget"] for p in points)
    tied = fixed_fpr([0, 1], [.5, .5])
    assert all(p["recall"] == 0 and p["no_positive_predictions"] for p in tied)


def test_class_conditional_truncation_denominator(completed):
    records = completed[0]
    analysis = truncation_analysis(records)
    for flag in (False, True):
        positives = [r for r in records if r["truncated"] == flag and r["label"] == 1]
        negatives = [r for r in records if r["truncated"] == flag and r["label"] == 0]
        group = analysis["groups"]["truncated" if flag else "not_truncated"]
        assert group["fnr"] == (sum(r["error_type"] == "FN" for r in positives) / len(positives) if positives else None)
        assert group["fpr"] == (sum(r["error_type"] == "FP" for r in negatives) / len(negatives) if negatives else None)


def test_empty_truncated_support_is_unknown(completed):
    rows = copy.deepcopy(completed[0])
    for r in rows:
        r.update(truncated=False, input_tokens=20, tokens_analyzed=20, tokens_excluded=0)
    result = truncation_analysis(rows)
    assert result["groups"]["truncated"]["fnr"] is None
    assert result["groups"]["truncated"]["fnr_interval"] is None
    assert recommendations(result, characterize(rows))["B1"] == "NOT_SUPPORTED_BY_TRUNCATED_FN_EVIDENCE"


def test_confidence_boundaries():
    assert confidence({"raw_score": .4, "error_type": "FN"}) == "BORDERLINE_WRONG"
    assert confidence({"raw_score": .6, "error_type": "FP"}) == "BORDERLINE_WRONG"
    assert confidence({"raw_score": .1, "error_type": "FN"}) == "HIGH_CONFIDENCE_WRONG"
    assert confidence({"raw_score": .9, "error_type": "FP"}) == "HIGH_CONFIDENCE_WRONG"
    assert confidence({"raw_score": .2, "error_type": "FN"}) == "OTHER_WRONG"


def test_confidence_counts_patterns_and_stability(completed):
    records, reports = completed
    result = characterize(records)
    for error in ("FN", "FP"):
        summary = result["confidence"][error]
        assert summary["count"] == summary["borderline"] + summary["high_confidence"] + summary["other"]
    assert len(result["fold_groups"]) == 5
    assert all(p["error_count"] == len(p["supporting_sample_ids"]) for p in result["patterns"])
    assert stability(reports)["recall"]["minimum"] <= stability(reports)["recall"]["maximum"]


@pytest.mark.parametrize("count,expected", [(2, "2-31"), (31, "2-31"), (32, "32-127"),
    (128, "128-256"), (256, "128-256"), (257, "257-512"), (512, "257-512"), (513, "513+")])
def test_length_boundaries(count, expected):
    assert bucket(count) == expected


def test_wilson_descriptive_interval():
    assert interval(0, 0) is None
    assert interval(0, 10)["lower"] == 0
    assert interval(5, 10)["lower"] < .5 < interval(5, 10)["upper"]


def test_schema_and_no_raw_text_artifacts(completed):
    validate_schema(completed[0])
    assert schema_projection(completed[0][0])["metadata"]["partition"] == "BASE_TRAIN"
    assert not {"text", "prompt", "response", "canonical_text_reference"} & set(CSV_FIELDS)
    assert csv_bytes(completed[0]) == csv_bytes(completed[0])
    assert b"synthetic text" not in csv_bytes(completed[0])


def test_dataset_and_authoritative_write_gate(tmp_path):
    allowed = {(ROOT / "Dataset/approved.csv").resolve()}
    payload_policy(ROOT / "Dataset/approved.csv", "rb", os.O_RDONLY, allowed)
    for path, mode, flags in [(ROOT / "Dataset/protected.csv", "rb", os.O_RDONLY),
        (ROOT / "PHASE-3/03_schema/mixed.jsonl", "rb", os.O_RDONLY),
        (ROOT / "Dataset/approved.csv", "wb", os.O_WRONLY),
        (ROOT / "Dataset/approved.csv", None, os.O_RDWR),
        (ROOT / "artifacts/models/dm_b_v1/transformer/model.safetensors", "wb", os.O_WRONLY)]:
        with pytest.raises((ValueError, RuntimeError)):
            payload_policy(path, mode, flags, allowed)


def test_hash_drift_and_path_escape_rejected(tmp_path):
    with pytest.raises(ValueError):
        verify_hashes(ROOT, {"detection_service/configs/dm_b_v1_training.json": "0" * 64})
    with pytest.raises(ValueError):
        verify_hashes(ROOT, {"../outside.json": "0" * 64})


def test_baseline_preserved_and_no_baseline_loader_calls():
    assert baseline_check()["status"] == "PASS"
    code = (ROOT / CODE[0]).read_text() + (ROOT / CODE[1]).read_text()
    assert "from_artifact(" not in code and "snapshot_download(" not in code
    assert "train_once(" not in code and 'load_partition(MANIFEST, "VALIDATION")' not in code


class FakeBatch(dict):
    def to(self, device):
        return self


class FakeTokenizer:
    def encode(self, text, **kwargs):
        assert kwargs["add_special_tokens"] and not kwargs["truncation"]
        return list(range(int(text)))

    def __call__(self, texts, **kwargs):
        assert kwargs["max_length"] == 256 and kwargs["truncation"] and kwargs["padding"]
        counts = [min(int(t), 256) for t in texts]
        width = max(counts)
        return FakeBatch(attention_mask=torch.tensor([[1] * n + [0] * (width - n) for n in counts]),
                         input_ids=torch.zeros((len(texts), width), dtype=torch.long))


class FakeModel:
    def eval(self):
        return self

    def __call__(self, **inputs):
        return SimpleNamespace(logits=torch.tensor([[0., 1.]] * len(inputs["input_ids"])))


def test_actual_predict_padding_special_tokens_and_truncation():
    records = predict(FakeTokenizer(), FakeModel(), ["20", "256", "257", "600"], config())
    assert [r["tokens_analyzed"] for r in records] == [20, 256, 256, 256]
    assert [r["tokens_excluded"] for r in records] == [0, 0, 1, 344]
    assert [r["truncated"] for r in records] == [False, False, True, True]
    assert all(r["logit_margin"] == 1. for r in records)
    assert all(r["raw_score"] == pytest.approx(1 / (1 + math.exp(-1))) for r in records)


def test_preflight_exact_fold_counts_and_membership():
    from detection_service.analysis.semantic_oof_preflight import fold_execution_plan
    rows, _ = selected_rows()
    plan = fold_execution_plan(rows)
    assert (plan["rows"], plan["positive"], plan["negative"]) == (1135, 183, 952)
    assert plan["planned_once_per_sample"]
    assert [r["held_out_positive"] for r in plan["folds"]] == [36, 36, 37, 37, 37]
    for fold in plan["folds"]:
        assert fold["train_rows"] == 908 and fold["held_out_rows"] == 227
        assert fold["identity_overlap"] == fold["canonical_lineage_overlap"] == 0
        assert not set(fold["train_sample_ids"]) & set(fold["held_out_sample_ids"])
        assert fold["train_positive"] + fold["held_out_positive"] == 183
        assert fold["train_negative"] + fold["held_out_negative"] == 952
        assert fold["train_lineage_groups"] + fold["held_out_lineage_groups"] == 1134
    assert [r["train_lineage_groups"] for r in plan["folds"]] == [907, 908, 907, 907, 907]
    assert [r["held_out_lineage_groups"] for r in plan["folds"]] == [227, 226, 227, 227, 227]


def test_preflight_independent_metric_answers():
    from detection_service.analysis.semantic_oof_preflight import metric_validation
    proof = metric_validation()
    expected = proof["binary_fixture"]["expected"]
    for name, value in expected.items():
        actual = proof["binary_fixture"]["actual"][name]
        assert actual == value if isinstance(value, dict) else actual == pytest.approx(value, abs=1e-12)
    assert {expected[k] for k in ("fpr", "fnr", "precision", "recall", "specificity", "f1")} == {.5}
    assert expected["roc_auc"] == .75 and expected["pr_auc"] == 5 / 6
    assert [r["recall"] for r in proof["fixed_fpr_fixture"]["actual"]] == [.25, .5, .75]
    assert [r["fp"] for r in proof["fixed_fpr_fixture"]["actual"]] == [0, 2, 4]


def test_preflight_schema_accepts_hard_rows_and_no_text(completed):
    import jsonschema
    from detection_service.analysis.semantic_oof_preflight import csv_record_schema, output_contract
    schema = csv_record_schema(CSV_FIELDS)
    validator = jsonschema.Draft202012Validator(schema)
    errors = [r for r in completed[0] if r["error_type"] in ("FN", "FP")]
    assert errors
    for row in errors:
        validator.validate({k: row[k] for k in CSV_FIELDS})
    contract = output_contract(CSV_FIELDS)
    assert not contract["raw_text_included"]
    assert contract["original_input_tokens_field"].startswith("input_tokens")
    assert contract["results_status"] == "PENDING AUTHORITATIVE OOF EXECUTION"


def test_preflight_schema_rejects_prompt_or_changed_limit(completed):
    import jsonschema
    from detection_service.analysis.semantic_oof_preflight import csv_record_schema
    validator = jsonschema.Draft202012Validator(csv_record_schema(CSV_FIELDS))
    original = {k: completed[0][0][k] for k in CSV_FIELDS}
    for changed in ({**original, "prompt": "not permitted"}, {**original, "max_input_tokens": 512}):
        with pytest.raises(jsonschema.ValidationError):
            validator.validate(changed)


def test_preflight_output_contract_and_run_metadata(monkeypatch, completed):
    from detection_service.scripts import semantic_oof_baseline as pipeline
    from detection_service.analysis.semantic_oof_preflight import PRODUCT_NAMES, RUN_METADATA_FIELDS, RUN_METADATA_NAME
    monkeypatch.setattr(pipeline, "file_hash", lambda path: "a" * 64)
    metadata = pipeline.build_run_metadata(config(), {"code_commit": "b" * 40, "oof_preflight_sha256": "c" * 64},
                                           completed[1], "2026-10-04T00:00:00+00:00", 10.)
    assert set(RUN_METADATA_FIELDS) <= set(metadata)
    assert set(metadata["output_sha256"]) == set(PRODUCT_NAMES)
    assert RUN_METADATA_NAME not in metadata["output_sha256"]
    assert metadata["code_commit"] == "b" * 40 and len(metadata["per_fold_runtime"]) == 5
    assert metadata["manifest_sha256"] == MANIFEST_SHA256 and metadata["seed"] == 1701
    assert metadata["tokenizer_revision"] == metadata["upstream_revision"] == REVISION


def test_preflight_environment_records_executable_and_versions():
    import sys
    from detection_service.analysis.semantic_oof_preflight import environment
    evidence = environment()
    assert evidence["python_executable"] == sys.executable
    assert evidence["packages"]["torch_runtime"] == torch.__version__
    assert {"python", "torch", "transformers", "scikit-learn", "tokenizers"} <= set(evidence["packages"])


def test_wrong_head_cannot_start_full_run(monkeypatch):
    from detection_service.scripts import semantic_oof_baseline as pipeline
    values = iter(["a" * 40, "b" * 40])
    monkeypatch.setattr(pipeline.subprocess, "check_output", lambda *args, **kwargs: next(values))
    with pytest.raises(ValueError, match="freeze commit"):
        pipeline.committed_freeze(require_clean=True)


def test_dirty_tree_cannot_start_full_run(monkeypatch):
    from detection_service.scripts import semantic_oof_baseline as pipeline
    values = iter(["a" * 40, "a" * 40, " M unrelated_file.py\n"])
    monkeypatch.setattr(pipeline.subprocess, "check_output", lambda *args, **kwargs: next(values))
    with pytest.raises(ValueError, match="clean"):
        pipeline.committed_freeze(require_clean=True)


def test_run_stops_at_preflight_before_loading_text_or_training(monkeypatch, tmp_path):
    from detection_service.scripts import semantic_oof_baseline as pipeline
    historical_output = pipeline.OUTPUT
    acceptance = json.loads((historical_output / 'acceptance_manifest_v1.json').read_text())
    marker = historical_output / 'run_started_v1.json'
    marker_hash = file_hash(marker)
    assert marker_hash == acceptance['original_input_sha256']['run_started_v1.json']
    # Exercise the pre-run gate in a fresh fixture, not the accepted run directory.
    monkeypatch.setattr(pipeline, 'OUTPUT', tmp_path / 'fresh-oof-output')
    def blocked():
        raise ValueError("STOP: intentionally uncommitted preflight")
    def forbidden(*args, **kwargs):
        pytest.fail("run passed its startup gate")
    monkeypatch.setattr(pipeline, "check_prerun", blocked)
    monkeypatch.setattr(pipeline, "load_base_texts", forbidden)
    monkeypatch.setattr(pipeline, "run_folds", forbidden)
    with pytest.raises(ValueError, match="uncommitted"):
        pipeline.run()
    assert not pipeline.OUTPUT.exists()
    assert file_hash(marker) == marker_hash


def test_preflight_plan_deterministic_and_single_class_rejected():
    from detection_service.analysis.semantic_oof_preflight import fold_execution_plan
    rows, _ = fixture()
    assert fold_execution_plan(rows) == fold_execution_plan(rows)
    for row in rows:
        row["label"] = "0"
    with pytest.raises(ValueError, match="both labels"):
        fold_execution_plan(rows)
