"""Offline checks of the target-only committed-before-query design."""

from detection_service.research_protocol import r2_ds_design as d, r2_ds_predeclare as p


def test_seed_projection_and_counts():
    seed=p.files.read_json(p.OUT/'r2_ds_seed_manifest_v1.json')
    rows=seed['parents']
    assert len(rows)==seed['actual_parents']==seed['expected_parents']
    assert sum(seed['source_counts'].values())==len(rows)
    assert len({r['parent_sample_id'] for r in rows})==len(rows)
    assert all(r['truth_label']==1 and r['baseline_operational_decision']==1 for r in rows)
    assert all(r['baseline_calibrated_score']>=d.THRESHOLD for r in rows)
    assert all('baseline_raw_score' not in r and r['target_detector']=='D_S' for r in rows)


def test_frozen_objective_and_reversible_probes():
    frozen=p.files.read_json(p.OUT/'r2_ds_predeclaration_v1.json')
    clarification=p.files.read_json(p.OUT/'r2_ds_predeclaration_clarification_v1.json')
    assert clarification['design']==d.DESIGN
    assert clarification['authoritative_prior_model_queries']==0
    assert frozen['model_queries_before_predeclaration']==0
    assert d.DESIGN['target_score']=='calibrated_score'
    assert 'ALT_CASE' in d.DESIGN['saliency_probe']
    assert d.DESIGN['generation_query_counts']==dict(D_M_B=0,D_G=0,ensemble=0)
    assert frozen['seed_manifest_sha256']==p.files.sha(p.OUT/'r2_ds_seed_manifest_v1.json')


def test_accepted_stack_preserved():
    assert p.preserved()>250
