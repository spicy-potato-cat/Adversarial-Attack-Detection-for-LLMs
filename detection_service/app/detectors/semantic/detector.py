from __future__ import annotations

from time import perf_counter
from pathlib import Path
import json

from detection_service.app.contracts.detection_request import DetectionRequest
from detection_service.app.contracts.detector_result import (
    DetectorResult,
    ModelMetadata,
    SemanticFeatures,
)
from detection_service.app.detectors.base import BaseDetector
from detection_service.app.detectors.semantic.classifier import (
    LogisticRegressionSemanticClassifier,
    SemanticClassifierError,
)
from detection_service.app.detectors.semantic.config import SemanticConfig
from detection_service.app.detectors.semantic.embeddings import (
    EmbeddingEncoder,
    SemanticEncoderError,
    SentenceTransformerEncoder,
)


class SemanticDetectorError(RuntimeError):
    pass


class SemanticBaselineDetector(BaseDetector):
    detector_id = "semantic_embedding_lr"
    detector_version = "v1"

    def __init__(
        self,
        config: SemanticConfig,
        encoder: EmbeddingEncoder | None = None,
        classifier: LogisticRegressionSemanticClassifier | None = None,
    ) -> None:
        config.validate()
        self.config = config
        self.encoder = encoder or SentenceTransformerEncoder(config)
        self.classifier = classifier
        self.detector_version = (
            classifier.metadata.classifier_version if classifier is not None else config.classifier_version
        )

    @classmethod
    def from_artifact(
        cls,
        artifact_dir: str | Path,
        *,
        device: str | None = None,
    ) -> "SemanticBaselineDetector":
        source = Path(artifact_dir)
        config_path = source / "model_config.json"
        if not config_path.exists():
            raise SemanticDetectorError(f"semantic model_config.json is missing: {config_path}")
        try:
            model_config = json.loads(config_path.read_text(encoding="utf-8"))
            classifier = LogisticRegressionSemanticClassifier.load(source)
            encoder_load_path = model_config.get("encoder_local_path") or model_config["encoder_model"]
            semantic_config = SemanticConfig(
                embedding_model_id=encoder_load_path,
                embedding_model_revision=model_config["encoder_revision"],
                pooling=model_config["pooling"],
                device=device or model_config.get("device_policy", "cpu"),
                batch_size=int(model_config["batch_size"]),
                max_length=model_config["max_sequence_length"],
                normalize_embeddings=bool(model_config["normalize_embeddings"]),
                local_files_only=True,
                classifier_version=model_config["detector_version"],
                positive_label=int(model_config["label_mapping"]["attack"]),
                classifier_artifact_dir=str(source),
            )
        except SemanticClassifierError as exc:
            raise SemanticDetectorError(f"semantic classifier artifact is invalid: {exc}") from exc
        except (KeyError, TypeError, ValueError) as exc:
            raise SemanticDetectorError("semantic model artifact configuration is invalid") from exc
        return cls(semantic_config, classifier=classifier)

    def detect(self, request: DetectionRequest) -> DetectorResult:
        started = perf_counter()
        if self.classifier is None:
            return DetectorResult(
                detector_id=self.detector_id,
                detector_version=self.detector_version,
                status="not_trained",
                model=self._model_metadata(),
                latency_ms=(perf_counter() - started) * 1000,
                warnings=["SEMANTIC_CLASSIFIER_NOT_TRAINED"],
                metadata={
                    "pooling": self.config.pooling,
                    "max_length": self.config.max_length,
                    "batch_size": self.config.batch_size,
                },
            )
        try:
            embedding = self.encoder.encode([request.content.text])
            raw_score = float(self.classifier.predict_raw(embedding)[0])
        except (SemanticEncoderError, SemanticClassifierError) as exc:
            raise SemanticDetectorError(str(exc)) from exc

        return DetectorResult(
            detector_id=self.detector_id,
            detector_version=self.detector_version,
            status="success",
            raw_score=raw_score,
            binary_vote=(
                raw_score >= self.classifier.metadata.default_cutpoint
                if self.classifier.metadata.default_cutpoint is not None
                else None
            ),
            semantic_features=SemanticFeatures(
                embedding_dim=int(embedding.shape[1]),
                embedding_model_id=self.classifier.metadata.embedding_model_id,
                embedding_model_revision=self.classifier.metadata.embedding_model_revision,
                normalized_embeddings=self.config.normalize_embeddings,
                classifier_type=self.classifier.metadata.classifier_type,
                classifier_version=self.classifier.metadata.classifier_version,
            ),
            model=self._model_metadata(),
            latency_ms=(perf_counter() - started) * 1000,
            warnings=[],
            metadata={
                "pooling": self.config.pooling,
                "max_length": self.config.max_length,
                "batch_size": self.config.batch_size,
                "training_manifest_id": self.classifier.metadata.training_manifest_id,
                "feature_normalization": self.classifier.metadata.feature_normalization,
                "label_mapping": self.classifier.metadata.label_mapping,
                "probability_type": "raw_logistic_regression_probability",
                "cutpoint_type": (
                    "DEFAULT_DEVELOPMENT_CUTPOINT"
                    if self.classifier.metadata.default_cutpoint is not None
                    else None
                ),
                "default_cutpoint": self.classifier.metadata.default_cutpoint,
            },
        )

    def _model_metadata(self) -> ModelMetadata:
        return ModelMetadata(
            model_id=(
                self.classifier.metadata.embedding_model_id
                if self.classifier is not None
                else self.config.embedding_model_id
            ),
            model_revision=(
                self.classifier.metadata.embedding_model_revision
                if self.classifier is not None
                else self.config.embedding_model_revision
            ),
            tokenizer_id=(
                self.classifier.metadata.embedding_model_id
                if self.classifier is not None
                else self.config.embedding_model_id
            ),
            device=self.config.device,
        )
