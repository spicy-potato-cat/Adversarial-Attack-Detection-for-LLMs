"""Deterministic reference-only release package; never runs research experiments."""

import argparse
import hashlib
import json
from pathlib import Path

from detection_service.research_protocol import detector_semantics as files
from detection_service.research_protocol import protocol_lock as lock
from detection_service.research_protocol.alignment import digest
from detection_service.research_protocol.regime import require

PHASE15 = "d98fc5a64e09b756ef8652301e79d1d97755639c"
OUT = files.OUT+"/release"
INVENTORY = OUT+"/protocol_release_inventory_v1.json"
MANIFEST = OUT+"/protocol_release_manifest_v1.json"
TEMPLATE = OUT+"/experiment_execution_template_v1.json"
HASHES = files.OUT+"/phase17_18_artifact_hashes_v1.json"
DOCS = tuple("reviews/EXP_PROTOCOL_001_"+name+"_v1.md" for name in ("FROZEN_SPECIFICATION","RESEARCH_EXECUTION_RUNBOOK"))
CODE = ("detection_service/research_protocol/release_packaging.py","detection_service/tests/test_protocol_release.py")
ROLES = {
    files.OUT+"/detector_set_manifest_v1.json":"detector_contract",
    files.OUT+"/schemas/prediction_schema_v1.json":"prediction_contract",
    files.OUT+"/regime_contract_manifest_v1.json":"regime_contract",
    files.OUT+"/operating_point_manifest_v1.json":"operating_policy",
    files.OUT+"/core_metrics/core_metrics_contract_v1.json":"core_metrics",
    files.OUT+"/uncertainty/uncertainty_contract_v1.json":"uncertainty_contract",
    files.OUT+"/cross_regime/cross_regime_contract_v1.json":"cross_regime_contract",
    files.OUT+"/r0/r0_cross_regime_bundle_v1.json":"historical_R0_baseline",
    files.OUT+"/r0/r0_operational_result_bundle_v1.json":"operational_R0_baseline",
    lock.LOCK:"protocol_lock",TEMPLATE:"execution_template",
}


def self_hashed(payload):
    return dict(**payload,manifest_hash=digest(payload))


def template():
    return dict(template_version="experiment_execution_template_v1",release_id=lock.RELEASE_ID,
        is_executable=False,contains_results=False,request_schema=lock.ExperimentRequest.model_json_schema(),
        required_references=["protocol_lock_sha","regime_manifest_sha","dataset_source_hashes","lineage_provenance"],
        regimes=[dict(threat_regime="R1_SHIFTED_UNSEEN",target_detector=None,bootstrap_unit="DECLARE_FROM_LINEAGE"),
                 dict(threat_regime="R2_SINGLE_DETECTOR_TARGETED",target_detector_options=["D_S","D_M-B","D_G"],bootstrap_unit="LINEAGE_CLUSTERED"),
                 dict(threat_regime="R3_ENSEMBLE_TARGETED",target_detector="ALL",bootstrap_unit="LINEAGE_CLUSTERED")],
        decision_view="OPERATIONAL",comparison_view_id="OPERATIONAL_FIXED_V1",action="EVALUATE_ONLY",
        operational_policy_sha=lock.operational.POLICY_SHA,threshold_override_allowed=False,
        notes="Schema/template only. No manifest instance, sample IDs, predictions, or completed experiment.")


def reconstruct(root=files.ROOT):
    root = Path(root)
    frozen = lock.verify_lock(root)
    expected_lock = hashlib.sha256(lock.git("show",PHASE15+":"+lock.LOCK)).hexdigest()
    require(files.sha(root/lock.LOCK) == expected_lock, "RELEASE_LOCK_ANCHOR_CONFLICT")
    outputs = {TEMPLATE:files.manifest_bytes(template())}
    paths = dict(frozen["bindings"])
    for p in (lock.LOCK,lock.HASHES,lock.REPORT,*DOCS,*CODE): paths[p] = files.sha(root/p)
    paths[TEMPLATE] = hashlib.sha256(outputs[TEMPLATE]).hexdigest()
    require(not any("/Raw/" in p or ".model-cache" in p or p.endswith((".safetensors",".bin",".joblib")) for p in paths),
            "RAW_DATA_OR_WEIGHTS_FORBIDDEN_IN_RELEASE")
    records = []
    for p,h in sorted(paths.items()):
        role = ROLES.get(p,"support/"+p)
        records.append(dict(logical_role=role,artifact_path=p,sha256=h,artifact_version=Path(p).stem,
            required_for_execution=role in ROLES.values() or p.startswith("detection_service/research_protocol/"),
            required_for_reproducibility=True,source_phase="17/18" if p in (*DOCS,*CODE,TEMPLATE) else "15" if p in (lock.LOCK,lock.HASHES,lock.REPORT,*lock.CODE) else "0-14"))
    inventory = self_hashed(dict(inventory_version="protocol_release_inventory_v1",release_id=lock.RELEASE_ID,records=records,
        raw_prompts_included=False,model_weights_included=False,content_kind="REFERENCES_AND_METADATA_ONLY"))
    outputs[INVENTORY] = files.manifest_bytes(inventory)
    manifest = self_hashed(dict(manifest_version="protocol_release_manifest_v1",release_id=lock.RELEASE_ID,status="FROZEN",
        protocol_lock_sha=expected_lock,phase14_commit=lock.PHASE14,phase15_commit=PHASE15,
        detector_set_id=files.read_json(root/files.OUT/"detector_set_manifest_v1.json")["stack_id"],operating_policy_id="operating_policy_v1",
        core_metrics_contract_version="core_metrics_bundle_v1",uncertainty_contract_version="uncertainty_contract_v1",cross_regime_contract_version="cross_regime_contract_v1",
        historical_R0_reference=dict(path=files.OUT+"/r0/r0_cross_regime_bundle_v1.json",sha256=paths[files.OUT+"/r0/r0_cross_regime_bundle_v1.json"]),
        operational_R0_reference=dict(path=files.OUT+"/r0/r0_operational_result_bundle_v1.json",sha256=paths[files.OUT+"/r0/r0_operational_result_bundle_v1.json"]),
        next_authorized_research_regime="R1_SHIFTED_UNSEEN",R1_executed=False,
        release_inventory_sha=hashlib.sha256(outputs[INVENTORY]).hexdigest(),Phase16="PHASE_16_NOT_DEFINED_IN_APPROVED_PLAN"))
    outputs[MANIFEST] = files.manifest_bytes(manifest)
    return outputs


def audit_inventory(root=files.ROOT):
    root = Path(root)
    inventory = files.read_json(root/INVENTORY)
    require(inventory["manifest_hash"] == digest({k:v for k,v in inventory.items() if k != "manifest_hash"}), "RELEASE_INVENTORY_SELF_HASH")
    records = inventory["records"]
    require(len({r["logical_role"] for r in records}) == len(records) == len({r["artifact_path"] for r in records}), "DUPLICATE_AUTHORITATIVE_ROLE_OR_PATH")
    require(set(ROLES.values()) <= {r["logical_role"] for r in records}, "MISSING_AUTHORITATIVE_ROLE")
    require(all(files.sha(files.contained(root,r["artifact_path"])) == r["sha256"] for r in records), "RELEASE_ARTIFACT_DRIFT")
    require((root/INVENTORY).read_bytes() == reconstruct(root)[INVENTORY], "RELEASE_INVENTORY_CONFLICT")
    return {"status":"PASS","hash_checks":len(records),"unique_authoritative_roles":len(ROLES)}


def freeze():
    root = files.ROOT
    require(lock.git("rev-parse","HEAD").decode().strip() == PHASE15, "PHASE15_COMMIT_GATE")
    outputs = reconstruct(root)
    require(not any((root/p).exists() for p in (*outputs,HASHES)), "REFUSE_RELEASE_OVERWRITE")
    for p,b in outputs.items():
        (root/p).parent.mkdir(parents=True,exist_ok=True)
        with (root/p).open("xb") as stream: stream.write(b)
    inventory = dict(artifact_version="phase17_18_artifact_hashes_v1",phase15_commit=PHASE15,
        sha256={p:files.sha(root/p) for p in (*outputs,*DOCS,*CODE)})
    with (root/HASHES).open("xb") as stream: stream.write(files.manifest_bytes(inventory))
    return audit_inventory(root)


def check(root=files.ROOT):
    root = Path(root)
    inventory = files.read_json(root/HASHES)["sha256"]
    require(all(files.sha(root/p) == h for p,h in inventory.items()), "PHASE17_18_ARTIFACT_DRIFT")
    require(all((root/p).read_bytes() == b for p,b in reconstruct(root).items()), "RELEASE_RECONSTRUCTION_DRIFT")
    return dict(**audit_inventory(root),byte_identical=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode",choices=("freeze","check"),default="check")
    print(json.dumps(freeze() if parser.parse_args().mode == "freeze" else check(),indent=2))
