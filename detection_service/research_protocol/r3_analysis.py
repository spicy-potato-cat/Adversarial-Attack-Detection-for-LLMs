"""Frozen-core R3 analysis and metadata-only Phase-2 failure population."""
from collections import Counter
import hashlib
import json
import statistics

from detection_service.research_protocol import r3_inputs as i, r3_scoring as scoring, r3_freeze as freeze
from detection_service.research_protocol import protocol_lock, protocol_patch_001
from detection_service.research_protocol.core_metrics import evaluate_core
from detection_service.research_protocol.metric_catalog import metric_catalog
from detection_service.research_protocol.operating_policy import native_prediction
from detection_service.research_protocol.r2_ds_transfer_run import aligned
from detection_service.research_protocol.r3_readonly_cache import verified_reads
from detection_service.research_protocol.uncertainty import BootstrapConfig, bootstrap_metrics
from detection_service.research_protocol.r0_operational import verified_policy
from detection_service.research_protocol.regime import require

IDS = ('ds_v2', 'dm_b_v1', 'dg_v1')
FAILURES = i.OUT / 'r3_all_three_failure_manifest_v1.json'


def describe(rows, decisions):
    n = len(rows)
    successful = sum(decisions[r['sample_id']] == (0, 0, 0) for r in rows)
    calls = [r['candidate_evaluations'] for r in rows]
    return dict(parent_count=n, all_three_successes=successful, target_success_rate=successful/n if n else None,
        FN={label: sum(decisions[r['sample_id']][index] == 0 for r in rows) for index, label in enumerate(IDS)},
        failure_patterns=dict(sorted(Counter(''.join(str(1-bit) for bit in decisions[r['sample_id']]) for r in rows).items())),
        candidate_evaluations=sum(calls), detector_calls=3*sum(calls),
        candidate_queries_mean=statistics.mean(calls) if calls else None,
        candidate_queries_median=statistics.median(calls) if calls else None,
        candidate_queries_min=min(calls) if calls else None, candidate_queries_max=max(calls) if calls else None,
        candidate_evaluations_per_success=sum(calls)/successful if successful else None,
        mechanism_counts=dict(Counter(r['mechanism'] for r in rows)))


def transitions(rows, decisions, original):
    result = {label: dict(catch_to_catch=0, catch_to_miss=0, miss_to_catch=0, miss_to_miss=0) for label in IDS}
    for row in rows:
        for index, label in enumerate(IDS):
            before = original[(row['parent_sample_id'], label)].operational_binary_prediction
            after = decisions[row['sample_id']][index]
            key = ('catch' if before else 'miss') + '_to_' + ('catch' if after else 'miss')
            result[label][key] += 1
    return result


def analyze():
    i.gate()
    require(not FAILURES.exists(), 'R3_FAILURE_POPULATION_ALREADY_FROZEN')
    prediction_commit = i.p.committed(scoring.PREDICTION_MANIFEST)
    require(scoring.PREDICTIONS.read_bytes() == i.p.git('show', prediction_commit + ':' + scoring.PREDICTIONS.relative_to(i.p.ROOT).as_posix()), 'COMMITTED_R3_PREDICTIONS_REQUIRED')
    prediction_metadata = i.p.files.read_json(scoring.PREDICTION_MANIFEST)
    require(prediction_metadata['status'] == 'PASS' and i.p.files.sha(scoring.PREDICTIONS) == prediction_metadata['prediction_sha256'], 'R3_PREDICTIONS_DRIFT')
    rows = i.p.files.read_json(freeze.TERMINALS)['terminals']
    with verified_reads():
        value, policy = scoring.manifest(), verified_policy()
        records = i.read_predictions(scoring.PREDICTIONS, policy)
        table = aligned(value, records, policy)
        bundle = protocol_patch_001.evaluate_official(protocol_lock.ExperimentRequest(manifest=value, bootstrap_unit='LINEAGE_CLUSTERED'),
            tuple(native_prediction(record) for record in records))
        require(bundle.core_metrics == evaluate_core(table), 'R3_AGGREGATE_RECONSTRUCTION_CONFLICT')
        decisions = {r.sample_id: r.decisions for r in table.rows}
        require(all((decisions[r['sample_id']] == (0, 0, 0)) == r['success'] for r in rows), 'R3_TARGET_SUCCESS_REPLAY_CONFLICT')
        summary = describe(rows, decisions)
        require(summary['all_three_successes'] == bundle.core_metrics.common_mode.all_three_fn_count, 'R3_COMMON_MODE_DENOMINATOR_CONFLICT')
        from detection_service.research_protocol.r2_ds_analysis import source_table
        sources = {}
        for source in sorted({r['source'] for r in rows}):
            selected = [r for r in rows if r['source'] == source]
            sub = source_table(value, records, policy, source)
            core = evaluate_core(sub)
            names = tuple(name for name in metric_catalog(core) if name.startswith(('pair/', 'pattern/', 'recovery/', 'all_three/')) or name.endswith('/fnr'))
            ci = bootstrap_metrics(sub, names, BootstrapConfig(unit='LINEAGE_CLUSTERED', domain='ATTACK_ONLY'))
            sources[source] = dict(**describe(selected, decisions), inherited_lineages=len({r['lineage_id'] for r in selected}),
                core=core.model_dump(mode='json'), uncertainty=ci.model_dump(mode='json'))
        operators = {mechanism: describe([r for r in rows if r['mechanism'] == mechanism], decisions)
            for mechanism in (*i.design.OPERATORS, 'BENIGN_CONTEXT_PADDING',
                *['GLOBAL_' + op for op in i.design.OPERATORS], 'UNCHANGED')}
        original = {(r.sample_id, r.detector_id): r for r in i.read_predictions(i.p.R1 / 'r1_predictions_v1.csv', policy)}
        paired = dict(overall=transitions(rows, decisions, original),
            by_source={source: transitions([r for r in rows if r['source'] == source], decisions, original) for source in sources},
            by_operator={mechanism: transitions([r for r in rows if r['mechanism'] == mechanism], decisions, original) for mechanism in operators},
            causal_claim=False)
        child = {(r.sample_id, r.detector_id): r for r in records}
        coverage = {}
        for label in IDS:
            observations = []
            for row in rows:
                before = original[(row['parent_sample_id'], label)]
                after = child[(row['sample_id'], label)]
                observations.append(dict(sample_id=row['sample_id'], parent_sample_id=row['parent_sample_id'],
                    source=row['source'], mechanism=row['mechanism'], all_three_success=row['success'],
                    parent_input_tokens=before.input_tokens, child_input_tokens=after.input_tokens,
                    parent_tokens_analyzed=before.tokens_analyzed, child_tokens_analyzed=after.tokens_analyzed,
                    parent_truncated=before.truncated, child_truncated=after.truncated))
            coverage[label] = dict(rows=observations, parent_truncated=sum(r['parent_truncated'] for r in observations),
                child_truncated=sum(r['child_truncated'] for r in observations),
                new_truncation=sum(r['child_truncated'] and not r['parent_truncated'] for r in observations),
                successful_with_new_truncation=sum(r['all_three_success'] and r['child_truncated'] and not r['parent_truncated'] for r in observations))
        comparisons = {}
        wanted = {r['parent_sample_id']: r for r in rows}
        for name, directory in (('R2_DMB', 'r2_dmb'), ('R2_DS', 'r2_ds')):
            prefix = directory
            terminals = i.p.files.read_json(i.p.ROOT / i.p.files.OUT / directory / (prefix + '_terminal_manifest_v1.json'))['terminals']
            past = i.read_predictions(i.p.ROOT / i.p.files.OUT / directory / (prefix + '_predictions_v1.csv'), policy)
            lookup = {(r.sample_id, r.detector_id): r.operational_binary_prediction for r in past}
            full_failures = sum(all(lookup[(r['sample_id'], label)] == 0 for label in IDS) for r in terminals)
            require(full_failures == 0, 'ACCEPTED_R2_COMMON_MODE_INPUT_CONFLICT')
            matched = []
            for terminal in terminals:
                if terminal['parent_sample_id'] in wanted:
                    current = wanted[terminal['parent_sample_id']]
                    matched.append(dict(parent_sample_id=terminal['parent_sample_id'], inherited_lineage=current['lineage_id'],
                        past_decisions={label: lookup[(terminal['sample_id'], label)] for label in IDS},
                        R3_decisions=dict(zip(IDS, decisions[current['sample_id']]))))
            comparisons[name] = dict(full_population=len(terminals), matched_parent_count=len(matched), rows=matched,
                full_all_three_FN=full_failures,
                prediction_sha256=i.p.files.sha(i.p.ROOT / i.p.files.OUT / directory / (prefix + '_predictions_v1.csv')),
                matched_past_all_three_FN=sum(all(v == 0 for v in r['past_decisions'].values()) for r in matched),
                matched_R3_all_three_FN=sum(all(v == 0 for v in r['R3_decisions'].values()) for r in matched),
                interpretation='Descriptive matched-parent accounting, not an architecture-controlled or causal comparison; seed sets/objectives/coverage differ.')
    failures = []
    for row in rows:
        if decisions[row['sample_id']] != (0, 0, 0):
            continue
        failures.append(dict(sample_id=row['sample_id'], parent_sample_id=row['parent_sample_id'], source=row['source'],
            lineage_id=row['lineage_id'], attack_family=row['attack_family'], dataset_id=row['dataset_id'], dataset_revision=row['dataset_revision'],
            regime='R3_ENSEMBLE_TARGETED', terminal_text_sha256=row['terminal_text_sha256'], validity_status=row['validity_status'],
            base_decisions={label: 'BENIGN' for label in IDS}, base_scores={label: dict(raw_score=child[(row['sample_id'], label)].raw_score,
                calibrated_score=child[(row['sample_id'], label)].calibrated_score, status='OK') for label in IDS}))
    failures.sort(key=lambda r: (r['parent_sample_id'], r['terminal_text_sha256']))
    membership_hash = hashlib.sha256(i.p.files.canonical_bytes(failures)).hexdigest()
    failure_manifest = dict(artifact_version='r3_all_three_failure_manifest_v1', status='FROZEN' if failures else 'EMPTY',
        member_count=len(failures), empty=not failures, members=failures, membership_sha256=membership_hash,
        membership_hash_definition='SHA256 canonical ASCII JSON of members sorted by (parent_sample_id,terminal_text_sha256); sorted keys, compact separators, no newline.',
        freeze_before_verifier_inference=True, verifier_authoritative_queries=0, protected_evaluation_accessed=False,
        raw_text_policy='LOCAL_ONLY_IGNORED; exact bytes in frozen generation journal',
        deduplication='One member per (regime,parent_sample_id,terminal strict UTF8 hash).',
        prediction_commit=prediction_commit, prediction_sha256=i.p.files.sha(scoring.PREDICTIONS),
        regime_sha256=i.p.files.sha(freeze.REGIME), terminal_manifest_sha256=i.p.files.sha(freeze.TERMINALS),
        detector_manifest_sha256=i.p.digest('artifacts/research_protocol/detector_set_manifest_v1.json'),
        detector_identities=i.p.files.read_json(i.OUT / 'r3_runtime_preflight_v1.json')['identities'],
        frozen_R2_failure_populations={name: dict(count=row['full_all_three_FN'], prediction_sha256=row['prediction_sha256'])
            for name, row in comparisons.items()},
        thresholds=dict(zip(i.design.DOMAIN, i.design.THRESHOLDS)),
        verifier_contract_sha256=i.p.digest('artifacts/research_protocol/verifier/verifier_study_predeclaration_v1.json'))
    outputs = dict(r3_result_bundle_v1=bundle.model_dump(mode='json'), r3_summary_v1=summary,
        r3_source_analysis_v1=sources, r3_operator_analysis_v1=operators, r3_parent_child_transitions_v1=paired,
        r3_coverage_analysis_v1=dict(detectors=coverage, causal_claim=False), r3_matched_comparison_v1=comparisons,
        r3_all_three_failure_manifest_v1=failure_manifest,
        r3_attack_only_guard_v1=dict(FPR='NOT_APPLICABLE_ATTACK_ONLY_REGIME', ROC_AUC='NOT_APPLICABLE_ATTACK_ONLY_REGIME',
            AP='NOT_APPLICABLE_ATTACK_ONLY_REGIME', benign_count=0))
    for name, data in outputs.items():
        i.p.publish(i.OUT / (name + '.json'), data)
    i.p.publish(i.OUT / 'r3_analysis_provenance_v1.json', dict(status='PASS', prediction_commit=prediction_commit,
        protocol_patch_id=protocol_patch_001.PATCH_ID, sha256={name + '.json': i.p.files.sha(i.OUT / (name + '.json')) for name in outputs},
        replicates=1000, seed=1701, confidence_level=0.95, bootstrap_unit='LINEAGE_CLUSTERED',
        verifier_queries=0, protected_queries=0, new_training=False, post_generation_adaptation=False))
    print(json.dumps(dict(status='R3_ANALYSIS_PASS', summary=summary, failure_population=len(failures), membership_sha256=membership_hash), indent=2))


if __name__ == '__main__':
    analyze()
