"""Validate the new-run ledger and score only a committed terminal population."""

import argparse
from collections import Counter, defaultdict
import csv
from datetime import datetime, timezone
import json
import os
from time import perf_counter

from detection_service.research_protocol import r2_ds_authoritative_v2 as restart
from detection_service.research_protocol import r2_ds_predeclare as p, r2_ds_design as d, r2_ds_freeze as freeze


def lines(path):
    return [json.loads(line) for line in path.read_bytes().splitlines()]


def ledger():
    generator=p.files.read_json(p.OUT/'r2_ds_generator_manifest_v1.json')
    receipt=generator['query_journal']
    p.require(p.digest(receipt['path'])==receipt['sha256'] and p.digest(receipt['logical_path'])==receipt['logical_sha256'],'LEDGER_HASH_DRIFT')
    returns=lines(p.ROOT/receipt['path'])
    logical=lines(p.ROOT/receipt['logical_path'])
    p.require([r['query_sequence_number'] for r in returns]==list(range(1,len(returns)+1)),'QUERY_SEQUENCE_DRIFT')
    p.require([r['logical_query_number'] for r in logical]==list(range(1,len(logical)+1)),'LOGICAL_SEQUENCE_DRIFT')
    p.require(all(r['run_id']==restart.RUN_ID and r['target_detector']=='D_S' and r['query_scope']=='AUTHORITATIVE_GENERATION' for r in returns),'TARGET_ISOLATION_FAILURE')
    p.require(len(returns)==generator['target_generation_queries'] and len(logical)==generator['total_logical_queries'],'QUERY_TOTAL_CONFLICT')
    unique_by_seed=defaultdict(list)
    logical_by_seed=defaultdict(list)
    for row in returns:
        unique_by_seed[row['seed_sample_id']].append(row)
    for row in logical:
        logical_by_seed[row['seed_sample_id']].append(row)
    with (p.R1/'r1_predictions_v1.csv').open(encoding='utf-8',newline='') as stream:
        baseline={r['sample_id']:r for r in csv.DictReader(stream) if r['detector_id']=='ds_v2'}
    terminals=p.files.read_json(p.OUT/'r2_ds_terminal_manifest_v1.json')['terminals']
    expected=[r['parent_sample_id'] for r in p.parents()]
    p.require(list(unique_by_seed)==expected,'QUERY_SEED_ORDER_DRIFT')
    p.require([r['parent_sample_id'] for r in terminals]==expected and len(terminals)==698,'TERMINAL_SEED_ORDER_DRIFT')
    p.require(len({r['sample_id'] for r in terminals})==698,'DUPLICATE_TERMINAL_ID')
    p.require(len({r['terminal_text_sha256'] for r in terminals})==698,'DUPLICATE_TERMINAL_TEXT')
    traces=[]
    for terminal in terminals:
        sid=terminal['parent_sample_id']
        actual=unique_by_seed[sid]
        requests=logical_by_seed[sid]
        p.require(actual and actual[0]['query_role']=='BASELINE_REPLAY','BASELINE_FIRST_REQUIRED')
        first=actual[0]
        p.require(first['candidate_sha256']==terminal['parent_text_sha256'],'BASELINE_PARENT_HASH_DRIFT')
        stored=baseline[sid]
        raw_delta=abs(first['raw_score']-float(stored['raw_score']))
        cal_delta=abs(first['calibrated_score']-float(stored['calibrated_score']))
        p.require(raw_delta<=1e-12 and cal_delta<=1e-12 and first['operational_decision']==int(stored['operational_binary_prediction']) and first['native_decision']==int(stored['native_binary_prediction']),'BASELINE_REPLAY_FAILURE')
        p.require(len(actual)==terminal['unique_model_queries']<=61 and len(requests)==terminal['logical_queries'],'SEED_QUERY_BUDGET_DRIFT')
        p.require([r['candidate_sha256'] for r in requests if not r['cached']]==[r['candidate_sha256'] for r in actual],'LOGICAL_RETURN_DRIFT')
        p.require(len({r['candidate_sha256'] for r in actual})==len(actual),'DUPLICATE_UNIQUE_CALL')
        p.require(all(r['status']=='OK' for r in actual),'GENERATION_NON_OK')
        traces.append(dict(sample_id=sid,raw_delta=raw_delta,calibrated_delta=cal_delta,queries=len(actual),logical_queries=len(requests)))
    return dict(status='PASS',run_id=restart.RUN_ID,baseline_replays=698,baseline_replay_violations=0,
        max_raw_delta=max(r['raw_delta'] for r in traces),max_calibrated_delta=max(r['calibrated_delta'] for r in traces),
        unique_model_queries=len(returns),logical_queries=len(logical),max_queries_per_seed=max(r['queries'] for r in traces),
        duplicate_terminal_ids=0,duplicate_terminal_text_hashes=0,
        roles=dict(Counter(r['query_role'] for r in returns)),rows=traces,journal=receipt,
        forbidden_generation_queries=dict(D_M_B=0,D_G=0,ensemble=0))


def freeze_run():
    p.publish(p.OUT/'r2_ds_query_accounting_v2.json',ledger())
    manifest=freeze.regime_manifest()
    p.publish(p.OUT/'r2_ds_regime_manifest_v1.json',manifest.model_dump(mode='json'))
    result,_=freeze.validate()
    p.publish(p.OUT/'r2_ds_freeze_acceptance_v1.json',result)
    print(json.dumps({k:v for k,v in result.items() if k!='sha256'},indent=2))


def durable_native(stream,row):
    stream.write(row.deterministic_json().encode('ascii')+b'\n')
    stream.flush()
    os.fsync(stream.fileno())


def score_run():
    from detection_service.research_protocol import r2_ds_transfer_run as scoring
    from detection_service.research_protocol import protocol_lock,protocol_patch_001,ds_runtime
    from detection_service.research_protocol.adapters import primary_adapters
    from detection_service.research_protocol.r1_scoring import prediction_csv_bytes
    from detection_service.research_protocol.operating_policy import apply_operating_policy
    from detection_service.research_protocol.release_validation import offline
    from detection_service.research_protocol.r2_ds_query_journal import QueryJournal
    freeze_commit,private=freeze.transfer_gate()
    p.require(not (p.OUT/'r2_ds_prediction_manifest_v1.json').exists(),'PREDICTIONS_ALREADY_ACCEPTED')
    ledger()
    value=scoring.manifest()
    protocol_patch_001.verify_experiment_preflight(protocol_lock.ExperimentRequest(manifest=value,bootstrap_unit='LINEAGE_CLUSTERED'))
    texts={r['metadata']['sample_id']:r['private_generation']['text'] for r in private}
    targets={r['metadata']['sample_id']:r['metadata'] for r in private}
    adapters=primary_adapters()
    adapters=(ds_runtime.accepted_ds_adapter(),*adapters[1:])
    policy=scoring.verified_policy()
    started=datetime.now(timezone.utc).isoformat()
    timer=perf_counter()
    records=[]
    deltas=[]
    query=QueryJournal(restart.PRIVATE/'final_replay_queries_v2.jsonl',restart.RUN_ID+'-FINAL-REPLAY','REPLAY_VALIDATION')
    try:
        for adapter in adapters:
            path=restart.PRIVATE/('transfer_native_'+adapter.detector_id+'_v2.jsonl')
            with path.open('xb') as stream,offline():
                for index,sample in enumerate(value.samples,1):
                    text=texts[sample.sample_id]
                    if adapter.detector_id==d.DETECTOR_ID:
                        row=query.score(adapter,text,sample.sample_id,'REPLAY_VALIDATION')
                    else:
                        row=adapter.predict(text,sample_id=sample.sample_id,truth_label=1)
                    durable_native(stream,row)
                    p.require(row.status=='OK','TRANSFER_NON_OK:'+adapter.detector_id+':'+str(row.error_code))
                    if adapter.detector_id==d.DETECTOR_ID:
                        target=targets[sample.sample_id]
                        delta=abs(row.calibrated_score-target['terminal_calibrated_score'])
                        p.require(delta<=1e-12 and int(row.calibrated_score>=d.THRESHOLD)==target['terminal_decision'],'BLOCKED_DS_TERMINAL_REPLAY_MISMATCH')
                        deltas.append(delta)
                    records.append(row)
                    if index%50==0 or index==1:
                        print(json.dumps(dict(stage='POST_FREEZE_TRANSFER',detector=adapter.detector_id,completed=index,total=698)),flush=True)
    except BaseException as exc:
        returned_counts={a.detector_id:len(lines(restart.PRIVATE/('transfer_native_'+a.detector_id+'_v2.jsonl')))
            for a in adapters if (restart.PRIVATE/('transfer_native_'+a.detector_id+'_v2.jsonl')).exists()}
        p.publish(p.OUT/'r2_ds_transfer_interruption_v2.json',dict(status='BLOCKED',error=str(exc),freeze_commit=freeze_commit,
            returned_canonical_records=sum(returned_counts.values()),returned_records_by_detector=returned_counts,
            accepted_partial_predictions=False,ds_final_replay_queries=query.sequence,
            completed_predictions_by_detector=dict(Counter(r.detector_id for r in records))))
        raise
    finally:
        query.close()
    p.require(len(records)==2094,'INCOMPLETE_R2_SCORING')
    p.preserved()
    records.sort(key=lambda r:(r.sample_id,('ds_v2','dm_b_v1','dg_v1').index(r.detector_id)))
    projected=tuple(apply_operating_policy(r,policy) for r in records)
    table=scoring.aligned(value,projected,policy)
    path=p.OUT/'r2_ds_predictions_v1.csv'
    with path.open('xb') as stream:
        stream.write(prediction_csv_bytes(projected))
    p.require(scoring.read_predictions(policy)==projected,'PREDICTION_ROUNDTRIP_CONFLICT')
    p.publish(p.OUT/'r2_ds_prediction_manifest_v1.json',dict(artifact_version='r2_ds_prediction_manifest_v1',status='PASS',run_id=restart.RUN_ID,
        freeze_commit=freeze_commit,scoring_code_commit=p.committed(p.ROOT/'detection_service/research_protocol/r2_ds_completion_v2.py'),
        started_at=started,completed_at=datetime.now(timezone.utc).isoformat(),runtime_seconds=perf_counter()-timer,
        manifest_sha256=p.files.sha(p.OUT/'r2_ds_regime_manifest_v1.json'),prediction_sha256=p.files.sha(path),
        expected_predictions=2094,actual_predictions=2094,detector_ok_counts={a.detector_id:698 for a in adapters},
        coverage=table.coverage.model_dump(mode='json'),duplicates=0,ds_max_calibrated_score_delta=max(deltas),ds_operational_mismatches=0,
        native_journal_sha256={a.detector_id:p.files.sha(restart.PRIVATE/('transfer_native_'+a.detector_id+'_v2.jsonl')) for a in adapters},
        final_replay_query_journal=dict(path=query.path.relative_to(p.ROOT).as_posix(),sha256=p.files.sha(query.path),queries=query.sequence),
        detector_changes=False,threshold_changes=False,model_training=False))
    print(json.dumps(dict(status='R2_TRANSFER_SCORING_PASS',predictions=2094)),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode',required=True,choices=('freeze','score'))
    mode=parser.parse_args().mode
    (freeze_run if mode=='freeze' else score_run)()
