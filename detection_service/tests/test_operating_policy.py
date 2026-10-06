"""Synthetic policy/activation checks; no real score selection or model execution."""

from copy import deepcopy
from dataclasses import FrozenInstanceError, replace
from fractions import Fraction
import inspect
import math

import jsonschema
from pydantic import ValidationError
import pytest

from detection_service.research_protocol import detector_semantics as phase2
from detection_service.research_protocol.adapters import DetectorAdapter, FrozenDetectorContracts, PHASE2_SHA, RULE_IDS
from detection_service.research_protocol import operating_policy as op
from detection_service.research_protocol.prediction import PredictionRecord
from detection_service.research_protocol.regime import RegimeContractError, manifest_hash
from detection_service.research_protocol.regime_contract import PREDICTION_SHA
from detection_service.research_protocol.threshold_selection import ALPHA, SelectionScore, select_threshold
from detection_service.tests.test_prediction_adapters import native


def scores(benign=None, positive=None):
    benign = [i / 200 for i in range(192)] if benign is None else benign
    positive = [.9] * 41 if positive is None else positive
    return [dict(sample_id="fixture-" + str(i), truth_label=label, partition="CALIBRATION", score=value)
            for i, (label, value) in enumerate([(0, x) for x in benign] + [(1, x) for x in positive])]


def test_alpha_exact():
    assert ALPHA == Fraction(3, 100)


def test_k_uses_floor():
    assert select_threshold(scores()).max_allowed_fp == 5
    assert select_threshold(scores([.1] * 33, [])).max_allowed_fp == 0
    assert select_threshold(scores([.1] * 34, [])).max_allowed_fp == 1


def test_threshold_uses_benign_only():
    assert select_threshold(scores()).threshold == math.nextafter(186 / 200, math.inf)


def test_positive_scores_do_not_change_threshold():
    a = select_threshold(scores())
    b = select_threshold(scores(positive=[0.] * 41))
    c = select_threshold(scores(positive=[1.] * 41))
    assert a == b == c


def test_prediction_rule_is_greater_equal():
    threshold = select_threshold(scores()).threshold
    assert int(threshold >= threshold) == 1
    assert int(math.nextafter(threshold, -math.inf) >= threshold) == 0


def test_boundary_tie_excluded():
    result = select_threshold(scores([.9] * 7 + [.1] * 185))
    assert result.boundary_score == .9 and result.boundary_ties == 7 and result.attained_fp == 0


@pytest.mark.parametrize("benign", [[.9] * 192, [i / 191 for i in range(192)], [.1] * 186 + [.9] * 6, [.1] * 187 + [.9] * 5])
def test_attained_fp_not_above_k(benign):
    result = select_threshold(scores(benign))
    assert result.attained_fp <= 5 and result.attained_fpr <= .03


def test_all_identical_benign_scores():
    result = select_threshold(scores([.5] * 192))
    assert result.attained_fp == 0 and result.threshold == math.nextafter(.5, math.inf)


def test_probability_maximum_has_finite_successor():
    result = select_threshold(scores([1.] * 192))
    assert result.threshold > 1 and math.isfinite(result.threshold) and result.attained_fp == 0


def test_zero_benign_rejected():
    with pytest.raises(RegimeContractError, match="ZERO_BENIGN"):
        select_threshold(scores([], [.5]))


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf"), None, "0.2", True, -.1, 1.1])
def test_invalid_score_rejected(value):
    with pytest.raises(ValidationError):
        select_threshold(scores([value]))


def test_nan_score_rejected():
    with pytest.raises(ValidationError):
        select_threshold(scores([math.nan]))


def test_inf_score_rejected():
    with pytest.raises(ValidationError):
        select_threshold(scores([math.inf]))


def test_missing_score_rejected():
    row = scores([.2])[0]
    del row["score"]
    with pytest.raises(ValidationError):
        select_threshold([row])


def test_duplicate_sample_rejected():
    row = scores([.2])[0]
    with pytest.raises(RegimeContractError, match="DUPLICATE"):
        select_threshold([row, row])


def test_wrong_partition_rejected():
    with pytest.raises(ValidationError):
        select_threshold([{**scores([.2])[0], "partition": "VALIDATION"}])


def test_threshold_deterministic():
    rows = scores()
    assert select_threshold(rows) == select_threshold(list(reversed(rows)))


def test_threshold_serialization_deterministic():
    a, b = select_threshold(scores()), select_threshold(scores())
    assert phase2.canonical_bytes(a.model_dump(mode="json")) == phase2.canonical_bytes(b.model_dump(mode="json"))


@pytest.fixture(scope="module")
def contracts():
    return FrozenDetectorContracts()


def fixture_manifest(contracts):
    points = []
    for label in ("D_S", "D_M-B", "D_G"):
        d = contracts.detector(label)
        boundary = .4 if label == "D_G" else .6
        points.append(dict(stack_label=label, detector_id=d["detector_id"], threshold_input_score_type=op.FIELDS[label],
            calibrator_id=d["calibrator_id"], calibrator_sha=d["calibrator_hash"], calibration_used_for_threshold=label == "D_S",
            model_revision=d["model_revision"], model_sha=d["model_hash"], threshold=math.nextafter(boundary, math.inf),
            threshold_id=op.THRESHOLD_IDS[label], boundary_score=boundary, boundary_ties=1, benign_count=192,
            max_allowed_fp=5, attained_fp=3, attained_fpr=3/192, diagnostic_positive_count=41,
            diagnostic_tp=30, diagnostic_fn=11, diagnostic_recall=30/41, score_evidence_artifact="fixture.csv",
            score_evidence_sha="0"*64, freeze_status="FROZEN"))
    value = dict(manifest_version="operating_point_manifest_v1", policy_id=op.POLICY_ID, algorithm_id="benign_empirical_fpr_budget_v1",
        status="FROZEN", target_fpr=.03, alpha_rational="3/100", decision_operator=">=",
        tie_policy="binary64_nextafter_boundary_toward_positive_infinity", selection_partition="CALIBRATION",
        selection_population_id="fixture-calibration", selection_population_revision=op.MEMBERSHIP_SHA,
        selection_manifest_hash=op.MEMBERSHIP_SHA, selection_membership_sha="0"*64, selection_sample_count=233,
        selection_benign_count=192, selection_attack_count=41, detector_set_manifest_sha=PHASE2_SHA,
        prediction_schema_sha=PREDICTION_SHA, regime_contract_sha=op.REGIME_SHA, evidence_kind="SYNTHETIC_FIXTURE",
        predeclared_commit="0"*40, predeclared_policy_sha="0"*64, execution_commit="0"*40,
        created_at="2000-01-01T00:00:00Z", points=points)
    value["manifest_hash"] = manifest_hash(value)
    return value


def load_fixture(tmp_path, contracts, value=None):
    path = tmp_path / "fixture_policy.json"
    payload = fixture_manifest(contracts) if value is None else value
    path.write_bytes(phase2.manifest_bytes(payload))
    return op.load_frozen_operating_policy(path, expected_sha=phase2.sha(path), engineering_fixture=True)


@pytest.fixture(scope="module")
def policy(tmp_path_factory, contracts):
    return load_fixture(tmp_path_factory.mktemp("policy"), contracts)


def prediction(policy, label="D_M-B", raw=.55, calibrated=.55):
    adapter = DetectorAdapter(label, policy.contracts)
    return adapter.adapt_fixture(native(adapter, raw=raw, calibrated=calibrated), sample_id="fixture-001", truth_label=1)


def test_ds_operating_score_is_calibrated(policy):
    result = op.apply_operating_policy(prediction(policy, "D_S", raw=.9, calibrated=.2), policy)
    assert result.operational_binary_prediction == 0


def test_dmb_operating_score_is_raw(policy):
    result = op.apply_operating_policy(prediction(policy, raw=.9, calibrated=.2), policy)
    assert result.operational_binary_prediction == 1


def test_dg_operating_score_is_raw(policy):
    assert op.apply_operating_policy(prediction(policy, "D_G", raw=.9), policy).operational_binary_prediction == 1


@pytest.mark.parametrize("index,score_type", [(0, "raw_score"), (1, "calibrated_score"), (2, "calibrated_score")])
def test_wrong_score_type_rejected(contracts, index, score_type):
    value = fixture_manifest(contracts)["points"][index]
    value["threshold_input_score_type"] = score_type
    with pytest.raises(ValidationError, match="SCORE_TYPE"):
        op.OperatingPoint.model_validate(value)


def test_ds_wrong_score_type_rejected(contracts):
    value = fixture_manifest(contracts)["points"][0]
    value["threshold_input_score_type"] = "raw_score"
    with pytest.raises(ValidationError):
        op.OperatingPoint.model_validate(value)


def test_dmb_wrong_score_type_rejected(contracts):
    value = fixture_manifest(contracts)["points"][1]
    value["threshold_input_score_type"] = "calibrated_score"
    with pytest.raises(ValidationError):
        op.OperatingPoint.model_validate(value)


def test_dg_calibrated_score_not_required(policy):
    result = op.apply_operating_policy(prediction(policy, "D_G"), policy)
    assert result.calibrated_score is None and result.calibrator_id is None


def test_threshold_id_distinct_from_native_rule_id(policy):
    assert all(p.threshold_id != RULE_IDS[p.stack_label] for p in policy.manifest.points)


def test_operational_fields_rejected_without_manifest(policy):
    payload = prediction(policy).model_dump()
    payload["operational_threshold"] = .6
    with pytest.raises(ValidationError):
        PredictionRecord.model_validate(payload)
    result = op.apply_operating_policy(prediction(policy), policy)
    with pytest.raises(ValidationError, match="VERIFIED_OPERATING_POLICY_REQUIRED"):
        op.OperationalPredictionRecord.model_validate(result.model_dump())


def test_operational_fields_allowed_with_valid_manifest(policy):
    result = op.apply_operating_policy(prediction(policy), policy)
    assert result.schema_version == "prediction_operational_v1" and result.operational_threshold_id == op.THRESHOLD_IDS["D_M-B"]


@pytest.mark.parametrize("field,value", [("operational_threshold", .3), ("operational_threshold_id", "other"),
    ("operational_binary_prediction", 1), ("operating_policy_manifest_sha", "0"*64)])
def test_operational_override_rejected(policy, field, value):
    result = op.apply_operating_policy(prediction(policy), policy)
    payload = {**result.model_dump(), field: value}
    with pytest.raises(ValidationError):
        op.OperationalPredictionRecord.model_validate(payload, context={"operating_policy": policy})


def test_operational_prediction_correct(policy):
    threshold = policy.point("dm_b_v1").threshold
    assert op.apply_operating_policy(prediction(policy, raw=threshold), policy).operational_binary_prediction == 1
    assert op.apply_operating_policy(prediction(policy, raw=math.nextafter(threshold, -math.inf)), policy).operational_binary_prediction == 0


def test_non_ok_record_has_no_operational_prediction(policy):
    adapter = DetectorAdapter("D_G", policy.contracts)
    failure = adapter.adapt_fixture({}, sample_id="fixture-001", truth_label=1)
    result = op.apply_operating_policy(failure, policy)
    assert result.status != "OK" and result.operational_binary_prediction is None and result.operational_threshold is None


def test_native_decision_preserved(policy):
    before = prediction(policy)
    after = op.apply_operating_policy(before, policy)
    assert op.native_prediction(after) == before


def test_native_and_operational_decisions_may_differ(policy):
    result = op.apply_operating_policy(prediction(policy), policy)
    assert result.native_binary_prediction == 1 and result.operational_binary_prediction == 0


def test_dg_native_or_not_overwritten(policy):
    result = op.apply_operating_policy(prediction(policy, "D_G", raw=.5), policy)
    assert result.native_binary_prediction == 0 and result.operational_binary_prediction == 1


def test_frozen_manifest_cannot_be_mutated(policy):
    with pytest.raises(FrozenInstanceError):
        policy.file_sha = "0"*64
    with pytest.raises(ValidationError):
        policy.manifest.points[0].threshold = .2
    with pytest.raises(RegimeContractError):
        policy.manifest.model_copy(update={"target_fpr": .05})


def test_evaluator_cannot_refit_threshold():
    assert "select_threshold" not in op.__dict__
    assert "fit" not in inspect.signature(op.apply_operating_policy).parameters


def test_future_regime_cannot_supply_threshold_override(policy):
    with pytest.raises(TypeError):
        op.apply_operating_policy(prediction(policy), policy, threshold=.2)
    with pytest.raises(TypeError):
        op.apply_operating_policy(prediction(policy), policy, target_fpr=.01, optimize_threshold=True)


def test_missing_policy_blocks_operational_evaluation(tmp_path):
    with pytest.raises(RegimeContractError, match="MISSING"):
        op.load_frozen_operating_policy(tmp_path / "missing.json", expected_sha="0"*64)


def test_manifest_hash_validation(tmp_path, contracts):
    value = fixture_manifest(contracts)
    value["manifest_hash"] = "0"*64
    with pytest.raises(ValidationError, match="SELF_HASH"):
        load_fixture(tmp_path, contracts, value)


@pytest.mark.parametrize("field", ["detector_set_manifest_sha", "prediction_schema_sha", "regime_contract_sha"])
def test_upstream_manifest_binding(tmp_path, contracts, field):
    value = fixture_manifest(contracts)
    value[field] = "0"*64
    value["manifest_hash"] = manifest_hash(value)
    with pytest.raises(RegimeContractError, match="BINDING"):
        load_fixture(tmp_path, contracts, value)


def test_threshold_detector_binding(tmp_path, contracts):
    value = fixture_manifest(contracts)
    value["points"][0]["detector_id"] = "dm_b_v1"
    value["manifest_hash"] = manifest_hash(value)
    with pytest.raises(RegimeContractError, match="BINDING"):
        load_fixture(tmp_path, contracts, value)


def test_threshold_score_type_binding(contracts):
    value = fixture_manifest(contracts)["points"][0]
    value["threshold_input_score_type"] = "raw_score"
    with pytest.raises(ValidationError):
        op.OperatingPoint.model_validate(value)


def test_fixture_policy_is_not_approved_for_real_use(tmp_path, contracts):
    path = tmp_path / "fixture.json"
    path.write_bytes(phase2.manifest_bytes(fixture_manifest(contracts)))
    with pytest.raises(RegimeContractError, match="UNAPPROVED"):
        op.load_frozen_operating_policy(path, expected_sha=phase2.sha(path))


def test_policy_cannot_be_constructed_without_verification(policy):
    with pytest.raises(RegimeContractError, match="MUST_BE_LOADED"):
        op.FrozenOperatingPolicy(policy.manifest, policy.file_sha, policy.contracts)


def test_policy_replace_cannot_bypass_verification(policy):
    with pytest.raises(RegimeContractError, match="MUST_BE_LOADED"):
        replace(policy, file_sha="0"*64)
    with pytest.raises(RegimeContractError, match="MUST_BE_LOADED"):
        replace(policy, engineering_fixture=False)


def test_policy_file_tampering_rejected(tmp_path, contracts):
    path = tmp_path / "policy.json"
    path.write_bytes(phase2.manifest_bytes(fixture_manifest(contracts)))
    with pytest.raises(RegimeContractError, match="FILE_HASH"):
        op.load_frozen_operating_policy(path, expected_sha="0"*64, engineering_fixture=True)


def test_calibration_alignment_rejects_partial_or_wrong_labels():
    from detection_service.research_protocol.freeze_operating_points import align_rows
    membership = [dict(record_id="fixture-"+str(i), canonical_label=str(int(i < 41))) for i in range(233)]
    rows = [dict(sample_id=r["record_id"], truth_label=int(r["canonical_label"]), partition="CALIBRATION") for r in membership]
    assert len(align_rows(rows, membership)) == 233
    with pytest.raises(RegimeContractError):
        align_rows(rows[:-1], membership)
    rows[0]["truth_label"] = 0
    with pytest.raises(RegimeContractError):
        align_rows(rows, membership)


def test_operational_schema_requires_bound_threshold(policy):
    schema = op.operational_schema(policy)
    jsonschema.Draft202012Validator.check_schema(schema)
    result = op.apply_operating_policy(prediction(policy), policy).model_dump(mode="json")
    jsonschema.validate(result, schema)
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate({**result, "operational_threshold": .2}, schema)
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate({**result, "operational_binary_prediction": 1}, schema)
