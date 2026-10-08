"""Prospective reuse of the accepted patch; no protocol mutation."""

from detection_service.research_protocol import protocol_patch_001 as patch,r2_ds_predeclare as p
from detection_service.research_protocol.r2_ds_clarification import declaration


def verified():
    patch.verify_patch()
    declaration()
    p.preserved()
    return patch.patch_commit()


def prequery_receipt(implementation):
    commit=verified()
    restart_path=p.OUT/'r2_ds_restart_authorization_v1.json'
    p.committed(restart_path)
    restart=p.files.read_json(restart_path)
    failed=p.ROOT/restart['failed_invocation_directory']
    p.require(p.files.sha(failed/'interruption_v1.json')==restart['interruption_sha256'],'RESTART_INTERRUPTION_DRIFT')
    p.require(p.files.sha(failed/'generation_v1.jsonl')==restart['empty_journal_sha256'] and (failed/'generation_v1.jsonl').stat().st_size==0,'RESTART_JOURNAL_NOT_EMPTY')
    interrupted=p.files.read_json(failed/'interruption_v1.json')
    p.require(interrupted['completed_parents']==0 and not interrupted['accepted_terminal_manifest_exists'],'RESTART_OUTCOME_CONFLICT')
    p.require(not any((p.PRIVATE/name).exists() for name in ('invocation_v1.json','generation_v1.jsonl','prequery_receipt_v1.json')),'PRIOR_AUTHORITATIVE_INVOCATION_EXISTS')
    path=p.PRIVATE/'prequery_receipt_v1.json'
    p.publish(path,dict(receipt_version='r2_ds_prequery_receipt_v1',
        protocol_patch_id=patch.PATCH_ID,protocol_patch_commit=commit,
        protocol_patch_sha256=p.files.sha(p.ROOT/patch.ARTIFACT),
        original_predeclaration_commit=p.committed(p.OUT/'r2_ds_predeclaration_v1.json'),
        clarification_sha256=p.files.sha(p.OUT/'r2_ds_predeclaration_clarification_v1.json'),
        seed_manifest_sha256=p.files.sha(p.OUT/'r2_ds_seed_manifest_v1.json'),
        generator_implementation_commit=implementation,
        generator_implementation_sha256=p.files.sha(p.ROOT/'detection_service/research_protocol/r2_ds_generator.py'),
        orchestration_sha256=p.files.sha(p.ROOT/'detection_service/research_protocol/r2_ds_generate_run.py'),
        documented_restart_sha256=p.files.sha(restart_path),
        authoritative_prior_model_queries=0,scientific_outcomes_observed='NONE',target='D_S'))
    return dict(path=path.relative_to(p.ROOT).as_posix(),sha256=p.files.sha(path))
