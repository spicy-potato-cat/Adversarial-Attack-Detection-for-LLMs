"""Model-free engineering checks; synthetic all-seed tests are not a live audit."""

from copy import deepcopy
import hashlib
import json
from types import SimpleNamespace

import pytest
from jsonschema import validate

from detection_service.research_protocol import r2_ds_predeclare as p,r2_ds_design as d,r2_ds_query_journal as journal
from detection_service.research_protocol import r2_ds_repair_evidence as repair,r2_ds_replay_diagnosis as diag
from detection_service.research_protocol.r2_ds_generate_run import TargetOracle


def row():
    return SimpleNamespace(raw_score=.9,calibrated_score=.8,status='OK',error_code=None,
        native_binary_prediction=1,input_tokens=20,tokens_analyzed=19,truncated=False)


class FakeAdapter:
    def predict(self,text,**kwargs):
        return row()


def test_r2_ds_query_logged_before_postquery_assertion(tmp_path):
    path=tmp_path/'queries.jsonl'
    log=journal.QueryJournal(path,'synthetic','CURRENT_DIAGNOSTIC')
    with pytest.raises(ValueError):
        log.score(FakeAdapter(),'synthetic text','seed-1','BASELINE_REPLAY')
        raise ValueError('later gate')
    assert len(path.read_bytes().splitlines())==1
    log.close()


def test_r2_ds_failed_gate_preserves_query_receipt(tmp_path):
    path=tmp_path/'queries.jsonl'
    log=journal.QueryJournal(path,'synthetic','AUTHORITATIVE_GENERATION')
    oracle=object.__new__(TargetOracle)
    oracle.journal=log
    oracle.adapter=FakeAdapter()
    oracle.seed_sample_id='seed-1'
    oracle.frozen_baseline=dict(raw_score=.91,calibrated_score=.81,native_decision=1,operational_decision=1)
    with pytest.raises(ValueError,match='BASELINE_TARGET_REPLAY_MISMATCH'):
        oracle.query_with_role('synthetic text','BASELINE_REPLAY')
    value=json.loads(path.read_bytes())
    assert value['raw_score']==.9 and value['calibrated_score']==.8
    assert value['query_sequence_number']==1
    log.close()


def test_r2_ds_baseline_replay_uses_exact_r1_parent_bytes():
    seed,text,stored=diag.first_seed()
    value=p.files.read_json(diag.OUT/'ds_baseline_replay_first_seed_v1.json')
    digest=hashlib.sha256(text.encode('utf-8')).hexdigest()
    assert digest==seed['parent_text_sha256']==value['input_sha256']==value['request_input_sha256']==value['engine_input_sha256']
    assert seed['parent_sample_id']==stored['sample_id']==value['sample_id']


def test_r2_ds_baseline_replay_uses_frozen_runtime_binding():
    from detection_service.research_protocol import ds_runtime
    value=p.files.read_json(diag.OUT/'ds_baseline_replay_first_seed_v1.json')
    assert value['runtime_binding_sha256']==p.digest(ds_runtime.BINDING)
    assert value['frozen_identity']==ds_runtime.accepted_ds_adapter()._identity


def synthetic_audit():
    return [dict(sample_id=str(i),raw_delta=0.,calibrated_delta=0.,native_match=True,operational_match=True) for i in range(698)]


def test_r2_ds_all_seed_replay_count_698():
    assert repair.summarize(synthetic_audit())['status']=='PASS'
    assert repair.summarize(synthetic_audit()[:-1])['status']=='FAIL'


def test_r2_ds_all_seed_replay_calibrated_delta_le_1e12():
    rows=synthetic_audit()
    rows[0]['calibrated_delta']=2e-12
    assert repair.summarize(rows)['status']=='FAIL'


def test_r2_ds_all_seed_native_decisions_exact():
    rows=synthetic_audit()
    rows[0]['native_match']=False
    assert repair.summarize(rows)['native_mismatches']==1 and repair.summarize(rows)['status']=='FAIL'


def test_r2_ds_all_seed_operational_decisions_exact():
    rows=synthetic_audit()
    rows[0]['operational_match']=False
    assert repair.summarize(rows)['operational_mismatches']==1 and repair.summarize(rows)['status']=='FAIL'


def test_r2_ds_historical_unknown_queries_not_reported_zero():
    assert repair.HISTORICAL_QUERIES=='UNKNOWN_EXACT_COUNT_BOUNDED_1_TO_61'
    assert p.files.read_json(diag.OUT/'ds_baseline_replay_first_seed_v1.json')['historical_failed_attempt_queries']==repair.HISTORICAL_QUERIES


def test_r2_ds_diagnostic_queries_separate_from_attack_budget():
    value=p.files.read_json(diag.OUT/'ds_baseline_replay_first_seed_v1.json')
    assert value['diagnostic_queries']==1 and value['authoritative_generation_queries']==0


def test_r2_ds_restart_from_seed_one():
    repair.restart_gate(repair.summarize(synthetic_audit()),'INPUT_IDENTITY_MISMATCH',['seed-1','seed-2'],'seed-1')


def test_r2_ds_prior_partial_run_not_resumed():
    with pytest.raises(ValueError,match='FULL_RESTART_FROM_SEED_ONE_REQUIRED'):
        repair.restart_gate(repair.summarize(synthetic_audit()),'INPUT_IDENTITY_MISMATCH',['seed-1','seed-2'],'seed-2')
    with pytest.raises(ValueError,match='STILL_UNRESOLVED'):
        repair.restart_gate(repair.summarize(synthetic_audit()),'UNKNOWN',['seed-1'],'seed-1')


def frozen_design():
    return p.files.read_json(p.OUT/'r2_ds_predeclaration_clarification_v1.json')['design']


def test_r2_ds_attack_design_unchanged():
    assert frozen_design()==d.DESIGN


def test_r2_ds_query_budget_unchanged():
    assert d.DESIGN['max_unique_model_queries_per_parent']==61==frozen_design()['max_unique_model_queries_per_parent']


def test_r2_ds_seed_manifest_unchanged():
    path=p.OUT/'r2_ds_seed_manifest_v1.json'
    assert path.read_bytes()==p.git('show','5f5e6f4:'+path.relative_to(p.ROOT).as_posix())


def test_r2_ds_threshold_unchanged():
    assert d.THRESHOLD==.5585373573968287==frozen_design()['target_threshold']
    assert repair.TOLERANCE==1e-12


def test_r2_ds_operator_registry_unchanged():
    assert list(d.OPERATORS)==frozen_design()['operators']
    assert list(d.PREFIXES)==frozen_design()['prefixes'] and list(d.SUFFIXES)==frozen_design()['suffixes']


def preserved(prefix):
    snapshot=p.files.read_json(p.OUT/'r2_ds_predeclaration_v1.json')['preservation_sha256']
    selected={key:value for key,value in snapshot.items() if key.startswith(prefix)}
    assert selected and all(p.digest(key)==value for key,value in selected.items())


def test_r0_preservation():
    preserved('artifacts/research_protocol/r0')


def test_r1_preservation():
    preserved('artifacts/research_protocol/r1')


def test_r2_dmb_preservation():
    preserved('artifacts/research_protocol/r2_dmb')


def test_protocol_patch_preservation():
    from detection_service.research_protocol import protocol_patch_001
    assert len(protocol_patch_001.verify_patch()['sha256'])==262


def test_durable_query_schema_and_no_raw_prompt(tmp_path):
    path=tmp_path/'queries.jsonl'
    log=journal.QueryJournal(path,'synthetic','CURRENT_DIAGNOSTIC')
    log.score(FakeAdapter(),'synthetic text','seed-1','BASELINE_REPLAY')
    value=json.loads(path.read_bytes())
    validate(value,p.files.read_json(diag.OUT/'ds_query_journal_schema_v1.json'))
    assert not any(key in value for key in ('text','prompt','original','replacement'))
    log.close()


def test_real_audit_not_claimed_from_synthetic_tests():
    assert p.files.read_json(diag.OUT/'ds_baseline_replay_all_seeds_v1.json')['status']=='NOT_RUN'
    assert p.files.read_json(diag.OUT/'ds_baseline_pipeline_comparison_v1.json')['primary_root_cause']=='UNKNOWN'


def test_logical_cache_hits_are_durable_without_extra_model_calls(tmp_path):
    from detection_service.research_protocol.r2_ds_generator import QueryCache
    path=tmp_path/'queries.jsonl'
    log=journal.QueryJournal(path,'synthetic','AUTHORITATIVE_GENERATION')
    oracle=object.__new__(TargetOracle)
    oracle.journal=log
    oracle.adapter=FakeAdapter()
    oracle.seed_sample_id='seed-1'
    oracle.frozen_baseline=dict(raw_score=.9,calibrated_score=.8,native_decision=1,operational_decision=1)
    cache=QueryCache(oracle)
    cache.query('synthetic text','BASELINE')
    cache.query('synthetic text','SALIENCY')
    assert log.sequence==1 and log.logical_queries==2
    assert len(path.read_bytes().splitlines())==1
    logical=[json.loads(line) for line in log.logical_path.read_bytes().splitlines()]
    assert [value['cached'] for value in logical]==[False,True]
    log.close()


def test_track_b_preservation():
    from detection_service.research_protocol.r2_ds_track_b_reference_v1 import verified
    receipt = verified()
    assert receipt['branch'] == 'prep/r3-verifier-001'
    assert receipt['original_task_reference'] == '0cd2d506380cbb3ec513207e4fa66ad422d2b3f2'
    assert receipt['approved_untouched_reference'] == '6c7173b70a10d1506d92360b421eaceb5e56405e'
    assert not receipt['track_b_modified_by_this_task']
    assert not receipt['scientific_protocol_changed']
    assert p.git('branch', '--show-current').decode().strip() == 'exp/r2-ds-001'
    before = p.files.read_json(p.ROOT / 'reviews/evidence/r2_ds_acceptance_context/before_v1.json')
    assert p.git('reflog', 'show', '--format=%H %gs', receipt['branch']).decode() == before['track_b_reflog']
    assert all(p.digest(name) == expected for name, expected in before['sha256'].items())
