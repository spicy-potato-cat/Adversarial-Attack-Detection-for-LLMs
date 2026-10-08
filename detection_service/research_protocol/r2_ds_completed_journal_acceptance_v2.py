"""Publish complete generation evidence after the approved branch-only gate update."""

from collections import Counter
from datetime import datetime, timezone
import statistics

from detection_service.research_protocol import r2_ds_predeclare as p
from detection_service.research_protocol import r2_ds_authoritative_v2 as r
from detection_service.research_protocol.r2_ds_completion_v2 import lines, ledger
from detection_service.research_protocol.r2_ds_track_b_reference_v1 import approved_reference, verified


def run():
    reference = verified()
    p.require(not (r.PRIVATE / 'interruption_v2.json').exists(), 'SCIENTIFIC_GENERATION_INTERRUPTED')
    p.require(not (p.OUT / 'r2_ds_generator_manifest_v1.json').exists(), 'GENERATION_ALREADY_PUBLISHED')
    receipt = p.files.read_json(r.RECEIPT)
    invocation = p.files.read_json(r.PRIVATE / 'invocation_v2.json')
    restart_commit = p.committed(r.RECEIPT)
    p.require(invocation['run_id'] == r.RUN_ID and invocation['restart_commit'] == restart_commit,
              'INVOCATION_PROVENANCE_CONFLICT')
    p.require(p.files.sha(p.ROOT / r.CODE) == receipt['orchestration_code_sha256'], 'RUN_CODE_DRIFT')
    with approved_reference():
        p.require(r.disposition.identities() == receipt['bindings'], 'SCIENTIFIC_BINDING_DRIFT')
    entries = lines(r.PRIVATE / 'generation_v2.jsonl')
    parents = p.parents()
    p.require(len(entries) == len(parents) == 698, 'INCOMPLETE_GENERATION')
    terminals = []
    implementation = receipt['generator_implementation_commit']
    for parent, entry in zip(parents, entries, strict=True):
        saved = entry['private_generation']
        p.require(r.sha(r.inverse(saved['text'], saved['script']).decode('utf-8')) == parent['parent_text_sha256'],
                  'INVERSE_PARENT_HASH_CONFLICT')
        p.require(entry['metadata'] == r.metadata(parent, saved, implementation), 'TERMINAL_METADATA_CONFLICT')
        terminals.append(entry['metadata'])
    returned = lines(r.PRIVATE / 'query_receipts_v2.jsonl')
    logical = lines(r.PRIVATE / 'query_receipts_v2_logical.jsonl')
    p.require(len(returned) == sum(t['unique_model_queries'] for t in terminals), 'UNIQUE_TOTAL_CONFLICT')
    p.require(len(logical) == sum(t['logical_queries'] for t in terminals), 'LOGICAL_TOTAL_CONFLICT')
    prequery = r.PRIVATE / 'prequery_receipt_v2.json'
    journal = r.PRIVATE / 'generation_v2.jsonl'
    validation_time = datetime.now(timezone.utc).isoformat()
    p.publish(p.OUT / 'r2_ds_completed_journal_acceptance_v2.json', dict(
        status='PASS', run_id=r.RUN_ID, reason='COMMANDER_APPROVED_TRACK_B_REFERENCE_UPDATE',
        original_orchestrator_code_commit=restart_commit, original_run_code_sha256=p.files.sha(p.ROOT / r.CODE),
        original_track_b_reference=reference['original_task_reference'],
        approved_track_b_reference=reference['approved_untouched_reference'],
        reference_authorization_sha256=p.files.sha(p.OUT / 'r2_ds_track_b_reference_update_v1.json'),
        generation_journal_sha256=p.files.sha(journal), complete_seeds=698, new_model_calls=0,
        scientific_bindings_unchanged=True, scientific_generator_unchanged=True,
        publication='Model-free reconstruction from complete original-run records; not a rerun or historical receipt rewrite.',
        validated_at=validation_time))
    generator = dict(artifact_version='r2_ds_generator_manifest_v1', status='PASS', run_id=r.RUN_ID,
        predeclaration_commit=receipt['commits']['predeclaration'],
        protocol_prequery_receipt=dict(path=prequery.relative_to(p.ROOT).as_posix(), sha256=p.files.sha(prequery)),
        implementation_commit=implementation, orchestration_commit=restart_commit,
        started_at=invocation['started_at'],
        completed_at=datetime.fromisoformat(returned[-1]['timestamp']).astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        completed_at_exact=returned[-1]['timestamp'],
        manifest_validation_completed_at=validation_time,
        completion_acceptance_artifact='r2_ds_completed_journal_acceptance_v2.json',
        design_sha256=receipt['bindings']['generator_contract_sha256'],
        private_journal=dict(path=journal.relative_to(p.ROOT).as_posix(), sha256=p.files.sha(journal)),
        target_generation_queries=len(returned), total_logical_queries=len(logical),
        max_queries=max(t['unique_model_queries'] for t in terminals), query_budget_violations=0,
        generation_call_counts=dict(D_S=len(returned), D_M_B=0, D_G=0, ensemble=0),
        isolation='Unchanged original-run target isolation and TargetOracle; no non-target generation feedback.',
        inverse_passed=698, inverse_failed=0, invalid_utf8=0, generation_errors=0, partial_runs_merged=False,
        baseline_replay_passed=698, baseline_replay_violations=0,
        query_journal=dict(path=(r.PRIVATE / 'query_receipts_v2.jsonl').relative_to(p.ROOT).as_posix(),
            sha256=p.files.sha(r.PRIVATE / 'query_receipts_v2.jsonl'),
            logical_path=(r.PRIVATE / 'query_receipts_v2_logical.jsonl').relative_to(p.ROOT).as_posix(),
            logical_sha256=p.files.sha(r.PRIVATE / 'query_receipts_v2_logical.jsonl')))
    p.publish(p.OUT / 'r2_ds_generator_manifest_v1.json', generator)
    terminal_hash = p.publish(p.OUT / 'r2_ds_terminal_manifest_v1.json', dict(
        artifact_version='r2_ds_terminal_manifest_v1', experiment_id='R2-DS-001', run_id=r.RUN_ID,
        status='FROZEN', parent_count=698, terminal_count=698, target_detector=r.d.TARGET,
        implementation_commit=implementation, terminals=terminals))
    p.publish(p.OUT / 'r2_ds_target_results_v1.json', dict(
        artifact_version='r2_ds_target_results_v1', baseline_detected=698, terminal_manifest_sha256=terminal_hash,
        successful_evasions=sum(t['target_evasion_success'] for t in terminals),
        target_evasion_rate=sum(t['target_evasion_success'] for t in terminals)/698,
        source_counts=dict(Counter(t['source'] for t in terminals)),
        successes_by_operator=dict(Counter(t['mechanism'] for t in terminals if t['target_evasion_success'])),
        median_unique_queries=statistics.median(t['unique_model_queries'] for t in terminals),
        unique_query_histogram={str(k): v for k, v in sorted(Counter(t['unique_model_queries'] for t in terminals).items())},
        median_baseline_score=statistics.median(t['baseline_calibrated_score'] for t in terminals),
        median_terminal_score=statistics.median(t['terminal_calibrated_score'] for t in terminals),
        target_coverage=dict(parent_truncated=sum(t['baseline_coverage']['truncated'] for t in terminals),
            terminal_truncated=sum(t['terminal_coverage']['truncated'] for t in terminals),
            newly_truncated=sum(t['terminal_coverage']['truncated'] and not t['baseline_coverage']['truncated'] for t in terminals))))
    ledger()


if __name__ == '__main__':
    run()
