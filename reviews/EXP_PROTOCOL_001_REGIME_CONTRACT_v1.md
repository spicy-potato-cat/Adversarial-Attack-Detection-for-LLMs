# EXP-PROTOCOL-001 Phase 4: Regime, Provenance And Lineage Contract

Status: **PASS**. Branch `exp/protocol-001`. Start local/fetched remote commit:
`18eda71db440613f1e084fee592a69d95e16f644`.
Cycle-1 authority: `dc6dd3041643fb70ad5b128d32c246f8763a8044`.
This phase implements metadata contracts only. Phase 5 is not started.

## Regime And Partition

`regime_manifest_v1` contains immutable `regime_sample_v1` records. One schema
supports `R0_NON_ADAPTIVE`, `R1_SHIFTED_UNSEEN`,
`R2_SINGLE_DETECTOR_TARGETED`, and `R3_ENSEMBLE_TARGETED`.
R4 is not introduced or operationalized.

Partition is a separate dimension: `BASE_TRAIN`, `CALIBRATION`, `VALIDATION`,
`META_TRAIN`, `INTERNAL_TEST`, `FROZEN_EXTERNAL`, `FINAL_TEST`,
`ATTACK_GENERATION`, `QUARANTINE`. Existing development governance retains
`BASE_TRAIN`, `CALIBRATION`, and `VALIDATION` unchanged. The remaining values
are schema support, not new actual partitions or permission to use data.
All 54 partition/regime-fixture combinations pass contract validation.

R0 represents ordinary non-adaptive evaluation; R1 represents shifted/unseen
sources without defining any particular unseen-source selection. Both require
null targets. R2 requires exactly one manifest-bound primary alias: `D_S`,
`D_M-B`, or `D_G`. R3 requires `ALL`. Comparator `D_M-A`, free-text synonyms,
null targeted-regime targets and incorrect ALL/single-target combinations fail.
Aliases are checked against the unchanged Phase-2 primary detector order.

## Canonical Fields

Manifest fields include version/protocol, deterministic experiment ID,
dataset identity/revision, dataset-source identity/revision, declared constituent
sources, partition, regime, metadata creation time, manifest hash,
sample/attack/benign counts, detector-set ID/hash, prediction-schema version/hash,
lifecycle status, evidence kind, notes, hash-bearing evidence references,
external-parent metadata and sample records.

Sample fields include record version, sample/dataset IDs and revisions,
partition/regime, source/native ID, truth label and adversarial flag,
attack family and provenance, target, attack method/revision, generator
type/model/system/revision, generated-descendant flag, generation-evaluation
state, parent/lineage IDs and provenance/justification, success definition,
success and validity flags, metadata creation time, source provenance status,
and nullable accepted outer-fold membership.

Types are strict, extra fields are forbidden, labels are integer 0/1 (not
booleans or strings), flags are booleans, counts are non-negative integers,
and SHA-256 values have fixed lowercase hexadecimal format. Timestamps are
validated UTC calendar timestamps with second precision. Required nullable
fields serialize explicitly as null. No prompt or detector-prediction fields
exist in the regime schemas.

Python validates arithmetic counts, unique sample IDs, canonical ordering,
dataset/source membership, graph relationships, valid timestamps, experiment ID
and self-hash. Exported JSON Schema enforces structural and expressible local
conditional requirements, including targets, generator fields and outcome
requirements. JSON Schema alone cannot verify hashes, cross-row relationships
or count arithmetic. Use `FrozenRegimeContracts.validate_manifest` for the
complete contract and authoritative input binding.

## Lineage And Parents

`sample_id` identifies one concrete evaluation item. `parent_sample_id` is
its immediate source item. `lineage_id` groups variants/descendants under the
same underlying source lineage, independently of sample ID or detector output.
Generated descendants require parent and lineage IDs, a generator type and
`DERIVED_FROM_PARENT` provenance. Multiple children may share one parent and
lineage, with distinct sample IDs.

Parent references resolve either to a sample in the manifest or to declared
external-parent metadata. External parents include source identity and an
evidence role/locator; that role must reference a SHA-bearing evidence entry.
Unresolved parents, inconsistent parent/child lineage, self-parenting, cycles,
duplicate/conflicting parent IDs and unused external parents are rejected.
An external-parent reference is a documented graph boundary, not a fabricated
claim that all upstream ancestry was reconstructed. References do not grant
dataset acquisition or licensing permission.

Lineage statuses: `SOURCE_PROVIDED`, `DERIVED_FROM_PARENT`,
`CANONICAL_DUPLICATE_GROUP`, `SINGLETON_FALLBACK`, `UNKNOWN`.
Unknown lineage requires a null ID. Singleton fallback requires an explicit
scientific justification, is unavailable for targeted regimes, and cannot
share its lineage with another sample. No singleton fallback is assigned to
real R0 records. Canonical duplicate groups remain exact-normalization groups,
not proof of semantic or documentary independence. No bootstrap is implemented.

## Attack And Generator Provenance

Attack family is source/protocol/accepted-metadata supported or `UNKNOWN`;
inapplicable families are null. No category is inferred from prompt content
or detector behavior. Attack methods and revisions form a required pair;
targeted regimes require both.

Generator types support `MODEL`, `RULE_BASED`, `HUMAN`, `DATASET_SOURCE`,
`OTHER`, or null where inapplicable. Model generation requires model and
revision, with no conflicting system field. Rule/other systems require
system identity and revision. Human/source provenance can be recorded without
inventing a model. Missing generator identity is not silently fabricated.

`valid_attack_attempt` records whether predeclared validity criteria were met;
it is neither the sample truth label nor an evasion result. `attack_success`
records a completed outcome under a versioned `attack_success_definition`
reference. Definition IDs must end in `_V<positive integer>`; no global success
definition is frozen. Targeted records require validity and a definition.
Completed generation evaluation requires explicit validity and success booleans;
pending evaluation has null success. Success cannot be true for an invalid
attempt. Valid-but-unsuccessful and invalid-unsuccessful attempts are distinct.
Synthetic `FIXTURE_ONLY_SUCCESS_V1` does not authorize real attack evaluation.
No ETR, TargetEvasionRate or other metric is calculated.

## Identity, Hashing And Immutability

Experiment ID is `EXP-Rn-<full SHA-256>` of canonical manifest identity content.
Identity excludes only experiment ID, self-hash, lifecycle status, notes,
manifest creation time and sample metadata creation times. It includes dataset
revisions, partition, regime, membership, lineage, attack-method/generator
revisions, evidence hashes, protocol version and the bound detector/prediction
contracts. Wall-clock time alone cannot determine experiment identity.

Canonical hashing uses sorted keys, compact JSON separators, UTF-8,
`ensure_ascii=true`, explicit nulls, integer counts and `allow_nan=false`, with
no trailing newline. Samples sort by sample ID, sources by dataset/revision,
evidence by role and external parents by sample ID. Notes have intentional
sequence order. `manifest_hash` excludes only its own field. The stored
reviewable JSON uses two-space indentation and one LF; its physical file hash
is separate from the embedded canonical content hash.

Lifecycle values: `DRAFT`, `FROZEN`, `COMPLETED`, `INVALID`, `ARCHIVED`.
Models and nested sequences are immutable. Normal assignment is rejected;
`model_copy(update=...)` on a frozen manifest is rejected; other updates are
revalidated rather than bypassing identity/hash checks. A changed identity
requires construction of a new validated revision. Unsafe Pydantic construction
is not an approved API. Artifact freeze preflights every output and refuses to
overwrite differing bytes.

## Prediction Join

Join key is `sample_id`, with unique `(sample_id, detector_id)` pairs.
Prediction identities are validated through Phase-3 adapters. Only the three
frozen primaries are accepted; labels must agree where a prediction has truth.
Full detector/sample coverage is required by default; an explicit partial
validation mode is available without manufacturing missing predictions.
Non-OK predictions remain failed results with null scores/votes.
Regime metadata is not copied into detector predictions. No metrics are added.

Fold-local historical OOF CSVs are not imported through the full-model adapter
or assigned final-model hashes. Their future importer remains a separately
qualified integration task. The Phase-3 D_S live-binding limitation is unchanged.

## R0 Representation

Created `artifacts/research_protocol/r0/r0_regime_manifest_v1.json` using
accepted membership/fold metadata only: **1,135 rows, 183 attack, 952 benign**.
Membership SHA remains
`9cdd5ecdd80f9ac3c8f05db63742721f4537ca2b64a2fe48f6c2b424b57483a6`;
fold SHA remains
`19dc0153cc257cc2331782d6dd61b7bb9fb8cb0ed88d3e782b69d5ba05c4bb8d`.

Authority is the accepted Cycle-1 alignment JSON, byte-verified against Git
commit `dc6dd3041643fb70ad5b128d32c246f8763a8044`. Its input hashes authenticate
the local governance files, folds and policies, including intentionally ignored
governance metadata. These source files were neither modified nor added to Git.
Record IDs, labels, source IDs/revisions, native IDs, N1 lineage IDs and folds
are preserved; sample identities match the fold inventory exactly.

The aggregate dataset identifies the development fixture; constituent records
retain `DS-TXT-017` / `DS-TXT-018` source identities. Source provenance remains
`PARTIAL`. Missing attack-method/generator/success fields remain null.
`COMPLETED` describes historical R0, not a new model run. `created_at` dates
this metadata representation, not original samples or historical execution.
No prompts, normalized payloads or detector prediction tables were parsed.
Existing frozen files may be read as bytes for preservation hashes, never scored.

## Verification And Artifacts

**279 tests passed; 0 failed, 0 skipped:** 165 Phase-4 tests plus 114 Phase-2/3
tests. Receipt: `artifacts/research_protocol/phase4_tests_v1.xml`.
All six synthetic regimes pass; R2 fixtures contain three shared-lineage
descendants and hash-referenced synthetic parent metadata. Audit-gated artifact
construction forbids model-library imports and raw/normalized prompt access.

Phase-4 inventory binds **14 files**: 11 schemas/contracts/metadata artifacts
plus three code/test files. SHA-256:

- Manifest schema: `96b3139f49f81bb1b8af284f70754b8bd64e8d060edb443ea88f14fe851acdbc`.
- Sample schema: `368b767eefe3346d5b75499ad3bb6c87682fc2736759e0aae859d6ec9ababd69`.
- Regime contract: `716631bec5e7bbe562acd375c90260f5bf11f92cffb6c6d63a7639908408c149`.
- Hash inventory: `3e7495c8daf62ce018d3072a255bd550d54319af4131a36b1db6a465c9b2e679`.
- R0 file: `4a7b694d72aa94f48cd31c81b107aef9b65fc31efdcaf11cfb88e7e4942cd45c`.

Phase-2 manifest remains
`2da5aa92cb14ac19cd49fa7150e7a4ef79b59e1e5fb1aa8ba4148456da618f31`.
Phase-3 prediction schema remains
`f61cc717b6118e288201ee8525b41e6806a642d665c42c0d1b9d6d1bcde2e484`.
Phase-3 adapter manifest remains
`43bdae201bc7faf23ea8a2ecadda69e28eeb4d775d0f12a6c005a894d958b9b3`.
All Phase-2 165 evidence hashes, including 96 baseline preservation checks,
and Phase-3 six artifact checks pass. Detector/model/calibrator diffs are empty.

Read-only verification:
`.local-python/python.exe -m detection_service.research_protocol.regime_contract --mode check`.
No model execution, training, recalibration, R0 scoring/results recalculation,
threshold selection, metrics, bootstrap, dataset acquisition, attack generation,
real R1/R2/R3 data, verifier/router, Cycle-2 or Phase-5 work occurred.
Commit/push identifiers are returned after synchronization and do not rewrite
historical model/run provenance.

**PHASE_4_COMPLETE_READY_FOR_PHASE_5**. Phase 5 is not started.

THE SINGLE MOST IMPORTANT REGIME-CONTRACT GUARANTEE:
Partition and threat regime remain independent, while every sample retains
explicit source, target, lineage and attack-outcome provenance without
inventing data, independence or detector decisions.
