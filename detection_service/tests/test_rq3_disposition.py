"""RQ3 development disposition tests over committed frozen bytes; no detector or verifier models."""
import json
import subprocess

import pytest

from detection_service.research_protocol import rq3_disposition as rq3
from detection_service.research_protocol.phase1_synthesis import sha256

FROZEN_SCIENTIFIC_DIRS = [rq3.P + name for name in ('r0', 'r1', 'r2_dmb', 'r2_ds', 'r3', 'operating_points')]


def git(*args, text=True):
    return subprocess.check_output(['git', *args], cwd=rq3.ROOT, text=text)


@pytest.fixture(scope='module')
def audit():
    return rq3.audit_population(rq3.FrozenReader())


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
