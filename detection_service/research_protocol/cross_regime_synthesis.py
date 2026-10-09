"""Phase-2 cross-regime synthesis over frozen committed evidence only.

Model-free: no detector, verifier or protected-data access. R0-R2 bundles are
read through the Phase-1 Git-object allowlist at the integration baseline; the
accepted R3 freeze is read through CommittedR3Reader at its declared freeze SHA.
"""
import argparse
import csv
import hashlib
import io
import json
import re
import subprocess
import xml.etree.ElementTree as ET

from detection_service.research_protocol import phase1_synthesis as s
from detection_service.research_protocol import cross_regime_figures as figures

ROOT = s.ROOT
IDS = s.IDS
LABEL = dict(ds_v2='D_S', dm_b_v1='D_M-B', dg_v1='D_G')
REGIMES = ('R0', 'R1', 'R2-DMB', 'R2-D_S', 'R3')
MIXED, ATTACK_ONLY = ('R0', 'R1'), ('R2-DMB', 'R2-D_S', 'R3')
PAIRS = (('ds_v2', 'dm_b_v1'), ('ds_v2', 'dg_v1'), ('dm_b_v1', 'dg_v1'))
SYN = 'artifacts/research_protocol/synthesis/'
OUT = ROOT / SYN
FIGURES = OUT / 'figures'
HANDOFF = OUT / 'r3_accepted_handoff_v1.json'
REPORT = ROOT / 'reviews/CROSS_REGIME_SYNTHESIS_RESULTS_v1.md'
TEST_RECEIPT = ROOT / 'tmp/cross_regime_synthesis_tests.xml'
R3_DIR = 'artifacts/research_protocol/r3/'
NOT_IN_BUNDLE = 'NOT_IN_FROZEN_BUNDLE'
VERIFIER_PANEL = 'PENDING_FINAL_CONFIRMATION_OR_UNDEFINED'
RQ3_STATUS = 'NOT_EMPIRICALLY_IDENTIFIABLE_FROM_R3_DEVELOPMENT_FAILURE_POPULATION'
OUTPUTS = ('cross_regime_metrics_v1', 'cross_regime_tables_v1', 'cross_regime_rq1_findings_v1',
           'cross_regime_rq2_findings_v1', 'cross_regime_figure_manifest_v1')

ACCEPTED_R3 = dict(
    freeze_commit_sha='adc2f7077203a7c3a8b7b58122123fa27e2b0918',
    integration_baseline_commit=s.BASELINE_SHA,
    seed_freeze_commit='37fb38e9fd3d5be2f69e1961b6f80ff8c130e466',
    terminal_freeze_commit='51b40432f12676bf0b62e8f04b9bf48eb0e612f1',
    scoring_commit='875f2fcf5bea4b1c9b01c654609fcba1b5098375',
    failure_manifest_sha256='0e19da171825262881d89cb6f89016315082f254bb10cf02e316d0c9e39ce413',
    membership_sha256='4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945',
    parents=97, lineages=97, all_three_failures=0,
    source_counts={'INJECAGENT_BASE': 1, 'LLMAIL_INJECT': 96},
    verdict='R3_COMPLETE_EMPTY_FAILURE_POPULATION_READY_FOR_PHASE2_REVIEW')

# Role -> (committed file, member path). The accepted R3 freeze stores its
# common-mode, failure-pattern and uncertainty components inside the bundle.
R3_ROLES = {
    'result_bundle': ('r3_result_bundle_v1.json', ()),
    'common_mode': ('r3_result_bundle_v1.json', ('core_metrics', 'common_mode')),
    'failure_patterns': ('r3_result_bundle_v1.json', ('core_metrics', 'failure_patterns')),
    'uncertainty': ('r3_result_bundle_v1.json', ('uncertainty',)),
    'prediction_manifest': ('r3_prediction_manifest_v1.json', ()),
    'all_three_failure_manifest': ('r3_all_three_failure_manifest_v1.json', ()),
    'freeze_receipt': ('r3_final_acceptance_v1.json', ()),
}
R3_SUPPLEMENTS = {
    'predictions': 'r3_predictions_v1.csv',
    'regime_manifest': 'r3_regime_manifest_v1.json',
    'terminal_manifest': 'r3_terminal_manifest_v1.json',
    'seed_manifest': 'r3_seed_manifest_v1.json',
    'summary': 'r3_summary_v1.json',
    'source': 'r3_source_analysis_v1.json',
    'transitions': 'r3_parent_child_transitions_v1.json',
    'analysis_provenance': 'r3_analysis_provenance_v1.json',
    'generation_results': 'r3_generation_results_v1.json',
    'query_accounting': 'r3_query_accounting_v1.json',
    'full_query_accounting': 'r3_full_query_accounting_v1.json',
    'runtime_preflight': 'r3_runtime_preflight_v1.json',
}
FROZEN_SCOPE = ('artifacts/research_protocol/r0', 'artifacts/research_protocol/r1', 'artifacts/research_protocol/r2_dmb',
                'artifacts/research_protocol/r2_ds', 'artifacts/models', 'detection_service/app')


def mismatch(condition, detail):
    s.require(condition, 'R3_SYNTHESIS_INPUT_MISMATCH:' + detail)


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def first_added(path):
    commits = git('log', '--format=%H', '--diff-filter=A', '--', path).decode().split()
    return commits[-1] if commits else None


def canonical(value):
    from detection_service.research_protocol.detector_semantics import canonical_bytes
    return canonical_bytes(value)


def member(value, path):
    for key in path:
        value = value[key]
    return value


# ---------------------------------------------------------------- R3 ingestion

def build_handoff(reader):
    """Envelope naming the accepted freeze SHA and the committed bytes it binds."""
    commit = ACCEPTED_R3['freeze_commit_sha']
    artifacts = {role: dict(path=R3_DIR + name, sha256=s.sha256(reader(commit, R3_DIR + name)), member='/'.join(path) or None)
                 for role, (name, path) in R3_ROLES.items()}
    supplements = {role: dict(path=R3_DIR + name, sha256=s.sha256(reader(commit, R3_DIR + name)))
                   for role, name in R3_SUPPLEMENTS.items()}
    return dict(artifact_version='r3_accepted_handoff_v1', status='ACCEPTED', frozen=True, freeze_commit_sha=commit,
        source_schema='ACCEPTED_R3_FREEZE_V1', input_contract='r3_result_input_contract_v1', artifacts=artifacts,
        supplements=supplements, commits={k: ACCEPTED_R3[k] for k in ('integration_baseline_commit', 'seed_freeze_commit',
            'terminal_freeze_commit', 'scoring_commit', 'freeze_commit_sha')},
        verifier_authoritative_queries_at_freeze=0, protected_evaluation_accessed=False,
        schema_reconciliation=[
            'The accepted R3 freeze predates separate component files: common_mode, failure_patterns and uncertainty '
            'are addressed as members of the committed result bundle and checked for exact equality.',
            'prediction_batch_sha is bound by re-deriving the frozen core metrics from the committed prediction CSV '
            'and regime manifest (model-free), not by a manifest field.',
            'The frozen failure manifest reports member_count (population_count equivalent), file SHA and membership SHA.',
            'r3_final_acceptance_v1.json is the freeze receipt; its committed SHA map binds every R3 component.',
            'All reads are committed Git objects at the freeze SHA; no frozen R3 file is created or modified.'])


def rederive_core(regime_bytes, csv_bytes):
    from detection_service.research_protocol.core_metrics import evaluate_core
    from detection_service.research_protocol.operating_policy import OperationalPredictionRecord
    from detection_service.research_protocol.r0_operational import verified_policy
    from detection_service.research_protocol.r2_ds_transfer_run import aligned
    from detection_service.research_protocol.regime import RegimeManifest
    policy = verified_policy()
    integers = {'truth_label', 'native_binary_prediction', 'operational_binary_prediction', 'input_tokens', 'tokens_analyzed'}
    floats = {'raw_score', 'calibrated_score', 'operational_threshold', 'latency_ms'}
    records = []
    for row in csv.DictReader(io.StringIO(csv_bytes.decode('utf-8'), newline='')):
        data = {k: None if v == '' else int(v) if k in integers else float(v) if k in floats else
                v == 'true' if k == 'truncated' else json.loads(v) if k == 'metadata' else v for k, v in row.items()}
        records.append(OperationalPredictionRecord.model_validate(data, context={'operating_policy': policy}))
    table = aligned(RegimeManifest.model_validate_json(regime_bytes), tuple(records), policy)
    return evaluate_core(table).model_dump(mode='json'), len(records)


def validate_accepted_r3(handoff, reader, expected=ACCEPTED_R3):
    """Fail closed unless every R3 input is the accepted committed freeze."""
    authoritative = type(reader) is s.CommittedR3Reader
    s.require(authoritative or (handoff.get('evidence_kind') == 'SYNTHETIC_FIXTURE' and
              getattr(reader, 'evidence_kind', None) == 'SYNTHETIC_FIXTURE'), 'R3_COMMITTED_READER_REQUIRED')
    s.require(handoff.get('status') == 'ACCEPTED' and handoff.get('frozen') is True, 'R3_NOT_ACCEPTED_FROZEN')
    commit = handoff.get('freeze_commit_sha', '')
    s.require(bool(re.fullmatch('[0-9a-f]{40}', commit)), 'R3_COMMITTED_FREEZE_SHA_REQUIRED')
    mismatch(commit == expected['freeze_commit_sha'], 'FREEZE_COMMIT')
    descriptors = {**handoff.get('artifacts', {}), **handoff.get('supplements', {})}
    s.require(set(R3_ROLES) <= set(handoff.get('artifacts', {})) and set(R3_SUPPLEMENTS) <= set(handoff.get('supplements', {})),
              'R3_PARTIAL_BUNDLE')
    raw, payload, cache = {}, {}, {}
    for role in (*R3_ROLES, *R3_SUPPLEMENTS):
        desc = descriptors[role]
        path = desc.get('path', '')
        s.require(path.startswith(R3_DIR) and '..' not in path.split('/') and '\\' not in path, 'R3_ARTIFACT_PATH_INVALID')
        s.require(bool(re.fullmatch('[0-9a-f]{64}', desc.get('sha256', ''))), 'R3_ARTIFACT_HASH_REQUIRED')
        if role in R3_ROLES:
            s.require(path == R3_DIR + R3_ROLES[role][0] and desc.get('member') == ('/'.join(R3_ROLES[role][1]) or None),
                      'R3_ROLE_BINDING_CONFLICT:' + role)
        else:
            s.require(path == R3_DIR + R3_SUPPLEMENTS[role], 'R3_ROLE_BINDING_CONFLICT:' + role)
        if path not in cache:
            cache[path] = reader(commit, path)
        s.require(s.sha256(cache[path]) == desc['sha256'], 'R3_ARTIFACT_HASH_MISMATCH:' + role)
        raw[role] = cache[path]
        if path.endswith('.json'):
            payload[role] = member(json.loads(cache[path]), R3_ROLES[role][1] if role in R3_ROLES else ())
    bundle = payload['result_bundle']
    s.validate_frozen_bundle(bundle)
    mismatch(bundle['threat_regime'] == 'R3_ENSEMBLE_TARGETED' and bundle['target_detector'] == 'ALL' and
             bundle['comparison_view_id'] == 'OPERATIONAL_FIXED_V1' and bundle['benign_count'] == 0 and
             bundle['attack_count'] == bundle['population_count'] == expected['parents'], 'BUNDLE_SCOPE')
    for role, (_, path) in R3_ROLES.items():
        if path:
            mismatch(payload[role] == member(bundle, path), 'COMPONENT_BINDING:' + role)
    for block in bundle['uncertainty']:
        config = block['config']
        mismatch(config['replicates'] == 1000 and config['seed'] == 1701 and config['confidence_level'] == 0.95 and
                 config['unit'] == 'LINEAGE_CLUSTERED' and config['method'] == 'PERCENTILE_BOOTSTRAP_V1', 'UNCERTAINTY_POLICY')
    common = bundle['core_metrics']['common_mode']
    core, records = rederive_core(raw['regime_manifest'], raw['predictions'])
    mismatch(core == bundle['core_metrics'] and records == 3 * expected['parents'], 'PREDICTION_BATCH_REDERIVATION')
    prediction = payload['prediction_manifest']
    mismatch(prediction['status'] == 'PASS' and prediction['prediction_sha256'] == s.sha256(raw['predictions']) and
             prediction['actual_calls'] == 3 * expected['parents'] and prediction['missing'] == prediction['duplicates'] ==
             prediction['non_OK'] == prediction['replay_decision_mismatches'] == 0 and
             prediction['verifier_queries'] == prediction['protected_queries'] == 0 and
             prediction['freeze_commit'] == expected['terminal_freeze_commit'], 'PREDICTION_MANIFEST')
    failures = payload['all_three_failure_manifest']
    mismatch(descriptors['all_three_failure_manifest']['sha256'] == expected['failure_manifest_sha256'], 'FAILURE_MANIFEST_HASH')
    mismatch(failures['membership_sha256'] == expected['membership_sha256'] ==
             hashlib.sha256(canonical(failures['members'])).hexdigest(), 'MEMBERSHIP_HASH')
    mismatch(failures['member_count'] == len(failures['members']) == common['all_three_fn_count'] ==
             expected['all_three_failures'], 'FAILURE_COUNT')
    mismatch(failures['empty'] is (not failures['members']) and
             failures['status'] == ('EMPTY' if not failures['members'] else 'FROZEN'), 'FAILURE_STATUS')
    mismatch(failures['freeze_before_verifier_inference'] is True and failures['verifier_authoritative_queries'] == 0 and
             failures['protected_evaluation_accessed'] is False, 'FAILURE_FREEZE_CHRONOLOGY')
    mismatch(failures['prediction_sha256'] == prediction['prediction_sha256'] and failures['prediction_commit'] == expected['scoring_commit']
             and failures['terminal_manifest_sha256'] == s.sha256(raw['terminal_manifest']) and
             failures['regime_sha256'] == s.sha256(raw['regime_manifest']), 'FAILURE_MANIFEST_BINDING')
    receipt = payload['freeze_receipt']
    mismatch(receipt['status'] == 'PASS' and receipt['verdict'] == expected['verdict'] and
             receipt['verifier_queries'] == receipt['protected_queries'] == 0, 'FREEZE_RECEIPT_STATUS')
    for key in ('integration_baseline_commit', 'seed_freeze_commit', 'terminal_freeze_commit', 'scoring_commit'):
        mismatch(receipt[key] == expected[key], 'FREEZE_RECEIPT_COMMIT:' + key)
    for role, desc in descriptors.items():
        if desc['path'] != descriptors['freeze_receipt']['path']:
            mismatch(receipt['sha256'].get(desc['path']) == desc['sha256'], 'FREEZE_RECEIPT_BINDING:' + role)
    provenance = payload['analysis_provenance']
    mismatch(provenance['status'] == 'PASS' and provenance['replicates'] == 1000 and provenance['seed'] == 1701 and
             provenance['confidence_level'] == 0.95 and provenance['bootstrap_unit'] == 'LINEAGE_CLUSTERED' and
             provenance['verifier_queries'] == provenance['protected_queries'] == 0 and
             provenance['prediction_commit'] == expected['scoring_commit'], 'ANALYSIS_PROVENANCE')
    for role in ('result_bundle', 'all_three_failure_manifest', 'summary', 'source', 'transitions'):
        mismatch(provenance['sha256'][descriptors[role]['path'].rsplit('/', 1)[1]] == descriptors[role]['sha256'],
                 'ANALYSIS_PROVENANCE_BINDING:' + role)
    summary, terminals = payload['summary'], payload['terminal_manifest']
    mismatch(summary['parent_count'] == expected['parents'] and summary['all_three_successes'] == common['all_three_fn_count'],
             'SUMMARY')
    mismatch(terminals['status'] == 'FROZEN' and terminals['parent_count'] == expected['parents'] and
             terminals['source_counts'] == expected['source_counts'] and terminals['inherited_lineages'] == expected['lineages'] and
             len({t['lineage_id'] for t in terminals['terminals']}) == expected['lineages'] and
             sum(t['success'] for t in terminals['terminals']) == common['all_three_fn_count'] and
             terminals['inverse_passes'] == expected['parents'], 'TERMINAL_MANIFEST')
    seeds = payload['seed_manifest']
    mismatch(seeds['actual_parents'] == expected['parents'] and seeds['source_counts'] == expected['source_counts'] and
             seeds['inherited_lineages'] == expected['lineages'] and seeds['authoritative_queries_before_freeze'] == 0 and
             [p['sample_id'] for p in seeds['parents']] == [t['parent_sample_id'] for t in terminals['terminals']], 'SEED_MANIFEST')
    generation, accounting, full = payload['generation_results'], payload['query_accounting'], payload['full_query_accounting']
    mismatch(generation['status'] == 'PASS' and generation['parents'] == expected['parents'] and
             generation['all_three_successes'] == common['all_three_fn_count'] and
             generation['verifier_queries'] == generation['protected_queries'] == 0 and
             generation['terminal_manifest_sha256'] == s.sha256(raw['terminal_manifest']), 'GENERATION_RESULTS')
    mismatch(accounting['status'] == 'PASS' and accounting['parents'] == expected['parents'] and
             accounting['budget_violations'] == accounting['reconstruction_failures'] == 0 and
             accounting['verifier_queries'] == accounting['protected_queries'] == 0 and
             accounting['max_candidate_evaluations_per_parent'] <= 61 and accounting['max_detector_calls_per_parent'] <= 183,
             'QUERY_ACCOUNTING')
    mismatch(full['status'] == 'PASS' and full['verifier_calls'] == full['protected_calls'] == 0 and
             full['post_freeze_replay_calls'] == 3 * expected['parents'], 'FULL_QUERY_ACCOUNTING')
    runtime, frozen = payload['runtime_preflight'], bundle['core_metrics']['individual']['provenance']
    mismatch(runtime['status'] == 'PASS' and runtime['R3_attack_queries'] == runtime['verifier_queries'] == runtime['protected_queries'] == 0
             and [r['threshold'] for r in runtime['identities']] == frozen['operational_thresholds']
             and [r['threshold_id'] for r in runtime['identities']] == frozen['operational_threshold_ids']
             and [r['detector_id'] for r in runtime['identities']] == list(IDS), 'RUNTIME_IDENTITY')
    if authoritative:
        git('merge-base', '--is-ancestor', commit, 'HEAD')
        for name, key in (('r3_all_three_failure_manifest_v1.json', 'freeze_commit_sha'), ('r3_final_acceptance_v1.json', 'freeze_commit_sha'),
                          ('r3_terminal_manifest_v1.json', 'terminal_freeze_commit'), ('r3_prediction_manifest_v1.json', 'scoring_commit'),
                          ('r3_seed_manifest_v1.json', 'seed_freeze_commit')):
            mismatch(first_added(R3_DIR + name) == expected[key], 'FREEZE_CHRONOLOGY:' + name)
        verifier = git('ls-tree', '-r', '--name-only', commit, '--', 'artifacts/research_protocol/verifier').decode().split()
        mismatch(not any(re.search(r'verifier_(predictions|recovery|result_bundle|overlap|unique)', name.rsplit('/', 1)[-1])
                             and 'schema' not in name for name in verifier), 'VERIFIER_RESULTS_BEFORE_FREEZE')
    return payload


def r3_target(payload):
    common = payload['result_bundle']['core_metrics']['common_mode']
    n, k = payload['result_bundle']['attack_count'], common['all_three_fn_count']
    return dict(target_detector='ALL', valid_attempt_count=n, target_evasion_count=k,
        target_evasion_lineage_count=len({t['lineage_id'] for t in payload['terminal_manifest']['terminals'] if t['success']}),
        valid_attempt_lineage_count=payload['terminal_manifest']['inherited_lineages'],
        target_evasion_rate=dict(numerator=k, denominator=n, reason=None, status='DEFINED', value=k / n),
        transfers=[], transfer_status='NOT_APPLICABLE_TARGET_ALL',
        definition='Valid reversible terminal with all three OK operational BENIGN decisions; equals canonical-replay all-three FN.',
        interval_metric='all_three/jfn')


# ------------------------------------------------------------- registry build

def frozen_inputs_unchanged(read_receipt, handoff):
    rows = []
    for read in read_receipt:
        working = s.sha256((ROOT / read['path']).read_bytes())
        head = s.sha256(git('show', 'HEAD:' + read['path']))
        s.require(working == head == read['sha256'], 'FROZEN_REGIME_ARTIFACT_CHANGED:' + read['path'])
        rows.append(dict(read, first_committed_in=first_added(read['path'])))
    for desc in {d['path']: d for d in (*handoff['artifacts'].values(), *handoff['supplements'].values())}.values():
        s.require(s.sha256((ROOT / desc['path']).read_bytes()) == desc['sha256'], 'FROZEN_R3_ARTIFACT_CHANGED:' + desc['path'])
    return rows


def frozen_scope_diff():
    return dict(
        baseline_to_head=git('diff', '--name-only', s.BASELINE_SHA, 'HEAD', '--', *FROZEN_SCOPE).decode().split(),
        r3_freeze_to_head=git('diff', '--name-only', ACCEPTED_R3['freeze_commit_sha'], 'HEAD', '--', R3_DIR).decode().split(),
        working_tree=git('status', '--porcelain', '--', *FROZEN_SCOPE, R3_DIR).decode().split('\n')[:-1])


def load_handoff(reader):
    built = build_handoff(reader)
    if HANDOFF.exists():
        s.require(HANDOFF.read_bytes() == s.bytes_json(built), 'R3_HANDOFF_ENVELOPE_DRIFT')
    return built


def build_registry():
    base = s.load_pre_r3()
    reader = s.CommittedR3Reader(ROOT, phase2_authorized=True)
    handoff = load_handoff(reader)
    payload = validate_accepted_r3(handoff, reader)
    reads = frozen_inputs_unchanged(base['read_receipt'], handoff)
    scope = frozen_scope_diff()
    s.require(not any(scope.values()), 'FROZEN_SCIENTIFIC_SCOPE_CHANGED')
    r3 = s.normalize('R3', payload['result_bundle'], supplements={'source': payload['source'], 'transitions': payload['transitions']},
                     provenance={'freeze_commit_sha': handoff['freeze_commit_sha'], 'handoff_sha256': s.sha256(s.bytes_json(handoff)),
                                 'artifacts': handoff['artifacts'], 'supplements': handoff['supplements']})
    r3['targeted'] = [r3_target(payload)]
    r3 = s.RegimeRecord.model_validate(r3).model_dump(mode='json')
    records = [r for r in base['records'] if r['regime_id'] != 'R3'] + [r3]
    s.require([r['regime_id'] for r in records] == list(REGIMES) and all(r['status'] == 'OBSERVED' for r in records),
              'REGIME_REGISTRY_INCOMPLETE')
    family = next(r for r in records if r['regime_id'] == 'R1')['source_family']['family']
    terminals = payload['terminal_manifest']
    accounting, full = payload['query_accounting'], payload['full_query_accounting']
    failures = payload['all_three_failure_manifest']
    metrics = dict(schema_version='cross_regime_metrics_v1', regimes=list(REGIMES),
        population_type={r['regime_id']: r['population_type'] for r in records}, records=records,
        r3=dict(parents=terminals['parent_count'], inherited_lineages=terminals['inherited_lineages'],
            source_counts=terminals['source_counts'], target=r3['targeted'][0],
            candidate_evaluations=accounting['candidate_evaluations'], generation_detector_calls=accounting['detector_calls'],
            max_candidate_evaluations_per_parent=accounting['max_candidate_evaluations_per_parent'],
            budget_violations=accounting['budget_violations'], reconstruction_failures=accounting['reconstruction_failures'],
            post_freeze_replay_calls=full['post_freeze_replay_calls'], total_model_calls=full['total_model_calls'],
            failure_manifest=dict(path=handoff['artifacts']['all_three_failure_manifest']['path'],
                sha256=handoff['artifacts']['all_three_failure_manifest']['sha256'], status=failures['status'],
                member_count=failures['member_count'], empty=failures['empty'], membership_sha256=failures['membership_sha256']),
            verifier_queries_before_failure_freeze=0, protected_queries=0,
            detector_identities=payload['runtime_preflight']['identities']),
        r1_attack_sources={g: dict(sample_count=v['sample_count'], lineage_count=v['lineage_count'],
            attack_family=v['attack_family'], uncertainty_status=v['uncertainty_status']) for g, v in family['groups'].items()},
        read_receipt=reads, r3_handoff=dict(path=SYN + 'r3_accepted_handoff_v1.json', sha256=s.sha256(s.bytes_json(handoff))),
        frozen_scope_diff=scope, rq3=rq3_status(failures),
        authoritative_queries=dict(ds_v2=0, dm_b_v1=0, dg_v1=0, verifier=0), protected_access=False,
        scientific_inference=False, resampling_performed=False,
        uncertainty_policy='Frozen intervals copied unchanged (1000 PCG64 percentile replicates, seed 1701, 95%, lineage-clustered); no resampling.')
    return metrics, handoff


def rq3_status(failures):
    return dict(r3_base_stack_all_three_failure_population=failures['member_count'],
        development_recovery_denominator=failures['member_count'],
        development_recovery={v: dict(status='UNDEFINED', value=None, reason='ZERO_DENOMINATOR') for v in ('V1', 'V2', 'V3')},
        status=RQ3_STATUS, owner='Phase-2 Track B (final RQ3 disposition)', verifier_queries=0, verifier_panel=VERIFIER_PANEL)


# ----------------------------------------------------------- flat metric index

def value_of(cell):
    if isinstance(cell, dict) and 'status' in cell:
        return cell['value'] if cell['status'] in ('OBSERVED', 'DEFINED') else cell['status']
    return cell


def interval(record, metric_id):
    for block in record['uncertainty']:
        for row in block['intervals']:
            if row['metric_id'] == metric_id:
                return dict(lower=row['ci_lower'], upper=row['ci_upper'], point=row['point_estimate'], status=row['status'],
                            domain=block['config']['domain'], valid_replicates=row['replicates_valid'])
    return dict(status=NOT_IN_BUNDLE)


def ci_value(ci):
    return [ci['lower'], ci['upper']] if ci.get('lower') is not None else ci['status']


def index(metrics):
    """Flat key -> frozen value map; every findings statement cites these keys."""
    out = {}
    for r in metrics['records']:
        rid = r['regime_id']
        out[f'{rid}/attack_count'], out[f'{rid}/benign_count'] = r['attack_count'], r['benign_count']
        out[f'{rid}/lineage_count'] = r['lineage']['count']
        for d in r['detectors']:
            for key in ('tp', 'fn', 'tn', 'fp'):
                out[f'{rid}/{d["detector_id"]}/{key}'] = d[key] if d[key] is not None else 'NOT_APPLICABLE'
            for key in ('recall', 'fnr', 'fpr', 'roc_auc', 'ap'):
                out[f'{rid}/{d["detector_id"]}/{key}'] = value_of(d[key])
            out[f'{rid}/ci/individual/{d["detector_id"]}/fnr'] = ci_value(interval(r, f'individual/{d["detector_id"]}/fnr'))
        for p in r['pairs']:
            pair = f'{p["left_detector"]}~{p["right_detector"]}'
            for key in ('shared_fn', 'union_fn'):
                out[f'{rid}/pair/{pair}/{key}'] = p[key]
            for key in ('jfn', 'independence_reference', 'ejf', 'fn_jaccard'):
                out[f'{rid}/pair/{pair}/{key}'] = value_of(p[key])
                out[f'{rid}/ci/pair/{p["left_detector"]}/{p["right_detector"]}/{key}'] = ci_value(
                    interval(r, f'pair/{p["left_detector"]}/{p["right_detector"]}/{key}'))
        out[f'{rid}/all_three_fn'], out[f'{rid}/all_three_jfn'] = r['all_three_fn'], value_of(r['all_three_jfn'])
        out[f'{rid}/ci/all_three/jfn'] = ci_value(interval(r, 'all_three/jfn'))
        for p in r['failure_patterns']:
            out[f'{rid}/pattern/{p["pattern_id"]}'] = p['count']
        for x in r['recovery']:
            for key in ('unique_catch_count', 'both_others_miss_count'):
                out[f'{rid}/recovery/{x["detector_id"]}/{key}'] = x[key]
            for key in ('unique_catch_rate', 'conditional_recovery'):
                out[f'{rid}/recovery/{x["detector_id"]}/{key}'] = value_of(x[key])
        for t in r['targeted']:
            target = t['target_detector']
            for key in ('valid_attempt_count', 'target_evasion_count'):
                out[f'{rid}/target/{target}/{key}'] = t[key]
            out[f'{rid}/target/{target}/target_evasion_rate'] = value_of(t['target_evasion_rate'])
            name = t.get('interval_metric') or f'target/{target}/evasion'
            out[f'{rid}/ci/target/{target}/evasion'] = ci_value(interval(r, name))
            for x in t['transfers']:
                out[f'{rid}/transfer/{target}->{x["transfer_detector"]}/joint_evasion_count'] = x['joint_evasion_count']
                out[f'{rid}/transfer/{target}->{x["transfer_detector"]}/etr'] = value_of(x['etr'])
                out[f'{rid}/ci/transfer/{target}->{x["transfer_detector"]}/etr'] = ci_value(
                    interval(r, f'transfer/{target}/{x["transfer_detector"]}/etr'))
        for d, row in r['parent_child'].get('overall', {}).items():
            for key, count in row.items():
                out[f'{rid}/transition/{d}/{key}'] = count
    for rid, rows in source_rows(metrics).items():
        for row in rows:
            for key, value in row.items():
                if key not in ('source', 'regime'):
                    out[f'{rid}/source/{row["source"]}/{key}'] = value
    r3 = metrics['r3']
    for key in ('parents', 'inherited_lineages', 'candidate_evaluations', 'generation_detector_calls', 'budget_violations',
                'reconstruction_failures', 'post_freeze_replay_calls', 'verifier_queries_before_failure_freeze', 'protected_queries'):
        out[f'R3/{key}'] = r3[key]
    for source, count in r3['source_counts'].items():
        out[f'R3/source_count/{source}'] = count
    for key in ('status', 'member_count', 'sha256', 'membership_sha256'):
        out[f'R3/failure_manifest/{key}'] = r3['failure_manifest'][key]
    for source, row in metrics['r1_attack_sources'].items():
        out[f'R1/attack_source/{source}/sample_count'] = row['sample_count']
        out[f'R1/attack_source/{source}/lineage_count'] = row['lineage_count']
    rq3 = metrics['rq3']
    out['RQ3/development_recovery_denominator'] = rq3['development_recovery_denominator']
    for v, cell in rq3['development_recovery'].items():
        out[f'RQ3/recovery/{v}'] = value_of(cell)
    return out


# --------------------------------------------------------------------- tables

def with_ci(cell, ci):
    return dict(cell, ci95=ci)


def source_rows(metrics):
    """Frozen source-conditioned rows; R0 has no frozen source decomposition."""
    records = {r['regime_id']: r for r in metrics['records']}
    result = {'R0': [dict(regime='R0', source='ALL', status='SOURCE_DECOMPOSITION_UNAVAILABLE_IN_FROZEN_INPUTS')]}
    rows = []
    for group, v in records['R1']['source_family']['family']['groups'].items():
        core = v['core_metrics']
        row = dict(regime='R1', source=group, attacks=v['sample_count'], lineages=v['lineage_count'],
                   all_three_fn=core['common_mode']['all_three_fn_count'], uncertainty_status=v['uncertainty_status'])
        for d in core['individual']['detectors']:
            row[f'{d["detector_id"]}/fn'], row[f'{d["detector_id"]}/fnr'] = d['fn'], value_of(d['fnr'])
        rows.append(row)
    result['R1'] = rows
    for rid in ('R2-DMB', 'R2-D_S'):
        record, rows = records[rid], []
        analysis = record['source_family']['source']
        target = record['targeted'][0]['target_detector']
        for group, transitions in sorted(record['parent_child']['by_source'].items()):
            v = analysis[group]
            row = dict(regime=rid, source=group, attacks=v['seed_count'], lineages=v['lineage_count'],
                       target_evasion_count=v['target_evasion_count'], target_evasion_rate=value_of(v['target_evasion_rate']),
                       all_three_fn=v['successful_evasion_patterns']['111'])
            for d, counts in transitions.items():
                fn = counts['catch_to_miss'] + counts['miss_to_miss']
                row[f'{d}/fn'], row[f'{d}/fnr'] = fn, fn / sum(counts.values())
            intervals = {i['metric_id']: i for i in v['uncertainty']['intervals']}
            row['target_evasion_ci95'] = ci_value(dict(lower=intervals[f'target/{target}/evasion']['ci_lower'],
                upper=intervals[f'target/{target}/evasion']['ci_upper'], status=intervals[f'target/{target}/evasion']['status']))
            for other in IDS:
                if other != target:
                    key = 'etr_' + dict(ds_v2='ds', dm_b_v1='dmb', dg_v1='dg')[other]
                    row[f'etr/{other}'] = value_of(v[key])
                    entry = intervals[f'transfer/{target}/{other}/etr']
                    row[f'etr/{other}/ci95'] = [entry['ci_lower'], entry['ci_upper']] if entry['ci_lower'] is not None else entry['status']
            rows.append(row)
        s.require(sum(r['all_three_fn'] for r in rows) == record['all_three_fn'], 'SOURCE_ALL_THREE_CONFLICT:' + rid)
        result[rid] = rows
    rows = []
    for group, v in sorted(records['R3']['source_family']['source'].items()):
        intervals = {i['metric_id']: i for i in v['uncertainty']['intervals']}
        row = dict(regime='R3', source=group, attacks=v['parent_count'], lineages=v['inherited_lineages'],
                   all_three_fn=v['all_three_successes'], target_evasion_count=v['all_three_successes'],
                   target_evasion_rate=v['target_success_rate'])
        for d in IDS:
            row[f'{d}/fn'], row[f'{d}/fnr'] = v['FN'][d], v['FN'][d] / v['parent_count']
            entry = intervals[f'individual/{d}/fnr']
            row[f'{d}/fnr/ci95'] = [entry['ci_lower'], entry['ci_upper']] if entry['ci_lower'] is not None else entry['status']
        entry = intervals['all_three/jfn']
        row['target_evasion_ci95'] = [entry['ci_lower'], entry['ci_upper']] if entry['ci_lower'] is not None else entry['status']
        rows.append(row)
    s.require(sum(r['all_three_fn'] for r in rows) == records['R3']['all_three_fn'], 'SOURCE_ALL_THREE_CONFLICT:R3')
    result['R3'] = rows
    return result


def tables(metrics):
    out = dict(A=[], B=[], C=[], D=[], E=[], F=[])
    for r in metrics['records']:
        rid = r['regime_id']
        base = dict(regime=rid, population_type=r['population_type'], attack_count=r['attack_count'], benign_count=r['benign_count'])
        for d in r['detectors']:
            row = dict(base, **{k: d[k] for k in ('detector_id', 'threshold_id', 'threshold', 'tp', 'fn', 'tn', 'fp')})
            row['recall'] = d['recall']
            row['fnr'] = with_ci(d['fnr'], interval(r, f'individual/{d["detector_id"]}/fnr'))
            row['fpr'] = with_ci(d['fpr'], interval(r, f'individual/{d["detector_id"]}/fpr')) if rid in MIXED else d['fpr']
            row['roc_auc'], row['ap'] = d['roc_auc'], d['ap']
            row['ranking_source'] = 'FROZEN_RANKING_SUPPLEMENT' if rid in MIXED else 'NOT_APPLICABLE_ATTACK_ONLY'
            out['A'].append(row)
        for p in r['pairs']:
            row = dict(base, left_detector=p['left_detector'], right_detector=p['right_detector'],
                       shared_fn=p['shared_fn'], union_fn=p['union_fn'])
            for key in ('jfn', 'independence_reference', 'ejf', 'fn_jaccard'):
                row[key] = with_ci(p[key], interval(r, f'pair/{p["left_detector"]}/{p["right_detector"]}/{key}'))
            out['B'].append(row)
        out['C'].append(dict(base, all_three_fn=r['all_three_fn'], all_three_jfn=with_ci(r['all_three_jfn'], interval(r, 'all_three/jfn')),
            failure_patterns={p['pattern_id']: dict(count=p['count'], meaning=p['meaning'], rate=p['attack_rate']['value'],
                ci95=interval(r, 'pattern/' + p['pattern_id'])) for p in r['failure_patterns']},
            recovery={x['detector_id']: dict(unique_catch_pattern=x['unique_catch_pattern'], unique_catch_count=x['unique_catch_count'],
                unique_catch_rate=with_ci(x['unique_catch_rate'], interval(r, f'recovery/{x["detector_id"]}/unique_catch_rate')),
                both_others_miss_count=x['both_others_miss_count'],
                conditional_recovery=with_ci(x['conditional_recovery'], interval(r, f'recovery/{x["detector_id"]}/conditional_recovery')))
                for x in r['recovery']}))
        if not r['targeted']:
            out['D'].append(dict(base, target_detector=None, status='NOT_APPLICABLE_NON_TARGETED_REGIME'))
        for t in r['targeted']:
            target = t['target_detector']
            out['D'].append(dict(base, target_detector=target, valid_attempt_count=t['valid_attempt_count'],
                target_evasion_count=t['target_evasion_count'],
                target_evasion_lineage_count=t.get('target_evasion_lineage_count'),
                target_evasion_rate=with_ci(t['target_evasion_rate'], interval(r, t.get('interval_metric') or f'target/{target}/evasion')),
                transfers=[dict(transfer_detector=x['transfer_detector'], joint_evasion_count=x['joint_evasion_count'],
                    etr=with_ci(x['etr'], interval(r, f'transfer/{target}/{x["transfer_detector"]}/etr'))) for x in t['transfers']],
                transfer_status=t.get('transfer_status', 'OBSERVED' if any(x['etr']['status'] == 'DEFINED' for x in t['transfers'])
                                      else 'UNDEFINED_ZERO_TARGET_EVASIONS'),
                interval_note='R3 target interval is the frozen ATTACK_ONLY all_three/jfn interval (identical population and numerator).'
                              if rid == 'R3' else None))
        overall = r['parent_child'].get('overall')
        if not overall:
            out['E'].append(dict(base, status='NOT_APPLICABLE_NO_PARENT_CHILD_STRUCTURE'))
        for d in IDS if overall else ():
            out['E'].append(dict(base, detector_id=d, **overall[d], parent_child_pairs=sum(overall[d].values())))
    for rid, rows in source_rows(metrics).items():
        out['F'].extend(rows)
    return dict(schema_version='cross_regime_tables_v1', population_classes=dict(mixed=list(MIXED), attack_only=list(ATTACK_ONLY)),
        descriptions=dict(A='Core detector performance by regime (operational fixed thresholds)', B='Pairwise/common-mode failure metrics',
            C='All-three failure behavior, failure patterns, unique catches and conditional recovery', D='Targeted attack behavior and ETR',
            E='Parent-child transitions (immediate R1 parent to terminal)', F='Source-conditioned results'),
        attack_only_guard='FPR, ROC-AUC and AP are NOT_APPLICABLE for R2-DMB, R2-D_S and R3 (no benign denominator); TN/FP null.',
        undefined='Undefined values remain UNDEFINED with null value; never zero.',
        intervals='ci95 copied from frozen bundles; NOT_IN_FROZEN_BUNDLE where the regime did not compute that interval.',
        tables=out)


# -------------------------------------------------------------------- findings

def P(value):
    return f'{100 * value:.2f}%'


def CI(value):
    return f'[{value[0]:.4f}, {value[1]:.4f}]' if isinstance(value, list) else str(value)


def lineages(count):
    return f'{count} lineage' + ('' if count == 1 else 's')


def finding(fid, kind, text, keys, X):
    for key in keys:
        s.require(key in X, 'UNTRACEABLE_FINDING_KEY:' + key)
    return dict(id=fid, kind=kind, statement=text, evidence=[dict(key=key, value=X[key]) for key in keys])


def rq1(metrics):
    X = index(metrics)
    det = lambda rid, d, k: X[f'{rid}/{d}/{k}']
    items = []
    for d in IDS:
        keys = [f'{rid}/{d}/{k}' for rid in MIXED for k in ('tp', 'fn', 'fp', 'recall', 'fnr', 'fpr', 'roc_auc', 'ap')] + \
               [f'{rid}/attack_count' for rid in MIXED] + [f'{rid}/benign_count' for rid in MIXED]
        text = (f'{LABEL[d]}: attack recall {P(det("R0", d, "recall"))} ({det("R0", d, "tp")}/{X["R0/attack_count"]}) in R0 vs '
                f'{P(det("R1", d, "recall"))} ({det("R1", d, "tp")}/{X["R1/attack_count"]}) in R1 (FNR {P(det("R0", d, "fnr"))} -> '
                f'{P(det("R1", d, "fnr"))}); benign FPR {P(det("R0", d, "fpr"))} ({det("R0", d, "fp")}/{X["R0/benign_count"]}) -> '
                f'{P(det("R1", d, "fpr"))} ({det("R1", d, "fp")}/{X["R1/benign_count"]}) at the same fixed operating threshold. '
                f'Frozen ranking metrics: ROC-AUC {det("R0", d, "roc_auc"):.4f} -> {det("R1", d, "roc_auc"):.4f}, '
                f'AP {det("R0", d, "ap"):.4f} -> {det("R1", d, "ap"):.4f}.')
        items.append(finding('RQ1-' + LABEL[d], 'OBSERVED', text, keys, X))
    items.append(finding('RQ1-ALL-THREE', 'OBSERVED',
        f'All-three attack FN: {X["R0/all_three_fn"]}/{X["R0/attack_count"]} in R0 and {X["R1/all_three_fn"]}/{X["R1/attack_count"]} in R1.',
        ['R0/all_three_fn', 'R0/attack_count', 'R1/all_three_fn', 'R1/attack_count'], X))
    sources = sorted(metrics['r1_attack_sources'])
    keys = ['R0/attack_count', 'R0/benign_count', 'R0/lineage_count', 'R1/attack_count', 'R1/benign_count', 'R1/lineage_count'] + \
           [f'R1/attack_source/{g}/{k}' for g in sources for k in ('sample_count', 'lineage_count')]
    items.append(finding('RQ1-COMPOSITION', 'LIMITATION',
        f'R0 contains {X["R0/attack_count"]} attacks and {X["R0/benign_count"]} benign samples ({X["R0/lineage_count"]} lineages); '
        f'R1 contains {X["R1/attack_count"]} attacks and {X["R1/benign_count"]} hard-benign samples ({X["R1/lineage_count"]} lineages). '
        'R1 attacks are ' + ' and '.join(f'{X[f"R1/attack_source/{g}/sample_count"]} {g} ({lineages(X[f"R1/attack_source/{g}/lineage_count"])})'
                                        for g in sources) +
        '. R0 has no frozen source decomposition in the synthesis inputs. The populations are unpaired and differ in source composition.',
        keys, X))
    keys = [f'R1/source/{g}/{d}/fnr' for g in sources for d in IDS] + [f'R1/source/{g}/{d}/fn' for g in sources for d in IDS]
    items.append(finding('RQ1-SOURCE', 'OBSERVED',
        'R1 source-conditioned FNR: ' + '; '.join(f'{g}: ' + ', '.join(f'{LABEL[d]} {X[f"R1/source/{g}/{d}/fn"]}/'
            f'{X[f"R1/attack_source/{g}/sample_count"]} ({P(X[f"R1/source/{g}/{d}/fnr"])})' for d in IDS) for g in sources) +
        '. InjecAgent is a single inherited lineage cluster; its source-level behavior is not independent-case evidence.',
        keys + [f'R1/attack_source/{g}/sample_count' for g in sources], X))
    items.append(finding('RQ1-LIMITS', 'LIMITATION',
        'R0 -> R1 differences are descriptive: different, unpaired populations and sources at fixed thresholds; no single cause is '
        'attributed. R1 is a non-adaptive shifted population and does not establish adaptive robustness.', [], X))
    up = lambda d, k: X[f'R1/{d}/{k}'] > X[f'R0/{d}/{k}']
    answer = (f'Detector behavior changed in detector-specific directions under the R0 -> R1 shift at fixed operating thresholds. '
              f'D_S attack recall {"rose" if up("ds_v2", "recall") else "fell"} ({P(X["R0/ds_v2/recall"])} -> {P(X["R1/ds_v2/recall"])}) '
              f'and its benign FPR {"rose" if up("ds_v2", "fpr") else "fell"} ({P(X["R0/ds_v2/fpr"])} -> {P(X["R1/ds_v2/fpr"])}). '
              f'D_M-B kept near-complete attack recall ({P(X["R0/dm_b_v1/recall"])} -> {P(X["R1/dm_b_v1/recall"])}) but its benign FPR '
              f'{"rose" if up("dm_b_v1", "fpr") else "fell"} ({P(X["R0/dm_b_v1/fpr"])} -> {P(X["R1/dm_b_v1/fpr"])}). '
              f'D_G attack recall {"rose" if up("dg_v1", "recall") else "fell"} ({P(X["R0/dg_v1/recall"])} -> {P(X["R1/dg_v1/recall"])}) '
              f'while its benign FPR {"rose" if up("dg_v1", "fpr") else "fell"} ({P(X["R0/dg_v1/fpr"])} -> {P(X["R1/dg_v1/fpr"])}). '
              'Distribution shift therefore did not affect the detectors uniformly. These are descriptive comparisons of unpaired '
              'populations with different source composition; R1 alone does not establish adaptive robustness.')
    return dict(schema_version='cross_regime_rq1_findings_v1', question='How does detector behavior change under distribution shift?',
                primary_comparison='R0 -> R1', answer=answer, findings=items, causal_claims=False, significance_tests=False)


def rq2(metrics):
    X = index(metrics)
    items = []
    pair = lambda rid, a, b, k: X[f'{rid}/pair/{a}~{b}/{k}']
    items.append(finding('RQ2-R1-REFERENCE', 'OBSERVED',
        f'R1 non-adaptive reference: all-three FN {X["R1/all_three_fn"]}/{X["R1/attack_count"]}; shared FN '
        + ', '.join(f'{LABEL[a]}/{LABEL[b]} {pair("R1", a, b, "shared_fn")}' for a, b in PAIRS) + '.',
        ['R1/all_three_fn', 'R1/attack_count'] + [f'R1/pair/{a}~{b}/shared_fn' for a, b in PAIRS], X))
    t = 'R2-DMB/target/dm_b_v1'
    items.append(finding('RQ2-R2-DMB', 'OBSERVED',
        f'R2-DMB: {X[t + "/target_evasion_count"]}/{X[t + "/valid_attempt_count"]} D_M-B target evasions '
        f'(stored 95% CI {CI(X["R2-DMB/ci/target/dm_b_v1/evasion"])}); ETR to D_S and D_G is '
        f'{X["R2-DMB/transfer/dm_b_v1->ds_v2/etr"]} / {X["R2-DMB/transfer/dm_b_v1->dg_v1/etr"]} because the target-success '
        f'denominator is 0; all-three FN {X["R2-DMB/all_three_fn"]}/{X["R2-DMB/attack_count"]}.',
        [t + '/target_evasion_count', t + '/valid_attempt_count', 'R2-DMB/ci/target/dm_b_v1/evasion',
         'R2-DMB/transfer/dm_b_v1->ds_v2/etr', 'R2-DMB/transfer/dm_b_v1->dg_v1/etr', 'R2-DMB/all_three_fn', 'R2-DMB/attack_count'], X))
    t = 'R2-D_S/target/ds_v2'
    items.append(finding('RQ2-R2-DS-TARGET', 'OBSERVED',
        f'R2-D_S: {X[t + "/target_evasion_count"]}/{X[t + "/valid_attempt_count"]} D_S target evasions '
        f'({P(X[t + "/target_evasion_rate"])}; stored 95% CI {CI(X["R2-D_S/ci/target/ds_v2/evasion"])}).',
        [t + '/target_evasion_count', t + '/valid_attempt_count', t + '/target_evasion_rate', 'R2-D_S/ci/target/ds_v2/evasion'], X))
    items.append(finding('RQ2-R2-DS-DG-OVERLAP', 'OBSERVED',
        f'Of the {X[t + "/target_evasion_count"]} successful D_S evasions, {X["R2-D_S/transfer/ds_v2->dg_v1/joint_evasion_count"]} were also '
        f'missed by D_G (ETR {P(X["R2-D_S/transfer/ds_v2->dg_v1/etr"])}; stored 95% CI {CI(X["R2-D_S/ci/transfer/ds_v2->dg_v1/etr"])}).',
        [t + '/target_evasion_count', 'R2-D_S/transfer/ds_v2->dg_v1/joint_evasion_count', 'R2-D_S/transfer/ds_v2->dg_v1/etr',
         'R2-D_S/ci/transfer/ds_v2->dg_v1/etr'], X))
    items.append(finding('RQ2-R2-DS-DMB-RECOVERY', 'OBSERVED',
        f'D_M-B missed {X["R2-D_S/transfer/ds_v2->dm_b_v1/joint_evasion_count"]} of the {X[t + "/target_evasion_count"]} successful D_S '
        f'evasions (ETR {P(X["R2-D_S/transfer/ds_v2->dm_b_v1/etr"])}; stored 95% CI {CI(X["R2-D_S/ci/transfer/ds_v2->dm_b_v1/etr"])}), '
        f'so all-three FN in R2-D_S is {X["R2-D_S/all_three_fn"]}/{X["R2-D_S/attack_count"]}.',
        [t + '/target_evasion_count', 'R2-D_S/transfer/ds_v2->dm_b_v1/joint_evasion_count', 'R2-D_S/transfer/ds_v2->dm_b_v1/etr',
         'R2-D_S/ci/transfer/ds_v2->dm_b_v1/etr', 'R2-D_S/all_three_fn', 'R2-D_S/attack_count'], X))
    items.append(finding('RQ2-R3-ALL-THREE', 'OBSERVED',
        f'R3: {X["R3/target/ALL/target_evasion_count"]}/{X["R3/target/ALL/valid_attempt_count"]} simultaneous (all-three) evasions across '
        f'{X["R3/parents"]} frozen lineage-distinct parents; all-three JFN {X["R3/all_three_jfn"]}; stored percentile-bootstrap 95% CI '
        f'{CI(X["R3/ci/all_three/jfn"])} from a zero-event population (not a population robustness bound).',
        ['R3/target/ALL/target_evasion_count', 'R3/target/ALL/valid_attempt_count', 'R3/parents', 'R3/all_three_jfn', 'R3/ci/all_three/jfn'], X))
    items.append(finding('RQ2-R3-DETECTORS', 'OBSERVED',
        'R3 per-detector FN: ' + ', '.join(f'{LABEL[d]} {X[f"R3/{d}/fn"]}/{X["R3/attack_count"]} (FNR {P(X[f"R3/{d}/fnr"])}; '
                                          f'stored 95% CI {CI(X[f"R3/ci/individual/{d}/fnr"])})' for d in IDS) + '.',
        [f'R3/{d}/{k}' for d in IDS for k in ('fn', 'fnr')] + [f'R3/ci/individual/{d}/fnr' for d in IDS] + ['R3/attack_count'], X))
    keys = [f'R3/pair/ds_v2~dg_v1/{k}' for k in ('shared_fn', 'union_fn', 'jfn', 'independence_reference', 'ejf', 'fn_jaccard')]
    items.append(finding('RQ2-R3-DS-DG', 'OBSERVED',
        f'R3 D_S/D_G: shared FN {pair("R3", "ds_v2", "dg_v1", "shared_fn")}, JFN {pair("R3", "ds_v2", "dg_v1", "jfn"):.4f}, FNR-product '
        f'reference {pair("R3", "ds_v2", "dg_v1", "independence_reference"):.4f}, EJF {pair("R3", "ds_v2", "dg_v1", "ejf"):+.4f}, FN Jaccard '
        f'{pair("R3", "ds_v2", "dg_v1", "fn_jaccard"):.4f}. Every R3 D_S miss was also a D_G miss.', keys, X))
    regimes_dmb = [rid for rid in REGIMES if rid != 'R0']
    keys = [f'{rid}/pair/{a}~{b}/shared_fn' for rid in REGIMES for a, b in PAIRS if 'dm_b_v1' in (a, b)] + \
           [f'{rid}/dm_b_v1/fn' for rid in REGIMES]
    items.append(finding('RQ2-DMB-COMPLEMENTARITY', 'OBSERVED',
        'D_M-B FN by regime: ' + ', '.join(f'{rid} {X[f"{rid}/dm_b_v1/fn"]}/{X[f"{rid}/attack_count"]}' for rid in REGIMES) +
        '. Pairwise shared FN involving D_M-B (D_S/D_M-B, D_M-B/D_G): ' +
        ', '.join(f'{rid} {X[f"{rid}/pair/ds_v2~dm_b_v1/shared_fn"]}/{X[f"{rid}/pair/dm_b_v1~dg_v1/shared_fn"]}' for rid in REGIMES) +
        f'; in {", ".join(regimes_dmb)} D_M-B shared no observed miss with either other detector.',
        keys + [f'{rid}/attack_count' for rid in REGIMES], X))
    keys = [f'{rid}/dg_v1/fnr' for rid in REGIMES] + [f'{rid}/pair/ds_v2~dg_v1/ejf' for rid in REGIMES] + \
           [f'{rid}/pair/ds_v2~dg_v1/fn_jaccard' for rid in REGIMES]
    items.append(finding('RQ2-DG-BASE-RATE', 'OBSERVED',
        'D_G FNR by regime: ' + ', '.join(f'{rid} {P(X[f"{rid}/dg_v1/fnr"])}' for rid in REGIMES) +
        '. Because D_G misses most attacks in every regime, D_S/D_G overlap is bounded by that base rate; D_S/D_G EJF by regime: ' +
        ', '.join(f'{rid} {X[f"{rid}/pair/ds_v2~dg_v1/ejf"]:+.4f}' for rid in REGIMES) + '. EJF is a descriptive deviation from the '
        'FNR-product reference, not a test of independence or evidence of causal dependence.', keys, X))
    keys = [f'R3/transition/{d}/{k}' for d in IDS for k in ('catch_to_catch', 'catch_to_miss', 'miss_to_catch', 'miss_to_miss')]
    items.append(finding('RQ2-R3-TRANSITIONS', 'OBSERVED',
        'R3 parent -> terminal transitions under the unchanged operational policy: ' + '; '.join(
            f'{LABEL[d]} catch->miss {X[f"R3/transition/{d}/catch_to_miss"]}, miss->catch {X[f"R3/transition/{d}/miss_to_catch"]}, '
            f'catch->catch {X[f"R3/transition/{d}/catch_to_catch"]}, miss->miss {X[f"R3/transition/{d}/miss_to_miss"]}' for d in IDS) + '.',
        keys, X))
    sources = sorted(metrics['r3']['source_counts'])
    keys = [f'R3/source_count/{g}' for g in sources] + [f'R3/source/{g}/all_three_fn' for g in sources] + ['R3/inherited_lineages']
    items.append(finding('RQ2-R3-SOURCES', 'LIMITATION',
        f'R3 population: {X["R3/parents"]} parents, {X["R3/inherited_lineages"]} inherited lineages; ' +
        ', '.join(f'{g} {X[f"R3/source_count/{g}"]} (all-three FN {X[f"R3/source/{g}/all_three_fn"]})' for g in sources) +
        '. Source generalization is limited; the result concerns the frozen attack population and predefined generator.',
        keys + ['R3/parents'], X))
    interpretations = [
        ('RQ2-I1', 'D_S and D_G showed substantial overlap under the D_S-targeted regime.',
         ['R2-D_S/transfer/ds_v2->dg_v1/joint_evasion_count', 'R2-D_S/target/ds_v2/target_evasion_count']),
        ('RQ2-I2', 'D_M-B provided complete observed recovery for the 104 successful D_S evasions.',
         ['R2-D_S/transfer/ds_v2->dm_b_v1/joint_evasion_count', 'R2-D_S/target/ds_v2/target_evasion_count']),
        ('RQ2-I3', 'The fixed R3 ensemble-aware generator did not produce an all-three failure.',
         ['R3/target/ALL/target_evasion_count', 'R3/failure_manifest/member_count']),
        ('RQ2-I4', 'Detector diversity was not uniformly distributed: D_S/D_G failures overlapped, while D_M-B remained complementary '
                   'in the observed R2-D_S and R3 samples.',
         ['R2-D_S/transfer/ds_v2->dg_v1/joint_evasion_count', 'R3/pair/ds_v2~dg_v1/shared_fn', 'R2-D_S/dm_b_v1/fn', 'R3/dm_b_v1/fn'])]
    for fid, text, keys in interpretations:
        items.append(finding(fid, 'INTERPRETATION', text, keys, X))
    s.require(X['R2-D_S/target/ds_v2/target_evasion_count'] == 104 and X['R2-D_S/transfer/ds_v2->dm_b_v1/joint_evasion_count'] == 0,
              'INTERPRETATION_PREMISE_CONFLICT')
    answer = (f'At the three-detector stack level, no all-three common-mode failure was observed in the non-adaptive R1 reference or in '
              f'any frozen targeted or ensemble-aware population: all-three FN was {X["R1/all_three_fn"]}/{X["R1/attack_count"]} (R1), '
              f'{X["R2-DMB/all_three_fn"]}/{X["R2-DMB/attack_count"]} (R2-DMB), {X["R2-D_S/all_three_fn"]}/{X["R2-D_S/attack_count"]} '
              f'(R2-D_S) and {X["R3/all_three_fn"]}/{X["R3/attack_count"]} (R3). Complementarity was not uniform. Under D_S-targeted '
              f'pressure, {X["R2-D_S/transfer/ds_v2->dg_v1/joint_evasion_count"]} of {X["R2-D_S/target/ds_v2/target_evasion_count"]} '
              f'successful D_S evasions were also missed by D_G, whereas D_M-B missed {X["R2-D_S/transfer/ds_v2->dm_b_v1/joint_evasion_count"]} '
              f'of them. D_M-B had {X["R2-DMB/target/dm_b_v1/target_evasion_count"]}/{X["R2-DMB/attack_count"]} target evasions in R2-DMB '
              f'and {X["R3/dm_b_v1/fn"]}/{X["R3/attack_count"]} misses in R3. In R3 every D_S miss ({X["R3/ds_v2/fn"]}) was also a D_G miss. '
              'Overlapping D_S/D_G failures emerged, but no all-three common-mode failure was observed for these frozen populations and '
              'fixed generators.')
    not_established = ['D_M-B is universally robust.', 'The detector stack is unbreakable.',
        'Heterogeneous detectors are statistically independent.', 'EJF proves causal dependence between detector errors.',
        'Zero observed R3 events prove zero underlying all-three risk.',
        'Results generalize to arbitrary adversarial prompts, other generators, budgets or sources.',
        'Verifier effectiveness (RQ3) or production guarantees.']
    return dict(schema_version='cross_regime_rq2_findings_v1',
        question='Do heterogeneous detectors retain complementary error behavior under targeted and ensemble-aware adversarial pressure, '
                 'or do overlapping/common-mode failures emerge?',
        regimes=['R1', 'R2-DMB', 'R2-D_S', 'R3'], answer=answer, findings=items, not_established=not_established,
        r3_zero_event_caveat='The frozen R3 all-three CI [0.0, 0.0] is the empirical percentile-bootstrap result from a zero-event '
                             'population. It is NOT a population robustness bound and is not a true attack-success probability of 0. '
                             'Primary result: 0 observed simultaneous evasions / 97 frozen lineage-distinct parents.',
        causal_claims=False, independence_claims=False, significance_tests=False)


# ------------------------------------------------------------------- figures

def point(value, ci=None, label=None, tip=None):
    entry = dict(value=value if isinstance(value, (int, float)) and not isinstance(value, bool) else None)
    if entry['value'] is None:
        entry['short'] = {'UNDEFINED': 'UNDEF', 'NOT_APPLICABLE': 'N/A'}.get(value, str(value)[:6])
    if isinstance(ci, list):
        entry['lo'], entry['hi'] = ci
    if label:
        entry['label'] = label
    if tip:
        entry['tip'] = tip
    return entry


def figure_specs(metrics):
    X = index(metrics)
    rows = source_rows(metrics)
    note = 'R0, R1: mixed attack+benign. R2-DMB, R2-D_S, R3: attack-only. Whiskers: frozen 95% lineage-clustered percentile CIs where stored.'
    pair_label = lambda a, b: f'{LABEL[a]} x {LABEL[b]}'

    def pair_panels(key, label):
        return [dict(title=pair_label(a, b), groups=list(REGIMES), series=[dict(key=None, points=[
            point(X[f'{rid}/pair/{a}~{b}/{key}'], X[f'{rid}/ci/pair/{a}/{b}/{key}'],
                  label(X[f'{rid}/pair/{a}~{b}/{key}'], rid, a, b), f'{rid} {pair_label(a, b)} {key}') for rid in REGIMES])]) for a, b in PAIRS]

    frac = lambda v, rid, a, b: f'{v:.3f}' if isinstance(v, float) else None
    specs = {
        '01_fnr': dict(kind='grouped', title='Detector false-negative rate by regime',
            subtitle='Operational fixed thresholds; FNR = FN / attacks', groups=list(REGIMES), note=note, high=1.0,
            description='Grouped bars of FNR per detector for R0, R1, R2-DMB, R2-D_S and R3.',
            series=[dict(key=d, name=LABEL[d], points=[point(X[f'{rid}/{d}/fnr'], X[f'{rid}/ci/individual/{d}/fnr'],
                f'{X[f"{rid}/{d}/fn"]}/{X[f"{rid}/attack_count"]}', f'{rid} {LABEL[d]} FNR') for rid in REGIMES]) for d in IDS]),
        '02_pairwise_jfn': dict(kind='panels', title='Pairwise joint false-negative rate (JFN)',
            subtitle='JFN = shared FN / attacks', panels=pair_panels('jfn', lambda v, rid, a, b: f'{X[f"{rid}/pair/{a}~{b}/shared_fn"]}'),
            note=note, description='Small multiples of pairwise JFN by regime.'),
        '03_ejf': dict(kind='panels', diverging=True, title='Excess joint failure (EJF) by detector pair',
            subtitle='EJF = JFN - FNR_i x FNR_j (descriptive reference, not an independence test)',
            panels=pair_panels('ejf', lambda v, rid, a, b: ('0' if v == 0 else f'{v:+.3f}') if isinstance(v, float) else None), note=note,
            description='Small multiples of EJF by regime; red above zero, blue below.'),
        '04_fn_jaccard': dict(kind='panels', title='False-negative Jaccard by detector pair',
            subtitle='Shared FN / union FN; UNDEF where the union is empty', panels=pair_panels('fn_jaccard', frac), note=note,
            description='Small multiples of FN Jaccard by regime.'),
        '05_all_three_jfn': dict(kind='grouped', title='All-three joint false-negative rate',
            subtitle='Attacks missed by D_S, D_M-B and D_G simultaneously', groups=list(REGIMES),
            note='R3 [0, 0] is a zero-event percentile-bootstrap interval, not a population robustness bound.\n' + note,
            description='All-three JFN by regime with stored intervals.',
            series=[dict(key=None, name='All three', points=[point(X[f'{rid}/all_three_jfn'], X[f'{rid}/ci/all_three/jfn'],
                f'{X[f"{rid}/all_three_fn"]}/{X[f"{rid}/attack_count"]}', f'{rid} all-three JFN') for rid in REGIMES])]),
        '06_target_success': dict(kind='grouped', title='Targeted attack success: R2-DMB vs R2-D_S vs R3',
            subtitle='Target evasion rate (R3 target ALL = simultaneous evasion of all three)',
            groups=['R2-DMB\ntarget D_M-B', 'R2-D_S\ntarget D_S', 'R3\ntarget ALL'], high=0.25,
            note='Valid attempts: R2-DMB 800, R2-D_S 698, R3 97 lineage-distinct parents. Whiskers: frozen 95% CIs.',
            description='Target success rate per targeted regime.',
            series=[dict(key=None, name='Target success', points=[point(X[f'{rid}/target/{t}/target_evasion_rate'], X[f'{rid}/ci/target/{t}/evasion'],
                f'{X[f"{rid}/target/{t}/target_evasion_count"]}/{X[f"{rid}/target/{t}/valid_attempt_count"]}', f'{rid} target success')
                for rid, t in (('R2-DMB', 'dm_b_v1'), ('R2-D_S', 'ds_v2'), ('R3', 'ALL'))])]),
        '07_r2ds_transfer': dict(kind='panels', title='Evasion transfer from successful targeted evasions (ETR)',
            subtitle='ETR = joint evasions / target evasions', high=1.0,
            panels=[dict(title='R2-D_S (104 D_S evasions)', groups=['to D_M-B', 'to D_G'], series=[dict(key=None, points=[
                    point(X[f'R2-D_S/transfer/ds_v2->{d}/etr'], X[f'R2-D_S/ci/transfer/ds_v2->{d}/etr'],
                          f'{X[f"R2-D_S/transfer/ds_v2->{d}/joint_evasion_count"]}/104', f'R2-D_S ETR to {LABEL[d]}') for d in ('dm_b_v1', 'dg_v1')])]),
                dict(title='R2-DMB', status='UNDEFINED: 0 target evasions'),
                dict(title='R3', status='NOT_APPLICABLE: target ALL')],
            note='Frozen conditional ETR; not a detector-independent transfer probability.', description='R2-D_S transfer behavior.'),
        '08_source_conditioned': dict(kind='panels', title='Source-conditioned detector FNR', high=1.0,
            subtitle='R0 has no frozen source decomposition. InjecAgent is one inherited lineage cluster in every regime.',
            legend=[(LABEL[d], d) for d in IDS],
            panels=[dict(title=rid, groups=[f'{r["source"].split("_")[0]}\nn={r["attacks"]}' for r in rows[rid]],
                series=[dict(key=d, points=[point(r[f'{d}/fnr'], r.get(f'{d}/fnr/ci95'), f'{r[f"{d}/fn"]}', f'{rid} {r["source"]} {LABEL[d]}')
                        for r in rows[rid]]) for d in IDS]) for rid in ('R1', 'R2-DMB', 'R2-D_S', 'R3')],
            note='Bars: FN / source attacks. Labels: FN counts. Whiskers only where a frozen source interval exists (R3).',
            description='Per-source FNR by detector for R1, R2-DMB, R2-D_S and R3.'),
        '09_failure_patterns': dict(kind='heatmap', title='Failure-pattern distribution by regime',
            subtitle='Pattern bits = (D_S, D_M-B, D_G) miss; cell = count and share of attacks',
            columns=[dict(id=p['pattern_id'], meaning=short_meaning(p['pattern_id'])) for p in metrics['records'][0]['failure_patterns']],
            rows=[dict(regime=r['regime_id'], n=r['attack_count'], cells=[dict(count=p['count'], fraction=p['count'] / r['attack_count'])
                  for p in r['failure_patterns']]) for r in metrics['records']],
            note='111 = all-three common-mode miss. Attack rows only; R0/R1 benign samples excluded.',
            description='Heatmap of the eight failure patterns per regime.'),
        '10_verifier_status': dict(kind='status', title='Verifier recovery (RQ3) status',
            subtitle='No verifier inference performed; no recovery result is reported', rows=[
                dict(label='R3 base-stack all-three failure population', status=str(X['R3/failure_manifest/member_count'])),
                dict(label='Development-stage recovery denominator', status=str(X['RQ3/development_recovery_denominator'])),
                dict(label='Development-stage Recovery(V_k), V1/V2/V3', status='UNDEFINED'),
                dict(label='Verifier panel', status=VERIFIER_PANEL)],
            note='RQ3 remains NOT EMPIRICALLY IDENTIFIABLE FROM R3 DEVELOPMENT FAILURE POPULATION; Track B owns the final disposition.',
            description='Status-only panel; no verifier data.')}
    return specs


def short_meaning(pattern):
    missed = [LABEL[d] for d, bit in zip(IDS, pattern) if bit == '1']
    return 'none missed' if not missed else ('all missed' if len(missed) == 3 else '+'.join(missed) + ' miss')


def figure_manifest(specs, rendered):
    return dict(schema_version='cross_regime_figure_manifest_v1', renderer='detection_service/research_protocol/cross_regime_figures.py',
        renderer_sha256=s.sha256((ROOT / 'detection_service/research_protocol/cross_regime_figures.py').read_bytes()),
        backend='Dependency-free deterministic SVG (no plotting library; fixed numeric formatting)',
        palette=dict(categorical={LABEL[k]: v for k, v in figures.SERIES.items()}, single=figures.SINGLE,
                     diverging=dict(positive=figures.POSITIVE, negative=figures.NEGATIVE), sequential=list(figures.SEQUENTIAL),
                     validation='validate_palette.js light --pairs all: PASS; aqua contrast WARN relieved by direct labels and table views'),
        undefined='Non-observed values are labeled (UNDEF, N/A, status panels), never drawn as zero',
        verifier_panel=VERIFIER_PANEL,
        figures={name: dict(file='figures/' + name + '.svg', sha256=s.sha256(rendered[name + '.svg']), spec=spec)
                 for name, spec in specs.items()})


# ------------------------------------------------------------------ pipeline

def generate():
    metrics, handoff = build_registry()
    specs = figure_specs(metrics)
    rendered = figures.render(specs)
    values = {'r3_accepted_handoff_v1': handoff, 'cross_regime_metrics_v1': metrics, 'cross_regime_tables_v1': tables(metrics),
              'cross_regime_rq1_findings_v1': rq1(metrics), 'cross_regime_rq2_findings_v1': rq2(metrics),
              'cross_regime_figure_manifest_v1': figure_manifest(specs, rendered)}
    files = {SYN + name + '.json': s.bytes_json(value) for name, value in values.items()}
    files.update({SYN + 'figures/' + name: data for name, data in rendered.items()})
    return files, values


def write(files):
    for path, data in files.items():
        target = ROOT / path
        s.require(not target.exists() or target.read_bytes() == data, 'REFUSE_DIFFERENT_SYNTHESIS_BYTES:' + path)
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open('xb') as stream:
                stream.write(data)


def test_receipt():
    cases = list(ET.parse(TEST_RECEIPT).getroot().iter('testcase'))
    count = lambda tag: sum(case.find(tag) is not None for case in cases)
    receipt = dict(path=TEST_RECEIPT.relative_to(ROOT).as_posix(), sha256=s.sha256(TEST_RECEIPT.read_bytes()),
                   passed=len(cases) - count('failure') - count('error') - count('skipped'), failed=count('failure') + count('error'),
                   skipped=count('skipped'))
    s.require(cases and receipt['failed'] == receipt['skipped'] == 0, 'SYNTHESIS_TESTS_NOT_PASSING')
    return receipt


def freeze():
    files, values = generate()
    for path, data in files.items():
        s.require((ROOT / path).exists() and (ROOT / path).read_bytes() == data, 'SYNTHESIS_OUTPUT_NOT_REPRODUCED:' + path)
        s.require(git('show', 'HEAD:' + path) == data, 'SYNTHESIS_OUTPUT_NOT_COMMITTED:' + path)
    receipt = test_receipt()
    metrics = values['cross_regime_metrics_v1']
    bundle = dict(schema_version='cross_regime_result_bundle_v1', status='PASS',
        verdict='CROSS_REGIME_SYNTHESIS_COMPLETE_READY_FOR_RESEARCH_FREEZE',
        analysis_commit=git('rev-parse', 'HEAD').decode().strip(), branch='analysis/cross-regime-001',
        regime_provenance={r['regime_id']: provenance_row(r, metrics) for r in metrics['records']},
        outputs={path: s.sha256(data) for path, data in sorted(files.items())},
        integrated_track_b=dict(cherry_picked=['37e165ab5f9dde38798ea1c0bbcbc81d4f1c013d', '3b7d6271a621d07ee890d549df134bbd938d8e2d'],
            excluded=dict(commit='3ba519c2a70e7005d451f6eb4aeef55f02881bc0', reason='Verifier execution preparation; not required for synthesis'),
            phase1_scaffold_unchanged=True),
        rq1_answer=values['cross_regime_rq1_findings_v1']['answer'], rq2_answer=values['cross_regime_rq2_findings_v1']['answer'],
        rq3=metrics['rq3'], verifier_panel=VERIFIER_PANEL, test_receipt=receipt,
        integrity=dict(scientific_inference=False, detector_inference=False, verifier_inference=0, protected_access=False,
            resampling=False, frozen_scientific_artifacts_changed=False, frozen_scope_diff=metrics['frozen_scope_diff']),
        r2_dg='OPTIONAL_EXPLORATORY_APPENDIX; not executed (r2_dg_final_disposition_v1.json)')
    path = OUT / 'cross_regime_result_bundle_v1.json'
    write({SYN + 'cross_regime_result_bundle_v1.json': s.bytes_json(bundle)})
    from detection_service.research_protocol import cross_regime_report
    data = cross_regime_report.render(values, bundle, s.sha256(path.read_bytes()))
    s.require(not REPORT.exists() or REPORT.read_bytes() == data, 'REFUSE_DIFFERENT_REPORT_BYTES')
    if not REPORT.exists():
        with REPORT.open('xb') as stream:
            stream.write(data)
    print(json.dumps(dict(status='PASS', verdict=bundle['verdict'], tests=receipt, outputs=len(bundle['outputs'])), indent=2))


def provenance_row(record, metrics):
    if record['regime_id'] == 'R3':
        handoff = record['provenance']
        return dict(freeze_commit=handoff['freeze_commit_sha'], handoff_sha256=handoff['handoff_sha256'],
                    result_bundle=handoff['artifacts']['result_bundle'], failure_manifest=handoff['artifacts']['all_three_failure_manifest'],
                    experiment_id=record['provenance']['experiment_id'])
    reads = [r for r in metrics['read_receipt'] if r['path'] in {a['path'] for a in record['provenance']['artifacts']}]
    return dict(read_commit=record['provenance']['baseline_sha'], artifacts=reads, experiment_id=record['provenance']['experiment_id'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', choices=('generate', 'freeze'), required=True)
    args = parser.parse_args()
    if args.stage == 'generate':
        files, _ = generate()
        write(files)
        print(json.dumps(dict(status='GENERATED', files=len(files)), indent=2))
    else:
        freeze()
