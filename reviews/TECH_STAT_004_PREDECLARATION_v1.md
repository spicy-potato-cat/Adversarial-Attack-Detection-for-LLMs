# TECH-STAT-004 Predeclared Feature Ablation v1

Prepared before any project B1-B6 outcome was computed or inspected.
Accepted startup: `9b63a230943be3f47e812f6495a8f3435fdff642`, clean tree;
STAT-003 commit `6e88dfe` in ancestry. New branch: `tech/stat-004`.
Cycle: D_S substantive improvement **1 of maximum 2**.

Only frozen QUALITY-001 BASE_TRAIN rows (1,135; 183 positive/952 negative),
five existing canonical-lineage folds, seed 1701. No fold regeneration.
Only the frozen reference LM and fixed Logistic Regression recipe are used.
No D_M-A, D_M-B or D_G scores, semantic residuals or embeddings guide features.
Semantic/statistical prior artifacts are preserved with opaque hashes only.

## Frozen Blocks

| Block | Added | Total | Definition |
|---|---:|---:|---|
| B0 | 10 | 10 | Unchanged v1 ordered representation; exact frozen predictions/metrics must reproduce |
| B1 | 6 | 16 | Length-conditioned robust z and empirical percentile for NLL, maximum and standard deviation of surprisal |
| B2 | 10 | 26 | Median, unscaled MAD, IQR, q25/q75/q90/q95/q99, top-min(5,n) mean, top-ceil(.1n) mean |
| B3 | 3 | 29 | Strict exceedance fractions above benign training-token q90/q95/q99 |
| B4 | 4 | 33 | q95 anomaly runs/n, longest/n, mean length/n, singleton runs/anomalous tokens |
| B5 | 14 | 47 | Deterministic thirds: mean, median, q95 density and availability per region; tail/prefix and middle/prefix mean contrasts |
| B6 | 20 | 67 | Full 8/16/32/64-token windows, half-scale stride plus end anchor: max/median/IQR/top2 mean window NLL and availability |
| B7 | 0 | not tested | PREDECLARED-SKIPPED; no character/semantic structural features |

Window statistics use the numerically stable log-PPL domain of the inherited
causal surprisal sequence, not isolated-window rescoring or a new LM.
Unusable scales/empty regions use defined zero placeholders plus availability
flags, not learned imputation. Local windows are genuinely multi-scale and
overlapping, unlike the inherited one-window summaries on short prompts.

Length bins: <16, 16-31, 32-63, 64-127, 128+ input tokens, including the first
unscored token. Fit each fold's benign references only on its four training
folds. Minimum 20 benign rows per bin; sparse bins explicitly pool nearest bins,
index-distance ties lower first, until sufficient. Every fallback is logged.
No silent global fallback. Robust z uses MAD+1e-6 and is clipped to [-20,20].
Empirical CDF includes right-side ties; quantiles use linear interpolation.
Anomaly references are token-weighted benign quantiles within those pooled bins.

## Selection And Diagnostics

Primary selection is Recall@FPR<=3%, not raw 0.5 accuracy. Material improvement:
at least **3 absolute recall points over B0** at 3%. Preserve 1%/5% recall
within two points, ROC/AP within .01, fold 3% recall SD within +.03 and minimum
within -.03 of baseline. Short (<32) recall must not decline and short-benign
FPR at the pooled 3% point may increase by no more than two percentage points.

Among eligible blocks select the earliest within two recall points of the
best eligible 3% block and within two points of its 1%/5% recalls. If none is
eligible, retain B0 and report lack of supported representation improvement.
This is development selection, not independently validated final performance.

Short diagnostics: <16, 16-31, 32-63, 64+; fixed pooled operating points applied
to each bucket, not bucket-specific threshold searches. All denominators and
score distributions are explicit; absent classes yield null rates.

Error banks: frozen raw v1 60 FN/203 FP. Report recovery and new errors under
raw 0.5 and pooled 3% comparisons; also report matched B0-3% banks to distinguish
threshold movement from discrimination. No oversampling or extra training rows.

Paired canonical-lineage bootstrap: 1,000 replicates, seed 1701, identical
resampled indices across blocks; differences in Recall@3%, ROC-AUC and AP.
Conditional fixed-OOF uncertainty only: no refit/shared-training uncertainty or
multiplicity correction. Selection and thresholds remain descriptive.

## Execution And Isolation

STAT-003 runtime: 58.61 seconds. Estimate: **120-240 seconds**, using one frozen
CPU LM extraction followed by five reference fits/35 fixed LR fits and cached
token evidence. Extraction unexpectedly exceeding 150 seconds or fold execution
exceeding 300 seconds stops for Commander review. No automatic repeat.

Cache is local ignored `detection_service/outputs/stat004/token_evidence.npz`:
IDs, numeric surprisals, offsets and coverage only; no token strings/IDs or
prompt content. Learned references are fitted only after splitting training
folds. Original approved CSV/Parquet containers physically include other
partitions; only authorized BASE_TRAIN scalar locators/texts enter processing.

Run requires a clean tree and committed definition/code bytes. Commit this
predeclared package before outcomes, then:

```powershell
.\.local-python\python.exe -m detection_service.scripts.statistical_feature_ablation --mode run
```

No CALIBRATION/VALIDATION/protected experiment, E1-E10, final ds_v2, deployed
threshold, SVM/HGB or complementarity analysis. One further substantive redesign
cycle remains; it is not consumed automatically.
