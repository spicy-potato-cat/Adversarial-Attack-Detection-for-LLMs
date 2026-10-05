# TECH-COMMON-001 DEVELOPMENT COMMON-MODE CHARACTERIZATION

Status: **PARTIAL_D_G_UNMEASURED**. Not final/protected research performance.

1,135 aligned BASE_TRAIN samples: 183 positive, 952 negative. D_S v1, B2+LR and D_M-B v1 are frozen OOF predictions; each sample was held out from its scoring model. Same five QUALITY-001 folds, zero canonical-lineage leakage. D_G is externally frozen without project BASE_TRAIN fitting, but its scores are unavailable here.

Whole tied score blocks, inclusive >=, maximal recall under each budget, then minimum FPR, then highest threshold. Every detector selects its own descriptive point; no deployment threshold is frozen. FN Jaccard is zero for empty unions; conditional recovery is null for empty denominators. Counts and rates refer to attacks; unique-catch rates use all 183 attacks. Independence is an algebraic reference, not an asserted model of detector independence.

The candidate is DEVELOPMENT_STACK_CANDIDATE, not final research_stack_v2. Three-detector stack JFN and unique catches remain UNMEASURED; pairwise D_S/D_M-B evidence does not answer guard complementarity. Source/fold breakdowns apply unchanged pooled thresholds. Attack family is unavailable in consumed metadata and was not manufactured. Source comparisons are not frozen R1 experiments.

## At 1% FPR budget

TABLE A — individual (rates are fractions).

| detector | fpr | fnr | recall | tp | fp | fn | tn |
|---|---|---|---|---|---|---|---|
| D_M-B_v1 | 0.007353 | 0.032787 | 0.967213 | 177 | 7 | 6 | 945 |
| D_S_B2_LR | 0.009454 | 0.672131 | 0.327869 | 60 | 9 | 123 | 943 |
| D_S_v1 | 0.007353 | 0.754098 | 0.245902 | 45 | 7 | 138 | 945 |


TABLE B — pairwise (D_S-v1 versus B2 is representation transition context).

| left | right | fnr_i | fnr_j | jfn_count | jfn | independence_reference | ejf | fn_jaccard |
|---|---|---|---|---|---|---|---|---|
| D_M-B_v1 | D_S_B2_LR | 0.032787 | 0.672131 | 5 | 0.027322 | 0.022037 | 0.005285 | 0.040323 |
| D_M-B_v1 | D_S_v1 | 0.032787 | 0.754098 | 6 | 0.032787 | 0.024725 | 0.008062 | 0.043478 |
| D_S_B2_LR | D_S_v1 | 0.672131 | 0.754098 | 111 | 0.606557 | 0.506853 | 0.099704 | 0.740000 |


TABLE C — primary stack.

| stack | all_detector_jfn | all_detector_fn_count |
|---|---|---|
| DEVELOPMENT_STACK_CANDIDATE | UNMEASURED | UNMEASURED |
| DEVELOPMENT_STACK_V1 | UNMEASURED | UNMEASURED |


TABLE D — unique catches.

| stack | detector | unique_catch_count | unique_catch_rate | recovery_given_others_miss |
|---|---|---|---|---|
| DEVELOPMENT_STACK_CANDIDATE | D_S_B2_LR | UNMEASURED | UNMEASURED | UNMEASURED |
| DEVELOPMENT_STACK_CANDIDATE | D_M-B_v1 | UNMEASURED | UNMEASURED | UNMEASURED |
| DEVELOPMENT_STACK_CANDIDATE | D_G_v1 | UNMEASURED | UNMEASURED | UNMEASURED |
| DEVELOPMENT_STACK_V1 | D_S_v1 | UNMEASURED | UNMEASURED | UNMEASURED |
| DEVELOPMENT_STACK_V1 | D_M-B_v1 | UNMEASURED | UNMEASURED | UNMEASURED |
| DEVELOPMENT_STACK_V1 | D_G_v1 | UNMEASURED | UNMEASURED | UNMEASURED |


TABLE E — candidate minus v1.

| metric | other | baseline | candidate | delta |
|---|---|---|---|---|
| jfn | D_M-B_v1 | 0.032787 | 0.027322 | -0.005464 |
| ejf | D_M-B_v1 | 0.008062 | 0.005285 | -0.002777 |
| fn_jaccard | D_M-B_v1 | 0.043478 | 0.040323 | -0.003156 |
| jfn | D_G_v1 | UNMEASURED | UNMEASURED | UNMEASURED |
| ejf | D_G_v1 | UNMEASURED | UNMEASURED | UNMEASURED |
| fn_jaccard | D_G_v1 | UNMEASURED | UNMEASURED | UNMEASURED |
| all_detector_jfn | primary_stack | UNMEASURED | UNMEASURED | UNMEASURED |
| all_detector_fn_count | primary_stack | UNMEASURED | UNMEASURED | UNMEASURED |
| unique_catch_count | primary_stack | UNMEASURED | UNMEASURED | UNMEASURED |
| unique_catch_rate | primary_stack | UNMEASURED | UNMEASURED | UNMEASURED |
| recovery_given_others_miss | primary_stack | UNMEASURED | UNMEASURED | UNMEASURED |

## At 3% FPR budget

TABLE A — individual (rates are fractions).

| detector | fpr | fnr | recall | tp | fp | fn | tn |
|---|---|---|---|---|---|---|---|
| D_M-B_v1 | 0.023109 | 0.021858 | 0.978142 | 179 | 22 | 4 | 930 |
| D_S_B2_LR | 0.029412 | 0.453552 | 0.546448 | 100 | 28 | 83 | 924 |
| D_S_v1 | 0.029412 | 0.677596 | 0.322404 | 59 | 28 | 124 | 924 |


TABLE B — pairwise (D_S-v1 versus B2 is representation transition context).

| left | right | fnr_i | fnr_j | jfn_count | jfn | independence_reference | ejf | fn_jaccard |
|---|---|---|---|---|---|---|---|---|
| D_M-B_v1 | D_S_B2_LR | 0.021858 | 0.453552 | 3 | 0.016393 | 0.009914 | 0.006480 | 0.035714 |
| D_M-B_v1 | D_S_v1 | 0.021858 | 0.677596 | 4 | 0.021858 | 0.014811 | 0.007047 | 0.032258 |
| D_S_B2_LR | D_S_v1 | 0.453552 | 0.677596 | 78 | 0.426230 | 0.307325 | 0.118905 | 0.604651 |


TABLE C — primary stack.

| stack | all_detector_jfn | all_detector_fn_count |
|---|---|---|
| DEVELOPMENT_STACK_CANDIDATE | UNMEASURED | UNMEASURED |
| DEVELOPMENT_STACK_V1 | UNMEASURED | UNMEASURED |


TABLE D — unique catches.

| stack | detector | unique_catch_count | unique_catch_rate | recovery_given_others_miss |
|---|---|---|---|---|
| DEVELOPMENT_STACK_CANDIDATE | D_S_B2_LR | UNMEASURED | UNMEASURED | UNMEASURED |
| DEVELOPMENT_STACK_CANDIDATE | D_M-B_v1 | UNMEASURED | UNMEASURED | UNMEASURED |
| DEVELOPMENT_STACK_CANDIDATE | D_G_v1 | UNMEASURED | UNMEASURED | UNMEASURED |
| DEVELOPMENT_STACK_V1 | D_S_v1 | UNMEASURED | UNMEASURED | UNMEASURED |
| DEVELOPMENT_STACK_V1 | D_M-B_v1 | UNMEASURED | UNMEASURED | UNMEASURED |
| DEVELOPMENT_STACK_V1 | D_G_v1 | UNMEASURED | UNMEASURED | UNMEASURED |


TABLE E — candidate minus v1.

| metric | other | baseline | candidate | delta |
|---|---|---|---|---|
| jfn | D_M-B_v1 | 0.021858 | 0.016393 | -0.005464 |
| ejf | D_M-B_v1 | 0.007047 | 0.006480 | -0.000567 |
| fn_jaccard | D_M-B_v1 | 0.032258 | 0.035714 | 0.003456 |
| jfn | D_G_v1 | UNMEASURED | UNMEASURED | UNMEASURED |
| ejf | D_G_v1 | UNMEASURED | UNMEASURED | UNMEASURED |
| fn_jaccard | D_G_v1 | UNMEASURED | UNMEASURED | UNMEASURED |
| all_detector_jfn | primary_stack | UNMEASURED | UNMEASURED | UNMEASURED |
| all_detector_fn_count | primary_stack | UNMEASURED | UNMEASURED | UNMEASURED |
| unique_catch_count | primary_stack | UNMEASURED | UNMEASURED | UNMEASURED |
| unique_catch_rate | primary_stack | UNMEASURED | UNMEASURED | UNMEASURED |
| recovery_given_others_miss | primary_stack | UNMEASURED | UNMEASURED | UNMEASURED |

## At 5% FPR budget

TABLE A — individual (rates are fractions).

| detector | fpr | fnr | recall | tp | fp | fn | tn |
|---|---|---|---|---|---|---|---|
| D_M-B_v1 | 0.035714 | 0.010929 | 0.989071 | 181 | 34 | 2 | 918 |
| D_S_B2_LR | 0.048319 | 0.371585 | 0.628415 | 115 | 46 | 68 | 906 |
| D_S_v1 | 0.049370 | 0.546448 | 0.453552 | 83 | 47 | 100 | 905 |


TABLE B — pairwise (D_S-v1 versus B2 is representation transition context).

| left | right | fnr_i | fnr_j | jfn_count | jfn | independence_reference | ejf | fn_jaccard |
|---|---|---|---|---|---|---|---|---|
| D_M-B_v1 | D_S_B2_LR | 0.010929 | 0.371585 | 2 | 0.010929 | 0.004061 | 0.006868 | 0.029412 |
| D_M-B_v1 | D_S_v1 | 0.010929 | 0.546448 | 2 | 0.010929 | 0.005972 | 0.004957 | 0.020000 |
| D_S_B2_LR | D_S_v1 | 0.371585 | 0.546448 | 58 | 0.316940 | 0.203052 | 0.113888 | 0.527273 |


TABLE C — primary stack.

| stack | all_detector_jfn | all_detector_fn_count |
|---|---|---|
| DEVELOPMENT_STACK_CANDIDATE | UNMEASURED | UNMEASURED |
| DEVELOPMENT_STACK_V1 | UNMEASURED | UNMEASURED |


TABLE D — unique catches.

| stack | detector | unique_catch_count | unique_catch_rate | recovery_given_others_miss |
|---|---|---|---|---|
| DEVELOPMENT_STACK_CANDIDATE | D_S_B2_LR | UNMEASURED | UNMEASURED | UNMEASURED |
| DEVELOPMENT_STACK_CANDIDATE | D_M-B_v1 | UNMEASURED | UNMEASURED | UNMEASURED |
| DEVELOPMENT_STACK_CANDIDATE | D_G_v1 | UNMEASURED | UNMEASURED | UNMEASURED |
| DEVELOPMENT_STACK_V1 | D_S_v1 | UNMEASURED | UNMEASURED | UNMEASURED |
| DEVELOPMENT_STACK_V1 | D_M-B_v1 | UNMEASURED | UNMEASURED | UNMEASURED |
| DEVELOPMENT_STACK_V1 | D_G_v1 | UNMEASURED | UNMEASURED | UNMEASURED |


TABLE E — candidate minus v1.

| metric | other | baseline | candidate | delta |
|---|---|---|---|---|
| jfn | D_M-B_v1 | 0.010929 | 0.010929 | 0.000000 |
| ejf | D_M-B_v1 | 0.004957 | 0.006868 | 0.001911 |
| fn_jaccard | D_M-B_v1 | 0.020000 | 0.029412 | 0.009412 |
| jfn | D_G_v1 | UNMEASURED | UNMEASURED | UNMEASURED |
| ejf | D_G_v1 | UNMEASURED | UNMEASURED | UNMEASURED |
| fn_jaccard | D_G_v1 | UNMEASURED | UNMEASURED | UNMEASURED |
| all_detector_jfn | primary_stack | UNMEASURED | UNMEASURED | UNMEASURED |
| all_detector_fn_count | primary_stack | UNMEASURED | UNMEASURED | UNMEASURED |
| unique_catch_count | primary_stack | UNMEASURED | UNMEASURED | UNMEASURED |
| unique_catch_rate | primary_stack | UNMEASURED | UNMEASURED | UNMEASURED |
| recovery_given_others_miss | primary_stack | UNMEASURED | UNMEASURED | UNMEASURED |

## Measured interpretation

B2+LR reduces D_S/D_M-B shared misses from 6 to 5 at <=1% and from 4 to 3 at <=3%; both share 2 misses at <=5%. Each reduction is one attack (0.5464 percentage points). The paired conditional intervals include zero. At <=3% and <=5%, FN Jaccard increases despite fewer/unchanged shared misses because the D_S FN union shrinks. At <=5%, EJF increases because D_S marginal FNR decreases while both semantic misses remain shared. These distinctions prevent equating better standalone discrimination with less dependence. Full primary-stack reduction and statistical exclusive catches remain unmeasured without D_G.

## Uncertainty

1000 paired canonical attack-lineage percentile bootstrap replicates, seed 1701; same attacks in each detector/candidate comparison. Fixed pooled points are held unchanged. Conditional development uncertainty excludes model refitting, threshold selection, development selection and dependence from overlapping training folds. The canonical lineage minimum does not resolve full upstream semantic dependence. Small-count deltas must not be treated as robust population gains. Exact intervals are in bootstrap_intervals_v1.json.

| budget | estimate | lower | upper |
|---|---|---|---|
| 0.010000 | -0.005464 | -0.016393 | 0.000000 |
| 0.030000 | -0.005464 | -0.016393 | 0.000000 |
| 0.050000 | 0.000000 | 0.000000 | 0.000000 |

## Isolation

Detector training, CALIBRATION payloads, VALIDATION payloads, protected payloads, E1-E10, R2/R3 generation and verifier/router work: **NO**. No fusion or ensemble decision policy implemented. Existing detector source and evidence unchanged.
