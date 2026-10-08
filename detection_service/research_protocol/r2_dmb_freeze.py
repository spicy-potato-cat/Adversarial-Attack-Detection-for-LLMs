"""Validate every private terminal against the metadata-only R2 freeze."""

from collections import Counter
import json

from detection_service.research_protocol import r2_dmb_design as d,r2_dmb_predeclare as p
from detection_service.research_protocol.r2_dmb_generator import inverse,sha,require


def regime_manifest():
    from detection_service.research_protocol.regime import create_manifest
    original=p.files.read_json(p.R1/'r1_dataset_manifest_v1.json')
    generator=p.files.read_json(p.OUT/'r2_dmb_generator_manifest_v1.json')
    terminals=p.files.read_json(p.OUT/'r2_dmb_terminal_manifest_v1.json')['terminals']
    parent_rows={s['sample_id']:(i,s) for i,s in enumerate(original['samples'])}
    samples=[]
    parents=[]
    for row in terminals:
        index,source=parent_rows[row['parent_sample_id']]
        child={**source,'sample_id':row['sample_id'],'threat_regime':d.DESIGN['threat_regime'],
            'parent_sample_id':source['sample_id'],'target_detector':d.TARGET,
            'attack_method':'DMB_REVERSIBLE_SEARCH_V1','attack_method_revision':generator['implementation_commit'],
            'generator_type':'RULE_BASED','generator_model':None,'generator_system':'DMB_REVERSIBLE_SEARCH_V1',
            'generator_revision':generator['implementation_commit'],'generated_sample':True,
            'generation_evaluation_status':'COMPLETED','lineage_provenance_status':'DERIVED_FROM_PARENT',
            'lineage_justification':'Inherited unchanged from frozen R1 parent; reversible detector-evasion descendant.',
            'attack_success_definition':'TARGET_OPERATIONAL_MISS_V1','attack_success':row['target_evasion_success'],
            'valid_attack_attempt':True,'created_at':generator['completed_at']}
        samples.append(child)
        parents.append({**{k:source[k] for k in ('sample_id','lineage_id','dataset_id','dataset_revision','source','source_native_id','provenance_status')},
            'evidence_role':'r1_parent_manifest','evidence_locator':'/samples/'+str(index)})
    payload={k:v for k,v in original.items() if k not in ('experiment_id','manifest_hash','sample_count','attack_count','benign_count')}
    payload.update(dataset_id='R2-DMB-001',dataset_revision=p.files.sha(p.OUT/'r2_dmb_terminal_manifest_v1.json'),
        threat_regime=d.DESIGN['threat_regime'],dataset_source='FROZEN_R1_ATTACK_PARENTS',
        dataset_source_revision=p.files.sha(p.OUT/'r2_dmb_terminal_manifest_v1.json'),samples=samples,
        dataset_sources=[s for s in original['dataset_sources'] if s['source'] in {r['source'] for r in samples}],
        created_at=generator['completed_at'],external_parents=parents,
        evidence=[dict(role=role,path=path.relative_to(p.ROOT).as_posix(),sha256=p.files.sha(path)) for role,path in
            (('r1_parent_manifest',p.R1/'r1_dataset_manifest_v1.json'),('terminal_metadata',p.OUT/'r2_dmb_terminal_manifest_v1.json'),
             ('predeclared_design',p.OUT/'r2_dmb_predeclaration_v1.json'))],
        notes=('Attack-only D_M-B targeted detector-evasion experiment. Validity means reversible text preservation, not downstream jailbreak success.',
            'All 800 parents retained regardless of target evasion; inherited lineages, including one 400-row InjecAgent component.'))
    return create_manifest(**payload)


def validate():
    p.preserved()
    from detection_service.research_protocol.r2_dmb_patch_binding import verified
    verified()
    declaration=p.files.read_json(p.OUT/'r2_dmb_predeclaration_v1.json')
    require(declaration['design']==d.DESIGN,'DESIGN_DRIFT')
    metadata=p.files.read_json(p.OUT/'r2_dmb_generator_manifest_v1.json')
    binding=metadata['private_journal']
    protocol_receipt=metadata['protocol_prequery_receipt']
    require(p.digest(protocol_receipt['path'])==protocol_receipt['sha256'],'PREQUERY_RECEIPT_DRIFT')
    prequery=p.files.read_json(p.ROOT/protocol_receipt['path'])
    require(prequery['authoritative_prior_model_queries']==0,'PRIOR_QUERY_CONFLICT')
    require(prequery['generator_implementation_commit']==metadata['implementation_commit'],'GENERATOR_COMMIT_CONFLICT')
    require(p.digest(binding['path'])==binding['sha256'],'PRIVATE_GENERATION_DRIFT')
    private=[json.loads(line) for line in (p.ROOT/binding['path']).read_bytes().splitlines()]
    terminal=p.files.read_json(p.OUT/'r2_dmb_terminal_manifest_v1.json')
    rows=terminal['terminals']
    require(len(private)==len(rows)==800,'INCOMPLETE_TERMINAL_POPULATION')
    seeds=p.parents()
    texts=p.private_parents()
    require([r['parent_sample_id'] for r in rows]==[r['parent_sample_id'] for r in seeds],'PARENT_ORDER_DRIFT')
    require(len({r['sample_id'] for r in rows})==800,'DUPLICATE_TERMINAL_ID')
    unique=0
    for row,entry,parent in zip(rows,private,seeds):
        require(row==entry['metadata'],'PRIVATE_METADATA_CONFLICT')
        result=entry['private_generation']
        text=result['text']
        original=texts[row['parent_sample_id']]
        require(inverse(text,result['script'])==original.encode('utf-8'),'INVERSE_RECONSTRUCTION_FAILED')
        require(sha(text)==row['terminal_text_sha256'] and sha(original)==row['parent_text_sha256']==parent['parent_text_sha256'],'TERMINAL_OR_PARENT_HASH_CONFLICT')
        require(row['lineage_id']==row['parent_lineage_id']==parent['lineage_id'],'LINEAGE_INHERITANCE_CONFLICT')
        require(row['source']==parent['source'] and row['attack_family']==parent['attack_family'],'PARENT_METADATA_CONFLICT')
        require(row['target_detector']==d.TARGET and row['threat_regime']==d.DESIGN['threat_regime'],'TARGET_OR_REGIME_CONFLICT')
        require(row['baseline_decision']==1 and row['baseline_raw_score']>=d.THRESHOLD,'BASELINE_NOT_DETECTED')
        require(abs(row['baseline_raw_score']-parent['baseline_raw_score'])<=1e-12,'BASELINE_REPLAY_CONFLICT')
        require(row['terminal_raw_score']==result['terminal']['raw_score'],'TERMINAL_SCORE_CONFLICT')
        require(row['terminal_decision']==int(row['terminal_raw_score']>=d.THRESHOLD),'TARGET_DECISION_CONFLICT')
        require(row['target_evasion_success']==(row['terminal_raw_score']<d.THRESHOLD),'TARGET_SUCCESS_CONFLICT')
        require(row['inverse_reconstruction'] and row['validity_status']==d.DESIGN['validity'],'INVALID_TERMINAL')
        require(row['original_byte_length']==len(original.encode('utf-8')) and row['terminal_byte_length']==len(text.encode('utf-8')),'BYTE_LENGTH_CONFLICT')
        trace=result['query_trace']
        evaluations=sum(not q['cached'] for q in trace)
        require(evaluations==row['unique_model_queries']<=61 and len(trace)==row['logical_queries'],'QUERY_BUDGET_CONFLICT')
        require(len({q['candidate_id'] for q in trace})==evaluations,'QUERY_CACHE_CONFLICT')
        require(row['saliency_span_count']<=16 and row['ranked_span_count']<=8,'SPAN_BUDGET_CONFLICT')
        require(any(q['candidate_id']==row['terminal_text_sha256'] and q['raw_score']==row['terminal_raw_score'] for q in trace),'TERMINAL_NOT_QUERIED')
        require(row['baseline_coverage']=={k:result['baseline'][k] for k in ('input_tokens','tokens_analyzed','truncated')},'BASELINE_COVERAGE_CONFLICT')
        require(row['terminal_coverage']=={k:result['terminal'][k] for k in ('input_tokens','tokens_analyzed','truncated')},'TERMINAL_COVERAGE_CONFLICT')
        unique+=evaluations
    counts=metadata['generation_call_counts']
    require(counts['D_S']==counts['D_G']==counts['ensemble']==0,'BLOCKED_R2_TARGET_ISOLATION')
    require(counts['D_M_B']==unique==metadata['target_generation_queries'],'QUERY_TOTAL_CONFLICT')
    require(metadata['inverse_passed']==800 and metadata['inverse_failed']==metadata['generation_errors']==metadata['invalid_utf8']==0,'INVALID_GENERATION')
    result=dict(artifact_version='r2_dmb_freeze_acceptance_v1',status='PASS',parents=800,terminals=800,
        inverse_passed=800,inverse_failed=0,invalid_utf8=0,payload_deletion_violations=0,query_budget_violations=0,
        generation_call_counts=counts,unique_target_queries=unique,max_target_queries=max(r['unique_model_queries'] for r in rows),
        lineage_count=len({r['lineage_id'] for r in rows}),source_counts=dict(Counter(r['source'] for r in rows)),
        implementation_commit=metadata['implementation_commit'],predeclaration_commit=metadata['predeclaration_commit'],
        sha256={path.name:p.files.sha(path) for path in p.OUT.glob('*.json') if path.name!='r2_dmb_freeze_acceptance_v1.json'})
    return result,private


def transfer_gate():
    receipt=p.OUT/'r2_dmb_freeze_acceptance_v1.json'
    commit=p.committed(receipt)
    require(not p.git('status','--porcelain').decode().strip(),'BLOCKED_R2_TARGET_ISOLATION:DIRTY_TREE')
    stored=p.files.read_json(receipt)
    for name,expected in stored['sha256'].items():
        path=p.OUT/name
        require(p.files.sha(path)==expected and path.read_bytes()==p.git('show',commit+':'+path.relative_to(p.ROOT).as_posix()),'FROZEN_TERMINAL_DRIFT')
    result,private=validate()
    # Later prediction/analysis artifacts are not part of the original freeze receipt.
    result['sha256']=stored['sha256']
    require(result==stored,'FREEZE_ACCEPTANCE_CONFLICT')
    return commit,private


if __name__=='__main__':
    manifest=regime_manifest()
    p.publish(p.OUT/'r2_dmb_regime_manifest_v1.json',manifest.model_dump(mode='json'))
    result,_=validate()
    p.publish(p.OUT/'r2_dmb_freeze_acceptance_v1.json',result)
    print(result)
