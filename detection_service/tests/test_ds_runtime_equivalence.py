"""Runtime binding plumbing only; authoritative real-LM equivalence is a separate gate."""

from pathlib import Path
from types import SimpleNamespace

import pytest

from detection_service.research_protocol import ds_equivalence as equivalence
from detection_service.research_protocol import ds_runtime as runtime
from detection_service.research_protocol.adapters import DetectorAdapter


def test_canonical_prediction_implementation_unchanged():
    assert runtime.FrozenDSAdapter.predict is DetectorAdapter.predict
    assert runtime.FrozenDSAdapter.validate_prediction_record is DetectorAdapter.validate_prediction_record
    assert not (runtime.files.ROOT/"detection_service/app/detectors/statistical_v2/detector.py").exists()


def test_archived_runtime_hash_and_git_provenance():
    identity = runtime.FrozenDSAdapter()._identity
    assert identity["implementation_revision"] == "e6b6a2af2a78e2a31aae6d9377378993f678b073"
    assert runtime.files.sha(runtime.files.ROOT/identity["implementation_path"]) == identity["implementation_sha256"]
    assert runtime.files.sha(runtime.files.ROOT/identity["model_artifact_path"]) == "c5e754dc8b6e88b7437e4b81016e8f8ec23d018607d4f4e78906212b2a561157"


def test_archived_package_is_exact_source_not_new_extractor():
    identity = runtime.FrozenDSAdapter()._identity
    module = runtime.archived_package(identity)
    assert Path(module.__file__).resolve().parent == (runtime.files.ROOT/identity["implementation_path"]).parent
    assert module.B2StatisticalDetector.detector_version == "ds_v2"


@pytest.mark.parametrize("raw,calibrated",[(.01,.1),(.99,.9),(.5,.5)])
def test_scores_and_native_votes_match(raw,calibrated):
    result = SimpleNamespace(status="OK",error_code=None,raw_score=raw,calibrated_score=calibrated,native_binary_prediction=int(calibrated >= .5))
    assert equivalence.compare_scores(result,raw,calibrated) == (0.,0.)


@pytest.mark.parametrize("field,value,reason",[("raw_score",.7,"SCORE_EQUIVALENCE"),
    ("calibrated_score",.6,"SCORE_EQUIVALENCE"),("native_binary_prediction",1,"NATIVE_DECISION"),
    ("status","UNAVAILABLE","LIVE_NON_OK")])
def test_equivalence_refuses_mismatch(field,value,reason):
    result = SimpleNamespace(status="OK",error_code="fixture",raw_score=.1,calibrated_score=.2,native_binary_prediction=0)
    setattr(result,field,value)
    with pytest.raises(ValueError,match=reason): equivalence.compare_scores(result,.1,.2)


def test_frozen_lock_remains_valid():
    assert runtime.protocol_lock.verify_lock()["protocol_release_id"] == "exp_protocol_001_v1"


def test_long_input_is_accepted_historical_recipe_not_r1():
    text,golden,authority = equivalence.accepted_long_input()
    assert len(text) == golden["metadata"]["character_length"] == 31500
    assert golden["input_coverage"]["input_tokens"] == 4502
    assert golden["input_coverage"]["truncated"] is True
    assert authority["source_commit"] == runtime.files.BASE


def test_historical_membership_and_complete_source_hashes():
    population,authority = equivalence.historical_inputs()
    assert authority["calibration_rows"] == 233
    assert len(authority["source_artifact_sha256"]) == 3
    assert len(population) == 233 + authority["base_train_rows"]
    assert {item["row"]["partition"] for item in population} == {"CALIBRATION","BASE_TRAIN"}
    assert not any(item["row"]["partition"].startswith("R1") for item in population)
