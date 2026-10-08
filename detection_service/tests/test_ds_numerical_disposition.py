"""Scientific disposition and immutable research-contract checks."""

from detection_service.research_protocol import ds_numerical_disposition as d


def disposition():
    return d.p.files.read_json(d.PATH)


def test_ds_disposition_preserves_historical_anomaly():
    v=disposition()
    assert v['observed_historical_anomaly'] and v['historical_raw_delta']>1e-12 and v['historical_calibrated_delta']>1e-12
    assert v['accepted_anomalous_terminals']==v['accepted_anomalous_scientific_outcomes']==0
    assert not v['anomalous_untargeted_feedback']
    assert v['historical_blocker_sha256']==d.p.files.sha(d.p.OUT/'r2_ds_blocker_v1.json')


def test_ds_disposition_does_not_claim_cause():
    v=disposition()
    assert v['causal_origin']=='UNRESOLVED' and v['proven_cause']=='NONE'
    assert v['OMP_MKL_difference']=='DOCUMENTED_LEAD_ONLY'
    assert v['classification']=='NON_REPRODUCIBLE_EXECUTION_CONTEXT_NUMERICAL_ANOMALY'


def test_ds_disposition_current_equivalence_passes():
    v=disposition()['current_evidence']
    assert v['equivalence_records']==243 and v['same_process_repetitions']==100 and v['cross_process_repetitions']==10
    assert v['diagnostic_r1_baselines']==9 and v['affected_seed_exact']
    assert v['native_mismatches']==v['operational_mismatches']==0
    assert all(v['equivalence_summary'][s]['above_tolerance']==0 for s in ('raw','calibrated'))


def test_disposition_gate_durable_and_replayed():
    v=disposition()['gate']
    assert v['status']=='OK' and v['raw_delta']<=1e-12 and v['calibrated_delta']<=1e-12
    assert v['native_match'] and v['operational_match'] and v['diagnostic_queries']==1
    assert d.p.digest(v['journal']['path'])==v['journal']['sha256']
    assert d.p.digest(v['journal']['logical_path'])==v['journal']['logical_sha256']


def test_r2_ds_seed_manifest_unchanged():
    assert d.identities()['seed_manifest_sha256']==disposition()['bindings']['seed_manifest_sha256']


def test_r2_ds_generator_contract_unchanged():
    assert d.identities()['generator_contract_sha256']==disposition()['bindings']['generator_contract_sha256']


def test_r2_ds_query_budget_unchanged():
    assert d.design.DESIGN['max_unique_model_queries_per_parent']==disposition()['bindings']['max_queries_per_seed']==61


def test_r2_ds_threshold_unchanged():
    assert d.design.THRESHOLD==disposition()['bindings']['threshold']==.5585373573968287


def test_r2_ds_replay_tolerance_unchanged():
    assert d.design.DESIGN['score_replay_tolerance']==disposition()['bindings']['replay_tolerance']==1e-12


def test_track_b_untouched():
    assert d.p.git('rev-parse','prep/r3-verifier-001').decode().strip()==d.numerical.TRACK_B


def test_r0_preservation():
    assert d.p.preserved()==503


def test_r1_preservation():
    assert d.p.preserved()==503


def test_r2_dmb_preservation():
    assert d.p.preserved()==503


def test_protocol_patch_preservation():
    from detection_service.research_protocol import protocol_patch_001
    assert len(protocol_patch_001.verify_patch()['sha256'])==262
