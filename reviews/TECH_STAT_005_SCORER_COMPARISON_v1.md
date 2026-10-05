# TECH-STAT-005 Scorer Comparison v1

Status: **PASS**. Selected scorer: **S0 Logistic Regression**.
Recommendation: **RECOMMEND_D_S_CYCLE_2**, subject to Commander authorization.
No cycle-2 execution or final ds_v2 artifact is authorized by this report.

## Repository And Provenance

Branch: `tech/stat-005`. Clean authoritative startup:
`b09beb5340a4d6c21e165f4cb1b596cfc3657216`.
Definitions, selection rule, implementation and 169 passing pre-run tests were
committed before the authoritative run, at:
`f123a46c320075a52ef0af3d09e2de734e4895f9`.
The run began with a clean tree. The later acceptance commit contains evidence
and verification, not a different model-run provenance. Run metadata is not
rewritten to the acceptance commit.

The original STAT-004 1,000-iteration and 5,000-iteration failures, accepted
20,000-iteration evidence, STAT-003 and SEM-003 evidence remain unchanged.

## Frozen Fixture And Representation

BASE_TRAIN only: 1,135 rows, 183 positive and 952 negative; the same five frozen
QUALITY-001 folds, seed 1701. Identity and canonical-lineage leakage: **0**.
Every row has exactly one OOF score per scorer: **3,405 aligned scores**.

- Manifest SHA: `9cdd5ecdd80f9ac3c8f05db63742721f4537ca2b64a2fe48f6c2b424b57483a6`.
- Fold SHA: `19dc0153cc257cc2331782d6dd61b7bb9fb8cb0ed88d3e782b69d5ba05c4bb8d`.
- B2: unchanged 26-feature schema, SHA `93d3892b158c35eccfadc27c879754db69ea5293782492ee5d4ff01a33bff983`.
- Numerical cache SHA: `02241c0b2de1941783187f398c82ce3e8a7ec0a67655ace10f13ced7c29a70b3`.

Only integrity-checked numerical evidence and BASE_TRAIN metadata were consumed.
No LM extraction was repeated. Five fresh B2 reference sets were fitted on each
outer training set, never its held-out fold. SVM additionally fitted five fresh
training-only StandardScalers. No feature, reference definition, bin, quantile
or top-k definition changed. No B3+ feature entered any scorer.

## Predeclared Scorers And Selection

Exactly one configuration per family; all use training-label-derived balanced
class weights, with no resampling or parameter search:

- S0: LR, lbfgs, L2, C=1, balanced, seed 1701, max_iter=20000, tol=0.0001; no scaler.
- S1: training-only StandardScaler then SVC RBF, C=1, gamma=scale, balanced, seed 1701, probability=False. Scores are decision_function values, not probabilities.
- S2: HGB, learning_rate=0.1, max_iter=100, max_leaf_nodes=31, l2_regularization=0, early_stopping=False, seed 1701, native balanced weights; no scaler. OpenMP limited to one thread for reproducible, modest compute.

The complete estimator defaults and rule are frozen in
`artifacts/statistical_v2/scorer_comparison/scorer_definitions_v1.json`.
Non-LR eligibility requires at least +2pp pooled Recall@3%, a positive lower
bound on its conditional paired 95% interval, at most 2pp loss at 1%/5%, at
most 0.01 ROC/AP loss, at most 3pp fold-SD increase/fold-minimum loss, no loss
in under-16 recall, at most 2pp combined-short recall loss and at most one
additional long-benign FP. Among eligible candidates, prefer the predeclared
simpler family within 2pp of the best at all three frontiers. Otherwise retain
LR. Modest runtime differences do not disqualify a superior scorer.

## Aggregate Ranking Results

Recall and attained FPR columns are percentages, in budget order 1% / 3% / 5%.
PR-AUC is average precision. Fit/inference totals exclude reference construction,
bootstrap, repeated prediction checks and file verification.

| Scorer | ROC-AUC | PR-AUC | Recall 1 / 3 / 5 | Attained FPR 1 / 3 / 5 | Fit / inference seconds |
|---|---:|---:|---|---|---|
| S0 LR | 0.896760 | 0.731587 | 32.79 / 54.64 / 62.84 | 0.945 / 2.941 / 4.832 | 5.403561 / 0.001444 |
| S1 RBF-SVM | 0.882502 | 0.663912 | 26.78 / 46.99 / 61.20 | 0.945 / 2.836 / 4.517 | 0.105288 / 0.050434 |
| S2 HGB | 0.867791 | 0.724083 | 37.70 / 57.92 / 62.84 | 0.945 / 2.836 / 4.622 | 1.350091 / 0.024430 |

| Scorer | FPR budget | TP | FN | FP | TN |
|---|---:|---:|---:|---:|---:|
| S0 | 1% | 60 | 123 | 9 | 943 |
| S0 | 3% | 100 | 83 | 28 | 924 |
| S0 | 5% | 115 | 68 | 46 | 906 |
| S1 | 1% | 49 | 134 | 9 | 943 |
| S1 | 3% | 86 | 97 | 27 | 925 |
| S1 | 5% | 112 | 71 | 43 | 909 |
| S2 | 1% | 69 | 114 | 9 | 943 |
| S2 | 3% | 106 | 77 | 27 | 925 |
| S2 | 5% | 115 | 68 | 44 | 908 |

S0 reproduces accepted STAT-004 B2 **exactly**: maximum score difference 0.0;
ROC/AP and all three frontier counts are identical. All 15 fits completed with
no convergence warnings. LR iterations were 4586/4125/5395/3755/5040; all are
below 20000. SVM fits completed; HGB ran exactly its fixed 100 iterations.
Entire run: **19.831892 seconds**, below the predeclared 40-120 second estimate
and 300-second stop limit. No retry was used.

## Fold Stability

Each recall/FPR entry below is a percentage pair. Fold-specific frontiers differ
from the pooled frontier and are descriptive, not five deployment policies.

| Scorer | Fold | ROC-AUC | PR-AUC | R1 / FPR | R3 / FPR | R5 / FPR | Fit / inference seconds |
|---|---:|---:|---:|---|---|---|---|
| S0 | 0 | 0.9151 | 0.6841 | 16.67 / 0.524 | 44.44 / 2.618 | 52.78 / 4.712 | 1.1446 / 0.000351 |
| S0 | 1 | 0.8585 | 0.7457 | 44.44 / 0.000 | 58.33 / 2.094 | 63.89 / 3.141 | 1.0225 / 0.000279 |
| S0 | 2 | 0.9232 | 0.7931 | 43.24 / 0.526 | 62.16 / 2.632 | 67.57 / 4.211 | 1.2691 / 0.000265 |
| S0 | 3 | 0.8875 | 0.7575 | 43.24 / 0.526 | 59.46 / 1.579 | 62.16 / 4.737 | 0.8508 / 0.000293 |
| S0 | 4 | 0.9020 | 0.6568 | 10.81 / 0.526 | 43.24 / 2.632 | 56.76 / 4.211 | 1.1166 / 0.000257 |
| S1 | 0 | 0.9033 | 0.6261 | 2.78 / 0.524 | 38.89 / 2.618 | 47.22 / 4.712 | 0.0223 / 0.011301 |
| S1 | 1 | 0.8522 | 0.7196 | 33.33 / 0.000 | 52.78 / 2.618 | 61.11 / 3.665 | 0.0197 / 0.009092 |
| S1 | 2 | 0.9084 | 0.7427 | 27.03 / 0.526 | 59.46 / 2.632 | 67.57 / 4.211 | 0.0213 / 0.009730 |
| S1 | 3 | 0.8634 | 0.6133 | 8.11 / 0.000 | 40.54 / 2.632 | 54.05 / 4.211 | 0.0217 / 0.010694 |
| S1 | 4 | 0.8844 | 0.6477 | 8.11 / 0.000 | 45.95 / 2.632 | 56.76 / 4.211 | 0.0202 / 0.009617 |
| S2 | 0 | 0.9052 | 0.7667 | 38.89 / 0.524 | 63.89 / 2.618 | 77.78 / 4.712 | 0.3273 / 0.005413 |
| S2 | 1 | 0.8416 | 0.7175 | 50.00 / 0.524 | 61.11 / 2.618 | 61.11 / 2.618 | 0.2589 / 0.004857 |
| S2 | 2 | 0.8821 | 0.7407 | 45.95 / 0.526 | 56.76 / 2.632 | 62.16 / 3.684 | 0.2550 / 0.004994 |
| S2 | 3 | 0.8523 | 0.7187 | 45.95 / 0.526 | 48.65 / 1.053 | 51.35 / 4.211 | 0.2598 / 0.004652 |
| S2 | 4 | 0.8639 | 0.7094 | 29.73 / 0.526 | 51.35 / 2.632 | 62.16 / 4.737 | 0.2492 / 0.004514 |

| Scorer | Mean R3 | Population SD (pp) | Minimum R3 | Maximum R3 |
|---|---:|---:|---:|---:|
| S0 | 53.53% | 8.01 | 43.24% | 62.16% |
| S1 | 47.52% | 7.69 | 38.89% | 59.46% |
| S2 | 56.35% | 5.73 | 48.65% | 63.89% |

## Paired Comparisons

1,000 paired canonical-lineage-group bootstrap replicates, seed 1701, recompute
each scorer's descriptive frontier per replicate. Intervals are conditional on
these fixed OOF scores; they do not refit classifiers or account for shared
training, multiplicity, development selection or training instability.

| Comparison vs LR | Delta R3 (pp), 95% interval | Delta ROC-AUC, 95% interval | Delta PR-AUC, 95% interval |
|---|---|---|---|
| S1 | -7.65 [-19.67, +2.22] | -0.014258 [-0.025130, -0.003621] | -0.067675 [-0.104925, -0.031875] |
| S2 | +3.28 [-5.21, +13.02] | -0.028970 [-0.049644, -0.007163] | -0.007504 [-0.040741, +0.027156] |

HGB has the highest observed pooled R3 and better fold stability. Its observed
gain is not supported by a positive lower bound, and its ROC decline exceeds
the frozen 0.01 allowance. It fails those two guards, so cannot replace LR.
SVM fails the material-gain, paired-support, R1, AUC, AP, fold-minimum and
combined-short guards. Neither is rejected because of runtime.

## Subgroups And Error Transitions

At each scorer's own pooled <=3% frontier, all three detect **0/26 under-16
attacks**. Long-benign FPs: LR **12/17**, SVM **9/17**, HGB **7/17**. These
are small diagnostic subgroups, not population guarantees.
The separate subgroup report records all four buckets and score summaries.

| Compared with LR | LR FNs recovered | New FNs | LR FPs recovered | New FPs |
|---|---:|---:|---:|---:|
| S1 | 11 | 25 | 10 | 9 |
| S2 | 20 | 14 | 15 | 14 |

Shared FN across all three: **61**. Unique positive catches: LR **9**, SVM
**2**, HGB **11**. Exact ordered sample-ID banks are stored in
`error_transition_v1.json`; no raw prompts are duplicated. These are
within-D_S scorer-diversity counts, **not cross-detector complementarity**.

## Acceptance And Recommendation

PASS: frozen B2, identical five-fold population, 15 completed scorer fits, zero
leakage, exact LR reproduction, training-only references/scalers/weights,
complete ranking/subgroup/transition/paired analyses and exactly one selection.
Output hashes: 8/8. STAT-003 and accepted STAT-004 outputs: 9/9 each.
Preserved STAT/SEM/historical evidence: 101/101. Baseline preservation: 96/96.
Tests: 169/169 pre-run and post-run; expanded acceptance suite 177/177.

Candidate recipe ready: **YES**, B2 + unchanged S0 LR. Final ds_v2: **NO**.
Cycle: **1/2**. Calibration, CALIBRATION payloads, VALIDATION payloads,
protected data, other detector outputs and E1-E10: **NO**.
Cross-detector complementarity: **DEFERRED**; no D_S promotion is claimed.

Recommend **RECOMMEND_D_S_CYCLE_2**: scorer-family substitution does not
resolve the persistent very-short attack weakness, and selected LR still flags
12/17 long-benign records. This supports a Commander decision about the one
remaining substantive cycle, not unapproved tuning or a predetermined new
feature recipe. Development results are not unbiased final performance.
Stop here for Commander review. Do not train a final model or begin cycle 2.
