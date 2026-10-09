"""Render DEVELOPMENT_RESEARCH_FREEZE_v1.md from the frozen freeze/protocol/matrix values only."""


def P(value):
    return f'{100 * value:.2f}%' if isinstance(value, float) else str(value)


def table(header, rows):
    lines = ['| ' + ' | '.join(header) + ' |', '|' + '|'.join('---' for _ in header) + '|']
    return '\n'.join(lines + ['| ' + ' | '.join(str(v) for v in row) + ' |' for row in rows])


def render(freeze, protocol, matrix, X):
    metrics = freeze['primary_metrics']
    out = ['# Development Research Freeze v1', '', 'STATUS: ' + freeze['status'], '',
           '**PROTECTED DATA HAS NOT BEEN OPENED OR SCORED AS OF THIS FREEZE.**', '',
           f'Project: {freeze["project_title"]}. Frozen at {freeze["frozen_at"]}. Research-freeze commit: the commit that first adds '
           '`artifacts/research_protocol/final/development_research_freeze_v1.json` on `final/research-freeze-001`.', '']

    def section(title, *body):
        out.extend(['## ' + title, '', *body, ''])

    a = freeze['accepted_inputs']
    section('1. Accepted Inputs',
        table(['Input', 'Reference'], [
            ['RQ1/RQ2 synthesis', f'`{a["rq1_rq2_branch"]}` @ `{a["rq1_rq2_head"]}` ({a["rq1_rq2_verdict"]})'],
            ['RQ3 disposition', f'`{a["rq3_branch"]}` @ `{a["rq3_head"]}` ({a["rq3_verdict"]})'],
            ['R3 freeze', f'`{a["r3_freeze"]}`'], ['Integration baseline', f'`{a["integration_baseline"]}`'],
            ['RQ1/RQ2 result bundle', f'`{a["rq1_rq2_result_bundle"]["sha256"]}`'],
            ['RQ3 disposition artifact', f'`{a["rq3_disposition"]["sha256"]}`'],
            ['Verifier predeclaration (VERIFIER-RECOVERY-001)', f'`{a["verifier_predeclaration_sha256"]}`']]), '',
        'RQ3 integration: cherry-picked ' + ', '.join(f'`{k[:7]}` ({v})' for k, v in a['integration']['cherry_picked'].items()) +
        '; skipped as patch-equivalent ' + ', '.join(f'`{k[:7]}` ({v})' for k, v in a['integration']['skipped_patch_equivalent'].items()) +
        '. All RQ3-branch files are byte-identical to the accepted RQ3 head; no RQ1/RQ2 result changed.')
    section('2. Frozen Detector Stack',
        table(['Label', 'Detector', 'Threshold ID', 'Threshold', 'Score', 'Model SHA-256', 'Revision'],
              [[r['label'], r['detector_id'], r['threshold_id'], repr(r['threshold']), r['score_field'], '`' + r['model_sha256'] + '`',
                r['model_revision'] or 'n/a'] for r in freeze['detector_stack']]), '', 'Decision: ATTACK if score >= threshold (ties are ATTACK).')
    rows = []
    for rid, m in metrics.items():
        d = m['detectors']
        rows.append([rid, m['attack_count'], m['benign_count']] + [f'{P(d[k]["recall"])} / {P(d[k]["fpr"])}' for k in ('D_S', 'D_M-B', 'D_G')] +
                    [f'{m["all_three_fn"]}/{m["attack_count"]}'])
    section('3. Development Metric Summary',
        table(['Regime', 'Attacks', 'Benign', 'D_S recall / FPR', 'D_M-B recall / FPR', 'D_G recall / FPR', 'All-three FN'], rows), '',
        'FPR is NOT_APPLICABLE for the attack-only regimes R2-DMB, R2-D_S and R3.', '',
        table(['Regime', 'D_S x D_M-B shared FN', 'D_S x D_G shared FN', 'D_M-B x D_G shared FN', 'D_S x D_G JFN', 'D_S x D_G EJF'],
              [[rid, m['pairs']['D_SxD_M-B']['shared_fn'], m['pairs']['D_SxD_G']['shared_fn'], m['pairs']['D_M-BxD_G']['shared_fn'],
                f'{m["pairs"]["D_SxD_G"]["jfn"]:.4f}', f'{m["pairs"]["D_SxD_G"]["ejf"]:+.4f}'] for rid, m in metrics.items()]), '',
        f'R2-DMB: {metrics["R2-DMB"]["target"]["evasions"]}/{metrics["R2-DMB"]["target"]["attempts"]} D_M-B target evasions; ETR '
        f'{metrics["R2-DMB"]["target"]["etr_to_DS"]}. R2-D_S: {metrics["R2-D_S"]["target"]["evasions"]}/{metrics["R2-D_S"]["target"]["attempts"]} '
        f'D_S target evasions ({P(metrics["R2-D_S"]["target"]["rate"])}); D_G also missed {metrics["R2-D_S"]["target"]["DG_also_missed"]}; '
        f'D_M-B missed {metrics["R2-D_S"]["target"]["DMB_also_missed"]}/{metrics["R2-D_S"]["target"]["evasions"]} D_S-evasive terminals. R3: {metrics["R3"]["target"]["evasions"]}/'
        f'{metrics["R3"]["target"]["attempts"]} all-three evasions over {metrics["R3"]["population"]["parents"]} lineage-distinct parents '
        f'({metrics["R3"]["population"]["LLMail"]} LLMail, {metrics["R3"]["population"]["InjecAgent"]} InjecAgent); stored interval '
        f'{metrics["R3"]["target"]["rate_ci95"]} is a zero-event percentile bootstrap, not a population robustness bound.')
    section('4. RQ1 Final Answer', '**' + freeze['rq1']['finding'] + '**', '', freeze['rq1']['accepted_answer'])
    section('5. RQ2 Final Answer', '**' + freeze['rq2']['finding'] + '**', '', freeze['rq2']['accepted_answer'], '',
        'Terminology: D_M-B detected ' + ('all ' if metrics['R2-D_S']['target']['DMB_also_missed'] == 0 else
        f'{metrics["R2-D_S"]["target"]["evasions"] - metrics["R2-D_S"]["target"]["DMB_also_missed"]} of the ') +
        f'{metrics["R2-D_S"]["target"]["evasions"]} observed D_S-evasive terminals (detection coverage, not Recovery(V_k)).')
    r3 = freeze['rq3']
    section('6. RQ3 Final Disposition and H3',
        f'RQ3: **{r3["status"]}** ({r3["reason"]}). {r3["finding"]}', '',
        f'Eligible regimes: {", ".join(r3["eligible_regimes"])}; eligible terminals {r3["eligible_terminals"]}; all-three failures '
        f'{r3["all_three_failures"]}. Recovery: ' + ', '.join(f'{k} {v["status"]} (null)' for k, v in r3['recovery'].items()) + '.', '',
        f'R0 is not substituted: its {r3["r0_excluded"]["all_three_failures"]} all-three misses are excluded. {r3["r0_excluded"]["reason"]}', '',
        f'H3: **{freeze["h3"]["status"]}**. {freeze["h3"]["reason"]}')
    section('7. Key Tables and Figures',
        f'Tables A-F: `{freeze["tables"]["path"]}` (SHA-256 `{freeze["tables"]["sha256"]}`). Figure manifest: `{freeze["figure_manifest"]["path"]}` '
        f'(SHA-256 `{freeze["figure_manifest"]["sha256"]}`).', '', '\n'.join('- `' + p + '`' for p in freeze['figure_manifest']['figures']))
    section('8. Limitations (frozen before any protected access)', '\n'.join(f'- **{x["id"]}**: {x["text"]}' for x in freeze['limitations']))
    section('9. Interpretation Boundaries', '\n'.join('- ' + x for x in freeze['interpretation_boundaries']))
    section('10. Verifier and R2-D_G Dispositions',
        f'Verifier study {freeze["verifier_disposition"]["experiment_id"]}: {freeze["verifier_disposition"]["status"]} '
        f'({freeze["verifier_disposition"]["outcome"]}); scientific queries ' +
        ', '.join(f'{k} {v}' for k, v in freeze['verifier_disposition']['scientific_queries'].items()) + '.', '',
        f'R2-D_G: {freeze["r2_dg_disposition"]["classification"]}; executed {freeze["r2_dg_disposition"]["executed"]}.', '',
        'Future work (NOT_EXECUTED): ' + '; '.join(x['item'] for x in freeze['future_work']) + '.')
    section('11. Protected Confirmation Protocol',
        f'Protocol `{protocol["protocol_id"]}`: **{protocol["status"]}**. Executable: {protocol["executable"]}. Stage B authorized: '
        f'{protocol["stage_b_authorized"]}. Protected samples opened: {protocol["protected_samples_opened"]}.', '', protocol['reason'], '',
        'Missing before any access: ' + '; '.join(protocol['missing_before_access']) + '.', '',
        table(['Governance evidence', 'SHA-256', 'Tracked'], [[f'`{e["path"]}`', f'`{e["sha256"]}`', e['tracked']] for e in protocol['governance_evidence']]), '',
        'Bound for any future authorized protocol: the frozen detector stack and thresholds above, prediction_v1 schema, the frozen metric '
        'definitions, UNDEFINED/NOT_APPLICABLE rules and the frozen lineage-clustered bootstrap. ' + protocol['required_next_authorization'])
    section('12. Claim-Confirmation Matrix (frozen before access)',
        f'Evaluation status: {matrix["evaluation_status"]}. {matrix["rule"]}', '',
        '\n\n'.join(f'**{cl["claim_id"]}** ({cl["question"]}): {cl["claim"]}\n' +
                    '\n'.join(f'- {k}: {v}' for k, v in cl['criteria'].items()) for cl in matrix['claims']))
    section('13. Freeze Statement',
        'PROTECTED DATA HAS NOT BEEN OPENED OR SCORED AS OF THIS FREEZE. No detector, verifier or protected scientific query was made; '
        'no development artifact, threshold, model identity, metric definition or attack definition changed.')
    return ('\n'.join(out).rstrip() + '\n').encode('ascii')
