"""Analytic completion checks without real models or reserved prompt payloads."""
import copy
import itertools
import math
from pathlib import Path
import subprocess
import sys

import pytest


def test_current_machine_completion_paths_are_additive():
    from detection_service.scripts import common_mode_completion, common_mode_development, guard_development

    assert guard_development.GUARD_OUTPUT == common_mode_development.GUARD_OUTPUT
    assert guard_development.GUARD_OUTPUT == "artifacts/guard_v1/development/completion_v3"
    output, reports = common_mode_completion.release_paths(3)
    assert output == "artifacts/common_mode/development/completion_v3"
    assert all(name.endswith("_v3.md") for name in reports)
    assert common_mode_completion.COMPLETION_START == "3ef06414836a51b3409e7be9251da7753299da3a"

from detection_service.analysis.common_mode import align, analyze, bootstrap, failure_metrics, paired_effect, DIRECTION
from detection_service.analysis.development_characterization import characterization, subgroup_diagnostics
from detection_service.scripts.common_mode_development import ROOT, REVISION
from detection_service.scripts.guard_development import score_records, run_live


def canonical(key, i, score, label):
    return {"sample_id": str(i), "partition": "BASE_TRAIN", "truth_label": label, "score": score,
            "score_direction": DIRECTION, "detector_id": key, "detector_version": "v1",
            "source": "synthetic", "lineage_group": str(i), "fold": i % 2, "attack_family": None}


def four_detectors():
    return {key: [canonical(key, i, score, label) for i, (score, label) in enumerate([(1., 1), (.2, 1), (0., 0), (.8, 0)])]
            for key in ("D_S_v1", "D_S_B2_LR", "D_M-B_v1", "D_G_v1")}


def analytic_misses():
    patterns = list(itertools.product((False, True), repeat=3))
    misses = {key: [p[i] for p in patterns] for i, key in enumerate("SMG")}
    misses["C"] = misses["S"].copy()
    misses["C"][-1] = False
    return misses


def test_pairwise_conditionals_analytic():
    p = failure_metrics({"a": [True, True, False, False], "b": [True, False, False, False]})["pairwise"][0]
    assert p["jfn_count"] == 1 and p["left_fn_count"] == 2 and p["right_fn_count"] == 1
    assert p["p_failure_left_given_right"] == 1.
    assert p["p_failure_right_given_left"] == .5


def test_pairwise_zero_denominator_and_small_count_flag():
    result = failure_metrics({key: [False] for key in "SMG"}, {"stack": list("SMG")})
    assert all(p["p_failure_left_given_right"] is None and p["p_failure_right_given_left"] is None for p in result["pairwise"])
    assert all(u["small_conditional_denominator"] for u in result["unique"])


def test_paired_stack_changes_and_bootstrap():
    stacks = {"old": list("SMG"), "new": list("CMG")}
    comparison = {"baseline": "S", "candidate": "C", "others": ["M", "G"], "stack_names": ("old", "new")}
    result = failure_metrics(analytic_misses(), stacks)
    effects = paired_effect(result, **comparison)
    assert next(r["delta"] for r in effects if r["metric"] == "fnr") == -1 / 8
    assert next(r["delta"] for r in effects if r["metric"] == "all_detector_fn_count") == -1
    assert next(r["delta"] for r in effects if r["metric"] == "unique_catch_count") == 1
    a = bootstrap(analytic_misses(), list("abcdefgh"), stacks, comparison, repetitions=40)
    b = bootstrap(analytic_misses(), list("abcdefgh"), stacks, comparison, repetitions=40)
    assert a == b and "delta/all_detector_jfn/primary_stack" in a["intervals"]
    assert result["unique"][0]["other_members_miss_count"] >= 0


@pytest.mark.parametrize("field,value", [("sample_id", "extra"), ("truth_label", 0), ("source", "wrong"),
                                       ("score_direction", "unknown"), ("lineage_group", "wrong")])
def test_dg_alignment_refusals(field, value):
    data = four_detectors()
    data["D_G_v1"][0][field] = value
    with pytest.raises(ValueError):
        align(data)


def test_four_detector_order_and_group_accounting():
    data = four_detectors()
    stacks = {"old": ["D_S_v1", "D_M-B_v1", "D_G_v1"], "new": ["D_S_B2_LR", "D_M-B_v1", "D_G_v1"]}
    result = analyze(data, stacks, repetitions=10)
    assert result == analyze({k: list(reversed(v)) for k, v in reversed(list(data.items()))}, stacks, repetitions=10)
    for budget in result["budgets"]:
        for field in ("source", "fold", "attack_family"):
            groups = [g for g in budget["grouped"] if g["field"] == field]
            assert sum(g["rows"] for g in groups) == 4
            assert sum(g["attack_rows"] for g in groups) == 2
            for key in data:
                assert sum(next(r["tp"] for r in g["individual"] if r["detector"] == key) for g in groups) == 1
        family = next(g for g in budget["grouped"] if g["field"] == "attack_family")
        assert family["value"] == "UNKNOWN"


@pytest.mark.parametrize("scores,auc,ap", [([1., 0.], 1., 1.), ([0., 1.], 0., .5), ([.5, .5], .5, .5)])
def test_analytic_ranking_ties(scores, auc, ap):
    result = characterization([1, 0], scores, [True, False])
    assert result["roc_auc"] == auc and result["pr_auc"] == ap
    assert result["native"]["tp"] == result["native"]["tn"] == 1


def test_native_vote_is_not_score_cutpoint():
    result = characterization([1, 0], [.5, .5], [False, True])
    assert result["native"]["fn"] == result["native"]["fp"] == 1
    assert result["native"]["fpr"] == result["native"]["fnr"] == 1


@pytest.mark.parametrize("labels", [[1, 1], [0, 0]])
def test_single_label_source_metrics_undefined(labels):
    result = characterization(labels, [.2, .8], [False, True])
    assert result["roc_auc"] is None and result["pr_auc"] is None and result["fixed_fpr"] is None


def test_subgroup_stronger_catches_and_patterns():
    data = four_detectors()
    # At zero FPR, all only catch the highest-score attack. Recover short attack
    # with semantic, then catch the benign long record to exercise FP accounting.
    data["D_M-B_v1"][1]["score"] = .9
    result = analyze(data, repetitions=10)
    diagnostics = subgroup_diagnostics(data, result["budgets"][0]["individual"], {"0": 10, "1": 8, "2": 70, "3": 64})
    short, long = diagnostics
    assert short["count"] == 2 and short["detector_counts"]["D_M-B_v1"] == 2
    assert short["either_stronger_detector_catches"] == 2 and short["candidate_all_three_miss"] == 0
    assert long["count"] == 2 and all(v == 0 for v in long["detector_counts"].values())
    assert sum(p["count"] for p in short["patterns"]) == 2
    assert "NO_ENSEMBLE" in short["scope"]


def test_subgroup_missing_guard_never_assumed_zero():
    data = four_detectors()
    del data["D_G_v1"]
    result = analyze(data, repetitions=10)
    short = subgroup_diagnostics(data, result["budgets"][0]["individual"], {"0": 10, "1": 8, "2": 70, "3": 64})[0]
    assert short["detector_counts"]["D_G_v1"] is None
    assert short["either_stronger_detector_catches"] is None and short["candidate_all_three_miss"] is None


def test_missing_guard_logical_bounds_collapse_when_semantic_catches_all():
    data = four_detectors()
    del data["D_G_v1"]
    data["D_M-B_v1"][1]["score"] = .9
    result = analyze(data, repetitions=10)
    short = subgroup_diagnostics(data, result["budgets"][0]["individual"], {"0": 10, "1": 8, "2": 70, "3": 64})[0]
    assert short["detector_counts"]["D_G_v1"] is None
    assert short["either_stronger_detector_catches"] == 2
    assert short["candidate_all_three_miss"] == 0
    assert short["candidate_all_three_miss_bounds"] == {"lower": 0, "upper": 0}


def fake_score(sid, text):
    return {"status": "success", "detector_id": "guard_external", "detector_version": "dg_v1", "model_revision": REVISION,
            "raw_score": .5, "binary_vote": False, "latency_ms": .1,
            "input_coverage": {"input_tokens": 3, "tokens_analyzed": 3, "tokens_excluded": 0,
                               "coverage_ratio": 1., "truncated": False, "inference_chunks": 1}}


def score_inputs():
    rows = [{"record_id": str(i), "partition": "BASE_TRAIN", "canonical_label": str(i % 2),
             "lineage_group_id": str(i), "source_dataset": "synthetic"} for i in range(2)]
    folds = [{"sample_id": str(i), "partition": "BASE_TRAIN", "label": str(i % 2), "lineage_group": str(i), "outer_fold": str(i)} for i in range(2)]
    return rows, folds, ["synthetic a", "synthetic b"]


def test_one_call_per_sample_no_prompt_artifact():
    rows, folds, texts = score_inputs()
    calls = []
    def detect(sid, text):
        calls.append(sid)
        return fake_score(sid, text)
    scored = list(score_records(rows, folds, texts, detect))
    assert calls == ["0", "1"]
    assert all(r["raw_score"] == .5 and r["native_binary_prediction"] == 0 for r in scored)
    assert all(not any("text" in field or "prompt" in field for field in r) for r in scored)


@pytest.mark.parametrize("partition", ["CALIBRATION", "VALIDATION", "INTERNAL_TEST", "FROZEN_EXTERNAL", "FINAL_TEST"])
def test_reserved_refusal_before_detector_call(partition):
    rows, folds, texts = score_inputs()
    rows[0]["partition"] = partition
    def detect(*args):
        raise AssertionError("must not score")
    with pytest.raises(ValueError, match="reserved"):
        list(score_records(rows, folds, texts, detect))


@pytest.mark.parametrize("field,value", [("model_revision", "wrong"), ("status", "insufficient_input"),
                                       ("raw_score", math.nan), ("binary_vote", 1)])
def test_invalid_guard_result_refused(field, value):
    rows, folds, texts = score_inputs()
    def detect(*args):
        result = fake_score(*args)
        result[field] = value
        return result
    with pytest.raises(ValueError):
        list(score_records(rows, folds, texts, detect))


def test_blocked_live_run_before_payload_or_model(monkeypatch, tmp_path):
    import detection_service.scripts.guard_development as module
    monkeypatch.setattr(module, "preflight", lambda root: ({"status": "BLOCKED"}, [], [], {}, {}))
    def forbidden(*args):
        raise AssertionError("payload must remain unopened")
    monkeypatch.setattr(module, "selected_texts", forbidden)
    with pytest.raises(ValueError, match="blocked"):
        run_live(tmp_path)
    assert not list(tmp_path.iterdir())


def test_model_free_modules_in_fresh_process():
    code = "import sys; import detection_service.scripts.common_mode_completion; import detection_service.scripts.guard_development; assert not any(n in sys.modules for n in ('torch','transformers','sklearn')); print('PASS')"
    p = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True)
    assert p.returncode == 0, p.stderr


def test_frozen_oof_subgroup_reconstruction():
    from detection_service.scripts.common_mode_completion import reconstruct
    result, *_ = reconstruct(repetitions=10)
    b = next(r for r in result["budgets"] if r["budget"] == .03)
    assert b["subgroups"][0]["count"] == 26
    assert b["subgroups"][0]["detector_counts"]["D_S_B2_LR"] == 0
    assert b["subgroups"][1]["count"] == 17
    assert b["subgroups"][1]["detector_counts"]["D_S_B2_LR"] == 12
    assert result["aligned_samples"] == 1135
    families = [g for g in b["grouped"] if g["field"] == "attack_family"]
    assert sum(g["rows"] for g in families) == 1135
    assert next(g["rows"] for g in families if g["value"] == "direct_prompt_injection") == 4


def test_started_guard_run_refuses_before_models(monkeypatch, tmp_path):
    import detection_service.scripts.guard_development as module
    monkeypatch.setattr(module, "preflight", lambda root: ({"status": "READY"}, [], [], {}, {}))
    output = tmp_path / module.GUARD_OUTPUT
    output.mkdir(parents=True)
    (output / "dg_v1_run_started.json").write_text("{}")
    with pytest.raises(ValueError, match="already started"):
        module.run_live(tmp_path)
    assert not (output / "dg_v1_base_train_predictions.csv").exists()


def test_future_evidence_release_does_not_overwrite_report_paths():
    from detection_service.scripts.common_mode_completion import release_paths
    old_output, old_reports = release_paths(2)
    new_output, new_reports = release_paths(3)
    assert old_output != new_output and not set(old_reports) & set(new_reports)
    assert all(name.endswith("_v3.md") for name in new_reports)
