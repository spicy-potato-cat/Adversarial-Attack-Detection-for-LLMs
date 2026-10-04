"""Post-run acceptance regressions use frozen predictions/metadata, never model fits."""

import ast
import csv
import io
import json
import subprocess

import pytest

from detection_service.analysis import semantic_oof_acceptance as acceptance
from detection_service.analysis.semantic_oof import interval


@pytest.fixture(scope="module")
def evidence():
    records = acceptance.original.read_predictions()
    _, sources = acceptance.original.selected_rows()
    return records, sources, acceptance.products(records, sources)


def load(evidence, name):
    return json.loads(evidence[2][name])


def test_all_original_output_hashes():
    assert len(acceptance.EXPECTED_OUTPUTS) == 9
    acceptance.original.verify_hashes(acceptance.OUT, acceptance.EXPECTED_OUTPUTS)


def test_original_code_commit_in_all_run_records():
    for name in ("completion_v1.json", "run_started_v1.json", "dm_b_v1_oof_run_metadata.json"):
        assert acceptance.read(acceptance.OUT / name)["code_commit"] == acceptance.RUN_COMMIT


def test_original_preflight_hash():
    assert acceptance.file_hash(acceptance.original.PREFLIGHT / "oof_preflight_v1.json") == acceptance.PREFLIGHT_SHA


def test_full_authority_verifier_accepts_original_or_descendant_head():
    records, sources, baseline = acceptance.authoritative_inputs()
    assert len(records) == len(sources) == 1135
    assert baseline["hash_checks"] == 96


def test_fixture_identity_and_leakage(evidence):
    records = evidence[0]
    assert len(records) == len({r["sample_id"] for r in records}) == 1135
    assert sum(r["label"] for r in records) == 183
    groups = {}
    for row in records:
        groups.setdefault(row["lineage_group"], set()).add(row["fold"])
        assert row["partition"] == "BASE_TRAIN" and row["calibrated_probability"] is None
    assert len(groups) == 1134 and all(len(folds) == 1 for folds in groups.values())


@pytest.mark.parametrize("key,fp,fn", [("raw_0_5", 5, 17), ("budget_1pct", 7, 6),
                                      ("budget_3pct", 22, 4), ("budget_5pct", 34, 2)])
def test_rate_reconstruction_and_denominators(evidence, key, fp, fn):
    row = load(evidence, "dm_b_v1_rate_intervals_v1.json")[key]
    assert (row["fp"], row["fn"]) == (fp, fn)
    assert row["fpr"] == fp / 952 and row["fnr"] == fn / 183
    assert row["fpr_95pct"] == interval(fp, 952) and row["fnr_95pct"] == interval(fn, 183)


@pytest.mark.parametrize("successes,total,low,high", [(0, 4, 0, .4898908364545973),
    (4, 183, .008532172862779297, .05484486826842917),
    (22, 952, .015309792016924884, .03474187542143915)])
def test_wilson_hand_checked(successes, total, low, high):
    value = interval(successes, total)
    assert value["lower"] == pytest.approx(low, abs=1e-14)
    assert value["upper"] == pytest.approx(high, abs=1e-14)
    assert interval(successes, total) == value


def test_empty_interval_is_not_zero():
    assert interval(0, 0) is None


def test_fold_stability_matches_original_and_population_sd(evidence):
    stability = load(evidence, "dm_b_v1_fold_stability_v1.json")
    original = acceptance.read(acceptance.OUT / "dm_b_v1_recipe_fold_metrics.json")["folds"]
    for fold, report in zip(stability["folds"], original, strict=True):
        assert fold["sample_count"] == 227
        for field in ("roc_auc", "pr_auc", "recall_at_fixed_fpr", "confusion_matrix"):
            assert fold[field] == report["metrics"][field]
    summary = stability["summaries"]["budget_3pct"]["recall"]
    assert summary["mean"] == pytest.approx(.978078078078078)
    assert summary["population_sd"] == pytest.approx(.0207098374168969)
    assert (summary["min"], summary["max"]) == (34 / 36, 1)


def test_threshold_equality_is_recovered(evidence):
    rows = list(csv.DictReader(io.StringIO(evidence[2]["dm_b_v1_raw_fn_v1.csv"].decode())))
    row = next(r for r in rows if r["sample_id"] == "W2-303f4b2a371e72661137710d")
    assert float(row["raw_score"]) == float(row["descriptive_3pct_threshold"])
    assert row["recovered_at_3pct"] == "True" and float(row["distance_below_threshold"]) == 0


def test_raw_and_persistent_sets_and_confidence(evidence):
    residual = load(evidence, "dm_b_v1_residual_failure_analysis_v1.json")
    assert len(residual["raw_fn_ids"]) == 17 and len(residual["recovered_ids"]) == 13
    assert tuple(residual["persistent_ids"]) == acceptance.PERSISTENT_IDS
    assert set(residual["raw_fn_ids"]) == set(residual["recovered_ids"]) | set(acceptance.PERSISTENT_IDS)
    assert not set(residual["recovered_ids"]) & set(acceptance.PERSISTENT_IDS)
    assert residual["raw_high_confidence_fn"] == 12
    assert residual["persistent_high_confidence"] == 4 and residual["persistent_borderline"] == 0


def test_persistent_metadata_is_id_only_and_source_preserved(evidence):
    rows = list(csv.DictReader(io.StringIO(evidence[2]["dm_b_v1_persistent_fn_3pct_v1.csv"].decode())))
    assert tuple(r["sample_id"] for r in rows) == acceptance.PERSISTENT_IDS
    assert [int(r["input_tokens"]) for r in rows] == [19, 19, 25, 43]
    for row in rows:
        assert row["attack_family"] == "direct_prompt_injection"
        assert row["generator"] == "NOT_AVAILABLE" and row["structural_subtype"] == "UNKNOWN"
        assert row["record_locator"].startswith("ART-W2-DEEPSET-")
        assert row["truncated"] == "False" and row["tokens_excluded"] == "0"
        assert row["tokens_analyzed"] == row["input_tokens"]
        assert float(row["distance_below_threshold"]) > 0
        assert "prompt" not in row and "text" not in row


def test_unknown_metadata_is_not_inferred():
    row = {key: None for key in ("sample_id", "fold", "source_name", "source_revision", "lineage_group",
           "logit_margin", "confidence_category", "input_tokens", "tokens_analyzed", "truncated", "tokens_excluded")}
    row["raw_score"] = .01
    result = acceptance.metadata_row(row, {}, .02)
    assert result["attack_family"] == "UNKNOWN" and result["record_locator"] == "UNKNOWN"
    assert result["generator"] == "NOT_AVAILABLE"


def test_shared_broad_family_is_not_actionable(evidence):
    residual = load(evidence, "dm_b_v1_residual_failure_analysis_v1.json")
    assert residual["all_positive_metadata_distribution"]["attack_family"] == {"direct_prompt_injection": 183}
    assert residual["coherence_classification"] == "PARTIAL_CLUSTER" and not residual["actionable_cluster"]
    assert residual["decision"] == "FREEZE_DM_B_V1" and residual["persistent_distinct_lineage_groups"] == 4


def test_truncation_does_not_explain_current_misses(evidence):
    truncation = load(evidence, "dm_b_v1_residual_failure_analysis_v1.json")["truncation"]
    assert (truncation["positive_truncated"], truncation["fn"], truncation["tp"]) == (4, 0, 4)
    assert truncation["fnr_95pct"]["upper"] > .48
    assert truncation["B1_256_to_512"] == "NOT_SUPPORTED_AS_NEXT_MODEL_IMPROVEMENT_EXPERIMENT"


def test_analysis_deterministic_and_isolated(evidence):
    assert acceptance.products(evidence[0], evidence[1]) == evidence[2]
    assert all(not used for used in load(evidence, "dm_b_v1_residual_failure_analysis_v1.json")["isolation"].values())
    assert "not an unbiased estimate" in acceptance.CAVEAT


def test_postrun_refuses_training_before_load(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("post-run execution passed its completed-run gate")
    monkeypatch.setattr(acceptance.original, "check_prerun", forbidden)
    monkeypatch.setattr(acceptance.original, "load_base_texts", forbidden)
    monkeypatch.setattr(acceptance.original, "run_folds", forbidden)
    with pytest.raises(ValueError, match="run already started"):
        acceptance.original.run()


@pytest.mark.parametrize("relative", ["Dataset/Raw/example.csv", "PHASE-3/03_schema/example.jsonl"])
def test_acceptance_blocks_all_raw_and_protected(relative):
    with pytest.raises((ValueError, RuntimeError)):
        acceptance.original.payload_policy(acceptance.ROOT / relative, "r", 0, set())


def test_frozen_models_cannot_be_written():
    with pytest.raises(ValueError):
        acceptance.original.payload_policy(acceptance.ROOT / "artifacts/models/dm_b_v1/config.json", "w", 0, set())


def test_unrelated_head_rejected(monkeypatch):
    monkeypatch.setattr(acceptance.subprocess, "run", lambda *a, **k: subprocess.CompletedProcess([], 1))
    with pytest.raises(ValueError, match="ancestor"):
        acceptance.verify_run_provenance({})


def test_acceptance_contains_no_model_execution_calls():
    tree = ast.parse((acceptance.ROOT / acceptance.CODE[0]).read_text(encoding="utf-8"))
    forbidden = {"run_folds", "fit_transformer", "load_base_texts", "initialize", "predict", "synthetic_smoke", "run", "upstream"}
    calls = {n.func.attr for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)}
    # subprocess.run is permitted only for the Git ancestry check.
    assert not (calls & (forbidden - {"run"}))
    runs = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "run"]
    assert len(runs) == 1 and isinstance(runs[0].func.value, ast.Name) and runs[0].func.value.id == "subprocess"
