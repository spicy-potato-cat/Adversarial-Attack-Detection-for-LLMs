"""Post-score acceptance; no fitting, detector calls or threshold selection."""

from collections import Counter
import json

import pytest

from detection_service.research_protocol import r1_corpus as c, r1_scoring as scoring, r1_analysis as analysis, protocol_lock
from detection_service.research_protocol.core_metrics import evaluate_core
from detection_service.research_protocol.cross_regime import RegimeResultBundle, compatibility
from detection_service.research_protocol.operating_policy import native_prediction
from detection_service.research_protocol.r0_operational import verified_policy, THRESHOLDS, IDS
from detection_service.research_protocol.uncertainty import bootstrap_metrics


@pytest.fixture(scope='module')
def scored():
    policy=verified_policy()
    manifest=scoring.input_manifest()
    records=scoring.read_predictions(policy)
    table=analysis.aligned(manifest,records,policy)
    return manifest,records,table


def read(name):
    return c.files.read_json(c.OUT/(name+'_v1.json'))


@pytest.fixture(scope='module')
def result():
    return RegimeResultBundle.model_validate_json((c.OUT/'r1_result_bundle_v1.json').read_bytes())


def test_r1_membership_frozen_before_scoring():
    meta=read('r1_prediction_manifest')
    assert scoring.gate_b_anchor()==meta['gate_b_commit']
    assert read('r1_gate_b_acceptance')['model_predictions']==0
    assert meta['manifest_sha256']==c.files.sha(c.OUT/'r1_dataset_manifest_v1.json')
    assert protocol_lock.git('merge-base','--is-ancestor',meta['gate_b_commit'],'HEAD')==b''


def test_r1_all_predictions_present(scored):
    manifest,records,table=scored
    assert len(records)==3*manifest.sample_count==5400
    assert table.coverage.status=='COMPLETE'
    assert not table.coverage.missing_predictions


def test_r1_three_detectors_per_sample(scored):
    _,records,_=scored
    counts=Counter(r.sample_id for r in records)
    assert len(counts)==1800 and set(counts.values())=={3}
    assert len({(r.sample_id,r.detector_id) for r in records})==5400
    assert set(r.detector_id for r in records)=={'ds_v2','dm_b_v1','dg_v1'}


def test_r1_no_non_ok_predictions(scored):
    _,records,table=scored
    assert all(r.status=='OK' for r in records)
    assert table.coverage.non_ok_predictions==0
    assert all(native_prediction(r).operational_binary_prediction is None for r in records)


def test_r1_operational_thresholds_exact(scored):
    _,records,_=scored
    points=dict(zip(('ds_v2','dm_b_v1','dg_v1'),zip(THRESHOLDS,IDS)))
    for row in records:
        threshold,identity=points[row.detector_id]
        assert (row.operational_threshold,row.operational_threshold_id)==(threshold,identity)
        score=row.calibrated_score if row.detector_id=='ds_v2' else row.raw_score
        assert row.operational_binary_prediction==int(score>=threshold)


def test_r1_csv_roundtrip(scored):
    _,records,_=scored
    assert (c.OUT/'r1_predictions_v1.csv').read_bytes()==scoring.prediction_csv_bytes(records)
    assert c.files.sha(c.OUT/'r1_predictions_v1.csv')==read('r1_prediction_manifest')['prediction_artifact_sha256']


def test_r1_scoring_no_adaptation():
    value=read('r1_prediction_manifest')
    assert not any(value[k] for k in ('detector_changes','model_training','calibration_changes','threshold_changes'))
    assert value['preflight']['status']=='PASS'


def test_r1_individual_metrics(scored,result):
    _,records,table=scored
    assert evaluate_core(table)==result.core_metrics
    for detector in result.core_metrics.individual.detectors:
        selected=[r for r in records if r.detector_id==detector.detector_id]
        assert detector.tp==sum(r.truth_label==1 and r.operational_binary_prediction==1 for r in selected)
        assert detector.fn==800-detector.tp
        assert detector.fp==sum(r.truth_label==0 and r.operational_binary_prediction==1 for r in selected)
        assert detector.tn==1000-detector.fp


def test_r1_common_mode(scored,result):
    attacks=[r for r in scored[2].rows if r.truth_label]
    for (i,j),pair in zip(((0,1),(0,2),(1,2)),result.core_metrics.common_mode.pairs):
        expected=sum(r.decisions[i]==r.decisions[j]==0 for r in attacks)
        assert pair.shared_fn_count==expected and pair.jfn.value==expected/800
        assert pair.ejf.value==pair.jfn.value-pair.independence_reference.value
    assert result.core_metrics.common_mode.all_three_fn_count==sum(r.decisions==(0,0,0) for r in attacks)


def test_r1_failure_patterns(scored,result):
    counts=Counter(''.join(str(1-d) for d in r.decisions) for r in scored[2].rows if r.truth_label)
    assert {p.pattern_id:p.count for p in result.core_metrics.failure_patterns.patterns}=={f'{i:03b}':counts[f'{i:03b}'] for i in range(8)}
    assert sum(counts.values())==800


def test_r1_unique_catches(result):
    counts={p.pattern_id:p.count for p in result.core_metrics.failure_patterns.patterns}
    for row in result.core_metrics.recovery.detectors:
        assert row.unique_catch_count==counts[row.unique_catch_pattern]
        assert row.unique_catch_rate.value==row.unique_catch_count/800


def test_r1_recovery(result):
    shared=result.core_metrics.common_mode.all_three_fn_count
    for row in result.core_metrics.recovery.detectors:
        assert row.both_others_miss_count==row.unique_catch_count+shared
        assert row.conditional_recovery.value==(row.unique_catch_count/row.both_others_miss_count if row.both_others_miss_count else None)


def test_r1_bootstrap_unit_valid(result):
    assert read('r1_source_selection')['rules']['bootstrap_unit']=='LINEAGE_CLUSTERED'
    assert len(result.uncertainty)==2
    for value in result.uncertainty:
        assert value.config.unit=='LINEAGE_CLUSTERED' and value.config.replicates==1000 and value.config.seed==1701
        assert value.config.confidence_level==0.95


def test_r1_uncertainty_deterministic(scored,result):
    for old in result.uncertainty:
        current=bootstrap_metrics(scored[2],tuple(v.metric_id for v in old.intervals),old.config)
        assert current==old


def test_r1_frontier_does_not_modify_operational_policy():
    value=read('r1_descriptive_frontier')
    assert not value['operational_policy_changed']
    assert c.files.sha(c.ROOT/'artifacts/research_protocol/operating_point_manifest_v1.json')=='06fa4548a62ae0e0968f9d93339910f8841a0f366b5346b0892a2be6904fb0cc'
    for row in value['detectors'].values():
        assert row['view']=='descriptive_frontier_v1'
        for point in row['points']:
            assert point['fpr']<=point['budget'] and point['role']=='R1_SECONDARY_DESCRIPTIVE_ONLY_NOT_OPERATIONAL'


def test_r1_ranking_metrics(scored):
    from sklearn.metrics import roc_auc_score,average_precision_score
    stored=read('r1_ranking_metrics')['detectors']
    for detector in stored:
        values=[r for r in scored[1] if r.detector_id==detector]
        labels=[r.truth_label for r in values]
        scores=[r.raw_score for r in values]
        assert abs(stored[detector]['roc_auc']-roc_auc_score(labels,scores))<1e-12
        assert abs(stored[detector]['average_precision']-average_precision_score(labels,scores))<1e-12


def test_r1_cross_regime_policy_compatible(result):
    reference,_=analysis.r0_reference()
    assert not compatibility(reference,result)
    assert read('r0_r1_comparison')['paired'] is False


def test_r1_r0_delta_direction():
    for row in read('r0_r1_comparison')['metrics'].values():
        if row['status']=='OBSERVED':
            assert row['delta_fraction']==row['current']-row['reference']
            assert row['delta_percentage_points']==100*row['delta_fraction']


def test_r1_result_bundle_valid(result):
    assert result.population_count==1800 and result.attack_count==800 and result.benign_count==1000
    assert result.comparison_view_id=='OPERATIONAL_FIXED_V1'
    assert result.lineage_count==1097 and result.unknown_lineage_rows==0
    assert RegimeResultBundle.model_validate_json(result.model_dump_json())==result


def test_r1_source_conditioned_analysis(scored):
    rows=read('r1_family_analysis')['groups']
    assert set(rows)=={'LLMAIL_INJECT','INJECAGENT_BASE'}
    assert rows['INJECAGENT_BASE']['lineage_count']==1
    assert rows['LLMAIL_INJECT']['lineage_count']==96
    for source,value in rows.items():
        assert value['sample_count']==400
        for detector in value['core_metrics']['individual']['detectors']:
            assert detector['tp']+detector['fn']==400


def test_r1_result_artifact_hashes():
    value=read('r1_analysis_provenance')
    for path,expected in value['sha256'].items():
        assert c.files.sha(c.ROOT/path)==expected
    assert not value['post_R1_adaptation'] and not value['model_training']
    assert not value['R2_started'] and not value['R3_started']


def test_r1_prediction_canonical_metadata(scored):
    for record in scored[1]:
        assert record.metadata.evidence_kind=='LIVE_FROZEN_MODEL'
        assert record.input_tokens>=record.tokens_analyzed>=0
        assert record.latency_ms>=0
        assert not record.metadata.unlabeled_inference
