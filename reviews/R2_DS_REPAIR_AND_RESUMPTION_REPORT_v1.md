# R2-DS-001 REPAIR AND RESUMPTION REPORT

STATUS: BLOCKED

## Root Cause

Primary category: **UNKNOWN**. No input-identity or accepted-runtime-binding mismatch was found. The first observed difference is raw class-1 probability (stage P), but the first causal divergence cannot be localized: R1 did not retain this seed's token IDs, surprisals or 26-feature vector. Live LR reconstruction and both stored/live Platt reconstructions match exactly. Numerical-environment variation is not proven; no package or runtime changes were made to chase a matching score.

Secondary contributor: incomplete historical intermediate/environment telemetry limits diagnosis. This is not evidence that frozen R1 is defective. The historical first-parent search ran before its baseline gate; none of its unpersisted candidate outcomes were inspected or used to modify the algorithm.

## First-Seed Replay

Sample ID: `R1-DS-TXT-005-0010925a66bfbcf27df3b1a726edbea30b29fe5eeddbccce5c62c10525777785`.

Parent UTF-8 SHA-256: `5f3543782e03ad2479e9c0d07feb867e4a6edb5a84ba0115a72e353633f235e0`.

Input bytes: `279`.

Frozen R1 raw score: `0.9254972378912807`.

Live raw score: `0.9254974294828613`.

Raw delta: `1.9159158060055859e-07`.

Frozen R1 calibrated score: `0.844565288092724`.

Live calibrated score: `0.8445657399577122`.

Calibrated delta: `4.5186498820459775e-07`.

Native and operational decisions match (1/1). Token counts match: 101 input, 100 analyzed; no truncation. Raw/calibrated tolerance remains **1e-12**; this replay FAILS both score checks. Unchanged decisions do not waive the gate. Input, request and engine text hashes are identical. Frozen model/reference/tokenizer/schema/calibrator identities and numerical environment are recorded in the first-seed diagnostic.

## Pipeline Evidence

```json
{
  "additional_lm_queries": 0,
  "environmental_variation_proven": false,
  "final_verdict": "R2_DS_BASELINE_REPLAY_STILL_UNRESOLVED",
  "first_causal_divergence": "UNKNOWN_WITHIN_REFERENCE_INFERENCE_OR_FEATURE_PATH",
  "first_observed_divergence": "P_RAW_CLASS1_PROBABILITY",
  "generation_allowed": false,
  "historical_numerical_environment": "NOT_RECORDED_IN_R1_SCORING_MANIFEST; training-package versions match replay, but do not establish R1 process configuration",
  "live_calibration_reconstruction_delta": 0.0,
  "primary_root_cause": "UNKNOWN",
  "r1_calibration_reconstruction_delta": 0.0,
  "r1_native_journal_sha256": "21f51edf46c4b9b759af160981c9b6faae211d92efc9a210ca10bd53b63ba787",
  "raw_reconstruction_delta": 0.0,
  "secondary_contributors": [
    "Historical R1 intermediate telemetry and exact numerical environment are not retained; this is a diagnostic evidence limitation, not a proven numerical cause."
  ],
  "stages": {
    "A_exact_input_bytes": "MATCH: frozen input file hash, seed text hash, request hash and engine-input hash identical",
    "B_raw_text_selection": "MATCH: unchanged R1 JSONL text field; validator rejects blank text without changing text",
    "C_tokenizer_identity": "MATCH_FROZEN_CONFIGURATION",
    "D_tokenizer_revision": "MATCH_FROZEN_SNAPSHOT_HASHES",
    "E_token_ids": "LIVE_HASH_RECORDED; R1 IDs not retained, historical IDs only reconstructable from frozen text/tokenizer, not observed",
    "F_token_count": "MATCH: 101 input tokens and 100 next-token targets",
    "G_prompt_truncation_and_windows": "MATCH_COUNTS: no truncation; frozen recipe implies one reference chunk [0,101)",
    "H_reference_revision": "MATCH_FROZEN_REVISION_AND_WEIGHTS",
    "I_perplexity_inputs": "LIVE_CAPTURED; R1 token-level evidence not retained",
    "J_sliding_windows": "FROZEN_RECIPE_RECONSTRUCTION: single 100-target window, width128/stride64; R1 window telemetry absent",
    "K_token_surprisals": "LIVE_CAPTURED; HISTORICAL_NOT_STORED",
    "L_26_feature_vector": "LIVE_CAPTURED; HISTORICAL_NOT_STORED",
    "M_feature_order_schema": "MATCH_FROZEN_SCHEMA_AND_CODE",
    "N_feature_dtype": "LIVE_FLOAT64; frozen implementation specifies float64; historical runtime dtype telemetry absent",
    "O_lr_coefficients_intercept": "MATCH_FROZEN_MODEL_HASH; float64 byte hashes recorded",
    "P_raw_probability": "FIRST_OBSERVED_SCORE_DIVERGENCE: causal earlier divergence cannot be localized without R1 intermediates",
    "Q_raw_log_odds": "RECONSTRUCTED_FROM_EACH_RAW_PROBABILITY: input differs; no different transform observed",
    "R_clipping": "MATCH_FROZEN_EPSILON_1e-12; neither first-seed raw probability is at clipping boundary",
    "S_platt_parameters": "MATCH_FROZEN_CALIBRATOR_HASH",
    "T_calibrated_score": "DIFFERENT_BECAUSE_RAW_INPUT_DIFFERS; frozen formula reconstructs both stored R1 and live calibrated scores",
    "U_threshold_comparison": "MATCH_NATIVE_AND_OPERATIONAL_DECISIONS; does not waive score tolerance"
  },
  "status": "UNRESOLVED",
  "tolerance_changed": false
}
```

## All-Seed Replay Audit

Expected seeds: 698. Replayed in the all-seed audit: **0**. Audit verdict: **NOT_RUN**, because the root cause is UNKNOWN and Section 13 requires stopping. Maximum/median deltas, count above tolerance and decision mismatches for the all-seed population are unavailable, not zero. The single first-seed diagnostic is counted separately. No first-seed fix or all-seed PASS is claimed.

## Query Accounting

Historical failed attempt exact count known: NO; bound 1-61 remains UNKNOWN_EXACT_COUNT_BOUNDED_1_TO_61. Current diagnostic baseline calls: **1**, logical requests: 1, unique model calls: 1. All-seed audit calls: 0. Authoritative restart attack calls: **0**. D_M-B/D_G/ensemble generation calls: **0/0/0**.

Durable model journal: YES, `detection_service/outputs/r2-ds-repair-001/diagnostic_queries_v1.jsonl`; SHA `5800ae312409d6c8fba35fb5deac60fdea8f2bff258b49807251b67067d78bac`. New journal schema: `r2_ds_query_journal_v1`, SHA `fc1cd4e65aad551e3165ae0410bf441e9459eba814b76fc95f7bcca778d5fe89`. Returned scores are fsynced before status/replay checks; subsequent logical requests and cache hits have a separate fsynced ledger. The first diagnostic used the preceding model-return ledger version, whose exact code bytes are archived locally and hash-bound; it made only one logical request and one model call. No original diagnostic receipt was rewritten after the logical-ledger enhancement.

## Accounting Repair

Generation now logs returned raw/calibrated scores before assertions and checks frozen raw/calibrated/native/operational baseline equivalence before saliency. Cache-hit logical receipts do not add model calls. The entry point rejects an UNKNOWN diagnosis or non-PASS all-seed audit. Restart gating requires seed 1; previous invocation files remain preserved, not resumed or merged. Full restart receipt/bookkeeping is NOT created because the prerequisite audit did not pass. No live repaired generation was run.

## Scientific Integrity

Seed membership, objective, operators/order, padding, saliency, ranking/ties, 61-query budget, threshold, success criterion, validity, lineage and random seed: UNCHANGED. No tolerance relaxation, score rounding, clipping change, retraining, calibration fit, source normalization or package upgrade/downgrade. R0/R1/R2-DMB and the accepted protocol patch remain unchanged. Track B remains `0cd2d506380cbb3ec513207e4fa66ad422d2b3f2`; no worktree or merge change. No R2-DG/R3/verifier/protected evaluation.

## Repair Git

Starting HEAD: `5f5e6f4b159fb2aa75bec9a3f26360b776e4afc0`. Branch: `exp/r2-ds-001`. Diagnosis/accounting evidence commit and final HEAD are reported externally after commit/push to avoid self-reference. This is a BLOCKED diagnosis/accounting commit, not an accepted all-seed runtime repair. Restart-receipt, terminal-freeze, transfer-scoring and accepted-result analysis commits: NONE. No raw prompts, model weights or private pipeline/journal contents are committed.

## R2-D_S Final Result

**NOT_RUN**. No authoritative restart, accepted terminals, evasion rates/CIs, transfer rates/CIs or common-mode result exists.

## Tests And Preservation

```json
{
  "tests": {
    "passed": 181,
    "failed": 0,
    "errors": 0,
    "skipped": 0,
    "receipts": [
      {
        "path": "tmp/r2_ds_repair_tests.xml",
        "sha256": "47c8fb6757f3660e01e87962637b9ea700fd5f5c7fc324c948c002bcb1c9ba20",
        "passed": 109
      },
      {
        "path": "tmp/r2_ds_repair_preservation_tests.xml",
        "sha256": "d49a27a339d3a30e724e0941078065fa49bbcceed27ba1613cfb3acfdf4f1b2a",
        "passed": 72
      }
    ],
    "note": "The all-seed audit predicate tests use synthetic engineering rows; no real 698-seed audit was run."
  },
  "preservation": {
    "source_hash_checks": 503,
    "baseline": {
      "status": "PASS",
      "hash_checks": 96,
      "evidence_sha256": "4b42dd44f2604f12e099f1fc60decef866c64d036c9a6554fcd3e049513b8a21",
      "tracked_baseline_diff": "EMPTY"
    },
    "release": {
      "status": "PASS",
      "hash_checks": 118,
      "R1_started": false
    },
    "patch_hash_checks": 262,
    "prior_ds_artifacts_unchanged": 9,
    "Track_B_head": "0cd2d506380cbb3ec513207e4fa66ad422d2b3f2"
  }
}
```

Tests include all requested narrow-repair predicates and synthetic failure injection. Synthetic 698-row validation is not relabeled as real replay. Original R2-DS blocked-state artifacts and report remain byte-identical.

## FINAL VERDICT

**R2_DS_BASELINE_REPLAY_STILL_UNRESOLVED**

THE ROOT CAUSE WAS: UNKNOWN; the replay divergence is confirmed upstream of calibration, but the first causal stage is not supported by retained R1 intermediate evidence.

THE REPAIR DID NOT CHANGE THE EXPERIMENT BECAUSE: Only diagnostic capture, durable query/logical accounting and fail-closed pre-query gates changed; every frozen scientific choice and accepted artifact is preserved.

NEXT AUTHORIZED STEP: Stop and request review of a separately scoped numerical/runtime diagnosis; do not start R2-DG, R3 or a generation restart.
