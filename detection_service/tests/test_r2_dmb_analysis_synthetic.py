"""Pre-run synthetic checks for derived ratios and unchanged bootstrap rules."""

from copy import deepcopy

import numpy as np
import pytest

from detection_service.research_protocol import r2_dmb_analysis as a
from detection_service.research_protocol.adapters import FrozenDetectorContracts
from detection_service.research_protocol.core_metrics_contract import synthetic_r2,align_fixture
from detection_service.research_protocol.alignment import bind_predictions
from detection_service.research_protocol.regime import create_manifest
from detection_service.research_protocol.uncertainty import BootstrapConfig,make_plan


@pytest.fixture(scope='module')
def targeted():
    contracts=FrozenDetectorContracts()
    bundle=deepcopy(synthetic_r2(contracts)[0])
    payload=bundle['manifest']
    payload['samples']=[s for s in payload['samples'] if s['target_detector']=='D_M-B' and s['valid_attack_attempt'] and s['truth_label']==1]
    ids={s['sample_id'] for s in payload['samples']}
    parent_ids={s['parent_sample_id'] for s in payload['samples']}
    payload['external_parents']=[r for r in payload['external_parents'] if r['sample_id'] in parent_ids]
    for k in ('sample_count','attack_count','benign_count','manifest_hash','experiment_id'):
        payload.pop(k)
    value=create_manifest(**payload)
    bundle['manifest']=value.model_dump(mode='json')
    bundle['prediction_binding']=bind_predictions(value).model_dump(mode='json')
    for k in ('predictions','explicit_decisions'):
        bundle[k]=[r for r in bundle[k] if r['sample_id'] in ids]
    return contracts,bundle


def test_r2_dmb_joint_transfer_synthetic(targeted):
    table=align_fixture(targeted[1],targeted[0])
    result=a.joint_transfer_interval(table)
    n=sum(r.decisions[1]==0 for r in table.rows)
    numerator=sum(r.decisions==(0,0,0) for r in table.rows)
    assert result['interval']['point_estimate']==(numerator/n if n else None)


def test_r2_dmb_joint_bootstrap_uses_frozen_plan(targeted):
    table=align_fixture(targeted[1],targeted[0])
    result=a.joint_transfer_interval(table)
    config=BootstrapConfig(unit='LINEAGE_CLUSTERED',domain='VALID_TARGET_ATTEMPTS',target_detector='D_M-B')
    plan=make_plan(table,config)
    assert result['plan_sha']==plan.plan_sha
    values=[]
    for indexes in plan.resamples:
        n=sum(table.rows[i].decisions[1]==0 for i in indexes)
        if n:
            values.append(sum(table.rows[i].decisions==(0,0,0) for i in indexes)/n)
    interval=result['interval']
    assert interval['replicates_valid']==len(values)
    if interval['status']=='ESTIMATED':
        assert [interval['ci_lower'],interval['ci_upper']]==list(np.quantile(values,[.025,.975],method=config.quantile_method))


def test_r2_dmb_undefined_etr_when_no_success(targeted):
    bundle=deepcopy(targeted[1])
    for row in bundle['explicit_decisions']:
        if row['detector_id']=='dm_b_v1':
            row['decision']=1
    result=a.joint_transfer_interval(align_fixture(bundle,targeted[0]))
    interval=result['interval']
    assert interval['point_estimate'] is interval['ci_lower'] is interval['ci_upper'] is None
    assert interval['status']=='OBSERVED_UNDEFINED' and interval['replicates_invalid']==1000


def test_r2_dmb_uncertainty_deterministic_synthetic(targeted):
    table=align_fixture(targeted[1],targeted[0])
    assert a.joint_transfer_interval(table)==a.joint_transfer_interval(table)


def test_r2_dmb_lineage_bootstrap_synthetic(targeted):
    table=align_fixture(targeted[1],targeted[0])
    config=BootstrapConfig(unit='LINEAGE_CLUSTERED',domain='VALID_TARGET_ATTEMPTS',target_detector='D_M-B')
    plan=make_plan(table,config)
    for draw in plan.resamples:
        from collections import Counter
        counts=Counter(draw)
        for lineage in {r.lineage_id for r in table.rows}:
            assert len({counts[i] for i,r in enumerate(table.rows) if r.lineage_id==lineage})==1


def test_r2_dmb_empty_operator_stratum():
    result=a.describe([],{})
    assert result['target_evasion_rate']['value'] is None
    assert result['etr_ds']['value'] is result['etr_dg']['value'] is result['joint_transfer']['value'] is None


def test_r2_dmb_success_subset_patterns():
    rows=[dict(sample_id='fixture-1',target_evasion_success=True,baseline_raw_score=.8,terminal_raw_score=.0001,unique_model_queries=5)]
    result=a.describe(rows,{'fixture-1':(0,0,0)})
    assert result['successful_evasion_patterns']['111']==1
    assert result['joint_transfer']['value']==result['etr_ds']['value']==result['etr_dg']['value']==1.
