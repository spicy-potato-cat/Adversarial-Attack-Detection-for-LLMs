"""Model-free ranking/native metrics and ID-aligned subgroup diagnostics."""
from collections import Counter, defaultdict
import math

from detection_service.analysis.common_mode import align, fixed_fpr, require


def characterization(labels, scores, native):
    """Native vote metrics plus tie-aware ROC-AUC and average precision.

The native decision is supplied, never reconstructed from a raw 0.5 cutpoint.
Single-label source groups have undefined ranking/FPR or FNR where appropriate.
"""
    require(bool(labels) and len(labels) == len(scores) == len(native), "misaligned native evidence")
    require(all(type(y) is int and y in (0, 1) for y in labels), "invalid native labels")
    require(all(type(v) is bool for v in native), "invalid native votes")
    require(all(type(s) in (int, float) and math.isfinite(s) and 0 <= s <= 1 for s in scores), "invalid native scores")
    tp = sum(y == 1 and p for y, p in zip(labels, native))
    fp = sum(y == 0 and p for y, p in zip(labels, native))
    pos, neg = sum(labels), len(labels) - sum(labels)
    fn, tn = pos - tp, neg - fp
    precision = tp / (tp + fp) if tp + fp else 0.
    blocks = defaultdict(lambda: [0, 0])
    for y, score in zip(labels, scores):
        blocks[score][y] += 1
    ap = auc = None
    if pos and neg:
        concordant = below = 0.
        for score in sorted(blocks):
            nneg, npos = blocks[score]
            concordant += npos * (below + .5 * nneg)
            below += nneg
        auc = concordant / (pos * neg)
        seen = hits = 0
        ap = 0.
        for score in sorted(blocks, reverse=True):
            nneg, npos = blocks[score]
            seen += nneg + npos
            hits += npos
            ap += npos / pos * hits / seen
    return {"rows": len(labels), "positive": pos, "negative": neg,
            "native": {"tn": tn, "fp": fp, "fn": fn, "tp": tp, "accuracy": (tn + tp) / len(labels),
                       "precision": precision, "recall": tp / pos if pos else None,
                       "specificity": tn / neg if neg else None, "f1": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0.,
                       "fpr": fp / neg if neg else None, "fnr": fn / pos if pos else None},
            "roc_auc": auc, "pr_auc": ap, "pr_auc_definition": "average_precision_whole_tied_blocks",
            "fixed_fpr": fixed_fpr(labels, scores) if pos and neg else None,
            "scope": "DEVELOPMENT_DESCRIPTIVE_OPERATING_CAPACITY"}


def subgroup_diagnostics(detectors, points, token_counts):
    """Describe frozen D_S-token subgroups; missing guard metrics remain null.

No group threshold is fitted. Catch-pattern counts are diagnostics, not a
blocking/fusion policy. Group membership comes from the S0 OOF token metadata.
"""
    data = align(detectors)
    reference = next(iter(data.values()))
    require(set(token_counts) == {r["sample_id"] for r in reference}, "token subgroup membership mismatch")
    require(all(type(v) is int and v >= 0 for v in token_counts.values()), "invalid D_S token counts")
    keys = ["D_S_v1", "D_S_B2_LR", "D_M-B_v1", "D_G_v1"]
    thresholds = {p["detector"]: p["threshold"] for p in points}
    require(set(thresholds) == set(data), "subgroup operating point mismatch")
    indicators = {key: [thresholds[key] is not None and r["score"] >= thresholds[key] for r in rows] for key, rows in data.items()}
    groups = [("under_16_attacks", [i for i, r in enumerate(reference) if r["truth_label"] == 1 and token_counts[r["sample_id"]] < 16]),
              ("64_plus_benign", [i for i, r in enumerate(reference) if r["truth_label"] == 0 and token_counts[r["sample_id"]] >= 64])]
    result = []
    for name, selected in groups:
        attacks = name == "under_16_attacks"
        counts = {key: sum(indicators[key][i] for i in selected) if key in data else None for key in keys}
        stronger_members = ("D_M-B_v1", "D_G_v1")
        stack_members = ("D_S_B2_LR", "D_M-B_v1", "D_G_v1")
        stronger_available = all(k in data for k in stronger_members)
        all_available = all(k in data for k in stack_members)
        known_stronger_catches = sum(any(indicators[k][i] for k in stronger_members if k in data) for i in selected)
        stronger_bounds = {"lower": known_stronger_catches, "upper": known_stronger_catches if stronger_available else len(selected)}
        possible_all_misses = sum(not any(indicators[k][i] for k in stack_members if k in data) for i in selected)
        miss_bounds = {"lower": possible_all_misses if all_available else 0, "upper": possible_all_misses}
        patterns = Counter("|".join(f'{key}={int(indicators[key][i])}' for key in keys if key in data) for i in selected)
        result.append({"subgroup": name, "count": len(selected), "label": 1 if attacks else 0,
                       "token_basis": "frozen S0/B2 reference-LM input_tokens; not semantic/guard tokenizer counts",
                       "detector_counts": counts, "count_meaning": "attack_catches" if attacks else "benign_false_positives",
                       "either_stronger_detector_catches": stronger_bounds["lower"] if stronger_bounds["lower"] == stronger_bounds["upper"] else None,
                       "either_stronger_count_bounds": stronger_bounds,
                       "candidate_all_three_miss": miss_bounds["lower"] if attacks and miss_bounds["lower"] == miss_bounds["upper"] else None,
                       "candidate_all_three_miss_bounds": miss_bounds if attacks else None,
                       "bounds_note": "Exact when lower=upper; other values remain unmeasured. These are logical count bounds, not confidence intervals or inferred D_G predictions.",
                       "patterns": [{"pattern": pattern, "count": count} for pattern, count in sorted(patterns.items())],
                       "sample_ids": [reference[i]["sample_id"] for i in selected],
                       "missing_detectors": [key for key in keys if key not in data],
                       "scope": "DESCRIPTIVE_SUBGROUP_NO_ENSEMBLE_DECISION"})
    return result
