from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np


class SemanticClassifierError(RuntimeError):
    pass


@dataclass(frozen=True)
class SemanticClassifierMetadata:
    classifier_type: str
    classifier_version: str
    embedding_model_id: str
    embedding_model_revision: str
    embedding_dim: int
    positive_label: int
    training_manifest_id: str
    feature_normalization: str
    label_mapping: dict[str, int]
    software_version: str
    created_at: str
    solver: str = "lbfgs"
    penalty: str = "l2"
    C: float = 1.0
    class_weight: str | dict[int, float] | None = None
    max_iter: int = 1000
    random_seed: int = 1701
    fit_intercept: bool = True
    default_cutpoint: float | None = None


class LogisticRegressionSemanticClassifier:
    classifier_type = "logistic_regression"

    def __init__(self, model: Any, metadata: SemanticClassifierMetadata) -> None:
        self.model = model
        self.metadata = metadata

    @classmethod
    def train(
        cls,
        embeddings: np.ndarray,
        labels: list[int],
        metadata: SemanticClassifierMetadata,
        *,
        max_iter: int = 1000,
        class_weight: str | dict[int, float] | None = None,
        solver: str = "lbfgs",
        penalty: str = "l2",
        C: float = 1.0,
        random_seed: int = 1701,
        fit_intercept: bool = True,
    ) -> "LogisticRegressionSemanticClassifier":
        try:
            from sklearn.linear_model import LogisticRegression
        except Exception as exc:
            raise SemanticClassifierError("scikit-learn is required for semantic LR training") from exc

        x = np.asarray(embeddings, dtype=float)
        y = np.asarray(labels, dtype=int)
        if x.ndim != 2:
            raise SemanticClassifierError("embeddings must be a two-dimensional matrix")
        if len(y) != x.shape[0]:
            raise SemanticClassifierError("label count must match embedding rows")
        if x.shape[1] != metadata.embedding_dim:
            raise SemanticClassifierError("embedding dimension does not match metadata")
        model = LogisticRegression(
            solver=solver,
            penalty=penalty,
            C=C,
            max_iter=max_iter,
            class_weight=class_weight,
            random_state=random_seed,
            fit_intercept=fit_intercept,
        ).fit(x, y)
        return cls(model, metadata)

    def predict_raw(self, embeddings: np.ndarray) -> np.ndarray:
        x = np.asarray(embeddings, dtype=float)
        if x.ndim != 2:
            raise SemanticClassifierError("embeddings must be a two-dimensional matrix")
        if x.shape[1] != self.metadata.embedding_dim:
            raise SemanticClassifierError("embedding dimension does not match classifier metadata")
        if not hasattr(self.model, "predict_proba"):
            raise SemanticClassifierError("semantic classifier does not expose predict_proba")
        probabilities = np.asarray(self.model.predict_proba(x), dtype=float)
        classes = list(getattr(self.model, "classes_", []))
        try:
            positive_index = classes.index(self.metadata.positive_label)
        except ValueError as exc:
            raise SemanticClassifierError("positive label is absent from classifier classes") from exc
        return probabilities[:, positive_index]

    def save(self, directory: str | Path) -> Path:
        target = Path(directory)
        target.mkdir(parents=True, exist_ok=True)
        model_path = target / "classifier.joblib"
        metadata_path = target / "classifier_metadata.json"
        try:
            import joblib
        except Exception as exc:
            raise SemanticClassifierError("joblib is required to save semantic classifier") from exc
        joblib.dump(self.model, model_path)
        metadata_path.write_text(json.dumps(asdict(self.metadata), indent=2), encoding="utf-8")
        return model_path

    @classmethod
    def load(cls, directory: str | Path) -> "LogisticRegressionSemanticClassifier":
        source = Path(directory)
        model_path = source / "classifier.joblib"
        metadata_path = source / "classifier_metadata.json"
        if not model_path.exists() and (source / "semantic_lr_classifier.pkl").exists():
            model_path = source / "semantic_lr_classifier.pkl"
            metadata_path = source / "semantic_lr_classifier.metadata.json"
        if not model_path.exists():
            raise SemanticClassifierError(f"semantic classifier artifact is missing: {model_path}")
        if not metadata_path.exists():
            raise SemanticClassifierError(f"semantic classifier metadata is missing: {metadata_path}")
        try:
            if model_path.suffix == ".joblib":
                import joblib

                model = joblib.load(model_path)
            else:
                import pickle

                with model_path.open("rb") as handle:
                    model = pickle.load(handle)
        except Exception as exc:
            raise SemanticClassifierError("semantic classifier artifact could not be loaded") from exc
        metadata = SemanticClassifierMetadata(**json.loads(metadata_path.read_text(encoding="utf-8")))
        return cls(model, metadata)
