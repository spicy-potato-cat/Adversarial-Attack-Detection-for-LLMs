"""Restart provenance and fail-closed baseline accounting without model calls."""

from types import SimpleNamespace
import json
from unittest.mock import patch
import pytest

from detection_service.research_protocol import r2_ds_authoritative_v2 as r
from detection_service.research_protocol.r2_ds_query_journal import QueryJournal


def receipt():
    return r.p.files.read_json(r.RECEIPT)


def test_r2_ds_restart_from_seed_one():
    v=receipt()
    assert v['restart_from_seed_one'] and v['first_seed_sample_id']==r.p.parents()[0]['parent_sample_id']
    assert v['expected_seeds']==698 and v['inherited_lineages']==94


def test_r2_ds_new_run_id():
    v=receipt()
    assert v['run_id']==r.RUN_ID and v['run_id']=='R2-DS-001-AUTHORITATIVE-V2-20261009'
    assert v['private_directory']!='detection_service/outputs/r2-ds-001'


def test_restart_receipt_preserves_prior_unknown_accounting():
    v=receipt()
    assert v['historical_failed_attempt']=='UNKNOWN_EXACT_COUNT_BOUNDED_1_TO_61'
    assert v['historical_diagnostic_queries']==dict(prior_repair=1,numerical_diagnosis=362,disposition_gate=1,total_known=364)
    assert v['prior_accepted_terminals']==0 and not any(v['prior_transfer_queries'].values())


def test_restart_scientific_design_and_code_unchanged():
    v=receipt()
    assert not any(v['changed'].values())
    assert v['bindings']==r.disposition.identities()
    assert v['generator_implementation_commit']==r.implementation_anchor()


def test_r2_ds_query_journal_durable(tmp_path):
    row=SimpleNamespace(raw_score=.9,calibrated_score=.8,status='OK',error_code=None,
        native_binary_prediction=1,input_tokens=10,tokens_analyzed=9,truncated=False)
    q=QueryJournal(tmp_path/'q.jsonl','test-v2','AUTHORITATIVE_GENERATION')
    with patch('detection_service.research_protocol.r2_ds_query_journal.os.fsync') as sync:
        q.score(SimpleNamespace(predict=lambda *a,**k:row),'fixed fixture','id','BASELINE_REPLAY')
        assert sync.call_count==2
    q.close()
    saved=json.loads(q.path.read_text())
    assert saved['query_sequence_number']==1 and saved['candidate_sha256']==r.sha('fixed fixture')


def test_r2_ds_baseline_logged_before_gate(tmp_path):
    q=QueryJournal(tmp_path/'q.jsonl','test-v2','AUTHORITATIVE_GENERATION')
    actual=SimpleNamespace(raw_score=.9,calibrated_score=.8,status='OK',error_code=None,
        native_binary_prediction=1,input_tokens=10,tokens_analyzed=9,truncated=False)
    oracle=r.TargetOracle.__new__(r.TargetOracle)
    oracle.journal=q
    oracle.adapter=SimpleNamespace(predict=lambda *a,**k:actual)
    oracle.seed_sample_id='id'
    oracle.frozen_baseline=dict(raw_score=.7,calibrated_score=.6,native_decision=1,operational_decision=1)
    with pytest.raises(ValueError,match='BASELINE_TARGET_REPLAY_MISMATCH'):
        oracle.query_with_role('fixed fixture','BASELINE_REPLAY')
    q.close()
    saved=json.loads(q.path.read_text())
    assert saved['calibrated_score']==.8 and q.sequence==1


def test_r2_ds_no_mutation_after_baseline_failure():
    calls=[]
    class Oracle:
        detector_id='ds_v2'
        def logical_query(self,text,role,cached):
            calls.append(role)
        def query_with_role(self,text,role):
            raise ValueError('BASELINE_TARGET_REPLAY_MISMATCH')
    with pytest.raises(ValueError,match='BASELINE_TARGET_REPLAY_MISMATCH'):
        r.generate('A fixed fixture with words',Oracle())
    assert calls==['BASELINE_REPLAY']


def test_r2_ds_isolation_rejects_non_target_construction():
    from detection_service.research_protocol.adapters import DetectorAdapter
    with r.target_isolation(),pytest.raises(ValueError,match='BLOCKED_R2_TARGET_ISOLATION'):
        DetectorAdapter('D_G',None)


def test_r2_ds_isolation_rejects_ensemble_import():
    with r.target_isolation(),pytest.raises(ValueError,match='BLOCKED_UNTARGETED_GENERATION_IMPORT'):
        __import__('detection_service.research_protocol.common_mode')


def test_r2_ds_restart_code_bound():
    assert receipt()['orchestration_code_sha256']==r.p.files.sha(r.p.ROOT/r.CODE)
