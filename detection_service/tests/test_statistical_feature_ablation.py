"""STAT-004 feature mathematics, fold-local references and governance regressions."""

import copy
import json

import numpy as np
import pytest

from detection_service.analysis import statistical_feature_ablation as features
from detection_service.analysis import statistical_ablation_results as results
from detection_service.app.detectors.statistical.features import extract_features
from detection_service.app.detectors.statistical_risk.schema import FEATURE_NAMES
from detection_service.quality.development_fixture import ROOT, file_hash
from detection_service.scripts import statistical_feature_ablation as pipeline


def item(values, input_tokens=None):
    vector = extract_features(values, 128, 64, 8)
    return {"surprisals": list(values), "input_tokens": input_tokens or len(values) + 1,
            "tokens_analyzed": len(values), "v1_features": [getattr(vector, name) for name in FEATURE_NAMES]}


def fixture():
    rows, evidence = [], []
    for i in range(100):
        label = i % 2
        rows.append({"sample_id": f"synthetic-{i:03}", "partition": "BASE_TRAIN", "label": str(label),
                     "outer_fold": str((i // 2) % 5), "lineage_group": f"group-{i:03}"})
        evidence.append(item([1. + label + (i % 7) * .05, 2. + label, 1.5 + label] * 6))
    return rows, evidence


@pytest.fixture(scope="module")
def toy():
    rows, evidence = fixture()
    scores, reports, refs = features.evaluate(rows, evidence)
    return rows, evidence, scores, reports, refs


def test_authoritative_fold_and_manifest_hashes():
    assert file_hash(ROOT / pipeline.baseline.FOLD_PATH) == pipeline.FOLDS
    assert file_hash(ROOT / "data_governance/manifests/development_partition_manifest_v1.csv") == pipeline.MANIFEST


def test_baseline_integrity_and_fixed_counts():
    metadata = pipeline.read(pipeline.baseline.OUTPUT / "completion_v1.json")
    pipeline.baseline.verify_hashes(pipeline.baseline.OUTPUT, metadata["artifact_sha256"])
    metrics = pipeline.read(pipeline.baseline.OUTPUT / "ds_v1_recipe_oof_metrics.json")
    assert metrics["confusion_matrix"] == {"tn": 749, "fp": 203, "fn": 60, "tp": 123}


@pytest.mark.parametrize("tokens,bin,bucket", [(2, 0, "<16"), (15, 0, "<16"), (16, 1, "16-31"),
    (31, 1, "16-31"), (32, 2, "32-63"), (63, 2, "32-63"), (64, 3, "64+"), (127, 3, "64+"), (128, 4, "64+")])
def test_length_boundaries(tokens, bin, bucket):
    assert features.length_bin(tokens) == bin and features.short_bucket(tokens) == bucket


@pytest.mark.parametrize("tokens", [0, 1, -1, 1.2])
def test_invalid_lengths_rejected(tokens):
    with pytest.raises(ValueError):
        features.length_bin(tokens)


def test_schema_counts_order_and_determinism():
    definitions = features.definitions()
    assert definitions == features.definitions()
    assert [len(features.names(b)) for b in features.BLOCKS] == [10, 16, 26, 29, 33, 47, 67]
    assert features.names("B0") == FEATURE_NAMES
    assert len(features.names("B6")) == len(set(features.names("B6")))
    assert definitions["B7"] == "PREDECLARED_SKIPPED"
    for b in definitions["blocks"]:
        digest = b["schema_sha256"]
        assert digest == features.hashlib.sha256(features.json_bytes({k: v for k, v in b.items() if k != "schema_sha256"})).hexdigest()


def test_training_only_reference_membership_and_benign_filter(toy):
    rows, _, _, _, references = toy
    for ref in references:
        fold = ref["fold"]
        training = {r["sample_id"] for r in rows if int(r["outer_fold"]) != fold}
        benign = {r["sample_id"] for r in rows if int(r["outer_fold"]) != fold and r["label"] == "0"}
        assert set(ref["fit_training_ids"]) == training
        assert set(ref["benign_ids"]) == benign
        assert len(training) == 80


def test_held_out_cannot_influence_reference_or_normalization():
    rows, evidence = fixture()
    train = [i for i, row in enumerate(rows) if row["outer_fold"] != "0"]
    held = [rows[i]["sample_id"] for i in range(len(rows)) if i not in train]
    before = features.References.fit([rows[i] for i in train], [evidence[i] for i in train], held)
    modified = copy.deepcopy(evidence)
    for i in range(len(rows)):
        if i not in train:
            modified[i] = item([100.] * 18)
    after = features.References.fit([rows[i] for i in train], [modified[i] for i in train], held)
    assert before.payload == after.payload
    assert np.array_equal(before.transform(evidence[1], "B6"), after.transform(evidence[1], "B6"))


def test_reference_rejects_held_out_ids():
    rows, evidence = fixture()
    with pytest.raises(ValueError, match="leakage"):
        features.References.fit(rows, evidence, [rows[0]["sample_id"]])


@pytest.mark.parametrize("partition", ["CALIBRATION", "VALIDATION", "INTERNAL_TEST", "FROZEN_EXTERNAL"])
def test_reserved_reference_partitions_rejected(partition):
    rows, evidence = fixture()
    rows[0]["partition"] = partition
    with pytest.raises(ValueError, match="reserved"):
        features.References.fit(rows, evidence)


def test_sparse_pool_is_explicit_and_deterministic():
    rows, evidence = fixture()
    ref = features.References.fit(rows, evidence).payload
    assert ref == features.References.fit(rows, evidence).payload
    assert ref["bins"]["0"]["sparse_fallback"] is True
    assert ref["bins"]["0"]["pooled_bins"] == [0, 1]
    assert ref["bins"]["1"]["pooled_bins"] == [1]
    assert all(b["benign_row_count"] >= 20 for b in ref["bins"].values())


def test_mad_iqr_quantiles_topk_correct():
    rows, evidence = fixture()
    ref = features.References.fit(rows, evidence)
    value = item([1., 2., 3., 4., 10.])
    vector = dict(zip(features.names("B2"), ref.transform(value, "B2"), strict=True))
    assert vector["surprisal_median"] == 3
    assert vector["surprisal_mad"] == 1
    assert vector["surprisal_iqr"] == 2
    assert vector["surprisal_q25"] == 2 and vector["surprisal_q75"] == 4
    assert vector["surprisal_q90"] == pytest.approx(7.6)
    assert vector["surprisal_top5_mean"] == 4
    assert vector["surprisal_top10pct_mean"] == 10


def test_exceedance_reference_and_strict_threshold():
    rows, _ = fixture()
    evidence = [item([1., 2., 3., 4., 5.]) for _ in rows]
    ref = features.References.fit(rows, evidence)
    assert ref.payload["bins"]["0"]["tau"] == [5., 5., 5.]
    value = dict(zip(features.names("B3"), ref.transform(item([5., 6.]), "B3"), strict=True))
    assert value["exceedance_q95_fraction"] == .5


@pytest.mark.parametrize("mask,expected", [([False], [0, 0, 0, 0]), ([True], [1, 1, 1, 1]),
    ([True, True, False, True], [.5, .5, .375, 1 / 3]), ([True] * 4, [.25, 1, 1, 0])])
def test_anomaly_runs(mask, expected):
    assert features.anomaly_runs(mask) == pytest.approx(expected)


@pytest.mark.parametrize("n", [1, 2, 3, 7, 8, 15, 16, 31, 32, 63, 64, 65, 128])
def test_short_inputs_and_all_features_finite(n):
    rows, evidence = fixture()
    ref = features.References.fit(rows, evidence)
    vector = ref.transform(item([1.] * n), "B6")
    assert vector.shape == (67,) and np.isfinite(vector).all()
    assert np.array_equal(vector[:10], item([1.] * n)["v1_features"])


def test_empty_regions_are_flagged_and_remainders_are_deterministic():
    rows, evidence = fixture()
    ref = features.References.fit(rows, evidence)
    tiny = dict(zip(features.names("B5"), ref.transform(item([4.]), "B5"), strict=True))
    assert tiny["prefix_mean"] == 4 and tiny["prefix_available"] == 1
    assert tiny["middle_available"] == tiny["tail_available"] == 0
    regular = dict(zip(features.names("B5"), ref.transform(item([1., 2., 3., 4., 5.]), "B5"), strict=True))
    assert regular["prefix_mean"] == 1.5 and regular["middle_mean"] == 3.5 and regular["tail_mean"] == 5


@pytest.mark.parametrize("n,scale", [(9, 8), (17, 8), (65, 16), (128, 32), (130, 64)])
def test_multiscale_full_coverage_and_valid_sizes(n, scale):
    values = np.arange(n)
    windows = features.windows(values, scale)
    assert all(len(w) == scale for w in windows)
    assert set(np.concatenate(windows)) == set(values)
    assert windows[-1][-1] == n - 1


def test_unusable_windows_are_explicit():
    rows, evidence = fixture()
    ref = features.References.fit(rows, evidence)
    vector = dict(zip(features.names("B6"), ref.transform(item([1.] * 7), "B6"), strict=True))
    assert features.windows(np.arange(7), 8) == []
    assert all(vector[f"window_{scale}_available"] == 0 for scale in features.SCALES)


@pytest.mark.parametrize("values", [[float("nan")], [float("inf")], [-1.]])
def test_invalid_token_evidence_rejected(values):
    with pytest.raises(ValueError):
        features.sequence({"surprisals": values, "input_tokens": 2, "tokens_analyzed": 1})


def test_exactly_once_per_block_and_fixed_metrics(toy):
    rows, evidence, scores, reports, _ = toy
    for b in features.BLOCKS:
        assert len(scores[b]) == 100 and np.isfinite(scores[b]).all()
        assert [r["fold"] for r in reports[b]] == list(range(5))
        assert all(r["identity_leakage"] == r["lineage_leakage"] == 0 for r in reports[b])
    products = pipeline.analysis_products(rows, evidence, scores, reports)
    assert len(products["block_predictions_v1.csv"].splitlines()) == 701
    assert products == pipeline.analysis_products(rows, evidence, scores, reports)


def test_lr_recipe_is_unchanged(toy):
    rows, evidence, _, _, _ = toy
    x = np.asarray([e["v1_features"] for e in evidence])
    model = features.fit_lr(x, np.asarray([int(r["label"]) for r in rows]))
    assert all(model.get_params()[k] == v for k, v in features.RECIPE.items() if k != "scorer")


def test_lineage_leakage_rejected():
    rows, evidence = fixture()
    rows[0]["lineage_group"] = rows[2]["lineage_group"]
    with pytest.raises(ValueError, match="lineage"):
        features.evaluate(rows, evidence)


def test_fixed_fpr_and_threshold_equality():
    points = results.fixed_fpr([0, 0, 1, 1], [.1, .2, .2, .8], (.0, .5))
    assert points[0]["recall"] == .5 and points[0]["fp"] == 0
    assert points[1]["recall"] == 1 and points[1]["fp"] == 1
    assert results.votes(np.asarray([.1, .2, .2, .8]), points[1]).tolist() == [False, True, True, True]


def test_error_bank_transitions_hand_checked():
    result = results.transitions(["a", "b", "c", "d"], np.asarray([1, 0, 1, 0]),
                                 np.asarray([False, True, True, False]), np.asarray([True, False, False, True]))
    assert [result[k]["count"] for k in result] == [1, 1, 1, 1]


def test_short_analysis_denominators_and_null_empty_group(toy):
    rows, evidence, scores, reports, _ = toy
    aggregate, folds, short, errors = results.summarize(rows, evidence, scores, reports)
    assert short["B0"]["<16"]["raw_0_5"]["recall"] is None
    assert short["B0"]["16-31"]["raw_0_5"]["positive"] == 50
    assert results.select(rows, evidence, scores, aggregate, folds)["final_ds_v2_created"] is False


def test_simplicity_rule_uses_smallest_equivalent_block(toy):
    rows, evidence, scores, reports, _ = toy
    aggregate, folds, _, _ = results.summarize(rows, evidence, scores, reports)
    aggregate = copy.deepcopy(aggregate)
    for p in aggregate["B0"]["recall_at_fixed_fpr"]:
        p["recall"] = .1
    selection = results.select(rows, evidence, scores, aggregate, folds)
    assert selection["selected_block"] == "B1"


def test_no_raw_prompt_or_semantic_score_artifacts(toy):
    rows, evidence, scores, reports, _ = toy
    products = pipeline.analysis_products(rows, evidence, scores, reports)
    assert all("raw_text" not in text.decode() and "semantic_score" not in text.decode() for text in products.values())
    assert features.definitions()["complementarity"] == "DEFERRED_TO_LATER_COMMON_STACK_ANALYSIS"


def test_paired_bootstrap_deterministic_and_identical_scores_zero(monkeypatch, toy):
    rows, _, scores, _, _ = toy
    policy = copy.deepcopy(features.definitions())
    policy["paired_bootstrap"]["repetitions"] = 10
    monkeypatch.setattr(results, "definitions", lambda: policy)
    identical = {b: scores["B0"] for b in features.BLOCKS}
    first = results.paired_bootstrap(rows, identical)
    assert first == results.paired_bootstrap(rows, identical)
    for block in first["differences_vs_B0"].values():
        assert block["valid_repetitions"] == 10
        assert all(v == 0 for metric in block["metrics"].values() for v in metric.values())


def test_protected_source_policy_rejects_payloads():
    config = {"source_artifact_sha256": {}}
    pipeline.baseline.install_payload_gate(config)
    with pytest.raises(ValueError, match="protected"):
        (ROOT / "Dataset/Raw/nonapproved.csv").open()
    with pytest.raises(RuntimeError, match="protected"):
        (ROOT / "PHASE-3/04_quality/nonapproved.jsonl").open()
