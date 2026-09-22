from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pytest

from detection_service.app.contracts.detection_request import DetectionContent, DetectionRequest
from detection_service.app.detectors.semantic.classifier import (
    LogisticRegressionSemanticClassifier,
    SemanticClassifierMetadata,
)
from detection_service.app.detectors.semantic.config import SemanticConfig
from detection_service.app.detectors.semantic.detector import SemanticBaselineDetector
from detection_service.app.detectors.semantic.embeddings import (
    SemanticEncoderError,
    SentenceTransformerEncoder,
)
from detection_service.scripts.train_semantic_baseline import (
    EXPECTED_MANIFEST_SHA256,
    load_manifest,
    select_rows,
    shortcut_check,
    sha256_file,
)


class FakeEncoder:
    def __init__(self) -> None:
        self.calls = []

    def encode(self, texts: list[str]) -> np.ndarray:
        self.calls.append(list(texts))
        return np.array([[len(text), text.count("!")] for text in texts], dtype=float)


class FakeProbabilityModel:
    classes_ = np.array([0, 1])

    def predict_proba(self, embeddings: np.ndarray) -> np.ndarray:
        scores = np.clip(embeddings[:, 1] / 3.0, 0.0, 1.0)
        return np.column_stack([1.0 - scores, scores])


def metadata() -> SemanticClassifierMetadata:
    return SemanticClassifierMetadata(
        classifier_type="logistic_regression",
        classifier_version="synthetic-test",
        embedding_model_id="fake-encoder",
        embedding_model_revision="test-revision",
        embedding_dim=2,
        positive_label=1,
        training_manifest_id="SYNTHETIC_TEST_FIXTURE",
        feature_normalization="fake-none",
        label_mapping={"benign": 0, "attack": 1},
        software_version="test",
        created_at=datetime.now(UTC).isoformat(),
    )


def request(text: str = "hello!!!") -> DetectionRequest:
    return DetectionRequest(
        request_id="semantic-test",
        content=DetectionContent(type="user_prompt", text=text),
    )


def test_semantic_detector_returns_raw_score_without_calibration_or_vote():
    encoder = FakeEncoder()
    classifier = LogisticRegressionSemanticClassifier(FakeProbabilityModel(), metadata())
    detector = SemanticBaselineDetector(
        SemanticConfig(
            embedding_model_id="fake-encoder",
            embedding_model_revision="test-revision",
            classifier_version="synthetic-test",
        ),
        encoder=encoder,
        classifier=classifier,
    )
    result = detector.detect(request())
    assert result.status == "success"
    assert result.raw_score == pytest.approx(1.0)
    assert result.calibrated_probability is None
    assert result.binary_vote is None
    assert result.semantic_features.embedding_dim == 2
    assert result.features is None
    assert encoder.calls == [["hello!!!"]]


def test_semantic_detector_reports_untrained_head_without_guessing_score():
    detector = SemanticBaselineDetector(
        SemanticConfig(embedding_model_id="fake-encoder", embedding_model_revision="test-revision"),
        encoder=FakeEncoder(),
        classifier=None,
    )
    result = detector.detect(request("hello"))
    assert result.status == "not_trained"
    assert result.raw_score is None
    assert "SEMANTIC_CLASSIFIER_NOT_TRAINED" in result.warnings


def test_sentence_transformer_encoder_fails_explicitly_without_hashing_fallback(monkeypatch):
    def missing_dependency(name: str):
        if name == "sentence_transformers":
            raise ImportError("missing")
        raise AssertionError(name)

    monkeypatch.setattr(
        "detection_service.app.detectors.semantic.embeddings.import_module",
        missing_dependency,
    )
    with pytest.raises(SemanticEncoderError, match="no fallback encoder is permitted"):
        SentenceTransformerEncoder(
            SemanticConfig(embedding_model_id="missing", embedding_model_revision="revision")
        )


def test_classifier_save_load_roundtrip_with_metadata(tmp_path: Path):
    classifier = LogisticRegressionSemanticClassifier(FakeProbabilityModel(), metadata())
    classifier.save(tmp_path)
    assert (tmp_path / "classifier.joblib").exists()
    assert (tmp_path / "classifier_metadata.json").exists()
    loaded = LogisticRegressionSemanticClassifier.load(tmp_path)
    scores = loaded.predict_raw(np.array([[4.0, 1.5]], dtype=float))
    assert scores[0] == pytest.approx(0.5)
    assert loaded.metadata.training_manifest_id == "SYNTHETIC_TEST_FIXTURE"


def test_trained_classifier_save_reload_and_feature_dimension_validation(tmp_path: Path):
    meta = SemanticClassifierMetadata(
        classifier_type="logistic_regression",
        classifier_version="unit-test",
        embedding_model_id="fake-encoder",
        embedding_model_revision="fake-revision",
        embedding_dim=2,
        positive_label=1,
        training_manifest_id="manifest-sha",
        feature_normalization="unit-normalized",
        label_mapping={"benign": 0, "attack": 1},
        software_version="test",
        created_at=datetime.now(UTC).isoformat(),
        default_cutpoint=0.5,
    )
    classifier = LogisticRegressionSemanticClassifier.train(
        np.array([[0.0, 0.0], [0.2, 0.1], [1.0, 1.0], [1.2, 1.1]], dtype=float),
        [0, 0, 1, 1],
        meta,
        class_weight="balanced",
        random_seed=1701,
    )
    classifier.save(tmp_path)
    loaded = LogisticRegressionSemanticClassifier.load(tmp_path)
    assert loaded.metadata.default_cutpoint == 0.5
    assert loaded.predict_raw(np.array([[1.1, 1.1]], dtype=float))[0] > 0.5
    with pytest.raises(Exception, match="embedding dimension"):
        loaded.predict_raw(np.array([[1.0, 2.0, 3.0]], dtype=float))


def test_semantic_detector_declares_development_binary_vote_only_when_cutpoint_exists():
    meta = metadata()
    meta = SemanticClassifierMetadata(
        **{**meta.__dict__, "default_cutpoint": 0.5},
    )
    detector = SemanticBaselineDetector(
        SemanticConfig(
            embedding_model_id="fake-encoder",
            embedding_model_revision="test-revision",
            classifier_version="synthetic-test",
        ),
        encoder=FakeEncoder(),
        classifier=LogisticRegressionSemanticClassifier(FakeProbabilityModel(), meta),
    )
    result = detector.detect(request("hello!!!"))
    assert result.raw_score == pytest.approx(1.0)
    assert result.binary_vote is True
    assert result.calibrated_probability is None
    assert result.metadata["cutpoint_type"] == "DEFAULT_DEVELOPMENT_CUTPOINT"


def test_development_manifest_hash_and_partition_boundaries():
    manifest_path = Path("data_governance/manifests/development_partition_manifest_v1.csv")
    assert sha256_file(manifest_path) == EXPECTED_MANIFEST_SHA256
    rows = load_manifest(manifest_path, EXPECTED_MANIFEST_SHA256)
    assert len(select_rows(rows, "BASE_TRAIN")) == 1135
    assert len(select_rows(rows, "VALIDATION")) == 233
    assert len(select_rows(rows, "CALIBRATION")) == 233
    assert {row["source_dataset"] for row in select_rows(rows, "BASE_TRAIN")} == {
        "deepset Prompt Injection",
        "Do-Not-Answer",
    }


def test_training_manifest_rejects_protected_source(tmp_path: Path):
    manifest = tmp_path / "manifest.csv"
    manifest.write_text(
        "record_id,source_dataset,canonical_label,partition\n"
        "one,XSTest,0,BASE_TRAIN\n",
        encoding="utf-8",
    )
    with pytest.raises(RuntimeError, match="non-approved sources"):
        load_manifest(manifest, sha256_file(manifest))


def test_shortcut_check_rejects_obvious_metadata_leakage():
    rows = [{"record_id": "one"}]
    with pytest.raises(RuntimeError, match="metadata leakage"):
        shortcut_check(rows, {"one": "This row says canonical_label is 1."})


def test_semantic_artifact_missing_classifier_fails_explicitly(tmp_path: Path):
    (tmp_path / "model_config.json").write_text(
        """
{
  "encoder_model": "fake",
  "encoder_local_path": "fake",
  "encoder_revision": "revision",
  "pooling": "cls_token",
  "device_policy": "cpu",
  "batch_size": 1,
  "max_sequence_length": 8,
  "normalize_embeddings": true,
  "detector_version": "dm_a_v1",
  "label_mapping": {"benign": 0, "attack": 1}
}
""",
        encoding="utf-8",
    )
    with pytest.raises(Exception, match="classifier"):
        SemanticBaselineDetector.from_artifact(tmp_path)
