# TECH-STAT-004 Short-Prompt Analysis

Status: **PASS - completed descriptive analysis, with residual limitations.**
All evidence is BASE_TRAIN OOF; no calibrated or deployment policy is selected.
Length buckets remain<16,16-31,32-63,64+ input tokens. Final run used20000
consistently, with unchanged feature definitions and fold-local references.

## Pooled <=3% Frontier By Bucket

Each block's pooled frontier is applied to its bucket rows; these are NOT
separately tuned per-bucket operating points. Cells: **TP / FP**. Denominators
in headers are positives/negatives. FN=positive-TP; TN=negative-FP.

| Block | <16 (26/737) | 16-31 (59/155) | 32-63 (55/43) | 64+ (43/17) |
|---|---|---|---|---|
| B0 | 1/6 | 9/8 | 22/7 | 27/7 |
| B1 | 0/0 | 8/7 | 46/11 | 28/4 |
| B2 | 0/0 | 18/6 | 45/10 | 37/12 |
| B3 | 0/0 | 18/6 | 45/10 | 37/12 |
| B4 | 0/0 | 16/5 | 45/10 | 37/11 |
| B5 | 0/0 | 13/7 | 43/10 | 34/11 |
| B6 | 0/0 | 24/13 | 43/11 | 35/4 |

Selected B2 vsB0, rates in percent:

| Bucket | B0 Recall | B2 Recall | B0 FPR | B2 FPR |
|---|---:|---:|---:|---:|
| <16 | 3.85 | **0.00** | 0.81 | 0.00 |
| 16-31 | 15.25 | **30.51** | 5.16 | **3.87** |
| 32-63 | 40.00 | 81.82 | 16.28 | 23.26 |
| 64+ | 62.79 | 86.05 | 41.18 | **70.59** |
| Combined<32 (85/892) | 11.76 | **21.18** | 1.57 | **0.67** |

B2 improves combined-short recall9.41pp while reducing short-benign FP8 rows.
The gain is confined to16-31 tokens, not ultra-short attacks. All26<16
positives remain missed at this frontier. B1 length conditioning alone loses
combined-short recall and fails the predeclared selection guard. Distribution
summaries in B2 recover16-31 behavior; extra blocks are not uniformly helpful.

## Raw0.5 Diagnostic

Cells again TP/FP; not an optimized or deployed threshold.

| Block | <16 | 16-31 | 32-63 | 64+ |
|---|---|---|---|---|
| B0 | 5/101 | 29/57 | 47/29 | 42/16 |
| B2 | 1/13 | 52/70 | 55/31 | 40/17 |

Combined-short raw recall34/85=40.00% becomes53/85=62.35%; FP158/892=17.71%
becomes83/892=9.30%. This aggregate hides<16 recall declining5/26 to1/26
and16-31 benign FP increasing57 to70. Raw0.5 never chose the representation.

## Score Distributions

Median/q90 OOF raw scores; not calibrated risks. Complete count/min/q25/median/
q75/q90/max summaries for both classes, all blocks and buckets are frozen in
`short_prompt_analysis_v1.json`, alongside raw and pooled1/3/5% counts/rates.

| Bucket | B0 Positive | B2 Positive | B0 Negative | B2 Negative |
|---|---|---|---|---|
| <16 | .35659/.68692 | .22096/.38392 | .29007/.55369 | .11063/.31783 |
| 16-31 | .49016/.82967 | .75993/.89898 | .41417/.71786 | .46854/.77729 |
| 32-63 | .73746/.92986 | .93344/.99420 | .57612/.83104 | .68355/.91614 |
| 64+ | .90115/.99999993 | .96631/.99999484 | .76543/.90207 | .88551/.95812 |

## Interpretation And Limits

Pooled attained FPR2.94% is heavily influenced by737<16 benign rows. It does
not bound subgroup FPR:64+ has only17 benign rows,12 falsely positive under
B2's pooled3% frontier. The small denominator makes its70.59% estimate noisy,
but the observed increase is real descriptive evidence, not a hidden success.
32-63 FPR also rises7/43 to10/43. No per-bucket threshold or redesign is
authorized or performed in this phase.

B6 has higher16-31 recall24/59 but also13/155 FP, versus B2's18/59 and6/155.
Compact B2 meets the frozen combined-short guard and is within2pp of the best
eligible pooled frontiers, but this does not solve every length subgroup.
Selection on this same development fixture is not unbiased evaluation.
No hard-example oversampling, protected data, semantic-score inspection,
threshold tuning, or final ds_v2 training occurred.

Recommendation: carry forward B2 for separately authorized STAT-005 comparison,
while preserving the<16 blind spot and longer-benign FPR problem explicitly.
Complementarity and independent performance evaluation remain deferred.
