# EXP-PROTOCOL-001 Frozen Specification v1

## 1. Protocol Identity
Release `exp_protocol_001_v1`; branch `exp/protocol-001`; FROZEN before R1.
Phase 16: PHASE_16_NOT_DEFINED_IN_APPROVED_PLAN. No Phase-16 functionality exists.

## 2. Frozen Detector Stack
Primary order: D_S (`ds_v2`), D_M-B (`dm_b_v1`), D_G (`dg_v1`).
D_M-A is COMPARATOR_ONLY and never enters primary common-mode accounting.
The detector manifest is the authoritative model/code/calibrator identity source.

## 3. Canonical Score Semantics
HIGHER_IS_MORE_ADVERSARIAL. D_S raw LR class-1 probability maps through frozen
`ds_v2_cal_v1` sigmoid-on-clipped-log-odds calibration. D_M-B uses raw ATTACK
softmax for decisions. D_G uses maximum malicious chunk probability for operational
decisions; its native OR-of-chunk-argmax remains distinct.

## 4. Prediction Contract
Use `prediction_v1` with the frozen Phase-3 null operational lock. Activate only
the Phase-5 policy-bound `prediction_operational_v1` projection. Preserve non-OK
statuses and null decisions; STRICT_COMPLETE rejects missing/non-OK rows.
The R0 historical operational score projection is not a final-model prediction:
it preserves OOF/direct source provenance and validates every accepted source row.

## 5. Regime And Partition Contract
Use `regime_manifest_v1`, `regime_sample_v1`, and the unchanged Phase-4 contract.
Partitions describe governance; threat_regime describes experimental conditions.
Do not repartition, reinterpret labels, or fit on evaluation outcomes.

## 6. Lineage Contract
Retain parent IDs, source revisions, evidence, and explicit unknown lineage.
Generated R2/R3 descendants remain clustered. Do not invent independent identities
for descendants or duplicate canonical IDs to represent bootstrap multiplicity.

## 7. Frozen Operating Policy
`operating_policy_v1`, `benign_empirical_fpr_budget_v1`, CALIBRATION 3% benign FPR
selection budget, inclusive `>=`. This budget is not a future-dataset guarantee.

| Detector | Threshold | ID | Input |
|---|---:|---|---|
| D_S | 0.5585373573968287 | ds_v2_op3_cal_v1 | calibrated score |
| D_M-B | 0.0004967087297700347 | dm_b_v1_op3_raw_v1 | raw ATTACK softmax |
| D_G | 0.21291141211986545 | dg_v1_op3_raw_v1 | raw maximum malicious probability |

## 8. Operational And Descriptive Views
Primary future view: OPERATIONAL_FIXED_V1 with the exact operating manifest hash.
Historical descriptive 1/3/5% views retain their separate stored cutpoints.
Descriptive outputs cannot populate operational predictions or replace policy.
No direct cross-view improvement claim is permitted.

## 9. Individual Metrics
TP/FP/TN/FN on complete aligned labels. Accuracy=(TP+TN)/N; precision=TP/(TP+FP);
recall=TP/(TP+FN); specificity=TN/(TN+FP); F1=2TP/(2TP+FP+FN);
FPR=FP/(FP+TN); FNR=FN/(FN+TP); NPV=TN/(TN+FN).
Zero denominators remain undefined, not zero. Retain all numerator/denominator pairs.

## 10. Common-Mode Metrics
On attacks, JFN=shared misses/attack count. Independence reference=FNR_A*FNR_B.
EJF=JFN-independence reference, including negative values. FN Jaccard=shared FN/
union FN; zero union is undefined. All-three JFN=all-three misses/attack count.

## 11. Failure-Pattern Semantics
Frozen bit order S/M/G; bit 1 means miss, 0 means catch. All eight patterns
000 through 111 partition the attack population. They are not fusion decisions.

## 12. Unique Catches
Detector catches while both others miss. Count and rate over all attacks.
Unique S/M/G catch patterns are 011/101/110 respectively.

## 13. Conditional Recovery
Unique catch count divided by the number of attacks both other detectors miss.
The denominator is unique catch plus pattern 111; zero opportunities is undefined.

## 14. TargetEvasionRate
R2 only: target misses among valid targeted attack attempts, divided by valid
targeted attempts. Do not condition this denominator on successful evasion.

## 15. ETR
R2 only: among valid attempts that evade the target, the fraction also missed by
the specified untargeted detector. Zero target evasions yields undefined ETR.
R3 has no single target-to-detector ETR and remains NOT_APPLICABLE for that metric.

## 16. Bootstrap And Uncertainty
PERCENTILE_BOOTSTRAP_V1; 1,000 replicates; seed 1701; confidence .95; NumPy 2.1.3
PCG64; explicit linear quantiles .025/.975. Declare SAMPLE_PAIRED or LINEAGE_CLUSTERED.
Keep detector outcomes paired; generated descendants require clustering. Attack
and benign domains remain separate; mixed-population metrics may use declared
stratified-label sampling. Target/transfer use VALID_TARGET_ATTEMPTS.
Observed frozen-core point, never replicate mean. Undefined replicates are invalid;
at least 95% valid support is needed, otherwise null CI/UNSTABLE_DENOMINATOR.
Observed undefined points have null CI. Paired deltas require identical populations
and shared selections, B minus A. No p-values or causal claims.

## 17. Cross-Regime Comparison
Slots: R0, R1, R2-D_S, R2-D_M-B, R2-D_G, R3. Require identical detector/order,
metric definitions, labels, compatible decision/view and exact operational policy.
Different datasets are unpaired; report current-minus-reference fractions and
percentage points, not significance. NOT_RUN, NOT_APPLICABLE, and UNDEFINED
remain distinct from zero. Incompatible views yield no deltas.

## 18. Historical R0 Baseline
Accepted 1,135/183/952 population, D_S/D_M-B OOF and frozen D_G development scores.
Phase-13 1/3/5% tables reproduce exactly. Historical Python-MT19937 intervals
are explicitly replayed separately from production PCG64; no history is rewritten.

## 19. Operational R0 Baseline
Same population and score provenance; D_S only applies frozen calibration.
Phase-14 confusion counts TP/FP/TN/FN: S=113/43/909/70;
M=181/58/894/2; G=42/17/935/141. Actual FPRs are 43/952, 58/952, 17/952.
Retain the frozen operational bundle and production uncertainty as future reference.

## 20. Preflight And Protocol Lock
`protocol_lock_manifest_v1` binds accepted Git bytes and exact frozen settings.
`verify_experiment_preflight` validates the strict ExperimentRequest, hashes,
schema/regime/target/lineage, and fixed policy. Official evaluation is read-only;
TEST_FIXTURE cannot publish real experiments. A preflight PASS is not evidence
that inference ran or that dataset-specific governance was approved.

## 21. Forbidden Modifications After Freeze
No detector, model, calibrator, partition, threshold/ID/operator, direction, metric,
bootstrap default, or policy override. No auto-fitting or adaptation on any
evaluation partition, including VALIDATION/INTERNAL_TEST/FROZEN_EXTERNAL/FINAL_TEST.

## 22. Future R1 Execution Order
Follow the runbook's 14 steps. R1_SHIFTED_UNSEEN; target null; declare bootstrap
unit from actual lineage before interpreting results. No policy adaptation.
Dataset qualification/execution requires its own authorization; none occurs here.

## 23. Future R2 Execution Order
R2_SINGLE_DETECTOR_TARGETED. Follow the runbook with exactly one target D_S, D_M-B, or D_G. Record method/revision,
generator/revision, parent/lineage, validity, and attack-success definition.
Use clustered descendants and correctly conditioned TargetEvasionRate/ETR.

## 24. Future R3 Execution Order
R3_ENSEMBLE_TARGETED. Follow the runbook with target ALL and generation/lineage provenance. Use clustered
uncertainty; analyze individual/pair/all-three failures, patterns and recovery.
Do not reinterpret R3 as single-target R2 transfer.

## 25. Artifact Provenance Rules
Hash exact bytes; use deterministic canonical serialization and nonrecursive
self-hashes. Preserve actual model/run commits separately from evidence commits.
Record source, sample/lineage manifest, adapter, model, calibrator, policy and code
identities. Package references only, no raw prompts or weights. Never silently
substitute a missing frozen artifact or infer a revision from current upstream HEAD.

## 26. Failure And Stop Conditions
Stop on hash drift, incomplete predictions, ambiguous scores/provenance, missing
lineage, invalid targets, policy/view mismatch, overrides/fitting requests,
nondeterministic reconstruction, missing/conflicting release roles, network needs,
protected leakage, or historical/operational regression. Report the actual blocker.
No verifier/router selection or implementation occurs here; verifier experiments
are separate and begin only after base-stack R1/R2/R3 evidence exists.

R1 HAS NOT STARTED. NO FUTURE REGIME DATA WAS USED TO MODIFY THE PROTOCOL.
EXP-PROTOCOL-001 IS FROZEN BEFORE R1.
