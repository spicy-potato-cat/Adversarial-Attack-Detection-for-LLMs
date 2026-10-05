"""Synthetic B2 final-package, inference and calibration isolation tests."""

import copy
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
import pytest

from detection_service.analysis import statistical_feature_ablation as features
from detection_service.app.contracts.detector_result import DetectorResult
from detection_service.app.contracts.detection_request import DetectionContent, DetectionRequest
from detection_service.app.detectors.semantic.calibration import EPSILON, METHOD, SigmoidCalibrator
from detection_service.app.detectors.statistical.config import PerplexityConfig
from detection_service.app.detectors.statistical.perplexity_engine import InferenceEvidence
from detection_service.app.detectors.statistical_v2 import B2Model, B2StatisticalDetector, load_calibration
from detection_service.app.detectors.statistical_v2 import model as constants
from detection_service.scripts import freeze_statistical_v2 as driver
from detection_service.tests.test_statistical_feature_ablation import fixture


@pytest.fixture(scope="module")
def toy():
    rows, evidence = fixture()
    refs = features.References.fit(rows, evidence)
    x = np.asarray([refs.transform(e, "B2") for e in evidence])
    fit = {}
    lr = features.fit_lr(x, np.asarray([int(r["label"]) for r in rows]), fit.update)
    payload = {"classes": [0, 1], "recipe": driver.prior.core.estimator("S0").get_params(),
               "coefficients": lr.coef_.tolist(), "intercept": lr.intercept_.tolist()}
    manifest = {"detector_version": "ds_v2", "feature_schema_sha256": driver.prior.core.B2_SHA,
                "feature_names": list(features.names("B2")), "runtime_code_sha256": {}, "final_operating_point": "NOT_FROZEN"}
    return rows, evidence, x, lr, payload, refs.payload, manifest


def package(directory, toy):
    directory.mkdir()
    _, _, _, _, payload, refs, manifest = toy
    for name, value in ((constants.MODEL_FILE, payload), (constants.REFERENCE_FILE, refs),
                        (constants.MANIFEST_FILE, manifest), (constants.TRAINING_FILE, {"partition": "BASE_TRAIN"})):
        driver.write(directory / name, value)
    driver.write(directory / constants.INTEGRITY_FILE, driver.hashes(directory, constants.FROZEN_FILES[:-1]))
    return B2Model.load(directory)


def test_exact_schema_recipe_and_fixture():
    assert driver.prior.core.B2_SHA == "93d3892b158c35eccfadc27c879754db69ea5293782492ee5d4ff01a33bff983"
    assert len(features.names("B2")) == 26
    params = driver.prior.core.estimator("S0").get_params()
    assert params["max_iter"] == 20000 and params["tol"] == 1e-4 and params["solver"] == "lbfgs"
    assert params["C"] == 1 and params["penalty"] == "l2" and params["class_weight"] == "balanced"
    assert driver.file_hash(driver.ROOT / driver.baseline.MANIFEST_PATH) == driver.source.MANIFEST
    assert driver.file_hash(driver.ROOT / driver.baseline.FOLD_PATH) == driver.source.FOLDS
    driver.verify_prior()


def test_serialization_is_exact_and_never_refits(tmp_path, toy):
    rows, evidence, x, lr, *_ = toy
    model = package(tmp_path / "model", toy)
    with patch.object(features.References, "fit", side_effect=AssertionError("no refit")):
        loaded = B2Model.load(tmp_path / "model")
        assert np.array_equal(np.asarray([loaded.transform(e) for e in evidence]), x)
        assert np.array_equal(model.predict(x), lr.predict_proba(x)[:, 1])
        assert np.array_equal(model.predict(x), loaded.predict(x))
        assert loaded.references.payload["fit_training_ids"] == [r["sample_id"] for r in rows]


@pytest.mark.parametrize("partition", ["CALIBRATION", "VALIDATION", "INTERNAL_TEST", "FROZEN_EXTERNAL"])
def test_reserved_reference_fitting_forbidden(toy, partition):
    rows, evidence, *_ = toy
    rows = copy.deepcopy(rows)
    rows[0]["partition"] = partition
    with pytest.raises(ValueError, match="reserved"):
        features.References.fit(rows, evidence)


@pytest.mark.parametrize("change", ["schema", "recipe", "classes", "coefficients", "bins"])
def test_invalid_package_rejected(toy, change):
    _, _, _, _, payload, refs, manifest = copy.deepcopy(toy)
    if change == "schema":
        manifest["feature_schema_sha256"] = "wrong"
    elif change == "recipe":
        payload["recipe"]["C"] = 2
    elif change == "classes":
        payload["classes"] = [1, 0]
    elif change == "coefficients":
        payload["coefficients"] = [[0.] * 25]
    else:
        refs["bins"].pop("0")
    with pytest.raises(constants.StatisticalScorerError):
        B2Model(payload, refs, manifest)


def test_raw_score_direction(toy):
    _, _, _, _, payload, refs, manifest = copy.deepcopy(toy)
    payload["coefficients"] = [[1.] + [0.] * 25]
    payload["intercept"] = [0.]
    model = B2Model(payload, refs, manifest)
    x = np.zeros((2, 26))
    x[:, 0] = [-1, 1]
    assert model.predict(x)[0] < .5 < model.predict(x)[1]


@pytest.mark.parametrize("matrix", [np.zeros((1, 25)), np.full((1, 26), np.nan), np.full((1, 26), np.inf)])
def test_no_matrix_fallback(toy, matrix):
    _, _, _, _, payload, refs, manifest = toy
    with pytest.raises(constants.StatisticalScorerError):
        B2Model(payload, refs, manifest).predict(matrix)


def test_detector_contract_and_insufficient_input(toy):
    _, evidence, _, _, payload, refs, manifest = toy
    obs = InferenceEvidence(evidence[0]["surprisals"], 19, 18, False, 1, 1024)
    engine = SimpleNamespace(score=lambda text: obs, model=SimpleNamespace())
    extractor = SimpleNamespace(config=PerplexityConfig(), engine=engine)
    model = B2Model(payload, refs, manifest)
    detector = B2StatisticalDetector(extractor, model)
    request = DetectionRequest(request_id="synthetic", content=DetectionContent(type="user_prompt", text="Synthetic fixture."))
    with patch.object(features.References, "fit", side_effect=AssertionError("no refit")):
        result = detector.detect(request)
        assert isinstance(result, DetectorResult) and result.detector_version == "ds_v2"
        assert result.raw_score == detector.detect(request).raw_score
        assert len(result.metadata["b2_features"]) == 26 and result.calibrated_probability is None
        assert result.metadata["cutpoint_type"] == "DEVELOPMENT_DEFAULT_NOT_FINAL_OPERATING_POINT"
        assert result.metadata["final_operating_point"] == "NOT_FROZEN"
        engine.score = lambda text: InferenceEvidence([], 0, 0, False, 0, 1024)
        result = detector.detect(request)
        assert result.status == "insufficient_input" and result.raw_score is result.binary_vote is None


def test_calibration_reload_model_binding_and_ranking(tmp_path, toy):
    directory = tmp_path / "model"
    package(directory, toy)
    raw, labels = np.array([.1, .3, .6, .9]), np.array([0, 0, 1, 1])
    cal = SigmoidCalibrator.fit_mapping(raw, labels, {"partitions_fitted": ["CALIBRATION"]})
    out = tmp_path / "cal"
    out.mkdir()
    driver.write(out / constants.CAL_FILE, {"slope": cal.slope, "intercept": cal.intercept, "epsilon": EPSILON})
    driver.write(out / constants.CAL_METRICS, {})
    driver.write(out / constants.CAL_MANIFEST, {"detector_version": "ds_v2", "calibration_version": "ds_v2_cal_v1",
        "method": METHOD, "partitions_fitted": ["CALIBRATION"], "feature_schema_sha256": driver.prior.core.B2_SHA,
        "model_binding": driver.hashes(directory, constants.FROZEN_FILES)})
    driver.write(out / constants.CAL_INTEGRITY, driver.hashes(out, (constants.CAL_FILE, constants.CAL_MANIFEST, constants.CAL_METRICS)))
    loaded = load_calibration(out, directory)
    assert np.array_equal(loaded.predict(raw), cal.predict(raw)) and (np.diff(loaded.predict(raw)) > 0).all()
    with (directory / constants.MODEL_FILE).open("ab") as handle:
        handle.write(b" ")
    with pytest.raises(constants.StatisticalScorerError, match="mismatched"):
        load_calibration(out, directory)


def test_missing_artifact_has_no_fallback(tmp_path):
    with pytest.raises(constants.StatisticalScorerError, match="no fallback"):
        B2Model.load(tmp_path)
