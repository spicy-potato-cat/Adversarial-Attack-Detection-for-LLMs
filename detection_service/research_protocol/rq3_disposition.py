"""Phase 2 Track B RQ3 development disposition from committed frozen evidence; no model loading."""
from __future__ import annotations
import argparse
import csv
import io
import json
from pathlib import Path
import subprocess
from detection_service.research_protocol.phase1_synthesis import bytes_json, require, sha256
from detection_service.research_protocol.verifier_phase2 import EMPTY, RecoveryMetric
from detection_service.research_protocol.verifier_preparation import REVISIONS

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = 'artifacts/research_protocol/verifier/rq3_development_disposition_v1.json'
R3_FREEZE_SHA = 'adc2f7077203a7c3a8b7b58122123fa27e2b0918'
PREP_SHA = '3b7d6271a621d07ee890d549df134bbd938d8e2d'
P = 'artifacts/research_protocol/'
PREDECLARATION = P + 'verifier/verifier_study_predeclaration_v1.json'
POPULATION_CONTRACT = P + 'verifier/failure_population_input_contract_v1.json'
EXECUTION_CONTRACT = P + 'verifier/verifier_phase2_execution_contract_v1.json'
R2_DG_DISPOSITION = P + 'synthesis/r2_dg_final_disposition_v1.json'
R3_MANIFEST = P + 'r3/r3_all_three_failure_manifest_v1.json'
R3_ACCEPTANCE = P + 'r3/r3_final_acceptance_v1.json'
R3_TRANSITIONS = P + 'r3/r3_parent_child_transitions_v1.json'
R2_DMB_ACCEPTANCE = P + 'r2_dmb/r2_dmb_final_acceptance_v1.json'
R2_DS_ACCEPTANCE = P + 'r2_ds/r2_ds_final_acceptance_v2.json'
R1_PREDICTIONS = P + 'r1/r1_predictions_v1.csv'
R1_REGISTRY = P + 'protocol_patches/exp_protocol_001_patch_001.json'
R0_PREDICTIONS = P + 'r0/r0_operational_predictions_v1.csv'
HASH_INVENTORY = P + 'exp_protocol_001_final_hash_inventory_v1.json'
OPERATING_POINTS = P + 'operating_point_manifest_v1.json'

# Verbatim frozen predeclaration text; any drift fails closed.
RULE = ('After base experiments close and separate authorization: valid attack-positive terminal candidates '
        'from completed R2 targets and R3 with all three OK operational BENIGN decisions; no initial R1 misses '
        'in primary population.')
EMPTY_RULE = 'UNDEFINED; null rate and CI, no substitute population'
PRIMARY_METRIC = 'Recovery(V_k) = count verifier ATTACK / frozen base-stack failure population N'
VALID = 'VALID_REVERSIBLE_TEXT_PRESERVING'
DETECTORS = ('ds_v2', 'dm_b_v1', 'dg_v1')
LABELS = {'ds_v2': 'D_S', 'dm_b_v1': 'D_M-B', 'dg_v1': 'D_G'}

ELIGIBLE = {
    'R2-DMB': dict(predictions=P + 'r2_dmb/r2_dmb_predictions_v1.csv',
                   terminals=P + 'r2_dmb/r2_dmb_terminal_manifest_v1.json', manifest_key='R2_DMB'),
    'R2-D_S': dict(predictions=P + 'r2_ds/r2_ds_predictions_v1.csv',
                   terminals=P + 'r2_ds/r2_ds_terminal_manifest_v1.json', manifest_key='R2_DS'),
    'R3': dict(predictions=P + 'r3/r3_predictions_v1.csv',
               terminals=P + 'r3/r3_terminal_manifest_v1.json', manifest_key=None),
}

# Frozen input -> registry whose committed `sha256` map records its hash at the freeze.
BINDINGS = {
    ELIGIBLE['R2-DMB']['predictions']: R2_DMB_ACCEPTANCE, ELIGIBLE['R2-DMB']['terminals']: R2_DMB_ACCEPTANCE,
    ELIGIBLE['R2-D_S']['predictions']: R2_DS_ACCEPTANCE, ELIGIBLE['R2-D_S']['terminals']: R2_DS_ACCEPTANCE,
    ELIGIBLE['R3']['predictions']: R3_ACCEPTANCE, ELIGIBLE['R3']['terminals']: R3_ACCEPTANCE,
    R3_MANIFEST: R3_ACCEPTANCE, R3_TRANSITIONS: R3_ACCEPTANCE,
    R1_PREDICTIONS: R1_REGISTRY, R0_PREDICTIONS: HASH_INVENTORY, OPERATING_POINTS: HASH_INVENTORY,
}
# Read allowlist: scientific evidence at the accepted R3 freeze, Phase 2 contracts at accepted preparation.
ALLOWED = {path: R3_FREEZE_SHA for path in (*BINDINGS, *set(BINDINGS.values()), PREDECLARATION, R3_ACCEPTANCE)}
ALLOWED.update({path: PREP_SHA for path in (POPULATION_CONTRACT, EXECUTION_CONTRACT, R2_DG_DISPOSITION)})


class FrozenReader:
    """Committed bytes only, from the explicit allowlist at its pinned commit; every read is recorded."""
    def __init__(self, root=ROOT):
        self.root = Path(root)
        self.reads = {}

    def __call__(self, path):
        require(path in ALLOWED, 'RQ3_READ_OUTSIDE_FROZEN_ALLOWLIST')
        commit = ALLOWED[path]
        data = subprocess.check_output(['git', 'show', f'{commit}:{path}'], cwd=self.root)
        self.reads[path] = dict(path=path, commit=commit, sha256=sha256(data))
        return data

    def json(self, path):
        return json.loads(self(path))

    def bound(self, path):
        data = self(path)
        registry = BINDINGS.get(path)
        if registry:
            require(self.json(registry)['sha256'].get(path) == sha256(data), 'RQ3_FROZEN_INPUT_HASH_MISMATCH')
        return data


def membership_sha256(members):
    """R3 manifest definition: canonical ASCII JSON, sorted keys, compact separators, no newline."""
    return sha256(json.dumps(members, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('ascii'))


def predictions(raw):
    samples = {}
    for row in csv.DictReader(io.StringIO(raw.decode('utf-8'), newline='')):
        s = samples.setdefault(row['sample_id'], dict(truth=row['truth_label'], decisions={}))
        require(s['truth'] == row['truth_label'] and row['detector_id'] in DETECTORS and
                row['detector_id'] not in s['decisions'], 'RQ3_PREDICTION_ROW_CONFLICT')
        s['decisions'][row['detector_id']] = (row['status'], row['operational_binary_prediction'])
    require(all(set(s['decisions']) == set(DETECTORS) for s in samples.values()), 'RQ3_PREDICTION_COVERAGE_INCOMPLETE')
    return samples


def benign(sample, detector):
    return sample['decisions'][detector] == ('OK', '0')


def all_ok(sample):
    return all(status == 'OK' for status, _ in sample['decisions'].values())


def all_three(sample):
    return all(benign(sample, d) for d in DETECTORS)


def fn_counts(samples, ids):
    return {LABELS[d]: sum(benign(samples[i], d) for i in ids) for d in DETECTORS}


def audit_regime(reader, regime):
    """Apply the predeclared rule to one eligible regime's frozen terminals and operational predictions."""
    spec = ELIGIBLE[regime]
    raw = reader.bound(spec['predictions'])
    samples = predictions(raw)
    terminals = json.loads(reader.bound(spec['terminals']))['terminals']
    ids = [t['sample_id'] for t in terminals]
    require(len(set(ids)) == len(ids) and set(ids) == set(samples), 'RQ3_TERMINAL_PREDICTION_MEMBERSHIP_CONFLICT')
    valid = {t['sample_id'] for t in terminals if t['validity_status'] == VALID and t['inverse_reconstruction'] is True}
    eligible = sorted(i for i in valid if samples[i]['truth'] == '1' and all_ok(samples[i]))
    failures = sorted(i for i in eligible if all_three(samples[i]))
    shared = sorted(i for i in eligible if benign(samples[i], 'ds_v2') and benign(samples[i], 'dg_v1'))
    keep = set(eligible)
    return dict(regime=regime, eligible_for_verifier_study=True, terminal_outputs=len(terminals),
        valid_terminal_outputs=len(valid), eligible_attack_outputs=len(eligible),
        canonical_unique_outputs=len({(t['parent_sample_id'], t['terminal_text_sha256'])
                                      for t in terminals if t['sample_id'] in keep}),
        inherited_lineages=len({t['lineage_id'] for t in terminals if t['sample_id'] in keep}),
        false_negatives=fn_counts(samples, eligible), all_three_failures=len(failures),
        all_three_failure_ids=failures, ds_dg_shared_misses=len(shared), ds_dg_shared_misses_used_for_rq3=False,
        predictions_path=spec['predictions'], predictions_sha256=sha256(raw))


def audit_excluded(reader, regime, path, reason):
    raw = reader.bound(path)
    samples = predictions(raw)
    attacks = sorted(i for i, s in samples.items() if s['truth'] == '1')
    failures = sorted(i for i in attacks if all_ok(samples[i]) and all_three(samples[i]))
    return dict(regime=regime, eligible_for_verifier_study=False, attack_outputs=len(attacks),
        all_three_failures=len(failures), all_three_failure_ids=failures, exclusion_reason=reason,
        predictions_path=path, predictions_sha256=sha256(raw))


def audit_population(reader):
    """Full predeclared pool: eligible R2/R3 terminals, plus audited regimes the rule excludes."""
    declaration_raw = reader(PREDECLARATION)
    declaration = json.loads(declaration_raw)
    manifest = json.loads(reader.bound(R3_MANIFEST))
    require(manifest['verifier_contract_sha256'] == sha256(declaration_raw), 'RQ3_PREDECLARATION_BINDING_CONFLICT')
    population = declaration['failure_population']
    require(declaration['experiment_id'] == 'VERIFIER-RECOVERY-001' and population['rule'] == RULE and
            population['empty'] == EMPTY_RULE and declaration['primary_metric'] == PRIMARY_METRIC and
            declaration['failure_population_tuning'] is False, 'RQ3_PREDECLARATION_TEXT_CONFLICT')
    require(manifest['status'] == 'EMPTY' and manifest['empty'] is True and manifest['member_count'] == 0 and
            manifest['members'] == [] and manifest['freeze_before_verifier_inference'] is True and
            manifest['verifier_authoritative_queries'] == 0 and manifest['protected_evaluation_accessed'] is False,
            'RQ3_FROZEN_MANIFEST_STATE_CONFLICT')
    regimes = {r: audit_regime(reader, r) for r in ELIGIBLE}
    r3 = regimes['R3']
    require(manifest['prediction_sha256'] == r3['predictions_sha256'] and
            manifest['terminal_manifest_sha256'] == reader.reads[ELIGIBLE['R3']['terminals']]['sha256'] and
            manifest['membership_sha256'] == membership_sha256(r3['all_three_failure_ids']) and
            manifest['member_count'] == r3['all_three_failures'], 'RQ3_R3_MANIFEST_RECOUNT_CONFLICT')
    for regime, spec in ELIGIBLE.items():
        if spec['manifest_key']:
            frozen = manifest['frozen_R2_failure_populations'][spec['manifest_key']]
            require(frozen['prediction_sha256'] == regimes[regime]['predictions_sha256'] and
                    frozen['count'] == regimes[regime]['all_three_failures'], 'RQ3_R2_MANIFEST_RECOUNT_CONFLICT')
    r2_dg = reader.json(R2_DG_DISPOSITION)
    require(r2_dg['executed'] is False and r2_dg['blocks']['verifier_study'] is False, 'RQ3_R2_DG_STATE_CONFLICT')
    domain = "admits only 'valid attack-positive terminal candidates from completed R2 targets and R3'"
    excluded = {
        'R0': audit_excluded(reader, 'R0', R0_PREDICTIONS,
            f'Outside the predeclared eligibility domain: the frozen rule {domain}; R0 is neither a completed R2 '
            'target nor R3.'),
        'R1': audit_excluded(reader, 'R1', R1_PREDICTIONS,
            "The frozen rule states 'no initial R1 misses in primary population' and " + domain + '.'),
        'R2-D_G': dict(regime='R2-D_G', eligible_for_verifier_study=False, executed=False,
            classification=r2_dg['classification'], all_three_failures=None,
            exclusion_reason=f'No completed R2-D_G target exists; the frozen rule {domain}.'),
    }
    failures = sorted(i for r in regimes.values() for i in r['all_three_failure_ids'])
    return dict(predeclaration=dict(path=PREDECLARATION, sha256=sha256(declaration_raw),
            experiment_id=declaration['experiment_id'], rule=RULE, empty_rule=EMPTY_RULE,
            protected_rule=population['protected'], duplicates_rule=population['duplicates']),
        eligible_regimes=list(ELIGIBLE), regimes=regimes, excluded_regimes=excluded,
        combined=dict(eligible_attack_outputs=sum(r['eligible_attack_outputs'] for r in regimes.values()),
            all_three_failures=len(failures), member_ids=failures, membership_sha256=membership_sha256(failures),
            status='EMPTY' if not failures else 'NONEMPTY'),
        r3_manifest=dict(path=R3_MANIFEST, sha256=reader.reads[R3_MANIFEST]['sha256'],
            membership_sha256=manifest['membership_sha256'], member_count=manifest['member_count']))


def recovery_cells():
    """Predeclared empty rule through the frozen result schema: null rate and CI, never 0."""
    return {v: RecoveryMetric(population_count=0, recovered_count=0, status=EMPTY, recovery=None,
                ci95=dict(status='UNDEFINED', ci_lower=None, ci_upper=None, reason='ZERO_DENOMINATOR')
            ).model_dump(mode='json') for v in sorted(REVISIONS)}


def operating_point_caveat(reader):
    manifest = json.loads(reader.bound(OPERATING_POINTS))
    points = {p['detector_id']: p for p in manifest['points']}
    r1 = predictions(reader.bound(R1_PREDICTIONS))

    def positive_rate(truth, detector):
        rows = [s for s in r1.values() if s['truth'] == truth and s['decisions'][detector][0] == 'OK']
        hits = sum(s['decisions'][detector][1] == '1' for s in rows)
        return dict(numerator=hits, denominator=len(rows), value=hits / len(rows))
    return dict(development_target_benign_fpr=manifest['target_fpr'],
        development_selection_partition=manifest['selection_partition'],
        development_benign_count=manifest['selection_benign_count'],
        detectors={LABELS[d]: dict(threshold=points[d]['threshold'], threshold_id=points[d]['threshold_id'],
            threshold_input_score_type=points[d]['threshold_input_score_type'],
            development_attained_benign_fpr=points[d]['attained_fpr'],
            r1_attack_recall=positive_rate('1', d), r1_benign_fpr=positive_rate('0', d)) for d in DETECTORS},
        interpretation='D_M-B retained complete observed attack coverage in the frozen R1/R2/R3 samples considered '
            'here, but this occurred alongside substantial benign false-positive inflation under R1 distribution '
            'shift. All three thresholds came from the same development 3% benign-FPR budget; D_M-B operates on '
            'its raw attack probability at about 0.0005. Its zero-miss behavior is not cost-free robustness and '
            'does not establish D_M-B as the strongest detector.')


def r3_caveat(reader, r3):
    terminals = json.loads(reader.bound(ELIGIBLE['R3']['terminals']))
    overall = json.loads(reader.bound(R3_TRANSITIONS))['overall']
    moves = {LABELS[d]: overall[d] for d in DETECTORS}
    require(all(m['catch_to_miss'] + m['miss_to_miss'] == r3['false_negatives'][k] for k, m in moves.items()),
            'RQ3_R3_TRANSITION_RECOUNT_CONFLICT')
    return dict(parents=terminals['parent_count'], inherited_lineages=terminals['inherited_lineages'],
        source_counts=terminals['source_counts'], d_s_terminal_misses=r3['false_negatives']['D_S'],
        transitions=moves, all_three_successes=r3['all_three_failures'],
        interpretation='All D_S terminal misses were inherited parent misses (miss to miss); the R3 optimizer '
            'induced no new D_S or D_M-B miss. New degradation occurred only on D_G. 96 of 97 parents are '
            'LLMail-Inject and one is InjecAgent, which sharply limits source-level generalization.')


def build(root=ROOT):
    reader = FrozenReader(root)
    audit = audit_population(reader)
    require(audit['combined']['all_three_failures'] == 0,
            'RQ3_NONEMPTY_POPULATION_REQUIRES_HANDOFF_GATED_EXECUTION')
    population_contract = reader.json(POPULATION_CONTRACT)
    execution = reader.json(EXECUTION_CONTRACT)
    require(population_contract['empty_status'] == EMPTY and population_contract['automatic_broadening'] is False and
            population_contract['replacement_population'] is False and execution['empty'] == EMPTY and
            execution['replacement_allowed'] is False and execution['no_future_sample_tuning'] is True,
            'RQ3_EMPTY_POLICY_CONFLICT')
    acceptance = reader.json(R3_ACCEPTANCE)
    require(acceptance['verdict'] == 'R3_COMPLETE_EMPTY_FAILURE_POPULATION_READY_FOR_PHASE2_REVIEW' and
            acceptance['verifier_queries'] == 0 and acceptance['protected_queries'] == 0, 'RQ3_R3_ACCEPTANCE_CONFLICT')
    manifest = json.loads(reader.bound(R3_MANIFEST))
    require('samples' not in manifest and 'population_count' not in manifest, 'RQ3_MANIFEST_SHAPE_CHANGED')
    caveats = dict(operating_point=operating_point_caveat(reader), r3=r3_caveat(reader, audit['regimes']['R3']))
    return dict(artifact_version='rq3_development_disposition_v1', experiment_id='VERIFIER-RECOVERY-001',
        status='CLOSED_NOT_TESTED', outcome=EMPTY, r3_freeze_commit=R3_FREEZE_SHA, phase2_preparation_commit=PREP_SHA,
        predeclaration=audit['predeclaration'], eligible_regimes=audit['eligible_regimes'],
        population_audit=audit['regimes'], excluded_regimes=audit['excluded_regimes'],
        combined_population=audit['combined'], r3_failure_manifest=audit['r3_manifest'],
        primary_metric=dict(definition=PRIMARY_METRIC, conditioning_event='Attack-positive eligible terminal with '
            'all three base detectors OK operational BENIGN (F_E = 1)'),
        empty_denominator_behavior=dict(status=EMPTY, predeclaration=EMPTY_RULE,
            failure_population_contract=dict(path=POPULATION_CONTRACT, empty_status=population_contract['empty_status'],
                automatic_broadening=False, replacement_population=False),
            execution_contract=dict(path=EXECUTION_CONTRACT, empty=execution['empty'], replacement_allowed=False),
            not_zero='Recovery is a conditional rate with zero denominator; it is null and UNDEFINED, not 0%.'),
        recovery=recovery_cells(),
        rq3=dict(status='NOT_TESTED', label='NOT EMPIRICALLY TESTED / NOT IDENTIFIABLE UNDER THE PREDECLARED '
            'DEVELOPMENT FAILURE POPULATION', reason='Recovery(V_k) is conditional on base-stack all-three failure; '
            'the predeclared development failure population across R2-DMB, R2-D_S and R3 is empty, so the '
            'conditional estimand has no denominator.'),
        h3=dict(status='NOT_TESTED', reason='H3 contrasts standalone verifier accuracy with conditional Recovery on '
            'base-stack failures. The required non-empty conditional population never occurred, so H3 received no '
            'evidence either way.'),
        scientific_queries={'V1': 0, 'V2': 0, 'V3': 0, 'D_S': 0, 'D_M-B': 0, 'D_G': 0, 'protected': 0},
        frozen_query_records=dict(r3_verifier_queries=acceptance['verifier_queries'],
            r3_protected_queries=acceptance['protected_queries'],
            manifest_verifier_authoritative_queries=manifest['verifier_authoritative_queries']),
        verifier_inference_performed=False, text_resolved=False, substitute_population_used=False,
        post_hoc_broadening=False, protected_data_used=False, protected_confirmation='UNOPENED_UNSCORED_UNTOUCHED',
        phase2_handoff_gate=dict(status='NOT_INVOKED_EMPTY_POPULATION', reason='The handoff-gated path '
            '(validate_r3_handoff, load_failure_population) guards text resolution and verifier queries. The R3 '
            'freeze commit carries no separate common_mode, failure_patterns, uncertainty or freeze_receipt handoff '
            'files, and its failure manifest uses r3_all_three_failure_manifest_v1 fields (members, member_count, '
            'status EMPTY) rather than failure_population_input_contract_v1 fields. Membership was therefore read '
            'from committed manifest bytes and independently recounted. With zero members no text is resolved and '
            'no verifier executes, so the outcome does not depend on the gate.'),
        caveats=caveats,
        future_work=dict(
            ds_dg_secondary_verifier_study=dict(status='NOT_EXECUTED', population_constructed=False,
                classification=['NOT_RQ3', 'NOT_PART_OF_CURRENT_FROZEN_STUDY',
                                'REQUIRES_NEW_PREDECLARATION_BEFORE_ANY_VERIFIER_QUERY'],
                question='If D_M-B were absent, how would the candidate verifiers compare with the observed D_M-B '
                    'complementary detection behavior?',
                observed_shared_misses_before_reconciliation={r: audit['regimes'][r]['ds_dg_shared_misses']
                                                              for r in ('R2-D_S', 'R3')}),
            stronger_attack_regime=dict(status='NOT_EXECUTED', classification=['NOT_AN_RQ3_SUBSTITUTE',
                'NEW_REGIME_REQUIRES_SEPARATE_PREDECLARATION'], r3_changed=False, attack_budget_changed=False,
                new_attacks_generated=False, r4_created=False)),
        inputs=sorted(reader.reads.values(), key=lambda r: r['path']))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default=OUTPUT)
    parser.add_argument('--check', action='store_true', help='fail if the committed disposition is stale')
    args = parser.parse_args(argv)
    data = bytes_json(build())
    path = Path(args.output)
    if args.check:
        require(json.loads(path.read_bytes()) == json.loads(data), 'RQ3_DISPOSITION_STALE')
    else:
        path.write_bytes(data)


if __name__ == '__main__':
    main()
