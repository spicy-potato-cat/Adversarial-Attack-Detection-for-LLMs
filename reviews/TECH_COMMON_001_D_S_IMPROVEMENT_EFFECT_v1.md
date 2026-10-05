# TECH-COMMON-001 D_S Improvement Effect

DEVELOPMENT COMMON-MODE CHARACTERIZATION. Candidate-minus-baseline deltas.

## 1% FPR budget

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

## 3% FPR budget

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

## 5% FPR budget

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

Improved standalone D_S discrimination does not by itself establish preserved statistical complementarity. Measured D_S/D_M-B joint failures and overlap are descriptive evidence only. D_S/D_G JFN/EJF/Jaccard, all-detector JFN and D_S exclusive catches cannot be concluded without D_G. No causal or final-performance claim is supported. NOT READY FOR FULL REPORT RESULTS INTEGRATION; partial two-detector development tables may be used only with this limitation.
