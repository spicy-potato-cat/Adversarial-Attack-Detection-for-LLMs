# TECH-SEM-002 DEVELOPMENT-ONLY VALIDATION

233 rows; final frozen checkpoint; raw-score cutpoint 0.5.

```json
{
  "sample_count": 233,
  "positive_count": 39,
  "negative_count": 194,
  "default_development_cutpoint": 0.5,
  "confusion_matrix": {
    "tn": 191,
    "fp": 3,
    "fn": 4,
    "tp": 35
  },
  "accuracy": 0.9699570815450643,
  "precision": 0.9210526315789473,
  "recall_tpr": 0.8974358974358975,
  "specificity_tnr": 0.9845360824742269,
  "f1": 0.9090909090909091,
  "fnr": 0.10256410256410256,
  "fpr": 0.015463917525773196,
  "roc_auc": 0.9906159132963257,
  "pr_auc": 0.9689594152012977,
  "scope": "DEVELOPMENT-ONLY VALIDATION; NOT E1-E10",
  "source_artifact_sha256": {
    "Dataset/Raw/datasets/GitHub/Do-Not-Answer/datasets/Instruction/do_not_answer_en.csv": "8585dc135d3b8692b2e464151a313f5164e30f06416e03aa5d11e6c3a21d980e",
    "Dataset/Raw/datasets/HuggingFace/deepset-prompt-injections/data/train-00000-of-00001-9564e8b05b4757ab.parquet": "2e10bc7ab30f542c97e4e83e2a5683000b5057d25ec10908784c631d44124c04",
    "Dataset/Raw/datasets/HuggingFace/deepset-prompt-injections/data/test-00000-of-00001-701d16158af87368.parquet": "39ac797cabc157eeed58435a08593b2952bb6cb16fc394a2d383f447cc7b246e"
  }
}
```

These results are not E1-E10 and are not protected evaluation results.
The approved development corpus is narrow; no comprehensive attack-taxonomy claim.
CALIBRATION was not consumed. No retraining or threshold optimization follows.
