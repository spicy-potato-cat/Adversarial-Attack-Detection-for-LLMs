"""Model-free validation for additive Track B-002 supporting artifacts."""
from pathlib import Path
import hashlib,json,re

DMB_SHA='0bb192d2c468530479fa8ec0786f35d8bf5a8287e4ee401a953292d221736844'
DG_MODEL='meta-llama/Llama-Prompt-Guard-2-22M'
DG_REV='11614a155199674a0a95e6602d6ab0417b790ed0'
REVISIONS={'V1':'a8ded8e697ce7c355e395a0df51f94adb4a2fd27','V2':'90c9989b1a342275dd0d1a95aad283c04e075671','V3':'3de033d89b499a18d9a573b5192bf3b967ef48c5'}
CLASSES={'GIT_TRACKED','GIT_LFS','REMOTE_IMMUTABLE','DETERMINISTICALLY_RECONSTRUCTABLE','LOCAL_ONLY','UNKNOWN'}
def require(v,code):
    if not v:raise ValueError(code)
def read(root,path):return json.loads((Path(root)/path).read_text(encoding='utf-8'))
def validate_portability(v):
    require(v['artifact_version']=='frozen_stack_portability_manifest_v2','PORTABILITY_VERSION')
    require(type(v['artifacts']) is list and bool(v['artifacts']),'ARTIFACT_INVENTORY_REQUIRED')
    require(len({r['logical_path'] for r in v['artifacts']})==len(v['artifacts']),'DUPLICATE_ARTIFACT')
    for row in v['artifacts']:
        require(row['classification'] in CLASSES,'CLASSIFICATION_INVALID')
        if row.get('expected_sha256') is not None:require(re.fullmatch('[0-9a-f]{64}',row['expected_sha256']),'INVALID_ARTIFACT_SHA')
        if row['classification']=='REMOTE_IMMUTABLE':require(re.fullmatch('[0-9a-f]{40}',row['remote']['revision']),'REMOTE_REVISION_UNPINNED')
    require(v['accepted_detector_manifests_modified'] is False,'ACCEPTED_MANIFEST_MODIFIED')
    return v
def validate_readiness(v):
    require(v['artifact_version']=='verifier_runtime_readiness_v1','READINESS_VERSION')
    require({r['candidate_id'] for r in v['models']}==set(REVISIONS) and len(v['models'])==3,'READINESS_EXACT_CANDIDATES')
    require(v['authoritative_verifier_queries']==0 and all(n==0 for n in v['authoritative_r3_queries'].values()),'AUTHORITATIVE_QUERY_FORBIDDEN')
    require(v['failure_population']=='NOT_OPENED_NOT_CONSTRUCTED','FAILURE_POPULATION_TOUCHED')
    for r in v['models']:
        require(r['revision']==REVISIONS[r['candidate_id']],'VERIFIER_REVISION_CHANGED')
        require(r['scientific_inference_executed'] is False and r['weights_downloaded'] is False,'INFERENCE_OR_DOWNLOAD_OCCURRED')
        require(r['threshold_tuned_on_failure_population'] is False,'FUTURE_FAILURE_TUNING')
        require(r['live_execution_ready'] is False,'UNTESTED_LIVE_READINESS_CLAIM')
    return v
def validate_dg(v):
    require(v['frozen_model']==DG_MODEL and v['frozen_revision']==DG_REV,'DG_IDENTITY_DRIFT')
    require(v['proof']['parsed_json_identical'] is True,'DG_SEMANTIC_CHANGE')
    require(v['original_environment_recorded_sha256']==v['reconstructed_crlf_sha256'],'DG_RECONSTRUCTION_FAILURE')
    require(v['scientific_impact']=='NONE' and v['accepted_historical_artifacts_modified'] is False,'DG_SCIENTIFIC_CHANGE')
    return v
def validate_fresh_clone(v):
    require(v['execution_status']=='EXECUTION_DEFERRED_UNTIL_TRACK_A_IDLE','FRESH_CLONE_EXECUTED')
    for r in v['required_artifacts']:
        require(re.fullmatch('[0-9a-f]{64}',r['expected_sha256'] or ''),'FRESH_CLONE_HASH_MISSING')
    require(v['dmb_expected_sha256']==DMB_SHA and v['dmb_expected_size_bytes']==328492280,'DMB_FRESH_CLONE_DRIFT')
    return v
