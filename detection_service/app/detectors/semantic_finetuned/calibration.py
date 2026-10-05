"""Separate Platt mapping bound to the frozen D_M-B transformer and tokenizer."""

from __future__ import annotations

import json
from pathlib import Path

from detection_service.app.detectors.semantic.calibration import (
    EPSILON, MANIFEST_SHA256, SemanticCalibrationError, SigmoidCalibrator, file_sha256,
)

CALIBRATION_VERSION = "dm_b_v1_cal_v1"
METHOD = "platt_sigmoid_on_softmax_log_odds"
INPUT_SCORE = "logit(clip(raw_softmax_class_1_probability,1e-12,1-1e-12))"


def model_binding(directory: Path) -> dict[str, str]:
    directory = directory.resolve()
    manifest = directory / "integrity_manifest.json"
    files = json.loads(manifest.read_text(encoding="utf-8"))
    required = {"model_config.json", "transformer/config.json", "transformer/model.safetensors", "transformer/tokenizer.json"}
    if not isinstance(files, dict) or not required.issubset(files):
        raise SemanticCalibrationError("incomplete D_M-B model binding")
    for name, digest in files.items():
        path = (directory / name).resolve()
        if not path.is_relative_to(directory) or file_sha256(path) != digest:
            raise SemanticCalibrationError("frozen D_M-B model integrity failure")
    return {**files, "integrity_manifest.json": file_sha256(manifest)}


class FineTunedCalibrator(SigmoidCalibrator):
    @classmethod
    def load(cls, directory: Path, model_dir: Path) -> "FineTunedCalibrator":
        try:
            artifact = directory / "calibrator.json"
            payload = json.loads(artifact.read_text(encoding="utf-8"))
            metadata = json.loads((directory / "calibration_metadata.json").read_text(encoding="utf-8"))
            if not isinstance(payload, dict) or not isinstance(metadata, dict):
                raise ValueError("calibrator and metadata must be JSON objects")
            expected = {
                "schema_version": "1.0", "detector_id": "semantic_finetuned",
                "detector_version": "dm_b_v1", "calibration_version": CALIBRATION_VERSION,
                "calibration_method": METHOD, "input_score_definition": INPUT_SCORE,
                "calibration_manifest_sha256": MANIFEST_SHA256,
                "label_mapping": {"benign": 0, "attack": 1},
                "calibration_sample_count": 233, "calibration_positive_count": 41,
                "calibration_negative_count": 192, "partitions_fitted": ["CALIBRATION"],
                "transformer_retrained": False, "validation_consumed": False,
                "protected_data_consumed": False,
            }
            if any(metadata.get(k) != v for k, v in expected.items()):
                raise ValueError("D_M-B calibration identity, data boundary, or score definition mismatch")
            if metadata["frozen_model_sha256"] != model_binding(model_dir):
                raise ValueError("calibrator is incompatible with frozen D_M-B")
            if metadata["calibrator_sha256"] != file_sha256(artifact) or payload["epsilon"] != EPSILON:
                raise ValueError("calibrator integrity or input transform mismatch")
            return cls(payload["slope"], payload["intercept"], metadata)
        except (OSError, ValueError, KeyError, TypeError, SemanticCalibrationError) as exc:
            raise SemanticCalibrationError(f"D_M-B calibrator unavailable or invalid; no fallback: {exc}") from exc
