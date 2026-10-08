"""One authoritative offline D_M-B-only generation invocation, then freeze."""

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

from detection_service.research_protocol import r2_dmb_design as d, r2_dmb_predeclare as p
from detection_service.research_protocol.r2_dmb_generator import generate,sha,inverse,require


@contextmanager
def target_isolation():
    from detection_service.research_protocol.adapters import DetectorAdapter
    constructor,predict,importer=DetectorAdapter.__init__,DetectorAdapter.predict,builtins.__import__
    def restricted_init(self,label,contracts):
        require(label=='D_M-B','BLOCKED_R2_TARGET_ISOLATION')
        return constructor(self,label,contracts)
    def restricted_predict(self,*args,**kwargs):
        require(self.detector_id==d.DETECTOR_ID,'BLOCKED_R2_TARGET_ISOLATION')
        return predict(self,*args,**kwargs)
    def restricted_import(name,*args,**kwargs):
        require(not any(fragment in name for fragment in ('ds_runtime','detectors.statistical','detectors.guard','common_mode','r1_scoring','r1_analysis')),'BLOCKED_UNTARGETED_GENERATION_IMPORT')
        return importer(name,*args,**kwargs)
    DetectorAdapter.__init__,DetectorAdapter.predict,builtins.__import__=restricted_init,restricted_predict,restricted_import
    try:
        yield
    finally:
        DetectorAdapter.__init__,DetectorAdapter.predict,builtins.__import__=constructor,predict,importer


class TargetOracle:
    detector_id=d.DETECTOR_ID

    def __init__(self):
        from detection_service.research_protocol.adapters import DetectorAdapter,FrozenDetectorContracts
        self.adapter=DetectorAdapter(d.TARGET,FrozenDetectorContracts())
        self.adapter._live=self.adapter._load_live()
        runtime=self.adapter._live
        import torch
        torch.set_num_threads(runtime.config.cpu_threads)
        require(runtime.config.max_sequence_length==256 and runtime.config.truncation_side=='right','R2_PROTOCOL_MUTATION_REQUIRED')
        require(runtime.tokenizer.is_fast,'EXACT_TOKENIZER_OFFSETS_REQUIRED')
        self.tokenizer=runtime.tokenizer

    def coverage_end(self,text):
        encoded=self.tokenizer(text,add_special_tokens=True,truncation=True,max_length=256,return_offsets_mapping=True)
        return max((b for a,b in encoded['offset_mapping'] if b>a),default=0)

    def __call__(self,text):
        row=self.adapter.predict(text,sample_id='R2-PROBE-'+sha(text),truth_label=1)
        require(row.status=='OK','GENERATION_NON_OK:'+str(row.error_code))
        return dict(status=row.status,raw_score=row.raw_score,input_tokens=row.input_tokens,
            tokens_analyzed=row.tokens_analyzed,truncated=row.truncated)


def implementation_anchor():
    commit=p.committed(p.ROOT/'detection_service/research_protocol/r2_dmb_generate_run.py')
    for name in ('r2_dmb_generator.py','r2_dmb_generate_run.py'):
        path=p.ROOT/'detection_service/research_protocol'/name
        require(path.read_bytes()==p.git('show',commit+':'+path.relative_to(p.ROOT).as_posix()),'GENERATOR_IMPLEMENTATION_DRIFT')
    return commit


def run():
    os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_DATASETS_OFFLINE='1')
    from detection_service.research_protocol.release_validation import offline
    require(not p.git('status','--porcelain').decode().strip(),'CLEAN_GENERATOR_START_REQUIRED')
    implementation=implementation_anchor()
    require(p.git('rev-parse','HEAD').decode().strip()==implementation,'AUTHORITATIVE_IMPLEMENTATION_HEAD_REQUIRED')
    precommit=p.committed(p.OUT/'r2_dmb_predeclaration_v1.json')
    p.committed(p.OUT/'r2_dmb_seed_manifest_v1.json')
    require(p.files.read_json(p.OUT/'r2_dmb_predeclaration_v1.json')['design']==d.DESIGN,'DESIGN_DRIFT')
    p.preserved()
    require(not (p.OUT/'r2_dmb_terminal_manifest_v1.json').exists(),'ACCEPTED_GENERATION_ALREADY_EXISTS')
    p.PRIVATE.mkdir(parents=True,exist_ok=True)
    receipt=p.PRIVATE/'invocation_v1.json'
    require(not receipt.exists(),'PRIOR_INVOCATION_EXISTS_RESTART_REQUIRES_DOCUMENTATION')
    started=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    from detection_service.research_protocol.r2_dmb_patch_binding import prequery_receipt
    protocol_receipt=prequery_receipt(implementation)
    p.publish(receipt,dict(status='RUNNING',started_at=started,implementation_commit=implementation,predeclaration_commit=precommit,
        protocol_prequery_receipt=protocol_receipt))
    texts=p.private_parents()
    seeds=p.parents()
    terminals=[]
    journal=p.PRIVATE/'generation_v1.jsonl'
    require(not journal.exists(),'REFUSE_PARTIAL_RUN_MERGE')
    try:
        with target_isolation(),offline(),journal.open('xb') as stream:
            oracle=TargetOracle()
            for index,parent in enumerate(seeds,1):
                result=generate(texts[parent['parent_sample_id']],oracle)
                require(abs(result['baseline']['raw_score']-parent['baseline_raw_score'])<=1e-12,'BASELINE_TARGET_REPLAY_MISMATCH')
                require(inverse(result['text'],result['script'])==texts[parent['parent_sample_id']].encode('utf-8'),'INVERSE_FAILURE')
                metadata=dict(experiment_id='R2-DMB-001',sample_id='R2-DMB-'+sha(parent['parent_sample_id']),parent_sample_id=parent['parent_sample_id'],
                    source=parent['source'],attack_family=parent['attack_family'],lineage_id=parent['lineage_id'],
                    parent_lineage_id=parent['lineage_id'],target_detector=d.TARGET,threat_regime=d.DESIGN['threat_regime'],
                    generation_method='DMB_REVERSIBLE_SEARCH_V1',generation_status='COMPLETED',
                    generator_revision=implementation,mechanism=result['mechanism'],
                    operators_used=list(dict.fromkeys(e['operator'] for e in result['script']['edits'])),
                    word_spans_modified=[{k:e[k] for k in ('start','end','operator','insertion_offsets')} for e in result['script']['edits']],
                    transformation_metadata=dict(private_edit_script_only=True,prefix_number=d.PREFIXES.index(result['script']['prefix'])+1 if result['script']['prefix'] else None,
                        suffix_number=d.SUFFIXES.index(result['script']['suffix'])+1 if result['script']['suffix'] else None),
                    logical_queries=result['logical_queries'],unique_model_queries=result['unique_model_queries'],
                    parent_text_sha256=parent['parent_text_sha256'],terminal_text_sha256=sha(result['text']),
                    original_byte_length=len(texts[parent['parent_sample_id']].encode('utf-8')),terminal_byte_length=len(result['text'].encode('utf-8')),
                    baseline_raw_score=result['baseline']['raw_score'],terminal_raw_score=result['terminal']['raw_score'],
                    baseline_decision=1,terminal_decision=int(result['terminal']['raw_score']>=d.THRESHOLD),
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
                    print(json.dumps(dict(stage='DMB_ONLY_GENERATION',completed=index,total=800,
                        successes=sum(t['target_evasion_success'] for t in terminals),unique_queries=sum(t['unique_model_queries'] for t in terminals))),flush=True)
        p.preserved()
        require(len(terminals)==800,'INCOMPLETE_GENERATION')
        generator=dict(artifact_version='r2_dmb_generator_manifest_v1',status='PASS',predeclaration_commit=precommit,
            protocol_prequery_receipt=protocol_receipt,
            implementation_commit=implementation,started_at=started,completed_at=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
            design_sha256=p.digest('artifacts/research_protocol/r2_dmb/r2_dmb_predeclaration_v1.json'),
            private_journal=dict(path=journal.relative_to(p.ROOT).as_posix(),sha256=p.files.sha(journal)),
            target_generation_queries=sum(t['unique_model_queries'] for t in terminals),
            max_queries=max(t['unique_model_queries'] for t in terminals),query_budget_violations=0,
            generation_call_counts=dict(D_S=0,D_G=0,ensemble=0,D_M_B=sum(t['unique_model_queries'] for t in terminals)),
            isolation='Generic non-target adapters rejected and untargeted detector/evaluator imports prohibited for entire generation.',
            inverse_passed=800,inverse_failed=0,invalid_utf8=0,generation_errors=0,partial_runs_merged=False)
        p.publish(p.OUT/'r2_dmb_generator_manifest_v1.json',generator)
        terminal_hash=p.publish(p.OUT/'r2_dmb_terminal_manifest_v1.json',dict(artifact_version='r2_dmb_terminal_manifest_v1',
            experiment_id='R2-DMB-001',status='FROZEN',parent_count=800,terminal_count=800,
            target_detector=d.TARGET,implementation_commit=implementation,terminals=terminals))
        p.publish(p.OUT/'r2_dmb_target_results_v1.json',dict(artifact_version='r2_dmb_target_results_v1',baseline_detected=800,
            terminal_manifest_sha256=terminal_hash,successful_evasions=sum(t['target_evasion_success'] for t in terminals),
            target_evasion_rate=sum(t['target_evasion_success'] for t in terminals)/800,
            source_counts=dict(Counter(t['source'] for t in terminals)),
            successes_by_operator=dict(Counter(t['mechanism'] for t in terminals if t['target_evasion_success'])),
            median_unique_queries=statistics.median(t['unique_model_queries'] for t in terminals),
            unique_query_histogram={str(k):v for k,v in sorted(Counter(t['unique_model_queries'] for t in terminals).items())},
            median_baseline_score=statistics.median(t['baseline_raw_score'] for t in terminals),
            median_terminal_score=statistics.median(t['terminal_raw_score'] for t in terminals),
            target_coverage=dict(parent_truncated=sum(t['baseline_coverage']['truncated'] for t in terminals),
                terminal_truncated=sum(t['terminal_coverage']['truncated'] for t in terminals),
                newly_truncated=sum(t['terminal_coverage']['truncated'] and not t['baseline_coverage']['truncated'] for t in terminals))))
        report='# R2 D_M-B Generation v1\n\n'+json.dumps(generator,indent=2)+'\n\n'+json.dumps(p.files.read_json(p.OUT/'r2_dmb_target_results_v1.json'),indent=2)+'\n\n'
        report+='Validity is exact reversible text preservation, not downstream jailbreak success. Every original attack remains in the terminal denominator. Raw text and edit contents are local-only. No untargeted scores were consulted. One 400-row InjecAgent lineage limits source inference.\n'
        (p.ROOT/'reviews/R2_DMB_GENERATION_v1.md').write_text(report,encoding='utf-8',newline='\n')
        print(json.dumps(dict(status='GENERATION_COMPLETE_FREEZE_COMMIT_REQUIRED',terminals=800,successes=sum(t['target_evasion_success'] for t in terminals))),flush=True)
    except BaseException as exc:
        p.publish(p.PRIVATE/'interruption_v1.json',dict(status='INTERRUPTED_OR_FAILED',implementation_commit=implementation,
            completed_parents=len(terminals),error_type=type(exc).__name__,error=str(exc),accepted_terminal_manifest_exists=(p.OUT/'r2_dmb_terminal_manifest_v1.json').exists()))
        raise


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--generate',action='store_true',required=True)
    parser.parse_args()
    run()
