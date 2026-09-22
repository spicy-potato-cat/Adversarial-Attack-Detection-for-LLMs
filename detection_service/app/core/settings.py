import os
from dataclasses import dataclass, field

from detection_service.app.detectors.statistical.config import PerplexityConfig
from detection_service.app.detectors.semantic.config import SemanticConfig


@dataclass(frozen=True)
class Settings:
    pipeline_version: str
    statistical: PerplexityConfig
    semantic: SemanticConfig = field(default_factory=SemanticConfig)
    enable_semantic_detector: bool = False

    @classmethod
    def from_env(cls) -> "Settings":
        config = PerplexityConfig(
            model_id=os.getenv("STAT_MODEL_ID", PerplexityConfig.model_id),
            model_revision=os.getenv("STAT_MODEL_REVISION", PerplexityConfig.model_revision),
            tokenizer_id=os.getenv("STAT_TOKENIZER_ID", PerplexityConfig.tokenizer_id),
            device=os.getenv("STAT_DEVICE", PerplexityConfig.device),
            max_analysis_tokens=int(os.getenv("STAT_MAX_ANALYSIS_TOKENS", "4096")),
            window_size=int(os.getenv("STAT_WINDOW_SIZE", "128")),
            window_stride=int(os.getenv("STAT_WINDOW_STRIDE", "64")),
            provisional_high_surprisal_threshold=float(
                os.getenv("STAT_HIGH_SURPRISAL_THRESHOLD", "8.0")
            ),
        )
        semantic = SemanticConfig(
            embedding_model_id=os.getenv("SEMANTIC_EMBEDDING_MODEL_ID", SemanticConfig.embedding_model_id),
            embedding_model_revision=os.getenv(
                "SEMANTIC_EMBEDDING_MODEL_REVISION",
                SemanticConfig.embedding_model_revision,
            ),
            pooling=os.getenv("SEMANTIC_POOLING", SemanticConfig.pooling),
            device=os.getenv("SEMANTIC_DEVICE", SemanticConfig.device),
            batch_size=int(os.getenv("SEMANTIC_BATCH_SIZE", "32")),
            max_length=(
                int(os.environ["SEMANTIC_MAX_LENGTH"])
                if os.getenv("SEMANTIC_MAX_LENGTH")
                else None
            ),
            normalize_embeddings=os.getenv("SEMANTIC_NORMALIZE_EMBEDDINGS", "true").lower()
            in {"1", "true", "yes"},
            local_files_only=os.getenv("SEMANTIC_LOCAL_FILES_ONLY", "true").lower()
            in {"1", "true", "yes"},
            classifier_version=os.getenv("SEMANTIC_CLASSIFIER_VERSION", "UNTRAINED"),
            positive_label=int(os.getenv("SEMANTIC_POSITIVE_LABEL", "1")),
            classifier_artifact_dir=os.getenv("SEMANTIC_MODEL_DIR"),
        )
        config.validate()
        semantic.validate()
        return cls(
            pipeline_version=os.getenv("DETECTION_PIPELINE_VERSION", "dev-v0.1"),
            statistical=config,
            semantic=semantic,
            enable_semantic_detector=os.getenv("ENABLE_SEMANTIC_DETECTOR", "false").lower()
            in {"1", "true", "yes"},
        )
