"""Exact accepted R0 history, with OOF identity and RNG provenance preserved."""

from collections import Counter
from copy import deepcopy
import json
import subprocess
import sys

import pytest

from detection_service.research_protocol import detector_semantics as files
from detection_service.research_protocol import r0_reproduction as r0
from detection_service.research_protocol.core_metrics_contract import align_fixture
from detection_service.research_protocol.adapters import FrozenDetectorContracts
from detection_service.research_protocol.historical_uncertainty import historical_lineage_plan, replay_historical_uncertainty
from detection_service.research_protocol.regime import RegimeContractError
from detection_service.research_protocol.uncertainty import BootstrapConfig
from detection_service.research_protocol.uncertainty_contract import fixtures


@pytest.fixture(scope="module")
def history():
    return r0.load_history()


@pytest.fixture(scope="module")
def decisions(history):
    return r0.historical_decisions(history)


@pytest.fixture(scope="module")
def results(history,decisions):
    return r0.reproduce(history,decisions)


def test_r0_population(history):
    m=history["manifest"]
    assert (m.sample_count,m.attack_count,m.benign_count)==(1135,183,952)
    assert len({s.sample_id for s in m.samples})==1135


def test_r0_manifest_hash(history):
    assert files.sha(history["root"]/r0.MEMBERSHIP)==r0.MEMBERSHIP_SHA


def test_r0_fold_hash(history):
    assert files.sha(history["root"]/r0.FOLDS)==r0.FOLD_SHA


def test_r0_unique_sample_ids(history):
    assert all(len(rows)==len({r["sample_id"] for r in rows})==1135 for rows in history["detectors"].values())


@pytest.mark.parametrize("detector,kind",[("ds_v2","OOF"),("dm_b_v1","OOF"),("dg_v1","FROZEN_DIRECT_DEVELOPMENT")])
def test_r0_detector_provenance(history,detector,kind):
    assert history["import_manifest"]["historical_models"][detector]["evidence_kind"]==kind


def test_r0_semantic_run_commit_not_rewritten(history):
    assert history["import_manifest"]["historical_models"]["dm_b_v1"]["run_code_commit"]=="5096d078b599c43ddd4e32b4fbfcaedcc83e4646"
    assert history["import_manifest"]["pre_R0_machinery_commit"]==r0.PRE_R0_COMMIT


def test_r0_raw_score_semantics(history):
    models=history["import_manifest"]["historical_models"]
    assert models["ds_v2"]["score_semantics"]=="UNCALIBRATED_CLASS1_PROBABILITY"
    assert "SOFTMAX" in models["dm_b_v1"]["score_semantics"]
    assert models["dg_v1"]["score_semantics"]=="MAX_CHUNK_MALICIOUS_CLASS_SOFTMAX"


COUNTS={"1PCT":((60,123,9,943),(177,6,7,945),(34,149,6,946)),
        "3PCT":((100,83,28,924),(179,4,22,930),(42,141,17,935)),
        "5PCT":((115,68,46,906),(181,2,34,918),(49,134,44,908))}


@pytest.mark.parametrize("budget,index",[(b,i) for b in COUNTS for i in range(3)])
def test_r0_confusion_exact(results,budget,index):
    d=results["results"][budget].individual.detectors[index]
    assert (d.tp,d.fn,d.fp,d.tn)==COUNTS[budget][index]


@pytest.mark.parametrize("index,shared,jaccard",[(0,3,3/84),(1,61,61/163),(2,4,4/141)])
def test_r0_pairwise_3pct(results,index,shared,jaccard):
    pair=results["results"]["3PCT"].common_mode.pairs[index]
    assert pair.shared_fn_count==shared and pair.jfn.value==shared/183 and pair.fn_jaccard.value==jaccard
    assert pair.independence_reference.value==pair.left_fnr.value*pair.right_fnr.value
    assert pair.ejf.value==pair.jfn.value-pair.independence_reference.value


@pytest.mark.parametrize("budget,count",[("1PCT",5),("3PCT",3),("5PCT",2)])
def test_r0_all_three_exact(results,budget,count):
    assert results["results"][budget].common_mode.all_three_fn_count==count


def test_r0_failure_patterns_exact(results):
    assert [p.count for p in results["results"]["3PCT"].failure_patterns.patterns]==[20,79,0,1,22,58,0,3]


def test_r0_unique_catches_exact(results):
    assert [d.unique_catch_count for d in results["results"]["3PCT"].recovery.detectors]==[1,58,0]


def test_r0_conditional_recovery_exact(results):
    assert [(d.conditional_recovery.numerator,d.conditional_recovery.denominator) for d in results["results"]["3PCT"].recovery.detectors]==[(1,4),(58,61),(0,3)]


@pytest.mark.parametrize("detector,auc,ap",[("ds_v2",.896760,.731587),("dm_b_v1",.996349,.987704),("dg_v1",.814954,.500652)])
def test_r0_ranking_metrics(results,detector,auc,ap):
    ranking=results["ranking"][detector]
    assert abs(ranking["roc_auc"]-auc)<=1e-6 and abs(ranking["average_precision"]-ap)<=1e-6
    assert ranking["pr_metric_definition"]=="AVERAGE_PRECISION_WHOLE_TIED_BLOCKS"


def test_r0_historical_descriptive_decision_import(decisions):
    assert len(decisions)==10215
    assert len({(r["budget_id"],r["sample_id"],r["detector_id"]) for r in decisions})==10215
    assert {r["budget_id"] for r in decisions}=={"1PCT","3PCT","5PCT"}
    assert not {"prompt","text","input_text"}&decisions[0].keys()


def test_r0_operational_thresholds_not_used(results):
    for table in results["tables"].values():
        p=table.provenance
        assert p.decision_view=="EXPLICIT" and p.operating_policy_sha is None and p.operational_thresholds is None


@pytest.mark.parametrize("change",["provenance","decision","score","hash","lineage"])
def test_r0_corrupted_historical_import_rejected(history,decisions,change):
    rows=deepcopy(decisions)
    field,value={"provenance":("explicit_decision_provenance_id","wrong"),"decision":("explicit_binary_decision",1-rows[0]["explicit_binary_decision"]),
        "score":("score",.12345),"hash":("source_artifact_sha","0"*64),"lineage":("lineage_id","wrong")}[change]
    rows[0][field]=value
    with pytest.raises(RegimeContractError):
        r0.align_history(history,rows,"1PCT")


def test_r0_duplicate_and_missing_decisions_rejected(history,decisions):
    for rows in (decisions[1:],decisions+[decisions[0]]):
        with pytest.raises(RegimeContractError):
            r0.align_history(history,rows,"1PCT")


def test_r0_bundle_future_regimes_not_run(results):
    assert results["matrix"]["regime_status"]=={"R0":"OBSERVED","R1":"NOT_RUN","R2-D_S":"NOT_RUN","R2-D_M-B":"NOT_RUN","R2-D_G":"NOT_RUN","R3":"NOT_RUN"}


def test_r0_historical_uncertainty_exact(results):
    uncertainty=results["historical_uncertainty"]["3PCT"]
    expected={"pair/dm_b_v1/dg_v1/jfn":(.00546448087431694,.04371584699453552),
        "pair/ds_v2/dg_v1/jfn":(.2677595628415301,.40437158469945356),"all_three/jfn":(0.,.03825136612021858)}
    for interval in uncertainty["intervals"]:
        assert (interval["ci_lower"],interval["ci_upper"])==pytest.approx(expected[interval["metric_id"]],abs=1e-12)
    assert uncertainty["plan"]["lineage_units"]==183 and uncertainty["plan"]["rng"]=="python.random.Random/MT19937"
    assert uncertainty["compliance"]=="HISTORICAL_RNG_REPLAY_NOT_PRODUCTION_PCG64"


def test_r0_production_rng_not_relabelled_as_historical(results):
    production=results["production_uncertainty"]
    assert production.config.seed==1701 and production.config.replicates==1000
    assert production.plan_sha!=results["historical_uncertainty"]["3PCT"]["plan"]["plan_sha"]


def test_r0_reproduction_serialization_deterministic(history,decisions,results):
    second=r0.reproduce(history,decisions,include_uncertainty=False)
    for budget,result in second["results"].items():
        assert result.deterministic_bytes()==results["results"][budget].deterministic_bytes()
    assert r0.csv_bytes(decisions)==r0.csv_bytes(r0.historical_decisions(history))


def test_descriptive_frontier_reproduces_stored_thresholds(results):
    assert [p["threshold"] for p in results["frontier"]["ds_v2"]]==[.9334402237345568,.8501334532357456,.784023369186312]


def test_legacy_rng_synthetic_lineages_and_old_engine_agree():
    contracts=FrozenDetectorContracts()
    table=align_fixture(fixtures(contracts)["lineage"],contracts)
    config=BootstrapConfig(unit="LINEAGE_CLUSTERED",domain="ATTACK_ONLY",replicates=40)
    draws,plan=historical_lineage_plan(table,config)
    for draw in draws:
        count=Counter(draw)
        for lineage in {r.lineage_id for r in table.rows if r.truth_label}:
            assert len({count[i] for i,r in enumerate(table.rows) if r.lineage_id==lineage})==1
    from detection_service.analysis.common_mode import bootstrap
    attacks=[r for r in table.rows if r.truth_label]
    misses={k:[r.decisions[i]==0 for r in attacks] for i,k in enumerate(("S","M","G"))}
    old=bootstrap(misses,[r.lineage_id for r in attacks],stacks={"all":["S","M","G"]},repetitions=40)
    replay=replay_historical_uncertainty(table,["all_three/jfn"],config=config)
    interval=replay["intervals"][0]
    reference=old["intervals"]["all_detector_jfn/all"]
    assert [interval["point_estimate"],interval["ci_lower"],interval["ci_upper"]]==[reference["estimate"],reference["lower"],reference["upper"]]
    assert historical_lineage_plan(table,config)[1]==plan


def test_r0_model_free_no_raw_payload_access():
    code='''
import sys
def audit(event,args):
    if event=="import" and args[0].split(".")[0] in ("torch","transformers","sklearn","sentence_transformers"):
        raise AssertionError("model/runtime import forbidden")
    if event=="open" and isinstance(args[0],(str,bytes)):
        name=str(args[0]).replace(chr(92),"/").lower()
        if "/dataset/raw/" in name or "normalized_records" in name:
            raise AssertionError("raw prompt access forbidden")
sys.addaudithook(audit)
from detection_service.research_protocol.adapters import DetectorAdapter
def forbidden(*a,**k): raise AssertionError("model execution forbidden")
DetectorAdapter.predict=forbidden
DetectorAdapter._load_live=forbidden
from detection_service.research_protocol.r0_reproduction import load_history,historical_decisions,reproduce
h=load_history()
reproduce(h,historical_decisions(h),include_uncertainty=False)
print("PASS")
'''
    result=subprocess.run([sys.executable,"-c",code],capture_output=True,text=True)
    assert result.returncode==0,result.stderr
