# TECH-GUARD-001 Test Report v1

Date: 2026-10-02. Status: PASS for standalone acceptance.

## Commands And Counts

Repository-root commands using the existing interpreter:
```powershell
.\.local-python\python.exe -m detection_service.scripts.prepare_guard
.\.local-python\python.exe -m pytest detection_service/tests/test_guard.py -q --basetemp detection_service/outputs/guard-unit-temp
.\.local-python\python.exe -m detection_service.scripts.smoke_guard
.\.local-python\python.exe -m detection_service.scripts.verify_guard_regressions
```
Preparation: FROZEN_LOAD_PASS.
Guard: 49 passed, 0 failed, 0 skipped.
Combined: 151 passed, 0 failed, 0 skipped, 9 intentionally deselected.
The 49 guard tests are included in 151, not additive.
artifacts/models/dg_v1/test_evidence.json records node IDs/outcomes/durations.
Runner source records exact selection and repository-local basetemp/JUnit paths.

| Area | Synthetic Tests Passed |
|---|---:|
| Statistical engine/detector/features/export/API | 22 |
| D_M-A | 9 |
| D_M-A calibration | 18 |
| D_M-B | 26 |
| D_M-B calibration | 27 |
| D_G | 49 |

Existing API tests cover semantic routing. This is synthetic regression, not
scientific reevaluation of other authoritative models. Existing optimizer tests
use tiny throwaway fixtures; no authoritative/project model is trained.

## Guard Test Coverage

Strict config roundtrip/pinned identity and policy rejection; real tiny DeBERTa
model/tokenizer initialization; offline artifact reload/model reuse; DetectorResult
JSON compatibility; class-1 orientation/bounds, bool vote and null calibration.
Native argmax ties, deterministic repeated inference, empty/whitespace/invalid type,
Unicode/NUL/surrogate and zero-token behavior.
510/511/956/957 boundaries, 10,000 tokens, full overlap union/tail, batch/context
budget, special tokens, tail-only max aggregation and no decode/re-encode.
Missing/hash-corrupt artifact/model/config/tokenizer; escaped path; bad revision/
architecture/count; loader/dependency/inference failures; partial random-head
initialization; invalid/nonfinite logits. All fail explicitly without fallback.

## Real Pinned CPU Smoke

Pinned authoritative weights/tokenizer loaded offline, with no missing model keys.
CPU float32, 8 threads, eval/inference mode. Exact repeat scores/votes/coverage/
metadata for short, Unicode, NUL and long-tail synthetic engineering strings.
Short/Unicode/NUL each one chunk. Long case: 1,294 content tokens, three chunks,
tail end 1,294, zero excluded; full content-ID union independently verified.
Independent unpadded real-model chunk inference matches maximum score (1e-6
absolute tolerance) and OR-of-native-votes from the batched guard.
Finite bounded score; calibrated_probability=None; valid DetectorResult JSON.
Model identity reused, gradients disabled and all upstream hashes unchanged.
Evidence: artifacts/models/dg_v1/smoke_evidence.json.
Synthetic scores are engineering checks, NOT accuracy or benchmark results.

## Data Restrictions

These nine existing actual-data tests were intentionally deselected:
- test_development_manifest_hash_and_partition_boundaries
- test_manifest_integrity_count_and_calibration_membership
- test_cross_partition_lineage_is_rejected
- test_protected_source_and_bad_label_mapping_are_rejected
- test_text_loader_rejects_non_calibration_rows_before_file_access
- test_text_loader_reads_only_approved_files_and_verifies_selected_text
- test_manifest_boundary_and_class_weights_base_train_only
- test_calibration_partition_count_and_manifest_integrity
- test_selected_calibration_texts_only_and_approved_source_access

Python open audit denies actual Dataset/PHASE-3/data_governance/experiment_readiness
roots during the selected suite; attempted accesses: zero. Native-library I/O
is not intercepted; selected tests were also inspected for actual-data access.
Synthetic temp manifests live inside ignored repository-local output directories.
No existing tests changed. Project/protected data accessed: NO. E1-E10: NO.

## Failures, Warnings And Environment

Initial tokenizer inspection failed due to Windows default encoding; explicit UTF-8
fixed inspection. Production JSON decoding is UTF-8.
First guard run: 48 pass/1 fail due to synthetic fast-tokenizer fixture lacking
its CLS/SEP postprocessor. Fixture corrected; all 49 pass. Production tokenizer
was verified independently throughout. No candidate/fallback/label change.
Existing suite warnings: AnyIO BlockingPortal and SciPy disp/iprint deprecations.
Fast tokenizer efficiency advice is expected; direct-ID chunks avoid re-tokenization.
No unresolved dependency errors, package installs or upgrades. Optional hf_xet
absence did not prevent authorized normal-HTTP download.

Python 3.11.9, torch 2.6.0+cpu, transformers 4.49.0, Hub 0.36.2,
tokenizers 0.21.4, safetensors 0.8.0, NumPy 2.1.3, pytest 8.3.4.
Intel i7-12650H, 16 logical CPUs, RAM 16,869,548,032 bytes.
Installed Torch has no CUDA; no GPU result claimed. Caches/tmp/output repo-local.
Blocked standalone checks: none. Central default service wiring: DEFERRED.
