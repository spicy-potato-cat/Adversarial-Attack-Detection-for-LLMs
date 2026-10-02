import hashlib
import json

import numpy as np

FEATURE_NAMES = (
    "whole_prompt_nll", "whole_prompt_ppl", "global_perplexity",
    "mean_window_perplexity", "max_window_perplexity", "std_window_perplexity",
    "mean_surprisal", "max_surprisal", "surprisal_std", "high_surprisal_ratio",
)
FEATURE_SCHEMA = {
    "schema_version": "ds_features_v1", "extractor_version": "v0.1",
    "feature_names": list(FEATURE_NAMES), "feature_count": len(FEATURE_NAMES),
    "normalization": "identity; no scaling, log transformation, imputation or selection",
    "ordering_source": "existing export_features.FIELDNAMES[3:13]",
    "compatibility_aliases_retained": True,
    "excluded": "source/label metadata, runtime latency, coverage counters and auxiliary surface anomalies",
}


def json_bytes(value):
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")


def schema_hash():
    return hashlib.sha256(json_bytes(FEATURE_SCHEMA)).hexdigest()


def feature_vector(result):
    if result.status != "success" or result.features is None:
        raise ValueError("STOP: statistical evidence is insufficient for scoring")
    values = [getattr(result.features, name) for name in FEATURE_NAMES]
    if any(value is None for value in values):
        raise ValueError("STOP: missing statistical feature; imputation is not authorized")
    vector = np.asarray(values, dtype=np.float64)
    if vector.shape != (len(FEATURE_NAMES),) or not np.isfinite(vector).all():
        raise ValueError("STOP: non-finite or malformed statistical feature vector")
    return vector
