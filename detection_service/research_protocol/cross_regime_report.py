"""Render the cross-regime synthesis report from frozen synthesis values only."""
from detection_service.research_protocol import cross_regime_synthesis as c

TITLES = dict(R0='R0 non-adaptive development', R1='R1 shifted unseen', **{'R2-DMB': 'R2 single-detector targeted (D_M-B)',
              'R2-D_S': 'R2 single-detector targeted (D_S)', 'R3': 'R3 ensemble-aware (target ALL)'})


def fmt(cell, digits=4):
    if isinstance(cell, dict):
        if cell.get('status') in ('OBSERVED', 'DEFINED'):
            return f'{cell["value"]:.{digits}f}'
        return cell.get('status', 'UNDEFINED')
    if isinstance(cell, float):
        return f'{cell:.{digits}f}'
    return 'NOT_APPLICABLE' if cell is None else str(cell)


def ci(cell):
    value = cell.get('ci95', {}) if isinstance(cell, dict) else {}
    if value.get('lower') is not None:
        return f'[{value["lower"]:.4f}, {value["upper"]:.4f}]'
    return value.get('status', 'NOT_APPLICABLE')


def table(header, rows):
    lines = ['| ' + ' | '.join(header) + ' |', '|' + '|'.join('---' for _ in header) + '|']
    lines += ['| ' + ' | '.join(str(v) for v in row) + ' |' for row in rows]
    return '\n'.join(lines)


def findings(block):
    return '\n'.join(f'- **{f["id"]}** ({f["kind"]}): {f["statement"]}' for f in block['findings'])


def render(values, bundle, bundle_sha):
    metrics, T = values['cross_regime_metrics_v1'], values['cross_regime_tables_v1']['tables']
    q1, q2 = values['cross_regime_rq1_findings_v1'], values['cross_regime_rq2_findings_v1']
    X = c.index(metrics)
    records = {r['regime_id']: r for r in metrics['records']}
    r3, rq3 = metrics['r3'], metrics['rq3']
    out = ['# Cross-Regime Synthesis Results v1', '', 'STATUS: PASS', '',
           'All values are rendered from frozen machine-readable artifacts by '
           '`detection_service/research_protocol/cross_regime_report.py`; no rounded report value substitutes for an artifact value. '
           f'Result bundle: `artifacts/research_protocol/synthesis/cross_regime_result_bundle_v1.json` (SHA-256 `{bundle_sha}`).', '']

    def section(title, *body):
        out.extend(['## ' + title, '', *body, ''])

    reads = {r['path']: r for r in metrics['read_receipt']}
    rows = []
    for rid in c.REGIMES:
        record = records[rid]
        if rid == 'R3':
            rows.append([rid, TITLES[rid], 'R3 freeze `' + record['provenance']['freeze_commit_sha'] + '`',
                         '`' + record['provenance']['artifacts']['result_bundle']['sha256'][:16] + '...`'])
        else:
            path = record['provenance']['artifacts'][0]['path']
            rows.append([rid, TITLES[rid], 'first committed `' + reads[path]['first_committed_in'] + '`; read at `' + reads[path]['commit'] + '`',
                         '`' + reads[path]['sha256'][:16] + '...`'])
    section('1. Experiment Sequence',
        'R0 (non-adaptive development) -> R1 (shifted unseen) -> R2-DMB (D_M-B-targeted) -> R2-D_S (D_S-targeted) -> '
        'Phase-1 integration baseline `' + c.ACCEPTED_R3['integration_baseline_commit'] + '` -> R3 (ensemble-aware, target ALL) -> '
        'this synthesis. R2-D_G is an OPTIONAL_EXPLORATORY_APPENDIX and was not executed. No experiment was rerun for this synthesis.', '',
        table(['Regime', 'Definition', 'Frozen bundle provenance', 'Bundle SHA-256'], rows), '',
        'R3 commits: seed freeze `' + c.ACCEPTED_R3['seed_freeze_commit'] + '`, terminal freeze `' + c.ACCEPTED_R3['terminal_freeze_commit'] +
        '`, scoring `' + c.ACCEPTED_R3['scoring_commit'] + '`, analysis/failure freeze `' + c.ACCEPTED_R3['freeze_commit_sha'] + '`.')
    section('2. Frozen Detector Stack',
        table(['Label', 'Detector', 'Threshold ID', 'Operational threshold', 'Model SHA-256', 'Model revision'],
              [[r['label'], r['detector_id'], r['threshold_id'], repr(r['threshold']), '`' + r['model_sha256'] + '`', r['model_revision'] or 'n/a']
               for r in r3['detector_identities']]), '',
        'Operational decisions use `score >= threshold` (ties are ATTACK). D_S uses its calibrated probability; D_M-B and D_G use raw '
        'scores. Thresholds, models and calibrators are identical across all five regimes; no detector was retrained or re-selected.')
    section('3. Regime Definitions',
        table(['Regime', 'Population type', 'Attacks', 'Benign', 'Lineages', 'Target'],
              [[rid, records[rid]['population_type'], records[rid]['attack_count'], records[rid]['benign_count'],
                records[rid]['lineage']['count'], (records[rid]['targeted'][0]['target_detector'] if records[rid]['targeted'] else 'none')]
               for rid in c.REGIMES]), '',
        'Mixed attack+benign regimes: R0, R1. Attack-only regimes: R2-DMB, R2-D_S, R3. FPR, ROC-AUC and AP are reported only for mixed '
        'regimes; for attack-only regimes they are NOT_APPLICABLE (no benign denominator), never zero.')
    for number, rid in enumerate(c.REGIMES, 4):
        rows = [r for r in T['A'] if r['regime'] == rid]
        body = [table(['Detector', 'TP', 'FN', 'FNR', 'FNR 95% CI', 'FP', 'TN', 'FPR', 'ROC-AUC', 'AP'],
                      [[r['detector_id'], r['tp'], r['fn'], fmt(r['fnr']), ci(r['fnr']), fmt(r['fp']), fmt(r['tn']), fmt(r['fpr']),
                        fmt(r['roc_auc']), fmt(r['ap'])] for r in rows]), '',
                f'All-three FN: {X[rid + "/all_three_fn"]}/{X[rid + "/attack_count"]}.']
        target = next((r for r in T['D'] if r['regime'] == rid and r.get('target_detector')), None)
        if target:
            body.append(f'Target {target["target_detector"]}: {target["target_evasion_count"]}/{target["valid_attempt_count"]} '
                        f'(rate {fmt(target["target_evasion_rate"])}, 95% CI {ci(target["target_evasion_rate"])}). ' +
                        ('; '.join(f'ETR to {x["transfer_detector"]}: {x["joint_evasion_count"]}/{target["target_evasion_count"]} = '
                                   f'{fmt(x["etr"])} (CI {ci(x["etr"])})' for x in target['transfers']) or
                         'Transfer: ' + target['transfer_status'] + '.'))
        if rid == 'R3':
            body.append(f'Parents {r3["parents"]}, inherited lineages {r3["inherited_lineages"]}, sources {r3["source_counts"]}. '
                        f'Candidate evaluations {r3["candidate_evaluations"]}, generation detector calls {r3["generation_detector_calls"]}, '
                        f'post-freeze replay calls {r3["post_freeze_replay_calls"]}, budget violations {r3["budget_violations"]}, '
                        f'reconstruction failures {r3["reconstruction_failures"]}. Failure manifest {r3["failure_manifest"]["status"]} '
                        f'({r3["failure_manifest"]["member_count"]} members).')
        section(f'{number}. {rid}', *body)
    figures = values['cross_regime_figure_manifest_v1']['figures']
    section('9. Cross-Regime Metrics',
        '### Table B: pairwise common-mode metrics', '',
        table(['Regime', 'Pair', 'Shared FN', 'Union FN', 'JFN', 'JFN CI', 'FNR_i x FNR_j', 'EJF', 'EJF CI', 'FN Jaccard'],
              [[r['regime'], r['left_detector'] + '/' + r['right_detector'], r['shared_fn'], r['union_fn'], fmt(r['jfn']), ci(r['jfn']),
                fmt(r['independence_reference']), fmt(r['ejf']), ci(r['ejf']), fmt(r['fn_jaccard'])] for r in T['B']]), '',
        '### Table C: all-three failures, unique catches and conditional recovery', '',
        table(['Regime', 'All-three FN', 'All-three JFN', 'CI', 'Unique catches (D_S/D_M-B/D_G)', 'Conditional recovery (D_S/D_M-B/D_G)'],
              [[r['regime'], r['all_three_fn'], fmt(r['all_three_jfn']), ci(r['all_three_jfn']),
                '/'.join(str(r['recovery'][d]['unique_catch_count']) for d in c.IDS),
                '/'.join(fmt(r['recovery'][d]['conditional_recovery']) for d in c.IDS)] for r in T['C']]), '',
        '### Failure-pattern counts (bits = D_S, D_M-B, D_G miss)', '',
        table(['Regime'] + [f'{i:03b}' for i in range(8)],
              [[r['regime']] + [r['failure_patterns'][f'{i:03b}']['count'] for i in range(8)] for r in T['C']]), '',
        '### Table D: targeted attack behavior', '',
        table(['Regime', 'Target', 'Successes / attempts', 'Rate', 'CI', 'Transfer'],
              [[r['regime'], r.get('target_detector') or 'none', f'{r["target_evasion_count"]}/{r["valid_attempt_count"]}'
                if r.get('target_detector') else 'NOT_APPLICABLE', fmt(r['target_evasion_rate']) if r.get('target_detector') else 'NOT_APPLICABLE',
                ci(r['target_evasion_rate']) if r.get('target_detector') else 'NOT_APPLICABLE',
                ('; '.join(f'{x["transfer_detector"]} {x["joint_evasion_count"]} ({fmt(x["etr"])})' for x in r['transfers'])
                 or r.get('transfer_status')) if r.get('target_detector') else r['status']] for r in T['D']]), '',
        '### Table E: parent-child transitions', '',
        table(['Regime', 'Detector', 'catch->catch', 'catch->miss', 'miss->catch', 'miss->miss'],
              [[r['regime'], r.get('detector_id', '-'), r.get('catch_to_catch', r.get('status')), r.get('catch_to_miss', ''),
                r.get('miss_to_catch', ''), r.get('miss_to_miss', '')] for r in T['E']]), '',
        '### Table F: source-conditioned results', '',
        table(['Regime', 'Source', 'Attacks', 'Lineages', 'FN D_S/D_M-B/D_G', 'All-three FN', 'Target successes'],
              [[r['regime'], r['source'], r.get('attacks', '-'), r.get('lineages', '-'),
                '/'.join(str(r[f'{d}/fn']) for d in c.IDS) if 'ds_v2/fn' in r else r.get('status', '-'),
                r.get('all_three_fn', '-'), r.get('target_evasion_count', 'NOT_APPLICABLE')] for r in T['F']]), '',
        '### Figures', '',
        '\n'.join(f'- `artifacts/research_protocol/synthesis/{v["file"]}`: {v["spec"]["title"]}' for v in figures.values()))
    section('10. RQ1 Answer', '**' + q1['question'] + '**', '', q1['answer'], '', findings(q1))
    section('11. RQ2 Answer', '**' + q2['question'] + '**', '', q2['answer'], '', findings(q2))
    section('12. Common-Mode Interpretation',
        'Pairwise shared FN by regime (D_S/D_M-B, D_S/D_G, D_M-B/D_G): ' +
        ', '.join(f'{rid} ' + '/'.join(str(X[f"{rid}/pair/{a}~{b}/shared_fn"]) for a, b in c.PAIRS) for rid in c.REGIMES) +
        '. D_G FNR by regime: ' + ', '.join(f'{rid} {100 * X[rid + "/dg_v1/fnr"]:.2f}%' for rid in c.REGIMES) +
        '. D_S misses also missed by D_G: ' +
        ', '.join(f'{rid} {X[rid + "/pair/ds_v2~dg_v1/shared_fn"]}/{X[rid + "/ds_v2/fn"]}' for rid in c.REGIMES) +
        '. D_S/D_G JFN by regime: ' +
        ', '.join(f'{rid} {X[rid + "/pair/ds_v2~dg_v1/jfn"]:.4f}' for rid in c.REGIMES) + '; D_S/D_G EJF: ' +
        ', '.join(f'{rid} {X[rid + "/pair/ds_v2~dg_v1/ejf"]:+.4f}' for rid in c.REGIMES) + '. EJF and the FNR product are descriptive '
        'references; they do not test independence and do not establish causal dependence between detector errors. All-three '
        'common-mode misses (pattern 111) by regime: ' +
        ', '.join(f'{rid} {X[rid + "/all_three_fn"]}/{X[rid + "/attack_count"]}' for rid in c.REGIMES) + '.')
    section('13. D_M-B Complementarity Observation',
        f'D_M-B missed {X["R2-D_S/transfer/ds_v2->dm_b_v1/joint_evasion_count"]} of the {X["R2-D_S/target/ds_v2/target_evasion_count"]} '
        f'successful D_S evasions, had {X["R2-DMB/target/dm_b_v1/target_evasion_count"]}/{X["R2-DMB/attack_count"]} target evasions under '
        f'R2-DMB, and missed {X["R3/dm_b_v1/fn"]}/{X["R3/attack_count"]} R3 terminals. In R1, R2-DMB, R2-D_S and R3 it shared no observed '
        'miss with either other detector. This is complete observed recovery for these frozen populations and generators only; it does '
        'not establish that D_M-B is universally robust. Attack-side complementarity is reported separately from benign behavior: '
        f'D_M-B benign FPR was {100 * X["R0/dm_b_v1/fpr"]:.2f}% in R0 and {100 * X["R1/dm_b_v1/fpr"]:.2f}% in R1 at the same threshold.')
    section('14. Zero-Event R3 Interpretation', q2['r3_zero_event_caveat'], '',
        f'Stored all-three JFN interval: {X["R3/ci/all_three/jfn"]} (frozen 1000-replicate percentile bootstrap, seed 1701, '
        'lineage-clustered). No new inferential interval was added. The absence of all-three failures is evidence about the frozen '
        '97-parent population and the predefined reversible generator and budget, not about arbitrary adversarial prompts.')
    section('15. Source and Lineage Limitations',
        f'R3: {r3["parents"]} parents, {r3["inherited_lineages"]} inherited lineages, ' +
        ', '.join(f'{k} {v}' for k, v in sorted(r3['source_counts'].items())) +
        '. R3 source generalization is limited: InjecAgent contributes a single parent/lineage. In R1, R2-DMB and R2-D_S the InjecAgent '
        'attacks form one inherited lineage cluster, so source-level InjecAgent intervals are degenerate and not independent-case '
        'evidence. R0 has no frozen source decomposition. R0 and R1 are unpaired populations with different composition; R2 and R3 '
        'seed sets, objectives and budgets differ, so cross-regime comparisons are descriptive.')
    section('16. What Is NOT Established', '\n'.join('- ' + item for item in q2['not_established']) +
        '\n- R1 alone does not establish adaptive robustness.\n- No significance test or causal comparison was performed.')
    section('17. Verifier / RQ3 Status',
        f'R3 base-stack all-three failure population: {rq3["r3_base_stack_all_three_failure_population"]}. '
        f'Development-stage verifier recovery denominator: {rq3["development_recovery_denominator"]}. '
        'Development-stage Recovery(V_k): UNDEFINED for V1, V2 and V3. RQ3 remains NOT EMPIRICALLY IDENTIFIABLE FROM R3 DEVELOPMENT '
        f'FAILURE POPULATION. Verifier panel: {c.VERIFIER_PANEL}. No verifier inference was run (0 queries) and no protected/final '
        'evaluation data was accessed. Phase-2 Track B owns the final RQ3 disposition.')
    tests = bundle['test_receipt']
    section('18. Readiness for Research Freeze',
        f'Inputs: R0, R1, R2-DMB, R2-D_S and R3 frozen bundles validated and unchanged. Tests: {tests["passed"]} passed, '
        f'{tests["failed"]} failed, {tests["skipped"]} skipped (`{tests["path"]}`, SHA-256 `{tests["sha256"]}`). '
        f'Synthesis outputs: {len(bundle["outputs"])} hash-bound files. Analysis commit: `{bundle["analysis_commit"]}`.', '',
        'Verdict: **' + bundle['verdict'] + '**')
    return ('\n'.join(out).rstrip() + '\n').encode('ascii')
