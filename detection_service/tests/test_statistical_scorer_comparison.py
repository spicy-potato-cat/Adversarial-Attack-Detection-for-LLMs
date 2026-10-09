"""STAT-005 frozen recipes, fold-local transforms and ranking diagnostics."""

import copy
import warnings

import numpy as np
import pytest

from detection_service.analysis import statistical_scorer_comparison as core
from detection_service.analysis import statistical_scorer_results as results
from detection_service.scripts import statistical_scorer_comparison as driver
from detection_service.tests.test_statistical_feature_ablation import fixture, item


@pytest.fixture(scope="module")
def toy():
    rows, evidence = fixture()
    scores, reports, refs = core.evaluate(rows, evidence)
    return rows, evidence, scores, reports, refs


def test_frozen_b2_and_fixture():
    d = core.definitions()
    assert d["feature_count"] == 26 and d["B2_schema_sha256"] == core.B2_SHA
    assert d["feature_names"] == list(core.features.names("B2"))
    assert driver.file_hash(driver.ROOT / driver.baseline.FOLD_PATH) == driver.source.FOLDS
    assert driver.file_hash(driver.ROOT / "data_governance/manifests/development_partition_manifest_v1.csv") == driver.source.MANIFEST
    assert driver.git('branch', '--show-current') == 'exp/r2-ds-001'
    metadata = driver.read(driver.OUT / 'run_metadata_v1.json')
    accepted = driver.read(driver.OUT / 'acceptance_evidence_v1.json')
    assert accepted['status'] == 'PASS'
    assert metadata['start_commit'] == driver.START
    assert metadata['code_commit'] == accepted['model_run_code_commit']
    assert driver.git('merge-base', '--is-ancestor', driver.START, metadata['code_commit']) == ''
    assert driver.git('merge-base', '--is-ancestor', metadata['code_commit'], 'HEAD') == ''
    driver.baseline.verify_hashes(driver.OUT, metadata['artifact_sha256'])
    driver.baseline.verify_hashes(driver.OUT, accepted['verified_sha256'])
    # Runtime provenance stays frozen; test code may evolve after the model run.
    runtime = {path: digest for path, digest in metadata['code_sha256'].items()
               if not path.startswith('detection_service/tests/')}
    driver.baseline.verify_hashes(driver.ROOT, runtime)
    assert metadata['B2_schema_sha256'] == core.B2_SHA
    assert metadata['manifest_sha256'] == driver.source.MANIFEST
    assert metadata['fold_sha256'] == driver.source.FOLDS


def test_exact_scorer_configs():
    lr, svm, hgb = (core.estimator(s) for s in core.SCORERS)
    assert lr.max_iter == 20000 and lr.tol == 1e-4 and lr.solver == "lbfgs"
    assert lr.C == 1 and lr.penalty == "l2" and lr.class_weight == "balanced" and lr.random_state == 1701
    assert svm.named_steps["svc"].get_params() == core.definitions()["scorers"]["S1"]["params"]
    svc = svm.named_steps["svc"]
    assert svc.kernel == "rbf" and svc.C == 1 and svc.gamma == "scale" and svc.class_weight == "balanced"
    assert svc.probability is False and svc.random_state == 1701
    assert hgb.learning_rate == .1 and hgb.max_iter == 100 and hgb.max_leaf_nodes == 31
    assert hgb.l2_regularization == 0 and hgb.early_stopping is False and hgb.random_state == 1701
    assert hgb.class_weight == "balanced" and core.definitions()["scorers"]["S2"]["scaling"] is None


@pytest.mark.parametrize("partition", ["CALIBRATION", "VALIDATION", "INTERNAL_TEST", "FROZEN_EXTERNAL"])
def test_reserved_partitions_rejected(partition):
    rows, evidence = fixture()
    rows[0]["partition"] = partition
    with pytest.raises(ValueError, match="BASE_TRAIN"):
        core.evaluate(rows, evidence)


def test_no_held_out_reference_or_scaler_influence():
    rows, evidence = fixture()
    before, train, held, ref = core.fold_features(rows, evidence, 0)
    changed = copy.deepcopy(evidence)
    for i in held:
        changed[i] = item([100.] * 18)
    after, train2, held2, ref2 = core.fold_features(rows, changed, 0)
    assert ref == ref2 and train == train2 and held == held2
    assert np.array_equal(before[train], after[train])
    y = np.asarray([int(rows[i]["label"]) for i in train])
    _, fit1 = core.fit_score("S1", before[train], y, before[held])
    _, fit2 = core.fit_score("S1", after[train2], y, after[held2])
    assert fit1["scaler"] == fit2["scaler"]
    assert fit1["scaler"]["training_rows"] == 80
    assert fit1["scaler"]["mean"] == np.mean(before[train], axis=0).tolist()
    assert fit1["effective_gamma"] == fit2["effective_gamma"]


def test_lineage_leakage_rejected():
    rows, evidence = fixture()
    rows[0]["lineage_group"] = rows[2]["lineage_group"]
    with pytest.raises(ValueError, match="lineage"):
        core.evaluate(rows, evidence)


@pytest.mark.parametrize("scorer", core.SCORERS)
def test_population_order_weights_and_exactly_once(scorer, toy):
    rows, evidence, scores, reports, refs = toy
    assert np.isfinite(scores[scorer]).all() and len(scores[scorer]) == len(rows)
    assert [r["fold"] for r in reports[scorer]] == list(range(5))
    for r in reports[scorer]:
        train = [row for row in rows if int(row["outer_fold"]) != r["fold"]]
        expected = {str(c): len(train) / (2 * sum(int(row["label"]) == c for row in train)) for c in (0, 1)}
        assert r["training_class_weights"] == expected and r["completed"] and not r["convergence_warnings"]
        assert r["reference_sha256"] == core.digest(refs[r["fold"]])
        assert r["identity_leakage"] == r["lineage_leakage"] == 0
        assert (r["scaler"] is not None) == (scorer == "S1")
        assert r["fit_seconds"] >= 0 and r["inference_seconds"] >= 0


def test_svm_scores_are_not_probabilities(toy):
    _, _, scores, _, _ = toy
    assert min(scores["S1"]) < 0
    assert results.metrics([0, 0, 1, 1], [-3., -2., .1, 4.])["roc_auc"] == 1


def test_ordering_gate():
    rows, evidence = fixture()
    with pytest.raises(ValueError, match="order"):
        core.evaluate(rows[::-1], evidence[::-1])


def test_rank_frontiers_and_counts():
    m = results.metrics([0, 0, 1, 1], [-3., -2., -2., 1.])
    assert m["recall_at_fixed_fpr"][0]["tp"] == 1
    assert m["recall_at_fixed_fpr"][0]["fp"] == 0
    assert m["recall_at_fixed_fpr"][0]["fn"] == 1 and m["recall_at_fixed_fpr"][0]["tn"] == 2
    assert "confusion_matrix" not in m


def test_subgroup_denominators_and_transitions(toy):
    rows, evidence, scores, reports, _ = toy
    aggregate, folds, groups, errors = results.analyze(rows, evidence, scores, reports)
    for s in core.SCORERS:
        buckets = [groups[s][b]["pooled_frontiers"][1] for b in core.features.SHORT_BUCKETS]
        assert sum(b["positive"] for b in buckets) == sum(b["negative"] for b in buckets) == 50
        assert sum(b["tp"] for b in buckets) == aggregate[s]["recall_at_fixed_fpr"][1]["tp"]
        assert groups[s]["64+"]["pooled_frontiers"][1]["fpr"] is None
    assert errors["shared_FN"]["count"] == 0
    assert all(v["count"] == 0 for v in errors["unique_catches"].values())
    assert all(v["count"] == len(v["sample_ids"]) for e in errors["versus_S0"].values() for v in e.values())


def test_paired_alignment_and_zero_difference(monkeypatch, toy):
    rows, _, scores, _, _ = toy
    policy = copy.deepcopy(core.definitions())
    policy["bootstrap"]["repetitions"] = 10
    monkeypatch.setattr(results, "definitions", lambda: policy)
    identical = {s: scores["S0"] for s in core.SCORERS}
    first = results.paired(rows, identical)
    assert first == results.paired(rows, identical)
    assert all(v == 0 for s in first["differences_vs_S0"].values() for m in s["metrics"].values() for v in m.values())
    identical["S1"] = identical["S1"][:-1]
    with pytest.raises(ValueError, match="alignment"):
        results.paired(rows, identical)


def test_tie_retains_simple_lr(monkeypatch, toy):
    rows, evidence, scores, reports, _ = toy
    policy = copy.deepcopy(core.definitions())
    policy["bootstrap"]["repetitions"] = 10
    monkeypatch.setattr(results, "definitions", lambda: policy)
    identical = {s: scores["S0"] for s in core.SCORERS}
    aggregate, folds, groups, _ = results.analyze(rows, evidence, identical, reports)
    comparisons = results.paired(rows, identical)
    assert results.select(aggregate, folds, groups, comparisons)["selected_scorer"] == "S0"


def test_warning_stops_without_scoring(monkeypatch):
    class Failed:
        def fit(self, x, y):
            warnings.warn("not converged", core.ConvergenceWarning)
        def decision_function(self, x):
            pytest.fail("must not score unconverged fit")
    monkeypatch.setattr(core, "estimator", lambda s: Failed())
    with pytest.raises(ValueError, match="convergence"):
        core.fit_score("S1", np.ones((30, 26)), np.asarray([0, 1] * 15), np.ones((5, 26)))


def test_material_gain_uncertainty_and_simplicity_guards(toy):
    rows, evidence, scores, reports, _ = toy
    aggregate, folds, groups, _ = results.analyze(rows, evidence, scores, reports)
    for i, point in enumerate(aggregate["S0"]["recall_at_fixed_fpr"]):
        point["recall"] = .2 + i * .1
    comparisons = {"differences_vs_S0": {s: {"metrics": {"recall_at_3pct": {"lower_95pct": .1}}} for s in ("S1", "S2")}}
    assert results.select(aggregate, folds, groups, comparisons)["selected_scorer"] == "S1"
    for s in ("S1", "S2"):
        aggregate[s]["recall_at_fixed_fpr"][1]["recall"] = .31
    assert results.select(aggregate, folds, groups, comparisons)["selected_scorer"] == "S0"
    for s in ("S1", "S2"):
        aggregate[s]["recall_at_fixed_fpr"][1]["recall"] = .8
        comparisons["differences_vs_S0"][s]["metrics"]["recall_at_3pct"]["lower_95pct"] = -.01
    assert results.select(aggregate, folds, groups, comparisons)["selected_scorer"] == "S0"


def test_no_prompts_or_calibrated_output(monkeypatch, toy):
    rows, evidence, scores, reports, _ = toy
    policy = copy.deepcopy(core.definitions())
    policy["bootstrap"]["repetitions"] = 10
    monkeypatch.setattr(results, "definitions", lambda: policy)
    data = driver.products(rows, evidence, scores, reports, results.paired(rows, scores))
    assert len(data["scorer_predictions_v1.csv"].splitlines()) == 301
    assert all(b"raw_text" not in content and b"semantic_score" not in content for content in data.values())
    assert core.definitions()["calibration"] is False and core.definitions()["hyperparameter_search"] is False


def test_payload_gate():
    driver.source.install_gate({"source_artifact_sha256": {}})
    with pytest.raises(ValueError, match="protected"):
        (driver.ROOT / "Dataset/Raw/forbidden.csv").open()
    with pytest.raises(RuntimeError, match="forbids"):
        (driver.ROOT / "PHASE-3/04_quality/forbidden.jsonl").open()
