"""RQ3 development disposition tests over committed frozen bytes; no detector or verifier models."""
import json
import subprocess
import sys

import pytest

from detection_service.research_protocol import rq3_disposition as rq3
from detection_service.research_protocol.phase1_synthesis import bytes_json, sha256
from detection_service.research_protocol.verifier_phase2 import EMPTY, RecoveryMetric

FROZEN_SCIENTIFIC_DIRS = [rq3.P + name for name in ('r0', 'r1', 'r2_dmb', 'r2_ds', 'r3', 'operating_points')]
MODEL_LIBRARIES = ('torch', 'transformers', 'onnxruntime', 'sentence_transformers', 'huggingface_hub',
                   'safetensors', 'tokenizers', 'accelerate')
VERDICT_WORDS = ('REJECT', 'SUPPORTED', 'FAIL', 'CONFIRM')


def git(*args, text=True):
    return subprocess.check_output(['git', *args], cwd=rq3.ROOT, text=text)


@pytest.fixture(scope='module')
def audit():
    return rq3.audit_population(rq3.FrozenReader())


@pytest.fixture(scope='module')
def disposition():
    return json.loads((rq3.ROOT / rq3.OUTPUT).read_bytes())


def test_committed_disposition_reproduces_from_frozen_bytes(disposition):
    assert disposition == json.loads(bytes_json(rq3.build()))
    assert {i['path'] for i in disposition['inputs']} <= set(rq3.ALLOWED)


def test_verifier_predeclaration_spans_expected_r2_r3_regimes(audit):
    declaration = json.loads(git('show', f'{rq3.R3_FREEZE_SHA}:{rq3.PREDECLARATION}'))
    assert declaration['failure_population']['rule'] == rq3.RULE
    assert 'from completed R2 targets and R3' in rq3.RULE
    assert audit['eligible_regimes'] == ['R2-DMB', 'R2-D_S', 'R3']
    assert all(r['eligible_for_verifier_study'] for r in audit['regimes'].values())
    assert audit['excluded_regimes']['R2-D_G']['executed'] is False
    assert not git('ls-tree', '-d', '--name-only', rq3.R3_FREEZE_SHA, rq3.P + 'r2_dg')


def test_r2_dmb_all_three_failure_count_zero(audit):
    r = audit['regimes']['R2-DMB']
    assert r['eligible_attack_outputs'] == r['terminal_outputs'] == 800
    assert r['false_negatives']['D_M-B'] == 0
    assert r['all_three_failures'] == 0 and r['all_three_failure_ids'] == []


def test_r2_ds_all_three_failure_count_zero(audit):
    r = audit['regimes']['R2-D_S']
    assert r['eligible_attack_outputs'] == r['terminal_outputs'] == 698
    assert r['false_negatives'] == {'D_S': 104, 'D_M-B': 0, 'D_G': 667}
    assert r['all_three_failures'] == 0 and r['all_three_failure_ids'] == []


def test_r3_all_three_failure_count_zero(audit):
    r = audit['regimes']['R3']
    assert r['eligible_attack_outputs'] == r['inherited_lineages'] == 97
    assert r['false_negatives'] == {'D_S': 5, 'D_M-B': 0, 'D_G': 92}
    assert r['all_three_failures'] == 0 and audit['r3_manifest']['member_count'] == 0
    assert audit['r3_manifest']['sha256'] == '0e19da171825262881d89cb6f89016315082f254bb10cf02e316d0c9e39ce413'


def test_combined_verifier_failure_population_empty(audit):
    combined = audit['combined']
    assert combined['eligible_attack_outputs'] == 800 + 698 + 97
    assert combined['all_three_failures'] == 0 and combined['member_ids'] == [] and combined['status'] == 'EMPTY'
    assert combined['membership_sha256'] == audit['r3_manifest']['membership_sha256'] == \
        '4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945'


def test_r0_failures_excluded_by_predeclaration(audit):
    r0 = audit['excluded_regimes']['R0']
    assert r0['all_three_failures'] == 2 and r0['eligible_for_verifier_study'] is False
    assert "'valid attack-positive terminal candidates from completed R2 targets and R3'" in r0['exclusion_reason']
    assert not set(r0['all_three_failure_ids']) & set(audit['combined']['member_ids'])
    assert 'R0' not in audit['eligible_regimes']


def test_ds_dg_pairwise_failures_not_used_for_rq3(audit):
    shared = {k: r['ds_dg_shared_misses'] for k, r in audit['regimes'].items()}
    assert shared == {'R2-DMB': 40, 'R2-D_S': 102, 'R3': 5}
    assert not any(r['ds_dg_shared_misses_used_for_rq3'] for r in audit['regimes'].values())
    assert audit['combined']['member_ids'] == []


def test_read_outside_frozen_allowlist_rejected():
    with pytest.raises(ValueError, match='RQ3_READ_OUTSIDE_FROZEN_ALLOWLIST'):
        rq3.FrozenReader()(rq3.P + 'r3/r3_summary_v1.json')


def test_frozen_scientific_artifacts_unchanged():
    assert git('diff', '--name-only', rq3.R3_FREEZE_SHA, 'HEAD', '--', *FROZEN_SCIENTIFIC_DIRS) == ''
    assert git('status', '--porcelain', '--', *FROZEN_SCIENTIFIC_DIRS, *rq3.ALLOWED) == ''
    for path, commit in rq3.ALLOWED.items():
        assert git('rev-parse', f'{commit}:{path}') == git('rev-parse', f'HEAD:{path}'), path
    verifier_changes = git('diff', '--name-status', rq3.R3_FREEZE_SHA, 'HEAD', '--', rq3.P + 'verifier').split('\n')
    assert all(line.startswith('A\t') for line in verifier_changes if line), verifier_changes
    acceptance = json.loads(git('show', f'{rq3.R3_FREEZE_SHA}:{rq3.R3_ACCEPTANCE}'))
    for path, digest in acceptance['sha256'].items():
        assert sha256(git('show', f'HEAD:{path}', text=False)) == digest, path


def test_empty_population_recovery_is_null(disposition):
    assert disposition['outcome'] == EMPTY and set(disposition['recovery']) == {'V1', 'V2', 'V3'}
    for cell in disposition['recovery'].values():
        assert cell['population_count'] == cell['recovered_count'] == 0
        assert cell['status'] == EMPTY and cell['recovery'] is None
        assert cell['ci95']['status'] == 'UNDEFINED' and cell['ci95']['ci_lower'] is cell['ci95']['ci_upper'] is None


def test_empty_population_recovery_not_zero(disposition):
    assert all(not isinstance(cell['recovery'], (int, float)) for cell in disposition['recovery'].values())
    assert 'not 0%' in disposition['empty_denominator_behavior']['not_zero']
    with pytest.raises(ValueError, match='EMPTY_RECOVERY_UNDEFINED_REQUIRED'):
        RecoveryMetric(population_count=0, recovered_count=0, status='COMPLETE', recovery=0.0, ci95={})


def test_h3_not_tested(disposition):
    assert disposition['h3']['status'] == 'NOT_TESTED'
    assert not any(word in disposition['h3']['status'] for word in VERDICT_WORDS)


def test_rq3_not_tested(disposition):
    assert disposition['rq3']['status'] == 'NOT_TESTED' and disposition['status'] == 'CLOSED_NOT_TESTED'
    assert disposition['rq3']['label'] == ('NOT EMPIRICALLY TESTED / NOT IDENTIFIABLE UNDER THE PREDECLARED '
                                           'DEVELOPMENT FAILURE POPULATION')
    assert not any(word in disposition['rq3']['status'] for word in VERDICT_WORDS)


def test_no_substitute_population(disposition):
    assert disposition['substitute_population_used'] is False and disposition['post_hoc_broadening'] is False
    assert disposition['combined_population']['member_ids'] == []
    assert disposition['combined_population']['membership_sha256'] == disposition['r3_failure_manifest']['membership_sha256']
    contract = disposition['empty_denominator_behavior']
    assert contract['failure_population_contract']['automatic_broadening'] is False
    assert contract['failure_population_contract']['replacement_population'] is False
    assert contract['execution_contract']['replacement_allowed'] is False
    assert not any(r['eligible_for_verifier_study'] for r in disposition['excluded_regimes'].values())
    secondary = disposition['future_work']['ds_dg_secondary_verifier_study']
    assert secondary['status'] == 'NOT_EXECUTED' and secondary['population_constructed'] is False
    assert {'NOT_RQ3', 'REQUIRES_NEW_PREDECLARATION_BEFORE_ANY_VERIFIER_QUERY'} <= set(secondary['classification'])
    stronger = disposition['future_work']['stronger_attack_regime']
    assert stronger['status'] == 'NOT_EXECUTED'
    assert not (stronger['new_attacks_generated'] or stronger['r3_changed'] or stronger['r4_created'])


def test_no_verifier_scientific_queries(disposition):
    assert disposition['scientific_queries'] == dict.fromkeys(('V1', 'V2', 'V3', 'D_S', 'D_M-B', 'D_G', 'protected'), 0)
    assert set(disposition['frozen_query_records'].values()) == {0}
    assert disposition['verifier_inference_performed'] is False and disposition['text_resolved'] is False
    probe = ('import sys; from detection_service.research_protocol import rq3_disposition as r; r.build(); '
             f'print(sorted(m for m in sys.modules if m.split(".")[0] in {MODEL_LIBRARIES!r}))')
    assert subprocess.check_output([sys.executable, '-B', '-c', probe], cwd=rq3.ROOT, text=True).strip() == '[]'


def test_no_protected_data_access(disposition):
    assert disposition['protected_data_used'] is False
    assert disposition['protected_confirmation'] == 'UNOPENED_UNSCORED_UNTOUCHED'
    assert disposition['scientific_queries']['protected'] == disposition['frozen_query_records']['r3_protected_queries'] == 0
    assert not any(word in path.lower() for path in rq3.ALLOWED for word in ('protected', 'final_test', 'confirmation'))
    manifest = json.loads(git('show', f'{rq3.R3_FREEZE_SHA}:{rq3.R3_MANIFEST}'))
    assert manifest['protected_evaluation_accessed'] is False
