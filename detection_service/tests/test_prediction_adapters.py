"""Phase-3 engineering fixtures only. No detector models or project data."""

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import jsonschema
from pydantic import ValidationError
import pytest

from detection_service.research_protocol import detector_semantics as phase2
from detection_service.research_protocol.adapters import (
    AdapterContractError, DetectorAdapter, FrozenDetectorContracts, PHASE2_SHA, primary_adapters,
)
from detection_service.research_protocol.prediction import PredictionRecord, STATUS_VALUES
from detection_service.research_protocol.prediction_contract import SCHEMA, build_artifacts


@pytest.fixture(scope="module")
def adapters():
    return primary_adapters()


def native(adapter, raw=.2, calibrated=.1, *, count=20):
    d = adapter._identity
    output = {"detector_id": d["runtime_detector_id"], "detector_version": adapter.detector_id,
        "status": "success", "raw_score": raw, "calibrated_probability": calibrated,
        "model": {"model_id": d["reference_model_name"] or d["model_name"],
            "model_revision": d["reference_model_revision"] or d["model_revision"],
            "tokenizer_id": d["tokenizer_name"], "device": "cpu"},
        "latency_ms": 12.0, "metadata": {"calibration_version": d["calibrator_id"]}}
    if d["stack_label"] == "D_S":
        output["binary_vote"] = calibrated >= d["default_threshold"]
        output["metadata"].update(feature_schema_sha256=d["feature_schema_sha256"], feature_count=d["feature_count"])
        output["input_coverage"] = {"input_tokens": count, "tokens_analyzed": min(count, d["project_input_limit"]) - 1,
            "truncated": count > d["project_input_limit"]}
    elif d["stack_label"] == "D_M-B":
        output["binary_vote"] = raw >= d["default_threshold"]
        output["metadata"].update(tokenizer_revision=d["tokenizer_revision"], max_sequence_length=d["project_input_limit"],
            truncation_side="right", padding="longest_in_batch", input_tokens_including_special=count,
            tokens_analyzed_including_special=min(count, d["project_input_limit"]), truncated=count > d["project_input_limit"])
    else:
        output["calibrated_probability"] = None
        output["binary_vote"] = raw > .5
        output["input_coverage"] = {"input_tokens": count, "tokens_analyzed": count, "truncated": False}
        output["metadata"].update(aggregation=d["aggregation_policy"]["raw_score"],
            decision_rule=d["aggregation_policy"]["binary_vote"], positive_class=d["adversarial_class"]["index"],
            context_limit=d["context_length"], chunk_size=d["chunking_policy"]["content_tokens"],
            overlap=d["chunking_policy"]["overlap"], stride=d["chunking_policy"]["stride"],
            tail_covered=True, final_tail_end=count)
    return output


def adapt(adapter, output=None, **kwargs):
    return adapter.adapt_fixture(output if output is not None else native(adapter), sample_id="fixture-001", truth_label=1, **kwargs)


def test_prediction_schema_valid(adapters):
    schema = json.loads((phase2.ROOT / SCHEMA).read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator.check_schema(schema)
    for adapter in adapters:
        record = adapt(adapter)
        assert record.status == "OK"
        jsonschema.validate(record.model_dump(mode="json"), schema)
        assert PredictionRecord.model_validate_json(record.deterministic_json()) == record


@pytest.mark.parametrize("field,value", [("native_binary_prediction", 2), ("truth_label", -1),
    ("truth_label", True), ("native_binary_prediction", "1")])
def test_prediction_schema_rejects_invalid_binary(adapters, field, value):
    payload = adapt(adapters[0]).model_dump()
    payload[field] = value
    with pytest.raises(ValidationError):
        PredictionRecord.model_validate(payload)


def test_prediction_schema_rejects_nan_score(adapters):
    payload = adapt(adapters[0]).model_dump()
    payload["raw_score"] = float("nan")
    with pytest.raises(ValidationError):
        PredictionRecord.model_validate(payload)


@pytest.mark.parametrize("field", ["raw_score", "calibrated_score", "latency_ms"])
def test_prediction_schema_rejects_infinite_score(adapters, field):
    payload = adapt(adapters[0]).model_dump()
    payload[field] = float("inf")
    with pytest.raises(ValidationError):
        PredictionRecord.model_validate(payload)


def test_score_direction_required(adapters):
    payload = adapt(adapters[0]).model_dump()
    del payload["score_direction"]
    with pytest.raises(ValidationError):
        PredictionRecord.model_validate(payload)


def test_score_direction_is_canonical(adapters):
    for adapter in adapters:
        assert adapt(adapter).score_direction == "HIGHER_IS_MORE_ADVERSARIAL"
    payload = adapt(adapters[0]).model_dump()
    payload["score_direction"] = "HIGHER_IS_MORE_BENIGN"
    with pytest.raises(ValidationError):
        PredictionRecord.model_validate(payload)


def test_operational_fields_null_before_phase5(adapters):
    for adapter in adapters:
        record = adapt(adapter)
        assert (record.operational_threshold, record.operational_threshold_id, record.operational_binary_prediction) == (None, None, None)


@pytest.mark.parametrize("field,value", [("operational_threshold", .5), ("operational_threshold_id", "default_0_5"),
                                       ("operational_binary_prediction", 0)])
def test_operational_prediction_rejected_without_manifest(adapters, field, value):
    payload = adapt(adapters[0]).model_dump()
    payload[field] = value
    with pytest.raises(ValidationError):
        PredictionRecord.model_validate(payload)
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(payload, json.loads((phase2.ROOT / SCHEMA).read_text(encoding="utf-8")))


def test_ds_adapter_identity(adapters):
    ds = adapters[0]
    assert ds.detector_id == ds.contracts.detector("D_S")["detector_id"]
    assert ds.detector_role == "PRIMARY_STATISTICAL"
    assert not ds.live_binding_available


def test_ds_raw_score_semantics(adapters):
    assert adapt(adapters[0]).raw_score == .2


def test_ds_calibrated_score_semantics(adapters):
    record = adapt(adapters[0])
    assert record.calibrated_score == .1
    assert record.calibrator_id == adapters[0]._identity["calibrator_id"]


def test_ds_native_vote_uses_calibrated_default(adapters):
    ds = adapters[0]
    assert adapt(ds, native(ds, .9, .1)).native_binary_prediction == 0
    assert adapt(ds, native(ds, .2, .8)).native_binary_prediction == 1


def test_dmb_adapter_identity(adapters):
    dm = adapters[1]
    assert dm.detector_id == dm.contracts.detector("D_M-B")["detector_id"]
    assert dm.detector_role == "PRIMARY_SEMANTIC" and dm.live_binding_available


def test_dmb_calibration_preserved(adapters):
    record = adapt(adapters[1])
    assert record.raw_score == .2 and record.calibrated_score == .1
    assert record.calibrator_id == adapters[1]._identity["calibrator_id"]


def test_dmb_native_vote_uses_raw_score(adapters):
    dm = adapters[1]
    assert adapt(dm, native(dm, .9, .1)).native_binary_prediction == 1
    assert adapt(dm, native(dm, .2, .8)).native_binary_prediction == 0


def test_dg_adapter_identity(adapters):
    guard = adapters[2]
    assert guard.detector_id == guard.contracts.detector("D_G")["detector_id"]
    assert guard.detector_role == "PRIMARY_EXTERNAL_GUARD" and guard.live_binding_available


def test_dg_calibrated_score_is_null(adapters):
    record = adapt(adapters[2])
    assert record.calibrated_score is None and record.calibrator_id is None


def test_dg_raw_score_is_max_chunk_malicious_probability(adapters):
    chunks = [.2, .9, .4]
    output = native(adapters[2], max(chunks))
    output["binary_vote"] = any(c > .5 for c in chunks)
    record = adapt(adapters[2], output)
    assert record.raw_score == max(chunks) and record.native_binary_prediction == 1


def test_dg_native_vote_uses_or_argmax(adapters):
    # Both synthetic chunks tie: class 0 wins, despite raw_score >= 0.5.
    output = native(adapters[2], .5)
    assert output["binary_vote"] is False
    record = adapt(adapters[2], output)
    assert record.status == "OK" and record.native_binary_prediction == 0


def test_dg_raw_score_and_native_vote_are_distinct_concepts(adapters):
    guard = adapters[2]
    benign = native(guard, .5)
    rounded_positive = deepcopy(benign)
    # Rounded softmax can be .5 even when argmax on logits is class 1.
    # The adapter does not infer the native argmax from the stored probability.
    rounded_positive["binary_vote"] = True
    a, b = adapt(guard, benign), adapt(guard, rounded_positive)
    assert a.raw_score == b.raw_score == .5
    assert (a.native_binary_prediction, b.native_binary_prediction) == (0, 1)


@pytest.mark.parametrize("status", ["insufficient_input", "unavailable", "not_trained", "unknown"])
def test_non_ok_status_not_mapped_to_benign(adapters, status):
    output = native(adapters[1])
    output["status"] = status
    record = adapt(adapters[1], output)
    assert record.status != "OK" and record.error_code is not None
    assert record.raw_score is record.calibrated_score is record.native_binary_prediction is None


@pytest.mark.parametrize("field,value", [("detector_version", "ds_v1"), ("detector_id", "semantic_embedding_lr")])
def test_artifact_mismatch_rejected(adapters, field, value):
    output = native(adapters[0])
    output[field] = value
    record = adapt(adapters[0], output)
    assert record.status == "ARTIFACT_MISMATCH" and record.native_binary_prediction is None


def test_tokens_accounting(adapters):
    ds, dm, dg = adapters
    assert (adapt(ds).input_tokens, adapt(ds).tokens_analyzed) == (20, 19)
    assert (adapt(dm).input_tokens, adapt(dm).tokens_analyzed) == (18, 18)
    guard = adapt(dg, native(dg, count=1000))
    assert guard.input_tokens == guard.tokens_analyzed == 1000
    assert guard.metadata.token_count_basis == "UNIQUE_CONTENT"
    double_count = native(dg, count=1000)
    double_count["input_coverage"]["tokens_analyzed"] = 1128
    assert adapt(dg, double_count).status == "OUTPUT_VALIDATION_ERROR"


def test_truncation_field(adapters):
    ds, dm, dg = adapters
    record = adapt(ds, native(ds, count=5000))
    assert record.truncated and record.tokens_analyzed == 4095
    record = adapt(dm, native(dm, count=300))
    assert record.truncated and record.input_tokens == 298 and record.tokens_analyzed == 254
    assert not adapt(dg, native(dg, count=1000)).truncated


def test_manifest_binding(adapters):
    for adapter in adapters:
        adapter.validate_frozen_identity()
        record = adapt(adapter)
        assert record.metadata.phase2_manifest_sha256 == PHASE2_SHA
        assert record.model_hash == adapter._identity["model_hash"]
        assert record.model_revision == adapter._identity["model_revision"]


def test_comparator_excluded_from_primary_adapter_set(adapters):
    with pytest.raises(AdapterContractError, match="NOT_A_PRIMARY"):
        DetectorAdapter("D_M-A", adapters[0].contracts)
    payload = adapt(adapters[0]).model_dump(mode="json")
    payload["detector_id"] = "dm_a_v1"
    with pytest.raises(AdapterContractError):
        adapters[0].validate_prediction_record(payload)
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(payload, json.loads((phase2.ROOT / SCHEMA).read_text(encoding="utf-8")))


def test_prediction_serialization_deterministic(adapters):
    record = adapt(adapters[0])
    a = record.deterministic_json()
    assert a == record.deterministic_json() and not a.endswith("\n")
    assert a == PredictionRecord.model_validate_json(a).deterministic_json()


def test_schema_hash_stable():
    generated = build_artifacts()[SCHEMA]
    assert (phase2.ROOT / SCHEMA).read_bytes() == phase2.manifest_bytes(generated)
    assert hashlib.sha256(phase2.manifest_bytes(generated)).hexdigest() == phase2.sha(phase2.ROOT / SCHEMA)


@pytest.mark.parametrize("field,value", [("raw_score", "0.2"), ("raw_score", True), ("latency_ms", -1.0),
                                       ("unknown", "extra"), ("tokens_analyzed", 999), ("truncated", 1)])
def test_strict_canonical_types_and_extras(adapters, field, value):
    payload = adapt(adapters[0]).model_dump()
    payload[field] = value
    with pytest.raises(ValidationError):
        PredictionRecord.model_validate(payload)


def test_unlabeled_inference_requires_explicit_workflow(adapters):
    adapter = adapters[1]
    with pytest.raises(AdapterContractError, match="UNLABELED"):
        adapter.adapt_fixture(native(adapter), sample_id="fixture-unlabeled", truth_label=None)
    record = adapter.adapt_fixture(native(adapter), sample_id="fixture-unlabeled", truth_label=None, allow_unlabeled=True)
    assert record.status == "OK" and record.truth_label is None and record.metadata.unlabeled_inference


@pytest.mark.parametrize("field,value", [("raw_score", float("nan")), ("raw_score", float("inf")),
    ("binary_vote", None), ("binary_vote", 0), ("calibrated_probability", None)])
def test_bad_native_output_is_structured_error(adapters, field, value):
    output = native(adapters[0])
    output[field] = value
    record = adapt(adapters[0], output)
    assert record.status != "OK" and record.native_binary_prediction is None


def test_different_calibrator_binding_rejected(adapters):
    output = native(adapters[1])
    output["metadata"]["calibration_version"] = adapters[0]._identity["calibrator_id"]
    assert adapt(adapters[1], output).status == "ARTIFACT_MISMATCH"


def test_native_vote_mismatch_not_repaired(adapters):
    for adapter in adapters[:2]:
        output = native(adapter)
        output["binary_vote"] = not output["binary_vote"]
        record = adapt(adapter, output)
        assert record.status == "OUTPUT_VALIDATION_ERROR" and record.native_binary_prediction is None


def test_guard_calibration_and_policy_change_rejected(adapters):
    guard = adapters[2]
    output = native(guard)
    output["calibrated_probability"] = .3
    assert adapt(guard, output).status == "CALIBRATION_ERROR"
    output = native(guard)
    output["metadata"]["stride"] += 1
    assert adapt(guard, output).status == "ARTIFACT_MISMATCH"


def test_phase2_hash_mismatch_stops_construction(monkeypatch):
    original = phase2.sha
    monkeypatch.setattr(phase2, "sha", lambda p: "0" * 64 if Path(p).name == phase2.NAME else original(p))
    with pytest.raises(AdapterContractError, match="PHASE2_MANIFEST_HASH_MISMATCH"):
        FrozenDetectorContracts()


def test_ds_live_binding_unavailable_without_reconstruction(adapters):
    ds = adapters[0]
    assert ds._live is None
    record = ds.predict("Synthetic engineering fixture", sample_id="fixture-live", truth_label=0)
    assert record.status == "UNAVAILABLE" and record.error_code == "DS_FROZEN_RUNTIME_BINDING_UNAVAILABLE"
    assert record.raw_score is record.native_binary_prediction is record.latency_ms is None
    assert ds._live is None


def test_frozen_native_output_source_binding(adapters, tmp_path):
    # An isolated fixture inventory emulates a previously accepted native JSON result.
    contracts = deepcopy(adapters[1].contracts)
    contracts.root = tmp_path
    path = tmp_path / "artifacts/models/dm_b_v1/fixture_native.json"
    path.parent.mkdir(parents=True)
    payload = {"result": native(adapters[1])}
    path.write_bytes(phase2.manifest_bytes(payload))
    relative = path.relative_to(tmp_path).as_posix()
    contracts._manifest["accepted_evidence_locations"][relative] = {"local_path": relative, "sha256": phase2.sha(path)}
    # Reuse the verified constructor; only the source-reader root is isolated.
    adapter = deepcopy(adapters[1])
    adapter.contracts = contracts
    record = adapter.adapt_existing_output(source_path=relative, source_locator="/result", sample_id="fixture-frozen", truth_label=1)
    assert record.status == "OK" and record.latency_ms == 12.0
    assert record.metadata.source_sha256 == phase2.sha(path)
    assert record.metadata.binding_mode == "FROZEN_EVIDENCE"
    assert record.metadata.latency_basis == "ACCEPTED_DETECTOR_REPORTED"
    del payload["result"]["latency_ms"]
    path.write_bytes(phase2.manifest_bytes(payload))
    mismatch = adapter.adapt_existing_output(source_path=relative, source_locator="/result", sample_id="fixture-frozen", truth_label=1)
    assert mismatch.status == "ARTIFACT_MISMATCH" and mismatch.native_binary_prediction is None
    contracts._manifest["accepted_evidence_locations"][relative]["sha256"] = phase2.sha(path)
    unmeasured = adapter.adapt_existing_output(source_path=relative, source_locator="/result", sample_id="fixture-frozen", truth_label=1)
    assert unmeasured.status == "OK" and unmeasured.latency_ms is None


def test_oof_not_relabelled_as_final_weights(adapters):
    record = adapters[1].adapt_existing_output(source_path="artifacts/semantic_v2/oof/dm_b_v1_recipe_oof_predictions.csv",
        sample_id="fixture-oof", truth_label=1)
    assert record.status == "ARTIFACT_MISMATCH" and record.native_binary_prediction is None


def test_other_detector_evidence_source_rejected(adapters):
    record = adapters[1].adapt_existing_output(source_path="artifacts/models/dg_v1/smoke_evidence.json",
        sample_id="fixture-wrong-source", truth_label=1)
    assert record.status == "ARTIFACT_MISMATCH"


def test_schema_requires_version_and_operational_null_fields(adapters):
    schema = build_artifacts()[SCHEMA]
    for field in ("schema_version", "metadata_version", "operational_threshold", "operational_threshold_id",
                  "operational_binary_prediction"):
        payload = adapt(adapters[0]).model_dump(mode="json")
        del payload[field]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(payload, schema)


def test_lazy_live_loader_hooks_without_model_execution(adapters, monkeypatch):
    for original in adapters[1:]:
        adapter = deepcopy(original)
        calls = []
        fake = SimpleNamespace(from_artifact=lambda *args, **kwargs: calls.append((args, kwargs)) or "fixture-loader")
        monkeypatch.setattr(adapter, "validate_frozen_identity", lambda: None)
        monkeypatch.setattr("detection_service.research_protocol.adapters.importlib.import_module",
            lambda name, a=adapter, f=fake: SimpleNamespace(**{a._identity["implementation_class"]: f}))
        assert adapter._load_live() == "fixture-loader"
        if adapter.detector_id == adapters[1].detector_id:
            assert calls[0][1]["require_calibration"] is True
        else:
            assert calls[0][1]["workspace"] == phase2.ROOT


@pytest.mark.parametrize("status", ["TOKENIZATION_ERROR", "INFERENCE_ERROR", "CALIBRATION_ERROR"])
def test_typed_live_errors_are_not_predictions(adapters, status):
    adapter = deepcopy(adapters[1])
    def fail(request):
        raise AdapterContractError(status, "NOT_EXPOSED")
    adapter._live = SimpleNamespace(detect=fail)
    record = adapter.predict("Synthetic text", sample_id="fixture-errors", truth_label=1)
    assert record.status == status and record.native_binary_prediction is None
    assert record.latency_ms is not None


def test_live_exception_does_not_echo_prompt_or_message(adapters):
    adapter = deepcopy(adapters[1])
    secret = "SENSITIVE_SYNTHETIC_MESSAGE"
    def fail(request):
        raise RuntimeError(secret + request.content.text)
    adapter._live = SimpleNamespace(detect=fail)
    record = adapter.predict("SYNTHETIC_PROMPT_CONTENT", sample_id="fixture-errors", truth_label=1)
    assert record.status == "INFERENCE_ERROR" and record.native_binary_prediction is None
    assert secret not in record.deterministic_json() and "SYNTHETIC_PROMPT_CONTENT" not in record.deterministic_json()


def test_live_hook_and_fixture_use_same_schema(adapters):
    adapter = deepcopy(adapters[1])
    output = native(adapter)
    adapter._live = SimpleNamespace(detect=lambda request: deepcopy(output))
    live = adapter.predict("Synthetic text", sample_id="fixture-001", truth_label=1)
    fixture = adapt(adapter, output)
    assert live.status == fixture.status == "OK"
    assert live.raw_score == fixture.raw_score and live.calibrated_score == fixture.calibrated_score
    assert live.native_binary_prediction == fixture.native_binary_prediction
    assert live.latency_ms is not None and fixture.latency_ms is None
    assert live.metadata.latency_basis == "LIVE_WALL_CLOCK"


@pytest.mark.parametrize("text", [None, "", "  ", 123, "\ud800"])
def test_invalid_input_never_calls_detector(adapters, text):
    adapter = deepcopy(adapters[1])
    adapter._live = SimpleNamespace(detect=lambda request: pytest.fail("invalid input must not reach inference"))
    assert adapter.predict(text, sample_id="fixture-invalid", truth_label=0).status == "INVALID_INPUT"


def test_model_free_phase3_import_and_no_project_dataset_access():
    code = """
import sys
from pathlib import Path
root = Path.cwd()
def audit(event, args):
    if event == 'open' and isinstance(args[0], (str, bytes)):
        if Path(args[0]).resolve().is_relative_to(root / 'Dataset'):
            raise AssertionError('project dataset access forbidden')
sys.addaudithook(audit)
from detection_service.research_protocol.prediction_contract import build_artifacts
assert build_artifacts()
assert not any(m in sys.modules for m in ('torch','transformers','sklearn'))
assert not any(m.startswith('detection_service.app.detectors') for m in sys.modules)
"""
    result = subprocess.run([sys.executable, "-B", "-c", code], cwd=phase2.ROOT, capture_output=True)
    assert result.returncode == 0, result.stderr.decode()


def test_frozen_files_and_phase2_unchanged():
    result = subprocess.run(["git", "diff", "--exit-code", "2e976f2c444001b12b6aa1196e46dde60ce8f0bd", "--",
        "detection_service/app", "detection_service/analysis", "detection_service/configs", "artifacts/models",
        "artifacts/research_protocol/detector_set_manifest_v1.json", "detection_service/research_protocol/detector_semantics.py"],
        cwd=phase2.ROOT, capture_output=True)
    assert result.returncode == 0, result.stdout.decode()
    assert phase2.sha(phase2.ROOT / phase2.OUT / phase2.NAME) == PHASE2_SHA


def test_non_ok_canonical_record_cannot_claim_benign(adapters):
    payload = adapt(adapters[0]).model_dump()
    payload.update(status="INFERENCE_ERROR", error_code="FAILED", raw_score=None,
                   calibrated_score=None, calibrator_id=None, native_binary_prediction=0)
    with pytest.raises(ValidationError):
        PredictionRecord.model_validate(payload)
    assert "INSUFFICIENT_INPUT" in STATUS_VALUES
