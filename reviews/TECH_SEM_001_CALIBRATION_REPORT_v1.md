# Calibration Objective

Status: PASS. D_M-A dm_a_v1 now supplies a separate calibrated probability.
Date: 2026-10-01. Classifier and encoder remain frozen.

# Frozen D_M-A Configuration

WhereIsAI/UAE-Large-V1; dimension 1024; CLS pooling; normalized embeddings;
512-token truncation; preserved source.raw_text. LR remains lbfgs/l2/C=1.0,
class_weight=balanced, max_iter=1000, seed=1701, fit_intercept=True.
Exact configuration and frozen artifact hashes are recorded in calibration metadata.

# Calibration Dataset

Only CALIBRATION member text/labels from Do-Not-Answer and deepset Prompt Injection.
BASE_TRAIN and VALIDATION membership metadata was checked for disjoint lineage;
neither partition was embedded, fitted, or evaluated in this task. Protected source
files and the mixed-source normalized archive were not opened.
Selected source text SHA-256 and deepset source labels match the manifest.
Label semantics follow LABEL_TAXONOMY_v1.md as specialized by the approved
DEVELOPMENT_DATA_CONSTITUTION_v1.md: benign/hard-benign=0; injection attempt=1.

# Calibration Manifest Hash

`9cdd5ecdd80f9ac3c8f05db63742721f4537ca2b64a2fe48f6c2b424b57483a6`. Verified before fitting and after execution.
Calibration membership/order hash: `763a84800607293b5a7b884628b73bb9ece392dd4e7307fb946938b749f50418`.

# Calibration Method

`platt_sigmoid_on_lr_log_odds`; version `dm_a_v1_sigmoid_v1`.
Fit q = sigmoid(a * logit(clip(p, 1e-12, 1-1e-12)) + b).
Two parameters, smoothed Platt targets, positive slope constraint (>=1e-8),
unweighted cross entropy, no additional penalty. Deterministic L-BFGS-B;
maxiter=1000, ftol=1e-12, gtol=1e-10; no random-state-dependent fitting.
Method and settings were specified in code before any fit diagnostics.
No alternative methods, validation selection, or threshold search were performed.

# Method Rationale

A two-parameter sigmoid is sample-efficient for 233 examples compared with a
flexible stepwise mapping. Smoothed class targets stabilize separated samples.
The positive slope preserves ordering; calibration estimates probability under
the reserved development mixture rather than the classifier's balanced class weighting.

# Sample Counts

Total: 233; positive: 41;
negative: 192.
Source counts: `{"Do-Not-Answer": 133, "deepset Prompt Injection": 100}`.
Exact/canonical lineage groups are disjoint across all three manifest partitions.

# Raw Probability Definition

raw_score remains the existing LR predict_proba output for class 1.
The classifier is never fitted in this task; its fit method is guarded against calls.
Coefficient and artifact hashes match before/after. Raw probability equality after
serialization/reload is verified on all 233 calibration embeddings.

# Calibrated Probability Definition

calibrated_probability is the frozen sigmoid mapping applied to raw_score.
The binary vote continues to use raw_score >= 0.5, explicitly labeled
DEFAULT_DEVELOPMENT_CUTPOINT. No new operating threshold was selected.

# Calibration-Fit Diagnostics

These are fitting-partition diagnostics, **not independent generalization results**.

| Probability | Brier Score | Log Loss |
|---|---:|---:|
| Raw | 0.06831763 | 0.25733477 |
| Calibrated | 0.04515597 | 0.14516420 |

Ten equal-width bins include probabilities 0 and 1. Counts, mean probabilities,
positive fractions, quantiles and summaries are in calibration_fit_diagnostics.json.

# Artifact

`artifacts/models/dm_a_v1/calibration/`: calibrator.json, calibration_config.json,
calibration_metadata.json, calibration_fit_diagnostics.json, service_smoke.json.
No raw text, per-record calibration scores, or calibration embeddings are packaged.
Mapping integrity and classifier/configuration hash compatibility are checked at load.

# Service Integration

/v1/detect/input: PASS; returns raw_score, calibrated_probability,
binary_vote, latency and calibration version/method/manifest metadata.
Repeated inference on synthetic meeting text is deterministic. Existing artifact
loading automatically loads the calibration subdirectory and fails explicitly for
invalid or incomplete calibration. require_calibration=True also rejects absence.

The default service's semantic detector wiring requires this calibration layer.
Enable it with `ENABLE_SEMANTIC_DETECTOR=true` and
`SEMANTIC_MODEL_DIR=artifacts/models/dm_a_v1`; retain `SEMANTIC_DEVICE=cpu`.
These use the existing service configuration interface.

# Limitations

Fitting diagnostics are optimistic and cannot establish improved generalization.
VALIDATION was preserved for a later approved protocol. The 41 positives give
limited calibration evidence; source labels remain MEDIUM confidence. Calibration
reflects this narrow development mixture, not deployment prevalence or the full
attack taxonomy. Exact/canonical lineage checks do not resolve all semantic or
documentary dependencies. Local encoder revisions are pinned by content hashes.

# Reproducibility

Frozen config, source hashes, selected membership hash, encoder/tokenizer hashes,
software versions, Git revision and working-tree state are in metadata.
CPU deterministic inference, eval mode, seed=1701; no embedding cache reused.
Run: `.\.local-python\python.exe -m detection_service.scripts.calibrate_semantic_baseline`.
The runner refuses to overwrite an existing authoritative calibration directory.
Tests and actual verification evidence are in TECH_SEM_001_CALIBRATION_TEST_REPORT_v1.md.
