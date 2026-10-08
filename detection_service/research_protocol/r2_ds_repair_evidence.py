"""Read-only deterministic pipeline comparison; never rerun the reference LM."""

import hashlib
import json
import numpy as np
from scipy.special import expit

from detection_service.research_protocol import r2_ds_replay_diagnosis as diag,r2_ds_predeclare as p

HISTORICAL_QUERIES='UNKNOWN_EXACT_COUNT_BOUNDED_1_TO_61'
TOLERANCE=1e-12


def compare(stored,live):
    return dict(raw_delta=abs(live['raw_score']-stored['raw_score']),
        calibrated_delta=abs(live['calibrated_score']-stored['calibrated_score']),
        native_match=live['native_decision']==stored['native_decision'],
        operational_match=live['operational_decision']==stored['operational_decision'])


def summarize(rows,expected=698):
    valid=len(rows)==expected and len({r['sample_id'] for r in rows})==expected
    raw=[r['raw_delta'] for r in rows]
    cal=[r['calibrated_delta'] for r in rows]
    passed=valid and all(r['raw_delta']<=TOLERANCE and r['calibrated_delta']<=TOLERANCE and r['native_match'] and r['operational_match'] for r in rows)
    return dict(status='PASS' if passed else 'FAIL',expected=expected,replayed=len(rows),
        max_raw_delta=max(raw,default=None),max_calibrated_delta=max(cal,default=None),
        median_raw_delta=float(np.median(raw)) if raw else None,median_calibrated_delta=float(np.median(cal)) if cal else None,
        calibrated_above_tolerance=sum(v>TOLERANCE for v in cal),
        native_mismatches=sum(not r['native_match'] for r in rows),operational_mismatches=sum(not r['operational_match'] for r in rows))


def restart_gate(audit,root_cause,seed_order,requested_start):
    p.require(root_cause not in ('UNKNOWN','FROZEN_R1_EVIDENCE_DEFECT'),'R2_DS_BASELINE_REPLAY_STILL_UNRESOLVED')
    p.require(audit['status']=='PASS' and audit['replayed']==698,'R2_DS_BASELINE_REPLAY_STILL_UNRESOLVED')
    p.require(requested_start==seed_order[0],'FULL_RESTART_FROM_SEED_ONE_REQUIRED')


def trace():
    value=p.files.read_json(diag.OUT/'ds_baseline_replay_first_seed_v1.json')
    capture=p.files.read_json(p.ROOT/value['pipeline_capture']['path'])
    p.require(p.digest(value['pipeline_capture']['path'])==value['pipeline_capture']['sha256'],'CAPTURE_DRIFT')
    metadata=p.files.read_json(p.R1/'r1_prediction_manifest_v1.json')
    native_path=p.ROOT/'detection_service/outputs/r1-clearance-001/native_ds_v2_v1.jsonl'
    p.require(p.files.sha(native_path)==metadata['native_journal_sha256']['ds_v2'],'R1_NATIVE_JOURNAL_DRIFT')
    stored=next(json.loads(line) for line in native_path.read_bytes().splitlines() if json.loads(line)['sample_id']==value['sample_id'])
    p.require(stored['raw_score']==value['raw_frozen_r1_score'] and stored['calibrated_score']==value['calibrated_frozen_r1_score'],'R1_CSV_NATIVE_CONFLICT')
    identity=value['frozen_identity']
    model=p.files.read_json(p.ROOT/identity['model_artifact_path'])
    coefficients=np.asarray(model['coefficients'],dtype=np.float64)
    intercept=np.asarray(model['intercept'],dtype=np.float64)
    vector=np.asarray(value['feature_vector'],dtype=np.float64)
    reconstructed_raw=float(expit((vector[None,:]@coefficients.T).ravel()+intercept[0])[0])
    calibration=value['calibration_parameters']
    def calibrated(raw):
        clipped=np.clip(raw,calibration['epsilon'],1-calibration['epsilon'])
        return float(expit(calibration['slope']*(np.log(clipped)-np.log1p(-clipped))+calibration['intercept']))
    stages={
        'A_exact_input_bytes':'MATCH: frozen input file hash, seed text hash, request hash and engine-input hash identical',
        'B_raw_text_selection':'MATCH: unchanged R1 JSONL text field; validator rejects blank text without changing text',
        'C_tokenizer_identity':'MATCH_FROZEN_CONFIGURATION', 'D_tokenizer_revision':'MATCH_FROZEN_SNAPSHOT_HASHES',
        'E_token_ids':'LIVE_HASH_RECORDED; R1 IDs not retained, historical IDs only reconstructable from frozen text/tokenizer, not observed',
        'F_token_count':'MATCH: 101 input tokens and 100 next-token targets',
        'G_prompt_truncation_and_windows':'MATCH_COUNTS: no truncation; frozen recipe implies one reference chunk [0,101)',
        'H_reference_revision':'MATCH_FROZEN_REVISION_AND_WEIGHTS',
        'I_perplexity_inputs':'LIVE_CAPTURED; R1 token-level evidence not retained',
        'J_sliding_windows':'FROZEN_RECIPE_RECONSTRUCTION: single 100-target window, width128/stride64; R1 window telemetry absent',
        'K_token_surprisals':'LIVE_CAPTURED; HISTORICAL_NOT_STORED',
        'L_26_feature_vector':'LIVE_CAPTURED; HISTORICAL_NOT_STORED',
        'M_feature_order_schema':'MATCH_FROZEN_SCHEMA_AND_CODE',
        'N_feature_dtype':'LIVE_FLOAT64; frozen implementation specifies float64; historical runtime dtype telemetry absent',
        'O_lr_coefficients_intercept':'MATCH_FROZEN_MODEL_HASH; float64 byte hashes recorded',
        'P_raw_probability':'FIRST_OBSERVED_SCORE_DIVERGENCE: causal earlier divergence cannot be localized without R1 intermediates',
        'Q_raw_log_odds':'RECONSTRUCTED_FROM_EACH_RAW_PROBABILITY: input differs; no different transform observed',
        'R_clipping':'MATCH_FROZEN_EPSILON_1e-12; neither first-seed raw probability is at clipping boundary',
        'S_platt_parameters':'MATCH_FROZEN_CALIBRATOR_HASH',
        'T_calibrated_score':'DIFFERENT_BECAUSE_RAW_INPUT_DIFFERS; frozen formula reconstructs both stored R1 and live calibrated scores',
        'U_threshold_comparison':'MATCH_NATIVE_AND_OPERATIONAL_DECISIONS; does not waive score tolerance'}
    result=dict(status='UNRESOLVED',primary_root_cause='UNKNOWN',
        secondary_contributors=['Historical R1 intermediate telemetry and exact numerical environment are not retained; this is a diagnostic evidence limitation, not a proven numerical cause.'],
        first_observed_divergence='P_RAW_CLASS1_PROBABILITY',first_causal_divergence='UNKNOWN_WITHIN_REFERENCE_INFERENCE_OR_FEATURE_PATH',
        stages=stages,raw_reconstruction_delta=abs(reconstructed_raw-value['raw_live_score']),
        r1_calibration_reconstruction_delta=abs(calibrated(value['raw_frozen_r1_score'])-value['calibrated_frozen_r1_score']),
        live_calibration_reconstruction_delta=abs(calibrated(value['raw_live_score'])-value['calibrated_live_score']),
        r1_native_journal_sha256=p.files.sha(native_path),
        historical_numerical_environment='NOT_RECORDED_IN_R1_SCORING_MANIFEST; training-package versions match replay, but do not establish R1 process configuration',
        environmental_variation_proven=False,tolerance_changed=False,additional_lm_queries=0,
        generation_allowed=False,final_verdict='R2_DS_BASELINE_REPLAY_STILL_UNRESOLVED')
    p.publish(diag.OUT/'ds_baseline_pipeline_comparison_v1.json',result)
    p.publish(diag.OUT/'ds_baseline_replay_all_seeds_v1.json',dict(status='NOT_RUN',expected_seeds=698,replayed=0,
        reason='First-seed root cause UNKNOWN; authorization Section 13 requires STOP before all-seed audit or restart.',
        maximum_raw_delta=None,maximum_calibrated_delta=None,median_raw_delta=None,median_calibrated_delta=None,
        calibrated_above_tolerance=None,native_mismatches=None,operational_mismatches=None,
        audit_queries=0,authoritative_restart_attack_queries=0))
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    trace()
