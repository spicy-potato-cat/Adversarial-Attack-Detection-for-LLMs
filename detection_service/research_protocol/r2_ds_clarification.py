"""Prospective clarification of generic tie descriptions, before any queries."""

from detection_service.research_protocol import r2_ds_predeclare as p,r2_ds_design as d


def declaration():
    path=p.OUT/'r2_ds_predeclaration_clarification_v1.json'
    value=p.files.read_json(path)
    p.committed(path)
    p.require(value['design']==d.DESIGN,'DESIGN_DRIFT')
    p.require(value['original_predeclaration_sha256']==p.files.sha(p.OUT/'r2_ds_predeclaration_v1.json'),'PREDECLARATION_DRIFT')
    p.require(value['authoritative_prior_model_queries']==0,'PRIOR_QUERY_CONFLICT')
    return value


if __name__=='__main__':
    p.require(not p.PRIVATE.exists(),'PRIOR_INVOCATION_EXISTS')
    p.publish(p.OUT/'r2_ds_predeclaration_clarification_v1.json',dict(
        artifact_version='r2_ds_predeclaration_clarification_v1',design=d.DESIGN,
        original_predeclaration_sha256=p.files.sha(p.OUT/'r2_ds_predeclaration_v1.json'),
        original_predeclaration_commit=p.committed(p.OUT/'r2_ds_predeclaration_v1.json'),
        authoritative_prior_model_queries=0,operators_unchanged=True,query_budget_unchanged=True,
        objective_unchanged=True,protocol_patch_unchanged=True,
        correction='Inherited generic tie descriptions now explicitly say calibrated score, consistent with the original DS objective.'))
