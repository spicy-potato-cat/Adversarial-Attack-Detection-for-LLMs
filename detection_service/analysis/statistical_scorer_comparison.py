"""STAT-005 fixed scorers on unchanged, training-fold-derived B2 features."""

from contextlib import nullcontext
import hashlib
import time
import warnings

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from threadpoolctl import threadpool_limits

from detection_service.analysis import statistical_feature_ablation as features
from detection_service.analysis.statistical_oof import check_membership, digest_ids, require
from detection_service.quality.development_fixture import json_bytes

SCORERS = ("S0", "S1", "S2")
B2_SHA = "93d3892b158c35eccfadc27c879754db69ea5293782492ee5d4ff01a33bff983"


def estimator(scorer):
    require(scorer in SCORERS, "undeclared scorer")
    if scorer == "S0":
        return LogisticRegression(**{**{k: v for k, v in features.RECIPE.items() if k != "scorer"}, "max_iter": 20000})
    if scorer == "S1":
        return Pipeline([("scale", StandardScaler()), ("svc", SVC(kernel="rbf", C=1., gamma="scale",
            class_weight="balanced", probability=False, random_state=1701))])
    return HistGradientBoostingClassifier(learning_rate=.1, max_iter=100, max_leaf_nodes=31,
        l2_regularization=0., early_stopping=False, random_state=1701, class_weight="balanced")


def definitions():
    block = next(b for b in features.definitions()["blocks"] if b["schema_version"] == "stat004_B2_v1")
    require(block["feature_count"] == 26 and block["schema_sha256"] == B2_SHA, "B2 drift")
    svm = estimator("S1")
    return {"phase": "TECH-STAT-005", "cycle": "1_OF_MAXIMUM_2", "B2_schema_sha256": B2_SHA,
        "feature_names": block["feature_names"], "feature_count": 26,
        "scorers": {
            "S0": {"family": "LogisticRegression", "params": estimator("S0").get_params(), "scaling": None,
                   "score": "uncalibrated predict_proba class1; ranking only"},
            "S1": {"family": "RBF-SVM", "params": svm.named_steps["svc"].get_params(),
                   "scaling": svm.named_steps["scale"].get_params(), "score": "decision_function; NOT probability"},
            "S2": {"family": "HistGradientBoosting", "params": estimator("S2").get_params(), "scaling": None,
                   "score": "uncalibrated predict_proba class1; ranking only", "openmp_threads": 1}},
        "folds": 5, "seed": 1701, "class_balance": "Training labels only; native class_weight=balanced, n/(2*n_class). No oversampling.",
        "selection": {"material_gain": .02, "near_best_tolerance": .02, "budget_1_5_min_change": -.02,
            "auc_ap_min_change": -.01, "fold_3_sd_max_increase": .03, "fold_3_min_max_drop": .03,
            "under16_recall_min_change": 0., "combined_short_recall_min_change": -.02,
            "long_benign_fp_max_increase": 1, "positive_paired_3pct_lower_bound_required": True,
            "simplicity_order": list(SCORERS),
            "rule": "Non-LR eligibility: >=2pp pooled R3 gain, positive conditional paired 95% lower bound, R1/R5/AUC/AP/fold/subgroup guards. Pick earliest eligible within2pp of best eligible at all1/3/5 budgets; none=>S0. No runtime-based rejection for modest differences.",
            "subgroups": "Frozen diagnostic guardrails, not additional optimization data; long-benign count guard uses17 rows and is not a population guarantee."},
        "bootstrap": {"repetitions": 1000, "seed": 1701, "unit": "Canonical lineage groups; paired identical sample indices",
            "limitations": "Conditional fixed-OOF percentile intervals, no classifier refits/shared-training/multiplicity/selection adjustment; frontiers recomputed per resample."},
        "calibration": False, "hyperparameter_search": False, "raw_threshold_comparison": False,
        "deployment_threshold_selection": False, "final_ds_v2": False, "cross_detector_complementarity": "DEFERRED"}


def digest(payload):
    return hashlib.sha256(json_bytes(payload)).hexdigest()


def fold_features(rows, evidence, fold):
    check_membership(rows)
    require(fold in range(5) and len(rows) == len(evidence), "invalid fold/evidence")
    train = [i for i, r in enumerate(rows) if int(r["outer_fold"]) != fold]
    held = [i for i, r in enumerate(rows) if int(r["outer_fold"]) == fold]
    training, testing = [rows[i] for i in train], [rows[i] for i in held]
    require(not {r["lineage_group"] for r in training} & {r["lineage_group"] for r in testing}, "lineage leakage")
    refs = features.References.fit(training, [evidence[i] for i in train], [r["sample_id"] for r in testing])
    matrix = np.asarray([refs.transform(e, "B2") for e in evidence])
    require(matrix.shape == (len(rows), 26) and np.isfinite(matrix).all(), "B2 matrix drift")
    record = {"fold": fold, "train_membership_sha256": digest_ids(training),
              "held_out_membership_sha256": digest_ids(testing), **refs.payload}
    return matrix, train, held, record


def fit_score(scorer, x, labels, held):
    require(x.ndim == held.ndim == 2 and x.shape[1] == held.shape[1] == 26
            and np.isfinite(x).all() and np.isfinite(held).all() and set(labels.tolist()) == {0, 1}, "invalid scorer input")
    model = estimator(scorer)
    balance = {str(c): len(labels) / (2 * int(sum(labels == c))) for c in (0, 1)}
    start = time.perf_counter()
    context = threadpool_limits(limits=1, user_api="openmp") if scorer == "S2" else nullcontext()
    with context:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always", ConvergenceWarning)
            model.fit(x, labels)
        fit_seconds = time.perf_counter() - start
        messages = [str(w.message) for w in caught if issubclass(w.category, ConvergenceWarning)]
        require(not messages, f"{scorer} convergence warning; stop, no recipe changes")
        scaler = None
        if scorer == "S1":
            svc, scale = model.named_steps["svc"], model.named_steps["scale"]
            require(svc.fit_status_ == 0 and svc.probability is False, "SVM incomplete/probability calibration forbidden")
            require(scale.n_samples_seen_ == len(labels), "scaler training count drift")
            scaler = {"training_rows": int(scale.n_samples_seen_), "mean": scale.mean_.tolist(),
                      "var": scale.var_.tolist(), "scale": scale.scale_.tolist()}
            iteration = svc.n_iter_.tolist()
            extra = {"support_vectors": svc.n_support_.tolist(), "effective_gamma": float(svc._gamma),
                     "actual_class_weights": svc.class_weight_.tolist()}
            predict = model.decision_function
        else:
            iteration = model.n_iter_.tolist() if scorer == "S0" else [int(model.n_iter_)]
            require(scorer != "S0" or max(iteration) < 20000, "LR ceiling; stop")
            require(scorer != "S2" or iteration == [100], "HGB fixed iteration drift")
            extra = {}
            predict = lambda values: model.predict_proba(values)[:, 1]
        start = time.perf_counter()
        scores = np.asarray(predict(held))
        inference_seconds = time.perf_counter() - start
        require(scores.shape == (len(held),) and np.isfinite(scores).all()
                and np.array_equal(scores, predict(held)), "invalid/nonrepeatable scores")
        require(scorer == "S1" or ((scores >= 0) & (scores <= 1)).all(), "invalid probability scores")
    return scores, {"fit_seconds": fit_seconds, "inference_seconds": inference_seconds,
        "inference_ms_per_row": inference_seconds * 1000 / len(held), "n_iter": iteration,
        "completed": True, "convergence_warnings": messages, "training_class_weights": balance,
        "scaler": scaler, **extra}


def evaluate(rows, evidence, progress=None):
    check_membership(rows)
    definitions()
    labels = np.asarray([int(r["label"]) for r in rows])
    scores, reports, references = {s: np.full(len(rows), np.nan) for s in SCORERS}, {s: [] for s in SCORERS}, []
    for fold in range(5):
        matrix, train, held, ref = fold_features(rows, evidence, fold)
        references.append(ref)
        for scorer in SCORERS:
            try:
                predicted, record = fit_score(scorer, matrix[train], labels[train], matrix[held])
            except Exception as exc:
                raise ValueError(f"STOP: {scorer} fold {fold}: {exc}") from exc
            require(np.isnan(scores[scorer][held]).all(), "multiple OOF scores")
            scores[scorer][held] = predicted
            report = {"fold": fold, "train_rows": len(train), "held_out_rows": len(held),
                "train_membership_sha256": ref["train_membership_sha256"],
                "held_out_membership_sha256": ref["held_out_membership_sha256"], "reference_sha256": digest(ref),
                "identity_leakage": 0, "lineage_leakage": 0, **record}
            reports[scorer].append(report)
            if progress:
                progress(scorer, report)
    require(all(np.isfinite(s).all() for s in scores.values()), "missing OOF scores")
    return scores, reports, references
