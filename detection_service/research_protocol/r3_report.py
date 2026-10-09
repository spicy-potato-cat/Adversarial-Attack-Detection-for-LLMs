"""Metadata-only R3 final report and preservation/test acceptance receipt."""
import json
import xml.etree.ElementTree as ET

from detection_service.research_protocol import r3_inputs as i, r3_scoring as scoring, r3_freeze as freeze
from detection_service.research_protocol import r3_run as run
from detection_service.research_protocol.r3_integration import preservation, PARENT, TRACK_B
from detection_service.research_protocol.regime import require

REPORT = i.p.ROOT / 'reviews/R3_ENSEMBLE_AWARE_RESULTS_v1.md'


def read(name):
    return i.p.files.read_json(i.OUT / (name + '_v1.json'))


def test_receipts():
    result = []
    for filename in ('r3_pre_run.xml', 'r3_metrics_regression.xml', 'r3_post_run.xml'):
        path = i.p.ROOT / 'tmp' / filename
        cases = list(ET.parse(path).getroot().iter('testcase'))
        require(cases and not any(case.find(tag) is not None for case in cases for tag in ('failure', 'error', 'skipped')), 'R3_TEST_FAILURE:' + filename)
        result.append(dict(path=path.relative_to(i.p.ROOT).as_posix(), passed=len(cases), failed=0, skipped=0, sha256=i.p.files.sha(path)))
    return result


def write_report():
    seed, runtime = read('r3_seed_manifest'), read('r3_runtime_preflight')
    generation, accounting = read('r3_generation_results'), read('r3_query_accounting')
    prediction, summary = read('r3_prediction_manifest'), read('r3_summary')
    bundle, paired = read('r3_result_bundle'), read('r3_parent_child_transitions')
    sources, operators = read('r3_source_analysis'), read('r3_operator_analysis')
    failures, coverage = read('r3_all_three_failure_manifest'), read('r3_coverage_analysis')
    acceptance = read('r3_final_validation')
    interval = next(row for result in bundle['uncertainty'] for row in result['intervals'] if row['metric_id'] == 'all_three/jfn')
    n, succeeded = summary['parent_count'], summary['all_three_successes']
    sections = []

    def section(title, body):
        sections.append('## ' + title + '\n\n' + body + '\n')

    def pretty(value):
        return '```json\n' + json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True) + '\n```'

    section('1. Integration Provenance', f'Track-A parent: `{PARENT}`. Track-B integrated reference: `{TRACK_B}`. '
        f'All eight ordered cherry-picks integrated without conflicts. Integration baseline: `{seed["integration_baseline_commit"]}`. '
        'No original R0/R1/R2 scientific artifact or detector file changed. Portability was DEFERRED_NOT_BLOCKING_PHASE1; no fresh-clone or cloud-backup gate was run.')
    section('2. Exact Seed Population', f'{n} attack-positive R1 parents, {seed["inherited_lineages"]} inherited lineages. '
        f'Sources: {json.dumps(seed["source_counts"], sort_keys=True)}. '
        f'Seed freeze: `{runtime["seed_freeze_commit"]}`. Membership hash: `{seed["membership_sha256"]}`. '
        'The frozen one-parent-per-inherited-lineage rule limits membership to 97, not the 800 ceiling. '
        'Selection uses frozen R1 metadata/operational decisions only; no R2 outcome, future R3 result, verifier behavior, or protected data selected membership.')
    section('3. Runtime Integrity', pretty(dict(status=runtime['status'], identities=runtime['identities'],
        synthetic_text_preflight_calls=runtime['synthetic_text_model_calls'], code_execution_commit=read('r3_authoritative_run_receipt')['execution_commit'])) +
        '\nCPU float32 accepted runtime; eight CPU threads from the accepted recipe. Frozen adapters, models, calibrators, schema and thresholds remained unchanged. '
        'A task-local immutable read cache avoids repeatedly parsing/hash-reading the same frozen files: initial exact-byte/duplicate-key validation, stamp checks per access, full byte and object rechecks at scope exit. '
        'The new journaled search matches the frozen synthetic algorithm on engineering fixtures. No live oracle was relabeled SYNTHETIC_FIXTURE.')
    section('4. Query Accounting', pretty(accounting) + '\nPost-freeze replay: ' + str(prediction['actual_calls']) +
        ' additional detector calls, accounted separately from generation and the three preflight calls. '
        'Each uncached candidate reserves three slots before any detector call; logical cache hits are separate; failures are charged and abort without retries. '
        'One authoritative invocation; no difficult-seed restart. Journal events were flushed and fsynced. Raw text/edit scripts remain in ignored local storage.')
    section('5. R3 Target Success', f'{succeeded}/{n} simultaneous evasions; rate {100*summary["target_success_rate"]:.6f}%. '
        'Success requires exact UTF8 inverse reconstruction and all three OK operational BENIGN decisions; normalized minimax objective strictly below zero. Inclusive threshold ties are ATTACK.\n\n' + pretty(interval))
    individual = bundle['core_metrics']['individual']['detectors']
    section('6. Per-Detector Behavior', '| Detector | TP | FN | Recall | FNR |\n|---|---:|---:|---:|---:|\n' +
        '\n'.join(f'| {r["detector_id"]} | {r["tp"]} | {r["fn"]} | {r["recall"]["value"]:.6f} | {r["fnr"]["value"]:.6f} |' for r in individual) +
        '\n\nAttack-only population. FPR, ROC-AUC and AP are NOT_APPLICABLE, not zero. Canonical native and operational schemas remain distinct.')
    pairs = bundle['core_metrics']['common_mode']['pairs']
    section('7. Pairwise Common-Mode Metrics', '| Pair | Shared FN | JFN | FNR product reference | EJF | FN Jaccard |\n|---|---:|---:|---:|---:|---:|\n' +
        '\n'.join('| ' + '/'.join((r['left_detector'], r['right_detector'])) + ' | ' + str(r['shared_fn_count']) + ' | ' +
            ' | '.join('UNDEFINED' if r[k]['value'] is None else f'{r[k]["value"]:.6f}' for k in ('jfn', 'independence_reference', 'ejf', 'fn_jaccard')) + ' |' for r in pairs) +
        '\n\nFNR products are descriptive reference quantities, not evidence that detector errors are independent.')
    section('8. All-Three Common-Mode Result', f'All-three FN/JFN: {succeeded}/{n} = {summary["target_success_rate"]:.6f}. '
        'This equals generation target success and canonical replay accounting.\n\n' + pretty(dict(
            failure_patterns=bundle['core_metrics']['failure_patterns']['patterns'], recovery=bundle['core_metrics']['recovery']['detectors'])))
    section('9. Parent-Child Transitions', pretty(paired['overall']) +
        '\nExactly paired to each immediate R1 parent under the unchanged operational policy. Source/operator strata are in `r3_parent_child_transitions_v1.json`. '
        'Inherited parent misses are distinguished from newly induced catch-to-miss changes; overlap is not all newly induced transfer.')
    section('10. Source Analysis', pretty({source: {k: row[k] for k in ('parent_count', 'all_three_successes', 'target_success_rate', 'FN', 'inherited_lineages')}
        for source, row in sources.items()}) + '\nSource-specific core metrics and unchanged-policy intervals are frozen in `r3_source_analysis_v1.json`. '
        'Only one InjecAgent parent/lineage was eligible under the one-lineage rule; its bootstrap interval is degenerate and does not establish within-source generalization.')
    section('11. Operator Analysis', pretty({op: row for op, row in operators.items() if row['parent_count']}) +
        '\nThese are selected terminal mechanisms, not randomized treatment arms or exclusive operator exposure. Unselected candidates remain in the query journal. '
        'The source/operator and query-efficiency summaries do not authorize future operator changes.')
    section('12. Uncertainty', 'Frozen 1,000-replicate PCG64 bootstrap, seed 1701, 95% linear percentile intervals, inherited R1 LINEAGE_CLUSTERED unit. '
        'The canonical result bundle binds resampling plan and RNG hashes; paired detector metrics share draws. '
        'Undefined denominators remain null, with the frozen 95% valid-replicate rule. A zero-event percentile interval can be [0,0]; it is not a population robustness bound. No uncertainty setting changed after outcomes.')
    section('13. R1 / R2 Comparison', 'R2-DMB target evasion: 0/800. R2-D_S target evasion: 104/698; among successful D_S evasions, '
        'D_M-B misses 0/104, D_G misses 102/104, all-three misses 0/104. '
        f'R3 simultaneous evasion: {succeeded}/{n}. R3 uses a different, lineage-restricted seed population and ALL minimax objective. '
        'The frozen R1 attack population has D_M-B FN 0/800 and therefore zero all-three misses; selected-parent changes are reported in Section 9. '
        '`r3_matched_comparison_v1.json` records same-parent joins to both frozen R2 populations; comparisons are descriptive, not architecture-only or causal. '
        'No R2 experiment was rerun.')
    section('14. Limitations', 'One frozen reversible operator family and budget; no paraphrase, gradient attack, new operator, target-model compromise judge, or protected confirmation. '
        'Exact inverse preservation does not establish tokenizer-visible semantic preservation or downstream instruction execution. '
        'The minimax raw/calibrated ratios reflect frozen heterogeneous thresholds, not calibrated cross-model risk equality. '
        'The one-lineage policy strongly restricts InjecAgent representation. Source labels/provenance retain their earlier uncertainty. '
        'Truncation/normalization associations cannot identify causal mechanisms. No universal robustness/vulnerability or production guarantee is claimed.\n\n' +
        pretty({label: {k: v for k, v in row.items() if k != 'rows'} for label, row in coverage['detectors'].items()}))
    section('15. Frozen Verifier Handoff Population', f'Status {failures["status"]}; members {failures["member_count"]}; empty {failures["empty"]}. '
        f'Manifest `artifacts/research_protocol/r3/r3_all_three_failure_manifest_v1.json`; file SHA `{i.p.files.sha(i.OUT / "r3_all_three_failure_manifest_v1.json")}`; '
        f'membership SHA `{failures["membership_sha256"]}`. Bound terminal/prediction/stack/threshold/verifier-contract hashes; metadata only, no raw prompts in Git. '
        'The population is frozen before any verifier scientific call. An EMPTY manifest authorizes review, not manufactured failures or an R3 redesign. Phase 2 still requires its separate authorization.')
    section('16. Non-Execution And Acceptance', 'Verifier scientific inference: NOT_RUN, 0 calls. Protected/final evaluation: NOT_RUN, 0 calls. '
        'R2-D_G: NOT_RUN. Training, selection, Cycle 2, portability/fresh-clone/cloud backup: NOT_RUN.\n\n' +
        pretty(dict(status=acceptance['status'], tests=acceptance['test_receipts'], integrity=acceptance['integrity_summary'])) +
        '\nScientific run provenance remains the pre-query execution commit. Later terminal/scoring/analysis acceptance commits do not retroactively become model-run provenance. '
        'Final evidence commit and remote synchronization are reported externally to avoid self-referential hashes.')
    verdict = ('R3_COMPLETE_FAILURE_POPULATION_FROZEN_READY_FOR_PHASE2' if failures['member_count'] else
               'R3_COMPLETE_EMPTY_FAILURE_POPULATION_READY_FOR_PHASE2_REVIEW')
    payload = ('# R3 Ensemble-Aware Results v1\n\nSTATUS: PASS\n\n' + '\n'.join(sections) + '\n## Final Verdict\n\n' + verdict + '\n').encode('ascii')
    require(not REPORT.exists(), 'REFUSE_R3_REPORT_OVERWRITE')
    with REPORT.open('xb') as stream:
        stream.write(payload)
    return verdict


def accept():
    receipts = test_receipts()
    i.gate()
    rows, accounting = freeze.validate()
    require(read('r3_terminal_manifest')['terminals'] == rows, 'R3_TERMINAL_ACCEPTANCE_CONFLICT')
    require(read('r3_query_accounting')['detector_calls'] == accounting['detector_calls'], 'R3_QUERY_ACCOUNTING_DRIFT')
    analysis = read('r3_analysis_provenance')
    require(analysis['status'] == 'PASS' and all(i.p.files.sha(i.OUT / name) == expected for name, expected in analysis['sha256'].items()), 'R3_ANALYSIS_HASH_DRIFT')
    require(read('r3_prediction_manifest')['prediction_sha256'] == i.p.files.sha(scoring.PREDICTIONS), 'R3_PREDICTION_ACCEPTANCE_DRIFT')
    preserved = preservation()
    summary = {k: v for k, v in preserved.items() if k not in ('sha256', 'checkout_only_line_endings')}
    i.p.publish(i.OUT / 'r3_final_validation_v1.json', dict(status='PASS', test_receipts=receipts,
        integrity_summary=summary, models_changed=False, thresholds_changed=False, attack_contract_changed=False,
        verifier_queries=0, protected_queries=0, portability_gate='DEFERRED_NOT_BLOCKING_PHASE1'))
    verdict = write_report()
    hashes = {path.relative_to(i.p.ROOT).as_posix(): i.p.files.sha(path) for path in i.OUT.glob('*') if path.is_file()}
    hashes[REPORT.relative_to(i.p.ROOT).as_posix()] = i.p.files.sha(REPORT)
    i.p.publish(i.OUT / 'r3_final_acceptance_v1.json', dict(status='PASS', verdict=verdict,
        sha256=hashes, model_run_commit=read('r3_authoritative_run_receipt')['execution_commit'],
        integration_baseline_commit=read('r3_seed_manifest')['integration_baseline_commit'],
        seed_freeze_commit=read('r3_runtime_preflight')['seed_freeze_commit'],
        terminal_freeze_commit=i.p.committed(freeze.TERMINALS), scoring_commit=i.p.committed(scoring.PREDICTION_MANIFEST),
        test_receipts=receipts, verifier_queries=0, protected_queries=0))
    print(json.dumps(dict(status='PASS', verdict=verdict, accepted_hash_checks=len(hashes), report=str(REPORT)), indent=2))


if __name__ == '__main__':
    accept()
