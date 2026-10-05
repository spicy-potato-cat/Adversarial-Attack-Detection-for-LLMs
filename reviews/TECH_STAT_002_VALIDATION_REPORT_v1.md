# TECH-STAT-002 Validation Report v1

**DEVELOPMENT-ONLY VALIDATION - NOT E1-E10**

Date: 2026-10-02. Execution status: PASS; performance is not an acceptance claim.
VALIDATION evaluated exactly once, only after scorer and calibrator were frozen.
No model/scorer/calibrator was refitted after viewing these results.
Default calibrated-probability cutpoint: 0.5, not the final operating point.

## Counts And Metrics

Samples: 233; positive: 39; negative: 194.
TN=189, FP=5, FN=21, TP=18.

| Metric | Value |
|---|---:|
| Accuracy | 0.8884120172 |
| Precision | 0.7826086957 |
| Recall / TPR | 0.4615384615 |
| Specificity / TNR | 0.9742268041 |
| F1 | 0.5806451613 |
| FNR | 0.5384615385 |
| FPR | 0.0257731959 |
| ROC-AUC | 0.8243457573 |
| PR-AUC (average precision, project convention) | 0.6454767386 |

At this default decision, 21 of 39 positives are missed (FNR 53.85%).
Accuracy alone must not conceal the low 46.15% recall.
This is not a tuning signal used to revise the scorer, calibration or cutpoint.

## Isolation And Reproducibility

233 x 10 finite feature matrix, zero failures; extraction 10.768 seconds.
Manifest/text/source integrity verified before and after; matrix and row-order
hashes stored in validation_metrics.json. validation_started.json is an exclusive
logical once-only gate: a second runner invocation refuses evaluation.
VALIDATION labels/text were not used for fitting. Metadata-only membership
checks before this phase do not constitute feature extraction/evaluation.
No raw prompts or row-level predictions are committed.
Protected/internal/external evaluation, R0-R3 and E1-E10: NOT EXECUTED.
No JFN/EJF, adaptive attacks, disagreement routing or final stack integration.
The development corpus is narrow. The scorer is trained on the current approved development distribution; no protected evaluation, distribution-shift or adaptive-attack claim follows. Calibration diagnostics are fitting-partition only. Final operating thresholds are NOT FROZEN. The reference LM and statistical feature extractor were not trained or changed.
