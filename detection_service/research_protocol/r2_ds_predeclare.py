"""Target-only frozen R1 projection; no model load or generation query."""

import csv
from collections import Counter
import json
import hashlib

from detection_service.research_protocol import detector_semantics as files, r2_ds_design as d
from detection_service.research_protocol.protocol_lock import git
from detection_service.research_protocol.r1_corpus import publish
from detection_service.research_protocol.regime import require

ROOT=files.ROOT
OUT=ROOT/files.OUT/'r2_ds'
PRIVATE=ROOT/'detection_service/outputs/r2-ds-001'
R1=ROOT/files.OUT/'r1'


def digest(path):
    return files.sha(ROOT/path)


def committed(path):
    relative=path.relative_to(ROOT).as_posix()
    commits=git('log','--format=%H','--diff-filter=A','--',relative).decode().splitlines()
    require(len(commits)==1,'COMMIT_REQUIRED:'+relative)
    require(path.read_bytes()==git('show',commits[0]+':'+relative),'COMMITTED_BYTES_REQUIRED:'+relative)
    return commits[0]


def parents():
    return files.read_json(OUT/'r2_ds_seed_manifest_v1.json')['parents']


def count():
    return len(parents())


def preserved():
    snapshot=files.read_json(OUT/'r2_ds_predeclaration_v1.json')['preservation_sha256']
    require(all(digest(path)==sha for path,sha in snapshot.items()),'R2_PROTOCOL_MUTATION_REQUIRED')
    require(git('rev-parse','exp/protocol-001').decode().strip()==d.PROTOCOL_HEAD,'PROTOCOL_BRANCH_DRIFT')
    require(git('rev-parse','exp/r2-dmb-001').decode().strip()==d.SOURCE_HEAD,'DMB_BRANCH_DRIFT')
    return len(snapshot)


def private_parents():
    entry=files.read_json(R1/'r1_sample_manifest_v1.json')['private_input']
    require(digest(entry['path'])==entry['sha256'],'R1_PRIVATE_INPUT_DRIFT')
    wanted={r['parent_sample_id']:r['parent_text_sha256'] for r in parents()}
    result={}
    for line in (ROOT/entry['path']).read_bytes().splitlines():
        row=json.loads(line)
        if row['sample_id'] in wanted:
            require(row['sample_id'] not in result,'DUPLICATE_PRIVATE_PARENT')
            require(hashlib.sha256(row['text'].encode('utf-8')).hexdigest()==wanted[row['sample_id']],'PARENT_TEXT_DRIFT')
            result[row['sample_id']]=row['text']
    require(len(result)==len(wanted),'MISSING_PRIVATE_PARENT')
    return result


def predeclare():
    require(git('rev-parse','HEAD').decode().strip()==d.SOURCE_HEAD,'BLOCKED_START_STATE')
    require(git('branch','--show-current').decode().strip()=='exp/r2-ds-001','DS_BRANCH_REQUIRED')
    from detection_service.research_protocol import protocol_patch_001 as patch
    from detection_service.research_protocol import r2_dmb_predeclare as prior
    from detection_service.research_protocol.release_validation import check_acceptance
    patch.verify_patch()
    prior.preserved()
    check_acceptance()
    acceptance=files.read_json(ROOT/files.OUT/'r2_dmb/r2_dmb_final_acceptance_v1.json')
    require(acceptance['status']=='PASS','DMB_ACCEPTANCE_REQUIRED')
    require(all(digest(path)==sha for path,sha in acceptance['sha256'].items()),'DMB_EVIDENCE_DRIFT')
    accepted=files.read_json(R1/'r1_gate_d_acceptance_v1.json')
    require(all(digest(path)==sha for path,sha in accepted['sha256'].items()),'R1_EVIDENCE_DRIFT')
    manifest=files.read_json(R1/'r1_dataset_manifest_v1.json')
    attacks=[s for s in manifest['samples'] if s['truth_label']==1]
    authoritative=next(r for r in files.read_json(R1/'r1_result_bundle_v1.json')['core_metrics']['individual']['detectors'] if r['detector_id']==d.DETECTOR_ID)
    target_rows={}
    with (R1/'r1_predictions_v1.csv').open(encoding='utf-8',newline='') as stream:
        reader=csv.reader(stream)
        columns=next(reader)
        indexes={k:columns.index(k) for k in ('detector_id','sample_id','truth_label','status','calibrated_score','operational_binary_prediction','operational_threshold','operational_threshold_id')}
        for values in reader:
            if values[indexes['detector_id']]!=d.DETECTOR_ID or values[indexes['truth_label']]!='1':
                continue
            row={k:values[i] for k,i in indexes.items()}
            require(row['sample_id'] not in target_rows,'DUPLICATE_DS_PARENT')
            require(row['status']=='OK','BLOCKED_R2_DS_SEED_MISMATCH')
            require(float(row['operational_threshold'])==d.THRESHOLD and row['operational_threshold_id']==d.THRESHOLD_ID,'DS_THRESHOLD_DRIFT')
            require(int(row['operational_binary_prediction'])==int(float(row['calibrated_score'])>=d.THRESHOLD),'BLOCKED_R2_DS_SEED_MISMATCH')
            target_rows[row['sample_id']]=row
    require(set(target_rows)=={s['sample_id'] for s in attacks} and len(attacks)==authoritative['attack_count']==800,'BLOCKED_R2_DS_SEED_MISMATCH')
    selected=[s for s in attacks if target_rows[s['sample_id']]['operational_binary_prediction']=='1']
    require(len(selected)==authoritative['tp'] and len(attacks)-len(selected)==authoritative['fn'],'BLOCKED_R2_DS_SEED_MISMATCH')
    metadata={s['sample_id']:s for s in files.read_json(R1/'r1_sample_manifest_v1.json')['samples']}
    rows=[dict(parent_sample_id=s['sample_id'],lineage_id=s['lineage_id'],source=s['source'],dataset_id=s['dataset_id'],
        dataset_revision=s['dataset_revision'],source_native_id=s['source_native_id'],attack_family=s['attack_family'],
        truth_label=1,target_detector=d.TARGET,parent_text_sha256=metadata[s['sample_id']]['text_sha256'],
        baseline_calibrated_score=float(target_rows[s['sample_id']]['calibrated_score']),baseline_operational_decision=1,
        threshold=d.THRESHOLD,threshold_id=d.THRESHOLD_ID) for s in selected]
    seed_hash=publish(OUT/'r2_ds_seed_manifest_v1.json',dict(artifact_version='r2_ds_seed_manifest_v1',source_head=d.SOURCE_HEAD,
        r1_attack_count=len(attacks),expected_parents=authoritative['tp'],actual_parents=len(rows),target_baseline_catches=len(rows),
        source_counts=dict(Counter(r['source'] for r in rows)),lineage_count=len({r['lineage_id'] for r in rows}),
        selection='All frozen R1 attack rows caught by D_S; only D_S prediction columns projected.',parents=rows))
    paths=git('ls-tree','-r','--name-only',d.SOURCE_HEAD).decode().splitlines()
    snapshot={path:digest(path) for path in paths if path.startswith(('artifacts/','detection_service/research_protocol/',
        'detection_service/app/','detection_service/configs/','reviews/R2_DMB','reviews/EXP_PROTOCOL_001_PATCH_001'))}
    publish(OUT/'r2_ds_predeclaration_v1.json',dict(artifact_version='r2_ds_predeclaration_v1',status='FROZEN_PRE_RUN',
        design=d.DESIGN,source_head=d.SOURCE_HEAD,seed_manifest_sha256=seed_hash,preservation_sha256=snapshot,
        parent_order='Frozen R1 attack order filtered solely by D_S operational catches.',
        model_queries_before_predeclaration=0,generation_implementation_exists=False,
        private_storage=PRIVATE.relative_to(ROOT).as_posix()))
    print(dict(status='PREDECLARED',parents=len(rows),sources=dict(Counter(r['source'] for r in rows)),lineages=len({r['lineage_id'] for r in rows})))


if __name__=='__main__':
    predeclare()
