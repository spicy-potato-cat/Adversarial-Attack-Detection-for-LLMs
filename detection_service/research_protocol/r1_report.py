"""Render R1 evidence without changing membership, metrics or policies."""

import json
from detection_service.research_protocol import r1_corpus as c, r1_analysis as analysis, r1_scoring as scoring, release_packaging


def read(name):
    return c.files.read_json(c.OUT/(name+'_v1.json'))


def percentage(value):
    return 'UNDEFINED' if value is None else f'{100*value:.3f}%'


def table(headers,rows):
    return '\n'.join(['| '+' | '.join(headers)+' |','|'+'|'.join(['---']*len(headers))+'|',
                      *['| '+' | '.join('UNDEFINED' if v is None else str(v) for v in row)+' |' for row in rows]])+'\n'


def reference_file(name):
    inventory=c.files.read_json(c.ROOT/release_packaging.INVENTORY)
    rows=[r for r in inventory['records'] if r['artifact_path'].endswith('/'+name)]
    assert len(rows)==1
    row=rows[0]
    assert c.files.sha(c.ROOT/row['artifact_path'])==row['sha256']
    return c.files.read_json(c.ROOT/row['artifact_path']),row


def render():
    manifest=scoring.input_manifest()
    score=read('r1_prediction_manifest')
    bundle=read('r1_result_bundle')
    core=bundle['core_metrics']
    ranking=read('r1_ranking_metrics')['detectors']
    frontier=read('r1_descriptive_frontier')['detectors']
    families=read('r1_family_analysis')
    coverage=read('r1_token_coverage')['detectors']
    comparison=read('r0_r1_comparison')
    r0,reference=analysis.r0_reference()
    r0_ranking,rank_reference=reference_file('r0_score_metrics_reproduction_v1.json')
    r0_frontier,frontier_reference=reference_file('r0_descriptive_frontier_v1.json')
    intervals={v['metric_id']:v for group in bundle['uncertainty'] for v in group['intervals']}
    def ci(key):
        row=intervals[key]
        return '['+percentage(row['ci_lower'])+', '+percentage(row['ci_upper'])+']' if row['status']=='ESTIMATED' else row['status']
    sections=[]
    def section(number,title,body):
        sections.append(f'## {number}. {title}\n\n'+body.strip()+'\n')
    section(1,'R1 Dataset Constitution',
        f'Gate B PASS. Dataset `{manifest.dataset_id}`: 1,800 rows, 800 attacks and 1,000 benign inputs. '+
        '400 LLMail-Inject explicit attack attempts, 400 InjecAgent BASE responses (200 direct-harm, 200 data-stealing), and 1,000 OR-Bench hard-benign prompts. '+
        f'Pre-scoring freeze commit `{score["gate_b_commit"]}`. Dataset manifest file SHA-256 `{score["manifest_sha256"]}`. '
        'No detector score informed source selection or sampling. All sources are cleared with local-only restriction; raw text is excluded from Git.')
    section(2,'Unseen-Source Justification','No R1 source was used in the accepted BASE_TRAIN, CALIBRATION or VALIDATION constitution (deepset Prompt Injection and Do-Not-Answer). '+
        'LLMail is human/adaptive indirect injection against disclosed upstream defenses; InjecAgent is textual external/tool injection; OR-Bench is a model-selected over-defence shift. '+
        'This is source-disjoint project development evaluation, not proof of unseen foundation-model pretraining. LLMail is not a new R2 attack against this stack. '
        'See [source clearance](R1_SOURCE_CLEARANCE_v1.md) and its exact revision/license/mirror evidence.')
    section(3,'Contamination Audit','All 23,380 candidates were compared with all 1,601 development rows. Raw exact and approved N1 matches: zero. '+
        'Source-native IDs are not comparable across these source domains; no documented shared development lineage, hidden reuse UNKNOWN. '+
        'Approved lexical threegram Jaccard census at 0.7/0.8/0.9 found one unselected LLMail candidate at 0.97123; selected near matches: zero. '+
        'Eleven multi-team LLMail candidates were excluded before score-blind sampling. No new semantic threshold. Originals were not modified.')
    section(4,'Lineage Structure','1,097 lineage components: 96 hashed LLMail teams, one 400-row InjecAgent transitive attacker/user dependency component, and 1,000 OR singleton fallbacks. '+
        'LLMail max five selected prompts per team; all 17 InjecAgent user tools represented. Source relations and N1 duplicates are unioned conservatively. '+
        'LINEAGE_CLUSTERED was frozen pre-score. The giant InjecAgent cluster limits pooled inference and forbids pretending 400 independent cases. OR singleton fallback does not prove independence.')
    thresholds=(0.5585373573968287,0.0004967087297700347,0.21291141211986545)
    section(5,'Frozen Detector Identities',table(['Detector','Frozen Identity','Operational Score','Threshold'],[
        ['D_S','ds_v2 + ds_v2_cal_v1','calibrated_score',thresholds[0]],['D_M-B','dm_b_v1 + frozen calibration','raw_score',thresholds[1]],
        ['D_G','Meta Prompt Guard 2 22M; 11614a155199674a0a95e6602d6ab0417b790ed0','raw_score',thresholds[2]]])+
        'Inclusive >=, exact frozen IDs; native votes remain separate. D_S accepted archive provenance/equivalence is preserved. All runtimes use existing frozen loaders, revisions, tokenization, windows and weights. No resource/device overrides.')
    section(6,'Operational Performance',table(['Detector','TP','FN','FP','TN','Accuracy','Precision','Recall','Specificity','F1','FPR','FNR'],[
        [r['detector_id'],r['tp'],r['fn'],r['fp'],r['tn'],*[percentage(r[k]['value']) for k in ('accuracy','precision','recall','specificity','f1','fpr','fnr')]] for r in core['individual']['detectors']])+
        f'Gate C PASS: {score["coverage"]["received_predictions"]}/5,400 canonical predictions, no missing, duplicate or non-OK rows. '
        'After an interrupted invocation, the unchanged resume-safe scorer validated all three complete native journals and finalized the receipt without new inference. '
        'The receipt start/completion timestamps and runtime describe that resumed finalization invocation, not total original inference time; native per-row latencies are preserved. '
        'Operational thresholds are transported from calibration; 3% calibration budget is not a guarantee of 3% R1 FPR.')
    section(7,'Descriptive Frontier',table(['Detector','Budget','Raw Threshold','Recall','Attained FPR','TP','FN','FP','TN'],[
        [detector,percentage(p['budget']),p['threshold'],percentage(p['recall']),percentage(p['fpr']),p['tp'],p['fn'],p['fp'],p['tn']]
        for detector,row in frontier.items() for p in row['points']])+
        'SECONDARY descriptive_frontier_v1 only. Whole tied blocks; no threshold or operational decision changed.')
    section(8,'Ranking Metrics',table(['Detector','R0 ROC-AUC','R1 ROC-AUC','R0 AP','R1 AP'],[
        [d,r0_ranking[d]['roc_auc'],r['roc_auc'],r0_ranking[d]['average_precision'],r['average_precision']] for d,r in ranking.items()])+
        'Frozen Phase-13 whole-tied-block ROC-AUC and Average Precision, raw-score basis. AP changes are prevalence-sensitive: R0 attack prevalence 183/1135; R1 800/1800. '+
        'R0 ranking metadata is loaded through the release inventory, not reconstructed manually.')
    section(9,'Pairwise Shared Failure',table(['Pair','Shared FN','JFN','95% CI JFN','Independence Reference','EJF','FN Jaccard'],[
        [p['left_detector']+'/'+p['right_detector'],p['shared_fn_count'],percentage(p['jfn']['value']),ci('pair/'+p['left_detector']+'/'+p['right_detector']+'/jfn'),
         percentage(p['independence_reference']['value']),percentage(p['ejf']['value']),percentage(p['fn_jaccard']['value'])] for p in core['common_mode']['pairs']])+
        'Independence products are references, not assumptions. EJF is joint failure minus the product of marginal FNRs.')
    section(10,'All-Three Failure',f'All-three FN: {core["common_mode"]["all_three_fn_count"]}/800. JFN: '+percentage(core['common_mode']['all_three_jfn']['value'])+'. 95% CI: '+ci('all_three/jfn')+'.')
    section(11,'Failure Patterns',table(['Miss Pattern S/M/G','Attack Count','Attack Rate'],[
        [p['pattern_id'],p['count'],percentage(p['attack_rate']['value'])] for p in core['failure_patterns']['patterns']])+
        '0 means caught; 1 means missed. Thus 000 is caught by all and 111 is missed by all. No ensemble or router decision is created.')
    section(12,'Unique Catches',table(['Detector','Unique Catch Count','Rate / All 800 Attacks','95% CI'],[
        [r['detector_id'],r['unique_catch_count'],percentage(r['unique_catch_rate']['value']),ci('recovery/'+r['detector_id']+'/unique_catch_rate')] for r in core['recovery']['detectors']]))
    section(13,'Conditional Recovery',table(['Detector','Recovered','Both Others Miss','Recovery','95% CI / Status'],[
        [r['detector_id'],r['unique_catch_count'],r['both_others_miss_count'],percentage(r['conditional_recovery']['value']),ci('recovery/'+r['detector_id']+'/conditional_recovery')] for r in core['recovery']['detectors']])+
        'Undefined/unstable denominators remain explicit; these are conditional descriptive rates, not verifier performance.')
    source_rows=[]
    for source,group in families['groups'].items():
        sub=group['core_metrics']
        source_rows.append([source,group['sample_count'],group['lineage_count'],*[percentage(d['fnr']['value']) for d in sub['individual']['detectors']],
            *[percentage(p['jfn']['value']) for p in sub['common_mode']['pairs']],sub['common_mode']['all_three_fn_count'],percentage(sub['common_mode']['all_three_jfn']['value'])])
    section(14,'Family-Conditioned Analysis',table(['Source / High-Level Family','N','Lineages','S FNR','M FNR','G FNR','S/M JFN','S/G JFN','M/G JFN','All FN','All JFN'],source_rows)+
        '\nWorst-family/source observations:\n\n'+table(['Metric','Worst Source','N','Rate'],[[k,v['source'],v['n'],percentage(v['value'])] for k,v in families['worst_family_or_source'].items()])+
        'Source and high-level family coincide here. Both groups have 400 positives; no detailed subtype inference. InjecAgent has only one dependency cluster, so source-level results are descriptive, not independent-case inference. '+
        'Equal-rate worst-source ties are listed deterministically, not as uniquely worse sources. '+
        'Complete source-conditioned eight-pattern and pairwise accounting is in r1_family_analysis_v1.json. n<20 would be LOW_SUPPORT_DESCRIPTIVE_ONLY; no such attack group here.')
    section(15,'Uncertainty','Production defaults unchanged: 1,000 replicates, PCG64 seed 1701, 95% percentile intervals, LINEAGE_CLUSTERED, attack and benign domains separate. '+
        'All requested FNR/FPR, pairwise/three-way JFN, unique catch and recovery intervals are retained with their valid-replicate statuses.\n\n'+
        table(['Detector','FNR 95% CI','FPR 95% CI'],[[r['detector_id'],ci('individual/'+r['detector_id']+'/fnr'),ci('individual/'+r['detector_id']+'/fpr')] for r in core['individual']['detectors']])+
        'The 400-row InjecAgent cluster is sampled whole and can be absent or repeated; pooled source mixture and denominators vary. These conditional empirical CIs do not account for training-set, unseen-source or foundation-model exposure uncertainty. Singleton OR fallback is a modelling limitation.')
    keys=[k for k in comparison['metrics'] if k.endswith(('/fnr','/fpr','/jfn','/ejf','/unique_catch_rate','/conditional_recovery'))]
    section(16,'R0 Versus R1 Comparison',table(['Metric','R0','R1','Delta Fraction','Delta Percentage Points'],[
        [k,comparison['metrics'][k]['reference'],comparison['metrics'][k]['current'],comparison['metrics'][k]['delta_fraction'],comparison['metrics'][k]['delta_percentage_points']] for k in keys])+
        'Every delta is R1 minus R0. Descriptive and unpaired; no sample/lineage correspondence, paired significance test or causal attribution. '+comparison['limitation'])
    drift=[]
    for d,row in ranking.items():
        old=next(r for r in r0.core_metrics.individual.detectors if r.detector_id==d)
        new=next(r for r in core['individual']['detectors'] if r['detector_id']==d)
        old_front=next(p for p in r0_frontier['points'][d] if p['budget']==.03)
        new_front=next(p for p in frontier[d]['points'] if p['budget']==.03)
        drift.append([d,new['fnr']['value']-old.fnr.value,new['fpr']['value']-old.fpr.value,row['roc_auc']-r0_ranking[d]['roc_auc'],new_front['recall']-old_front['recall']])
    section(17,'Operating-Point Drift Versus Ranking Degradation',table(['Detector','Operational FNR Delta','Operational FPR Delta','ROC-AUC Delta','3% Frontier Recall Delta'],drift)+
        'Frozen policy drift and discrimination are distinct measurements. A low transported threshold can raise FPR without proving poor ranking; a falling ROC-AUC/frontier supports discrimination degradation. '+
        'AP also depends on changed prevalence. Source mix, input length/coverage and OOF-versus-final-model provenance prevent isolating a single cause; no calibration refit is proposed from R1.')
    section(18,'Limitations','Source-attempt labels may contain judge noise; hard benign labels are benchmark labels, not universal harmlessness. LLMail excludes uncertain labels/multi-team keys and uses only phase-2 files. '+
        'Model pretraining and hidden source reuse are UNKNOWN. Large InjecAgent dependency cluster and generated OR singleton fallback limit uncertainty. '+
        'R0 is historical development OOF for S/M; R1 uses final models and a different source/label/length mix. Source/family analysis is not a controlled causal comparison. '+
        'Text-only tool-response screening is not end-to-end agent safety or attack-success measurement. Token coverage/truncation is frozen, not repaired after outcomes.\n\n'+
        table(['Detector','Truncated Rows','Max Input Tokens'],[[d,r['truncated_rows'],r['max_input_tokens']] for d,r in coverage.items()])+
        'Raw prompts and participant IDs remain local-only. No protected/final benchmark payload was used.')
    joint=comparison['metrics']['all_three/jfn']
    recovery_changes={k:v['delta_fraction'] for k,v in comparison['metrics'].items() if k.endswith('/unique_catch_rate')}
    observations=[]
    for row in core['individual']['detectors']:
        detector=row['detector_id']
        point=next(p for p in frontier[detector]['points'] if p['budget']==.03)
        observations.append(
            f'{detector}: operational recall {percentage(row["recall"]["value"])} and FPR {percentage(row["fpr"]["value"])}; '
            f'raw ROC-AUC {ranking[detector]["roc_auc"]:.6f}; descriptive 3%-budget recall {percentage(point["recall"])} '
            f'at attained FPR {percentage(point["fpr"])}.')
        if ranking[detector]['roc_auc']==1.0:
            observations.append('Perfect empirical ranking is confined to this curated source mixture. '
                'It is compatible with operational false positives under a transported threshold and does not establish general unseen-attack robustness.')
        if ranking[detector]['roc_auc']<.5:
            observations.append('ROC-AUC below 0.5 and the weak low-FPR frontier indicate poor discrimination in the frozen score direction on this population, '
                'not just transported-threshold drift. This does not establish its cause; score direction, model and policy remain unchanged.')
    section(19,'Research Interpretation',f'All-three JFN moved from {percentage(joint["reference"])} to {percentage(joint["current"])} '+
        f'({joint["delta_percentage_points"]:+.3f} percentage points). '+
        ('This is increased shared failure in this frozen R1 population.' if joint['delta_fraction']>0 else 'There is no observed increase in all-three shared failure in this R1 population.')+
        ' Pairwise EJF and exclusive-catch changes must be read alongside marginal errors, ranking and source-conditioned results; a single changed JFN does not establish diversity collapse. '+
        'Unique-catch changes: '+json.dumps(recovery_changes,sort_keys=True)+'. No significance or broad safety claim is made.\n\n'+
        '\n\n'.join(observations)+'\n\n'+
        'Zero all-three misses here is driven by D_M-B catching every observed attack; it is not evidence that every stack member adds exclusive coverage. '
        'D_S and D_G have no exclusive catches in this population. Zero-event percentile intervals do not bound future unseen-source risk.')
    section(20,'No Post-R1 Adaptation','No detector, model, feature, tokenizer, preprocessing, reference LM, calibration, operational threshold, metric definition, bootstrap definition, prediction semantics, regime semantics, R0 evidence or protocol lock was changed after observing R1. '+
        'No retraining, fitting, targeted attack generation, protected/final evaluation, router, verifier, R2 or R3 was begun. Cycle 2 remains DEFERRED. '+
        'Gate-B and Gate-C commits remain separate. Full artifact/test/hash receipts accompany acceptance.')
    content='# R1_SHIFTED_UNSEEN Results v2\n\nStatus: **COMPLETE**, OPERATIONAL_FIXED_V1. This prospectively supersedes the unchanged v1 blocked report.\n\n'+'\n'.join(sections)
    path=c.ROOT/'reviews/R1_SHIFTED_UNSEEN_RESULTS_v2.md'
    data=content.encode('utf-8')
    assert not path.exists() or path.read_bytes()==data
    if not path.exists():
        with path.open('xb') as stream:
            stream.write(data)
    c.publish(c.OUT/'r1_ranking_reference_bindings_v1.json',dict(r0_ranking_reference=rank_reference,r0_frontier_reference=frontier_reference,r0_operational_reference=reference,report_sha256=c.sha(data)))
    print(str(path),c.sha(data))


if __name__=='__main__':
    render()
