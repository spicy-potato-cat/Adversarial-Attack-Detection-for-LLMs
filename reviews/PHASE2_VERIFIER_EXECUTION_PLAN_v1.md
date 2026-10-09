# Phase 2 verifier execution plan v1

Prepared at integration `71e3a5239cb24a3e59e99d271c6aa46841dbc084` using synthetic supplied outputs only. Authoritative verifier queries: 0.

Use the frozen candidate revisions and native policies in `verifier_phase2_execution_contract_v1.json`; no future failure tuning. V1 and V2 mappings are ready and may execute independently after the R3 freeze. V3 Yes/No adapter is ready; local runtime remains V3_NOT_FEASIBLE_CURRENT_MACHINE. A compatible external machine may later supply V3 records at the same revision and population hash. No hardware, package, CUDA, cache, quantization, or candidate changes are part of Phase 1.

1. Receive Track A's accepted R3 result handoff and committed freeze SHA. Validate every component hash through `CommittedR3Reader(root, phase2_authorized=True)` and `load_failure_population`; do not search live files or journals.
2. Require nested failure-population freeze receipt, unique IDs, inherited lineage/parent fields, attack truth, all-three benign base decisions, accepted R3/internal partition, and local text references. Record `frozen_at` before the actual first verifier query timestamp. Resolve UTF-8 local text only at authorized execution, with root containment and hashes checked.
3. If population size is zero, emit `VERIFIER_RECOVERY_UNDEFINED_EMPTY_FAILURE_POPULATION` with null recovery and intervals; make zero research queries and stop. Do not replace or broaden the population.
4. For each available candidate, retain all frozen IDs in the denominator. Map supplied native outputs using frozen rules; preserve errors, invalid output, input-limit status, truncation and coverage. Official recovery stays null for incomplete coverage. Record raw output, native-rule/tokenizer/model revision, runtime, population hash and first-query timestamp.
5. Produce seven named outputs covered by `verifier_result_schema_v1.json`. Include N, recovered count, Recovery, 95% CI, source/family support, named-subset catch overlap/unique catches, and unrecovered IDs. V1/V2 results are independent of V3 availability; comparisons are descriptive, and V1/V2 unique catches are explicitly relative to that subset.
6. Consume frozen lineage-clustered uncertainty with its generating provenance. Do not recalculate R3/base metrics or change the bootstrap protocol. Freeze result hashes and analysis commit, then hand results to synthesis.

Phase 1 tests validate all three supplied-output mappings, ties, errors, ID order, missing predictions, empty denominator, and result schemas. Existing synthetic adapters keep a model-loading stop line. Real model execution remains a Phase 2 operation after authorization and accepted handoff; no execution is performed here.
