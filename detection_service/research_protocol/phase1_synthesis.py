"""Model-free Phase 1 synthesis. Reads an explicit pre-R3 Git-object allowlist."""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
import subprocess
from typing import Literal
from pydantic import BaseModel, ConfigDict, model_validator
from detection_service.research_protocol.cross_regime import RegimeResultBundle
from detection_service.research_protocol.metric_catalog import metric_catalog

BASELINE_SHA = '71e3a5239cb24a3e59e99d271c6aa46841dbc084'
OLD_TRACK_B_SHA = '6c7173b70a10d1506d92360b421eaceb5e56405e'
IDS = ('ds_v2', 'dm_b_v1', 'dg_v1')
NOT_OBSERVED = 'NOT_YET_OBSERVED'
ROOT = Path(__file__).resolve().parents[2]
BUNDLES = {
    'R0': 'r0/r0_operational_result_bundle_v1.json',
    'R1': 'r1/r1_result_bundle_v1.json',
    'R2-DMB': 'r2_dmb/r2_dmb_result_bundle_v1.json',
    'R2-D_S': 'r2_ds/r2_ds_result_bundle_v1.json',
}
SUPPLEMENTS = {
    'R0': {'ranking': 'r0/r0_score_metrics_reproduction_v1.json'},
    'R1': {'ranking': 'r1/r1_ranking_metrics_v1.json', 'family': 'r1/r1_family_analysis_v1.json'},
    'R2-DMB': {'source': 'r2_dmb/r2_dmb_source_analysis_v1.json', 'transitions': 'r2_dmb/r2_dmb_parent_child_transitions_v1.json'},
    'R2-D_S': {'source': 'r2_ds/r2_ds_source_analysis_v1.json', 'transitions': 'r2_ds/r2_ds_parent_child_transitions_v1.json'},
}
ALLOWED = frozenset('artifacts/research_protocol/' + p for p in
    list(BUNDLES.values()) + [p for group in SUPPLEMENTS.values() for p in group.values()])
R3_ROLES = ('result_bundle', 'prediction_manifest', 'common_mode', 'failure_patterns',
            'uncertainty', 'all_three_failure_manifest')

def require(condition, code):
    if not condition:
        raise ValueError(code)

def bytes_json(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()

def sha256(data):
    return hashlib.sha256(data).hexdigest()

class CommittedR3Reader:
    """Explicit Phase 2 interface; verifies Git commit existence before any read."""
    def __init__(self,root,*,phase2_authorized=False):
        require(phase2_authorized is True,'PHASE2_R3_READ_AUTHORIZATION_REQUIRED')
        self.root=Path(root)
    def __call__(self,commit,path):
        import re
        require(bool(re.fullmatch('[0-9a-f]{40}',commit)),'COMMITTED_SHA_REQUIRED')
        require(path.startswith('artifacts/research_protocol/r3/') and '..' not in path.split('/') and
                '\\' not in path,'R3_INPUT_PATH_INVALID')
        subprocess.check_call(['git','cat-file','-e',commit+'^{commit}'],cwd=self.root,
                              stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        return subprocess.check_output(['git','show',commit+':'+path],cwd=self.root)

def git_bytes(path, *, root=ROOT, commit=BASELINE_SHA):
    require(commit == BASELINE_SHA and path in ALLOWED, 'PHASE1_READ_OUTSIDE_FROZEN_ALLOWLIST')
    return subprocess.check_output(['git', 'show', f'{commit}:{path}'], cwd=root)

def read_frozen(relative, reads, *, root=ROOT):
    path = 'artifacts/research_protocol/' + relative
    data = git_bytes(path, root=root)
    reads.append(dict(path=path, commit=BASELINE_SHA, sha256=sha256(data)))
    return json.loads(data)

def cell(value, status=None):
    return {'status': status or ('OBSERVED' if value is not None else 'UNDEFINED'), 'value': value}

def metric(value):
    return cell(value['value'], 'OBSERVED' if value['status'] == 'DEFINED' else 'UNDEFINED')

def assert_value(actual, expected, name):
    require((actual is None and expected is None) or
            (actual is not None and expected is not None and math.isclose(actual, expected, abs_tol=1e-12)),
            'FROZEN_FORMULA_CONFLICT_' + name)

def ratio(a, b):
    return a / b if b else None

def validate_frozen_bundle(raw):
    # The historical uncertainty hash includes the generating NumPy version.
    # Validate core relations with the existing model; validate stored intervals
    # against its catalog without rebuilding a runtime-dependent contract hash.
    core_only=copy.deepcopy(raw)
    core_only['uncertainty']=[]; core_only['uncertainty_contract_hash']=None
    bundle=RegimeResultBundle.model_validate_json(json.dumps(core_only))
    catalog=metric_catalog(bundle.core_metrics)
    seen=set()
    for u in raw['uncertainty']:
        require(u['uncertainty_contract_sha']==raw['uncertainty_contract_hash'] and
                u['alignment_sha']==bundle.core_metrics.individual.alignment_sha and
                u['operating_policy_sha']==raw['operating_point_manifest_hash'] and
                u['regime_manifest_sha']==raw['regime_manifest_hash'] and
                u['detector_manifest_sha']==raw['detector_manifest_hash'] and
                u['prediction_schema_sha']==raw['prediction_schema_hash'] and
                u['core_metrics_contract_sha']==raw['core_metrics_contract_hash'], 'FROZEN_INTERVAL_PROVENANCE_CONFLICT')
        require(u['config']['confidence_level']==.95, 'FROZEN_CI_LEVEL_CONFLICT')
        for item in u['intervals']:
            name=item['metric_id']
            require(name in catalog and name not in seen,'FROZEN_INTERVAL_METRIC_CONFLICT')
            assert_value(item['point_estimate'],catalog[name],'INTERVAL_POINT')
            seen.add(name)
    return bundle

class MetricCell(BaseModel):
    model_config = ConfigDict(extra='forbid')
    status: Literal['OBSERVED', 'UNDEFINED', 'NOT_APPLICABLE', 'NOT_YET_OBSERVED']
    value: float | None
    @model_validator(mode='after')
    def valid(self):
        require((self.value is not None) == (self.status == 'OBSERVED'), 'CELL_STATUS_VALUE_CONFLICT')
        return self

class DetectorRecord(BaseModel):
    model_config = ConfigDict(extra='forbid')
    detector_id: str
    threshold_id: str
    threshold: float
    tp: int | None
    fn: int | None
    tn: int | None
    fp: int | None
    recall: MetricCell
    fnr: MetricCell
    fpr: MetricCell
    roc_auc: MetricCell
    ap: MetricCell

class PairRecord(BaseModel):
    model_config = ConfigDict(extra='forbid')
    left_detector: str
    right_detector: str
    shared_fn: int
    union_fn: int
    jfn: MetricCell
    independence_reference: MetricCell
    ejf: MetricCell
    fn_jaccard: MetricCell

class RegimeRecord(BaseModel):
    model_config = ConfigDict(extra='forbid')
    schema_version: Literal['canonical_regime_v1'] = 'canonical_regime_v1'
    regime_id: str
    status: Literal['OBSERVED', 'AWAITING_FROZEN_R3_BUNDLE']
    population_type: Literal['MIXED', 'ATTACK_ONLY', 'NOT_YET_OBSERVED']
    attack_count: int | None
    benign_count: int | None
    detectors: list[DetectorRecord]
    pairs: list[PairRecord]
    all_three_fn: int | None
    all_three_jfn: MetricCell
    recovery: list[dict]
    failure_patterns: list[dict]
    targeted: list[dict]
    source_family: dict
    parent_child: dict
    uncertainty: list[dict]
    lineage: dict
    provenance: dict
    @model_validator(mode='after')
    def guard(self):
        if self.population_type == 'ATTACK_ONLY':
            require(self.benign_count == 0, 'ATTACK_ONLY_BENIGN_CONFLICT')
            for d in self.detectors:
                require(all(getattr(d, k).status == 'NOT_APPLICABLE' for k in ('fpr','roc_auc','ap')),
                        'ATTACK_ONLY_METRIC_GUARD')
                require(d.tn is None and d.fp is None, 'ATTACK_ONLY_COUNTS_GUARD')
        if self.status == 'AWAITING_FROZEN_R3_BUNDLE':
            require(self.attack_count is None and self.all_three_fn is None and
                    self.all_three_jfn.status == NOT_OBSERVED, 'R3_PLACEHOLDER_MUST_NOT_BE_ZERO')
        return self

def normalize(regime_id, raw, *, supplements=None, provenance=None):
    """Validate frozen schema, then check aggregate counts against failure patterns."""
    b = validate_frozen_bundle(raw)
    require(b.comparison_view_id == 'OPERATIONAL_FIXED_V1', 'OPERATIONAL_VIEW_REQUIRED')
    supplements = supplements or {}
    c = raw['core_metrics']
    n, benign = b.attack_count, b.benign_count
    patterns = {p['pattern_id']: p['count'] for p in c['failure_patterns']['patterns']}
    require(set(patterns) == {f'{i:03b}' for i in range(8)} and sum(patterns.values()) == n,
            'FAILURE_PATTERN_POPULATION_CONFLICT')
    p = c['individual']['provenance']
    ranking = supplements.get('ranking', {})
    ranking = ranking.get('detectors', ranking)
    detectors = []
    for i, d in enumerate(c['individual']['detectors']):
        require(d['detector_id'] == IDS[i], 'DETECTOR_ORDER_CONFLICT')
        fn = sum(v for k, v in patterns.items() if k[i] == '1')
        require(d['fn'] == fn and d['tp'] + fn == n and d['tn'] + d['fp'] == benign, 'COUNT_CONFLICT')
        assert_value(d['fnr']['value'], ratio(fn, n), 'FNR')
        assert_value(d['recall']['value'], ratio(d['tp'], n), 'RECALL')
        assert_value(d['fpr']['value'], ratio(d['fp'], benign), 'FPR')
        rank = ranking.get(d['detector_id'], {})
        detectors.append(dict(detector_id=d['detector_id'], threshold_id=p['operational_threshold_ids'][i],
            threshold=p['operational_thresholds'][i], tp=d['tp'], fn=fn, tn=d['tn'] if benign else None,
            fp=d['fp'] if benign else None, recall=metric(d['recall']), fnr=metric(d['fnr']),
            fpr=metric(d['fpr']) if benign else cell(None, 'NOT_APPLICABLE'),
            roc_auc=cell(rank.get('roc_auc')) if benign else cell(None,'NOT_APPLICABLE'),
            ap=cell(rank.get('average_precision')) if benign else cell(None,'NOT_APPLICABLE')))
    pairs = []
    for q in c['common_mode']['pairs']:
        i,j = IDS.index(q['left_detector']), IDS.index(q['right_detector'])
        shared = sum(v for k,v in patterns.items() if k[i] == k[j] == '1')
        union = detectors[i]['fn'] + detectors[j]['fn'] - shared
        ref = ratio(detectors[i]['fn'],n) * ratio(detectors[j]['fn'],n) if n else None
        expected = dict(jfn=ratio(shared,n), independence_reference=ref,
                        ejf=ratio(shared,n)-ref if n else None, fn_jaccard=ratio(shared,union))
        require(q['shared_fn_count'] == shared and q['union_count'] == union, 'PAIR_COUNT_CONFLICT')
        for k,v in expected.items(): assert_value(q[k]['value'],v,k.upper())
        pairs.append(dict(left_detector=q['left_detector'],right_detector=q['right_detector'],
                          shared_fn=shared, union_fn=union, **{k:metric(q[k]) for k in expected}))
    require(c['common_mode']['all_three_fn_count'] == patterns['111'], 'ALL_THREE_COUNT_CONFLICT')
    assert_value(c['common_mode']['all_three_jfn']['value'],ratio(patterns['111'],n),'ALL_THREE_JFN')
    for r in c['recovery']['detectors']:
        require(r['unique_catch_count'] == patterns[r['unique_catch_pattern']], 'UNIQUE_CATCH_CONFLICT')
        assert_value(r['conditional_recovery']['value'],ratio(r['unique_catch_count'],r['both_others_miss_count']), 'CONDITIONAL_RECOVERY')
    targets = [copy.deepcopy(t) for t in (c['evasion_transfer'] or {}).get('targets',[]) if t['valid_attempt_count']]
    for t in targets:
        assert_value(t['target_evasion_rate']['value'],ratio(t['target_evasion_count'],t['valid_attempt_count']),'TARGET_EVASION')
        for x in t['transfers']:
            assert_value(x['etr']['value'],ratio(x['joint_evasion_count'],t['target_evasion_count']),'ETR')
    result = dict(regime_id=regime_id,status='OBSERVED',population_type='MIXED' if benign else 'ATTACK_ONLY',
        attack_count=n,benign_count=benign,detectors=detectors,pairs=pairs,
        all_three_fn=patterns['111'],all_three_jfn=metric(c['common_mode']['all_three_jfn']),
        recovery=copy.deepcopy(c['recovery']['detectors']),failure_patterns=copy.deepcopy(c['failure_patterns']['patterns']),
        targeted=targets,source_family={k:v for k,v in supplements.items() if k in ('source','family')},
        parent_child=supplements.get('transitions',{}),uncertainty=copy.deepcopy(raw['uncertainty']),
        lineage=dict(count=b.lineage_count,unknown_rows=b.unknown_lineage_rows),
        provenance=dict(provenance or {},frozen_bundle_provenance=p,experiment_id=b.experiment_id,
                        dataset_id=b.dataset_id,dataset_revision=b.dataset_revision))
    return RegimeRecord.model_validate(result).model_dump(mode='json')

def r3_placeholder():
    return RegimeRecord(regime_id='R3',status='AWAITING_FROZEN_R3_BUNDLE',population_type=NOT_OBSERVED,
        attack_count=None,benign_count=None,detectors=[],pairs=[],all_three_fn=None,
        all_three_jfn=MetricCell(status=NOT_OBSERVED,value=None),recovery=[],failure_patterns=[],targeted=[],
        source_family={},parent_child={},uncertainty=[],lineage={'status':NOT_OBSERVED},
        provenance={'status':NOT_OBSERVED}).model_dump(mode='json')

def load_pre_r3(*, root=ROOT):
    reads, records = [], []
    for rid, path in BUNDLES.items():
        raw=read_frozen(path,reads,root=root)
        supplements={k:read_frozen(v,reads,root=root) for k,v in SUPPLEMENTS[rid].items()}
        records.append(normalize(rid,raw,supplements=supplements,
            provenance={'baseline_sha':BASELINE_SHA,'artifacts':copy.deepcopy(reads[-(len(supplements)+1):])}))
    return dict(schema_version='regime_registry_pre_r3_v1',baseline_sha=BASELINE_SHA,
                records=records+[r3_placeholder()],read_receipt=reads,
                authoritative_queries={'ds_v2':0,'dm_b_v1':0,'dg_v1':0,'verifier':0},protected_access=False)

def interval(record, name):
    return next((copy.deepcopy(i) for u in record['uncertainty'] for i in u['intervals']
                 if i['metric_id'] == name), {'status':NOT_OBSERVED if record['regime_id']=='R3' else 'UNDEFINED'})

def tables(registry):
    result={k:[] for k in 'ABCDE'}
    for r in registry['records']:
        base={'regime':r['regime_id'],'attack_count':r['attack_count'],'status':r['status']}
        for d in r['detectors']:
            result['A'].append(dict(base,benign_count=r['benign_count'],**d))
        for p in r['pairs']: result['B'].append(dict(base,**p))
        result['C'].append(dict(base,all_three_fn=r['all_three_fn'],all_three_jfn=r['all_three_jfn'],ci95=interval(r,'all_three/jfn')))
        for t in r['targeted']: result['D'].append(dict(base,**t))
        for d,v in r['parent_child'].get('overall',{}).items(): result['E'].append(dict(base,detector_id=d,**v))
        if r['regime_id']=='R3':
            for d in IDS: result['A'].append(dict(base,detector_id=d,**{k:cell(None,NOT_OBSERVED) for k in ('recall','fnr','fpr','roc_auc','ap')}))
            for i,j in ((0,1),(0,2),(1,2)):
                result['B'].append(dict(base,left_detector=IDS[i],right_detector=IDS[j],shared_fn=None,
                    **{k:cell(None,NOT_OBSERVED) for k in ('jfn','independence_reference','ejf','fn_jaccard')}))
            result['D'].append(dict(base,target_detector='ALL',target_evasion_rate=cell(None,NOT_OBSERVED),transfers=[]))
            result['E'].append(dict(base,transition_status=NOT_OBSERVED))
    return result

def figure_data(registry):
    t=tables(registry)
    data={ '01_fnr':[dict(regime=x['regime'],series=x['detector_id'],**x['fnr']) for x in t['A']] }
    for key, name in [('02_pairwise_jfn','jfn'),('03_ejf','ejf'),('04_fn_jaccard','fn_jaccard')]:
        data[key]=[dict(regime=x['regime'],series=x['left_detector']+' × '+x['right_detector'],**x[name]) for x in t['B']]
    data['05_all_three_jfn']=[dict(regime=x['regime'],series='all_three',**x['all_three_jfn'],ci95=x['ci95']) for x in t['C']]
    data['06_targeted_evasion']=[dict(regime=x['regime'],series=x['target_detector'],**metric(x['target_evasion_rate']))
        if x['regime']!='R3' else dict(regime='R3',series='ALL',**cell(None,NOT_OBSERVED)) for x in t['D']]
    data['07_transfer_matrix']=[dict(regime=x['regime'],series=x['target_detector']+' → '+v['transfer_detector'],**metric(v['etr']))
        for x in t['D'] for v in x['transfers']]+[dict(regime='R3',series='ALL',**cell(None,NOT_OBSERVED))]
    source=[]
    for r in registry['records']:
        family=r['source_family'].get('family',{}).get('groups',{})
        for group,v in family.items():
            for d in v['core_metrics']['individual']['detectors']:
                source.append(dict(regime=r['regime_id'],series=group+'/'+d['detector_id'],**metric(d['fnr']),
                    lineage_count=v['lineage_count'],uncertainty_status=v['uncertainty_status']))
        # Frozen paired-transition source counts determine terminal detector FN exactly.
        for group,ds in r['parent_child'].get('by_source',{}).items():
            for d,v in ds.items():
                source.append(dict(regime=r['regime_id'],series=group+'/'+d,
                    **cell(ratio(v['catch_to_miss']+v['miss_to_miss'],sum(v.values())))))
    data['08_source_failure']=source+[dict(regime='R0',series='source decomposition unavailable',**cell(None,'UNDEFINED')),
                                    dict(regime='R3',series='source',**cell(None,NOT_OBSERVED))]
    data['09_verifier_recovery']=[dict(regime='R3',series=v,**cell(None,NOT_OBSERVED)) for v in ('V1','V2','V3')]
    return data

def export(registry, destination, *, plot=True, preview=False):
    destination=Path(destination); destination.mkdir(parents=True,exist_ok=True)
    generated={'canonical_records_v1.json':registry,'tables_v1.json':tables(registry),'figure_data_v1.json':figure_data(registry)}
    for name,value in generated.items(): (destination/name).write_bytes(bytes_json(value))
    if plot:
        import matplotlib
        matplotlib.use('Agg')
        matplotlib.rcParams['svg.hashsalt'] = 'phase1_synthesis_v1'
        import matplotlib.pyplot as plt
        for name,rows in generated['figure_data_v1.json'].items():
            if name=='07_transfer_matrix':
                import numpy as np
                fig,axes=plt.subplots(1,3,figsize=(9,4),layout='constrained')
                cmap=plt.get_cmap('Blues').copy(); cmap.set_bad('#ededed')
                for ax,rid in zip(axes,('R2-DMB','R2-D_S','R3')):
                    ax.set_title(rid)
                    if rid=='R3':
                        ax.set_axis_off();ax.text(.5,.5,NOT_OBSERVED,transform=ax.transAxes,ha='center',fontsize=8)
                        continue
                    values=np.full((3,3),np.nan); labels={}
                    for row in rows:
                        if row['regime']!=rid: continue
                        left,right=row['series'].split(' → ');i,j=IDS.index(left),IDS.index(right)
                        values[i,j]=row['value'] if row['status']=='OBSERVED' else np.nan
                        labels[i,j]=f"{row['value']:.3f}" if row['value'] is not None else 'UNDEFINED'
                    ax.imshow(values,cmap=cmap,vmin=0,vmax=1)
                    ax.set_xticks(range(3),['DS','DMB','DG']);ax.set_yticks(range(3),['DS','DMB','DG'])
                    ax.set_xlabel('Transfer detector');ax.set_ylabel('Target detector')
                    for i in range(3):
                        for j in range(3):ax.text(j,i,labels.get((i,j),'N/A'),ha='center',va='center',fontsize=7)
                fig.suptitle('Conditional evasion transfer (ETR, fraction)')
                fig.savefig(destination/(name+'.svg'),metadata={'Date':None})
                if preview:fig.savefig(destination/(name+'.png'),dpi=120)
                plt.close(fig);continue
            fig,ax=plt.subplots(figsize=(9,5),layout='constrained')
            observed=[r for r in rows if r['status']=='OBSERVED']
            labels=[r['regime']+' / '+r['series'] for r in observed]
            ax.barh(range(len(observed)),[r['value'] for r in observed],color='#295e8c')
            ax.set_yticks(range(len(observed)),labels,fontsize=7)
            ax.set_xlabel('Fraction'); ax.set_title({'01_fnr':'FNR','02_pairwise_jfn':'Pairwise JFN','03_ejf':'EJF',
                '04_fn_jaccard':'FN Jaccard','05_all_three_jfn':'All-three JFN'}.get(name,name[3:].replace('_',' ').capitalize()))
            ax.text(.99,.01,'R3: NOT_YET_OBSERVED',transform=ax.transAxes,ha='right',fontsize=8)
            if not observed:
                ax.set_axis_off()
                ax.text(.5,.5,'V1 / V2 / V3\nNOT_YET_OBSERVED\nAwaiting frozen R3 failure population',
                        transform=ax.transAxes,ha='center',va='center')
            unavailable=sorted({r['regime']+': '+r['status'] for r in rows if r['status'] not in ('OBSERVED',NOT_OBSERVED)})
            if unavailable: fig.text(.01,.005,'; '.join(unavailable),fontsize=7)
            fig.savefig(destination/(name+'.svg'),metadata={'Date':None})
            if preview: fig.savefig(destination/(name+'.png'),dpi=120)
            plt.close(fig)
    return generated

def validate_r3_handoff(handoff, reader):
    """Phase 2 only: reader(commit,path)->committed bytes, never a worktree reader."""
    import re
    require(type(reader) is CommittedR3Reader or (handoff.get('evidence_kind')=='SYNTHETIC_FIXTURE' and
            getattr(reader,'evidence_kind',None)=='SYNTHETIC_FIXTURE'), 'R3_COMMITTED_READER_REQUIRED')
    require(handoff.get('status')=='ACCEPTED' and handoff.get('frozen') is True,'R3_NOT_ACCEPTED_FROZEN')
    commit=handoff.get('freeze_commit_sha','')
    require(bool(re.fullmatch('[0-9a-f]{40}',commit)),'R3_COMMITTED_FREEZE_SHA_REQUIRED')
    descriptors=handoff.get('artifacts',{})
    require(set(R3_ROLES+('freeze_receipt',)) <= set(descriptors),'R3_PARTIAL_BUNDLE')
    payload={}
    for role in R3_ROLES+('freeze_receipt',):
        desc=descriptors[role]
        path=desc.get('path','')
        require(path.startswith('artifacts/research_protocol/r3/') and '..' not in path.split('/') and '\\' not in path,'R3_ARTIFACT_PATH_INVALID')
        require(bool(re.fullmatch('[0-9a-f]{64}',desc.get('sha256',''))),'R3_ARTIFACT_HASH_REQUIRED')
        raw=reader(commit,path)
        require(sha256(raw)==desc['sha256'],'R3_ARTIFACT_HASH_MISMATCH')
        payload[role]=json.loads(raw)
    receipt=payload['freeze_receipt']
    require(receipt.get('status')=='ACCEPTED' and receipt.get('frozen') is True and
            receipt.get('verifier_authoritative_queries_at_freeze')==0 and
            receipt.get('protected_evaluation_accessed') is False,'R3_FREEZE_RECEIPT_INVALID')
    require(receipt.get('artifact_hashes')=={r:descriptors[r]['sha256'] for r in R3_ROLES},'R3_FREEZE_BINDING_CONFLICT')
    # Bind component results to bundle, not merely to arbitrary hashes.
    raw=payload['result_bundle']; validate_frozen_bundle(raw)
    require(raw['threat_regime'].startswith('R3_'),'R3_REGIME_REQUIRED')
    for role,key in [('common_mode','common_mode'),('failure_patterns','failure_patterns')]:
        require(payload[role]==raw['core_metrics'][key],'R3_COMPONENT_BINDING_CONFLICT')
    require(payload['uncertainty']==raw['uncertainty'],'R3_UNCERTAINTY_BINDING_CONFLICT')
    prediction=payload['prediction_manifest']
    require(prediction.get('prediction_batch_sha')==raw['core_metrics']['individual']['provenance']['prediction_batch_sha'], 'R3_PREDICTION_BINDING_CONFLICT')
    manifest=payload['all_three_failure_manifest']
    require(manifest.get('population_count')==raw['core_metrics']['common_mode']['all_three_fn_count'], 'R3_FAILURE_COUNT_BINDING_CONFLICT')
    return payload

if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--output',required=True); parser.add_argument('--no-plot',action='store_true')
    args=parser.parse_args(); export(load_pre_r3(),args.output,plot=not args.no_plot)
