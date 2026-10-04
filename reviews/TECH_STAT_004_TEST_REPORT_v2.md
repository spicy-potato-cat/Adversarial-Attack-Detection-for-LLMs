# TECH-STAT-004 Test Report - Cap-Only Continuation

Implementation regression tests: **PASS**. Scientific ablation acceptance:
**BLOCKED** at B4 fold 0, n_iter_=5000, ConvergenceWarning.

## Commands And Results

```powershell
.\.local-python\python.exe -m pytest detection_service/tests/test_statistical_feature_ablation.py detection_service/tests/test_statistical_oof.py detection_service/tests/test_statistical_risk.py -q --junitxml=artifacts/statistical_v2/feature_ablation/resume_5000/prerun_tests_v1.xml
.\.local-python\python.exe -m detection_service.scripts.statistical_feature_ablation_resume --mode prepare
.\.local-python\python.exe -m detection_service.scripts.statistical_feature_ablation_resume --mode run
.\.local-python\python.exe -m pytest detection_service/tests/test_statistical_feature_ablation.py detection_service/tests/test_statistical_oof.py detection_service/tests/test_statistical_risk.py -q --junitxml=artifacts/statistical_v2/feature_ablation/resume_5000/poststop_tests_v1.xml
.\.local-python\python.exe -m detection_service.scripts.statistical_feature_ablation_resume --mode check
```

Command listing is by purpose, not chronological: preparation preceded the
final pre-run XML and fix commit; authoritative execution followed a clean
fix commit. Pre-run: **145 passed**, 0 failed/errors/skipped, 11.050s.
Post-stop: **145 passed**, 0 failed/errors/skipped, 10.785s.
Authoritative run: expected hard stop, exit1, B4/fold0 nonconvergence.
Acceptance checker: expected refusal, exit1, `STOP: run failure recorded`.
No authoritative retry occurred.

## Numerical And Governance Coverage

- All scorer parameters match the frozen recipe except max_iter=5000.
- Solver lbfgs, tolerance1e-4, C1, L2, balanced weights, seed1701 unchanged.
- Historical recipe remains max_iter1000; no v1 detector recipe modification.
- Exact definition SHA and cumulative schemas remain unchanged.
- Every synthetic block/fold emits cap, actual iterations, convergence status,
  convergence warnings, and fit runtime; 35/35 synthetic fits converge.
- Injected failure records block/fold and prevents prediction and subsequent fit.
- Fold-local references, held-out independence, lineage gates, feature math,
  short buckets, fixed-FPR handling, transitions, compactness rules, deterministic
  paired bootstrap, protected-path rejection, and no prompt/semantic outputs pass.

## Post-Stop Evidence Verification

Resume `checked()` verified frozen code/environment, manifest/folds, original
history, feature definitions, cache SHA, 54 opaque STAT/SEM artifacts, and 10
original STAT-004 files. STAT-003 `check()` passed 9/9 output hashes.
`baseline_check()` passed96/96 with tracked baseline diff empty.

Independent stop-state inspection confirms exactly the attempted fit sequence
B0,B1,B2,B3,B4 on fold0, first four converged, last nonconverged, and no
accepted block metrics/predictions/selection/completion metadata artifacts.
Full five-fold B0 reproduction is not claimed.

All resumed evidence remains separate from original v1 failure records.
Unit tests use synthetic data for their LR fits; they are not protected or
additional authoritative experiments. Deprecations in Starlette/AnyIO and
SciPy's disp/iprint API are non-blocking; no dependency installation required.

Scientific acceptance requires35/35 converged authoritative fits and complete
OOF analyses. Neither is achieved, so the phase remains BLOCKED and STAT-005
is not ready. Further cap/scaler/solver/feature changes require a new decision.
