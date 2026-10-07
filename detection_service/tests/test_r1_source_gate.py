"""Blocked-source qualification evidence, not R1 experiment acceptance tests."""

from detection_service.research_protocol import detector_semantics as files
from detection_service.research_protocol import ds_runtime, protocol_lock, release_validation

PATH = files.OUT + "/r1/r1_source_qualification_blocker_v1.json"


def evidence():
    return files.read_json(files.ROOT / PATH)


def test_source_governance_evidence_hashes():
    for path, expected in evidence()["evidence_sha256"].items():
        assert files.sha(files.ROOT / path) == expected


def test_role_decisions_match_current_register():
    register = (files.ROOT / "data_governance/DATA_PROMOTION_REGISTER_v1.md").read_text()
    for decision in evidence()["decision_snapshot"]:
        matches = [line for line in register.splitlines()
                   if decision["dataset_id"] in line and decision["status"] in line]
        assert len(matches) == 1
        assert not decision["r1_eligible"]
        assert "| NO |" in matches[0]
    assert len(evidence()["decision_snapshot"]) == 17


def test_gate_b_is_blocked_not_empty_corpus_pass():
    value = evidence()
    assert value["gate_b"] == "BLOCKED_SOURCE_GOVERNANCE"
    assert value["qualified_external_attack_sources"] == 0
    assert value["sample_count"] is None
    assert value["exact_canonical_overlaps_remaining"] is None
    assert value["official_preflight"] == "NOT_RUN_NO_CORPUS"
    assert value["scientific_conclusion"].startswith("NOT_MEASURED")


def test_no_downstream_experiment_artifacts():
    value = evidence()
    assert not value["experiment_executed"] and not value["dataset_frozen"]
    assert value["gate_c"] == value["gate_d"] == "NOT_STARTED"
    assert value["r1_detector_predictions"] == 0
    for name in value["not_created"]:
        assert not (files.ROOT / files.OUT / "r1" / name).exists()


def test_missing_forensic_evidence_not_claimed_present():
    for path in evidence()["missing_evidence"]:
        assert not (files.ROOT / path).exists()


def test_protected_source_boundary_not_waived():
    value = evidence()
    xs = next(row for row in value["decision_snapshot"] if row["dataset_id"] == "DS-TXT-009")
    assert xs["status"] == "APPROVED_FOR_PROTECTED_EVAL" and not xs["r1_eligible"]
    assert not value["protected_source_payloads_opened"]
    assert not value["source_decisions_changed"]


def test_ds_live_equivalence_still_passes():
    adapter = ds_runtime.accepted_ds_adapter()
    proof = files.read_json(files.ROOT / ds_runtime.EQUIVALENCE)
    binding = files.read_json(files.ROOT / ds_runtime.BINDING)
    assert adapter.live_binding_available and proof["status"] == binding["status"] == "PASS"
    assert binding["max_raw_score_difference"] <= 1e-12
    assert binding["max_calibrated_score_difference"] <= 1e-12
    assert binding["decision_mismatch_count"] == 0
    # This verifies the committed proof; it does not repeat LM inference on R1.
    assert protocol_lock.git("rev-parse", evidence()["gate_a_commit"]).decode().strip() == evidence()["gate_a_commit"]


def test_protocol_lock_unchanged():
    assert files.sha(files.ROOT / files.OUT / "protocol_lock_manifest_v1.json") == "d0e1f38898b4f82c93daaa6425f4ddb3592fe080fe50db6ef36f2be9dbed2353"
    assert protocol_lock.verify_lock()["protocol_release_id"] == "exp_protocol_001_v1"


def test_r0_artifacts_unchanged():
    checked = release_validation.check_acceptance()
    assert checked["status"] == "PASS" and checked["hash_checks"] == 118
