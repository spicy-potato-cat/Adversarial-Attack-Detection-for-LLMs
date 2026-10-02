from __future__ import annotations

import json
import warnings
from pathlib import Path

import joblib
import numpy as np
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression

from detection_service.app.detectors.semantic.calibration import EPSILON, SigmoidCalibrator, file_sha256
from .schema import FEATURE_NAMES, FEATURE_SCHEMA, schema_hash

RECIPE = {
    "scorer": "LogisticRegression", "solver": "lbfgs", "penalty": "l2", "C": 1.0,
    "class_weight": "balanced", "max_iter": 1000, "random_state": 1701, "fit_intercept": True,
}
CALIBRATION_VERSION = "ds_v1_cal_v1"
METHOD = "platt_sigmoid_on_lr_log_odds"


class StatisticalScorerError(RuntimeError):
    pass


def verify_hashes(root: Path, hashes: dict):
    root = root.resolve()
    for name, digest in hashes.items():
        path = (root / name).resolve()
        if not path.is_relative_to(root) or not path.is_file() or file_sha256(path) != digest:
            raise StatisticalScorerError(f"Statistical artifact integrity failure: {name}")


def validate_partition(rows, partition):
    if partition not in {"BASE_TRAIN", "CALIBRATION", "VALIDATION"} or not rows:
        raise StatisticalScorerError("Invalid statistical development partition")
    if any(row.get("partition") != partition for row in rows):
        raise StatisticalScorerError(f"Statistical operation requires {partition} only")
    labels = np.asarray([int(row["canonical_label"]) for row in rows])
    if set(labels.tolist()) != {0, 1}:
        raise StatisticalScorerError("Both approved binary labels are required")
    return labels


def check_matrix(matrix):
    x = np.asarray(matrix, dtype=np.float64)
    if x.ndim != 2 or x.shape[1] != len(FEATURE_NAMES) or not np.isfinite(x).all():
        raise StatisticalScorerError("Invalid or non-finite statistical matrix; no imputation")
    return x


class StatisticalScorer:
    def __init__(self, model):
        self.model = model
        if list(model.classes_) != [0, 1] or model.coef_.shape != (1, len(FEATURE_NAMES)):
            raise StatisticalScorerError("Statistical scorer class orientation/shape mismatch")
        if not np.isfinite(model.coef_).all() or not np.isfinite(model.intercept_).all():
            raise StatisticalScorerError("Non-finite statistical coefficients")
        if any(model.get_params().get(key) != value for key, value in RECIPE.items() if key != "scorer"):
            raise StatisticalScorerError("Statistical scorer recipe mismatch")

    @classmethod
    def fit(cls, matrix, rows):
        labels = validate_partition(rows, "BASE_TRAIN")
        x = check_matrix(matrix)
        if len(x) != len(labels):
            raise StatisticalScorerError("Statistical feature/label count mismatch")
        with warnings.catch_warnings():
            warnings.simplefilter("error", ConvergenceWarning)
            try:
                model = LogisticRegression(**{k: v for k, v in RECIPE.items() if k != "scorer"}).fit(x, labels)
            except ConvergenceWarning as exc:
                raise StatisticalScorerError("STOP: statistical scorer failed to converge") from exc
        if not len(model.n_iter_) or max(model.n_iter_) >= RECIPE["max_iter"]:
            raise StatisticalScorerError("STOP: statistical scorer failed to converge")
        return cls(model)

    def predict(self, matrix):
        scores = np.asarray(self.model.predict_proba(check_matrix(matrix))[:, 1])
        if not np.isfinite(scores).all() or ((scores < 0) | (scores > 1)).any():
            raise StatisticalScorerError("Invalid statistical raw probabilities")
        return scores

    @classmethod
    def load(cls, directory):
        try:
            source = Path(directory).resolve()
            hashes = json.loads((source / "integrity_manifest.json").read_text(encoding="utf-8"))
            if not {"scorer.joblib", "model_config.json", "feature_schema.json", "training_metadata.json"}.issubset(hashes):
                raise ValueError("Incomplete statistical integrity manifest")
            verify_hashes(source, hashes)
            config = json.loads((source / "model_config.json").read_text(encoding="utf-8"))
            schema = json.loads((source / "feature_schema.json").read_text(encoding="utf-8"))
            if config["detector_version"] != "ds_v1" or config["detector_id"] != "statistical_perplexity":
                raise ValueError("Statistical scorer identity mismatch")
            if config["scorer_recipe"] != RECIPE or schema != FEATURE_SCHEMA or config["feature_schema_sha256"] != schema_hash():
                raise ValueError("Statistical feature schema or recipe mismatch")
            return cls(joblib.load(source / "scorer.joblib")), config
        except Exception as exc:
            if isinstance(exc, StatisticalScorerError):
                raise
            raise StatisticalScorerError("Statistical scorer unavailable/invalid; no fallback") from exc


def fit_calibrator(raw, rows, metadata):
    labels = validate_partition(rows, "CALIBRATION")
    if np.asarray(raw).shape != labels.shape:
        raise StatisticalScorerError("Calibration feature/label count mismatch")
    return SigmoidCalibrator.fit_mapping(raw, labels, metadata)


def load_calibrator(directory, model_dir):
    try:
        directory, model_dir = Path(directory), Path(model_dir)
        metadata = json.loads((directory / "calibration_metadata.json").read_text(encoding="utf-8"))
        payload = json.loads((directory / "calibrator.json").read_text(encoding="utf-8"))
        integrity = json.loads((directory / "integrity_manifest.json").read_text(encoding="utf-8"))
        if set(integrity) != {"calibrator.json", "calibration_metadata.json", "calibration_config.json"}:
            raise ValueError("Incomplete statistical calibration integrity manifest")
        verify_hashes(directory, integrity)
        expected = {"detector_version": "ds_v1", "calibration_version": CALIBRATION_VERSION,
                    "calibration_method": METHOD, "partitions_fitted": ["CALIBRATION"],
                    "feature_schema_sha256": schema_hash()}
        if any(metadata.get(k) != v for k, v in expected.items()):
            raise ValueError("Statistical calibration identity/schema mismatch")
        required_binding = {"scorer.joblib", "model_config.json", "feature_schema.json", "training_metadata.json", "integrity_manifest.json"}
        if set(metadata["frozen_scorer_sha256"]) != required_binding:
            raise ValueError("Incomplete statistical calibration/scorer binding")
        verify_hashes(model_dir, metadata["frozen_scorer_sha256"])
        if metadata["calibrator_sha256"] != file_sha256(directory / "calibrator.json") or payload["epsilon"] != EPSILON:
            raise ValueError("Statistical calibrator hash or transform mismatch")
        return SigmoidCalibrator(payload["slope"], payload["intercept"], metadata)
    except Exception as exc:
        raise StatisticalScorerError("Statistical calibrator unavailable/invalid; no fallback") from exc
