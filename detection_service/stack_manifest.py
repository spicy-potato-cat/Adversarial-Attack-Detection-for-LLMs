"""Metadata-only candidate stack freeze; never imports or executes detectors."""

import hashlib
from importlib.metadata import version
import json
import math
from pathlib import Path, PurePosixPath
import platform

ROOT = Path(__file__).resolve().parents[1]
START = "8c8e53d985d931eaa30672d866aab47d01c28bd7"
STACK_ID = "research_stack_candidate_v2"
OUT = ROOT / "artifacts/stack"
MANIFEST = STACK_ID + ".json"
CHECKSUM = STACK_ID + ".sha256"
INTEGRITY = "stack_integrity_v1.json"
BASELINE = "artifacts/quality/quality_001/baseline_preservation_v1.json"
BASELINE_SHA = "4b42dd44f2604f12e099f1fc60decef866c64d036c9a6554fcd3e049513b8a21"
DS = "artifacts/statistical_v2/final"
DS_CAL = "artifacts/statistical_v2/calibration/completed_v1"
DM = "artifacts/models/dm_b_v1"
DG = "artifacts/models/dg_v1"
B2_SHA = "93d3892b158c35eccfadc27c879754db69ea5293782492ee5d4ff01a33bff983"
DG_REV = "11614a155199674a0a95e6602d6ab0417b790ed0"
DM_REV = "fb53ab8802853c8e4fbdbcd0529f21fc6f459b2b"
DS_BINDING = {
    "ds_v2_model.json": "c5e754dc8b6e88b7437e4b81016e8f8ec23d018607d4f4e78906212b2a561157",
    "ds_v2_feature_reference.json": "fd26774585223913d12b8c20556a8fc1a50fa5dea7a3a75068a7bb30efce76ec",
    "ds_v2_model_manifest_v1.json": "8b62666f713c47c6f35fceb3a153a6da80de6081654d0b552bd882e8750c4aa1",
    "ds_v2_training_metadata_v1.json": "5dcbf8c45180612b2a20d9879c7ccb1d80bfd6d6055d4e7a80f85420d98d1839",
    "ds_v2_integrity_v1.json": "3465236b57a89b8b1c4f148e45dec192d2b295e6baefc0226402160d6f2740a9",
}
DS_CAL_SHA = "964cea57d98673d2026fb2f0e9d5884aec61a653e726847e0fb6ccbf36e95f23"
DS_CAL_BINDING = {
    "ds_v2_cal_v1.json": DS_CAL_SHA,
    "ds_v2_calibration_manifest_v1.json": "6ad2a6d42a81f4b51f2390bc14a126dfe9236b3c04b01e4eabbc0c3479d54d94",
    "ds_v2_calibration_metrics_v1.json": "72fd28a8f89a08b8fe2921fb3b73152a69dce727e0ea1a05ca07ab18f4de15ab",
    "ds_v2_calibration_integrity_v1.json": "05729c90b0485444a6268151b488eb5cb8f13bc696731475f0a856bd1fb764f9",
}
CODE = ("detection_service/stack_manifest.py", "detection_service/scripts/freeze_research_stack.py",
        "detection_service/tests/test_stack_manifest.py")
DEFAULT = "DEVELOPMENT_DEFAULT_NOT_FINAL_OPERATING_POINT"
DIRECTION = "higher = more adversarial"


class StackIntegrityError(RuntimeError):
    pass


def require(condition, message):
    if not condition:
        raise StackIntegrityError(message)


def canonical_bytes(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                      allow_nan=False).encode("utf-8")


def canonical_sha256(value):
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def file_sha256(path):
    with Path(path).open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def artifact_path(root, name):
    relative = PurePosixPath(name)
    require(isinstance(name, str) and "\\" not in name and not relative.is_absolute()
            and ".." not in relative.parts and ":" not in name, "invalid artifact path")
    # Only frozen artifact/code namespaces; never dataset or forensic row tables.
    require(name.startswith(("artifacts/models/", DS + "/", DS_CAL + "/", "detection_service/app/",
            "detection_service/analysis/", "detection_service/.model-cache/", "detection_service/configs/"))
            or name in (*CODE, BASELINE), "non-artifact path forbidden")
    require(relative.suffix not in (".csv", ".parquet", ".jsonl", ".npy", ".npz"), "row/feature table forbidden")
    path = (Path(root) / name).resolve()
    require(path.is_relative_to(Path(root).resolve()), "artifact escapes workspace")
    return path


def read_json(path):
    def unique(pairs):
        obj = {}
        for key, value in pairs:
            require(key not in obj, "duplicate JSON key")
            obj[key] = value
        return obj
    def invalid(value):
        raise StackIntegrityError("non-finite JSON value: " + value)
    return json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=unique, parse_constant=invalid)


def verify_hashes(root, hashes):
    require(isinstance(hashes, dict) and bool(hashes), "empty artifact inventory")
    for name, expected in hashes.items():
        require(isinstance(expected, str) and len(expected) == 64 and all(c in "0123456789abcdef" for c in expected),
                "invalid expected SHA-256")
        path = artifact_path(root, name)
        require(path.is_file(), "missing artifact: " + name)
        require(file_sha256(path) == expected, "artifact hash drift: " + name)


def prefixed(prefix, hashes):
    return {prefix + "/" + key: value for key, value in hashes.items()}


def accepted_state(root):
    verify_hashes(root, {BASELINE: BASELINE_SHA})
    frozen = read_json(artifact_path(root, BASELINE))["sha256"]
    require(len(frozen) == 96, "baseline inventory mismatch")
    hashes = {BASELINE: BASELINE_SHA, **frozen, **prefixed(DS, DS_BINDING), **prefixed(DS_CAL, DS_CAL_BINDING)}
    verify_hashes(root, hashes)
    load = lambda path: read_json(artifact_path(root, path))
    ds = load(DS + "/ds_v2_model_manifest_v1.json")
    require(ds["detector_version"] == "ds_v2" and ds["representation"] == "B2"
            and ds["feature_count"] == len(set(ds["feature_names"])) == 26
            and ds["feature_schema_sha256"] == B2_SHA and ds["final_operating_point"] == "NOT_FROZEN",
            "D_S identity/schema drift")
    require(load(DS + "/ds_v2_integrity_v1.json") == {k: v for k, v in DS_BINDING.items() if k != "ds_v2_integrity_v1.json"},
            "D_S model integrity binding mismatch")
    ds_cal = load(DS_CAL + "/ds_v2_calibration_manifest_v1.json")
    require(ds_cal["model_binding"] == DS_BINDING and ds_cal["detector_version"] == "ds_v2"
            and ds_cal["calibration_version"] == "ds_v2_cal_v1"
            and ds_cal["feature_schema_sha256"] == B2_SHA and ds_cal["final_operating_point"] == "NOT_FROZEN"
            and ds_cal["partitions_fitted"] == ["CALIBRATION"], "D_S calibrator/model binding mismatch")
    ds_cal_hashes = load(DS_CAL + "/ds_v2_calibration_integrity_v1.json")
    require(ds_cal_hashes == {k: v for k, v in DS_CAL_BINDING.items() if k != "ds_v2_calibration_integrity_v1.json"},
            "D_S calibration integrity mismatch")
    ds_cal_hashes.update(DS_CAL_BINDING)
    hashes.update(prefixed(DS_CAL, ds_cal_hashes))
    hashes.update(ds["runtime_code_sha256"])
    hashes.update(prefixed(ds["reference_lm"]["snapshot_path"], ds["reference_lm"]["file_sha256"]))

    dm = load(DM + "/model_config.json")
    recipe = dm["recipe"]
    require(recipe["detector_id"] == "semantic_finetuned" and recipe["detector_version"] == "dm_b_v1"
            and recipe["upstream_model"] == "distilbert/distilroberta-base"
            and recipe["upstream_revision"] == recipe["tokenizer_revision"] == DM_REV
            and dm["training_status"] == "COMPLETE" and dm["label_mapping"] == {"benign": 0, "attack": 1},
            "D_M-B identity/revision drift")
    dm_binding = {**load(DM + "/integrity_manifest.json"), "integrity_manifest.json": frozen[DM + "/integrity_manifest.json"]}
    hashes.update(prefixed(DM, dm_binding))
    dm_cal = load(DM + "/calibration/calibration_metadata.json")
    require(dm_cal["frozen_model_sha256"] == dm_binding and dm_cal["detector_id"] == "semantic_finetuned"
            and dm_cal["detector_version"] == "dm_b_v1" and dm_cal["calibration_version"] == "dm_b_v1_cal_v1"
            and dm_cal["partitions_fitted"] == ["CALIBRATION"]
            and dm_cal["recipe"]["final_threshold"] == "NOT_FROZEN"
            and dm_cal["calibrator_sha256"] == frozen[DM + "/calibration/calibrator.json"],
            "D_M-B calibrator/model binding mismatch")
    require(load(DM + "/transformer/config.json")["id2label"] == {"0": "BENIGN", "1": "ATTACK"},
            "D_M-B score orientation mismatch")
    for path in (DS_CAL + "/ds_v2_cal_v1.json", DM + "/calibration/calibrator.json"):
        params = load(path)
        require(math.isfinite(params["slope"]) and params["slope"] > 0
                and math.isfinite(params["intercept"]) and params["epsilon"] == 1e-12, "invalid sigmoid mapping")

    dg = load(DG + "/freeze_metadata.json")
    guard = load(DG + "/model_config.json")
    require(dg["model_id"] == guard["model_id"] == "meta-llama/Llama-Prompt-Guard-2-22M"
            and dg["revision"] == dg["tokenizer_revision"] == guard["revision"] == guard["tokenizer_revision"] == DG_REV
            and dg["project_version"] == guard["detector_version"] == "dg_v1"
            and guard["detector_id"] == "guard_external" and dg["project_calibration"] is None
            and dg["long_input_policy"] == guard and guard["decision"] == "OR_of_native_chunk_argmax_class_1",
            "D_G identity/revision/native policy mismatch")
    require(load(DG + "/integrity_manifest.json") == {k: frozen[DG + "/" + k] for k in ("model_config.json", "freeze_metadata.json")},
            "D_G freeze integrity mismatch")
    hashes.update(prefixed(dg["snapshot_path"], dg["file_sha256"]))
    verify_hashes(root, hashes)
    return {"artifact_sha256": hashes, "ds": ds, "ds_cal": ds_cal, "ds_cal_hashes": ds_cal_hashes,
            "dm": dm, "dm_binding": dm_binding, "dm_cal": dm_cal, "dg": dg, "guard": guard}


def environment():
    return {"python": platform.python_version(), "packages": {p: version(p) for p in
            ("torch", "transformers", "numpy", "scikit-learn", "scipy", "tokenizers", "safetensors", "pydantic")}}


def build_manifest(root=ROOT, state=None):
    s = state if state is not None else accepted_state(root)
    common = {"score_direction": DIRECTION, "final_operating_threshold": "NOT_FROZEN",
              "vote_policy_status": DEFAULT, "input": "original_request.content.text_independently",
              "silent_fallback": False}
    return {"stack_id": STACK_ID, "stack_version": "2", "status": "FROZEN_CANDIDATE_NOT_FINAL_SYSTEM",
        "source_commit": START, "implementation_sha256": {p: file_sha256(artifact_path(root, p)) for p in CODE},
        "detector_order": ["D_S", "D_M-B", "D_G"],
        "detectors": [
            {**common, "role": "D_S", "detector_id": "statistical", "runtime_detector_id": "statistical_perplexity",
             "detector_version": "ds_v2", "representation": "B2", "feature_count": 26,
             "feature_schema_sha256": B2_SHA, "model_artifacts": prefixed(DS, DS_BINDING),
             "reference_lm": s["ds"]["reference_lm"], "input_policy": s["ds"]["extractor_config"],
             "reference_state": "FROZEN_BASE_TRAIN_ONLY_NO_INFERENCE_REFIT",
             "raw_score_semantics": "uncalibrated LR class1 probability",
             "calibration": {"version": "ds_v2_cal_v1", "state": "FROZEN", "path": DS_CAL,
                             "method": s["ds_cal"]["method"], "artifact_sha256": DS_CAL_SHA,
                             "model_binding": DS_BINDING},
             "compatibility_vote": "calibrated_probability >= 0.5"},
            {**common, "role": "D_M-B", "detector_id": "semantic_finetuned", "runtime_detector_id": "semantic_finetuned",
             "detector_version": "dm_b_v1", "model_artifacts": prefixed(DM, s["dm_binding"]),
             "upstream_model": "distilbert/distilroberta-base", "model_revision": DM_REV, "tokenizer_revision": DM_REV,
             "raw_score_semantics": "uncalibrated softmax class1 ATTACK probability",
             "input_policy": {k: s["dm"]["recipe"][k] for k in ("text_field", "max_sequence_length", "truncation_side", "padding_side", "padding")},
             "calibration": {"version": "dm_b_v1_cal_v1", "state": "FROZEN", "path": DM + "/calibration",
                             "method": s["dm_cal"]["calibration_method"], "artifact_sha256": s["dm_cal"]["calibrator_sha256"],
                             "model_binding": s["dm_binding"]},
             "compatibility_vote": "raw_score >= 0.5; calibration does not change native vote"},
            {**common, "role": "D_G", "detector_id": "guard_external", "runtime_detector_id": "guard_external",
             "detector_version": "dg_v1", "upstream_model": s["dg"]["model_id"], "model_revision": DG_REV,
             "tokenizer_revision": DG_REV, "model_artifacts": prefixed(s["dg"]["snapshot_path"], s["dg"]["file_sha256"]),
             "raw_score_semantics": "temperature1 class1 softmax; max across native chunks",
             "input_policy": s["guard"], "calibration": {"state": "NONE", "version": None, "artifact_sha256": None},
             "compatibility_vote": "OR_of_native_chunk_argmax_class_1; ties choose class0"}],
        "comparators": [{"detector_id": "semantic_embedding_lr", "detector_version": "dm_a_v1", "primary_member": False,
                         "role": "FROZEN_BASELINE_COMPARATOR_ONLY"}],
        "contract": {"field_mapping": {"detector_id": "stack alias from runtime_detector_id", "detector_version": "detector_version",
            "raw_score": "raw_score", "calibrated_probability": "calibrated_probability", "binary_prediction": "binary_vote",
            "latency_ms": "latency_ms", "metadata": "metadata"},
            "nullable_calibrated_probability": True, "failure": "typed exception or explicit non-success status; no substitution",
            "success_requires_valid_scores": True, "insufficient_input": "explicit status; no fabricated vote/score",
            "input_distribution": "pass original prompt independently to each detector; no cross-detector transformed input",
            "tokenization": "detector-specific; no shared tokenizer forced", "runtime_schema_unchanged": True},
        "decision_state": {"final_thresholds": "NOT_FROZEN", "ensemble_policy": "NOT_FROZEN",
            "verifier": "NOT_SELECTED", "routing": "NOT_IMPLEMENTED", "D_S_cycle_2": "DEFERRED"},
        "artifact_sha256": s["artifact_sha256"], "environment": environment(),
        "scope": {"datasets_accessed": False, "prompts_scored": False, "models_deserialized": False,
                  "training": False, "threshold_selection": False, "protected_experiments": False, "E1_E10": False}}


def verify_manifest(manifest, root=ROOT, expected_sha=None):
    try:
        digest = canonical_sha256(manifest)
        require(expected_sha is None or digest == expected_sha, "canonical manifest hash drift")
        require(manifest["detector_order"] == ["D_S", "D_M-B", "D_G"], "detector order drift")
        detectors = manifest["detectors"]
        require([d["role"] for d in detectors] == manifest["detector_order"], "primary membership/order drift")
        require(len({d["detector_id"] for d in detectors}) == 3, "duplicate detector IDs")
        require([d["detector_version"] for d in detectors] == ["ds_v2", "dm_b_v1", "dg_v1"], "detector version drift")
        require(all(d["score_direction"] == DIRECTION and d["final_operating_threshold"] == "NOT_FROZEN"
                    and d["vote_policy_status"] == DEFAULT and not d["silent_fallback"] for d in detectors), "score/threshold/fallback policy drift")
        expected = build_manifest(root)
        require(manifest == expected, "candidate manifest identity/artifact/contract drift")
        return {"status": "PASS", "canonical_sha256": digest, "artifact_hash_checks": len(expected["artifact_sha256"]),
                "original_baseline_hash_checks": 96, "primary_detectors": 3, "datasets_accessed": False,
                "prompts_scored": False, "models_deserialized": False}
    except StackIntegrityError:
        raise
    except Exception as exc:
        raise StackIntegrityError("stack unavailable or invalid; no fallback: " + str(exc)) from exc


def integrity_document(manifest, report, manifest_file_sha):
    return {**report, "stack_id": STACK_ID, "source_commit": START, "manifest_file_sha256": manifest_file_sha,
            "canonicalization": "UTF-8 JSON; sorted keys; compact separators; ensure_ascii=true; no NaN/Infinity; no trailing newline",
            "accepted_artifact_sha256": manifest["artifact_sha256"]}


def check_package(directory=OUT, root=ROOT):
    try:
        directory = Path(directory)
        manifest = read_json(directory / MANIFEST)
        report = verify_manifest(manifest, root, (directory / CHECKSUM).read_text(encoding="ascii").strip())
        require(read_json(directory / INTEGRITY) == integrity_document(manifest, report, file_sha256(directory / MANIFEST)),
                "stack integrity record drift")
        return report
    except StackIntegrityError:
        raise
    except Exception as exc:
        raise StackIntegrityError("stack package unavailable or invalid; no fallback: " + str(exc)) from exc
