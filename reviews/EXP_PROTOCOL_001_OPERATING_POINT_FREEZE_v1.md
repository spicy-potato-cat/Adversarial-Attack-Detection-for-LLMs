# EXP-PROTOCOL-001 Phase 5: Operating-Point Freeze

Status: **PASS**. Final verdict: **PHASE_5_COMPLETE_READY_FOR_PHASE_6**.
Phase 6 is not started. Cycle 2 remains deferred.

## Authority And Execution Provenance

- Branch: `exp/protocol-001`.
- Start HEAD: `d82e745e2dd39eef4e1455b495fec3582d85f94b`.
- Cycle-1 authority: `dc6dd3041643fb70ad5b128d32c246f8763a8044`.
- Algorithm, activation implementation, synthetic tests, and preregistration were
  committed before any real calibration inference or threshold selection:
  `9c63092d51d194930c276e215b8bbd98085cfde5`.
- D_G execution commit is that same predeclaration commit. The later publication
  commit is evidence provenance, not model-run provenance. Run metadata is not rewritten.
- Predeclaration SHA-256:
  `992eac53d0b9bd84ce8bb28cd94f8c20d79f768072c625b87f004d4d69f6cfca`.

## Frozen Policy

Policy: `operating_policy_v1`.
Algorithm: `benign_empirical_fpr_budget_v1`.
Comparison: **ATTACK iff threshold-input score >= threshold**.
Tie policy: `binary64_nextafter_boundary_toward_positive_infinity`.

The authorized pre-test partition is CALIBRATION, not VALIDATION or a future
threat regime. Its accepted membership contains exactly 233 unique IDs: 41
attack and 192 benign. All three detectors align to these same IDs and labels:
zero duplicates, missing IDs, or label disagreements.

Selection manifest:
`data_governance/manifests/development_partition_manifest_v1.csv`.
SHA-256: `9cdd5ecdd80f9ac3c8f05db63742721f4537ca2b64a2fe48f6c2b424b57483a6`.
Selected membership digest:
`fcb21024ad8e4c2d33569c26fefdb551b319c5441791c3bac1933849c6c57cf6`.

Alpha is the Commander-predeclared **3% empirical benign FPR budget**, represented
exactly as `3/100`. It was not chosen by optimizing performance. Therefore
`K = floor(3 * 192 / 100) = 5`. The attainable budget ceiling is 5/192, or
2.6041666667%; this is not a guarantee of future-regime FPR under distribution shift.

For each detector, sort only benign scores descending, take the sixth largest
as the boundary, and choose its binary64 successor toward positive infinity.
Every boundary tie is excluded. Attained FP may be less than five; there is no
adjustment to force equality. Empty, missing, duplicate, wrong-partition, or
nonfinite evidence fails rather than dropping rows. The finite successor of
probability 1 is explicitly supported; unrepresentable thresholds fail.

Positive scores do not select thresholds. All three selected thresholds were
persisted in `selected_thresholds_before_diagnostics_v1.json` before positive
diagnostics began. There was one selection attempt and no reselection.

## Results

Each detector has 192 benign calibration rows and attained **5 FP / 2.6041666667% FPR**.
The positive diagnostics below use 41 attack rows and do not modify the policy.

| Detector | Threshold input | Frozen threshold | Boundary | Boundary ties | TP | FN | Diagnostic recall |
|---|---|---|---|---|---|---|---|
| `ds_v2` | Calibrated score | 0.5585373573968287 | 0.5585373573968286 | 1 | 26 | 15 | 63.41463415% |
| `dm_b_v1` | Raw attack softmax | 0.0004967087297700347 | 0.0004967087297700346 | 1 | 38 | 3 | 92.68292683% |
| `dg_v1` | Raw max malicious chunk probability | 0.21291141211986545 | 0.21291141211986542 | 1 | 9 | 32 | 21.95121951% |

Threshold IDs are respectively `ds_v2_op3_cal_v1`, `dm_b_v1_op3_raw_v1`, and
`dg_v1_op3_raw_v1`. D_G's low diagnostic recall is recorded without rescue tuning.

## Score Provenance

**D_S:** reused accepted final-model calibration predictions; no live D_S
invocation, reconstruction, archived runtime restoration, or substitution.
Logical accepted artifact:
`artifacts/statistical_v2/calibration/completed_v1/calibration_predictions_v1.csv`.
Actual local evidence:
`detection_service/outputs/common003-preserved-stack/artifacts/statistical_v2/calibration/completed_v1/calibration_predictions_v1.csv`.
SHA-256: `35fedee4cafd2b60adcfcc4eb586784cca03e26472940059dc924cc0f49eadfa`.
The source `calibrated_probability` maps to the frozen `calibrated_score` input.
Calibrator `ds_v2_cal_v1` is used for the threshold.

**D_M-B:** reused accepted
`artifacts/models/dm_b_v1/calibration/calibration_scores.json`.
SHA-256: `3e364c0f48773a462b480b0580728760edb959a686247f5290c0deed47596208`.
The raw probability byte digest also matches accepted calibration metadata.
`dm_b_v1_cal_v1` remains bound and available analytically, but is not used for
operating-point selection. No new D_M-B inference or recalibration occurred.

**D_G:** inventory found only accepted BASE_TRAIN predictions, not CALIBRATION
scores. One authorized offline pass scored exactly 233 CALIBRATION records.
Model: `meta-llama/Llama-Prompt-Guard-2-22M`.
Revision: `11614a155199674a0a95e6602d6ab0417b790ed0`.
Weights SHA-256: `5120e30bcd536ce285345d9ec104bea6bd6e8f94365b99a340c764f417ea5fa1`.
Malicious class index: 1. Native preprocessing unchanged; chunk content size
510, overlap 64, stride 446, full tail coverage; score aggregation is maximum
malicious probability. CPU inference took 72.3228991 seconds, with seed 1701,
eight torch threads, and deterministic algorithms enabled. All statuses were OK.
No download, model substitution, training, or D_G calibration occurred.
Run settings, source hashes, package versions, and execution commit are retained
in `operating_points/dg_calibration_run_v1.json`.

No VALIDATION samples were supplied to a detector, used for threshold selection,
or inspected for operational performance. Integrity hashing and selected-row
extraction necessarily read shared source containers and partition metadata;
this is not a claim that files containing other partitions were never opened.
Only selected CALIBRATION text was materialized for inference. No protected,
INTERNAL_TEST, FROZEN_EXTERNAL, FINAL_TEST, R1, R2, or R3 data was used.

## Native And Operational Views

Native/default rules remain unchanged: D_S calibrated >=0.5, D_M-B raw >=0.5,
and D_G OR of native chunk argmax votes. Threshold IDs are distinct from native
rule IDs. Operational decisions may differ from native votes.

`load_frozen_operating_policy` requires an independently trusted manifest file
hash and checks the self-hash, detector/model/calibrator identities, score
evidence hashes, and earlier protocol bindings. `apply_operating_policy` consumes
that verified immutable policy; it cannot fit, override, or reselect thresholds.
Missing or mismatched policy blocks activation. Non-OK results have null
operational fields and are never converted to benign predictions.

The original `prediction_v1` schema remains byte-identical and null-locked.
Activation is an additive `prediction_operational_v1` projection with an explicit
policy SHA. The published operational schema binds thresholds and IDs;
full validation additionally requires verified policy context. It is not
silently substituted into the Phase-4 native join contract. Future evaluation
must explicitly consume this projection; Phase-6 evaluation is not implemented.

## Integrity And Artifacts

- Phase-2 accepted checks: 165/165, including 96/96 baseline preservation checks.
- Phase-3 artifact checks: 6/6. Phase-4 artifact checks: 14/14.
- Phase-5 inventory checks: 12/12. Independent aligned-score FP/TP/FN accounting passed.
- 233 saved real D_G predictions passed operational activation and JSON roundtrip;
  all native fields were preserved, with four native/operational vote differences.
- Regression suite: 344 passed, zero failed, zero skipped. See the test report.
- No detector source, model, calibrator, raw source, or earlier protocol artifact changed.
  The only existing tracked-file edit is the narrow `.gitattributes` byte-preservation addition.
- Prior Phase-4 regression tests checked historical R0 metadata only; no R0
  inference, prediction metrics, confusion matrices, common-mode analysis, or frontier analysis ran.
- No retraining, recalibration, general metrics engine, bootstrap, verifier,
  protected experiment, Cycle-2 work, or Phase-6 work occurred.

| Artifact | SHA-256 |
|---|---|
| `artifacts/research_protocol/operating_point_manifest_v1.json` | `06fa4548a62ae0e0968f9d93339910f8841a0f366b5346b0892a2be6904fb0cc` |
| `artifacts/research_protocol/operating_points/calibration_operating_scores_v1.csv` | `146920d8de22e369cf3c4d1e5ae1a74ff8779a01f20b2b035d8be4b99585a4d8` |
| `artifacts/research_protocol/operating_points/threshold_freeze_evidence_v1.json` | `393616d807b12d10354485c0c1c1bd3d04c5a0e6d5f7508c5e471d2741b537db` |

The deterministic alignment CSV contains IDs, labels, scores, and source locators,
not raw prompts. All score/run/selection/schema/code hashes are published in
`artifacts/research_protocol/phase5_artifact_hashes_v1.json`.

## Acceptance

All 30 Phase-5 criteria pass. Publication uses two logical commits: predeclaration
before execution, then frozen evidence and reports. No raw data or weights are
included. Final commit identity and remote synchronization are reported after
normal push and fetch, without rewriting execution provenance.

**Single most important guarantee:** operational thresholds are selected once
from benign CALIBRATION scores and remain fixed across future threat regimes,
independently of the preserved native/default decisions.
