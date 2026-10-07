"""Read-only R1 evaluation using the frozen official metrics/uncertainty path."""

import argparse

from detection_service.analysis.common_mode import fixed_fpr
from detection_service.analysis.development_characterization import characterization
from detection_service.research_protocol import r1_corpus as c, r1_scoring as scoring, protocol_lock, release_packaging
from detection_service.research_protocol.alignment import align_evaluation, bind_predictions
from detection_service.research_protocol.core_metrics import evaluate_core
from detection_service.research_protocol.cross_regime import RegimeResultBundle, compare_bundles
from detection_service.research_protocol.metric_catalog import metric_catalog
from detection_service.research_protocol.operating_policy import native_prediction
from detection_service.research_protocol.r0_operational import verified_policy
from detection_service.research_protocol.regime import create_manifest, require


def scoring_anchor():
    path=(c.OUT/'r1_prediction_manifest_v1.json').relative_to(c.ROOT).as_posix()
    commits=protocol_lock.git('log','--format=%H','--diff-filter=A','--',path).decode().splitlines()
    require(len(commits)==1,'COMMITTED_GATE_C_REQUIRED')
    commit=commits[0]
    require((c.ROOT/path).read_bytes()==protocol_lock.git('show',commit+':'+path),'SCORING_MANIFEST_DRIFT')
    metadata=c.files.read_json(c.ROOT/path)
    prediction_path=c.OUT/'r1_predictions_v1.csv'
    require(c.files.sha(prediction_path)==metadata['prediction_artifact_sha256'],'PREDICTION_ARTIFACT_DRIFT')
    require(prediction_path.read_bytes()==protocol_lock.git('show',commit+':'+prediction_path.relative_to(c.ROOT).as_posix()),'PREDICTIONS_NOT_COMMITTED')
    return commit


def r0_reference():
    require(c.files.sha(c.ROOT/release_packaging.INVENTORY)=='b04002287dfc22f5dc933f9270a5511de03b4f7877c90a72e93025ca0d75cf22','RELEASE_INVENTORY_DRIFT')
    inventory=c.files.read_json(c.ROOT/release_packaging.INVENTORY)
    entries=[r for r in inventory['records'] if r['logical_role']=='operational_R0_baseline']
    require(len(entries)==1,'R0_INVENTORY_REFERENCE_AMBIGUOUS')
    row=entries[0]
    require(c.files.sha(c.ROOT/row['artifact_path'])==row['sha256'],'R0_REFERENCE_DRIFT')
    return RegimeResultBundle.model_validate_json((c.ROOT/row['artifact_path']).read_bytes()),row


def aligned(manifest,records,policy):
    return align_evaluation(manifest,records,binding=bind_predictions(manifest),decision_view='OPERATIONAL',contracts=policy.contracts,operating_policy=policy)


def source_analysis(manifest,records,policy):
    results={}
    for source in sorted({s.source for s in manifest.samples if s.truth_label}):
        selected=[s for s in manifest.samples if s.source==source]
        payload=manifest.model_dump(mode='json')
        payload.update(samples=[s.model_dump(mode='json') for s in selected],sample_count=len(selected),attack_count=len(selected),benign_count=0)
        subgroup=create_manifest(**payload)
        ids={s.sample_id for s in selected}
        core=evaluate_core(aligned(subgroup,[r for r in records if r.sample_id in ids],policy))
        results[source]=dict(sample_count=len(selected),attack_family=selected[0].attack_family,
            support_status='LOW_SUPPORT_DESCRIPTIVE_ONLY' if len(selected)<20 else 'SOURCE_CONDITIONED_DESCRIPTIVE',
            lineage_count=len({s.lineage_id for s in selected}),uncertainty_status='ONE_CLUSTER_NOT_INDEPENDENT_SOURCE_INFERENCE' if len({s.lineage_id for s in selected})==1 else 'NO_ADDITIONAL_FAMILY_CI_REQUESTED',
            core_metrics=core.model_dump(mode='json'),derived_subpopulation_manifest_hash=subgroup.manifest_hash,
            parent_manifest_hash=manifest.manifest_hash)
    worst={}
    for i in range(3):
        source=max(results,key=lambda s:results[s]['core_metrics']['individual']['detectors'][i]['fnr']['value'])
        row=results[source]['core_metrics']['individual']['detectors'][i]
        worst['fnr/'+row['detector_id']]=dict(source=source,attack_family=results[source]['attack_family'],n=results[source]['sample_count'],value=row['fnr']['value'])
    for i in range(3):
        source=max(results,key=lambda s:results[s]['core_metrics']['common_mode']['pairs'][i]['jfn']['value'])
        pair=results[source]['core_metrics']['common_mode']['pairs'][i]
        worst['jfn/'+pair['left_detector']+'/'+pair['right_detector']]=dict(source=source,n=results[source]['sample_count'],value=pair['jfn']['value'])
    source=max(results,key=lambda s:results[s]['core_metrics']['common_mode']['all_three_jfn']['value'])
    worst['all_three/jfn']=dict(source=source,n=results[source]['sample_count'],value=results[source]['core_metrics']['common_mode']['all_three_jfn']['value'])
    return dict(view='OPERATIONAL_FIXED_V1',groups=results,worst_family_or_source=worst,
        limitation='Source and high-level family are one-to-one here; no detailed subtype inference; large InjecAgent dependency cluster; no new experiment or operating point')


def analyze():
    commit=scoring_anchor()
    scoring.gate_b_anchor()
    manifest=scoring.input_manifest()
    request=protocol_lock.ExperimentRequest(manifest=manifest,bootstrap_unit='LINEAGE_CLUSTERED')
    preflight=protocol_lock.verify_experiment_preflight(request)
    policy=verified_policy()
    records=scoring.read_predictions(policy)
    table=aligned(manifest,records,policy)
    bundle=protocol_lock.evaluate_official(request,tuple(native_prediction(r) for r in records))
    require(bundle.core_metrics==evaluate_core(table),'OFFICIAL_CORE_RECONSTRUCTION_CONFLICT')
    reference,reference_entry=r0_reference()
    comparison=compare_bundles(reference,bundle)
    require(comparison['status']=='OBSERVED' and not comparison['paired'],'CROSS_REGIME_COMPATIBILITY_FAILURE')
    reference_catalog,current_catalog=metric_catalog(reference.core_metrics),metric_catalog(bundle.core_metrics)
    for key,row in comparison['metrics'].items():
        row.update(reference=reference_catalog.get(key),current=current_catalog.get(key))
    comparison['reference_inventory_entry']=reference_entry
    comparison['limitation']='R0 statistical/semantic evidence is fold-local OOF; R1 uses frozen final models. Sources, attack mix, lengths, prevalence and model execution provenance differ; no causal or paired inference.'
    ranking={}
    frontier={}
    coverage={}
    sources={s.sample_id:s.source for s in manifest.samples}
    for detector in ('ds_v2','dm_b_v1','dg_v1'):
        values=[r for r in records if r.detector_id==detector]
        labels=[r.truth_label for r in values]
        scores=[r.raw_score for r in values]
        actual=characterization(labels,scores,[bool(r.native_binary_prediction) for r in values])
        ranking[detector]=dict(roc_auc=actual['roc_auc'],average_precision=actual['pr_auc'],definition=actual['pr_auc_definition'],score_basis='raw_score',sample_count=len(values))
        frontier[detector]=dict(view='descriptive_frontier_v1',score_basis='raw_score',points=[{**p,'role':'R1_SECONDARY_DESCRIPTIVE_ONLY_NOT_OPERATIONAL'} for p in fixed_fpr(labels,scores)])
        coverage[detector]=dict(truncated_rows=sum(r.truncated for r in values),max_input_tokens=max(r.input_tokens for r in values),
            by_source={s:dict(rows=sum(1 for r in values if sources[r.sample_id]==s),
                truncated=sum(r.truncated for r in values if sources[r.sample_id]==s)) for s in c.REVISIONS})
    core=bundle.core_metrics.model_dump(mode='json')
    outputs={
        'r1_result_bundle_v1':bundle.model_dump(mode='json'),
        'r1_operational_metrics_v1':core['individual'],
        'r1_common_mode_v1':core['common_mode'],
        'r1_failure_patterns_v1':dict(**core['failure_patterns'],recovery=core['recovery']),
        'r1_family_analysis_v1':source_analysis(manifest,records,policy),
        'r1_uncertainty_v1':dict(artifact_version='r1_uncertainty_v1',unit='LINEAGE_CLUSTERED',frozen_pre_score=True,
            intervals=[u.model_dump(mode='json') for u in bundle.uncertainty],
            caution='97 attack clusters, including one 400-row InjecAgent cluster; pooled cluster-bootstrap source mix varies strongly. OR has 1000 assumed singleton fallback units; no proof of generator independence.'),
        'r1_ranking_metrics_v1':dict(artifact_version='r1_ranking_metrics_v1',detectors=ranking,definition_source='Frozen Phase-13 development_characterization.characterization; whole tied blocks; no operational decision changes'),
        'r1_descriptive_frontier_v1':dict(artifact_version='r1_descriptive_frontier_v1',detectors=frontier,operational_policy_changed=False),
        'r0_r1_comparison_v1':comparison,
        'r1_token_coverage_v1':dict(artifact_version='r1_token_coverage_v1',detectors=coverage),
    }
    for name,value in outputs.items():
        c.publish(c.OUT/(name+'.json'),value)
    inventory=dict(artifact_version='r1_analysis_provenance_v1',status='PASS',scoring_commit=commit,gate_b_commit=scoring.gate_b_anchor(),
        preflight=preflight,protocol_release_id='exp_protocol_001_v1',
        sha256={p.relative_to(c.ROOT).as_posix():c.files.sha(p) for p in c.OUT.glob('*.json') if p.name not in ('r1_analysis_provenance_v1.json',)},
        predictions_sha256=c.files.sha(c.OUT/'r1_predictions_v1.csv'),
        contracts={r['logical_role']:dict(path=r['artifact_path'],sha256=r['sha256']) for r in c.files.read_json(c.ROOT/release_packaging.INVENTORY)['records'] if r['logical_role'] in
            ('protocol_lock','operating_policy','core_metrics','uncertainty_contract','cross_regime_contract','detector_contract','prediction_contract','regime_contract')},
        model_training=False,post_R1_adaptation=False,R2_started=False,R3_started=False,Cycle2='DEFERRED')
    c.publish(c.OUT/'r1_analysis_provenance_v1.json',inventory)
    print(c.files.manifest_bytes(dict(status='GATE_D_METRICS_COMPLETE',operational=core['individual']['detectors'],
        common=core['common_mode'],ranking=ranking,failure_patterns=core['failure_patterns']['patterns'],recovery=core['recovery']['detectors'])).decode(),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--analyze',action='store_true',required=True)
    parser.parse_args()
    analyze()
