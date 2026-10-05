# TECH-STAT-005 Test Report v1

Status: **PASS**. Authoritative run code:
`f123a46c320075a52ef0af3d09e2de734e4895f9`.
Acceptance code is verification-only and belongs to the later evidence commit.

## Test Runs

Pre-run and initial post-run commands:

```powershell
.\.local-python\python.exe -m pytest detection_service/tests/test_statistical_scorer_comparison.py detection_service/tests/test_statistical_feature_ablation.py detection_service/tests/test_statistical_feature_ablation_acceptance.py detection_service/tests/test_statistical_oof.py detection_service/tests/test_statistical_risk.py -q --junitxml=artifacts/statistical_v2/scorer_comparison/prerun_tests_v1.xml
```

Pre-run: **169 passed**, 0 failures/errors/skips, 12.231 seconds.
Post-run, same tests with `postrun_tests_v1.xml`: **169 passed**,
0 failures/errors/skips, 12.731 seconds.

Expanded verification-only acceptance suite:

```powershell
.\.local-python\python.exe -m pytest detection_service/tests/test_statistical_scorer_acceptance.py detection_service/tests/test_statistical_scorer_comparison.py detection_service/tests/test_statistical_feature_ablation.py detection_service/tests/test_statistical_feature_ablation_acceptance.py detection_service/tests/test_statistical_oof.py detection_service/tests/test_statistical_risk.py -q --junitxml=artifacts/statistical_v2/scorer_comparison/acceptance_tests_v1.xml
.\.local-python\python.exe -m detection_service.scripts.statistical_scorer_acceptance --mode record
.\.local-python\python.exe -m detection_service.scripts.statistical_scorer_acceptance --mode check
```

Expanded suite: **177 passed**, 0 failures/errors/skips. Tests fit only tiny
synthetic classifier fixtures; stored authoritative acceptance tests do not fit
any classifier. No additional project scorer run or model training occurred.

Known warnings: Starlette/AnyIO deprecated BlockingPortal alias and SciPy's
deprecated L-BFGS-B disp/iprint options in existing synthetic LR tests. No
ConvergenceWarning occurred in the authoritative 15-fit run. No package
installation or environment change was needed.

## Coverage

- QUALITY-001 manifest/fold hashes and unchanged 26-feature B2 schema/order.
- Training-fold-only B2 references; held-out mutation cannot alter training transforms or references.
- Exact S0/S1/S2 configurations and training-label-only balanced weights.
- SVM scaler training counts/means/variances/scales and gamma derived from scaled training variance; no scaler for LR/HGB.
- Deterministic sample ordering, lineage/identity disjointness, once-per-scorer/fold coverage and complete finite scores.
- SVM uses uncalibrated margins with probability=False; ranking accepts negative scores and never assumes raw 0.5 policy.
- Fixed-FPR tie handling and TP/FN/FP/TN accounting; all subgroup denominators, null empty synthetic subgroups and all transition IDs/counts.
- Paired alignment, deterministic paired resampling, predeclared gain/uncertainty/subgroup guards and simpler-scorer tie behavior.
- Convergence warning triggers STOP before scoring; no automatic recipe changes or retries.
- Forbidden partitions/raw payloads, no calibration/validation/protected analysis, no raw prompts or other detector output features.
- Stored prediction metadata rejects partition/label/fold/lineage/score-kind/calibrated-output/schema tampering.

## Authoritative Reconstruction

`statistical_scorer_comparison --mode check`: **PASS**.
Eight result hashes verify. Reconstructed metrics, fold stability, paired
comparisons, subgroups, transitions, selected scorer and predictions match
stored bytes. Five reference sets and five StandardScaler states reconstruct
from training-only numerical evidence, with membership digests and all 15
fit reports bound to their folds. This reconstruction is not another scorer fit.

`statistical_scorer_acceptance`: **PASS**, with LogisticRegression.fit,
SVC.fit and HistGradientBoostingClassifier.fit patched to raise immediately.
Zero classifier refits are permitted. Raw dataset/PHASE-3 payload access is
denied by the audit gate. Independent Boolean-mask calculations verify all
3,405 prediction metadata records, 54 aggregate/subgroup confusion checks
and 12 exact error/unique/shared sample-ID banks. The independent arithmetic
does not call the production counts/transitions helpers.

S0 is identical to accepted STAT-004 B2: maximum score difference **0.0**,
identical ROC/AP and all three pooled frontier counts. LR converged below
its 20000 limit in all folds; SVM completed in all folds; HGB completed its
fixed 100 iterations. Total authorized scorer fits: **15**, no retries.

## Preservation And Isolation

STAT-003 output hashes: **9/9**. Accepted STAT-004 output hashes: **9/9**.
Preflight-preserved evidence/code/reports: **101/101**, including historical
STAT-004 failure evidence and accepted SEM-003 evidence. Original baseline
preservation: **96/96**, empty tracked baseline diff.
The numerical cache, manifest, folds and prior detector artifacts are unchanged.
No D_S v1, D_M-A, D_M-B, D_G, calibration, service wiring or production model
file was modified. Preservation hashing does not analyze semantic residuals.

Authoritative run: BASE_TRAIN 1135, positive183/negative952; five fresh B2
references, five training-only SVM scalers, 15 scorer-fold fits, 3405 OOF scores,
identity leakage0, lineage leakage0, observed raw dataset payload opens **[]**.
No CALIBRATION/VALIDATION/protected/E1-E10/other-detector outputs, no model
download, no expensive LM pass and no final ds_v2. Cycle remains **1/2**.

## Acceptance

All phase gates pass; S0 is the sole selected candidate scorer. This accepts
the controlled comparison, not D_S production readiness or unbiased final
performance. Reports, output hashes, verification code and test XML are bound
in `artifacts/statistical_v2/scorer_comparison/acceptance_evidence_v1.json`.
Recommendation: **RECOMMEND_D_S_CYCLE_2**. Stop for Commander review.
