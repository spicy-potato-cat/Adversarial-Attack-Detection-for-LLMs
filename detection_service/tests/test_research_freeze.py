"""Stage-A RESEARCH-FREEZE-001 checks: accepted inputs, RQ3 pool, immutability, pre-access protected gate."""
import json
import subprocess

import pytest

from detection_service.research_protocol import cross_regime_synthesis as c
from detection_service.research_protocol import phase1_synthesis as s
from detection_service.research_protocol import research_freeze as r


@pytest.fixture(scope='module')
def built():
    return r.build()


@pytest.fixture(scope='module')
def files(built):
    return r.outputs(built)


def test_rq1_rq2_bundle_accepted(built):
    inputs = r.load_inputs()
    assert inputs['bundle']['verdict'] == 'CROSS_REGIME_SYNTHESIS_COMPLETE_READY_FOR_RESEARCH_FREEZE'
    assert inputs['bundle_sha256'] == s.sha256((c.ROOT / r.SYNTHESIS_BUNDLE).read_bytes())
    assert built['freeze']['rq1']['finding'].startswith('Detector behavior changed substantially and heterogeneously')
    assert built['freeze']['rq2']['finding'].startswith('Observed detector diversity was uneven.')
    assert built['freeze']['rq1']['accepted_answer'] == built['values']['cross_regime_rq1_findings_v1']['answer']
    assert built['freeze']['rq2']['accepted_answer'] == built['values']['cross_regime_rq2_findings_v1']['answer']


def test_rq3_bundle_accepted_full_pool(built):
    rq3 = built['freeze']['rq3']
    assert (rq3['status'], rq3['reason']) == ('NOT_TESTED', 'VERIFIER_RECOVERY_UNDEFINED_EMPTY_FAILURE_POPULATION')
    assert rq3['eligible_regimes'] == ['R2-DMB', 'R2-D_S', 'R3']
    assert (rq3['eligible_terminals'], rq3['all_three_failures']) == (1595, 0)
    assert all(v == dict(value=None, status='UNDEFINED') for v in rq3['recovery'].values()) and set(rq3['recovery']) == {'V1', 'V2', 'V3'}
    assert built['freeze']['h3']['status'] == 'NOT_TESTED'
    disposition = json.loads((c.ROOT / r.RQ3_DISPOSITION).read_bytes())
    pool = disposition['population_audit']
    assert sum(pool[k]['eligible_attack_outputs'] for k in ('R2-DMB', 'R2-D_S', 'R3')) == 1595
    assert sum(pool[k]['all_three_failures'] for k in ('R2-DMB', 'R2-D_S', 'R3')) == 0


def test_r0_not_substituted(built):
    disposition = json.loads((c.ROOT / r.RQ3_DISPOSITION).read_bytes())
    assert disposition['excluded_regimes']['R0']['eligible_for_verifier_study'] is False
    assert disposition['substitute_population_used'] is False and disposition['post_hoc_broadening'] is False
    assert built['freeze']['rq3']['substitute_population'] is False and built['freeze']['rq3']['r0_excluded']['all_three_failures'] == 2


def test_rq3_files_identical_to_accepted_head():
    changed = subprocess.check_output(['git', 'diff', '--name-only', c.ACCEPTED_R3['freeze_commit_sha'], r.ACCEPTED['rq3_head']], cwd=c.ROOT).decode().split()
    blob = lambda rev, path: subprocess.check_output(['git', 'rev-parse', rev + ':' + path], cwd=c.ROOT).strip()
    for path in changed:
        assert blob(r.ACCEPTED['rq3_head'], path) == blob('HEAD', path), path
        if path.endswith(('.json', '.csv')):
            assert subprocess.check_output(['git', 'show', r.ACCEPTED['rq3_head'] + ':' + path], cwd=c.ROOT) == (c.ROOT / path).read_bytes(), path


def test_development_artifacts_unchanged():
    scope = ['artifacts/research_protocol/' + d for d in ('r0', 'r1', 'r2_dmb', 'r2_ds', 'r3', 'synthesis')] + ['artifacts/models', 'detection_service/app']
    assert subprocess.check_output(['git', 'diff', '--name-only', r.ACCEPTED['rq1_rq2_head'], 'HEAD', '--', *scope], cwd=c.ROOT) == b''
    assert subprocess.check_output(['git', 'status', '--porcelain', '--', *scope], cwd=c.ROOT) == b''
    head = r.ACCEPTED['rq1_rq2_head']
    bundle = json.loads(subprocess.check_output(['git', 'show', head + ':' + r.SYNTHESIS_BUNDLE], cwd=c.ROOT))
    for path, digest in bundle['outputs'].items():
        assert s.sha256((c.ROOT / path).read_bytes()) == digest


def test_r3_failure_manifest_preserved():
    data = (c.ROOT / 'artifacts/research_protocol/r3/r3_all_three_failure_manifest_v1.json').read_bytes()
    assert s.sha256(data) == '0e19da171825262881d89cb6f89016315082f254bb10cf02e316d0c9e39ce413'
    assert json.loads(data)['membership_sha256'] == '4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945'


def test_detector_identities_and_thresholds_preserved(built):
    stack = {d['label']: d for d in built['freeze']['detector_stack']}
    assert [stack[k]['threshold'] for k in ('D_S', 'D_M-B', 'D_G')] == [0.5585373573968287, 0.0004967087297700347, 0.21291141211986545]
    assert [stack[k]['detector_id'] for k in ('D_S', 'D_M-B', 'D_G')] == ['ds_v2', 'dm_b_v1', 'dg_v1']
    assert stack['D_M-B']['model_sha256'] == '0bb192d2c468530479fa8ec0786f35d8bf5a8287e4ee401a953292d221736844'
    assert stack['D_G']['model_revision'] == '11614a155199674a0a95e6602d6ab0417b790ed0'
    assert built['protocol']['bound_for_any_future_authorized_protocol']['detector_stack'] == built['freeze']['detector_stack']
    assert s.sha256((c.ROOT / r.PREDECLARATION).read_bytes()) == r.ACCEPTED['verifier_predeclaration_sha256']


def test_protected_protocol_frozen_incomplete_before_access(built, files):
    protocol = built['protocol']
    assert protocol['status'] == 'PROTECTED_CONFIRMATION_PROTOCOL_INCOMPLETE'
    assert protocol['executable'] is False and protocol['stage_b_authorized'] is False
    assert protocol['protected_samples_opened'] is False and protocol['protected_queries'] == 0
    assert protocol['candidate_source']['dataset_id'] == 'DS-TXT-009'
    for row in protocol['governance_evidence']:
        assert s.sha256((c.ROOT / row['path']).read_bytes()) == row['sha256']
    freeze = json.loads(files[r.FINAL + r.FREEZE.name])
    assert freeze['protected_confirmation']['protocol']['sha256'] == s.sha256(files[r.FINAL + r.PROTOCOL.name])


def test_claim_matrix_frozen_before_access(built, files):
    matrix = built['matrix']
    assert matrix['frozen_before_protected_access'] is True and matrix['evaluation_status'] == 'NOT_EVALUATED_PROTECTED_CONFIRMATION_BLOCKED'
    statuses = {'CONFIRMED', 'PARTIALLY_CONFIRMED', 'QUALIFIED', 'CONTRADICTED', 'NOT_EVALUABLE'}
    for claim in matrix['claims']:
        assert set(claim['criteria']) == statuses and claim['development_evidence']
    X = built['X']
    for claim in matrix['claims']:
        for key, value in claim['development_evidence'].items():
            if '/' in key:
                assert X[key] == value, key
    freeze = json.loads(files[r.FINAL + r.FREEZE.name])
    assert freeze['protected_confirmation']['claim_confirmation_matrix']['sha256'] == s.sha256(files[r.FINAL + r.MATRIX.name])


def test_protected_data_not_opened_and_no_protected_outputs(built):
    final = c.ROOT / r.FINAL
    names = {p.name for p in final.iterdir()} if final.exists() else set()
    forbidden = {'protected_access_receipt_v1.json', 'protected_predictions_v1.csv', 'protected_prediction_manifest_v1.json',
                 'protected_runtime_receipt_v1.json', 'protected_result_bundle_v1.json'}
    assert not names & forbidden
    assert built['freeze']['protected_confirmation']['opened'] is False and built['freeze']['protected_confirmation']['scored'] is False
    assert built['freeze']['protected_confirmation']['statement'] == 'PROTECTED DATA HAS NOT BEEN OPENED OR SCORED AS OF THIS FREEZE.'


def test_verifier_scientific_queries_zero(built):
    assert set(built['freeze']['verifier_disposition']['scientific_queries'].values()) == {0}
    assert built['freeze']['integrity'] == dict(model_inference=False, verifier_queries=0, protected_queries=0, resampling=False,
                                                development_artifacts_changed=False)


def test_terminology_and_required_limitations(files):
    freeze = json.loads(files[r.FINAL + r.FREEZE.name])
    claims = ' '.join([freeze['rq1']['finding'], freeze['rq2']['finding'], freeze['rq3']['finding']] +
                      [x['text'] for x in freeze['limitations']]).lower()
    for banned in ('universally robust', 'unbreakable', 'strongest detector', 'stack is secure', 'are independent',
                   'proves causal', 'probability is zero', 'verifier recovery'):
        assert banned not in claims, banned
    assert 'D_M-B detected all 104 observed D_S-evasive terminals' in files['reviews/' + r.REPORT.name].decode()
    assert len(freeze['limitations']) >= 12
    assert 'PROTECTED DATA HAS NOT BEEN OPENED OR SCORED AS OF THIS FREEZE.' in files['reviews/' + r.REPORT.name].decode()


def test_freeze_reproducible(files):
    assert files == r.outputs(r.build())
    for path, data in files.items():
        if (c.ROOT / path).exists():
            assert (c.ROOT / path).read_bytes() == data, path
