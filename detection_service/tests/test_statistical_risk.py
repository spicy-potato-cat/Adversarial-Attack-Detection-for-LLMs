import json
from pathlib import Path
from unittest.mock import patch

import joblib
import numpy as np
import pytest
from fastapi.testclient import TestClient

from detection_service.app.contracts.detection_request import DetectionContent, DetectionRequest
from detection_service.app.contracts.detector_result import DetectorResult
from detection_service.app.core.settings import Settings
from detection_service.app.detectors.semantic.calibration import SigmoidCalibrator, file_sha256
from detection_service.app.detectors.statistical.config import PerplexityConfig
from detection_service.app.detectors.statistical.perplexity_detector import StatisticalPerplexityDetector
from detection_service.app.detectors.statistical.perplexity_engine import PerplexityEngine
from detection_service.app.detectors.statistical_risk import ScoredStatisticalDetector, StatisticalScorer, StatisticalScorerError
from detection_service.app.detectors.statistical_risk.schema import FEATURE_NAMES, FEATURE_SCHEMA, json_bytes, schema_hash, feature_vector
from detection_service.app.detectors.statistical_risk.scorer import fit_calibrator, load_calibrator
from detection_service.app.main import create_app, _default_detectors
from detection_service.scripts.export_features import FIELDNAMES
from detection_service.scripts.train_statistical_risk import selected_rows, write, SCORER_FILES, RECIPE, CALIBRATION_RECIPE
from detection_service.tests.fakes import CharacterTokenizer, DeterministicCausalModel


def rows(partition, count=20):
    return [{"partition": partition, "canonical_label": str(i % 2)} for i in range(count)]


def matrix(count=20):
    return np.asarray([[float((i % 2) * 2 + i / count)] * 10 for i in range(count)])


def request(text):
    return DetectionRequest(request_id="synthetic", content=DetectionContent(type="user_prompt", text=text))


@pytest.fixture
def extractor():
    cfg = PerplexityConfig(model_id="test", model_revision="fixture", tokenizer_id="test",
                          max_analysis_tokens=200, window_size=8, window_stride=4)
    engine = PerplexityEngine(cfg, CharacterTokenizer(64), DeterministicCausalModel(64))
    return StatisticalPerplexityDetector(cfg, engine)


@pytest.fixture
def artifact(tmp_path):
    scorer = StatisticalScorer.fit(matrix(), rows("BASE_TRAIN"))
    joblib.dump(scorer.model, tmp_path / "scorer.joblib")
    cfg = {"detector_id": "statistical_perplexity", "detector_version": "ds_v1",
           "scorer_recipe": RECIPE, "feature_schema_sha256": schema_hash()}
    write(tmp_path / "model_config.json", cfg)
    write(tmp_path / "feature_schema.json", FEATURE_SCHEMA)
    write(tmp_path / "training_metadata.json", {"partitions_fitted": ["BASE_TRAIN"]})
    write(tmp_path / "integrity_manifest.json", {n: file_sha256(tmp_path / n) for n in SCORER_FILES})
    caldir = tmp_path / "calibration"
    cal = fit_calibrator(scorer.predict(matrix()), rows("CALIBRATION"), {
        "detector_version": "ds_v1", "calibration_version": "ds_v1_cal_v1",
        "calibration_method": "platt_sigmoid_on_lr_log_odds", "partitions_fitted": ["CALIBRATION"],
        "feature_schema_sha256": schema_hash(),
        "frozen_scorer_sha256": {n: file_sha256(tmp_path / n) for n in (*SCORER_FILES, "integrity_manifest.json")},
    })
    cal.save(caldir)
    write(caldir / "calibration_config.json", CALIBRATION_RECIPE)
    write(caldir / "integrity_manifest.json", {n: file_sha256(caldir / n) for n in ("calibrator.json", "calibration_metadata.json", "calibration_config.json")})
    return tmp_path, scorer, cal


def test_feature_schema_stable_export_order_and_hash():
    assert list(FEATURE_NAMES) == FIELDNAMES[3:13]
    assert len(FEATURE_NAMES) == 10
    import hashlib
    assert schema_hash() == hashlib.sha256(json_bytes(FEATURE_SCHEMA)).hexdigest()
    assert "identity" in FEATURE_SCHEMA["normalization"]


def test_feature_values_and_compatibility_aliases_not_modified(extractor):
    result = extractor.detect(request("hello synthetic note"))
    vector = feature_vector(result)
    assert vector.tolist() == [getattr(result.features, name) for name in FEATURE_NAMES]
    assert vector[0] == vector[6] and vector[1] == vector[2]
    assert np.array_equal(vector, feature_vector(extractor.detect(request("hello synthetic note"))))


@pytest.mark.parametrize("value", [None, float("nan"), float("inf")])
def test_invalid_features_stop_without_imputation(extractor, value):
    result = extractor.detect(request("synthetic note"))
    result.features.whole_prompt_nll = value
    with pytest.raises(ValueError):
        feature_vector(result)


def test_scorer_training_reproducibility_convergence_and_orientation():
    first = StatisticalScorer.fit(matrix(), rows("BASE_TRAIN"))
    second = StatisticalScorer.fit(matrix(), rows("BASE_TRAIN"))
    assert np.array_equal(first.model.coef_, second.model.coef_)
    assert np.array_equal(first.model.intercept_, second.model.intercept_)
    assert first.model.coef_.shape == (1, 10) and max(first.model.n_iter_) < 1000
    scores = first.predict(matrix())
    assert np.isfinite(scores).all() and ((scores >= 0) & (scores <= 1)).all()
    assert scores[1] > scores[0]  # Class-1 probability, not a perplexity threshold.


@pytest.mark.parametrize("partition", ["CALIBRATION", "VALIDATION", "INTERNAL_TEST", "FROZEN_EXTERNAL", "R0"])
def test_scorer_fit_base_train_only(partition):
    with pytest.raises(StatisticalScorerError, match="BASE_TRAIN"):
        StatisticalScorer.fit(matrix(), rows(partition))


@pytest.mark.parametrize("partition", ["BASE_TRAIN", "VALIDATION", "INTERNAL_TEST", "R1"])
def test_calibrator_fit_calibration_only(partition):
    with pytest.raises(StatisticalScorerError, match="CALIBRATION"):
        fit_calibrator(np.linspace(.1, .9, 20), rows(partition), {})


@pytest.mark.parametrize("value", [float("nan"), float("inf")])
def test_nonfinite_matrix_rejected(value):
    values = matrix()
    values[0, 0] = value
    with pytest.raises(StatisticalScorerError):
        StatisticalScorer.fit(values, rows("BASE_TRAIN"))


def test_nonconvergence_is_stop(monkeypatch):
    from sklearn.exceptions import ConvergenceWarning
    def fail(*args, **kwargs):
        raise ConvergenceWarning("synthetic failure")
    monkeypatch.setattr("sklearn.linear_model.LogisticRegression.fit", fail)
    with pytest.raises(StatisticalScorerError, match="converge"):
        StatisticalScorer.fit(matrix(), rows("BASE_TRAIN"))


def test_scorer_and_calibrator_save_reload_deterministic(artifact):
    directory, scorer, cal = artifact
    loaded, _ = StatisticalScorer.load(directory)
    calibration = load_calibrator(directory / "calibration", directory)
    before, after = scorer.predict(matrix()), loaded.predict(matrix())
    assert np.array_equal(before, after)
    assert np.array_equal(cal.predict(before), calibration.predict(after))
    assert ((calibration.predict(after) >= 0) & (calibration.predict(after) <= 1)).all()


@pytest.mark.parametrize("name", ["scorer.joblib", "feature_schema.json", "model_config.json"])
def test_missing_or_corrupt_scorer_no_fallback(artifact, name):
    directory, _, _ = artifact
    (directory / name).write_bytes(b"corrupted")
    with pytest.raises(StatisticalScorerError):
        StatisticalScorer.load(directory)


def test_missing_scorer_explicit(tmp_path):
    with pytest.raises(StatisticalScorerError):
        StatisticalScorer.load(tmp_path)


@pytest.mark.parametrize("name", ["calibrator.json", "calibration_metadata.json", "integrity_manifest.json"])
def test_missing_or_corrupt_calibrator_explicit(artifact, name):
    directory, _, _ = artifact
    (directory / "calibration" / name).write_bytes(b"corrupted")
    with pytest.raises(StatisticalScorerError):
        load_calibrator(directory / "calibration", directory)


def test_calibration_bound_to_exact_scorer(artifact):
    directory, _, _ = artifact
    (directory / "scorer.joblib").write_bytes(b"different")
    with pytest.raises(StatisticalScorerError):
        load_calibrator(directory / "calibration", directory)


def test_detector_schema_vote_evidence_reuse_and_no_runtime_fit(extractor, artifact):
    _, scorer, cal = artifact
    det = ScoredStatisticalDetector(extractor, scorer, cal)
    identity = (id(det.extractor.engine.model), id(det.scorer), id(det.calibrator))
    with patch.object(StatisticalScorer, "fit", side_effect=AssertionError("runtime fitting forbidden")), \
         patch.object(SigmoidCalibrator, "fit_mapping", side_effect=AssertionError("runtime calibration forbidden")):
        one, two = det.detect(request("hello note")), det.detect(request("hello note"))
    assert one.detector_version == "ds_v1" and one.detector_id == "statistical_perplexity"
    assert one.raw_score == two.raw_score and one.calibrated_probability == two.calibrated_probability
    assert one.binary_vote == (one.calibrated_probability >= .5)
    assert one.metadata["binary_vote_basis"] == "calibrated_probability"
    assert one.features == extractor.detect(request("hello note")).features
    assert one.latency_ms > 0 and one.input_coverage == two.input_coverage
    assert identity == (id(det.extractor.engine.model), id(det.scorer), id(det.calibrator))
    DetectorResult.model_validate_json(one.model_dump_json())


def test_calibrated_not_raw_vote_rule(extractor, artifact):
    _, scorer, cal = artifact
    with patch.object(scorer, "predict", return_value=np.array([.8])), patch.object(cal, "predict", return_value=np.array([.2])):
        result = ScoredStatisticalDetector(extractor, scorer, cal).detect(request("hello note"))
    assert result.raw_score == .8 and result.calibrated_probability == .2 and result.binary_vote is False


def test_single_token_explicitly_insufficient_not_fake_vote(extractor, artifact):
    _, scorer, cal = artifact
    result = ScoredStatisticalDetector(extractor, scorer, cal).detect(request("x"))
    assert result.status == "insufficient_input" and result.detector_version == "ds_v1"
    assert result.raw_score is result.calibrated_probability is result.binary_vote is None


@pytest.mark.parametrize("text", ["Unicode caf\u00e9 \u4f60\u597d", "hello note " * 100])
def test_long_unicode_extractor_and_coverage_preserved(extractor, artifact, text):
    _, scorer, cal = artifact
    legacy = extractor.detect(request(text))
    scored = ScoredStatisticalDetector(extractor, scorer, cal).detect(request(text))
    assert scored.features == legacy.features and scored.input_coverage == legacy.input_coverage
    if len(text) > 200:
        assert scored.input_coverage.truncated and scored.input_coverage.tokens_analyzed == 199


def test_scorer_and_calibrator_required(extractor, artifact):
    _, scorer, cal = artifact
    with pytest.raises(StatisticalScorerError):
        ScoredStatisticalDetector(extractor, None, cal)
    with pytest.raises(StatisticalScorerError):
        ScoredStatisticalDetector(extractor, scorer, None)


def test_api_smoke_and_structured_scoring_failure(extractor, artifact):
    _, scorer, cal = artifact
    det = ScoredStatisticalDetector(extractor, scorer, cal)
    with TestClient(create_app(detector_factory=lambda: det)) as client:
        payload = {"request_id": "api", "content": {"type": "user_prompt", "text": "synthetic note"}}
        response = client.post("/v1/detect/input", json=payload)
        assert response.status_code == 200 and response.json()["detectors"][0]["detector_version"] == "ds_v1"
        with patch.object(scorer, "predict", side_effect=StatisticalScorerError("private internal detail")):
            failure = client.post("/v1/detect/input", json=payload)
        assert failure.status_code == 503 and "private internal" not in failure.text
        assert failure.json()["detail"]["code"] == "STATISTICAL_SCORER_UNAVAILABLE"


def test_settings_default_factory_requires_scored_artifacts(monkeypatch, tmp_path):
    monkeypatch.setenv("STATISTICAL_MODEL_DIR", str(tmp_path / "missing"))
    settings = Settings.from_env()
    assert settings.statistical_model_dir == str(tmp_path / "missing")
    with pytest.raises(StatisticalScorerError):
        _default_detectors(settings)


def test_manifest_drift_rejected_before_data_access(tmp_path):
    fake = tmp_path / "manifest.csv"
    fake.write_text("partition\nBASE_TRAIN\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="manifest integrity"):
        selected_rows(fake, "BASE_TRAIN")


@pytest.mark.parametrize("partition", ["FROZEN_EXTERNAL", "INTERNAL_TEST", "R2"])
def test_protected_partition_rejected_before_manifest_access(tmp_path, partition):
    with pytest.raises(RuntimeError, match="Protected"):
        selected_rows(tmp_path / "nonexistent", partition)


def test_protected_source_metadata_rejected_before_text_loading():
    from detection_service.scripts.calibrate_semantic_baseline import validate_rows
    with pytest.raises(RuntimeError, match="protected or non-approved"):
        validate_rows([{"source_dataset": "XSTest"}])


def test_validation_exactly_once_and_postfreeze_gate(tmp_path, monkeypatch):
    from detection_service.scripts import train_statistical_risk as runner
    monkeypatch.setattr(runner, "MODEL", tmp_path)
    write(tmp_path / "validation_started.json", {"already_started": True})
    with pytest.raises(RuntimeError, match="exactly-once"):
        runner.validate()


def test_no_existing_extractor_source_edit():
    root = Path(__file__).resolve().parents[2]
    metadata = json.loads((root / "artifacts/models/dm_b_v1/calibration/calibration_metadata.json").read_text(encoding="utf-8"))
    names = [n for n in metadata["preserved_files_sha256"] if n.startswith("detection_service/app/detectors/statistical/")]
    assert len(names) == 5
    assert all(file_sha256(root / name) == metadata["preserved_files_sha256"][name] for name in names)
