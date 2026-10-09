"""Phase 2 Track B RQ3 development disposition from committed frozen evidence; no model loading."""
from __future__ import annotations
import csv
import io
import json
from pathlib import Path
import subprocess
from detection_service.research_protocol.phase1_synthesis import require, sha256

ROOT = Path(__file__).resolve().parents[2]
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
