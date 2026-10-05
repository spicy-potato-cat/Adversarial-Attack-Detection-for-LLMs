# TECH Implementation Status v7

Date: 2026-10-02. TECH-STAT-002: PASS.
This new version does not overwrite v6 or any prior completion report.

| Component | Status |
|---|---|
| D_S v0.1 feature extractor | Preserved, hash-identical; not trained/changed |
| D_S ds_v1 statistical scorer | Trained on BASE_TRAIN only; frozen and reloaded |
| D_S ds_v1_cal_v1 | CALIBRATION-only Platt; frozen and bound to scorer |
| D_S probabilities/vote | Available; vote uses calibrated probability >= 0.5 |
| D_S service/API | Configured scored path verified; explicit failures/no fallback |
| D_S development validation | Once only after freeze; 233 samples |
| D_M-A/calibration | Unchanged; synthetic regressions PASS |
| D_M-B/calibration | Unchanged; synthetic regressions PASS |
| D_G/chunk/tail | Unchanged; synthetic regressions PASS |
| Combined regressions | 193 PASS, 0 FAIL, 0 SKIP; 9 data-reading tests deselected |
| research_stack_v1 | NOT FROZEN; integration not resumed automatically |
| Protected evaluation/E1-E10 | NOT RUN |
| Final operating points | NOT FROZEN |

D_S identity: statistical_perplexity / ds_v1.
Artifact root: artifacts/models/ds_v1.
Ten statistical inputs in the existing export order; no scaling/imputation.
One balanced lbfgs/l2/C=1.0 LR fit (1135, 183 positive), converged in 193 iterations.
One sigmoid fit (233, 41 positive); no scorer retraining or data-driven threshold search.
Validation: TN189/FP5/FN21/TP18; accuracy 88.84%, recall 46.15%, FNR53.85%.
This default-decision limitation is reported, not concealed or tuned away.
Calibration diagnostics are in-sample only; no scientific superiority claims.

Set STATISTICAL_MODEL_DIR=artifacts/models/ds_v1 to enable scored D_S.
Without it, legacy evidence-only v0.1 remains an explicit compatibility mode.
With it, missing scorer/calibration/reference artifacts fail without downgrade.

BASE_TRAIN used for scorer: YES. CALIBRATION used for scorer: NO.
CALIBRATION used for calibrator: YES. VALIDATION used for fitting: NO.
Protected data/E1-E10/adaptive attacks/JFN-EJF/full-stack integration: NO.
The development corpus is narrow. The scorer is trained on the current approved development distribution; no protected evaluation, distribution-shift or adaptive-attack claim follows. Calibration diagnostics are fitting-partition only. Final operating thresholds are NOT FROZEN. The reference LM and statistical feature extractor were not trained or changed.

Recommendation: READY TO RESUME TECH-INTEGRATION-002.
Not READY FOR E1-E10 or final research results.
