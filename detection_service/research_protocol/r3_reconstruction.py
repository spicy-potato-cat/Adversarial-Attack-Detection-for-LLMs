"""Model-free reconstruction from already recorded generation responses."""
from detection_service.research_protocol import r3_generator as g, r3_preparation as d
from detection_service.research_protocol.regime import require


class RecordedEvaluator:
    def __init__(self, events, coverage_end):
        self.expected = [r for r in events if r['event'] == 'LOGICAL']
        self.scores = {r['candidate_id']: r['scores'] for r in events if r['event'] == 'EVALUATED'}
        self.end = coverage_end
        self.logical_requests = 0
        self.cache, self.trace = {}, []
        self.budget = d.QueryBudget()
        self.detector_queries = dict.fromkeys(d.DOMAIN, 0)

    def coverage_end(self, parent):
        require(type(self.end) is int and 0 <= self.end <= len(parent), 'R3_RECORDED_COVERAGE_INVALID')
        return self.end

    def query(self, text, stage):
        require(self.logical_requests < len(self.expected), 'R3_RECONSTRUCTION_EXTRA_REQUEST')
        expected = self.expected[self.logical_requests]
        self.logical_requests += 1
        key, cached = d.sha(text), text in self.cache
        require((key, stage, cached) == (expected['candidate_id'], expected['stage'], expected['cached']),
                'R3_RECONSTRUCTION_QUERY_ORDER_CONFLICT')
        if not cached:
            self.budget.reserve()
            require(key in self.scores, 'R3_RECONSTRUCTION_MISSING_RESPONSE')
            self.cache[text] = self.scores[key]
            self.budget.individual_queries += 3
            for label in d.DOMAIN:
                self.detector_queries[label] += 1
        scores = self.cache[text]
        self.trace.append(dict(stage=stage, candidate_id=key, cached=cached, objective=d.objective(scores)))
        return dict(scores)


def reconstruct(parent, saved, events):
    evaluator = RecordedEvaluator(events, saved['coverage_end'])
    result = g.generate(parent, evaluator)
    require(evaluator.logical_requests == len(evaluator.expected), 'R3_RECONSTRUCTION_UNCONSUMED_REQUESTS')
    for key in ('text', 'script', 'scores', 'baseline_scores', 'objective', 'success', 'mechanism',
                'candidate_evaluations', 'individual_detector_queries', 'detector_queries', 'logical_requests',
                'trace', 'coverage_end', 'eligible_spans', 'saliency_spans', 'ranked_spans'):
        require(result[key] == saved[key], 'R3_RECONSTRUCTION_TERMINAL_CONFLICT:' + key)
    # No native prediction is executed or relabeled; only the comparison receipt is published.
    return dict(status='PASS', evidence_kind='READ_ONLY_REPLAY_OF_RECORDED_GENERATION',
        additional_model_calls=0, logical_requests_reconstructed=evaluator.logical_requests)
