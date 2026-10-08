"""Authoritative post-run ledger, provenance and transfer evidence checks."""

import pytest

from detection_service.research_protocol import r2_ds_predeclare as p
from detection_service.research_protocol import r2_ds_completion_v2 as c
from detection_service.research_protocol import r2_ds_authoritative_v2 as restart


@pytest.fixture(scope='module')
def accounting():
    return c.ledger()


def test_r2_ds_baseline_replay_every_seed(accounting):
    assert accounting['baseline_replays'] == len(accounting['rows']) == 698
    assert accounting['baseline_replay_violations'] == 0
    assert accounting['max_raw_delta'] <= 1e-12
    assert accounting['max_calibrated_delta'] <= 1e-12


def test_r2_ds_query_budget(accounting):
    assert accounting['max_queries_per_seed'] <= 61
    assert accounting['unique_model_queries'] <= accounting['logical_queries']
    assert all(row['queries'] <= 61 for row in accounting['rows'])


@pytest.mark.parametrize('detector', ['D_M_B', 'D_G', 'ensemble'])
def test_r2_ds_no_forbidden_generation_calls(accounting, detector):
    assert accounting['forbidden_generation_queries'][detector] == 0


def test_new_private_raw_text_not_committed():
    assert not p.git('ls-files', '--', restart.PRIVATE.relative_to(p.ROOT).as_posix()).strip()


def test_r2_ds_dmb_dg_queries_only_after_freeze():
    predictions = p.files.read_json(p.OUT / 'r2_ds_prediction_manifest_v1.json')
    freeze_commit = p.committed(p.OUT / 'r2_ds_freeze_acceptance_v1.json')
    assert predictions['freeze_commit'] == freeze_commit
    assert p.git('merge-base', '--is-ancestor', freeze_commit, predictions['scoring_code_commit']) == b''
    assert p.git('show', freeze_commit + ':artifacts/research_protocol/r2_ds/r2_ds_terminal_manifest_v1.json') == (p.OUT / 'r2_ds_terminal_manifest_v1.json').read_bytes()


def test_r2_ds_ds_terminal_replay():
    predictions = p.files.read_json(p.OUT / 'r2_ds_prediction_manifest_v1.json')
    assert predictions['ds_max_calibrated_score_delta'] <= 1e-12
    assert predictions['ds_operational_mismatches'] == 0
    assert predictions['final_replay_query_journal']['queries'] == 698
    path = p.ROOT / predictions['final_replay_query_journal']['path']
    assert p.files.sha(path) == predictions['final_replay_query_journal']['sha256']
    assert all(row['query_role'] == 'REPLAY_VALIDATION' for row in c.lines(path))


def test_track_b_untouched():
    receipt = p.files.read_json(p.OUT / 'r2_ds_track_b_reference_update_v1.json')
    assert receipt['original_task_reference'] == '0cd2d506380cbb3ec513207e4fa66ad422d2b3f2'
    assert receipt['commander_authorization'] == 'Accept the updated Track-B reference; finish Track A'
    assert p.git('rev-parse', 'prep/r3-verifier-001').decode().strip() == receipt['approved_untouched_reference']
    assert not receipt['track_b_modified_by_this_task'] and not receipt['track_b_merged_by_this_task']


def test_recorded_feedback_reconstruction_complete():
    evidence = p.files.read_json(p.OUT / 'r2_ds_operator_attempts_v2.json')
    assert evidence['status'] == 'PASS'
    assert evidence['reconstructed_seeds'] == 698
    assert evidence['new_model_queries'] == 0
    assert p.files.sha(restart.PRIVATE / 'generation_v2.jsonl') == evidence['generation_journal_sha256']
