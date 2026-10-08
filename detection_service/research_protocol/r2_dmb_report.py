"""Read-only R2 research report; no generator/model imports or adaptation."""

import json

from detection_service.research_protocol import r2_dmb_predeclare as p
from detection_service.research_protocol.regime import require


def read(name):
    return p.files.read_json(p.OUT/(name+'_v1.json'))


def table(headers,rows):
    return '\n'.join(['| '+' | '.join(headers)+' |','|'+'|'.join('---' for _ in headers)+'|',
        *['| '+' | '.join('UNDEFINED' if v is None else str(v) for v in row)+' |' for row in rows]])+'\n'


def code(value):
    return '```json\n'+json.dumps(value,sort_keys=True,indent=2,ensure_ascii=True,allow_nan=False)+'\n```\n'


def render():
    bundle=read('r2_dmb_result_bundle')
    core=bundle['core_metrics']
    summary=read('r2_dmb_transfer_metrics')
    generator=read('r2_dmb_generator_manifest')
    predictions=read('r2_dmb_prediction_manifest')
    source=read('r2_dmb_source_analysis')
    operators=read('r2_dmb_operator_analysis')
    intervals={r['metric_id']:r for group in bundle['uncertainty'] for r in group['intervals']}
    def rate(row):
        return 'UNDEFINED' if row['value'] is None else f"{100*row['value']:.3f}%"
    def ci(key):
        row=intervals[key]
        return f"[{row['ci_lower']}, {row['ci_upper']}] ({row['status']}; {row['replicates_valid']}/{row['replicates_requested']} valid)"
    sections=[]
    def section(number,title,body):
        sections.append(f'## {number}. {title}\n\n'+body.strip()+'\n')
    section(1,'Experiment Objective','R2-DMB-001 measures reversible, D_M-B-directed input-detector evasion and subsequent untargeted transfer. It does not test downstream LLM jailbreak execution.')
    section(2,'Threat Model','Only the frozen D_M-B raw attack probability was observable to generation. No D_S, D_G, ensemble, external API, LLM judge or gradient oracle. No post-outcome generator redesign.')
    section(3,'Frozen Target Detector','D_M-B dm_b_v1; encoder fb53ab8802853c8e4fbdbcd0529f21fc6f459b2b; weight SHA 0bb192d2c468530479fa8ec0786f35d8bf5a8287e4ee401a953292d221736844. '+
        '256-token right-truncated window. Raw attack-class probability >= 0.0004967087297700347 is adversarial (dm_b_v1_op3_raw_v1). Calibration was not substituted into this criterion. All three frozen loaders and operational policies are unchanged.')
    section(4,'Seed Population','Exactly 800 accepted R1 attack parents, all caught by D_M-B: 400 LLMail and 400 InjecAgent BASE. All parents retained regardless of generation success. '+
        '97 inherited lineages: 96 LLMail team components plus one 400-row InjecAgent dependency component. No untargeted-detector selection, cherry-picking or subsampling.')
    section(5,'Target-Isolation Guarantee',code(generator['generation_call_counts'])+
        f"Predeclaration commit `{generator['predeclaration_commit']}`; implementation commit `{generator['implementation_commit']}`; terminal freeze commit `{predictions['freeze_commit']}`. "+
        'Non-target adapters and untargeted scoring/evaluator imports are rejected during the entire generation context. Tests run with that guard. D_S/D_G child scoring started only after the terminal freeze commit and clean-tree gate.')
    section(6,'Attack-Generation Algorithm','Exact tokenizer analyzed-region offsets; standalone ASCII word spans and specified structured-token fallback; deterministic 16-span spacing; x-occlusion saliency; top eight words; four ordered reversible mutations; eight fixed padding candidates; four original-parent global fallbacks. '+
        'Every successful stage evaluates its full specified candidate set before choosing by the predeclared priorities. The predeclared padding-failure rule retains the lowest-scoring padding candidate even if worse than the pre-padding candidate. No random restart or post-hoc search.')
    section(7,'Query Budget',code(dict(maximum_per_parent=61,total_unique=generator['target_generation_queries'],observed_maximum=generator['max_queries'],violations=generator['query_budget_violations'],
        histogram=read('r2_dmb_target_results')['unique_query_histogram']))+'Per-parent exact-string caching avoids duplicate model evaluations; logical and unique queries are retained separately. Generation used the frozen CPU runtime, singleton predictions and configured thread count.')
    section(8,'Attack-Validity Definition','VALID_REVERSIBLE_TEXT_PRESERVING: every terminal edit script inversely reconstructs the exact parent UTF-8 bytes. 800/800 validated; no deletion or semantic rewriting operator. '+
        'This structural definition does not certify model-visible equivalence after tokenization, downstream attack effectiveness, or protected-LLM compromise. Raw prompts, edits and participant identities remain local-only.')
    section(9,'Target-Evasion Results',table(['Baseline detected','Successful evasions','Rate','95% lineage CI'],[[800,summary['target_evasion_count'],rate(summary['target_evasion_rate']),ci('target/dm_b_v1/evasion')]])+
        code({k:summary[k] for k in ('median_baseline_score','median_terminal_score','median_score_reduction','median_unique_queries')}))
    section(10,'Cross-Detector Transfer',table(['Direction','Misses among successful evasions','Denominator','ETR','95% CI'],[
        ['D_M-B to D_S',summary['etr_ds']['numerator'],summary['target_evasion_count'],rate(summary['etr_ds']),ci('transfer/dm_b_v1/ds_v2/etr')],
        ['D_M-B to D_G',summary['etr_dg']['numerator'],summary['target_evasion_count'],rate(summary['etr_dg']),ci('transfer/dm_b_v1/dg_v1/etr')],
        ['D_M-B to BOTH',summary['joint_transfer']['numerator'],summary['target_evasion_count'],rate(summary['joint_transfer']),json.dumps(summary['joint_transfer_uncertainty']['interval'])]])+
        'A zero successful-evasion denominator is UNDEFINED, never zero. ETR includes pre-existing untargeted misses; paired transitions below distinguish new misses from inherited ones.')
    section(11,'Common-Mode Failures',table(['Detector','TP','FN','Recall','FNR'],[[r['detector_id'],r['tp'],r['fn'],rate(r['recall']),rate(r['fnr'])] for r in core['individual']['detectors']])+
        '\n'+table(['Pair','Shared FN','JFN','Independence reference','EJF','FN Jaccard','JFN CI'],[
            [r['left_detector']+'/'+r['right_detector'],r['shared_fn_count'],rate(r['jfn']),r['independence_reference']['value'],r['ejf']['value'],rate(r['fn_jaccard']),ci('pair/'+r['left_detector']+'/'+r['right_detector']+'/jfn')] for r in core['common_mode']['pairs']])+
        f"All-three misses: {core['common_mode']['all_three_fn_count']}/800; JFN {rate(core['common_mode']['all_three_jfn'])}; CI {ci('all_three/jfn')}. "+
        'FPR, ROC-AUC and AP: NOT_APPLICABLE_ATTACK_ONLY_REGIME. No benign denominator or attack-only ranking metric was invented.')
    section(12,'Failure Patterns',table(['Miss pattern S/M/G','Full terminal population','Successful D_M-B evasions'],[
        [r['pattern_id'],r['count'],summary['successful_evasion_patterns'][r['pattern_id']]] for r in core['failure_patterns']['patterns']])+
        '0=CATCH, 1=MISS. Successful target evasions have M=1, so only 010, 011, 110 and 111 can occur.\n\n'+
        table(['Detector','Unique catches','Unique-catch rate','Conditional recovery'],[[r['detector_id'],r['unique_catch_count'],rate(r['unique_catch_rate']),rate(r['conditional_recovery'])] for r in core['recovery']['detectors']]))
    section(13,'Source-Conditioned Results',table(['Source','Seeds','Lineages','Evasions','Target rate','ETR S','ETR G','Joint ETR','Median queries'],[
        [s,r['seed_count'],r['lineage_count'],r['target_evasion_count'],rate(r['target_evasion_rate']),rate(r['etr_ds']),rate(r['etr_dg']),rate(r['joint_transfer']),r['median_unique_queries']] for s,r in source.items()])+
        'Each source artifact includes target and transfer CIs, baseline/terminal medians and operator-success counts. InjecAgent has ONE inherited cluster; its source-specific bootstrap interval is degenerate and does not provide independent-case uncertainty. No causal source comparison.')
    section(14,'Operator-Conditioned Results',table(['Terminal mechanism','Terminal selections','Successes','Success proportion','Median score reduction','ETR S','ETR G'],[
        [op,r['terminal_selections'],r['target_evasion_count'],rate(r['success_proportion']),r['median_score_reduction'],rate(r['etr_ds']),rate(r['etr_dg'])] for op,r in operators.items()])+
        'These are selected-terminal strata, not randomized operator trials. Greedy terminal mechanism names the final accepted operator; earlier accepted edits may coexist. Attempted terminal selections are not all probe trials. Operator analysis did not influence generation.')
    section(15,'Coverage And Truncation',code({s:{k:v for k,v in r.items() if k!='rows'} for s,r in read('r2_dmb_coverage_analysis')['detectors'].items()})+
        'Per-input parent/child tokens, analyzed tokens and excluded tokens are retained in the coverage artifact. More tokens are a tokenizer fragmentation proxy, not proof of semantic change. Truncation association is not a causal explanation of evasion.')
    section(16,'R1 Parent To R2 Child Transitions',code(read('r2_dmb_parent_child_transitions'))+
        'Paired same-parent, same-policy descriptive counts. In particular, transferred misses need not be newly induced: D_G already missed 764/800 R1 parents. No significance or causal claim.')
    section(17,'Uncertainty','Unchanged 1,000-replicate PCG64 seed-1701 95% percentile cluster bootstrap, inherited R1 lineages, valid-only undefined-replicate rule and 95% support requirement. '+
        'Canonical target/transfer/FNR/JFN intervals come directly from the frozen APIs. Joint ETR composes the authorized all-three/target-evasion count ratio on the same validated frozen target-domain plan, with the frozen Interval policy and quantile method; it does not modify the protocol catalog. '+
        'Zero-event percentile intervals do not prove future immunity. One large InjecAgent component dominates population resampling; source-mixture uncertainty and generator capacity constrain interpretation.')
    section(18,'Scientific Interpretation',
        (f"The predefined generator produced {summary['target_evasion_count']}/800 valid target evasions. Among those, transfer to D_S was {rate(summary['etr_ds'])}, to D_G {rate(summary['etr_dg'])}, and to both {rate(summary['joint_transfer'])}. " if summary['target_evasion_count'] else
         'The predefined generator produced no target evasions. Transfer is undefined; this is a limitation of the fixed generator, not evidence of universal D_M-B robustness. ')+
        f"Observed all-three misses changed from 0/800 R1 parents to {core['common_mode']['all_three_fn_count']}/800 R2 children. "+
        'Read this with paired transitions and source dependence, not as an independent-population causal comparison. A successful evasion is detector-directed, not downstream jailbreak success.')
    section(19,'Limitations','Only one target and one predeclared deterministic operator family/query budget; no LLM rewriting or downstream success judge. Structural reversibility may still fragment tokens or remove instructions from the analyzed window. '+
        'Curated R1 source mix, benchmark labels, hidden pretraining/source reuse, one giant InjecAgent lineage, score-direction assumptions, and low R1 D_G recall limit broad conclusions. No success-only cherry-picking: all 800 terminals are reported. Local-only data distribution restrictions remain.')
    section(20,'Protocol Integrity','All 252 predeclared source/model/protocol/R0/R1 preservation hashes unchanged. No model, feature, tokenizer, calibration, score direction, threshold, detector decision, metric formula, lineage definition, uncertainty contract or historical evidence was modified. '+
        'No protected/final-test data, verifier, retraining, new gradient objective, ensemble-directed search or Cycle 2 work. Release and baseline checks accompany final acceptance.')
    section(21,'R3 Not Started','R3 was NOT started. This experiment targets only D_M-B. The next research step requires separate authorization; no next target is run by this task.')
    content='# R2 D_M-B Targeted Evasion Results v2\n\nStatus: COMPLETE; frozen detector-evasion experiment.\n\nProspective protocol binding: exp_protocol_001_patch_001. Original blocked report v1 preserved.\n\n'+'\n'.join(sections)
    path=p.ROOT/'reviews/R2_DMB_TARGETED_EVASION_RESULTS_v2.md'
    data=content.encode('utf-8')
    require(not path.exists() or path.read_bytes()==data,'REPORT_OVERWRITE_CONFLICT')
    if not path.exists():
        with path.open('xb') as stream:
            stream.write(data)
    p.publish(p.OUT/'r2_dmb_report_binding_v1.json',dict(report_path=path.relative_to(p.ROOT).as_posix(),sha256=p.files.sha(path)))
    print(path)


if __name__=='__main__':
    render()
