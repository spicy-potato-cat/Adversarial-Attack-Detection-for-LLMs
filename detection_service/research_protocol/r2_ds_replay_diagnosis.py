"""One exact first-seed replay; instrument unchanged mathematics, never search."""

import csv
from dataclasses import asdict
from datetime import datetime,timezone
import hashlib
from importlib.metadata import version
import json
import os
import platform
import sys

from detection_service.research_protocol import r2_ds_predeclare as p,ds_runtime
from detection_service.research_protocol.r2_ds_query_journal import QueryJournal

OUT=p.OUT/'diagnostics'
PRIVATE=p.ROOT/'detection_service/outputs/r2-ds-repair-001'


def first_seed():
    seed=p.parents()[0]
    text=p.private_parents()[seed['parent_sample_id']]
    with (p.R1/'r1_predictions_v1.csv').open(encoding='utf-8',newline='') as stream:
        stored=next(row for row in csv.DictReader(stream) if row['sample_id']==seed['parent_sample_id'] and row['detector_id']=='ds_v2')
    p.require(hashlib.sha256(text.encode('utf-8')).hexdigest()==seed['parent_text_sha256'],'INPUT_IDENTITY_MISMATCH')
    return seed,text,stored


def run():
    from detection_service.research_protocol.release_validation import offline
    from detection_service.research_protocol.r2_ds_generate_run import target_isolation
    from detection_service.app.detectors.semantic import calibration
    import numpy as np
    import torch
    os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_DATASETS_OFFLINE='1')
    p.require(not (OUT/'ds_baseline_replay_first_seed_v1.json').exists(),'DIAGNOSIS_ALREADY_EXISTS')
    p.preserved()
    seed,text,stored=first_seed()
    run_id='r2-ds-repair-first-seed-v1'
    captured={}
    PRIVATE.mkdir(parents=True,exist_ok=True)
    journal=QueryJournal(PRIVATE/'diagnostic_queries_v1.jsonl',run_id,'CURRENT_DIAGNOSTIC')
    with offline(),target_isolation():
        adapter=ds_runtime.accepted_ds_adapter()
        runtime=adapter._load_live()
        adapter._live=runtime
        original_score=runtime.extractor.engine.score
        original_detect=runtime.detect
        original_transform=runtime.model.transform
        def score(value):
            captured['engine_input_sha256']=hashlib.sha256(value.encode('utf-8')).hexdigest()
            result=original_score(value)
            captured['observation']=asdict(result)
            return result
        def transform(item):
            captured['feature_inputs']=item
            result=original_transform(item)
            captured['feature_dtype']=str(result.dtype)
            captured['vector']=result.tolist()
            return result
        def detect(request):
            captured['request_input_sha256']=hashlib.sha256(request.content.text.encode('utf-8')).hexdigest()
            result=original_detect(request)
            captured['native']=result.model_dump(mode='json')
            return result
        runtime.extractor.engine.score=score
        runtime.model.transform=transform
        runtime.detect=detect
        actual=journal.score(adapter,text,seed['parent_sample_id'],'BASELINE_REPLAY')
        journal.close()
        # Persist native evidence before any score/status assertion.
        p.publish(PRIVATE/'first_seed_pipeline_capture_v1.json',captured)
        ids=runtime.extractor.engine.tokenizer(text,add_special_tokens=False)['input_ids']
        identity=adapter._identity
        calibration_payload=p.files.read_json(p.ROOT/identity['calibrator_artifact'])
        raw=float(stored['raw_score'])
        calibrated=float(stored['calibrated_score'])
        value=dict(artifact_version='ds_baseline_replay_first_seed_v1',run_id=run_id,timestamp=datetime.now(timezone.utc).isoformat(),
            sample_id=seed['parent_sample_id'],source=seed['source'],lineage_id=seed['lineage_id'],
            input_sha256=seed['parent_text_sha256'],input_utf8_byte_sha256=hashlib.sha256(text.encode('utf-8')).hexdigest(),
            input_byte_length=len(text.encode('utf-8')),input_representation='Exact frozen R1 JSONL text decoded as JSON, no strip/normalization/newline rewrite',
            r1_private_input=p.files.read_json(p.R1/'r1_sample_manifest_v1.json')['private_input'],
            runtime_binding=p.files.read_json(p.ROOT/ds_runtime.BINDING),runtime_binding_sha256=p.digest(ds_runtime.BINDING),
            frozen_identity=identity,raw_live_score=actual.raw_score,raw_frozen_r1_score=raw,
            raw_absolute_delta=abs(actual.raw_score-raw) if actual.raw_score is not None else None,
            calibrated_live_score=actual.calibrated_score,calibrated_frozen_r1_score=calibrated,
            calibrated_absolute_delta=abs(actual.calibrated_score-calibrated) if actual.calibrated_score is not None else None,
            native_live_decision=actual.native_binary_prediction,native_frozen_r1_decision=int(stored['native_binary_prediction']),
            operational_live_decision=int(actual.calibrated_score>=.5585373573968287) if actual.calibrated_score is not None else None,
            operational_frozen_r1_decision=int(stored['operational_binary_prediction']),status=actual.status,error_code=actual.error_code,
            r1_coverage={key:stored[key] for key in ('input_tokens','tokens_analyzed','truncated')},
            live_coverage={key:getattr(actual,key) for key in ('input_tokens','tokens_analyzed','truncated')},
            native_input_coverage=captured.get('native',{}).get('input_coverage'),
            request_input_sha256=captured.get('request_input_sha256'),engine_input_sha256=captured.get('engine_input_sha256'),
            token_ids_sha256=hashlib.sha256(p.files.canonical_bytes(ids)).hexdigest(),token_count=len(ids),
            feature_names=runtime.model.manifest['feature_names'],feature_vector=captured.get('vector'),feature_dtype=captured.get('feature_dtype'),
            coefficient_dtype=str(runtime.model.coef.dtype),coefficient_sha256=hashlib.sha256(runtime.model.coef.tobytes()).hexdigest(),
            intercept_sha256=hashlib.sha256(runtime.model.intercept.tobytes()).hexdigest(),
            calibration_parameters=calibration_payload,calibration_dtype=str(np.asarray([actual.raw_score],dtype=float).dtype),
            raw_calibration_log_odds=float(calibration.log_odds(np.asarray([actual.raw_score]))[0]) if actual.raw_score is not None else None,
            environment=dict(python=sys.version,packages={name:version(name) for name in ('numpy','scipy','scikit-learn','torch','transformers')},
                platform=platform.platform(),device=runtime.extractor.config.device,model_dtype=str(next(runtime.extractor.engine.model.parameters()).dtype),
                torch_num_threads=torch.get_num_threads(),torch_interop_threads=torch.get_num_interop_threads(),
                deterministic_algorithms=torch.are_deterministic_algorithms_enabled(),
                variables={key:os.environ.get(key) for key in ('OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS')}),
            diagnostic_queries=journal.sequence,historical_failed_attempt_queries='UNKNOWN_EXACT_COUNT_BOUNDED_1_TO_61',
            authoritative_generation_queries=0,untargeted_queries=0,
            pipeline_capture=dict(path=(PRIVATE/'first_seed_pipeline_capture_v1.json').relative_to(p.ROOT).as_posix(),sha256=p.files.sha(PRIVATE/'first_seed_pipeline_capture_v1.json')),
            query_journal=dict(path=journal.path.relative_to(p.ROOT).as_posix(),sha256=p.files.sha(journal.path)),
            code_sha256={name:p.files.sha(p.ROOT/'detection_service/research_protocol'/name) for name in ('r2_ds_replay_diagnosis.py','r2_ds_query_journal.py')},
            tolerance=1e-12,attack_generation_started=False)
        p.publish(OUT/'ds_baseline_replay_first_seed_v1.json',value)
        print(json.dumps({key:value[key] for key in ('sample_id','status','raw_frozen_r1_score','raw_live_score','raw_absolute_delta','calibrated_frozen_r1_score','calibrated_live_score','calibrated_absolute_delta','diagnostic_queries')},indent=2),flush=True)


if __name__=='__main__':
    run()
