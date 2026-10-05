# TECH-STAT-002 Calibration Report v1

Date: 2026-10-02. Status: PASS.
Calibration version: ds_v1_cal_v1.

## Reserved Data And Method

CALIBRATION only: 233; positive 41; negative 192.
Manifest hash: 9cdd5ecdd80f9ac3c8f05db63742721f4537ca2b64a2fe48f6c2b424b57483a6.
Feature extraction: 233 x 10, zero failures/nonfinite values,
13.433 seconds. Frozen extractor/scorer reused.
No BASE_TRAIN or VALIDATION feature matrix used in this fit.
All selected text/source/label hashes verified. Protected data used: NO.

Method: platt_sigmoid_on_lr_log_odds, reusing the unchanged project sigmoid fitter.
q = sigmoid(a * logit(clip(p,1e-12,1-1e-12)) + b), p=raw LR class-1 probability.
Slope a=1.268563607221541; intercept b=-1.5257967190918829.
Smoothed Platt targets, positive slope bound 1e-8, unweighted cross entropy,
no extra penalty; L-BFGS-B/maxiter=1000/ftol=1e-12/gtol=1e-10.
One pre-specified method; no calibration/threshold selection using VALIDATION.
Optimizer converged in 7 iterations.
Positive slope preserves raw-score orientation; no class reversal.

## FITTING-PARTITION CALIBRATION DIAGNOSTICS

| Score | Brier | Log Loss |
|---|---:|---:|
| Raw | 0.1543496643 | 0.4724154438 |
| Calibrated | 0.0970526314 | 0.3166353178 |

These are IN-SAMPLE diagnostics on the fitting partition, not out-of-sample
generalization estimates or evidence of calibration quality under shift.
No independent calibration-quality claim follows from these improvements.

## Artifact, Reload And Decision

Artifact: artifacts/models/ds_v1/calibration/calibrator.json.
SHA-256: b71a64cd3cb2f1cfc8d3a256caade709e68ce01f2dcd267e29617b92831ff9eb.
JSON metadata/config/integrity manifest bind calibration to exact scorer/schema/
model-config/training metadata bytes. Reload output exactly equals fitted output.
Scorer retrained: NO; extractor/model parameters unchanged. VALIDATION used: NO.
Calibration was committed at 5fac44c before the sole development validation pass.
Vote: calibrated_probability >= 0.5, DEFAULT DEVELOPMENT CUTPOINT.
Unlike D_M-A/D_M-B's preserved raw-score votes, this follows TECH-STAT-002's
explicit calibrated-probability preference. No other detector was changed.
Final operating point: NOT FROZEN.
The development corpus is narrow. The scorer is trained on the current approved development distribution; no protected evaluation, distribution-shift or adaptive-attack claim follows. Calibration diagnostics are fitting-partition only. Final operating thresholds are NOT FROZEN. The reference LM and statistical feature extractor were not trained or changed.
