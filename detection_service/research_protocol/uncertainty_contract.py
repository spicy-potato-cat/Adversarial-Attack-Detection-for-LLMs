"""Synthetic-only freeze/check gate for Phases 11 and 12."""

import argparse
from copy import deepcopy
import json
from pathlib import Path

from detection_service.research_protocol import detector_semantics as files
from detection_service.research_protocol.adapters import FrozenDetectorContracts
from detection_service.research_protocol.alignment import bind_predictions
from detection_service.research_protocol.core_metrics_contract import align_fixture, synthetic_core, synthetic_r2, check as prior_check
from detection_service.research_protocol.cross_regime import cross_regime_contract, cross_regime_matrix, result_bundle
from detection_service.research_protocol.regime import RegimeManifest, create_manifest, require
from detection_service.research_protocol.uncertainty import BootstrapConfig, bootstrap_metrics, uncertainty_contract

U = files.OUT + "/uncertainty"
C = files.OUT + "/cross_regime"
HASHES = files.OUT + "/phase11_12_artifact_hashes_v1.json"
CODE = tuple("detection_service/research_protocol/"+p for p in
    ("metric_catalog.py","uncertainty.py","cross_regime.py","uncertainty_contract.py")) + (
    "detection_service/tests/test_uncertainty.py","detection_service/tests/test_cross_regime.py")


def fixtures(contracts):
    sample = synthetic_core(contracts)
    lineage = deepcopy(sample)
    for row in lineage["manifest"]["samples"]:
        if row["truth_label"]:
            row["lineage_id"] = "cluster-"+str(int(row["sample_id"][-3:],2)//2)
    lineage["manifest"] = create_manifest(**lineage["manifest"]).model_dump(mode="json")
    lineage["prediction_binding"] = bind_predictions(RegimeManifest.model_validate_json(json.dumps(lineage["manifest"]))).model_dump(mode="json")
    paired = deepcopy(sample)
    for row in paired["explicit_decisions"]:
        if row["sample_id"] == "core-attack-111" and row["detector_id"] == "ds_v2":
            row["decision"] = 1
    r2 = synthetic_r2(contracts)[0]
    return dict(sample=sample,lineage=lineage,sparse_recovery=sample,paired_candidate=paired,r2=r2)


def regime_fixtures(contracts):
    f = fixtures(contracts)
    result = []
    for name in ("R0","R1","R2-D_S","R2-D_M-B","R2-D_G","R3"):
        bundle = deepcopy(f["r2"] if name.startswith(("R2","R3")) else f["sample"])
        payload = bundle["manifest"]
        if name.startswith("R2-"):
            payload["samples"] = [s for s in payload["samples"] if s["target_detector"] == name[3:]]
            parent_ids = {s["parent_sample_id"] for s in payload["samples"]}
            payload["external_parents"] = [p for p in payload["external_parents"] if p["sample_id"] in parent_ids]
        if name in ("R1","R3"):
            payload["threat_regime"] = "R1_SHIFTED_UNSEEN" if name=="R1" else "R3_ENSEMBLE_TARGETED"
            for row in payload["samples"]:
                row["threat_regime"] = payload["threat_regime"]
                if name=="R3":
                    row["target_detector"] = "ALL"
        ids = {s["sample_id"] for s in payload["samples"]}
        bundle["predictions"] = [p for p in bundle["predictions"] if p["sample_id"] in ids]
        bundle["explicit_decisions"] = [p for p in bundle["explicit_decisions"] if p["sample_id"] in ids]
        # create_manifest recalculates membership hashes and counts.
        payload.pop("sample_count",None)
        payload.pop("attack_count",None)
        payload.pop("benign_count",None)
        bundle["manifest"] = create_manifest(**payload).model_dump(mode="json")
        manifest = RegimeManifest.model_validate_json(json.dumps(bundle["manifest"]))
        bundle["prediction_binding"] = bind_predictions(manifest).model_dump(mode="json")
        result.append(result_bundle(align_fixture(bundle,contracts),manifest,"HISTORICAL_DESCRIPTIVE_3PCT_V1"))
    return tuple(result)


def build(root=files.ROOT):
    contracts = FrozenDetectorContracts(root)
    f = fixtures(contracts)
    tables = {k:align_fixture(v,contracts) for k,v in f.items()}
    metrics = ("pair/ds_v2/dm_b_v1/jfn","pair/ds_v2/dm_b_v1/ejf","pair/ds_v2/dm_b_v1/fn_jaccard",
        "all_three/jfn","recovery/ds_v2/unique_catch_rate","recovery/ds_v2/conditional_recovery")
    expected = {}
    for name in ("sample","lineage"):
        config = BootstrapConfig(unit="SAMPLE_PAIRED" if name=="sample" else "LINEAGE_CLUSTERED",domain="ATTACK_ONLY")
        expected[name] = bootstrap_metrics(tables[name],metrics,config).model_dump(mode="json")
    config = BootstrapConfig(unit="SAMPLE_PAIRED",domain="ATTACK_ONLY")
    expected["paired_delta"] = bootstrap_metrics(tables["paired_candidate"],("all_three/jfn",),config,paired_reference=tables["sample"]).model_dump(mode="json")
    config = BootstrapConfig(unit="LINEAGE_CLUSTERED",domain="VALID_TARGET_ATTEMPTS",target_detector="D_S")
    expected["r2"] = bootstrap_metrics(tables["r2"],("target/ds_v2/evasion","transfer/ds_v2/dm_b_v1/etr"),config).model_dump(mode="json")
    bundles = regime_fixtures(contracts)
    return {U+"/uncertainty_contract_v1.json":uncertainty_contract(),
        U+"/synthetic_sample_bootstrap_fixture_v1.json":dict(fixture_version="bootstrap_fixture_v1",sample=f["sample"],sparse_recovery=f["sparse_recovery"],paired_candidate=f["paired_candidate"]),
        U+"/synthetic_lineage_bootstrap_fixture_v1.json":dict(fixture_version="bootstrap_fixture_v1",lineage=f["lineage"],r2=f["r2"]),
        U+"/synthetic_bootstrap_expected_v1.json":expected,
        C+"/cross_regime_contract_v1.json":cross_regime_contract(),
        C+"/synthetic_regime_bundles_v1.json":[b.model_dump(mode="json") for b in bundles],
        C+"/synthetic_cross_regime_expected_v1.json":dict(complete=cross_regime_matrix(bundles,reference_slot="R0"),r0_only=cross_regime_matrix(bundles[:1],reference_slot="R0"))}


def freeze(root=files.ROOT):
    root = Path(root)
    prior_check(root)
    artifacts = build(root)
    require(not any((root/p).exists() for p in (*artifacts,HASHES)),"REFUSE_PHASE11_12_OVERWRITE")
    for p,value in artifacts.items():
        path = root/p
        path.parent.mkdir(parents=True,exist_ok=True)
        with path.open("xb") as stream:
            stream.write(files.manifest_bytes(value))
    inventory = dict(artifact_version="phase11_12_artifact_hashes_v1",sha256={p:files.sha(root/p) for p in (*artifacts,*CODE)})
    with (root/HASHES).open("xb") as stream:
        stream.write(files.manifest_bytes(inventory))
    return dict(status="PASS",hash_checks=len(inventory["sha256"]),real_R0_import=False)


def check(root=files.ROOT):
    root = Path(root)
    prior_check(root)
    inventory = files.read_json(root/HASHES)["sha256"]
    artifacts = build(root)
    require(set(inventory) == set(artifacts)|set(CODE),"PHASE11_12_INVENTORY_CONFLICT")
    require(all(files.sha(root/p)==s for p,s in inventory.items()),"PHASE11_12_HASH_MISMATCH")
    require(all((root/p).read_bytes()==files.manifest_bytes(value) for p,value in artifacts.items()),"PHASE11_12_NONDETERMINISM")
    return dict(status="PASS",hash_checks=len(inventory),real_R0_import=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode",choices=("freeze","check"),default="check")
    print(json.dumps(freeze() if parser.parse_args().mode=="freeze" else check(),indent=2))
