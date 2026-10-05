# TECH-STACK-001 Candidate Heterogeneous Base Stack Freeze v1

Status: **PASS**. Integration/reproducibility only; no performance evaluation.

## Source And Identity

Verified clean start: `8c8e53d985d931eaa30672d866aab47d01c28bd7`.
Branch: `tech/stack-001`. Startup artifact verification:128 matching hashes.
Stack ID: `research_stack_candidate_v2`; stack version2.
Status: `FROZEN_CANDIDATE_NOT_FINAL_SYSTEM`.
Canonical manifest SHA:
`dce1392430198894247ca318d6c2627f024ef403742d2a0779bb7b7606847110`.
File-byte SHA:
`4bd076dfc07717555034732b55a9a65c0bc531bb17beab58659b088254247dae`.

Source commit records the accepted detector basis, not a later evidence commit.
Exact stack checker/CLI/test source hashes are recorded in the manifest; freeze
was executed with those new implementation files pending in this workspace.
No source metadata from earlier model/calibration runs was rewritten.

## Deterministic Primary Stack

| Order | Role | Stack ID / Runtime ID | Version | Calibration |
|---|---|---|---|---|
| 1 | D_S | statistical / statistical_perplexity | ds_v2 | ds_v2_cal_v1 |
| 2 | D_M-B | semantic_finetuned / semantic_finetuned | dm_b_v1 | dm_b_v1_cal_v1 |
| 3 | D_G | guard_external / guard_external | dg_v1 | NONE |

D_M-A `dm_a_v1` remains frozen baseline/comparator only, explicitly excluded from
primary membership. ds_v1 also remains preserved; it is not this candidate D_S.

D_S: B2,26 features, schemaSHA:
`93d3892b158c35eccfadc27c879754db69ea5293782492ee5d4ff01a33bff983`.
ModelSHA: `c5e754dc8b6e88b7437e4b81016e8f8ec23d018607d4f4e78906212b2a561157`.
ReferenceSHA: `fd26774585223913d12b8c20556a8fc1a50fa5dea7a3a75068a7bb30efce76ec`.
CalibrationSHA: `964cea57d98673d2026fb2f0e9d5884aec61a653e726847e0fb6ccbf36e95f23`.
Reference LM/tokenizer: `distilbert/distilgpt2`, revision
`2290a62682d06624634c1f46a6ad5be0f47f38aa`; original4096 analysis cap and128/64
window policy preserved. References remain frozen BASE_TRAIN-only.

D_M-B upstream: `distilbert/distilroberta-base`, revision/tokenizer revision
`fb53ab8802853c8e4fbdbcd0529f21fc6f459b2b`.
Fine-tuned weightSHA:
`0bb192d2c468530479fa8ec0786f35d8bf5a8287e4ee401a953292d221736844`.
CalibrationSHA: `7af044ff8e0e29020450bffa93f92c973da4cc4a4888067d88938eefbb2566b9`.
All transformer/tokenizer/config hashes and the nine-file calibration/model
binding are recorded and verified. Right truncation at256 tokens is unchanged.

D_G: `meta-llama/Llama-Prompt-Guard-2-22M`, revision/tokenizer revision
`11614a155199674a0a95e6602d6ab0417b790ed0`.
WeightSHA: `5120e30bcd536ce285345d9ec104bea6bd6e8f94365b99a340c764f417ea5fa1`.
Freeze/config and all nine upstream snapshot files match their accepted hashes.
No project calibration.510 content-token chunks,64 overlap,512 model context,
native tokenizer and max-chunk score aggregation remain unchanged.

## Stack-Facing Contract

Fields: detector_id,detector_version,raw_score,calibrated_probability,
binary_prediction,latency_ms,metadata. Existing runtime contract is untouched.
Manifest explicitly aliases runtime statistical_perplexity to stack statistical,
and conceptual binary_prediction to runtime binary_vote. This is a documented
integration contract, not a new endpoint or runtime adapter.

All raw scores mean higher=more adversarial. D_S uses uncalibrated LR class1
probability; D_M-B uses uncalibrated softmax class1 ATTACK probability; D_G uses
temperature1 class1 softmax, max across native chunks. D_G calibrated probability
is null because no calibrator exists. Failure is a typed exception or explicit
non-success status; no replacement detector, refit or silent fallback is allowed.

Original request.content.text must be passed independently to each detector.
No detector consumes another's transformed input. Tokenization, normalization,
truncation/windowing and coverage remain detector-specific. No shared tokenizer.

Compatibility/default votes are explicitly labelled
`DEVELOPMENT_DEFAULT_NOT_FINAL_OPERATING_POINT` in the stack contract:
D_S calibrated_probability>=0.5; D_M-B raw_score>=0.5, unchanged by calibration;
D_G OR of native chunk argmax class1, preserving class0 tie behavior exactly.
Existing native metadata labels are preserved, not rewritten in detector code.

## Integrity And Scope

`python -m detection_service.scripts.freeze_research_stack --mode check` verifies
the saved package, expected identities/order, exact artifact/code hashes,
D_S schema, both calibrator/model bindings, D_G revision/native policy,
score/input semantics, unfrozen thresholds and comparator exclusion.
Missing, corrupt, swapped, drifted or path-escaping artifacts fail loudly.
JSON duplicate keys and non-finite values are rejected. Canonical SHA is over
UTF-8 JSON with sorted keys, compact separators, ensure_ascii=true and no newline.
Separate file-byte hashes bind the pretty-printed saved manifest.

Saved-package verification:129 artifact hashes plus three implementation hashes;
the129 include all96 original baseline hashes. No historical snapshot/checker
was modified or expanded. There is no claim that its exact96 namespace check
passes the previously added ds_v2 modules; this phase checks original bytes.

No Dataset/PHASE-3 payload, row table or embedding/feature array was opened.
Model weights were read for SHA-256 only, not deserialized. A separate isolated
audit observed144 unique permitted paths and no heavy model-runtime imports.
No prompts, datasets, training, calibration, threshold search, protected/E1-E10
evaluation, network download or live three-model smoke occurred.
Default service wiring remains untouched. No ensemble decision logic was built.

Final thresholds: **NOT FROZEN**. Ensemble policy: **NOT FROZEN**.
Verifier: **NOT SELECTED**. Routing: **NOT IMPLEMENTED**. D_S cycle2: **DEFERRED**.

The known D_S under16/long-benign limitations and D_M-B truncation policy remain.
This phase establishes identity/reproducibility, not performance, independence,
cross-detector complementarity, safety efficacy or deployment readiness.

Recommendation: **READY FOR DEVELOPMENT COMMON-MODE RESULTS INGESTION**.
Protected evaluation requires separate authorization.
