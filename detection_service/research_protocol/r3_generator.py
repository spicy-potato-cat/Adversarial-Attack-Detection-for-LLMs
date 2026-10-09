"""Authoritative-capable minimax search; frozen prep remains synthetic-only."""
from copy import deepcopy
import os

from detection_service.research_protocol import r3_preparation as d
from detection_service.research_protocol.r2_dmb_generator import edit, evenly_spaced, inverse, render, require, sha, word_spans


class Journal:
    def __init__(self, path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.stream = path.open('xb')
        self.sequence = 0

    def write(self, event, **fields):
        self.sequence += 1
        row = dict(sequence=self.sequence, event=event, **fields)
        self.stream.write(d.canonical_json(row) + b'\n')
        self.stream.flush()
        os.fsync(self.stream.fileno())

    def close(self):
        self.stream.close()


class CandidateEvaluator:
    def __init__(self, oracles, journal, parent_id):
        require(set(oracles) == set(d.DOMAIN), 'R3_EXACT_DOMAIN_REQUIRED')
        require(journal is not None and bool(parent_id), 'DURABLE_JOURNAL_AND_PARENT_REQUIRED')
        self.oracles, self.journal, self.parent_id = dict(oracles), journal, parent_id
        self.budget = d.QueryBudget()
        self.detector_queries = dict.fromkeys(d.DOMAIN, 0)
        self.cache, self.trace = {}, []
        self.logical_requests, self.failed = 0, False

    def query(self, text, stage):
        require(not self.failed, 'R3_ABORTED_EVALUATOR')
        self.logical_requests += 1
        cached = text in self.cache
        key = dict(parent_sample_id=self.parent_id, stage=stage, candidate_id=sha(text))
        try:
            self.journal.write('LOGICAL', **key, cached=cached)
            if not cached:
                self.budget.reserve()
                self.journal.write('RESERVED', **key, candidate_evaluation=self.budget.candidate_evaluations,
                                   individual_slots=3)
                scores = {}
                for detector, field in zip(d.DOMAIN, d.FIELDS):
                    self.journal.write('ATTEMPTED', **key, detector=detector)
                    self.budget.individual_queries += 1
                    self.detector_queries[detector] += 1
                    row = self.oracles[detector](text)
                    self.journal.write('RETURNED', **key, detector=detector, prediction=row)
                    require(row.get('status') == 'OK', 'R3_NON_OK_ABORT')
                    scores[detector] = row[field]
                d.operational_margins(scores)
                self.cache[text] = scores
                self.journal.write('EVALUATED', **key, scores=scores, objective=d.objective(scores))
            result = self.cache[text]
            self.trace.append(dict(stage=stage, candidate_id=sha(text), cached=cached, objective=d.objective(result)))
            return dict(result)
        except BaseException:
            self.failed = True
            raise

    def coverage_end(self, parent):
        ends = [self.oracles[label].coverage_end(parent) for label in d.DOMAIN]
        require(all(type(end) is int and 0 <= end <= len(parent) for end in ends), 'R3_INVALID_COVERAGE')
        return min(ends)


def generate(parent, evaluator):
    """Exact frozen preparation algorithm with an explicit durable evaluator."""
    require(d.legacy.OPERATORS == d.OPERATORS, 'R3_FROZEN_REGISTRY_DRIFT')
    baseline = evaluator.query(parent, 'BASELINE')
    require(d.objective(baseline) >= 0, 'R3_SEED_ALREADY_ALL_BENIGN')
    end = evaluator.coverage_end(parent)
    spans = word_spans(parent, end)
    probes = []
    for a, b in evenly_spaced(spans):
        scores = evaluator.query(parent[:a] + 'x' * (b-a) + parent[b:], 'SALIENCY')
        probes.append(((a,b), d.objective(baseline)-d.objective(scores)))
    ranked = sorted(probes, key=lambda r: (-r[1], r[0][0]))[:8]
    empty = dict(edits=[], prefix='', suffix='')
    current = (parent, empty, baseline, 'UNCHANGED')

    def variant(script, mechanism, stage):
        text = render(parent, script)
        require(inverse(text, script) == parent.encode('utf-8', errors='strict'), 'R3_INVALID_INVERSE')
        return text, script, evaluator.query(text, stage), mechanism

    def rank(row, priority):
        return d.objective(row[2]), priority, sha(row[0])

    for span, _ in ranked:
        variants, seen = [], set()
        for priority, operator in enumerate(d.OPERATORS):
            change = edit(parent, span, operator)
            if change is None:
                continue
            script = deepcopy(current[1])
            script['edits'].append(change)
            text = render(parent, script)
            if text in seen:
                continue
            seen.add(text)
            variants.append((variant(script, operator, 'GREEDY'), priority))
        if variants:
            best, _ = min(variants, key=lambda v: rank(*v))
            if d.objective(best[2]) < d.objective(current[2]):
                current = best
        if d.objective(current[2]) < 0:
            break
    if d.objective(current[2]) >= 0:
        variants = []
        for side, paddings in enumerate((d.legacy.PREFIXES, d.legacy.SUFFIXES)):
            for index, padding in enumerate(paddings):
                script = deepcopy(current[1])
                script['prefix' if side == 0 else 'suffix'] = padding
                row = variant(script, 'BENIGN_CONTEXT_PADDING', 'PADDING')
                variants.append((row, side * 4 + index))
        best, _ = min(variants, key=lambda v: rank(*v))
        if d.objective(best[2]) < d.objective(current[2]):
            current = best
    if d.objective(current[2]) >= 0:
        variants = []
        for priority, operator in enumerate(d.OPERATORS):
            script = deepcopy(empty)
            script['edits'] = [e for e in (edit(parent,s,operator) for s in spans) if e is not None]
            variants.append((variant(script,'GLOBAL_'+operator,'GLOBAL'), priority))
        best, _ = min(variants, key=lambda v: rank(*v))
        if d.objective(best[2]) < d.objective(current[2]):
            current = best
    text, script, scores, mechanism = current
    require(inverse(text,script) == parent.encode('utf-8',errors='strict'), 'R3_INVALID_TERMINAL')
    return dict(text=text, script=script, scores=scores, baseline_scores=baseline, objective=d.objective(scores),
        success=d.success(scores,reversible=True), mechanism=mechanism,
        evidence_kind='LIVE_FROZEN_MODEL', candidate_evaluations=evaluator.budget.candidate_evaluations,
        individual_detector_queries=evaluator.budget.individual_queries, detector_queries=evaluator.detector_queries,
        logical_requests=evaluator.logical_requests, trace=evaluator.trace, coverage_end=end,
        eligible_spans=len(spans), saliency_spans=len(probes), ranked_spans=len(ranked))
