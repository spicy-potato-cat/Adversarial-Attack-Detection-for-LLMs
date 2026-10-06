"""Metadata-only contract fixtures; no attacks, models, prompts or metrics."""

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import get_args

import jsonschema
from pydantic import ValidationError
import pytest

from detection_service.research_protocol import detector_semantics as phase2
from detection_service.research_protocol.adapters import DetectorAdapter, FrozenDetectorContracts, PHASE2_SHA
from detection_service.research_protocol.regime import (
    Partition, RegimeContractError, RegimeManifest, RegimeSample, ThreatRegime,
    create_manifest, experiment_id, manifest_hash, manifest_schema, sample_schema,
)
from detection_service.research_protocol import regime_contract as phase4
from detection_service.tests.test_prediction_adapters import native


@pytest.fixture(scope="module")
def contracts():
    return phase4.FrozenRegimeContracts()


@pytest.fixture(scope="module")
def fixtures(contracts):
    return phase4.synthetic_fixtures(contracts)


def fixture(fixtures, name="r0"):
    return deepcopy(fixtures[phase4.FIXTURES + "/" + name + "_manifest_v1.json"])


def rehash(payload):
    payload["experiment_id"] = experiment_id(payload)
    payload["manifest_hash"] = manifest_hash(payload)
    return payload


def bad_sample(row, **changes):
    value = {**row, **changes}
    with pytest.raises((ValidationError, RegimeContractError)):
        RegimeSample.model_validate(value)


def test_regime_manifest_schema_valid(fixtures):
    schema = manifest_schema()
    jsonschema.Draft202012Validator.check_schema(schema)
    for name in ("r0", "r1", "r2_ds", "r2_dmb", "r2_dg", "r3"):
        payload = fixture(fixtures, name)
        jsonschema.validate(payload, schema)
        model = RegimeManifest.model_validate(payload)
        assert RegimeManifest.model_validate_json(model.deterministic_json()) == model


def test_regime_sample_schema_valid(fixtures):
    schema = sample_schema()
    jsonschema.Draft202012Validator.check_schema(schema)
    for name in ("r0", "r1", "r2_ds", "r2_dmb", "r2_dg", "r3"):
        for row in fixture(fixtures, name)["samples"]:
            jsonschema.validate(row, schema)
            assert RegimeSample.model_validate(row).sample_id == row["sample_id"]


def test_threat_regime_enum():
    assert get_args(ThreatRegime) == ("R0_NON_ADAPTIVE", "R1_SHIFTED_UNSEEN", "R2_SINGLE_DETECTOR_TARGETED", "R3_ENSEMBLE_TARGETED")


def test_partition_enum():
    assert get_args(Partition) == ("BASE_TRAIN", "CALIBRATION", "VALIDATION", "META_TRAIN", "INTERNAL_TEST", "FROZEN_EXTERNAL", "FINAL_TEST", "ATTACK_GENERATION", "QUARANTINE")


@pytest.mark.parametrize("partition", get_args(Partition))
@pytest.mark.parametrize("name", ["r0", "r1", "r2_ds", "r2_dmb", "r2_dg", "r3"])
def test_partition_regime_orthogonality(fixtures, partition, name):
    payload = fixture(fixtures, name)
    payload["partition"] = partition
    for row in payload["samples"]:
        row["partition"] = partition
    assert RegimeManifest.model_validate(rehash(payload)).partition == partition


def test_r0_allows_null_target(fixtures):
    assert all(r.target_detector is None for r in RegimeManifest.model_validate(fixture(fixtures)).samples)


def test_r1_allows_null_target(fixtures):
    assert all(r.target_detector is None for r in RegimeManifest.model_validate(fixture(fixtures, "r1")).samples)


@pytest.mark.parametrize("name,target", [("r0", "D_M-B"), ("r1", "ALL"), ("r2_ds", None),
    ("r2_ds", "ALL"), ("r2_ds", "D_M-A"), ("r3", "D_M-B"), ("r3", None), ("r2_ds", "STATISTICAL")])
def test_invalid_target_combinations(fixtures, name, target):
    row = fixture(fixtures, name)["samples"][0]
    bad_sample(row, target_detector=target)
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate({**row, "target_detector": target}, sample_schema())


def test_r2_requires_primary_target(fixtures):
    for name, target in (("r2_ds", "D_S"), ("r2_dmb", "D_M-B"), ("r2_dg", "D_G")):
        assert RegimeSample.model_validate(fixture(fixtures, name)["samples"][0]).target_detector == target


def test_r2_rejects_all_target(fixtures):
    bad_sample(fixture(fixtures, "r2_ds")["samples"][0], target_detector="ALL")


def test_r2_rejects_comparator_target(fixtures):
    bad_sample(fixture(fixtures, "r2_ds")["samples"][0], target_detector="D_M-A")


def test_r3_requires_all_target(fixtures):
    row = fixture(fixtures, "r3")["samples"][0]
    assert RegimeSample.model_validate(row).target_detector == "ALL"
    bad_sample(row, target_detector=None)


@pytest.mark.parametrize("name", ["r2_ds", "r3"])
@pytest.mark.parametrize("field", ["attack_method", "attack_method_revision", "lineage_id", "parent_sample_id",
                                   "valid_attack_attempt", "attack_success_definition"])
def test_targeted_required_fields(fixtures, name, field):
    bad_sample(fixture(fixtures, name)["samples"][0], **{field: None})


def test_r2_requires_attack_method(fixtures):
    bad_sample(fixture(fixtures, "r2_ds")["samples"][0], attack_method=None)


def test_r3_requires_attack_method(fixtures):
    bad_sample(fixture(fixtures, "r3")["samples"][0], attack_method=None)


def test_r2_requires_lineage(fixtures):
    bad_sample(fixture(fixtures, "r2_ds")["samples"][0], lineage_id=None)


def test_r3_requires_lineage(fixtures):
    bad_sample(fixture(fixtures, "r3")["samples"][0], lineage_id=None)


def test_parent_sample_lineage_contract(fixtures):
    payload = fixture(fixtures, "r2_ds")
    payload["samples"][0]["lineage_id"] = "wrong-lineage"
    with pytest.raises(ValidationError, match="PARENT_LINEAGE_CONFLICT"):
        RegimeManifest.model_validate(rehash(payload))


def test_multiple_descendants_share_lineage(fixtures):
    manifest = RegimeManifest.model_validate(fixture(fixtures, "r2_ds"))
    assert len({r.sample_id for r in manifest.samples}) == 3
    assert len({r.lineage_id for r in manifest.samples}) == 1
    assert len({r.parent_sample_id for r in manifest.samples}) == 1


@pytest.mark.parametrize("change", ["missing", "self", "cycle", "unused", "missing_evidence"])
def test_parent_graph_rejects_conflicts(fixtures, change):
    payload = fixture(fixtures, "r2_ds")
    rows = payload["samples"]
    if change == "missing":
        rows[0]["parent_sample_id"] = "absent-parent"
    elif change == "self":
        rows[0]["parent_sample_id"] = rows[0]["sample_id"]
    elif change == "cycle":
        rows[0]["parent_sample_id"] = rows[1]["sample_id"]
        rows[1]["parent_sample_id"] = rows[0]["sample_id"]
    elif change == "unused":
        payload["external_parents"].append({**payload["external_parents"][0], "sample_id": "unused-parent"})
    else:
        payload["external_parents"][0]["evidence_role"] = "missing"
    with pytest.raises((ValidationError, RegimeContractError)):
        RegimeManifest.model_validate(rehash(payload))


def test_attack_success_requires_definition(fixtures):
    bad_sample(fixture(fixtures, "r2_ds")["samples"][0], attack_success_definition=None)


def test_valid_attack_attempt_distinct_from_attack_success(fixtures):
    row = fixture(fixtures, "r2_ds")["samples"][0]
    result = RegimeSample.model_validate(row)
    assert result.truth_label == 1 and result.valid_attack_attempt is True and result.attack_success is False
    assert RegimeSample.model_validate({**row, "valid_attack_attempt": False}).attack_success is False
    bad_sample(row, attack_success=True, valid_attack_attempt=False)


@pytest.mark.parametrize("definition", ["unversioned", "TARGET_EVASION", "TARGET_EVASION_V0", ""])
def test_success_definition_version_required(fixtures, definition):
    bad_sample(fixture(fixtures, "r2_ds")["samples"][0], attack_success_definition=definition)


def test_generator_provenance_validation(fixtures):
    row = fixture(fixtures, "r2_ds")["samples"][0]
    model = {**row, "generator_type": "MODEL", "generator_model": "fixture-model", "generator_system": None, "generator_revision": "fixture-model-v1"}
    assert RegimeSample.model_validate(model).generator_model == "fixture-model"
    bad_sample(model, generator_revision=None)
    bad_sample(model, generator_model=None)
    bad_sample(row, generator_type=None)
    bad_sample(row, generator_model="not-a-rule-engine")
    bad_sample(row, generator_revision=None)


def test_pending_generation_has_no_success(fixtures):
    row = fixture(fixtures, "r3")["samples"][0]
    pending = {**row, "generation_evaluation_status": "PENDING", "attack_success": None}
    assert RegimeSample.model_validate(pending).attack_success is None
    bad_sample(pending, attack_success=False)
    bad_sample(row, attack_success=None)


def test_sample_ids_unique(fixtures):
    payload = fixture(fixtures)
    payload["samples"][1]["sample_id"] = payload["samples"][0]["sample_id"]
    with pytest.raises(ValidationError, match="DUPLICATE_SAMPLE_ID"):
        RegimeManifest.model_validate(rehash(payload))


@pytest.mark.parametrize("field", ["sample_count", "attack_count", "benign_count"])
def test_counts_match_manifest(fixtures, field):
    payload = fixture(fixtures)
    payload[field] += 1
    with pytest.raises(ValidationError, match="MANIFEST_COUNT_CONFLICT"):
        RegimeManifest.model_validate(rehash(payload))


def test_truth_label_consistency(fixtures):
    row = fixture(fixtures)["samples"][0]
    bad_sample(row, is_adversarial=not row["is_adversarial"])
    for value in (True, "1", 2, None):
        bad_sample(row, truth_label=value)


def test_detector_manifest_binding(contracts, fixtures):
    payload = fixture(fixtures)
    payload["primary_detector_manifest_sha"] = "0" * 64
    with pytest.raises(RegimeContractError, match="DETECTOR_MANIFEST_BINDING_MISMATCH"):
        contracts.validate_manifest(rehash(payload))


def test_prediction_schema_binding(contracts, fixtures):
    payload = fixture(fixtures)
    payload["prediction_schema_sha"] = "0" * 64
    with pytest.raises(RegimeContractError, match="PREDICTION_SCHEMA_BINDING_MISMATCH"):
        contracts.validate_manifest(rehash(payload))


def test_manifest_serialization_deterministic(fixtures):
    payload = fixture(fixtures)
    record = RegimeManifest.model_validate(payload)
    reordered = dict(reversed(list(payload.items())))
    assert record.deterministic_json() == RegimeManifest.model_validate(reordered).deterministic_json()
    assert not record.deterministic_json().endswith("\n")
    assert '"target_detector":null' in record.deterministic_json()


def test_manifest_hash_stable(fixtures):
    payload = fixture(fixtures)
    assert manifest_hash(payload) == payload["manifest_hash"]
    payload["manifest_hash"] = "0" * 64
    assert manifest_hash(payload) != payload["manifest_hash"]
    with pytest.raises(ValidationError, match="MANIFEST_HASH_MISMATCH"):
        RegimeManifest.model_validate(payload)


def test_experiment_identity_not_clock_only(fixtures):
    payload = fixture(fixtures, "r2_ds")
    identity = payload["experiment_id"]
    payload["created_at"] = "2001-01-01T00:00:00Z"
    payload["samples"][0]["created_at"] = payload["created_at"]
    assert experiment_id(payload) == identity
    assert manifest_hash(payload) != payload["manifest_hash"]
    payload["samples"][0]["attack_method_revision"] = "different-method-v2"
    assert experiment_id(payload) != identity


def test_frozen_manifest_identity_fields_immutable(fixtures):
    manifest = RegimeManifest.model_validate(fixture(fixtures))
    with pytest.raises(ValidationError):
        manifest.dataset_revision = "new"
    with pytest.raises(ValidationError):
        manifest.samples[0].sample_id = "changed"
    with pytest.raises(RegimeContractError, match="FROZEN_MANIFEST_MUTATION"):
        manifest.model_copy(update={"dataset_revision": "new"})
    assert isinstance(manifest.samples, tuple) and isinstance(manifest.notes, tuple)


def test_invalid_partition_rejected(fixtures):
    bad_sample(fixture(fixtures)["samples"][0], partition="TEST")


def test_invalid_regime_rejected(fixtures):
    bad_sample(fixture(fixtures)["samples"][0], threat_regime="R4_FULL_SYSTEM_ADAPTIVE")


@pytest.mark.parametrize("name", ["r0", "r1", "r2_ds", "r2_dmb", "r2_dg", "r3"])
def test_synthetic_regime_fixture(contracts, fixtures, name):
    result = contracts.validate_manifest(fixture(fixtures, name))
    assert result.evidence_kind == "SYNTHETIC_FIXTURE" and result.status == "FROZEN"
    assert all(r.provenance_status == "SYNTHETIC_FIXTURE" for r in result.samples)


def test_singleton_fallback_requires_justification(fixtures):
    row = fixture(fixtures)["samples"][0]
    fallback = {**row, "lineage_id": "fixture-singleton", "lineage_provenance_status": "SINGLETON_FALLBACK"}
    bad_sample(fallback)
    assert RegimeSample.model_validate({**fallback, "lineage_justification": "Fixture explicitly assumes independence; not actual research evidence."}).lineage_id


@pytest.mark.parametrize("field,value", [("source", "wrong-source"), ("dataset_revision", "wrong-revision"),
    ("partition", "FINAL_TEST"), ("provenance_status", "COMPLETE")])
def test_manifest_sample_provenance_consistency(fixtures, field, value):
    payload = fixture(fixtures)
    payload["samples"][0][field] = value
    with pytest.raises((ValidationError, RegimeContractError)):
        RegimeManifest.model_validate(rehash(payload))


@pytest.mark.parametrize("field,value", [("valid_attack_attempt", "true"), ("attack_success", 1),
    ("generated_sample", 1), ("created_at", "2000-02-30T00:00:00Z"), ("raw_prompt", "forbidden")])
def test_strict_metadata_types_and_no_prompt_fields(fixtures, field, value):
    bad_sample(fixture(fixtures, "r2_ds")["samples"][0], **{field: value})


@pytest.fixture(scope="module")
def prediction_adapters():
    frozen = FrozenDetectorContracts()
    return tuple(DetectorAdapter(label, frozen) for label in ("D_S", "D_M-B", "D_G"))


def synthetic_predictions(payload, adapters):
    return [a.adapt_fixture(native(a), sample_id=row["sample_id"], truth_label=row["truth_label"])
            for row in payload["samples"] for a in adapters]


def test_prediction_join(contracts, fixtures, prediction_adapters):
    payload = fixture(fixtures)
    predictions = synthetic_predictions(payload, prediction_adapters)
    assert len(phase4.validate_prediction_join(payload, predictions, contracts)) == 9


@pytest.mark.parametrize("change", ["duplicate", "missing", "unknown_sample", "wrong_truth", "comparator", "model_hash"])
def test_prediction_join_rejects_conflicts(contracts, fixtures, prediction_adapters, change):
    payload = fixture(fixtures)
    predictions = synthetic_predictions(payload, prediction_adapters)
    if change == "duplicate":
        predictions.append(predictions[0])
    elif change == "missing":
        predictions.pop()
    else:
        values = {"unknown_sample": ("sample_id", "absent"), "wrong_truth": ("truth_label", 0),
                  "comparator": ("detector_id", "dm_a_v1"), "model_hash": ("model_hash", "0" * 64)}
        field, value = values[change]
        predictions[0] = {**predictions[0].model_dump(), field: value}
    with pytest.raises(ValueError):
        phase4.validate_prediction_join(payload, predictions, contracts)


def test_non_ok_join_does_not_manufacture_benign(contracts, fixtures, prediction_adapters):
    payload = fixture(fixtures)
    predictions = synthetic_predictions(payload, prediction_adapters)
    predictions[0] = prediction_adapters[0].adapt_fixture({}, sample_id=payload["samples"][0]["sample_id"], truth_label=1)
    result = phase4.validate_prediction_join(payload, predictions, contracts)
    assert result[0].status != "OK" and result[0].native_binary_prediction is None and result[0].raw_score is None


def test_real_r0_metadata_only(contracts):
    value = phase4.accepted_r0(contracts)
    assert (value["sample_count"], value["attack_count"], value["benign_count"]) == (1135, 183, 952)
    assert value["partition"] == "BASE_TRAIN" and value["status"] == "COMPLETED"
    assert all(r["target_detector"] is None and r["outer_fold"] in range(5) for r in value["samples"])
    assert all(r["lineage_provenance_status"] == "CANONICAL_DUPLICATE_GROUP" for r in value["samples"])
    assert all(r["provenance_status"] == "PARTIAL" for r in value["samples"])
    assert {r["dataset_id"] for r in value["samples"]} == {"DS-TXT-017", "DS-TXT-018"}


def test_regime_contract_artifacts_deterministic():
    result = phase4.check()
    assert result["status"] == "PASS" and result["prior_contracts_unchanged"]


def test_build_does_not_load_models_prompts_or_predictions():
    code = '''
import sys
def audit(event, args):
    if event == "import" and args[0].split(".")[0] in ("torch", "transformers", "sklearn", "sentence_transformers"):
        raise AssertionError("model library import forbidden")
    if event == "open" and isinstance(args[0], (str, bytes)):
        name = str(args[0]).replace("\\\\", "/").lower()
        if "/dataset/raw/" in name or "normalized_records" in name or name.endswith("predictions.csv"):
            raise AssertionError("prompt/prediction access forbidden")
sys.addaudithook(audit)
from detection_service.research_protocol.regime_contract import build_artifacts
artifacts = build_artifacts()
assert len(artifacts) == 11
assert not any(n.startswith("detection_service.app.detectors") for n in sys.modules)
print("PASS")
'''
    output = subprocess.check_output([sys.executable, "-c", code], cwd=phase2.ROOT, text=True)
    assert output.strip() == "PASS"


@pytest.mark.parametrize("field,value", [("attack_method", None), ("attack_method_revision", None),
    ("attack_success_definition", None), ("parent_sample_id", None), ("lineage_id", None),
    ("generator_system", None), ("generator_revision", None), ("valid_attack_attempt", 1),
    ("attack_family", None), ("generation_evaluation_status", "NOT_APPLICABLE")])
def test_sample_schema_rejects_invalid_relations(fixtures, field, value):
    row = fixture(fixtures, "r2_ds")["samples"][0]
    bad_sample(row, **{field: value})
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate({**row, field: value}, sample_schema())


@pytest.mark.parametrize("binding", ["detector", "prediction", "adapter"])
def test_authoritative_input_mismatch_stops_before_build(monkeypatch, binding):
    paths = {"detector": phase2.OUT + "/" + phase2.NAME, "prediction": phase4.phase3.SCHEMA,
             "adapter": phase4.phase3.CONTRACT}
    real_sha = phase2.sha
    monkeypatch.setattr(phase2, "sha", lambda path: "0" * 64 if Path(path) == phase2.ROOT / paths[binding] else real_sha(path))
    with pytest.raises(RegimeContractError, match="AUTHORITATIVE_INPUT_HASH_MISMATCH"):
        phase4.FrozenRegimeContracts()


def test_noncanonical_order_rejected_and_factory_sorts(contracts, fixtures):
    payload = fixture(fixtures)
    payload["samples"].reverse()
    with pytest.raises(ValidationError, match="NON_CANONICAL_SAMPLE_ORDER"):
        RegimeManifest.model_validate(rehash(payload))
    assert create_manifest(**payload).experiment_id == fixture(fixtures)["experiment_id"]


def test_draft_copy_revalidates_identity(fixtures):
    payload = fixture(fixtures)
    payload["status"] = "DRAFT"
    manifest = RegimeManifest.model_validate(rehash(payload))
    with pytest.raises(ValidationError, match="EXPERIMENT_ID_MISMATCH"):
        manifest.model_copy(update={"dataset_revision": "changed"})


def test_freeze_refuses_overwrite_before_publishing(tmp_path, monkeypatch):
    (tmp_path / "existing.json").write_bytes(b"old frozen evidence")
    monkeypatch.setattr(phase4, "build_artifacts", lambda root: {"new.json": {}, "existing.json": {}})
    monkeypatch.setattr(phase4, "expected_hashes", lambda root, artifacts: {})
    with pytest.raises(RegimeContractError, match="REFUSE_DIFFERENT_FROZEN_BYTES"):
        phase4.freeze(tmp_path)
    assert not (tmp_path / "new.json").exists()
    assert (tmp_path / "existing.json").read_bytes() == b"old frozen evidence"


def test_r0_synthetic_fixture(fixtures):
    assert RegimeManifest.model_validate(fixture(fixtures)).threat_regime == "R0_NON_ADAPTIVE"


def test_r1_synthetic_fixture(fixtures):
    assert RegimeManifest.model_validate(fixture(fixtures, "r1")).threat_regime == "R1_SHIFTED_UNSEEN"


def test_r2_ds_synthetic_fixture(fixtures):
    assert RegimeManifest.model_validate(fixture(fixtures, "r2_ds")).samples[0].target_detector == "D_S"


def test_r2_dmb_synthetic_fixture(fixtures):
    assert RegimeManifest.model_validate(fixture(fixtures, "r2_dmb")).samples[0].target_detector == "D_M-B"


def test_r2_dg_synthetic_fixture(fixtures):
    assert RegimeManifest.model_validate(fixture(fixtures, "r2_dg")).samples[0].target_detector == "D_G"


def test_r3_synthetic_fixture(fixtures):
    assert RegimeManifest.model_validate(fixture(fixtures, "r3")).samples[0].target_detector == "ALL"
