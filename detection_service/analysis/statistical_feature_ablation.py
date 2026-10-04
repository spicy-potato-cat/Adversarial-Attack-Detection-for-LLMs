"""Predeclared STAT-004 cumulative statistical features; v1 is not modified."""

import hashlib
import math
import time
import warnings

import numpy as np
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression

from detection_service.analysis.statistical_oof import check_membership, digest_ids, metrics, require
from detection_service.app.detectors.statistical_risk.schema import FEATURE_NAMES, json_bytes
from detection_service.app.detectors.statistical_risk.scorer import RECIPE

LENGTH_BOUNDS = (16, 32, 64, 128)
SHORT_BUCKETS = ("<16", "16-31", "32-63", "64+")
CORE = ("whole_prompt_nll", "max_surprisal", "surprisal_std")
QUANTILES = (.25, .75, .90, .95, .99)
SCALES = (8, 16, 32, 64)
ADDED = {
    "B0": FEATURE_NAMES,
    "B1": tuple(f"length_{kind}_{name}" for name in CORE for kind in ("robust_z", "percentile")),
    "B2": ("surprisal_median", "surprisal_mad", "surprisal_iqr", "surprisal_q25", "surprisal_q75",
           "surprisal_q90", "surprisal_q95", "surprisal_q99", "surprisal_top5_mean", "surprisal_top10pct_mean"),
    "B3": ("exceedance_q90_fraction", "exceedance_q95_fraction", "exceedance_q99_fraction"),
    "B4": ("anomaly_runs_per_token", "anomaly_longest_run_fraction", "anomaly_mean_run_fraction", "isolated_anomaly_fraction"),
    "B5": tuple(f"{region}_{name}" for region in ("prefix", "middle", "tail")
                for name in ("mean", "median", "anomaly_fraction", "available")) + ("tail_minus_prefix_mean", "middle_minus_prefix_mean"),
    "B6": tuple(f"window_{scale}_{name}" for scale in SCALES for name in
                ("max_mean_nll", "median_mean_nll", "iqr_mean_nll", "top2_mean_nll", "available")),
}
BLOCKS = tuple(ADDED)
MAX_ITER = 20000


def names(block):
    require(block in BLOCKS, "undeclared feature block")
    return tuple(name for b in BLOCKS[:BLOCKS.index(block) + 1] for name in ADDED[b])


def definitions():
    rules = {
        "phase": "TECH-STAT-004", "cycle": "1_OF_MAXIMUM_2", "B7": "PREDECLARED_SKIPPED",
        "length_conditioning": {"input_tokens_include_first_unscored_token": True, "boundaries": list(LENGTH_BOUNDS),
            "minimum_benign_rows": 20, "sparse_pool": "Target bin then nearest bin index, ties lower index first; stop at >=20 benign training rows. Log every pooled bin. No silent global fallback.",
            "robust_z": "(x - benign median)/(benign MAD + 1e-6), clipped [-20,20]",
            "percentile": "Empirical right-inclusive CDF among pooled benign training rows", "core": list(CORE)},
        "distribution": {"quantile_method": "linear", "mad": "median(abs(x-median(x))); unscaled",
            "iqr": "q75-q25", "top_k": "min(5,n)", "top_fraction": "ceil(0.10*n), minimum 1"},
        "anomaly": {"reference": "Length-bin pooled benign training token surprisals; token-weighted quantiles .90/.95/.99",
            "exceedance": "strict >, denominator analyzed next-token surprisals", "runs": "Contiguous >q95 tokens; runs/n, longest/n, mean run length/n, singleton runs/anomalous tokens; no anomalies=>zeros"},
        "regions": "numpy.array_split(sequence,3); earlier regions receive remainders. Empty region: statistics=0 plus available=0; contrasts use these defined values.",
        "windows": {"scales": list(SCALES), "stride": "scale//2", "coverage": "Full valid windows only; append final anchored window if needed. Unusable scale=>four zero placeholders plus available=0.",
            "statistics": "max/median/IQR/top-min(2,count)-mean of window mean surprisal (log-PPL domain); inherited causal context, NOT independently rescored isolated windows."},
        "short_analysis_buckets": list(SHORT_BUCKETS), "scorer_recipe": RECIPE,
        "normalization": "B0 identity unchanged. No extra scaler, imputation, C tuning or class-weight tuning.",
        "selection": {"primary": "Recall@FPR<=3%", "material_gain": .03, "near_best_tolerance": .02,
            "budget_1_and_5_min_vs_B0": -.02, "auc_and_ap_min_vs_B0": -.01,
            "fold_recall_3_sd_max_increase": .03, "fold_recall_3_min_max_drop": .03,
            "short_recall_3_min_change": 0., "short_fpr_3_max_increase": .02,
            "rule": "Eligible means >=3 recall points over B0 at 3%, preservation guards above. Choose earliest eligible block within 2 points of best eligible 3% recall AND within 2 points of its 1/5% recalls. If none eligible, retain B0. Raw 0.5 confusion never selects a block."},
        "paired_bootstrap": {"repetitions": 1000, "seed": 1701, "unit": "Canonical lineage groups resampled, paired identical indices across blocks",
            "metrics": ["recall_at_3pct", "roc_auc", "pr_auc"], "limitations": "Conditional fixed-OOF percentile intervals; no model refits, shared-training uncertainty or multiplicity correction. Frontiers recomputed within resamples; not future threshold guarantees."},
        "error_banks": "Frozen v1 raw 0.5 FN=60/FP=203; transitions at raw 0.5 and each pooled 3% frontier. Also matched B0 3% error-bank transitions. IDs are diagnostic, never oversampled.",
        "complementarity": "DEFERRED_TO_LATER_COMMON_STACK_ANALYSIS", "deployment_threshold_selection": False,
    }
    rules["blocks"] = []
    for block in BLOCKS:
        schema = {"schema_version": f"stat004_{block}_v1", "feature_names": list(names(block)), "feature_count": len(names(block)),
                  "new_feature_names": list(ADDED[block]), "rules": {k: v for k, v in rules.items() if k != "blocks"}}
        rules["blocks"].append({**schema, "schema_sha256": hashlib.sha256(json_bytes(schema)).hexdigest()})
    return rules


def length_bin(tokens):
    require(isinstance(tokens, int) and tokens >= 2, "invalid scoreable input length")
    return int(np.searchsorted(LENGTH_BOUNDS, tokens, side="right"))


def short_bucket(tokens):
    return SHORT_BUCKETS[min(length_bin(tokens), 3)]


def sequence(item):
    values = np.asarray(item["surprisals"], dtype=np.float64)
    require(values.ndim == 1 and len(values) > 0 and np.isfinite(values).all() and (values >= 0).all(), "invalid token evidence")
    require(len(values) == item["tokens_analyzed"] and len(values) == min(item["input_tokens"], 4096) - 1,
            "token coverage mismatch")
    return values


def top_mean(values, k):
    return float(np.mean(np.sort(values)[-min(k, len(values)):]))


def anomaly_runs(mask):
    lengths, current = [], 0
    for value in mask:
        if value:
            current += 1
        elif current:
            lengths.append(current)
            current = 0
    if current:
        lengths.append(current)
    if not lengths:
        return [0., 0., 0., 0.]
    n = len(mask)
    return [len(lengths) / n, max(lengths) / n, float(np.mean(lengths)) / n, lengths.count(1) / sum(lengths)]


def windows(values, scale):
    if len(values) < scale:
        return []
    starts = list(range(0, len(values) - scale + 1, scale // 2))
    if starts[-1] != len(values) - scale:
        starts.append(len(values) - scale)
    return [values[start:start + scale] for start in starts]


class References:
    def __init__(self, payload):
        self.payload = payload

    @classmethod
    def fit(cls, rows, evidence, forbidden_ids=()):
        require(len(rows) == len(evidence) and bool(rows), "reference fitting membership mismatch")
        ids = [r["sample_id"] for r in rows]
        require(len(ids) == len(set(ids)) and not set(ids) & set(forbidden_ids), "held-out reference leakage")
        require(all(r["partition"] == "BASE_TRAIN" for r in rows), "reserved reference partition")
        benign = [i for i, r in enumerate(rows) if int(r["label"]) == 0]
        require(len(benign) >= 20, "insufficient benign training references")
        bins = {b: [i for i in benign if length_bin(evidence[i]["input_tokens"]) == b] for b in range(5)}
        payload = {"fit_training_ids": ids, "benign_ids": [rows[i]["sample_id"] for i in benign], "bins": {}}
        for target in range(5):
            selected, pooled = [], []
            for b in sorted(range(5), key=lambda v: (abs(v - target), v)):
                selected.extend(bins[b])
                pooled.append(b)
                if len(selected) >= 20:
                    break
            tokens = np.concatenate([sequence(evidence[i]) for i in selected])
            reference = {"pooled_bins": pooled, "sparse_fallback": len(pooled) > 1, "benign_row_count": len(selected),
                         "token_count": len(tokens), "core": {}, "tau": np.quantile(tokens, [.90, .95, .99], method="linear").tolist()}
            for name in CORE:
                values = np.sort([evidence[i]["v1_features"][FEATURE_NAMES.index(name)] for i in selected])
                median = float(np.median(values))
                reference["core"][name] = {"median": median, "mad": float(np.median(np.abs(values - median))), "sorted_values": values.tolist()}
            payload["bins"][str(target)] = reference
        return cls(payload)

    def transform(self, item, block):
        require(block in BLOCKS, "undeclared feature block")
        base = list(item["v1_features"])
        require(len(base) == 10 and np.isfinite(base).all(), "invalid v1 evidence")
        if block == "B0":
            return np.asarray(base, dtype=np.float64)
        values = sequence(item)
        ref = self.payload["bins"][str(length_bin(item["input_tokens"]))]
        components = {"B0": base, "B1": []}
        for name in CORE:
            value, learned = base[FEATURE_NAMES.index(name)], ref["core"][name]
            components["B1"].extend([float(np.clip((value - learned["median"]) / (learned["mad"] + 1e-6), -20, 20)),
                                     float(np.searchsorted(learned["sorted_values"], value, side="right") / len(learned["sorted_values"]))])
        q25, q75, q90, q95, q99 = np.quantile(values, QUANTILES, method="linear")
        median = float(np.median(values))
        components["B2"] = [median, float(np.median(np.abs(values - median))), float(q75 - q25),
                             float(q25), float(q75), float(q90), float(q95), float(q99),
                             top_mean(values, 5), top_mean(values, max(1, math.ceil(.10 * len(values))))]
        components["B3"] = [float(np.mean(values > tau)) for tau in ref["tau"]]
        components["B4"] = anomaly_runs(values > ref["tau"][1])
        regional = []
        for region in np.array_split(values, 3):
            regional.extend([float(np.mean(region)), float(np.median(region)), float(np.mean(region > ref["tau"][1])), 1.] if len(region) else [0.] * 4)
        components["B5"] = regional + [regional[8] - regional[0], regional[4] - regional[0]]
        local = []
        for scale in SCALES:
            averages = np.asarray([np.mean(w) for w in windows(values, scale)])
            if len(averages):
                local.extend([float(np.max(averages)), float(np.median(averages)),
                              float(np.quantile(averages, .75) - np.quantile(averages, .25)), top_mean(averages, 2), 1.])
            else:
                local.extend([0.] * 5)
        components["B6"] = local
        vector = np.asarray([value for b in BLOCKS[:BLOCKS.index(block) + 1] for value in components[b]])
        require(vector.shape == (len(names(block)),) and np.isfinite(vector).all(), "non-finite/misordered features")
        return vector


def fit_lr(matrix, labels, convergence=None):
    require(np.isfinite(matrix).all() and set(labels.tolist()) == {0, 1}, "invalid LR training data")
    # Keep the historical recipe/feature hashes intact; only the authorized cap differs.
    params = {k: v for k, v in RECIPE.items() if k != "scorer"}
    model = LogisticRegression(**{**params, "max_iter": MAX_ITER})
    started = time.perf_counter()
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", ConvergenceWarning)
        model.fit(matrix, labels)
    messages = [str(w.message) for w in caught if issubclass(w.category, ConvergenceWarning)]
    record = {"max_iter": MAX_ITER, "n_iter": model.n_iter_.tolist(),
              "converged": bool(not messages and max(model.n_iter_) < MAX_ITER),
              "convergence_warnings": messages, "fit_seconds": time.perf_counter() - started}
    if convergence:
        convergence(record)
    require(record["converged"], "LR did not converge at 20000; STOP for Commander")
    return model


def evaluate(rows, evidence, progress=None, convergence=None):
    check_membership(rows)
    require(len(rows) == len(evidence), "OOF evidence length mismatch")
    labels = np.asarray([int(r["label"]) for r in rows])
    scores = {b: np.full(len(rows), np.nan) for b in BLOCKS}
    reports, references = {b: [] for b in BLOCKS}, []
    for fold in range(5):
        train = [i for i, r in enumerate(rows) if int(r["outer_fold"]) != fold]
        held = [i for i, r in enumerate(rows) if int(r["outer_fold"]) == fold]
        train_rows, held_rows = [rows[i] for i in train], [rows[i] for i in held]
        require(not {r["lineage_group"] for r in train_rows} & {r["lineage_group"] for r in held_rows}, "lineage leakage")
        refs = References.fit(train_rows, [evidence[i] for i in train], [r["sample_id"] for r in held_rows])
        references.append({"fold": fold, "training_membership_sha256": digest_ids(train_rows),
                           "held_out_membership_sha256": digest_ids(held_rows), **refs.payload})
        full_matrix = np.asarray([refs.transform(item, "B6") for item in evidence])
        for block in BLOCKS:
            matrix = full_matrix[:, :len(names(block))]
            fit_record = {}
            def record_fit(record):
                fit_record.update(record)
                if convergence:
                    convergence({"fold": fold, "block": block, **record})
            model = fit_lr(matrix[train], labels[train], record_fit)
            predicted = model.predict_proba(matrix[held])[:, 1]
            require(np.isfinite(predicted).all() and np.array_equal(predicted, model.predict_proba(matrix[held])[:, 1]), "unstable/invalid probabilities")
            require(np.isnan(scores[block][held]).all(), "duplicate held-out predictions")
            scores[block][held] = predicted
            reports[block].append({"fold": fold, "train_rows": len(train), "held_out_rows": len(held),
                "train_membership_sha256": digest_ids(train_rows), "held_out_membership_sha256": digest_ids(held_rows),
                "reference_sha256": hashlib.sha256(json_bytes(refs.payload)).hexdigest(), **fit_record,
                "identity_leakage": 0, "lineage_leakage": 0, "metrics": metrics(labels[held], predicted)})
            if progress:
                progress(fold, block)
    require(all(np.isfinite(s).all() for s in scores.values()), "missing OOF predictions")
    return scores, reports, references
