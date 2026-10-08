"""Frozen core/cluster bootstrap plus read-only paired and operator summaries."""

import csv
from collections import Counter
import statistics

import numpy as np

from detection_service.research_protocol import r2_dmb_predeclare as p,r2_dmb_design as d,r2_dmb_transfer_run as scoring
from detection_service.research_protocol import protocol_lock,protocol_patch_001
from detection_service.research_protocol.core_metrics import evaluate_core
from detection_service.research_protocol.metric_types import rate
from detection_service.research_protocol.uncertainty import BootstrapConfig,Interval,make_plan,validate_plan,bootstrap_metrics
from detection_service.research_protocol.regime import create_manifest,require
from detection_service.research_protocol.operating_policy import native_prediction

IDS=('ds_v2','dm_b_v1','dg_v1')
PATTERNS=tuple(f'{i:03b}' for i in range(8))
NA='NOT_APPLICABLE_ATTACK_ONLY_REGIME'


def joint_transfer_interval(table):
    """Compose the authorized joint/target ratio on the unchanged frozen plan.

    No metric is added to the protocol catalog. Interval validates the existing
    undefined-replicate policy; sampling and quantiles use the frozen config.
    """
    config=BootstrapConfig(unit='LINEAGE_CLUSTERED',domain='VALID_TARGET_ATTEMPTS',target_detector='D_M-B')
    require(all(r.target_detector=='D_M-B' and r.valid_attack_attempt is True and r.truth_label==1 for r in table.rows),'JOINT_TARGET_DOMAIN_REQUIRED')
    plan=validate_plan(table,config,make_plan(table,config))
    rows=table.rows
    valid=[]
    for indexes in plan.resamples:
        denominator=sum(rows[i].decisions[1]==0 for i in indexes)
        if denominator:
            valid.append(sum(rows[i].decisions==(0,0,0) for i in indexes)/denominator)
    denominator=sum(r.decisions[1]==0 for r in rows)
    point=sum(r.decisions==(0,0,0) for r in rows)/denominator if denominator else None
    status='OBSERVED_UNDEFINED' if point is None else 'UNSTABLE_DENOMINATOR' if 100*len(valid)<95*config.replicates else 'ESTIMATED'
    endpoints=np.quantile(valid,[.025,.975],method=config.quantile_method) if status=='ESTIMATED' else (None,None)
    interval=Interval(metric_id='derived_joint_transfer/dm_b_v1/ds_v2_and_dg_v1',point_estimate=point,
        ci_lower=float(endpoints[0]) if endpoints[0] is not None else None,ci_upper=float(endpoints[1]) if endpoints[1] is not None else None,
        replicates_requested=config.replicates,replicates_valid=len(valid),replicates_invalid=config.replicates-len(valid),status=status)
    return dict(definition='All-three misses / successful D_M-B evasions; derived ratio, not a protocol-catalog mutation.',
        interval=interval.model_dump(mode='json'),plan_sha=plan.plan_sha,config=config.model_dump(mode='json'))


def source_table(manifest,records,policy,source):
    selected=[s for s in manifest.samples if s.source==source]
    ids={s.sample_id for s in selected}
    parent_ids={s.parent_sample_id for s in selected}
    payload=manifest.model_dump(mode='json')
    for key in ('sample_count','attack_count','benign_count','experiment_id','manifest_hash'):
        payload.pop(key)
    payload.update(samples=[s.model_dump(mode='json') for s in selected],
        external_parents=[r for r in payload['external_parents'] if r['sample_id'] in parent_ids],
        dataset_sources=[r for r in payload['dataset_sources'] if r['source']==source])
    subset=create_manifest(**payload)
    return scoring.aligned(subset,[r for r in records if r.sample_id in ids],policy)


def describe(rows,decisions):
    successes=[r for r in rows if r['target_evasion_success']]
    n=len(successes)
    patterns=Counter(''.join(str(1-v) for v in decisions[r['sample_id']]) for r in successes)
    counts={detector:sum(decisions[r['sample_id']][i]==0 for r in successes) for i,detector in enumerate(IDS) if i!=1}
    return dict(seed_count=len(rows),target_evasion_count=n,target_evasion_rate=rate(n,len(rows)).model_dump(mode='json'),
        etr_ds=rate(counts['ds_v2'],n).model_dump(mode='json'),etr_dg=rate(counts['dg_v1'],n).model_dump(mode='json'),
        joint_transfer=rate(patterns['111'],n).model_dump(mode='json'),
        successful_evasion_patterns={key:patterns[key] for key in PATTERNS},
        median_baseline_score=statistics.median(r['baseline_raw_score'] for r in rows) if rows else None,
        median_terminal_score=statistics.median(r['terminal_raw_score'] for r in rows) if rows else None,
        median_score_reduction=statistics.median(r['baseline_raw_score']-r['terminal_raw_score'] for r in rows) if rows else None,
        median_unique_queries=statistics.median(r['unique_model_queries'] for r in rows) if rows else None,
        terminal_selections=len(rows),success_proportion=rate(n,len(rows)).model_dump(mode='json'))


def analyze():
    prediction_commit=p.committed(p.OUT/'r2_dmb_prediction_manifest_v1.json')
    require((p.OUT/'r2_dmb_predictions_v1.csv').read_bytes()==p.git('show',prediction_commit+':artifacts/research_protocol/r2_dmb/r2_dmb_predictions_v1.csv'),'PREDICTIONS_NOT_COMMITTED')
    p.preserved()
    prediction_metadata=p.files.read_json(p.OUT/'r2_dmb_prediction_manifest_v1.json')
    require(p.files.sha(p.OUT/'r2_dmb_predictions_v1.csv')==prediction_metadata['prediction_sha256'],'PREDICTION_HASH_DRIFT')
    value=scoring.manifest()
    policy=scoring.verified_policy()
    records=scoring.read_predictions(policy)
    table=scoring.aligned(value,records,policy)
    bundle=protocol_patch_001.evaluate_official(protocol_lock.ExperimentRequest(manifest=value,bootstrap_unit='LINEAGE_CLUSTERED'),
        tuple(native_prediction(r) for r in records))
    require(bundle.core_metrics==evaluate_core(table),'R2_CORE_RECONSTRUCTION_CONFLICT')
    terminals=p.files.read_json(p.OUT/'r2_dmb_terminal_manifest_v1.json')['terminals']
    by_id={r['sample_id']:r for r in terminals}
    decisions={r.sample_id:r.decisions for r in table.rows}
    require(all((decisions[r['sample_id']][1]==0)==r['target_evasion_success'] for r in terminals),'TARGET_RESCORE_SUCCESS_CONFLICT')
    summary=describe(terminals,decisions)
    joint=joint_transfer_interval(table)
    target=next(r for r in bundle.core_metrics.evasion_transfer.targets if r.target_detector==d.DETECTOR_ID)
    require(target.target_evasion_count==summary['target_evasion_count'] and target.valid_attempt_count==800,'TARGET_DENOMINATOR_CONFLICT')
    for row in target.transfers:
        require(row.etr.model_dump(mode='json')==summary['etr_ds' if row.transfer_detector=='ds_v2' else 'etr_dg'],'TRANSFER_FORMULA_CONFLICT')
    sources={}
    for source in sorted({r['source'] for r in terminals}):
        selected=[r for r in terminals if r['source']==source]
        sub=source_table(value,records,policy,source)
        config=BootstrapConfig(unit='LINEAGE_CLUSTERED',domain='VALID_TARGET_ATTEMPTS',target_detector='D_M-B')
        names=('target/dm_b_v1/evasion','transfer/dm_b_v1/ds_v2/etr','transfer/dm_b_v1/dg_v1/etr')
        intervals=bootstrap_metrics(sub,names,config)
        sources[source]={**describe(selected,decisions),'lineage_count':len({r['lineage_id'] for r in selected}),
            'uncertainty':intervals.model_dump(mode='json'),'joint_transfer_uncertainty':joint_transfer_interval(sub),
            'most_successful_operator':Counter(r['mechanism'] for r in selected if r['target_evasion_success']).most_common(),
            'causal_comparison':False}
    mechanisms=(*d.OPERATORS,'BENIGN_CONTEXT_PADDING',*d.DESIGN['global_operators'],'UNCHANGED')
    operators={op:describe([r for r in terminals if r['mechanism']==op],decisions) for op in mechanisms}
    parent_ids={r['parent_sample_id'] for r in terminals}
    original={}
    with (p.R1/'r1_predictions_v1.csv').open(encoding='utf-8',newline='') as stream:
        for row in csv.DictReader(stream):
            if row['sample_id'] in parent_ids:
                require(row['status']=='OK','R1_PARENT_NON_OK')
                original[(row['sample_id'],row['detector_id'])]=row
    require(len(original)==2400,'INCOMPLETE_R1_PARENT_JOIN')
    child={(r.sample_id,r.detector_id):r for r in records}
    def transitions(selected):
        result={detector:dict(catch_to_catch=0,catch_to_miss=0,miss_to_catch=0,miss_to_miss=0) for detector in IDS}
        for r in selected:
            for i,detector in enumerate(IDS):
                before=int(original[(r['parent_sample_id'],detector)]['operational_binary_prediction'])
                after=decisions[r['sample_id']][i]
                key=('catch' if before else 'miss')+'_to_'+('catch' if after else 'miss')
                result[detector][key]+=1
        return result
    paired=dict(overall=transitions(terminals),by_source={s:transitions([r for r in terminals if r['source']==s]) for s in sources},
        by_operator={op:transitions([r for r in terminals if r['mechanism']==op]) for op in mechanisms},
        mapping='One authoritative R1 parent per terminal; same frozen operational policy; descriptive paired transitions, no causal or significance claim.')
    coverage={}
    for detector in IDS:
        observations=[]
        for r in terminals:
            before=original[(r['parent_sample_id'],detector)]
            after=child[(r['sample_id'],detector)]
            observations.append(dict(sample_id=r['sample_id'],parent_sample_id=r['parent_sample_id'],source=r['source'],mechanism=r['mechanism'],
                target_evasion_success=r['target_evasion_success'],parent_input_tokens=int(before['input_tokens']),
                child_input_tokens=after.input_tokens,parent_tokens_analyzed=int(before['tokens_analyzed']),child_tokens_analyzed=after.tokens_analyzed,
                parent_excluded_tokens=int(before['input_tokens'])-int(before['tokens_analyzed']),child_excluded_tokens=after.input_tokens-after.tokens_analyzed,
                parent_truncated=before['truncated']=='true',child_truncated=after.truncated))
        coverage[detector]=dict(rows=observations,terminal_truncated_count=sum(r['child_truncated'] for r in observations),
            parent_to_child_truncation_increases=sum(r['child_truncated'] and not r['parent_truncated'] for r in observations),
            successful_evasions_with_new_truncation=sum(r['target_evasion_success'] and r['child_truncated'] and not r['parent_truncated'] for r in observations),
            successful_evasions_without_new_truncation=sum(r['target_evasion_success'] and not(r['child_truncated'] and not r['parent_truncated']) for r in observations),
            successful_evasions_with_more_excluded_tokens=sum(r['target_evasion_success'] and r['child_excluded_tokens']>r['parent_excluded_tokens'] for r in observations),
            successful_evasions_with_more_input_tokens=sum(r['target_evasion_success'] and r['child_input_tokens']>r['parent_input_tokens'] for r in observations),
            successful_evasions_unchanged_coverage=sum(r['target_evasion_success'] and r['child_input_tokens']==r['parent_input_tokens'] and r['child_tokens_analyzed']==r['parent_tokens_analyzed'] and r['child_truncated']==r['parent_truncated'] for r in observations))
    core=bundle.core_metrics.model_dump(mode='json')
    outputs=dict(r2_dmb_result_bundle_v1=bundle.model_dump(mode='json'),
        r2_dmb_transfer_metrics_v1={**summary,'canonical_target':target.model_dump(mode='json'),'joint_transfer_uncertainty':joint},
        r2_dmb_common_mode_v1=core['common_mode'],r2_dmb_failure_patterns_v1=dict(**core['failure_patterns'],recovery=core['recovery'],
            success_subset_patterns=summary['successful_evasion_patterns']),r2_dmb_parent_child_transitions_v1=paired,
        r2_dmb_source_analysis_v1=sources,r2_dmb_operator_analysis_v1=operators,r2_dmb_coverage_analysis_v1=dict(detectors=coverage,
            interpretation='Token fragmentation and truncation associations only; reversible preservation does not prove downstream instruction execution.'),
        r2_dmb_uncertainty_v1=dict(canonical_intervals=[u.model_dump(mode='json') for u in bundle.uncertainty],
            derived_joint_transfer=joint,source_intervals={s:r['uncertainty'] for s,r in sources.items()},
            caution='Inherited 97 lineages, including one 400-row InjecAgent cluster; source-level InjecAgent CI is degenerate, not independent-case confidence. Undefined replicate rules unchanged.'),
        r2_dmb_attack_only_guard_v1=dict(FPR=NA,ROC_AUC=NA,AP=NA,benign_count=0))
    for name,data in outputs.items():
        p.publish(p.OUT/(name+'.json'),data)
    p.publish(p.OUT/'r2_dmb_analysis_provenance_v1.json',dict(status='PASS',prediction_commit=prediction_commit,
        protocol_patch_id=protocol_patch_001.PATCH_ID,protocol_patch_sha256=p.files.sha(p.ROOT/protocol_patch_001.ARTIFACT),
        freeze_commit=prediction_metadata['freeze_commit'],source_head=d.SOURCE_HEAD,
        sha256={path.name:p.files.sha(path) for path in p.OUT.glob('*.json') if path.name!='r2_dmb_analysis_provenance_v1.json'},
        post_generation_adaptation=False,detector_training=False,threshold_changes=False,R3_started=False,verifier_started=False,Cycle2='DEFERRED'))
    print(p.files.manifest_bytes(dict(status='R2_ANALYSIS_COMPLETE',summary=summary,common=core['common_mode']['all_three_jfn'])).decode(),flush=True)


if __name__=='__main__':
    analyze()
