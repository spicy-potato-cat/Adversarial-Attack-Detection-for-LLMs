"""Formal disposition and one journaled preflight of the accepted D_S runtime."""

from collections import Counter
from datetime import datetime, timezone
import hashlib
import json

from detection_service.research_protocol import ds_numerical_diagnosis as numerical
from detection_service.research_protocol import r2_ds_predeclare as p, r2_ds_design as design, ds_runtime
from detection_service.research_protocol.r2_ds_query_journal import QueryJournal

START = '54529b121634e517e336e83051e0f54ddec312f2'
PATH = p.OUT/'ds_numerical_disposition_v1.json'
REPORT = p.ROOT/'reviews/DS_NUMERICAL_DISPOSITION_001.md'
PRIVATE = p.ROOT/'detection_service/outputs/ds-numerical-disposition-001'
FROZEN = ('r2_ds_generator.py', 'r2_ds_design.py', 'r2_ds_generate_run.py', 'r2_ds_query_journal.py')


def identities():
    numerical.integrity()
    for name in FROZEN:
        relative = 'detection_service/research_protocol/'+name
        p.require((p.ROOT/relative).read_bytes()==p.git('show',START+':'+relative),'FROZEN_SOURCE_DRIFT:'+name)
    seeds = p.parents()
    p.require(len(seeds)==698 and Counter(r['source'] for r in seeds)==dict(LLMAIL_INJECT=384,INJECAGENT_BASE=314), 'SEED_MEMBERSHIP_DRIFT')
    p.require(len({r['lineage_id'] for r in seeds})==94,'LINEAGE_DRIFT')
    p.require(design.THRESHOLD==.5585373573968287 and design.DESIGN['score_replay_tolerance']==1e-12,'DECISION_CONTRACT_DRIFT')
    identity = ds_runtime.accepted_ds_adapter()._identity
    p.require(identity['model_hash']=='c5e754dc8b6e88b7437e4b81016e8f8ec23d018607d4f4e78906212b2a561157','MODEL_DRIFT')
    p.require(identity['calibrator_hash']=='964cea57d98673d2026fb2f0e9d5884aec61a653e726847e0fb6ccbf36e95f23','CALIBRATOR_DRIFT')
    return dict(seed_manifest_sha256=p.files.sha(p.OUT/'r2_ds_seed_manifest_v1.json'),
        generator_contract_sha256=p.files.sha(p.OUT/'r2_ds_predeclaration_v1.json'),
        clarification_sha256=p.files.sha(p.OUT/'r2_ds_predeclaration_clarification_v1.json'),
        query_journal_schema_sha256=p.files.sha(p.OUT/'diagnostics/ds_query_journal_schema_v1.json'),
        runtime_binding_sha256=p.digest(ds_runtime.BINDING),model_sha256=identity['model_hash'],
        calibrator_sha256=identity['calibrator_hash'],feature_schema_sha256=identity['feature_schema_sha256'],
        threshold_id=design.THRESHOLD_ID,threshold=design.THRESHOLD,replay_tolerance=1e-12,
        max_queries_per_seed=61,frozen_code_sha256={n:p.files.sha(p.ROOT/'detection_service/research_protocol'/n) for n in FROZEN})


def run():
    from detection_service.research_protocol.release_validation import offline
    from detection_service.research_protocol.r2_ds_generate_run import target_isolation
    import detection_service.app.detectors.semantic.calibration
    p.require(p.git('rev-parse','HEAD').decode().strip()==START,'BLOCKED_START_STATE')
    p.require(not PATH.exists(),'DISPOSITION_ALREADY_EXISTS')
    bound = identities()
    diagnosis = numerical.read('ds_numerical_runtime_diagnosis')
    acceptance = numerical.read('ds_numerical_acceptance')
    p.require(acceptance['status']=='PASS' and all(p.files.sha(numerical.OUT/(n+'_v1.json'))==h for n,h in acceptance['artifacts'].items()),'DIAGNOSTIC_EVIDENCE_DRIFT')
    eq = numerical.read('ds_243_equivalence_recheck')
    repeated = numerical.read('ds_repeatability_first_seed')
    r1 = numerical.read('ds_r1_diagnostic_replays')
    p.require(eq['summary']['count']==243 and all(eq['summary'][k]['above_tolerance']==0 for k in ('raw','calibrated')), 'EQUIVALENCE_FAILURE')
    p.require(all(v['maximum_delta']==0 for v in repeated['combined'].values()) and r1['summary']['count']==9,'STABILITY_FAILURE')
    seed,text,stored = numerical.first()
    journal = QueryJournal(PRIVATE/'gate_queries_v1.jsonl','ds-disposition-gate-v1','CURRENT_DIAGNOSTIC')
    try:
        with offline(),target_isolation():
            adapter = ds_runtime.accepted_ds_adapter()
            actual = journal.score(adapter,text,seed['parent_sample_id'],'BASELINE_REPLAY')
    finally:
        journal.close()
    gate = dict(sample_id=seed['parent_sample_id'],status=actual.status,raw_score=actual.raw_score,
        calibrated_score=actual.calibrated_score,frozen_raw=float(stored['raw_score']),frozen_calibrated=float(stored['calibrated_score']),
        raw_delta=abs(actual.raw_score-float(stored['raw_score'])) if actual.raw_score is not None else None,
        calibrated_delta=abs(actual.calibrated_score-float(stored['calibrated_score'])) if actual.calibrated_score is not None else None,
        native_match=actual.native_binary_prediction==int(stored['native_binary_prediction']),
        operational_match=actual.calibrated_score is not None and int(actual.calibrated_score>=design.THRESHOLD)==int(stored['operational_binary_prediction']),
        diagnostic_queries=journal.sequence,environment=numerical.environment(),
        journal=dict(path=journal.path.relative_to(p.ROOT).as_posix(),sha256=p.files.sha(journal.path),
            logical_path=journal.logical_path.relative_to(p.ROOT).as_posix(),logical_sha256=p.files.sha(journal.logical_path)))
    p.publish(PRIVATE/'gate_result_v1.json',gate)
    p.require(actual.status=='OK' and gate['raw_delta']<=1e-12 and gate['calibrated_delta']<=1e-12 and gate['native_match'] and gate['operational_match'],'DS_DISPOSITION_GATE_FAILED')
    p.require(identities()==bound,'DISPOSITION_IDENTITY_DRIFT')
    prior = numerical.read('ds_baseline_replay_first_seed')
    value = dict(artifact_version='ds_numerical_disposition_v1',status='PASS',created_at=datetime.now(timezone.utc).isoformat(),
        observed_historical_anomaly=True,historical_raw_delta=prior['raw_absolute_delta'],
        historical_calibrated_delta=prior['calibrated_absolute_delta'],causal_origin='UNRESOLVED',proven_cause='NONE',
        OMP_MKL_difference='DOCUMENTED_LEAD_ONLY',accepted_anomalous_terminals=0,accepted_anomalous_scientific_outcomes=0,
        anomalous_untargeted_feedback=False,classification='NON_REPRODUCIBLE_EXECUTION_CONTEXT_NUMERICAL_ANOMALY',
        scientific_treatment=['EXCLUDE_FAILED_RUN_FROM_SCIENTIFIC_RESULTS','PRESERVE_FAILED_RUN_AS_AUDIT_EVIDENCE',
                              'USE_CURRENT_VERIFIED_FROZEN_RUNTIME_FOR_NEW_AUTHORITATIVE_RUN'],
        current_evidence=dict(equivalence_records=243,equivalence_summary=eq['summary'],affected_seed_exact=True,
            same_process_repetitions=100,cross_process_repetitions=10,diagnostic_r1_baselines=9,
            native_mismatches=0,operational_mismatches=0),
        diagnostic_calls=dict(numerical_diagnosis=362,prior_repair=1,current_disposition_gate=1,total_known=364,
            historical_failed_attempt='UNKNOWN_EXACT_COUNT_BOUNDED_1_TO_61'),
        no_protocol_relaxation=True,detector_semantics_changed=False,gate=gate,bindings=bound,
        prior_diagnosis_sha256=p.files.sha(numerical.OUT/'ds_numerical_runtime_diagnosis_v1.json'),
        historical_blocker_sha256=p.files.sha(p.OUT/'r2_ds_blocker_v1.json'),
        historical_report_sha256=p.files.sha(p.ROOT/'reviews/R2_DS_TARGETED_EVASION_RESULTS_v1.md'),
        disposition_code_sha256=p.files.sha(p.ROOT/'detection_service/research_protocol/ds_numerical_disposition.py'),
        start_commit=START,track_b=numerical.TRACK_B)
    p.publish(PATH,value)
    report = '# DS-NUMERICAL-DISPOSITION-001\n\nStatus: PASS.\n\n'
    report += 'Disposition: NON_REPRODUCIBLE_EXECUTION_CONTEXT_NUMERICAL_ANOMALY. Causal origin UNRESOLVED; proven cause NONE. The OMP/MKL difference is a documented lead only.\n\n'
    report += f"The preserved historical raw/calibrated mismatches were {value['historical_raw_delta']:.17g} / {value['historical_calibrated_delta']:.17g}. That execution produced zero accepted terminals or scientific outcomes and no D_M-B/D_G/ensemble feedback. Its exact query count remains unknown, bounded 1-61. No historical score is declared wrong or rewritten.\n\n"
    report += 'Current evidence: 243-record equivalence passes; 100 same-process and ten fresh-process repetitions are identical and exactly match the affected R1 seed; nine diagnostic R1 baselines reproduce, including long/multi-window/truncated inputs. These nine include the affected first seed. Native and operational mismatches are zero.\n\n'
    report += f"The new one-call durable preflight passed: raw delta {gate['raw_delta']}, calibrated delta {gate['calibrated_delta']}; both decisions match. Known diagnostic calls total 364: one prior repair, 362 numerical-diagnosis calls, one disposition gate. The historical failed attempt remains separately unknown.\n\n"
    report += 'Scientific treatment: exclude the failed execution from scientific results, preserve it as audit evidence, and use the currently verified frozen runtime for a new authoritative run. No tolerance, threshold, detector, generator algorithm, membership, query budget, transfer formula or bootstrap change is authorized by this disposition.\n\n'
    report += 'Restart is permissible because zero terminals/results were accepted, no transfer feedback was used, and the frozen search/population remain hash-bound. This is a disposition of an execution anomaly, without a claim of established mechanism.\n\n```json\n'+json.dumps(dict(bindings=bound,gate=gate),indent=2)+'\n```\n'
    with REPORT.open('xb') as stream:
        stream.write(report.encode('ascii'))
    print(json.dumps(dict(status='PASS',gate=gate,classification=value['classification']),indent=2))


if __name__=='__main__':
    run()
