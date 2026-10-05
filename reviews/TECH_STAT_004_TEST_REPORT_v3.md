# TECH-STAT-004 Test And Acceptance Report

Status: **PASS**. All35 authoritative fits converged; B0 reproduced exactly.
Model/run code commit: `e8533cba2379df67eeca9f5e54c7f1de26c4cd9f`.
Acceptance-tool code is post-run verification only, not revised model provenance.

## Commands

```powershell
.\.local-python\python.exe -m detection_service.scripts.statistical_feature_ablation_resume --mode prepare
.\.local-python\python.exe -m pytest detection_service/tests/test_statistical_feature_ablation.py detection_service/tests/test_statistical_oof.py detection_service/tests/test_statistical_risk.py -q --junitxml=artifacts/statistical_v2/feature_ablation/resume_20000/prerun_tests_v1.xml
# Numerical correction committed; clean tree verified before run.
.\.local-python\python.exe -m detection_service.scripts.statistical_feature_ablation_resume --mode run
.\.local-python\python.exe -m detection_service.scripts.statistical_feature_ablation_acceptance
.\.local-python\python.exe -m pytest detection_service/tests/test_statistical_feature_ablation.py detection_service/tests/test_statistical_feature_ablation_acceptance.py detection_service/tests/test_statistical_oof.py detection_service/tests/test_statistical_risk.py -q --junitxml=artifacts/statistical_v2/feature_ablation/resume_20000/acceptance_tests_v1.xml
```

Pre-run145 tests passed, 0 failed/errors/skipped. Initial post-run145 tests
passed;3 adapter unit tests passed; final combined148 tests passed. All test
classifier fits use synthetic unit fixtures, not additional project model runs.
Existing Starlette/AnyIO and SciPy optimizer deprecations are non-blocking.
No dependency installation or environment change occurred.

## Verification-Only Adapter

The original frozen `--mode check` attempt found an AttributeError:
`statistical_oof_baseline` has no `digest_ids` attribute. The checker calls
that helper through the wrong module; the canonical implementation already
exists in `analysis.statistical_oof` and was used by fitting code.

The acceptance adapter binds this exact existing helper while executing the
frozen checks, then restores module state. It rejects conflicting implementations.
Three tests cover success cleanup, exception cleanup and conflict rejection.
No fitting, scoring change, output mutation or bypass of preservation checks
is introduced. Frozen run code and provenance remain unchanged. The bare frozen
resume checker still needs this binding; use the acceptance adapter command.

## Authoritative Acceptance

- 9/9 final output hashes and 9/9 STAT-003 output hashes pass.
- 96/96 baseline hashes, 54/54 opaque STAT/SEM hashes and 20/20 prior STAT-004
  artifact/report hashes pass; baseline tracked diff empty.
- 1135 identities per block, all seven blocks, BASE_TRAIN labels/folds/lineage,
  and exactly-once OOF coverage pass.
- Aggregate, all fold metrics, short-prompt buckets, error-bank transitions,
  selection and prediction products reconstruct byte-for-byte where applicable.
- All five training-only references reconstruct; held-out membership/lineage
  checks pass and references bind to every block/fold record.
- All 35 fits use cap 20000, converge without convergence warnings, have valid runtimes,
  match fold records, and have n_iter_ < 20000. Maximum 9752, B6/fold 2.
- B0 predictions have maximum absolute difference 0.0; confusion/AUC/AP/all
  fixed-FPR points exactly match the authoritative STAT-003 baseline.
- Paired 1000-resample bootstrap reconstructs byte-for-byte with no model refit.
- No reserved/protected partitions, other detector outputs, final ds_v2,
  deployment threshold, STAT-005 or E1-E10 activity.

## Scope And Provenance

Numerical parameter tests prove only max_iter changed from5000 to20000;
the original recipe remains1000. Solver/tolerance/C/L2/weights/seed and exact
feature-definition SHA stay frozen. No scaling or feature amendment.
Earlier1000/5000 failures remain intact; current outputs use one20000 recipe.
The token cache was hash-checked; all fold-local learned values were freshly
fitted from training rows. Run code was committed and tree clean at execution.
Post-run evidence commits must not be substituted for the recorded run commit.

Scientific acceptance is complete for the development feature ablation only.
No final-performance claim is warranted. See the feature and short-prompt
reports for selection bias, conditional-bootstrap limits, ultra-short failures,
subgroup false positives and fold variability.
