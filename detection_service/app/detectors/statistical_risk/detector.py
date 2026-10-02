from pathlib import Path
from time import perf_counter

from transformers import AutoModelForCausalLM, AutoTokenizer

from detection_service.app.detectors.base import BaseDetector
from detection_service.app.detectors.statistical.config import PerplexityConfig
from detection_service.app.detectors.statistical.perplexity_detector import StatisticalPerplexityDetector
from detection_service.app.detectors.statistical.perplexity_engine import PerplexityEngine
from .schema import feature_vector, schema_hash
from .scorer import StatisticalScorer, StatisticalScorerError, load_calibrator, verify_hashes


class ScoredStatisticalDetector(BaseDetector):
    detector_id = "statistical_perplexity"
    detector_version = "ds_v1"

    def __init__(self, extractor, scorer, calibrator):
        if scorer is None or calibrator is None:
            raise StatisticalScorerError("Scorer and calibrator required; no evidence-only fallback")
        self.extractor, self.scorer, self.calibrator = extractor, scorer, calibrator

    @classmethod
    def from_artifact(cls, directory, *, workspace=None, device="cpu"):
        root = Path(workspace or Path(__file__).resolve().parents[4]).resolve()
        try:
            source = Path(directory).resolve()
            scorer, config = StatisticalScorer.load(source)
            verify_hashes(root, config["feature_extractor_sha256"])
            calibrator = load_calibrator(source / "calibration", source)
            reference = config["reference_lm"]
            snapshot = (root / reference["snapshot_path"]).resolve()
            if not snapshot.is_relative_to(root):
                raise ValueError("Reference model path escapes workspace")
            verify_hashes(snapshot, reference["file_sha256"])
            cfg = PerplexityConfig(**config["extractor_config"])
            from dataclasses import replace
            cfg = replace(cfg, device=device)
            tokenizer = AutoTokenizer.from_pretrained(snapshot, local_files_only=True, use_fast=True, trust_remote_code=False)
            model = AutoModelForCausalLM.from_pretrained(snapshot, local_files_only=True, use_safetensors=True, trust_remote_code=False)
            model.requires_grad_(False)
            extractor = StatisticalPerplexityDetector(cfg, PerplexityEngine(cfg, tokenizer, model))
            return cls(extractor, scorer, calibrator)
        except Exception as exc:
            if isinstance(exc, StatisticalScorerError):
                raise
            raise StatisticalScorerError("D_S ds_v1 initialization failed; no fallback") from exc

    def detect(self, request):
        started = perf_counter()
        result = self.extractor.detect(request)
        metadata = {**result.metadata, "feature_extractor_version": "v0.1",
                    "feature_schema_sha256": schema_hash(), "probability_type": "raw_LR_class_1_probability",
                    "calibration_version": "ds_v1_cal_v1", "calibration_method": "platt_sigmoid_on_lr_log_odds",
                    "cutpoint_type": "DEFAULT_DEVELOPMENT_CUTPOINT", "default_cutpoint": 0.5,
                    "binary_vote_basis": "calibrated_probability", "final_operating_point": "NOT_FROZEN"}
        if result.status == "insufficient_input":
            return result.model_copy(update={"detector_version": "ds_v1", "metadata": metadata,
                                             "latency_ms": (perf_counter() - started) * 1000})
        try:
            vector = feature_vector(result)
            raw = float(self.scorer.predict(vector[None, :])[0])
            probability = float(self.calibrator.predict([raw])[0])
            if not 0 <= probability <= 1:
                raise ValueError("Invalid calibrated statistical probability")
        except Exception as exc:
            raise StatisticalScorerError("D_S scoring failed; no fallback") from exc
        return result.model_copy(update={
            "detector_version": "ds_v1", "raw_score": raw, "calibrated_probability": probability,
            "binary_vote": probability >= 0.5, "metadata": metadata,
            "latency_ms": (perf_counter() - started) * 1000,
        })
