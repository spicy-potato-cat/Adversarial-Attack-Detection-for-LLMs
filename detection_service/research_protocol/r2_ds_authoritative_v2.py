"""Receipt-gated restart orchestration around the unchanged frozen D_S search."""

import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
import json
import os
import statistics

from detection_service.research_protocol import r2_ds_predeclare as p, r2_ds_design as d
from detection_service.research_protocol import ds_numerical_disposition as disposition
from detection_service.research_protocol import ds_numerical_diagnosis as numerical
from detection_service.research_protocol.r2_ds_generator import generate, inverse, sha
from detection_service.research_protocol.r2_ds_generate_run import TargetOracle, target_isolation, implementation_anchor
from detection_service.research_protocol.r2_ds_query_journal import QueryJournal

RECEIPT = p.OUT/'r2_ds_authoritative_restart_receipt_v2.json'
PRIVATE = p.ROOT/'detection_service/outputs/r2-ds-001-authoritative-v2'
RUN_ID = 'R2-DS-001-AUTHORITATIVE-V2-20261009'
CODE = 'detection_service/research_protocol/r2_ds_authoritative_v2.py'


def authorize():
    value=p.files.read_json(disposition.PATH)
    p.require(value['status']=='PASS' and value['gate']['calibrated_delta']<=1e-12,'DS_DISPOSITION_GATE_FAILED')
    phase_a=p.committed(disposition.PATH)
    bindings=disposition.identities()
    p.require(bindings==value['bindings'],'DISPOSITION_BINDING_DRIFT')
    p.require(not (p.OUT/'r2_ds_terminal_manifest_v1.json').exists(),'PRIOR_ACCEPTED_TERMINALS')
    commits=dict(predeclaration='9a1c4371f9c1c9fc2531fc181a2f046e387b98b2',
        calibrated_tie_clarification=p.git('rev-parse','99a3379').decode().strip(),
        generator=p.git('rev-parse','e9a6598').decode().strip(),
        loader_repair='154055902dc7d28c55da3dd0a75a5ac85eaa44a7',
        blocker_evidence='5f5e6f4b159fb2aa75bec9a3f26360b776e4afc0',
        durable_accounting_repair='35b88f7fd445e209434e77474862818211c2043c',
        numerical_diagnosis=disposition.START,numerical_disposition=phase_a)
    p.publish(RECEIPT,dict(artifact_version='r2_ds_authoritative_restart_receipt_v2',status='AUTHORIZED',
        run_id=RUN_ID,created_at=datetime.now(timezone.utc).isoformat(),commits=commits,bindings=bindings,
        disposition_sha256=p.files.sha(disposition.PATH),restart_from_seed_one=True,
        first_seed_sample_id=p.parents()[0]['parent_sample_id'],expected_seeds=698,
        source_counts=dict(Counter(r['source'] for r in p.parents())),inherited_lineages=94,
        historical_failed_attempt='UNKNOWN_EXACT_COUNT_BOUNDED_1_TO_61',
        historical_diagnostic_queries=dict(prior_repair=1,numerical_diagnosis=362,disposition_gate=1,total_known=364),
        prior_accepted_terminals=0,prior_transfer_queries=dict(D_M_B=0,D_G=0,ensemble=0),
        changed=dict(attack_design=False,seed_membership=False,operator_registry=False,query_budget=False,
                     target_objective=False,threshold=False,replay_tolerance=False),
        generator_implementation_commit=implementation_anchor(),
        orchestration_code_sha256=p.files.sha(p.ROOT/CODE),private_directory=PRIVATE.relative_to(p.ROOT).as_posix(),
        orchestration_change='Additive receipt-gated invocation and new output directory; frozen generate/TargetOracle/isolation/journal bytes unchanged. Replaces obsolete runner startup gates only for this explicitly authorized run.',
        role_aliases=dict(BASELINE='BASELINE_REPLAY',SALIENCY='SALIENCY_PROBE',FINAL_REPLAY='REPLAY_VALIDATION'),
        track_b=numerical.TRACK_B))


def restart_gate():
    receipt=p.files.read_json(RECEIPT)
    commit=p.committed(RECEIPT)
    p.require(p.git('rev-parse','HEAD').decode().strip()==commit,'RESTART_COMMIT_HEAD_REQUIRED')
    p.require(not p.git('status','--porcelain').decode().strip(),'CLEAN_RESTART_REQUIRED')
    p.require(receipt['run_id']==RUN_ID and receipt['restart_from_seed_one'],'RESTART_ID_CONFLICT')
    p.require(receipt['disposition_sha256']==p.files.sha(disposition.PATH),'DISPOSITION_DRIFT')
    p.require(receipt['bindings']==disposition.identities(),'RESTART_CONTRACT_DRIFT')
    p.require(receipt['orchestration_code_sha256']==p.files.sha(p.ROOT/CODE),'RESTART_CODE_DRIFT')
    p.require(receipt['first_seed_sample_id']==p.parents()[0]['parent_sample_id'],'RESTART_SEED_ORDER_DRIFT')
    p.require(not (PRIVATE/'invocation_v2.json').exists(),'AUTHORITATIVE_V2_ALREADY_INVOKED')
    return receipt,commit


def metadata(parent,result,implementation):
    text=result['text']
    return dict(experiment_id='R2-DS-001',run_id=RUN_ID,sample_id='R2-DS-'+sha(parent['parent_sample_id']),
        parent_sample_id=parent['parent_sample_id'],source=parent['source'],attack_family=parent['attack_family'],
        lineage_id=parent['lineage_id'],parent_lineage_id=parent['lineage_id'],target_detector=d.TARGET,
        threat_regime=d.DESIGN['threat_regime'],generation_method='DS_REVERSIBLE_SEARCH_V1',generation_status='COMPLETED',
        generator_revision=implementation,mechanism=result['mechanism'],
        operators_used=list(dict.fromkeys(e['operator'] for e in result['script']['edits'])),
        word_spans_modified=[{k:e[k] for k in ('start','end','operator','insertion_offsets')} for e in result['script']['edits']],
        transformation_metadata=dict(private_edit_script_only=True,
            prefix_number=d.PREFIXES.index(result['script']['prefix'])+1 if result['script']['prefix'] else None,
            suffix_number=d.SUFFIXES.index(result['script']['suffix'])+1 if result['script']['suffix'] else None),
        logical_queries=result['logical_queries'],unique_model_queries=result['unique_model_queries'],
        parent_text_sha256=parent['parent_text_sha256'],terminal_text_sha256=sha(text),
        original_byte_length=result['original_byte_length'],terminal_byte_length=len(text.encode('utf-8')),
        baseline_calibrated_score=result['baseline']['calibrated_score'],terminal_calibrated_score=result['terminal']['calibrated_score'],
        baseline_decision=1,terminal_decision=int(result['terminal']['calibrated_score']>=d.THRESHOLD),
        target_threshold=d.THRESHOLD,target_threshold_id=d.THRESHOLD_ID,validity_status=result['validity_status'],
        inverse_reconstruction=True,target_evasion_success=result['success'],
        baseline_coverage={k:result['baseline'][k] for k in ('input_tokens','tokens_analyzed','truncated')},
        terminal_coverage={k:result['terminal'][k] for k in ('input_tokens','tokens_analyzed','truncated')},
        analyzed_parent_character_end=result['coverage_end'],eligible_span_count=result['eligible_spans'],
        saliency_span_count=result['saliency_spans'],ranked_span_count=result['ranked_spans'])


def returned_rows():
    path=PRIVATE/'query_receipts_v2.jsonl'
    return [json.loads(line) for line in path.read_bytes().splitlines()] if path.exists() else []


def generate_run():
    from detection_service.research_protocol.release_validation import offline
    from detection_service.research_protocol import protocol_patch_001 as patch
    import detection_service.app.detectors.semantic.calibration
    receipt,commit=restart_gate()
    implementation=receipt['generator_implementation_commit']
    started=datetime.now(timezone.utc).isoformat()
    p.publish(PRIVATE/'invocation_v2.json',dict(run_id=RUN_ID,status='RUNNING',restart_commit=commit,
        started_at=started,environment_before_loader=numerical.environment()))
    prequery_path=PRIVATE/'prequery_receipt_v2.json'
    p.publish(prequery_path,dict(receipt_version='r2_ds_prequery_receipt_v2',run_id=RUN_ID,restart_commit=commit,
        authoritative_prior_model_queries=0,prior_query_scope='THIS_NEW_AUTHORITATIVE_RUN_ONLY',
        historical_failed_queries=receipt['historical_failed_attempt'],historical_diagnostic_queries=receipt['historical_diagnostic_queries'],
        generator_implementation_commit=implementation,
        generator_implementation_sha256=p.files.sha(p.ROOT/'detection_service/research_protocol/r2_ds_generator.py'),
        orchestration_sha256=p.files.sha(p.ROOT/CODE),protocol_patch_id=patch.PATCH_ID,
        protocol_patch_commit=patch.patch_commit(),restart_receipt_sha256=p.files.sha(RECEIPT),
        scientific_outcomes_observed='NONE_FOR_NEW_RUN',bindings=receipt['bindings']))
    protocol_receipt=dict(path=prequery_path.relative_to(p.ROOT).as_posix(),sha256=p.files.sha(prequery_path))
    texts=p.private_parents()
    with (p.R1/'r1_predictions_v1.csv').open(encoding='utf-8',newline='') as source:
        baseline_rows={r['sample_id']:dict(raw_score=float(r['raw_score']),calibrated_score=float(r['calibrated_score']),
            native_decision=int(r['native_binary_prediction']),operational_decision=int(r['operational_binary_prediction']))
            for r in csv.DictReader(source) if r['detector_id']==d.DETECTOR_ID}
    terminals=[]
    journal=QueryJournal(PRIVATE/'query_receipts_v2.jsonl',RUN_ID,'AUTHORITATIVE_GENERATION')
    path=PRIVATE/'generation_v2.jsonl'
    current_parent=None
    environment=None
    try:
        with offline(),target_isolation(),path.open('xb') as stream:
            oracle=TargetOracle(journal)
            environment=numerical.environment()
            p.publish(PRIVATE/'generation_environment_v2.json',environment)
            for index,parent in enumerate(p.parents(),1):
                current_parent=parent
                oracle.seed_sample_id=parent['parent_sample_id']
                oracle.frozen_baseline=baseline_rows[parent['parent_sample_id']]
                result=generate(texts[parent['parent_sample_id']],oracle)
                p.require(inverse(result['text'],result['script'])==texts[parent['parent_sample_id']].encode('utf-8'),'INVERSE_FAILURE')
                result['original_byte_length']=len(texts[parent['parent_sample_id']].encode('utf-8'))
                row=metadata(parent,result,implementation)
                stream.write(p.files.canonical_bytes(dict(metadata=row,private_generation=result))+b'\n')
                stream.flush()
                os.fsync(stream.fileno())
                terminals.append(row)
                print(json.dumps(dict(stage='DS_ONLY_GENERATION',run_id=RUN_ID,completed=index,total=698,
                    successes=sum(t['target_evasion_success'] for t in terminals),unique_queries=journal.sequence,
                    logical_queries=journal.logical_queries)),flush=True)
    except BaseException as exc:
        journal.close()
        rows=returned_rows()
        failed=rows[-1] if rows else None
        recurrence='BASELINE_TARGET_REPLAY_MISMATCH' in str(exc)
        blocked=dict(artifact_version='r2_ds_authoritative_interruption_v2',status='BLOCKED',run_id=RUN_ID,
            reason='R2_DS_BASELINE_REPLAY_RECURRENCE' if recurrence else 'R2_DS_REQUIRES_REPAIR',error=str(exc),
            restart_commit=commit,completed_seeds=len(terminals),accepted_terminals=0,current_seed=current_parent,
            failed_model_return=failed,frozen_baseline=baseline_rows.get(current_parent['parent_sample_id']) if current_parent else None,
            unique_generation_queries=len(rows),logical_generation_queries=journal.logical_queries,
            generation_call_counts=dict(D_S=len(rows),D_M_B=0,D_G=0,ensemble=0),
            baseline_replay_violations=int(recurrence),environment=environment or numerical.environment(),
            journal_sha256=p.files.sha(journal.path),logical_journal_sha256=p.files.sha(journal.logical_path),
            partial_results_accepted=False,transfer_started=False)
        p.publish(PRIVATE/'interruption_v2.json',blocked)
        p.publish(p.OUT/'r2_ds_authoritative_interruption_v2.json',blocked)
        raise
    else:
        journal.close()
    p.require(len(terminals)==698,'INCOMPLETE_GENERATION')
    p.require(disposition.identities()==receipt['bindings'],'POST_GENERATION_CONTRACT_DRIFT')
    generator=dict(artifact_version='r2_ds_generator_manifest_v1',status='PASS',run_id=RUN_ID,
        predeclaration_commit=receipt['commits']['predeclaration'],protocol_prequery_receipt=protocol_receipt,
        implementation_commit=implementation,orchestration_commit=commit,started_at=started,
        completed_at=datetime.now(timezone.utc).isoformat(),design_sha256=receipt['bindings']['generator_contract_sha256'],
        private_journal=dict(path=path.relative_to(p.ROOT).as_posix(),sha256=p.files.sha(path)),
        target_generation_queries=journal.sequence,total_logical_queries=journal.logical_queries,
        max_queries=max(r['unique_model_queries'] for r in terminals),query_budget_violations=0,
        generation_call_counts=dict(D_S=journal.sequence,D_M_B=0,D_G=0,ensemble=0),
        isolation='Unchanged target_isolation guard and TargetOracle; no non-target generation feedback.',
        inverse_passed=698,inverse_failed=0,invalid_utf8=0,generation_errors=0,partial_runs_merged=False,
        baseline_replay_passed=698,baseline_replay_violations=0,
        query_journal=dict(path=journal.path.relative_to(p.ROOT).as_posix(),sha256=p.files.sha(journal.path),
            logical_path=journal.logical_path.relative_to(p.ROOT).as_posix(),logical_sha256=p.files.sha(journal.logical_path)))
    p.require(journal.sequence==sum(r['unique_model_queries'] for r in terminals),'QUERY_TOTAL_CONFLICT')
    p.publish(p.OUT/'r2_ds_generator_manifest_v1.json',generator)
    terminal_hash=p.publish(p.OUT/'r2_ds_terminal_manifest_v1.json',dict(artifact_version='r2_ds_terminal_manifest_v1',
        experiment_id='R2-DS-001',run_id=RUN_ID,status='FROZEN',parent_count=698,terminal_count=698,
        target_detector=d.TARGET,implementation_commit=implementation,terminals=terminals))
    p.publish(p.OUT/'r2_ds_target_results_v1.json',dict(artifact_version='r2_ds_target_results_v1',baseline_detected=698,
        terminal_manifest_sha256=terminal_hash,successful_evasions=sum(r['target_evasion_success'] for r in terminals),
        target_evasion_rate=sum(r['target_evasion_success'] for r in terminals)/698,
        source_counts=dict(Counter(r['source'] for r in terminals)),
        successes_by_operator=dict(Counter(r['mechanism'] for r in terminals if r['target_evasion_success'])),
        median_unique_queries=statistics.median(r['unique_model_queries'] for r in terminals),
        unique_query_histogram={str(k):v for k,v in sorted(Counter(r['unique_model_queries'] for r in terminals).items())},
        median_baseline_score=statistics.median(r['baseline_calibrated_score'] for r in terminals),
        median_terminal_score=statistics.median(r['terminal_calibrated_score'] for r in terminals),
        target_coverage=dict(parent_truncated=sum(r['baseline_coverage']['truncated'] for r in terminals),
            terminal_truncated=sum(r['terminal_coverage']['truncated'] for r in terminals),
            newly_truncated=sum(r['terminal_coverage']['truncated'] and not r['baseline_coverage']['truncated'] for r in terminals))))
    print(json.dumps(dict(status='GENERATION_COMPLETE_FREEZE_COMMIT_REQUIRED',terminals=698)),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode',required=True,choices=('authorize','generate'))
    mode=parser.parse_args().mode
    (authorize if mode=='authorize' else generate_run)()
