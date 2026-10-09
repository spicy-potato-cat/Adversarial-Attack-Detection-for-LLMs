"""Phase 2 input gates and synthetic recovery analysis; no model loading."""
from __future__ import annotations
from collections import defaultdict
from dataclasses import asdict
from datetime import datetime
import itertools
import json
from pathlib import Path
import re
import subprocess
from pydantic import BaseModel, ConfigDict, model_validator
from typing import Literal
from detection_service.research_protocol.phase1_synthesis import (
    R3_ROLES, require, sha256, bytes_json, validate_r3_handoff, cell, ratio, CommittedR3Reader)
from detection_service.research_protocol.verifier_preparation import (
    REVISIONS, FailurePopulation, recovery)

AUTHORITATIVE_QUERIES=0
EMPTY='VERIFIER_RECOVERY_UNDEFINED_EMPTY_FAILURE_POPULATION'

def aware_time(value):
    require(isinstance(value,str),'FREEZE_TIME_REQUIRED')
    stamp=datetime.fromisoformat(value.replace('Z','+00:00'))
    require(stamp.tzinfo is not None,'FREEZE_TIMEZONE_REQUIRED')
    return stamp

def validate_population_manifest(manifest,receipt,*,manifest_sha,freeze_commit_sha,first_verifier_query_at=None):
    require(isinstance(receipt,dict),'FAILURE_FREEZE_RECEIPT_REQUIRED')
    require(receipt.get('status')=='ACCEPTED' and receipt.get('frozen') is True and
            receipt.get('r3_status')=='ACCEPTED','FAILURE_FREEZE_NOT_ACCEPTED')
    require(bool(re.fullmatch('[0-9a-f]{40}',freeze_commit_sha)),'FAILURE_COMMITTED_FREEZE_REQUIRED')
    require(receipt.get('manifest_sha256')==manifest_sha,'FAILURE_MANIFEST_HASH_MISMATCH')
    require(receipt.get('verifier_authoritative_queries_at_freeze')==0 and
            receipt.get('protected_evaluation_accessed') is False,'FAILURE_POPULATION_NOT_PRERUN_FROZEN')
    frozen=aware_time(receipt.get('frozen_at'))
    if first_verifier_query_at is not None:
        require(frozen < aware_time(first_verifier_query_at),'FAILURE_POPULATION_FROZEN_AFTER_QUERIES')
    require(manifest.get('status')=='ACCEPTED' and manifest.get('regime')=='R3' and
            manifest.get('partition')=='INTERNAL_TEST','FAILURE_MANIFEST_REGIME_REJECTED')
    samples=manifest.get('samples')
    require(isinstance(samples,list) and manifest.get('population_count')==len(samples),'FAILURE_COUNT_CONFLICT')
    ids=set()
    for s in samples:
        require(all(isinstance(s.get(k),str) and s[k].strip() for k in
            ('sample_id','lineage_id','parent_sample_id','source')),'FAILURE_LINEAGE_REQUIRED')
        require(s['sample_id'] not in ids,'FAILURE_DUPLICATE_SAMPLE')
        ids.add(s['sample_id'])
        require(s.get('regime')=='R3' and s.get('partition')=='INTERNAL_TEST' and
                s.get('truth_label')==1 and s.get('base_decisions')==['BENIGN']*3,'ALL_THREE_FAILURE_REQUIRED')
        require(s.get('attack_family') is None or isinstance(s['attack_family'],str),'FAILURE_FAMILY_INVALID')
        ref=s.get('text_ref',{})
        require(isinstance(ref.get('path'),str) and ref['path'] and bool(re.fullmatch('[0-9a-f]{64}',ref.get('sha256',''))),
                'FAILURE_LOCAL_TEXT_REFERENCE_REQUIRED')
        require('text' not in s,'FAILURE_TEXT_EXECUTION_TIME_ONLY')
    return dict(status='READY' if samples else EMPTY,population_count=len(samples),samples=tuple(samples),
        membership_sha256=sha256(bytes_json(samples)),
        manifest_sha256=manifest_sha,freeze_commit_sha=freeze_commit_sha,freeze_receipt=receipt,
        first_verifier_query_at=first_verifier_query_at,text_resolved=False)

def load_failure_population(handoff,reader,*,first_verifier_query_at=None):
    """Load only a validated final R3 handoff; never search journals or widen scope."""
    payload=validate_r3_handoff(handoff,reader)
    receipt=payload['freeze_receipt']
    population_receipt=receipt.get('failure_population_freeze_receipt')
    require(population_receipt is not None,'FAILURE_FREEZE_RECEIPT_REQUIRED')
    return validate_population_manifest(payload['all_three_failure_manifest'],population_receipt,
        manifest_sha=handoff['artifacts']['all_three_failure_manifest']['sha256'],
        freeze_commit_sha=handoff['freeze_commit_sha'],first_verifier_query_at=first_verifier_query_at)

def resolve_local_text(population,local_root,*,phase2_authorized=False):
    require(phase2_authorized is True,'VERIFIER_TEXT_EXECUTION_AUTHORIZATION_REQUIRED')
    require(population['membership_sha256']==sha256(bytes_json(population['samples'])),'FAILURE_POPULATION_MUTATED')
    root=Path(local_root).resolve(strict=True)
    resolved=[]
    for s in population['samples']:
        ref=s['text_ref']; relative=Path(ref['path'])
        require(not relative.is_absolute() and '..' not in relative.parts,'FAILURE_TEXT_PATH_INVALID')
        path=(root/relative).resolve(strict=True)
        require(path.is_relative_to(root),'FAILURE_TEXT_OUTSIDE_LOCAL_ROOT')
        data=path.read_bytes()
        require(sha256(data)==ref['sha256'],'FAILURE_TEXT_HASH_MISMATCH')
        resolved.append(dict(s,text=data.decode('utf-8')))
    return tuple(resolved)

class RecoveryMetric(BaseModel):
    model_config=ConfigDict(extra='forbid')
    population_count:int
    recovered_count:int
    status:Literal['COMPLETE','INCOMPLETE','VERIFIER_RECOVERY_UNDEFINED_EMPTY_FAILURE_POPULATION']
    recovery:float|None
    ci95:dict
    @model_validator(mode='after')
    def validate_metric(self):
        require(0<=self.recovered_count<=self.population_count,'RECOVERY_COUNT_CONFLICT')
        if self.population_count==0:
            require(self.status==EMPTY and self.recovery is None,'EMPTY_RECOVERY_UNDEFINED_REQUIRED')
        elif self.status=='COMPLETE':
            require(self.recovery==self.recovered_count/self.population_count,'RECOVERY_RATE_CONFLICT')
        else: require(self.recovery is None,'INCOMPLETE_RECOVERY_CANNOT_BE_OFFICIAL')
        return self

class PredictionResult(BaseModel):
    model_config=ConfigDict(extra='forbid')
    sample_id:str
    lineage_id:str
    regime:str
    verifier_id:Literal['V1','V2','V3']
    model_revision:str
    raw_score:float|None
    normalized_probability:float|None
    probability_semantics:Literal['NATIVE_CLASS_SOFTMAX','UNAVAILABLE']
    decision:Literal['ATTACK','BENIGN']|None
    status:Literal['OK','ERROR','INVALID_OUTPUT','INPUT_LIMIT_EXCEEDED']
    input_coverage:float
    truncation:bool
    latency_ms:float
    provenance:dict
    evidence_kind:Literal['SYNTHETIC_FIXTURE','FROZEN_FAILURE_EXECUTION']
    @model_validator(mode='after')
    def mapping(self):
        require(self.model_revision==REVISIONS[self.verifier_id],'VERIFIER_REVISION_CONFLICT')
        require((self.status=='OK')==(self.decision is not None),'VERIFIER_STATUS_DECISION_CONFLICT')
        require(0<=self.input_coverage<=1 and self.latency_ms>=0,'VERIFIER_COVERAGE_OR_LATENCY_INVALID')
        require(self.normalized_probability is None or 0<=self.normalized_probability<=1,'VERIFIER_PROBABILITY_INVALID')
        require(self.probability_semantics!='UNAVAILABLE' or self.normalized_probability is None,'VERIFIER_PROBABILITY_FABRICATED')
        return self

class OverlapMetric(BaseModel):
    left_verifier:Literal['V1','V2','V3']
    right_verifier:Literal['V1','V2','V3']
    population_count:int
    shared_catches:int|None
    catch_jaccard:dict
    status:Literal['COMPLETE','INCOMPLETE','NOT_YET_OBSERVED']

class UniqueRecovery(BaseModel):
    verifier_id:Literal['V1','V2','V3']
    compared_verifier_ids:list[str]
    unique_catches:int|None
    unique_sample_ids:list[str]
    status:Literal['COMPLETE','INCOMPLETE','NOT_YET_OBSERVED']

class SourceRecovery(BaseModel):
    verifier_id:Literal['V1','V2','V3']
    group_type:Literal['source','attack_family']
    group_id:str
    lineage_count:int
    metric:RecoveryMetric

class UncertaintyResult(BaseModel):
    status:Literal['SUPPLIED_FROZEN_INTERVAL','NOT_YET_OBSERVED','UNDEFINED']
    population_sha256:str
    method:str
    confidence_level:Literal[0.95]=.95
    lineage_clustered:bool
    replicates:int|None
    seed:int|None
    intervals:list[dict]
    provenance:dict

class VerifierResultBundle(BaseModel):
    schema_version:Literal['verifier_result_bundle_v1']='verifier_result_bundle_v1'
    population_sha256:str
    freeze_commit_sha:str
    evidence_kind:Literal['SYNTHETIC_FIXTURE','FROZEN_FAILURE_EXECUTION']
    predictions:list[PredictionResult]
    recovery:dict[str,RecoveryMetric]
    overlap:list[OverlapMetric]
    unique_recovery:list[UniqueRecovery]
    source_analysis:list[SourceRecovery]
    uncertainty:UncertaintyResult
    unrecovered_sample_ids:list[str]|None
    pending_verifier_ids:list[str]
    provenance:dict

def recovery_cell(population,predictions,vid,*,regime=None):
    value=recovery(population,predictions,vid,regime=regime)
    return RecoveryMetric(population_count=value['denominator'],recovered_count=value['detected'],
        status=EMPTY if not value['denominator'] else value['status'],recovery=value['recovery'],
        ci95={'status':'UNDEFINED' if not value['denominator'] else 'NOT_YET_OBSERVED',
              'ci_lower':None,'ci_upper':None,'reason':'Consume frozen Phase 2 lineage intervals; no bootstrap in Phase 1.'})

def analyze_synthetic(population,predictions_by_verifier):
    """Independent V1/V2 results remain valid when V3 is pending. No new CI."""
    require(type(population) is FailurePopulation,'SYNTHETIC_POPULATION_REQUIRED')
    require(set(predictions_by_verifier)<=set(REVISIONS),'UNKNOWN_VERIFIER')
    metrics={v:recovery_cell(population,p,v) for v,p in predictions_by_verifier.items()}
    sample_ids={s.sample_id for s in population.samples}
    catch={v:{p.sample_id for p in ps if p.status=='OK' and p.decision=='ATTACK' and
            p.input_coverage==1 and not p.truncation} for v,ps in predictions_by_verifier.items()}
    complete={v for v,m in metrics.items() if m.status=='COMPLETE' or (not sample_ids and m.status==EMPTY)}
    overlap=[]
    for i,j in itertools.combinations(sorted(predictions_by_verifier),2):
        good={i,j}<=complete; shared=len(catch[i]&catch[j]); union=len(catch[i]|catch[j])
        overlap.append(dict(left_verifier=i,right_verifier=j,population_count=len(sample_ids),
            shared_catches=shared if good else None,catch_jaccard=cell(ratio(shared,union)) if good else cell(None),
            status='COMPLETE' if good else 'INCOMPLETE'))
    all_complete=set(predictions_by_verifier)<=complete
    unique=[]
    for v in sorted(predictions_by_verifier):
        others=set().union(*(catch[u] for u in catch if u!=v))
        ids=sorted(catch[v]-others) if all_complete else []
        unique.append(dict(verifier_id=v,compared_verifier_ids=sorted(predictions_by_verifier),unique_catches=len(ids) if all_complete else None,
                           unique_sample_ids=ids,status='COMPLETE' if all_complete else 'INCOMPLETE'))
    sources=[]
    from detection_service.research_protocol.verifier_preparation import synthetic_population
    for group_type in ('source','attack_family'):
        grouped=defaultdict(list)
        for s in population.samples: grouped[getattr(s,group_type) or 'UNDEFINED'].append(s)
        for group,ss in sorted(grouped.items()):
            sub=synthetic_population(ss); ids={s.sample_id for s in ss}
            for v,ps in predictions_by_verifier.items():
                m=recovery_cell(sub,[p for p in ps if p.sample_id in ids],v)
                sources.append(dict(verifier_id=v,group_type=group_type,group_id=group,
                                    lineage_count=len({s.lineage_id for s in ss}),metric=m))
    bundle=VerifierResultBundle(population_sha256=population.membership_sha256,freeze_commit_sha='0'*40,
        evidence_kind='SYNTHETIC_FIXTURE',predictions=[asdict(p) for v in sorted(predictions_by_verifier) for p in predictions_by_verifier[v]],
        recovery=metrics,overlap=overlap,unique_recovery=unique,source_analysis=sources,
        uncertainty=UncertaintyResult(status='UNDEFINED' if not sample_ids else 'NOT_YET_OBSERVED',
            population_sha256=population.membership_sha256,method='FROZEN_LINEAGE_CLUSTERED_PERCENTILE',
            lineage_clustered=True,replicates=None,seed=None,intervals=[],provenance={'phase1_no_resampling':True}),
        unrecovered_sample_ids=sorted(sample_ids-set().union(*catch.values())) if all_complete and catch else None,
        pending_verifier_ids=sorted(set(REVISIONS)-set(predictions_by_verifier)),provenance={'authoritative_queries':0})
    return bundle.model_dump(mode='json')
