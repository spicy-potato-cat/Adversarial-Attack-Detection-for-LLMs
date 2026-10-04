"""Predeclared ranking-only scorer metrics, diagnostics and paired selection."""

import numpy as np
from sklearn.metrics import average_precision_score, roc_auc_score

from detection_service.analysis.statistical_ablation_results import counts, transitions, votes
from detection_service.analysis.statistical_feature_ablation import SHORT_BUCKETS, short_bucket
from detection_service.analysis.statistical_oof import check_membership, describe, fixed_fpr, require
from detection_service.analysis.statistical_scorer_comparison import SCORERS, definitions


def metrics(labels, scores):
    labels, scores = np.asarray(labels), np.asarray(scores, dtype=float)
    require(labels.shape == scores.shape and np.isfinite(scores).all() and set(labels.tolist()) == {0, 1}, "invalid ranking scores")
    positive, negative = int(sum(labels == 1)), int(sum(labels == 0))
    return {"sample_count": len(labels), "positive_count": positive, "negative_count": negative,
        "roc_auc": float(roc_auc_score(labels, scores)), "pr_auc": float(average_precision_score(labels, scores)),
        "pr_auc_definition": "average_precision", "scope": "DEVELOPMENT_OOF_NOT_FINAL_PERFORMANCE",
        "recall_at_fixed_fpr": [{**p, "fn": positive - p["tp"], "tn": negative - p["fp"]}
                                for p in fixed_fpr(labels, scores)]}


def summary(values):
    return {"mean": float(np.mean(values)), "population_sd": float(np.std(values)),
            "minimum": float(min(values)), "maximum": float(max(values))}


def stability(reports):
    result = {k: summary([r["metrics"][k] for r in reports]) for k in ("roc_auc", "pr_auc")}
    for i, budget in enumerate((.01, .03, .05)):
        for k in ("recall", "attained_fpr"):
            result[f"{k}_at_{budget}"] = summary([r["metrics"]["recall_at_fixed_fpr"][i][k] for r in reports])
    return result


def analyze(rows, evidence, scores, reports):
    check_membership(rows)
    require(set(scores) == set(SCORERS) and len(evidence) == len(rows), "scorer population mismatch")
    labels = np.asarray([int(r["label"]) for r in rows])
    ids = [r["sample_id"] for r in rows]
    aggregate, folds, subgroups = {}, {}, {}
    for scorer in SCORERS:
        require(np.asarray(scores[scorer]).shape == (len(rows),), "scorer alignment mismatch")
        aggregate[scorer] = metrics(labels, scores[scorer])
        completed = []
        for report in reports[scorer]:
            mask = np.asarray([int(r["outer_fold"]) == report["fold"] for r in rows])
            completed.append({**report, "metrics": metrics(labels[mask], scores[scorer][mask])})
        require([r["fold"] for r in completed] == list(range(5)), "fold coverage mismatch")
        folds[scorer] = {"folds": completed, "stability": stability(completed),
            "runtime": {"fit_seconds_total": sum(r["fit_seconds"] for r in completed),
                        "inference_seconds_total": sum(r["inference_seconds"] for r in completed)}}
        subgroups[scorer] = {}
        groups = [(b, np.asarray([short_bucket(e["input_tokens"]) == b for e in evidence])) for b in SHORT_BUCKETS]
        groups.append(("combined_<32", np.asarray([e["input_tokens"] < 32 for e in evidence])))
        for bucket, mask in groups:
            subgroups[scorer][bucket] = {"pooled_frontiers": [{"budget": p["budget"],
                **counts(labels[mask], votes(scores[scorer], p)[mask])} for p in aggregate[scorer]["recall_at_fixed_fpr"]],
                "positive_scores": describe(scores[scorer][mask & (labels == 1)].tolist()),
                "negative_scores": describe(scores[scorer][mask & (labels == 0)].tolist())}
    predicted = {s: votes(scores[s], aggregate[s]["recall_at_fixed_fpr"][1]) for s in SCORERS}
    errors = {"scope": "WITHIN_D_S_SCORER_DIVERSITY_NOT_CROSS_DETECTOR_COMPLEMENTARITY", "versus_S0": {}}
    for scorer in SCORERS[1:]:
        result = transitions(ids, labels, predicted["S0"], predicted[scorer])
        errors["versus_S0"][scorer] = {k.replace("v1_", "LR_"): v for k, v in result.items()}
    mask = (labels == 1) & ~np.logical_or.reduce(list(predicted.values()))
    errors["shared_FN"] = {"count": int(sum(mask)), "sample_ids": [sid for sid, v in zip(ids, mask, strict=True) if v]}
    errors["unique_catches"] = {}
    for scorer in SCORERS:
        mask = (labels == 1) & predicted[scorer] & ~np.logical_or.reduce([predicted[s] for s in SCORERS if s != scorer])
        errors["unique_catches"][scorer] = {"count": int(sum(mask)), "sample_ids": [sid for sid, v in zip(ids, mask, strict=True) if v]}
    return aggregate, folds, subgroups, errors


def paired(rows, scores):
    check_membership(rows)
    require(set(scores) == set(SCORERS) and all(np.asarray(s).shape == (len(rows),) and np.isfinite(s).all()
            for s in scores.values()), "paired sample alignment drift")
    policy = definitions()["bootstrap"]
    labels = np.asarray([int(r["label"]) for r in rows])
    groups = {}
    for i, row in enumerate(rows):
        groups.setdefault(row["lineage_group"], []).append(i)
    members = list(groups.values())
    rng = np.random.default_rng(policy["seed"])
    differences = {s: [] for s in SCORERS[1:]}
    def values(y, s):
        return np.asarray([fixed_fpr(y, s, (.03,))[0]["recall"], roc_auc_score(y, s), average_precision_score(y, s)])
    for _ in range(policy["repetitions"]):
        indices = np.asarray([i for g in rng.integers(0, len(members), len(members)) for i in members[g]])
        y = labels[indices]
        if len(set(y.tolist())) != 2:
            continue
        baseline = values(y, scores["S0"][indices])
        for scorer in differences:
            differences[scorer].append(values(y, scores[scorer][indices]) - baseline)
    baseline = values(labels, scores["S0"])
    return {"policy": policy, "differences_vs_S0": {s: {"valid_repetitions": len(v), "metrics": {
        metric: {"observed_difference": float((values(labels, scores[s]) - baseline)[i]),
                 "lower_95pct": float(np.quantile(np.asarray(v)[:, i], .025)),
                 "upper_95pct": float(np.quantile(np.asarray(v)[:, i], .975))}
        for i, metric in enumerate(("recall_at_3pct", "roc_auc", "pr_auc"))}} for s, v in differences.items()}}


def select(aggregate, folds, subgroups, comparisons):
    policy = definitions()["selection"]
    base, basefold = aggregate["S0"], folds["S0"]["stability"]["recall_at_0.03"]
    eligibility = {}
    for scorer in SCORERS[1:]:
        a, fold = aggregate[scorer], folds[scorer]["stability"]["recall_at_0.03"]
        points, bp = a["recall_at_fixed_fpr"], base["recall_at_fixed_fpr"]
        subgroup = lambda s, group: subgroups[s][group]["pooled_frontiers"][1]
        def recall_guard(group, change):
            previous = subgroup("S0", group)["recall"]
            return previous is None or subgroup(scorer, group)["recall"] >= previous + change
        checks = {"material_3pct_gain": points[1]["recall"] >= bp[1]["recall"] + policy["material_gain"],
            "paired_support": comparisons["differences_vs_S0"][scorer]["metrics"]["recall_at_3pct"]["lower_95pct"] > 0,
            "preserve_1pct": points[0]["recall"] >= bp[0]["recall"] + policy["budget_1_5_min_change"],
            "preserve_5pct": points[2]["recall"] >= bp[2]["recall"] + policy["budget_1_5_min_change"],
            "auc": a["roc_auc"] >= base["roc_auc"] + policy["auc_ap_min_change"],
            "ap": a["pr_auc"] >= base["pr_auc"] + policy["auc_ap_min_change"],
            "fold_sd": fold["population_sd"] <= basefold["population_sd"] + policy["fold_3_sd_max_increase"],
            "fold_min": fold["minimum"] >= basefold["minimum"] - policy["fold_3_min_max_drop"],
            "under16": recall_guard("<16", policy["under16_recall_min_change"]),
            "combined_short": recall_guard("combined_<32", policy["combined_short_recall_min_change"]),
            "long_benign": subgroup(scorer, "64+")["fp"] <= subgroup("S0", "64+")["fp"] + policy["long_benign_fp_max_increase"]}
        eligibility[scorer] = {"eligible": bool(all(checks.values())), "checks": {k: bool(v) for k, v in checks.items()}}
    eligible = [s for s in SCORERS[1:] if eligibility[s]["eligible"]]
    best = max(eligible, key=lambda s: aggregate[s]["recall_at_fixed_fpr"][1]["recall"]) if eligible else "S0"
    selected = next((s for s in eligible if all(aggregate[s]["recall_at_fixed_fpr"][i]["recall"] >=
        aggregate[best]["recall_at_fixed_fpr"][i]["recall"] - policy["near_best_tolerance"] for i in (0, 1, 2))), "S0")
    return {"selected_scorer": selected, "best_eligible_scorer": best, "eligibility": eligibility, "policy": policy,
        "B2_schema_sha256": definitions()["B2_schema_sha256"], "candidate_recipe": definitions()["scorers"][selected],
        "candidate_recipe_ready": True, "cycle": "1_OF_MAXIMUM_2", "final_ds_v2_trained": False,
        "scope": "SAME_DEVELOPMENT_OOF_SELECTION_NOT_UNBIASED_FINAL_EVALUATION", "complementarity": "DEFERRED"}
