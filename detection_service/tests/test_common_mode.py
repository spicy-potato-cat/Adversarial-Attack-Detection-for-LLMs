"""Analytic truth tables and refusal tests; no model/data payload required."""
import copy
import itertools
import math
import sys

import pytest

from detection_service.analysis.common_mode import (
    DIRECTION, align, analyze, bootstrap, failure_metrics, fixed_fpr, paired_effect,
)


def records(key, scores=(1., 0.)):
    return [{"sample_id": str(i), "partition": "BASE_TRAIN", "truth_label": 1 - i,
             "detector_id": key, "detector_version": "v1", "score": score,
             "score_direction": DIRECTION, "source": "synthetic", "lineage_group": str(i), "fold": i}
            for i, score in enumerate(scores)]


def table():
    patterns = list(itertools.product((False, True), repeat=3))
    return {key: [r[i] for r in patterns] for i, key in enumerate("SMG")}


def test_analytic_independent_truth_table():
    result = failure_metrics(table(), {"stack": list("SMG")})
    assert result["fnr"] == {"S": .5, "M": .5, "G": .5}
    for pair in result["pairwise"]:
        assert pair["jfn_count"] == 2
        assert pair["jfn"] == pair["independence_reference"] == .25
        assert pair["ejf"] == 0
        assert pair["fn_jaccard"] == 1 / 3
    assert result["stacks"][0]["all_detector_fn_count"] == 1
    assert result["stacks"][0]["all_detector_jfn"] == 1 / 8
    for unique in result["unique"]:
        assert unique["unique_catch_count"] == 1
        assert unique["unique_catch_rate"] == 1 / 8
        assert unique["other_members_miss_count"] == 2
        assert unique["recovery_given_others_miss"] == .5


def test_correlated_failures():
    pair = failure_metrics({"a": [True, False], "b": [True, False]})["pairwise"][0]
    assert pair["jfn"] == .5 and pair["ejf"] == .25 and pair["fn_jaccard"] == 1


def test_disjoint_failures():
    pair = failure_metrics({"a": [True, False], "b": [False, True]})["pairwise"][0]
    assert pair["jfn"] == 0 and pair["ejf"] == -.25 and pair["fn_jaccard"] == 0


def test_empty_union_and_undefined_recovery():
    result = failure_metrics({k: [False, False] for k in "SMG"}, {"stack": list("SMG")})
    assert all(p["fn_jaccard"] == 0 for p in result["pairwise"])
    assert all(p["recovery_given_others_miss"] is None for p in result["unique"])


def test_missing_stack_stays_unmeasured():
    result = failure_metrics({"S": [True], "M": [True]}, {"stack": list("SMG")})
    assert result["stacks"][0]["all_detector_jfn"] is None
    assert all(r["unique_catch_count"] is None for r in result["unique"])


@pytest.mark.parametrize("field,value,match", [
    ("truth_label", 0, "truth label mismatch"), ("lineage_group", "other", "lineage mismatch"),
    ("source", "other", "source mismatch"), ("fold", 2, "fold mismatch"),
    ("score_direction", "lower", "score direction"), ("score_direction", None, "score direction"),
    ("score", math.nan, "invalid score"), ("score", math.inf, "invalid score"),
    ("truth_label", 1.0, "invalid truth label"), ("partition", "VALIDATION", "partition"),
    ("detector_version", None, "identity"), ("detector_version", "other", "identity"),
])
def test_alignment_refusals(field, value, match):
    data = {k: records(k) for k in "ab"}
    data["b"][0][field] = value
    with pytest.raises(ValueError, match=match):
        align(data)


@pytest.mark.parametrize("change", ["missing", "duplicate", "extra"])
def test_identity_refusals(change):
    data = {k: records(k) for k in "ab"}
    if change == "missing":
        data["b"].pop()
    elif change == "duplicate":
        data["b"].append(copy.deepcopy(data["b"][0]))
    else:
        data["b"].append({**data["b"][0], "sample_id": "extra"})
    with pytest.raises(ValueError):
        align(data)


def test_alignment_order_and_optional_metadata():
    data = {"b": list(reversed(records("b"))), "a": records("a")}
    data["b"][0]["source"] = None
    assert list(align(data)) == ["a", "b"]
    assert [r["sample_id"] for r in align(data)["b"]] == ["0", "1"]


def test_metadata_mismatch_when_first_unknown():
    data = {k: records(k) for k in "abc"}
    data["a"][0]["source"] = None
    data["c"][0]["source"] = "other"
    with pytest.raises(ValueError, match="source mismatch"):
        align(data)


def test_lineage_fold_leakage():
    data = records("a")
    data[1]["lineage_group"] = data[0]["lineage_group"]
    with pytest.raises(ValueError, match="lineage.*leakage"):
        align({"a": data})


@pytest.mark.parametrize("budget,expected_fp", [(0.01, 1), (0.03, 3), (0.05, 5)])
def test_budgets_and_inclusive_binary_conversion(budget, expected_fp):
    labels = [0] * 100 + [1] * 6
    scores = [float(i) for i in range(100)] + [98.5, 97.5, 96.5, 95.5, 94.5, 93.5]
    point = fixed_fpr(labels, scores, (budget,))[0]
    predicted = [s >= point["threshold"] for s in scores]
    assert point["fp"] == sum(p and y == 0 for p, y in zip(predicted, labels)) == expected_fp
    assert point["tp"] == expected_fp
    assert point["fpr"] <= budget


def test_tied_blocks_cannot_split_and_most_conservative_tie():
    point = fixed_fpr([0] * 100 + [1, 1], [0.] * 98 + [1., 1., 2., 1.], (.01,))[0]
    assert point["tp"] == 1 and point["fp"] == 0 and point["threshold"] == 2.
    # Extra benign blocks that catch no attacks cannot lower the chosen threshold.
    point = fixed_fpr([0, 0, 1], [1., 0., 2.], (1.,))[0]
    assert point["threshold"] == 2. and point["fp"] == 0


def test_all_negative_point():
    point = fixed_fpr([0, 1], [1., 1.], (0.,))[0]
    assert point["threshold"] is None and point["no_positive_predictions"]
    assert point["tp"] == point["fp"] == 0


@pytest.mark.parametrize("budget", [-1., 1.1, math.nan, math.inf, "0.01"])
def test_budget_refusal(budget):
    with pytest.raises(ValueError, match="budget"):
        fixed_fpr([0, 1], [0., 1.], (budget,))


def test_paired_deltas_including_stack_and_unique():
    misses = table()
    misses["C"] = misses["S"].copy()
    misses["C"][-1] = False  # Recover the single all-detector miss.
    stacks = {"old": list("SMG"), "new": list("CMG")}
    result = failure_metrics(misses, stacks)
    effect = paired_effect(result, "S", "C", list("MG"), ("old", "new"))
    assert next(r["delta"] for r in effect if r["metric"] == "all_detector_jfn") == -1 / 8
    assert next(r["delta"] for r in effect if r["metric"] == "unique_catch_count") == 1
    assert next(r["delta"] for r in effect if r["metric"] == "jfn" and r["other"] == "M") == -1 / 8


def test_bootstrap_determinism_joint_lineage_and_deltas():
    misses = table()
    misses["C"] = misses["S"].copy()
    comparison = {"baseline": "S", "candidate": "C", "others": ["M", "G"]}
    groups = ["duplicate", "duplicate", "2", "3", "4", "5", "6", "7"]
    a = bootstrap(misses, groups, comparison=comparison, repetitions=50)
    b = bootstrap(dict(reversed(list(misses.items()))), groups, comparison=comparison, repetitions=50)
    assert a == b
    assert a["attack_lineage_groups"] == 7
    for key, interval in a["intervals"].items():
        if key.startswith("delta/"):
            assert interval == {"estimate": 0., "lower": 0., "upper": 0.}


def test_analyze_order_grouped_and_no_model_imports():
    data = {k: records(k) for k in "abc"}
    first = analyze(data, {"stack": list("abc")}, repetitions=10)
    second = analyze({k: list(reversed(v)) for k, v in reversed(list(data.items()))}, {"stack": list("abc")}, repetitions=10)
    assert first == second
    assert len(first["budgets"]) == 3
    assert first["budgets"][0]["stacks"][0]["all_detector_jfn"] == 0
    assert first["budgets"][0]["grouped"]
    assert "torch" not in sys.modules and "transformers" not in sys.modules


@pytest.mark.parametrize("misses", [{"a": []}, {"a": [True], "b": []}, {"a": [1]}])
def test_invalid_indicators(misses):
    with pytest.raises(ValueError):
        failure_metrics(misses)


def test_committed_adapter_population_and_frontier_reconstruction():
    from detection_service.scripts.common_mode_development import ROOT, INPUTS, canonical, read_csv, read_json
    fixture = {r["sample_id"]: r for r in read_csv(ROOT / "artifacts/quality/quality_001/development_folds_v1.csv")}
    data = {k: canonical(read_csv(ROOT / name), k, fixture) for k, name in INPUTS.items()}
    ordered = align(data)
    assert len(ordered["D_S_v1"]) == 1135
    expected_files = {"D_S_v1": "artifacts/statistical_v2/oof/ds_v1_recipe_oof_metrics.json",
                      "D_S_B2_LR": "artifacts/statistical_v2/scorer_comparison/scorer_metrics_v1.json",
                      "D_M-B_v1": "artifacts/semantic_v2/oof/dm_b_v1_recipe_oof_metrics.json"}
    for key, name in expected_files.items():
        reference = read_json(ROOT / name)
        if key == "D_S_B2_LR":
            reference = reference["S0"]
        actual = fixed_fpr([r["truth_label"] for r in ordered[key]], [r["score"] for r in ordered[key]])
        assert [(p["tp"], p["fp"]) for p in actual] == [(p["tp"], p["fp"]) for p in reference["recall_at_fixed_fpr"]]


@pytest.mark.parametrize("field,value", [("label", "1"), ("lineage_group", "bad"), ("fold", "5"), ("score_kind", "unknown")])
def test_selected_candidate_adapter_refuses_drift(field, value):
    from detection_service.scripts.common_mode_development import ROOT, INPUTS, canonical, read_csv
    fixture = {r["sample_id"]: r for r in read_csv(ROOT / "artifacts/quality/quality_001/development_folds_v1.csv")}
    rows = read_csv(ROOT / INPUTS["D_S_B2_LR"])
    rows[0][field] = value
    with pytest.raises(ValueError):
        canonical(rows, "D_S_B2_LR", fixture)


def test_authoritative_integrity_refusal(tmp_path):
    from detection_service.scripts.common_mode_development import checked_hash
    path = tmp_path / "evidence.csv"
    path.write_bytes(b"changed")
    with pytest.raises(ValueError, match="hash mismatch"):
        checked_hash(path, "0" * 64)
