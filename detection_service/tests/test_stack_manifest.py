"""Metadata-only stack verification: no detector imports, prompts or dataset reads."""

import copy
import json
from pathlib import Path

import pytest

from detection_service import stack_manifest as stack


@pytest.fixture(scope="module")
def manifest():
    return stack.build_manifest()


def test_real_accepted_artifact_integrity(manifest):
    report = stack.verify_manifest(manifest)
    assert report["status"] == "PASS" and report["original_baseline_hash_checks"] == 96
    assert report["artifact_hash_checks"] >= 128
    assert not report["datasets_accessed"] and not report["prompts_scored"] and not report["models_deserialized"]


def test_exact_identities_calibration_and_exclusion(manifest):
    ds, dm, dg = manifest["detectors"]
    assert ds["detector_id"] == "statistical" and ds["runtime_detector_id"] == "statistical_perplexity"
    assert ds["model_artifacts"][stack.DS + "/ds_v2_model.json"] == stack.DS_BINDING["ds_v2_model.json"]
    assert ds["feature_schema_sha256"] == stack.B2_SHA and ds["feature_count"] == 26
    assert ds["calibration"]["artifact_sha256"] == stack.DS_CAL_SHA
    assert dm["model_artifacts"][stack.DM + "/transformer/model.safetensors"] == "0bb192d2c468530479fa8ec0786f35d8bf5a8287e4ee401a953292d221736844"
    assert dm["calibration"]["artifact_sha256"] == "7af044ff8e0e29020450bffa93f92c973da4cc4a4888067d88938eefbb2566b9"
    assert dg["model_revision"] == stack.DG_REV and dg["calibration"]["state"] == "NONE"
    assert [d["calibration"]["version"] for d in manifest["detectors"]] == ["ds_v2_cal_v1", "dm_b_v1_cal_v1", None]
    assert manifest["comparators"][0]["primary_member"] is False


def test_canonical_hash_is_key_order_and_format_independent(manifest):
    reordered = dict(reversed(list(manifest.items())))
    assert stack.canonical_sha256(reordered) == stack.canonical_sha256(manifest)
    assert stack.canonical_sha256(json.loads(json.dumps(manifest, indent=4))) == stack.canonical_sha256(manifest)
    assert not stack.canonical_bytes(manifest).endswith(b"\n")


@pytest.mark.parametrize("change", ["order", "duplicate", "version", "direction", "threshold", "schema", "model_hash",
    "calibration_hash", "binding", "guard_revision", "add_comparator", "promote_comparator", "default_vote",
    "cross_detector_input", "tokenizer", "ensemble", "fallback"])
def test_manifest_drift_rejected(manifest, change, monkeypatch):
    edited = copy.deepcopy(manifest)
    ds, dm, dg = edited["detectors"]
    if change == "order": edited["detector_order"].reverse()
    elif change == "duplicate": dm["detector_id"] = ds["detector_id"]
    elif change == "version": ds["detector_version"] = "ds_v1"
    elif change == "direction": dm["score_direction"] = "lower = more adversarial"
    elif change == "threshold": ds["final_operating_threshold"] = 0.5
    elif change == "schema": ds["feature_schema_sha256"] = "0" * 64
    elif change == "model_hash": dm["model_artifacts"][stack.DM + "/transformer/model.safetensors"] = "0" * 64
    elif change == "calibration_hash": ds["calibration"]["artifact_sha256"] = "0" * 64
    elif change == "binding": dm["calibration"]["model_binding"]["model_config.json"] = "0" * 64
    elif change == "guard_revision": dg["model_revision"] = "0" * 40
    elif change == "add_comparator": edited["detectors"].append(edited["comparators"][0])
    elif change == "promote_comparator": edited["comparators"][0]["primary_member"] = True
    elif change == "default_vote": dg["compatibility_vote"] = "raw >= 0.5"
    elif change == "cross_detector_input": ds["input"] = "semantic transformed input"
    elif change == "tokenizer": edited["contract"]["tokenization"] = "shared tokenizer"
    elif change == "ensemble": edited["decision_state"]["ensemble_policy"] = "majority vote"
    else: ds["silent_fallback"] = True
    # Expected identity is cached, but the validation and comparison are real.
    monkeypatch.setattr(stack, "build_manifest", lambda root: manifest)
    with pytest.raises(stack.StackIntegrityError):
        stack.verify_manifest(edited)


def test_checksum_drift_rejected(manifest):
    with pytest.raises(stack.StackIntegrityError, match="hash drift"):
        stack.verify_manifest(manifest, expected_sha="0" * 64)


def test_missing_real_artifact_rejected(tmp_path, manifest):
    with pytest.raises(stack.StackIntegrityError, match="missing artifact"):
        stack.verify_manifest(manifest, root=tmp_path)


def test_tampered_file_rejected(tmp_path):
    path = tmp_path / "artifacts/models/fixture.json"
    path.parent.mkdir(parents=True)
    path.write_text("changed", encoding="utf-8")
    with pytest.raises(stack.StackIntegrityError, match="hash drift"):
        stack.verify_hashes(tmp_path, {"artifacts/models/fixture.json": "0" * 64})


@pytest.mark.parametrize("role", ["D_S", "D_M-B"])
def test_wrong_accepted_calibrator_binding_rejected(role, monkeypatch):
    original = stack.read_json
    suffix = "ds_v2_calibration_manifest_v1.json" if role == "D_S" else "calibration_metadata.json"
    def swapped(path):
        value = original(path)
        if Path(path).name == suffix and (role == "D_S" or "dm_b_v1" in str(path)):
            value["model_binding" if role == "D_S" else "frozen_model_sha256"]["model_config.json"] = "0" * 64
        return value
    monkeypatch.setattr(stack, "read_json", swapped)
    with pytest.raises(stack.StackIntegrityError, match="binding mismatch"):
        stack.accepted_state(stack.ROOT)


@pytest.mark.parametrize("path", ["Dataset/Raw/data.json", "PHASE-3/data.json", "../escape.json",
    "C:/escape.json", "artifacts/models/../../escape.json", "artifacts/models/data.parquet",
    "artifacts/statistical_v2/calibration/completed_v1/calibration_predictions_v1.csv"])
def test_dataset_and_escape_paths_forbidden(path):
    with pytest.raises(stack.StackIntegrityError):
        stack.artifact_path(stack.ROOT, path)


@pytest.mark.parametrize("text", ['{"a":1,"a":2}', '{"a":NaN}', '{"a":Infinity}'])
def test_ambiguous_json_rejected(tmp_path, text):
    path = tmp_path / "bad.json"
    path.write_text(text)
    with pytest.raises(stack.StackIntegrityError):
        stack.read_json(path)


def test_frozen_package():
    if not stack.OUT.exists():
        return  # Pre-freeze suite also exercises all checker paths above.
    assert stack.check_package()["status"] == "PASS"


def test_missing_calibrator_file_rejected(tmp_path, monkeypatch):
    original = stack.artifact_path
    def missing(root, name):
        path = original(root, name)
        return tmp_path / "absent.json" if name == stack.DS_CAL + "/ds_v2_cal_v1.json" else path
    monkeypatch.setattr(stack, "artifact_path", missing)
    with pytest.raises(stack.StackIntegrityError, match="missing artifact"):
        stack.accepted_state(stack.ROOT)


@pytest.mark.parametrize("change", ["checksum", "file_bytes", "integrity", "missing_checksum"])
def test_package_drift_rejected(tmp_path, manifest, change, monkeypatch):
    content = (json.dumps(manifest, indent=2) + "\n").encode()
    report = {"status": "PASS", "canonical_sha256": stack.canonical_sha256(manifest),
              "artifact_hash_checks": len(manifest["artifact_sha256"]), "original_baseline_hash_checks": 96,
              "primary_detectors": 3, "datasets_accessed": False, "prompts_scored": False, "models_deserialized": False}
    integrity = stack.integrity_document(manifest, report, stack.hashlib.sha256(content).hexdigest())
    (tmp_path / stack.MANIFEST).write_bytes(content)
    (tmp_path / stack.CHECKSUM).write_text(report["canonical_sha256"] + "\n", encoding="ascii")
    if change == "checksum": (tmp_path / stack.CHECKSUM).write_text("0" * 64, encoding="ascii")
    elif change == "file_bytes": (tmp_path / stack.MANIFEST).write_bytes(content + b" ")
    elif change == "integrity": integrity["primary_detectors"] = 4
    else: (tmp_path / stack.CHECKSUM).unlink()
    (tmp_path / stack.INTEGRITY).write_text(json.dumps(integrity), encoding="utf-8")
    monkeypatch.setattr(stack, "build_manifest", lambda root: manifest)
    with pytest.raises(stack.StackIntegrityError):
        stack.check_package(tmp_path)
