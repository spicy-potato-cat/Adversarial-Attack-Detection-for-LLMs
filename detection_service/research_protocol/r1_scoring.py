"""Resume-safe frozen R1 scoring, available only after a committed corpus freeze."""

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
import os
from time import perf_counter

from detection_service.research_protocol import r1_corpus as c, protocol_lock, ds_runtime
from detection_service.research_protocol.adapters import primary_adapters
from detection_service.research_protocol.alignment import align_evaluation, bind_predictions
from detection_service.research_protocol.operating_policy import apply_operating_policy, OperationalPredictionRecord, native_prediction
from detection_service.research_protocol.prediction import PredictionRecord
from detection_service.research_protocol.r0_operational import verified_policy
from detection_service.research_protocol.r0_reproduction import csv_bytes
from detection_service.research_protocol.regime import RegimeManifest, require

GATE_B = c.OUT / 'r1_gate_b_acceptance_v1.json'
RUN_CODE = 'detection_service/research_protocol/r1_scoring.py'


def gate_b_anchor():
    relative=GATE_B.relative_to(c.ROOT).as_posix()
    commits=protocol_lock.git('log','--format=%H','--diff-filter=A','--',relative).decode().splitlines()
    require(len(commits)==1,'COMMITTED_GATE_B_REQUIRED')
    commit=commits[0]
    require(GATE_B.read_bytes()==protocol_lock.git('show',commit+':'+relative),'GATE_B_ACCEPTANCE_DRIFT')
    acceptance=c.files.read_json(GATE_B)
    require(acceptance['status']=='PASS','GATE_B_MUST_PASS')
    for path, expected in acceptance['sha256'].items():
        require(c.files.sha(c.ROOT/path)==expected,'GATE_B_FILE_DRIFT:'+path)
        require((c.ROOT/path).read_bytes()==protocol_lock.git('show',commit+':'+path),'GATE_B_NOT_COMMITTED:'+path)
    require((c.ROOT/RUN_CODE).read_bytes()==protocol_lock.git('show',commit+':'+RUN_CODE),'SCORING_CODE_NOT_PRECOMMITTED')
    return commit


def input_manifest():
    value=RegimeManifest.model_validate_json((c.OUT/'r1_dataset_manifest_v1.json').read_bytes())
    for ref in value.evidence:
        require(c.files.sha(c.ROOT/ref.path)==ref.sha256,'CORPUS_EVIDENCE_DRIFT')
    return value


def inputs(manifest):
    meta=c.files.read_json(c.OUT/'r1_sample_manifest_v1.json')
    path=c.ROOT/meta['private_input']['path']
    require(c.files.sha(path)==meta['private_input']['sha256'],'PRIVATE_INPUT_DRIFT')
    rows=[json.loads(line) for line in path.read_bytes().splitlines()]
    require([r['sample_id'] for r in rows]==[r.sample_id for r in manifest.samples],'PRIVATE_INPUT_MEMBERSHIP_DRIFT')
    text={r['sample_id']:r['text'] for r in rows}
    require(all(c.sha(text[r['sample_id']])==r['text_sha256'] for r in meta['samples']),'PRIVATE_INPUT_TEXT_HASH_DRIFT')
    return text


def prediction_csv_bytes(records):
    rows=[]
    for record in records:
        row=record.model_dump(mode='json')
        rows.append({k:json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False) if isinstance(v,(dict,list)) else
                     'true' if v is True else 'false' if v is False else v for k,v in row.items()})
    return csv_bytes(rows)


def read_predictions(policy=None):
    import csv
    policy=policy or verified_policy()
    rows=[]
    integers={'truth_label','native_binary_prediction','operational_binary_prediction','input_tokens','tokens_analyzed'}
    floats={'raw_score','calibrated_score','operational_threshold','latency_ms'}
    with (c.OUT/'r1_predictions_v1.csv').open(encoding='utf-8',newline='') as stream:
        for row in csv.DictReader(stream):
            data={k:None if v=='' else int(v) if k in integers else float(v) if k in floats else
                  v=='true' if k=='truncated' else json.loads(v) if k=='metadata' else v for k,v in row.items()}
            rows.append(OperationalPredictionRecord.model_validate(data,context={'operating_policy':policy}))
    return tuple(rows)


def score():
    os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_DATASETS_OFFLINE='1')
    from detection_service.research_protocol.release_validation import offline
    commit=gate_b_anchor()
    manifest=input_manifest()
    preflight=protocol_lock.verify_experiment_preflight(protocol_lock.ExperimentRequest(manifest=manifest,bootstrap_unit='LINEAGE_CLUSTERED'))
    texts=inputs(manifest)
    policy=verified_policy()
    started=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    timer=perf_counter()
    adapters=primary_adapters()
    adapters=(ds_runtime.accepted_ds_adapter(),*adapters[1:])
    predictions=[]
    run_identity=dict(gate_b_commit=commit,manifest_sha256=c.files.sha(c.OUT/'r1_dataset_manifest_v1.json'),run_code_sha256=c.files.sha(c.ROOT/RUN_CODE))
    for adapter in adapters:
        journal=c.PRIVATE/('native_'+adapter.detector_id+'_v1.jsonl')
        identity=c.PRIVATE/('native_'+adapter.detector_id+'_binding_v1.json')
        c.publish(identity,run_identity)
        previous=[PredictionRecord.model_validate_json(line) for line in journal.read_bytes().splitlines()] if journal.exists() else []
        require([r.sample_id for r in previous]==[s.sample_id for s in manifest.samples[:len(previous)]],'CHECKPOINT_MEMBERSHIP_OR_ORDER_DRIFT')
        for row in previous:
            require(row.status=='OK' and row.detector_id==adapter.detector_id,'CHECKPOINT_NON_OK_OR_DETECTOR_CONFLICT')
            adapter.validate_prediction_record(row)
        with journal.open('ab') as stream, offline():
            for index,sample in enumerate(manifest.samples[len(previous):],len(previous)+1):
                result=adapter.predict(texts[sample.sample_id],sample_id=sample.sample_id,truth_label=sample.truth_label)
                stream.write(result.deterministic_json().encode('ascii')+b'\n')
                stream.flush()
                require(result.status=='OK','STOP_NON_OK:'+adapter.detector_id+':'+sample.sample_id+':'+str(result.error_code))
                previous.append(result)
                if index%50==0 or index==1 or index==manifest.sample_count:
                    print(json.dumps(dict(stage='SCORING',detector=adapter.detector_id,completed=index,total=manifest.sample_count,elapsed_seconds=perf_counter()-timer)),flush=True)
        predictions.extend(previous)
    require(len(predictions)==manifest.sample_count*3,'INCOMPLETE_SCORING')
    gate_b_anchor()
    inputs(manifest)
    protocol_lock.verify_experiment_preflight(protocol_lock.ExperimentRequest(manifest=manifest,bootstrap_unit='LINEAGE_CLUSTERED'))
    order={a.detector_id:i for i,a in enumerate(adapters)}
    predictions.sort(key=lambda r:(r.sample_id,order[r.detector_id]))
    projected=tuple(apply_operating_policy(r,policy) for r in predictions)
    aligned=align_evaluation(manifest,projected,binding=bind_predictions(manifest),decision_view='OPERATIONAL',contracts=policy.contracts,operating_policy=policy)
    output=c.OUT/'r1_predictions_v1.csv'
    data=prediction_csv_bytes(projected)
    require(not output.exists() or output.read_bytes()==data,'REFUSE_PREDICTION_OVERWRITE')
    if not output.exists():
        with output.open('xb') as stream:
            stream.write(data)
    require(read_predictions(policy)==projected,'PREDICTION_CSV_ROUNDTRIP_CONFLICT')
    c.publish(c.OUT/'r1_prediction_manifest_v1.json',dict(artifact_version='r1_prediction_manifest_v1',status='PASS',
        **run_identity,started_at=started,completed_at=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        runtime_seconds=perf_counter()-timer,preflight=preflight,prediction_artifact_sha256=c.sha(data),
        native_journal_sha256={a.detector_id:c.files.sha(c.PRIVATE/('native_'+a.detector_id+'_v1.jsonl')) for a in adapters},
        coverage=aligned.coverage.model_dump(mode='json'),detector_ok_counts=Counter(r.detector_id for r in predictions),
        duplicates=0,score_view='prediction_operational_v1 from unchanged native prediction_v1',bootstrap_unit='LINEAGE_CLUSTERED',
        detector_changes=False,model_training=False,calibration_changes=False,threshold_changes=False))
    print(json.dumps(dict(status='GATE_C_PASS',predictions=len(predictions),runtime_seconds=perf_counter()-timer)),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--score',action='store_true',required=True)
    parser.parse_args()
    score()
