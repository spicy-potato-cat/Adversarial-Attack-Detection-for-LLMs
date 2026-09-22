from time import perf_counter
from importlib import metadata as importlib_metadata

from detection_service.app.contracts.detection_request import DetectionRequest
from detection_service.app.contracts.detector_result import (
    DetectorResult,
    InputCoverage,
    ModelMetadata,
)
from detection_service.app.detectors.base import BaseDetector
from detection_service.app.detectors.statistical.config import PerplexityConfig
from detection_service.app.detectors.statistical.features import extract_features
from detection_service.app.detectors.statistical.perplexity_engine import PerplexityEngine


class StatisticalPerplexityDetector(BaseDetector):
    detector_id = "statistical_perplexity"
    detector_version = "v0.1"

    def __init__(self, config: PerplexityConfig, engine: PerplexityEngine | None = None) -> None:
        self.config = config
        self.engine = engine or PerplexityEngine(config)

    def detect(self, request: DetectionRequest) -> DetectorResult:
        started = perf_counter()
        evidence = self.engine.score(request.content.text)
        features = extract_features(
            evidence.surprisals,
            window_size=self.config.window_size,
            window_stride=self.config.window_stride,
            high_surprisal_threshold=self.config.provisional_high_surprisal_threshold,
            raw_text=request.content.text,
        )
        scoreable_tokens = max(evidence.input_tokens - 1, 0)
        tokens_excluded = max(scoreable_tokens - evidence.tokens_analyzed, 0)
        coverage_ratio = (
            evidence.tokens_analyzed / scoreable_tokens if scoreable_tokens else 0.0
        )
        return DetectorResult(
            detector_id=self.detector_id,
            detector_version=self.detector_version,
            status="success" if evidence.tokens_analyzed else "insufficient_input",
            features=features,
            input_coverage=InputCoverage(
                input_tokens=evidence.input_tokens,
                scoreable_tokens=scoreable_tokens,
                tokens_analyzed=evidence.tokens_analyzed,
                tokens_excluded=tokens_excluded,
                coverage_ratio=coverage_ratio,
                truncated=evidence.truncated,
                inference_chunks=evidence.inference_chunks,
                model_context_tokens=evidence.model_context_tokens,
                window_size=self.config.window_size,
                window_stride=self.config.window_stride,
            ),
            model=ModelMetadata(
                model_id=self.config.model_id,
                model_revision=self.config.model_revision,
                tokenizer_id=self.config.tokenizer_id,
                device=self.config.device,
            ),
            latency_ms=(perf_counter() - started) * 1000,
            warnings=evidence.warnings,
            metadata={
                "character_length": len(request.content.text),
                "runtime": self._runtime_metadata(),
            },
        )

    def _runtime_metadata(self) -> dict[str, str]:
        versions = {}
        for package in ("torch", "transformers"):
            try:
                versions[package] = importlib_metadata.version(package)
            except importlib_metadata.PackageNotFoundError:
                versions[package] = "UNKNOWN"
        return {
            "torch_version": versions["torch"],
            "transformers_version": versions["transformers"],
            "model_dtype": self._model_dtype(),
        }

    def _model_dtype(self) -> str:
        parameters = getattr(self.engine.model, "parameters", None)
        if callable(parameters):
            try:
                first_parameter = next(parameters())
                return str(first_parameter.dtype)
            except StopIteration:
                return "NO_PARAMETERS"
            except Exception:
                return "UNKNOWN"
        return "UNKNOWN"
