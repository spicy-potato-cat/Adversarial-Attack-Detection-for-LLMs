"""Reconstruct operator attempts from recorded feedback without model calls."""

from collections import Counter
from copy import deepcopy
import json
from unittest.mock import patch

from detection_service.research_protocol import r2_ds_generator as g
from detection_service.research_protocol import r2_ds_design as d
from detection_service.research_protocol import r2_ds_predeclare as p
from detection_service.research_protocol import r2_ds_authoritative_v2 as restart
from detection_service.research_protocol.r2_ds_completion_v2 import lines, ledger


def reconstruct(saved, receipts):
    parent = g.inverse(saved['text'], saved['script']).decode('utf-8')
    by_hash = {r['candidate_sha256']: r for r in receipts}
    attempts = []
    latest = {}
    global_index = 0
    original_render = g.render
    original_query = g.QueryCache.query

    class RecordedOracle:
        detector_id = d.DETECTOR_ID

        def coverage_end(self, text):
            p.require(text == parent, 'REPLAY_PARENT_CONFLICT')
            return saved['coverage_end']

        def __call__(self, text):
            row = by_hash[g.sha(text)]
            return {key: row[key] for key in
                    ('status', 'calibrated_score', 'input_tokens', 'tokens_analyzed', 'truncated')}

    def render(text, script):
        candidate = original_render(text, script)
        latest[candidate] = deepcopy(script)
        return candidate

    def query(cache, text, stage):
        nonlocal global_index
        cached = text in cache.cache
        if stage == 'GLOBAL':
            operator = 'GLOBAL_' + d.OPERATORS[global_index]
            global_index += 1
        elif stage == 'GREEDY':
            operator = latest[text]['edits'][-1]['operator']
        elif stage == 'PADDING':
            operator = 'BENIGN_CONTEXT_PADDING'
        elif stage == 'SALIENCY':
            operator = 'ALT_CASE'
        else:
            operator = 'BASELINE'
        result = original_query(cache, text, stage)
        attempts.append(dict(stage=stage, operator=operator, cached=cached,
                             score=result['calibrated_score']))
        return result

    with patch.object(g, 'render', render), patch.object(g.QueryCache, 'query', query):
        replay = g.generate(parent, RecordedOracle())
    for key in replay:
        p.require(json.loads(json.dumps(replay[key])) == saved[key], 'OPERATOR_RECONSTRUCTION_CONFLICT:' + key)
    return attempts


def run():
    accounting = ledger()
    receipts = lines(p.ROOT / accounting['journal']['path'])
    by_seed = {}
    for row in receipts:
        by_seed.setdefault(row['seed_sample_id'], []).append(row)
    entries = lines(restart.PRIVATE / 'generation_v2.jsonl')
    logical, unique, seeds, decreases, evasions = (Counter() for _ in range(5))
    stages = Counter()
    for entry in entries:
        saved = entry['private_generation']
        attempts = reconstruct(saved, by_seed[entry['metadata']['parent_sample_id']])
        seen = set()
        for row in attempts:
            op = row['operator']
            if op == 'BASELINE':
                continue
            logical[op] += 1
            unique[op] += int(not row['cached'])
            decreases[op] += int(row['score'] < saved['baseline']['calibrated_score'])
            evasions[op] += int(row['score'] < d.THRESHOLD)
            stages[row['stage']] += 1
            seen.add(op)
        seeds.update(seen)
    p.publish(p.OUT / 'r2_ds_operator_attempts_v2.json', dict(
        status='PASS', run_id=restart.RUN_ID, reconstructed_seeds=len(entries),
        new_model_queries=0, generation_journal_sha256=p.digest(restart.PRIVATE / 'generation_v2.jsonl'),
        definition='Logical attempts include cached candidates; unique calls exclude cache hits. '
                   'Score decrease and evasion counts describe attempted candidates, not independent trials. '
                   'Selection and transfer outcomes are in operator_analysis_v1.',
        stage_attempts=dict(stages), operators={op: dict(logical_attempts=logical[op],
            unique_model_calls=unique[op], seeds_attempting=seeds[op],
            attempts_decreasing_baseline_score=decreases[op], attempts_evading_target=evasions[op])
            for op in sorted(logical)}))


if __name__ == '__main__':
    run()
