# R2-DS-001 FINAL REPORT

STATUS: BLOCKED

## Repository

Start: `99b012e5b72fbae9273fa73ccc8d84d579a69c83`. Branch: `exp/r2-ds-001`.

Predeclaration: `9a1c4371f9c1c9fc2531fc181a2f046e387b98b2`; prospective calibrated-tie clarification: `99a3379`; initial generator: `e9a6598`; zero-query loader repair: `154055902dc7d28c55da3dd0a75a5ac85eaa44a7`. Final blocker evidence commit is reported externally after commit/push. No terminal-freeze, transfer-scoring or analysis-result commit exists.

## Seed Population

Frozen R1 attacks: 800. DS baseline catches and selected seeds: 698. LLMail: 384; InjecAgent: 314; inherited lineages: 94. Selection uses only frozen DS columns, preserves parent order, and is not hard-coded.

## Target Isolation And Query Accounting

Only DS was scored. D_M-B/D_G/ensemble generation queries: 0/0/0. The runtime isolation guard remained active. DS unique count is NOT PERSISTED; between 1 and 61 first-parent evaluations occurred. No accepted terminal was written. An empty terminal journal does NOT mean zero queries.

## Generator And Validity

Frozen calibrated-score objective below 0.5585373573968287; 61-query cap; up to 16 reversible ALT_CASE probes, top eight words, four accepted reversible operators, fixed padding and original-parent global variants. Exact inverse UTF-8 reconstruction is the validity rule, not downstream jailbreak success. Raw inputs remain ignored local-only.

## Execution Blocker

First invocation failed while loading a model-free shared calibration helper, before any query; its receipts and empty journal are preserved separately. A committed narrow loader repair and documented full restart followed. The restart completed first-parent search but failed its baseline comparison to accepted R1 with tolerance 1e-12. Exact live score/delta and candidate query trace were not persisted because the baseline check occurs after search and journal append occurs after that check. This is an auditability gap, not a zero-event result. No further model queries or tolerance changes were made.

## Target Evasion And Transfer

Baseline population: 698. Accepted terminals: 0. Successful evasions, target rate/CI, baseline-terminal medians and median queries: NOT_RUN / NOT_ACCEPTED. Transfer denominator, DS->DMB, DS->DG, and joint transfer counts/rates/CIs: NOT_RUN, not zero and not a zero-denominator ETR estimate.

## Full Population And Paired Analysis

TP/FN/Recall/FNR for all three, pairwise JFN/independence/EJF/Jaccard, all-three JFN, patterns, recovery, paired transitions, source/operator outcomes and coverage/truncation conclusions: NOT_RUN. No frozen terminal population exists to support them. FPR/ROC-AUC/AP remain NOT_APPLICABLE_ATTACK_ONLY_REGIME. The frozen inherited-lineage 1000-replicate seed-1701 95% percentile CI contract remains unchanged and was not run on incomplete data.

## R2-DMB Comparison And Interpretation

Accepted R2-DMB remains 0/800 target evasions. R2-DS has no accepted result, so target difficulty cannot be compared. No DS-specific vulnerability, transfer or all-three failure claim is supported. Even a completed comparison could not isolate detector architecture from objectives, seed sets, probes or analyzed coverage.

## Tests And Preservation

{
  "passed": 156,
  "failed": 0,
  "errors": 0,
  "skipped": 0,
  "receipt_sha256": "62f15d88549a3228985f4e4e0da26103dc26cfb0a2058c49bb453c1f8e808c8c"
}

{
  "source_preservation_checks": 503,
  "baseline_preservation": {
    "status": "PASS",
    "hash_checks": 96,
    "evidence_sha256": "4b42dd44f2604f12e099f1fc60decef866c64d036c9a6554fcd3e049513b8a21",
    "tracked_baseline_diff": "EMPTY"
  },
  "release_preservation": {
    "status": "PASS",
    "hash_checks": 118,
    "R1_started": false
  },
  "patch_hash_checks": 262,
  "models_changed": false,
  "thresholds_changed": false,
  "R0_changed": false,
  "R1_changed": false,
  "R2_DMB_changed": false,
  "R3_started": false,
  "R2_DG_started": false,
  "verifier_started": false,
  "protected_evaluation_started": false
}

Only model-free preflight and prior accepted-output regression ran. DS post-generation/freeze/result tests could not run because those artifacts do not exist. No model, calibration, threshold, R0/R1/R2-DMB/protocol formula or bootstrap change. No protected data, R2-DG, R3 or verifier work.

## FINAL VERDICT

BLOCKED

THE SINGLE MOST IMPORTANT R2-DS FINDING: The frozen R1 baseline replay gate failed before any terminal population was accepted; no evasion or transfer result can be reported.

NEXT DECISION REQUIRED: Review a narrowly scoped baseline-replay/accounting repair before resuming DS; evaluate R2-DG value only after accepted R2-DS evidence and before the prepared R3 design.
