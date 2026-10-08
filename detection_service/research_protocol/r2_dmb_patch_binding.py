"""Prospective binding and pre-query receipt; no attack-design changes."""

from detection_service.research_protocol import protocol_patch_001 as patch
from detection_service.research_protocol import r2_dmb_predeclare as p

ADDENDUM = p.OUT / 'r2_dmb_predeclaration_addendum_v1.json'
ACCEPTANCE = p.ROOT / 'artifacts/research_protocol/protocol_patches/exp_protocol_001_patch_001_acceptance_v3.json'


def bind():
    patch.verify_patch()
    acceptance = p.files.read_json(ACCEPTANCE)
    p.require(acceptance['status'] == 'PASS', 'PATCH_ACCEPTANCE_REQUIRED')
    p.require(acceptance['tests']['failed'] == acceptance['tests']['skipped'] == acceptance['tests']['errors'] == 0, 'PATCH_REGRESSION_NOT_PASS')
    patch_commit = patch.patch_commit()
    p.publish(ADDENDUM,dict(artifact_version='r2_dmb_predeclaration_addendum_v1',
        protocol_patch_id=patch.PATCH_ID, protocol_patch_commit=patch_commit,
        protocol_patch_sha256=p.files.sha(p.ROOT / patch.ARTIFACT),
        acceptance_sha256=p.files.sha(ACCEPTANCE),
        original_predeclaration_commit=p.committed(p.OUT/'r2_dmb_predeclaration_v1.json'),
        original_predeclaration_sha256=p.files.sha(p.OUT/'r2_dmb_predeclaration_v1.json'),
        seed_manifest_sha256=p.files.sha(p.OUT/'r2_dmb_seed_manifest_v1.json'),
        original_predeclaration_unchanged=True,attack_target='D_M-B',seed_population_unchanged=True,
        operators_unchanged=True,query_budget_unchanged=True,success_condition_unchanged=True,
        random_seed_unchanged=True,target_isolation_unchanged=True,
        only_change='Prospective protocol-version binding from exp_protocol_001_v1 to exp_protocol_001_patch_001',
        authoritative_prior_model_queries=0,scientific_outcomes_observed='NONE'))


def verified():
    patch.verify_patch()
    value=p.files.read_json(ADDENDUM)
    p.committed(ADDENDUM)
    p.require(value['protocol_patch_id']==patch.PATCH_ID,'PATCH_BINDING_CONFLICT')
    p.require(value['protocol_patch_commit']==patch.patch_commit(),'PATCH_COMMIT_CONFLICT')
    p.require(value['protocol_patch_sha256']==p.files.sha(p.ROOT/patch.ARTIFACT),'PATCH_BINDING_DRIFT')
    p.require(value['acceptance_sha256']==p.files.sha(ACCEPTANCE),'PATCH_ACCEPTANCE_DRIFT')
    p.committed(ACCEPTANCE)
    for filename,key in (('r2_dmb_predeclaration_v1.json','original_predeclaration_sha256'),
                         ('r2_dmb_seed_manifest_v1.json','seed_manifest_sha256')):
        p.require(p.files.sha(p.OUT/filename)==value[key],'ORIGINAL_R2_ARTIFACT_DRIFT')
    p.preserved()
    return value


def prequery_receipt(implementation):
    value=verified()
    p.require(not any((p.PRIVATE/name).exists() for name in ('invocation_v1.json','generation_v1.jsonl','prequery_receipt_v1.json')),
              'PRIOR_AUTHORITATIVE_INVOCATION_EXISTS')
    path=p.PRIVATE/'prequery_receipt_v1.json'
    p.publish(path,dict(receipt_version='r2_dmb_prequery_receipt_v1',
        protocol_patch_id=patch.PATCH_ID,protocol_patch_commit=value['protocol_patch_commit'],
        original_predeclaration_commit=value['original_predeclaration_commit'],
        predeclaration_addendum_sha256=p.files.sha(ADDENDUM),seed_manifest_sha256=value['seed_manifest_sha256'],
        generator_implementation_commit=implementation,
        generator_implementation_sha256=p.files.sha(p.ROOT/'detection_service/research_protocol/r2_dmb_generator.py'),
        orchestration_sha256=p.files.sha(p.ROOT/'detection_service/research_protocol/r2_dmb_generate_run.py'),
        authoritative_prior_model_queries=0,scientific_outcomes_observed='NONE',
        target_isolation_unchanged=True,attack_design_unchanged=True))
    return dict(path=path.relative_to(p.ROOT).as_posix(),sha256=p.files.sha(path))


if __name__=='__main__':
    bind()
