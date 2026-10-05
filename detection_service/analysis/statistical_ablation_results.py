"""Fixed STAT-004 diagnostics and selection; no adaptive feature construction."""

import numpy as np
from sklearn.metrics import average_precision_score, roc_auc_score

from detection_service.analysis.statistical_feature_ablation import BLOCKS, SHORT_BUCKETS, definitions, short_bucket
from detection_service.analysis.statistical_oof import describe, fixed_fpr, metrics, stability


def votes(scores, point):
    return np.zeros(len(scores), dtype=bool) if point["no_positive_predictions"] else scores >= point["descriptive_threshold"]


def counts(labels, predicted):
    pos, neg = labels == 1, labels == 0
    tp, fp = int(sum(pos & predicted)), int(sum(neg & predicted))
    return {"positive": int(sum(pos)), "negative": int(sum(neg)), "tp": tp, "fp": fp,
            "fn": int(sum(pos)) - tp, "tn": int(sum(neg)) - fp,
            "recall": tp / sum(pos) if sum(pos) else None, "fpr": fp / sum(neg) if sum(neg) else None}


def transitions(ids, labels, baseline_vote, current_vote):
    sets = {"v1_FN_recovered": (labels == 1) & ~baseline_vote & current_vote,
            "v1_FP_recovered": (labels == 0) & baseline_vote & ~current_vote,
            "new_FN": (labels == 1) & baseline_vote & ~current_vote,
            "new_FP": (labels == 0) & ~baseline_vote & current_vote}
    return {key: {"count": int(sum(mask)), "sample_ids": [sid for sid, selected in zip(ids, mask, strict=True) if selected]}
            for key, mask in sets.items()}


def summarize(rows, evidence, scores, fold_reports):
    labels = np.asarray([int(r["label"]) for r in rows])
    ids = [r["sample_id"] for r in rows]
    aggregate = {b: {"feature_count": definitions()["blocks"][i]["feature_count"],
                      "schema_sha256": definitions()["blocks"][i]["schema_sha256"], **metrics(labels, scores[b])}
                 for i, b in enumerate(BLOCKS)}
    fold_data = {b: {"folds": fold_reports[b], "stability": stability(fold_reports[b]),
                    "attained_fpr_stability": {str(budget): {
                        "mean": float(np.mean(v := [r["metrics"]["recall_at_fixed_fpr"][i]["attained_fpr"] for r in fold_reports[b]])),
                        "population_sd": float(np.std(v)), "min": min(v), "max": max(v)}
                        for i, budget in enumerate((.01, .03, .05))}} for b in BLOCKS}
    short = {}
    errors = {}
    baseline_raw = scores["B0"] >= .5
    baseline_3 = votes(scores["B0"], aggregate["B0"]["recall_at_fixed_fpr"][1])
    for block in BLOCKS:
        short[block] = {}
        for bucket in SHORT_BUCKETS:
            mask = np.asarray([short_bucket(e["input_tokens"]) == bucket for e in evidence])
            short[block][bucket] = {
                "raw_0_5": counts(labels[mask], scores[block][mask] >= .5),
                "pooled_frontiers": [{"budget": p["budget"], **counts(labels[mask], votes(scores[block], p)[mask])}
                                     for p in aggregate[block]["recall_at_fixed_fpr"]],
                "positive_scores": describe(scores[block][mask & (labels == 1)].tolist()),
                "negative_scores": describe(scores[block][mask & (labels == 0)].tolist())}
        selected_3 = votes(scores[block], aggregate[block]["recall_at_fixed_fpr"][1])
        errors[block] = {"raw_bank_at_raw_0_5": transitions(ids, labels, baseline_raw, scores[block] >= .5),
                         "raw_bank_at_pooled_3pct": transitions(ids, labels, baseline_raw, selected_3),
                         "matched_3pct_bank": transitions(ids, labels, baseline_3, selected_3)}
    return aggregate, fold_data, short, errors


def combined_short(rows, evidence, scores, point):
    mask = np.asarray([e["input_tokens"] < 32 for e in evidence])
    return counts(np.asarray([int(r["label"]) for r in rows])[mask], votes(scores, point)[mask])


def select(rows, evidence, scores, aggregate, fold_data):
    policy = definitions()["selection"]
    baseline = aggregate["B0"]
    bp = baseline["recall_at_fixed_fpr"]
    bs = combined_short(rows, evidence, scores["B0"], bp[1])
    stability0 = fold_data["B0"]["stability"]["recall_at_fpr_0.03"]
    eligibility = {}
    for block in BLOCKS[1:]:
        a = aggregate[block]
        points = a["recall_at_fixed_fpr"]
        s = combined_short(rows, evidence, scores[block], points[1])
        fold = fold_data[block]["stability"]["recall_at_fpr_0.03"]
        checks = {
            "material_3pct_gain": points[1]["recall"] >= bp[1]["recall"] + policy["material_gain"],
            "preserve_1pct": points[0]["recall"] >= bp[0]["recall"] + policy["budget_1_and_5_min_vs_B0"],
            "preserve_5pct": points[2]["recall"] >= bp[2]["recall"] + policy["budget_1_and_5_min_vs_B0"],
            "auc_sanity": a["roc_auc"] >= baseline["roc_auc"] + policy["auc_and_ap_min_vs_B0"],
            "ap_sanity": a["pr_auc"] >= baseline["pr_auc"] + policy["auc_and_ap_min_vs_B0"],
            "fold_sd_guard": fold["standard_deviation_population"] <= stability0["standard_deviation_population"] + policy["fold_recall_3_sd_max_increase"],
            "fold_min_guard": fold["minimum"] >= stability0["minimum"] - policy["fold_recall_3_min_max_drop"],
            "short_recall_guard": bs["recall"] is None or s["recall"] >= bs["recall"],
            "short_fpr_guard": bs["fpr"] is None or s["fpr"] <= bs["fpr"] + policy["short_fpr_3_max_increase"],
        }
        eligibility[block] = {"eligible": bool(all(checks.values())), "checks": {k: bool(v) for k, v in checks.items()}, "short_3pct": s}
    eligible = [b for b in BLOCKS[1:] if eligibility[b]["eligible"]]
    if eligible:
        best = max(eligible, key=lambda b: aggregate[b]["recall_at_fixed_fpr"][1]["recall"])
        selected = next(b for b in eligible if all(aggregate[b]["recall_at_fixed_fpr"][i]["recall"] >=
                            aggregate[best]["recall_at_fixed_fpr"][i]["recall"] - policy["near_best_tolerance"] for i in (0, 1, 2)))
    else:
        selected, best = "B0", "B0"
    definition = next(b for b in definitions()["blocks"] if b["schema_version"] == f"stat004_{selected}_v1")
    return {"selected_block": selected, "best_eligible_3pct_block": best, "eligibility": eligibility,
            "policy": policy, "feature_count": definition["feature_count"], "schema_sha256": definition["schema_sha256"],
            "feature_names": definition["feature_names"], "baseline_short_3pct": bs,
            "selected_short_3pct": combined_short(rows, evidence, scores[selected], aggregate[selected]["recall_at_fixed_fpr"][1]),
            "selection_scope": "DEVELOPMENT_SELECTION_ON_SAME_OOF_FIXTURE; requires later independent evaluation, not unbiased final performance",
            "final_ds_v2_created": False, "complementarity": "DEFERRED_TO_LATER_COMMON_STACK_ANALYSIS", "cycle": "1_OF_MAXIMUM_2"}


def paired_bootstrap(rows, scores):
    policy = definitions()["paired_bootstrap"]
    groups = {}
    labels = np.asarray([int(r["label"]) for r in rows])
    for i, row in enumerate(rows):
        groups.setdefault(row["lineage_group"], []).append(i)
    members = list(groups.values())
    rng = np.random.default_rng(policy["seed"])
    differences = {b: [] for b in BLOCKS[1:]}
    def values(y, s):
        return np.asarray([fixed_fpr(y, s, (.03,))[0]["recall"], roc_auc_score(y, s), average_precision_score(y, s)])
    for _ in range(policy["repetitions"]):
        indices = np.asarray([i for g in rng.integers(0, len(members), len(members)) for i in members[g]])
        y = labels[indices]
        if len(set(y.tolist())) != 2:
            continue
        baseline = values(y, scores["B0"][indices])
        for block in differences:
            differences[block].append(values(y, scores[block][indices]) - baseline)
    baseline = values(labels, scores["B0"])
    return {"policy": policy, "differences_vs_B0": {b: {"valid_repetitions": len(v), "metrics": {
                metric: {"observed_difference": float((values(labels, scores[b]) - baseline)[i]),
                         "lower_95pct": float(np.quantile(np.asarray(v)[:, i], .025)),
                         "upper_95pct": float(np.quantile(np.asarray(v)[:, i], .975))}
                for i, metric in enumerate(policy["metrics"])}} for b, v in differences.items()}}
