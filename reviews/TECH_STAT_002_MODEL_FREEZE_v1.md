# TECH-STAT-002 Model Freeze v1

Date: 2026-10-02. Status: PASS.
Detector statistical_perplexity / ds_v1. Extractor remains v0.1.
ScoredStatisticalDetector wraps the authoritative evidence-only extractor; original
statistical module bytes and causal math remain unchanged.

## Feature Schema

Feature count: 10. Schema SHA-256:
`2b042f88e7403985e5f94e34bb1107b377069e591322767a482a33b5e2cbf8b7`.

Ordering follows existing export_features.FIELDNAMES[3:13] exactly:
1. whole_prompt_nll
2. whole_prompt_ppl
3. global_perplexity
4. mean_window_perplexity
5. max_window_perplexity
6. std_window_perplexity
7. mean_surprisal
8. max_surprisal
9. surprisal_std
10. high_surprisal_ratio

No scaling, log transforms, imputation or feature selection. Existing compatibility
aliases are deliberately retained, not newly derived features. Runtime latency,
source/label metadata, coverage counters and auxiliary surface anomalies are not
classifier inputs; all original evidence remains in DetectorResult.

## Frozen Extractor And Scorer

Reference LM/tokenizer: distilbert/distilgpt2, revision
2290a62682d06624634c1f46a6ad5be0f47f38aa. CPU float32, context 1024.
Analysis cap 4096, window size 128, stride 64, high-surprisal diagnostic cutoff 8.0.
Shifted causal N-1 math, segmented inference, overlap and analyzed-tail coverage
are unchanged. Prefix truncation is explicitly reported, not hidden.
The reference snapshot was copied from the existing exact local cache; no download.
Seven snapshot hashes and five extractor-module hashes are in model_config.json.

LR recipe frozen before BASE_TRAIN extraction:
solver=lbfgs; penalty=l2; C=1.0; class_weight=balanced; max_iter=1000;
random_state=1701; fit_intercept=True. lbfgs seed effect is limited, but recorded.
Manifest SHA-256: 9cdd5ecdd80f9ac3c8f05db63742721f4537ca2b64a2fe48f6c2b424b57483a6.
BASE_TRAIN: 1135, positive=183, negative=952. No CALIBRATION/VALIDATION scorer fitting.
Converged, n_iter=193. Coefficients, in the frozen order:
```json
[
  -0.008487385019663745,
  -0.021803155584697323,
  -0.021803155584697323,
  -0.193984515248614,
  0.23666581921164648,
  0.41118054978520263,
  -0.008487385019663745,
  0.7057740270166308,
  -1.8702543499336501,
  2.918165220807766
]
```
LR intercept: -2.8543400579338614.
Artifact: artifacts/models/ds_v1/scorer.joblib.
Scorer SHA-256: `2a68f2cdff57da7c9bc7b94c9bedbb712f4a2597a70efa90892ec78e319ccdd7`.
Schema/model/scorer/training metadata bound by integrity_manifest.json.
Hash-bound artifact bytes are preserved across Git checkout, including CRLF JSON.

## Calibration And Decision

Version ds_v1_cal_v1; Platt sigmoid on clipped LR class-1 log-odds.
Slope 1.268563607221541; intercept -1.5257967190918829; epsilon 1e-12.
Only CALIBRATION: 233, positive=41, negative=192. Scorer not retrained.
Calibrator SHA-256: `b71a64cd3cb2f1cfc8d3a256caade709e68ce01f2dcd267e29617b92831ff9eb`.
Separate calibration integrity manifest and scorer-binding hashes.
raw_score = uncalibrated LR class-1 probability; higher means adversarial-input risk.
calibrated_probability = frozen sigmoid mapping, never raw copied as calibrated.
binary_vote = calibrated_probability >= 0.5, DEFAULT DEVELOPMENT CUTPOINT.
Final operating point: NOT FROZEN. No threshold optimization.

## Runtime And Limits

Offline strict artifact loading; scorer/calibrator/reference loaded once and reused.
Set STATISTICAL_MODEL_DIR=artifacts/models/ds_v1 for the scored service path.
Absent configuration explicitly retains legacy evidence-only v0.1 mode; missing
artifacts when ds_v1 is configured fail, never downgrade to legacy scoring.
The artifact recipe controls all extraction parameters; only device may be selected.
Empty input is schema-rejected; too-short unscoreable inputs remain insufficient_input
with null probabilities/vote. Other scoring failures are explicit.
Training/scorer freeze commit cdf14a0; calibration freeze commit 5fac44c.
Development validation happened once after both commits; no fit followed it.
The development corpus is narrow. The scorer is trained on the current approved development distribution; no protected evaluation, distribution-shift or adaptive-attack claim follows. Calibration diagnostics are fitting-partition only. Final operating thresholds are NOT FROZEN. The reference LM and statistical feature extractor were not trained or changed.
