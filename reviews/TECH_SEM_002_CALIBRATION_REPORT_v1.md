# TECH-SEM-002 Calibration Report v1

Date: 2026-10-01. TECH-SEM-002-CALIBRATION: PASS. Regression and real-model acceptance gates passed.
Target: semantic_finetuned / dm_b_v1. Calibration version: dm_b_v1_cal_v1.
Method: platt_sigmoid_on_softmax_log_odds. Raw score remains softmax(logits)[1], positive class = attack.
Mapping: q = sigmoid(a * logit(clip(raw_softmax_class_1_probability,1e-12,1-1e-12)) + b).
Slope: 0.5342020363895714; intercept: 0.9137732043262331.
Recipe (smoothing, monotonic constraint and optimizer) is in calibration_config.json.
Only one pre-specified fit; no method search or threshold optimization.

## Data and Integrity

CALIBRATION: 233; positive: 41; negative: 192.
Manifest SHA-256: `9cdd5ecdd80f9ac3c8f05db63742721f4537ca2b64a2fe48f6c2b424b57483a6`.
Source text hashes and deepset labels verified against the manifest.
Source counts: {'Do-Not-Answer': 133, 'deepset Prompt Injection': 100}.
BASE_TRAIN features used: NO. VALIDATION used: NO. Protected data used: NO.
Only CALIBRATION membership rows were validated and scored. Historical validation
artifacts were hash-checked only; no rows, predictions or metrics were parsed.
All 46 frozen files retain their hashes; model/tokenizer binding unchanged.
Transformer retrained: NO. All parameters disabled for gradients; backward and
AdamW steps guarded; encoder hash unchanged. D_M-A and D_S remain intact.

## Fitting-Partition Calibration Diagnostics

| Score | Brier | Log Loss |
|---|---:|---:|
| Raw | 0.0202090050 | 0.1293313895 |
| Calibrated | 0.0161928795 | 0.0766560814 |

These are **in-sample fitting diagnostics**, not unbiased generalization results.
They do not establish improved out-of-sample calibration or distribution-shift quality.

## Artifacts and Integration

Artifact directory: artifacts/models/dm_b_v1/calibration/.
Contains calibrator.json, calibration_metadata.json, calibration_config.json,
calibration_fit_diagnostics.json, calibration_scores.json and service_smoke.json.
No raw text or embeddings packaged. Transparent JSON; no executable pickle.
Reload and deterministic mapping: PASS. Raw scores and raw-score votes match
before/after on all 233 calibration records. Synthetic service/API smoke: PASS.
calibrated_probability: AVAILABLE. Base detector version remains dm_b_v1.
Existing model loading auto-attaches calibration when present; absent calibration
returns None only when require_calibration=False. Service wiring requires calibration.
Missing, incomplete, corrupt or model-incompatible calibration fails explicitly.
No raw-as-calibrated, identity, dummy, or D_M-A fallback is permitted.
Default binary vote remains raw_score >= 0.5. Final operating threshold: NOT FROZEN.

## Scientific Limits

The approved development corpus is narrow. No protected evaluation, E1-E10,
D_G integration, ensemble or shared-failure experiment occurred. Calibration
quality under distribution shift remains unknown until a separately approved evaluation.
Command: `.\.local-python\python.exe -m detection_service.scripts.calibrate_semantic_finetuned`.
The runner refuses an existing authoritative calibration directory.

## Acceptance Evidence

104 tests passed, 0 failed, 0 skipped, 0 blocked; 7 legacy tests that inspect real
VALIDATION membership metadata were deliberately deselected without modification.
New CALIBRATION-only and synthetic boundary tests cover the relevant non-access
policy. See TECH_SEM_002_CALIBRATION_TEST_REPORT_v1.md for the exact command.
Real calibrated-model reload, configured service wiring and deterministic API
inference passed. The existing D_M-A model and calibrator return exactly their
recorded synthetic API values. D_S regression tests pass. All 46 preflight-frozen
files retain their hashes. Evidence is in calibration/verification.json,
calibration/test_evidence.json and calibration/test_results.xml.
Recommendation: READY FOR DETECTOR STACK INTEGRATION AFTER TECH-GUARD-001.
This is not readiness for E1-E10.
