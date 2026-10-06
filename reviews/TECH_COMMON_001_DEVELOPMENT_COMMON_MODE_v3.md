# TECH-COMMON-001 Development Common-Mode Characterization v3

Status: **PASS**. DEVELOPMENT COMMON-MODE CHARACTERIZATION; not protected/final research performance.

## Methodology

1,135 aligned BASE_TRAIN records (183 positive, 952 negative), five frozen QUALITY-001 folds, seed 1701. D_S v1, B2+LR and D_M-B are authoritative fold-local OOF scores; no row was fitted by its scoring model. The candidate uses the selected S0/B2 evidence, never a whole-BASE_TRAIN fitted ds_v2. D_G is externally frozen without project BASE_TRAIN fitting; missing D_G evidence is never substituted.

## Matched-FPR rule

Each detector selects its own descriptive threshold at 1/3/5%. Use whole tied blocks and inclusive >=; maximize recall without exceeding budget, then minimize attained FPR, then choose the highest threshold. No final/deployment threshold or ensemble decision rule is created.

Failure metrics use attack rows only: JFN is the joint miss fraction; IND is the product of marginal FNRs; EJF=JFN−IND. Jaccard is intersection/union (zero for empty union). Conditional failure P(F_left|F_right) uses the right FN count. Exclusive catches require both other members to miss; the rate uses all 183 attacks and recovery uses other-two misses as denominator. Empty conditional denominators yield null; denominators <10 carry a descriptive small-count flag.

## D_G characterization

| metric | native | le_1_percent | le_3_percent | le_5_percent |
|---|---|---|---|---|
| tn | 941 | 946 | 935 | 908 |
| fp | 11 | 6 | 17 | 44 |
| fn | 147 | 149 | 141 | 134 |
| tp | 36 | 34 | 42 | 49 |
| accuracy | 0.860793 | UNMEASURED | UNMEASURED | UNMEASURED |
| precision | 0.765957 | UNMEASURED | UNMEASURED | UNMEASURED |
| recall | 0.196721 | 0.185792 | 0.229508 | 0.267760 |
| specificity | 0.988445 | UNMEASURED | UNMEASURED | UNMEASURED |
| f1 | 0.313043 | UNMEASURED | UNMEASURED | UNMEASURED |
| fpr | 0.011555 | 0.006303 | 0.017857 | 0.046218 |
| fnr | 0.803279 | 0.814208 | 0.770492 | 0.732240 |
| roc_auc | 0.814954 | UNMEASURED | UNMEASURED | UNMEASURED |
| pr_auc | 0.500652 | UNMEASURED | UNMEASURED | UNMEASURED |

## table 2 individual

Rates are fractions. UNMEASURED is a missing result, not zero.

| detector | budget | fpr | recall | fnr | tp | fn | fp | tn |
|---|---|---|---|---|---|---|---|---|
| D_G_v1 | 0.010000 | 0.006303 | 0.185792 | 0.814208 | 34 | 149 | 6 | 946 |
| D_M-B_v1 | 0.010000 | 0.007353 | 0.967213 | 0.032787 | 177 | 6 | 7 | 945 |
| D_S_B2_LR | 0.010000 | 0.009454 | 0.327869 | 0.672131 | 60 | 123 | 9 | 943 |
| D_S_v1 | 0.010000 | 0.007353 | 0.245902 | 0.754098 | 45 | 138 | 7 | 945 |
| D_G_v1 | 0.030000 | 0.017857 | 0.229508 | 0.770492 | 42 | 141 | 17 | 935 |
| D_M-B_v1 | 0.030000 | 0.023109 | 0.978142 | 0.021858 | 179 | 4 | 22 | 930 |
| D_S_B2_LR | 0.030000 | 0.029412 | 0.546448 | 0.453552 | 100 | 83 | 28 | 924 |
| D_S_v1 | 0.030000 | 0.029412 | 0.322404 | 0.677596 | 59 | 124 | 28 | 924 |
| D_G_v1 | 0.050000 | 0.046218 | 0.267760 | 0.732240 | 49 | 134 | 44 | 908 |
| D_M-B_v1 | 0.050000 | 0.035714 | 0.989071 | 0.010929 | 181 | 2 | 34 | 918 |
| D_S_B2_LR | 0.050000 | 0.048319 | 0.628415 | 0.371585 | 115 | 68 | 46 | 906 |
| D_S_v1 | 0.050000 | 0.049370 | 0.453552 | 0.546448 | 83 | 100 | 47 | 905 |

## table 3 pairwise

Rates are fractions. UNMEASURED is a missing result, not zero.

| stack | budget | left | right | jfn_count | jfn | independence_reference | ejf | fn_jaccard |
|---|---|---|---|---|---|---|---|---|
| DEVELOPMENT_STACK_V1 | 0.010000 | D_M-B_v1 | D_S_v1 | 6 | 0.032787 | 0.024725 | 0.008062 | 0.043478 |
| DEVELOPMENT_STACK_V1 | 0.010000 | D_G_v1 | D_S_v1 | 111 | 0.606557 | 0.613993 | -0.007435 | 0.630682 |
| DEVELOPMENT_STACK_V1 | 0.010000 | D_G_v1 | D_M-B_v1 | 6 | 0.032787 | 0.026695 | 0.006092 | 0.040268 |
| DEVELOPMENT_STACK_CANDIDATE | 0.010000 | D_M-B_v1 | D_S_B2_LR | 5 | 0.027322 | 0.022037 | 0.005285 | 0.040323 |
| DEVELOPMENT_STACK_CANDIDATE | 0.010000 | D_G_v1 | D_S_B2_LR | 96 | 0.524590 | 0.547254 | -0.022664 | 0.545455 |
| DEVELOPMENT_STACK_CANDIDATE | 0.010000 | D_G_v1 | D_M-B_v1 | 6 | 0.032787 | 0.026695 | 0.006092 | 0.040268 |
| DEVELOPMENT_STACK_V1 | 0.030000 | D_M-B_v1 | D_S_v1 | 4 | 0.021858 | 0.014811 | 0.007047 | 0.032258 |
| DEVELOPMENT_STACK_V1 | 0.030000 | D_G_v1 | D_S_v1 | 92 | 0.502732 | 0.522082 | -0.019350 | 0.531792 |
| DEVELOPMENT_STACK_V1 | 0.030000 | D_G_v1 | D_M-B_v1 | 4 | 0.021858 | 0.016841 | 0.005017 | 0.028369 |
| DEVELOPMENT_STACK_CANDIDATE | 0.030000 | D_M-B_v1 | D_S_B2_LR | 3 | 0.016393 | 0.009914 | 0.006480 | 0.035714 |
| DEVELOPMENT_STACK_CANDIDATE | 0.030000 | D_G_v1 | D_S_B2_LR | 61 | 0.333333 | 0.349458 | -0.016125 | 0.374233 |
| DEVELOPMENT_STACK_CANDIDATE | 0.030000 | D_G_v1 | D_M-B_v1 | 4 | 0.021858 | 0.016841 | 0.005017 | 0.028369 |
| DEVELOPMENT_STACK_V1 | 0.050000 | D_M-B_v1 | D_S_v1 | 2 | 0.010929 | 0.005972 | 0.004957 | 0.020000 |
| DEVELOPMENT_STACK_V1 | 0.050000 | D_G_v1 | D_S_v1 | 68 | 0.371585 | 0.400131 | -0.028547 | 0.409639 |
| DEVELOPMENT_STACK_V1 | 0.050000 | D_G_v1 | D_M-B_v1 | 2 | 0.010929 | 0.008003 | 0.002926 | 0.014925 |
| DEVELOPMENT_STACK_CANDIDATE | 0.050000 | D_M-B_v1 | D_S_B2_LR | 2 | 0.010929 | 0.004061 | 0.006868 | 0.029412 |
| DEVELOPMENT_STACK_CANDIDATE | 0.050000 | D_G_v1 | D_S_B2_LR | 47 | 0.256831 | 0.272089 | -0.015259 | 0.303226 |
| DEVELOPMENT_STACK_CANDIDATE | 0.050000 | D_G_v1 | D_M-B_v1 | 2 | 0.010929 | 0.008003 | 0.002926 | 0.014925 |

## table 4 all detector

Rates are fractions. UNMEASURED is a missing result, not zero.

| stack | budget | all_detector_fn_count | all_detector_jfn |
|---|---|---|---|
| DEVELOPMENT_STACK_CANDIDATE | 0.010000 | 5 | 0.027322 |
| DEVELOPMENT_STACK_V1 | 0.010000 | 6 | 0.032787 |
| DEVELOPMENT_STACK_CANDIDATE | 0.030000 | 3 | 0.016393 |
| DEVELOPMENT_STACK_V1 | 0.030000 | 4 | 0.021858 |
| DEVELOPMENT_STACK_CANDIDATE | 0.050000 | 2 | 0.010929 |
| DEVELOPMENT_STACK_V1 | 0.050000 | 2 | 0.010929 |

## table 5 unique

Rates are fractions. UNMEASURED is a missing result, not zero.

| stack | budget | detector | unique_catch_count | unique_catch_rate | other_members_miss_count | recovery_given_others_miss |
|---|---|---|---|---|---|---|
| DEVELOPMENT_STACK_CANDIDATE | 0.010000 | D_S_B2_LR | 1 | 0.005464 | 6 | 0.166667 |
| DEVELOPMENT_STACK_CANDIDATE | 0.010000 | D_M-B_v1 | 91 | 0.497268 | 96 | 0.947917 |
| DEVELOPMENT_STACK_CANDIDATE | 0.010000 | D_G_v1 | 0 | 0.000000 | 5 | 0.000000 |
| DEVELOPMENT_STACK_V1 | 0.010000 | D_S_v1 | 0 | 0.000000 | 6 | 0.000000 |
| DEVELOPMENT_STACK_V1 | 0.010000 | D_M-B_v1 | 105 | 0.573770 | 111 | 0.945946 |
| DEVELOPMENT_STACK_V1 | 0.010000 | D_G_v1 | 0 | 0.000000 | 6 | 0.000000 |
| DEVELOPMENT_STACK_CANDIDATE | 0.030000 | D_S_B2_LR | 1 | 0.005464 | 4 | 0.250000 |
| DEVELOPMENT_STACK_CANDIDATE | 0.030000 | D_M-B_v1 | 58 | 0.316940 | 61 | 0.950820 |
| DEVELOPMENT_STACK_CANDIDATE | 0.030000 | D_G_v1 | 0 | 0.000000 | 3 | 0.000000 |
| DEVELOPMENT_STACK_V1 | 0.030000 | D_S_v1 | 0 | 0.000000 | 4 | 0.000000 |
| DEVELOPMENT_STACK_V1 | 0.030000 | D_M-B_v1 | 88 | 0.480874 | 92 | 0.956522 |
| DEVELOPMENT_STACK_V1 | 0.030000 | D_G_v1 | 0 | 0.000000 | 4 | 0.000000 |
| DEVELOPMENT_STACK_CANDIDATE | 0.050000 | D_S_B2_LR | 0 | 0.000000 | 2 | 0.000000 |
| DEVELOPMENT_STACK_CANDIDATE | 0.050000 | D_M-B_v1 | 45 | 0.245902 | 47 | 0.957447 |
| DEVELOPMENT_STACK_CANDIDATE | 0.050000 | D_G_v1 | 0 | 0.000000 | 2 | 0.000000 |
| DEVELOPMENT_STACK_V1 | 0.050000 | D_S_v1 | 0 | 0.000000 | 2 | 0.000000 |
| DEVELOPMENT_STACK_V1 | 0.050000 | D_M-B_v1 | 66 | 0.360656 | 68 | 0.970588 |
| DEVELOPMENT_STACK_V1 | 0.050000 | D_G_v1 | 0 | 0.000000 | 2 | 0.000000 |

## table 6 ds effect

Rates are fractions. UNMEASURED is a missing result, not zero.

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

## table 7 subgroups

Rates are fractions. UNMEASURED is a missing result, not zero.

| budget | subgroup | count | D_S_candidate | D_M-B | D_G | either_stronger_catches | all_three_miss |
|---|---|---|---|---|---|---|---|
| 0.010000 | under_16_attacks | 26 | 0 | 25 | 6 | 25 | 1 |
| 0.010000 | 64_plus_benign | 17 | 6 | 0 | 0 | 0 | UNMEASURED |
| 0.030000 | under_16_attacks | 26 | 0 | 26 | 7 | 26 | 0 |
| 0.030000 | 64_plus_benign | 17 | 12 | 3 | 0 | 3 | UNMEASURED |
| 0.050000 | under_16_attacks | 26 | 0 | 26 | 7 | 26 | 0 |
| 0.050000 | 64_plus_benign | 17 | 15 | 4 | 0 | 4 | UNMEASURED |

## Conditional pairwise failure

| budget | left | right | jfn_count | left_fn_count | right_fn_count | p_failure_left_given_right | p_failure_right_given_left |
|---|---|---|---|---|---|---|---|
| 0.010000 | D_M-B_v1 | D_S_v1 | 6 | 6 | 138 | 0.043478 | 1.000000 |
| 0.010000 | D_G_v1 | D_S_v1 | 111 | 149 | 138 | 0.804348 | 0.744966 |
| 0.010000 | D_G_v1 | D_M-B_v1 | 6 | 149 | 6 | 1.000000 | 0.040268 |
| 0.010000 | D_M-B_v1 | D_S_B2_LR | 5 | 6 | 123 | 0.040650 | 0.833333 |
| 0.010000 | D_G_v1 | D_S_B2_LR | 96 | 149 | 123 | 0.780488 | 0.644295 |
| 0.010000 | D_G_v1 | D_M-B_v1 | 6 | 149 | 6 | 1.000000 | 0.040268 |
| 0.030000 | D_M-B_v1 | D_S_v1 | 4 | 4 | 124 | 0.032258 | 1.000000 |
| 0.030000 | D_G_v1 | D_S_v1 | 92 | 141 | 124 | 0.741935 | 0.652482 |
| 0.030000 | D_G_v1 | D_M-B_v1 | 4 | 141 | 4 | 1.000000 | 0.028369 |
| 0.030000 | D_M-B_v1 | D_S_B2_LR | 3 | 4 | 83 | 0.036145 | 0.750000 |
| 0.030000 | D_G_v1 | D_S_B2_LR | 61 | 141 | 83 | 0.734940 | 0.432624 |
| 0.030000 | D_G_v1 | D_M-B_v1 | 4 | 141 | 4 | 1.000000 | 0.028369 |
| 0.050000 | D_M-B_v1 | D_S_v1 | 2 | 2 | 100 | 0.020000 | 1.000000 |
| 0.050000 | D_G_v1 | D_S_v1 | 68 | 134 | 100 | 0.680000 | 0.507463 |
| 0.050000 | D_G_v1 | D_M-B_v1 | 2 | 134 | 2 | 1.000000 | 0.014925 |
| 0.050000 | D_M-B_v1 | D_S_B2_LR | 2 | 2 | 68 | 0.029412 | 1.000000 |
| 0.050000 | D_G_v1 | D_S_B2_LR | 47 | 134 | 68 | 0.691176 | 0.350746 |
| 0.050000 | D_G_v1 | D_M-B_v1 | 2 | 134 | 2 | 1.000000 | 0.014925 |

## D_S improvement interpretation

At 1%, D_S/D_M-B shared misses change 6→5 out of 183 attacks. ΔJFN=-0.005464, conditional 95% interval [-0.016393, 0.000000]. The delta interval includes zero; evidence for a population gain is inconclusive.

At 3%, D_S/D_M-B shared misses change 4→3 out of 183 attacks. ΔJFN=-0.005464, conditional 95% interval [-0.016393, 0.000000]. The delta interval includes zero; evidence for a population gain is inconclusive.

At 5%, D_S/D_M-B shared misses change 2→2 out of 183 attacks. ΔJFN=0.000000, conditional 95% interval [0.000000, 0.000000]. The delta interval includes zero; evidence for a population gain is inconclusive.

Positive EJF describes failure association relative to an independence reference, not causal dependence. Smaller marginal D_S FNR can increase EJF or Jaccard even if shared-FN counts stay fixed. No broad independence claim follows from these few semantic misses.

Full-stack deltas and exclusive catches are measured in Tables 4–6; assess their paired intervals and small event counts before claiming improved complementarity. No final detector promotion or architecture policy is authorized.

## Uncertainty and limitations

1,000 deterministic paired attack-lineage percentile bootstrap replicates, seed 1701, fixed pooled operating points; only attack rows enter FN-dependent intervals. Identical resampled attacks across detector/stack comparisons. The fixture has 183 distinct attack canonical-lineage groups. Intervals condition on fixed OOF scores/thresholds, exclude refitting, development selection and overlapping-training-fold uncertainty, and do not resolve upstream semantic lineage. A degenerate zero-event bootstrap interval is not proof of zero population risk.

| budget | estimate | lower | upper |
|---|---|---|---|
| 0.010000 | -0.005464 | -0.016393 | 0.000000 |
| 0.030000 | -0.005464 | -0.016393 | 0.000000 |
| 0.050000 | 0.000000 | 0.000000 | 0.000000 |

Source/fold groups apply unchanged pooled thresholds; no subgroup tuning. Existing per-ID family labels are retained for the four integrity-bound semantic residual records; all other records are UNKNOWN. This selectively annotated group was identified by prior semantic failures, so its family metrics are not a population family comparison. No label is inferred from text or generalized from a source. Sources are not R1/R2/R3 experiments. Subgroup tokens use frozen D_S reference-LM counts, not semantic/guard tokenizer counts. Catch/FP patterns are descriptive evidence, not a fusion rule. If a known detector catches every attack in a subgroup, the logical bounds establish zero all-three misses there despite absent D_G predictions; no guard result is imputed. Figures omitted to avoid extra plotting dependencies; all mandatory tables are CSV/JSON.

## Access blockers

```json
{
  "status": "READY",
  "data_status": "VERIFIED",
  "model_status": "VERIFIED",
  "missing_inputs": [],
  "missing_snapshot_files": [],
  "snapshot_path": "C:\\Users\\harsh\\Adversarial-Attack-Detection-for-LLMs\\detection_service\\.model-cache\\dg_v1\\snapshot-11614a155199674a0a95e6602d6ab0417b790ed0",
  "hf_cache_checked": "C:\\Users\\harsh\\.cache\\huggingface\\hub\\models--meta-llama--Llama-Prompt-Guard-2-22M\\snapshots\\11614a155199674a0a95e6602d6ab0417b790ed0",
  "hf_cache_present": false,
  "hf_access": {
    "status": "ACCESS_CHECK_UNAVAILABLE",
    "cli": "C:\\Users\\harsh\\AppData\\Local\\Programs\\Python\\Python312\\Scripts\\hf.EXE",
    "command": "hf auth login"
  },
  "package_mismatches": {},
  "python_3_11": true,
  "environment": {
    "python": "3.11.9",
    "platform": "Windows-10-10.0.26200-SP0",
    "packages": {
      "torch": "2.6.0",
      "transformers": "4.49.0",
      "tokenizers": "0.21.4",
      "scikit-learn": "1.6.1",
      "numpy": "2.1.3",
      "pyarrow": "19.0.1"
    },
    "device": "cpu",
    "cuda_runtime_visibility": "NOT_PROBED_WITHOUT_MODEL_RUNTIME",
    "nvidia_smi_visible": true,
    "cpu_count": 16
  },
  "model_id": "meta-llama/Llama-Prompt-Guard-2-22M",
  "revision": "11614a155199674a0a95e6602d6ab0417b790ed0",
  "manifest_sha256": "9cdd5ecdd80f9ac3c8f05db63742721f4537ca2b64a2fe48f6c2b424b57483a6",
  "fold_sha256": "19dc0153cc257cc2331782d6dd61b7bb9fb8cb0ed88d3e782b69d5ba05c4bb8d",
  "verified_sha256": {
    "data_governance/manifests/development_partition_manifest_v1.csv": "9cdd5ecdd80f9ac3c8f05db63742721f4537ca2b64a2fe48f6c2b424b57483a6",
    "artifacts/quality/quality_001/development_folds_v1.csv": "19dc0153cc257cc2331782d6dd61b7bb9fb8cb0ed88d3e782b69d5ba05c4bb8d",
    "Dataset/Raw/datasets/GitHub/Do-Not-Answer/datasets/Instruction/do_not_answer_en.csv": "8585dc135d3b8692b2e464151a313f5164e30f06416e03aa5d11e6c3a21d980e",
    "Dataset/Raw/datasets/HuggingFace/deepset-prompt-injections/data/test-00000-of-00001-701d16158af87368.parquet": "39ac797cabc157eeed58435a08593b2952bb6cb16fc394a2d383f447cc7b246e",
    "Dataset/Raw/datasets/HuggingFace/deepset-prompt-injections/data/train-00000-of-00001-9564e8b05b4757ab.parquet": "2e10bc7ab30f542c97e4e83e2a5683000b5057d25ec10908784c631d44124c04",
    "detection_service/.model-cache/dg_v1/snapshot-11614a155199674a0a95e6602d6ab0417b790ed0/config.json": "1dc4742d04507072cafffb7235dc5dba5af9ba126f7a9830b95ed7ec00fd9104",
    "detection_service/.model-cache/dg_v1/snapshot-11614a155199674a0a95e6602d6ab0417b790ed0/LICENSE": "73755cee886613ae3135140882289e0a4955d5f0e90f8b1c1ffc962aa9082917",
    "detection_service/.model-cache/dg_v1/snapshot-11614a155199674a0a95e6602d6ab0417b790ed0/model.safetensors": "5120e30bcd536ce285345d9ec104bea6bd6e8f94365b99a340c764f417ea5fa1",
    "detection_service/.model-cache/dg_v1/snapshot-11614a155199674a0a95e6602d6ab0417b790ed0/MODEL_CARD.md": "7aacb25a94cab70530bca3545feda87bf7a935eaca92998222365b090acfd97c",
    "detection_service/.model-cache/dg_v1/snapshot-11614a155199674a0a95e6602d6ab0417b790ed0/README.md": "5d2a3e0c46397609a784a5034dc823da408aa8b5a414828609f32dc18ee16933",
    "detection_service/.model-cache/dg_v1/snapshot-11614a155199674a0a95e6602d6ab0417b790ed0/special_tokens_map.json": "9463f61e1b109a8eb4688b829260d7c6b1e6dff04c98ff7269bb89e2b92369b9",
    "detection_service/.model-cache/dg_v1/snapshot-11614a155199674a0a95e6602d6ab0417b790ed0/tokenizer.json": "6eb983352e73f1697b883a8c3f6b66bdfa336ab3d29dd3687f8316d0ff2789c1",
    "detection_service/.model-cache/dg_v1/snapshot-11614a155199674a0a95e6602d6ab0417b790ed0/tokenizer_config.json": "557b3d33d3f41b81ad769244e506549e98a1857d41dd58160aacd4d98d710b5a",
    "detection_service/.model-cache/dg_v1/snapshot-11614a155199674a0a95e6602d6ab0417b790ed0/USE_POLICY.md": "5ae40fe842b87b5773c47cfd25992a496cc09b17cbb246968762f06352d89270"
  },
  "live_rows_scored": 0,
  "unblock": [
    "Restore exact authoritative manifest and three approved source files; verify listed hashes. No supported exact bootstrap was found.",
    "hf auth login; hf auth whoami. Obtain access at https://huggingface.co/meta-llama/Llama-Prompt-Guard-2-22M if needed.",
    "hf download meta-llama/Llama-Prompt-Guard-2-22M --revision 11614a155199674a0a95e6602d6ab0417b790ed0 --local-dir \"C:\\Users\\harsh\\Adversarial-Attack-Detection-for-LLMs\\detection_service\\.model-cache\\dg_v1\\snapshot-11614a155199674a0a95e6602d6ab0417b790ed0\"",
    "Install detection_service/requirements.txt and pyarrow==19.0.1 tokenizers==0.21.4 in Python 3.11; keep frozen versions.",
    "python -m detection_service.scripts.guard_development --check",
    "python -m detection_service.scripts.guard_development --run",
    "python -m detection_service.scripts.common_mode_completion --release 4"
  ],
  "no_raw_prompt_text_saved": true,
  "scope": "DEVELOPMENT_ONLY"
}
```

## Preservation and tests

```json
{
  "tests": {
    "existing_prerun": {
      "status": "PASS",
      "tests": 115,
      "failures": 0,
      "errors": 0,
      "skipped": 0,
      "path": "C:\\Users\\harsh\\Adversarial-Attack-Detection-for-LLMs\\artifacts\\common_mode\\development\\completion_v3\\track2_continuation_prerun.xml",
      "sha256": "ea0accacf3a55f851b79a680925353f2c551d15818835dae39f4cf90037728b8"
    },
    "expanded": {
      "status": "PASS",
      "tests": 79,
      "failures": 0,
      "errors": 0,
      "skipped": 0,
      "path": "C:\\Users\\harsh\\Adversarial-Attack-Detection-for-LLMs\\artifacts\\common_mode\\development\\completion_v3\\track2_completion_tests.xml",
      "sha256": "9601d1a22c46ddd5a84b249d66e7ae68c2d50517c8eb0b6fdbb94dd267653110"
    }
  },
  "preservation": {
    "strict_original_suite": {
      "returncode": 0,
      "status": "PASS",
      "command": "python -m detection_service.scripts.verify_quality_preservation --mode check"
    },
    "baseline_files": 96,
    "exact_byte_matches": 96,
    "newline_only_matches": 0,
    "newline_differences": [],
    "unexplained_changes": 0,
    "tracked_detector_diff": "EMPTY",
    "original_track2_artifacts_and_reports_verified": 62,
    "historical_evidence": "BYTE_IDENTICAL",
    "stat004_sha256": {
      "artifacts/statistical_v2/feature_ablation/resume_20000/block_fold_metrics_v1.json": "2f3823da52fd0d9874fd89e14d4d7feb791225ea690ed3956d1d381f847df7c5",
      "artifacts/statistical_v2/feature_ablation/resume_20000/block_metrics_v1.json": "73a5225e6bcfdbb889014e732727d96b21bc8a59230955478908ebd677d5f64f",
      "artifacts/statistical_v2/feature_ablation/resume_20000/block_predictions_v1.csv": "32e21d581b433a422e4f438274a01d0719ccbae1c8f4788505e30f05c2414f2e",
      "artifacts/statistical_v2/feature_ablation/resume_20000/error_bank_transition_v1.json": "625e6a357d2495a4f06e992874a8eeab2699c6dfa4d9dcb61469e94a13fcc1d9",
      "artifacts/statistical_v2/feature_ablation/resume_20000/fold_references_v1.json": "38fc670b45fac1f776e3c30986ccf5e6f318276011576ef33bed196e69cac691",
      "artifacts/statistical_v2/feature_ablation/resume_20000/lr_convergence_v1.json": "6c9d80b0e029e34e966389339b8a1f83cfee54c286e075e834da7f8c6cbea7a4",
      "artifacts/statistical_v2/feature_ablation/resume_20000/paired_comparison_v1.json": "64e7aa9d17b0f181ed8cb0ec82be6666841c65963a08d3a60a097f008d3bb71c",
      "artifacts/statistical_v2/feature_ablation/resume_20000/selected_representation_v1.json": "05c0ab4f01cceb2a57e70e9ed0fe68717a0118a8d0a8cedf6bb5d26b5857adf2",
      "artifacts/statistical_v2/feature_ablation/resume_20000/short_prompt_analysis_v1.json": "f26ed7323d76562c0261c4670719acda4a054d3d4a201fab66a3a401b01d42e3"
    },
    "interpretation": "Strict preservation suite passes with exact baseline bytes."
  }
}
```

## Isolation

D_S/D_M-B/D_G training: NO. CALIBRATION/VALIDATION/protected prompt payloads: NO. E1-E10, adaptive generation, verifier, routing, final threshold and fusion: NO. Historical predictions/artifacts and first Track-2 reports are byte-preserved.
