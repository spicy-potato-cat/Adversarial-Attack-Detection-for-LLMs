# TECH-STAT-004 Test Report v1

Unit/regression status: **PASS**. Authoritative ablation acceptance: **BLOCKED**.
Run code: `2eed02d6257f0f55bd6e52e499dcc2017e8a728d`.

## Pre-Run Tests

```powershell
.\.local-python\python.exe -m pytest detection_service/tests/test_statistical_feature_ablation.py detection_service/tests/test_statistical_oof.py detection_service/tests/test_statistical_risk.py -q --junitxml=artifacts/statistical_v2/feature_ablation/prerun_tests_v1.xml
```

142 passed, zero failures/errors/skips. Tests use tiny synthetic fixtures or
frozen metadata; no project detector training/calibration/validation is hidden
inside the tests. They verify the fixed LR recipe and representation math, but
cannot guarantee convergence on every authoritative feature matrix.

Coverage: manifest/fold hashes and historical baseline counts/hashes; deterministic
length binning and sparse pooling; MAD/IQR/quantiles/top-k; strict exceedance;
anomaly runs; short inputs and empty-region availability; full overlapping
multi-scale coverage; finite features; exact feature ordering/schema hashes;
training-benign-only references; held-out mutation cannot influence those
references or unchanged training transformations; reserved partitions/protected
paths rejected; canonical-lineage disjointness; exactly-once block predictions;
fixed-FPR equality handling; diagnostic error transitions; compactness selection
and paired-bootstrap determinism.

Warnings: 78 existing SciPy L-BFGS-B deprecated `disp`/`iprint` warnings across
synthetic tests, plus one Starlette/AnyIO deprecation. None is a convergence
warning or a failed unit test. No packages were installed or changed.

## Real Run

```powershell
.\.local-python\python.exe -m detection_service.scripts.statistical_feature_ablation --mode run
```

Started only after the predeclared package was committed and the tree was clean.
Full numeric extraction reproduced the original v1 features exactly for all
1,135 authorized BASE_TRAIN records. Fold 0 B0 completed; fold 0 B1 raised a
**ConvergenceWarning: 1,000 iteration limit reached**. It was treated as an error,
not ignored, and caused the intended stop at 60.57 seconds. No block performance
artifact, selected representation or final model was emitted.

No retry, scaler, solver/C/weights/penalty change or new feature definition was
introduced. A numeric-range inspection used fold-0 training features only and
did not fit another classifier. All B1 values were finite; disparate magnitudes
are a plausible conditioning issue requiring an explicit convergence decision.

## Post-Stop Preservation

`statistical_oof_baseline --mode check`: PASS; 1,135 historical rows, nine
original output hashes. `verify_quality_preservation --mode check`: PASS;
96 original hashes, empty tracked baseline diff. The frozen preflight's 54
STAT/SEM preserved file hashes also pass. Model/recipe/schema/calibration and
previous semantic evidence were not overwritten.

Run start/failure records are preserved without changing their provenance.
The numeric cache is ignored and independently hashed in the blocked summary;
no raw prompts or model caches are staged. Protected/PHASE-3 payload opens and
raw source writes are denied. Approved mixed source containers provide only
selected BASE_TRAIN scalar texts to processing.

## Acceptance Checklist

Clean startup and authoritative HEAD: PASS.
Frozen fixtures/definitions and baseline preservation: PASS.
Full B0 reproduction: NOT COMPLETE.
B1-B6 evaluation: NOT COMPLETE.
Full five-fold stability, paired intervals, short-prompt impact, error-bank
movement and selected representation: NOT AVAILABLE.
Therefore TECH-STAT-004 is **BLOCKED**, not PASS, and STAT-005 is not ready.
No final ds_v2, protected experiment, threshold selection or complementarity
claim is made. After any authorized continuation the original failure must be
retained and the technical exception frozen before scoring additional folds.
