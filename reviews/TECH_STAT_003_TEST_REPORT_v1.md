# TECH-STAT-003 Test Report v1

Status: **PASS**

Client date: 2026-10-04 (Asia/Calcutta)

## Executed Verification

```powershell
.\.local-python\python.exe -m detection_service.scripts.statistical_oof_baseline --mode prepare
.\.local-python\python.exe -m detection_service.scripts.statistical_oof_baseline --mode smoke
.\.local-python\python.exe -m detection_service.scripts.verify_statistical_oof
.\.local-python\python.exe -m detection_service.scripts.statistical_oof_baseline --mode run
.\.local-python\python.exe -m detection_service.scripts.statistical_oof_baseline --mode check
.\.local-python\python.exe -m detection_service.scripts.verify_quality_preservation --mode check
```

Prepare/smoke/run/evidence write modes are immutable and must not be rerun against
existing outputs. `check` is read-only and reusable; it does not run models or
access raw source texts. An initial development test invocation also passed
before prepare; no real-source fold fitting occurred during tests.

## New Suite

`detection_service/tests/test_statistical_oof.py`: **37 passed, 0 failed,
0 skipped, 0 errors, 0 blocked**.

- Frozen QUALITY-001 hash and metadata membership verification.
- Exactly one prediction per sample and sample-ID ordering.
- Instrumented fitting verifies exact outer-training matrices/labels only.
- Identity and lineage isolation, including indivisible same-fold groups.
- Invalid folds, duplicate IDs, reordered rows, non-BASE_TRAIN data and labels
  rejected before fitting.
- Existing final scorer load is prohibited in the OOF reproduction test.
- Same ten-feature schema/hash and exact frozen LR parameters.
- Repeated synthetic scientific outputs/coefficients/metrics deterministic.
- Fixed binary cutpoint 0.5; alternate threshold requests rejected.
- Metrics checked against a hand-computed confusion/AUC/AP fixture.
- Fixed-FPR correctness: tied blocks, coarse integer budgets, perfect ranking,
  conservative plateau ties and no feasible positive predictions.
- CALIBRATION, VALIDATION, INTERNAL_TEST and final partition text selection
  rejected before any payload open.
- Nonfinite features or feature/evidence membership mismatch fail loudly.
- Fold stability, conditional bootstrap, preregistered token buckets and
  descriptive-only characterization/hypotheses.
- No raw prompt/token strings in prediction records; calibrated probability null.

No existing test was weakened or modified. The guarded final test run disables
third-party pytest plugin auto-loading and denies Python opens of Dataset,
PHASE-3, prior output caches, reference model cache, and serialized/weight files.
**Prohibited-open attempts: 0**. Native I/O is not covered by Python's audit hook;
these tests use only synthetic matrices/models and metadata, not native readers
of dataset payloads.

The fake-tokenizer/causal-model smoke extracts the original ten features from
40 synthetic strings and completes five fold-local fits with zero leakage.
Each standard OOF projection passes QUALITY-001's frozen schema. No real project
text or reference weights are used in that correctness smoke.

## Actual BASE_TRAIN Run

- Fresh original feature extraction: 1,135 rows, exactly 10 finite columns.
- Five real fold-local LR fits, all converged below 1,000 iterations.
- Every held-out prediction repeated without refitting and bitwise matched.
- 1,135 unique standard-schema projections validated.
- Five 908-row training sets / 227-row held-out sets; identity/lineage leakage 0.
- No final scorer/calibrator load or new detector generation.
- Post-run hash and metric recomputation check: PASS (nine bound outputs).
- Original shared source containers verified before/after selected-record loading.
- Final baseline preservation: PASS (96 hashes; tracked baseline diff empty).
- QUALITY-001 fixture/core files and all original detector artifacts unchanged.

Scientific determinism excludes wall-clock/latency measurements. No second real
OOF training run was conducted merely to claim cross-run determinism. Coefficients,
iterations, recipe, train/held-out ID hashes, source hashes, local reference hashes,
code hashes and environment are retained for later authorized reproduction.

## Isolation Interpretation

The existing loader operates on original CSV/Parquet containers shared by
BASE_TRAIN/CALIBRATION/VALIDATION. Container bytes are hashed and parsed/decoded
for row selection; only BASE_TRAIN locator scalars reach extraction, fitting or
analysis. No reserved row is used. This is not a claim of physical container
isolation. The runtime path allowlist permits only the three approved immutable
development containers, while rejecting other Dataset paths and PHASE-3 payloads.
Native Parquet path use remains limited by the existing approved source mapping.

CALIBRATION use: NO. VALIDATION use: NO. Protected source use: NO.
E1-E10/adaptive experiments: NO. Semantic/guard predictions: NO.
New features/ds_v2/threshold optimization: NO. Downloads/dependency changes: NO.

## Warnings And Diagnostic QA

Synthetic tests emitted existing SciPy L-BFGS-B option deprecation warnings
(25 warnings). They did not cause convergence or numerical failures. No package
upgrade or solver change was made to suppress them.

Post-run diagnostic QA identified tied zero quartiles in window-variation rules.
The original grouping/ranking output remains frozen; a separate caveat artifact
documents that those rules cannot establish high variance or enrichment. It also
documents non-enrichment of low mean PPL/FP surprisal variance and missing long/
tail evidence. No retraining, rescoring, model-feature addition, prediction edit,
threshold edit, or raw-text inspection was used for that interpretation.

## Evidence

- `test_evidence_v1.json` SHA:
  `2e6cdfa28cbefafd4f6a367a524224978f5e2eb1b2e3153e4e8b3921f53b8a5e`.
- `synthetic_smoke_v1.json` SHA:
  `49b393580dbce38fb1cfdb586e4565d48304c0582982ab3f6df81f4ea2b858c5`.
- `completion_v1.json` SHA:
  `a1598906792b5ae4db3321d703fb9724729e678477384924814143be37acd015`.
- Diagnostic caveats SHA:
  `cba3b93638051bff16142cf34b821d8924adac79b9abfed5e23e3d7741258436`.

Recommendation: **READY FOR TECH-STAT-004 FEATURE ENGINEERING**.
Do not create D_S v2 yet or interpret these diagnostics as final performance.
