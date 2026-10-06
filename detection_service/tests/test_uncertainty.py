"""Synthetic resampling correctness and denial tests; no detector inference."""

from collections import Counter
from copy import deepcopy
import json

import numpy as np
from pydantic import ValidationError
import pytest

from detection_service.research_protocol.adapters import FrozenDetectorContracts
from detection_service.research_protocol.alignment import AlignedEvaluation, digest
from detection_service.research_protocol.core_metrics import evaluate_core, _Accounting
from detection_service.research_protocol.core_metrics_contract import align_fixture
from detection_service.research_protocol.regime import RegimeContractError
from detection_service.research_protocol.uncertainty import (
    BootstrapConfig, Interval, ResamplingPlan, UncertaintyResult, _weighted_values, bootstrap_metrics, domain_indices, make_plan,
)
from detection_service.research_protocol.uncertainty_contract import fixtures


@pytest.fixture(scope="module")
def tables():
    contracts = FrozenDetectorContracts()
    return {k:align_fixture(v,contracts) for k,v in fixtures(contracts).items()}


def cfg(**updates):
    return BootstrapConfig(**{**dict(unit="SAMPLE_PAIRED",domain="ATTACK_ONLY",replicates=40),**updates})


@pytest.fixture(scope="module")
def full_sample(tables):
    names = ("all_three/jfn","pair/ds_v2/dm_b_v1/jfn","pair/ds_v2/dm_b_v1/ejf","pair/ds_v2/dm_b_v1/fn_jaccard",
             "recovery/ds_v2/unique_catch_rate","recovery/ds_v2/conditional_recovery")
    return bootstrap_metrics(tables["sample"],names,cfg(replicates=1000))


def test_bootstrap_defaults():
    c = BootstrapConfig(unit="SAMPLE_PAIRED",domain="ATTACK_ONLY")
    assert (c.seed,c.replicates,c.confidence_level,c.method,c.quantile_method)==(1701,1000,.95,"PERCENTILE_BOOTSTRAP_V1","linear")


def test_seed_1701():
    assert cfg().seed==1701


def test_replicates_1000_default():
    assert BootstrapConfig(unit="LINEAGE_CLUSTERED",domain="ATTACK_ONLY").replicates==1000


def test_percentile_ci_method(tables):
    table,c = tables["sample"],cfg()
    plan = make_plan(table,c)
    values = [_weighted_values(_Accounting(table),table,indices)["all_three/jfn"] for indices in plan.resamples]
    interval = bootstrap_metrics(table,["all_three/jfn"],c,plan=plan).intervals[0]
    assert [interval.ci_lower,interval.ci_upper]==list(np.quantile(values,[.025,.975],method="linear"))


def test_sample_paired_keeps_detector_rows_together(tables):
    table = tables["sample"]
    for indices in make_plan(table,cfg()).resamples:
        value = _weighted_values(_Accounting(table),table,indices)["pair/ds_v2/dm_b_v1/jfn"]
        assert value==sum(table.rows[i].decisions[:2]==(0,0) for i in indices)/len(indices)


def test_lineage_cluster_keeps_descendants_together(tables):
    table = tables["lineage"]
    for draw in make_plan(table,cfg(unit="LINEAGE_CLUSTERED")).resamples:
        count = Counter(draw)
        for lineage in {r.lineage_id for r in table.rows if r.truth_label}:
            assert len({count[i] for i,r in enumerate(table.rows) if r.lineage_id==lineage})==1


def test_lineage_selected_twice_preserves_cluster(tables):
    table = tables["lineage"]
    plan = make_plan(table,cfg(unit="LINEAGE_CLUSTERED"))
    assert any(max(Counter(draw).values())>=2 for draw in plan.resamples)
    assert len({r.sample_id for r in table.rows})==len(table.rows)


@pytest.mark.parametrize("domain,label",[("ATTACK_ONLY",1),("BENIGN_ONLY",0)])
def test_label_domains(tables,domain,label):
    table = tables["sample"]
    assert all(table.rows[i].truth_label==label for draw in make_plan(table,cfg(domain=domain)).resamples for i in draw)


def test_attack_only_domain(tables):
    assert len(domain_indices(tables["sample"],cfg()))==8


def test_benign_only_domain(tables):
    assert len(domain_indices(tables["sample"],cfg(domain="BENIGN_ONLY")))==2


def test_stratified_label_domain(tables):
    table = tables["sample"]
    for indices in make_plan(table,cfg(domain="STRATIFIED_LABEL")).resamples:
        assert Counter(table.rows[i].truth_label for i in indices)=={1:8,0:2}
    result = bootstrap_metrics(table,["individual/ds_v2/accuracy"],cfg(domain="STRATIFIED_LABEL"))
    assert result.intervals[0].point_estimate==.5


def test_valid_target_attempt_domain(tables):
    table = tables["r2"]
    c = cfg(unit="LINEAGE_CLUSTERED",domain="VALID_TARGET_ATTEMPTS",target_detector="D_S")
    indices = domain_indices(table,c)
    assert len(indices)==100
    assert all(table.rows[i].truth_label and table.rows[i].valid_attack_attempt and table.rows[i].target_detector=="D_S" for i in indices)


def test_point_estimate_not_bootstrap_mean(tables):
    table,c = tables["sample"],cfg(replicates=1,seed=1702)
    result = bootstrap_metrics(table,["all_three/jfn"],c)
    values = _weighted_values(_Accounting(table),table,make_plan(table,c).resamples[0])
    assert result.intervals[0].point_estimate==evaluate_core(table).common_mode.all_three_jfn.value==.125
    assert values["all_three/jfn"]!=.125


def test_same_seed_is_deterministic(tables):
    a = bootstrap_metrics(tables["sample"],["all_three/jfn"],cfg())
    b = bootstrap_metrics(tables["sample"],["all_three/jfn"],cfg())
    assert a.deterministic_bytes()==b.deterministic_bytes()


def test_different_seed_can_change_resample(tables):
    assert make_plan(tables["sample"],cfg()).resamples != make_plan(tables["sample"],cfg(seed=1702)).resamples


def test_invalid_replicate_not_zero(full_sample):
    interval = next(i for i in full_sample.intervals if i.metric_id.endswith("conditional_recovery"))
    assert interval.replicates_invalid>0 and interval.replicates_valid+interval.replicates_invalid==1000


def test_unstable_denominator_policy(full_sample):
    interval = next(i for i in full_sample.intervals if i.metric_id.endswith("conditional_recovery"))
    assert interval.replicates_valid<950 and interval.status=="UNSTABLE_DENOMINATOR" and interval.ci_lower is None


@pytest.mark.parametrize("suffix,point",[("pair/ds_v2/dm_b_v1/jfn",.25),("pair/ds_v2/dm_b_v1/fn_jaccard",1/3),
    ("all_three/jfn",.125),("recovery/ds_v2/unique_catch_rate",.125),("recovery/ds_v2/conditional_recovery",.5)])
def test_core_bootstrap_metrics(full_sample,suffix,point):
    assert next(i for i in full_sample.intervals if i.metric_id==suffix).point_estimate==point


def test_ejf_bootstrap_allows_negative(full_sample):
    interval = next(i for i in full_sample.intervals if i.metric_id.endswith("/ejf"))
    assert interval.ci_lower<0<interval.ci_upper and interval.point_estimate==0


@pytest.mark.parametrize("name,point",[("target/ds_v2/evasion",.4),("transfer/ds_v2/dm_b_v1/etr",.25)])
def test_target_evasion_and_etr_bootstrap(tables,name,point):
    result = bootstrap_metrics(tables["r2"],[name],cfg(unit="LINEAGE_CLUSTERED",domain="VALID_TARGET_ATTEMPTS",target_detector="D_S"))
    assert result.intervals[0].point_estimate==point


def test_paired_delta_uses_shared_resample(tables):
    current,reference,c = tables["paired_candidate"],tables["sample"],cfg()
    plan = make_plan(current,c)
    expected = [_weighted_values(_Accounting(current),current,i)["all_three/jfn"]-_weighted_values(_Accounting(reference),reference,i)["all_three/jfn"] for i in plan.resamples]
    result = bootstrap_metrics(current,["all_three/jfn"],c,paired_reference=reference,plan=plan)
    interval = result.intervals[0]
    assert interval.point_estimate==-.125 and [interval.ci_lower,interval.ci_upper]==list(np.quantile(expected,[.025,.975],method="linear"))


def test_bootstrap_serialization_deterministic(full_sample):
    assert UncertaintyResult.model_validate_json(full_sample.deterministic_bytes())==full_sample


def test_observed_undefined(tables):
    result = bootstrap_metrics(tables["r2"],["transfer/ds_v2/dm_b_v1/etr"],cfg(unit="LINEAGE_CLUSTERED",domain="VALID_TARGET_ATTEMPTS",target_detector="D_S"))
    assert result.intervals[0].status=="ESTIMATED"
    with pytest.raises((RegimeContractError,ValidationError)):
        Interval(metric_id="undefined",point_estimate=None,ci_lower=0.,ci_upper=0.,replicates_requested=1,replicates_valid=0,replicates_invalid=1,status="OBSERVED_UNDEFINED")


def test_generated_shared_lineage_cannot_sample_rows(tables):
    with pytest.raises(RegimeContractError,match="REQUIRE_LINEAGE"):
        make_plan(tables["r2"],cfg(domain="VALID_TARGET_ATTEMPTS",target_detector="D_S"))


def test_forged_plan_cannot_split_lineage(tables):
    table,c = tables["lineage"],cfg(unit="LINEAGE_CLUSTERED")
    payload = make_plan(table,c).model_dump()
    first = list(payload["resamples"][0])
    first[0] = next(i for i in payload["domain_indices"] if table.rows[i].lineage_id!=table.rows[first[0]].lineage_id)
    payload["resamples"] = (tuple(first),)+payload["resamples"][1:]
    payload.pop("plan_sha")
    plan = ResamplingPlan(**payload,plan_sha=digest(payload))
    with pytest.raises(RegimeContractError):
        bootstrap_metrics(table,["all_three/jfn"],c,plan=plan)


@pytest.mark.parametrize("changes",[{"replicates":0},{"seed":True},{"quantile_method":"nearest"},{"confidence_level":.9}])
def test_invalid_configs(changes):
    with pytest.raises(ValidationError):
        cfg(**changes)


def test_wrong_metric_domain(tables):
    with pytest.raises(RegimeContractError):
        bootstrap_metrics(tables["sample"],["individual/ds_v2/fpr"],cfg())


def test_95_percent_support_boundary():
    for valid,status in ((949,"UNSTABLE_DENOMINATOR"),(950,"ESTIMATED")):
        interval=Interval(metric_id="rate",point_estimate=.5,ci_lower=.1 if valid==950 else None,ci_upper=.9 if valid==950 else None,
            replicates_requested=1000,replicates_valid=valid,replicates_invalid=1000-valid,status=status)
        assert interval.status==status


def changed_table(table, *, decisions=None, lineage=None):
    payload=table.model_dump(mode="json")
    for row in payload["rows"]:
        if decisions is not None:
            row["decisions"]=list(decisions)
        if lineage is not None:
            row["lineage_id"]=lineage
    payload.pop("alignment_sha")
    payload["alignment_sha"]=digest(payload)
    return AlignedEvaluation.model_validate_json(json.dumps(payload))


def test_undefined_observed_point_has_null_ci(tables):
    table=changed_table(tables["sample"],decisions=(1,1,1))
    result=bootstrap_metrics(table,["recovery/ds_v2/conditional_recovery","pair/ds_v2/dm_b_v1/fn_jaccard"],cfg())
    assert all(i.point_estimate is None and i.status=="OBSERVED_UNDEFINED" and i.replicates_invalid==40 and i.ci_lower is None for i in result.intervals)


def test_zero_target_evasion_etr_has_null_ci(tables):
    table=changed_table(tables["r2"],decisions=(1,1,1))
    result=bootstrap_metrics(table,["transfer/ds_v2/dm_b_v1/etr"],cfg(unit="LINEAGE_CLUSTERED",domain="VALID_TARGET_ATTEMPTS",target_detector="D_S"))
    assert result.intervals[0].status=="OBSERVED_UNDEFINED" and result.intervals[0].replicates_invalid==40


def test_stratification_does_not_split_mixed_label_lineage(tables):
    table=changed_table(tables["sample"],lineage="same-cluster")
    with pytest.raises(RegimeContractError,match="MIXED_LABEL"):
        make_plan(table,cfg(unit="LINEAGE_CLUSTERED",domain="STRATIFIED_LABEL"))


def test_paired_population_mismatch_rejected(tables):
    reference=changed_table(tables["sample"],lineage="other-lineage")
    with pytest.raises(RegimeContractError,match="CORRESPONDENCE"):
        bootstrap_metrics(tables["sample"],["all_three/jfn"],cfg(),paired_reference=reference)


def test_nonfinite_interval_rejected():
    with pytest.raises(ValidationError):
        Interval(metric_id="invalid",point_estimate=float("nan"),ci_lower=0.,ci_upper=1.,replicates_requested=1,replicates_valid=1,replicates_invalid=0,status="ESTIMATED")
