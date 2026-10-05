"""Synthetic OOF correctness and metadata integrity, without real source texts."""

import copy
import csv
import json

import numpy as np
import pytest

from detection_service.analysis.statistical_oof import (
    COMPARISON_THRESHOLD, BUDGETS, check_membership, fixed_fpr, metrics, run_folds,
    stable_predictions, stability, characterize, hypotheses, rate_intervals, length_bucket,
)
from detection_service.app.detectors.statistical_risk.scorer import RECIPE, StatisticalScorer
from detection_service.app.detectors.statistical_risk.schema import FEATURE_NAMES, schema_hash
from detection_service.quality.development_fixture import ROOT, verify
from detection_service.quality.policy import FOLD_PATH
from detection_service.scripts.statistical_oof_baseline import load_base_texts


def synthetic():
    rows = [{"sample_id": f"synthetic-{i:03}", "partition": "BASE_TRAIN", "label": str(i % 2),
             "lineage_group": "LG-N1-" + f"{i:024x}", "source_name": "synthetic", "outer_fold": str(i % 5)} for i in range(40)]
    rng = np.random.default_rng(1701)
    x = rng.uniform(0.1, 2.0, size=(40, 10))
    x[:, 0] = np.arange(40) / 40
    x[:, 1] += np.asarray([int(r["label"]) for r in rows]) * 2
    x[:, 2] = x[:, 1]
    x[:, 6] = x[:, 0]
    evidence = [{"input_tokens": 20, "tokens_analyzed": 19, "tokens_excluded": 0, "truncated": False,
                 "window_count": 1, "character_length": 50, "inference_chunks": 1, "extraction_latency_ms": 0.0} for _ in rows]
    return rows, x, evidence


@pytest.fixture(scope="module")
def completed():
    rows, x, evidence = synthetic()
    return run_folds(rows, x, evidence)


def test_frozen_fixture_verified_without_constructing_new_artifact():
    result = verify()
    assert result["fold_sha256"] == "19dc0153cc257cc2331782d6dd61b7bb9fb8cb0ed88d3e782b69d5ba05c4bb8d"
    assert result["statistics"]["rows"] == 1135
    with (ROOT / FOLD_PATH).open(encoding="utf-8", newline="") as handle:
        check_membership(list(csv.DictReader(handle)))


def test_feature_schema_and_recipe_not_changed():
    assert len(FEATURE_NAMES) == 10
    assert schema_hash() == "2b042f88e7403985e5f94e34bb1107b377069e591322767a482a33b5e2cbf8b7"
    assert RECIPE == {"scorer": "LogisticRegression", "solver": "lbfgs", "penalty": "l2", "C": 1.0,
                      "class_weight": "balanced", "max_iter": 1000, "random_state": 1701, "fit_intercept": True}
    assert COMPARISON_THRESHOLD == 0.5 and BUDGETS == (.01, .03, .05)


def test_one_prediction_each_and_deterministic_order(completed):
    rows, reports = completed
    assert len(rows) == len({r["sample_id"] for r in rows}) == 40
    assert [r["sample_id"] for r in rows] == sorted(r["sample_id"] for r in rows)
    assert {r["fold"] for r in rows} == set(range(5))
    assert len(reports) == 5


def test_fit_never_sees_held_out_matrix_or_labels():
    rows, x, evidence = synthetic()
    calls = []

    def observed(matrix, fitting_rows):
        fold = len(calls)
        wanted = [i for i, r in enumerate(rows) if int(r["outer_fold"]) != fold]
        assert np.array_equal(matrix, x[wanted])
        assert [int(r["canonical_label"]) for r in fitting_rows] == [int(rows[i]["label"]) for i in wanted]
        assert all(r["partition"] == "BASE_TRAIN" for r in fitting_rows)
        calls.append(fold)
        return StatisticalScorer.fit(matrix, fitting_rows)

    _, reports = run_folds(rows, x, evidence, fit=observed)
    assert calls == list(range(5))
    assert all(r["identity_leakage"] == r["lineage_leakage"] == 0 for r in reports)


def test_authoritative_whole_train_model_never_loaded(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("final baseline scorer must not load for OOF")
    monkeypatch.setattr(StatisticalScorer, "load", forbidden)
    run_folds(*synthetic())


def test_fold_fits_use_exact_recipe(completed):
    for report in completed[1]:
        assert report["recipe"] == RECIPE
        assert report["train_rows"] == 32 and report["held_out_rows"] == 8
        assert report["train_positive"] == 16
        assert report["n_iter"][0] < 1000


def test_deterministic_scientific_predictions_and_metrics(completed):
    second, reports = run_folds(*synthetic())
    assert stable_predictions(second) == stable_predictions(completed[0])
    for first, other in zip(completed[1], reports, strict=True):
        assert first["metrics"] == other["metrics"]
        assert first["coefficients"] == other["coefficients"]


@pytest.mark.parametrize("mutation,reason", [("order", "order"), ("duplicate", "duplicate"),
                                         ("partition", "BASE_TRAIN"), ("label", "binary labels"), ("fold", "membership")])
def test_membership_drift_rejected(mutation, reason):
    rows, x, evidence = synthetic()
    if mutation == "order":
        rows.reverse()
    elif mutation == "duplicate":
        rows[1]["sample_id"] = rows[0]["sample_id"]
    elif mutation == "partition":
        rows[0]["partition"] = "VALIDATION"
    elif mutation == "label":
        rows[0]["label"] = "2"
    elif mutation == "fold":
        rows[0]["outer_fold"] = "5"
    with pytest.raises(ValueError, match=reason):
        run_folds(rows, x, evidence)


def test_split_lineage_rejected():
    rows, x, evidence = synthetic()
    rows[1]["lineage_group"] = rows[0]["lineage_group"]
    with pytest.raises(ValueError, match="lineage group split"):
        run_folds(rows, x, evidence)


def test_same_group_is_preserved_in_fold_training():
    rows, x, evidence = synthetic()
    rows[10]["lineage_group"] = rows[0]["lineage_group"]
    assert rows[10]["outer_fold"] == rows[0]["outer_fold"]
    result, reports = run_folds(rows, x, evidence)
    assert result[0]["fold"] == result[10]["fold"]
    assert all(r["lineage_leakage"] == 0 for r in reports)


@pytest.mark.parametrize("partition", ["CALIBRATION", "VALIDATION", "INTERNAL_TEST", "FINAL_TEST", "FROZEN_EXTERNAL"])
def test_partition_content_rejected_before_any_payload_open(partition):
    with pytest.raises(ValueError, match="text selection forbidden"):
        load_base_texts([{"partition": partition}], {})


def test_missing_or_nonfinite_features_stop():
    rows, x, evidence = synthetic()
    x[0, 0] = np.nan
    with pytest.raises(Exception, match="non-finite"):
        run_folds(rows, x, evidence)
    with pytest.raises(ValueError, match="membership mismatch"):
        run_folds(rows, np.zeros((40, 10)), evidence[:-1])


def test_metric_correctness():
    result = metrics([0, 0, 1, 1], [.1, .8, .2, .9])
    assert result["confusion_matrix"] == {"tn": 1, "fp": 1, "fn": 1, "tp": 1}
    assert result["fpr"] == result["fnr"] == result["accuracy"] == result["f1"] == .5
    assert result["roc_auc"] == .75
    assert result["pr_auc"] == pytest.approx(5 / 6)


def test_threshold_cannot_be_tuned():
    with pytest.raises(ValueError, match="cutpoint is frozen"):
        metrics([0, 1], [.1, .9], threshold=.6)


def test_fixed_fpr_whole_tied_blocks_and_no_feasible_positive():
    points = fixed_fpr([1, 0, 1, 0], [.9, .9, .8, .1])
    assert all(p["recall"] == 0 and p["fp"] == 0 for p in points)
    assert all(p["no_positive_predictions"] and p["descriptive_threshold"] is None for p in points)


def test_fixed_fpr_integer_budget_boundary():
    labels = [1, 1] + [0] * 100
    scores = [.96, .94, .95] + [.1] * 99
    point = fixed_fpr(labels, scores)[0]
    assert point["budget"] == .01 and point["attained_fpr"] == .01
    assert point["recall"] == 1 and point["fp"] == 1 and point["tp"] == 2
    assert point["descriptive_threshold"] == .94


def test_fixed_fpr_perfect_ranking_and_conservative_ties():
    points = fixed_fpr([0, 0, 1, 1], [.1, .2, .8, .9])
    assert all(p["recall"] == 1 and p["attained_fpr"] == 0 for p in points)
    assert all(p["descriptive_threshold"] == .8 for p in points)


def test_fixed_fpr_all_scores_tied():
    assert fixed_fpr([0, 1], [.5, .5])[0]["recall"] == 0


def test_binary_inclusive_cutpoint():
    result = metrics([0, 1], [.5, .5])
    assert result["confusion_matrix"] == {"tn": 0, "fp": 1, "fn": 0, "tp": 1}


def test_stability_matches_fold_series(completed):
    stats = stability(completed[1])
    scores = [r["metrics"]["fpr"] for r in completed[1]]
    assert stats["fpr"]["mean"] == np.mean(scores)
    assert stats["fpr"]["standard_deviation_population"] == np.std(scores, ddof=0)


def test_characterization_and_hypotheses_are_descriptive_only(completed):
    diagnostics = characterize(completed[0])
    gaps = hypotheses(diagnostics)
    assert sum(g["rows"] for g in diagnostics["feature_summaries"].values()) == 40
    assert "NOT_ASSESSABLE" in diagnostics["unmeasured"]["anomaly_position_or_tail"]
    assert gaps["features_implemented"] is gaps["ds_v2_created"] is False
    assert all("NOT_IMPLEMENTED" in next(k for k in h if k.startswith("proposed_features")) for h in gaps["hypotheses"])
    counts = [r["unique_supporting_error_count"] for r in gaps["hypotheses"]]
    assert counts == sorted(counts, reverse=True)


def test_conditional_lineage_bootstrap_deterministic(completed):
    first = rate_intervals(completed[0], repetitions=50)
    assert first == rate_intervals(completed[0], repetitions=50)
    assert first["valid_repetitions"] == 50
    assert set(first["intervals"]) == {"fpr", "fnr", "recall"}


@pytest.mark.parametrize("tokens,bucket", [(2, "2-31"), (31, "2-31"), (32, "32-127"), (128, "128-511"),
                                           (512, "512-4095"), (4096, "4096+")])
def test_preregistered_length_buckets(tokens, bucket):
    assert length_bucket(tokens) == bucket


def test_predictions_have_no_prompt_or_token_strings(completed):
    assert all(not ({"text", "prompt", "response", "token", "token_id"} & set(r)) for r in completed[0])
    assert all(r["calibrated_probability"] is None for r in completed[0])
