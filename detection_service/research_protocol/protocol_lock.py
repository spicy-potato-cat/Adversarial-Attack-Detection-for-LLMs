"""Git-anchored immutable protocol preflight and official read-only evaluation."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from functools import lru_cache
from typing import Literal

from detection_service.research_protocol import detector_semantics as files
from detection_service.research_protocol import r0_operational as operational
from detection_service.research_protocol.alignment import align_evaluation, bind_predictions, digest
from detection_service.research_protocol.core_metrics import evaluate_core
from detection_service.research_protocol.cross_regime import result_bundle
from detection_service.research_protocol.metric_catalog import metric_catalog
from detection_service.research_protocol.operating_policy import apply_operating_policy
from detection_service.research_protocol.regime import FrozenMetadata, RegimeManifest, require
from detection_service.research_protocol.regime_contract import FrozenRegimeContracts
from detection_service.research_protocol.uncertainty import BootstrapConfig, bootstrap_metrics

PHASE14 = "2941f1412d15f16bfc1564d1d584a76c0b909df3"
RELEASE_ID = "exp_protocol_001_v1"
LOCK = files.OUT+"/protocol_lock_manifest_v1.json"
HASHES = files.OUT+"/phase15_artifact_hashes_v1.json"
REPORT = "reviews/EXP_PROTOCOL_001_PROTOCOL_LOCK_v1.md"
CODE = ("detection_service/research_protocol/protocol_lock.py", "detection_service/tests/test_protocol_lock.py")


def git(*args):
    return subprocess.check_output(["git", *args], cwd=files.ROOT)


@lru_cache(maxsize=1)
def source_bindings():
    paths = git("ls-tree", "-r", "--name-only", PHASE14, "--", files.OUT,
                "detection_service/research_protocol").decode().splitlines()
    bindings = {p: hashlib.sha256(git("show", PHASE14+":"+p)).hexdigest() for p in paths}
    # Prior inventory entries include the exact tests/reports required to replay.
    for path in paths:
        if path.endswith("artifact_hashes_v1.json"):
            for p,h in json.loads(git("show", PHASE14+":"+path))["sha256"].items():
                require(p not in bindings or bindings[p] == h, "CONFLICTING_AUTHORITATIVE_BINDING")
                bindings[p] = h
    return dict(sorted(bindings.items()))


def build_lock(root=files.ROOT):
    root = Path(root)
    bindings = source_bindings().copy()
    require(all(files.sha(files.contained(root,p)) == h for p,h in bindings.items()), "AUTHORITATIVE_ARTIFACT_DRIFT")
    bindings.update({p:files.sha(root/p) for p in CODE})
    detector = files.read_json(root/files.OUT/"detector_set_manifest_v1.json")
    policy = files.read_json(root/operational.POLICY)
    payload = dict(manifest_version="protocol_lock_manifest_v1", protocol_release_id=RELEASE_ID,
        protocol_version="exp_protocol_001_v1", phase14_source_commit=PHASE14, status="FROZEN",
        readiness="READY_FOR_EXPERIMENT_PREFLIGHT", bindings=dict(sorted(bindings.items())),
        primary_detector_order=detector["primary_detector_order"], primary_detector_ids=[d["detector_id"] for d in detector["detectors"]],
        comparator="D_M-A_COMPARATOR_ONLY", score_direction="HIGHER_IS_MORE_ADVERSARIAL",
        detector_score_semantics={d["stack_label"]:{k:d[k] for k in ("native_score_definition","calibrator_id","calibrator_hash","calibrator_input","calibrator_output")} for d in detector["detectors"]},
        operating_policy_id=policy["policy_id"], decision_operator=policy["decision_operator"],
        threshold_selection_algorithm=policy["algorithm_id"], threshold_selection_partition="CALIBRATION",
        thresholds=[dict(detector=p["stack_label"],detector_id=p["detector_id"],threshold=p["threshold"],threshold_id=p["threshold_id"],score_type=p["threshold_input_score_type"]) for p in policy["points"]],
        prediction_schema_version="prediction_v1", regime_schema_version="regime_manifest_v1",
        core_metrics_version="core_metrics_bundle_v1", comparison_view="OPERATIONAL_FIXED_V1",
        uncertainty_defaults=BootstrapConfig(unit="LINEAGE_CLUSTERED",domain="ATTACK_ONLY").model_dump(mode="json"),
        allowed_action="EVALUATE_ONLY", forbidden="No runtime overrides, fitting, adaptation, detector selection, or definition changes",
        Phase16="PHASE_16_NOT_DEFINED_IN_APPROVED_PLAN", R1_started=False,R2_started=False,R3_started=False,Cycle2="DEFERRED")
    payload["manifest_hash"] = digest(payload)
    return payload


def phase15_anchor():
    """Trust committed bytes, not a mutable adjacent inventory/self-hash alone."""
    for line in git("rev-list", "--first-parent", "--parents", "HEAD").decode().splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[1] == PHASE14:
            probe = subprocess.run(["git","cat-file","-e",parts[0]+":"+LOCK],cwd=files.ROOT,capture_output=True)
            return parts[0] if probe.returncode == 0 else None
    return None


def verify_lock(root=files.ROOT, *, lock_fixture=None):
    root = Path(root)
    anchor = phase15_anchor()
    if lock_fixture is not None:
        lock = lock_fixture
    else:
        require(anchor is not None, "COMMITTED_PROTOCOL_LOCK_REQUIRED")
        blob = git("show",anchor+":"+LOCK)
        require((root/LOCK).read_bytes() == blob, "PROTOCOL_LOCK_GIT_ANCHOR_MISMATCH")
        lock = files.read_json(root/LOCK)
        for p in (*CODE,HASHES,REPORT):
            require((root/p).read_bytes() == git("show",anchor+":"+p), "PHASE15_CODE_OR_EVIDENCE_DRIFT")
    require(lock == build_lock(root), "PROTOCOL_LOCK_CONTENT_OR_SELF_HASH_MISMATCH")
    require(lock["primary_detector_order"] == ["D_S","D_M-B","D_G"] and lock["primary_detector_ids"] == ["ds_v2","dm_b_v1","dg_v1"], "PRIMARY_ORDER_DRIFT")
    require(tuple(p["threshold"] for p in lock["thresholds"]) == operational.THRESHOLDS and
            tuple(p["threshold_id"] for p in lock["thresholds"]) == operational.IDS, "THRESHOLD_DRIFT")
    return lock


class ExperimentRequest(FrozenMetadata):
    manifest: RegimeManifest
    purpose: Literal["OFFICIAL_EVALUATION", "TEST_FIXTURE"] = "OFFICIAL_EVALUATION"
    action: Literal["EVALUATE_ONLY"] = "EVALUATE_ONLY"
    decision_view: Literal["OPERATIONAL"] = "OPERATIONAL"
    comparison_view_id: Literal["OPERATIONAL_FIXED_V1"] = "OPERATIONAL_FIXED_V1"
    operating_policy_sha: Literal[operational.POLICY_SHA] = operational.POLICY_SHA
    bootstrap_unit: Literal["SAMPLE_PAIRED", "LINEAGE_CLUSTERED"]


def verify_experiment_preflight(request, *, root=files.ROOT, lock_fixture=None):
    request = ExperimentRequest.model_validate(request.model_dump() if isinstance(request,ExperimentRequest) else request)
    require(lock_fixture is None or request.purpose == "TEST_FIXTURE", "FIXTURE_LOCK_NOT_OFFICIAL_AUTHORITY")
    lock = verify_lock(root,lock_fixture=lock_fixture)
    policy = operational.verified_policy(root)
    manifest = FrozenRegimeContracts(root).validate_manifest(request.manifest)
    require(manifest.status == "FROZEN", "FROZEN_EXPERIMENT_MEMBERSHIP_REQUIRED")
    require((manifest.evidence_kind == "SYNTHETIC_FIXTURE") == (request.purpose == "TEST_FIXTURE"), "FIXTURE_NOT_REAL_EXPERIMENT")
    require(manifest.threat_regime in ("R1_SHIFTED_UNSEEN","R2_SINGLE_DETECTOR_TARGETED","R3_ENSEMBLE_TARGETED"), "FUTURE_REGIME_REQUIRED")
    require(manifest.partition not in ("BASE_TRAIN","CALIBRATION","META_TRAIN","ATTACK_GENERATION","QUARANTINE"), "EVALUATION_PARTITION_REQUIRED")
    if manifest.threat_regime.startswith(("R2_","R3_")):
        require(request.bootstrap_unit == "LINEAGE_CLUSTERED", "GENERATED_ATTACK_LINEAGE_CLUSTERING_REQUIRED")
        require(all(s.lineage_id and s.attack_method and s.attack_method_revision and s.attack_success_definition
                    and s.valid_attack_attempt is not None for s in manifest.samples), "TARGETED_PROVENANCE_REQUIRED")
    if any(s.generated_sample for s in manifest.samples):
        require(request.bootstrap_unit == "LINEAGE_CLUSTERED", "GENERATED_ATTACK_LINEAGE_CLUSTERING_REQUIRED")
    if request.bootstrap_unit == "LINEAGE_CLUSTERED":
        require(all(s.lineage_id for s in manifest.samples), "LINEAGE_REQUIRED_FOR_CLUSTER_BOOTSTRAP")
    return dict(status="PASS",purpose=request.purpose,experiment_id=manifest.experiment_id,
        protocol_lock_sha=hashlib.sha256(files.manifest_bytes(lock)).hexdigest(),
        operating_policy_sha=policy.file_sha,experiment_executed=False)


def evaluate_official(request, predictions):
    """The sole official metrics path: preflight -> fixed policy -> complete core.

    No threshold/configuration kwargs, fitting, model loading, or persistence.
    Synthetic fixture mode cannot publish an official experiment result.
    """
    request = ExperimentRequest.model_validate(request.model_dump() if isinstance(request,ExperimentRequest) else request)
    require(request.purpose == "OFFICIAL_EVALUATION", "TEST_FIXTURE_CANNOT_PUBLISH_REAL_RESULT")
    verify_experiment_preflight(request)
    policy = operational.verified_policy()
    projected = tuple(apply_operating_policy(p,policy) for p in predictions)
    table = align_evaluation(request.manifest, projected, binding=bind_predictions(request.manifest),
        decision_view="OPERATIONAL",contracts=policy.contracts,operating_policy=policy)
    core = evaluate_core(table)
    names = metric_catalog(core)
    attack = tuple(k for k in names if k.startswith(("pair/","pattern/","recovery/","all_three/")) or k.endswith("/fnr"))
    benign = tuple(k for k in names if k.endswith("/fpr"))
    intervals = [bootstrap_metrics(table,attack,BootstrapConfig(unit=request.bootstrap_unit,domain="ATTACK_ONLY"))]
    if core.individual.benign_count:
        intervals.append(bootstrap_metrics(table,benign,BootstrapConfig(unit=request.bootstrap_unit,domain="BENIGN_ONLY")))
    if request.manifest.threat_regime == "R2_SINGLE_DETECTOR_TARGETED":
        target = request.manifest.samples[0].target_detector
        target_names = tuple(k for k in names if k.startswith(("target/","transfer/")))
        intervals.append(bootstrap_metrics(table,target_names,BootstrapConfig(unit="LINEAGE_CLUSTERED",domain="VALID_TARGET_ATTEMPTS",target_detector=target)))
    return result_bundle(table,request.manifest,"OPERATIONAL_FIXED_V1",uncertainty=tuple(intervals))


def freeze():
    root = files.ROOT
    require(git("rev-parse","HEAD").decode().strip() == PHASE14, "PHASE14_COMMIT_GATE")
    lock = build_lock(root)
    report = ("# EXP-PROTOCOL-001 Protocol Lock\n\nStatus: FROZEN; release exp_protocol_001_v1; READY_FOR_EXPERIMENT_PREFLIGHT.\n\n"
        "The lock binds exact Phase-14 Git-source hashes, all prior inventories/code, OOF/direct R0 baselines, schemas, detector order, score/calibration semantics, exact thresholds/IDs/operator, and production defaults. Its nonrecursive self-hash excludes only manifest_hash.\n\n"
        "Official verification anchors the lock and Phase-15 code/inventory/report to the direct accepted child of the Phase-14 commit on first-parent history. A mutable adjacent hash file is not a trust anchor. No official evaluation can run before that commit exists.\n\n"
        "ExperimentRequest is strict and forbids extra keys. Official evaluation exposes no detector, threshold, fitting, calibration, metric, or bootstrap-default overrides. It calls preflight before consuming canonical predictions, applies only the verified frozen policy, requires STRICT_COMPLETE, then reuses frozen core/uncertainty/bundle contracts. No fit/load/download/persistence path exists.\n\n"
        "Synthetic R1, three R2 targets, and R3 exercise preflight only. TEST_FIXTURE cannot publish official results. R2/R3 require clustered lineage and attack/validity provenance. Protected evaluation may be read-only; any fitting/adaptation action is rejected for every partition.\n\n"
        "D_M-A remains comparator-only. Operational/descriptive view mixing is forbidden. No partitions or frozen files change; R1/R2/R3 are NOT_STARTED; Cycle 2 DEFERRED.\n")
    outputs = {LOCK:files.manifest_bytes(lock),REPORT:report.encode("ascii")}
    require(not any((root/p).exists() for p in (*outputs,HASHES)), "REFUSE_PHASE15_OVERWRITE")
    for p,b in outputs.items():
        with (root/p).open("xb") as stream: stream.write(b)
    inventory = dict(artifact_version="phase15_artifact_hashes_v1",phase14_commit=PHASE14,
        sha256={p:files.sha(root/p) for p in (*outputs,*CODE)})
    with (root/HASHES).open("xb") as stream: stream.write(files.manifest_bytes(inventory))
    return {"status":"FROZEN","bindings":len(lock["bindings"]),"lock_sha":files.sha(root/LOCK)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--freeze",action="store_true")
    parser.add_argument("--request",type=Path)
    args = parser.parse_args()
    if args.freeze:
        value = freeze()
    elif args.request:
        value = verify_experiment_preflight(ExperimentRequest.model_validate_json(args.request.read_bytes()))
    else:
        lock = verify_lock()
        value = {"status":"PASS","bindings":len(lock["bindings"]),"protocol_release_id":RELEASE_ID}
    print(json.dumps(value,indent=2))
