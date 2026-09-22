from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SemanticConfig:
    embedding_model_id: str = "TODO-MODEL"
    embedding_model_revision: str = "TODO-MODEL-REVISION"
    pooling: str = "sentence-transformer-default"
    device: str = "cpu"
    batch_size: int = 32
    max_length: int | None = None
    normalize_embeddings: bool = True
    local_files_only: bool = True
    classifier_version: str = "UNTRAINED"
    positive_label: int = 1
    classifier_artifact_dir: str | None = None

    def validate(self) -> None:
        if not self.embedding_model_id.strip():
            raise ValueError("embedding_model_id must not be blank")
        if not self.embedding_model_revision.strip():
            raise ValueError("embedding_model_revision must not be blank")
        if self.batch_size < 1:
            raise ValueError("batch_size must be positive")
        if self.max_length is not None and self.max_length < 1:
            raise ValueError("max_length must be positive when configured")
        if self.classifier_artifact_dir is not None and not self.classifier_artifact_dir.strip():
            raise ValueError("classifier_artifact_dir must not be blank when configured")

    @property
    def loads_from_local_path(self) -> bool:
        return Path(self.embedding_model_id).exists()
