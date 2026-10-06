"""Hand-computed synthetic Phase-6-10 truth tables; no real experiment scoring."""

from copy import deepcopy
import inspect
import itertools
import json
from pathlib import Path
import subprocess
import sys

from pydantic import ValidationError
import pytest

from detection_service.research_protocol import core_metrics as metrics
from detection_service.research_protocol import core_metrics_contract as contract
from detection_service.research_protocol import detector_semantics as phase2
from detection_service.research_protocol.adapters import AdapterContractError, FrozenDetectorContracts
from detection_service.research_protocol.alignment import (
    AlignedEvaluation, IncompleteEvaluationError, POLICY_SHA, PRIMARY, PredictionBinding, align_evaluation, bind_predictions,
)
from detection_service.research_protocol.metric_types import PATTERNS, Rate, rate
from detection_service.research_protocol.operating_policy import apply_operating_policy, load_frozen_operating_policy
from detection_service.research_protocol.prediction import PredictionRecord
from detection_service.research_protocol.regime import RegimeContractError, RegimeManifest, create_manifest
from detection_service.research_protocol.regime_contract import sample_payload


@pytest.fixture(scope="module")
def contracts():
    return FrozenDetectorContracts()


@pytest.fixture(scope="module")
def core_bundle(contracts):
    return contract.synthetic_core(contracts)


@pytest.fixture(scope="module")
def r2_bundle(contracts):
    return contract.synthetic_r2(contracts)[0]


@pytest.fixture(scope="module")
def core_table(core_bundle, contracts):
    return contract.align_fixture(core_bundle, contracts)


@pytest.fixture(scope="module")
def core_result(core_table):
    return metrics.evaluate_core(core_table)


@pytest.fixture(scope="module")
def r2_table(r2_bundle, contracts):
    return contract.align_fixture(r2_bundle, contracts)


@pytest.fixture(scope="module")
def r2_result(r2_table):
    return metrics.evaluate_core(r2_table)


@pytest.fixture(scope="module")
def policy():
    return load_frozen_operating_policy(phase2.ROOT / "artifacts/research_protocol/operating_point_manifest_v1.json", expected_sha=POLICY_SHA)


def align(bundle, contracts, *, view="EXPLICIT", strict=True, policy=None, decisions=None, provenance="TEST_FIXTURE_HAND_DECLARED_V1"):
    explicit = {(r["sample_id"],r["detector_id"]):r["decision"] for r in bundle["explicit_decisions"]} if decisions is None else decisions
    return align_evaluation(bundle["manifest"], bundle["predictions"], binding=bundle["prediction_binding"],
        decision_view=view, contracts=contracts, strict_complete=strict, operating_policy=policy,
        explicit_decisions=explicit if view=="EXPLICIT" else None, explicit_provenance_id=provenance if view=="EXPLICIT" else None)


def case(contracts, outcomes):
    samples, decisions = [], {}
    for i, (label, votes) in enumerate(outcomes):
        sample = sample_payload("R0_NON_ADAPTIVE", sample_id="case-"+format(i,"03d"), label=label)
        samples.append(sample)
        decisions[sample["sample_id"]] = tuple(votes)
    return contract.align_fixture(contract.fixture_bundle(contracts, samples, decisions), contracts)


def failed_record(record):
    value = deepcopy(record)
    value.update(status="INFERENCE_ERROR", error_code="FIXTURE_INFERENCE_FAILURE", raw_score=None,
        calibrated_score=None, calibrator_id=None, native_binary_prediction=None)
    return value


def test_confusion_matrix_exact(core_result):
    assert [(d.tp,d.fp,d.tn,d.fn) for d in core_result.individual.detectors] == [(4,1,1,4)]*3


@pytest.mark.parametrize("metric,expected,numerator,denominator", [
    ("accuracy",.5,5,10), ("precision",.8,4,5), ("recall",.5,4,8), ("specificity",.5,1,2),
    ("f1",8/13,8,13), ("fpr",.5,1,2), ("fnr",.5,4,8), ("npv",.2,1,5)])
def test_individual_rates(core_result, metric, expected, numerator, denominator):
    for detector in core_result.individual.detectors:
        result = getattr(detector,metric)
        assert (result.value,result.numerator,result.denominator,result.status,result.reason) == (expected,numerator,denominator,"DEFINED",None)


def test_individual_attack_denominator(core_result):
    assert core_result.individual.attack_count==8 and core_result.individual.population_count==10
    assert all(d.fnr.denominator==8 and d.fpr.denominator==2 for d in core_result.individual.detectors)


@pytest.mark.parametrize("outcomes,fields", [([(1,(0,0,0))],("precision","specificity","fpr")),
    ([(0,(0,0,0))],("precision","recall","fnr","f1")), ([(1,(1,1,1))],("specificity","fpr","npv"))])
def test_zero_denominators(contracts, outcomes, fields):
    result=metrics.individual_metrics(case(contracts,outcomes))
    for detector in result.detectors:
        for name in fields:
            value=getattr(detector,name)
            assert value.value is None and value.denominator==0 and value.status=="UNDEFINED" and value.reason=="ZERO_DENOMINATOR"


@pytest.mark.parametrize("view", ["NATIVE","EXPLICIT"])
def test_non_ok_prediction_blocks_strict_metrics(core_bundle, contracts, view):
    bundle=deepcopy(core_bundle)
    key=(bundle["predictions"][0]["sample_id"],bundle["predictions"][0]["detector_id"])
    bundle["predictions"][0]=failed_record(bundle["predictions"][0])
    bundle["explicit_decisions"]=[r for r in bundle["explicit_decisions"] if (r["sample_id"],r["detector_id"])!=key]
    with pytest.raises(IncompleteEvaluationError) as error:
        align(bundle,contracts,view=view)
    assert error.value.coverage.non_ok_predictions==1 and error.value.coverage.coverage_rate==29/30
    table=align(bundle,contracts,view=view,strict=False)
    assert len(table.rows)==10 and table.rows[0].decisions[0] is None
    for function in (metrics.individual_metrics,metrics.common_mode_metrics,metrics.failure_patterns,metrics.recovery_metrics,
                     metrics.evasion_transfer_metrics,metrics.evaluate_core):
        with pytest.raises(IncompleteEvaluationError):
            function(table)


def test_failed_inference_cannot_receive_explicit_vote(core_bundle,contracts):
    bundle=deepcopy(core_bundle)
    bundle["predictions"][0]=failed_record(bundle["predictions"][0])
    with pytest.raises(RegimeContractError,match="NON_OK_EXPLICIT"):
        align(bundle,contracts,strict=False)


def test_missing_prediction_blocks_strict_metrics(core_bundle,contracts):
    bundle=deepcopy(core_bundle)
    removed=bundle["predictions"].pop()
    bundle["explicit_decisions"]=[r for r in bundle["explicit_decisions"] if (r["sample_id"],r["detector_id"])!=(removed["sample_id"],removed["detector_id"])]
    with pytest.raises(IncompleteEvaluationError) as error:
        align(bundle,contracts)
    assert error.value.coverage.missing_predictions==1
    diagnostic=align(bundle,contracts,strict=False)
    assert diagnostic.rows[-1].decisions[-1] is None and len(diagnostic.rows)==10


def test_missing_requested_decision_blocks_strict(core_bundle,contracts):
    explicit={(r["sample_id"],r["detector_id"]):r["decision"] for r in core_bundle["explicit_decisions"]}
    explicit.pop(next(iter(explicit)))
    with pytest.raises(IncompleteEvaluationError) as error:
        align(core_bundle,contracts,decisions=explicit)
    assert error.value.coverage.missing_decisions==1 and error.value.coverage.ok_predictions==30


def test_duplicate_detector_sample_rejected(core_bundle,contracts):
    bundle=deepcopy(core_bundle)
    bundle["predictions"].append(bundle["predictions"][0])
    with pytest.raises(RegimeContractError,match="DUPLICATE_DETECTOR_SAMPLE"):
        align(bundle,contracts)


@pytest.mark.parametrize("label", [0,None])
def test_truth_label_mismatch_rejected(core_bundle,contracts,label):
    bundle=deepcopy(core_bundle)
    bundle["predictions"][0]["truth_label"]=label
    bundle["predictions"][0]["metadata"]["unlabeled_inference"]=label is None
    with pytest.raises(RegimeContractError,match="TRUTH_LABEL_CONFLICT"):
        align(bundle,contracts)


@pytest.mark.parametrize("field,value", [("partition","VALIDATION"),("threat_regime","R1_SHIFTED_UNSEEN"),
    ("experiment_id","WRONG-EXPERIMENT"),("regime_manifest_sha","0"*64),
    ("detector_manifest_sha","0"*64),("prediction_schema_sha","0"*64)])
def test_batch_binding_conflicts_rejected(core_bundle,contracts,field,value):
    bundle=deepcopy(core_bundle)
    bundle["prediction_binding"][field]=value
    with pytest.raises(RegimeContractError,match="REGIME_BINDING"):
        align(bundle,contracts)


@pytest.mark.parametrize("field,value", [("sample_id","unknown"),("detector_id","dm_a_v1"),
    ("detector_role","PRIMARY_EXTERNAL_GUARD"),("model_hash","0"*64),
    ("native_binary_prediction",True),("raw_score",float("nan")),("schema_version","unknown")])
def test_prediction_contract_conflicts_rejected(core_bundle,contracts,field,value):
    bundle=deepcopy(core_bundle)
    bundle["predictions"][0][field]=value
    with pytest.raises((RegimeContractError,AdapterContractError,ValidationError)):
        align(bundle,contracts)


@pytest.mark.parametrize("view", ["AUTO","BEST_FPR","OPTIMIZED","DYNAMIC",None])
def test_unapproved_decision_views_rejected(core_bundle,contracts,view):
    with pytest.raises(RegimeContractError,match="INVALID_DECISION_VIEW"):
        align(core_bundle,contracts,view=view)


@pytest.mark.parametrize("value", [True,2,"0",None])
def test_explicit_binary_strict(core_bundle,contracts,value):
    bundle=deepcopy(core_bundle)
    bundle["explicit_decisions"][0]["decision"]=value
    with pytest.raises(RegimeContractError,match="BINARY_DECISIONS"):
        align(bundle,contracts)


@pytest.mark.parametrize("value", [None,""," "])
def test_explicit_provenance_required(core_bundle,contracts,value):
    with pytest.raises(RegimeContractError,match="PROVENANCE_REQUIRED"):
        align(core_bundle,contracts,provenance=value)


def test_explicit_does_not_choose_from_scores(core_bundle,contracts):
    bundle=deepcopy(core_bundle)
    for row in bundle["explicit_decisions"]:
        row["decision"]=1-row["decision"]
    result=metrics.evaluate_core(align(bundle,contracts))
    assert result.individual.provenance.explicit_provenance_id=="TEST_FIXTURE_HAND_DECLARED_V1"
    assert result.individual.detectors[0].fn==4
    assert result.individual.provenance.operational_thresholds is None
    assert result.individual.provenance.explicit_decisions_sha!=metrics.evaluate_core(align(core_bundle,contracts)).individual.provenance.explicit_decisions_sha


def test_native_view_uses_native_only(core_bundle,contracts):
    table=align(core_bundle,contracts,view="NATIVE")
    assert table.rows==align(core_bundle,contracts).rows
    assert table.provenance.operating_policy_sha is None and table.provenance.explicit_provenance_id is None


def test_operational_policy_binding_required(core_bundle,contracts):
    with pytest.raises(RegimeContractError,match="OPERATING_POLICY_REQUIRED"):
        align(core_bundle,contracts,view="OPERATIONAL")


def operational_bundle(core_bundle,policy):
    bundle=deepcopy(core_bundle)
    bundle["predictions"]=[apply_operating_policy(PredictionRecord.model_validate(r),policy).model_dump() for r in bundle["predictions"]]
    return bundle


def test_operational_view_consumes_frozen_decisions(core_bundle,contracts,policy):
    bundle=operational_bundle(core_bundle,policy)
    table=align(bundle,contracts,view="OPERATIONAL",policy=policy)
    result=metrics.evaluate_core(table)
    assert result.individual.provenance.operating_policy_sha==POLICY_SHA
    assert result.individual.provenance.operational_thresholds==tuple(p.threshold for p in policy.manifest.points)
    assert all((d.tp,d.fp,d.tn,d.fn)==(4,1,1,4) for d in result.individual.detectors)


@pytest.mark.parametrize("field,value", [("operational_threshold",.5),("operational_threshold_id","wrong"),
    ("operational_binary_prediction",0),("operating_policy_manifest_sha","0"*64)])
def test_operational_override_rejected(core_bundle,contracts,policy,field,value):
    bundle=operational_bundle(core_bundle,policy)
    bundle["predictions"][0][field]=value
    with pytest.raises((RegimeContractError,ValidationError)):
        align(bundle,contracts,view="OPERATIONAL",policy=policy)


def test_operational_non_ok_stays_null(core_bundle,contracts,policy):
    bundle=deepcopy(core_bundle)
    bundle["predictions"][0]=failed_record(bundle["predictions"][0])
    bundle=operational_bundle(bundle,policy)
    assert bundle["predictions"][0]["operational_binary_prediction"] is None
    with pytest.raises(IncompleteEvaluationError):
        align(bundle,contracts,view="OPERATIONAL",policy=policy)


def test_failure_indicator(core_table):
    for row in core_table.rows:
        for i in range(3):
            assert metrics.failure_indicator(row,i)==int(row.truth_label==1 and row.decisions[i]==0)


def test_fnr_matches_individual_metrics(core_result):
    for (i,j),pair in zip(((0,1),(0,2),(1,2)),core_result.common_mode.pairs):
        assert pair.left_fnr==core_result.individual.detectors[i].fnr
        assert pair.right_fnr==core_result.individual.detectors[j].fnr


def test_pairwise_shared_fn_jfn_reference_jaccard(core_result):
    for pair in core_result.common_mode.pairs:
        assert pair.shared_fn_count==2 and pair.jfn==rate(2,8)
        assert pair.independence_reference.value==.25 and pair.ejf.value==0.
        assert (pair.intersection_count,pair.union_count)==(2,6) and pair.fn_jaccard==rate(2,6)


@pytest.mark.parametrize("outcomes,expected", [([(1,(0,0,0)),(1,(1,1,1))],.25),
    ([(1,(0,1,1)),(1,(1,0,1))],-.25)])
def test_ejf_signs(contracts,outcomes,expected):
    pair=metrics.common_mode_metrics(case(contracts,outcomes)).pairs[0]
    assert pair.ejf.value==expected


def test_independence_reference_is_product_of_reported_fnrs(contracts):
    table=case(contracts,[(1,(0,0,1)),(1,(1,0,1)),(1,(1,1,1)),(1,(1,1,1)),(1,(1,1,1))])
    pair=metrics.common_mode_metrics(table).pairs[0]
    assert pair.independence_reference.value==pair.left_fnr.value*pair.right_fnr.value==.2*.4


def test_jaccard_zero_union_returns_null(contracts):
    common=metrics.common_mode_metrics(case(contracts,[(1,(1,1,1))]))
    assert all(p.union_count==0 and p.fn_jaccard.value is None and p.fn_jaccard.reason=="ZERO_DENOMINATOR" for p in common.pairs)


def test_all_three_fn_and_jfn(core_result):
    assert core_result.common_mode.all_three_fn_count==1 and core_result.common_mode.all_three_jfn==rate(1,8)


def test_primary_pairs_only_and_comparator_excluded(core_result):
    assert [(p.left_detector,p.right_detector) for p in core_result.common_mode.pairs]==[("ds_v2","dm_b_v1"),("ds_v2","dg_v1"),("dm_b_v1","dg_v1")]
    assert core_result.individual.provenance.primary_detector_labels==PRIMARY
    assert "dm_a" not in core_result.deterministic_bytes().decode()


@pytest.mark.parametrize("pattern",PATTERNS)
def test_failure_pattern_bit_order_and_every_pattern(core_result,core_table,pattern):
    row=next(r for r in core_table.rows if r.sample_id=="core-attack-"+pattern)
    assert "".join(str(metrics.failure_indicator(row,i)) for i in range(3))==pattern
    result=next(p for p in core_result.failure_patterns.patterns if p.pattern_id==pattern)
    assert result.count==1 and result.attack_rate==rate(1,8)


def test_failure_pattern_sum_fn_and_shared_invariants(core_result):
    p={p.pattern_id:p.count for p in core_result.failure_patterns.patterns}
    assert sum(p.values())==8
    for i,d in enumerate(core_result.individual.detectors):
        assert sum(v for k,v in p.items() if k[i]=="1")==d.fn
    assert p["111"]==core_result.common_mode.all_three_fn_count
    assert (p["110"]+p["111"],p["101"]+p["111"],p["011"]+p["111"])==tuple(pair.shared_fn_count for pair in core_result.common_mode.pairs)


@pytest.mark.parametrize("index,pattern",[(0,"011"),(1,"101"),(2,"110")])
def test_unique_catch_recovery_pattern_and_denominator(core_result,index,pattern):
    result=core_result.recovery.detectors[index]
    assert result.unique_catch_pattern==pattern and result.unique_catch_count==1 and result.unique_catch_rate==rate(1,8)
    assert result.both_others_miss_count==2 and result.conditional_recovery==rate(1,2)


def test_recovery_zero_denominator_returns_null(contracts):
    recovery=metrics.recovery_metrics(case(contracts,[(1,(1,1,1))]))
    assert all(d.conditional_recovery==rate(0,0) for d in recovery.detectors)


@pytest.mark.parametrize("index",range(3))
def test_r2_target_evasion_valid_denominator_and_transfers(r2_result,index):
    target=r2_result.evasion_transfer.targets[index]
    assert target.valid_attempt_count==100 and target.target_evasion_count==40 and target.target_evasion_rate==rate(40,100)
    assert tuple(t.joint_evasion_count for t in target.transfers)==(10,20)
    assert tuple(t.etr.value for t in target.transfers)==(.25,.5)
    assert all(t.etr.denominator==40 for t in target.transfers)
    ids=r2_result.individual.provenance.primary_detector_ids
    assert tuple(t.transfer_detector for t in target.transfers)==tuple(d for i,d in enumerate(ids) if i!=index)


def test_attack_success_not_implicit_evasion(r2_table,r2_result):
    assert sum(r.attack_success is True for r in r2_table.rows)==180
    assert sum(t.target_evasion_count for t in r2_result.evasion_transfer.targets)==120
    assert all(not r.attack_success for r in r2_table.rows if r.truth_label and r.valid_attack_attempt and r.decisions[PRIMARY.index(r.target_detector)]==0)


def test_invalid_and_benign_attempts_excluded(r2_table,r2_result):
    assert len(r2_table.rows)==309 and sum(not r.valid_attack_attempt for r in r2_table.rows)==6
    assert sum(t.valid_attempt_count for t in r2_result.evasion_transfer.targets)==300
    assert sum(r.truth_label==0 and r.valid_attack_attempt for r in r2_table.rows)==3


def test_multiple_lineage_descendants_preserved(r2_table,r2_result):
    assert len(r2_table.rows)==309 and len({r.lineage_id for r in r2_table.rows})==15
    assert all(r.parent_sample_id is not None for r in r2_table.rows)
    for target in r2_result.evasion_transfer.targets:
        assert (target.unique_lineage_count,target.valid_attempt_lineage_count,target.target_evasion_lineage_count)==(5,5,5)


def test_zero_target_evasions_returns_null_etr(r2_bundle,contracts):
    bundle=deepcopy(r2_bundle)
    for row in bundle["explicit_decisions"]:
        row["decision"]=1
    result=metrics.evasion_transfer_metrics(align(bundle,contracts))
    assert all(t.target_evasion_rate==rate(0,100) and all(x.etr==rate(0,0) for x in t.transfers) for t in result.targets)


def test_zero_valid_attempts_returns_null_target_rate(r2_bundle,contracts):
    bundle=deepcopy(r2_bundle)
    payload=bundle["manifest"]
    for row in payload["samples"]:
        row.update(valid_attack_attempt=False,attack_success=False)
    bundle["manifest"]=create_manifest(**payload).model_dump(mode="json")
    bundle["prediction_binding"]=bind_predictions(RegimeManifest.model_validate(bundle["manifest"])).model_dump()
    result=metrics.evasion_transfer_metrics(align(bundle,contracts))
    assert all(t.target_evasion_rate==rate(0,0) for t in result.targets)


def test_r2_target_must_match_manifest(r2_bundle,contracts):
    bundle=deepcopy(r2_bundle)
    payload=bundle["manifest"]
    payload["samples"][0]["target_detector"]="ALL"
    with pytest.raises((RegimeContractError,ValidationError),match="R2_REQUIRES_SINGLE"):
        align(bundle,contracts)


def test_r3_rejected_by_r2_transfer_metric(r2_bundle,contracts):
    bundle=deepcopy(r2_bundle)
    payload=bundle["manifest"]
    payload["threat_regime"]="R3_ENSEMBLE_TARGETED"
    for row in payload["samples"]:
        row.update(threat_regime="R3_ENSEMBLE_TARGETED",target_detector="ALL")
    bundle["manifest"]=create_manifest(**payload).model_dump(mode="json")
    bundle["prediction_binding"]=bind_predictions(RegimeManifest.model_validate(bundle["manifest"])).model_dump()
    table=align(bundle,contracts)
    with pytest.raises(RegimeContractError,match="REQUIRES_R2"):
        metrics.evasion_transfer_metrics(table)
    assert metrics.evaluate_core(table).evasion_transfer is None


def test_no_attack_population_returns_undefined_failure_rates(contracts):
    result=metrics.evaluate_core(case(contracts,[(0,(0,0,0))]))
    assert result.common_mode.all_three_jfn.value is None
    assert all(p.jfn.value is None and p.independence_reference.value is None and p.ejf.value is None for p in result.common_mode.pairs)
    assert all(p.attack_rate.value is None for p in result.failure_patterns.patterns)


def test_empty_population_consistent_undefined(contracts):
    template=contract.synthetic_core(contracts)["manifest"]
    template.update(samples=[],sample_count=0,attack_count=0,benign_count=0)
    manifest=create_manifest(**template)
    table=align_evaluation(manifest,[],binding=bind_predictions(manifest),decision_view="NATIVE",contracts=contracts)
    result=metrics.evaluate_core(table)
    assert result.individual.population_count==0 and table.coverage.coverage_rate is None
    assert all(d.accuracy==rate(0,0) for d in result.individual.detectors)


def test_result_provenance_and_deterministic_serialization(core_bundle,contracts,core_result):
    shuffled=deepcopy(core_bundle)
    shuffled["predictions"].reverse()
    shuffled["explicit_decisions"].reverse()
    other=metrics.evaluate_core(align(shuffled,contracts))
    assert other.deterministic_bytes()==core_result.deterministic_bytes()
    assert other.deterministic_bytes().endswith(b"\n") and not other.deterministic_bytes().endswith(b"\n\n")
    assert metrics.CoreMetricsResult.model_validate_json(other.deterministic_bytes())==other
    for section in (other.individual,other.common_mode,other.failure_patterns,other.recovery):
        assert section.provenance.experiment_id==core_bundle["manifest"]["experiment_id"]
        assert section.provenance.regime_manifest_sha==core_bundle["manifest"]["manifest_hash"]
        assert section.alignment_sha==core_result.individual.alignment_sha


def test_alignment_is_immutable_and_hash_bound(core_table):
    with pytest.raises(ValidationError):
        core_table.rows=()
    payload=core_table.model_dump()
    payload["rows"][0]["decisions"]=(0,0,0)
    with pytest.raises((RegimeContractError,ValidationError),match="HASH_MISMATCH"):
        AlignedEvaluation.model_validate(payload)


def test_metric_models_reject_inconsistent_counts(core_result):
    payload=core_result.model_dump()
    payload["individual"]["detectors"][0]["fn"]=5
    with pytest.raises((RegimeContractError,ValidationError)):
        metrics.CoreMetricsResult.model_validate(payload)


def test_cross_module_invariants_exhaustive_binary_patterns(contracts):
    for pattern in itertools.product((0,1),repeat=3):
        result=metrics.evaluate_core(case(contracts,[(1,tuple(1-v for v in pattern))]))
        assert result.common_mode.all_three_fn_count==int(all(pattern))
        for i,d in enumerate(result.individual.detectors):
            assert d.fn==pattern[i]
            assert result.recovery.detectors[i].unique_catch_count==int(not pattern[i] and all(pattern[j] for j in range(3) if j!=i))


def test_metric_apis_have_no_threshold_override_or_refitting():
    for function in (metrics.evaluate_core,metrics.individual_metrics,metrics.common_mode_metrics,metrics.failure_patterns,
                     metrics.recovery_metrics,metrics.evasion_transfer_metrics):
        assert tuple(inspect.signature(function).parameters)==("table",)
    source=Path(metrics.__file__).read_text()
    assert "threshold_selection" not in source and "select_threshold" not in source


def test_engine_imports_and_fixture_evaluation_do_not_execute_models():
    code='''
import sys
def audit(event,args):
    if event=="import" and args[0].split(".")[0] in ("torch","transformers","sklearn","sentence_transformers"):
        raise AssertionError("model import forbidden")
    if event=="open" and isinstance(args[0],(str,bytes)):
        name=str(args[0]).replace(chr(92),"/").lower()
        if "/dataset/raw/" in name or "normalized_records" in name or "r0_regime_manifest" in name or "predictions.csv" in name:
            raise AssertionError("real prompt/prediction access forbidden")
sys.addaudithook(audit)
from detection_service.research_protocol.adapters import FrozenDetectorContracts,DetectorAdapter
def forbidden(*a,**k): raise AssertionError("model execution forbidden")
DetectorAdapter.predict=forbidden
DetectorAdapter._load_live=forbidden
from detection_service.research_protocol.core_metrics_contract import synthetic_core,synthetic_r2,align_fixture
from detection_service.research_protocol.core_metrics import evaluate_core
c=FrozenDetectorContracts()
for bundle in (synthetic_core(c),synthetic_r2(c)[0]):
    evaluate_core(align_fixture(bundle,c))
print("PASS")
'''
    result=subprocess.run([sys.executable,"-c",code],capture_output=True,text=True)
    assert result.returncode==0,result.stderr


def test_frozen_core_contract_artifacts():
    if not (phase2.ROOT/contract.HASHES).exists():
        pytest.skip("Artifact freeze follows initial synthetic correctness tests")
    assert contract.check()["status"]=="PASS"
