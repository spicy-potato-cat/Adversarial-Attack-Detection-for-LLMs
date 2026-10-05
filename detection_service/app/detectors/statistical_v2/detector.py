"""Existing LM evidence -> frozen B2 references -> LR -> optional sigmoid."""

from pathlib import Path
from time import perf_counter

import numpy as np

from detection_service.app.detectors.base import BaseDetector
from detection_service.app.detectors.statistical.perplexity_detector import StatisticalPerplexityDetector
from detection_service.app.detectors.statistical_risk.schema import feature_vector
from detection_service.app.detectors.statistical_risk.scorer import StatisticalScorerError
from .model import B2Model, load_calibration


class _ObservedEngine:
    """Reuse v0.1 result construction without scoring the LM a second time."""
    def __init__(self, observation, model):
        self.observation, self.model = observation, model

    def score(self, text):
        return self.observation


class B2StatisticalDetector(BaseDetector):
    detector_id = "statistical_perplexity"
    detector_version = "ds_v2"

    def __init__(self, extractor, model, calibrator=None):
        if extractor is None or model is None:
            raise StatisticalScorerError("ds_v2 extractor/model required; no fallback")
        self.extractor, self.model, self.calibrator = extractor, model, calibrator

    @classmethod
    def from_artifact(cls, directory, *, calibration_dir=None, workspace=None):
        from detection_service.scripts.statistical_oof_baseline import extractor
        root = Path(workspace or Path(__file__).resolve().parents[4]).resolve()
        model = B2Model.load(directory, root)
        reference = model.manifest["reference_lm"]
        if not (root / reference["snapshot_path"]).resolve().is_relative_to(root):
            raise StatisticalScorerError("ds_v2 reference path escapes workspace")
        calibration = load_calibration(calibration_dir, directory) if calibration_dir is not None else None
        return cls(extractor(model.manifest), model, calibration)

    def detect(self, request):
        started = perf_counter()
        observation = self.extractor.engine.score(request.content.text)
        result = StatisticalPerplexityDetector(self.extractor.config,
            _ObservedEngine(observation, self.extractor.engine.model)).detect(request)
        metadata = {**result.metadata, "feature_schema_sha256": self.model.manifest["feature_schema_sha256"],
            "feature_schema_version": "stat004_B2_v1", "feature_count": 26,
            "raw_score_semantics": "LR class1 probability; higher=more adversarial; uncalibrated",
            "reference_state": "FROZEN_BASE_TRAIN_ONLY_NO_INFERENCE_REFIT",
            "calibration_version": "ds_v2_cal_v1" if self.calibrator else None,
            "cutpoint_type": "DEVELOPMENT_DEFAULT_NOT_FINAL_OPERATING_POINT", "default_cutpoint": 0.5,
            "binary_vote_basis": "calibrated_probability" if self.calibrator else "raw_score",
            "final_operating_point": "NOT_FROZEN"}
        if result.status == "insufficient_input":
            return result.model_copy(update={"detector_version": "ds_v2", "metadata": metadata,
                                            "latency_ms": (perf_counter() - started) * 1000})
        try:
            item = {"surprisals": observation.surprisals, "input_tokens": observation.input_tokens,
                    "tokens_analyzed": observation.tokens_analyzed, "v1_features": feature_vector(result).tolist()}
            vector = self.model.transform(item)
            raw = float(self.model.predict(vector[None, :])[0])
            probability = float(self.calibrator.predict(np.asarray([raw]))[0]) if self.calibrator else None
            metadata["b2_features"] = dict(zip(self.model.manifest["feature_names"], vector.tolist(), strict=True))
        except Exception as exc:
            raise StatisticalScorerError("ds_v2 inference failed; no fallback") from exc
        return result.model_copy(update={"detector_version": "ds_v2", "raw_score": raw,
            "calibrated_probability": probability, "binary_vote": (probability if probability is not None else raw) >= .5,
            "metadata": metadata, "latency_ms": (perf_counter() - started) * 1000})
