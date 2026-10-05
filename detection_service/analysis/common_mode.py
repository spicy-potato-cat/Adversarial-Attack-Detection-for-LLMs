"""Model-free, deterministic DEVELOPMENT COMMON-MODE CHARACTERIZATION.

Scores are ordered risk values, never pooled across detectors. Operating points
use whole tied blocks, inclusive >=, maximal recall, then minimal FPR, then the
highest threshold. Empty FN unions have Jaccard 0; undefined recovery is None.
Bootstrap resamples canonical attack-lineage groups jointly at fixed pooled
operating points. It conditions on scores/thresholds and does not refit models.
"""
from collections import defaultdict
from itertools import combinations
import math
import random

BUDGETS = (0.01, 0.03, 0.05)
DIRECTION = "higher_is_more_adversarial"


def require(condition, message):
    """Refuse invalid evidence without silently dropping or repairing rows."""
    if not condition:
        raise ValueError("STOP: " + message)


def align(detectors):
    """Validate complete membership and metadata, returning sample-ID order.

Each mapping value is a sequence of canonical records. Detector identity is
the (detector_id, detector_version) pair; every record declares score direction.
Unknown metadata is None, never an invented source/family/fold annotation.
"""
    require(bool(detectors), "no detectors")
    aligned, reference, identities = {}, None, set()
    for key in sorted(detectors):
        rows = list(detectors[key])
        require(bool(rows), "empty detector evidence")
        ids = [r["sample_id"] for r in rows]
        require(all(isinstance(i, str) and i for i in ids), "invalid sample identity")
        require(len(ids) == len(set(ids)), "duplicate sample identity")
        identity = {(r.get("detector_id"), r.get("detector_version")) for r in rows}
        require(len(identity) == 1 and all(isinstance(v, str) and v for v in next(iter(identity))), "mixed/unknown detector identity")
        identity = (rows[0]["detector_id"], rows[0]["detector_version"])
        require(identity not in identities, "duplicate detector identity")
        identities.add(identity)
        for r in rows:
            require(r.get("score_direction") == DIRECTION, "mixed/unknown score direction")
            require(type(r.get("truth_label")) is int and r["truth_label"] in (0, 1), "invalid truth label")
            require(type(r.get("score")) in (int, float) and math.isfinite(r["score"]), "nonfinite/invalid score")
            require(isinstance(r.get("lineage_group"), str) and r["lineage_group"], "missing lineage group")
            require(r.get("partition") == "BASE_TRAIN", "non-development partition")
        current = {r["sample_id"]: r for r in rows}
        if reference is not None:
            require(current.keys() == reference.keys(), "missing/extra sample IDs")
            for sid, r in current.items():
                other = reference[sid]
                require(r["truth_label"] == other["truth_label"], "truth label mismatch")
                require(r["lineage_group"] == other["lineage_group"], "lineage mismatch")
                for field in ("source", "fold", "attack_family"):
                    if r.get(field) is not None and other.get(field) is not None:
                        require(r[field] == other[field], field + " mismatch")
        else:
            reference = current
        aligned[key] = [current[sid] for sid in sorted(current)]
    # Compare metadata against every detector, including when the first lacks it.
    for index in range(len(reference)):
        for field in ("source", "fold", "attack_family"):
            values = {rows[index].get(field) for rows in aligned.values()} - {None}
            require(len(values) <= 1, field + " mismatch")
        folds = {rows[index].get("fold") for rows in aligned.values()} - {None}
        if folds:
            require(all(type(f) is int and f >= 0 for f in folds), "invalid fold")
    groups = defaultdict(set)
    for index, r in enumerate(next(iter(aligned.values()))):
        folds = {rows[index].get("fold") for rows in aligned.values()} - {None}
        groups[r["lineage_group"]].update(folds)
    require(all(len(folds) <= 1 for folds in groups.values()), "canonical-lineage fold leakage")
    return aligned


def fixed_fpr(labels, scores, budgets=BUDGETS):
    """Reproduce QUALITY-001/STAT-003 attainable fixed-FPR semantics."""
    require(len(labels) == len(scores) and bool(labels), "invalid arrays")
    require(all(type(y) is int and y in (0, 1) for y in labels) and set(labels) == {0, 1}, "both binary labels required")
    require(all(type(s) in (int, float) and math.isfinite(s) for s in scores), "invalid scores")
    require(all(type(a) in (int, float) and math.isfinite(a) and 0 <= a <= 1 for a in budgets), "invalid FPR budget")
    positive, negative = sum(labels), len(labels) - sum(labels)
    blocks = defaultdict(lambda: [0, 0])
    for y, score in zip(labels, scores):
        blocks[score][y] += 1
    candidates = [(0, 0, None)]
    tp = fp = 0
    for score in sorted(blocks, reverse=True):
        fp += blocks[score][0]
        tp += blocks[score][1]
        candidates.append((tp, fp, score))
    points = []
    for budget in budgets:
        allowable = [p for p in candidates if p[1] / negative <= budget]
        # Stable max preserves the highest threshold when counts tie.
        tp, fp, threshold = max(allowable, key=lambda p: (p[0], -p[1]))
        points.append({"budget": budget, "threshold": threshold, "no_positive_predictions": threshold is None,
                       "tp": tp, "fp": fp, "fn": positive - tp, "tn": negative - fp,
                       "positive_denominator": positive, "negative_denominator": negative,
                       "fpr": fp / negative, "fnr": (positive - tp) / positive, "recall": tp / positive,
                       "role": "DEVELOPMENT_DESCRIPTIVE_OPERATING_CAPACITY"})
    return points


def failure_metrics(misses, stacks=None):
    """Compute attack-only pairwise, stack and exclusive-catch metrics.

Unique catch rates use ALL attacks as denominator. Conditional recovery uses
attacks missed by all OTHER members of the named stack. No ensemble vote is
created or exposed. Missing stacks carry null metrics and explicit status.
"""
    require(bool(misses), "no failure indicators")
    lengths = {len(v) for v in misses.values()}
    require(len(lengths) == 1 and next(iter(lengths)) > 0, "empty/misaligned attacks")
    require(all(type(v) is bool for values in misses.values() for v in values), "binary failure indicators required")
    n = next(iter(lengths))
    fnr = {key: sum(values) / n for key, values in misses.items()}
    pairwise = []
    for left, right in combinations(sorted(misses), 2):
        intersection = sum(a and b for a, b in zip(misses[left], misses[right]))
        union = sum(a or b for a, b in zip(misses[left], misses[right]))
        jfn = intersection / n
        ind = fnr[left] * fnr[right]
        pairwise.append({"left": left, "right": right, "attack_denominator": n, "fnr_i": fnr[left],
                         "fnr_j": fnr[right], "jfn_count": intersection, "jfn": jfn,
                         "independence_reference": ind, "ejf": jfn - ind,
                         "fn_union_count": union, "fn_jaccard": intersection / union if union else 0.0})
    stack_reports, unique = [], []
    for name, members in sorted((stacks or {}).items()):
        require(len(members) >= 2 and len(members) == len(set(members)), "invalid stack membership")
        missing = sorted(set(members) - misses.keys())
        if missing:
            stack_reports.append({"stack": name, "members": members, "status": "UNMEASURED_MISSING_DETECTOR",
                                  "missing": missing, "all_detector_jfn": None, "all_detector_fn_count": None})
            for key in members:
                unique.append({"stack": name, "detector": key, "status": "UNMEASURED_MISSING_DETECTOR",
                               "unique_catch_count": None, "unique_catch_rate": None,
                               "other_members_miss_count": None, "recovery_given_others_miss": None})
            continue
        count = sum(all(misses[k][i] for k in members) for i in range(n))
        stack_reports.append({"stack": name, "members": members, "status": "MEASURED",
                              "attack_denominator": n, "all_detector_jfn": count / n, "all_detector_fn_count": count})
        for key in members:
            others = [k for k in members if k != key]
            denominator = sum(all(misses[k][i] for k in others) for i in range(n))
            caught = sum(not misses[key][i] and all(misses[k][i] for k in others) for i in range(n))
            unique.append({"stack": name, "detector": key, "status": "MEASURED", "attack_denominator": n,
                           "unique_catch_count": caught, "unique_catch_rate": caught / n,
                           "other_members_miss_count": denominator,
                           "recovery_given_others_miss": caught / denominator if denominator else None})
    return {"fnr": fnr, "pairwise": pairwise, "stacks": stack_reports, "unique": unique}


def paired_effect(result, baseline, candidate, others, stack_names=None):
    """Return candidate-minus-baseline deltas on identical attacks."""
    rows = []
    for other in others:
        def find(key):
            return next((p for p in result["pairwise"] if {p["left"], p["right"]} == {key, other}), None)
        old, new = find(baseline), find(candidate)
        for metric in ("jfn", "ejf", "fn_jaccard"):
            a, b = (old[metric] if old else None), (new[metric] if new else None)
            rows.append({"metric": metric, "other": other, "baseline": a, "candidate": b,
                         "delta": b - a if a is not None and b is not None else None})
    if stack_names:
        old_name, new_name = stack_names
        for category, metric in (("stacks", "all_detector_jfn"), ("stacks", "all_detector_fn_count"),
                                 ("unique", "unique_catch_count"), ("unique", "unique_catch_rate"),
                                 ("unique", "recovery_given_others_miss")):
            a = next(r[metric] for r in result[category] if r["stack"] == old_name and (category == "stacks" or r["detector"] == baseline))
            b = next(r[metric] for r in result[category] if r["stack"] == new_name and (category == "stacks" or r["detector"] == candidate))
            rows.append({"metric": metric, "other": "primary_stack", "baseline": a, "candidate": b,
                         "delta": b - a if a is not None and b is not None else None})
    return rows


def scalar_metrics(result):
    """Flatten measured failure rates for uncertainty calculation."""
    out = {"fnr/" + k: v for k, v in result["fnr"].items()}
    for p in result["pairwise"]:
        for metric in ("jfn", "ejf", "fn_jaccard"):
            out[f'{metric}/{p["left"]}/{p["right"]}'] = p[metric]
    for s in result["stacks"]:
        if s["all_detector_jfn"] is not None:
            out["all_detector_jfn/" + s["stack"]] = s["all_detector_jfn"]
    return out


def bootstrap(misses, lineage_groups, stacks=None, comparison=None, repetitions=1000, seed=1701):
    """Paired attack-lineage percentile bootstrap, conditional on fixed points."""
    require(type(repetitions) is int and repetitions > 0, "invalid bootstrap repetitions")
    require(len(lineage_groups) == len(next(iter(misses.values()))) and all(lineage_groups), "bootstrap lineage mismatch")
    point = failure_metrics(misses, stacks)
    groups = defaultdict(list)
    for i, group in enumerate(lineage_groups):
        groups[group].append(i)
    ordered = [groups[g] for g in sorted(groups)]
    rng = random.Random(seed)
    draws = defaultdict(list)
    def flatten(result):
        flat = scalar_metrics(result)
        if comparison:
            for effect in paired_effect(result, **comparison):
                if effect["delta"] is not None:
                    flat[f'delta/{effect["metric"]}/{effect["other"]}'] = effect["delta"]
        return flat
    estimates = flatten(point)
    for _ in range(repetitions):
        indices = [i for _ in ordered for i in ordered[rng.randrange(len(ordered))]]
        sampled = {k: [v[i] for i in indices] for k, v in misses.items()}
        for key, value in flatten(failure_metrics(sampled, stacks)).items():
            draws[key].append(value)
    def quantile(values, q):
        values = sorted(values)
        pos = (len(values) - 1) * q
        low = math.floor(pos)
        return values[low] + (values[math.ceil(pos)] - values[low]) * (pos - low)
    return {"method": "paired canonical attack-lineage percentile bootstrap at fixed pooled thresholds",
            "scope": "DEVELOPMENT_UNCERTAINTY_CONDITIONAL_ON_FIXED_SCORES_AND_OPERATING_POINTS",
            "limitations": "No threshold reselection, model refits, training-fold dependence, selection uncertainty or full semantic lineage uncertainty.",
            "repetitions": repetitions, "seed": seed, "level": 0.95, "attack_rows": len(lineage_groups),
            "attack_lineage_groups": len(ordered),
            "intervals": {k: {"estimate": estimates[k], "lower": quantile(v, .025), "upper": quantile(v, .975)} for k, v in sorted(draws.items())}}


def analyze(detectors, stacks=None, comparison=None, budgets=BUDGETS, repetitions=1000, seed=1701):
    """Validate, select individual points, then describe shared failure sets."""
    aligned = align(detectors)
    rows = next(iter(aligned.values()))
    labels = [r["truth_label"] for r in rows]
    positive_indices = [i for i, y in enumerate(labels) if y]
    points = {key: fixed_fpr(labels, [r["score"] for r in records], budgets) for key, records in aligned.items()}
    results = []
    for index, budget in enumerate(budgets):
        predictions = {key: [p[index]["threshold"] is not None and r["score"] >= p[index]["threshold"] for r in aligned[key]] for key, p in points.items()}
        misses = {key: [not values[i] for i in positive_indices] for key, values in predictions.items()}
        failure = failure_metrics(misses, stacks)
        grouped = []
        for field in ("source", "attack_family", "fold"):
            metadata = [next((records[i].get(field) for records in aligned.values() if records[i].get(field) is not None), None) for i in range(len(rows))]
            for value in sorted({v for v in metadata if v is not None}, key=str):
                chosen = [i for i in positive_indices if metadata[i] == value]
                all_chosen = [i for i in range(len(rows)) if metadata[i] == value]
                group_individual = []
                for key, predicted in predictions.items():
                    tp = sum(labels[i] == 1 and predicted[i] for i in all_chosen)
                    fp = sum(labels[i] == 0 and predicted[i] for i in all_chosen)
                    npos = len(chosen)
                    nneg = len(all_chosen) - npos
                    group_individual.append({"detector": key, "tp": tp, "fp": fp, "fn": npos - tp, "tn": nneg - fp,
                                             "fpr": fp / nneg if nneg else None, "fnr": (npos - tp) / npos if npos else None})
                grouped.append({"field": field, "value": value, "rows": len(all_chosen), "attack_rows": len(chosen),
                                "operating_point": "pooled threshold applied unchanged; no subgroup optimization",
                                "individual": group_individual,
                                "failure": failure_metrics({k: [not v[i] for i in chosen] for k, v in predictions.items()}, stacks) if chosen else None})
        results.append({"budget": budget, "individual": [{"detector": k, **points[k][index]} for k in sorted(points)],
                        **failure, "effect": paired_effect(failure, **comparison) if comparison else [], "grouped": grouped,
                        "bootstrap": bootstrap(misses, [rows[i]["lineage_group"] for i in positive_indices], stacks, comparison, repetitions, seed)})
    return {"scope": "DEVELOPMENT COMMON-MODE CHARACTERIZATION", "aligned_samples": len(rows),
            "positive": sum(labels), "negative": len(labels) - sum(labels), "detectors": sorted(aligned), "budgets": results}
