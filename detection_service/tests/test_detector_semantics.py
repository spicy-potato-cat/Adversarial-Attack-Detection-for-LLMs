"""Static Phase-2 checks only: no detector imports, predictions, or fitting."""

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest

from detection_service.research_protocol import detector_semantics as semantics


@pytest.fixture(scope="module")
def manifest():
    return semantics.build_manifest()


def test_primary_detector_order(manifest):
    assert manifest["primary_detector_order"] == ["D_S", "D_M-B", "D_G"]
    assert [d["stack_label"] for d in manifest["detectors"]] == manifest["primary_detector_order"]


def test_comparator_excluded(manifest):
    assert manifest["comparators"] == [{"detector_id": "dm_a_v1", "runtime_detector_id": "semantic_embedding_lr",
        "detector_role": "COMPARATOR_ONLY", "primary_stack_member": False}]
    assert "dm_a_v1" not in [d["detector_id"] for d in manifest["detectors"]]


def test_unique_detector_ids(manifest):
    records = manifest["detectors"] + manifest["comparators"]
    assert len({d["detector_id"] for d in records}) == 4


def test_roles_explicit(manifest):
    assert [d["detector_role"] for d in manifest["detectors"]] == [
        "PRIMARY_STATISTICAL", "PRIMARY_SEMANTIC", "PRIMARY_EXTERNAL_GUARD"]
    assert [d["detector_id"] for d in manifest["detectors"]] == ["ds_v2", "dm_b_v1", "dg_v1"]


def test_score_direction_defined(manifest):
    assert all(d["native_score_direction"] == semantics.DIRECTION for d in manifest["detectors"])
    assert all(d["native_score_range"] == [0, 1] for d in manifest["detectors"])


def test_canonical_score_direction(manifest):
    assert all(d["canonical_score_direction"] == "HIGHER_IS_MORE_ADVERSARIAL" and
               not d["direction_normalization_required"] and d["future_direction_transform"] is None
               for d in manifest["detectors"])


def test_ds_artifact_hashes(manifest):
    ds = manifest["detectors"][0]
    assert ds["model_hash"] == semantics.MODEL_HASHES[0]
    assert ds["reference_hash"] == semantics.REFERENCE_SHA
    assert ds["feature_schema_sha256"] == semantics.B2_SHA
    assert ds["feature_count"] == len(ds["feature_names"]) == 26
    assert ds["full_training_iterations"] == 5492


def test_dmb_artifact_hashes(manifest):
    dm = manifest["detectors"][1]
    assert dm["model_hash"] == semantics.MODEL_HASHES[1]
    assert dm["model_revision"] == dm["tokenizer_revision"] == semantics.DM_REV
    assert dm["training_evidence"] == {"partition": "BASE_TRAIN", "epochs": 3,
        "optimizer": "AdamW", "learning_rate": 2e-5, "batch_size": 8, "seed": 1701}


def test_dg_revision(manifest):
    guard = manifest["detectors"][2]
    assert guard["model_revision"] == guard["tokenizer_revision"] == semantics.DG_REV
    assert guard["model_name"] == "meta-llama/Llama-Prompt-Guard-2-22M"
    assert len(guard["snapshot_file_sha256"]) == 9
    assert guard["snapshot_global_sha256"] is None
    assert guard["model_hash"] == guard["snapshot_file_sha256"]["model.safetensors"]


def test_ds_calibrator_binding(manifest):
    ds = manifest["detectors"][0]
    assert ds["calibrator_id"] == "ds_v2_cal_v1" and ds["calibrator_hash"] == semantics.CAL_HASHES[0]
    assert ds["calibration_binding"]["ds_v2_model.json"] == ds["model_hash"]
    assert ds["calibration_binding"]["ds_v2_feature_reference.json"] == ds["reference_hash"]
    assert ds["calibrator_input"] == "logit(clip(raw_LR_class_1_probability,1e-12,1-1e-12))"


def test_dmb_calibrator_binding(manifest):
    dm = manifest["detectors"][1]
    assert dm["calibrator_id"] == "dm_b_v1_cal_v1" and dm["calibrator_hash"] == semantics.CAL_HASHES[1]
    assert dm["calibration_binding"]["transformer/model.safetensors"] == dm["model_hash"]
    assert dm["calibrator_input"] == "logit(clip(raw_softmax_class_1_probability,1e-12,1-1e-12))"


def test_dg_has_no_calibrator(manifest):
    guard = manifest["detectors"][2]
    assert not guard["calibrated_score_available"]
    assert all(guard[k] is None for k in ("calibrator_id", "calibrator_hash", "calibrator_artifact",
        "calibrator_input", "calibrator_output", "calibrator_output_range"))


def test_operational_threshold_not_frozen(manifest):
    assert all(d["operational_threshold_status"] == "NOT_FROZEN" and d["operational_threshold"] is None
               for d in manifest["detectors"])
    assert [d["default_threshold"] for d in manifest["detectors"]] == [0.5, 0.5, None]
    assert [d["default_threshold_status"] for d in manifest["detectors"]] == [
        "DEVELOPMENT_CONVENIENCE", "DEVELOPMENT_CONVENIENCE", "NATIVE_MODEL_DECISION"]


def test_dg_chunking_semantics(manifest):
    guard = manifest["detectors"][2]
    assert guard["context_length"] == 512 and guard["project_input_limit"] is None
    assert guard["chunking_policy"] == {"content_tokens": 510, "special_tokens": 2,
        "overlap": 64, "stride": 446, "tail_handling": "full tail coverage"}
    assert guard["adversarial_class"]["index"] == 1
    assert guard["adversarial_class"]["serialized_label"] == "LABEL_1"
    assert guard["adversarial_class"]["meaning"] == "malicious_instruction_override_attempt"
    assert guard["native_binary_rule"] == "OR over chunk logits.argmax == class 1; ties choose class 0"


def test_detector_manifest_deterministic(manifest):
    assert semantics.manifest_bytes(manifest) == semantics.manifest_bytes(semantics.build_manifest())
    assert (semantics.ROOT / semantics.OUT / semantics.NAME).read_bytes() == semantics.manifest_bytes(manifest)


def test_detector_manifest_hash_stable(manifest):
    digest = hashlib.sha256(semantics.manifest_bytes(manifest)).hexdigest()
    assert digest == "2da5aa92cb14ac19cd49fa7150e7a4ef79b59e1e5fb1aa8ba4148456da618f31"
    assert semantics.check_package()["manifest_sha256"] == digest


def test_raw_calibrated_and_native_decisions_not_conflated(manifest):
    assert [d["threshold_input_score_type"] for d in manifest["detectors"]] == [
        "calibrated_probability", "raw_score", "native_chunk_argmax"]
    assert all(d["ranking_input_score_type"] == "raw_score" for d in manifest["detectors"])
    for d in manifest["detectors"][:2]:
        assert d["calibrator_output_range"] == [0, 1]
        assert d["calibrator_parameters"]["slope"] > 0
        assert d["calibrator_parameters"]["epsilon"] == 1e-12


def test_ds_causal_shift_and_two_window_scales(manifest):
    ds = manifest["detectors"][0]
    assert ds["context_length"] == 1024 and ds["project_input_limit"] == 4096
    assert ds["chunking_policy"]["overlap"] == 64 and ds["chunking_policy"]["stride"] == 960
    assert "logits[:, :-1]" in ds["aggregation_policy"] and "IDs[:, 1:]" in ds["aggregation_policy"]
    assert "128-token feature windows, stride 64" in ds["aggregation_policy"]
    assert "insufficient_input" in ds["insufficient_input_policy"]


def test_dmb_truncation_and_classes(manifest):
    dm = manifest["detectors"][1]
    assert dm["context_length"] == 512 and dm["project_input_limit"] == 256
    assert dm["chunking_policy"] is None
    assert dm["adversarial_class"] == {"index": 1, "serialized_label": "ATTACK",
        "benign_index": 0, "benign_label": "BENIGN"}
    assert "including special tokens" in dm["truncation_policy"]


def test_explicit_preserved_provenance_not_runtime_substitution(manifest):
    ds = manifest["detectors"][0]
    assert ds["implementation_path"].startswith(semantics.BACKUP + "/")
    assert ds["implementation_revision"] == semantics.PRESERVED_COMMIT
    assert manifest["artifact_integrity"]["archive_is_runtime_fallback"] is False
    assert manifest["artifact_integrity"]["active_tree_ds_v2_available"] is False
    assert not (semantics.ROOT / ds["implementation_logical_path"]).is_file()
    assert manifest["stack_manifest_sha"] == semantics.STACK_SHA
    assert manifest["stack_manifest_hash_kind"] == "CANONICAL_JSON_SHA256"
    assert manifest["stack_manifest_file_sha256"] == "4bd076dfc07717555034732b55a9a65c0bc531bb17beab58659b088254247dae"


@pytest.mark.parametrize("change", [
    lambda m: m["primary_detector_order"].reverse(),
    lambda m: m["detectors"][0].update(detector_id="dm_a_v1"),
    lambda m: m["comparators"][0].update(primary_stack_member=True),
    lambda m: m["detectors"][0].update(native_score_direction=None),
    lambda m: m["detectors"][1].update(canonical_score_direction="MORE_BENIGN"),
    lambda m: m["detectors"][0].update(calibrator_id="dm_b_v1_cal_v1"),
    lambda m: m["detectors"][1].update(model_hash="0" * 64),
    lambda m: m["detectors"][2].update(model_revision="0" * 40),
    lambda m: m["detectors"][0].update(operational_threshold_status="FROZEN"),
    lambda m: m["detectors"][0].update(implementation_path="artifacts/data_cycle2/model.py"),
    lambda m: m["detectors"][2]["chunking_policy"].update(stride=510),
])
def test_invalid_contract_rejected(manifest, monkeypatch, change):
    candidate = deepcopy(manifest)
    change(candidate)
    monkeypatch.setattr(semantics, "build_manifest", lambda root: manifest)
    with pytest.raises(semantics.SemanticsIntegrityError):
        semantics.validate_manifest(candidate)


@pytest.mark.parametrize("path", ["../escape", "C:/outside", "/outside", "artifacts/data_cycle2/test.json",
                                  "artifacts/statistical_v2/failure_atlas/test.json"])
def test_unsafe_or_cycle2_path_rejected(path):
    with pytest.raises(semantics.SemanticsIntegrityError):
        semantics.contained(semantics.ROOT, path)


def test_hash_drift_stops_before_manifest_creation(monkeypatch):
    original = semantics.sha
    def tamper(path):
        return "0" * 64 if Path(path).name == "ds_v2_model.json" else original(path)
    monkeypatch.setattr(semantics, "sha", tamper)
    with pytest.raises(semantics.SemanticsIntegrityError, match="hash mismatch"):
        semantics.build_manifest()


def test_detector_implementations_unchanged():
    result = subprocess.run(["git", "diff", "--exit-code", semantics.BASE, "--",
        "detection_service/app", "detection_service/analysis", "detection_service/configs", "artifacts/models"],
        cwd=semantics.ROOT, capture_output=True)
    assert result.returncode == 0, result.stdout.decode()


def test_metadata_only_without_runtime_import_or_dataset_access():
    script = """
import sys
from pathlib import Path
root = Path.cwd()
def audit(event, args):
    if event == 'open' and isinstance(args[0], (str, bytes)):
        p = Path(args[0]).resolve()
        if p.is_relative_to(root / 'Dataset'):
            raise AssertionError('dataset access forbidden')
sys.addaudithook(audit)
from detection_service.research_protocol.detector_semantics import check_package
assert check_package()['status'] == 'PASS'
assert not any(m in sys.modules for m in ('torch', 'transformers', 'sklearn'))
assert not any(m.startswith('detection_service.app.detectors') for m in sys.modules)
"""
    result = subprocess.run([sys.executable, "-B", "-c", script], cwd=semantics.ROOT, capture_output=True)
    assert result.returncode == 0, result.stderr.decode()


def test_frozen_scope(manifest):
    assert manifest["scope"]["metadata_only"] is True
    assert all(not v for k, v in manifest["scope"].items() if k != "metadata_only")
    assert manifest["artifact_integrity"]["hash_checks"] == 165
    assert manifest["artifact_integrity"]["baseline_preservation_checks"] == 96
