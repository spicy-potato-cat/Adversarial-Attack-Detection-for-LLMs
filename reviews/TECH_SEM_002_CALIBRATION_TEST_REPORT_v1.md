# TECH-SEM-002 Calibration Test Report v1

Date: 2026-10-01. Status: PASS.
Target: semantic_finetuned / dm_b_v1; calibration: dm_b_v1_cal_v1.

## Command and Results

```powershell
.\.local-python\python.exe -m pytest -o addopts= -q -k "not test_development_manifest_hash_and_partition_boundaries and not test_manifest_integrity_count_and_calibration_membership and not test_cross_partition_lineage_is_rejected and not test_protected_source_and_bad_label_mapping_are_rejected and not test_text_loader_rejects_non_calibration_rows_before_file_access and not test_text_loader_reads_only_approved_files_and_verifies_selected_text and not test_manifest_boundary_and_class_weights_base_train_only" --basetemp=detection_service/outputs/sem002-calibration-final-tests --junitxml=detection_service/outputs/sem002-calibration-final-tests.xml
```

Final run: **104 passed, 0 failed, 0 skipped, 0 blocked, 7 deselected**, 9.39 seconds.
The seven existing governance tests inspect real VALIDATION membership metadata.
They remain unchanged and are deliberately excluded under this phase's stricter
no-inspection policy. New tests filter CALIBRATION before row validation, use
synthetic other-partition rows, reject non-CALIBRATION features before source
access, and guard approved source paths and selected Parquet scalar indices.
No historical validation rows, predictions, metrics or features were processed.

Existing Starlette/AnyIO and sklearn/SciPy deprecation warnings remain; no
dependency installation or upgrade was required. The preceding 102-case run also
passed; two malformed-JSON-schema cases were then added and the final 104-case
suite passed. No unit-test failures occurred.

## Coverage

| Requirement | Result |
|---|---|
| Transparent artifact creation, schema and reload | PASS |
| Deterministic output, bounds and positive-slope monotonicity | PASS |
| Repeated score produces identical calibrated probability | PASS |
| Frozen model/tokenizer/recipe/historical evidence hashes | PASS; 46 files |
| No transformer updates | PASS; gradients disabled, backward/AdamW guarded, encoder hash unchanged |
| DetectorResult calibrated_probability | PASS; populated, finite, separate raw score |
| Raw score and default raw-score binary_vote | PASS; unchanged on all 233 CALIBRATION records |
| Missing calibration | PASS; explicit None only in optional raw adapter; required service load fails |
| Corrupt/incompatible calibration, invalid input, nonfinite output | PASS; explicit errors, no fallback |
| dm_b_v1 final artifact reload | PASS; actual locally frozen model |
| Independent configured service and synthetic API | PASS |
| D_M-A regression and saved calibration regression | PASS; actual API values exactly equal prior evidence |
| D_S regression | PASS; existing tests and unchanged hashes |
| Manifest hash and 233-row CALIBRATION counts | PASS; 41 positive, 192 negative |
| CALIBRATION-only source access and non-access boundary | PASS |
| Protected-data non-access | PASS; whitelist and non-CALIBRATION rejection |

## Real Artifact Evidence

`artifacts/models/dm_b_v1/calibration/verification.json` records actual trained
model reload, configured service wiring, deterministic API inference, mapping
reload on recorded calibration scores, and preserved raw scores/votes.
The independent actual D_M-A model/calibrator smoke matches its prior saved raw
score, calibrated probability and binary vote exactly. No D_M-A fitting occurred.
All pre-existing artifacts, including v5, retain exact preflight hashes.

JUnit: `calibration/test_results.xml`. Command, totals and tested source SHA-256:
`calibration/test_evidence.json`. Calibration manifest and source hashes,
coefficients, packages including SciPy, model binding and fitter code hashes are
in calibration metadata. Weights remain local and Git-ignored.

## Execution Notes and Boundaries

The initial preflight's committed-text comparison encountered Git's expected CRLF
conversion in the v5 report. The comparison was corrected for ordinary text
reports only; frozen D_M-B model files remain exact byte comparisons, and every
preserved file is subsequently checked against its exact local SHA-256.
No model integrity discrepancy, coefficient change, or detector regression occurred.

CALIBRATION used: YES. BASE_TRAIN features used: NO. VALIDATION used: NO.
Protected data used: NO. Transformer retrained: NO. D_G/E1-E10/ensembles: NOT RUN.
No threshold optimization or calibration-method search occurred. Calibration
diagnostics are in-sample fitting diagnostics, not generalization evidence.
