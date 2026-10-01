# TECH-SEM-001 Calibration Test Report v1

Date: 2026-10-01
Status: PASS

## Test Execution

Command:

```powershell
.\.local-python\python.exe -m pytest -o addopts= -q --junitxml=artifacts/models/dm_a_v1/calibration/test_results.xml
```

Result: **55 passed, 0 failed, 0 skipped, 0 blocked**, in 10.44 seconds.
This includes 23 new calibration cases and the 32 existing regression cases.
Two dependency deprecation warnings (Starlette/AnyIO and sklearn/SciPy) do not
affect execution. No dependency problem remains.

## Required Checks

| Check | Result | Evidence |
|---|---|---|
| Calibrator serialization | PASS | JSON slope/intercept, transform epsilon and metadata saved. |
| Calibrator reload | PASS | Integrity-checked synthetic round trip and actual saved artifact reload. |
| Deterministic probability | PASS | Exact repeated mapping outputs; real encoder/API smoke identical across requests and reload. |
| Raw probability unchanged | PASS | All 233 frozen-classifier outputs match after classifier reload; calibrated detector preserves original raw_score. |
| Probability in [0,1] | PASS | Finite endpoint/interior results; NaN, infinity and invalid inputs rejected. |
| Model/calibrator compatibility | PASS | Exact classifier/config/metadata hash binding; changed classifier and metadata rejected. |
| Calibration manifest hash | PASS | Required SHA-256 verified; altered manifest stops before loading text. |
| Calibration count | PASS | 233 members, 41 positives, 192 negatives; invalid artifact count rejected. |
| No classifier retraining | PASS | Authoritative run blocked LogisticRegression.fit; coefficient and existing artifact hashes unchanged. |
| No lexical fallback | PASS | Existing import-failure test and encoder source checks; real frozen encoder used. |
| Unavailable calibrator | PASS | Missing/corrupt mapping rejected; default service wiring requires calibration. |
| DetectorResult probability | PASS | Separate calibrated_probability, raw_score, default binary_vote, metadata and latency verified. |
| API probability | PASS | /v1/detect/input returns HTTP 200 with separate calibrated_probability. |
| VALIDATION excluded from fitting | PASS | Text loader accepts CALIBRATION only; no validation inference/evaluation function called. |
| Protected data excluded | PASS | Approved source/artifact allowlist; protected-source rejection; only three approved source files loaded. |

Additional coverage: exact/canonical lineage boundaries, label mapping, artifact
tampering, monotonic sigmoid mapping and diagnostic bin endpoints.

Existing LR training unit tests use tiny synthetic fixtures only. The frozen
authoritative classifier was not fitted or modified during calibration.

## Actual Artifact and API Smoke

Artifact: `artifacts/models/dm_a_v1/calibration/`.
Calibration version: `dm_a_v1_sigmoid_v1`.
Calibrator SHA-256:
`8769d252cce23df70c2cf2264f7765d0e7a10fc7650cc3ea8489e826cda8ff36`.

Reloaded real encoder and classifier, required the saved calibration layer, then
sent synthetic meeting text through /v1/detect/input twice:

- detector_version: `dm_a_v1`
- raw_score: `0.35952208369973776`
- calibrated_probability: `0.09938668294115482`
- binary_vote: `false`
- HTTP status: `200`
- repeated predictions: exactly equal

The vote remains raw_score >= 0.5 and carries DEFAULT_DEVELOPMENT_CUTPOINT.
No new threshold was selected. The API does not echo input text.

## Integrity and Data Boundaries

The development manifest remains:
`9cdd5ecdd80f9ac3c8f05db63742721f4537ca2b64a2fe48f6c2b424b57483a6`.

All ten pre-existing D_M-A files retain their SHA-256 values, including BASE_TRAIN
and VALIDATION embedding files, classifier metadata, model configuration,
training metadata and validation results. All five D_S source files are unchanged.
The authoritative classifier retains SHA-256:
`3103c504a4ccf4afece9b97373f2b913d3a1de22dc8151d4a3b582bfcf1c6e97`.

Source membership: Do-Not-Answer 133; deepset Prompt Injection 100.
Each selected text matches its manifest exact hash, and deepset labels match the
source rows. Source file hashes were checked before/after reading. All three
partitions' lineage membership was checked using manifest metadata; BASE_TRAIN
and VALIDATION text was not embedded or evaluated. The mixed-source normalized
archive and protected dataset payloads were not opened.

Encoder and tokenizer fingerprints match the frozen configuration. No embedding
cache was reused. The authoritative run produced no raw calibration text, per-row
score cache, or calibration embedding artifact.

## Dependencies and Reproducibility

Python 3.11.9; NumPy 2.1.3; SciPy 1.17.1; sklearn 1.6.1;
sentence-transformers 3.4.1; torch 2.6.0; transformers 4.49.0; pyarrow 19.0.1.

Only pyarrow was newly installed, to read the two approved Parquet source files
without accessing the mixed-source normalized archive. Calibration runner
dependencies are pinned in `detection_service/requirements-calibration.txt`.
No further package installation is required.

Git HEAD: `9a68a4322fa1c010588ae9c0911c7d52286a8043`.
The worktree contains this task's uncommitted implementation and artifacts;
metadata records the working-tree state. Calibration embeddings took 60.44 seconds
on CPU. The sigmoid fit converged; its optimizer iteration count is in metadata.

## Scientific Boundary

Calibration-fit diagnostics use the same 233 samples that fitted the mapping.
They are not held-out results and do not establish improved generalization.
No protected experiments, D_M-B implementation, or D_G integration were started.

Recommendation: READY FOR TECH-SEM-002 under separate authorization.
