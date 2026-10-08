"""Append-only, fsync-backed model-return receipts independent of later gates."""

from datetime import datetime,timezone
import hashlib
import json
import os

SCHEMA_VERSION='r2_ds_query_journal_v1'
ROLES=('BASELINE_REPLAY','SALIENCY_PROBE','GREEDY_VARIANT','PADDING_VARIANT','GLOBAL_VARIANT','REPLAY_VALIDATION')


class QueryJournal:
    def __init__(self,path,run_id,scope):
        self.path=path
        self.run_id=run_id
        self.scope=scope
        self.sequence=0
        self.logical_queries=0
        path.parent.mkdir(parents=True,exist_ok=True)
        self.stream=path.open('xb',buffering=0)
        self.logical_path=path.with_name(path.stem+'_logical.jsonl')
        self.logical_stream=self.logical_path.open('xb',buffering=0)

    def logical(self,text,seed_sample_id,role,cached=False):
        self.logical_queries+=1
        record=dict(run_id=self.run_id,query_scope=self.scope,seed_sample_id=seed_sample_id,
            logical_query_number=self.logical_queries,query_role=role,cached=cached,
            candidate_sha256=hashlib.sha256(text.encode('utf-8')).hexdigest())
        encoded=(json.dumps(record,sort_keys=True)+'\n').encode('ascii')
        view=memoryview(encoded)
        while view:
            size=self.logical_stream.write(view)
            if not size:
                raise OSError('LOGICAL_RECEIPT_WRITE_FAILED')
            view=view[size:]
        os.fsync(self.logical_stream.fileno())

    def returned(self,text,row,seed_sample_id,role):
        if role not in ROLES:
            raise ValueError('UNKNOWN_QUERY_ROLE')
        data=text.encode('utf-8',errors='strict')
        digest=hashlib.sha256(data).hexdigest()
        self.sequence+=1
        record=dict(schema_version=SCHEMA_VERSION,run_id=self.run_id,query_scope=self.scope,
            seed_sample_id=seed_sample_id,query_sequence_number=self.sequence,query_role=role,
            candidate_id=digest,candidate_sha256=digest,candidate_byte_length=len(data),target_detector='D_S',
            raw_score=row.raw_score,calibrated_score=row.calibrated_score,status=row.status,error_code=row.error_code,
            native_decision=row.native_binary_prediction,
            operational_decision=int(row.calibrated_score>=.5585373573968287) if row.calibrated_score is not None else None,
            input_tokens=row.input_tokens,tokens_analyzed=row.tokens_analyzed,truncated=row.truncated,
            timestamp=datetime.now(timezone.utc).isoformat())
        encoded=(json.dumps(record,sort_keys=True,ensure_ascii=True,allow_nan=False)+'\n').encode('ascii')
        view=memoryview(encoded)
        while view:
            size=self.stream.write(view)
            if not size:
                raise OSError('QUERY_RECEIPT_WRITE_FAILED')
            view=view[size:]
        os.fsync(self.stream.fileno())
        return record

    def score(self,adapter,text,seed_sample_id,role,logical_already_logged=False):
        if not logical_already_logged:
            self.logical(text,seed_sample_id,role)
        row=adapter.predict(text,sample_id=seed_sample_id,truth_label=1)
        self.returned(text,row,seed_sample_id,role)
        return row

    def close(self):
        self.stream.close()
        self.logical_stream.close()
