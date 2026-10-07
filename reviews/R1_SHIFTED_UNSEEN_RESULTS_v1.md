# R1_SHIFTED_UNSEEN Results v1

Status: **BLOCKED AT GATE B - SOURCE GOVERNANCE**.
Gate A: **PASS**, commit `861db5287816141c4a8e7f486dfe963636eaa3aa`.
Gate B: **BLOCKED**. Gates C and D: **NOT_STARTED**.
This is a partial execution/blocker report, not an R1 performance report.

## 1. R1 Dataset Constitution

No R1 dataset ID, membership, labels or source revisions were frozen. Sample,
attack and benign counts are **NOT_ESTABLISHED**, not a zero-row evaluation.
Existing local source-qualification metadata was inspected without opening new
source payloads. No R1 detector scores were inspected or generated.

The current role-specific `data_governance/DATA_PROMOTION_REGISTER_v1.md`
supersedes the older readiness recommendations only for its expressly approved
roles. Public availability and raw-file presence do not constitute promotion.

| Sources | Current role | R1 qualification outcome |
|---|---|---|
| deepset; Do-Not-Answer | APPROVED_FOR_DEVELOPMENT | Excluded: actual development sources, not unseen |
| XSTest | APPROVED_FOR_PROTECTED_EVAL / SOURCE_LEVEL_RESERVED | Not accessed: current authorization prohibits protected/final data; no R1 row clearance |
| JBB GCG artifact | APPROVED_FOR_ATTACK_GENERATION | Seed/stress-generation only; no evaluation approval |
| AdvBench; HarmBench; JBB | REVIEW_REQUIRED | Rights, semantics and/or aggregate lineage unresolved |
| WildJailbreak; WildGuardMix | REVIEW_REQUIRED | Conditional rights, PII, revisions and aggregate overlap unresolved |
| Tensor Trust; BIPIA; InjecAgent; AgentDojo; LLMail-Inject | REVIEW_REQUIRED | Required current source-specific forensic qualification absent |
| OR-Bench | REVIEW_REQUIRED | Edition/component qualification absent |
| AutoDAN local material; SALAD example | QUARANTINE | Missing generated outputs or incomplete artifact/unknown rights |

Zero qualified external attack sources remain. Thus the required two meaningful
external attack sources/families cannot be constituted under existing clearance.
XSTest approval is not silently converted into permission to cross its reserved
boundary. Even separately resolving that benign boundary would not clear attacks.

## 2. Unseen-Source Justification

NOT_ESTABLISHED. The 1,601-row development manifest is unchanged at SHA-256
`9cdd5ecdd80f9ac3c8f05db63742721f4537ca2b64a2fe48f6c2b424b57483a6`.
Reusing deepset or Do-Not-Answer is not an external-source solution. No claim of
unseen status, project independence or unknown upstream-model exposure is made.

## 3. Contamination Audit

NOT_RUN: no authorized R1 membership exists. Exact/canonical overlaps remaining
are **UNKNOWN**, not zero. No exclusions were fabricated.

Existing source-promotion/qualification and contamination-policy summaries were
read. Historical PILOT-01/WAVE-2 logs retain hashes and method descriptions but
are not the actual pair/cluster matrices. These referenced materials are missing:

- `PHASE-3/02_registry`
- `PHASE-3/reports/PILOT-01_FORENSIC_REPORT.md`
- `PHASE-3/reports/WAVE-2_FORENSIC_REPORT.md`
- `PHASE-3/09_legal_privacy/PILOT-01_RIGHTS_AND_PRIVACY_REVIEW.md`
- `PHASE-3/09_legal_privacy/WAVE-2_RIGHTS_AND_PRIVACY_REVIEW.md`
- `PHASE-3/11_contamination_matrix`

No attempt was made to recreate missing clearances from logs, external-repository
label guesses, public licenses or detector outputs. Cycle-2 qualification was
aborted by prior Commander instruction and was not reactivated.

## 4. Lineage Structure

NOT_ESTABLISHED: no R1 lineages or singleton fallback assignments. Source-specific
participant, behavior, scenario, trajectory and variant dependencies remain
qualification requirements. Singleton fallback would not establish independence.

## 5. Frozen Detector Identities

D_S: frozen `ds_v2`, B2 26-feature schema, accepted balanced L2 LR, frozen
`ds_v2_cal_v1`; exact archived implementation from
`e6b6a2af2a78e2a31aae6d9377378993f678b073`, SHA
`4912273d2caad3ff4f4094b9684310dc85199421fde7823b7de66d55607558fd`.
Additive private-package loading leaves the absent active application path and
all frozen protocol artifacts unchanged. Canonical prediction logic is inherited.

Reference LM: `distilbert/distilgpt2`, revision
`2290a62682d06624634c1f46a6ad5be0f47f38aa`.
Feature schema SHA:
`93d3892b158c35eccfadc27c879754db69ea5293782492ee5d4ff01a33bff983`.
Model SHA: `c5e754dc8b6e88b7437e4b81016e8f8ec23d018607d4f4e78906212b2a561157`.
Reference artifact SHA:
`fd26774585223913d12b8c20556a8fc1a50fa5dea7a3a75068a7bb30efce76ec`.
Calibrator SHA: `964cea57d98673d2026fb2f0e9d5884aec61a653e726847e0fb6ccbf36e95f23`.
CPU; context 1024, prefix 4096, LM overlap/stride 64/960, feature window/stride
128/64. Native calibrated cutpoint 0.5 remains distinct from operational
`0.5585373573968287`, threshold ID `ds_v2_op3_cal_v1`.

Gate A used all 233 accepted CALIBRATION records and 10 historical BASE_TRAIN
representatives: 243 authoritative score comparisons, 197 benign/46 attack.
Maximum raw delta `3.4861002973229915e-14`; calibrated delta
`1.902644708451362e-14`; tolerance `1e-12`. Native and operational mismatches: 0.
Stored BASE feature vectors matched exactly. A separate pre-existing accepted
long synthetic recipe exercised 4502 input tokens, 4095 analyzed, 5 LM chunks,
63 windows and truncation; token accounting and inherited features matched.
It was not an additional historical ds_v2 score comparison. No fitting occurred.
See `reviews/R1_DS_RUNTIME_EQUIVALENCE_v1.md` for complete gate evidence.

D_M-B: frozen `dm_b_v1`; operational raw threshold
`0.0004967087297700347`, ID `dm_b_v1_op3_raw_v1`.
D_G: frozen `dg_v1`, Meta Llama-Prompt-Guard-2-22M revision
`11614a155199674a0a95e6602d6ab0417b790ed0`; operational raw threshold
`0.21291141211986545`, ID `dg_v1_op3_raw_v1`.
Neither semantic/guard detector was run on R1.

## 6. Operational Performance

NOT_MEASURED for all detectors. No prediction artifact, confusion matrix,
accuracy, precision, recall, specificity, F1, FPR or FNR is available for R1.

## 7. Descriptive Frontier

NOT_MEASURED. No R1 thresholds or Recall@FPR<=1/3/5% were computed.
The frozen operational policy was not modified.

## 8. Ranking Metrics

NOT_MEASURED. No R1 ROC-AUC or Average Precision claim.

## 9. Pairwise Shared Failure

NOT_MEASURED for S/M, S/G and M/G. Shared FN, JFN, independence references,
EJF, Jaccard and confidence intervals are unavailable, not zero.

## 10. All-Three Failure

NOT_MEASURED. No count, JFN or interval is available.

## 11. Failure Patterns

NOT_MEASURED for every pattern `000` through `111`.

## 12. Unique Catches

NOT_MEASURED for D_S, D_M-B and D_G; no rate or interval.

## 13. Conditional Recovery

NOT_MEASURED; neither numerator nor denominator was established.

## 14. Family-Conditioned Analysis

NOT_MEASURED. No family counts, support classifications, worst-family FNR,
pairwise/all-three JFN or thresholds selected from outcomes.

## 15. Uncertainty

NOT_RUN. No bootstrap unit declared for nonexistent membership and no final CIs
computed. Frozen defaults (1000 replicates, seed 1701, 95% percentile) unchanged.

## 16. R0 vs R1 Comparison

NOT_RUN. R0 release evidence remains byte-preserved. Without R1 there is no
cross-regime delta, paired inference or descriptive comparison. R0 values were
not manually recreated and are not presented as R1 measurements.

## 17. Operating-Point Drift vs Ranking Degradation

UNDETERMINED. Runtime equivalence is an engineering verification, not evidence
of distribution-shift robustness, calibration drift or discrimination change.

## 18. Limitations

The binding blocker is source governance, not model access or CPU inference.
Existing summaries explicitly exclude the needed external attack sources from
evaluation; missing detailed rights/contamination evidence prevents resolving
these statuses from current accepted evidence. Gate A passes but does not grant
new source roles. An empty corpus or fixture cannot substitute for real R1.

Gate A regression: 192 passed, zero failures/errors/skips. Accepted baseline:
96 hash checks PASS; final release: 118 hash checks/reconstruction PASS.
Blocker/regression verification is recorded separately in
`artifacts/research_protocol/r1/r1_gate_b_test_receipt_v1.json`.
Latest combined regression: **201 passed**, zero failures/errors/skips, 90.55 s:
9 blocker/preservation tests plus the same 192 Gate-A regression tests. This
rechecks the committed Gate-A proof; it does not repeat authoritative LM scoring.
The 30 requested experiment acceptance tests cannot certify an unrun experiment;
only applicable runtime, stop-state and preservation checks were run.

## 19. Research Interpretation

**No R1 scientific finding is supported.** The available evidence establishes
that frozen D_S live inference can be reconstructed faithfully, while the
required R1 population cannot yet pass source clearance.

Required resolution: restore/review authoritative rights, privacy, pinned
revision, label and lineage evidence; record evaluation-only clearance for at
least two meaningful external attack sources/families and shifted benign data;
explicitly resolve any reserved/pristine source boundary. Then resume Gate B,
audit against all development partitions, freeze deterministic membership and
commit before scoring. Do not waive quarantine or change the frozen stack.

## 20. No Post-R1 Adaptation

No post-R1 adaptation occurred. No R1 scoring occurred. Detector parameters,
features, model revisions, calibrators, operational thresholds, metrics,
bootstrap definitions, prediction/regime semantics, R0, protocol lock and release
artifacts remain unchanged. No source payload was downloaded or modified; no raw
data or model cache is committed. R2/R3, verifier/router, protected/final
evaluation and Cycle-2 work were not started.

Final verdict: **BLOCKED**. No Gate-B freeze, Gate-C scoring or Gate-D analysis
commit is claimed; the blocker report is a separate documentation commit.
