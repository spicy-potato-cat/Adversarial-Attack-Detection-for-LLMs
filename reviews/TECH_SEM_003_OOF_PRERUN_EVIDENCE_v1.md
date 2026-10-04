# TECH-SEM-003 OOF Pre-Run Evidence v1

Date: 2026-10-04. **PRE-RUN PROOFS PASS; AUTHORITATIVE OOF EXECUTION PENDING**.
The post-commit `check-prerun` gate must report READY_FOR_LONG_RUN before execution.
No full five-fold transformer run was started. No actual OOF results yet exist.

## Repository And Commit Provenance

Path: `C:\Users\harsh\Adversarial-Attack-Detection-for-LLMs`.
Branch: `tech/sem-003`.
Start commit: `6e88dfe7e283434b9313e1078423ae74a21ffffd`.
Expected QUALITY-001 commit `e649f4d` is an ancestor.

This report, exact pipeline/test bytes and pre-run evidence are committed together.
The freeze commit is resolved with:

```powershell
git log -1 --format=%H -- artifacts/semantic_v2/oof/preflight/oof_preflight_v1.json
```

The run requires HEAD to equal that commit, a clean tracked/untracked working tree,
matching runtime code SHA-256 hashes, and committed Git objects for code/preflight
evidence. Git's tracked line-ending attributes are applied for object comparison;
independent byte hashes still bind the actual runtime files. The actual resulting
commit SHA and post-commit cleanliness are recorded in the Commander handoff.
An artifact cannot contain the literal hash of the commit that contains it without
self-reference; execution therefore captures the verified commit, not a guessed SHA.
No code will be changed after the freeze before execution. No results are auto-committed.

## Authoritative Fixture

Manifest: `data_governance/manifests/development_partition_manifest_v1.csv`.
SHA-256: `9cdd5ecdd80f9ac3c8f05db63742721f4537ca2b64a2fe48f6c2b424b57483a6`.
Folds: `artifacts/quality/quality_001/development_folds_v1.csv`.
SHA-256: `19dc0153cc257cc2331782d6dd61b7bb9fb8cb0ed88d3e782b69d5ba05c4bb8d`.
Verified again: 1,135 BASE_TRAIN rows, 183 positive, 952 negative, five folds,
seed 1701, 1,134 canonical-lineage groups, zero canonical-group leakage. Frozen
QUALITY integrity verification passes all 11 hash checks. Folds are never rewritten.
Minimum canonical grouping is not a claim of complete semantic/upstream independence.

## Exact Fold Execution Plan

| Fold | Train Rows | Held Rows | Train + | Train - | Held + | Held - | Train Groups | Held Groups | ID Overlap | Group Overlap |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 908 | 227 | 147 | 761 | 36 | 191 | 907 | 227 | 0 | 0 |
| 1 | 908 | 227 | 147 | 761 | 36 | 191 | 908 | 226 | 0 | 0 |
| 2 | 908 | 227 | 146 | 762 | 37 | 190 | 907 | 227 | 0 | 0 |
| 3 | 908 | 227 | 146 | 762 | 37 | 190 | 907 | 227 | 0 | 0 |
| 4 | 908 | 227 | 146 | 762 | 37 | 190 | 907 | 227 | 0 | 0 |

`preflight/fold_execution_plan.json` materializes ALL exact train/held-out sample IDs,
membership SHA-256 hashes, class counts/weights and group counts for each fold.
Union and multiplicity checks prove every fixture ID is planned held out once.
Output order is frozen ascending sample-ID order, not fold completion order.
These are verified planned memberships, not evidence of completed training.

## Frozen Recipe And Upstream

Detector `semantic_finetuned`; reproduction of `dm_b_v1`, not dm_b_v2.
Model/tokenizer: `distilbert/distilroberta-base`.
Revision: `fb53ab8802853c8e4fbdbcd0529f21fc6f459b2b`.
82,119,938 parameters; model capacity 512; baseline project input **256**.
Seed 1701; three epochs; batch eight; AdamW LR 2e-5; all layers train; float32 CPU,
eight Torch threads; gradient accumulation one; gradient clip one.
Weight decay .01 except bias/LayerNorm weights; original linear schedule, ceil(10%)
warmup; 342 steps per fold and 1,710 total. Final epoch only, no selection.
Each fold resets seeds before loading the same local immutable upstream snapshot
and binary head. Complete initial parameter hashes must match across folds.
Class weights use ONLY that fold's training labels, N/(2*N_class).
Right truncation/padding, longest-in-batch padding and original preprocessing remain.
No recipe change reduces runtime. No downloaded checkpoint or final model reuse.
Local upstream/tokenizer hashes and original frozen recipe SHA-256 are verified.

Binary cutpoint is fixed raw probability .5, data-independent, not selected from
held-out or reserved data. Final `dm_b_v1_cal_v1` is NOT loaded or used. Fixed-FPR
points are descriptive attainable ROC points, not deployment policies.

## Metric Implementation Evidence

PASS: TN/FP/FN/TP, accuracy, FPR/FNR, precision, recall, specificity, F1, ROC-AUC,
average precision (PR-AUC) and Recall@FPR<=1/3/5%.
`metric_validation_v1.json` contains explicitly synthetic labels/scores, expected
and measured answers plus independent rank/count reasoning. Four binary examples
give one case of each confusion category. A separate 100-negative/four-positive
ranking fixture gives distinct fixed-FPR answers and conservative tie selection.
Numeric comparisons allow 1e-12 floating-point roundoff; no performance estimate
is derived for project data. Score ties/no-positive ROC point are also tested.
These synthetic numbers are NOT the forthcoming authoritative OOF metrics.

## Truncation And Confidence Pipeline

PASS: output records ID/fold/label/source/revision/lineage, `input_tokens` (the
original_input_tokens equivalent), max_input_tokens 256, attention-mask analyzed
count, excluded count, truncated flag, raw probability, signed class-one-minus-
class-zero logit margin, prediction/error, absolute probability distance to .5,
confidence category and latency. Counts include special tokens, exclude padding.
<=256 tokens are not truncated; >256 are truncated and analyzed count is bounded.
Synthetic tokenizer/model checks cover 20/256/257/600 token inputs; renewed real
upstream smoke independently verifies 6->6 and 1,504->256, with 1,248 excluded.
No real full dataset passed through a model. Payload locations are NOT inferred.

Boundaries already defined by implementation, unchanged here:
borderline FN/FP = abs(raw_positive_probability-.5) <= .1;
high-confidence FN = p<=.1; high-confidence FP = p>=.9.
Tests cover all four categories and inclusive boundary rounding. Distance is in
probability space; logit margin is separately signed and recorded. Nothing depends
on a later threshold fit. Uncalibrated confidence is not epistemic certainty.

Future class-conditional truncation rates, score summaries, source/fold/length
groups and descriptive Wilson intervals are implemented. Null denominators remain
unknown. Patterns overlap, semantic causes remain hypotheses, source/label mixtures
are confounded, and no R1/generalization or truncation-causality claim is made.

## Output Contract

All successful outputs are under `artifacts/semantic_v2/oof/`:

- `dm_b_v1_recipe_oof_predictions.csv`
- `dm_b_v1_recipe_oof_metrics.json`
- `dm_b_v1_recipe_fold_metrics.json`
- `dm_b_v1_recipe_oof_curves.json`
- `dm_b_v1_truncation_analysis.json`
- `dm_b_v1_error_characterization.json`
- `dm_b_v1_hard_examples.csv`
- `dm_b_v1_v2_recommendation.json`
- `dm_b_v1_oof_run_metadata.json`
- `completion_v1.json`

`run_started_v1.json` is the once-only run marker. `failure_v1.json` is created on
an exception after execution starts. Failed/started runs refuse automatic rerun.
`preflight/output_contract_v1.json` freezes ordered CSV fields, JSON Schema and
paths. Hard examples share the prediction schema and retain only FN/FP IDs and
metadata; prompt fields/additional properties or changed max length are rejected.
Exactly one OOF score per ID means repeated misses are not claimed. Hard IDs are
diagnostic references, not new training data. No raw text is exported.

Run metadata will contain verified code commit, manifest/fold hashes, upstream and
tokenizer revisions, seed/device, Python executable, package versions, actual total
runtime, start/end UTC timestamps, each fold's total/fit/prediction runtime and
timestamps, configuration/preflight hashes, and hashes of eight data products.
Completion hashes products plus run metadata, avoiding circular self-hashing.
The post-run check verifies provenance, output hashes, schema, membership and
recomputed metrics/diagnostics. Results must be reviewed before any future commit.

## Environment And Runtime

Python executable:
`C:\Users\harsh\Adversarial-Attack-Detection-for-LLMs\.local-python\python.exe`.
Python 3.11.9; Torch 2.6.0+cpu; Transformers 4.49.0; scikit-learn 1.6.1;
tokenizers 0.21.4; NumPy 2.1.3; SciPy 1.17.1; PyArrow 19.0.1;
Hugging Face Hub 0.36.2; safetensors 0.8.0; jsonschema 4.23.0.
Frozen original preparation package dictionary matches. No packages/builds changed.
CPU i7-12650H, 16 logical CPUs, recipe eight Torch threads, approximately 16.9 GB
total RAM. RTX 3070 Ti Laptop GPU (8,192 MiB) visible physically; CUDA unavailable
in this Torch build. Authoritative run is planned on CPU, without fallback changes.

Runtime retained: **75-100 minutes**, not measured full-job runtime.
Prior run 1,088.367622 seconds/426 steps scales to ~72.81 training minutes/1,710
steps plus loading/inference and CPU/RAM variation. No substantial benchmark was
run to refine this. Renewed smoke training/prediction elapsed 5.544696 seconds,
excluding setup/checks; this short-text smoke is not a full-job performance estimate.

## Preservation, Tests And Isolation

Established preservation: **96 checked; zero mismatches; tracked baseline diff empty**.
Original D_M-B integrity including weights also matches opaque SHA-256 hashes;
original SEM-002 freeze/training/calibration reports and STAT-003 artifacts remain
unchanged. No authoritative classifier/calibrator was deserialized for scoring.
Quality fixture checked again. Current phase is confined to new analysis/scripts,
tests, phase-specific artifacts/reports and narrow line-ending attributes.

Tests: **94 passed; zero failed/errors/skips**: original 47 semantic, 10 added
preflight, 37 statistical regression. Combined JUnit and evidence are retained.
New tests exercise exact fold plan, independent metric answers, hard-row schema,
output/provenance contract, environment, wrong-HEAD/dirty-tree rejection and stopping
before data/training when preflight fails. A transient strict equality on AP roundoff
was corrected to the documented numeric tolerance before the passing freeze.
Existing SciPy solver-option deprecation warnings are non-blocking; no installation
is required. Real upstream synthetic smoke: three epochs/three steps, parameters
updated, finite training loss, deterministic inference, no dataset payload opened.

CALIBRATION rows: NO. VALIDATION rows: NO. Protected payloads: NO.
E1-E10: NO. dm_b_v2: NO. Full OOF training: NO. No new payload/model download.
Fixture metadata may mention reserved partition counts, not their semantic content.
Future text loading selects only frozen BASE_TRAIN locators from the three approved
source containers; mixed CSV/Parquet containers physically include reserved rows,
so this is scalar-selection isolation, not physical byte isolation. Python audit
gates are defense-in-depth, not an OS boundary for native libraries. No raw edits.

## Pre-Run Package Hashes

Authoritative package: `artifacts/semantic_v2/oof/preflight/oof_preflight_v1.json`.
SHA-256: `9f0465747c214f01cce3c5927b7ea2f8058d5d97c310ce6b3e2b6f8af9fb6dc7`.
Checksum file: `oof_preflight_v1.sha256`.
Active `analysis_config_v2.json` SHA-256:
`5b50e3eccd2afeca32875905e414313b337785969abd59d9755daae94bf4e6e2`.
`fold_execution_plan.json` SHA-256:
`d0beaa0185e6bebea9d2382cc249044edb8ed10a113059a91eec9c64e66c5c5a`.
The manifest hashes configuration, anchors, fold plan, output contract, synthetic
metric proof, fixture/preservation evidence, renewed smoke, test evidence and XML.
Earlier preparation artifacts remain immutable historical evidence, explicitly
superseded by version two and independently hash-bound rather than overwritten.

The manifest's PRE_RUN_VERIFIED_COMMIT_REQUIRED state records its generation
before commit. `check-prerun` supplies the final commit-aware READY_FOR_LONG_RUN
attestation. No post-commit file rewrite is needed to claim a commit hash or readiness.

## Results Not Yet Available

Confusion, FPR/FNR, ROC/PR, Recall@1/3/5%, truncation-associated FN counts,
confidence-error counts, hard IDs, source/fold stability and B1/B2/B3 recommendation:
**PENDING AUTHORITATIVE OOF EXECUTION**. No synthetic/estimated substitutes.
Overall TECH-SEM-003 is still PARTIAL; NOT READY FOR TECH-SEM-004.

## Authoritative Commander Commands

CLI was inspected and its non-long preflight/check modes exercised. After this
package is committed and final clean-tree verification passes, run manually:

```powershell
Set-Location C:\Users\harsh\Adversarial-Attack-Detection-for-LLMs
git status
git rev-parse HEAD
.\.local-python\python.exe -m detection_service.scripts.semantic_oof_baseline --mode check-prerun
if ($LASTEXITCODE -ne 0) { throw 'Pre-run evidence failed. Stop for review.' }
.\.local-python\python.exe -m detection_service.scripts.semantic_oof_baseline --mode run
if ($LASTEXITCODE -ne 0) { throw 'OOF run failed. Stop for review. Do not rerun.' }
.\.local-python\python.exe -m detection_service.scripts.semantic_oof_baseline --mode check
if ($LASTEXITCODE -ne 0) { throw 'Post-run verification failed. Stop for review.' }
```

Do not change code, environment, fixture, model revision or configuration before
the run. Do not delete markers to force a restart or commit generated results
automatically. Return completed output for post-run acceptance review.
**STOP: the implementation agent does not execute the long run.**
