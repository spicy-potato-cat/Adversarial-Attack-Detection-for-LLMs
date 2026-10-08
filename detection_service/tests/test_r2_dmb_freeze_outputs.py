"""Post-generation, pre-transfer output acceptance; no scoring calls."""

import pytest

from detection_service.research_protocol import r2_dmb_predeclare as p,r2_dmb_freeze as freeze


@pytest.fixture(scope='module')
def accepted():
    return freeze.validate()


def test_r2_dmb_terminal_one_per_parent(accepted):
    assert accepted[0]['parents']==accepted[0]['terminals']==800


def test_r2_dmb_inverse_reconstruction_outputs(accepted):
    assert accepted[0]['inverse_passed']==800 and accepted[0]['inverse_failed']==0


def test_r2_dmb_no_payload_deletion_outputs(accepted):
    assert accepted[0]['payload_deletion_violations']==accepted[0]['invalid_utf8']==0


def test_r2_dmb_no_ds_generation_query(accepted):
    assert accepted[0]['generation_call_counts']['D_S']==0


def test_r2_dmb_no_dg_generation_query(accepted):
    assert accepted[0]['generation_call_counts']['D_G']==0


def test_r2_dmb_no_ensemble_generation_query(accepted):
    assert accepted[0]['generation_call_counts']['ensemble']==0


def test_r2_dmb_query_budget_outputs(accepted):
    assert accepted[0]['max_target_queries']<=61 and accepted[0]['query_budget_violations']==0


def test_r2_dmb_terminal_hashes_stable(accepted):
    receipt=p.files.read_json(p.OUT/'r2_dmb_freeze_acceptance_v1.json')
    for name,expected in receipt['sha256'].items():
        assert p.files.sha(p.OUT/name)==expected


def test_r2_dmb_regime_manifest_valid():
    from detection_service.research_protocol.regime_contract import FrozenRegimeContracts
    from detection_service.research_protocol.r2_dmb_transfer_run import manifest
    value=FrozenRegimeContracts().validate_manifest(manifest())
    assert value.sample_count==value.attack_count==800 and value.benign_count==0
    assert value.threat_regime=='R2_SINGLE_DETECTOR_TARGETED'
    assert all(s.target_detector=='D_M-B' and s.valid_attack_attempt for s in value.samples)


def test_r2_dmb_raw_text_not_committed(accepted):
    assert not p.git('ls-files','--','detection_service/outputs/r2-dmb-001').decode().strip()
    rows=p.files.read_json(p.OUT/'r2_dmb_terminal_manifest_v1.json')['terminals']
    assert all(not any(k in r for k in ('text','prompt','original','replacement','script')) for r in rows)


def test_r2_dmb_implementation_precedes_generation(accepted):
    stored=p.files.read_json(p.OUT/'r2_dmb_generator_manifest_v1.json')
    assert p.committed(p.ROOT/'detection_service/research_protocol/r2_dmb_generate_run.py')==stored['implementation_commit']
    assert p.git('merge-base','--is-ancestor',stored['predeclaration_commit'],stored['implementation_commit'])==b''
