"""Read-only frozen-runtime inventory. Never loads models or dataset populations."""
import hashlib
import json
from pathlib import Path
import subprocess

BASE='99b012e5b72fbae9273fa73ccc8d84d579a69c83'
PRESERVED='e6b6a2af2a78e2a31aae6d9377378993f678b073'
BACKUP='detection_service/outputs/common003-preserved-stack/'
MANIFEST='artifacts/research_protocol/detector_set_manifest_v1.json'
MAIN=Path(r'C:\Users\harsh\Adversarial-Attack-Detection-for-LLMs')
CLASSES=('GIT_TRACKED','GIT_LFS','REMOTE_IMMUTABLE','DETERMINISTICALLY_RECONSTRUCTABLE','LOCAL_ONLY','UNKNOWN')
def sha(data): return hashlib.sha256(data).hexdigest()
def git(root,*args): return subprocess.check_output(['git','-C',str(root),*args],stderr=subprocess.DEVNULL)

def inventory(root, *, accepted_local_root=MAIN):
    root=Path(root).resolve()
    assert root.name == 'Adversarial-Attack-Detection-for-LLMs-track-b'
    assert git(root,'merge-base','HEAD',BASE).decode().strip() == BASE
    frozen=json.loads((root/MANIFEST).read_text(encoding='utf-8'))
    tracked=set(git(root,'ls-files').decode().splitlines())
    historic=set(git(root,'ls-tree','-r','--name-only',PRESERVED).decode().splitlines())
    locations=frozen['accepted_evidence_locations']
    rows={}
    def add(logical,role,detector,*,remote=None,expected=None):
        if logical in rows:
            rows[logical]['roles'].append(role)
            if detector not in rows[logical]['detectors']: rows[logical]['detectors'].append(detector)
            return
        entry=locations.get(logical,{})
        local=entry.get('local_path',logical)
        expected=expected or entry.get('sha256')
        # Only explicitly listed runtime/configuration/model files are inspected.
        assert not any(x in logical.lower() for x in ('r2_ds','final_test','protected','sample_manifest'))
        assert 'prediction' not in logical.lower() or logical.startswith('detection_service/') and logical.endswith('.py')
        restored=local[len(BACKUP):] if local.startswith(BACKUP) else None
        candidate=root/local
        source='TRACK_B_CHECKOUT'
        if not candidate.is_file():
            candidate=Path(accepted_local_root)/local
            source='ACCEPTED_LOCAL_FILE_READ_ONLY'
        exists=candidate.is_file()
        size=candidate.stat().st_size if exists else None
        observed=sha(candidate.read_bytes()) if exists and size<=20*1024*1024 else None
        mismatch=bool(expected and observed and expected!=observed)
        if local in tracked:
            git_bytes=git(root,'show',BASE+':'+local)
            git_blob_sha=sha(git_bytes)
            prefix=git_bytes[:140]
            classification='GIT_LFS' if prefix.startswith(b'version https://git-lfs.github.com/spec/v1') else 'GIT_TRACKED'
        elif restored in historic:
            data=git(root,'show',PRESERVED+':'+restored)
            historical_sha=sha(data)
            assert expected is None or historical_sha==expected, logical
            classification='DETERMINISTICALLY_RECONSTRUCTABLE'
        elif remote:
            classification='REMOTE_IMMUTABLE'
        elif exists:
            classification='LOCAL_ONLY'
        else:
            classification='UNKNOWN'
        row=dict(logical_path=logical,runtime_location=local,roles=[role],detectors=[detector],
            classification=classification,expected_sha256=expected,exists_on_machine=exists,
            present_in_track_b_checkout=(root/local).is_file(),location_inspected=str(candidate) if exists else None,
            byte_size=size,hash_observed_sha256=observed,hash_status='MISMATCH' if mismatch else 'VERIFIED' if expected and observed else 'RECORDED_NOT_REHASHED_LARGE_FILE' if exists and expected else 'UNBOUND' if exists else 'MISSING',
            source=source,remote=remote,
            remote_availability='NEEDS_POST_TRACK_A_FRESH_CLONE_TEST' if remote else 'NOT_APPLICABLE')
        if local in tracked:
            row['git_blob_sha256']=git_blob_sha
            row['git_blob_matches_frozen_hash']=git_blob_sha==expected if expected else None
            row['checkout_byte_drift']=mismatch
            row['checkout_drift_reason']='BINDING_EXPECTED_DIFFERS_FROM_BASE_BLOB' if mismatch and observed==git_blob_sha else 'LINE_ENDING_CONVERSION' if mismatch and git_bytes.replace(b'\r\n',b'\n') == candidate.read_bytes().replace(b'\r\n',b'\n') else 'OTHER_OR_NONE'
            if mismatch:
                row['required_action']='Restore exact accepted Git blob bytes in an authorized isolated runtime; never change frozen expected hash. Audit does not modify checkout.'
        if restored in historic:
            row['exact_restoration']=dict(commit=PRESERVED,git_path=restored,sha256=historical_sha,
                destination=local,method='Extract exact Git blob after authorization; no retraining, refitting or recalibration',
                executed=False,remote_commit_reachability='NOT_PROVEN; accepted historic commit exists locally')
        rows[logical]=row
    for d in frozen['detectors']:
        label=d['stack_label']
        for key,role,hashkey in [('model_artifact_path','MODEL_OR_CLASSIFIER','model_hash'),
                 ('calibrator_artifact','CALIBRATOR','calibrator_hash'),
                 ('reference_artifact_path','FEATURE_REFERENCE','reference_hash'),
                 ('configuration_path','CONFIGURATION',None),('implementation_path','IMPLEMENTATION','implementation_sha256')]:
            path=d.get(key)
            if path:
                remote=None
                if label=='D_G' and key=='model_artifact_path':
                    remote=dict(model_id=d['model_name'],revision=d['model_revision'],file='model.safetensors',gated=True)
                add(path,role,label,remote=remote,expected=d.get(hashkey))
        if label=='D_S':
            snap=d['reference_lm_snapshot']
            for name,expected in snap['file_sha256'].items():
                add(snap['snapshot_path']+'/'+name,'REFERENCE_LM_TOKENIZER_SNAPSHOT',label,
                    remote=dict(model_id=snap['model_id'],revision=snap['revision'],file=name),expected=expected)
            for logical,entry in locations.items():
                if logical.startswith(('detection_service/app/detectors/statistical_v2/',
                    'detection_service/analysis/','detection_service/app/detectors/statistical/')) and logical.endswith('.py'):
                    add(logical,'FEATURE_RUNTIME_CODE',label)
            # All identity-bound final model metadata are restored byte-for-byte.
            for logical in locations:
                if logical.startswith('artifacts/statistical_v2/final/') and logical.endswith('.json') and not any(x in logical for x in ('preflight','environment','smoke','started','adapter')):
                    add(logical,'MODEL_FEATURE_SCHEMA_BINDING',label)
            for logical in locations:
                if logical.startswith('artifacts/statistical_v2/calibration/completed_v1/') and any(logical.endswith(n) for n in ('ds_v2_calibration_integrity_v1.json','ds_v2_calibration_manifest_v1.json')):
                    add(logical,'CALIBRATION_BINDING',label)
            # Runtime code binding includes archive source paths in the model manifest.
            config_local=Path(accepted_local_root)/d['configuration_path']
            if config_local.exists():
                config=json.loads(config_local.read_text(encoding='utf-8'))
                for logical,expected in config.get('runtime_code_sha256',{}).items():
                    add(logical,'MODEL_RUNTIME_CODE_BINDING',label,expected=expected)
        elif label=='D_M-B':
            for logical in locations:
                if logical.startswith('artifacts/models/dm_b_v1/transformer/'):
                    add(logical,'FINE_TUNED_MODEL_TOKENIZER',label)
            add('artifacts/models/dm_b_v1/integrity_manifest.json','INTEGRITY_BINDING',label)
            add('artifacts/models/dm_b_v1/calibration/calibration_config.json','CALIBRATION_CONFIGURATION',label)
            # Upstream weights cannot replace the frozen project fine-tune.
            remote=dict(model_id=d['model_name'],revision=d['model_revision'],tokenizer_revision=d['tokenizer_revision'],role='BASE_PROVENANCE_ONLY_NOT_A_WEIGHT_REPLACEMENT')
            rows['remote://D_M-B-base']=dict(logical_path='remote://D_M-B-base',roles=['BASE_MODEL_PROVENANCE'],
                detectors=[label],classification='REMOTE_IMMUTABLE',remote=remote,remote_availability='NEEDS_POST_TRACK_A_FRESH_CLONE_TEST')
        else:
            snap=d.get('upstream_snapshot') or {}
            # Frozen per-file snapshot hashes reside in D_G freeze metadata.
            config=json.loads((root/'artifacts/models/dg_v1/freeze_metadata.json').read_text())
            for name,expected in config['file_sha256'].items():
                add(config['snapshot_path']+'/'+name,'MODEL_TOKENIZER_LICENSE_SNAPSHOT',label,
                    remote=dict(model_id=config['model_id'],revision=config['revision'],file=name,gated=True),expected=expected)
            add('artifacts/models/dg_v1/freeze_metadata.json','REVISION_LICENSE_DEPENDENCY_BINDING',label)
    for p in ('detection_service/research_protocol/ds_runtime.py',MANIFEST,
        'artifacts/research_protocol/runtime/ds_v2_runtime_binding_v1.json',
        'artifacts/research_protocol/runtime/ds_v2_equivalence_evidence_v1.json',
        'artifacts/research_protocol/operating_points/selected_thresholds_before_diagnostics_v1.json',
        'artifacts/research_protocol/operating_policy_manifest_v1.json',
        'artifacts/research_protocol/operating_points/predeclared_policy_v1.json',
        'artifacts/research_protocol/protocol_lock_manifest_v1.json',
        'artifacts/research_protocol/protocol_patches/exp_protocol_001_patch_001.json',
        'detection_service/research_protocol/adapters.py','detection_service/research_protocol/operating_policy.py',
        'detection_service/research_protocol/prediction.py','detection_service/research_protocol/protocol_lock.py',
        'detection_service/research_protocol/detector_semantics.py',
        'detection_service/app/detectors/guard/model.py','detection_service/app/detectors/guard/config.py',
        'detection_service/app/detectors/semantic_finetuned/config.py','detection_service/app/detectors/semantic_finetuned/calibration.py',
        'detection_service/app/detectors/base.py','detection_service/app/contracts/detector_result.py',
        'artifacts/models/dg_v1/environment.json',
        'detection_service/requirements.txt','detection_service/requirements-finetuned.txt','detection_service/requirements-quality.txt'):
        if (root/p).exists(): add(p,'RUNTIME_POLICY_DEPENDENCY_MANIFEST','FULL_STACK')
    critical=[r['logical_path'] for r in rows.values() if r['classification']=='LOCAL_ONLY' and 'MODEL_OR_CLASSIFIER' in r['roles']]
    return dict(artifact_version='frozen_stack_portability_manifest_v1',base_commit=BASE,
        accepted_detector_manifest_sha256=sha((root/MANIFEST).read_bytes()),
        scope='Static explicitly bound runtime files only; no dataset payloads, model loading, inference, downloads, cache writes or restoration',
        artifacts=[rows[k] for k in sorted(rows)],classification_enum=list(CLASSES),
        critical_local_only=critical,hash_mismatches=[r['logical_path'] for r in rows.values() if r.get('hash_status')=='MISMATCH'],
        overall_status='LOCAL_ARTIFACTS_CRITICAL' if critical else 'UNKNOWN_REQUIRES_FRESH_CLONE_TEST',
        fresh_clone_test='NEEDS_POST_TRACK_A_FRESH_CLONE_TEST',
        runtime_environment=dict(accepted_reference='artifacts/models/dg_v1/environment.json and frozen requirements',
            preparation_interpreter='Python 3.12 metadata/synthetic only; not accepted scientific runtime',
            authoritative_runtime='Restore frozen Python/dependency versions on another isolated machine; no package/environment changes performed here'),
        authoritative_queries={'D_S':0,'D_M-B':0,'D_G':0,'verifier':0},protected_data_opened=False,
        restoration_executed=False,retraining_permitted=False)

def report(v):
    lines=['# Frozen-stack portability audit v1','',
      'Verdict: **'+v['overall_status']+'**. Static preparation only; no inference or restoration.',
      '', 'D_M-B fine-tuned weights are critical LOCAL_ONLY. An upstream base checkpoint cannot',
      'replace these frozen project weights. No immutable hosted fine-tune is recorded.',
      '', 'D_S classifier, calibrator, feature references and archived code have exact hash-matching',
      'blobs in accepted Git history at '+PRESERVED+'. They are deterministically',
      'reconstructable without retraining. Their required archive destinations are ignored and',
      'absent from a fresh Track B checkout. This audit does not restore them or change loaders.',
      'Historic commit availability on a fresh remote clone still needs proof.',
      '', 'D_S reference LM and D_G weights/tokenizers have pinned upstream revisions and per-file',
      'hashes. Remote identifiers do not prove current downloadability. D_G is gated.',
      'Large weight files were inventoried by size/existence; no large-file rehash was performed.',
      'Small explicitly bound runtime files were hashed read-only. See manifest for observed',
      'hash status versus recorded expected hashes. No protected/final data was inspected.',
      '', 'Fresh-checkout source byte drift is listed explicitly below. Where the Git blob hash',
      'matches the frozen hash and normalized line endings match, this is checkout line-ending',
      'conversion, not scientific retraining. Exact-byte runtime integrity still fails until',
      'an authorized isolated restoration supplies the frozen bytes. No expected hash was relaxed.',
      'Any BINDING_EXPECTED_DIFFERS_FROM_BASE_BLOB entry needs separate provenance resolution;',
      'do not assume line-ending conversion explains a frozen-hash versus Git-blob conflict.',
      '', '## Required runtime inventory','',
      '| Artifact | Classification | Required runtime location | Hash check |',
      '|---|---|---|---|']
    for r in v['artifacts']:
        lines.append('| '+r['logical_path']+' | '+r['classification']+' | '+r.get('runtime_location','upstream pinned provenance')+' | '+r.get('hash_status','remote identifier only')+' |')
    lines += ['', '## Post-Track-A fresh-clone gate','',
      '1. Clone the accepted history on an isolated machine and prove the preserved commit is reachable.',
      '2. Restore only exact bound D_S blobs into their expected archive destinations; verify every hash.',
      '3. Secure an authorized immutable backup of the exact D_M-B fine-tuned weights; compare its frozen hash. Do not retrain.',
      '4. Prove gated D_G access and retrieve pinned D_S/D_G snapshots, checking all per-file hashes.',
      '5. Reproduce accepted dependency versions in an isolated environment; validate loaders and protocol preflight.',
      '6. Run separately authorized fresh-clone tests after Track A is idle. No scientific result follows from this static audit.',
      '', 'R2-D_S: NOT_OBSERVED. R3/verifier/protected confirmation: NOT_STARTED.',
      'No shared environment changes, cache cleanup, model moves, uploads or Track-A writes.', '']
    return '\n'.join(lines)

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--publish',action='store_true')
    a=p.parse_args();v=inventory(a.root)
    if a.publish:
        out=Path(a.root)/'artifacts/research_protocol/portability/frozen_stack_portability_manifest_v1.json'
        md=Path(a.root)/'reviews/FROZEN_STACK_PORTABILITY_AUDIT_v1.md'
        assert not out.exists() and not md.exists()
        out.parent.mkdir(parents=True,exist_ok=True)
        out.write_text(json.dumps(v,indent=2,sort_keys=True)+'\n',encoding='utf-8',newline='\n')
        md.write_text(report(v),encoding='utf-8',newline='\n')
    print(json.dumps(dict(status=v['overall_status'],artifacts=len(v['artifacts']),critical=v['critical_local_only'],hash_mismatches=v['hash_mismatches'])))
