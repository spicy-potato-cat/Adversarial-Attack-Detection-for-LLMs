"""Transfer inference only after an accepted committed R2 terminal freeze."""

import argparse
import csv
from datetime import datetime,timezone
import json
import os
from time import perf_counter

from detection_service.research_protocol import r2_ds_predeclare as p,r2_ds_design as d,r2_ds_freeze as freeze
from detection_service.research_protocol.regime import RegimeManifest,require
from detection_service.research_protocol.operating_policy import apply_operating_policy,OperationalPredictionRecord
from detection_service.research_protocol.r0_operational import verified_policy


def manifest():
    value=RegimeManifest.model_validate_json((p.OUT/'r2_ds_regime_manifest_v1.json').read_bytes())
    for ref in value.evidence:
        require(p.digest(ref.path)==ref.sha256,'R2_MANIFEST_EVIDENCE_DRIFT')
    return value


def read_predictions(policy=None):
    policy=policy or verified_policy()
    integers={'truth_label','native_binary_prediction','operational_binary_prediction','input_tokens','tokens_analyzed'}
    floats={'raw_score','calibrated_score','operational_threshold','latency_ms'}
    records=[]
    with (p.OUT/'r2_ds_predictions_v1.csv').open(encoding='utf-8',newline='') as stream:
        for row in csv.DictReader(stream):
            data={k:None if v=='' else int(v) if k in integers else float(v) if k in floats else
                v=='true' if k=='truncated' else json.loads(v) if k=='metadata' else v for k,v in row.items()}
            records.append(OperationalPredictionRecord.model_validate(data,context={'operating_policy':policy}))
    return tuple(records)


def aligned(value,records,policy):
    from detection_service.research_protocol.alignment import align_evaluation,bind_predictions
    return align_evaluation(value,records,binding=bind_predictions(value),decision_view='OPERATIONAL',contracts=policy.contracts,operating_policy=policy)


def score():
    freeze_commit,private=freeze.transfer_gate()
    require(not (p.OUT/'r2_ds_prediction_manifest_v1.json').exists(),'SCORING_ALREADY_ACCEPTED')
    from detection_service.research_protocol import protocol_lock,protocol_patch_001,ds_runtime
    from detection_service.research_protocol.adapters import primary_adapters
    from detection_service.research_protocol.prediction import PredictionRecord
    from detection_service.research_protocol.r1_scoring import prediction_csv_bytes
    from detection_service.research_protocol.release_validation import offline
    os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_DATASETS_OFFLINE='1')
    value=manifest()
    request=protocol_lock.ExperimentRequest(manifest=value,bootstrap_unit='LINEAGE_CLUSTERED')
    protocol_patch_001.verify_experiment_preflight(request)
    texts={r['metadata']['sample_id']:r['private_generation']['text'] for r in private}
    terminal={r['metadata']['sample_id']:r['metadata'] for r in private}
    adapters=primary_adapters()
    adapters=(ds_runtime.accepted_ds_adapter(),*adapters[1:])
    policy=verified_policy()
    started=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    timer=perf_counter()
    records=[]
    for adapter in adapters:
        path=p.PRIVATE/('transfer_native_'+adapter.detector_id+'_v1.jsonl')
        binding=dict(freeze_commit=freeze_commit,manifest_sha256=p.files.sha(p.OUT/'r2_ds_regime_manifest_v1.json'),
            run_code_sha256=p.files.sha(p.ROOT/'detection_service/research_protocol/r2_ds_transfer_run.py'))
        p.publish(p.PRIVATE/('transfer_'+adapter.detector_id+'_binding_v1.json'),binding)
        previous=[PredictionRecord.model_validate_json(line) for line in path.read_bytes().splitlines()] if path.exists() else []
        require([r.sample_id for r in previous]==[s.sample_id for s in value.samples[:len(previous)]],'TRANSFER_CHECKPOINT_CONFLICT')
        for record in previous:
            require(record.status=='OK' and record.detector_id==adapter.detector_id,'TRANSFER_CHECKPOINT_NON_OK')
            adapter.validate_prediction_record(record)
        with path.open('ab') as stream,offline():
            for index,sample in enumerate(value.samples[len(previous):],len(previous)+1):
                row=adapter.predict(texts[sample.sample_id],sample_id=sample.sample_id,truth_label=1)
                require(row.status=='OK','TRANSFER_NON_OK:'+adapter.detector_id+':'+str(row.error_code))
                if adapter.detector_id==d.DETECTOR_ID:
                    target=terminal[sample.sample_id]
                    require(abs(row.calibrated_score-target['terminal_calibrated_score'])<=1e-12 and int(row.calibrated_score>=d.THRESHOLD)==target['terminal_decision'],'BLOCKED_DS_RESCORING_MISMATCH')
                stream.write(row.deterministic_json().encode('ascii')+b'\n')
                stream.flush()
                previous.append(row)
                if index%50==0 or index==1:
                    print(json.dumps(dict(stage='POST_FREEZE_TRANSFER',detector=adapter.detector_id,completed=index,total=p.count())),flush=True)
        records.extend(previous)
    require(len(records)==3*p.count(),'INCOMPLETE_R2_SCORING')
    p.preserved()
    records.sort(key=lambda r:(r.sample_id,('ds_v2','dm_b_v1','dg_v1').index(r.detector_id)))
    projected=tuple(apply_operating_policy(r,policy) for r in records)
    table=aligned(value,projected,policy)
    path=p.OUT/'r2_ds_predictions_v1.csv'
    data=prediction_csv_bytes(projected)
    require(not path.exists() or path.read_bytes()==data,'REFUSE_PREDICTION_OVERWRITE')
    if not path.exists():
        with path.open('xb') as stream:
            stream.write(data)
    require(read_predictions(policy)==projected,'R2_CSV_ROUNDTRIP_CONFLICT')
    target_rows=[r for r in records if r.detector_id==d.DETECTOR_ID]
    deltas=[abs(r.calibrated_score-terminal[r.sample_id]['terminal_calibrated_score']) for r in target_rows]
    p.publish(p.OUT/'r2_ds_prediction_manifest_v1.json',dict(artifact_version='r2_ds_prediction_manifest_v1',status='PASS',
        freeze_commit=freeze_commit,scoring_code_commit=p.committed(p.ROOT/'detection_service/research_protocol/r2_ds_transfer_run.py'),
        started_at=started,completed_at=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),runtime_seconds=perf_counter()-timer,
        manifest_sha256=p.files.sha(p.OUT/'r2_ds_regime_manifest_v1.json'),prediction_sha256=p.files.sha(path),
        expected_predictions=3*p.count(),actual_predictions=3*p.count(),detector_ok_counts={a.detector_id:p.count() for a in adapters},
        coverage=table.coverage.model_dump(mode='json'),duplicates=0,ds_max_calibrated_score_delta=max(deltas),ds_operational_mismatches=0,
        native_journal_sha256={a.detector_id:p.files.sha(p.PRIVATE/('transfer_native_'+a.detector_id+'_v1.jsonl')) for a in adapters},
        detector_changes=False,threshold_changes=False,model_training=False))
    print(json.dumps(dict(status='R2_TRANSFER_SCORING_PASS',predictions=3*p.count())),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--score',action='store_true',required=True)
    parser.parse_args()
    score()
