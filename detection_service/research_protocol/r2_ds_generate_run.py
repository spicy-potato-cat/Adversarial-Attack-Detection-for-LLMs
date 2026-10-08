"""One authoritative offline D_S-only generation invocation, then freeze."""

import argparse
import builtins
from collections import Counter
from contextlib import contextmanager
from datetime import datetime,timezone
import hashlib
import json
import os
import statistics
import traceback

from detection_service.research_protocol import r2_ds_design as d, r2_ds_predeclare as p
from detection_service.research_protocol.r2_ds_generator import generate,sha,inverse,require


@contextmanager
def target_isolation():
    from detection_service.research_protocol.adapters import DetectorAdapter
    constructor,predict,importer=DetectorAdapter.__init__,DetectorAdapter.predict,builtins.__import__
    def restricted_init(self,label,contracts):
        require(label=='D_S','BLOCKED_R2_TARGET_ISOLATION')
        return constructor(self,label,contracts)
    def restricted_predict(self,*args,**kwargs):
        require(self.detector_id==d.DETECTOR_ID,'BLOCKED_R2_TARGET_ISOLATION')
        return predict(self,*args,**kwargs)
    def restricted_import(name,*args,**kwargs):
        if name=='detection_service.app.detectors.semantic.calibration':
            return importer(name,*args,**kwargs)
        fromlist=kwargs.get('fromlist',args[2] if len(args)>2 else ()) or ()
        names=[name,*[name+'.'+item for item in fromlist]]
        require(not any(fragment in value for value in names for fragment in ('detectors.semantic','detectors.guard','common_mode','r1_scoring','r1_analysis','r2_ds_transfer','r2_ds_analysis','r2_dmb_transfer')),'BLOCKED_UNTARGETED_GENERATION_IMPORT')
        return importer(name,*args,**kwargs)
    DetectorAdapter.__init__,DetectorAdapter.predict,builtins.__import__=restricted_init,restricted_predict,restricted_import
    try:
        yield
    finally:
        DetectorAdapter.__init__,DetectorAdapter.predict,builtins.__import__=constructor,predict,importer


class TargetOracle:
    detector_id=d.DETECTOR_ID

    def __init__(self,journal=None):
        require(journal is not None,'DURABLE_QUERY_JOURNAL_REQUIRED')
        self.journal=journal
        self.seed_sample_id=None
        self.frozen_baseline=None
        from detection_service.research_protocol.ds_runtime import accepted_ds_adapter
        self.adapter=accepted_ds_adapter()
        self.adapter._live=self.adapter._load_live()
        runtime=self.adapter._live
        require(runtime.extractor.config.max_analysis_tokens==4096 and runtime.extractor.config.device=='cpu','R2_PROTOCOL_MUTATION_REQUIRED')
        self.tokenizer=runtime.extractor.engine.tokenizer
        require(self.tokenizer.is_fast,'EXACT_TOKENIZER_OFFSETS_REQUIRED')

    def coverage_end(self,text):
        encoded=self.tokenizer(text,add_special_tokens=False,truncation=True,max_length=4096,return_offsets_mapping=True)
        return max((b for a,b in encoded['offset_mapping'] if b>a),default=0)

    def __call__(self,text):
        return self.query_with_role(text,'BASELINE_REPLAY')

    def logical_query(self,text,role,cached):
        self.journal.logical(text,self.seed_sample_id,role,cached)
        self.logical_request_pending=not cached

    def query_with_role(self,text,role):
        require(self.seed_sample_id is not None,'SEED_QUERY_BINDING_REQUIRED')
        pending=getattr(self,'logical_request_pending',False)
        self.logical_request_pending=False
        row=self.journal.score(self.adapter,text,self.seed_sample_id,role,logical_already_logged=pending)
        require(row.status=='OK','GENERATION_NON_OK:'+str(row.error_code))
        if role=='BASELINE_REPLAY':
            require(self.frozen_baseline is not None,'FROZEN_BASELINE_REQUIRED')
            from detection_service.research_protocol.r2_ds_repair_evidence import compare
            delta=compare(self.frozen_baseline,dict(raw_score=row.raw_score,calibrated_score=row.calibrated_score,
                native_decision=row.native_binary_prediction,operational_decision=int(row.calibrated_score>=d.THRESHOLD)))
            require(delta['raw_delta']<=1e-12 and delta['calibrated_delta']<=1e-12 and delta['native_match'] and delta['operational_match'],'BASELINE_TARGET_REPLAY_MISMATCH')
        return dict(status=row.status,calibrated_score=row.calibrated_score,input_tokens=row.input_tokens,
            tokens_analyzed=row.tokens_analyzed,truncated=row.truncated)


def implementation_anchor():
    commit=p.git('log','-1','--format=%H','--','detection_service/research_protocol/r2_ds_generate_run.py').decode().strip()
    for name in ('r2_ds_generator.py','r2_ds_generate_run.py'):
        path=p.ROOT/'detection_service/research_protocol'/name
        require(path.read_bytes()==p.git('show',commit+':'+path.relative_to(p.ROOT).as_posix()),'GENERATOR_IMPLEMENTATION_DRIFT')
    return commit


def run():
    os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_DATASETS_OFFLINE='1')
    from detection_service.research_protocol.release_validation import offline
    from detection_service.research_protocol.r2_ds_repair_evidence import restart_gate
    diagnostic=p.files.read_json(p.OUT/'diagnostics/ds_baseline_pipeline_comparison_v1.json')
    audit=p.files.read_json(p.OUT/'diagnostics/ds_baseline_replay_all_seeds_v1.json')
    restart_gate(audit,diagnostic['primary_root_cause'],[r['parent_sample_id'] for r in p.parents()],p.parents()[0]['parent_sample_id'])
    require(not p.git('status','--porcelain').decode().strip(),'CLEAN_GENERATOR_START_REQUIRED')
    implementation=implementation_anchor()
    preflight=p.files.read_json(p.OUT/'r2_ds_preflight_acceptance_v2.json')
    p.committed(p.OUT/'r2_ds_preflight_acceptance_v2.json')
    require(preflight['status']=='PASS' and preflight['authoritative_model_queries']==0,'PREFLIGHT_REQUIRED')
    require(all(p.files.sha(p.ROOT/'detection_service/research_protocol'/name)==value for name,value in preflight['implementation_sha256'].items()),'PREFLIGHT_IMPLEMENTATION_DRIFT')
    require(p.git('rev-parse','HEAD').decode().strip()==implementation,'AUTHORITATIVE_IMPLEMENTATION_HEAD_REQUIRED')
    precommit=p.committed(p.OUT/'r2_ds_predeclaration_v1.json')
    p.committed(p.OUT/'r2_ds_seed_manifest_v1.json')
    from detection_service.research_protocol.r2_ds_clarification import declaration
    declaration()
    p.preserved()
    require(not (p.OUT/'r2_ds_terminal_manifest_v1.json').exists(),'ACCEPTED_GENERATION_ALREADY_EXISTS')
    p.PRIVATE.mkdir(parents=True,exist_ok=True)
    receipt=p.PRIVATE/'invocation_v1.json'
    require(not receipt.exists(),'PRIOR_INVOCATION_EXISTS_RESTART_REQUIRES_DOCUMENTATION')
    started=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    from detection_service.research_protocol.r2_ds_binding import prequery_receipt
    protocol_receipt=prequery_receipt(implementation)
    p.publish(receipt,dict(status='RUNNING',started_at=started,implementation_commit=implementation,predeclaration_commit=precommit,
        protocol_prequery_receipt=protocol_receipt))
    texts=p.private_parents()
    seeds=p.parents()
    terminals=[]
    journal=p.PRIVATE/'generation_v1.jsonl'
    require(not journal.exists(),'REFUSE_PARTIAL_RUN_MERGE')
    try:
        # DS shares these model-free probability helpers; no semantic runtime is loaded.
        from detection_service.app.detectors.semantic import calibration
        with target_isolation(),offline(),journal.open('xb') as stream:
            from detection_service.research_protocol.r2_ds_query_journal import QueryJournal
            import csv
            query_journal=QueryJournal(p.PRIVATE/'query_receipts_v1.jsonl',started,'AUTHORITATIVE_GENERATION')
            oracle=TargetOracle(query_journal)
            with (p.R1/'r1_predictions_v1.csv').open(encoding='utf-8',newline='') as source:
                baseline_rows={r['sample_id']:dict(raw_score=float(r['raw_score']),calibrated_score=float(r['calibrated_score']),
                    native_decision=int(r['native_binary_prediction']),operational_decision=int(r['operational_binary_prediction']))
                    for r in csv.DictReader(source) if r['detector_id']==d.DETECTOR_ID}
            for index,parent in enumerate(seeds,1):
                oracle.seed_sample_id=parent['parent_sample_id']
                oracle.frozen_baseline=baseline_rows[parent['parent_sample_id']]
                result=generate(texts[parent['parent_sample_id']],oracle)
                require(abs(result['baseline']['calibrated_score']-parent['baseline_calibrated_score'])<=1e-12,'BASELINE_TARGET_REPLAY_MISMATCH')
                require(inverse(result['text'],result['script'])==texts[parent['parent_sample_id']].encode('utf-8'),'INVERSE_FAILURE')
                metadata=dict(experiment_id='R2-DS-001',sample_id='R2-DS-'+sha(parent['parent_sample_id']),parent_sample_id=parent['parent_sample_id'],
                    source=parent['source'],attack_family=parent['attack_family'],lineage_id=parent['lineage_id'],
                    parent_lineage_id=parent['lineage_id'],target_detector=d.TARGET,threat_regime=d.DESIGN['threat_regime'],
                    generation_method='DS_REVERSIBLE_SEARCH_V1',generation_status='COMPLETED',
                    generator_revision=implementation,mechanism=result['mechanism'],
                    operators_used=list(dict.fromkeys(e['operator'] for e in result['script']['edits'])),
                    word_spans_modified=[{k:e[k] for k in ('start','end','operator','insertion_offsets')} for e in result['script']['edits']],
                    transformation_metadata=dict(private_edit_script_only=True,prefix_number=d.PREFIXES.index(result['script']['prefix'])+1 if result['script']['prefix'] else None,
                        suffix_number=d.SUFFIXES.index(result['script']['suffix'])+1 if result['script']['suffix'] else None),
                    logical_queries=result['logical_queries'],unique_model_queries=result['unique_model_queries'],
                    parent_text_sha256=parent['parent_text_sha256'],terminal_text_sha256=sha(result['text']),
                    original_byte_length=len(texts[parent['parent_sample_id']].encode('utf-8')),terminal_byte_length=len(result['text'].encode('utf-8')),
                    baseline_calibrated_score=result['baseline']['calibrated_score'],terminal_calibrated_score=result['terminal']['calibrated_score'],
                    baseline_decision=1,terminal_decision=int(result['terminal']['calibrated_score']>=d.THRESHOLD),
                    target_threshold=d.THRESHOLD,target_threshold_id=d.THRESHOLD_ID,
                    validity_status=result['validity_status'],inverse_reconstruction=True,target_evasion_success=result['success'],
                    baseline_coverage={k:result['baseline'][k] for k in ('input_tokens','tokens_analyzed','truncated')},
                    terminal_coverage={k:result['terminal'][k] for k in ('input_tokens','tokens_analyzed','truncated')},
                    analyzed_parent_character_end=result['coverage_end'],eligible_span_count=result['eligible_spans'],
                    saliency_span_count=result['saliency_spans'],ranked_span_count=result['ranked_spans'])
                stream.write(p.files.canonical_bytes(dict(metadata=metadata,private_generation=result))+b'\n')
                stream.flush()
                terminals.append(metadata)
                if index%10==0 or index==1:
                    print(json.dumps(dict(stage='DS_ONLY_GENERATION',completed=index,total=p.count(),
                        successes=sum(t['target_evasion_success'] for t in terminals),unique_queries=sum(t['unique_model_queries'] for t in terminals))),flush=True)
            query_journal.close()
        p.preserved()
        require(len(terminals)==p.count(),'INCOMPLETE_GENERATION')
        generator=dict(artifact_version='r2_ds_generator_manifest_v1',status='PASS',predeclaration_commit=precommit,
            protocol_prequery_receipt=protocol_receipt,
            implementation_commit=implementation,started_at=started,completed_at=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
            design_sha256=p.digest('artifacts/research_protocol/r2_ds/r2_ds_predeclaration_v1.json'),
            private_journal=dict(path=journal.relative_to(p.ROOT).as_posix(),sha256=p.files.sha(journal)),
            target_generation_queries=sum(t['unique_model_queries'] for t in terminals),
            max_queries=max(t['unique_model_queries'] for t in terminals),query_budget_violations=0,
            generation_call_counts=dict(D_M_B=0,D_G=0,ensemble=0,D_S=sum(t['unique_model_queries'] for t in terminals)),
            isolation='Generic non-target adapters rejected and untargeted detector/evaluator imports prohibited for entire generation.',
            inverse_passed=p.count(),inverse_failed=0,invalid_utf8=0,generation_errors=0,partial_runs_merged=False)
        p.publish(p.OUT/'r2_ds_generator_manifest_v1.json',generator)
        terminal_hash=p.publish(p.OUT/'r2_ds_terminal_manifest_v1.json',dict(artifact_version='r2_ds_terminal_manifest_v1',
            experiment_id='R2-DS-001',status='FROZEN',parent_count=p.count(),terminal_count=p.count(),
            target_detector=d.TARGET,implementation_commit=implementation,terminals=terminals))
        p.publish(p.OUT/'r2_ds_target_results_v1.json',dict(artifact_version='r2_ds_target_results_v1',baseline_detected=p.count(),
            terminal_manifest_sha256=terminal_hash,successful_evasions=sum(t['target_evasion_success'] for t in terminals),
            target_evasion_rate=sum(t['target_evasion_success'] for t in terminals)/p.count(),
            source_counts=dict(Counter(t['source'] for t in terminals)),
            successes_by_operator=dict(Counter(t['mechanism'] for t in terminals if t['target_evasion_success'])),
            median_unique_queries=statistics.median(t['unique_model_queries'] for t in terminals),
            unique_query_histogram={str(k):v for k,v in sorted(Counter(t['unique_model_queries'] for t in terminals).items())},
            median_baseline_score=statistics.median(t['baseline_calibrated_score'] for t in terminals),
            median_terminal_score=statistics.median(t['terminal_calibrated_score'] for t in terminals),
            target_coverage=dict(parent_truncated=sum(t['baseline_coverage']['truncated'] for t in terminals),
                terminal_truncated=sum(t['terminal_coverage']['truncated'] for t in terminals),
                newly_truncated=sum(t['terminal_coverage']['truncated'] and not t['baseline_coverage']['truncated'] for t in terminals))))
        report='# R2 D_S Generation v1\n\n'+json.dumps(generator,indent=2)+'\n\n'+json.dumps(p.files.read_json(p.OUT/'r2_ds_target_results_v1.json'),indent=2)+'\n\n'
        report+='Validity is exact reversible text preservation, not downstream jailbreak success. Every original attack remains in the terminal denominator. Raw text and edit contents are local-only. No untargeted scores were consulted. An inherited InjecAgent component limits source inference.\n'
        (p.ROOT/'reviews/R2_DS_GENERATION_v1.md').write_text(report,encoding='utf-8',newline='\n')
        print(json.dumps(dict(status='GENERATION_COMPLETE_FREEZE_COMMIT_REQUIRED',terminals=p.count(),successes=sum(t['target_evasion_success'] for t in terminals))),flush=True)
    except BaseException as exc:
        p.publish(p.PRIVATE/'interruption_v1.json',dict(status='INTERRUPTED_OR_FAILED',implementation_commit=implementation,
            completed_parents=len(terminals),error_type=type(exc).__name__,error=str(exc),accepted_terminal_manifest_exists=(p.OUT/'r2_ds_terminal_manifest_v1.json').exists()))
        raise


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--generate',action='store_true',required=True)
    parser.parse_args()
    run()
