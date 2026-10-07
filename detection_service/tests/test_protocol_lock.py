"""Preflight fixtures and temporary-copy tampering; no future experiment runs."""

from copy import deepcopy
import json
from pathlib import Path
import shutil

import pytest

from detection_service.research_protocol import protocol_lock as lock
from detection_service.research_protocol.regime import RegimeManifest, manifest_hash, experiment_id


@pytest.fixture(scope="module")
def frozen():
    return lock.build_lock()


def request(slot="r1"):
    path = lock.files.ROOT/lock.files.OUT/"fixtures/phase4"/(slot+"_manifest_v1.json")
    manifest = RegimeManifest.model_validate_json(path.read_bytes())
    return lock.ExperimentRequest(manifest=manifest,purpose="TEST_FIXTURE",
        bootstrap_unit="SAMPLE_PAIRED" if slot == "r1" else "LINEAGE_CLUSTERED")


@pytest.mark.parametrize("slot",["r1","r2_ds","r2_dmb","r2_dg","r3"])
def test_regime_preflight_fixture(slot,frozen):
    result = lock.verify_experiment_preflight(request(slot),lock_fixture=frozen)
    assert result["status"] == "PASS" and result["purpose"] == "TEST_FIXTURE"
    assert result["experiment_executed"] is False


def test_lock_deterministic_and_exact(frozen):
    assert frozen == lock.build_lock()
    assert frozen["protocol_release_id"] == "exp_protocol_001_v1"
    assert frozen["status"] == "FROZEN"
    assert frozen["primary_detector_order"] == ["D_S","D_M-B","D_G"]
    assert frozen["score_direction"] == "HIGHER_IS_MORE_ADVERSARIAL"
    assert tuple(p["threshold"] for p in frozen["thresholds"]) == lock.operational.THRESHOLDS
    assert tuple(p["threshold_id"] for p in frozen["thresholds"]) == lock.operational.IDS
    assert frozen["decision_operator"] == ">="
    assert frozen["comparator"] == "D_M-A_COMPARATOR_ONLY"
    assert frozen["manifest_hash"] == lock.digest({k:v for k,v in frozen.items() if k != "manifest_hash"})


@pytest.mark.parametrize("key",["threshold","threshold_id","detector_list","detector_order","score_direction",
    "calibrator_binding","decision_operator","metric_definitions","bootstrap_config","fit_threshold","auto_calibrate","train_detector"])
def test_runtime_overrides_rejected(key):
    payload = request().model_dump()
    payload[key] = "UNAUTHORIZED"
    with pytest.raises(ValueError): lock.ExperimentRequest.model_validate(payload)


@pytest.mark.parametrize("action",["FIT_THRESHOLD","TRAIN","CALIBRATE","DETECTOR_SELECTION","CHANGE_METRICS"])
def test_protected_policy_adaptation_rejected(action):
    payload = request().model_dump()
    payload["action"] = action
    with pytest.raises(ValueError): lock.ExperimentRequest.model_validate(payload)


@pytest.mark.parametrize("key,value",[("decision_view","EXPLICIT"),("comparison_view_id","HISTORICAL_DESCRIPTIVE_3PCT_V1"),
    ("operating_policy_sha","0"*64)])
def test_view_or_policy_override_rejected(key,value):
    payload = request().model_dump()
    payload[key] = value
    with pytest.raises(ValueError): lock.ExperimentRequest.model_validate(payload)


@pytest.mark.parametrize("slot",["r2_ds","r2_dmb","r2_dg","r3"])
def test_generated_requires_cluster(slot,frozen):
    payload = request(slot).model_dump()
    payload["bootstrap_unit"] = "SAMPLE_PAIRED"
    with pytest.raises(ValueError,match="LINEAGE_CLUSTERING"):
        lock.verify_experiment_preflight(lock.ExperimentRequest.model_validate(payload),lock_fixture=frozen)


@pytest.mark.parametrize("slot,target",[("r1","D_S"),("r2_ds",None),("r2_ds","ALL"),("r3","D_S")])
def test_wrong_target_semantics(slot,target):
    payload = request(slot).manifest.model_dump(mode="json")
    payload["samples"][0]["target_detector"] = target
    payload["experiment_id"] = experiment_id(payload)
    payload["manifest_hash"] = manifest_hash(payload)
    with pytest.raises(ValueError): RegimeManifest.model_validate_json(json.dumps(payload))


@pytest.mark.parametrize("slot",["r2_ds","r3"])
@pytest.mark.parametrize("field",["lineage_id","attack_method_revision","attack_success_definition"])
def test_targeted_provenance_required(slot,field):
    payload = request(slot).manifest.model_dump(mode="json")
    payload["samples"][0][field] = None
    payload["experiment_id"] = experiment_id(payload)
    payload["manifest_hash"] = manifest_hash(payload)
    with pytest.raises(ValueError): RegimeManifest.model_validate_json(json.dumps(payload))


@pytest.mark.parametrize("suffix",[
    "detector_set_manifest_v1.json","operating_point_manifest_v1.json","core_metrics_contract_v1.json",
    "uncertainty_contract_v1.json","cross_regime_contract_v1.json","prediction_schema_v1.json",
    "regime_contract_manifest_v1.json","r0_operational_result_bundle_v1.json",
])
def test_temporary_artifact_tamper_rejected(tmp_path,frozen,suffix):
    for path in frozen["bindings"]:
        dest = tmp_path/path
        dest.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(lock.files.ROOT/path,dest)
    matches = [p for p in frozen["bindings"] if p.endswith("/"+suffix)]
    assert len(matches) == 1
    path = tmp_path/matches[0]
    path.write_bytes(path.read_bytes()+b" ")
    with pytest.raises(ValueError,match="AUTHORITATIVE_ARTIFACT_DRIFT"):
        lock.verify_lock(tmp_path,lock_fixture=frozen)


@pytest.mark.parametrize("index",range(3))
def test_changed_threshold_in_lock_rejected(frozen,index):
    value = deepcopy(frozen)
    value["thresholds"][index]["threshold"] = 0.5
    value["manifest_hash"] = lock.digest({k:v for k,v in value.items() if k != "manifest_hash"})
    with pytest.raises(ValueError): lock.verify_lock(lock_fixture=value)


@pytest.mark.parametrize("field,value",[("primary_detector_order",["D_G","D_M-B","D_S"]),
    ("score_direction","LOWER_IS_MORE_ADVERSARIAL"),("decision_operator",">"),("comparator","PRIMARY"),
    ("uncertainty_defaults",{"replicates":50})])
def test_rehashed_semantic_tamper_rejected(frozen,field,value):
    payload = deepcopy(frozen)
    payload[field] = value
    payload["manifest_hash"] = lock.digest({k:v for k,v in payload.items() if k != "manifest_hash"})
    with pytest.raises(ValueError): lock.verify_lock(lock_fixture=payload)


def test_fixture_cannot_publish_official_result():
    with pytest.raises(ValueError,match="CANNOT_PUBLISH_REAL_RESULT"):
        lock.evaluate_official(request(),())


def test_no_fit_or_override_in_official_api():
    import inspect
    source = inspect.getsource(lock.evaluate_official)
    assert "verify_experiment_preflight(request)" in source
    assert "apply_operating_policy" in source and "align_evaluation" in source
    assert not any(k in source for k in (".fit(","fit_threshold(","auto_calibrate(","_load_live(","predict("))
    assert list(inspect.signature(lock.evaluate_official).parameters) == ["request","predictions"]
    with pytest.raises(TypeError): lock.evaluate_official(request(),(),threshold=0.5)


def test_fixture_lock_not_official_authority(frozen):
    payload = request().model_dump()
    payload["purpose"] = "OFFICIAL_EVALUATION"
    with pytest.raises(ValueError,match="NOT_OFFICIAL_AUTHORITY"):
        lock.verify_experiment_preflight(lock.ExperimentRequest.model_validate(payload),lock_fixture=frozen)
