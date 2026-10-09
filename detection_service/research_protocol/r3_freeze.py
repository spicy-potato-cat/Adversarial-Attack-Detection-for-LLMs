"""Read-only terminal acceptance and canonical R3 population publication."""
from collections import Counter, defaultdict
import json

from detection_service.research_protocol import r3_inputs as i, r3_preparation as d
from detection_service.research_protocol.r3_generator import inverse
from detection_service.research_protocol.regime import create_manifest, require

TERMINALS = i.OUT / 'r3_terminal_manifest_v1.json'
REGIME = i.OUT / 'r3_regime_manifest_v1.json'


def private_rows():
    return [json.loads(line) for line in (i.PRIVATE / 'generation_v1.jsonl').read_bytes().splitlines()]


def validate():
    i.gate()
    parents, texts = i.frozen_parents(), i.private_texts()
    private = private_rows()
    require(len(private) == len(parents), 'R3_INCOMPLETE_TERMINAL_POPULATION')
    rows = [entry['metadata'] for entry in private]
    require([r['parent_sample_id'] for r in rows] == [r['sample_id'] for r in parents], 'R3_PARENT_ORDER_DRIFT')
    require(len({r['sample_id'] for r in rows}) == len(parents), 'R3_DUPLICATE_TERMINAL')
    journal_path = i.PRIVATE / 'generation_queries_v1.jsonl'
    journal = [json.loads(line) for line in journal_path.read_bytes().splitlines()]
    require([r['sequence'] for r in journal] == list(range(1, len(journal) + 1)), 'R3_JOURNAL_SEQUENCE_BROKEN')
    grouped = defaultdict(list)
    for entry in journal:
        require(entry['parent_sample_id'] in texts, 'R3_UNKNOWN_JOURNAL_PARENT')
        grouped[entry['parent_sample_id']].append(entry)
    candidate_total, call_total, logical_total = 0, 0, 0
    for row, entry, parent in zip(rows, private, parents):
        result = entry['private_generation']
        original = texts[parent['sample_id']]
        require(inverse(result['text'], result['script']) == original.encode('utf-8'), 'R3_RECONSTRUCTION_FAILURE')
        require(d.sha(result['text']) == row['terminal_text_sha256'] and d.sha(original) == row['parent_text_sha256'], 'R3_TEXT_HASH_DRIFT')
        require(all(row[k] == parent[k] for k in ('source', 'lineage_id', 'dataset_id', 'dataset_revision', 'attack_family')), 'R3_LINEAGE_OR_SOURCE_DRIFT')
        require(result['scores'] == row['terminal_scores'] and result['baseline_scores'] == row['baseline_scores'] and
            row['objective'] == d.objective(result['scores']) and row['success'] == (row['objective'] < 0), 'R3_OUTCOME_CONFLICT')
        require(row['terminal_decisions'] == {label: int(result['scores'][label] >= threshold)
            for label, threshold in zip(d.DOMAIN, d.THRESHOLDS)}, 'R3_DECISION_CONFLICT')
        events = grouped[parent['sample_id']]
        logical = [r for r in events if r['event'] == 'LOGICAL']
        reservations = [r for r in events if r['event'] == 'RESERVED']
        attempted = [r for r in events if r['event'] == 'ATTEMPTED']
        returned = [r for r in events if r['event'] == 'RETURNED']
        evaluated = [r for r in events if r['event'] == 'EVALUATED']
        terminal = [r for r in events if r['event'] == 'TERMINAL']
        require(len(terminal) == 1 and terminal[0]['metadata'] == row, 'R3_TERMINAL_JOURNAL_CONFLICT')
        require(1 <= len(reservations) <= 61 and len(reservations) == len(evaluated) == row['candidate_evaluations'], 'R3_CANDIDATE_BUDGET_VIOLATION')
        require(len(attempted) == len(returned) == 3 * len(reservations) == row['detector_calls'] <= 183, 'R3_DETECTOR_BUDGET_VIOLATION')
        require(len(logical) == row['logical_requests'] == len(result['trace']), 'R3_LOGICAL_JOURNAL_CONFLICT')
        require([r['candidate_id'] for r in logical] == [r['candidate_id'] for r in result['trace']] and
            [r['cached'] for r in logical] == [r['cached'] for r in result['trace']], 'R3_TRACE_CONFLICT')
        keys = [(r['candidate_id'], r['detector']) for r in attempted]
        require(keys == [(r['candidate_id'], r['detector']) for r in returned] and len(set(keys)) == len(keys), 'R3_QUERY_PAIRING_CONFLICT')
        for reservation, evaluation in zip(reservations, evaluated):
            calls = [r for r in returned if r['candidate_id'] == reservation['candidate_id']]
            attempts = [r for r in attempted if r['candidate_id'] == reservation['candidate_id']]
            require(reservation['individual_slots'] == 3 and [r['detector'] for r in calls] == list(d.DOMAIN), 'R3_ALL_DOMAIN_CONFLICT')
            require(reservation['sequence'] < min(r['sequence'] for r in attempts) and
                all(a['sequence'] < b['sequence'] for a, b in zip(attempts, calls)) and
                max(r['sequence'] for r in calls) < evaluation['sequence'], 'R3_JOURNAL_ORDER_CONFLICT')
            require(all(r['prediction']['status'] == 'OK' for r in calls), 'R3_NON_OK_JOURNAL')
            scores = {r['detector']: r['prediction'][field] for r, field in zip(calls, d.FIELDS)}
            require(scores == evaluation['scores'] and d.objective(scores) == evaluation['objective'], 'R3_EVALUATION_JOURNAL_CONFLICT')
        require(any(r['candidate_id'] == row['terminal_text_sha256'] and r['scores'] == row['terminal_scores'] for r in evaluated), 'R3_TERMINAL_NOT_EVALUATED')
        require(all(e['operator'] in d.OPERATORS for e in result['script']['edits']) and
            result['script']['prefix'] in ('', *d.legacy.PREFIXES) and result['script']['suffix'] in ('', *d.legacy.SUFFIXES) and
            not (result['script']['prefix'] and result['script']['suffix']), 'R3_OPERATOR_CONTRACT_DRIFT')
        candidate_total += len(reservations)
        call_total += len(attempted)
        logical_total += len(logical)
    complete = i.p.files.read_json(i.PRIVATE / 'generation_complete_v1.json')
    require(complete['parents'] == len(parents) and complete['verifier_queries'] == complete['protected_queries'] == 0, 'R3_GENERATION_COMPLETION_CONFLICT')
    require(candidate_total <= 61 * len(parents) and call_total <= 183 * len(parents), 'R3_GLOBAL_BUDGET_VIOLATION')
    return rows, dict(parents=len(rows), candidate_evaluations=candidate_total, detector_calls=call_total,
        logical_requests=logical_total, cached_requests=logical_total-candidate_total,
        max_candidate_evaluations_per_parent=max(r['candidate_evaluations'] for r in rows),
        max_detector_calls_per_parent=max(r['detector_calls'] for r in rows),
        journal_sha256=i.p.files.sha(journal_path), private_generation_sha256=i.p.files.sha(i.PRIVATE / 'generation_v1.jsonl'),
        budget_violations=0, reconstruction_failures=0, verifier_queries=0, protected_queries=0,
        synthetic_preflight_calls=3, post_freeze_scoring_calls='NOT_STARTED')


def regime_manifest(rows, completed_at, implementation):
    original = i.p.files.read_json(i.p.R1 / 'r1_dataset_manifest_v1.json')
    source = {r['sample_id']: (index, r) for index, r in enumerate(original['samples'])}
    samples, parents = [], []
    for row in rows:
        index, parent = source[row['parent_sample_id']]
        samples.append(dict(parent, sample_id=row['sample_id'], threat_regime='R3_ENSEMBLE_TARGETED',
            parent_sample_id=parent['sample_id'], target_detector='ALL', attack_method='R3_MINIMAX_REVERSIBLE_V1',
            attack_method_revision=implementation, generator_type='RULE_BASED', generator_model=None,
            generator_system='R3_MINIMAX_REVERSIBLE_V1', generator_revision=implementation, generated_sample=True,
            generation_evaluation_status='COMPLETED', lineage_provenance_status='DERIVED_FROM_PARENT',
            lineage_justification='Inherited unchanged from frozen R1 parent; exact reversible detector-evasion descendant.',
            attack_success_definition='ALL_OPERATIONAL_MISS_V1', attack_success=row['success'], valid_attack_attempt=True,
            created_at=completed_at))
        parents.append(dict({k: parent[k] for k in ('sample_id', 'lineage_id', 'dataset_id', 'dataset_revision', 'source', 'source_native_id', 'provenance_status')},
            evidence_role='r1_parent_manifest', evidence_locator='/samples/' + str(index)))
    payload = {k: v for k, v in original.items() if k not in ('experiment_id', 'manifest_hash', 'sample_count', 'attack_count', 'benign_count')}
    payload.update(dataset_id='R3-ENSEMBLE-001', dataset_revision=i.p.files.sha(TERMINALS),
        threat_regime='R3_ENSEMBLE_TARGETED', dataset_source='FROZEN_R1_ATTACK_PARENTS', dataset_source_revision=i.p.files.sha(TERMINALS),
        samples=samples, dataset_sources=[r for r in original['dataset_sources'] if r['source'] in {s['source'] for s in samples}],
        created_at=completed_at, external_parents=parents,
        evidence=[dict(role=role, path=path.relative_to(i.p.ROOT).as_posix(), sha256=i.p.files.sha(path)) for role, path in (
            ('r1_parent_manifest', i.p.R1 / 'r1_dataset_manifest_v1.json'), ('terminal_metadata', TERMINALS),
            ('predeclared_design', i.OUT / 'r3_predeclaration_v1.json'), ('frozen_seed_membership', i.SEEDS))],
        notes=('Attack-only simultaneous evasion; validity means exact reversible UTF8 preservation, not downstream compromise.',
            'Deterministic one-parent-per-inherited-lineage policy; all selected parents retained regardless of outcome.'))
    return create_manifest(**payload)


def freeze():
    require(not TERMINALS.exists(), 'R3_TERMINALS_ALREADY_FROZEN')
    rows, accounting = validate()
    complete = i.p.files.read_json(i.PRIVATE / 'generation_complete_v1.json')
    receipt = i.p.files.read_json(i.PRIVATE / 'run_receipt_v1.json')
    i.p.publish(i.OUT / 'r3_authoritative_run_receipt_v1.json', dict(receipt,
        private_receipt_sha256=i.p.files.sha(i.PRIVATE / 'run_receipt_v1.json')))
    i.p.publish(TERMINALS, dict(artifact_version='r3_terminal_manifest_v1', status='FROZEN', terminals=rows,
        parent_count=len(rows), source_counts=dict(Counter(r['source'] for r in rows)),
        inherited_lineages=len({r['lineage_id'] for r in rows}), generation_journal_sha256=accounting['private_generation_sha256'],
        raw_text_policy='LOCAL_ONLY_IGNORED', inverse_passes=len(rows)))
    i.p.publish(i.OUT / 'r3_generation_results_v1.json', dict(complete, status='PASS',
        all_three_successes=sum(r['success'] for r in rows), target_success_rate=sum(r['success'] for r in rows)/len(rows),
        terminal_manifest_sha256=i.p.files.sha(TERMINALS), implementation_commit=receipt['implementation_commit']))
    i.p.publish(i.OUT / 'r3_query_accounting_v1.json', dict(artifact_version='r3_query_accounting_v1', status='PASS', **accounting))
    manifest = regime_manifest(rows, complete['completed_at'], receipt['implementation_commit'])
    i.p.publish(REGIME, manifest.model_dump(mode='json'))
    print(json.dumps(dict(status='R3_TERMINAL_FREEZE_PASS', **accounting), indent=2))


if __name__ == '__main__':
    freeze()
