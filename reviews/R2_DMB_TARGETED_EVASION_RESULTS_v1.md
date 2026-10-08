# R2-DMB-001 FINAL REPORT

STATUS: BLOCKED

Stop code: `R2_PROTOCOL_MUTATION_REQUIRED`.

## Repository

Source branch: `exp/protocol-001`.
Source HEAD: `62bf867b2acc53c3a8dc35d18f443558cd9da508`.
R2 branch: `exp/r2-dmb-001`.
Predeclaration commit: `5c74a379b51360a4b84993beba546948344405ea`.
Generator implementation commit: NOT CREATED; blocked before the authoritative implementation/run gate.
Attack-set freeze commit: NOT CREATED.
Transfer-scoring commit: NOT CREATED.
Analysis commit: NOT CREATED.
Final synchronization is recorded in the separate final handoff after the diagnostic commit.

## Blocker Evidence

The frozen sole official evaluation entry point is
`detection_service/research_protocol/protocol_lock.py:evaluate_official`.
Its R2 branch selects every `target/` and `transfer/` scalar from the frozen
metric catalog, then requests uncertainty with one `target_detector`.

The frozen catalog contains target and transfer entries for all three detectors,
including undefined entries for targets without valid attempts. The frozen
uncertainty validator in `uncertainty.py:validate_metric_domain` requires each
requested target metric to match the configured target. Consequently the official
D_M-B uncertainty request is rejected with `TARGET_METRIC_DOMAIN_CONFLICT`.

This was reproduced with the existing synthetic R2 fixture, not project attack
text or model inference. A D_M-B-only metric-name projection is accepted by the
same validator, confirming the mismatch is the official caller's request rather
than a changed uncertainty definition. No caller or validator was patched.

The Commander forbids changing the protocol release, metric/uncertainty contracts
or frozen components, and requires STOP when such a change is needed. Accordingly
no authoritative generation, terminal selection, transfer inference or official
R2 result is published. No alternative evaluator was silently substituted.

Required decision: explicitly authorize a separately versioned correction to the
official R2 evaluation path and its protocol provenance, or an explicitly approved
evaluation path compatible with the existing frozen contracts. This task does not
authorize that change. The original source branch and its release remain intact.

## Protocol Integrity

D_S modified: NO.
D_M-B modified: NO.
D_G modified: NO.
Thresholds changed: NO.
Calibration changed: NO.
R0 modified: NO.
R1 modified: NO.
Protected data used: NO.
R3 started: NO.
Verifier started: NO.
Cycle 2: DEFERRED.

## Seed Population

Expected R1 attacks: 800.
Actual R1 attacks: 800.
D_M-B baseline catches in accepted R1 evidence: 800.
R2 seeds: 800.
LLMail seeds: 400.
InjecAgent seeds: 400.
Unique inherited lineages: 97.
No subsampling or untargeted-detector selection.

## Target Isolation

D_S generation queries: 0.
D_G generation queries: 0.
Ensemble generation queries: 0.
D_M-B authoritative generation queries: 0.
Maximum authoritative queries for any seed: 0.
Query-budget violations: 0.
Target isolation: no authoritative generation performed; no untargeted access.

## Attack Validity

Terminal candidates: NOT GENERATED.
Inverse reconstruction: NOT RUN on authoritative candidates.
Invalid UTF-8/payload-deletion violations: NOT APPLICABLE; no generated population.
Validity status: NOT RUN.

## D_M-B Targeted Evasion

Successful evasions, TargetEvasionRate, confidence intervals, median target scores
and query statistics: NOT RUN. Do not interpret this as zero evasions or evidence
of robustness. The generator did not receive an authoritative run.

## Target Success by Source

LLMail and InjecAgent target evasion results: NOT RUN.

## Cross-Detector Transfer

Successful-evasion denominator and all directional/joint ETR metrics: NOT RUN.
No successful population exists; no value or zero denominator is invented.

## Full R2 Terminal Population

No population or TP/FN/recall/FNR metrics exist.
FPR: NOT_APPLICABLE_ATTACK_ONLY_REGIME.
ROC-AUC: NOT_APPLICABLE_ATTACK_ONLY_REGIME.
AP: NOT_APPLICABLE_ATTACK_ONLY_REGIME.

## Common-Mode

Pairwise shared failures, JFN, EJF, Jaccard and all-three misses: NOT RUN.

## Successful-Evasion Failure Patterns

000, 001, 010, 011, 100, 101, 110 and 111: NOT RUN; not zero.

## Parent To Child Transitions

D_S, D_M-B and D_G transitions: NOT RUN; no children were generated.

## Operator Results

All operator success/transfer results: NOT RUN.
Most effective/highest-transfer mechanism: NOT DETERMINED.

## Coverage Analysis

Authoritative child tokenization/truncation comparisons: NOT RUN.
No causal or associative coverage conclusion is made.

## R1 To R2 Interpretation

No R2 research outcome exists. The blocker concerns the frozen evaluation path,
not D_M-B robustness, generator effectiveness or transfer capability.

## Implementation Drafts

Reversible search, target-isolated invocation, freeze validation, transfer,
analysis and report drafts were written but not committed as accepted experiment
implementation. They were archived with byte-for-byte hash verification under
`detection_service/outputs/r2-dmb-001/blocked_implementation_draft/`, which is
gitignored. No raw prompt was included in this code archive.

The predeclaration/generator draft suite passed 41 tests (13 predeclaration and
28 generator tests) using synthetic text and fake target scores only. A subsequent
draft analytics suite had 43 passes and five failures: its synthetic fixture
retained benign rows despite an attack-only helper/domain expectation. That draft
and its failing XML are preserved, not accepted or silently presented as passing.
These draft checks are separate from the final accepted diagnostic test receipt.
No experiment results were generated during any test.

## Tests And Preservation

Final accepted checks comprise the 13 predeclaration tests and one explicit
synthetic protocol-blocker reproduction. See `r2_dmb_blocker_v1.json` for the
actual final receipt, counts and hashes. The diagnostic passing means the blocker
was reproduced; it does NOT mean the official R2 evaluation path passes.

252 predeclared source/model/protocol/R0/R1 hashes, 96 baseline-preservation hashes
and 118 frozen-release hashes are checked. Historical full-suite R1 results are
not claimed as a new R2 rerun. Post-generation/transfer tests were not run because
their required authoritative artifacts do not exist.

## Artifacts

- `artifacts/research_protocol/r2_dmb/r2_dmb_predeclaration_v1.json`
- `artifacts/research_protocol/r2_dmb/r2_dmb_seed_manifest_v1.json`
- `artifacts/research_protocol/r2_dmb/r2_dmb_blocker_v1.json`
- `detection_service/tests/test_r2_dmb_protocol_blocker.py`

No accepted generator manifest, terminal manifest, predictions, transfer metrics,
uncertainty bundle or R2 result bundle exists.

## FINAL VERDICT

BLOCKED

THE SINGLE MOST IMPORTANT R2-DMB FINDING:
The frozen official R2 uncertainty request is incompatible with its frozen
single-target domain validator, so the experiment was stopped before any
authoritative model query.

WHAT THIS MEANS FOR THE COMMON-MODE HYPOTHESIS:
No new R2 evidence supports or contradicts it because no attack generation or
transfer evaluation occurred.

NEXT AUTHORIZED RESEARCH STEP:
Resolve the explicit protocol-compatibility authorization first; only after that
may this D_M-B experiment resume, followed by separately authorized R2 targeting
the next frozen detector; do not start R3.
