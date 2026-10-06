"""Phase-2 static inventory. Never imports detectors or opens dataset payloads."""

import argparse
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import subprocess

ROOT = Path(__file__).resolve().parents[2]
BASE = "dc6dd3041643fb70ad5b128d32c246f8763a8044"
PRESERVED_COMMIT = "e6b6a2af2a78e2a31aae6d9377378993f678b073"
BACKUP = "detection_service/outputs/common003-preserved-stack"
PRESERVATION = "artifacts/common_mode/development/completion_v3/publication/frozen_stack_preservation_v1.json"
PRESERVATION_SHA = "3d48225805cd789200a618b6547ff6bd781cfcb2bbf8c09efd662165436352f5"
STACK = "artifacts/stack/research_stack_candidate_v2.json"
STACK_SHA = "dce1392430198894247ca318d6c2627f024ef403742d2a0779bb7b7606847110"
DS = "artifacts/statistical_v2/final"
DS_CAL = "artifacts/statistical_v2/calibration/completed_v1"
DM = "artifacts/models/dm_b_v1"
DG = "artifacts/models/dg_v1"
DS_REV = "2290a62682d06624634c1f46a6ad5be0f47f38aa"
DM_REV = "fb53ab8802853c8e4fbdbcd0529f21fc6f459b2b"
DG_REV = "11614a155199674a0a95e6602d6ab0417b790ed0"
B2_SHA = "93d3892b158c35eccfadc27c879754db69ea5293782492ee5d4ff01a33bff983"
MODEL_HASHES = (
    "c5e754dc8b6e88b7437e4b81016e8f8ec23d018607d4f4e78906212b2a561157",
    "0bb192d2c468530479fa8ec0786f35d8bf5a8287e4ee401a953292d221736844",
)
REFERENCE_SHA = "fd26774585223913d12b8c20556a8fc1a50fa5dea7a3a75068a7bb30efce76ec"
CAL_HASHES = (
    "964cea57d98673d2026fb2f0e9d5884aec61a653e726847e0fb6ccbf36e95f23",
    "7af044ff8e0e29020450bffa93f92c973da4cc4a4888067d88938eefbb2566b9",
)
DIRECTION = "HIGHER_IS_MORE_ADVERSARIAL"
ORDER = ["D_S", "D_M-B", "D_G"]
OUT = "artifacts/research_protocol"
NAME = "detector_set_manifest_v1.json"


class SemanticsIntegrityError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise SemanticsIntegrityError(message)


def read_json(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, "duplicate JSON key: " + key)
            result[key] = value
        return result

    def invalid(value):
        raise SemanticsIntegrityError("non-finite JSON constant: " + value)

    return json.loads(Path(path).read_text(encoding="utf-8"),
                      object_pairs_hook=unique, parse_constant=invalid)


def canonical_bytes(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("utf-8")


def manifest_bytes(value):
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=True,
                       allow_nan=False) + "\n").encode("utf-8")


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def contained(root, relative):
    p = PurePosixPath(relative)
    require(not p.is_absolute() and ".." not in p.parts and ":" not in relative
            and "\\" not in relative, "invalid relative evidence path")
    require(not any(x in relative.lower() for x in ("cycle2", "cycle_2", "failure_atlas", "stat008", "stat009")),
            "Cycle-2 artifact forbidden")
    path = (Path(root) / relative).resolve()
    require(path.is_relative_to(Path(root).resolve()), "evidence path escapes workspace")
    return path


def verify_evidence(root=ROOT):
    root = Path(root).resolve()
    preservation_path = contained(root, PRESERVATION)
    require(sha(preservation_path) == PRESERVATION_SHA, "accepted preservation inventory drift")
    preservation = read_json(preservation_path)
    require(preservation["source_commit"] == PRESERVED_COMMIT, "preserved code provenance drift")

    # Explicit accepted archive locations, not a runtime fallback or auto-merge.
    def locate(name):
        if name in preservation["files"]:
            return contained(root, BACKUP + "/" + name)
        return contained(root, name)

    stack_path = locate(STACK)
    require(sha(stack_path) == preservation["files"][STACK]["sha256"], "stack file-byte hash drift")
    stack = read_json(stack_path)
    require(hashlib.sha256(canonical_bytes(stack)).hexdigest() == STACK_SHA,
            "canonical stack hash drift")
    require(locate(STACK.replace(".json", ".sha256")).read_text(encoding="ascii").strip() == STACK_SHA,
            "stack checksum drift")
    require(stack["detector_order"] == ORDER, "accepted stack order drift")
    ds = read_json(locate(DS + "/ds_v2_model_manifest_v1.json"))
    hashes = {}

    def add(entries):
        for name, expected in entries.items():
            require(name not in hashes or hashes[name] == expected, "conflicting accepted evidence: " + name)
            hashes[name] = expected

    add(stack["artifact_sha256"])
    add(stack["implementation_sha256"])
    add(ds["runtime_code_sha256"])
    add({k: v["sha256"] for k, v in preservation["files"].items()})
    locators = {}
    for name, expected in sorted(hashes.items()):
        require(len(expected) == 64 and all(c in "0123456789abcdef" for c in expected), "invalid digest")
        path = locate(name)
        require(path.is_file(), "missing accepted evidence: " + name)
        require(sha(path) == expected, "accepted artifact hash mismatch: " + name)
        active = contained(root, name)
        if name in preservation["files"] and active.is_file():
            require(sha(active) == expected, "active/preserved evidence disagreement: " + name)
        locators[name] = {"local_path": path.relative_to(root).as_posix(), "sha256": expected,
                          "storage": "ACCEPTED_LOCAL_ARCHIVE" if name in preservation["files"] else "ACTIVE_WORKSPACE"}

    # Check the preserved runtime against accepted Git history without executing it.
    for name in ds["runtime_code_sha256"]:
        if name in preservation["files"]:
            blob = subprocess.check_output(["git", "show", PRESERVED_COMMIT + ":" + name], cwd=root)
            require(hashlib.sha256(blob).hexdigest() == hashes[name], "preserved Git implementation differs: " + name)
    baseline = read_json(root / "artifacts/quality/quality_001/baseline_preservation_v1.json")["sha256"]
    require(len(baseline) == 96 and all(hashes.get(k) == v for k, v in baseline.items()),
            "96-file baseline preservation binding drift")
    return stack, ds, locators, locate


def build_manifest(root=ROOT):
    stack, ds, locators, locate = verify_evidence(root)
    ds_train = read_json(locate(DS + "/ds_v2_training_metadata_v1.json"))
    ds_model = read_json(locate(DS + "/ds_v2_model.json"))
    ds_cal = read_json(locate(DS_CAL + "/ds_v2_calibration_manifest_v1.json"))
    dm = read_json(locate(DM + "/model_config.json"))
    dm_train = read_json(locate(DM + "/training_metadata.json"))
    dm_cal = read_json(locate(DM + "/calibration/calibration_metadata.json"))
    dg = read_json(locate(DG + "/freeze_metadata.json"))
    guard = read_json(locate(DG + "/model_config.json"))
    accepted = stack["detectors"]
    require([d["detector_version"] for d in accepted] == ["ds_v2", "dm_b_v1", "dg_v1"], "detector identity drift")
    require(ds["feature_count"] == len(set(ds["feature_names"])) == 26 and
            ds["feature_schema_sha256"] == B2_SHA and ds["reference_lm"]["revision"] == DS_REV,
            "D_S representation/reference drift")
    expected_lr = {"penalty": "l2", "C": 1.0, "class_weight": "balanced", "solver": "lbfgs",
                   "random_state": 1701, "tol": 0.0001, "max_iter": 20000}
    require(all(ds_model["recipe"].get(k) == v for k, v in expected_lr.items()) and
            ds_model["classes"] == [0, 1] and ds_train["recipe"] == ds_model["recipe"] and
            ds_train["n_iter"] == [5492] and ds_train["converged"] is True, "D_S scorer/convergence drift")
    require(ds_cal["model_binding"] == {p.rsplit("/", 1)[1]: h for p, h in accepted[0]["model_artifacts"].items()} and
            ds_cal["detector_version"] == "ds_v2" and ds_cal["calibration_version"] == "ds_v2_cal_v1" and
            ds_cal["partitions_fitted"] == ["CALIBRATION"], "D_S calibrator binding drift")
    require(dm_cal["frozen_model_sha256"] == {p.removeprefix(DM + "/"): h for p, h in accepted[1]["model_artifacts"].items()} and
            dm_cal["detector_version"] == "dm_b_v1" and dm_cal["calibration_version"] == "dm_b_v1_cal_v1" and
            dm_cal["partitions_fitted"] == ["CALIBRATION"], "D_M-B calibrator binding drift")
    require(dm["recipe"] == dm_train["recipe"] and dm["recipe"]["upstream_revision"] == DM_REV and
            dm["recipe"]["tokenizer_revision"] == DM_REV and dm["label_mapping"] == {"benign": 0, "attack": 1},
            "D_M-B recipe/orientation drift")
    require(dm_train["base_train_count"] == 1135 and dm_train["class_counts"] == {"0": 952, "1": 183}
            and not dm_train["calibration_used"] and not dm_train["protected_data_used"]
            and not dm_train["validation_used_for_training"], "D_M-B training partition evidence drift")
    require({k: dm["recipe"][k] for k in ("epochs", "optimizer", "learning_rate", "batch_size", "seed")} ==
            {"epochs": 3, "optimizer": "AdamW", "learning_rate": 2e-5, "batch_size": 8, "seed": 1701}, "D_M-B training drift")
    require(dg["revision"] == dg["tokenizer_revision"] == DG_REV and dg["project_calibration"] is None and
            guard == dg["long_input_policy"] == accepted[2]["input_policy"] and
            dg["documented_class_meaning"] == {"0": "benign", "1": "malicious_instruction_override_attempt"},
            "D_G identity/class/policy drift")

    def local(name):
        return locators[name]["local_path"]

    def record(index, detector_id, role, module, class_name, config, model_path, revision):
        native = accepted[index]
        require(native["score_direction"] == "higher = more adversarial" and
                native["final_operating_threshold"] == "NOT_FROZEN", "accepted score/threshold policy drift")
        return {
            "stack_label": ORDER[index], "detector_id": detector_id, "detector_role": role,
            "runtime_detector_id": native["runtime_detector_id"], "primary_stack_member": True,
            "implementation_path": local(module), "implementation_logical_path": module,
            "implementation_revision": revision, "implementation_sha256": locators[module]["sha256"],
            "implementation_class": class_name, "inference_entry_point": class_name + ".detect",
            "configuration_path": local(config), "model_artifact_path": local(model_path),
            "model_name": native.get("upstream_model"), "model_revision": native.get("model_revision"),
            "model_hash": locators[model_path]["sha256"],
            "reference_model_name": None, "reference_model_revision": None, "reference_hash": None,
            "calibrator_id": native["calibration"]["version"], "calibrator_hash": native["calibration"]["artifact_sha256"],
            "calibrator_artifact": None, "calibrator_input": None, "calibrator_output": None,
            "calibrator_output_range": None, "calibrator_represents_probability": False,
            "native_score_name": "raw_score", "native_score_range": [0, 1], "native_score_direction": DIRECTION,
            "canonical_score_direction": DIRECTION, "direction_normalization_required": False,
            "direction_status": "CANONICAL_DIRECTION_ALREADY_NATIVE", "future_direction_transform": None,
            "calibrated_score_available": index != 2, "ranking_input_score_type": "raw_score",
            "operational_threshold_status": "NOT_FROZEN", "operational_threshold": None,
            "tokenizer_name": native.get("upstream_model"), "tokenizer_revision": native.get("tokenizer_revision"),
            "artifact_integrity_status": "PASS", "notes": [],
        }

    statistical = record(0, "ds_v2", "PRIMARY_STATISTICAL",
        "detection_service/app/detectors/statistical_v2/detector.py", "B2StatisticalDetector",
        DS + "/ds_v2_model_manifest_v1.json", DS + "/ds_v2_model.json", PRESERVED_COMMIT)
    statistical.update(
        model_name="B2 statistical representation + LogisticRegression", model_revision=None,
        reference_model_name=ds["reference_lm"]["model_id"], reference_model_revision=DS_REV,
        reference_hash=locators[DS + "/ds_v2_feature_reference.json"]["sha256"],
        reference_artifact_path=local(DS + "/ds_v2_feature_reference.json"),
        reference_lm_snapshot=ds["reference_lm"], scorer_configuration=expected_lr,
        full_training_iterations=ds_train["n_iter"][0], training_partition="BASE_TRAIN",
        feature_schema_version=ds["feature_schema_version"], feature_count=26,
        feature_names=ds["feature_names"], feature_schema_sha256=B2_SHA,
        feature_extraction_entry_point="References.transform(item, 'B2')",
        feature_extraction_path="detection_service/analysis/statistical_feature_ablation.py",
        native_score_definition="sigmoid(B2_features @ LR_coefficients + LR_intercept); class 1 ATTACK probability; uncalibrated",
        adversarial_class={"index": 1, "meaning": "attack"},
        score_extraction_location="B2StatisticalDetector.detect -> B2Model.transform -> B2Model.predict",
        binary_decision_location="B2StatisticalDetector.detect",
        model_loader="B2StatisticalDetector.from_artifact; B2Model.load; load_calibration",
        calibrator_artifact=local(DS_CAL + "/ds_v2_cal_v1.json"),
        calibrator_method=ds_cal["method"], calibrator_input=ds_cal["recipe"]["input"],
        calibrator_output="sigmoid(slope * logit(clip(raw_score, epsilon, 1-epsilon)) + intercept)",
        calibrator_output_range=[0, 1], calibrator_represents_probability=True,
        calibration_binding=ds_cal["model_binding"], threshold_input_score_type="calibrated_probability",
        native_binary_rule="calibrated_probability >= 0.5; without calibrator, raw_score >= 0.5",
        native_threshold=None, default_threshold=0.5, default_threshold_status="DEVELOPMENT_CONVENIENCE",
        tokenizer_name=ds["reference_lm"]["model_id"], tokenizer_revision=DS_REV,
        context_length=1024, project_input_limit=ds["extractor_config"]["max_analysis_tokens"],
        truncation_policy="Keep first 4096 content tokens; tokenize without truncation or added special tokens; first token is unscored",
        chunking_policy={"context_tokens": 1024, "overlap": 64, "stride": 960,
            "tail_handling": "full retained-prefix tail; next-token positions scored once; overlapping context discarded from repeated targets"},
        aggregation_policy="Per-token negative natural-log next-token probabilities; logits[:, :-1] predict IDs[:, 1:]; concatenate unique targets; 128-token feature windows, stride 64, partial tail retained",
        b2_feature_semantics="10 inherited features + 6 frozen length-conditioned benign-reference features + 10 distributional surprisal features; no inference-time refit/scaler/imputation",
        insufficient_input_policy="Fewer than two content tokens: insufficient_input, no score or binary vote",
        notes=["reference_hash identifies the B2 feature-reference artifact, not LM weights; separate per-file LM hashes retained",
            "Final D_S code/artifacts are only in the accepted local archive and Git source revision; not importable at logical active-tree entry point. This inventory does not integrate them.",
            "R0 uses fold-local B2+LR raw OOF scores, not the final full-BASE_TRAIN model or calibrator."])

    semantic = record(1, "dm_b_v1", "PRIMARY_SEMANTIC",
        "detection_service/app/detectors/semantic_finetuned/detector.py", "FineTunedSemanticDetector",
        DM + "/model_config.json", DM + "/transformer/model.safetensors", BASE)
    semantic.update(
        native_score_definition="softmax(sequence_classifier_logits)[:, 1]; uncalibrated ATTACK probability",
        adversarial_class={"index": 1, "serialized_label": "ATTACK", "benign_index": 0, "benign_label": "BENIGN"},
        score_extraction_location="FineTunedSemanticDetector.detect_batch",
        binary_decision_location="FineTunedSemanticDetector.detect_batch: score >= 0.5",
        model_loader="FineTunedSemanticDetector.from_artifact",
        calibrator_artifact=local(DM + "/calibration/calibrator.json"),
        calibrator_method=dm_cal["calibration_method"], calibrator_input=dm_cal["input_score_definition"],
        calibrator_output="sigmoid(slope * logit(clip(raw_score, epsilon, 1-epsilon)) + intercept)",
        calibrator_output_range=[0, 1], calibrator_represents_probability=True,
        calibration_binding=dm_cal["frozen_model_sha256"], threshold_input_score_type="raw_score",
        native_binary_rule="raw_score >= 0.5; calibrator never changes native binary_vote",
        native_threshold=None, default_threshold=0.5, default_threshold_status="DEVELOPMENT_CONVENIENCE",
        context_length=dm["recipe"]["model_context_length"], project_input_limit=dm["recipe"]["max_sequence_length"],
        truncation_policy="Right truncation at 256 tokens including special tokens; right padding to longest in batch",
        chunking_policy=None, aggregation_policy="One sequence softmax; no chunk aggregation",
        special_token_policy="add_special_tokens=True; RoBERTa single-sequence boundary tokens included in 256-token budget; padding excluded from counts",
        training_evidence={"partition": "BASE_TRAIN", **{k: dm["recipe"][k] for k in ("epochs", "optimizer", "learning_rate", "batch_size", "seed")}},
        notes=["512 usable context; transformer config has 514 positional embeddings. Project limit remains 256.",
            "Raw and calibrated values are probabilities by implementation; no claim of perfect calibration.",
            "R0 ranking/points use raw OOF scores; not full-model calibrated inference."])

    external = record(2, "dg_v1", "PRIMARY_EXTERNAL_GUARD",
        "detection_service/app/detectors/guard/detector.py", "GuardDetector",
        DG + "/model_config.json", dg["snapshot_path"] + "/model.safetensors", BASE)
    external.update(
        native_score_definition="max over chunks of temperature-1 softmax(logits)[:, 1]",
        adversarial_class={"index": guard["positive_class"], "serialized_label": "LABEL_1",
            "meaning": dg["documented_class_meaning"]["1"], "benign_index": 0, "benign_label": "LABEL_0",
            "evidence_url": dg["label_evidence"], "evidence_commit": dg["label_evidence_commit"],
            "evidence_sha256": dg["label_evidence_sha256"]},
        score_extraction_location="GuardDetector._detect: logits.float().softmax(dim=-1)[:, 1]; maximum across chunks",
        binary_decision_location="GuardDetector._detect: OR(decision == config.positive_class)",
        model_loader="GuardDetector.from_artifact -> guard.model.load_frozen",
        threshold_input_score_type="native_chunk_argmax", native_binary_rule="OR over chunk logits.argmax == class 1; ties choose class 0",
        native_threshold=None, default_threshold=None, default_threshold_status="NATIVE_MODEL_DECISION",
        context_length=guard["context_tokens"], project_input_limit=None,
        truncation_policy="No input truncation; preserve upstream tokenizer normalization, slice token IDs without decode/re-encode",
        chunking_policy={"content_tokens": guard["chunk_tokens"], "special_tokens": guard["special_tokens"],
            "overlap": guard["overlap_tokens"], "stride": guard["chunk_tokens"] - guard["overlap_tokens"],
            "tail_handling": "full tail coverage"},
        aggregation_policy={"raw_score": "max_chunk_malicious_probability", "binary_vote": "OR_of_native_chunk_argmax_class_1"},
        special_token_policy="Tokenize content without specials; each chunk receives CLS=1 and SEP=2; PAD=0; upstream fast tokenizer",
        snapshot_file_sha256=dg["file_sha256"], snapshot_global_sha256=None,
        insufficient_input_policy="Zero content tokens: insufficient_input; null raw_score and binary_vote",
        notes=["Model name is 22M; serialized architecture is DebertaV2ForSequenceClassification. Provider labels are generic; class meaning is supported by frozen provider evidence.",
            "No project calibration. Native binary decision is not raw_score >= 0.5: exact ties are benign.",
            "model_hash is the weights file hash, not an invented global snapshot hash."])

    for index, detector in enumerate((statistical, semantic)):
        require(detector["model_hash"] == MODEL_HASHES[index] and detector["calibrator_hash"] == CAL_HASHES[index],
                "authoritative model/calibration SHA drift")
        params = read_json(locate(DS_CAL + "/ds_v2_cal_v1.json" if index == 0 else DM + "/calibration/calibrator.json"))
        require(params["epsilon"] == 1e-12 and math.isfinite(params["slope"]) and params["slope"] > 0 and
                math.isfinite(params["intercept"]), "calibrator orientation invalid")
        detector["calibrator_parameters"] = params
        detector["calibrator_probability_warning"] = "Probability-valued implementation; no guarantee of perfect calibration or shifted-distribution calibration"

    return {
        "protocol_version": "EXP-PROTOCOL-001_PHASE-2_v1", "cycle_1_base_commit": BASE,
        "stack_id": stack["stack_id"], "stack_manifest_sha": STACK_SHA,
        "stack_manifest_hash_kind": "CANONICAL_JSON_SHA256",
        "stack_manifest_file_sha256": sha(locate(STACK)), "stack_manifest_path": local(STACK),
        "stack_manifest_canonicalization": "UTF-8; sorted keys; compact separators; ensure_ascii=true; no NaN/Infinity; no trailing newline",
        "primary_detector_order": ORDER, "detectors": [statistical, semantic, external],
        "comparators": [{"detector_id": "dm_a_v1", "runtime_detector_id": "semantic_embedding_lr",
            "detector_role": "COMPARATOR_ONLY", "primary_stack_member": False}],
        "accepted_evidence_locations": locators,
        "artifact_integrity": {"status": "PASS", "hash_checks": len(locators), "baseline_preservation_checks": 96,
            "preserved_source_commit": PRESERVED_COMMIT, "preservation_inventory_sha256": PRESERVATION_SHA,
            "archive_is_runtime_fallback": False,
            "active_tree_ds_v2_available": contained(root, statistical["implementation_logical_path"]).is_file()},
        "scope": {"metadata_only": True, "model_execution": False, "dataset_scoring": False,
            "R0_rescoring": False, "threshold_selection": False, "prediction_schema_created": False,
            "regime_schema_created": False, "Cycle_2_resumed": False, "R1_started": False,
            "R2_started": False, "R3_started": False},
    }


def validate_manifest(value, root=ROOT):
    require(value == build_manifest(root), "detector manifest differs from verified frozen semantics")
    require(value["primary_detector_order"] == ORDER, "primary detector order drift")
    all_records = value["detectors"] + value["comparators"]
    require(len({d["detector_id"] for d in all_records}) == 4, "duplicate detector IDs")
    return {"status": "PASS", **value["artifact_integrity"]}


def check_package(root=ROOT):
    directory = Path(root) / OUT
    value = read_json(directory / NAME)
    require((directory / NAME).read_bytes() == manifest_bytes(value), "non-deterministic manifest encoding")
    require(sha(directory / NAME) == (directory / "detector_set_manifest_v1.sha256").read_text(encoding="ascii").strip(),
            "detector manifest byte hash mismatch")
    return {**validate_manifest(value, root), "manifest_sha256": sha(directory / NAME)}


def freeze(root=ROOT):
    value = build_manifest(root)
    directory = Path(root) / OUT
    directory.mkdir(parents=True, exist_ok=True)
    payload = manifest_bytes(value)
    checksum = (hashlib.sha256(payload).hexdigest() + "\n").encode("ascii")
    for name, content in ((NAME, payload), ("detector_set_manifest_v1.sha256", checksum)):
        path = directory / name
        if path.exists():
            require(path.read_bytes() == content, "refuse to overwrite different frozen protocol bytes")
        else:
            with path.open("xb") as stream:
                stream.write(content)
    return check_package(root)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("freeze", "check"), default="check")
    args = parser.parse_args()
    print(json.dumps(freeze() if args.mode == "freeze" else check_package(), indent=2))
