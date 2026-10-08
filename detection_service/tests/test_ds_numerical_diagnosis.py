"""Model-free acceptance checks of journal-backed numerical diagnostics."""

import json
import pytest
from detection_service.research_protocol import ds_numerical_diagnosis as d


def test_ds_repeat_same_process_stability():
    v = d.read('ds_repeatability_first_seed')['same_process']
    assert all(s['count']==100 and s['distinct_binary64_values']==1 and s['maximum_delta']==0 for s in v.values())


def test_ds_repeat_cross_process_stability():
    v = d.read('ds_repeatability_first_seed')
    assert len(set(v['worker_pids'])) == 10
    assert all(s['count']==10 and s['distinct_binary64_values']==1 and s['maximum_delta']==0 for s in v['cross_process'].values())
    assert all(s['maximum_delta']==0 for s in v['combined'].values())


def test_ds_eval_mode_recorded():
    for name in ('ds_243_equivalence_recheck','ds_r1_diagnostic_replays'):
        trace = d.read(name)['model_mode_trace']
        assert trace and all(not r['training'] and not r['active_dropout'] and not r['grad_enabled'] and r['inference_mode'] for r in trace)


def test_ds_dtype_trace_complete():
    v = d.read('ds_dtype_device_trace')
    fields = ('input_tensors','reference_weights','logits','log_softmax','probability_tensor','token_surprisals',
        'whole_prompt_perplexity','sliding_window_perplexities','statistical_summaries','feature_vector',
        'lr_coefficients','lr_intercept','lr_decision_function','raw_probability','calibration_log_odds','calibration_output')
    assert all(v.get(k) is not None for k in fields)
    assert v['logits']['dtype']=='torch.float32' and v['feature_vector']=='float64'


def test_ds_device_trace_complete():
    v = d.read('ds_dtype_device_trace')
    assert v['input_tensors']['device']==v['reference_weights']['device']==v['logits']['device']=='cpu'
    assert v['cpu_comparison']=='NOT_APPLICABLE_ALREADY_CPU'


def test_ds_243_equivalence_recheck():
    v = d.read('ds_243_equivalence_recheck')
    assert len(v['rows'])==v['summary']['count']==243
    assert len({r['sample_id'] for r in v['rows']})==243
    assert v['authority']['calibration_rows']==233 and v['authority']['base_train_rows']==10
    assert v['summary']==d.summary(v['rows'])


def test_ds_diagnostic_queries_separated():
    v = d.read('ds_numerical_runtime_diagnosis')
    count = 0
    for receipt in v['journals']:
        path = d.p.ROOT/receipt['path']
        assert d.p.files.sha(path)==receipt['sha256']
        rows = [json.loads(line) for line in path.read_text().splitlines()]
        assert all(r['query_scope']=='CURRENT_DIAGNOSTIC' and r['query_role']=='BASELINE_REPLAY' and r['target_detector']=='D_S' for r in rows)
        assert len(rows)==receipt['queries']
        count += len(rows)
    assert count==v['diagnostic_queries']==243+100+10+d.read('ds_r1_diagnostic_replays')['summary']['count']


def test_ds_no_r2_generation_queries():
    assert d.read('ds_numerical_runtime_diagnosis')['integrity']['generation_queries']==0


def test_ds_no_dmb_queries():
    assert d.read('ds_numerical_runtime_diagnosis')['integrity']['dmb_queries']==0


def test_ds_no_dg_queries():
    assert d.read('ds_numerical_runtime_diagnosis')['integrity']['dg_queries']==0


def test_ds_no_ensemble_queries():
    assert d.read('ds_numerical_runtime_diagnosis')['integrity']['ensemble_queries']==0


def test_ds_no_threshold_change():
    assert d.integrity()['threshold']==.5585373573968287


def test_ds_no_tolerance_change():
    assert d.integrity()['tolerance']==1e-12


def test_ds_no_model_change():
    assert not d.integrity()['model_changes']


def test_ds_no_calibrator_change():
    assert not d.integrity()['calibrator_changes']


def test_ds_no_feature_schema_change():
    assert not d.integrity()['feature_schema_changes']


def test_metadata_selection_not_score_based():
    parents = [dict(parent_sample_id=str(i),source='A' if i<8 else 'B',input_tokens=i*300) for i in range(16)]
    expected = d.select_r1(parents)
    perturbed = [dict(r,baseline_calibrated_score=1/(i+1)) for i,r in enumerate(parents)]
    assert [r['parent_sample_id'] for r in expected]==[r['parent_sample_id'] for r in d.select_r1(perturbed)]
    assert len(expected)<=10 and expected[0]==parents[0]


def test_summary_counts_numerical_failures_separately_from_decisions():
    rows = [dict(raw_delta=1e-7,calibrated_delta=2e-7,native_mismatch=False,operational_mismatch=False)]
    result = d.summary(rows)
    assert result['raw']['above_tolerance']==1 and result['native_mismatches']==0


def test_same_logits_analysis_not_substituted():
    v = d.read('ds_feature_sensitivity')
    assert not v['detector_modified'] and v['reference_lm_queries']==0
    assert len(v['features'])==26
    assert v['same_logits_higher_precision']['normal_dtype']=='torch.float32'
    assert v['same_logits_higher_precision']['diagnostic_dtype']=='torch.float64'
