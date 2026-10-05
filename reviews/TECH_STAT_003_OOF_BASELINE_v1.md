# TECH-STAT-003 D_S v1 Recipe OOF Baseline v1

Status: **PASS**

Client date: 2026-10-04 (Asia/Calcutta)

Repository: `C:\Users\harsh\Adversarial-Attack-Detection-for-LLMs`

Branch: `tech/stat-003`; repository base: `e649f4d`.
New pipeline code is local and separately SHA-256 bound in the frozen analysis
config; repository HEAD is not misrepresented as containing uncommitted code.
No push was performed.

## Fixture And Recipe Freeze

QUALITY-001 completion `e649f4d` is present; startup working tree was clean.

- Manifest SHA: `9cdd5ecdd80f9ac3c8f05db63742721f4537ca2b64a2fe48f6c2b424b57483a6`.
- Fold SHA: `19dc0153cc257cc2331782d6dd61b7bb9fb8cb0ed88d3e782b69d5ba05c4bb8d`.
- Feature schema SHA: `2b042f88e7403985e5f94e34bb1107b377069e591322767a482a33b5e2cbf8b7`.
- Config SHA: `e96355e54f9c6a78a395907c0a19ac21ffa8cc31d486b25bb1ca7f2d30bfece0`.

The existing fixture was verified, not replaced or reassigned. BASE_TRAIN has
1,135 rows: 183 positives, 952 negatives, 1,134 approved canonical lineage groups.
Five held-out folds each contain 227 rows; each training set contains 908 rows.
Every row receives one OOF prediction; training/held-out identity leakage: 0;
canonical-lineage leakage: 0. This does not establish complete semantic or
documentary lineage independence.

The 10-feature extractor, ordering, identity normalization, reference model and
tokenizer are unchanged. Reference: `distilbert/distilgpt2`, revision
`2290a62682d06624634c1f46a6ad5be0f47f38aa`. Exact local snapshot files were verified
before offline loading, including weight SHA
`e1ff18884359fe8beb795a5f414feb85a6ce3d929ad019c0d958c039d2b94a1b`.
Context 1,024; input cap 4,096; window 128; stride 64; existing exceedance threshold
8.0. No diagnostic token strings/positions were retained.

Each fold independently fits the existing LR recipe: `lbfgs`, L2, `C=1.0`,
`class_weight=balanced`, `max_iter=1000`, `random_state=1701`, intercept enabled.
No scaler, imputer, feature selection, calibration, or scorer comparison.
Convergence iterations by fold: **334, 330, 279, 485, 213**; all converged.
Original final scorer/calibrator were never deserialized or used for prediction.
Fold coefficients/intercepts and membership hashes are reproducibility metadata,
not a new deployed detector version or saved replacement model.

Fresh feature extraction ran once for all selected BASE_TRAIN records. Sharing
these deterministic features across folds is safe because the externally pinned
reference LM and extractor have no project-data fit, learned normalization, or
label-dependent adaptation. Only the LR is fitted, separately per outer fold.
The unchanged extractor took **54.74 seconds**; full run **58.61 seconds** on CPU
with eight threads. No GPU or cross-detector latency advantage is claimed.

## Binary Comparison Rule

**Raw fold-local LR class-1 probability >= 0.5.** This cutpoint was fixed in the
analysis config before prediction. It consumes no threshold-fitting data, so no
held-out labels or reserved partitions influence it; training-fold data alone
fits the LR mapping that produces its input probability.

This is an uncalibrated DEVELOPMENT comparison rule, not the deployed calibrated
`ds_v1_cal_v1` vote and not a new final threshold. All calibrated-probability cells
are null. No calibrator is fitted or loaded. Prior calibrated validation rates are
not directly comparable to these raw-cutpoint OOF rates.

## Aggregate Development OOF Metrics

| Measure | Value |
|---|---:|
| TN / FP / FN / TP | 749 / 203 / 60 / 123 |
| Accuracy | 0.768282 |
| Precision | 0.377301 |
| Recall | 0.672131 |
| Specificity | 0.786765 |
| F1 | 0.483301 |
| FNR | 0.327869 |
| FPR | 0.213235 |
| ROC-AUC | 0.810086 |
| PR-AUC (average precision) | 0.576684 |

The **21.32% FPR and 32.79% FNR** at this raw comparison cutpoint are development
limitations, not a final calibrated system claim.

## Fixed-FPR Discrimination

| Budget | Recall | Attained FPR | TP / 183 | FP / 952 |
|---|---:|---:|---:|---:|
| <=1% | 24.5902% | 0.7353% | 45 | 7 |
| <=3% | 32.2404% | 2.9412% | 59 | 28 |
| <=5% | 45.3552% | 4.9370% | 83 | 47 |

These are attainable empirical ROC points: full tied-score blocks only, no
interpolation or randomized splitting. Maximize descriptive recall under each
budget; ties prefer lower FPR and then the most conservative threshold. The
no-positive-prediction point is included explicitly. ROC/PR curves are saved.

**The descriptive thresholds are not selected/deployed thresholds and never
change binary predictions or error membership.** Using held-out labels to
describe the empirical ROC is not a training-only policy estimate; it must not be
misrepresented as such. Pooled OOF curves mix five fold-model probability scales;
fold-wise results expose that limitation.

## Fold Stability

| Fold | FPR % | FNR % | ROC-AUC | PR-AUC | Recall@1% | Recall@3% | Recall@5% |
|---|---:|---:|---:|---:|---:|---:|---:|
| 0 | 25.6545 | 30.5556 | 0.827807 | 0.521767 | 13.8889% | 25.0000% | 36.1111% |
| 1 | 19.3717 | 30.5556 | 0.822717 | 0.657464 | 30.5556% | 44.4444% | 50.0000% |
| 2 | 22.1053 | 27.0270 | 0.844523 | 0.702305 | 40.5405% | 43.2432% | 62.1622% |
| 3 | 18.9474 | 37.8378 | 0.792319 | 0.590190 | 27.0270% | 35.1351% | 48.6486% |
| 4 | 20.5263 | 37.8378 | 0.764865 | 0.437596 | 10.8108% | 10.8108% | 16.2162% |

| Measure | Fold Mean | Population SD | Minimum | Maximum |
|---|---:|---:|---:|---:|
| FPR | 0.213210 | 0.024273 | 0.189474 | 0.256545 |
| FNR | 0.327628 | 0.043395 | 0.270270 | 0.378378 |
| ROC-AUC | 0.810446 | 0.028353 | 0.764865 | 0.844523 |
| PR-AUC | 0.581865 | 0.094568 | 0.437596 | 0.702305 |
| Recall@1% | 0.245646 | 0.109574 | 0.108108 | 0.405405 |
| Recall@3% | 0.317267 | 0.125596 | 0.108108 | 0.444444 |
| Recall@5% | 0.426276 | 0.155707 | 0.162162 | 0.621622 |

All requested metric summaries, including accuracy/precision/recall/specificity/F1,
are in the machine-readable fold metrics. Fold 4 is notably weak at tight budgets.
Small held-out denominators (190/191 negatives, 36/37 positives) make those
budgets coarse. No significance test or tuning response was performed.

## Conditional Confidence Intervals

Preregistered 2,000-resample lineage-group percentile bootstrap, seed 1701,
95% confidence level, on fixed OOF predictions:

- FPR: **18.84% to 23.96%**.
- FNR: **25.89% to 39.78%**.
- Recall: **60.22% to 74.11%**.

These conditional development intervals do not refit models and do not capture
all uncertainty/dependence induced by overlapping training folds. They do not
provide a final population guarantee. Lineage grouping remains the approved
canonical minimum. No calibration or final-system operating point is evaluated.

## Data Isolation And Preservation

Only manifest-selected BASE_TRAIN texts/labels were supplied to the extractor,
fold fits, OOF metrics, and error analysis. CALIBRATION/VALIDATION membership
metadata was read only by fixture verification. Original CSV/Parquet source
containers are shared across partitions and were hashed/parsed/decoded to locate
selected records through the existing approved loader. This is record-selection
isolation, not a claim that shared-container bytes were physically isolated.
No reserved row was supplied to the models or diagnostics.

No protected source, mixed normalized forensic archive, colleague checkpoint,
semantic/guard predictions, adaptive attacks, or E1-E10 experiment was used.
No data was downloaded or changed. A path allowlist guards Python dataset opens;
native Parquet I/O is additionally bounded by the existing approved source map.

Final preservation check: **96 baseline files unchanged**, no tracked baseline
diff from `43f1405`. QUALITY-001 files and prior D_S reports are unchanged.
No ds_v2, new model features, threshold optimization, or final artifact replacement.

## Artifacts And Reproduction

Directory: `artifacts/statistical_v2/oof/`. Its name reserves future work; this
phase contains only v1-recipe development baseline/diagnostics, not ds_v2.

| File | SHA-256 |
|---|---|
| ds_v1_recipe_oof_predictions.csv | `9b90f505e5c0f21b26ad0b507db1df3291f0fbea83ce52ff53aabf2ef5856215` |
| ds_v1_recipe_oof_metrics.json | `4cdb8a379b08c9f37062be1ec42439cdd467e8580f076873f71d6f9b34da17ec` |
| ds_v1_recipe_fold_metrics.json | `2d65f3132e2a900a0e7b430a17854ff8091e6c140e5f71a17b4b99b8ec65f672` |
| ds_v1_error_characterization.json | `3e93a10b7ed4ef999c06e9cbfd1da816ee416c63a9e520f22e6a83819b18acf5` |
| ds_v1_feature_gap_hypotheses.json | `c525d63ce4149206523d79ffc3a3f7c30af2e680e8e656ee5c001ea2c3af01cb` |
| ds_v1_recipe_oof_curves.json | `042d2a70d646f8871eaac27f3c18e16be847719cda7216491a756ac13561f66c` |
| ds_v1_diagnostic_caveats_v1.json | `cba3b93638051bff16142cf34b821d8924adac79b9abfed5e23e3d7741258436` |
| analysis_config_v1.json | `e96355e54f9c6a78a395907c0a19ac21ffa8cc31d486b25bb1ca7f2d30bfece0` |
| completion_v1.json | `a1598906792b5ae4db3321d703fb9724729e678477384924814143be37acd015` |

Flat predictions contain IDs, labels, fold, lineage, source, version/recipe ID,
raw score, null calibrated probability, binary/error labels, the unchanged 10
features, and existing coverage/window/length metadata. No raw prompt, response,
token strings, or token IDs. Each row's standard OOF projection validates against
QUALITY-001's frozen schema; statistical columns are an explicit CSV extension.
Latency combines extraction time with amortized batch LR inference, not measured
single-request full-service latency. The feature matrix cache is local/ignored.

Read-only verification (does not refit or score texts):

```powershell
.\.local-python\python.exe -m detection_service.scripts.statistical_oof_baseline --mode check
.\.local-python\python.exe -m detection_service.scripts.verify_quality_preservation --mode check
```

The run marker prevents automatic reruns/refits. Python 3.11.9, scikit-learn
1.6.1, NumPy 2.1.3, SciPy 1.17.1, torch 2.6.0, transformers 4.49.0; complete
environment/reference/code hashes are in the config/completion evidence.
Wall-clock fields are not deterministic; synthetic repeated predictions,
coefficients and scientific metrics are. Real predictions were repeated per
fold without refitting and matched exactly. No real fold retraining was performed
to claim cross-run numerical reproducibility.

## Acceptance

Fixture/hash/preservation: PASS. Five-fold OOF coverage and zero leakage: PASS.
Fixed-FPR metrics, FN/FP characterization and qualified hypotheses: PASS.
CALIBRATION/VALIDATION use: NO. Protected data/E1-E10/ds_v2: NO.

**READY FOR TECH-STAT-004 FEATURE ENGINEERING. Do not create D_S v2 yet.**
