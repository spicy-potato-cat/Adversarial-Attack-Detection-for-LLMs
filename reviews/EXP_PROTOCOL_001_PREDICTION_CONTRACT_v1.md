# EXP-PROTOCOL-001 Phase 3: Canonical Prediction Contract

Status: **PASS**. Branch `exp/protocol-001`; start commit
`2e976f2c444001b12b6aa1196e46dde60ce8f0bd`. Representation only; no detector
implementation, model, calibrator, input policy, native decision, or operating
point was changed. No native model execution, download, dataset scoring,
R0 rescoring, R1/R2/R3, Cycle-2 work, or Phase-4 work occurred.

## Canonical Record

`PredictionRecord` is a strict, immutable Pydantic v2 model. The exported
Draft-2020-12 schema is `prediction_v1`, with `prediction_metadata_v1`.
All 25 top-level fields are present in serialized records:

- Identity: `schema_version`, `sample_id`, `truth_label`, `detector_id`,
  `detector_role`, `model_revision`, `model_hash`.
- Scores: `raw_score`, `raw_score_name`, `score_direction`, `calibrated_score`,
  `calibrator_id`.
- Native decision: `native_binary_prediction`, `native_decision_rule_id`.
- Operational decision: `operational_threshold`, `operational_threshold_id`,
  `operational_binary_prediction`.
- Status: `status`, `error_code`.
- Accounting: `latency_ms`, `input_tokens`, `tokens_analyzed`, `truncated`.
- Provenance: `metadata_version`, `metadata`.

Binary values are strict integers 0/1, not booleans or strings. A null truth label
requires explicitly declared unlabeled inference. Scores are finite numeric
probabilities in [0,1]; NaN, infinity, strings and booleans are rejected. Extra
fields are forbidden, including inside the typed provenance metadata. Revision
and SHA formats are validated. Native model identity and calibrator references
receive manifest-bound adapter validation in addition to structural validation.
Use `DetectorAdapter.validate_prediction_record` for that full binding check;
the standalone Python record model does not by itself authenticate model files.
The exported schema also constrains primary IDs, roles, model hashes/revisions,
native rule IDs and successful-result calibrator IDs from the Phase-2 manifest.

## Status And Decision Separation

Statuses: `OK`, `INVALID_INPUT`, `ARTIFACT_MISMATCH`, `TOKENIZATION_ERROR`,
`INFERENCE_ERROR`, `CALIBRATION_ERROR`, `OUTPUT_VALIDATION_ERROR`, `UNAVAILABLE`,
`INSUFFICIENT_INPUT`.

`OK` requires a finite raw score, native decision, token counts and truncation
flag, with a null error code. Every non-OK record has null raw/calibrated scores,
applied calibrator ID and native decision, plus a non-null diagnostic error code.
A detector failure never becomes a benign or malicious prediction. Exceptions
are not copied into records: only constant codes and allowlisted class names are
used, never exception messages or raw prompt text. Invalid sample IDs/labels are
rejected before inference through a structured `AdapterContractError`.

Raw score, optional calibrated score, native/default decision and future
operational decision are separate fields. The three operational fields have
null-only types and reject any non-null value. No approved operating-point
manifest exists in this phase. A native 0.5 default is never turned into an
operational threshold or threshold ID.

## Adapter Mapping

One compositional `DetectorAdapter` implements `predict`, `adapt_fixture`,
`adapt_existing_output`, `validate_frozen_identity`, and
`validate_prediction_record`. `primary_adapters()` returns the manifest order
**D_S, D_M-B, D_G**. IDs, roles, score direction, weights/revisions, calibrators
and defaults are consumed from the unchanged, hash-pinned Phase-2 manifest.
D_M-A has no primary adapter and is rejected from this set.

| Detector | Raw score | Calibrated score | Preserved native decision | Rule ID | Binding |
|---|---|---|---|---|---|
| D_S `ds_v2` | Frozen B2+LR class-1 probability | Approved `ds_v2_cal_v1` output | Calibrated >= development default 0.5 | `ds_v2_default_vote_v1` | CONTRACT_ONLY fixtures; FROZEN_EVIDENCE reader; live unavailable |
| D_M-B `dm_b_v1` | Frozen class-1 ATTACK softmax | Approved `dm_b_v1_cal_v1` output, independently retained | RAW >= development default 0.5 | `dm_b_v1_default_vote_v1` | Lazy LIVE binding and FROZEN_EVIDENCE reader; only fixture/mock tests executed |
| D_G `dg_v1` | Native maximum malicious-class chunk softmax | Null; no calibrator | Native emitted OR of class-1 chunk argmax; ties class 0 | `dg_v1_native_or_argmax_v1` | Lazy LIVE binding and FROZEN_EVIDENCE reader; only fixture/mock tests executed |

All scores use `HIGHER_IS_MORE_ADVERSARIAL`; no score inversion or normalization
is performed. The adapters copy native values and votes, not recompute
calibration or logits. D_S and D_M-B vote consistency is checked against the
manifest default and its correct input score; discrepancies become errors, not
repaired predictions. D_G's emitted vote is copied independently of its maximum
probability. At an exact .5 tie its native benign vote remains benign, while
`raw_score >= .5` would incorrectly vote attack. A rounded softmax value cannot
be used to reconstruct argmax on unrounded logits.

Missing required primary calibration is an error, not a raw-score fallback.
Guard calibration or altered chunk-policy metadata is rejected. The adapters
do not implement a different detector or alter any preprocessing.

## Frozen Versus Live Provenance

`adapt_fixture` marks records **SYNTHETIC_FIXTURE / CONTRACT_ONLY**, with null
latency. These engineering fixtures are not authoritative research predictions.
Synthetic raw/calibrated pairs test representation; they do not claim that the
approved calibrator actually produced those particular fixture probabilities.

`adapt_existing_output` reads a complete native JSON result at an explicit JSON
Pointer, verifies its accepted Phase-2 source checksum and detector-artifact
namespace, then records the source path/hash/locator. It does not trust arbitrary
caller-supplied historical scores or unqualified files. An evidence file from
another detector is rejected. No real historical output was imported in this
phase; the source-reader integration was verified with isolated synthetic JSON.

Fold-local R0 OOF predictions are **not** relabeled with final-model weights
hashes. This full-frozen-model adapter rejects those CSVs. Later R0 reproduction
must preserve its fold-specific provenance through an explicitly qualified
evidence importer; this phase does not build that regime machinery or rescore R0.

The D_S implementation remains in the accepted local archive/Git history, as
recorded in Phase 2. No code was copied, reconstructed, imported from the archive,
or substituted with `ds_v1`. A D_S live call returns `UNAVAILABLE` with null scores
and decisions. This is an explicit runtime-binding limitation, not a claim that
the three-model live stack is runnable now.

D_M-B's lazy loader calls the manifest implementation's `from_artifact` with
`require_calibration=True`. D_G's lazy loader calls its manifest implementation's
`from_artifact` with the verified workspace. Model loading is explicit, remains
offline in the existing frozen loaders, and was not executed here. Loader wiring
and live-result/error adaptation were tested through synthetic callables only.

## Token And Latency Accounting

- D_S input count is content tokens before the 4096 cap. Analyzed count is the
  native unique next-token targets: retained content minus the first unscored
  token. Thus a 4096-token prefix has 4095 scored targets. The first token still
  supplies causal context. This basis is explicitly recorded, not presented as
  interchangeable with classifier-token counts.
- D_M-B native counts include special tokens. Canonical content counts subtract
  the two boundary tokens derived statically from the hash-verified frozen
  tokenizer's RoBERTa postprocessor. The 256-token project budget therefore
  allows 254 analyzed content tokens; padding is excluded.
- D_G counts unique content tokens, not summed overlapping chunks. All content
  is covered by 510-token chunks, overlap 64, stride 446. Tail coverage and
  accounting are checked; no whole-input truncation is introduced.

`truncated` is true only when the frozen preprocessing discards content.
Unavailable coverage on non-OK calls remains null, not fabricated zero.
Live latency measures the wall-clock native `detect` call, excluding lazy model
initialization and adapter overhead. Imported latency is kept only if an accepted
detector-reported measurement exists; otherwise null. These different measurement
bases are explicit in metadata and should not be pooled as comparable timings.

## Tests And Preservation

**114 passed; 0 failures/errors/skips:** 74 Phase-3 tests plus 40 Phase-2 tests.
Receipt: `artifacts/research_protocol/phase3_tests_v1.xml`.
All 28 required test topics are covered, with additional strict-type, identity,
failure, source-checksum, cross-detector evidence, null-latency, OOF provenance,
loader-hook, diagnostic privacy, and special-token accounting checks.
An audit-gated subprocess verifies no project dataset access and no imports of
torch, transformers, sklearn or detector implementation modules during artifact
construction. Frozen detector/model/calibration diffs are empty. Phase-2 manifest
and validation code are unchanged; its 165 hash checks, including 96 baseline
preservation checks, still pass. No historical metrics were recomputed.

## Artifacts And Checksums

Prediction schema: `artifacts/research_protocol/schemas/prediction_schema_v1.json`
SHA: `f61cc717b6118e288201ee8525b41e6806a642d665c42c0d1b9d6d1bcde2e484`.

Adapter contract: `artifacts/research_protocol/adapter_contract_manifest_v1.json`
SHA: `43bdae201bc7faf23ea8a2ecadda69e28eeb4d775d0f12a6c005a894d958b9b3`.

Hash inventory: `artifacts/research_protocol/phase3_artifact_hashes_v1.json`
SHA: `b4576d12c4b0c37cd7f9e3fb424ef2b3d2456c27142f1c0ae314627d4ec735ae`.
It binds the schema, adapter contract and four implementation/test files.

Phase-2 manifest SHA remains
`2da5aa92cb14ac19cd49fa7150e7a4ef79b59e1e5fb1aa8ba4148456da618f31`.
Schema/contract files use deterministic UTF-8 JSON with sorted keys and a trailing
newline; prediction-record serialization uses compact sorted JSON without a
trailing newline. No NaN/Infinity is permitted.

Verification: `.local-python/python.exe -m detection_service.research_protocol.prediction_contract --mode check`.
No model execution is involved. Commit/push identifiers are returned after
synchronization and do not rewrite earlier model/run provenance.

**PHASE_3_COMPLETE_READY_FOR_PHASE_4**. Phase 4 has not started.

THE SINGLE MOST IMPORTANT CONTRACT GUARANTEE:
A detector's native decision is preserved independently of its scores, while
operational decisions remain null and every failed call remains a failure.
