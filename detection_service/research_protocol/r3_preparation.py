"""Preparation-only minimax search. No live detector imports or execution path."""
from copy import deepcopy
from dataclasses import dataclass
import hashlib
import json
import math
from typing import Protocol

from detection_service.research_protocol import r2_dmb_design as legacy
from detection_service.research_protocol.r2_dmb_generator import (
    edit, evenly_spaced, inverse, render, require, sha, word_spans,
)

DOMAIN = ('D_S', 'D_M-B', 'D_G')
THRESHOLDS = (0.5585373573968287, 0.0004967087297700347, 0.21291141211986545)
FIELDS = ('calibrated_probability', 'raw_score', 'raw_score')
OPERATORS = ('ALT_CASE', 'CONFUSABLE_FIRST', 'ZERO_WIDTH_INTERLEAVE', 'DOT_INTERLEAVE')
AUTHORITATIVE_QUERIES = {d: 0 for d in DOMAIN}

class SyntheticOracle(Protocol):
    evidence_kind: str
    detector: str
    def __call__(self, text: str) -> dict: ...
    def coverage_end(self, text: str) -> int: ...

def operational_margins(scores):
    require(set(scores) == set(DOMAIN), 'R3_EXACT_DOMAIN_REQUIRED')
    values = []
    for detector, threshold in zip(DOMAIN, THRESHOLDS):
        score = scores[detector]
        require(type(score) in (int, float) and math.isfinite(score) and 0 <= score <= 1,
                'R3_INVALID_SCORE')
        values.append(score / threshold - 1)
    return tuple(values)

def objective(scores):
    return max(operational_margins(scores))

def success(scores, *, reversible):
    return reversible and objective(scores) < 0

@dataclass
class QueryBudget:
    limit: int = 61
    candidate_evaluations: int = 0
    individual_queries: int = 0

    def reserve(self):
        require(self.candidate_evaluations < self.limit and
                self.individual_queries + 3 <= 3 * self.limit, 'R3_QUERY_BUDGET_EXCEEDED')
        self.candidate_evaluations += 1

class CandidateEvaluator:
    def __init__(self, oracles, *, limit=61):
        require(set(oracles) == set(DOMAIN), 'R3_EXACT_DOMAIN_REQUIRED')
        require(type(limit) is int and 1 <= limit <= 61, 'R3_INVALID_BUDGET')
        require(all(getattr(oracles[d], 'evidence_kind', None) == 'SYNTHETIC_FIXTURE' and
                    getattr(oracles[d], 'detector', None) == d for d in DOMAIN),
                'R3_PREPARATION_REJECTS_AUTHORITATIVE_ORACLE')
        self.oracles = dict(oracles)
        self.budget = QueryBudget(limit)
        self.detector_queries = dict.fromkeys(DOMAIN, 0)
        self.cache = {}
        self.trace = []
        self.logical_requests = 0
        self.failed = False

    def query(self, text, stage):
        require(not self.failed, 'R3_ABORTED_EVALUATOR')
        self.logical_requests += 1
        cached = text in self.cache
        if not cached:
            self.budget.reserve()
            scores = {}
            try:
                for detector, field in zip(DOMAIN, FIELDS):
                    self.budget.individual_queries += 1
                    self.detector_queries[detector] += 1
                    row = self.oracles[detector](text)
                    require(row.get('status') == 'OK', 'R3_NON_OK_ABORT')
                    scores[detector] = row[field]
                operational_margins(scores)
                self.cache[text] = scores
            except BaseException:
                self.failed = True
                raise
        result = self.cache[text]
        self.trace.append(dict(stage=stage, candidate_id=sha(text), cached=cached,
                               objective=objective(result)))
        return dict(result)

    def coverage_end(self, parent):
        ends = [self.oracles[d].coverage_end(parent) for d in DOMAIN]
        require(all(type(e) is int and 0 <= e <= len(parent) for e in ends), 'R3_INVALID_COVERAGE')
        return min(ends)

def generate_synthetic(parent, oracles):
    require(legacy.OPERATORS == OPERATORS, 'R3_FROZEN_REGISTRY_DRIFT')
    evaluator = CandidateEvaluator(oracles)
    baseline = evaluator.query(parent, 'BASELINE')
    require(objective(baseline) >= 0, 'R3_SEED_ALREADY_ALL_BENIGN')
    end = evaluator.coverage_end(parent)
    spans = word_spans(parent, end)
    probes = []
    for a, b in evenly_spaced(spans):
        scores = evaluator.query(parent[:a] + 'x' * (b-a) + parent[b:], 'SALIENCY')
        probes.append(((a,b), objective(baseline)-objective(scores)))
    ranked = sorted(probes, key=lambda r: (-r[1], r[0][0]))[:8]
    empty = dict(edits=[], prefix='', suffix='')
    current = (parent, empty, baseline, 'UNCHANGED')
    def variant(script, mechanism, stage):
        text = render(parent, script)
        require(inverse(text, script) == parent.encode('utf-8', errors='strict'), 'R3_INVALID_INVERSE')
        return text, script, evaluator.query(text, stage), mechanism
    def rank(row, priority):
        return objective(row[2]), priority, sha(row[0])
    for span, _ in ranked:
        variants = []
        seen = set()
        for priority, operator in enumerate(OPERATORS):
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
            if objective(best[2]) < objective(current[2]):
                current = best
        if objective(current[2]) < 0:
            break
    if objective(current[2]) >= 0:
        variants = []
        for side, paddings in enumerate((legacy.PREFIXES, legacy.SUFFIXES)):
            for index, padding in enumerate(paddings):
                script = deepcopy(current[1])
                script['prefix' if side == 0 else 'suffix'] = padding
                row = variant(script, 'BENIGN_CONTEXT_PADDING', 'PADDING')
                variants.append((row, side * 4 + index))
        best, _ = min(variants, key=lambda v: rank(*v))
        if objective(best[2]) < objective(current[2]):
            current = best
    if objective(current[2]) >= 0:
        variants = []
        for priority, operator in enumerate(OPERATORS):
            script = deepcopy(empty)
            script['edits'] = [e for e in (edit(parent,s,operator) for s in spans) if e is not None]
            variants.append((variant(script,'GLOBAL_'+operator,'GLOBAL'), priority))
        best, _ = min(variants, key=lambda v: rank(*v))
        if objective(best[2]) < objective(current[2]):
            current = best
    text, script, scores, mechanism = current
    require(inverse(text,script) == parent.encode('utf-8',errors='strict'), 'R3_INVALID_TERMINAL')
    return dict(text=text, script=script, scores=scores, objective=objective(scores),
        success=success(scores,reversible=True), mechanism=mechanism,
        evidence_kind='SYNTHETIC_FIXTURE', candidate_evaluations=evaluator.budget.candidate_evaluations,
        individual_detector_queries=evaluator.budget.individual_queries,
        detector_queries=evaluator.detector_queries, logical_requests=evaluator.logical_requests,
        trace=evaluator.trace, authoritative_queries=dict(AUTHORITATIVE_QUERIES))

def inherit_lineage(parent, child_id):
    require(bool(parent.get('lineage_id')), 'R3_LINEAGE_REQUIRED')
    keys = ('lineage_id','source','dataset_id','dataset_revision','attack_family')
    return dict({k: parent[k] for k in keys}, parent_sample_id=parent['sample_id'], sample_id=child_id)

def select_seeds(parents, decisions, limit=800):
    """Pure metadata selector. Caller supplies already frozen R1 metadata only."""
    require(type(limit) is int and 0 < limit <= 800, 'R3_INVALID_SEED_LIMIT')
    groups = {}
    seen = set()
    for p in parents:
        sid = p['sample_id']
        require(sid not in seen, 'R3_DUPLICATE_PARENT')
        seen.add(sid)
        require(p.get('threat_regime') == 'R1_SHIFTED_UNSEEN', 'R3_R1_PARENTS_ONLY')
        require(p.get('partition') not in ('FINAL_TEST','FROZEN_EXTERNAL','PROTECTED'), 'R3_PROTECTED_PARENT')
        if p['truth_label'] != 1 or not p.get('lineage_id'):
            continue
        row = decisions.get(sid, {})
        require(set(row) == set(DOMAIN), 'R3_COMPLETE_R1_DECISIONS_REQUIRED')
        require(all(v in ('ATTACK','BENIGN') for v in row.values()), 'R3_INVALID_R1_DECISION')
        if all(v == 'BENIGN' for v in row.values()):
            continue
        groups.setdefault(p['source'], []).append(dict(p))
    for rows in groups.values():
        rows.sort(key=lambda p: (sha('R3-ENSEMBLE-001|1701|'+p['sample_id']), p['sample_id']))
    chosen, lineages = [], set()
    while len(chosen) < limit and any(groups.values()):
        for source in sorted(groups):
            rows = groups[source]
            while rows and rows[0]['lineage_id'] in lineages:
                rows.pop(0)
            if rows and len(chosen) < limit:
                row = rows.pop(0)
                chosen.append(row)
                lineages.add(row['lineage_id'])
    return tuple(chosen)

def canonical_json(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('utf-8')

def serialize_synthetic_terminal(result, parent, child_id):
    require(result['evidence_kind'] == 'SYNTHETIC_FIXTURE', 'R3_PREPARATION_ONLY_SERIALIZER')
    require(inverse(result['text'],result['script']) == parent['text'].encode('utf-8'), 'R3_PARENT_MISMATCH')
    return canonical_json(dict(inherit_lineage(parent,child_id), **result))
