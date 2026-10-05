# TECH-STAT-002 Training Report v1

Date: 2026-10-02. Status: PASS.

## Data And Frozen Recipe

Manifest integrity passed; expected and actual:
9cdd5ecdd80f9ac3c8f05db63742721f4537ca2b64a2fe48f6c2b424b57483a6.
BASE_TRAIN only: 1135; positive 183; negative 952.
Approved sources: Do-Not-Answer and deepset Prompt Injection only.
Selected original text hashes and deepset source labels match the authoritative
manifest. Source-container hashes are checked before/after and against prior
frozen source evidence. Membership/source/revision/rights/label/lineage metadata
is checked across partitions; only current selected text is scored.
Original CSV/Parquet containers necessarily contain other rows; loaders access
selected text/label scalars for extraction, not the mixed-source normalized archive.

Feature order (10, preserved from the existing export):
`whole_prompt_nll, whole_prompt_ppl, global_perplexity, mean_window_perplexity, max_window_perplexity, std_window_perplexity, mean_surprisal, max_surprisal, surprisal_std, high_surprisal_ratio`.
Schema SHA-256: 2b042f88e7403985e5f94e34bb1107b377069e591322767a482a33b5e2cbf8b7.
Identity normalization; no scaling, log transform, imputation or selection.
No latency or source/label metadata in X. Compatibility aliases retained.
BASE_TRAIN matrix shape: (1135, 10); labels in the same manifest row order.
Matrix/order hashes and raw source hashes are in training_metadata.json.
Feature extraction failures: 0. Nonfinite values: 0.
Feature extraction runtime: 50.505 seconds.

Recipe specified and committed before fit:
LogisticRegression(lbfgs, l2, C=1.0, class_weight=balanced, max_iter=1000,
random_state=1701, fit_intercept=True). One scorer; no bakeoff/selection/search.
Feature schema and recipe were frozen before any training text extraction.

## Fit And Freeze

Scorer fit runtime: 0.061362 seconds.
Convergence: PASS; n_iter=[193], no convergence warning.
Coefficients/intercept recorded in training_metadata.json and model-freeze report.
Class orientation verified: classes_=[0,1], score column 1 means adversarial class.
Artifact: artifacts/models/ds_v1/scorer.joblib; SHA-256:
2a68f2cdff57da7c9bc7b94c9bedbb712f4a2597a70efa90892ec78e319ccdd7.
Saved/reloaded scorer gives exactly the same BASE_TRAIN probabilities.
Fit source commit: 1a7cd67c36758cda4415d22ddc4360764b15cf19.
Scorer frozen/committed at cdf14a0 before calibration and validation.

CALIBRATION used for scorer training: NO.
VALIDATION used for scorer training: NO.
Protected data used: NO. Reference LM training: NO. Extractor changes: NO.
No post-validation retraining or recipe changes occurred.

## Environment And Scope

Python 3.11.9; Torch 2.6.0+cpu; Transformers 4.49.0; sklearn 1.6.1;
NumPy 2.1.3; SciPy 1.17.1; joblib 1.6.0; CPU 8 threads.
No package changes; reference weights reused locally, not downloaded.
The development corpus is narrow. The scorer is trained on the current approved development distribution; no protected evaluation, distribution-shift or adaptive-attack claim follows. Calibration diagnostics are fitting-partition only. Final operating thresholds are NOT FROZEN. The reference LM and statistical feature extractor were not trained or changed.
