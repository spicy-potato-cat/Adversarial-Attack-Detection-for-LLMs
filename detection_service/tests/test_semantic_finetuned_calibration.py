from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

from detection_service.app.detectors.semantic.calibration import MANIFEST_SHA256, SemanticCalibrationError, file_sha256
from detection_service.app.detectors.semantic_finetuned.calibration import (
    CALIBRATION_VERSION, INPUT_SCORE, METHOD, FineTunedCalibrator, model_binding,
)
from detection_service.app.detectors.semantic_finetuned.detector import FineTunedDetectorError, FineTunedSemanticDetector
from detection_service.app.main import create_app
from detection_service.scripts import calibrate_semantic_finetuned as script
from detection_service.tests.test_semantic_finetuned import recipe, request, save_fixture, tiny_components


def mapping(directory):
    raw = np.linspace(.02, .98, 233)
    labels = np.array([0] * 192 + [1] * 41)
    metadata = {
        "schema_version": "1.0", "detector_id": "semantic_finetuned", "detector_version": "dm_b_v1",
        "calibration_version": CALIBRATION_VERSION, "calibration_method": METHOD,
        "input_score_definition": INPUT_SCORE, "calibration_manifest_sha256": MANIFEST_SHA256,
        "label_mapping": {"benign": 0, "attack": 1}, "partitions_fitted": ["CALIBRATION"],
        "transformer_retrained": False, "validation_consumed": False, "protected_data_consumed": False,
        "frozen_model_sha256": model_binding(directory),
    }
    return FineTunedCalibrator.fit_mapping(raw, labels, metadata)


@pytest.fixture
def artifact(tmp_path, tiny_components):
    tokenizer, model = tiny_components
    directory = tmp_path / "model"
    save_fixture(directory, recipe(), tokenizer, model)
    return directory, tokenizer, model


def test_calibration_artifact_schema_reload_bounds_monotonic_determinism(artifact):
    directory, _, _ = artifact
    calibrator = mapping(directory)
    calibrator.save(directory / "calibration")
    loaded = FineTunedCalibrator.load(directory / "calibration", directory)
    raw = np.array([0., .01, .25, .5, .75, .99, 1.])
    probabilities = loaded.predict(raw)
    assert np.array_equal(probabilities, calibrator.predict(raw))
    assert np.array_equal(probabilities, loaded.predict(raw))
    assert np.isfinite(probabilities).all() and ((probabilities >= 0) & (probabilities <= 1)).all()
    assert (np.diff(probabilities) >= 0).all()
    assert loaded.metadata["calibration_sample_count"] == 233
    assert loaded.metadata["calibration_positive_count"] == 41
    assert loaded.metadata["calibration_negative_count"] == 192
    assert loaded.metadata["calibration_version"] == CALIBRATION_VERSION
    payload = json.loads((directory / "calibration/calibrator.json").read_text())
    assert set(payload) == {"slope", "intercept", "epsilon"}


def test_calibrated_detector_preserves_raw_vote_weights_and_api(artifact, monkeypatch):
    import torch
    directory, tokenizer, model = artifact
    before = {str(p): file_sha256(p) for p in directory.rglob('*') if p.is_file()}
    raw_detector = FineTunedSemanticDetector(recipe(), tokenizer, model)
    original = raw_detector.detect(request())
    mapping(directory).save(directory / "calibration")
    monkeypatch.setattr(torch.Tensor, "backward", lambda *a, **k: pytest.fail("backward forbidden"))
    monkeypatch.setattr(torch.optim.AdamW, "step", lambda *a, **k: pytest.fail("optimizer step forbidden"))
    loaded = FineTunedSemanticDetector.from_artifact(directory, require_calibration=True)
    result = loaded.detect(request())
    assert result.raw_score == original.raw_score and result.binary_vote == original.binary_vote
    assert result.calibrated_probability is not None
    assert result.calibrated_probability == loaded.detect(request()).calibrated_probability
    assert result.detector_version == "dm_b_v1" and result.metadata["calibration_version"] == CALIBRATION_VERSION
    assert all(file_sha256(Path(p)) == digest for p, digest in before.items())
    with TestClient(create_app(detector_factory=lambda: loaded)) as client:
        response = client.post('/v1/detect/input', json=request().model_dump(mode='json'))
    assert response.status_code == 200
    output = response.json()['detectors'][0]
    assert output['calibrated_probability'] == result.calibrated_probability
    assert output['raw_score'] == original.raw_score and output['binary_vote'] == original.binary_vote


def test_missing_calibration_explicit_optional_vs_required(artifact):
    directory, _, _ = artifact
    assert FineTunedSemanticDetector.from_artifact(directory).detect(request()).calibrated_probability is None
    with pytest.raises(FineTunedDetectorError, match='no fallback'):
        FineTunedSemanticDetector.from_artifact(directory, require_calibration=True)


@pytest.mark.parametrize('tamper', ['payload', 'payload_array', 'metadata_array', 'identity', 'method', 'manifest', 'model', 'counts', 'input', 'validation', 'protected', 'missing_metadata'])
def test_invalid_calibration_never_substitutes_or_falls_back(artifact, tamper):
    directory, _, _ = artifact
    output = directory / 'calibration'
    mapping(directory).save(output)
    metadata_file = output / 'calibration_metadata.json'
    metadata = json.loads(metadata_file.read_text())
    if tamper == 'payload':
        (output / 'calibrator.json').write_text('{broken')
    elif tamper == 'payload_array':
        (output / 'calibrator.json').write_text('[]')
    elif tamper == 'metadata_array':
        metadata_file.write_text('[]')
    elif tamper == 'missing_metadata':
        metadata_file.unlink()
    else:
        key, value = {
            'identity': ('detector_version', 'dm_a_v1'), 'method': ('calibration_method', 'identity'),
            'manifest': ('calibration_manifest_sha256', 'wrong'), 'model': ('frozen_model_sha256', {}),
            'counts': ('calibration_sample_count', 232), 'input': ('input_score_definition', 'binary_vote'),
            'validation': ('validation_consumed', True), 'protected': ('protected_data_consumed', True),
        }[tamper]
        metadata[key] = value
        metadata_file.write_text(json.dumps(metadata))
    with pytest.raises(SemanticCalibrationError, match='no fallback'):
        FineTunedCalibrator.load(output, directory)
    with pytest.raises(FineTunedDetectorError, match='no fallback'):
        FineTunedSemanticDetector.from_artifact(directory)


def test_model_change_invalidates_calibration(artifact):
    directory, _, _ = artifact
    mapping(directory).save(directory / 'calibration')
    (directory / 'transformer/config.json').write_text('{}')
    with pytest.raises(SemanticCalibrationError):
        FineTunedCalibrator.load(directory / 'calibration', directory)


@pytest.mark.parametrize('raw', [np.array([float('nan')]), np.array([-1.]), np.array([2.])])
def test_invalid_raw_probabilities_rejected(raw):
    with pytest.raises(SemanticCalibrationError):
        FineTunedCalibrator(1., 0., {}).predict(raw)


def test_calibration_partition_count_and_manifest_integrity():
    rows = script.calibration_rows(script.MANIFEST)
    assert len(rows) == 233 and sum(int(r['canonical_label']) for r in rows) == 41
    assert all(r['partition'] == 'CALIBRATION' for r in rows)


def test_manifest_mismatch_stops_before_text_access(tmp_path, monkeypatch):
    changed = tmp_path / 'manifest.csv'
    changed.write_text('partition\nCALIBRATION\n')
    monkeypatch.setattr(script, 'load_calibration_texts', lambda *a: pytest.fail('source access forbidden'))
    with pytest.raises(RuntimeError, match='integrity'):
        script.calibration_rows(changed)


def test_other_partition_rows_not_validated_or_processed(tmp_path, monkeypatch):
    manifest = tmp_path / 'manifest.csv'
    with manifest.open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=['partition', 'canonical_label'])
        writer.writeheader()
        writer.writerow({'partition': 'VALIDATION', 'canonical_label': 'must_not_inspect'})
        writer.writerow({'partition': 'BASE_TRAIN', 'canonical_label': 'must_not_inspect'})
        for i in range(233):
            writer.writerow({'partition': 'CALIBRATION', 'canonical_label': str(int(i < 41))})
    monkeypatch.setattr(script, 'file_sha256', lambda _: MANIFEST_SHA256)
    captured = []
    monkeypatch.setattr(script, 'validate_rows', lambda rows: captured.extend(rows))
    assert len(script.calibration_rows(manifest)) == 233
    assert all(r['partition'] == 'CALIBRATION' for r in captured)


@pytest.mark.parametrize('partition', ['BASE_TRAIN', 'VALIDATION', 'FROZEN_EXTERNAL', 'INTERNAL_TEST'])
def test_non_calibration_features_rejected_before_source_access(tmp_path, partition):
    with pytest.raises(RuntimeError, match='CALIBRATION membership only'):
        script.load_calibration_texts([{'partition': partition}], tmp_path)


def test_authoritative_fit_refuses_existing_artifact(tmp_path, monkeypatch):
    (tmp_path / 'calibration').mkdir()
    monkeypatch.setattr(script, 'MODEL', tmp_path)
    monkeypatch.setattr(script, 'calibration_rows', lambda _: pytest.fail('must refuse before data access'))
    with pytest.raises(RuntimeError, match='refusing overwrite'):
        script.execute()


def test_selected_calibration_texts_only_and_approved_source_access(monkeypatch):
    import pyarrow.parquet as pq
    import detection_service.scripts.calibrate_semantic_baseline as loader
    rows = script.calibration_rows(script.MANIFEST)
    approved = {(Path.cwd() / name).resolve() for name in loader.SOURCE_FILES.values()}
    allowed = {}
    for row in rows:
        artifact, locator = row['canonical_text_reference'].split('::')
        path = (Path.cwd() / loader.SOURCE_FILES[artifact]).resolve()
        allowed.setdefault(path, set()).add(int(locator.split(':')[1]) - 1)
    real_read = pq.read_table
    real_hash = loader.file_sha256

    def guarded_hash(path):
        assert Path(path).resolve() in approved
        return real_hash(path)

    def guarded_read(path, **kwargs):
        path = Path(path).resolve()
        assert path in approved and kwargs['columns'] == ['text', 'label']
        table = real_read(path, **kwargs)

        class SelectedColumn:
            def __init__(self, name):
                self.name = name

            def __getitem__(self, index):
                assert index in allowed[path], 'non-CALIBRATION scalar access forbidden'
                return table[self.name][index]

        class SelectedTable:
            def __getitem__(self, name):
                return SelectedColumn(name)

        return SelectedTable()

    monkeypatch.setattr(loader, 'file_sha256', guarded_hash)
    monkeypatch.setattr(pq, 'read_table', guarded_read)
    texts, hashes = script.load_calibration_texts(rows, Path.cwd())
    assert len(texts) == 233 and set(hashes) == set(loader.SOURCE_FILES.values())


def test_calibration_failure_is_explicit_api_error(artifact, monkeypatch):
    directory, tokenizer, model = artifact
    calibrator = mapping(directory)
    detector = FineTunedSemanticDetector(recipe(), tokenizer, model, calibrator)
    monkeypatch.setattr(calibrator, 'predict', lambda _: np.array([float('nan')]))
    with TestClient(create_app(detector_factory=lambda: detector)) as client:
        response = client.post('/v1/detect/input', json=request().model_dump(mode='json'))
    assert response.status_code == 503
    assert response.json()['detail']['code'] == 'SEMANTIC_DETECTOR_UNAVAILABLE'
