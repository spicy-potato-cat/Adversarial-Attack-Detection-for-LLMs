from __future__ import annotations

import ast
import json
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

from detection_service.app.detectors.semantic.calibration import (
    CALIBRATION_VERSION,
    MANIFEST_SHA256,
    METHOD,
    SemanticCalibrationError,
    SigmoidCalibrator,
    model_binding,
)
from detection_service.app.detectors.semantic.classifier import LogisticRegressionSemanticClassifier
from detection_service.app.detectors.semantic.config import SemanticConfig
from detection_service.app.detectors.semantic.detector import SemanticBaselineDetector, SemanticDetectorError
from detection_service.app.main import create_app
from detection_service.scripts.calibrate_semantic_baseline import (
    calibration_rows,
    diagnostics,
    load_calibration_texts,
    validate_rows,
)
from detection_service.scripts.train_semantic_baseline import load_manifest
from detection_service.tests.test_semantic import FakeEncoder, FakeProbabilityModel, metadata, request


def synthetic_calibrator(tmp_path: Path) -> tuple[SigmoidCalibrator, Path]:
    model_dir = tmp_path / "model"
    model_dir.mkdir()
    classifier = LogisticRegressionSemanticClassifier(
        FakeProbabilityModel(), replace(metadata(), classifier_version="dm_a_v1", default_cutpoint=0.5)
    )
    classifier.save(model_dir)
    config = {
        "encoder_model": "fake-encoder", "encoder_revision": "test-revision", "pooling": "cls_token",
        "batch_size": 2, "max_sequence_length": 512, "normalize_embeddings": True,
        "device_policy": "cpu", "detector_version": "dm_a_v1", "label_mapping": {"benign": 0, "attack": 1},
    }
    (model_dir / "model_config.json").write_text(json.dumps(config), encoding="utf-8")
    meta = {
        "detector_id": "semantic_embedding_lr", "detector_version": "dm_a_v1",
        "calibration_version": CALIBRATION_VERSION, "calibration_method": METHOD,
        "calibration_manifest_sha256": MANIFEST_SHA256,
        "label_mapping": {"benign": 0, "attack": 1}, "frozen_model_sha256": model_binding(model_dir),
    }
    raw = np.concatenate([np.linspace(0.01, 0.45, 192), np.linspace(0.25, 0.99, 41)])
    labels = np.array([0] * 192 + [1] * 41)
    calibrator = SigmoidCalibrator.fit_mapping(raw, labels, meta)
    return calibrator, model_dir


def test_calibrator_serialization_reload_and_determinism(tmp_path):
    calibrator, model = synthetic_calibrator(tmp_path)
    output = model / "calibration"
    calibrator.save(output)
    loaded = SigmoidCalibrator.load(output, model)
    raw = np.array([0, 0.05, 0.2, 0.5, 0.8, 0.999, 1.0])
    original = raw.copy()
    first = loaded.predict(raw)
    assert np.array_equal(first, calibrator.predict(raw))
    assert np.array_equal(first, loaded.predict(raw))
    assert np.array_equal(raw, original)
    assert np.isfinite(first).all() and ((0 <= first) & (first <= 1)).all()
    assert np.all(np.diff(first) >= 0)


def test_calibrator_incompatible_model_is_rejected(tmp_path):
    calibrator, model = synthetic_calibrator(tmp_path)
    calibrator.save(model / "calibration")
    (model / "classifier.joblib").write_bytes(b"changed classifier")
    with pytest.raises(SemanticCalibrationError, match="incompatible"):
        SigmoidCalibrator.load(model / "calibration", model)


@pytest.mark.parametrize("field,value", [
    ("calibration_manifest_sha256", "wrong"), ("calibration_sample_count", 232),
    ("detector_version", "other-model"), ("calibration_method", "isotonic"),
    ("label_mapping", {"benign": 1, "attack": 0}),
])
def test_calibrator_invalid_metadata_is_rejected(tmp_path, field, value):
    calibrator, model = synthetic_calibrator(tmp_path)
    calibrator.save(model / "calibration")
    path = model / "calibration/calibration_metadata.json"
    meta = json.loads(path.read_text(encoding="utf-8"))
    meta[field] = value
    path.write_text(json.dumps(meta), encoding="utf-8")
    with pytest.raises(SemanticCalibrationError, match="invalid"):
        SigmoidCalibrator.load(path.parent, model)


def test_calibrator_missing_and_corrupted_mapping_fail_explicitly(tmp_path):
    calibrator, model = synthetic_calibrator(tmp_path)
    with pytest.raises(SemanticCalibrationError, match="unavailable"):
        SigmoidCalibrator.load(model / "calibration", model)
    calibrator.save(model / "calibration")
    (model / "calibration/calibrator.json").write_text('{"slope": 7}', encoding="utf-8")
    with pytest.raises(SemanticCalibrationError):
        SigmoidCalibrator.load(model / "calibration", model)


def test_artifact_loader_loads_calibration_and_requires_missing_mapping(tmp_path, monkeypatch):
    calibrator, model = synthetic_calibrator(tmp_path)
    monkeypatch.setattr("detection_service.app.detectors.semantic.detector.SentenceTransformerEncoder", lambda config: FakeEncoder())
    with pytest.raises(SemanticDetectorError, match="calibrator"):
        SemanticBaselineDetector.from_artifact(model, require_calibration=True)
    calibrator.save(model / "calibration")
    detector = SemanticBaselineDetector.from_artifact(model, require_calibration=True)
    result = detector.detect(request("hello!"))
    assert result.calibrated_probability is not None
    assert result.metadata["calibration_version"] == CALIBRATION_VERSION


def test_detector_and_api_preserve_raw_score_and_development_vote(tmp_path):
    calibrator, _ = synthetic_calibrator(tmp_path)
    classifier = LogisticRegressionSemanticClassifier(
        FakeProbabilityModel(), replace(metadata(), classifier_version="dm_a_v1", default_cutpoint=0.5)
    )
    config = SemanticConfig(embedding_model_id="fake-encoder", embedding_model_revision="test-revision")
    raw_detector = SemanticBaselineDetector(config, encoder=FakeEncoder(), classifier=classifier)
    calibrated_detector = SemanticBaselineDetector(config, encoder=FakeEncoder(), classifier=classifier, calibrator=calibrator)
    before = raw_detector.detect(request("hello!"))
    after = calibrated_detector.detect(request("hello!"))
    assert after.raw_score == before.raw_score
    assert after.binary_vote == before.binary_vote
    assert after.calibrated_probability == calibrator.predict([before.raw_score])[0]
    assert after.calibrated_probability != after.raw_score
    assert after.metadata["binary_vote_basis"] == "raw_score"
    assert after.latency_ms > 0
    with TestClient(create_app(detector_factory=lambda: calibrated_detector)) as client:
        response = client.post("/v1/detect/input", json={"request_id": "synthetic", "content": {"type": "user_prompt", "text": "hello!"}})
    assert response.status_code == 200
    body = response.json()["detectors"][0]
    assert body["calibrated_probability"] == after.calibrated_probability
    assert body["raw_score"] == before.raw_score


def test_manifest_integrity_count_and_calibration_membership(tmp_path):
    manifest = Path("data_governance/manifests/development_partition_manifest_v1.csv")
    rows = calibration_rows(manifest)
    assert len(rows) == 233
    assert {r["partition"] for r in rows} == {"CALIBRATION"}
    assert sum(int(r["canonical_label"]) for r in rows) == 41
    changed = tmp_path / "manifest.csv"
    changed.write_bytes(manifest.read_bytes() + b"\n")
    with pytest.raises(RuntimeError, match="integrity"):
        calibration_rows(changed)


def all_manifest_rows():
    return load_manifest(Path("data_governance/manifests/development_partition_manifest_v1.csv"), MANIFEST_SHA256)


def test_cross_partition_lineage_is_rejected():
    rows = all_manifest_rows()
    validation = next(r for r in rows if r["partition"] == "VALIDATION")
    calibration = next(r for r in rows if r["partition"] == "CALIBRATION")
    for key in ("normalized_hash", "lineage_group_id"):
        validation[key] = calibration[key]
    with pytest.raises(RuntimeError, match="crosses partition"):
        validate_rows(rows)


def test_protected_source_and_bad_label_mapping_are_rejected():
    rows = all_manifest_rows()
    rows[0]["source_dataset"] = "XSTest"
    with pytest.raises(RuntimeError, match="protected"):
        validate_rows(rows)
    rows = all_manifest_rows()
    rows[0]["canonical_label"] = "1"
    with pytest.raises(RuntimeError, match="taxonomy"):
        validate_rows(rows)


def test_text_loader_rejects_non_calibration_rows_before_file_access(tmp_path):
    rows = all_manifest_rows()
    with pytest.raises(RuntimeError, match="CALIBRATION membership only"):
        load_calibration_texts([next(r for r in rows if r["partition"] == "VALIDATION")], tmp_path)


def test_text_loader_reads_only_approved_files_and_verifies_selected_text(monkeypatch):
    import builtins
    from detection_service.scripts.calibrate_semantic_baseline import SOURCE_FILES

    rows = calibration_rows(Path("data_governance/manifests/development_partition_manifest_v1.csv"))
    approved = {(Path.cwd() / name).resolve() for name in SOURCE_FILES.values()}
    real_open = builtins.open

    def guarded_open(file, *args, **kwargs):
        if isinstance(file, (str, Path)):
            path = Path(file).resolve()
            if "Dataset" in path.parts or "PHASE-3" in path.parts:
                assert path in approved
        return real_open(file, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", guarded_open)
    texts, hashes = load_calibration_texts(rows, Path.cwd())
    assert len(texts) == 233 and set(hashes) == set(SOURCE_FILES.values())


@pytest.mark.parametrize("values", [[-0.1], [1.1], [np.nan], [np.inf], [[0.5]]])
def test_invalid_raw_probabilities_are_rejected(tmp_path, values):
    calibrator, _ = synthetic_calibrator(tmp_path)
    with pytest.raises(SemanticCalibrationError):
        calibrator.predict(np.array(values))


def test_diagnostic_bins_include_endpoints_and_are_fit_only():
    labels = np.array([0, 1, 0, 1])
    values = np.array([0, 1, 0.5, 0.9])
    result = diagnostics(labels, values, values)
    assert result["scope"] == "CALIBRATION-FIT DIAGNOSTICS ONLY"
    assert sum(b["count"] for b in result["raw"]["bins"]) == 4
    assert result["raw"]["bins"][0]["count"] == 1
    assert result["raw"]["bins"][9]["count"] == 2


def test_calibration_runner_never_calls_classifier_training_or_validation_evaluation():
    path = Path("detection_service/scripts/calibrate_semantic_baseline.py")
    tree = ast.parse(path.read_text(encoding="utf-8"))
    calls = [n.func for n in ast.walk(tree) if isinstance(n, ast.Call)]
    assert not any(isinstance(n, ast.Attribute) and n.attr in {"fit", "train", "evaluate_validation"} for n in calls)
    assert not any(isinstance(n, ast.Name) and n.id == "evaluate_validation" for n in calls)
    encoder_source = Path("detection_service/app/detectors/semantic/embeddings.py").read_text(encoding="utf-8")
    assert "HashingVectorizer" not in encoder_source and "TfidfVectorizer" not in encoder_source


def test_default_service_wiring_requires_authoritative_calibrator(tmp_path, monkeypatch):
    from detection_service.app.core.settings import Settings
    from detection_service.app.detectors.statistical.config import PerplexityConfig
    from detection_service.app.main import _default_detectors

    calibrator, model = synthetic_calibrator(tmp_path)
    monkeypatch.setattr("detection_service.app.main.StatisticalPerplexityDetector", lambda config: object())
    monkeypatch.setattr("detection_service.app.detectors.semantic.detector.SentenceTransformerEncoder", lambda config: FakeEncoder())
    settings = Settings(
        "test", PerplexityConfig(),
        semantic=SemanticConfig(classifier_artifact_dir=str(model)), enable_semantic_detector=True,
    )
    with pytest.raises(SemanticDetectorError, match="calibrator"):
        _default_detectors(settings)
    calibrator.save(model / "calibration")
    detectors = _default_detectors(settings)
    assert detectors[1].detect(request("hello!")).calibrated_probability is not None
