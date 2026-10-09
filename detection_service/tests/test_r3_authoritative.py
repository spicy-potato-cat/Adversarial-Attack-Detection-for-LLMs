"""Synthetic journal/search equivalence; never loads the authoritative stack."""
import json
import pytest

from detection_service.research_protocol import r3_generator as g, r3_preparation as d


class Oracle:
    evidence_kind = 'SYNTHETIC_FIXTURE'

    def __init__(self, detector, mode, parent):
        self.detector, self.mode, self.parent = detector, mode, parent

    def coverage_end(self, text):
        return len(text)

    def __call__(self, text):
        index = d.DOMAIN.index(self.detector)
        if self.mode == 'fail' and self.detector == 'D_M-B':
            return dict(status='UNAVAILABLE', raw_score=None)
        score = 0.99 if self.mode == 'constant' or text == self.parent else (
            0.0 if self.mode == 'success' else int(d.sha(text)[:8], 16) / (2**32 - 1))
        return dict(status='OK', **{d.FIELDS[index]: score})


@pytest.mark.parametrize('mode', ['constant', 'success', 'hash'])
@pytest.mark.parametrize('parent', ['ordinary testing content sample', 'word ' * 32, '!!!', 'Unicode \u03b1 testing example'])
def test_search_matches_frozen_preparation(tmp_path, mode, parent):
    oracles = {label: Oracle(label, mode, parent) for label in d.DOMAIN}
    expected = d.generate_synthetic(parent, oracles)
    journal = g.Journal(tmp_path / 'queries.jsonl')
    evaluator = g.CandidateEvaluator(oracles, journal, 'synthetic-parent')
    try:
        actual = g.generate(parent, evaluator)
    finally:
        journal.close()
    for key in ('text', 'script', 'scores', 'objective', 'success', 'mechanism',
                'candidate_evaluations', 'individual_detector_queries', 'detector_queries', 'logical_requests', 'trace'):
        assert actual[key] == expected[key]
    rows = [
        json.loads(line) for line in (tmp_path / 'queries.jsonl').read_bytes().splitlines()]
    assert sum(r['event'] == 'RESERVED' for r in rows) == actual['candidate_evaluations'] <= 61
    assert sum(r['event'] == 'ATTEMPTED' for r in rows) == sum(r['event'] == 'RETURNED' for r in rows) == actual['individual_detector_queries']
    assert actual['individual_detector_queries'] == 3 * actual['candidate_evaluations']
    assert g.inverse(actual['text'], actual['script']) == parent.encode('utf-8')
    from detection_service.research_protocol.r3_reconstruction import reconstruct
    proof = reconstruct(parent, actual, rows)
    assert proof['status'] == 'PASS' and proof['additional_model_calls'] == 0
    rows[0]['stage'] = 'CORRUPTED'
    with pytest.raises(ValueError, match='QUERY_ORDER'):
        reconstruct(parent, actual, rows)


def test_failure_charged_and_returned_before_abort(tmp_path):
    parent = 'ordinary testing content'
    journal = g.Journal(tmp_path / 'q.jsonl')
    evaluator = g.CandidateEvaluator({label: Oracle(label, 'fail', parent) for label in d.DOMAIN}, journal, 'parent')
    with pytest.raises(ValueError, match='NON_OK'):
        evaluator.query(parent, 'BASELINE')
    with pytest.raises(ValueError, match='ABORTED'):
        evaluator.query(parent, 'BASELINE')
    journal.close()
    rows = [json.loads(line) for line in (tmp_path / 'q.jsonl').read_bytes().splitlines()]
    assert evaluator.budget.candidate_evaluations == 1 and evaluator.budget.individual_queries == 2
    assert rows[-1]['event'] == 'RETURNED' and rows[-1]['prediction']['status'] == 'UNAVAILABLE'
    assert next(r for r in rows if r['event'] == 'RESERVED')['individual_slots'] == 3


def test_exact_cache_and_budget(tmp_path):
    parent = 'ordinary testing content'
    journal = g.Journal(tmp_path / 'q.jsonl')
    evaluator = g.CandidateEvaluator({label: Oracle(label, 'constant', parent) for label in d.DOMAIN}, journal, 'parent')
    for index in range(61):
        evaluator.query(parent + str(index), 'SALIENCY')
    evaluator.query(parent + '0', 'GREEDY')
    with pytest.raises(ValueError, match='BUDGET'):
        evaluator.query(parent + '61', 'GREEDY')
    journal.close()
    assert evaluator.budget.candidate_evaluations == 61 and evaluator.budget.individual_queries == 183


def test_no_journal_no_query():
    with pytest.raises(ValueError, match='JOURNAL'):
        g.CandidateEvaluator(dict.fromkeys(d.DOMAIN), None, 'parent')


def test_readonly_cache_byte_mutation_rejected(tmp_path):
    from detection_service.research_protocol import detector_semantics as files
    from detection_service.research_protocol.r3_readonly_cache import verified_reads
    path = tmp_path / 'metadata.json'
    path.write_text('{"x": 1}', encoding='ascii')
    original = files.read_json
    with pytest.raises(ValueError, match='BYTE_DRIFT'):
        with verified_reads():
            assert files.read_json(path) == {'x': 1}
            path.write_text('{"x": 2}', encoding='ascii')
    assert files.read_json is original


def test_readonly_cache_object_mutation_rejected(tmp_path):
    from detection_service.research_protocol import detector_semantics as files
    from detection_service.research_protocol.r3_readonly_cache import verified_reads
    path = tmp_path / 'metadata.json'
    path.write_text('{"x": 1}', encoding='ascii')
    with pytest.raises(ValueError, match='JSON_MUTATION'):
        with verified_reads():
            files.read_json(path)['x'] = 2


def test_readonly_cache_retains_validated_values(tmp_path):
    from detection_service.research_protocol import detector_semantics as files
    from detection_service.research_protocol.r3_readonly_cache import verified_reads
    path = tmp_path / 'metadata.json'
    path.write_text('{"x": 1}', encoding='ascii')
    digest = files.sha(path)
    with verified_reads():
        assert files.sha(path) == digest
        assert files.read_json(path) is files.read_json(path)
