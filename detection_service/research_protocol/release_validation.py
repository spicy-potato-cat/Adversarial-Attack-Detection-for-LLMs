"""Offline closeout audit and nonrecursive final acceptance artifact generation."""

import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
import xml.etree.ElementTree as ET

from detection_service.research_protocol import detector_semantics as files
from detection_service.research_protocol import protocol_lock as lock
from detection_service.research_protocol import release_packaging as package
from detection_service.research_protocol import r0_operational as op
from detection_service.research_protocol import r0_reproduction as history
from detection_service.research_protocol.regime import RegimeManifest, require

PHASE17 = "773853e6cf39130708e9780d84d6bd9173a1613c"
EVIDENCE = package.OUT+"/final_validation_evidence_v1.json"
VALIDATION_REPORT = "reviews/EXP_PROTOCOL_001_FINAL_VALIDATION_v1.md"
FINAL = package.OUT+"/exp_protocol_001_release_v1.json"
FINAL_HASHES = files.OUT+"/exp_protocol_001_final_hash_inventory_v1.json"
ACCEPTANCE_REPORT = "reviews/EXP_PROTOCOL_001_FINAL_ACCEPTANCE_v1.md"
CODE = ("detection_service/research_protocol/release_validation.py","detection_service/tests/test_protocol_release_audit.py")
TEST_NAMES = (
    "detector_semantics","prediction_adapters","regime_contract","operating_policy","core_metrics",
    "uncertainty","cross_regime","r0_reproduction","r0_operational","protocol_lock","protocol_release",
    "protocol_release_audit","common_mode","common_mode_final_acceptance","track2_completion",
    "semantic_oof_acceptance","statistical_scorer_acceptance","statistical_feature_ablation_acceptance",
)
TEST_PATHS = tuple("detection_service/tests/test_"+n+".py" for n in TEST_NAMES)
ISOLATED_NAMES = ("common_mode", "common_mode_final_acceptance", "track2_completion")
TEST_GROUPS = (
    tuple(p for p in TEST_PATHS if p.rsplit("/test_", 1)[1][:-3] in ISOLATED_NAMES),
    tuple(p for p in TEST_PATHS if p.rsplit("/test_", 1)[1][:-3] not in ISOLATED_NAMES),
)
TEST_COMMANDS = [
    [".local-python/python.exe", "-m", "pytest", *group,
     "-p", "detection_service.research_protocol.release_validation", "-o", "addopts=",
     "-q", "--tb=line", "--junitxml=tmp/protocol_final_"+name+".xml"]
    for group, name in zip(TEST_GROUPS, ("model_free", "remaining"))
]


class NetworkForbidden(BaseException):
    pass


def deny_network(*args, **kwargs):
    raise NetworkForbidden("NETWORK_ACTIVITY_FORBIDDEN_DURING_RELEASE_VALIDATION")


def pytest_sessionstart(session):
    """Explicit pytest plugin: unexpected network attempts cannot be hidden fallback."""
    socket.create_connection = deny_network
    socket.socket.connect = deny_network
    socket.socket.connect_ex = deny_network
    os.environ.update(HF_HUB_OFFLINE="1",TRANSFORMERS_OFFLINE="1",HF_DATASETS_OFFLINE="1")


@contextmanager
def offline():
    originals = (socket.create_connection,socket.socket.connect,socket.socket.connect_ex)
    try:
        socket.create_connection = socket.socket.connect = socket.socket.connect_ex = deny_network
        yield
    finally:
        socket.create_connection,socket.socket.connect,socket.socket.connect_ex = originals


def test_receipt(paths):
    paths = [Path(paths)] if isinstance(paths, (str, Path)) else list(map(Path, paths))
    require(bool(paths) and len({p.resolve() for p in paths}) == len(paths), "DUPLICATE_OR_EMPTY_TEST_RECEIPTS")
    counts = dict.fromkeys(("tests", "failures", "errors", "skipped"), 0)
    cases, receipts = [], []
    for path in paths:
        root = ET.parse(path).getroot()
        suites = list(root.iter("testsuite"))
        local = {k:sum(int(s.attrib.get(k,0)) for s in suites) for k in counts}
        require(local["tests"] > 0 and not any(local[k] for k in ("failures","errors","skipped")), "FULL_REGRESSION_NOT_PASS")
        elements = list(root.iter("testcase"))
        require(not any(c.find(tag) is not None for c in elements for tag in ("failure", "error", "skipped")), "FULL_REGRESSION_NOT_PASS")
        require(len(elements) == local["tests"], "TEST_RECEIPT_COUNT_MISMATCH")
        cases.extend(c.attrib["classname"]+"::"+c.attrib["name"] for c in elements)
        for key in counts: counts[key] += local[key]
        receipts.append(dict(path=str(path),sha256=files.sha(path),**local,
            seconds=sum(float(s.attrib.get("time",0)) for s in suites)))
    require(len(cases) == len(set(cases)), "DUPLICATE_TEST_CASE")
    modules = {c.split("::")[0] for c in cases}
    require({"detection_service.tests.test_"+n for n in TEST_NAMES} == modules, "REQUIRED_TEST_MODULE_MISSING_OR_UNEXPECTED")
    return dict(**counts,passed=counts["tests"],receipts=receipts,case_ids_sha=lock.digest(sorted(cases)),
        seconds=sum(r["seconds"] for r in receipts),modules=sorted(modules))


def tamper_audit():
    frozen = lock.verify_lock()
    mutations = [
        (op.POLICY,"D_S_threshold",0),(op.POLICY,"D_M-B_threshold",1),(op.POLICY,"D_G_threshold",2),
        (op.POLICY,"threshold_id",0),(files.OUT+"/detector_set_manifest_v1.json","detector_order",None),
        (files.OUT+"/detector_set_manifest_v1.json","score_direction",None),
        (op.POLICY,"operating_hash",None),(files.OUT+"/core_metrics/core_metrics_contract_v1.json","core_contract",None),
        (files.OUT+"/uncertainty/uncertainty_contract_v1.json","uncertainty_contract",None),
        (files.OUT+"/cross_regime/cross_regime_contract_v1.json","cross_regime_contract",None),
        (files.OUT+"/schemas/prediction_schema_v1.json","prediction_schema",None),
        (files.OUT+"/regime_contract_manifest_v1.json","regime_contract",None),
    ]
    cases = []
    with tempfile.TemporaryDirectory(prefix="protocol-tamper-",dir=files.ROOT/"tmp") as directory:
        root = Path(directory)
        for p in frozen["bindings"]:
            dest = root/p
            dest.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(files.ROOT/p,dest)
        for p,name,index in mutations:
            original = (root/p).read_bytes()
            value = json.loads(original)
            if index is not None:
                field = "threshold_id" if name == "threshold_id" else "threshold"
                value["points"][index][field] = "OVERRIDE" if field == "threshold_id" else 0.5
            elif name == "detector_order": value["primary_detector_order"].reverse()
            elif name == "score_direction": value["detectors"][0]["canonical_score_direction"] = "LOWER_IS_MORE_ADVERSARIAL"
            else: value["tampered"] = True
            (root/p).write_bytes(files.manifest_bytes(value))
            try:
                lock.verify_lock(root,lock_fixture=frozen)
            except ValueError as exc:
                require("AUTHORITATIVE_ARTIFACT_DRIFT" in str(exc), "TAMPER_FAILED_FOR_WRONG_REASON")
                cases.append(dict(case=name,status="REJECTED",reason=str(exc)))
            else:
                raise ValueError("TAMPER_UNEXPECTEDLY_ACCEPTED: "+name)
            finally:
                (root/p).write_bytes(original)
    for key,value in (("decision_view","EXPLICIT"),("comparison_view_id","HISTORICAL_DESCRIPTIVE_3PCT_V1"),
                      ("operating_policy_sha","0"*64),("action","FIT_THRESHOLD")):
        payload = fixture_request("r1").model_dump()
        payload[key] = value
        try: lock.ExperimentRequest.model_validate(payload)
        except ValueError: cases.append(dict(case=key+"_override",status="REJECTED"))
        else: raise ValueError("REQUEST_OVERRIDE_ACCEPTED")
    return dict(status="PASS",rejected=len(cases),cases=cases,real_artifacts_modified=False)


def fixture_request(slot):
    manifest = RegimeManifest.model_validate_json((files.ROOT/files.OUT/"fixtures/phase4"/(slot+"_manifest_v1.json")).read_bytes())
    return lock.ExperimentRequest(manifest=manifest,purpose="TEST_FIXTURE",bootstrap_unit="SAMPLE_PAIRED" if slot == "r1" else "LINEAGE_CLUSTERED")


def reconstruct_twice():
    original = {}
    inventories = (op.HASHES,lock.HASHES,package.HASHES)
    for inventory in inventories:
        value = files.read_json(files.ROOT/inventory)
        require(all(files.sha(files.ROOT/p) == h for p,h in value["sha256"].items()), "CLOSEOUT_INVENTORY_DRIFT")
        # Reconstruct canonical inventory bytes too, not merely listed payloads.
        original[inventory] = files.manifest_bytes(value)
    original[lock.LOCK] = files.manifest_bytes(lock.verify_lock())
    passes = []
    for index in (1,2):
        outputs = dict(original)
        outputs.update(op.reconstruct()[0])
        outputs.update(package.reconstruct())
        with tempfile.TemporaryDirectory(prefix=f"protocol-rebuild-{index}-",dir=files.ROOT/"tmp") as directory:
            for p,b in outputs.items():
                path = Path(directory)/p
                path.parent.mkdir(parents=True,exist_ok=True)
                path.write_bytes(b)
                require(path.read_bytes() == (files.ROOT/p).read_bytes(), "DETERMINISTIC_RECONSTRUCTION_DRIFT: "+p)
        passes.append({p:hashlib.sha256(b).hexdigest() for p,b in sorted(outputs.items())})
    require(passes[0] == passes[1], "RECONSTRUCTION_PASS_DISAGREEMENT")
    return dict(status="PASS",passes=2,byte_identical=True,artifacts_per_pass=len(passes[0]),sha256=passes[0])


def validate(receipt):
    require(lock.git("rev-parse","HEAD").decode().strip() == PHASE17, "PHASE17_18_COMMIT_GATE")
    with offline():
        tests = test_receipt(receipt)
        frozen = lock.verify_lock()
        quality = subprocess.run([str(files.ROOT/".local-python/python.exe"),"-m","detection_service.scripts.verify_quality_preservation","--mode","check"],cwd=files.ROOT,capture_output=True,text=True)
        require(quality.returncode == 0,"BASELINE_PRESERVATION_FAILURE: "+quality.stderr)
        baseline = json.loads(quality.stdout)
        historical = history.check()
        operational = op.check()
        inventory = package.check()
        rebuild = reconstruct_twice()
        tamper = tamper_audit()
        preflights = {slot:lock.verify_experiment_preflight(fixture_request(slot)) for slot in ("r1","r2_ds","r2_dmb","r2_dg","r3")}
    value = dict(evidence_version="final_validation_evidence_v1",status="PASS",source_commit=PHASE17,
        pending_validation_code_sha={p:files.sha(files.ROOT/p) for p in CODE},tests=tests,
        test_commands=TEST_COMMANDS,
        initial_combined_run=dict(tests=783,passed=782,failures=1,
            receipt_sha=files.sha(files.ROOT/"tmp/protocol_final_tests.xml"),accepted=False,
            failing_test="test_common_mode.py::test_analyze_order_grouped_and_no_model_imports",
            diagnosis="semantic_oof_acceptance imports semantic_oof, which imports torch at collection; common_mode asserts torch absent from global sys.modules",
            resolution="Separate fresh pytest processes for model-free suites and remaining suites; no existing tests changed or skipped"),
        baseline_preservation=baseline,frozen_detector_checks=165,lock_bindings=len(frozen["bindings"]),
        historical_R0=historical,operational_R0=operational,release_inventory=inventory,
        deterministic_reconstruction=rebuild,tamper=tamper,preflights=preflights,network_activity="NONE",
        R1_R2_R3_activity="NONE",Cycle2="DEFERRED",Phase16="PHASE_16_NOT_DEFINED_IN_APPROVED_PLAN")
    report = "# EXP-PROTOCOL-001 Final Validation\n\nStatus: PASS. Full required offline protocol and accepted Cycle-1 regression; zero failures/errors/skips.\n\n"
    report += "Test source commit is the Phase-17/18 commit with pending validation harness/test hashes separately recorded. No model/run provenance was rewritten.\n\n"
    report += "The initial combined process had 782 passes and one global sys.modules isolation failure. Semantic acceptance imports torch at collection, incompatible with the older common-mode fresh-process assertion. That failed receipt is NOT accepted. All required tests were rerun in separate fresh offline pytest processes; existing tests were not changed, skipped, or weakened. Receipt aggregation checks complete module coverage, counts, uniqueness, and zero failures/errors/skips.\n\n"
    report += "Network sockets were blocked by the explicit pytest plugin and audit context. No network download/API/model inference or real future-regime activity occurred. Negative socket tests exercise the block without making connections.\n\n"
    report += "Two reconstructions wrote only temporary directories and matched every frozen byte. All temporary tampering was restored/removed; accepted artifacts were never modified.\n\n```json\n"+json.dumps(value,indent=2)+"\n```\n"
    outputs = {EVIDENCE:files.manifest_bytes(value),VALIDATION_REPORT:report.encode("ascii")}
    require(not any((files.ROOT/p).exists() for p in outputs), "REFUSE_VALIDATION_EVIDENCE_OVERWRITE")
    for p,b in outputs.items():
        with (files.ROOT/p).open("xb") as stream: stream.write(b)
    return value


def acceptance_outputs(phase19):
    value = files.read_json(files.ROOT/EVIDENCE)
    require(value["status"] == "PASS" and value["tests"]["failures"] == value["tests"]["errors"] == value["tests"]["skipped"] == 0, "VALIDATION_NOT_ACCEPTED")
    require(lock.git("show",phase19+":"+EVIDENCE) == (files.ROOT/EVIDENCE).read_bytes(), "VALIDATION_GIT_ANCHOR_DRIFT")
    require(lock.git("rev-parse",phase19+"^").decode().strip() == PHASE17, "PHASE19_PARENT_CONFLICT")
    require(all(files.sha(files.ROOT/p) == h for p,h in value["pending_validation_code_sha"].items()), "VALIDATION_CODE_DRIFT")
    require(value["network_activity"] == value["R1_R2_R3_activity"] == "NONE", "UNAUTHORIZED_ACTIVITY")
    package.check()
    lock.verify_lock()
    payload = package.self_hashed(dict(release_id=lock.RELEASE_ID,status="FROZEN_READY_FOR_R1",
        protocol_lock_sha=files.sha(files.ROOT/lock.LOCK),release_inventory_sha=files.sha(files.ROOT/package.INVENTORY),
        release_manifest_sha=files.sha(files.ROOT/package.MANIFEST),final_validation_evidence_sha=files.sha(files.ROOT/EVIDENCE),
        phase14_commit=lock.PHASE14,phase15_commit=package.PHASE15,phase17_18_commit=PHASE17,phase19_commit=phase19,
        authoritative_branch="exp/protocol-001",source_commit_for_release=phase19,next_authorized_phase="R1_SHIFTED_UNSEEN",
        next_phase_started=False,cycle2_status="DEFERRED",protected_evaluation_status="NOT_STARTED",verifier_status="NOT_STARTED",
        Phase16="PHASE_16_NOT_DEFINED_IN_APPROVED_PLAN"))
    outputs = {FINAL:files.manifest_bytes(payload)}
    final_sha = hashlib.sha256(outputs[FINAL]).hexdigest()
    report = "# EXP-PROTOCOL-001 Final Acceptance\n\nSTATUS: PASS\n\n"
    report += "Phases 0-15, 17-20: PASS. Phase 16: PHASE_16_NOT_DEFINED_IN_APPROVED_PLAN.\n\n"
    report += "## Authoritative Commit Chain\n\nCycle-1: "+history.CYCLE1+"\n\nPhase 13: f533c106765041932271b56c8ccfa30d1efe691c\n\n"
    report += "\n".join(f"- {k}: {payload[k]}" for k in ("phase14_commit","phase15_commit","phase17_18_commit","phase19_commit"))
    report += "\n\nThe Phase-20 evidence commit is external to these self-hashed artifacts and reported at handoff. Model/run commits remain unchanged.\n\n"
    report += "## Frozen Thresholds\n\n"+"\n".join(f"- {p['detector']}: {p['threshold']!r}; {p['threshold_id']}; {p['score_type']}; >=." for p in lock.verify_lock()["thresholds"])
    report += "\n\n## R0 And Validation\n\nHistorical descriptive 1/3/5% evidence reproduces exactly, including separately labelled historical RNG replay. Operational baseline uses accepted OOF/OOF/frozen-development scores, the frozen D_S calibrator and fixed policy. The CALIBRATION 3% budget does not guarantee 3% R0 FPR. No thresholds were reselected.\n\n"
    metrics = files.read_json(files.ROOT/op.OUT/"r0_operational_metrics_v1.json")
    uncertainty = files.read_json(files.ROOT/op.OUT/"r0_operational_uncertainty_v1.json")
    report += "```json\n"+json.dumps(dict(operational_metrics=metrics,operational_uncertainty=uncertainty,final_validation=value),indent=2)+"\n```\n\n"
    report += "## Release Hashes\n\n"+"\n".join(f"- {k}: {payload[k]}" for k in ("protocol_lock_sha","release_inventory_sha","release_manifest_sha","final_validation_evidence_sha"))
    report += "\n- Final release artifact: "+final_sha+"\n\nThe final inventory binds this report and the final release; its own file SHA is reported externally to avoid recursive hashing.\n\n"
    report += "## Self-Rejection Audit\n\nPASS: unique authoritative roles; single policy/threshold source; exact score/calibrator identities; D_M-A comparator-only; no auto-fit/override route in official API; strict status/coverage and target/lineage validation; correct ETR denominators; operational/descriptive separation; explicit NOT_RUN; preserved historical evidence; two byte-identical reconstructions; hash-bound release references; nonrecursive self-hashes; no raw prompts/weights/future/protected data in release. Git cleanliness/synchronization is the final handoff gate.\n\n"
    report += "R1 HAS NOT STARTED\n\nNO FUTURE REGIME DATA WAS USED TO MODIFY THE PROTOCOL\n\nEXP-PROTOCOL-001 IS FROZEN BEFORE R1.\n\nR2/R3 NOT_STARTED; Cycle 2 DEFERRED; protected/final and verifier experiments NOT_STARTED.\n\n"
    report += "The pre-existing D_S live adapter remains unavailable; future scoring must resolve that execution prerequisite under separate authorization, without silently substituting runtime or changing the frozen recipe. This release freezes evaluation semantics and evidence, not a claim that live R1 scoring has already succeeded.\n\n"
    report += "## FINAL VERDICT\n\nEXP_PROTOCOL_001_COMPLETE_READY_FOR_R1\n\nTHE SINGLE MOST IMPORTANT FINAL GUARANTEE:\n\nThe protocol is frozen before unseen-regime evidence, with immutable operational policy and fail-closed provenance/metric/lineage checks.\n\nNEXT AUTHORIZED RESEARCH STEP: R1_SHIFTED_UNSEEN. Do not begin R1 in this closeout.\n"
    outputs[ACCEPTANCE_REPORT] = report.encode("ascii")
    paths = {r["artifact_path"]:r["sha256"] for r in files.read_json(files.ROOT/package.INVENTORY)["records"]}
    for p in (package.INVENTORY,package.MANIFEST,package.HASHES,EVIDENCE,VALIDATION_REPORT,*CODE): paths[p] = files.sha(files.ROOT/p)
    paths.update({p:hashlib.sha256(b).hexdigest() for p,b in outputs.items()})
    outputs[FINAL_HASHES] = files.manifest_bytes(package.self_hashed(dict(inventory_version="exp_protocol_001_final_hash_inventory_v1",release_id=lock.RELEASE_ID,
        source_commit_for_release=phase19,sha256=dict(sorted(paths.items())),self_hash_policy="Nonrecursive manifest_hash excludes itself; inventory file SHA reported externally")))
    return outputs


def accept():
    phase19 = lock.git("rev-parse","HEAD").decode().strip()
    require(lock.git("branch","--show-current").decode().strip() == "exp/protocol-001", "AUTHORITATIVE_BRANCH_REQUIRED")
    require(not lock.git("status","--porcelain").strip(), "CLEAN_PHASE19_COMMIT_REQUIRED")
    outputs = acceptance_outputs(phase19)
    require(not any((files.ROOT/p).exists() for p in outputs), "REFUSE_FINAL_RELEASE_OVERWRITE")
    for p,b in outputs.items():
        with (files.ROOT/p).open("xb") as stream: stream.write(b)
    return {"status":"FROZEN_READY_FOR_R1","artifacts":{p:files.sha(files.ROOT/p) for p in outputs}}


def check_acceptance():
    value = files.read_json(files.ROOT/FINAL)
    require(value["manifest_hash"] == lock.digest({k:v for k,v in value.items() if k != "manifest_hash"}), "FINAL_RELEASE_SELF_HASH")
    outputs = acceptance_outputs(value["phase19_commit"])
    require(all((files.ROOT/p).read_bytes() == b for p,b in outputs.items()), "FINAL_ACCEPTANCE_RECONSTRUCTION_DRIFT")
    inventory = files.read_json(files.ROOT/FINAL_HASHES)
    require(inventory["manifest_hash"] == lock.digest({k:v for k,v in inventory.items() if k != "manifest_hash"}), "FINAL_INVENTORY_SELF_HASH")
    require(all(files.sha(files.ROOT/p) == h for p,h in inventory["sha256"].items()), "FINAL_AUTHORITATIVE_ARTIFACT_DRIFT")
    return {"status":"PASS","hash_checks":len(inventory["sha256"]),"R1_started":False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode",choices=("validate","accept","check"),required=True)
    parser.add_argument("--receipt",type=Path,nargs="+",default=[Path("tmp/protocol_final_model_free.xml"),Path("tmp/protocol_final_remaining.xml")])
    args = parser.parse_args()
    result = validate(args.receipt) if args.mode == "validate" else accept() if args.mode == "accept" else check_acceptance()
    print(json.dumps(result,indent=2))
