# TECH-COMMON-002 D_S Improvement Effect v2

| budget | metric | other | baseline | candidate | delta |
|---|---|---|---|---|---|
| 0.010000 | fnr | D_S | 0.754098 | 0.672131 | -0.081967 |
| 0.010000 | jfn | D_M-B_v1 | 0.032787 | 0.027322 | -0.005464 |
| 0.010000 | ejf | D_M-B_v1 | 0.008062 | 0.005285 | -0.002777 |
| 0.010000 | fn_jaccard | D_M-B_v1 | 0.043478 | 0.040323 | -0.003156 |
| 0.010000 | jfn | D_G_v1 | 0.606557 | 0.524590 | -0.081967 |
| 0.010000 | ejf | D_G_v1 | -0.007435 | -0.022664 | -0.015229 |
| 0.010000 | fn_jaccard | D_G_v1 | 0.630682 | 0.545455 | -0.085227 |
| 0.010000 | all_detector_jfn | primary_stack | 0.032787 | 0.027322 | -0.005464 |
| 0.010000 | all_detector_fn_count | primary_stack | 6 | 5 | -1 |
| 0.010000 | unique_catch_count | primary_stack | 0 | 1 | 1 |
| 0.010000 | unique_catch_rate | primary_stack | 0.000000 | 0.005464 | 0.005464 |
| 0.010000 | recovery_given_others_miss | primary_stack | 0.000000 | 0.166667 | 0.166667 |
| 0.030000 | fnr | D_S | 0.677596 | 0.453552 | -0.224044 |
| 0.030000 | jfn | D_M-B_v1 | 0.021858 | 0.016393 | -0.005464 |
| 0.030000 | ejf | D_M-B_v1 | 0.007047 | 0.006480 | -0.000567 |
| 0.030000 | fn_jaccard | D_M-B_v1 | 0.032258 | 0.035714 | 0.003456 |
| 0.030000 | jfn | D_G_v1 | 0.502732 | 0.333333 | -0.169399 |
| 0.030000 | ejf | D_G_v1 | -0.019350 | -0.016125 | 0.003225 |
| 0.030000 | fn_jaccard | D_G_v1 | 0.531792 | 0.374233 | -0.157559 |
| 0.030000 | all_detector_jfn | primary_stack | 0.021858 | 0.016393 | -0.005464 |
| 0.030000 | all_detector_fn_count | primary_stack | 4 | 3 | -1 |
| 0.030000 | unique_catch_count | primary_stack | 0 | 1 | 1 |
| 0.030000 | unique_catch_rate | primary_stack | 0.000000 | 0.005464 | 0.005464 |
| 0.030000 | recovery_given_others_miss | primary_stack | 0.000000 | 0.250000 | 0.250000 |
| 0.050000 | fnr | D_S | 0.546448 | 0.371585 | -0.174863 |
| 0.050000 | jfn | D_M-B_v1 | 0.010929 | 0.010929 | 0.000000 |
| 0.050000 | ejf | D_M-B_v1 | 0.004957 | 0.006868 | 0.001911 |
| 0.050000 | fn_jaccard | D_M-B_v1 | 0.020000 | 0.029412 | 0.009412 |
| 0.050000 | jfn | D_G_v1 | 0.371585 | 0.256831 | -0.114754 |
| 0.050000 | ejf | D_G_v1 | -0.028547 | -0.015259 | 0.013288 |
| 0.050000 | fn_jaccard | D_G_v1 | 0.409639 | 0.303226 | -0.106413 |
| 0.050000 | all_detector_jfn | primary_stack | 0.010929 | 0.010929 | 0.000000 |
| 0.050000 | all_detector_fn_count | primary_stack | 2 | 2 | 0 |
| 0.050000 | unique_catch_count | primary_stack | 0 | 0 | 0 |
| 0.050000 | unique_catch_rate | primary_stack | 0.000000 | 0.000000 | 0.000000 |
| 0.050000 | recovery_given_others_miss | primary_stack | 0.000000 | 0.000000 | 0.000000 |


At 1%: REDUCED_SHARED_FAILURE, PRESERVED_COMPLEMENTARITY.
At 3%: REDUCED_SHARED_FAILURE, PRESERVED_COMPLEMENTARITY.
At 5%: NO_CLEAR_CHANGE.

At the descriptive 3% FPR budget, D_S B2+LR catches 1/4 attacks missed by both D_M-B and D_G, and all-three shared misses change from 4 to 3 out of 183 attacks.

Observed development failure association only; use the full completion report for paired intervals and limitations.
