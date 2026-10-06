"""Freeze/check Phase-3 schemas and adapter metadata, without running detectors."""

import argparse
import hashlib
from pathlib import Path

from detection_service.research_protocol import detector_semantics as phase2
from detection_service.research_protocol.adapters import FrozenDetectorContracts, PHASE2_SHA, RULE_IDS
from detection_service.research_protocol.prediction import METADATA_VERSION, SCHEMA_VERSION, STATUS_VALUES, prediction_schema

SCHEMA = phase2.OUT + "/schemas/prediction_schema_v1.json"
CONTRACT = phase2.OUT + "/adapter_contract_manifest_v1.json"
HASHES = phase2.OUT + "/phase3_artifact_hashes_v1.json"
CODE = ("detection_service/research_protocol/prediction.py", "detection_service/research_protocol/adapters.py",
        "detection_service/research_protocol/prediction_contract.py", "detection_service/tests/test_prediction_adapters.py")


def build_artifacts(root=phase2.ROOT):
    contracts = FrozenDetectorContracts(root)
    manifest = contracts._manifest
    schema = prediction_schema()
    schema["properties"]["detector_id"]["enum"] = [d["detector_id"] for d in manifest["detectors"]]
    for d in manifest["detectors"]:
        identity = {"detector_role": {"const": d["detector_role"]}, "model_revision": {"const": d["model_revision"]},
                    "model_hash": {"const": d["model_hash"]}, "native_decision_rule_id": {"const": RULE_IDS[d["stack_label"]]}}
        schema["allOf"].append({"if": {"properties": {"detector_id": {"const": d["detector_id"]}}},
                               "then": {"properties": identity}})
        schema["allOf"].append({"if": {"properties": {"detector_id": {"const": d["detector_id"]}, "status": {"const": "OK"}}},
                               "then": {"properties": {"calibrator_id": {"const": d["calibrator_id"]},
                                   "calibrated_score": {"type": "number" if d["calibrated_score_available"] else "null"}}}})
    schema_sha = hashlib.sha256(phase2.manifest_bytes(schema)).hexdigest()
    contract = {"contract_version": "adapter_contract_v1", "schema_version": SCHEMA_VERSION,
        "metadata_version": METADATA_VERSION, "phase2_manifest_path": phase2.OUT + "/" + phase2.NAME,
        "phase2_manifest_sha256": PHASE2_SHA, "prediction_schema_path": SCHEMA, "prediction_schema_sha256": schema_sha,
        "primary_detector_order": manifest["primary_detector_order"], "comparator_policy": "NO_PRIMARY_ADAPTER",
        "adapters": [{"stack_label": d["stack_label"], "detector_id": d["detector_id"], "detector_role": d["detector_role"],
            "phase2_identity_reference": "/detectors/" + str(i), "native_decision_rule_id": RULE_IDS[d["stack_label"]],
            "adapter_class": "DetectorAdapter", "module": CODE[1], "score_direction": d["canonical_score_direction"],
            "threshold_input_score_type": d["threshold_input_score_type"],
            "live_binding": "UNAVAILABLE_ACCEPTED_ARCHIVE_NOT_IMPORTABLE" if d["stack_label"] == "D_S" else "LAZY_FROZEN_LOADER_NOT_EXECUTED",
            "fixture_binding": "CONTRACT_ONLY", "existing_output_binding": "FROZEN_EVIDENCE",
            "operational_threshold_status": "NOT_FROZEN"} for i, d in enumerate(manifest["detectors"])],
        "statuses": STATUS_VALUES, "operational_fields": {k: None for k in
            ("operational_threshold", "operational_threshold_id", "operational_binary_prediction")},
        "token_accounting": {"D_S": "input: content tokens before cap; analyzed: unique next-token targets, excluding first; cap inherited from Phase 2",
            "D_M-B": "input/analyzed: native special-inclusive counts minus static frozen tokenizer boundary-token count; no padding",
            "D_G": "unique content tokens; never sum overlapping chunks", "truncated": "True only when frozen preprocessing discards content"},
        "latency": {"live": "wall-clock detect call, excluding lazy initialization; adaptation overhead excluded",
            "frozen": "accepted detector-reported measurement if present; otherwise null", "fixture": "null; never fabricate zero"},
        "existing_evidence_policy": "Hash-bound Phase-2 full-model JSON native outputs only; explicit JSON Pointer; no relabeling fold-local OOF with final-model hashes",
        "error_policy": "Null scores and native/operational decisions for every non-OK result; allowlisted diagnostic class, never exception text",
        "serialization": "UTF-8 sorted compact JSON; ensure_ascii=true; allow_nan=false; no trailing newline",
        "scope": {"detector_execution": False, "dataset_scoring": False, "threshold_selection": False,
            "R0_rescoring": False, "R1_R2_R3": False, "Cycle_2": False, "Phase_4": False}}
    return {SCHEMA: schema, CONTRACT: contract}


def expected_hashes(root, artifacts):
    return {"artifact_version": "phase3_artifact_hashes_v1", "phase2_manifest_sha256": PHASE2_SHA,
            "sha256": {**{p: hashlib.sha256(phase2.manifest_bytes(v)).hexdigest() for p, v in artifacts.items()},
                       **{p: phase2.sha(Path(root) / p) for p in CODE}}}


def check(root=phase2.ROOT):
    artifacts = build_artifacts(root)
    hashes = expected_hashes(root, artifacts)
    phase2.require(phase2.read_json(Path(root) / HASHES) == hashes, "Phase-3 hash inventory drift")
    for name, value in artifacts.items():
        phase2.require((Path(root) / name).read_bytes() == phase2.manifest_bytes(value), "Phase-3 deterministic artifact drift")
    return {"status": "PASS", "schema_sha256": hashes["sha256"][SCHEMA], "adapter_contract_sha256": hashes["sha256"][CONTRACT],
            "hash_inventory_sha256": phase2.sha(Path(root) / HASHES), "artifact_hash_checks": len(hashes["sha256"]),
            "phase2_manifest_unchanged": True}


def freeze(root=phase2.ROOT):
    artifacts = build_artifacts(root)
    artifacts[HASHES] = expected_hashes(root, artifacts)
    for name, value in artifacts.items():
        path = Path(root) / name
        content = phase2.manifest_bytes(value)
        if path.exists():
            phase2.require(path.read_bytes() == content, "refuse to overwrite different Phase-3 frozen bytes")
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("xb") as stream:
                stream.write(content)
    return check(root)


if __name__ == "__main__":
    import json
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("freeze", "check"), default="check")
    args = parser.parse_args()
    print(json.dumps(freeze() if args.mode == "freeze" else check(), indent=2))
