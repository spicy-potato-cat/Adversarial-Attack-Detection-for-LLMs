# EXP-PROTOCOL-001 Phases 11-13 Test Report

## Executed Regression Gate

Status: PASS. Full post-import protocol regression: **551 passed, 0 failed,
0 skipped, 0 errors**, in 426.81 seconds. Local JUnit receipt:
`tmp/exp_protocol_001_phase11_13_551_tests.xml` (not a research data artifact).

Command executed with the workspace Python 3.11.9:

```powershell
.\.local-python\python.exe -m pytest `
  detection_service/tests/test_detector_semantics.py `
  detection_service/tests/test_prediction_adapters.py `
  detection_service/tests/test_regime_contract.py `
  detection_service/tests/test_operating_policy.py `
  detection_service/tests/test_core_metrics.py `
  detection_service/tests/test_uncertainty.py `
  detection_service/tests/test_cross_regime.py `
  detection_service/tests/test_r0_reproduction.py `
  -o addopts='' -q --tb=short `
  --junitxml=tmp/exp_protocol_001_phase11_13_551_tests.xml
```

| Test module | Passed | Failed | Skipped |
|---|---:|---:|---:|
| Detector semantics | 40 | 0 | 0 |
| Prediction adapters | 74 | 0 | 0 |
| Regime contract | 165 | 0 | 0 |
| Operating policy | 65 | 0 | 0 |
| Core metrics | 96 | 0 | 0 |
| Phase-11 uncertainty | 42 | 0 | 0 |
| Phase-12 cross-regime | 24 | 0 | 0 |
| Phase-13 R0 reproduction | 45 | 0 | 0 |
| **Total** | **551** | **0** | **0** |

Before real R0 import, the complete existing/new synthetic protocol gate passed:
506 tests in 403.74 seconds. The Phase-11/12 synthetic modules also passed
independently: 66 tests in 65.19 seconds. The final independent R0 module run
passed 45 tests in 33.50 seconds. These are separate runs, not additive unique
test counts. Prior tests were not weakened.

## Phase-11 Acceptance Coverage

All 18 requested gates pass: frozen 1,000 replicates, seed 1701, 95% percentile
intervals; paired samples; clustered lineages and repeated full-cluster inclusion;
four explicit domains; undefined-not-zero treatment; the 95% valid-support
boundary; negative EJF; target evasion and ETR; paired B-minus-A deltas; and
deterministic serialization.

Production RNG: NumPy 2.1.3 PCG64, linear quantiles explicitly specified. Tests
cover observed-core points rather than bootstrap means, sparse recovery/ETR,
undefined observed points, wrong domains, mismatched paired populations,
corrupted plans, nonfinite values, and generated descendants that must remain
clustered. Synthetic fixtures contain metadata and outcomes only.

## Phase-12 Acceptance Coverage

All 16 requested gates pass. One strict result contract supports all six slots:
R0, R1, R2-D_S, R2-D_M-B, R2-D_G, and R3. Operational-policy and decision-view
mismatches are incompatible, with no misleading delta. Missing results are
NOT_RUN; inapplicable metrics are NOT_APPLICABLE; undefined values remain null.
R2 target/transfer metrics are correctly scoped and R3 is not treated as transfer.
Cross-regime fraction/percentage-point deltas are explicitly unpaired.

## Phase-13 Acceptance Coverage

All 28 requested gates pass in the reproduced results and tests: exact
1,135/183/952 population; complete truth/sample/detector alignment; accepted
D_S/D_M-B OOF evidence and frozen D_G development evidence; all nine confusion
tables; pairwise quantities; all-three misses; eight patterns; unique catch and
conditional recovery; full-precision ROC/AP; exact historical required CIs;
historical explicit provenance; no Phase-5 thresholds; complete real R0 bundle;
future regimes NOT_RUN; and hash-bound inputs.

The accepted historical RNG is Python MT19937, not NumPy PCG64. The additive
historical replay is explicitly labelled non-production, reproduces the accepted
machine-readable intervals, and leaves the frozen production contract unchanged.
Both methods' finite-sample intervals are shown in the R0 report.

OOF rows are not passed off as live final-model `PredictionRecord` objects. The
historical importer uses the unchanged strict EXPLICIT alignment contract and
binds actual score-source/run/fold evidence. Accepted model/run commit provenance
is preserved, particularly D_M-B
`5096d078b599c43ddd4e32b4fbfcaedcc83e4646`.

## Correction During Development

The first independent R0 run had 44 passing tests and one failing audit assertion:
it disallowed weight-file reads even for the mandatory SHA-only preservation
verifier. The test was corrected to allow only the integrity workflow while
still forbidding raw prompt access, live adapter predict/load calls, and model
runtime imports. The corrected independent run and full 551-test regression both
passed. No production metric, frozen prior test, model behavior, or accepted
result was altered to address that assertion.

## Integrity And Preservation Gates

- All 12 specified prerequisite artifact hashes passed before implementation.
- Previous Phases 6-10 contract check: all 11 inventory hashes and byte-identical
  synthetic reconstruction passed.
- New Phase-11/12 contract check: all 13 inventory hashes and byte-identical
  synthetic reconstruction passed before R0 import.
- Frozen detector verification: 165 checks, including all 96 original baseline
  preservation checks, passed during each historical-source verification.
- Accepted R0 import: 123 source hashes, 20 train/held-out fold-membership hashes,
  and exact membership reconstruction passed.
- Accepted Cycle-1 publication manifest matches its frozen Git blob at
  `dc6dd3041643fb70ad5b128d32c246f8763a8044`.
- Metadata-only historical decisions cover all 10,215 detector/sample/budget
  combinations, with stored inclusive cutpoints; no threshold refit or live
  rescoring was used to produce them.

The final release commands seal/check the 33-entry Phase-11/13 inventory and
reconstruct all 12 R0 outputs byte-identically. Staged Git bytes must also match
that inventory before commit; this prevents line-ending conversion from silently
changing frozen artifact hashes. Completion of those release checks and local/
remote commit equality is reported in the final handoff.

```powershell
.\.local-python\python.exe -m detection_service.research_protocol.uncertainty_contract --mode check
.\.local-python\python.exe -m detection_service.research_protocol.r0_reproduction --mode freeze
.\.local-python\python.exe -m detection_service.research_protocol.r0_reproduction --mode check
```

No detector source, model, calibrator, partition, accepted Cycle-1 output,
Phase-2/3/4/5 contract, operational threshold, or Phases 6-10 definition changed.
Weight bytes were read for SHA verification only. No raw prompt processing,
training, inference, data acquisition, protected experiment, verifier, real
R1/R2/R3 work, Cycle-2 work, or Phase-14 execution occurred.

## Commit Boundary And Final Scope

The pre-R0 machinery commit is
`9982b9bd2c5f8da7fc63a1b7977c1cccf91cfb70`. It was created before importing
historical R0, and the working tree was verified clean at that boundary. The
post-run evidence is a separate commit; it is not claimed as model-run provenance.

All requested implementation and regression gates have passed. Release remains
subject to the explicit hash/reconstruction and Git synchronization checks above.
Phase 14 is not authorized by completion of this task and is not started.
