from __future__ import annotations

import json
from pathlib import Path
from threading import RLock
from time import perf_counter

import torch
import numpy as np
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from detection_service.app.contracts.detection_request import DetectionRequest
from detection_service.app.contracts.detector_result import DetectorResult, ModelMetadata
from detection_service.app.detectors.base import BaseDetector
from detection_service.app.detectors.semantic.calibration import file_sha256
from detection_service.app.detectors.semantic.detector import SemanticDetectorError
from detection_service.app.detectors.semantic_finetuned.config import FineTunedConfig
from detection_service.app.detectors.semantic_finetuned.calibration import FineTunedCalibrator, METHOD, CALIBRATION_VERSION


class FineTunedDetectorError(SemanticDetectorError):
    pass


class FineTunedSemanticDetector(BaseDetector):
    detector_id = "semantic_finetuned"
    detector_version = "dm_b_v1"

    def __init__(self, config: FineTunedConfig, tokenizer, model, calibrator: FineTunedCalibrator | None = None) -> None:
        config.validate()
        if config.device == "cuda" and not torch.cuda.is_available():
            raise FineTunedDetectorError("D_M-B requires CUDA; CPU substitution is not permitted")
        if model.config.num_labels != 2 or model.config.model_type != "roberta":
            raise FineTunedDetectorError("D_M-B requires a binary RoBERTa sequence classifier")
        if model.config.id2label != {0: "BENIGN", 1: "ATTACK"}:
            raise FineTunedDetectorError("D_M-B label orientation is invalid")
        self.config, self.tokenizer = config, tokenizer
        self.calibrator = calibrator
        self.model = model.to(config.device).eval()
        self.tokenizer.truncation_side = config.truncation_side
        self.tokenizer.padding_side = config.padding_side
        self._lock = RLock()

    @classmethod
    def from_artifact(cls, directory: str | Path, *, device: str | None = None,
                      require_calibration: bool = False) -> "FineTunedSemanticDetector":
        source = Path(directory).resolve()
        try:
            payload = json.loads((source / "model_config.json").read_text(encoding="utf-8"))
            config = FineTunedConfig.from_dict(payload["recipe"])
            if payload["training_status"] != "COMPLETE" or payload["label_mapping"] != {"benign": 0, "attack": 1}:
                raise ValueError("model is not a completed frozen binary classifier")
            integrity = json.loads((source / "integrity_manifest.json").read_text(encoding="utf-8"))
            required = {"model_config.json", "transformer/config.json", "transformer/model.safetensors", "transformer/tokenizer.json"}
            if not required.issubset(integrity):
                raise ValueError("incomplete D_M-B integrity manifest")
            for name, digest in integrity.items():
                path = (source / name).resolve()
                if not path.is_relative_to(source) or file_sha256(path) != digest:
                    raise ValueError("D_M-B artifact integrity failure")
            if device is not None:
                from dataclasses import replace
                config = replace(config, device=device)
                config.validate()
            tokenizer = AutoTokenizer.from_pretrained(source / "transformer", local_files_only=True, use_fast=True)
            model = AutoModelForSequenceClassification.from_pretrained(
                source / "transformer", local_files_only=True, use_safetensors=True
            )
            calibration_dir = source / "calibration"
            if require_calibration and not calibration_dir.is_dir():
                raise ValueError("D_M-B calibration is required but missing")
            calibrator = FineTunedCalibrator.load(calibration_dir, source) if calibration_dir.exists() else None
            return cls(config, tokenizer, model, calibrator)
        except Exception as exc:
            if isinstance(exc, FineTunedDetectorError):
                raise
            raise FineTunedDetectorError("D_M-B artifact is unavailable or invalid; no fallback is permitted") from exc

    def detect(self, request: DetectionRequest) -> DetectorResult:
        return self.detect_batch([request])[0]

    def detect_batch(self, requests: list[DetectionRequest]) -> list[DetectorResult]:
        if not requests:
            return []
        results = []
        for start in range(0, len(requests), self.config.batch_size):
            batch = requests[start:start + self.config.batch_size]
            started = perf_counter()
            texts = [r.content.text for r in batch]
            try:
                with self._lock, torch.inference_mode():
                    self.model.eval()
                    token_counts = [len(self.tokenizer.encode(t, add_special_tokens=True, truncation=False, verbose=False)) for t in texts]
                    inputs = self.tokenizer(
                        texts, add_special_tokens=True, padding=True, truncation=True,
                        max_length=self.config.max_sequence_length, return_tensors="pt",
                    ).to(self.config.device)
                    logits = self.model(**inputs).logits
                    if logits.shape != (len(batch), 2) or not torch.isfinite(logits).all():
                        raise ValueError("invalid D_M-B logits")
                    scores = torch.softmax(logits, dim=-1)[:, 1].cpu().tolist()
                    calibrated = self.calibrator.predict(np.array(scores)) if self.calibrator else [None] * len(scores)
                    if self.calibrator and (np.shape(calibrated) != (len(scores),) or
                                            not np.isfinite(calibrated).all() or
                                            ((calibrated < 0) | (calibrated > 1)).any()):
                        raise ValueError("invalid D_M-B calibrated probabilities")
            except Exception as exc:
                raise FineTunedDetectorError("D_M-B inference failed; no fallback is permitted") from exc
            latency = (perf_counter() - started) * 1000 / len(batch)
            for score, probability, count in zip(scores, calibrated, token_counts):
                if not 0 <= score <= 1:
                    raise FineTunedDetectorError("D_M-B probability is outside [0,1]")
                truncated = count > self.config.max_sequence_length
                results.append(DetectorResult(
                    detector_id=self.detector_id, detector_version=self.detector_version, status="success",
                    raw_score=float(score), calibrated_probability=float(probability) if probability is not None else None,
                    binary_vote=score >= 0.5,
                    model=ModelMetadata(model_id=self.config.upstream_model, model_revision=self.config.upstream_revision,
                                        tokenizer_id=self.config.upstream_model, device=self.config.device),
                    latency_ms=latency, warnings=["SEMANTIC_INPUT_TRUNCATED"] if truncated else [],
                    metadata={
                        **({"calibration_method": METHOD, "calibration_version": CALIBRATION_VERSION} if self.calibrator else {}),
                        "probability_type": "raw_softmax_class_1_probability",
                        "label_mapping": {"benign": 0, "attack": 1},
                        "cutpoint_type": "DEFAULT_DEVELOPMENT_CUTPOINT", "default_cutpoint": 0.5,
                        "tokenizer_revision": self.config.tokenizer_revision,
                        "input_tokens_including_special": count,
                        "tokens_analyzed_including_special": min(count, self.config.max_sequence_length),
                        "max_sequence_length": self.config.max_sequence_length, "truncated": truncated,
                        "truncation_side": "right", "padding": "longest_in_batch",
                        "latency_basis": "batch_elapsed_ms_divided_by_batch_count",
                    },
                ))
        return results
