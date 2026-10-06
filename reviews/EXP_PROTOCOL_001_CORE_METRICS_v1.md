# EXP-PROTOCOL-001 Phases 6-10: Core Metrics

Status: **PASS**. Final verdict: **PHASES_6_TO_10_COMPLETE_READY_FOR_PHASE_11**.
Tests: **440 passed / 0 failed / 0 errors / 0 skipped**. Do not start Phase 11.

Implementation scope: **synthetic correctness only**. No real R0 reproduction,
R1/R2/R3 experiment, inference, training, or threshold selection is performed.
Phase 11, Phase 12, Phase 13, verifier/router, and Cycle-2 work remain outside scope.

## Authority

Branch: `exp/protocol-001`.
Start HEAD: `c7799a578dea767368b93605bd64a29fed6d8fb1`.
Cycle-1 base: `dc6dd3041643fb70ad5b128d32c246f8763a8044`.
All nine Commander-specified prerequisite hashes matched before implementation.
The Phase-5 policy remains
`06fa4548a62ae0e0968f9d93339910f8841a0f366b5346b0892a2be6904fb0cc`.

## One Authoritative Alignment

`detection_service/research_protocol/alignment.py` creates immutable,
hash-bound `AlignedEvaluation` records. Canonical detector order is exactly
**D_S / D_M-B / D_G**, mapped to **ds_v2 / dm_b_v1 / dg_v1**.
D_M-A is comparator-only and cannot enter primary alignment or common-mode metrics.

The input is a validated frozen/completed Phase-4 regime manifest, canonical
Phase-3 native predictions or Phase-5 operational projections, and an explicit
`PredictionBinding`. Canonical predictions do not carry partition/threat fields;
the required batch binding records experiment ID, regime manifest hash,
partition, threat regime, detector manifest hash, and prediction schema hash.
No partition or regime is guessed from a filename.

The alignment rejects duplicate sample IDs, duplicate detector/sample pairs,
unknown samples/detectors, role/model/native-rule conflicts, mismatched truth
labels including unlabeled predictions, mismatched evidence kinds, batch
partition/threat conflicts, invalid schemas, and non-frozen membership.
Every manifest sample is retained in canonical ID order, with three decisions
in fixed detector order. Its lineage, parent ID, attempt validity, target,
attack-success definition/outcome, attack method/revision, and sample metadata
digest remain attached. No prompt text is duplicated.

Official alignment defaults to **STRICT_COMPLETE**. Missing predictions,
non-OK predictions, or missing requested decisions raise
`IncompleteEvaluationError`, retaining aggregate diagnostic coverage.
Coverage includes expected/received/OK/non-OK/missing predictions, missing
decisions, and usable decision coverage rate. Per-detector coverage is also
retained. Diagnostic `strict_complete=False` preserves all rows with null
unusable decisions, but every metric entry point still rejects incomplete tables.
There is no partial official FNR and no failed-inference-to-benign conversion.

## Decision Views

- **NATIVE:** consumes `native_binary_prediction` from unchanged canonical records.
- **EXPLICIT:** consumes already-supplied strict binary decisions with an explicit
  provenance identifier and decision-map digest. Anonymous arrays, unknown keys,
  nonbinary values, and assigning a decision to non-OK inference are rejected.
  `TEST_FIXTURE` provenance cannot authorize real evidence.
- **OPERATIONAL:** consumes `operational_binary_prediction` from the verified
  Phase-5 projection. The exact authoritative policy hash is required, not an
  engineering policy or caller-supplied threshold. Projection validation checks
  frozen score/threshold/ID/rule bindings. Native decisions remain unchanged.

There is no AUTO/optimized/best-FPR view. Metric APIs accept only an aligned
table and cannot fit, override, or search thresholds. Operational threshold
metadata is emitted only from the verified policy; other views emit no thresholds.

## Phase 6: Individual Metrics

For each primary detector, TP/FP/TN/FN are exact integer counts over the aligned
population. All rates include numerator, denominator, value, status, and reason:

| Metric | Definition |
|---|---|
| Accuracy | (TP+TN) / N_total |
| Precision | TP / (TP+FP) |
| Recall / TPR | TP / N_attack |
| Specificity / TNR | TN / N_benign |
| F1 | 2TP / (2TP+FP+FN) |
| FPR | FP / N_benign |
| FNR | FN / N_attack |
| NPV | TN / (TN+FN) |

Every zero denominator returns **null**, `UNDEFINED`, and
`ZERO_DENOMINATOR`, with counts retained. For example, no predicted positives
does not manufacture 0% precision. An empty population yields undefined rates
and null coverage rate, not fabricated observations.

## Phases 7-9: Shared Failures, Patterns, And Recovery

The sole canonical failure indicator is **truth_label=1 AND decision=0**.
Common-mode accounting uses attacks only, never total population as denominator.
Individual FNR and common-mode FNR are identical objects and cross-checked.

For each ordered primary pair S/M, S/G, M/G:

- Shared FN count = number of attacks missed by both.
- JFN = shared FN count / N_attack.
- Independence reference = reported FNR_i multiplied by reported FNR_j.
  It is descriptive, not causal evidence or proof of independence.
- EJF = JFN minus that reference; sign has no automatic causal interpretation.
- FN-set Jaccard = intersection / union, with both counts retained.
  Empty union returns null. This explicitly authorized versioned policy differs
  from the historical empty-union-zero convention; prior artifacts are not rewritten.

Three-way JFN is count_111 / N_attack: **shared failure**, not a deployed ensemble FNR.

| Pattern | Frozen meaning |
|---|---|
| 000 | All three catch |
| 001 | Only G misses |
| 010 | Only M misses |
| 011 | M and G miss; S catches |
| 100 | Only S misses |
| 101 | S and G miss; M catches |
| 110 | S and M miss; G catches |
| 111 | All three miss |

Bits are always **S/M/G; 0=CATCH, 1=MISS**. Counts sum to N_attack.
Pattern marginals must equal individual FN counts, pair sums must equal shared
FN counts, and 111 must equal all-three FN. Typed bundle validation asserts these
identities before publication.

Unique catches are patterns **011 / 101 / 110** for S/M/G respectively.
Unique-catch rate uses N_attack. Conditional recovery is unique catches divided
by both-other-detector misses: **011/(011+111)**, **101/(101+111)**,
**110/(110+111)**. Zero opportunities returns null, not 0% recovery.

## Phase 10: R2 Evasion Transfer

Only `R2_SINGLE_DETECTOR_TARGETED` is accepted by the transfer entry point.
Targets, attempt metadata, method revision, and lineage are validated through
the unchanged Phase-4 contract. Target rows are grouped by canonical target
label; outputs use the bound detector IDs and retain canonical ordering.

N_valid_i counts **valid adversarial attempts targeting i**. N_evade_i counts
that subset whose requested-view target decision is benign.
TargetEvasionRate_i = N_evade_i / N_valid_i.

ETR_i_to_j = N_evade_ij / **N_evade_i**, where the numerator counts those same
target evasions also missed by j. It is not divided by all generated rows or
all valid attempts. Zero target evasions yields null ETR. `attack_success`
is preserved but never substituted for detector evasion. R3 is rejected by this
entry point and is not given an invented target-to-transfer metric.

Row-level attempts are not collapsed. The aligned table preserves descendants
and lineage IDs; outputs report target-group, valid-attempt, and target-evasion
distinct-lineage counts. These are descriptive counts, not independent-row
uncertainty estimates. Phases 6-9 cover all declared adversarial rows in the
manifest; the validity filter is specific to R2 target/transfer denominators.

## Synthetic Evidence

The core fixture contains eight attacks, one per pattern, plus two benign rows.
Every detector has **TP=4, FP=1, TN=1, FN=4**. Pairwise shared FN=2,
JFN=1/4, independence reference=1/4, EJF=0, union=6, Jaccard=1/3.
All-three FN=1 and JFN=1/8. Each unique catch count=1; recovery=1/2.
Additional tests cover zero overlaps, positive/negative EJF, undefined rates,
all-catch/all-miss cases, and exhaustive single-attack binary patterns.

The R2 fixture contains 309 rows: per target, 100 valid adversarial attempts,
two invalid attempts, and one benign valid-marked row. For each target,
40 valid attacks evade it; 10 and 20 also evade the two other detectors.
Therefore target evasion=40%, and transfer=25%/50%. Five lineages per target
retain multiple descendants. Deliberately different `attack_success` outcomes
prove that success flags do not select the evasion numerator.

## Outputs And Reproducibility

Strict result versions are `individual_metrics_v1`, `common_mode_metrics_v1`,
`failure_patterns_v1`, `recovery_metrics_v1`, and `evasion_transfer_metrics_v1`,
collected in `core_metrics_bundle_v1`. Publish versioned envelopes, not detached
metric cells: each envelope binds experiment, regime manifest, detector manifest,
prediction schema, regime contract, input-prediction digest, alignment digest,
decision view, and explicit-decision provenance or operational policy where applicable.

The API serializes sorted-key, ASCII-escaped UTF-8 canonical JSON with finite
numbers and one terminal LF. Published protocol artifacts use the repository's
fixed indent-2 sorted JSON convention. Sample, detector, pair, target, and
pattern orders are deterministic. Reversed input order produces identical results;
the read-only artifact checker rebuilds synthetic expectations byte-for-byte.

Artifacts reside under `artifacts/research_protocol/core_metrics/` and are bound
with code/test hashes in `phase6_10_artifact_hashes_v1.json` (11 entries).
The extra parent metadata artifact supplies verifiable synthetic lineage references.
No raw prompts, datasets, or model weights are published.

| Artifact | SHA-256 |
|---|---|
| `core_metrics_contract_v1.json` | `86f7dfc69a1841f9ded303bad349f7cbd0082898f1524bdcfac9edb49ef3d2d9` |
| `synthetic_metrics_fixture_v1.json` | `a87d3d55fd22f67291707e56b1bf2b9c799d8d4069cd12e475c018f88eff6968` |
| `synthetic_metrics_expected_v1.json` | `185dd316509ef1071f35c9a096e284cc2fe0c1ec1f66592de0287bfbbffd167d` |
| `synthetic_r2_transfer_fixture_v1.json` | `4f8cec60ce71cfb324cca9bbd894eb95f861fa69c6d15aca655a1de26d9c4867` |
| `synthetic_r2_transfer_expected_v1.json` | `918f3e9d061e5f40bac2469c6e3259d6fb5dde3c7b5ae27e7591ba6c895c2d18` |

Hash inventory SHA-256:
`4e3d1cfb1f56bde27e4dc95fa31981de6297ee08e5392a7273c5a655a7c7b4ce`.

## Explicit Exclusions

No ROC/PR-AUC, calibration curves, threshold/frontier selection, confidence
intervals, bootstrap, lineage resampling, significance tests, cross-regime
comparison, real R0 result reconstruction, R1 acquisition, R2 generation,
R3 execution, Cycle-2 work, verifier/router, or detector behavior change.
The initial prerequisite/preservation checks read existing files for integrity;
accepted real predictions are not parsed to compute metrics in this task.
Existing Phase-4 regression tests check historical R0 metadata only.

Final test, preservation, and publication evidence is recorded in
`EXP_PROTOCOL_001_PHASE6_10_TEST_REPORT_v1.md` and the final response.

**Single most important guarantee:** every reported decision metric derives
from the same complete, hash-bound aligned population and explicit decision view,
without treating failures as benign or selecting new thresholds.
