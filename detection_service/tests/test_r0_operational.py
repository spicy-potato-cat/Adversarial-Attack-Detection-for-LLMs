"""Offline historical-score projection tests; no runtime models or raw prompts."""

from copy import deepcopy
import hashlib
import json
import socket

import numpy as np
import pytest
from scipy.special import expit

from detection_service.research_protocol import r0_operational as op
from detection_service.research_protocol import r0_reproduction as old
from detection_service.research_protocol import detector_semantics as files
from detection_service.research_protocol.adapters import DetectorAdapter
from detection_service.research_protocol.core_metrics import evaluate_core
from detection_service.research_protocol.cross_regime import compatibility
from detection_service.research_protocol.uncertainty import BootstrapConfig


@pytest.fixture(scope="module")
def result():
    return op.reconstruct()


@pytest.fixture(scope="module")
def source():
    h = old.load_history()
    p = op.verified_policy()
    return h, p, op.score_records(h, p)


@pytest.mark.parametrize("field,count", [("rows",1135),("attack",183),("benign",952)])
def test_population(result, field, count):
    rows = result[1].rows
    actual = len(rows) if field == "rows" else sum(r.truth_label == (1 if field == "attack" else 0) for r in rows)
    assert actual == count


@pytest.mark.parametrize("index", range(3))
def test_exact_threshold_and_provenance(source, index):
    h, p, records = source
    point = p.manifest.points[index]
    assert point.threshold == op.THRESHOLDS[index]
    assert point.threshold_id == op.IDS[index]
    selected = [r for r in records if r.detector_id == point.detector_id]
    assert len(selected) == 1135
    for r in selected:
        assert r.model_evidence_kind == ("OOF" if index < 2 else "FROZEN_DEVELOPMENT_INFERENCE")
        score = r.calibrated_score if index == 0 else r.raw_score
        assert r.operational_binary_prediction == int(score >= op.THRESHOLDS[index])
        assert r.source_artifact_sha == h["hashes"][r.source_artifact_path]


def test_frozen_ds_calibration_not_fit(source):
    _, p, records = source
    params = p.contracts.detector("D_S")["calibrator_parameters"]
    selected = [r for r in records if r.detector_id == "ds_v2"]
    raw = np.asarray([r.raw_score for r in selected])
    clipped = np.clip(raw,1e-12,1-1e-12)
    expected = expit(params["slope"]*(np.log(clipped)-np.log1p(-clipped))+params["intercept"])
    assert np.array_equal(expected, [r.calibrated_score for r in selected])
    assert any(r.raw_score != r.calibrated_score for r in selected)


@pytest.mark.parametrize("index", range(3))
def test_independent_confusion_tallies(result, index):
    rows = result[1].rows
    actual = result[2].individual.detectors[index]
    assert actual.tp == sum(r.truth_label == 1 and r.decisions[index] == 1 for r in rows)
    assert actual.fn == sum(r.truth_label == 1 and r.decisions[index] == 0 for r in rows)
    assert actual.fp == sum(r.truth_label == 0 and r.decisions[index] == 1 for r in rows)
    assert actual.tn == sum(r.truth_label == 0 and r.decisions[index] == 0 for r in rows)


def test_patterns_common_mode_recovery(result):
    rows = [r for r in result[1].rows if r.truth_label]
    core = result[2].model_dump(mode="json")
    assert result[2] == evaluate_core(result[1])
    assert sum(p["count"] for p in core["failure_patterns"]["patterns"]) == 183
    for pair in result[2].common_mode.pairs:
        ids = result[1].provenance.primary_detector_ids
        a,b = ids.index(pair.left_detector),ids.index(pair.right_detector)
        assert pair.shared_fn_count == sum(r.decisions[a] == r.decisions[b] == 0 for r in rows)
    assert len(core["recovery"]["detectors"]) == 3


def test_policy_bound_bundle_and_complete_alignment(result):
    bundle = result[3]
    assert bundle.comparison_view_id == "OPERATIONAL_FIXED_V1"
    assert bundle.decision_view == "OPERATIONAL"
    assert bundle.operating_point_manifest_hash == op.POLICY_SHA
    assert result[1].coverage.status == "COMPLETE"
    assert result[1].coverage.ok_predictions == 3405


def test_uncertainty_production_domains(result):
    outputs = result[0]
    value = json.loads(outputs[op.OUT+"/r0_operational_uncertainty_v1.json"])
    for key, domain in (("attack","ATTACK_ONLY"),("benign","BENIGN_ONLY")):
        config = value[key]["config"]
        assert config == BootstrapConfig(unit="LINEAGE_CLUSTERED", domain=domain).model_dump(mode="json")
    assert len(value["attack"]["intervals"]) == 13
    assert len(value["benign"]["intervals"]) == 3


@pytest.mark.parametrize("field,value", [
    ("operational_threshold",0.5),("operational_threshold_id","override"),
    ("operating_policy_manifest_sha","0"*64),("model_evidence_kind","FINAL_IN_SAMPLE"),
    ("calibrated_score",0.0),("calibrator_sha","0"*64),
])
def test_tampered_record_rejected(source, field, value):
    _,p,records = source
    payload = records[0].model_dump()
    payload[field] = value
    with pytest.raises(ValueError):
        op.HistoricalOperationalScore.model_validate(payload, context={"operating_policy":p})


def test_no_policy_no_activation(source):
    with pytest.raises(ValueError):
        op.HistoricalOperationalScore.model_validate(source[2][0].model_dump())


def test_non_ok_null_only(source):
    _,p,records = source
    value = records[0].model_dump()
    value["status"] = "NON_OK"
    with pytest.raises(ValueError):
        op.HistoricalOperationalScore.model_validate(value, context={"operating_policy":p})
    value.update(operational_threshold=None,operational_threshold_id=None,operational_binary_prediction=None)
    assert op.HistoricalOperationalScore.model_validate(value, context={"operating_policy":p}).operational_binary_prediction is None


@pytest.mark.parametrize("change", ["missing","duplicate","non_ok","wrong_truth"])
def test_incomplete_or_conflicting_predictions_rejected(source, change):
    h,p,records = source
    altered = list(records)
    if change == "missing":
        altered.pop()
    elif change == "duplicate":
        altered.append(records[0])
    else:
        value = records[0].model_dump()
        if change == "wrong_truth":
            value["truth_label"] = 1-value["truth_label"]
        else:
            value.update(status="NON_OK",operational_threshold=None,operational_threshold_id=None,operational_binary_prediction=None)
        altered[0] = op.HistoricalOperationalScore.model_validate(value,context={"operating_policy":p})
    with pytest.raises(ValueError):
        op.align_operational(h, altered, p)


def test_historical_unchanged_and_unlike_views(result):
    inventory = files.read_json(files.ROOT/old.HASHES)["sha256"]
    assert all(files.sha(files.ROOT/p) == h for p,h in inventory.items())
    historic = json.loads((files.ROOT/old.OUT/"r0_cross_regime_bundle_v1.json").read_bytes())
    from detection_service.research_protocol.cross_regime import RegimeResultBundle
    assert compatibility(result[3], RegimeResultBundle.model_validate_json(json.dumps(historic)))


def test_no_model_inference_no_network(source, monkeypatch):
    def forbidden(*a,**kw):
        raise AssertionError("MODEL_INFERENCE_OR_NETWORK_FORBIDDEN")
    monkeypatch.setattr(DetectorAdapter,"predict",forbidden)
    monkeypatch.setattr(DetectorAdapter,"_load_live",forbidden)
    monkeypatch.setattr(socket,"create_connection",forbidden)
    h,p,_ = source
    assert len(op.score_records(h,p)) == 3405


def test_future_regimes_not_run(result):
    matrix = json.loads(result[0][op.OUT+"/r0_operational_cross_regime_matrix_v1.json"])
    assert matrix["regime_status"] == {"R0":"OBSERVED","R1":"NOT_RUN","R2-D_S":"NOT_RUN","R2-D_M-B":"NOT_RUN","R2-D_G":"NOT_RUN","R3":"NOT_RUN"}


def test_serialization_and_uncertainty_deterministic(result):
    assert result[0] == op.reconstruct()[0]
