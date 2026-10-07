"""Closeout rejection, canonical inventories, offline guards and release audit."""

from copy import deepcopy
import json
import socket
import xml.etree.ElementTree as ET

import pytest

from detection_service.research_protocol import release_validation as audit


def test_network_guard_fails_closed_without_connection():
    with audit.offline():
        with pytest.raises(audit.NetworkForbidden): socket.create_connection(("example.invalid",443))


def test_all_five_preflights_are_fixture_only():
    for slot in ("r1","r2_ds","r2_dmb","r2_dg","r3"):
        result = audit.lock.verify_experiment_preflight(audit.fixture_request(slot))
        assert result["status"] == "PASS"
        assert result["purpose"] == "TEST_FIXTURE" and result["experiment_executed"] is False


def test_tamper_audit_all_reject_and_no_source_mutation():
    before = audit.lock.build_lock()
    result = audit.tamper_audit()
    assert result["status"] == "PASS" and result["rejected"] == 16
    assert all(c["status"] == "REJECTED" for c in result["cases"])
    assert audit.lock.build_lock() == before


@pytest.mark.parametrize("change",["missing_role","duplicate_role","wrong_hash"])
def test_inventory_self_rejection(tmp_path,change):
    # Rehashed tampering remains invalid even if an attacker changes a sidecar.
    value = audit.files.read_json(audit.files.ROOT/audit.package.INVENTORY)
    if change == "missing_role": value["records"] = value["records"][1:]
    elif change == "duplicate_role": value["records"].append(deepcopy(value["records"][0]))
    else: value["records"][0]["sha256"] = "0"*64
    value["manifest_hash"] = audit.lock.digest({k:v for k,v in value.items() if k != "manifest_hash"})
    dest = tmp_path/audit.package.INVENTORY
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_bytes(audit.files.manifest_bytes(value))
    with pytest.raises((ValueError,OSError)): audit.package.audit_inventory(tmp_path)


@pytest.mark.parametrize("field",["failures","errors","skipped"])
def test_failing_or_skipped_junit_cannot_pass(tmp_path,field):
    root = ET.Element("testsuites")
    ET.SubElement(root,"testsuite",tests="1",**{field:"1"})
    path = tmp_path/"receipt.xml"
    ET.ElementTree(root).write(path)
    with pytest.raises(ValueError,match="REGRESSION_NOT_PASS"): audit.test_receipt(path)


def test_incomplete_junit_cannot_pass(tmp_path):
    root = ET.Element("testsuites")
    suite = ET.SubElement(root,"testsuite",tests="1")
    ET.SubElement(suite,"testcase",classname="unrelated",name="test_pass")
    path = tmp_path/"receipt.xml"
    ET.ElementTree(root).write(path)
    with pytest.raises(ValueError,match="MODULE_MISSING"): audit.test_receipt(path)


def receipts(tmp_path):
    paths = []
    for index, names in enumerate((audit.ISOLATED_NAMES, tuple(n for n in audit.TEST_NAMES if n not in audit.ISOLATED_NAMES))):
        root = ET.Element("testsuites")
        suite = ET.SubElement(root,"testsuite",tests=str(len(names)))
        for name in names:
            ET.SubElement(suite,"testcase",classname="detection_service.tests.test_"+name,name="fixture_pass")
        path = tmp_path/f"receipt-{index}.xml"
        ET.ElementTree(root).write(path)
        paths.append(path)
    return paths


def test_split_receipts_require_exact_full_coverage(tmp_path):
    result = audit.test_receipt(receipts(tmp_path))
    assert result["passed"] == len(audit.TEST_NAMES) and len(result["receipts"]) == 2


@pytest.mark.parametrize("change,reason",[("duplicate_case","DUPLICATE_TEST_CASE"),
    ("wrong_count","COUNT_MISMATCH"),("failure_child","REGRESSION_NOT_PASS"),
    ("duplicate_path","DUPLICATE_OR_EMPTY")])
def test_split_receipts_reject_invalid_evidence(tmp_path,change,reason):
    paths = receipts(tmp_path)
    root = ET.parse(paths[1]).getroot()
    suite = root.find("testsuite")
    if change == "duplicate_case":
        suite.append(deepcopy(suite[0]))
        suite.set("tests",str(len(suite)))
    elif change == "wrong_count": suite.set("tests","1")
    elif change == "failure_child": ET.SubElement(suite[0],"failure")
    else: paths.append(paths[0])
    ET.ElementTree(root).write(paths[1])
    with pytest.raises(ValueError,match=reason): audit.test_receipt(paths)


def test_final_serialization_has_no_recursive_hash():
    value = audit.package.self_hashed({"release_id":"exp_protocol_001_v1","next_phase_started":False})
    assert value["manifest_hash"] == audit.lock.digest({k:v for k,v in value.items() if k != "manifest_hash"})
    assert "phase20_commit" not in value


def test_official_api_has_no_policy_or_bootstrap_override():
    import inspect
    assert list(inspect.signature(audit.lock.evaluate_official).parameters) == ["request","predictions"]
    fields = audit.lock.ExperimentRequest.model_fields
    assert not set(fields) & {"threshold","threshold_id","fit","calibrator","replicates","seed","confidence","detectors"}


def test_accepted_baselines_are_different_views():
    historical = audit.files.read_json(audit.files.ROOT/audit.history.OUT/"r0_cross_regime_bundle_v1.json")
    operational = audit.files.read_json(audit.files.ROOT/audit.op.OUT/"r0_operational_result_bundle_v1.json")
    assert historical["comparison_view_id"] == "HISTORICAL_DESCRIPTIVE_3PCT_V1"
    assert operational["comparison_view_id"] == "OPERATIONAL_FIXED_V1"
    assert historical["operating_point_manifest_hash"] is None
    assert operational["operating_point_manifest_hash"] == audit.op.POLICY_SHA
