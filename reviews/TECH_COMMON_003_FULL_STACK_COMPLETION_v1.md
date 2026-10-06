# FULL THREE-DETECTOR DEVELOPMENT FINAL REPORT

STATUS: **PASS**

## Repository and provenance

Branch: tech/common-003-dg-completion. Completion start: `3ef06414836a51b3409e7be9251da7753299da3a`. D_G model/run code commit: `3a053f3224e56d9e7b483b72303e822af12e5741`. Common analysis execution: `3a053f3224e56d9e7b483b72303e822af12e5741`. Later commits contain post-run acceptance evidence, not retroactive run provenance. Publication commit/push identifiers are returned after synchronization.

## Environment

```json
{
  "cpu_count": 16,
  "cuda_runtime_visibility": "NOT_PROBED_WITHOUT_MODEL_RUNTIME",
  "device": "cpu",
  "nvidia_smi_visible": true,
  "packages": {
    "numpy": "2.1.3",
    "pyarrow": "19.0.1",
    "scikit-learn": "1.6.1",
    "tokenizers": "0.21.4",
    "torch": "2.6.0",
    "transformers": "4.49.0"
  },
  "platform": "Windows-10-10.0.26200-SP0",
  "python": "3.11.9"
}
```

Device: CPU; exact local snapshot, HF_HUB_OFFLINE=1 and TRANSFORMERS_OFFLINE=1. No package installation or model download.

## Authoritative fixture

1,135 BASE_TRAIN rows; 183 positive, 952 negative. Manifest `9cdd5ecdd80f9ac3c8f05db63742721f4537ca2b64a2fe48f6c2b424b57483a6`; folds `19dc0153cc257cc2331782d6dd61b7bb9fb8cb0ed88d3e782b69d5ba05c4bb8d`. Unique IDs, missing IDs, labels, canonical lineage and exact selected source-text hashes pass. Source containers include other partitions, but only BASE_TRAIN scalars were selected. No reserved/protected prompt scoring.

## D_G characterization

Model `meta-llama/Llama-Prompt-Guard-2-22M`, revision `11614a155199674a0a95e6602d6ab0417b790ed0`. Frozen 512-token capacity, 510-token content chunks, overlap 64, stride 446, complete tail coverage. Raw=max malicious-class chunk softmax; native=OR of malicious chunk argmax. No calibration.

## Table 1 Guard

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


## Table 2 Individual

| budget | detector | fpr | recall | fnr | tp | fn | fp | tn | roc_auc | pr_auc |
|---|---|---|---|---|---|---|---|---|---|---|
| 0.010000 | D_G_v1 | 0.006303 | 0.185792 | 0.814208 | 34 | 149 | 6 | 946 | 0.814954 | 0.500652 |
| 0.010000 | D_M-B_v1 | 0.007353 | 0.967213 | 0.032787 | 177 | 6 | 7 | 945 | 0.996349 | 0.987704 |
| 0.010000 | D_S_B2_LR | 0.009454 | 0.327869 | 0.672131 | 60 | 123 | 9 | 943 | 0.896760 | 0.731587 |
| 0.010000 | D_S_v1 | 0.007353 | 0.245902 | 0.754098 | 45 | 138 | 7 | 945 | 0.810086 | 0.576684 |
| 0.030000 | D_G_v1 | 0.017857 | 0.229508 | 0.770492 | 42 | 141 | 17 | 935 | 0.814954 | 0.500652 |
| 0.030000 | D_M-B_v1 | 0.023109 | 0.978142 | 0.021858 | 179 | 4 | 22 | 930 | 0.996349 | 0.987704 |
| 0.030000 | D_S_B2_LR | 0.029412 | 0.546448 | 0.453552 | 100 | 83 | 28 | 924 | 0.896760 | 0.731587 |
| 0.030000 | D_S_v1 | 0.029412 | 0.322404 | 0.677596 | 59 | 124 | 28 | 924 | 0.810086 | 0.576684 |
| 0.050000 | D_G_v1 | 0.046218 | 0.267760 | 0.732240 | 49 | 134 | 44 | 908 | 0.814954 | 0.500652 |
| 0.050000 | D_M-B_v1 | 0.035714 | 0.989071 | 0.010929 | 181 | 2 | 34 | 918 | 0.996349 | 0.987704 |
| 0.050000 | D_S_B2_LR | 0.048319 | 0.628415 | 0.371585 | 115 | 68 | 46 | 906 | 0.896760 | 0.731587 |
| 0.050000 | D_S_v1 | 0.049370 | 0.453552 | 0.546448 | 83 | 100 | 47 | 905 | 0.810086 | 0.576684 |


## Table 3 Pairwise

| budget | stack | left | right | jfn_count | jfn | independence_reference | ejf | fn_jaccard |
|---|---|---|---|---|---|---|---|---|
| 0.010000 | DEVELOPMENT_STACK_V1 | D_M-B_v1 | D_S_v1 | 6 | 0.032787 | 0.024725 | 0.008062 | 0.043478 |
| 0.010000 | DEVELOPMENT_STACK_V1 | D_G_v1 | D_S_v1 | 111 | 0.606557 | 0.613993 | -0.007435 | 0.630682 |
| 0.010000 | DEVELOPMENT_STACK_V1 | D_G_v1 | D_M-B_v1 | 6 | 0.032787 | 0.026695 | 0.006092 | 0.040268 |
| 0.010000 | DEVELOPMENT_STACK_CANDIDATE | D_M-B_v1 | D_S_B2_LR | 5 | 0.027322 | 0.022037 | 0.005285 | 0.040323 |
| 0.010000 | DEVELOPMENT_STACK_CANDIDATE | D_G_v1 | D_S_B2_LR | 96 | 0.524590 | 0.547254 | -0.022664 | 0.545455 |
| 0.010000 | DEVELOPMENT_STACK_CANDIDATE | D_G_v1 | D_M-B_v1 | 6 | 0.032787 | 0.026695 | 0.006092 | 0.040268 |
| 0.030000 | DEVELOPMENT_STACK_V1 | D_M-B_v1 | D_S_v1 | 4 | 0.021858 | 0.014811 | 0.007047 | 0.032258 |
| 0.030000 | DEVELOPMENT_STACK_V1 | D_G_v1 | D_S_v1 | 92 | 0.502732 | 0.522082 | -0.019350 | 0.531792 |
| 0.030000 | DEVELOPMENT_STACK_V1 | D_G_v1 | D_M-B_v1 | 4 | 0.021858 | 0.016841 | 0.005017 | 0.028369 |
| 0.030000 | DEVELOPMENT_STACK_CANDIDATE | D_M-B_v1 | D_S_B2_LR | 3 | 0.016393 | 0.009914 | 0.006480 | 0.035714 |
| 0.030000 | DEVELOPMENT_STACK_CANDIDATE | D_G_v1 | D_S_B2_LR | 61 | 0.333333 | 0.349458 | -0.016125 | 0.374233 |
| 0.030000 | DEVELOPMENT_STACK_CANDIDATE | D_G_v1 | D_M-B_v1 | 4 | 0.021858 | 0.016841 | 0.005017 | 0.028369 |
| 0.050000 | DEVELOPMENT_STACK_V1 | D_M-B_v1 | D_S_v1 | 2 | 0.010929 | 0.005972 | 0.004957 | 0.020000 |
| 0.050000 | DEVELOPMENT_STACK_V1 | D_G_v1 | D_S_v1 | 68 | 0.371585 | 0.400131 | -0.028547 | 0.409639 |
| 0.050000 | DEVELOPMENT_STACK_V1 | D_G_v1 | D_M-B_v1 | 2 | 0.010929 | 0.008003 | 0.002926 | 0.014925 |
| 0.050000 | DEVELOPMENT_STACK_CANDIDATE | D_M-B_v1 | D_S_B2_LR | 2 | 0.010929 | 0.004061 | 0.006868 | 0.029412 |
| 0.050000 | DEVELOPMENT_STACK_CANDIDATE | D_G_v1 | D_S_B2_LR | 47 | 0.256831 | 0.272089 | -0.015259 | 0.303226 |
| 0.050000 | DEVELOPMENT_STACK_CANDIDATE | D_G_v1 | D_M-B_v1 | 2 | 0.010929 | 0.008003 | 0.002926 | 0.014925 |


## Table 4 All Detector

| budget | stack | all_detector_fn_count | all_detector_jfn |
|---|---|---|---|
| 0.010000 | DEVELOPMENT_STACK_CANDIDATE | 5 | 0.027322 |
| 0.010000 | DEVELOPMENT_STACK_V1 | 6 | 0.032787 |
| 0.030000 | DEVELOPMENT_STACK_CANDIDATE | 3 | 0.016393 |
| 0.030000 | DEVELOPMENT_STACK_V1 | 4 | 0.021858 |
| 0.050000 | DEVELOPMENT_STACK_CANDIDATE | 2 | 0.010929 |
| 0.050000 | DEVELOPMENT_STACK_V1 | 2 | 0.010929 |


## Table 5 Unique

| budget | stack | detector | unique_catch_count | unique_catch_rate | other_members_miss_count | recovery_given_others_miss |
|---|---|---|---|---|---|---|
| 0.010000 | DEVELOPMENT_STACK_CANDIDATE | D_S_B2_LR | 1 | 0.005464 | 6 | 0.166667 |
| 0.010000 | DEVELOPMENT_STACK_CANDIDATE | D_M-B_v1 | 91 | 0.497268 | 96 | 0.947917 |
| 0.010000 | DEVELOPMENT_STACK_CANDIDATE | D_G_v1 | 0 | 0.000000 | 5 | 0.000000 |
| 0.010000 | DEVELOPMENT_STACK_V1 | D_S_v1 | 0 | 0.000000 | 6 | 0.000000 |
| 0.010000 | DEVELOPMENT_STACK_V1 | D_M-B_v1 | 105 | 0.573770 | 111 | 0.945946 |
| 0.010000 | DEVELOPMENT_STACK_V1 | D_G_v1 | 0 | 0.000000 | 6 | 0.000000 |
| 0.030000 | DEVELOPMENT_STACK_CANDIDATE | D_S_B2_LR | 1 | 0.005464 | 4 | 0.250000 |
| 0.030000 | DEVELOPMENT_STACK_CANDIDATE | D_M-B_v1 | 58 | 0.316940 | 61 | 0.950820 |
| 0.030000 | DEVELOPMENT_STACK_CANDIDATE | D_G_v1 | 0 | 0.000000 | 3 | 0.000000 |
| 0.030000 | DEVELOPMENT_STACK_V1 | D_S_v1 | 0 | 0.000000 | 4 | 0.000000 |
| 0.030000 | DEVELOPMENT_STACK_V1 | D_M-B_v1 | 88 | 0.480874 | 92 | 0.956522 |
| 0.030000 | DEVELOPMENT_STACK_V1 | D_G_v1 | 0 | 0.000000 | 4 | 0.000000 |
| 0.050000 | DEVELOPMENT_STACK_CANDIDATE | D_S_B2_LR | 0 | 0.000000 | 2 | 0.000000 |
| 0.050000 | DEVELOPMENT_STACK_CANDIDATE | D_M-B_v1 | 45 | 0.245902 | 47 | 0.957447 |
| 0.050000 | DEVELOPMENT_STACK_CANDIDATE | D_G_v1 | 0 | 0.000000 | 2 | 0.000000 |
| 0.050000 | DEVELOPMENT_STACK_V1 | D_S_v1 | 0 | 0.000000 | 2 | 0.000000 |
| 0.050000 | DEVELOPMENT_STACK_V1 | D_M-B_v1 | 66 | 0.360656 | 68 | 0.970588 |
| 0.050000 | DEVELOPMENT_STACK_V1 | D_G_v1 | 0 | 0.000000 | 2 | 0.000000 |


## Table 6 Ds Effect

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


## Table 7 Under 16 Attacks

| budget | attacks | D_G_v1 | D_M-B_v1 | D_S_B2_LR | D_S_v1 | either_stronger_catches | all_three_miss |
|---|---|---|---|---|---|---|---|
| 0.010000 | 26 | 6 | 25 | 0 | 0 | 25 | 1 |
| 0.030000 | 26 | 7 | 26 | 0 | 1 | 26 | 0 |
| 0.050000 | 26 | 7 | 26 | 0 | 2 | 26 | 0 |


## Table 8 Long Benign

| budget | benign | D_G_v1 | D_M-B_v1 | D_S_B2_LR | D_S_v1 | all_three_fp | ds_only_fp | ds_dm_overlap | ds_dg_overlap | dm_dg_overlap |
|---|---|---|---|---|---|---|---|---|---|---|
| 0.010000 | 17 | 0 | 0 | 6 | 3 | 0 | 6 | 0 | 0 | 0 |
| 0.030000 | 17 | 0 | 3 | 12 | 7 | 0 | 11 | 1 | 0 | 0 |
| 0.050000 | 17 | 0 | 4 | 15 | 9 | 0 | 12 | 3 | 0 | 0 |


## D_G fold characterization

```json
[
  {
    "fold": 0,
    "rows": 227,
    "positive": 36,
    "negative": 191,
    "roc_auc": 0.7901396160558464,
    "pr_auc": 0.41898114439368783,
    "fixed_fpr": [
      {
        "budget": 0.01,
        "fn": 33,
        "fnr": 0.9166666666666666,
        "fp": 1,
        "fpr": 0.005235602094240838,
        "negative_denominator": 191,
        "no_positive_predictions": false,
        "positive_denominator": 36,
        "recall": 0.08333333333333333,
        "role": "DEVELOPMENT_DESCRIPTIVE_OPERATING_CAPACITY",
        "threshold": 0.9316856861114502,
        "tn": 190,
        "tp": 3
      },
      {
        "budget": 0.03,
        "fn": 31,
        "fnr": 0.8611111111111112,
        "fp": 2,
        "fpr": 0.010471204188481676,
        "negative_denominator": 191,
        "no_positive_predictions": false,
        "positive_denominator": 36,
        "recall": 0.1388888888888889,
        "role": "DEVELOPMENT_DESCRIPTIVE_OPERATING_CAPACITY",
        "threshold": 0.3172931373119354,
        "tn": 189,
        "tp": 5
      },
      {
        "budget": 0.05,
        "fn": 28,
        "fnr": 0.7777777777777778,
        "fp": 8,
        "fpr": 0.041884816753926704,
        "negative_denominator": 191,
        "no_positive_predictions": false,
        "positive_denominator": 36,
        "recall": 0.2222222222222222,
        "role": "DEVELOPMENT_DESCRIPTIVE_OPERATING_CAPACITY",
        "threshold": 0.06180993467569351,
        "tn": 183,
        "tp": 8
      }
    ],
    "native": {
      "accuracy": 0.8502202643171806,
      "f1": 0.19047619047619047,
      "fn": 32,
      "fnr": 0.8888888888888888,
      "fp": 2,
      "fpr": 0.010471204188481676,
      "precision": 0.6666666666666666,
      "recall": 0.1111111111111111,
      "specificity": 0.9895287958115183,
      "tn": 189,
      "tp": 4
    }
  },
  {
    "fold": 1,
    "rows": 227,
    "positive": 36,
    "negative": 191,
    "roc_auc": 0.8096276905177429,
    "pr_auc": 0.4911815607653366,
    "fixed_fpr": [
      {
        "budget": 0.01,
        "fn": 29,
        "fnr": 0.8055555555555556,
        "fp": 1,
        "fpr": 0.005235602094240838,
        "negative_denominator": 191,
        "no_positive_predictions": false,
        "positive_denominator": 36,
        "recall": 0.19444444444444445,
        "role": "DEVELOPMENT_DESCRIPTIVE_OPERATING_CAPACITY",
        "threshold": 0.8497665524482727,
        "tn": 190,
        "tp": 7
      },
      {
        "budget": 0.03,
        "fn": 27,
        "fnr": 0.75,
        "fp": 5,
        "fpr": 0.02617801047120419,
        "negative_denominator": 191,
        "no_positive_predictions": false,
        "positive_denominator": 36,
        "recall": 0.25,
        "role": "DEVELOPMENT_DESCRIPTIVE_OPERATING_CAPACITY",
        "threshold": 0.078913614153862,
        "tn": 186,
        "tp": 9
      },
      {
        "budget": 0.05,
        "fn": 27,
        "fnr": 0.75,
        "fp": 5,
        "fpr": 0.02617801047120419,
        "negative_denominator": 191,
        "no_positive_predictions": false,
        "positive_denominator": 36,
        "recall": 0.25,
        "role": "DEVELOPMENT_DESCRIPTIVE_OPERATING_CAPACITY",
        "threshold": 0.078913614153862,
        "tn": 186,
        "tp": 9
      }
    ],
    "native": {
      "accuracy": 0.8634361233480177,
      "f1": 0.3111111111111111,
      "fn": 29,
      "fnr": 0.8055555555555556,
      "fp": 2,
      "fpr": 0.010471204188481676,
      "precision": 0.7777777777777778,
      "recall": 0.19444444444444445,
      "specificity": 0.9895287958115183,
      "tn": 189,
      "tp": 7
    }
  },
  {
    "fold": 2,
    "rows": 227,
    "positive": 37,
    "negative": 190,
    "roc_auc": 0.8540540540540541,
    "pr_auc": 0.47552231876543294,
    "fixed_fpr": [
      {
        "budget": 0.01,
        "fn": 34,
        "fnr": 0.918918918918919,
        "fp": 1,
        "fpr": 0.005263157894736842,
        "negative_denominator": 190,
        "no_positive_predictions": false,
        "positive_denominator": 37,
        "recall": 0.08108108108108109,
        "role": "DEVELOPMENT_DESCRIPTIVE_OPERATING_CAPACITY",
        "threshold": 0.9516217708587646,
        "tn": 189,
        "tp": 3
      },
      {
        "budget": 0.03,
        "fn": 31,
        "fnr": 0.8378378378378378,
        "fp": 5,
        "fpr": 0.02631578947368421,
        "negative_denominator": 190,
        "no_positive_predictions": false,
        "positive_denominator": 37,
        "recall": 0.16216216216216217,
        "role": "DEVELOPMENT_DESCRIPTIVE_OPERATING_CAPACITY",
        "threshold": 0.26131361722946167,
        "tn": 185,
        "tp": 6
      },
      {
        "budget": 0.05,
        "fn": 30,
        "fnr": 0.8108108108108109,
        "fp": 6,
        "fpr": 0.031578947368421054,
        "negative_denominator": 190,
        "no_positive_predictions": false,
        "positive_denominator": 37,
        "recall": 0.1891891891891892,
        "role": "DEVELOPMENT_DESCRIPTIVE_OPERATING_CAPACITY",
        "threshold": 0.050292547792196274,
        "tn": 184,
        "tp": 7
      }
    ],
    "native": {
      "accuracy": 0.8414096916299559,
      "f1": 0.18181818181818182,
      "fn": 33,
      "fnr": 0.8918918918918919,
      "fp": 3,
      "fpr": 0.015789473684210527,
      "precision": 0.5714285714285714,
      "recall": 0.10810810810810811,
      "specificity": 0.9842105263157894,
      "tn": 187,
      "tp": 4
    }
  },
  {
    "fold": 3,
    "rows": 227,
    "positive": 37,
    "negative": 190,
    "roc_auc": 0.7947368421052632,
    "pr_auc": 0.5419081281020942,
    "fixed_fpr": [
      {
        "budget": 0.01,
        "fn": 27,
        "fnr": 0.7297297297297297,
        "fp": 0,
        "fpr": 0.0,
        "negative_denominator": 190,
        "no_positive_predictions": false,
        "positive_denominator": 37,
        "recall": 0.2702702702702703,
        "role": "DEVELOPMENT_DESCRIPTIVE_OPERATING_CAPACITY",
        "threshold": 0.8728941679000854,
        "tn": 190,
        "tp": 10
      },
      {
        "budget": 0.03,
        "fn": 25,
        "fnr": 0.6756756756756757,
        "fp": 5,
        "fpr": 0.02631578947368421,
        "negative_denominator": 190,
        "no_positive_predictions": false,
        "positive_denominator": 37,
        "recall": 0.32432432432432434,
        "role": "DEVELOPMENT_DESCRIPTIVE_OPERATING_CAPACITY",
        "threshold": 0.30526429414749146,
        "tn": 185,
        "tp": 12
      },
      {
        "budget": 0.05,
        "fn": 25,
        "fnr": 0.6756756756756757,
        "fp": 5,
        "fpr": 0.02631578947368421,
        "negative_denominator": 190,
        "no_positive_predictions": false,
        "positive_denominator": 37,
        "recall": 0.32432432432432434,
        "role": "DEVELOPMENT_DESCRIPTIVE_OPERATING_CAPACITY",
        "threshold": 0.30526429414749146,
        "tn": 185,
        "tp": 12
      }
    ],
    "native": {
      "accuracy": 0.8722466960352423,
      "f1": 0.43137254901960786,
      "fn": 26,
      "fnr": 0.7027027027027027,
      "fp": 3,
      "fpr": 0.015789473684210527,
      "precision": 0.7857142857142857,
      "recall": 0.2972972972972973,
      "specificity": 0.9842105263157894,
      "tn": 187,
      "tp": 11
    }
  },
  {
    "fold": 4,
    "rows": 227,
    "positive": 37,
    "negative": 190,
    "roc_auc": 0.8236130867709816,
    "pr_auc": 0.5749924705890292,
    "fixed_fpr": [
      {
        "budget": 0.01,
        "fn": 27,
        "fnr": 0.7297297297297297,
        "fp": 1,
        "fpr": 0.005263157894736842,
        "negative_denominator": 190,
        "no_positive_predictions": false,
        "positive_denominator": 37,
        "recall": 0.2702702702702703,
        "role": "DEVELOPMENT_DESCRIPTIVE_OPERATING_CAPACITY",
        "threshold": 0.5600143074989319,
        "tn": 189,
        "tp": 10
      },
      {
        "budget": 0.03,
        "fn": 25,
        "fnr": 0.6756756756756757,
        "fp": 2,
        "fpr": 0.010526315789473684,
        "negative_denominator": 190,
        "no_positive_predictions": false,
        "positive_denominator": 37,
        "recall": 0.32432432432432434,
        "role": "DEVELOPMENT_DESCRIPTIVE_OPERATING_CAPACITY",
        "threshold": 0.23945845663547516,
        "tn": 188,
        "tp": 12
      },
      {
        "budget": 0.05,
        "fn": 23,
        "fnr": 0.6216216216216216,
        "fp": 9,
        "fpr": 0.04736842105263158,
        "negative_denominator": 190,
        "no_positive_predictions": false,
        "positive_denominator": 37,
        "recall": 0.3783783783783784,
        "role": "DEVELOPMENT_DESCRIPTIVE_OPERATING_CAPACITY",
        "threshold": 0.03908035159111023,
        "tn": 181,
        "tp": 14
      }
    ],
    "native": {
      "accuracy": 0.8766519823788547,
      "f1": 0.4166666666666667,
      "fn": 27,
      "fnr": 0.7297297297297297,
      "fp": 1,
      "fpr": 0.005263157894736842,
      "precision": 0.9090909090909091,
      "recall": 0.2702702702702703,
      "specificity": 0.9947368421052631,
      "tn": 189,
      "tp": 10
    }
  }
]
```

## D_G source characterization

```json
[
  {
    "source": "Do-Not-Answer",
    "rows": 659,
    "positive": 0,
    "negative": 659,
    "roc_auc": null,
    "pr_auc": null,
    "fixed_fpr": null,
    "native": {
      "accuracy": 0.9833080424886191,
      "f1": 0.0,
      "fn": 0,
      "fnr": null,
      "fp": 11,
      "fpr": 0.01669195751138088,
      "precision": 0.0,
      "recall": null,
      "specificity": 0.9833080424886191,
      "tn": 648,
      "tp": 0
    }
  },
  {
    "source": "deepset Prompt Injection",
    "rows": 476,
    "positive": 183,
    "negative": 293,
    "roc_auc": 0.8561703873626886,
    "pr_auc": 0.8128362513184785,
    "fixed_fpr": [
      {
        "budget": 0.01,
        "fn": 120,
        "fnr": 0.6557377049180327,
        "fp": 2,
        "fpr": 0.006825938566552901,
        "negative_denominator": 293,
        "no_positive_predictions": false,
        "positive_denominator": 183,
        "recall": 0.3442622950819672,
        "role": "DEVELOPMENT_DESCRIPTIVE_OPERATING_CAPACITY",
        "threshold": 0.014848045073449612,
        "tn": 291,
        "tp": 63
      },
      {
        "budget": 0.03,
        "fn": 105,
        "fnr": 0.5737704918032787,
        "fp": 6,
        "fpr": 0.020477815699658702,
        "negative_denominator": 293,
        "no_positive_predictions": false,
        "positive_denominator": 183,
        "recall": 0.4262295081967213,
        "role": "DEVELOPMENT_DESCRIPTIVE_OPERATING_CAPACITY",
        "threshold": 0.0067184786312282085,
        "tn": 287,
        "tp": 78
      },
      {
        "budget": 0.05,
        "fn": 99,
        "fnr": 0.5409836065573771,
        "fp": 13,
        "fpr": 0.04436860068259386,
        "negative_denominator": 293,
        "no_positive_predictions": false,
        "positive_denominator": 183,
        "recall": 0.45901639344262296,
        "role": "DEVELOPMENT_DESCRIPTIVE_OPERATING_CAPACITY",
        "threshold": 0.0041005657985806465,
        "tn": 280,
        "tp": 84
      }
    ],
    "native": {
      "accuracy": 0.6911764705882353,
      "f1": 0.3287671232876712,
      "fn": 147,
      "fnr": 0.8032786885245902,
      "fp": 0,
      "fpr": 0.0,
      "precision": 1.0,
      "recall": 0.19672131147540983,
      "specificity": 1.0,
      "tn": 293,
      "tp": 36
    }
  }
]
```

## Uncertainty

| budget | metric | event_count | denominator | estimate | lower | upper |
|---|---|---|---|---|---|---|
| 0.010000 | jfn/D_G_v1/D_M-B_v1 | 6 | 183 | 0.032787 | 0.010929 | 0.060109 |
| 0.010000 | jfn/D_G_v1/D_S_B2_LR | 96 | 183 | 0.524590 | 0.453552 | 0.601093 |
| 0.010000 | all_detector_jfn/DEVELOPMENT_STACK_CANDIDATE | 5 | 183 | 0.027322 | 0.005464 | 0.049180 |
| 0.010000 | all_detector_jfn/DEVELOPMENT_STACK_V1 | 6 | 183 | 0.032787 | 0.010929 | 0.060109 |
| 0.010000 | delta/all_detector_jfn/primary_stack | UNMEASURED | UNMEASURED | -0.005464 | -0.016393 | 0.000000 |
| 0.010000 | delta/recovery_given_others_miss/primary_stack | UNMEASURED | UNMEASURED | 0.166667 | 0.000000 | 0.500000 |
| 0.030000 | jfn/D_G_v1/D_M-B_v1 | 4 | 183 | 0.021858 | 0.005464 | 0.043716 |
| 0.030000 | jfn/D_G_v1/D_S_B2_LR | 61 | 183 | 0.333333 | 0.267760 | 0.404372 |
| 0.030000 | all_detector_jfn/DEVELOPMENT_STACK_CANDIDATE | 3 | 183 | 0.016393 | 0.000000 | 0.038251 |
| 0.030000 | all_detector_jfn/DEVELOPMENT_STACK_V1 | 4 | 183 | 0.021858 | 0.005464 | 0.043716 |
| 0.030000 | delta/all_detector_jfn/primary_stack | UNMEASURED | UNMEASURED | -0.005464 | -0.016393 | 0.000000 |
| 0.030000 | delta/recovery_given_others_miss/primary_stack | UNMEASURED | UNMEASURED | 0.250000 | 0.000000 | 0.920833 |
| 0.050000 | jfn/D_G_v1/D_M-B_v1 | 2 | 183 | 0.010929 | 0.000000 | 0.027322 |
| 0.050000 | jfn/D_G_v1/D_S_B2_LR | 47 | 183 | 0.256831 | 0.196585 | 0.322404 |
| 0.050000 | all_detector_jfn/DEVELOPMENT_STACK_CANDIDATE | 2 | 183 | 0.010929 | 0.000000 | 0.027322 |
| 0.050000 | all_detector_jfn/DEVELOPMENT_STACK_V1 | 2 | 183 | 0.010929 | 0.000000 | 0.027322 |
| 0.050000 | delta/all_detector_jfn/primary_stack | UNMEASURED | UNMEASURED | 0.000000 | 0.000000 | 0.000000 |
| 0.050000 | delta/recovery_given_others_miss/primary_stack | UNMEASURED | UNMEASURED | 0.000000 | 0.000000 | 0.000000 |

1,000 paired canonical attack-lineage percentile bootstrap replicates, seed 1701. Fixed scores and pooled thresholds; no threshold reselection, refitting, selection uncertainty or training-fold dependence modeled. Only 183 attack groups. Tiny shared-event and conditional denominators make intervals fragile; a zero-event interval is not proof of zero population risk. The unchanged engine supplies a paired recovery-delta interval, not an absolute conditional-recovery interval. Raw conditional numerators/denominators are in Table 5.

## Research answers

1. Independence is a reference, not established: D_M-B/D_G shared misses=4/183, JFN=0.021858, IND=0.016841, EJF=0.005017 at 3%. Positive EJF is observed excess failure association, not causal dependence.
2. D_S candidate recovers 1/4 attacks missed by both stronger guards.
3. All-three shared misses change 4 -> 3 at 3%; paired uncertainty is reported above.
4. Observed failure-diversity classification at 3%: REDUCED_SHARED_FAILURE, PRESERVED_COMPLEMENTARITY. This describes counts, not proof of distinct causal mechanisms.
5. Development evidence supports carrying the measured heterogeneous candidate into later Commander review; it does not authorize those later experiments or establish production, protected-benchmark or adaptive robustness.

## Tests and preservation

```json
{
  "tests": {
    "postrun_model_free": {
      "status": "PASS",
      "tests": 84,
      "failures": 0,
      "errors": 0,
      "skipped": 0,
      "path": "C:\\Users\\harsh\\Adversarial-Attack-Detection-for-LLMs\\tmp\\track2_postrun_common.xml",
      "sha256": "b0eab9d79faad24dfb3ffd3fb5ce6f3ede78cce27b7a5013663860fd7c5e57f3"
    },
    "postrun_guard_fixture": {
      "status": "PASS",
      "tests": 115,
      "failures": 0,
      "errors": 0,
      "skipped": 0,
      "path": "C:\\Users\\harsh\\Adversarial-Attack-Detection-for-LLMs\\tmp\\track2_postrun_guard.xml",
      "sha256": "f1c89febf61f2a4e539ea3f3890c10159aa06dc3a28c74cced8e6d515de46b52"
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
Initial combined pytest collected guard Torch imports and failed one model-free import-isolation assertion. Suites were rerun in separate processes without altering that assertion; all passed. Authoritative OOF evidence remains byte-identical and independently reconstructed. Prior final ds_v2/STACK-001 files were preserved byte-for-byte locally before the requested divergent branch switch; accepted history was not merged or rewritten.

## Governance

D_S cycle 2 DEFERRED; final thresholds NOT FROZEN; fusion NOT IMPLEMENTED; verifier NOT SELECTED; routing NOT IMPLEMENTED; training/calibration/VALIDATION/protected/E1-E10/R1-R3 NO. Fixed-FPR points are descriptive and detector-specific, not frozen deployment decisions.
## Final verdict

**READY_FOR_REPORT_RESULTS_INTEGRATION**

THE SINGLE MOST IMPORTANT EMPIRICAL FINDING:

At the descriptive 3% FPR budget, D_S B2+LR catches 1/4 attacks missed by both D_M-B and D_G, and all-three shared misses change from 4 to 3 out of 183 attacks.
