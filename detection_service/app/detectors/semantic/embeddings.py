from __future__ import annotations

from importlib import import_module
from typing import Any, Protocol

import numpy as np

from detection_service.app.detectors.semantic.config import SemanticConfig


class SemanticEncoderError(RuntimeError):
    pass


class EmbeddingEncoder(Protocol):
    def encode(self, texts: list[str]) -> np.ndarray:
        raise NotImplementedError


class SentenceTransformerEncoder:
    def __init__(self, config: SemanticConfig) -> None:
        config.validate()
        self.config = config
        try:
            module = import_module("sentence_transformers")
            sentence_transformer = getattr(module, "SentenceTransformer")
            kwargs: dict[str, Any] = {
                "device": config.device,
                "local_files_only": config.local_files_only,
            }
            if (
                config.embedding_model_revision != "TODO-MODEL-REVISION"
                and not config.loads_from_local_path
            ):
                kwargs["revision"] = config.embedding_model_revision
            self._model = sentence_transformer(config.embedding_model_id, **kwargs)
            if config.max_length is not None:
                self._model.max_seq_length = config.max_length
            if hasattr(self._model, "eval"):
                self._model.eval()
        except Exception as exc:
            raise SemanticEncoderError(
                "semantic embedding model is unavailable; no fallback encoder is permitted"
            ) from exc

    def encode(self, texts: list[str]) -> np.ndarray:
        try:
            values = self._model.encode(
                texts,
                batch_size=self.config.batch_size,
                convert_to_numpy=True,
                normalize_embeddings=self.config.normalize_embeddings,
                show_progress_bar=False,
            )
        except Exception as exc:
            raise SemanticEncoderError("semantic embedding inference failed") from exc
        embeddings = np.asarray(values, dtype=float)
        if embeddings.ndim != 2 or embeddings.shape[0] != len(texts):
            raise SemanticEncoderError("semantic embedding output shape is invalid")
        return embeddings
