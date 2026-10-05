# TECH-SEM-002 Test Report v1

Date: 2026-10-01
Status: PASS; AUTHORITATIVE MODEL AND POST-TRAINING CHECKS VERIFIED

## Test Command and Result

```powershell
.\.local-python\python.exe -m pytest -o addopts= -q -k "not test_text_loader_reads_only_approved_files_and_verifies_selected_text" --basetemp=detection_service/outputs/sem002-post-training-tests --junitxml=artifacts/models/dm_b_v1/post_training_tests.xml
```

**81 passed, 0 failed, 0 skipped, 1 deselected**, in 19.49 seconds after training.
The excluded legacy test reconstructs real CALIBRATION text, which this phase
must not consume. All remaining calibration-regression cases use synthetic
fixtures, metadata, or saved artifacts. The suite preserves D_M-A and D_S tests.
Two existing Starlette/AnyIO and sklearn/SciPy deprecation warnings remain.

Source hashes of the tested application/scripts/tests and results are recorded
in `artifacts/models/dm_b_v1_test_evidence.json`. The runner checked these before
emitting v5 completion status. Initial JUnit evidence is in `dm_b_v1_tests.xml`;
the post-training rerun is in `dm_b_v1/post_training_tests.xml`.

## Coverage

| Required behavior | Result | Evidence |
|---|---|---|
| Configuration parsing | PASS | JSON roundtrip, environment wiring, invalid recipes/revisions rejected. |
| Model metadata | PASS | Distinct semantic_finetuned / dm_b_v1 identity and immutable revisions. |
| Tokenizer/model loading | PASS | Tiny genuine RoBERTa artifact roundtrip; actual pinned upstream loading also passes. |
| DetectorResult compatibility | PASS | Raw score, null calibration, bool vote, latency and metadata serialized through API. |
| Score orientation / bounds | PASS | Controlled class-1 logits give high risk; reversed labels and nonfinite logits rejected. |
| Binary/default decision | PASS | Raw softmax class-1 probability >= 0.5; DEFAULT_DEVELOPMENT_CUTPOINT. |
| Deterministic eval | PASS | Repeated tiny-model and real upstream synthetic predictions agree; dropout disabled. |
| Empty / whitespace input | PASS | Request and API validation reject them with 422 at API. |
| Unicode / normal text | PASS | Synthetic Unicode and engineering text run without changing originals. |
| Maximum length / truncation | PASS | Exact boundary and over-limit token counts, coverage and warning verified. |
| Batch inference | PASS | Order and finite result count preserved across internal batches. |
| Model reuse | PASS | Tokenizer/model load once; repeated requests reuse instances. |
| Missing artifact / no fallback | PASS | Missing, corrupt or load-failed models fail explicitly; structured API 503. |
| Serialization / reload | PASS | Tiny fixture and final authoritative transformer/tokenizer reload with integrity checks. |
| Transformer parameter updates | PASS | Authoritative encoder before/after hashes differ; saved encoder matches final hash. |
| BASE_TRAIN isolation | PASS | Manifest hash/counts, BASE_TRAIN-only weights, text/label hashes and calibration rejection. |
| D_M-A regression | PASS | Existing regression suite and actual saved model/calibrator API smoke. |
| D_M-A calibration preservation | PASS | Raw/calibrated scores exactly match the prior synthetic API smoke; no refit. |
| D_S regression | PASS | Existing statistical tests pass; no statistical source changes. |
| Service integration | PASS | Configured service factory loads final dm_b_v1; isolated D_M-B API inference succeeds. |
| Final dm_b_v1 artifact reload | PASS | Completed model loads locally with all model/tokenizer hashes verified. |
| Final dm_b_v1 real-model smoke | PASS | Finite raw scores, null calibration, bool vote, latency, Unicode, truncation, deterministic batch/API predictions. |
| Development validation | PASS | One 233-row evaluation after final checkpoint freeze; not repeated during post-training checks. |

## Actual D_M-A Calibration Regression

Existing dm_a_v1 loaded with require_calibration=True. Synthetic meeting text
through its existing API produced exactly the previous values:

- raw_score: 0.35952208369973776
- calibrated_probability: 0.09938668294115482
- repeat_deterministic: true

No CALIBRATION text was used, no coefficient/calibrator fitting was performed,
and no D_M-A or D_S file appears in the Git diff. D_M-A frozen classifier/config
binding and saved calibrator integrity were verified at phase entry.

## Actual Upstream Synthetic Training Smoke

Pinned DistilRoBERTa revision: fb53ab8802853c8e4fbdbcd0529f21fc6f459b2b.
One scratch backward pass on eight synthetic 256-token examples: PASS.
Backbone parameter updates: verified. Eval determinism: PASS.
Evidence: `artifacts/models/dm_b_v1_pipeline_smoke.json`.
The scratch model is discarded and is not the final authoritative artifact.
No synthetic inputs were added to project training data.

## Data and Scientific Boundaries

All 1,135 BASE_TRAIN texts reconstruct and match authoritative text hashes.
No CALIBRATION or VALIDATION features have been consumed during preparation.
Protected data, colleague checkpoints, D_G, and E1-E10 were not used.
No metrics in this report are scientific detection performance evidence.
The Commander completed the frozen CPU recipe under the long-training rule.
VALIDATION was consumed once afterward, solely for development characterization.
No CALIBRATION text was consumed during training or post-training verification.

## Final Authoritative Artifact Verification

Actual trained dm_b_v1 save/reload, real-model API smoke and repeated eval-mode predictions PASS.
All D_M-A/D_S hashes remain unchanged. Training and validation are complete; v5 status is now emitted.

Independent post-training checks verified all 27 preserved files, frozen recipe
and preparation hashes, final encoder hash, model/tokenizer integrity, and the
configured service factory. Evidence: `artifacts/models/dm_b_v1/post_training_verification.json`.
Only synthetic inputs were used; VALIDATION was not repeated. Empty/whitespace
inputs are rejected by the existing request schema, not scored by the detector.
The first ad-hoc verification harness attempted to construct empty requests and
stopped at that expected schema rejection; the corrected harness verifies
rejection explicitly and passes. No model or production-code change was needed.
