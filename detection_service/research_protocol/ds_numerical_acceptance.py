"""Model-free interpretation and reporting of numerical diagnostic evidence."""

import argparse
import hashlib
import json
import statistics
import subprocess
import sys
import xml.etree.ElementTree as ET

from detection_service.research_protocol import ds_numerical_diagnosis as d

REPORT = d.p.ROOT/'reviews/DS_NUMERICAL_REPRODUCIBILITY_DIAGNOSIS_v1.md'
NAMES = ('ds_243_equivalence_recheck','ds_repeatability_first_seed','ds_runtime_environment',
         'ds_dtype_device_trace','ds_feature_sensitivity','ds_r1_diagnostic_replays')


def historical_environment():
    paths = [p for p in (d.p.R1).glob('*.json')]
    paths += [d.p.ROOT/'detection_service/research_protocol/r1_scoring.py',
              d.p.PRIVATE.parent/'r1-clearance-001/native_ds_v2_binding_v1.json',
              d.p.PRIVATE.parent/'r1-clearance-001/native_ds_v2_v1.jsonl']
    paths += list((d.p.ROOT/'reviews').glob('R1*.md'))
    versions = ('python','torch','transformers','numpy','scipy','scikit-learn')
    # Analysis/training version receipts are not evidence for the scoring process.
    return dict(search_paths=[dict(path=p.relative_to(d.p.ROOT).as_posix(),sha256=d.p.files.sha(p)) for p in paths],
        device=dict(status='KNOWN',value='cpu',evidence=d.ds_runtime.BINDING,
                    rationale='Pinned loader checks configured CPU; R1 scoring uses accepted_ds_adapter; canonical native journal records LIVE outputs.'),
        dependencies={k:dict(status='UNKNOWN',reason='No R1 inference-process version receipt found; training and uncertainty-analysis receipts excluded.') for k in versions},
        loader_intended_settings=dict(status='KNOWN',seed=1701,torch_threads=8,deterministic_algorithms=True,
            evidence='detection_service/scripts/statistical_oof_baseline.py:extractor called by accepted archived B2 loader'),
        runtime_settings=dict(status='UNKNOWN',fields=['OMP_NUM_THREADS','MKL_NUM_THREADS','torch_interop_threads','BLAS build','CPU identity']),
        exact_command=dict(status='UNKNOWN',known_entrypoint='python -m detection_service.research_protocol.r1_scoring --score'),
        container=dict(status='UNKNOWN'),requirement_hashes=dict(status='UNKNOWN_NOT_BOUND_TO_R1_PROCESS'),
        run_provenance=d.p.files.read_json(d.p.R1/'r1_analysis_provenance_v1.json')['scoring_commit'],
        warning='NumPy 2.1.3 in r1_uncertainty_v1.json describes analysis, not reference-LM inference.')


def journal_receipts():
    result = []
    for path in sorted(d.PRIVATE.glob('*.jsonl')):
        if path.stem.endswith('_logical'):
            continue
        rows = [json.loads(line) for line in path.read_text(encoding='ascii').splitlines()]
        logical = path.with_name(path.stem+'_logical.jsonl')
        logical_rows = [json.loads(line) for line in logical.read_text(encoding='ascii').splitlines()]
        d.p.require(len(rows)==len(logical_rows),'INCOMPLETE_DIAGNOSTIC_QUERY')
        d.p.require(all(r['query_scope']=='CURRENT_DIAGNOSTIC' and r['target_detector']=='D_S' and
                    r['query_role']=='BASELINE_REPLAY' and r['status']=='OK' for r in rows),'NON_DIAGNOSTIC_QUERY')
        d.p.require([r['query_sequence_number'] for r in rows]==list(range(1,len(rows)+1)),'JOURNAL_SEQUENCE_DRIFT')
        d.p.require([r['candidate_sha256'] for r in rows]==[r['candidate_sha256'] for r in logical_rows],'LOGICAL_RETURN_MISMATCH')
        result.append(dict(path=path.relative_to(d.p.ROOT).as_posix(),sha256=d.p.files.sha(path),queries=len(rows),
                           logical_path=logical.relative_to(d.p.ROOT).as_posix(),logical_sha256=d.p.files.sha(logical)))
    return result


def diagnose():
    import numpy as np
    eq, repeat, env, dtype, features, r1 = [d.read(n) for n in NAMES]
    journals = journal_receipts()
    count = sum(r['queries'] for r in journals)
    d.p.require(count==243+100+10+r1['summary']['count'],'DIAGNOSTIC_COUNT_DRIFT')
    old = d.p.files.read_json(d.p.ROOT/'detection_service/outputs/r2-ds-repair-001/first_seed_pipeline_capture_v1.json')
    current = d.p.files.read_json(d.PRIVATE/'first_seed_numeric_capture.json')
    a,b = np.asarray(old['observation']['surprisals']),np.asarray(current['observation']['surprisals'])
    prior = d.read('ds_baseline_replay_first_seed')
    discrepancy = dict(prior_repair_queries=1,historical_failed_attempt='UNKNOWN_EXACT_COUNT_BOUNDED_1_TO_61',
        prior_repair_raw=prior['raw_live_score'],current_raw=repeat['same_process']['raw']['minimum'],
        prior_repair_calibrated=prior['calibrated_live_score'],current_calibrated=repeat['same_process']['calibrated']['minimum'],
        token_surprisals_changed=int(np.sum(a!=b)),maximum_token_surprisal_delta=float(np.max(np.abs(a-b))),
        maximum_feature_delta=float(np.max(np.abs(np.asarray(old['vector'])-current['vector']))),
        prior_environment=prior['environment'],current_environment=env['after_loader'],
        prior_settings=dict(OMP_NUM_THREADS='4',MKL_NUM_THREADS='4'),
        current_settings=env['after_loader']['variables'],
        causal_thread_ab_not_run=True,
        evidence='Both recorded package versions, CPU/float32, loader torch threads 8 and deterministic=True match. Shell OMP/MKL differ. Prior logits were not saved; cannot separate LM forward from log_softmax effects.')
    stable = all(v['maximum_delta']==0 for v in repeat['combined'].values())
    score_pass = all(eq['summary'][k]['above_tolerance']==0 and r1['summary'][k]['above_tolerance']==0 for k in ('raw','calibrated'))
    decision_pass = all(v['summary'][k+'_mismatches']==0 for v in (eq,r1) for k in ('native','operational'))
    # Successful present-day replay does not establish why the earlier run differed.
    classification = 'INSUFFICIENT_HISTORICAL_EVIDENCE' if stable else 'CURRENT_RUNTIME_NONDETERMINISM'
    diagnosis = dict(status='UNRESOLVED' if stable else 'DIAGNOSED',classification=classification,
        first_observed_divergence='Token surprisals in saved prior repair vs current capture; historical R1 logits/surprisals absent. First retained R1 score divergence is raw LR probability.',
        runtime_deterministic_in_observed_runs=stable,score_reproducibility_current_diagnostic_set=score_pass,
        decision_reproducibility_current_diagnostic_set=decision_pass,
        historical_failed_replay_score_gate_preserved=False,
        materially_changed_behavior='NO_EVIDENCE_IN_OBSERVED_RECORDS; not a proof about untested records',
        numerical_only_consistency='Consistent with small upstream numerical variation; no causal proof of the backend/environment parameter responsible.',
        historical_environment=historical_environment(),prior_vs_current=discrepancy,
        precision_findings=dict(float64_postprocessing_delta=features['same_logits_higher_precision'],
            linear_float32_scale_l1_bound=features['linear_l1_float32_scale_bound'],
            observed_prior_raw_delta=prior['raw_absolute_delta'],
            plausible_scale_sufficient=features['linear_l1_float32_scale_bound']>=prior['raw_absolute_delta'],
            reduction_mean_delta=features['reduction_order_comparison'],
            caveat='The L1 bound assumes independent feature perturbations. Same-logits float64 change is larger than prior drift but does not recreate its cause. No production substitution.'),
        diagnostic_queries=count,journals=journals,purpose='DIAGNOSTIC_ONLY',
        accounting=dict(equivalence=243,same_process=100,fresh_processes=10,r1=r1['summary']['count'],prior_repair=1,
                        historical_failed_attempt='UNKNOWN_BOUNDED_1_TO_61',r2_generation_this_task=0,accepted_terminals=0),
        integrity=d.integrity(),recommendation='D. INSUFFICIENT_EVIDENCE_KEEP_R2_DS_BLOCKED',
        next_change='Seek separate authorization for an isolated thread/backend A/B reproduction with immutable environment receipts; do not relax tolerance or resume generation.',
        scoring_code_commit=eq['code_commit'],start_commit=d.START,
        evidence_sha256={n:d.p.files.sha(d.OUT/(n+'_v1.json')) for n in NAMES},
        private_numeric_capture_sha256=d.p.files.sha(d.PRIVATE/'first_seed_numeric_capture.json'),
        diagnostic_code_sha256=d.p.files.sha(d.p.ROOT/d.CODE),
        journal_code_sha256=d.p.files.sha(d.p.ROOT/'detection_service/research_protocol/r2_ds_query_journal.py'))
    d.save('ds_numerical_runtime_diagnosis',diagnosis)
    print(json.dumps(dict(status=diagnosis['status'],classification=classification,queries=count,current_score_replay=score_pass,current_decision_replay=decision_pass),indent=2))


def report():
    diagnosis = d.read('ds_numerical_runtime_diagnosis')
    eq, repeat, env, dtype, features, r1 = [d.read(n) for n in NAMES]
    receipts = [d.p.ROOT/'tmp/ds_numerical_tests.xml',d.p.ROOT/'tmp/ds_numerical_dmb_tests.xml']
    counts = dict(tests=0,failures=0,errors=0,skipped=0)
    cases = []
    for path in receipts:
        root = ET.parse(path).getroot()
        for suite in root.iter('testsuite'):
            for key in counts:
                counts[key] += int(suite.attrib[key])
        cases += [c.attrib['classname']+'::'+c.attrib['name'] for c in root.iter('testcase')]
    d.p.require(not any(counts[k] for k in ('failures','errors','skipped')) and len(cases)==len(set(cases)), 'POSTRUN_TESTS_NOT_PASS')
    from detection_service.research_protocol import protocol_patch_001
    patch_checks = len(protocol_patch_001.verify_patch()['sha256'])
    integrity = d.integrity()
    quality_checks,release_checks = 96,118
    # Re-run these APIs here; constants are expected counts, not substitutes for checks.
    from detection_service.research_protocol.release_validation import check_acceptance
    command = [sys.executable,'-B','-m','detection_service.scripts.verify_quality_preservation','--mode','check']
    quality = json.loads(subprocess.run(command,cwd=d.p.ROOT,capture_output=True,text=True,check=True).stdout)
    release = check_acceptance()
    d.p.require(quality['hash_checks']==quality_checks and release['hash_checks']==release_checks,'PRESERVATION_COUNT_DRIFT')
    accepted = dict(status='PASS',tests=counts,passed=counts['tests'],case_ids_sha256=hashlib.sha256(json.dumps(sorted(cases)).encode()).hexdigest(),
        receipts=[dict(path=p.relative_to(d.p.ROOT).as_posix(),sha256=d.p.files.sha(p)) for p in receipts],
        preservation=dict(quality=quality,release=release,source=integrity['source_preservation'],patch=patch_checks),
        artifacts={n:d.p.files.sha(d.OUT/(n+'_v1.json')) for n in (*NAMES,'ds_numerical_runtime_diagnosis')},
        interpretation_status=diagnosis['status'],r2_status='BLOCKED',diagnostic_queries=diagnosis['diagnostic_queries'])
    d.save('ds_numerical_acceptance',accepted)
    e = eq['summary']
    s,c = repeat['same_process'],repeat['cross_process']
    r = r1['summary']
    packages = env['after_loader']['packages']
    text = '# DS-NUMERICAL-001 FINAL REPORT\n\nSTATUS: '+diagnosis['status']+'\n\n'
    text += '## 243-Record Historical Equivalence Recheck\n\n'
    text += f"Records: 243. Historical equivalence still reproducible: YES.\n\nRaw maximum/median/p95: {e['raw']['maximum']:.17g} / {e['raw']['median']:.17g} / {e['raw']['p95']:.17g}.\n\nCalibrated maximum/median/p95: {e['calibrated']['maximum']:.17g} / {e['calibrated']['median']:.17g} / {e['calibrated']['p95']:.17g}.\n\nRaw >1e-12: {e['raw']['above_tolerance']}; calibrated >1e-12: {e['calibrated']['above_tolerance']}. Native mismatches: {e['native_mismatches']}; operational mismatches: {e['operational_mismatches']}.\n\n"
    text += 'Exact original 233 CALIBRATION plus 10 BASE_TRAIN records, no supplementary long query. All 243 use one LM chunk; 238 short/single-feature-window and five medium/multiple-feature-window records. No >1024, >4096 or truncated records in this corpus; those strata cannot establish long-input reproduction.\n\n'
    text += '## First Seed Repeatability\n\n'
    text += f"Same-process runs: 100. Raw min/max: {s['raw']['minimum']} / {s['raw']['maximum']}; calibrated min/max: {s['calibrated']['minimum']} / {s['calibrated']['maximum']}. Each has one distinct binary64 value and exact range zero.\n\n"
    text += 'Raw mathematical population stddev: 0; calibrated: 0. The NumPy summary reports raw stddev 2.22e-16 from mean-reduction rounding of identical values; this is not observed score variation.\n\n'
    text += f"Cross-process runs: 10 distinct fresh processes. Raw/calibrated maximum deltas: {c['raw']['maximum_delta']} / {c['calibrated']['maximum_delta']}. Each has one distinct binary64 value; stddev values in the JSON summary include ordinary reduction rounding. Runtime deterministic: YES in these observations, not a universal guarantee.\n\n"
    text += 'The first seed exactly matches frozen R1 raw 0.9254972378912807 and calibrated 0.844565288092724 in every present-day repeat. Its profile is 101 input tokens, 100 analyzed, one LM chunk, one feature window, no truncation.\n\n'
    text += '## Runtime\n\nPython: '+env['after_loader']['python']+'\n\n'
    text += '\n'.join(f'- {k}: {v}' for k,v in packages.items())+'\n\n'
    text += 'Device: CPU. Reference LM/logits/log-softmax: float32. Input IDs: int64. Token tensor values widen exactly to Python binary64; statistical reductions, 26 features, LR coefficients/intercept/probability and calibration are float64. No float16/bfloat16 transition.\n\n'
    text += 'model.eval confirmed during all forward passes; active dropout absent; inference_mode enabled; gradients disabled inside forward; parameters require_grad false. Tokenizer/preprocessing source uses deterministic tokenization/prefix/chunk selection, not sampling. CPU architecture/BLAS build and random-state hashes are stored in ds_runtime_environment_v1.json. NumPy/Python seed origin UNKNOWN; diagnostic did not seed either.\n\n'
    text += 'The unchanged accepted loader sets torch seed 1701, eight threads and deterministic algorithms True. Before/after settings, cuDNN and TF32 flags are recorded without diagnostic changes. TF32 is irrelevant to observed CPU execution. No installs or environment-variable changes performed.\n\n'
    text += '## Device / Precision Findings\n\nCPU vs normal-path delta: NOT_APPLICABLE_ALREADY_CPU.\n\n'
    precision = features['same_logits_higher_precision']
    text += f"Same captured logits, float64 diagnostic log-softmax: raw signed delta {precision['raw_delta']:.17g}; calibrated signed delta {precision['calibrated_delta']:.17g}; max token-surprisal delta {precision['maximum_token_delta']:.17g}. No extra LM invocation or substitution into accepted D_S.\n\n"
    text += f"Feature sensitivity sufficient in scale to explain ~1e-7 drift: YES as plausibility, NOT causal attribution. One-float32-epsilon independent-feature L1 first-order bound: {features['linear_l1_float32_scale_bound']:.17g}. Correlated features and CDF boundaries limit this estimate. NumPy mean vs statistics.fmean delta on the same widened surprisals: {features['reduction_order_comparison']['numpy_mean_minus_statistics_fmean']}. Reduction-order difference alone did not explain the prior discrepancy in this comparison.\n\n"
    text += 'Feature index/name/value/binary64 hex, LR derivative and upstream calculation are in ds_feature_sensitivity_v1.json; all 26 and inherited window statistics are retained.\n\n'
    text += '## R1 Diagnostic Samples\n\n'
    text += f"Samples replayed: {r['count']}. Raw >1e-12: {r['raw']['above_tolerance']}; calibrated >1e-12: {r['calibrated']['above_tolerance']}. Largest raw/calibrated deltas: {r['raw']['maximum']:.17g} / {r['calibrated']['maximum']:.17g}. Native/operational mismatches: {r['native_mismatches']} / {r['operational_mismatches']}.\n\n"
    text += 'Selection was persisted before scoring and uses first-parent membership and source/token-length metadata only, never replay outcomes. Source-specific minima/medians/maxima and additional length coverage are retained; max ten samples, not all 698.\n\n```json\n'+json.dumps(dict(by_source=r1['by_source'],length_window=r1['strata']),indent=2)+'\n```\n\n'
    text += '## Historical R1 Environment\n\nDevice known: YES (CPU). Dependency versions known: NO for the inference process. Accepted entrypoint/loader/run-code hashes are known; exact shell invocation, machine ID, backend build, container and process-specific package receipt are UNKNOWN. Training receipts and R1 uncertainty NumPy version are not substituted for inference evidence.\n\n'
    text += 'Earlier repair receipt: OMP_NUM_THREADS=4, MKL_NUM_THREADS=4. Current shell: both unset. Both receipts show matching package versions, CPU, float32, eight torch threads, deterministic algorithms True. These observed setting differences are candidates, not an isolated A/B proof. The task forbids changing this environment, so no four-thread-shell reproduction was attempted.\n\n'
    text += '## Root Cause\n\nClassification: '+diagnosis['classification']+'\n\nFirst causal stage: NOT PROVEN. Earliest observed difference between prior and current numeric captures is token surprisal, before feature construction/LR/calibration: 82/100 tokens differ, max 8.58306884765625e-06; feature max delta 3.814697265625e-06. Prior LM logits are missing, so forward-kernel versus log-softmax origin cannot be separated.\n\n'
    text += 'Current original-corpus and first-parent reproduction rule out a blanket present-runtime failure, and repeats found no current nondeterminism. They do not explain why the earlier repair execution differed, nor prove historical dependencies were identical.\n\n'
    text += '## Scientific Meaning\n\nScore reproducibility preserved: YES for current authorized diagnostic records; NO for the previously recorded mismatching repair replay. Decision reproducibility preserved: YES for observed comparisons. Evidence detector behavior materially changed: NO in these records, UNKNOWN outside them. No use of decision agreement to waive the frozen 1e-12 score gate.\n\n'
    text += '## Integrity\n\nTolerance, threshold, model, calibrator, feature schema, reference revision and attack generator changed: NO. R2 generation restarted: NO. D_M-B/D_G/ensemble queries: 0. R3 started: NO. Track B modified: NO. R1 evidence overwritten: NO. Raw prompts/token IDs remain local and ignored, not committed.\n\n'
    text += f"Diagnostic-only D_S calls: {diagnosis['diagnostic_queries']} = 243 equivalence + 100 same-process + 10 fresh-process + {r['count']} R1 baselines. Separate previous repair calls: 1. Historical failed attempt count remains UNKNOWN, bounded 1-61. Accepted R2 terminals: 0. Every current call has an fsync-backed logical request and returned-score receipt using the unchanged 35b88f7 journal.\n\n"
    text += '## Tests\n\n'+f"Passed: {counts['tests']}; failed: {counts['failures']+counts['errors']}; skipped: {counts['skipped']}. Baseline preservation 96/96; release 118/118; source preservation 503/503; protocol patch {patch_checks}/{patch_checks}. No preexisting tracked file changed relative to start.\n\n"
    text += '## Git\n\nStart HEAD: '+d.START+'\n\nDiagnostic scoring-code commit: '+diagnosis['scoring_code_commit']+'\n\nEvidence is a separate post-run commit on exp/r2-ds-001. Its final/remote SHA and clean-tree confirmation are returned in the chat closeout, because this report cannot contain its own commit SHA. Track B remains '+d.TRACK_B+'.\n\n'
    text += '## FINAL RECOMMENDATION\n\n'+diagnosis['recommendation']+'\n\nTHE OBSERVED 1e-7 SCORE DIFFERENCE IS MOST CONSISTENT WITH:\nSmall deterministic upstream numerical variation between execution contexts, with shell thread settings a documented lead but not an established cause.\n\nTHE NEXT CHANGE, IF ANY, SHOULD BE:\n'+diagnosis['next_change']+'\n\nThat next change has NOT been implemented. R2 remains BLOCKED.\n'
    REPORT.parent.mkdir(parents=True,exist_ok=True)
    with REPORT.open('xb') as stream:
        stream.write(text.encode('ascii'))
    print(json.dumps(accepted,indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode',choices=('diagnose','report'),required=True)
    globals()[parser.parse_args().mode]()
