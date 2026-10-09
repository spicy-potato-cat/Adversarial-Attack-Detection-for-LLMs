"""Synthetic descriptive accounting tests; no data or model inference."""
from types import SimpleNamespace

from detection_service.research_protocol.r3_analysis import describe, transitions, IDS


def test_empty_operator_stratum_is_undefined():
    row = describe([], {})
    assert row['parent_count'] == row['all_three_successes'] == 0
    assert row['target_success_rate'] is None and row['candidate_evaluations_per_success'] is None


def test_all_patterns_and_efficiency():
    rows = [dict(sample_id=str(index), candidate_evaluations=index+1, mechanism='SYNTHETIC') for index in range(8)]
    decisions = {str(index): tuple(int(bit) for bit in f'{index:03b}') for index in range(8)}
    summary = describe(rows, decisions)
    assert summary['parent_count'] == 8 and summary['all_three_successes'] == 1
    assert summary['target_success_rate'] == 1/8 and summary['candidate_evaluations'] == 36
    assert summary['detector_calls'] == 108 and summary['FN'] == dict.fromkeys(IDS, 4)
    assert summary['failure_patterns'] == dict.fromkeys((f'{index:03b}' for index in range(8)), 1)


def test_transitions_separate_inherited_and_induced_misses():
    rows = [dict(sample_id='c' + str(index), parent_sample_id='p' + str(index)) for index in range(4)]
    decisions = {'c0': (1,1,1), 'c1': (0,0,0), 'c2': (1,1,1), 'c3': (0,0,0)}
    original = {(row['parent_sample_id'], label): SimpleNamespace(operational_binary_prediction=int(index < 2))
        for index, row in enumerate(rows) for label in IDS}
    result = transitions(rows, decisions, original)
    assert all(value == dict(catch_to_catch=1, catch_to_miss=1, miss_to_catch=1, miss_to_miss=1) for value in result.values())
