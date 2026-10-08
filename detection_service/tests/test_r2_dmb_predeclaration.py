from detection_service.research_protocol import r2_dmb_design as d, r2_dmb_predeclare as p


def test_r2_dmb_predeclaration_valid():
    value=p.files.read_json(p.OUT/'r2_dmb_predeclaration_v1.json')
    assert value['design']==d.DESIGN and value['status']=='FROZEN_PRE_RUN'
    assert value['model_queries_before_predeclaration']==0
    assert not value['generation_implementation_exists']


def test_r2_dmb_seed_population_exact():
    assert len(p.parents())==800
    assert len({r['parent_sample_id'] for r in p.parents()})==800
    value=p.files.read_json(p.OUT/'r2_dmb_seed_manifest_v1.json')
    assert value['source_counts']=={'LLMAIL_INJECT':400,'INJECAGENT_BASE':400}
    assert value['lineage_count']==97


def test_r2_dmb_all_seeds_attack_positive():
    assert all(r['truth_label']==1 for r in p.parents())


def test_r2_dmb_all_seeds_dmb_detected():
    assert all(r['baseline_operational_decision']==1 and r['baseline_raw_score']>=d.THRESHOLD for r in p.parents())


def test_r2_dmb_target_detector_only():
    assert all(r['target_detector']=='D_M-B' for r in p.parents())
    assert d.DESIGN['untargeted_generation_access']=='PROHIBITED'


def test_r2_dmb_target_threshold_exact():
    assert d.THRESHOLD==0.0004967087297700347 and d.THRESHOLD_ID=='dm_b_v1_op3_raw_v1'
    assert all(r['threshold']==d.THRESHOLD and r['threshold_id']==d.THRESHOLD_ID for r in p.parents())


def test_r2_dmb_target_score_semantics_raw():
    assert d.DESIGN['target_score']=='raw_score'


def test_r2_dmb_operator_registry_exact():
    assert d.OPERATORS==('ALT_CASE','CONFUSABLE_FIRST','ZERO_WIDTH_INTERLEAVE','DOT_INTERLEAVE')
    assert d.DESIGN['max_unique_model_queries_per_parent']==1+16+32+8+4==61
    assert len(d.PREFIXES)==len(d.SUFFIXES)==4 and len(d.CONFUSABLES)==18


def test_r2_dmb_parent_hashes():
    assert len(p.private_parents())==800


def test_r2_dmb_lineage_inheritance():
    originals={r['sample_id']:r for r in p.files.read_json(p.R1/'r1_dataset_manifest_v1.json')['samples']}
    assert all(r['lineage_id']==originals[r['parent_sample_id']]['lineage_id'] for r in p.parents())


def test_protocol_release_hashes_unchanged():
    from detection_service.research_protocol.release_validation import check_acceptance
    assert check_acceptance()['hash_checks']==118


def test_r0_preservation():
    assert p.preserved()>118


def test_r1_preservation():
    assert p.preserved()>118
