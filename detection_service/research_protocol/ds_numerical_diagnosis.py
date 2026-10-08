"""Diagnostic-only observation of the unchanged accepted D_S runtime."""

import argparse
from contextlib import ExitStack
import csv
from dataclasses import asdict
import hashlib
from importlib.metadata import version
import json
import os
import platform
import random
import subprocess
import sys
from unittest.mock import patch

from detection_service.research_protocol import r2_ds_predeclare as p, ds_runtime
from detection_service.research_protocol.r2_ds_query_journal import QueryJournal

START = '35b88f7fd445e209434e77474862818211c2043c'
TRACK_B = '0cd2d506380cbb3ec513207e4fa66ad422d2b3f2'
OUT = p.OUT / 'diagnostics'
PRIVATE = p.ROOT / 'detection_service/outputs/ds-numerical-001'
CODE = 'detection_service/research_protocol/ds_numerical_diagnosis.py'
THRESHOLD = .5585373573968287
TOLERANCE = 1e-12


def read(name):
    return p.files.read_json(OUT / (name + '_v1.json'))


def save(name, value):
    p.publish(OUT / (name + '_v1.json'), value)


def integrity():
    p.require(p.git('branch', '--show-current').decode().strip() == 'exp/r2-ds-001', 'BRANCH_DRIFT')
    p.require(p.git('rev-parse', 'prep/r3-verifier-001').decode().strip() == TRACK_B, 'TRACK_B_DRIFT')
    p.require(p.git('merge-base', '--is-ancestor', START, 'HEAD') == b'', 'START_NOT_ANCESTOR')
    changed = p.git('diff', START, '--name-only', '--diff-filter=DMRT').decode().strip()
    p.require(not changed, 'PREEXISTING_TRACKED_FILE_CHANGED')
    return dict(source_preservation=p.preserved(), start=START, track_b=TRACK_B,
                tolerance=TOLERANCE, threshold=THRESHOLD,
                generation_queries=0, dmb_queries=0, dg_queries=0, ensemble_queries=0,
                model_changes=False, calibrator_changes=False, feature_schema_changes=False,
                attack_generator_changes=False, r3_started=False)


def stats(values):
    import numpy as np
    a = np.asarray(values, dtype=np.float64)
    return dict(count=len(a), minimum=float(a.min()), maximum=float(a.max()),
                mean=float(a.mean()), standard_deviation=float(a.std()),
                distinct_binary64_values=len({float(v).hex() for v in a}),
                maximum_delta=float(a.max()-a.min()))


def summary(rows):
    import numpy as np
    result = dict(count=len(rows))
    for field in ('raw', 'calibrated'):
        values = [r[field + '_delta'] for r in rows]
        result[field] = dict(maximum=max(values), median=float(np.median(values)),
                            p95=float(np.quantile(values, .95)), above_tolerance=sum(v > TOLERANCE for v in values))
    for field in ('native', 'operational'):
        result[field + '_mismatches'] = sum(r[field + '_mismatch'] for r in rows)
    return result


def environment():
    import numpy as np
    import torch
    from io import StringIO
    from contextlib import redirect_stdout
    stream = StringIO()
    with redirect_stdout(stream):
        np.show_config()
    return dict(python=sys.version, packages={n:version(n) for n in ('torch','transformers','numpy','scipy','scikit-learn')},
        platform=platform.platform(), machine=platform.machine(), processor=platform.processor(),
        numpy_backend=stream.getvalue(), torch_backend=torch.__config__.show(),
        torch_threads=torch.get_num_threads(), torch_interop_threads=torch.get_num_interop_threads(),
        deterministic_algorithms=torch.are_deterministic_algorithms_enabled(),
        cudnn_deterministic=torch.backends.cudnn.deterministic, cudnn_benchmark=torch.backends.cudnn.benchmark,
        tf32_matmul=torch.backends.cuda.matmul.allow_tf32, tf32_cudnn=torch.backends.cudnn.allow_tf32,
        cuda_version=torch.version.cuda, cudnn_version=torch.backends.cudnn.version(),
        torch_initial_seed=torch.initial_seed(),
        torch_rng_state_sha256=hashlib.sha256(torch.get_rng_state().numpy().tobytes()).hexdigest(),
        numpy_rng_state_sha256=hashlib.sha256(repr(np.random.get_state()).encode()).hexdigest(),
        python_rng_state_sha256=hashlib.sha256(repr(random.getstate()).encode()).hexdigest(),
        numpy_seed='UNKNOWN_NOT_SET_BY_DIAGNOSTIC', python_seed='UNKNOWN_NOT_SET_BY_DIAGNOSTIC',
        grad_enabled_outside_inference=torch.is_grad_enabled(),
        variables={k:os.environ.get(k) for k in ('OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS','PYTHONHASHSEED')})


class Capture:
    def __init__(self, runtime):
        self.runtime = runtime
        self.last = None
        self.observation = None
        self.mode_trace = []
        self.precision = False
        self.logits = []
        self.inputs = None
        score = runtime.extractor.engine.score
        def observe(text):
            self.observation = score(text)
            return self.observation
        runtime.extractor.engine.score = observe
        self.hook = runtime.extractor.engine.model.register_forward_hook(self.forward, with_kwargs=True)

    def forward(self, model, args, kwargs, output):
        import torch
        ids = kwargs['input_ids']
        active = [n for n,m in model.named_modules() if isinstance(m,torch.nn.Dropout) and m.training and m.p > 0]
        state = dict(training=model.training, active_dropout=active, grad_enabled=torch.is_grad_enabled(),
                     inference_mode=torch.is_inference_mode_enabled(), input_dtype=str(ids.dtype),
                     input_device=str(ids.device), logits_dtype=str(output.logits.dtype), logits_device=str(output.logits.device),
                     parameter_dtypes=sorted({str(v.dtype) for v in model.parameters()}),
                     parameter_devices=sorted({str(v.device) for v in model.parameters()}),
                     parameters_require_grad=any(v.requires_grad for v in model.parameters()))
        self.mode_trace.append(state)
        if model.training or active:
            raise RuntimeError('STOP_ACTIVE_STOCHASTIC_MODEL_MODE')
        if self.precision:
            self.logits.append((ids.detach().clone(), output.logits.detach().clone()))

    def detect(self, request):
        self.last = self.runtime.detect(request)
        return self.last


def protections(stack):
    from sklearn.linear_model import LogisticRegression
    from detection_service.analysis.statistical_feature_ablation import References
    from detection_service.app.detectors.semantic.calibration import SigmoidCalibrator
    for cls, method in ((LogisticRegression,'fit'),(References,'fit'),(SigmoidCalibrator,'fit_mapping')):
        stack.enter_context(patch.object(cls, method, side_effect=AssertionError('NO_FITTING_ALLOWED')))


def compare(actual, raw, calibrated, capture, sample_id, source=None):
    p.require(actual.status == 'OK', 'DIAGNOSTIC_NON_OK:' + str(actual.error_code))
    return dict(sample_id=sample_id, source=source,
        raw=actual.raw_score, calibrated=actual.calibrated_score, frozen_raw=raw, frozen_calibrated=calibrated,
        raw_delta=abs(actual.raw_score-raw), calibrated_delta=abs(actual.calibrated_score-calibrated),
        native_mismatch=actual.native_binary_prediction != int(calibrated >= .5),
        operational_mismatch=int(actual.calibrated_score >= THRESHOLD) != int(calibrated >= THRESHOLD),
        input_tokens=actual.input_tokens, tokens_analyzed=actual.tokens_analyzed, truncated=actual.truncated,
        lm_chunks=capture.last.input_coverage.inference_chunks, feature_windows=capture.last.features.window_count)


def strata(rows):
    groups = {}
    for key, predicate in (
        ('short_lt128',lambda r:r['input_tokens'] < 128),
        ('medium_128_1024',lambda r:128 <= r['input_tokens'] <= 1024),
        ('gt1024',lambda r:r['input_tokens'] > 1024), ('gt4096',lambda r:r['input_tokens'] > 4096),
        ('single_lm_chunk',lambda r:r['lm_chunks'] == 1), ('multiple_lm_chunks',lambda r:r['lm_chunks'] > 1),
        ('single_feature_window',lambda r:r['feature_windows'] == 1),
        ('multiple_feature_windows',lambda r:r['feature_windows'] > 1),
        ('truncated',lambda r:r['truncated']), ('not_truncated',lambda r:not r['truncated'])):
        subset = [r for r in rows if predicate(r)]
        groups[key] = summary(subset) if subset else dict(count=0, status='NO_CORPUS_COVERAGE')
    return groups


def equivalence():
    from detection_service.research_protocol.ds_equivalence import historical_inputs
    from detection_service.research_protocol.release_validation import offline
    from detection_service.research_protocol.r2_ds_generate_run import target_isolation
    baseline = integrity()
    before = environment()
    with offline(), ExitStack() as stack:
        protections(stack)
        population, authority = historical_inputs()
        p.require(len(population) == 243, 'EXACT_243_REQUIRED')
        with target_isolation():
            adapter = ds_runtime.accepted_ds_adapter()
            capture = Capture(adapter._load_live())
            adapter._live = capture
            save('ds_runtime_environment', dict(before_loader=before, after_loader=environment(),
                 numerical_settings_changed_by_diagnostic=False,
                 accepted_loader_settings='Existing loader sets torch seed 1701, threads 8, deterministic algorithms True; unchanged'))
            journal = QueryJournal(PRIVATE/'equivalence.jsonl','ds-numerical-equivalence-v1','CURRENT_DIAGNOSTIC')
            rows = []
            try:
                for i,item in enumerate(population):
                    sid = item['row']['record_id']
                    actual = journal.score(adapter,item['text'],sid,'BASELINE_REPLAY')
                    row = compare(actual,item['raw'],item['calibrated'],capture,sid)
                    row['authority_kind'] = item['evidence_kind']
                    if 'vector' in item:
                        import numpy as np
                        current = np.asarray([capture.last.metadata['b2_features'][n] for n in capture.runtime.model.manifest['feature_names']])
                        row['max_feature_delta'] = float(np.max(np.abs(current-item['vector'])))
                    rows.append(row)
                    if (i+1) % 50 == 0:
                        print(json.dumps(dict(equivalence_completed=i+1,total=243)),flush=True)
            finally:
                journal.close()
            save('ds_243_equivalence_recheck', dict(summary=summary(rows), rows=rows, authority=authority,
                strata=strata(rows), model_mode_trace=capture.mode_trace, diagnostic_queries=journal.sequence,
                purpose='DIAGNOSTIC_ONLY', integrity=baseline, code_commit=p.git('rev-parse','HEAD').decode().strip(),
                truth_label_note='Journal helper records truth_label=1; diagnostic comparison does not use labels, corpus membership and original labels remain unchanged'))


def first():
    from detection_service.research_protocol.r2_ds_replay_diagnosis import first_seed
    return first_seed()


def precision_analysis(capture, text, actual):
    import numpy as np
    import torch
    from detection_service.app.detectors.statistical.features import extract_features, _windows
    from detection_service.app.detectors.statistical_risk.schema import FEATURE_NAMES
    from detection_service.app.detectors.semantic.calibration import log_odds
    runtime = capture.runtime
    observation = capture.observation
    p.require(len(capture.logits) == 1, 'FIRST_SEED_SINGLE_CHUNK_REQUIRED')
    ids, logits = capture.logits[0]
    labels = ids[:,1:]
    normal = -torch.log_softmax(logits[:,:-1,:],dim=-1).gather(2,labels.unsqueeze(-1)).squeeze(-1)
    high = -torch.log_softmax(logits[:,:-1,:].double(),dim=-1).gather(2,labels.unsqueeze(-1)).squeeze(-1)
    p.require(normal[0].tolist() == observation.surprisals, 'SAME_LOGITS_NORMAL_PATH_RECONSTRUCTION_FAILED')
    cfg = runtime.extractor.config
    high_features = extract_features(high[0].tolist(),cfg.window_size,cfg.window_stride,cfg.provisional_high_surprisal_threshold,text)
    item = dict(surprisals=high[0].tolist(),input_tokens=observation.input_tokens,tokens_analyzed=observation.tokens_analyzed,
                v1_features=[getattr(high_features,n) for n in FEATURE_NAMES])
    high_vector = runtime.model.transform(item)
    vector = np.asarray([capture.last.metadata['b2_features'][n] for n in runtime.model.manifest['feature_names']])
    high_raw = float(runtime.model.predict(high_vector[None,:])[0])
    high_cal = float(runtime.calibrator.predict(np.asarray([high_raw]))[0])
    z = float((vector @ runtime.model.coef.T).item()+runtime.model.intercept[0])
    sensitivity = []
    for j,name in enumerate(runtime.model.manifest['feature_names']):
        step = float(np.finfo(np.float32).eps * max(1.,abs(vector[j])))
        derivative = float(actual.raw_score*(1-actual.raw_score)*runtime.model.coef[0,j])
        trial = vector.copy()
        trial[j] += step
        changed = float(runtime.model.predict(trial[None,:])[0])
        sensitivity.append(dict(index=j,name=name,value=float(vector[j]),binary64_hex=float(vector[j]).hex(),
            coefficient=float(runtime.model.coef[0,j]),perturbation=step,analytic_derivative=derivative,
            linear_probability_delta=derivative*step,exact_probability_delta=changed-actual.raw_score,
            upstream_source=('statistical/features.py:extract_features' if j<10 else
                'analysis/statistical_feature_ablation.py:References.transform B1 length reference' if j<16 else
                'analysis/statistical_feature_ablation.py:References.transform B2 quantiles/top means')))
    seq = np.asarray(observation.surprisals,dtype=np.float64)
    window_means = [float(np.mean(w)) for w in _windows(observation.surprisals,cfg.window_size,cfg.window_stride)]
    reduction_mean_delta = float(np.mean(seq))-capture.last.features.mean_surprisal
    dtype = dict(input_tensors=dict(dtype=str(ids.dtype),device=str(ids.device)),
        reference_weights=dict(dtype=str(next(runtime.extractor.engine.model.parameters()).dtype),device=str(next(runtime.extractor.engine.model.parameters()).device)),
        logits=dict(dtype=str(logits.dtype),device=str(logits.device)),
        log_softmax=dict(dtype=str(normal.dtype),device=str(normal.device)),
        probability_tensor='Not materialized in accepted path: log_softmax plus gather',
        token_surprisals='torch.float32 -> Python float binary64, exact widening',
        whole_prompt_perplexity='Python float binary64: statistics.fmean then math.exp',
        sliding_window_perplexities='Python float binary64: statistics.fmean then math.exp',
        statistical_summaries='Python binary64 statistics; NumPy float64 quantiles/median/reference transform',
        feature_vector=str(vector.dtype), lr_coefficients=str(runtime.model.coef.dtype),lr_intercept=str(runtime.model.intercept.dtype),
        lr_decision_function=dict(dtype='float64',value=z),raw_probability=dict(dtype='float64',value=actual.raw_score),
        calibration_log_odds=dict(dtype='float64',value=float(log_odds(np.asarray([actual.raw_score]))[0])),
        calibration_output=dict(dtype='float64',value=actual.calibrated_score),model_mode=capture.mode_trace[0],
        cpu_comparison='NOT_APPLICABLE_ALREADY_CPU',tf32_relevant=False,
        historical_device=dict(status='KNOWN',value='cpu',evidence=ds_runtime.BINDING),
        historical_dtype='UNKNOWN_PER_RUN; accepted loader default float32, native R1 journal has no dtype receipt')
    save('ds_dtype_device_trace',dtype)
    save('ds_feature_sensitivity',dict(features=sensitivity, inherited_features=capture.last.features.model_dump(mode='json'),
        token_count=observation.input_tokens,tokens_analyzed=len(seq),window_mean_nll=window_means,
        same_logits_higher_precision=dict(normal_dtype=str(normal.dtype),diagnostic_dtype=str(high.dtype),
            logits_sha256=hashlib.sha256(logits.cpu().numpy().tobytes()).hexdigest(),
            maximum_token_delta=float(np.max(np.abs(high[0].numpy()-seq))),
            high_feature_vector=high_vector.tolist(),maximum_feature_delta=float(np.max(np.abs(high_vector-vector))),
            raw=high_raw,calibrated=high_cal,raw_delta=high_raw-actual.raw_score,calibrated_delta=high_cal-actual.calibrated_score),
        reduction_order_comparison=dict(numpy_mean_minus_statistics_fmean=reduction_mean_delta),
        linear_l1_float32_scale_bound=sum(abs(r['linear_probability_delta']) for r in sensitivity),
        limitation='Plausibility only: historical logits/features absent. One-feature perturbations are analytical, not detector substitutions; CDF jumps are not bounded by local LR derivative.',
        reference_lm_queries=0,detector_modified=False))
    p.publish(PRIVATE/'first_seed_numeric_capture.json',dict(observation=asdict(observation),vector=vector.tolist(),input_ids=ids.tolist()))


def repeat(worker=None):
    from detection_service.research_protocol.release_validation import offline
    from detection_service.research_protocol.r2_ds_generate_run import target_isolation
    import detection_service.app.detectors.semantic.calibration
    p.require(read('ds_243_equivalence_recheck')['summary']['count'] == 243,'FIRST_TEST_REQUIRED')
    integrity()
    seed,text,stored = first()
    name = 'repeat' if worker is None else 'worker_'+str(worker)
    with offline(),ExitStack() as stack:
        protections(stack)
        with target_isolation():
            adapter = ds_runtime.accepted_ds_adapter()
            capture = Capture(adapter._load_live())
            adapter._live = capture
            journal = QueryJournal(PRIVATE/(name+'.jsonl'),'ds-numerical-'+name,'CURRENT_DIAGNOSTIC')
            rows = []
            try:
                for i in range(100 if worker is None else 1):
                    capture.precision = worker is None and i == 0
                    actual = journal.score(adapter,text,seed['parent_sample_id'],'BASELINE_REPLAY')
                    rows.append(compare(actual,float(stored['raw_score']),float(stored['calibrated_score']),capture,seed['parent_sample_id'],seed['source']))
                    if capture.precision:
                        precision_analysis(capture,text,actual)
                        capture.logits.clear()
                    if (i+1) % 25 == 0:
                        print(json.dumps(dict(same_process_completed=i+1)),flush=True)
            finally:
                journal.close()
            p.publish(PRIVATE/(name+'_results.json'),dict(rows=rows,environment=environment(),mode_trace=capture.mode_trace,
                pid=os.getpid(),diagnostic_queries=journal.sequence))


def cross():
    p.require((PRIVATE/'repeat_results.json').exists(),'SAME_PROCESS_TEST_REQUIRED')
    for i in range(10):
        subprocess.run([sys.executable,'-B','-m','detection_service.research_protocol.ds_numerical_diagnosis','--mode','worker','--index',str(i)],
                       cwd=p.ROOT,check=True)
        print(json.dumps(dict(fresh_process_completed=i+1,total=10)),flush=True)
    same = p.files.read_json(PRIVATE/'repeat_results.json')
    workers = [p.files.read_json(PRIVATE/('worker_'+str(i)+'_results.json')) for i in range(10)]
    rows = [w['rows'][0] for w in workers]
    save('ds_repeatability_first_seed', dict(same_process={k:stats([r[k] for r in same['rows']]) for k in ('raw','calibrated')},
        cross_process={k:stats([r[k] for r in rows]) for k in ('raw','calibrated')},
        combined={k:stats([r[k] for r in same['rows']+rows]) for k in ('raw','calibrated')},
        worker_pids=[w['pid'] for w in workers],same_process_pid=same['pid'],
        same_process_mode_trace=same['mode_trace'],worker_mode_traces=[w['mode_trace'] for w in workers],
        worker_environments=[w['environment'] for w in workers],diagnostic_queries=110))


def select_r1(parents):
    chosen = [parents[0]]
    # Metadata-only extrema and median for each source, plus coverage profiles.
    for source in sorted({r['source'] for r in parents}):
        ordered = sorted((r for r in parents if r['source'] == source),key=lambda r:(int(r['input_tokens']),r['parent_sample_id']))
        for r in (ordered[0],ordered[len(ordered)//2],ordered[-1]):
            if r not in chosen:
                chosen.append(r)
    for predicate in (lambda r:int(r['input_tokens'])>1024,lambda r:int(r['input_tokens'])>4096,
                      lambda r:128<int(r['input_tokens'])<=1024):
        candidates = sorted((r for r in parents if predicate(r)),key=lambda r:r['parent_sample_id'])
        if candidates and candidates[0] not in chosen:
            chosen.append(candidates[0])
    return chosen[:10]


def r1():
    from detection_service.research_protocol.release_validation import offline
    from detection_service.research_protocol.r2_ds_generate_run import target_isolation
    import detection_service.app.detectors.semantic.calibration
    p.require(read('ds_repeatability_first_seed')['diagnostic_queries'] == 110,'REPEATABILITY_REQUIRED')
    integrity()
    parents = p.parents()
    texts = p.private_parents()
    with (p.R1/'r1_predictions_v1.csv').open(encoding='utf-8',newline='') as stream:
        frozen = {r['sample_id']:r for r in csv.DictReader(stream) if r['detector_id']=='ds_v2'}
    parents = [dict(r,input_tokens=int(frozen[r['parent_sample_id']]['input_tokens'])) for r in parents]
    selected = select_r1(parents)
    p.publish(PRIVATE/'r1_selection_before_scoring.json', selected)
    with offline(),ExitStack() as stack:
        protections(stack)
        with target_isolation():
            adapter = ds_runtime.accepted_ds_adapter()
            capture = Capture(adapter._load_live())
            adapter._live = capture
            journal = QueryJournal(PRIVATE/'r1.jsonl','ds-numerical-r1-v1','CURRENT_DIAGNOSTIC')
            rows = []
            try:
                for seed in selected:
                    sid = seed['parent_sample_id']
                    actual = journal.score(adapter,texts[sid],sid,'BASELINE_REPLAY')
                    rows.append(compare(actual,float(frozen[sid]['raw_score']),float(frozen[sid]['calibrated_score']),capture,sid,seed['source']))
            finally:
                journal.close()
            save('ds_r1_diagnostic_replays',dict(rows=rows,summary=summary(rows),strata=strata(rows),
                by_source={s:summary([r for r in rows if r['source']==s]) for s in sorted({r['source'] for r in rows})},
                selection='First parent plus source token-length minimum/median/maximum, then >1024/>4096/128-1024 metadata representatives; tie sample ID; no score-based selection',
                selected_metadata=selected,diagnostic_queries=journal.sequence,model_mode_trace=capture.mode_trace))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode',required=True,choices=('equivalence','repeat','cross','worker','r1','integrity'))
    parser.add_argument('--index',type=int)
    args = parser.parse_args()
    if args.mode == 'worker':
        p.require(args.index is not None and 0 <= args.index < 10,'WORKER_INDEX_REQUIRED')
        repeat(args.index)
    else:
        globals()[args.mode]()


if __name__ == '__main__':
    main()
