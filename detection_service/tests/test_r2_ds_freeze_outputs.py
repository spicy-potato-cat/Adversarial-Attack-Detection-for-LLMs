"""Post-generation, pre-transfer output acceptance; no scoring calls."""

import pytest

from detection_service.research_protocol import r2_ds_predeclare as p,r2_ds_freeze as freeze


@pytest.fixture(scope='module')
def accepted():
    return freeze.validate()


def test_r2_ds_terminal_one_per_parent(accepted):
    assert accepted[0]['parents']==accepted[0]['terminals']==p.count()


def test_r2_ds_inverse_reconstruction_outputs(accepted):
    assert accepted[0]['inverse_passed']==p.count() and accepted[0]['inverse_failed']==0


def test_r2_ds_no_payload_deletion_outputs(accepted):
    assert accepted[0]['payload_deletion_violations']==accepted[0]['invalid_utf8']==0


def test_r2_ds_no_dmb_generation_query(accepted):
    assert accepted[0]['generation_call_counts']['D_M_B']==0


def test_r2_ds_no_dg_generation_query(accepted):
    assert accepted[0]['generation_call_counts']['D_G']==0


def test_r2_ds_no_ensemble_generation_query(accepted):
    assert accepted[0]['generation_call_counts']['ensemble']==0


def test_r2_ds_query_budget_outputs(accepted):
    assert accepted[0]['max_target_queries']<=61 and accepted[0]['query_budget_violations']==0


def test_r2_ds_terminal_hashes_stable(accepted):
    receipt=p.files.read_json(p.OUT/'r2_ds_freeze_acceptance_v1.json')
    for name,expected in receipt['sha256'].items():
        assert p.files.sha(p.OUT/name)==expected


def test_r2_ds_regime_manifest_valid():
    from detection_service.research_protocol.regime_contract import FrozenRegimeContracts
    from detection_service.research_protocol.r2_ds_transfer_run import manifest
    value=FrozenRegimeContracts().validate_manifest(manifest())
    assert value.sample_count==value.attack_count==p.count() and value.benign_count==0
    assert value.threat_regime=='R2_SINGLE_DETECTOR_TARGETED'
    assert all(s.target_detector=='D_S' and s.valid_attack_attempt for s in value.samples)


def test_r2_ds_raw_text_not_committed(accepted):
    assert not p.git('ls-files','--','detection_service/outputs/r2-ds-001').decode().strip()
    rows=p.files.read_json(p.OUT/'r2_ds_terminal_manifest_v1.json')['terminals']
    assert all(not any(k in r for k in ('text','prompt','original','replacement','script')) for r in rows)


def test_r2_ds_implementation_precedes_generation(accepted):
    stored=p.files.read_json(p.OUT/'r2_ds_generator_manifest_v1.json')
    from detection_service.research_protocol.r2_ds_generate_run import implementation_anchor
    assert implementation_anchor()==stored['implementation_commit']
    assert p.git('merge-base','--is-ancestor',stored['predeclaration_commit'],stored['implementation_commit'])==b''
