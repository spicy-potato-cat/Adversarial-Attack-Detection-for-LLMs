# TECH-STAT-005 Subgroup Analysis v1

Status: **PASS**. Diagnostic analysis only, using the frozen length groups and
the three predeclared scorers on 1,135 BASE_TRAIN OOF records.
Run code: `f123a46c320075a52ef0af3d09e2de734e4895f9`.
No subgroup-specific fit, search, threshold tuning or recalibration occurred.

## Scope And Denominators

Thresholds are each scorer's **pooled** descriptive 1%/3%/5% frontier, not
thresholds fitted within subgroups. A pooled 3% FPR does not imply 3% FPR in
each subgroup. Counts below sum to the aggregate confusion counts.

| Input tokens | Positive | Negative | Total |
|---|---:|---:|---:|
| <16 | 26 | 737 | 763 |
| 16-31 | 59 | 155 | 214 |
| 32-63 | 55 | 43 | 98 |
| 64+ | 43 | 17 | 60 |
| Total | 183 | 952 | 1135 |

Combined <32: 85 positive / 892 negative. This overlaps the first two groups
and must not be added to the total. Token counts and group definitions are
unchanged from STAT-004.

## Bucket Results

TP and FP triples are counts at pooled 1% / 3% / 5% budgets. Recall/FPR
columns are subgroup rates at the pooled 3% point. FN = positive minus TP;
TN = negative minus FP. Complete confusion counts and rates at all three
frontiers are in `subgroup_analysis_v1.json`.

| Scorer | Tokens | TP 1 / 3 / 5 | FP 1 / 3 / 5 | Recall at pooled 3% | Subgroup FPR at pooled 3% |
|---|---|---|---|---:|---:|
| S0 LR | <16 | 0 / 0 / 0 | 0 / 0 / 0 | 0.00% | 0.00% |
| S0 LR | 16-31 | 3 / 18 / 27 | 0 / 6 / 15 | 30.51% | 3.87% |
| S0 LR | 32-63 | 28 / 45 / 50 | 3 / 10 / 16 | 81.82% | 23.26% |
| S0 LR | 64+ | 29 / 37 / 38 | 6 / 12 / 15 | 86.05% | 70.59% |
| S1 SVM | <16 | 0 / 0 / 0 | 0 / 0 / 1 | 0.00% | 0.00% |
| S1 SVM | 16-31 | 3 / 13 / 26 | 0 / 5 / 12 | 22.03% | 3.23% |
| S1 SVM | 32-63 | 32 / 43 / 51 | 4 / 13 / 19 | 78.18% | 30.23% |
| S1 SVM | 64+ | 14 / 30 / 35 | 5 / 9 / 11 | 69.77% | 52.94% |
| S2 HGB | <16 | 0 / 0 / 1 | 0 / 4 / 7 | 0.00% | 0.54% |
| S2 HGB | 16-31 | 8 / 24 / 29 | 3 / 9 / 18 | 40.68% | 5.81% |
| S2 HGB | 32-63 | 33 / 48 / 50 | 2 / 7 / 11 | 87.27% | 16.28% |
| S2 HGB | 64+ | 28 / 34 / 35 | 4 / 7 / 8 | 79.07% | 41.18% |

Combined <32, at the pooled 3% point: LR 18/85 attacks (21.18%) with 6/892
FPs (0.67%); SVM 13/85 (15.29%) with 5/892 (0.56%); HGB 24/85 (28.24%)
with 13/892 (1.46%). HGB's short-input improvement is in the 16-31 group,
not the under-16 group, and comes with more short-benign FPs.

## Within-Scorer Score Summaries

Entries are q25 / median / q75. Full count, minimum, maximum and q90 for both
classes, including combined <32, are retained in the JSON artifact. SVM scores
are margins; LR/HGB scores are uncalibrated class-1 outputs. Score magnitudes
must **not** be compared as calibrated probabilities across families.

| Scorer | Tokens | Positive score q25 / median / q75 | Negative score q25 / median / q75 |
|---|---|---|---|
| S0 | <16 | 0.08996 / 0.22096 / 0.30137 | 0.04645 / 0.11063 / 0.20446 |
| S0 | 16-31 | 0.57744 / 0.75993 / 0.86763 | 0.33909 / 0.46854 / 0.67560 |
| S0 | 32-63 | 0.87348 / 0.93344 / 0.97742 | 0.49517 / 0.68355 / 0.84440 |
| S0 | 64+ | 0.90986 / 0.96631 / 0.99993 | 0.83820 / 0.88551 / 0.93938 |
| S1 | <16 | -1.15241 / -1.03119 / -0.86421 | -1.28169 / -1.12455 / -0.95403 |
| S1 | 16-31 | 0.21142 / 0.57754 / 0.98706 | -0.50383 / -0.05125 / 0.47997 |
| S1 | 32-63 | 1.05885 / 1.36529 / 1.54835 | -0.14359 / 0.47443 / 1.09004 |
| S1 | 64+ | 0.91356 / 1.11393 / 1.39630 | 0.57153 / 1.13376 / 1.47566 |
| S2 | <16 | 0.000458 / 0.002195 / 0.008455 | 0.000352 / 0.001096 / 0.004545 |
| S2 | 16-31 | 0.04976 / 0.41823 / 0.83622 | 0.00330 / 0.03028 / 0.19488 |
| S2 | 32-63 | 0.79832 / 0.98698 / 0.99890 | 0.04036 / 0.13951 / 0.48162 |
| S2 | 64+ | 0.83408 / 0.99447 / 0.99878 | 0.29091 / 0.43009 / 0.86299 |

## Critical Weaknesses

**Under 16 tokens:** all three miss all 26 attacks at both the pooled 1% and
3% points. At 5%, HGB catches one; LR and SVM still catch zero. Changing
scorer family with these fixed configurations therefore does not resolve this
development weakness. This does not prove that every nonlinear scorer or B2
representation is intrinsically incapable of detecting short attacks.

**64+ benign:** LR flags 12/17 (70.59%), SVM 9/17 (52.94%), HGB 7/17
(41.18%) at their own pooled <=3% points. HGB reduces the count by five but
still flags seven. These 17 examples are too small for broad population claims.
Long-attack recall also decreases versus LR: SVM 30/43 and HGB 34/43,
compared with LR 37/43. A lower long-benign FP count is not a cost-free gain.

## Error Banks And Conclusion

At the respective pooled <=3% frontiers, 61 attacks are missed by all three:
26 under-16, 28 in 16-31, 2 in 32-63 and 5 in 64+. Thus 54/61 shared FNs
are under 32 tokens. Exact IDs, transitions and unique catches are in
`error_transition_v1.json`; no raw prompt review or semantic/guard residual
analysis was performed.

HGB recovers 20 LR FNs but introduces 14, and recovers 15 LR FPs but
introduces 14. SVM recovers 11 LR FNs but introduces 25, and recovers 10 LR
FPs but introduces 9. LR/SVM/HGB unique catches are 9/2/11. These describe
**within-D_S** diversity only and do not justify stack-level promotion.

The frozen rule selects LR. Recommend Commander consideration of the one
remaining substantive cycle to address residual weaknesses. No cycle-2 work,
final fitting, calibration, protected experiments or cross-detector comparison
has started.
