"""Domain-only prospective correction with unchanged historical evidence."""

from types import SimpleNamespace
import pytest

from detection_service.research_protocol import protocol_patch_001 as patch
from detection_service.research_protocol import r2_dmb_predeclare as p, r2_dmb_design as d
from detection_service.research_protocol.adapters import FrozenDetectorContracts
from detection_service.research_protocol.core_metrics_contract import synthetic_r2, align_fixture
from detection_service.research_protocol.core_metrics import evaluate_core
from detection_service.research_protocol.metric_catalog import metric_catalog
from detection_service.research_protocol.uncertainty import BootstrapConfig, validate_metric_domain


def manifest(target="D_M-B", regime="R2_SINGLE_DETECTOR_TARGETED"):
    return SimpleNamespace(threat_regime=regime, samples=(SimpleNamespace(target_detector=target),))


@pytest.mark.parametrize("target",patch.PRIMARY, ids=("ds","dmb","dg"))
def test_r2_single_target_domain(target):
    domains = patch.validate_domains(manifest(target))
    assert domains.attack_target_domain == (target,)
    assert domains.attack_target_uncertainty_domain == (target,)
    assert domains.transfer_evaluation_domain == patch.PRIMARY
    assert domains.common_mode_domain == patch.PRIMARY


@pytest.mark.parametrize("field",("attack_target_domain","attack_target_uncertainty_domain"))
@pytest.mark.parametrize("extra",("D_S","D_G"))
def test_r2_rejects_extra_attack_targets(field,extra):
    value = patch.validate_domains(manifest()).model_dump()
    value[field] = ("D_M-B",extra)
    with pytest.raises(ValueError,match="DOMAIN_CONFLICT"):
        patch.validate_domains(manifest(),value)


def test_r2_transfer_detectors_not_attack_targets():
    value = patch.validate_domains(manifest())
    assert set(value.transfer_evaluation_domain)-set(value.attack_target_domain) == {"D_S","D_G"}


def test_r3_all_target_domain_still_valid():
    value = patch.validate_domains(manifest("ALL","R3_ENSEMBLE_TARGETED"))
    assert value.attack_target_domain == value.attack_target_uncertainty_domain == patch.PRIMARY


def test_mixed_r2_targets_rejected():
    value = manifest()
    value.samples += (SimpleNamespace(target_detector="D_S"),)
    with pytest.raises(ValueError,match="SINGLE_DECLARED"):
        patch.validate_domains(value)


@pytest.fixture(scope="module")
def table():
    contracts = FrozenDetectorContracts()
    return align_fixture(synthetic_r2(contracts)[0],contracts)


def test_target_metric_domain_conflict_reproduced_pre_patch(table):
    names = tuple(k for k in metric_catalog(evaluate_core(table)) if k.startswith(("target/","transfer/")))
    with pytest.raises(ValueError,match="TARGET_METRIC_DOMAIN_CONFLICT"):
        validate_metric_domain(names,BootstrapConfig(unit="LINEAGE_CLUSTERED",domain="VALID_TARGET_ATTEMPTS",target_detector="D_M-B"),table)


@pytest.mark.parametrize("target",patch.PRIMARY)
def test_target_metric_domain_conflict_resolved_post_patch(table,target):
    names = patch.target_metric_names(metric_catalog(evaluate_core(table)),target,table.provenance.primary_detector_ids)
    assert names
    validate_metric_domain(names,BootstrapConfig(unit="LINEAGE_CLUSTERED",domain="VALID_TARGET_ATTEMPTS",target_detector=target),table)
    assert all(k.split('/')[1] == table.provenance.primary_detector_ids[patch.PRIMARY.index(target)] for k in names)


@pytest.mark.parametrize("filename,sha",(
    ("r2_dmb_predeclaration_v1.json","6b87558fc2db14ad6d1ff73a707529726d8d466ac64893e05b28e125ce8e7c32"),
    ("r2_dmb_seed_manifest_v1.json","499cdcecace3b3b4725afca78aad7ee2bcca9436e297019b80cb947cd128dd56")))
def test_original_r2_artifacts_unchanged(filename,sha):
    assert p.files.sha(p.OUT/filename) == sha


def test_design_and_all_frozen_scientific_artifacts_unchanged():
    assert p.files.read_json(p.OUT/'r2_dmb_predeclaration_v1.json')['design'] == d.DESIGN
    assert p.preserved() == 252


def test_versioned_patch_hashes():
    assert patch.verify_patch(require_committed=False)['authoritative_R2_queries_before_correction'] == 0


def test_corrected_official_orchestrator_selects_only_declared_target(monkeypatch,table):
    from detection_service.research_protocol.release_validation import fixture_request
    request = fixture_request('r2_dmb').model_copy(update={'purpose':'OFFICIAL_EVALUATION'})
    calls = []
    monkeypatch.setattr(patch,'verify_experiment_preflight',lambda r: None)
    monkeypatch.setattr(patch.parent,'align_evaluation',lambda *a,**k: table)
    def bootstrap(aligned,names,config):
        validate_metric_domain(names,config,aligned)
        calls.append((names,config))
        return None
    monkeypatch.setattr(patch.parent,'bootstrap_metrics',bootstrap)
    monkeypatch.setattr(patch.parent,'result_bundle',lambda *a,**k: k)
    patch.evaluate_official(request,())
    target = [c for c in calls if c[1].domain == 'VALID_TARGET_ATTEMPTS']
    assert len(target) == 1 and target[0][1].target_detector == 'D_M-B'
    assert all(k.split('/')[1] == 'dm_b_v1' for k in target[0][0])
    assert any(k.startswith('all_three/') for k in calls[0][0])


@pytest.mark.parametrize('scope,prefix',(
    ('r0_results','artifacts/research_protocol/r0'),
    ('r1_results','artifacts/research_protocol/r1/'),
    ('detector_hashes','artifacts/models/'),
    ('thresholds','artifacts/research_protocol/operating_point'),
    ('calibrators','detection_service/configs/'),
    ('metric_formulas','detection_service/research_protocol/core_metrics'),
    ('bootstrap_contract','detection_service/research_protocol/uncertainty')))
def test_frozen_scientific_scope_unchanged(scope,prefix):
    snapshot = p.files.read_json(p.OUT/'r2_dmb_predeclaration_v1.json')['preservation_sha256']
    selected = {path:sha for path,sha in snapshot.items() if path.startswith(prefix)}
    assert selected, scope
    assert all(p.digest(path) == sha for path,sha in selected.items())


@pytest.mark.parametrize('tamper',(False,True))
def test_patch_git_anchor_and_historical_local_hash_authority(monkeypatch,tamper):
    seen=[]
    def git(*args):
        if args[0]=='log':
            return (('f'*40)+'\n').encode('ascii')
        assert args[0]=='show'
        path=args[1].split(':',1)[1]
        seen.append(path)
        data=(p.ROOT/path).read_bytes()
        return data+b' ' if tamper and path.endswith('protocol_patch_001.py') else data
    monkeypatch.setattr(patch.parent,'git',git)
    if tamper:
        with pytest.raises(ValueError,match='COMMITTED_PATCH_BYTES_REQUIRED'):
            patch.verify_patch()
    else:
        value=patch.verify_patch()
        assert set(seen)==set(value['patch_code_paths'])|{patch.ARTIFACT}
        assert 'artifacts/models/dg_v1/environment.json' not in seen
