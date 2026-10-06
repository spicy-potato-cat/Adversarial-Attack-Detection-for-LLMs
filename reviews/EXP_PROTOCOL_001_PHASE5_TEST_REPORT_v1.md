# EXP-PROTOCOL-001 Phase 5: Test Report

Status: **PASS**. No Phase-6 work performed.

## Pre-Scoring Tests And Commit Gate

65 synthetic tests passed before real scoring and were committed with the
algorithm and preregistration in `9c63092d51d194930c276e215b8bbd98085cfde5`.
Receipt: `artifacts/research_protocol/operating_points/predeclaration_tests_v1.xml`.
The freeze command verified exact committed code/test/preregistration bytes and
a clean working tree before loading scores and running D_G.

## Post-Freeze Regression

Command:

```powershell
.\.local-python\python.exe -m pytest detection_service/tests/test_detector_semantics.py detection_service/tests/test_prediction_adapters.py detection_service/tests/test_regime_contract.py detection_service/tests/test_operating_policy.py -q -p no:cacheprovider --junitxml=artifacts/research_protocol/phase5_tests_v1.xml
```

Result: **344 tests; 344 passed; 0 failures; 0 errors; 0 skipped**.
Runtime: 102.517 seconds.
Receipt SHA-256:
`8b07d38a05c9851b0328faf4668b6f461c3c3c7be989f7b113f4a785140a2ebb`.
The original pre-scoring receipt was not overwritten.

Coverage includes exact alpha/floor, benign-only selection, positive-score
invariance, >= comparisons, successor and tie exclusions, identical scores,
zero benign, NaN/infinity/missing scores, duplicates, wrong partitions,
determinism and serialization, detector/score/calibrator/threshold-ID bindings,
policy/hash/prior-contract enforcement, missing-policy blocking, non-OK null
behavior, native preservation, guard native-OR versus operational decisions,
immutability, and absence of evaluation-time threshold fitting or overrides.
Synthetic policy mode cannot activate real evidence; policy construction and
dataclass replacement cannot bypass verified loading.

## Authoritative Read-Only Checks

`freeze_operating_points --mode check`: PASS; all 12 Phase-5 inventory hashes
matched and the policy loaded with its published file SHA.

Independent checks against the saved alignment and accepted CALIBRATION manifest:

| Check | Result |
|---|---|
| Population | 233 total / 41 attack / 192 benign |
| Exact IDs, labels, CALIBRATION partition | PASS |
| Missing / duplicate IDs / label conflicts | 0 / 0 / 0 |
| All threshold scores finite | PASS |
| D_S FP / TP / FN | 5 / 26 / 15 |
| D_M-B FP / TP / FN | 5 / 38 / 3 |
| D_G FP / TP / FN | 5 / 9 / 32 |
| Threshold equals binary64 boundary successor | PASS for all three |
| FP <= K=5 | PASS for all three |
| Saved real D_G operational activation and JSON reload | 233/233 |
| Native D_G records preserved through projection | 233/233 |
| Native versus operational vote differences | 4; allowed, not overwritten |

These checks consumed existing evidence, did not rescore a model, and did not
reselect thresholds. Positive diagnostics were checked only after freeze.

## Preservation And Scope

Phase-2: 165 accepted integrity checks passed, including all 96 baseline checks.
Phase-3: six artifacts preserved. Phase-4: 14 artifacts preserved.
The six Commander-specified prerequisite hashes all matched.
Existing source/model/calibrator/protocol files are unchanged; new code and
schemas are additive, with only a narrow `.gitattributes` byte-preservation edit.

The regression suite's existing Phase-4 tests verify historical R0 membership
metadata; no raw prompts, R0 model scoring, or performance metrics are involved.
The Phase-5 dedicated preservation command only checks Phase-4 inventory bytes.
No VALIDATION inference or operational analysis, protected data, R1/R2/R3,
training, recalibration, D_S reconstruction, Cycle-2 resumption, or Phase-6
implementation was performed. Shared raw source files were hash-checked and
opened only to extract selected CALIBRATION rows; no raw content is published.

## Remaining Boundaries

The 3% budget describes empirical CALIBRATION FPR, not a future-distribution
guarantee. The low D_G diagnostic recall is not grounds for reselection.
`prediction_v1` remains native and null-locked; future operational evaluation
must explicitly load the frozen policy and consume `prediction_operational_v1`.
Descriptive regime-specific frontiers and general metrics remain later work.

Final verdict: **PHASE_5_COMPLETE_READY_FOR_PHASE_6**. Do not start Phase 6.
