"""Honest fold-local reproduction of the fixed D_S v1 recipe; no v2 features."""

from collections import Counter
import hashlib
import json
import math
import time

import numpy as np
from sklearn.metrics import average_precision_score, roc_auc_score, roc_curve, precision_recall_curve

from detection_service.app.detectors.statistical_risk.scorer import StatisticalScorer, RECIPE, check_matrix
from detection_service.app.detectors.statistical_risk.schema import FEATURE_NAMES, schema_hash

COMPARISON_THRESHOLD = 0.5
BUDGETS = (0.01, 0.03, 0.05)
BUCKETS = (("2-31", 2, 32), ("32-127", 32, 128), ("128-511", 128, 512),
           ("512-4095", 512, 4096), ("4096+", 4096, None))


def require(condition, message):
    if not condition:
        raise ValueError("STOP: " + message)


def digest_ids(rows):
    return hashlib.sha256("\n".join(r["sample_id"] for r in rows).encode("utf-8")).hexdigest()


def check_membership(rows):
    require(bool(rows), "empty OOF fixture")
    ids = [r["sample_id"] for r in rows]
    require(len(ids) == len(set(ids)), "duplicate sample identity")
    require(ids == sorted(ids), "OOF order must follow frozen sample-ID order")
    require({int(r["outer_fold"]) for r in rows} == set(range(5)), "invalid five-fold membership")
    require(all(r["partition"] == "BASE_TRAIN" and str(r["label"]) in ("0", "1") for r in rows), "BASE_TRAIN-only binary labels required")
    groups = {}
    for row in rows:
        group = row["lineage_group"]
        require(bool(group), "missing lineage group")
        if group in groups:
            require(groups[group] == int(row["outer_fold"]), "lineage group split")
        groups[group] = int(row["outer_fold"])


def fixed_fpr(labels, scores, budgets=BUDGETS):
    """Attainable empirical ROC points, including the no-positive-prediction point."""
    labels, scores = np.asarray(labels), np.asarray(scores, dtype=float)
    require(set(labels.tolist()) == {0, 1}, "fixed-FPR metrics need both labels")
    require(labels.shape == scores.shape and np.isfinite(scores).all(), "invalid score/label arrays")
    fpr, tpr, thresholds = roc_curve(labels, scores, drop_intermediate=False)
    negative, positive = int(sum(labels == 0)), int(sum(labels == 1))
    points = []
    for alpha in budgets:
        allowable = np.flatnonzero(fpr <= alpha)
        best = max(tpr[allowable])
        # Ties prefer smaller FPR, then the first (highest/most conservative) threshold.
        candidates = [int(i) for i in allowable if tpr[i] == best]
        index = min(candidates, key=lambda i: (fpr[i], i))
        threshold = float(thresholds[index])
        predicted = scores >= threshold
        points.append({"budget": alpha, "recall": float(tpr[index]), "attained_fpr": float(fpr[index]),
                       "tp": int(sum(predicted & (labels == 1))), "fp": int(sum(predicted & (labels == 0))),
                       "positive_denominator": positive, "negative_denominator": negative,
                       "descriptive_threshold": threshold if math.isfinite(threshold) else None,
                       "no_positive_predictions": not math.isfinite(threshold),
                       "threshold_role": "DESCRIPTIVE_ROC_POINT_NOT_SELECTED_OR_DEPLOYED_POLICY"})
    return points


def metrics(labels, scores, threshold=COMPARISON_THRESHOLD):
    require(threshold == COMPARISON_THRESHOLD, "comparison cutpoint is frozen at raw 0.5")
    labels, scores = np.asarray(labels, dtype=int), np.asarray(scores, dtype=float)
    require(labels.shape == scores.shape and set(labels.tolist()) == {0, 1}, "invalid metric labels")
    require(np.isfinite(scores).all() and ((scores >= 0) & (scores <= 1)).all(), "invalid raw probabilities")
    predicted = scores >= threshold
    tn = int(sum((labels == 0) & ~predicted))
    fp = int(sum((labels == 0) & predicted))
    fn = int(sum((labels == 1) & ~predicted))
    tp = int(sum((labels == 1) & predicted))
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn)
    return {"sample_count": len(labels), "positive_count": tp + fn, "negative_count": tn + fp,
            "comparison_rule": "raw_LR_class_1_probability >= 0.5; DEVELOPMENT_ONLY_UNCALIBRATED",
            "confusion_matrix": {"tn": tn, "fp": fp, "fn": fn, "tp": tp},
            "accuracy": (tn + tp) / len(labels), "precision": precision, "recall": recall,
            "specificity": tn / (tn + fp), "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0,
            "fnr": fn / (tp + fn), "fpr": fp / (tn + fp), "roc_auc": float(roc_auc_score(labels, scores)),
            "pr_auc": float(average_precision_score(labels, scores)), "pr_auc_definition": "average_precision",
            "recall_at_fixed_fpr": fixed_fpr(labels, scores), "scope": "DEVELOPMENT_OOF_NOT_FINAL_PERFORMANCE"}


def curves(labels, scores):
    fpr, tpr, thresholds = roc_curve(labels, scores, drop_intermediate=False)
    precision, recall, pr_thresholds = precision_recall_curve(labels, scores)
    return {"roc": {"fpr": fpr.tolist(), "tpr": tpr.tolist(),
                    "thresholds": [float(t) if math.isfinite(t) else None for t in thresholds]},
            "pr": {"precision": precision.tolist(), "recall": recall.tolist(), "thresholds": pr_thresholds.tolist()},
            "scope": "DESCRIPTIVE_ONLY_NO_OPERATING_POINT_SELECTED"}


def error_type(label, prediction):
    return {(0, 0): "TN", (0, 1): "FP", (1, 0): "FN", (1, 1): "TP"}[(int(label), int(prediction))]


def run_folds(rows, matrix, evidence, fit=StatisticalScorer.fit):
    check_membership(rows)
    x = check_matrix(matrix)
    require(len(x) == len(rows) == len(evidence), "feature/evidence membership mismatch")
    labels = np.asarray([int(r["label"]) for r in rows])
    predictions, fold_reports = {}, []
    for fold in range(5):
        test = [i for i, r in enumerate(rows) if int(r["outer_fold"]) == fold]
        train = [i for i, r in enumerate(rows) if int(r["outer_fold"]) != fold]
        train_rows, test_rows = [rows[i] for i in train], [rows[i] for i in test]
        require(not ({r["sample_id"] for r in train_rows} & {r["sample_id"] for r in test_rows}), "training/held-out identity leakage")
        require(not ({r["lineage_group"] for r in train_rows} & {r["lineage_group"] for r in test_rows}), "training/held-out lineage leakage")
        started = time.perf_counter()
        scorer = fit(x[train], [{"partition": "BASE_TRAIN", "canonical_label": str(y)} for y in labels[train]])
        fit_seconds = time.perf_counter() - started
        started = time.perf_counter()
        scores = scorer.predict(x[test])
        predict_ms = (time.perf_counter() - started) * 1000
        require(np.array_equal(scores, scorer.predict(x[test])), "repeat held-out inference drift")
        for i, score in zip(test, scores, strict=True):
            row = rows[i]
            sid = row["sample_id"]
            require(sid not in predictions, "duplicate OOF prediction")
            vote = int(score >= COMPARISON_THRESHOLD)
            predictions[sid] = {
                **row, "fold": fold, "label": int(row["label"]),
                "detector_id": "statistical_perplexity", "detector_version": "ds_v1",
                "candidate_id": "ds_v1_recipe_fold_local_baseline",
                "raw_score": float(score), "calibrated_probability": None, "binary_prediction": vote,
                "error_type": error_type(row["label"], vote),
                **{name: float(value) for name, value in zip(FEATURE_NAMES, x[i], strict=True)},
                **evidence[i], "scorer_predict_ms_amortized": predict_ms / len(test),
                "latency_ms": evidence[i]["extraction_latency_ms"] + predict_ms / len(test),
            }
        fold_reports.append({"fold": fold, "train_rows": len(train), "held_out_rows": len(test),
                             "train_positive": int(sum(labels[train])), "held_out_positive": int(sum(labels[test])),
                             "train_lineage_groups": len({r["lineage_group"] for r in train_rows}),
                             "held_out_lineage_groups": len({r["lineage_group"] for r in test_rows}),
                             "train_membership_sha256": digest_ids(train_rows), "held_out_membership_sha256": digest_ids(test_rows),
                             "identity_leakage": 0, "lineage_leakage": 0, "recipe": RECIPE, "n_iter": scorer.model.n_iter_.tolist(),
                             "coefficients": scorer.model.coef_.tolist(), "intercept": scorer.model.intercept_.tolist(),
                             "fit_seconds": fit_seconds, "metrics": metrics(labels[test], scores)})
    result = [predictions[r["sample_id"]] for r in rows]
    require(len(result) == len(rows) and len(predictions) == len(rows), "OOF coverage failure")
    return result, fold_reports


def stability(fold_reports):
    measures = ("accuracy", "precision", "recall", "specificity", "f1", "fnr", "fpr", "roc_auc", "pr_auc")
    output = {}
    values = {name: [f["metrics"][name] for f in fold_reports] for name in measures}
    for i, alpha in enumerate(BUDGETS):
        values[f"recall_at_fpr_{alpha}"] = [f["metrics"]["recall_at_fixed_fpr"][i]["recall"] for f in fold_reports]
    for name, series in values.items():
        output[name] = {"mean": float(np.mean(series)), "standard_deviation_population": float(np.std(series, ddof=0)),
                        "minimum": float(min(series)), "maximum": float(max(series))}
    return output


def rate_intervals(records, repetitions=2000, seed=1701):
    groups = {}
    for row in records:
        counts = groups.setdefault(row["lineage_group"], np.zeros(4, dtype=np.int64))
        counts[("TN", "FP", "FN", "TP").index(row["error_type"])] += 1
    matrix = np.asarray(list(groups.values()))
    rng = np.random.default_rng(seed)
    draws = {"fpr": [], "fnr": [], "recall": []}
    for _ in range(repetitions):
        tn, fp, fn, tp = matrix[rng.integers(0, len(matrix), size=len(matrix))].sum(axis=0)
        if tn + fp and tp + fn:
            draws["fpr"].append(float(fp / (tn + fp)))
            draws["fnr"].append(float(fn / (fn + tp)))
            draws["recall"].append(float(tp / (fn + tp)))
    return {"method": "lineage-group percentile bootstrap on fixed OOF predictions", "level": 0.95,
            "seed": seed, "repetitions": repetitions, "valid_repetitions": len(draws["fpr"]),
            "scope": "CONDITIONAL_DEVELOPMENT_DIAGNOSTICS; no model refits, threshold selection or final population guarantee",
            "limitations": "Does not capture model-refit uncertainty or all dependence from overlapping training folds; lineage is canonical minimum only.",
            "intervals": {k: {"lower": float(np.quantile(v, 0.025)), "upper": float(np.quantile(v, 0.975))} for k, v in draws.items()}}


def describe(values):
    if not values:
        return None
    array = np.asarray(values, dtype=float)
    return {"count": len(values), "minimum": float(min(array)), "q25": float(np.quantile(array, .25)),
            "median": float(np.median(array)), "q75": float(np.quantile(array, .75)),
            "q90": float(np.quantile(array, .90)), "maximum": float(max(array))}


def length_bucket(tokens):
    for name, low, high in BUCKETS:
        if tokens >= low and (high is None or tokens < high):
            return name
    raise ValueError("invalid scoreable input token count")


def subgroup(records):
    counts = Counter(r["error_type"] for r in records)
    tn, fp, fn, tp = [counts[k] for k in ("TN", "FP", "FN", "TP")]
    return {"rows": len(records), "positive": tp + fn, "negative": tn + fp,
            "confusion_matrix": {"tn": tn, "fp": fp, "fn": fn, "tp": tp},
            "fpr": fp / (tn + fp) if tn + fp else None, "fnr": fn / (tp + fn) if tp + fn else None,
            "recall": tp / (tp + fn) if tp + fn else None}


def characterize(records):
    output = {"scope": "DESCRIPTIVE_DEVELOPMENT_STATISTICS_NOT_SEMANTIC_LABELS_OR_CAUSAL_EXPLANATIONS",
              "comparison_threshold": COMPARISON_THRESHOLD,
              "feature_summaries": {}, "source_groups": {}, "fold_groups": {}, "length_groups": {}, "patterns": []}
    for error in ("TP", "TN", "FP", "FN"):
        chosen = [r for r in records if r["error_type"] == error]
        output["feature_summaries"][error] = {"rows": len(chosen), "features": {
            name: describe([r[name] for r in chosen]) for name in (*FEATURE_NAMES, "input_tokens", "tokens_analyzed", "window_count")}}
    for key, field in (("source_groups", "source_name"), ("fold_groups", "fold")):
        for value in sorted({r[field] for r in records}):
            output[key][str(value)] = subgroup([r for r in records if r[field] == value])
    for name, _, _ in BUCKETS:
        output["length_groups"][name] = subgroup([r for r in records if length_bucket(r["input_tokens"]) == name])

    for label, error, correct in ((1, "FN", "TP"), (0, "FP", "TN")):
        reference = [r for r in records if r["label"] == label]
        q = {name: {p: float(np.quantile([r[name] for r in reference], value)) for p, value in (("q25", .25), ("q50", .5), ("q75", .75), ("q90", .9))}
             for name in FEATURE_NAMES}
        if label:
            rules = [("low_PPL", f"whole_prompt_ppl <= positive q25 ({q['whole_prompt_ppl']['q25']})", lambda r: r["whole_prompt_ppl"] <= q["whole_prompt_ppl"]["q25"]),
                     ("low_mean_surprisal", "mean_surprisal <= positive q25", lambda r: r["mean_surprisal"] <= q["mean_surprisal"]["q25"]),
                     ("low_max_surprisal", "max_surprisal <= positive q25", lambda r: r["max_surprisal"] <= q["max_surprisal"]["q25"]),
                     ("weak_window_variation", "std_window_perplexity <= positive q25", lambda r: r["std_window_perplexity"] <= q["std_window_perplexity"]["q25"]),
                     ("aggregate_spike_proxy", "max_surprisal >= positive q75 and mean_surprisal <= positive q50; position/run unknown", lambda r: r["max_surprisal"] >= q["max_surprisal"]["q75"] and r["mean_surprisal"] <= q["mean_surprisal"]["q50"]),
                     ("no_threshold_8_exceedance", "existing high_surprisal_ratio == 0", lambda r: r["high_surprisal_ratio"] == 0)]
        else:
            rules = [("high_PPL", "whole_prompt_ppl >= negative q75", lambda r: r["whole_prompt_ppl"] >= q["whole_prompt_ppl"]["q75"]),
                     ("high_max_surprisal", "max_surprisal >= negative q90", lambda r: r["max_surprisal"] >= q["max_surprisal"]["q90"]),
                     ("high_surprisal_variation", "surprisal_std >= negative q75", lambda r: r["surprisal_std"] >= q["surprisal_std"]["q75"]),
                     ("high_window_variation", "std_window_perplexity >= negative q75", lambda r: r["std_window_perplexity"] >= q["std_window_perplexity"]["q75"]),
                     ("aggregate_spike_proxy", "max_surprisal >= negative q75 and mean_surprisal <= negative q50; position/run unknown", lambda r: r["max_surprisal"] >= q["max_surprisal"]["q75"] and r["mean_surprisal"] <= q["mean_surprisal"]["q50"])]
        rules.extend([("short_input", "input_tokens < 32", lambda r: r["input_tokens"] < 32),
                      ("long_input", "input_tokens >= 512", lambda r: r["input_tokens"] >= 512),
                      ("truncated_input", "existing truncated flag", lambda r: r["truncated"])])
        for name, definition, rule in rules:
            errors = [r for r in reference if r["error_type"] == error]
            successes = [r for r in reference if r["error_type"] == correct]
            supporting = [r["sample_id"] for r in errors if rule(r)]
            output["patterns"].append({"error_type": error, "pattern": name, "definition": definition,
                                       "error_count": len(supporting), "error_denominator": len(errors),
                                       "error_fraction": len(supporting) / len(errors) if errors else None,
                                       "correct_count": sum(rule(r) for r in successes), "correct_denominator": len(successes),
                                       "correct_fraction": sum(rule(r) for r in successes) / len(successes) if successes else None,
                                       "supporting_sample_ids": supporting})
        output.setdefault("class_reference_quantiles", {})[str(label)] = q
    output["unmeasured"] = {
        "anomaly_position_or_tail": "NOT_ASSESSABLE: token positions not retained in v1 aggregate feature output",
        "anomaly_runs_or_isolated_spikes": "Only aggregate proxies available; no token sequence/run features computed",
        "semantic_fluency_or_attack_mechanism": "NOT_INFERRED; statistical low surprise is not a semantic explanation",
        "long_prompt_dilution_causality": "Length correlations only; no intervention or region feature analysis",
    }
    output["source_limit"] = "All positives are from deepset in the approved corpus; source and label composition are confounded. No general distribution-shift claim."
    return output


def hypotheses(characterization):
    families = [
        ("robust_distribution", ["surprisal_quantiles", "median", "MAD", "IQR", "skewness", "kurtosis"],
         {"low_PPL", "low_mean_surprisal", "low_max_surprisal", "high_PPL", "high_surprisal_variation"},
         "Aggregate averages/extrema cannot resolve within-prompt distribution shape. Existing aliases duplicate two signals."),
        ("multi_threshold_surprisal", ["multiple_high_surprisal_ratios"], {"no_threshold_8_exceedance", "low_max_surprisal", "high_max_surprisal"},
         "The existing exceedance ratio uses only threshold 8; alternative shape sensitivity is untested."),
        ("window_robustness", ["median_window_PPL", "window_variance", "max_median_window_ratio"],
         {"weak_window_variation", "high_window_variation", "aggregate_spike_proxy"},
         "v1 already has max-window PPL; robust window center/contrast is not represented. Do not claim max-window PPL itself is missing."),
        ("length_normalization", ["token_count_normalization"], {"short_input", "long_input", "truncated_input"},
         "Coverage/length are diagnostic metadata, not scorer inputs; error concentration may motivate later length-aware statistical tests."),
        ("anomaly_runs", ["longest_anomaly_run", "anomaly_run_count"], {"aggregate_spike_proxy", "high_max_surprisal"},
         "Aggregate maxima cannot distinguish sustained anomalous runs from isolated events; proxy evidence is indirect."),
        ("regional_position", ["prefix_middle_tail_comparisons", "tail_minus_prefix", "anomaly_position"], set(),
         "Information gap only: position/tail effects were not measured, so there is no direct supporting error count."),
    ]
    ranked = []
    for family, features, patterns, rationale in families:
        supporting = set()
        matched = []
        for p in characterization["patterns"]:
            if p["pattern"] in patterns:
                supporting.update(p["supporting_sample_ids"])
                matched.append({"error_type": p["error_type"], "pattern": p["pattern"], "error_count": p["error_count"]})
        ranked.append({"family": family, "proposed_features_NOT_IMPLEMENTED": features,
                       "unique_supporting_error_count": len(supporting), "supporting_patterns": matched,
                       "rationale": rationale, "scope": "DEVELOPMENT_HYPOTHESIS_NOT_CAUSAL_OR_PERFORMANCE_EVIDENCE"})
    ranked.sort(key=lambda r: -r["unique_supporting_error_count"])
    for index, row in enumerate(ranked, 1):
        row["rank"] = index
    return {"ranking_rule": "Descending unique observed error IDs matching preregistered existing-statistic patterns; listed family order breaks ties. Overlapping counts are not independent evidence.",
            "features_implemented": False, "ds_v2_created": False, "hypotheses": ranked}


def oof_schema_projection(row):
    names = ("sample_id", "fold", "label", "source_name", "lineage_group", "detector_id", "detector_version", "candidate_id",
             "raw_score", "calibrated_probability", "binary_prediction", "input_tokens", "tokens_analyzed", "truncated", "latency_ms", "error_type")
    return {**{name: row[name] for name in names}, "metadata": {"partition": "BASE_TRAIN", "calibration_version": None,
                                                               "operating_point_id": "raw_0.5_development_comparison",
                                                               "raw_score_semantics": "Fold-local LR class-1 probability"}}


def stable_predictions(records):
    """Scientific outputs exclude wall-clock fields when checking determinism."""
    return json.dumps([{k: v for k, v in r.items() if "latency" not in k and k != "scorer_predict_ms_amortized"}
                       for r in records], sort_keys=True, allow_nan=False)
