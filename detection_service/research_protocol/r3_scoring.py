"""Canonical full-stack replay, only after committed R3 terminal freeze."""
import json
import os
from time import perf_counter

from detection_service.research_protocol import r3_inputs as i, r3_freeze as freeze, r3_run as run
from detection_service.research_protocol.r3_generator import Journal
from detection_service.research_protocol.r3_readonly_cache import verified_reads
from detection_service.research_protocol.regime import RegimeManifest, require
from detection_service.research_protocol.operating_policy import apply_operating_policy
from detection_service.research_protocol.r0_operational import verified_policy

PREDICTIONS = i.OUT / 'r3_predictions_v1.csv'
PREDICTION_MANIFEST = i.OUT / 'r3_prediction_manifest_v1.json'


def manifest():
    value = RegimeManifest.model_validate_json(freeze.REGIME.read_bytes())
    require(value.threat_regime == 'R3_ENSEMBLE_TARGETED' and value.partition == 'INTERNAL_TEST', 'R3_SCORING_SCOPE_CONFLICT')
    for reference in value.evidence:
        require(i.p.digest(reference.path) == reference.sha256, 'R3_REGIME_EVIDENCE_DRIFT')
    return value


def score():
    from detection_service.research_protocol.release_validation import offline
    from detection_service.research_protocol import protocol_lock, protocol_patch_001
    from detection_service.research_protocol.r1_scoring import prediction_csv_bytes
    from detection_service.research_protocol.r2_ds_transfer_run import aligned
    i.gate()
    freeze_commit = i.p.committed(freeze.TERMINALS)
    i.p.committed(freeze.REGIME)
    require(not PREDICTION_MANIFEST.exists() and not (i.PRIVATE / 'scoring_receipt_v1.json').exists(), 'R3_SCORING_SINGLE_INVOCATION')
    rows, accounting = freeze.validate()
    require(i.p.files.read_json(freeze.TERMINALS)['terminals'] == rows, 'R3_FROZEN_TERMINAL_DRIFT')
    texts = {entry['metadata']['sample_id']: entry['private_generation']['text'] for entry in freeze.private_rows()}
    by_id = {row['sample_id']: row for row in rows}
    value = manifest()
    with verified_reads():
        preflight = protocol_patch_001.verify_experiment_preflight(protocol_lock.ExperimentRequest(manifest=value, bootstrap_unit='LINEAGE_CLUSTERED'))
    receipt = dict(freeze_commit=freeze_commit, started_at=run.now(), regime_sha256=i.p.files.sha(freeze.REGIME),
        scoring_code_sha256=i.p.files.sha(i.p.ROOT / 'detection_service/research_protocol/r3_scoring.py'),
        scoring_code_commit=i.p.committed(i.p.ROOT / 'detection_service/research_protocol/r3_scoring.py'),
        replay_required=True, generation_score_reuse=False, expected_calls=3 * len(rows),
        generation_calls=accounting['detector_calls'], protocol_preflight=preflight, verifier_calls=0, protected_calls=0)
    i.p.publish(i.PRIVATE / 'scoring_receipt_v1.json', receipt)
    journal = Journal(i.PRIVATE / 'scoring_queries_v1.jsonl')
    records, deltas = [], dict.fromkeys(run.d.DOMAIN, 0.0)
    timer = perf_counter()
    try:
        with offline(), verified_reads():
            oracles, identities = run.load_stack()
            require(identities == i.p.files.read_json(run.PREFLIGHT)['identities'], 'R3_SCORING_MODEL_DRIFT')
            for index, sample in enumerate(value.samples, 1):
                for label in run.d.DOMAIN:
                    journal.write('ATTEMPTED', sample_id=sample.sample_id, detector=label, candidate_id=by_id[sample.sample_id]['terminal_text_sha256'])
                    record = oracles[label].adapter.predict(texts[sample.sample_id], sample_id=sample.sample_id, truth_label=1)
                    journal.write('RETURNED', sample_id=sample.sample_id, detector=label, prediction=record.model_dump(mode='json'))
                    require(record.status == 'OK', 'R3_SCORING_NON_OK:' + str(record.error_code))
                    score = record.calibrated_score if label == 'D_S' else record.raw_score
                    expected = by_id[sample.sample_id]['terminal_scores'][label]
                    threshold = run.d.THRESHOLDS[run.d.DOMAIN.index(label)]
                    require(int(score >= threshold) == by_id[sample.sample_id]['terminal_decisions'][label], 'R3_REPLAY_DECISION_MISMATCH')
                    if label == 'D_S':
                        require(abs(score - expected) <= 1e-12, 'R3_DS_REPLAY_SCORE_MISMATCH')
                    deltas[label] = max(deltas[label], abs(score - expected))
                    records.append(record)
                if index == 1 or index % 10 == 0 or index == len(rows):
                    print(json.dumps(dict(stage='R3_POST_FREEZE_REPLAY', completed=index, total=len(rows), calls=len(records))), flush=True)
        with verified_reads():
            policy = verified_policy()
            order = dict(ds_v2=0, dm_b_v1=1, dg_v1=2)
            records.sort(key=lambda r: (r.sample_id, order[r.detector_id]))
            projected = tuple(apply_operating_policy(record, policy) for record in records)
            table = aligned(value, projected, policy)
            require(len(projected) == len(rows) * 3, 'R3_INCOMPLETE_PREDICTIONS')
            data = prediction_csv_bytes(projected)
            require(not PREDICTIONS.exists(), 'R3_PREDICTION_OVERWRITE_FORBIDDEN')
            with PREDICTIONS.open('xb') as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            require(i.read_predictions(PREDICTIONS, policy) == projected, 'R3_PREDICTION_ROUNDTRIP_CONFLICT')
    finally:
        journal.close()
    i.gate()
    i.p.publish(PREDICTION_MANIFEST, dict(artifact_version='r3_prediction_manifest_v1', status='PASS', **receipt,
        completed_at=run.now(), runtime_seconds=perf_counter()-timer, actual_calls=len(records),
        detector_ok_counts={label: len(rows) for label in run.d.DOMAIN}, coverage=table.coverage.model_dump(mode='json'),
        replay_decision_mismatches=0, max_operational_score_delta=deltas,
        prediction_sha256=i.p.files.sha(PREDICTIONS), journal_sha256=i.p.files.sha(i.PRIVATE / 'scoring_queries_v1.jsonl'),
        duplicates=0, missing=0, non_OK=0, verifier_queries=0, protected_queries=0))
    i.p.publish(i.OUT / 'r3_full_query_accounting_v1.json', dict(status='PASS',
        authoritative_generation_calls=accounting['detector_calls'], candidate_evaluations=accounting['candidate_evaluations'],
        post_freeze_replay_calls=len(records), permitted_synthetic_preflight_calls=3,
        total_model_calls=accounting['detector_calls']+len(records)+3, verifier_calls=0, protected_calls=0,
        generation_accounting_sha256=i.p.files.sha(i.OUT / 'r3_query_accounting_v1.json'),
        prediction_manifest_sha256=i.p.files.sha(PREDICTION_MANIFEST)))
    print(json.dumps(dict(status='R3_SCORING_PASS', predictions=len(records), max_score_delta=deltas)), flush=True)


if __name__ == '__main__':
    score()
