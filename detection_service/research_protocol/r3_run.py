"""Explicit Phase-1 preflight and single-invocation authoritative R3 runner."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import json
import os
from time import perf_counter

from detection_service.research_protocol import r3_inputs as i, r3_preparation as d
from detection_service.research_protocol import r3_generator as g
from detection_service.research_protocol.r3_readonly_cache import verified_reads
from detection_service.research_protocol.regime import require

RUN_ID = 'R3-ENSEMBLE-001-AUTHORITATIVE-V1'
CODE = ('r3_run.py', 'r3_generator.py', 'r3_inputs.py', 'r3_readonly_cache.py')
PREFLIGHT = i.OUT / 'r3_runtime_preflight_v1.json'


def now():
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


class Oracle:
    def __init__(self, label, adapter):
        self.label, self.adapter = label, adapter
        live = adapter._live
        if label == 'D_S':
            require(live.extractor.config.device == 'cpu' and live.extractor.config.max_analysis_tokens == 4096,
                    'DS_RUNTIME_POLICY_DRIFT')
            self.tokenizer = live.extractor.engine.tokenizer
        else:
            self.tokenizer = live.tokenizer
        require(self.tokenizer.is_fast, 'EXACT_TOKENIZER_OFFSETS_REQUIRED')

    def coverage_end(self, text):
        if self.label == 'D_G':
            # The frozen guard covers the entire token stream, including the tail.
            return len(text)
        encoded = self.tokenizer(text, add_special_tokens=self.label == 'D_M-B', truncation=True,
            max_length=4096 if self.label == 'D_S' else 256, return_offsets_mapping=True)
        return max((b for a, b in encoded['offset_mapping'] if b > a), default=0)

    def __call__(self, text):
        record = self.adapter.predict(text, sample_id='R3-PROBE-' + d.sha(text), truth_label=1)
        value = record.model_dump(mode='json')
        value['calibrated_probability'] = record.calibrated_score
        return value


def load_stack():
    os.environ.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', HF_DATASETS_OFFLINE='1')
    import torch
    from detection_service.research_protocol.adapters import primary_adapters
    from detection_service.research_protocol.ds_runtime import accepted_ds_adapter
    from detection_service.research_protocol.r0_operational import verified_policy
    policy = verified_policy()
    require(tuple(point.threshold for point in policy.manifest.points) == d.THRESHOLDS, 'R3_THRESHOLD_DRIFT')
    adapters = primary_adapters()
    adapters = (accepted_ds_adapter(), *adapters[1:])
    # Use the accepted CPU recipe, not an inferred faster device or precision.
    recipe = i.p.files.read_json(i.p.ROOT / 'artifacts/models/dm_b_v1/model_config.json')['recipe']
    accepted_environment = i.p.files.read_json(i.p.OUT / 'ds_numerical_disposition_v1.json')['gate']['environment']
    require(recipe['cpu_threads'] == accepted_environment['torch_threads'] == 8, 'FROZEN_CPU_CONTEXT_CONFLICT')
    torch.set_num_threads(recipe['cpu_threads'])
    identities = []
    for label, adapter in zip(d.DOMAIN, adapters):
        identity = adapter._identity
        require(i.p.digest(identity['model_artifact_path']) == identity['model_hash'], 'R3_WEIGHT_HASH_DRIFT')
        if label == 'D_M-B':
            require(identity['model_hash'] == '0bb192d2c468530479fa8ec0786f35d8bf5a8287e4ee401a953292d221736844', 'DMB_SHA_DRIFT')
        if label == 'D_G':
            require(identity['model_name'] == 'meta-llama/Llama-Prompt-Guard-2-22M' and
                    identity['model_revision'] == '11614a155199674a0a95e6602d6ab0417b790ed0', 'DG_IDENTITY_DRIFT')
        adapter._live = adapter._load_live()
        model = adapter._live.extractor.engine.model if label == 'D_S' else adapter._live.model
        require(not model.training and all(str(p.dtype) == 'torch.float32' for p in model.parameters()),
                'R3_MODEL_MODE_OR_DTYPE_DRIFT')
        identities.append(dict(label=label, detector_id=adapter.detector_id, model_sha256=identity['model_hash'],
            model_revision=identity['model_revision'], reference_revision=identity['reference_model_revision'],
            threshold=policy.manifest.points[len(identities)].threshold,
            threshold_id=policy.manifest.points[len(identities)].threshold_id))
    return {label: Oracle(label, adapter) for label, adapter in zip(d.DOMAIN, adapters)}, identities


def preflight():
    from detection_service.research_protocol.release_validation import offline
    from detection_service.research_protocol.ds_numerical_diagnosis import environment
    baseline = i.gate()
    seed_commit = i.p.committed(i.SEEDS)
    require(not PREFLIGHT.exists(), 'R3_PREFLIGHT_ALREADY_RECORDED')
    journal = g.Journal(i.PRIVATE / 'preflight_queries_v1.jsonl')
    records, identities = {}, []
    try:
        with offline(), verified_reads():
            oracles, identities = load_stack()
            evaluator = g.CandidateEvaluator(oracles, journal, 'PERMITTED-SYNTHETIC-PREFLIGHT')
            text = 'Please summarize the agenda for an ordinary team meeting.'
            records = evaluator.query(text, 'RUNTIME_PREFLIGHT')
            ends = {label: oracle.coverage_end(text) for label, oracle in oracles.items()}
            require(all(0 < end <= len(text) for end in ends.values()), 'PREFLIGHT_COVERAGE_INVALID')
            env = environment()
    finally:
        journal.close()
    value = dict(artifact_version='r3_runtime_preflight_v1', status='PASS', created_at=now(),
        integration_baseline_commit=baseline, seed_freeze_commit=seed_commit, identities=identities,
        environment=env, fixture_text_sha256=d.sha(text), fixture_kind='PERMITTED_SYNTHETIC_TEXT',
        synthetic_text_model_calls=3, R3_attack_queries=0, verifier_queries=0, protected_queries=0,
        fixture_scores=records, coverage_ends=ends, journal_sha256=i.p.files.sha(i.PRIVATE / 'preflight_queries_v1.jsonl'),
        code_sha256={name: i.p.files.sha(i.p.ROOT / 'detection_service/research_protocol' / name) for name in CODE},
        read_cache='Task-local exact file hash and duplicate-key JSON validation on first access; metadata stamp checks per access; all cached bytes and JSON objects rechecked on exit. No frozen file edits.',
        detector_identity='PASS', thresholds='PASS', journaling='PASS', no_training=True)
    i.p.publish(PREFLIGHT, value)
    print(json.dumps(dict(status='R3_PREFLIGHT_PASS', identities=identities, model_calls=3, attack_queries=0), indent=2), flush=True)


def generation():
    from detection_service.research_protocol.release_validation import offline
    from detection_service.research_protocol.ds_numerical_diagnosis import environment
    baseline = i.gate()
    require(not i.p.git('status', '--porcelain').decode().strip(), 'CLEAN_GENERATION_START_REQUIRED')
    preflight = i.p.files.read_json(PREFLIGHT)
    implementation = i.p.committed(i.p.ROOT / 'detection_service/research_protocol/r3_generator.py')
    preflight_commit = i.p.committed(PREFLIGHT)
    require(i.p.git('rev-parse', 'HEAD').decode().strip() == preflight_commit, 'R3_RUN_CODE_HEAD_REQUIRED')
    require(preflight['status'] == 'PASS' and all(i.p.files.sha(i.p.ROOT / 'detection_service/research_protocol' / name) == expected
        for name, expected in preflight['code_sha256'].items()), 'R3_PREFLIGHT_CODE_DRIFT')
    parents, texts = i.frozen_parents(), i.private_texts()
    require(not (i.PRIVATE / 'run_receipt_v1.json').exists(), 'R3_SINGLE_INVOCATION_NO_SILENT_RESTART')
    contract_paths = ('r3_predeclaration_v1.json', 'r3_generator_contract_v1.json', 'r3_seed_policy_v1.json')
    started = now()
    receipt = dict(run_id=RUN_ID, started_at=started, integration_baseline_commit=baseline,
        seed_freeze_commit=i.p.committed(i.SEEDS), implementation_commit=implementation,
        execution_commit=preflight_commit, seed_manifest_sha256=i.p.files.sha(i.SEEDS),
        contract_sha256={name: i.p.files.sha(i.OUT / name) for name in contract_paths},
        operator_registry_sha256=i.p.digest('detection_service/research_protocol/r2_dmb_design.py'),
        query_budget_contract_sha256=i.p.files.sha(i.OUT / 'r3_predeclaration_v1.json'),
        uncertainty_policy_sha256=i.p.digest('artifacts/research_protocol/uncertainty/uncertainty_contract_v1.json'),
        runtime_preflight_sha256=i.p.files.sha(PREFLIGHT), detector_identities=preflight['identities'],
        candidate_evaluation_ceiling=len(parents) * 61, detector_call_ceiling=len(parents) * 183,
        authoritative_prior_attack_calls=0, verifier_calls=0, protected_calls=0)
    i.p.publish(i.PRIVATE / 'run_receipt_v1.json', receipt)
    journal = g.Journal(i.PRIVATE / 'generation_queries_v1.jsonl')
    terminals = []
    timer = perf_counter()
    current_parent = None
    try:
        with offline(), verified_reads(), (i.PRIVATE / 'generation_v1.jsonl').open('xb') as stream:
            oracles, identities = load_stack()
            require(identities == preflight['identities'], 'R3_RUNTIME_IDENTITY_DRIFT')
            i.p.publish(i.PRIVATE / 'generation_environment_v1.json', environment())
            for index, parent in enumerate(parents, 1):
                current_parent = parent['sample_id']
                evaluator = g.CandidateEvaluator(oracles, journal, current_parent)
                result = g.generate(texts[current_parent], evaluator)
                metadata = dict(sample_id='R3-' + d.sha(current_parent), parent_sample_id=current_parent,
                    source=parent['source'], lineage_id=parent['lineage_id'], dataset_id=parent['dataset_id'],
                    dataset_revision=parent['dataset_revision'], attack_family=parent['attack_family'],
                    parent_text_sha256=parent['parent_text_sha256'], terminal_text_sha256=d.sha(result['text']),
                    target_detector='ALL', truth_label=1, threat_regime='R3_ENSEMBLE_TARGETED',
                    inverse_reconstruction=True, validity_status='VALID_REVERSIBLE_TEXT_PRESERVING',
                    terminal_scores=result['scores'], baseline_scores=result['baseline_scores'],
                    terminal_decisions={label: int(result['scores'][label] >= threshold) for label, threshold in zip(d.DOMAIN, d.THRESHOLDS)},
                    success=result['success'], objective=result['objective'], mechanism=result['mechanism'],
                    operators_used=list(dict.fromkeys(e['operator'] for e in result['script']['edits'])),
                    candidate_evaluations=result['candidate_evaluations'], detector_calls=result['individual_detector_queries'],
                    logical_requests=result['logical_requests'], analyzed_parent_character_end=result['coverage_end'])
                journal.write('TERMINAL', parent_sample_id=current_parent, metadata=metadata)
                stream.write(d.canonical_json(dict(metadata=metadata, private_generation=result)) + b'\n')
                stream.flush()
                os.fsync(stream.fileno())
                terminals.append(metadata)
                print(json.dumps(dict(stage='R3_ALL_GENERATION', completed=index, total=len(parents),
                    successes=sum(t['success'] for t in terminals), candidate_evaluations=sum(t['candidate_evaluations'] for t in terminals),
                    detector_calls=sum(t['detector_calls'] for t in terminals), elapsed_seconds=perf_counter()-timer)), flush=True)
    except BaseException as exc:
        i.p.publish(i.PRIVATE / 'interruption_v1.json', dict(status='BLOCKED', run_id=RUN_ID, reason=str(exc),
            completed_parents=len(terminals), current_parent=current_parent, partial_results_accepted=False,
            no_silent_restart=True, verifier_queries=0, protected_queries=0))
        raise
    finally:
        journal.close()
    i.gate()
    i.p.publish(i.PRIVATE / 'generation_complete_v1.json', dict(status='COMPLETE_PENDING_TERMINAL_FREEZE',
        run_id=RUN_ID, parents=len(terminals), successes=sum(t['success'] for t in terminals),
        started_at=started, completed_at=now(), runtime_seconds=perf_counter()-timer,
        source_counts=dict(Counter(t['source'] for t in terminals)), verifier_queries=0, protected_queries=0))
    print(json.dumps(dict(status='R3_GENERATION_COMPLETE_TERMINAL_FREEZE_REQUIRED', parents=len(terminals))), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=('preflight', 'generate'), required=True)
    args = parser.parse_args()
    (preflight if args.mode == 'preflight' else generation)()
