# TECH-SEM-003 OOF Baseline v1

Status: **PARTIAL - PIPELINE VERIFIED; COMMANDER EXECUTION PENDING**.
Date: 2026-10-04. Development analysis only. Not final evaluation.

Continuation: the completed pre-run evidence package is documented in
`TECH_SEM_003_OOF_PRERUN_EVIDENCE_v1.md`. The original preparation JSONs below are
retained as historical evidence. Active configuration is now
`artifacts/semantic_v2/oof/preflight/analysis_config_v2.json`; exact code, 94 tests,
renewed short smoke, fold membership and output contracts are bound by the new
`oof_preflight_v1.json`. Actual OOF performance remains pending.

## Startup And Fixture

The clean-tree gate was initially blocked by uncommitted TECH-STAT-003 work.
The Commander explicitly approved committing that work locally and continuing.
Commit `6e88dfe` contains the completed statistical analysis; nothing was pushed.
Branch `tech/sem-003` was created from that clean commit. Expected QUALITY-001
commit `e649f4d` is an ancestor and was inspected. No folds were regenerated.

- Manifest SHA-256: `9cdd5ecdd80f9ac3c8f05db63742721f4537ca2b64a2fe48f6c2b424b57483a6`.
- Fold SHA-256: `19dc0153cc257cc2331782d6dd61b7bb9fb8cb0ed88d3e782b69d5ba05c4bb8d`.
- 1,135 BASE_TRAIN rows, 183 positive, 952 negative, five folds, seed 1701.
- 1,134 canonical-lineage groups; zero cross-fold canonical-group leakage.
- Each fold holds out 227 rows and trains on 908 rows. Positive held-out counts:
  36, 36, 37, 37, 37. Minimum canonical grouping is not proof of complete lineage.

## Frozen Reproduction

Detector: `semantic_finetuned`; version: `dm_b_v1`.
Upstream: `distilbert/distilroberta-base`, model/tokenizer revision
`fb53ab8802853c8e4fbdbcd0529f21fc6f459b2b`; 82,119,938 parameters.
Model context 512; baseline input remains 256 including special tokens.
Recipe SHA-256:
`2b5b41ce90ff931caf6a6fbddcd2beed19ea802cf657125b996dbdf0c96b0484`.

Three epochs, batch eight, float32, AdamW at 2e-5, weight decay .01 (zero for
bias/LayerNorm weights), linear schedule with ceil(10% of fold steps) warmup,
gradient norm clip one. Existing deterministic settings and training function are
reused without modification. All transformer/head layers train. Final epoch only;
no checkpoint selection. Each fold has 342 optimizer steps, 1,710 total.
Class weights are recalculated from that fold's training labels as N/(2*N_class).

Every fold resets seed 1701 BEFORE loading the local frozen upstream backbone
and initializing its binary head. Full initial parameter hashes must agree across
folds. Training and held-out IDs and canonical groups are explicitly disjoint.
Only held-out texts are scored after the final epoch. Each selected ID is predicted
once and outputs follow the frozen sample-ID order. Fold models are in-memory
temporary analysis models, not dm_b_v2, and no model checkpoints are promoted.
The existing final dm_b_v1 and its calibrator are never loaded for scoring.

Binary rule: raw class-one softmax probability >= .5. This is a fixed,
data-independent existing development cutpoint, not a held-out-selected threshold
or calibrated operating point. No threshold fitting consumes any partition.
ROC-AUC, average precision (PR-AUC), empirical Recall@FPR<=1/3/5%, per-fold metrics,
stability and full ROC/PR curves are implemented. Fixed-FPR thresholds are
descriptive attainable ROC points, explicitly not deployed policies.

## Compute And Long-Run Gate

CPU: Intel i7-12650H, 16 logical CPUs; recipe uses eight Torch threads.
RAM: 16,869,548,032 bytes total; approximately 3.7 GB available at initial probe.
Physical GPU: RTX 3070 Ti Laptop GPU, 8,192 MiB. Installed Torch 2.6.0+cpu reports
CUDA unavailable. Existing packages match the frozen preparation. No installation
or CUDA substitution was performed; execution device remains CPU.

Prior authoritative run: 1,088.367622 seconds for 426 steps. Linear scaling to
1,710 steps estimates **4,368.799609 seconds / 72.81 minutes of training**.
Allow roughly 75-100 minutes including loading, inference and variable CPU/RAM
pressure; this is an estimate, not a measured OOF duration or deadline.
Per-fold actual runtimes are pending. Full training was deliberately NOT launched,
as required by the long-run rule. No process is currently running for this phase.

## Verified Infrastructure

47 focused tests passed, zero failures/errors/skips. Real upstream synthetic smoke:
eight synthetic texts, three epochs, three optimizer steps; parameters updated and
repeat held-out inference deterministic. Measured training/prediction smoke elapsed
5.892882 seconds, excluding setup. No project dataset was opened by the smoke.
Coverage examples measured 6->6 tokens and 1,504->256 (1,248 excluded).
The initialized classification-head warning is expected for fresh upstream refits.

Analysis-config SHA-256:
`6cef1e880469155d0a99c976358c51d35d434eaafb1d7b055e61ba0494f07208`.
Preflight binds exact pipeline/test/helper bytes, original recipe/preparation,
upstream hashes, fixture hashes, packages, and original D_M-B/statistical artifacts.
Baseline preservation passes all 96 QUALITY-001 metadata/code checks; original
D_M-B weight files additionally pass their opaque SHA-256 integrity checks.
Original freeze/training/calibration reports remain unchanged.

## Commander Command

Run from PowerShell, keeping this workspace and frozen environment unchanged:

```powershell
Set-Location C:\Users\harsh\Adversarial-Attack-Detection-for-LLMs
.\.local-python\python.exe -m detection_service.scripts.semantic_oof_baseline --mode run
if ($LASTEXITCODE -ne 0) { throw 'TECH-SEM-003 failed; stop for review. Do not rerun.' }
.\.local-python\python.exe -m detection_service.scripts.semantic_oof_baseline --mode check
```

The command runs all five real folds and writes metrics/diagnostics, then the
check independently verifies output hashes, membership, schema, metrics, fixed-FPR
points, analysis products and preservation. Failed or started runs refuse automatic
restart/resume. Do not delete a run marker or edit configuration to bypass this gate.
Return the completed output for acceptance review and final reporting. Do not
train B1/B2/B3 or begin TECH-SEM-004 based on preparation alone.

## Artifacts And Acceptance

Already present under `artifacts/semantic_v2/oof/`: analysis_config_v1.json,
preflight_v1.json, synthetic_smoke_v1.json, test_results_v1.xml, test_evidence_v1.json.

Only after successful execution: dm_b_v1_recipe_oof_predictions.csv,
dm_b_v1_recipe_oof_metrics.json, dm_b_v1_recipe_fold_metrics.json,
dm_b_v1_recipe_oof_curves.json, dm_b_v1_truncation_analysis.json,
dm_b_v1_error_characterization.json, dm_b_v1_hard_examples.csv,
dm_b_v1_v2_recommendation.json and completion_v1.json. No raw text in these outputs.

Actual OOF confusion, FPR/FNR, ROC/PR, fixed-FPR recall, truncation rates, confidence
counts, source/fold stability, hard IDs and B1 justification are **NOT YET MEASURED**.
No placeholders are presented as results. PASS and READY FOR TECH-SEM-004 are
withheld until full execution and verification.

## Isolation

CALIBRATION rows used: NO. VALIDATION rows used: NO. Protected payloads: NO.
E1-E10: NO. dm_b_v2: NO. Additional packages/downloads: NONE.
Full execution selects only frozen BASE_TRAIN locators from three approved
Do-Not-Answer/deepset original source containers and verifies exact text/source
hashes. Those CSV/Parquet containers physically include reserved partition rows;
this is scalar-selection isolation, NOT physical byte isolation. Metadata eligibility
is checked, but unselected texts/labels are not supplied to training or diagnostics.
Python-level audit checks reject other Dataset/PHASE-3 paths and raw/model writes;
they are defense-in-depth, not an OS security boundary for native libraries.

Git: TECH-STAT-003 locally committed. The pre-run freeze commit is the commit
containing `preflight/oof_preflight_v1.json`; `--mode check-prerun` resolves and
verifies that exact HEAD and a clean working tree before any long run. Its SHA is
recorded in the final handoff and captured in future `dm_b_v1_oof_run_metadata.json`.
