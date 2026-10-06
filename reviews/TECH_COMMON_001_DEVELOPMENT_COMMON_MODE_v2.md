# TECH-COMMON-001 Development Common-Mode Characterization v2

Status: **PARTIAL**. DEVELOPMENT COMMON-MODE CHARACTERIZATION; not protected/final research performance.

## Methodology

1,135 aligned BASE_TRAIN records (183 positive, 952 negative), five frozen QUALITY-001 folds, seed 1701. D_S v1, B2+LR and D_M-B are authoritative fold-local OOF scores; no row was fitted by its scoring model. The candidate uses the selected S0/B2 evidence, never a whole-BASE_TRAIN fitted ds_v2. D_G is externally frozen without project BASE_TRAIN fitting; missing D_G evidence is never substituted.

## Matched-FPR rule

Each detector selects its own descriptive threshold at 1/3/5%. Use whole tied blocks and inclusive >=; maximize recall without exceeding budget, then minimize attained FPR, then choose the highest threshold. No final/deployment threshold or ensemble decision rule is created.

Failure metrics use attack rows only: JFN is the joint miss fraction; IND is the product of marginal FNRs; EJF=JFN−IND. Jaccard is intersection/union (zero for empty union). Conditional failure P(F_left|F_right) uses the right FN count. Exclusive catches require both other members to miss; the rate uses all 183 attacks and recovery uses other-two misses as denominator. Empty conditional denominators yield null; denominators <10 carry a descriptive small-count flag.

## D_G characterization

| metric | native | le_1_percent | le_3_percent | le_5_percent |
|---|---|---|---|---|
| tn | UNMEASURED | UNMEASURED | UNMEASURED | UNMEASURED |
| fp | UNMEASURED | UNMEASURED | UNMEASURED | UNMEASURED |
| fn | UNMEASURED | UNMEASURED | UNMEASURED | UNMEASURED |
| tp | UNMEASURED | UNMEASURED | UNMEASURED | UNMEASURED |
| accuracy | UNMEASURED | UNMEASURED | UNMEASURED | UNMEASURED |
| precision | UNMEASURED | UNMEASURED | UNMEASURED | UNMEASURED |
| recall | UNMEASURED | UNMEASURED | UNMEASURED | UNMEASURED |
| specificity | UNMEASURED | UNMEASURED | UNMEASURED | UNMEASURED |
| f1 | UNMEASURED | UNMEASURED | UNMEASURED | UNMEASURED |
| fpr | UNMEASURED | UNMEASURED | UNMEASURED | UNMEASURED |
| fnr | UNMEASURED | UNMEASURED | UNMEASURED | UNMEASURED |
| roc_auc | UNMEASURED | UNMEASURED | UNMEASURED | UNMEASURED |
| pr_auc | UNMEASURED | UNMEASURED | UNMEASURED | UNMEASURED |

## table 2 individual

Rates are fractions. UNMEASURED is a missing result, not zero.

| detector | budget | fpr | recall | fnr | tp | fn | fp | tn |
|---|---|---|---|---|---|---|---|---|
| D_M-B_v1 | 0.010000 | 0.007353 | 0.967213 | 0.032787 | 177 | 6 | 7 | 945 |
| D_S_B2_LR | 0.010000 | 0.009454 | 0.327869 | 0.672131 | 60 | 123 | 9 | 943 |
| D_S_v1 | 0.010000 | 0.007353 | 0.245902 | 0.754098 | 45 | 138 | 7 | 945 |
| D_G_v1 | 0.010000 | UNMEASURED | UNMEASURED | UNMEASURED | UNMEASURED | UNMEASURED | UNMEASURED | UNMEASURED |
| D_M-B_v1 | 0.030000 | 0.023109 | 0.978142 | 0.021858 | 179 | 4 | 22 | 930 |
| D_S_B2_LR | 0.030000 | 0.029412 | 0.546448 | 0.453552 | 100 | 83 | 28 | 924 |
| D_S_v1 | 0.030000 | 0.029412 | 0.322404 | 0.677596 | 59 | 124 | 28 | 924 |
| D_G_v1 | 0.030000 | UNMEASURED | UNMEASURED | UNMEASURED | UNMEASURED | UNMEASURED | UNMEASURED | UNMEASURED |
| D_M-B_v1 | 0.050000 | 0.035714 | 0.989071 | 0.010929 | 181 | 2 | 34 | 918 |
| D_S_B2_LR | 0.050000 | 0.048319 | 0.628415 | 0.371585 | 115 | 68 | 46 | 906 |
| D_S_v1 | 0.050000 | 0.049370 | 0.453552 | 0.546448 | 83 | 100 | 47 | 905 |
| D_G_v1 | 0.050000 | UNMEASURED | UNMEASURED | UNMEASURED | UNMEASURED | UNMEASURED | UNMEASURED | UNMEASURED |

## table 3 pairwise

Rates are fractions. UNMEASURED is a missing result, not zero.

| stack | budget | left | right | jfn_count | jfn | independence_reference | ejf | fn_jaccard |
|---|---|---|---|---|---|---|---|---|
| DEVELOPMENT_STACK_V1 | 0.010000 | D_M-B_v1 | D_S_v1 | 6 | 0.032787 | 0.024725 | 0.008062 | 0.043478 |
| DEVELOPMENT_STACK_V1 | 0.010000 | D_S_v1 | D_G_v1 | UNMEASURED | UNMEASURED | UNMEASURED | UNMEASURED | UNMEASURED |
| DEVELOPMENT_STACK_V1 | 0.010000 | D_M-B_v1 | D_G_v1 | UNMEASURED | UNMEASURED | UNMEASURED | UNMEASURED | UNMEASURED |
| DEVELOPMENT_STACK_CANDIDATE | 0.010000 | D_M-B_v1 | D_S_B2_LR | 5 | 0.027322 | 0.022037 | 0.005285 | 0.040323 |
| DEVELOPMENT_STACK_CANDIDATE | 0.010000 | D_S_B2_LR | D_G_v1 | UNMEASURED | UNMEASURED | UNMEASURED | UNMEASURED | UNMEASURED |
| DEVELOPMENT_STACK_CANDIDATE | 0.010000 | D_M-B_v1 | D_G_v1 | UNMEASURED | UNMEASURED | UNMEASURED | UNMEASURED | UNMEASURED |
| DEVELOPMENT_STACK_V1 | 0.030000 | D_M-B_v1 | D_S_v1 | 4 | 0.021858 | 0.014811 | 0.007047 | 0.032258 |
| DEVELOPMENT_STACK_V1 | 0.030000 | D_S_v1 | D_G_v1 | UNMEASURED | UNMEASURED | UNMEASURED | UNMEASURED | UNMEASURED |
| DEVELOPMENT_STACK_V1 | 0.030000 | D_M-B_v1 | D_G_v1 | UNMEASURED | UNMEASURED | UNMEASURED | UNMEASURED | UNMEASURED |
| DEVELOPMENT_STACK_CANDIDATE | 0.030000 | D_M-B_v1 | D_S_B2_LR | 3 | 0.016393 | 0.009914 | 0.006480 | 0.035714 |
| DEVELOPMENT_STACK_CANDIDATE | 0.030000 | D_S_B2_LR | D_G_v1 | UNMEASURED | UNMEASURED | UNMEASURED | UNMEASURED | UNMEASURED |
| DEVELOPMENT_STACK_CANDIDATE | 0.030000 | D_M-B_v1 | D_G_v1 | UNMEASURED | UNMEASURED | UNMEASURED | UNMEASURED | UNMEASURED |
| DEVELOPMENT_STACK_V1 | 0.050000 | D_M-B_v1 | D_S_v1 | 2 | 0.010929 | 0.005972 | 0.004957 | 0.020000 |
| DEVELOPMENT_STACK_V1 | 0.050000 | D_S_v1 | D_G_v1 | UNMEASURED | UNMEASURED | UNMEASURED | UNMEASURED | UNMEASURED |
| DEVELOPMENT_STACK_V1 | 0.050000 | D_M-B_v1 | D_G_v1 | UNMEASURED | UNMEASURED | UNMEASURED | UNMEASURED | UNMEASURED |
| DEVELOPMENT_STACK_CANDIDATE | 0.050000 | D_M-B_v1 | D_S_B2_LR | 2 | 0.010929 | 0.004061 | 0.006868 | 0.029412 |
| DEVELOPMENT_STACK_CANDIDATE | 0.050000 | D_S_B2_LR | D_G_v1 | UNMEASURED | UNMEASURED | UNMEASURED | UNMEASURED | UNMEASURED |
| DEVELOPMENT_STACK_CANDIDATE | 0.050000 | D_M-B_v1 | D_G_v1 | UNMEASURED | UNMEASURED | UNMEASURED | UNMEASURED | UNMEASURED |

## table 4 all detector

Rates are fractions. UNMEASURED is a missing result, not zero.

| stack | budget | all_detector_fn_count | all_detector_jfn |
|---|---|---|---|
| DEVELOPMENT_STACK_CANDIDATE | 0.010000 | UNMEASURED | UNMEASURED |
| DEVELOPMENT_STACK_V1 | 0.010000 | UNMEASURED | UNMEASURED |
| DEVELOPMENT_STACK_CANDIDATE | 0.030000 | UNMEASURED | UNMEASURED |
| DEVELOPMENT_STACK_V1 | 0.030000 | UNMEASURED | UNMEASURED |
| DEVELOPMENT_STACK_CANDIDATE | 0.050000 | UNMEASURED | UNMEASURED |
| DEVELOPMENT_STACK_V1 | 0.050000 | UNMEASURED | UNMEASURED |

## table 5 unique

Rates are fractions. UNMEASURED is a missing result, not zero.

| stack | budget | detector | unique_catch_count | unique_catch_rate | other_members_miss_count | recovery_given_others_miss |
|---|---|---|---|---|---|---|
| DEVELOPMENT_STACK_CANDIDATE | 0.010000 | D_S_B2_LR | UNMEASURED | UNMEASURED | UNMEASURED | UNMEASURED |
| DEVELOPMENT_STACK_CANDIDATE | 0.010000 | D_M-B_v1 | UNMEASURED | UNMEASURED | UNMEASURED | UNMEASURED |
| DEVELOPMENT_STACK_CANDIDATE | 0.010000 | D_G_v1 | UNMEASURED | UNMEASURED | UNMEASURED | UNMEASURED |
| DEVELOPMENT_STACK_V1 | 0.010000 | D_S_v1 | UNMEASURED | UNMEASURED | UNMEASURED | UNMEASURED |
| DEVELOPMENT_STACK_V1 | 0.010000 | D_M-B_v1 | UNMEASURED | UNMEASURED | UNMEASURED | UNMEASURED |
| DEVELOPMENT_STACK_V1 | 0.010000 | D_G_v1 | UNMEASURED | UNMEASURED | UNMEASURED | UNMEASURED |
| DEVELOPMENT_STACK_CANDIDATE | 0.030000 | D_S_B2_LR | UNMEASURED | UNMEASURED | UNMEASURED | UNMEASURED |
| DEVELOPMENT_STACK_CANDIDATE | 0.030000 | D_M-B_v1 | UNMEASURED | UNMEASURED | UNMEASURED | UNMEASURED |
| DEVELOPMENT_STACK_CANDIDATE | 0.030000 | D_G_v1 | UNMEASURED | UNMEASURED | UNMEASURED | UNMEASURED |
| DEVELOPMENT_STACK_V1 | 0.030000 | D_S_v1 | UNMEASURED | UNMEASURED | UNMEASURED | UNMEASURED |
| DEVELOPMENT_STACK_V1 | 0.030000 | D_M-B_v1 | UNMEASURED | UNMEASURED | UNMEASURED | UNMEASURED |
| DEVELOPMENT_STACK_V1 | 0.030000 | D_G_v1 | UNMEASURED | UNMEASURED | UNMEASURED | UNMEASURED |
| DEVELOPMENT_STACK_CANDIDATE | 0.050000 | D_S_B2_LR | UNMEASURED | UNMEASURED | UNMEASURED | UNMEASURED |
| DEVELOPMENT_STACK_CANDIDATE | 0.050000 | D_M-B_v1 | UNMEASURED | UNMEASURED | UNMEASURED | UNMEASURED |
| DEVELOPMENT_STACK_CANDIDATE | 0.050000 | D_G_v1 | UNMEASURED | UNMEASURED | UNMEASURED | UNMEASURED |
| DEVELOPMENT_STACK_V1 | 0.050000 | D_S_v1 | UNMEASURED | UNMEASURED | UNMEASURED | UNMEASURED |
| DEVELOPMENT_STACK_V1 | 0.050000 | D_M-B_v1 | UNMEASURED | UNMEASURED | UNMEASURED | UNMEASURED |
| DEVELOPMENT_STACK_V1 | 0.050000 | D_G_v1 | UNMEASURED | UNMEASURED | UNMEASURED | UNMEASURED |

## table 6 ds effect

Rates are fractions. UNMEASURED is a missing result, not zero.

| budget | metric | other | baseline | candidate | delta |
|---|---|---|---|---|---|
| 0.010000 | fnr | D_S | 0.754098 | 0.672131 | -0.081967 |
| 0.010000 | jfn | D_M-B_v1 | 0.032787 | 0.027322 | -0.005464 |
| 0.010000 | ejf | D_M-B_v1 | 0.008062 | 0.005285 | -0.002777 |
| 0.010000 | fn_jaccard | D_M-B_v1 | 0.043478 | 0.040323 | -0.003156 |
| 0.010000 | jfn | D_G_v1 | UNMEASURED | UNMEASURED | UNMEASURED |
| 0.010000 | ejf | D_G_v1 | UNMEASURED | UNMEASURED | UNMEASURED |
| 0.010000 | fn_jaccard | D_G_v1 | UNMEASURED | UNMEASURED | UNMEASURED |
| 0.010000 | all_detector_jfn | primary_stack | UNMEASURED | UNMEASURED | UNMEASURED |
| 0.010000 | all_detector_fn_count | primary_stack | UNMEASURED | UNMEASURED | UNMEASURED |
| 0.010000 | unique_catch_count | primary_stack | UNMEASURED | UNMEASURED | UNMEASURED |
| 0.010000 | unique_catch_rate | primary_stack | UNMEASURED | UNMEASURED | UNMEASURED |
| 0.010000 | recovery_given_others_miss | primary_stack | UNMEASURED | UNMEASURED | UNMEASURED |
| 0.030000 | fnr | D_S | 0.677596 | 0.453552 | -0.224044 |
| 0.030000 | jfn | D_M-B_v1 | 0.021858 | 0.016393 | -0.005464 |
| 0.030000 | ejf | D_M-B_v1 | 0.007047 | 0.006480 | -0.000567 |
| 0.030000 | fn_jaccard | D_M-B_v1 | 0.032258 | 0.035714 | 0.003456 |
| 0.030000 | jfn | D_G_v1 | UNMEASURED | UNMEASURED | UNMEASURED |
| 0.030000 | ejf | D_G_v1 | UNMEASURED | UNMEASURED | UNMEASURED |
| 0.030000 | fn_jaccard | D_G_v1 | UNMEASURED | UNMEASURED | UNMEASURED |
| 0.030000 | all_detector_jfn | primary_stack | UNMEASURED | UNMEASURED | UNMEASURED |
| 0.030000 | all_detector_fn_count | primary_stack | UNMEASURED | UNMEASURED | UNMEASURED |
| 0.030000 | unique_catch_count | primary_stack | UNMEASURED | UNMEASURED | UNMEASURED |
| 0.030000 | unique_catch_rate | primary_stack | UNMEASURED | UNMEASURED | UNMEASURED |
| 0.030000 | recovery_given_others_miss | primary_stack | UNMEASURED | UNMEASURED | UNMEASURED |
| 0.050000 | fnr | D_S | 0.546448 | 0.371585 | -0.174863 |
| 0.050000 | jfn | D_M-B_v1 | 0.010929 | 0.010929 | 0.000000 |
| 0.050000 | ejf | D_M-B_v1 | 0.004957 | 0.006868 | 0.001911 |
| 0.050000 | fn_jaccard | D_M-B_v1 | 0.020000 | 0.029412 | 0.009412 |
| 0.050000 | jfn | D_G_v1 | UNMEASURED | UNMEASURED | UNMEASURED |
| 0.050000 | ejf | D_G_v1 | UNMEASURED | UNMEASURED | UNMEASURED |
| 0.050000 | fn_jaccard | D_G_v1 | UNMEASURED | UNMEASURED | UNMEASURED |
| 0.050000 | all_detector_jfn | primary_stack | UNMEASURED | UNMEASURED | UNMEASURED |
| 0.050000 | all_detector_fn_count | primary_stack | UNMEASURED | UNMEASURED | UNMEASURED |
| 0.050000 | unique_catch_count | primary_stack | UNMEASURED | UNMEASURED | UNMEASURED |
| 0.050000 | unique_catch_rate | primary_stack | UNMEASURED | UNMEASURED | UNMEASURED |
| 0.050000 | recovery_given_others_miss | primary_stack | UNMEASURED | UNMEASURED | UNMEASURED |

## table 7 subgroups

Rates are fractions. UNMEASURED is a missing result, not zero.

| budget | subgroup | count | D_S_candidate | D_M-B | D_G | either_stronger_catches | all_three_miss |
|---|---|---|---|---|---|---|---|
| 0.010000 | under_16_attacks | 26 | 0 | 25 | UNMEASURED | UNMEASURED | UNMEASURED |
| 0.010000 | 64_plus_benign | 17 | 6 | 0 | UNMEASURED | UNMEASURED | UNMEASURED |
| 0.030000 | under_16_attacks | 26 | 0 | 26 | UNMEASURED | 26 | 0 |
| 0.030000 | 64_plus_benign | 17 | 12 | 3 | UNMEASURED | UNMEASURED | UNMEASURED |
| 0.050000 | under_16_attacks | 26 | 0 | 26 | UNMEASURED | 26 | 0 |
| 0.050000 | 64_plus_benign | 17 | 15 | 4 | UNMEASURED | UNMEASURED | UNMEASURED |

## Conditional pairwise failure

| budget | left | right | jfn_count | left_fn_count | right_fn_count | p_failure_left_given_right | p_failure_right_given_left |
|---|---|---|---|---|---|---|---|
| 0.010000 | D_M-B_v1 | D_S_v1 | 6 | 6 | 138 | 0.043478 | 1.000000 |
| 0.010000 | D_M-B_v1 | D_S_B2_LR | 5 | 6 | 123 | 0.040650 | 0.833333 |
| 0.030000 | D_M-B_v1 | D_S_v1 | 4 | 4 | 124 | 0.032258 | 1.000000 |
| 0.030000 | D_M-B_v1 | D_S_B2_LR | 3 | 4 | 83 | 0.036145 | 0.750000 |
| 0.050000 | D_M-B_v1 | D_S_v1 | 2 | 2 | 100 | 0.020000 | 1.000000 |
| 0.050000 | D_M-B_v1 | D_S_B2_LR | 2 | 2 | 68 | 0.029412 | 1.000000 |

## D_S improvement interpretation

At 1%, D_S/D_M-B shared misses change 6→5 out of 183 attacks. ΔJFN=-0.005464, conditional 95% interval [-0.016393, 0.000000]. The delta interval includes zero; evidence for a population gain is inconclusive.

At 3%, D_S/D_M-B shared misses change 4→3 out of 183 attacks. ΔJFN=-0.005464, conditional 95% interval [-0.016393, 0.000000]. The delta interval includes zero; evidence for a population gain is inconclusive.

At 5%, D_S/D_M-B shared misses change 2→2 out of 183 attacks. ΔJFN=0.000000, conditional 95% interval [0.000000, 0.000000]. The delta interval includes zero; evidence for a population gain is inconclusive.

Positive EJF describes failure association relative to an independence reference, not causal dependence. Smaller marginal D_S FNR can increase EJF or Jaccard even if shared-FN counts stay fixed. No broad independence claim follows from these few semantic misses.

Full-stack classification: **NO_CLEAR_CHANGE — D_G-dependent evidence unavailable**. D_S unique catches, recovery when D_M-B and D_G both miss, D_S/D_G association and all-three JFN remain unresolved. The available pairwise counts show one fewer shared miss at 1%/3%, but do not establish preserved primary-stack complementarity.

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
  "status": "BLOCKED",
  "data_status": "BLOCKED_MISSING_AUTHORITATIVE_DEVELOPMENT_DATA",
  "model_status": "BLOCKED_MISSING_PINNED_MODEL",
  "missing_inputs": [
    {
      "path": "data_governance/manifests/development_partition_manifest_v1.csv",
      "sha256": "9cdd5ecdd80f9ac3c8f05db63742721f4537ca2b64a2fe48f6c2b424b57483a6"
    },
    {
      "path": "Dataset/Raw/datasets/GitHub/Do-Not-Answer/datasets/Instruction/do_not_answer_en.csv",
      "sha256": "8585dc135d3b8692b2e464151a313f5164e30f06416e03aa5d11e6c3a21d980e"
    },
    {
      "path": "Dataset/Raw/datasets/HuggingFace/deepset-prompt-injections/data/test-00000-of-00001-701d16158af87368.parquet",
      "sha256": "39ac797cabc157eeed58435a08593b2952bb6cb16fc394a2d383f447cc7b246e"
    },
    {
      "path": "Dataset/Raw/datasets/HuggingFace/deepset-prompt-injections/data/train-00000-of-00001-9564e8b05b4757ab.parquet",
      "sha256": "2e10bc7ab30f542c97e4e83e2a5683000b5057d25ec10908784c631d44124c04"
    }
  ],
  "missing_snapshot_files": [
    {
      "file": "config.json",
      "sha256": "1dc4742d04507072cafffb7235dc5dba5af9ba126f7a9830b95ed7ec00fd9104"
    },
    {
      "file": "LICENSE",
      "sha256": "73755cee886613ae3135140882289e0a4955d5f0e90f8b1c1ffc962aa9082917"
    },
    {
      "file": "model.safetensors",
      "sha256": "5120e30bcd536ce285345d9ec104bea6bd6e8f94365b99a340c764f417ea5fa1"
    },
    {
      "file": "MODEL_CARD.md",
      "sha256": "7aacb25a94cab70530bca3545feda87bf7a935eaca92998222365b090acfd97c"
    },
    {
      "file": "README.md",
      "sha256": "5d2a3e0c46397609a784a5034dc823da408aa8b5a414828609f32dc18ee16933"
    },
    {
      "file": "special_tokens_map.json",
      "sha256": "9463f61e1b109a8eb4688b829260d7c6b1e6dff04c98ff7269bb89e2b92369b9"
    },
    {
      "file": "tokenizer.json",
      "sha256": "6eb983352e73f1697b883a8c3f6b66bdfa336ab3d29dd3687f8316d0ff2789c1"
    },
    {
      "file": "tokenizer_config.json",
      "sha256": "557b3d33d3f41b81ad769244e506549e98a1857d41dd58160aacd4d98d710b5a"
    },
    {
      "file": "USE_POLICY.md",
      "sha256": "5ae40fe842b87b5773c47cfd25992a496cc09b17cbb246968762f06352d89270"
    }
  ],
  "snapshot_path": "C:\\Users\\Asus\\Adversarial-Attack-Detection-for-LLMs\\detection_service\\.model-cache\\dg_v1\\snapshot-11614a155199674a0a95e6602d6ab0417b790ed0",
  "hf_cache_checked": "C:\\Users\\Asus\\.cache\\huggingface\\hub\\models--meta-llama--Llama-Prompt-Guard-2-22M\\snapshots\\11614a155199674a0a95e6602d6ab0417b790ed0",
  "hf_cache_present": false,
  "hf_access": {
    "status": "NOT_LOGGED_IN",
    "cli": "C:\\Users\\Asus\\OneDrive\\\ubb38\uc11c\\ChatGPT\\capstone\\dgad-repo\\main\\.venv\\Scripts\\hf.exe",
    "command": "hf auth login"
  },
  "package_mismatches": {
    "torch": {
      "expected": "2.6.0",
      "actual": null
    },
    "transformers": {
      "expected": "4.49.0",
      "actual": null
    },
    "tokenizers": {
      "expected": "0.21.4",
      "actual": null
    },
    "scikit-learn": {
      "expected": "1.6.1",
      "actual": null
    },
    "numpy": {
      "expected": "2.1.3",
      "actual": null
    },
    "pyarrow": {
      "expected": "19.0.1",
      "actual": null
    }
  },
  "python_3_11": true,
  "environment": {
    "python": "3.11.16",
    "platform": "Windows-10-10.0.26200-SP0",
    "packages": {
      "torch": null,
      "transformers": null,
      "tokenizers": null,
      "scikit-learn": null,
      "numpy": null,
      "pyarrow": null
    },
    "device": "cpu",
    "cuda_runtime_visibility": "NOT_PROBED_WITHOUT_MODEL_RUNTIME",
    "nvidia_smi_visible": true,
    "cpu_count": 12
  },
  "model_id": "meta-llama/Llama-Prompt-Guard-2-22M",
  "revision": "11614a155199674a0a95e6602d6ab0417b790ed0",
  "manifest_sha256": "9cdd5ecdd80f9ac3c8f05db63742721f4537ca2b64a2fe48f6c2b424b57483a6",
  "fold_sha256": "19dc0153cc257cc2331782d6dd61b7bb9fb8cb0ed88d3e782b69d5ba05c4bb8d",
  "verified_sha256": {
    "artifacts/quality/quality_001/development_folds_v1.csv": "19dc0153cc257cc2331782d6dd61b7bb9fb8cb0ed88d3e782b69d5ba05c4bb8d"
  },
  "live_rows_scored": 0,
  "unblock": [
    "Restore exact authoritative manifest and three approved source files; verify listed hashes. No supported exact bootstrap was found.",
    "hf auth login; hf auth whoami. Obtain access at https://huggingface.co/meta-llama/Llama-Prompt-Guard-2-22M if needed.",
    "hf download meta-llama/Llama-Prompt-Guard-2-22M --revision 11614a155199674a0a95e6602d6ab0417b790ed0 --local-dir \"C:\\Users\\Asus\\Adversarial-Attack-Detection-for-LLMs\\detection_service\\.model-cache\\dg_v1\\snapshot-11614a155199674a0a95e6602d6ab0417b790ed0\"",
    "Install detection_service/requirements.txt and pyarrow==19.0.1 tokenizers==0.21.4 in Python 3.11; keep frozen versions.",
    "python -m detection_service.scripts.guard_development --check",
    "python -m detection_service.scripts.guard_development --run",
    "python -m detection_service.scripts.common_mode_completion --release 3"
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
      "tests": 49,
      "failures": 0,
      "errors": 0,
      "skipped": 0,
      "path": "C:\\Users\\Asus\\Adversarial-Attack-Detection-for-LLMs\\artifacts\\common_mode\\development\\completion_v2\\track2_continuation_prerun.xml",
      "sha256": "7f2765273e38f6eca5aee930d6e762db68ece08d41fa6c9588cb12eb92d5f6aa"
    },
    "expanded": {
      "status": "PASS",
      "tests": 82,
      "failures": 0,
      "errors": 0,
      "skipped": 0,
      "path": "C:\\Users\\Asus\\Adversarial-Attack-Detection-for-LLMs\\artifacts\\common_mode\\development\\completion_v2\\track2_completion_tests.xml",
      "sha256": "8806527e3fcfec961e8d4fdc68a193515f22cf5d2e859ec8eb4ec0f664ceec03"
    }
  },
  "preservation": {
    "strict_original_suite": {
      "returncode": 1,
      "status": "FAIL_PREEXISTING_LINE_ENDING_DRIFT",
      "command": "python -m detection_service.scripts.verify_quality_preservation --mode check"
    },
    "baseline_files": 96,
    "exact_byte_matches": 59,
    "newline_only_matches": 37,
    "newline_differences": [
      {
        "path": "artifacts/models/dg_v1/environment.json",
        "expected_sha256": "e23929244cd567f6d1c236fe050a7b894bbfe12a7ae4c51f47d7aa2bbe739e2d",
        "actual_sha256": "9269b0b2ec53a92edec118937c5f07ceb6ed2a2ebdb9184c85da8ab79d453706",
        "matching_line_ending": [
          "CRLF"
        ]
      },
      {
        "path": "artifacts/models/dg_v1/qualification.json",
        "expected_sha256": "a8e6163dadd334324c9ca147ed650451e438ceddee4b907f28648f0539e2a4d6",
        "actual_sha256": "83b990f25dba882f14c5d3aba283797dd91fed85942190d36616e8b4304a72f6",
        "matching_line_ending": [
          "CRLF"
        ]
      },
      {
        "path": "detection_service/app/__init__.py",
        "expected_sha256": "d85d765bcbe5b99ebc7bf88f5739dfd584d7ebd60c8a4ab2fe6e39dfda35743c",
        "actual_sha256": "0518a7a8cddf7d93c1511930658ce71a53311a41fa374092ccb0b11a23a4c63d",
        "matching_line_ending": [
          "LF"
        ]
      },
      {
        "path": "detection_service/app/api/__init__.py",
        "expected_sha256": "02ccb8edbbf9d8b828678cdacb48cd7f8bfabbeb2a1524945c13e4b0670de88f",
        "actual_sha256": "f6ab5b294d896a5890a52082541df8b9795bf43f2661f903ddcc17ee32e7bf62",
        "matching_line_ending": [
          "LF"
        ]
      },
      {
        "path": "detection_service/app/api/detect.py",
        "expected_sha256": "ef277169c3324bb726d3f89b092fa75e5d918c5d06f076ea7068971e42548b0a",
        "actual_sha256": "32b1a22754b3957d893d6a0ce105539570ad5208dffe339219d0595f6c216102",
        "matching_line_ending": [
          "LF"
        ]
      },
      {
        "path": "detection_service/app/contracts/__init__.py",
        "expected_sha256": "1f6815e24cf9d72c3943979e2bef46cb2d94bee6be0b05291854884be7cf0aa3",
        "actual_sha256": "d2c894832c75b9cb34df34f12c43401af301b886d864074eab9723e6fed04794",
        "matching_line_ending": [
          "LF"
        ]
      },
      {
        "path": "detection_service/app/contracts/detection_request.py",
        "expected_sha256": "2ce4557b999d020f1cf12e680e2f7dba060d2781b81d6e219f9fab333a5f650b",
        "actual_sha256": "807ac049d6074191614cb29711059abd7ba8e543b31d0fcb00b52bfe22a1044b",
        "matching_line_ending": [
          "LF"
        ]
      },
      {
        "path": "detection_service/app/contracts/detector_result.py",
        "expected_sha256": "1fa6e3edf788a0660c9ec15d1a68875d8281fe841083eadc3cdd91caf5911004",
        "actual_sha256": "70f1f90045a30e11668e3dd1bce16feacab92beb16cb68dbb41134188bfed37b",
        "matching_line_ending": [
          "LF"
        ]
      },
      {
        "path": "detection_service/app/core/__init__.py",
        "expected_sha256": "6f5b3fc7ad823c3d746c898760a4d95d8f4773df41b108a32ecb7fd8a613c24c",
        "actual_sha256": "1a2dd7118cc8753d0b06c50b0de6da5330f071150de0b45a6987e35f3edbfc75",
        "matching_line_ending": [
          "LF"
        ]
      },
      {
        "path": "detection_service/app/core/settings.py",
        "expected_sha256": "2ac8549fd5dfd37ec5cce16aef27d0e9fe4b747b9e95bf32a249e4fda8726a7f",
        "actual_sha256": "0f4597cc582d295efb79613a685fd4fba7deb6af00912daad0365dc950721f0d",
        "matching_line_ending": [
          "LF"
        ]
      },
      {
        "path": "detection_service/app/detectors/__init__.py",
        "expected_sha256": "36ff6ace2f48d6f44c06d2ac02759ce4562c358b27841518fedd0c774a99d213",
        "actual_sha256": "c2a3a0a8ea50c2441bf29d11825c81e03f034e5fab84452109a39546cbe769a8",
        "matching_line_ending": [
          "LF"
        ]
      },
      {
        "path": "detection_service/app/detectors/base.py",
        "expected_sha256": "e0b6d7e9f0bfdffd8fa90f49d6ca82b46a7ef31a7acd01605b685ff7c2f307de",
        "actual_sha256": "ca861bf71282487c5816a07ca76162960fe1bc4e023871e0e010cb35c9a270e3",
        "matching_line_ending": [
          "LF"
        ]
      },
      {
        "path": "detection_service/app/detectors/guard/__init__.py",
        "expected_sha256": "85d87a5317f2c148a67d66d56d8d5d65329af5d73572a57e443335c303378941",
        "actual_sha256": "3f98520abf13cc1336ce4f511fdb023c35061b635acf9b0264d9883c2f8f0eb7",
        "matching_line_ending": [
          "LF"
        ]
      },
      {
        "path": "detection_service/app/detectors/guard/config.py",
        "expected_sha256": "ac39082b44400db70c8e13a2ae51a4d9632fd5bc458bfcceff708b2d3784cc53",
        "actual_sha256": "4491429fbd940617a9549871ff200d1953a4016bcce4c75148a5d332c0944d4c",
        "matching_line_ending": [
          "LF"
        ]
      },
      {
        "path": "detection_service/app/detectors/guard/detector.py",
        "expected_sha256": "cad7fa7ac3a43dc935eb30d964c8cef41a49f07618b97bfef73740d408c6982a",
        "actual_sha256": "f1d052e27e92e6b00266d6461dd14d44b4926880013a447454bd60544ab36f5a",
        "matching_line_ending": [
          "LF"
        ]
      },
      {
        "path": "detection_service/app/detectors/guard/model.py",
        "expected_sha256": "bb6c06f0ea2de880c95a8a4e034b1a6eec2dffc39077a220d8076d5f9991ccd9",
        "actual_sha256": "85daaf9881b65d77b34fcb0d4615abf11a10c88ea89e018685eb594f6fbac6e5",
        "matching_line_ending": [
          "LF"
        ]
      },
      {
        "path": "detection_service/app/detectors/semantic/__init__.py",
        "expected_sha256": "08d2f2abd25b0fe212e50a2efd1550a1ab12f24349385343b3bdf1f7ace5bc69",
        "actual_sha256": "0c51475917c203d2dd901864b0d2166a9539a1671eea4058c0291f9d77ee9301",
        "matching_line_ending": [
          "LF"
        ]
      },
      {
        "path": "detection_service/app/detectors/semantic/calibration.py",
        "expected_sha256": "06e7d3679ecfcb8f585e8b7741c261340bbecff838a30aadf52ceef1436c1f7b",
        "actual_sha256": "5d099270bdbd810b2b6d5585a92adc8127f3178d7fbac2cfc56e8ff88a27a948",
        "matching_line_ending": [
          "LF"
        ]
      },
      {
        "path": "detection_service/app/detectors/semantic/classifier.py",
        "expected_sha256": "8db3103ae3b182fb94f4494bfcf9669210dd4bd81e5df680136401db9202e8cb",
        "actual_sha256": "5f88e8742576b1751f15712c2439763a1bd01d7ebfb4dbaecbaa913a4430317f",
        "matching_line_ending": [
          "LF"
        ]
      },
      {
        "path": "detection_service/app/detectors/semantic/config.py",
        "expected_sha256": "2a3fdd8151e21056b614b276f2d07aac7b39141f11c6e1af9e8f08087c4ff509",
        "actual_sha256": "1dce0ce9132889fdb2339fb133bf6487c15f89fdfc6afccd353a18a1dd9c82f3",
        "matching_line_ending": [
          "LF"
        ]
      },
      {
        "path": "detection_service/app/detectors/semantic/detector.py",
        "expected_sha256": "495bbaf7426be1628e5a19bf975417d1632825201ba81f929a1f1d0320d36868",
        "actual_sha256": "7b9544c055f094328566008b71441ce95453de85810553ada5a8cc12cb7c74e4",
        "matching_line_ending": [
          "LF"
        ]
      },
      {
        "path": "detection_service/app/detectors/semantic/embeddings.py",
        "expected_sha256": "8aec0ad9d7a6e8430293a36442f6e59fd019c2bef36307b6c8bed80eadb90352",
        "actual_sha256": "e36d9559b46035597c0b28543fef563487af1a06aeb5d835884658f4b77590fe",
        "matching_line_ending": [
          "LF"
        ]
      },
      {
        "path": "detection_service/app/detectors/semantic_finetuned/__init__.py",
        "expected_sha256": "535d07903412868b3607e0e2cde0cbbda08ca656f39c7526ebc6be80c5ce3287",
        "actual_sha256": "698b7794915a8a3f0300cbdc15d420b102f4f8fca19eca761efe38c5aa222357",
        "matching_line_ending": [
          "LF"
        ]
      },
      {
        "path": "detection_service/app/detectors/semantic_finetuned/calibration.py",
        "expected_sha256": "821c1b748dba36bfbfa9f991c4034fa6f9abd8784695c94d34175c3e1d2dbe7e",
        "actual_sha256": "a931196acc0f5a5e4c9fa483075d7a6f67a7434655e30b9d5365fd8665187c4b",
        "matching_line_ending": [
          "LF"
        ]
      },
      {
        "path": "detection_service/app/detectors/semantic_finetuned/config.py",
        "expected_sha256": "5880f5e98e7ca935f8b421877f0242450f7cbd04397605335f0d27b9bc5ec4e0",
        "actual_sha256": "30410646a9ff917806b666607d22a585c1bf6e09b083d5d4712b0275ccb50ba1",
        "matching_line_ending": [
          "LF"
        ]
      },
      {
        "path": "detection_service/app/detectors/semantic_finetuned/data.py",
        "expected_sha256": "4f4d74fb471754ab4bcb359e2d81521e61725701338f4f1e82e69d7ee2c46145",
        "actual_sha256": "4e37fe1419796756eb3553c17cc3a45b4f456c47b47ebb0151565f2597bad8f4",
        "matching_line_ending": [
          "LF"
        ]
      },
      {
        "path": "detection_service/app/detectors/semantic_finetuned/detector.py",
        "expected_sha256": "0c13a0da3a762cd0bfe374ea67d8a37b9c9b49851adaebd6d116e05f1b98666c",
        "actual_sha256": "31569a6baa481a5f8be39a15f4ef4c0ee0d107a1f3c09dea58f469900a9f08f2",
        "matching_line_ending": [
          "LF"
        ]
      },
      {
        "path": "detection_service/app/detectors/statistical/__init__.py",
        "expected_sha256": "32ec738f8a25da0552facb413a694b038876ec4b35c56d21de5ed25145608a2e",
        "actual_sha256": "0db252975ca0dcf599cfa2d91015012598e502845f3108fb07507825aa88b42b",
        "matching_line_ending": [
          "LF"
        ]
      },
      {
        "path": "detection_service/app/detectors/statistical/config.py",
        "expected_sha256": "e5cc8512c3acbdad323ec826176513fd8173c8864c7aa8ae081a7503d46f7f17",
        "actual_sha256": "7f2c0366c02f13259ce22fc578c934d5e2486442d23f8873bc010d8837f7cf4c",
        "matching_line_ending": [
          "LF"
        ]
      },
      {
        "path": "detection_service/app/detectors/statistical/features.py",
        "expected_sha256": "b2ccdc4cc64789170a730990570373079645b870f027f6d11da2d78fe71866fa",
        "actual_sha256": "c5a1ce76d2d4e964aed89f19404443d5b412a447c8b2812f696bd14111401f06",
        "matching_line_ending": [
          "LF"
        ]
      },
      {
        "path": "detection_service/app/detectors/statistical/perplexity_detector.py",
        "expected_sha256": "032ab0652fdc5d4ddd3d6e833d558f29d63d04164e90901dc3eecd05b3dde599",
        "actual_sha256": "cc8858a6baba6f93f0c7e30c62122c38e578a9f4f235ffd4feb3b4beb1018d77",
        "matching_line_ending": [
          "LF"
        ]
      },
      {
        "path": "detection_service/app/detectors/statistical/perplexity_engine.py",
        "expected_sha256": "cd978bd44d719dbee29b510f8f6138638a2ff30d8d23a6a379fdf48e5c26b4c1",
        "actual_sha256": "3848cbb4002dc54feb6393e6850667280d002387d57fc15e31d78b5e5ce9834b",
        "matching_line_ending": [
          "LF"
        ]
      },
      {
        "path": "detection_service/app/detectors/statistical_risk/__init__.py",
        "expected_sha256": "a6853e1f79ddc4bb24d1316db9bde103c84820f1cc47241030b250397e68cd8b",
        "actual_sha256": "9fad047e51ee1533cb69e7824ea09d0e19d6067a84c0888ed9887427525bc7e3",
        "matching_line_ending": [
          "LF"
        ]
      },
      {
        "path": "detection_service/app/detectors/statistical_risk/detector.py",
        "expected_sha256": "e41d4b65f2bd20cbb4461fe49f2c673ad6e8b11f25a9fcac0bc69ef27b794ce4",
        "actual_sha256": "3593e8efe2d77eaee0be95159e95464554115d55131c5bbac309db936555793c",
        "matching_line_ending": [
          "LF"
        ]
      },
      {
        "path": "detection_service/app/detectors/statistical_risk/schema.py",
        "expected_sha256": "994e5660a8eaa69749f31f8afc6fecfc2d22adfa3e17fcb190c08ed22898955a",
        "actual_sha256": "3ad077ef43541729b25492b3b99792a776fde9d1090e4a1d0fdb4573f5caf90f",
        "matching_line_ending": [
          "LF"
        ]
      },
      {
        "path": "detection_service/app/detectors/statistical_risk/scorer.py",
        "expected_sha256": "a410637562e201b8d64ca8670e5c034f827f416bc7b6655da94de97817a17c12",
        "actual_sha256": "65c59321b3c8d3f8f5d6f35750a1959a1456a8f08840da6555df1d7d87fe15be",
        "matching_line_ending": [
          "LF"
        ]
      },
      {
        "path": "detection_service/app/main.py",
        "expected_sha256": "5cb01f1b7b41c33a739e4658cdedb33f85b7c3761c1cc533701ea0f7fa78677e",
        "actual_sha256": "8640d197df0b29913621c8adb7c8c59515bc457800651bcf370972e309f24121",
        "matching_line_ending": [
          "LF"
        ]
      }
    ],
    "unexplained_changes": 0,
    "tracked_detector_diff": "EMPTY",
    "original_track2_artifacts_and_reports_verified": 24,
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
    "interpretation": "Strict preservation suite is not passing bytewise on this fresh checkout. Every difference is verified LF/CRLF only; no baseline bytes/hashes modified."
  }
}
```

## Isolation

D_S/D_M-B/D_G training: NO. CALIBRATION/VALIDATION/protected prompt payloads: NO. E1-E10, adaptive generation, verifier, routing, final threshold and fusion: NO. Historical predictions/artifacts and first Track-2 reports are byte-preserved.
