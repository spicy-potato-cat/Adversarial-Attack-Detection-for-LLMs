"""Versioned sigmoid mapping over frozen LR log-odds; no classifier fitting."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
from scipy.optimize import minimize
from scipy.special import expit


MANIFEST_SHA256 = "9cdd5ecdd80f9ac3c8f05db63742721f4537ca2b64a2fe48f6c2b424b57483a6"
CALIBRATION_VERSION = "dm_a_v1_sigmoid_v1"
METHOD = "platt_sigmoid_on_lr_log_odds"
EPSILON = 1e-12
FROZEN_FILES = ("classifier.joblib", "classifier_metadata.json", "model_config.json")


class SemanticCalibrationError(RuntimeError):
    pass


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def model_binding(model_dir: Path) -> dict[str, str]:
    return {name: file_sha256(model_dir / name) for name in FROZEN_FILES}


def log_odds(probabilities: np.ndarray) -> np.ndarray:
    p = np.asarray(probabilities, dtype=float)
    if p.ndim != 1 or not np.isfinite(p).all() or ((p < 0) | (p > 1)).any():
        raise SemanticCalibrationError("raw probabilities must be a finite vector in [0,1]")
    clipped = np.clip(p, EPSILON, 1.0 - EPSILON)
    return np.log(clipped) - np.log1p(-clipped)


class SigmoidCalibrator:
    def __init__(self, slope: float, intercept: float, metadata: dict[str, Any]) -> None:
        if not np.isfinite([slope, intercept]).all() or slope <= 0:
            raise SemanticCalibrationError("calibrator requires a finite positive slope and intercept")
        self.slope = float(slope)
        self.intercept = float(intercept)
        self.metadata = metadata

    @classmethod
    def fit_mapping(
        cls, probabilities: np.ndarray, labels: np.ndarray, metadata: dict[str, Any]
    ) -> "SigmoidCalibrator":
        x = log_odds(probabilities)
        y = np.asarray(labels)
        if y.shape != x.shape or set(y.tolist()) != {0, 1}:
            raise SemanticCalibrationError("calibration requires aligned binary labels with both classes")
        positives = int(y.sum())
        negatives = len(y) - positives
        # Platt's smoothed targets avoid infinite estimates under separation.
        targets = np.where(y == 1, (positives + 1) / (positives + 2), 1 / (negatives + 2))

        def objective(params: np.ndarray) -> tuple[float, np.ndarray]:
            z = params[0] * x + params[1]
            residual = expit(z) - targets
            loss = np.mean(np.logaddexp(0, z) - targets * z)
            gradient = np.array([np.mean(residual * x), np.mean(residual)])
            return float(loss), gradient

        result = minimize(
            objective,
            np.array([1.0, np.log((positives + 1) / (negatives + 1))]),
            jac=True,
            method="L-BFGS-B",
            bounds=[(1e-8, None), (None, None)],
            options={"maxiter": 1000, "ftol": 1e-12, "gtol": 1e-10},
        )
        if not result.success:
            raise SemanticCalibrationError(f"sigmoid calibration did not converge: {result.message}")
        metadata = {
            **metadata,
            "optimizer_iterations": int(result.nit),
            "optimizer_converged": True,
            "calibration_sample_count": len(y),
            "calibration_positive_count": positives,
            "calibration_negative_count": negatives,
        }
        return cls(float(result.x[0]), float(result.x[1]), metadata)

    def predict(self, probabilities: np.ndarray) -> np.ndarray:
        return expit(self.slope * log_odds(probabilities) + self.intercept)

    def save(self, directory: Path) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        payload = {"slope": self.slope, "intercept": self.intercept, "epsilon": EPSILON}
        artifact = directory / "calibrator.json"
        artifact.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        metadata = {**self.metadata, "calibrator_sha256": file_sha256(artifact)}
        (directory / "calibration_metadata.json").write_text(
            json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
        )
        self.metadata = metadata

    @classmethod
    def load(cls, directory: Path, model_dir: Path) -> "SigmoidCalibrator":
        try:
            artifact = directory / "calibrator.json"
            metadata = json.loads((directory / "calibration_metadata.json").read_text(encoding="utf-8"))
            payload = json.loads(artifact.read_text(encoding="utf-8"))
            counts = [metadata[k] for k in (
                "calibration_sample_count", "calibration_positive_count", "calibration_negative_count"
            )]
            expected = {
                "detector_id": "semantic_embedding_lr",
                "detector_version": "dm_a_v1",
                "calibration_version": CALIBRATION_VERSION,
                "calibration_method": METHOD,
                "calibration_manifest_sha256": MANIFEST_SHA256,
                "label_mapping": {"benign": 0, "attack": 1},
            }
            if any(metadata.get(k) != v for k, v in expected.items()):
                raise ValueError("calibration metadata identity, manifest, or label mapping mismatch")
            if counts[0] != 233 or counts[1] <= 0 or counts[2] <= 0 or sum(counts[1:]) != counts[0]:
                raise ValueError("calibration sample counts are invalid")
            if metadata["frozen_model_sha256"] != model_binding(model_dir):
                raise ValueError("calibrator is incompatible with the frozen model artifacts")
            if metadata["calibrator_sha256"] != file_sha256(artifact) or payload["epsilon"] != EPSILON:
                raise ValueError("calibrator integrity or probability transform mismatch")
            return cls(payload["slope"], payload["intercept"], metadata)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            raise SemanticCalibrationError(f"semantic calibrator is unavailable or invalid: {exc}") from exc
