"""Reference-only packaging, self-hash, completeness and specification tests."""

from copy import deepcopy
import hashlib
import json

import jsonschema
import pytest

from detection_service.research_protocol import release_packaging as release


@pytest.fixture(scope="module")
def package():
    return release.reconstruct()


@pytest.mark.parametrize("path",[release.INVENTORY,release.MANIFEST,release.TEMPLATE])
def test_deterministic_release_bytes(package,path):
    assert package[path] == release.reconstruct()[path]


def test_release_inventory_complete_valid_hashes(package):
    value = json.loads(package[release.INVENTORY])
    records = value["records"]
    assert len({r["logical_role"] for r in records}) == len(records)
    assert len({r["artifact_path"] for r in records}) == len(records)
    assert set(release.ROLES.values()) <= {r["logical_role"] for r in records}
    for r in records:
        data = package.get(r["artifact_path"])
        if data is None: data = (release.files.ROOT/r["artifact_path"]).read_bytes()
        assert hashlib.sha256(data).hexdigest() == r["sha256"]
        assert type(r["required_for_execution"]) is bool
        assert type(r["required_for_reproducibility"]) is bool
        assert r["source_phase"]


def test_release_manifest_references_and_self_hash(package):
    value = json.loads(package[release.MANIFEST])
    assert value["release_id"] == "exp_protocol_001_v1"
    assert value["status"] == "FROZEN"
    assert value["phase14_commit"] == release.lock.PHASE14
    assert value["phase15_commit"] == release.PHASE15
    assert value["next_authorized_research_regime"] == "R1_SHIFTED_UNSEEN"
    assert value["R1_executed"] is False
    assert value["release_inventory_sha"] == hashlib.sha256(package[release.INVENTORY]).hexdigest()
    assert value["protocol_lock_sha"] == release.files.sha(release.files.ROOT/release.lock.LOCK)
    for key in ("historical_R0_reference","operational_R0_reference"):
        ref = value[key]
        assert ref["sha256"] == release.files.sha(release.files.ROOT/ref["path"])
    assert value["manifest_hash"] == release.digest({k:v for k,v in value.items() if k != "manifest_hash"})


def test_template_is_schema_not_experiment(package):
    value = json.loads(package[release.TEMPLATE])
    assert value["is_executable"] is False and value["contains_results"] is False
    assert "samples" not in value and "predictions" not in value
    jsonschema.Draft202012Validator.check_schema(value["request_schema"])
    assert len(value["regimes"]) == 3
    assert value["threshold_override_allowed"] is False
    assert value["action"] == "EVALUATE_ONLY"


def test_no_raw_prompts_weights_or_fake_results(package):
    records = json.loads(package[release.INVENTORY])["records"]
    assert not any("/Raw/" in r["artifact_path"] or ".model-cache" in r["artifact_path"]
                   or r["artifact_path"].endswith((".safetensors",".bin",".joblib")) for r in records)
    assert json.loads(package[release.INVENTORY])["raw_prompts_included"] is False
    assert json.loads(package[release.INVENTORY])["model_weights_included"] is False


def test_specification_all_26_sections_and_runbook_14_steps():
    spec = (release.files.ROOT/release.DOCS[0]).read_text()
    runbook = (release.files.ROOT/release.DOCS[1]).read_text()
    for n in range(1,27): assert f"## {n}. " in spec
    for n in range(1,15): assert f"\n{n}. " in runbook
    for regime in ("R1_SHIFTED_UNSEEN","R2_SINGLE_DETECTOR_TARGETED","R3_ENSEMBLE_TARGETED"):
        assert regime in spec and regime in runbook
    assert "R1 HAS NOT STARTED" in spec
    assert "NO FUTURE REGIME DATA WAS USED TO MODIFY THE PROTOCOL" in spec
    assert "EXP-PROTOCOL-001 IS FROZEN BEFORE R1" in spec
    assert "PHASE_16_NOT_DEFINED_IN_APPROVED_PLAN" in spec


def test_deterministic_self_hash_excludes_only_hash():
    payload = {"release_id":"exp_protocol_001_v1","status":"FROZEN"}
    value = release.self_hashed(payload)
    assert value["manifest_hash"] == release.digest(payload)
    altered = deepcopy(payload)
    altered["status"] = "EXECUTED"
    assert release.self_hashed(altered)["manifest_hash"] != value["manifest_hash"]
