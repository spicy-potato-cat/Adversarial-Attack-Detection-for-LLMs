"""Freeze target-only R1 parent projection and R2 design without detector calls."""

import csv
from collections import Counter
from pathlib import Path

from detection_service.research_protocol import detector_semantics as files, r2_dmb_design as d
from detection_service.research_protocol.r1_corpus import publish
from detection_service.research_protocol.protocol_lock import git
from detection_service.research_protocol.regime import require

ROOT = files.ROOT
OUT = ROOT / files.OUT / 'r2_dmb'
PRIVATE = ROOT / 'detection_service/outputs/r2-dmb-001'
R1 = ROOT / files.OUT / 'r1'


def digest(path):
    return files.sha(ROOT/path)


def preserved():
    snapshot=files.read_json(OUT/'r2_dmb_predeclaration_v1.json')['preservation_sha256']
    for path,expected in snapshot.items():
        require(digest(path)==expected,'R2_PROTOCOL_MUTATION_REQUIRED:'+path)
    require(git('rev-parse','exp/protocol-001').decode().strip()==d.SOURCE_HEAD,'SOURCE_BRANCH_DRIFT')
    return len(snapshot)


def committed(path):
    relative=path.relative_to(ROOT).as_posix()
    commits=git('log','--format=%H','--diff-filter=A','--',relative).decode().splitlines()
    require(len(commits)==1,'COMMIT_REQUIRED:'+relative)
    require(path.read_bytes()==git('show',commits[0]+':'+relative),'COMMITTED_BYTES_REQUIRED:'+relative)
    return commits[0]


def parents():
    return files.read_json(OUT/'r2_dmb_seed_manifest_v1.json')['parents']


def private_parents():
    manifest=files.read_json(R1/'r1_sample_manifest_v1.json')
    entry=manifest['private_input']
    require(digest(entry['path'])==entry['sha256'],'R1_PRIVATE_INPUT_DRIFT')
    import json
    texts={row['sample_id']:row['text'] for row in map(json.loads,(ROOT/entry['path']).read_bytes().splitlines())}
    result={p['parent_sample_id']:texts[p['parent_sample_id']] for p in parents()}
    import hashlib
    require(all(hashlib.sha256(result[p['parent_sample_id']].encode('utf-8')).hexdigest()==p['parent_text_sha256'] for p in parents()),'R2_PARENT_HASH_DRIFT')
    return result


def predeclare():
    require(git('rev-parse','HEAD').decode().strip()==d.SOURCE_HEAD,'PREDECLARATION_START_HEAD')
    require(git('branch','--show-current').decode().strip()=='exp/r2-dmb-001','R2_BRANCH_REQUIRED')
    require(git('rev-parse','origin/exp/protocol-001').decode().strip()==d.SOURCE_HEAD,'REMOTE_R1_DRIFT')
    acceptance=files.read_json(R1/'r1_gate_d_acceptance_v1.json')
    require(acceptance['status']=='PASS','R1_ACCEPTANCE_REQUIRED')
    for path,expected in acceptance['sha256'].items():
        require(digest(path)==expected,'R1_EVIDENCE_HASH_DRIFT:'+path)
    target_results=files.read_json(R1/'r1_result_bundle_v1.json')['core_metrics']['individual']['detectors']
    target=next(row for row in target_results if row['detector_id']==d.DETECTOR_ID)
    require(target['attack_count']==target['tp']==800 and target['fn']==0,'BLOCKED_R2_SEED_MISMATCH')
    manifest=files.read_json(R1/'r1_dataset_manifest_v1.json')
    samples=[s for s in manifest['samples'] if s['truth_label']==1]
    metadata={s['sample_id']:s for s in files.read_json(R1/'r1_sample_manifest_v1.json')['samples']}
    # Non-target rows are never decoded into score objects or accessed by selection.
    target_rows={}
    with (R1/'r1_predictions_v1.csv').open(encoding='utf-8',newline='') as stream:
        reader=csv.reader(stream)
        columns=next(reader)
        indexes={k:columns.index(k) for k in ('detector_id','sample_id','truth_label','raw_score','operational_binary_prediction','operational_threshold','operational_threshold_id')}
        for values in reader:
            if values[indexes['detector_id']]!=d.DETECTOR_ID:
                continue
            if values[indexes['truth_label']]!='1':
                continue
            row={k:values[i] for k,i in indexes.items()}
            require(row['sample_id'] not in target_rows,'DUPLICATE_TARGET_PARENT')
            require(float(row['operational_threshold'])==d.THRESHOLD and row['operational_threshold_id']==d.THRESHOLD_ID,'TARGET_THRESHOLD_DRIFT')
            require(row['operational_binary_prediction']=='1' and float(row['raw_score'])>=d.THRESHOLD,'BLOCKED_R2_SEED_MISMATCH')
            target_rows[row['sample_id']]=row
    require(len(samples)==len(target_rows)==800,'BLOCKED_R2_SEED_MISMATCH')
    rows=[]
    for s in samples:
        row=target_rows[s['sample_id']]
        rows.append(dict(parent_sample_id=s['sample_id'],lineage_id=s['lineage_id'],source=s['source'],
            dataset_id=s['dataset_id'],dataset_revision=s['dataset_revision'],source_native_id=s['source_native_id'],
            attack_family=s['attack_family'],truth_label=1,target_detector=d.TARGET,
            parent_text_sha256=metadata[s['sample_id']]['text_sha256'],baseline_raw_score=float(row['raw_score']),
            baseline_operational_decision=1,threshold=d.THRESHOLD,threshold_id=d.THRESHOLD_ID))
    seed=dict(artifact_version='r2_dmb_seed_manifest_v1',source_head=d.SOURCE_HEAD,
        expected_parents=800,actual_parents=len(rows),target_baseline_catches=800,
        source_counts=dict(Counter(p['source'] for p in rows)),lineage_count=len({p['lineage_id'] for p in rows}),
        selection='All frozen R1 attack rows caught by D_M-B; no untargeted decisions consulted.',parents=rows)
    seed_hash=publish(OUT/'r2_dmb_seed_manifest_v1.json',seed)
    paths=git('ls-tree','-r','--name-only',d.SOURCE_HEAD).decode().splitlines()
    frozen={p:digest(p) for p in paths if p.startswith(('artifacts/research_protocol/','artifacts/models/','detection_service/app/',
        'detection_service/configs/','detection_service/research_protocol/','artifacts/quality/'))}
    publish(OUT/'r2_dmb_predeclaration_v1.json',dict(artifact_version='r2_dmb_predeclaration_v1',status='FROZEN_PRE_RUN',
        design=d.DESIGN,source_head=d.SOURCE_HEAD,seed_manifest_sha256=seed_hash,
        parent_order='Frozen R1 attack manifest order; no subsampling.',preservation_sha256=frozen,
        private_storage=PRIVATE.relative_to(ROOT).as_posix(),model_queries_before_predeclaration=0,
        generation_implementation_exists=False,accepted_generation_artifact_exists=False,
        access_boundary='Predeclaration projects only D_M-B rows. Generation consumes only seed metadata and parent text; R1 untargeted score access prohibited.'))
    print(dict(status='PREDECLARED',parents=800,sources=seed['source_counts'],lineages=seed['lineage_count'],preservation_files=len(frozen)))


if __name__=='__main__':
    predeclare()
