"""Phase-2 cross-regime synthesis: frozen inputs, R3 freeze gate, determinism and traceability."""
import copy
import hashlib
import json
import re
import subprocess
import sys

import pytest

from detection_service.research_protocol import cross_regime_figures as figures
from detection_service.research_protocol import cross_regime_synthesis as c
from detection_service.research_protocol import phase1_synthesis as s


@pytest.fixture(scope='module')
def generated():
    return c.generate()


@pytest.fixture(scope='module')
def metrics(generated):
    return generated[1]['cross_regime_metrics_v1']


@pytest.fixture(scope='module')
def X(metrics):
    return c.index(metrics)


def reader():
    return s.CommittedR3Reader(c.ROOT, phase2_authorized=True)


class SyntheticReader:
    evidence_kind = 'SYNTHETIC_FIXTURE'

    def __init__(self, data):
        self.data = data

    def __call__(self, commit, path):
        return self.data[path]


def test_all_frozen_regime_bundles_load(metrics):
    assert [r['regime_id'] for r in metrics['records']] == list(c.REGIMES)
    assert all(r['status'] == 'OBSERVED' for r in metrics['records'])
    assert {r['regime_id']: (r['attack_count'], r['benign_count']) for r in metrics['records']} == {
        'R0': (183, 952), 'R1': (800, 1000), 'R2-DMB': (800, 0), 'R2-D_S': (698, 0), 'R3': (97, 0)}
    assert metrics['population_type'] == {'R0': 'MIXED', 'R1': 'MIXED', 'R2-DMB': 'ATTACK_ONLY', 'R2-D_S': 'ATTACK_ONLY', 'R3': 'ATTACK_ONLY'}


def test_same_frozen_stack_across_regimes(metrics):
    keys = ('operational_threshold_ids', 'operational_thresholds', 'detector_manifest_sha', 'operating_policy_sha')
    stacks = {r['regime_id']: tuple(json.dumps(r['provenance']['frozen_bundle_provenance'][k]) for k in keys) for r in metrics['records']}
    assert len(set(stacks.values())) == 1
    assert [d['threshold'] for d in metrics['r3']['detector_identities']] == [0.5585373573968287, 0.0004967087297700347, 0.21291141211986545]
    assert metrics['r3']['detector_identities'][1]['model_sha256'] == '0bb192d2c468530479fa8ec0786f35d8bf5a8287e4ee401a953292d221736844'
    assert metrics['r3']['detector_identities'][2]['model_revision'] == '11614a155199674a0a95e6602d6ab0417b790ed0'


def test_frozen_headline_values(X):
    assert [X[f'R0/{d}/fn'] for d in c.IDS] == [70, 2, 141] and X['R0/all_three_fn'] == 2
    assert [X[f'R1/{d}/recall'] for d in c.IDS] == [0.8725, 1.0, 0.045] and X['R1/all_three_fn'] == 0
    assert X['R2-DMB/target/dm_b_v1/target_evasion_count'] == 0 and X['R2-DMB/all_three_fn'] == 0
    assert (X['R2-D_S/target/ds_v2/target_evasion_count'], X['R2-D_S/target/ds_v2/valid_attempt_count']) == (104, 698)
    assert X['R2-D_S/transfer/ds_v2->dg_v1/joint_evasion_count'] == 102 and X['R2-D_S/transfer/ds_v2->dm_b_v1/joint_evasion_count'] == 0
    assert X['R3/target/ALL/target_evasion_count'] == 0 and [X[f'R3/{d}/fn'] for d in c.IDS] == [5, 0, 92]
    assert X['R3/pair/ds_v2~dg_v1/shared_fn'] == 5 and X['R3/pair/ds_v2~dg_v1/jfn'] == 5 / 97
    assert X['R3/pair/ds_v2~dg_v1/ejf'] == pytest.approx(5 / 97 - (5 / 97) * (92 / 97), abs=1e-15)
    assert (X['R3/all_three_fn'], X['R3/all_three_jfn'], X['R3/ci/all_three/jfn']) == (0, 0.0, [0.0, 0.0])
    assert X['R3/source_count/LLMAIL_INJECT'] == 96 and X['R3/source_count/INJECAGENT_BASE'] == 1 and X['R3/inherited_lineages'] == 97


def test_r3_accepted_handoff_validates_against_freeze():
    handoff = c.build_handoff(reader())
    assert c.HANDOFF.read_bytes() == s.bytes_json(handoff)
    payload = c.validate_accepted_r3(handoff, reader())
    assert payload['all_three_failure_manifest']['member_count'] == 0
    assert handoff['freeze_commit_sha'] == 'adc2f7077203a7c3a8b7b58122123fa27e2b0918'


@pytest.mark.parametrize('mutate,code', [
    (lambda h: h.update(freeze_commit_sha=c.ACCEPTED_R3['terminal_freeze_commit']), 'FREEZE_COMMIT'),
    (lambda h: h.update(freeze_commit_sha='working-tree'), 'COMMITTED_FREEZE_SHA'),
    (lambda h: h.update(frozen=False), 'NOT_ACCEPTED_FROZEN'),
    (lambda h: h['artifacts'].pop('freeze_receipt'), 'PARTIAL'),
    (lambda h: h['supplements'].pop('predictions'), 'PARTIAL'),
    (lambda h: h['artifacts']['result_bundle'].update(sha256='0' * 64), 'HASH_MISMATCH'),
    (lambda h: h['artifacts']['common_mode'].update(member='core_metrics/failure_patterns'), 'ROLE_BINDING'),
    (lambda h: h['artifacts']['all_three_failure_manifest'].update(path='artifacts/research_protocol/r3/../r1/x.json'), 'PATH_INVALID'),
])
def test_r3_handoff_fails_closed(mutate, code):
    handoff = c.build_handoff(reader())
    mutate(handoff)
    with pytest.raises(ValueError, match=code):
        c.validate_accepted_r3(handoff, reader())


def test_r3_requires_committed_reader_and_post_freeze_commit():
    handoff = c.build_handoff(reader())
    with pytest.raises(ValueError, match='COMMITTED_READER'):
        c.validate_accepted_r3(handoff, lambda commit, path: b'')
    early = dict(copy.deepcopy(handoff), freeze_commit_sha=c.ACCEPTED_R3['terminal_freeze_commit'])
    with pytest.raises(subprocess.CalledProcessError):
        c.validate_accepted_r3(early, reader(), expected=dict(c.ACCEPTED_R3, freeze_commit_sha=early['freeze_commit_sha']))


@pytest.mark.parametrize('field,value,code', [
    ('failure_manifest_sha256', '0' * 64, 'FAILURE_MANIFEST_HASH'), ('membership_sha256', '1' * 64, 'MEMBERSHIP_HASH'),
    ('all_three_failures', 1, 'FAILURE_COUNT'), ('verdict', 'R3_COMPLETE_FAILURE_POPULATION_FROZEN_READY_FOR_PHASE2', 'FREEZE_RECEIPT_STATUS'),
    ('scoring_commit', '0' * 40, 'PREDICTION_MANIFEST|FAILURE_MANIFEST_BINDING|FREEZE_RECEIPT_COMMIT'),
])
def test_r3_expected_identity_mismatch_stops(field, value, code):
    handoff = c.build_handoff(reader())
    with pytest.raises(ValueError, match='R3_SYNTHESIS_INPUT_MISMATCH:(' + code + ')'):
        c.validate_accepted_r3(handoff, reader(), expected=dict(c.ACCEPTED_R3, **{field: value}))


def test_tampered_failure_population_rejected_after_hash_rebinding():
    handoff = c.build_handoff(reader())
    data = {d['path']: reader()(handoff['freeze_commit_sha'], d['path'])
            for d in (*handoff['artifacts'].values(), *handoff['supplements'].values())}
    path = handoff['artifacts']['all_three_failure_manifest']['path']
    manifest = json.loads(data[path])
    manifest['member_count'] = 1
    data[path] = s.bytes_json(manifest)
    handoff['artifacts']['all_three_failure_manifest']['sha256'] = s.sha256(data[path])
    handoff['evidence_kind'] = 'SYNTHETIC_FIXTURE'
    expected = dict(c.ACCEPTED_R3, failure_manifest_sha256=s.sha256(data[path]))
    with pytest.raises(ValueError, match='FAILURE_COUNT'):
        c.validate_accepted_r3(handoff, SyntheticReader(data), expected=expected)


def test_r3_empty_failure_manifest_preserved(metrics):
    path = 'artifacts/research_protocol/r3/r3_all_three_failure_manifest_v1.json'
    committed = subprocess.check_output(['git', 'show', c.ACCEPTED_R3['freeze_commit_sha'] + ':' + path], cwd=c.ROOT)
    assert (c.ROOT / path).read_bytes() == committed
    assert hashlib.sha256(committed).hexdigest() == '0e19da171825262881d89cb6f89016315082f254bb10cf02e316d0c9e39ce413'
    manifest = json.loads(committed)
    assert (manifest['status'], manifest['empty'], manifest['member_count'], manifest['members']) == ('EMPTY', True, 0, [])
    assert manifest['membership_sha256'] == hashlib.sha256(b'[]').hexdigest() == c.ACCEPTED_R3['membership_sha256']
    assert metrics['r3']['failure_manifest'] == dict(path=path, sha256=hashlib.sha256(committed).hexdigest(), status='EMPTY',
                                                    member_count=0, empty=True, membership_sha256=manifest['membership_sha256'])


def test_outputs_deterministic_and_match_disk(generated, metrics):
    files, values = generated
    for path, data in files.items():
        assert (c.ROOT / path).read_bytes() == data, path
    assert s.bytes_json(c.tables(metrics)) == s.bytes_json(c.tables(json.loads(s.bytes_json(metrics))))
    assert s.bytes_json(c.rq1(metrics)) == files[c.SYN + 'cross_regime_rq1_findings_v1.json']
    assert s.bytes_json(c.rq2(metrics)) == files[c.SYN + 'cross_regime_rq2_findings_v1.json']


def test_figures_deterministic(generated, metrics):
    files, values = generated
    specs = c.figure_specs(metrics)
    first, second = figures.render(specs), figures.render(copy.deepcopy(specs))
    assert first == second and len(first) == 10
    manifest = values['cross_regime_figure_manifest_v1']
    for name, data in first.items():
        assert files[c.SYN + 'figures/' + name] == data
        assert manifest['figures'][name[:-4]]['sha256'] == s.sha256(data)
        assert re.search(rb'(x|y|x1|x2|y1|y2|width|height|rx)="[-+]?(nan|inf)', data, re.I) is None
    assert c.VERIFIER_PANEL.encode() in first['10_verifier_status.svg']


def walk(value):
    if isinstance(value, dict):
        yield value
        for v in value.values():
            yield from walk(v)
    elif isinstance(value, list):
        for v in value:
            yield from walk(v)


def test_undefined_metrics_remain_undefined(generated, X):
    files, values = generated
    for cell in walk(values['cross_regime_tables_v1']):
        if 'status' in cell and 'value' in cell and cell['status'] in ('UNDEFINED', 'NOT_APPLICABLE', 'NOT_YET_OBSERVED'):
            assert cell['value'] is None
    assert X['R2-DMB/transfer/dm_b_v1->ds_v2/etr'] == X['R2-DMB/transfer/dm_b_v1->dg_v1/etr'] == 'UNDEFINED'
    assert all(X[f'RQ3/recovery/{v}'] == 'UNDEFINED' for v in ('V1', 'V2', 'V3')) and X['RQ3/development_recovery_denominator'] == 0
    assert X['R1/recovery/ds_v2/conditional_recovery'] == 'UNDEFINED'
    assert not any('NOT_YET_OBSERVED' in json.dumps(v) for k, v in values.items() if k != 'r3_accepted_handoff_v1')


def test_attack_only_fpr_guard(generated, metrics):
    rows = generated[1]['cross_regime_tables_v1']['tables']['A']
    for row in rows:
        if row['regime'] in c.ATTACK_ONLY:
            assert all(row[k] == s.cell(None, 'NOT_APPLICABLE') for k in ('fpr', 'roc_auc', 'ap'))
            assert row['tn'] is None and row['fp'] is None and row['benign_count'] == 0
        else:
            assert row['fpr']['status'] == 'OBSERVED' and row['benign_count'] > 0
    record = copy.deepcopy(next(r for r in metrics['records'] if r['regime_id'] == 'R3'))
    record['detectors'][0]['fpr'] = s.cell(0.0)
    with pytest.raises(ValueError):
        s.RegimeRecord.model_validate(record)


@pytest.mark.parametrize('name', ['cross_regime_rq1_findings_v1', 'cross_regime_rq2_findings_v1'])
def test_findings_trace_to_frozen_metrics(generated, X, name):
    block = generated[1][name]
    assert block['causal_claims'] is False and block['significance_tests'] is False
    for item in block['findings']:
        if item['kind'] in ('OBSERVED', 'INTERPRETATION'):
            assert item['evidence'], item['id']
        for evidence in item['evidence']:
            assert X[evidence['key']] == evidence['value'], (item['id'], evidence['key'])
    text = ' '.join([block['answer']] + [f['statement'] for f in block['findings']]).lower()
    for banned in ('universally robust', 'unbreakable', 'statistically independent', 'proves', 'zero underlying risk',
                   'true attack success probability'):
        assert banned not in text, banned


def test_rq2_preserves_zero_event_caveat_and_limits(generated):
    rq2 = generated[1]['cross_regime_rq2_findings_v1']
    assert 'NOT a population robustness bound' in rq2['r3_zero_event_caveat']
    assert '0 observed simultaneous evasions / 97' in rq2['r3_zero_event_caveat']
    assert any('Zero observed R3 events' in item for item in rq2['not_established'])


def test_no_detector_verifier_or_protected_access():
    # Without torch/transformers no detector or verifier model can execute; runners and scoring code stay unloaded.
    code = ('import sys,json;from detection_service.research_protocol import cross_regime_synthesis as c;m,h=c.build_registry();'
            'bad=sorted(x for x in sys.modules if x.split(".")[0] in ("torch","transformers","huggingface_hub","safetensors","sklearn") or '
            'x.rsplit(".",1)[-1] in ("verifier_phase2","verifier_preparation","ds_runtime","r3_run","r3_scoring","r3_generator"));'
            'print(json.dumps(dict(bad=bad,paths=[r["path"] for r in m["read_receipt"]])))')
    result = json.loads(subprocess.check_output([sys.executable, '-B', '-c', code], cwd=c.ROOT).decode().strip().splitlines()[-1])
    assert result['bad'] == []
    assert set(result['paths']) == set(s.ALLOWED)
    assert not any('protected' in p.lower() or 'final_test' in p.lower() for p in result['paths'])


def test_frozen_scientific_artifacts_unchanged(metrics):
    assert metrics['frozen_scope_diff'] == dict(baseline_to_head=[], r3_freeze_to_head=[], working_tree=[])
    for read in metrics['read_receipt']:
        assert s.sha256((c.ROOT / read['path']).read_bytes()) == read['sha256']
    changed = subprocess.check_output(['git', 'diff', '--name-only', c.ACCEPTED_R3['freeze_commit_sha'], 'HEAD'], cwd=c.ROOT).decode().split()
    # Branch context: RQ3 integration and the research freeze add exactly these paths on final/research-freeze-001.
    integrated = ('artifacts/research_protocol/verifier/failure_population_input_contract_v1.json',
        'artifacts/research_protocol/verifier/rq3_development_disposition_v1.json',
        'artifacts/research_protocol/verifier/verifier_phase2_execution_contract_v1.json',
        'artifacts/research_protocol/verifier/verifier_result_schema_v1.json', 'artifacts/research_protocol/final/',
        'detection_service/research_protocol/rq3_disposition.py', 'detection_service/research_protocol/verifier_phase2.py',
        'detection_service/research_protocol/research_freeze', 'detection_service/tests/test_rq3_disposition.py',
        'detection_service/tests/test_verifier_phase2.py', 'detection_service/tests/test_research_freeze.py')
    assert all(p.startswith(('artifacts/research_protocol/synthesis/', 'detection_service/research_protocol/phase1_',
        'detection_service/research_protocol/cross_regime_', 'detection_service/tests/test_phase1_synthesis.py',
        'detection_service/tests/test_cross_regime_synthesis.py', 'reviews/') + integrated) for p in changed), changed
    assert metrics['authoritative_queries'] == dict(ds_v2=0, dm_b_v1=0, dg_v1=0, verifier=0) and metrics['protected_access'] is False
