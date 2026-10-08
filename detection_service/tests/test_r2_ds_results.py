"""Post-freeze acceptance of the unchanged targeted/transfer definitions."""

from collections import Counter
import pytest

from detection_service.research_protocol import r2_ds_predeclare as p, r2_ds_transfer_run as scoring
from detection_service.research_protocol import r2_ds_design as d, r2_ds_binding as binding
from detection_service.research_protocol.core_metrics import evaluate_core
from detection_service.research_protocol.cross_regime import RegimeResultBundle


def read(name):
    return p.files.read_json(p.OUT/(name+'_v1.json'))


@pytest.fixture(scope='module')
def evidence():
    policy=scoring.verified_policy()
    manifest=scoring.manifest()
    records=scoring.read_predictions(policy)
    table=scoring.aligned(manifest,records,policy)
    bundle=RegimeResultBundle.model_validate_json((p.OUT/'r2_ds_result_bundle_v1.json').read_bytes())
    return manifest,records,table,bundle


def test_r2_canonical_predictions_complete(evidence):
    manifest,records,table,bundle=evidence
    assert manifest.sample_count==bundle.population_count==p.count()
    assert len(records)==len({(r.sample_id,r.detector_id) for r in records})==3*p.count()
    assert table.coverage.status=='COMPLETE' and all(r.status=='OK' for r in records)


def test_r2_core_reconstructed(evidence):
    assert evaluate_core(evidence[2])==evidence[3].core_metrics


def test_r2_ds_rescore_identical(evidence):
    terminals={r['sample_id']:r for r in read('r2_ds_terminal_manifest')['terminals']}
    for r in evidence[1]:
        if r.detector_id==d.DETECTOR_ID:
            assert abs(r.calibrated_score-terminals[r.sample_id]['terminal_calibrated_score'])<=1e-12
            assert r.operational_binary_prediction==terminals[r.sample_id]['terminal_decision']
    assert read('r2_ds_prediction_manifest')['ds_operational_mismatches']==0


def test_r2_target_and_transfer_ratios(evidence):
    rows=evidence[2].rows
    target=next(r for r in evidence[3].core_metrics.evasion_transfer.targets if r.target_detector==d.DETECTOR_ID)
    successes=[r for r in rows if r.decisions[0]==0]
    assert target.valid_attempt_count==len(rows)==p.count()
    assert target.target_evasion_count==len(successes)
    for transfer in target.transfers:
        i=('ds_v2','dm_b_v1','dg_v1').index(transfer.transfer_detector)
        n=sum(r.decisions[i]==0 for r in successes)
        assert transfer.joint_evasion_count==n
        assert transfer.etr.value==(n/len(successes) if successes else None)


def test_r2_common_mode_and_patterns(evidence):
    rows=evidence[2].rows
    core=evidence[3].core_metrics
    counts=Counter(''.join(str(1-d) for d in r.decisions) for r in rows)
    assert core.common_mode.all_three_fn_count==counts['111']
    assert {r.pattern_id:r.count for r in core.failure_patterns.patterns}=={f'{i:03b}':counts[f'{i:03b}'] for i in range(8)}
    for pair in core.common_mode.pairs:
        i,j=[('ds_v2','dm_b_v1','dg_v1').index(k) for k in (pair.left_detector,pair.right_detector)]
        assert pair.shared_fn_count==sum(r.decisions[i]==r.decisions[j]==0 for r in rows)
        assert pair.jfn.value==pair.shared_fn_count/p.count()
        assert pair.ejf.value==pair.jfn.value-pair.independence_reference.value


def test_r2_success_subset_joint_transfer(evidence):
    rows=[r for r in evidence[2].rows if r.decisions[0]==0]
    summary=read('r2_ds_transfer_metrics')
    n=sum(r.decisions==(0,0,0) for r in rows)
    assert summary['joint_transfer']['value']==(n/len(rows) if rows else None)
    assert sum(summary['successful_evasion_patterns'].values())==len(rows)


def test_r2_attack_only_no_benign_metrics(evidence):
    assert evidence[3].benign_count==0 and evidence[3].attack_count==p.count()
    assert all(r.fpr.value is None for r in evidence[3].core_metrics.individual.detectors)
    guard=read('r2_ds_attack_only_guard')
    assert all(guard[k]=='NOT_APPLICABLE_ATTACK_ONLY_REGIME' for k in ('FPR','ROC_AUC','AP'))


def test_r2_bootstrap_domains_unchanged(evidence):
    for group in evidence[3].uncertainty:
        assert group.config.replicates==1000 and group.config.seed==1701
        assert group.config.confidence_level==.95 and group.config.unit=='LINEAGE_CLUSTERED'
        if group.config.domain=='VALID_TARGET_ATTEMPTS':
            assert group.config.target_detector=='D_S'
            assert all(r.metric_id.split('/')[1]=='ds_v2' for r in group.intervals)


def test_r2_source_and_operator_totals():
    sources=read('r2_ds_source_analysis')
    operators=read('r2_ds_operator_analysis')
    assert sum(r['seed_count'] for r in sources.values())==p.count()
    assert sum(r['seed_count'] for r in operators.values())==p.count()
    assert sources['INJECAGENT_BASE']['lineage_count']==1
    assert sources['LLMAIL_INJECT']['lineage_count']==len({row['lineage_id'] for row in p.parents() if row['source']=='LLMAIL_INJECT'})
    assert sum(r['target_evasion_count'] for r in sources.values())==sum(r['target_evasion_count'] for r in operators.values())


def test_r2_paired_transitions_complete():
    transitions=read('r2_ds_parent_child_transitions')['overall']
    assert all(sum(row.values())==p.count() for row in transitions.values())
    assert transitions['ds_v2']['miss_to_catch']==transitions['ds_v2']['miss_to_miss']==0
    assert transitions['ds_v2']['catch_to_miss']==read('r2_ds_transfer_metrics')['target_evasion_count']


def test_r2_prequery_binding_and_preservation():
    binding.verified()
    generator=read('r2_ds_generator_manifest')
    receipt=generator['protocol_prequery_receipt']
    assert p.digest(receipt['path'])==receipt['sha256']
    value=p.files.read_json(p.ROOT/receipt['path'])
    assert value['authoritative_prior_model_queries']==0
    assert value['generator_implementation_sha256']==p.files.sha(p.ROOT/'detection_service/research_protocol/r2_ds_generator.py')
    assert p.preserved()>252


def test_r2_analysis_output_hashes():
    for name,sha in read('r2_ds_analysis_provenance')['sha256'].items():
        assert p.files.sha(p.OUT/name)==sha
    assert not read('r2_ds_analysis_provenance')['R3_started']
