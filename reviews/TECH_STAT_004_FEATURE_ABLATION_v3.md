# TECH-STAT-004 FINAL REPORT

STATUS: **PASS - controlled development representation ablation accepted.**

This is not final D_S training, calibration, threshold selection, protected
evaluation, or a generalization claim. Earlier v1/v2 blocked reports and both
stopped-run directories remain unchanged.

## Repository And Fixture

Branch: `tech/stat-004`. Clean startup at
`5670f7780f084ce40545fa8c6b8a61100598d6a5`.
Final numerical correction committed before execution:
`e8533cba2379df67eeca9f5e54c7f1de26c4cd9f`.
This remains the authoritative model/run-code commit; a later acceptance
commit records the evidence and verification-only adapter, not the model run.
Original definition freeze: `2eed02d6257f0f55bd6e52e499dcc2017e8a728d`.

BASE_TRAIN: **1135 rows / 183 positives / 952 negatives**; five frozen
QUALITY-001 folds, 1134 canonical lineage groups, seed 1701.
Manifest SHA-256:
`9cdd5ecdd80f9ac3c8f05db63742721f4537ca2b64a2fe48f6c2b424b57483a6`.
Fold SHA-256:
`19dc0153cc257cc2331782d6dd61b7bb9fb8cb0ed88d3e782b69d5ba05c4bb8d`.
Identity and canonical-lineage leakage: **0**. Each block has exactly one
held-out prediction per sample: **7945 predictions = 7 x 1135**.

## Numerical Convergence

Original first ceiling: **1000**; B1/fold0 stopped.
Second ceiling: **5000**; B4/fold0 stopped.
Final authorized ceiling: **20000**, consistent across **all 35 fits**.
All scientific parameters unchanged: **YES**. LogisticRegression only;
lbfgs, L2, C=1, balanced weights, seed 1701, fit_intercept=True, tol=1e-4.
No scaling, normalization amendment, feature change, C search, solver or
tolerance change. No partial fitted models or mixed-cap metrics were reused.

| Block | Fold 0 | Fold 1 | Fold 2 | Fold 3 | Fold 4 |
|---|---:|---:|---:|---:|---:|
| B0 | 334 | 330 | 279 | 485 | 213 |
| B1 | 2670 | 3665 | 3960 | 2450 | 2658 |
| B2 | 4586 | 4125 | 5395 | 3755 | 5040 |
| B3 | 4922 | 5502 | 5844 | 3597 | 4983 |
| B4 | 5771 | 4432 | 5647 | 5254 | 4605 |
| B5 | 7026 | 7789 | 7832 | 5799 | 7020 |
| B6 | 9061 | 4106 | **9752** | 7418 | 8803 |

All 35 fits converged: **YES**; convergence warnings: **NONE**.
Maximum n_iter_: **9752, B6 fold 2**. Every fit's iteration ceiling, actual
iterations, convergence status, warning messages/status, and runtime are in
`lr_convergence_v1.json`. No fit reached 20000.
Recorded run runtime: **70.610557s**, excluding startup and acceptance checks.

The iteration-cap changes were numerical convergence corrections. No
feature-block or scorer-selection results were available before the final
authoritative ablation, so D_S remains in substantive improvement cycle 1.

## Feature Definitions And References

| Block | Total | Added | Cumulative Representation |
|---|---:|---:|---|
| B0 | 10 | 10 | Exact v1 statistical representation |
| B1 | 16 | 6 | Length-conditioned robust z and percentiles |
| B2 | 26 | 10 | Robust distribution summaries and top-tail means |
| B3 | 29 | 3 | Benign-reference exceedance densities |
| B4 | 33 | 4 | Contiguous anomaly-run statistics |
| B5 | 47 | 14 | Prefix/middle/tail statistics and contrasts |
| B6 | 67 | 20 | Valid 8/16/32/64-token multi-scale windows |
| B7 | - | - | PREDECLARED SKIPPED |

All names/order/formulas and seven schema hashes remain frozen. Exact
definition artifact SHA:
`a560a14b9a27ebd754d8b150d600e82aee99c46c6c7c5ff7e9f4d38801f9f4c2`.
The definition artifact retains its historical 1000 recipe; the separate
resume preflight explicitly records the actual 20000 numerical override.
Names, ordering, and block hashes are in `feature_block_definitions_v1.json`;
the selected ordered 26 names are in `selected_representation_v1.json`.

Five references were freshly fitted on their four training folds only,
before transformation; held-out identities were explicitly forbidden.
Only benign training rows fit medians, MADs, CDFs and token quantiles.
Sparse 64-127 bins pooled [3,2]; sparse 128+ bins pooled [4,3,2], in every
fold, with 45-51 benign rows. Other length bins required no pooling. Exact
training memberships, sparse fallback logs and values are in
`fold_references_v1.json` and reconstruct without classifier refits.

Deterministic token-surprisal cache reused only after SHA verification:
`02241c0b2de1941783187f398c82ce3e8a7ec0a67655ace10f13ced7c29a70b3`.
No raw payload reopening or LM inference was required for the final rerun.

## Aggregate Results

Recall and attained FPR are percentages. PR-AUC means average precision.
Frontiers are empirical descriptive ROC points, not deployed thresholds.

| Block | ROC-AUC | PR-AUC | Recall1% | FPR1% | Recall3% | FPR3% | Recall5% | FPR5% |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| B0 | 0.810086 | 0.576684 | 24.59 | 0.7353 | 32.24 | 2.9412 | 45.36 | 4.9370 |
| B1 | 0.885699 | 0.714874 | 36.61 | 0.9454 | 44.81 | 2.3109 | 59.02 | 4.8319 |
| **B2** | **0.896760** | **0.731587** | **32.79** | **0.9454** | **54.64** | **2.9412** | **62.84** | **4.8319** |
| B3 | 0.896588 | 0.731500 | 32.79 | 0.9454 | 54.64 | 2.9412 | 62.84 | 4.7269 |
| B4 | 0.896031 | 0.729747 | 33.88 | 0.9454 | 53.55 | 2.7311 | 62.84 | 4.9370 |
| B5 | 0.895693 | 0.718025 | 31.69 | 0.9454 | 49.18 | 2.9412 | 60.11 | 4.9370 |
| B6 | 0.898138 | 0.726537 | 30.05 | 0.9454 | 55.74 | 2.9412 | 61.20 | 4.6218 |

Corresponding counts, ordered **TP / FP / FN / TN**:

| Block | At <=1% | At <=3% | At <=5% | Raw0.5 |
|---|---|---|---|---|
| B0 | 45/7/138/945 | 59/28/124/924 | 83/47/100/905 | 123/203/60/749 |
| B1 | 67/9/116/943 | 82/22/101/930 | 108/46/75/906 | 145/153/38/799 |
| B2 | 60/9/123/943 | 100/28/83/924 | 115/46/68/906 | 148/131/35/821 |
| B3 | 60/9/123/943 | 100/28/83/924 | 115/45/68/907 | 148/130/35/822 |
| B4 | 62/9/121/943 | 98/26/85/926 | 115/47/68/905 | 148/136/35/816 |
| B5 | 58/9/125/943 | 90/28/93/924 | 110/47/73/905 | 144/139/39/813 |
| B6 | 55/9/128/943 | 102/28/81/924 | 112/44/71/908 | 148/120/35/832 |

B0 reproduction: **PASS**, maximum score difference **0.0**, identical raw
confusion, ROC/AP, and fixed-FPR points to TECH-STAT-003. No forced adjustment.

## Fold Stability

These are per-fold frontiers, not the pooled frontier applied within folds.
Cells give recall **mean / population SD / min-max**, all in percentage points.

| Block | <=1% | <=3% | <=5% |
|---|---|---|---|
| B0 | 24.56/10.96/10.81-40.54 | 31.73/12.56/10.81-44.44 | 42.63/15.57/16.22-62.16 |
| B1 | 38.90/13.79/13.51-55.56 | 50.84/8.83/37.84-61.11 | 58.45/8.53/44.44-69.44 |
| B2 | 31.68/14.77/10.81-44.44 | 53.53/8.01/43.24-62.16 | 60.63/5.25/52.78-67.57 |
| B3 | 31.68/14.77/10.81-44.44 | 52.43/9.34/40.54-62.16 | 60.63/5.25/52.78-67.57 |
| B4 | 31.14/14.38/10.81-44.44 | 50.83/10.81/32.43-59.46 | 60.63/5.25/52.78-67.57 |
| B5 | 31.68/15.16/10.81-48.65 | 46.98/12.24/27.03-59.46 | 58.44/4.34/50.00-62.16 |
| B6 | 30.03/17.80/5.41-56.76 | 47.97/10.53/30.56-62.16 | 59.52/4.73/52.78-64.86 |

B2 folds 0-4 ROC-AUC: .915067/.858493/.923186/.887482/.901991;
AP: .684088/.745734/.793088/.757536/.656814.
B2 ROC mean/SD/range: .897244/.022848/.858493-.923186;
AP: .727452/.049835/.656814-.793088.
B2 <=3% attained FPR, folds 0-4: 2.6178/2.0942/2.6316/1.5789/2.6316%.
Complete 35-fold metrics, confusion/denominators, all frontier counts,
ROC/AP mean/SD/ranges and attained-FPR stability are machine-readable in
`block_fold_metrics_v1.json` and independently reconstruct from predictions.

## Selected Representation

**B2, 26 features**. Schema SHA:
`93d3892b158c35eccfadc27c879754db69ea5293782492ee5d4ff01a33bff983`.

Frozen eligibility required >=3pp pooled Recall3% gain, Recall1/5% within 2pp
of B0, AUC/AP within .01, fold3% SD/min guards, and short (<32) recall/FPR guards.
B1 fails only the combined-short recall guard. B2-B6 are eligible. B6 has
the best eligible pooled3% recall (55.74%), but B2 is the earliest eligible
block within 2pp of it at all three budgets. B2 also has better pooled 1/5%
recall and a tighter 3% fold range than B6. No later-block preference was used.
B3 matches B2's pooled recall with 3 extra features; later blocks do not
provide a material enough gain under the predeclared compactness rule.

## Short Prompts And Error Banks

At each block's pooled <=3% frontier, combined <32 recall improves from
**10/85=11.76% to18/85=21.18%**; short-benign FP falls from
**14/892=1.57% to 6/892=0.67%**. Gains are from 16-31 tokens.
**<16-token recall falls from 1/26 to 0/26**. For 64+, B2 FP rises 7/17 to 12/17;
the small denominator and strong length imbalance make pooled FPR inadequate
as a subgroup guarantee. The companion short-prompt report details all buckets.

| Comparator, B2 Versus B0 | FN Recovered | FP Recovered | New FN | New FP |
|---|---:|---:|---:|---:|
| Frozen raw0.5 banks, B2 raw0.5 | 33/60 | 117/203 | 8 | 45 |
| Frozen raw0.5 banks, B2 pooled3% | 7/60 | 175/203 | 30 | 0 |
| Matched pooled3% banks | 46/124 | 17/28 | 5 | 17 |

The matched-budget comparison recovers 41 net positives at the same 28 FP.
Raw0.5 comparisons are diagnostic only and did not select B2. Banks were not
duplicated or oversampled. All blocks' counts and traceable sample IDs are
in `error_bank_transition_v1.json`.

## Paired Comparisons

1000 paired canonical-lineage-group resamples, seed 1701, recomputing each
resample's 3% frontier. Difference vs B0, with conditional 95% percentile intervals:

| Block | Recall3% Difference | ROC-AUC Difference | AP Difference |
|---|---|---|---|
| B1 | .12568 [.05713,.28110] | .07561 [.04500,.10700] | .13819 [.09253,.18688] |
| B2 | .22404 [.12717,.32052] | .08667 [.05648,.11843] | .15490 [.10733,.20403] |
| B3 | .22404 [.12255,.31697] | .08650 [.05633,.11829] | .15482 [.10704,.20351] |
| B4 | .21311 [.11485,.31522] | .08595 [.05606,.11782] | .15306 [.10499,.20082] |
| B5 | .16940 [.07566,.26012] | .08561 [.05491,.11809] | .14134 [.09391,.18731] |
| B6 | .23497 [.09192,.32749] | .08805 [.05597,.12161] | .14985 [.09996,.19934] |

Conditional fixed-OOF intervals exclude model refit/shared-training uncertainty
and multiplicity/selection adjustment. The representation was selected on the
same development fixture: these are not unbiased final-performance intervals,
deployment-FPR guarantees, or evidence of complementarity.

## Verification And Artifacts

- Pre-run 145 tests passed; post-run 145 tests passed; final acceptance 148 tests
  passed including 3 verification-adapter tests. Zero failures/errors/skips.
- Authoritative ablation output hashes: 9/9; original STAT-003 output hashes: 9/9.
- Baseline preservation 96/96; opaque STAT/SEM preservation 54/54;
  prior STAT-004 artifacts/reports 20/20. Baseline tracked diff empty.
- Aggregate, short, error, selection, per-fold metrics and reference values
  reconstruct; all 35 convergence records bind to fold reports; the 1000-resample
  paired output reconstructs byte-for-byte; no classifier refit in acceptance.
- The frozen checker initially failed on a missing `baseline.digest_ids` alias.
  `statistical_feature_ablation_acceptance` supplies the already-existing
  canonical helper only during verification, then restores module state.
  Run code/hashes and outputs were not changed. This is verification plumbing,
  not another scientific correction or model run. Use that adapter command.

Final results live in `artifacts/statistical_v2/feature_ablation/resume_20000/`:
block metrics/fold metrics/predictions, short analysis, error transitions,
selection, references, convergence, paired comparisons, immutable run metadata,
start/preflight, tests and acceptance evidence. No raw text or checkpoints.
Companions: `TECH_STAT_004_SHORT_PROMPT_ANALYSIS_v3.md` and
`TECH_STAT_004_TEST_REPORT_v3.md`. Previous directories/reports are preserved.

## Governance And Recommendation

D_S cycle: **1/2**; LogisticRegression only; complementarity **DEFERRED**.
CALIBRATION, VALIDATION, INTERNAL_TEST, FROZEN_EXTERNAL/FINAL_TEST,
E1-E10, other detector outputs and semantic residuals: **NOT USED**.
Final ds_v2: **NOT CREATED**. STAT-005: **NOT STARTED**. No push.
Frozen detectors, calibration artifacts and central service remain untouched.

**READY FOR TECH-STAT-005 SCORER COMPARISON**, using B2's frozen representation
as the accepted development candidate. This does not authorize execution or
production promotion. Preserve the ultra-short blind spot, subgroup-FPR issues,
and low-FPR fold variability in any later decision. Do not train final ds_v2.
