"""Data-only B2 reference/LR serialization and strictly model-bound calibration."""

import json
from pathlib import Path

import numpy as np
from scipy.special import expit

from detection_service.analysis.statistical_feature_ablation import References, names, definitions
from detection_service.analysis.statistical_scorer_comparison import B2_SHA, estimator
from detection_service.app.detectors.semantic.calibration import EPSILON, METHOD, SigmoidCalibrator
from detection_service.app.detectors.statistical_risk.scorer import StatisticalScorerError, verify_hashes

MODEL_FILE = "ds_v2_model.json"
REFERENCE_FILE = "ds_v2_feature_reference.json"
MANIFEST_FILE = "ds_v2_model_manifest_v1.json"
TRAINING_FILE = "ds_v2_training_metadata_v1.json"
INTEGRITY_FILE = "ds_v2_integrity_v1.json"
FROZEN_FILES = (MODEL_FILE, REFERENCE_FILE, MANIFEST_FILE, TRAINING_FILE, INTEGRITY_FILE)
CAL_FILE = "ds_v2_cal_v1.json"
CAL_MANIFEST = "ds_v2_calibration_manifest_v1.json"
CAL_METRICS = "ds_v2_calibration_metrics_v1.json"
CAL_INTEGRITY = "ds_v2_calibration_integrity_v1.json"


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


class B2Model:
    def __init__(self, payload, reference, manifest):
        if payload.get("classes") != [0, 1] or payload.get("recipe") != estimator("S0").get_params():
            raise StatisticalScorerError("ds_v2 class orientation/recipe mismatch")
        block = next(b for b in definitions()["blocks"] if b["schema_version"] == "stat004_B2_v1")
        if manifest.get("feature_schema_sha256") != B2_SHA or block["schema_sha256"] != B2_SHA \
                or manifest.get("feature_names") != list(names("B2")) or manifest.get("detector_version") != "ds_v2" \
                or manifest.get("final_operating_point") != "NOT_FROZEN":
            raise StatisticalScorerError("ds_v2 identity/schema/policy mismatch")
        self.coef = np.asarray(payload["coefficients"], dtype=np.float64)
        self.intercept = np.asarray(payload["intercept"], dtype=np.float64)
        if self.coef.shape != (1, 26) or self.intercept.shape != (1,) \
                or not np.isfinite(self.coef).all() or not np.isfinite(self.intercept).all():
            raise StatisticalScorerError("ds_v2 coefficients invalid")
        if set(reference.get("bins", {})) != {str(i) for i in range(5)}:
            raise StatisticalScorerError("ds_v2 reference bins incomplete")
        for ref in reference["bins"].values():
            for values in ref["core"].values():
                ordered = np.asarray(values["sorted_values"])
                if len(ordered) < 20 or not np.isfinite(ordered).all() or (np.diff(ordered) < 0).any():
                    raise StatisticalScorerError("ds_v2 reference distribution invalid")
        self.references = References(reference)
        self.manifest = manifest

    def transform(self, evidence):
        vector = self.references.transform(evidence, "B2")
        if vector.shape != (26,) or not np.isfinite(vector).all():
            raise StatisticalScorerError("ds_v2 B2 feature mismatch; no fallback")
        return vector

    def predict(self, matrix):
        x = np.asarray(matrix, dtype=np.float64)
        if x.ndim != 2 or x.shape[1] != 26 or not np.isfinite(x).all():
            raise StatisticalScorerError("ds_v2 matrix invalid; no imputation")
        return expit((x @ self.coef.T).ravel() + self.intercept[0])

    @classmethod
    def load(cls, directory, workspace=None):
        try:
            directory = Path(directory).resolve()
            integrity = read(directory / INTEGRITY_FILE)
            if set(integrity) != set(FROZEN_FILES[:-1]):
                raise ValueError("incomplete ds_v2 integrity manifest")
            verify_hashes(directory, integrity)
            manifest = read(directory / MANIFEST_FILE)
            root = Path(workspace or Path(__file__).resolve().parents[4]).resolve()
            verify_hashes(root, manifest["runtime_code_sha256"])
            return cls(read(directory / MODEL_FILE), read(directory / REFERENCE_FILE), manifest)
        except Exception as exc:
            raise StatisticalScorerError("ds_v2 unavailable or invalid; no fallback") from exc


def load_calibration(directory, model_dir):
    try:
        directory, model_dir = Path(directory), Path(model_dir)
        integrity = read(directory / CAL_INTEGRITY)
        if set(integrity) != {CAL_FILE, CAL_MANIFEST, CAL_METRICS}:
            raise ValueError("incomplete ds_v2 calibration integrity")
        verify_hashes(directory, integrity)
        metadata = read(directory / CAL_MANIFEST)
        expected = {"detector_version": "ds_v2", "calibration_version": "ds_v2_cal_v1",
                    "method": METHOD, "partitions_fitted": ["CALIBRATION"], "feature_schema_sha256": B2_SHA}
        if any(metadata.get(k) != v for k, v in expected.items()) or set(metadata["model_binding"]) != set(FROZEN_FILES):
            raise ValueError("wrong calibration identity/binding")
        verify_hashes(model_dir, metadata["model_binding"])
        payload = read(directory / CAL_FILE)
        if payload["epsilon"] != EPSILON:
            raise ValueError("wrong calibration transform")
        return SigmoidCalibrator(payload["slope"], payload["intercept"], metadata)
    except Exception as exc:
        raise StatisticalScorerError("ds_v2 calibrator unavailable or mismatched; no fallback") from exc
