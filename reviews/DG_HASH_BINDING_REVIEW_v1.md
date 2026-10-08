# D_G hash-binding review v1

Verdict: **DG_METADATA_ONLY_LINE_ENDING_DISCREPANCY_RESOLVED**.

Historical environment.json file-byte binding was computed over CRLF serialization; accepted Git blob stores LF. LF-to-CRLF conversion exactly reproduces the recorded hash, with identical parsed JSON.

Historical hash: `e23929244cd567f6d1c236fe050a7b894bbfe12a7ae4c51f47d7aa2bbe739e2d`. Git LF blob hash: `9269b0b2ec53a92edec118937c5f07ceb6ed2a2ebdb9184c85da8ab79d453706`.
Parsed JSON is identical. Reconstruction was in memory only; no accepted artifact changed.

Scientific impact: NONE for this discrepancy. Exact model revision, remote weight LFS hash,
tokenizer binding, preprocessing and frozen threshold are unchanged. Accepted R1/R2-DMB
predictions directly bind the same model hash/revision. R0 uses preserved source/import
bindings rather than those columns; its schema is retained. No scores were recomputed.
D_G authenticated config/tokenizer access at the exact revision: ACCESS_CONFIRMED.

Raw-file integrity remains byte-sensitive. Fresh-clone restoration must recreate the bound
CRLF environment bytes in an isolated authorized runtime or introduce an explicitly approved
additive representation binding; do not change old hashes to make a check pass.

| Artifact | Field | Recorded value | Expected value | Hashed meaning | Classification |
|---|---|---|---|---|---|
| artifacts/models/dg_v1/environment.json | Git blob file SHA256 | 9269b0b2ec53a92edec118937c5f07ceb6ed2a2ebdb9184c85da8ab79d453706 | e23929244cd567f6d1c236fe050a7b894bbfe12a7ae4c51f47d7aa2bbe739e2d | Exact environment JSON bytes with LF | line-ending mismatch; environment-only |
| artifacts/models/dg_v1/environment.json | Reconstructed historical CRLF file SHA256 | e23929244cd567f6d1c236fe050a7b894bbfe12a7ae4c51f47d7aa2bbe739e2d | e23929244cd567f6d1c236fe050a7b894bbfe12a7ae4c51f47d7aa2bbe739e2d | LF bytes replaced by CRLF only | MATCH |
| artifacts/research_protocol/detector_set_manifest_v1.json | detectors/D_G/model_name | meta-llama/Llama-Prompt-Guard-2-22M | meta-llama/Llama-Prompt-Guard-2-22M | Repository identity | MATCH |
| artifacts/research_protocol/detector_set_manifest_v1.json | detectors/D_G/model_revision | 11614a155199674a0a95e6602d6ab0417b790ed0 | 11614a155199674a0a95e6602d6ab0417b790ed0 | Immutable repository revision | MATCH |
| artifacts/research_protocol/detector_set_manifest_v1.json | detectors/D_G/tokenizer_revision | 11614a155199674a0a95e6602d6ab0417b790ed0 | 11614a155199674a0a95e6602d6ab0417b790ed0 | Immutable repository revision | MATCH |
| artifacts/research_protocol/detector_set_manifest_v1.json | detectors/D_G/model_hash | 5120e30bcd536ce285345d9ec104bea6bd6e8f94365b99a340c764f417ea5fa1 | 5120e30bcd536ce285345d9ec104bea6bd6e8f94365b99a340c764f417ea5fa1 | Exact safetensors bytes SHA256 | MATCH |
| artifacts/research_protocol/detector_set_manifest_v1.json | accepted_evidence_locations/artifacts/models/dg_v1/environment.json/sha256 | e23929244cd567f6d1c236fe050a7b894bbfe12a7ae4c51f47d7aa2bbe739e2d | e23929244cd567f6d1c236fe050a7b894bbfe12a7ae4c51f47d7aa2bbe739e2d | Historical exact CRLF environment file SHA256 | historical CRLF file-byte binding |
| artifacts/research_protocol/detector_set_manifest_v1.json | accepted_evidence_locations/detection_service/.model-cache/dg_v1/snapshot-11614a155199674a0a95e6602d6ab0417b790ed0/model.safetensors/sha256 | 5120e30bcd536ce285345d9ec104bea6bd6e8f94365b99a340c764f417ea5fa1 | 5120e30bcd536ce285345d9ec104bea6bd6e8f94365b99a340c764f417ea5fa1 | Exact frozen safetensors weight bytes SHA256 | MATCH |
| artifacts/research_protocol/detector_set_manifest_v1.json | detectors/2/model_hash | 5120e30bcd536ce285345d9ec104bea6bd6e8f94365b99a340c764f417ea5fa1 | 5120e30bcd536ce285345d9ec104bea6bd6e8f94365b99a340c764f417ea5fa1 | Exact frozen safetensors weight bytes SHA256 | MATCH |
| artifacts/research_protocol/detector_set_manifest_v1.json | detectors/2/model_name | meta-llama/Llama-Prompt-Guard-2-22M | meta-llama/Llama-Prompt-Guard-2-22M | Model repository identity | MATCH |
| artifacts/research_protocol/detector_set_manifest_v1.json | detectors/2/model_revision | 11614a155199674a0a95e6602d6ab0417b790ed0 | 11614a155199674a0a95e6602d6ab0417b790ed0 | Immutable model/tokenizer repository commit, not a file hash | MATCH |
| artifacts/research_protocol/detector_set_manifest_v1.json | detectors/2/snapshot_file_sha256/model.safetensors | 5120e30bcd536ce285345d9ec104bea6bd6e8f94365b99a340c764f417ea5fa1 | 5120e30bcd536ce285345d9ec104bea6bd6e8f94365b99a340c764f417ea5fa1 | Exact frozen safetensors weight bytes SHA256 | MATCH |
| artifacts/research_protocol/detector_set_manifest_v1.json | detectors/2/tokenizer_name | meta-llama/Llama-Prompt-Guard-2-22M | meta-llama/Llama-Prompt-Guard-2-22M | Model repository identity | MATCH |
| artifacts/research_protocol/detector_set_manifest_v1.json | detectors/2/tokenizer_revision | 11614a155199674a0a95e6602d6ab0417b790ed0 | 11614a155199674a0a95e6602d6ab0417b790ed0 | Immutable model/tokenizer repository commit, not a file hash | MATCH |
| artifacts/models/dg_v1/freeze_metadata.json | model_id | meta-llama/Llama-Prompt-Guard-2-22M | meta-llama/Llama-Prompt-Guard-2-22M | Model repository identity | MATCH |
| artifacts/models/dg_v1/freeze_metadata.json | revision | 11614a155199674a0a95e6602d6ab0417b790ed0 | 11614a155199674a0a95e6602d6ab0417b790ed0 | Immutable model/tokenizer repository commit, not a file hash | MATCH |
| artifacts/models/dg_v1/freeze_metadata.json | tokenizer_revision | 11614a155199674a0a95e6602d6ab0417b790ed0 | 11614a155199674a0a95e6602d6ab0417b790ed0 | Immutable model/tokenizer repository commit, not a file hash | MATCH |
| artifacts/models/dg_v1/freeze_metadata.json | file_sha256/model.safetensors | 5120e30bcd536ce285345d9ec104bea6bd6e8f94365b99a340c764f417ea5fa1 | 5120e30bcd536ce285345d9ec104bea6bd6e8f94365b99a340c764f417ea5fa1 | Exact frozen safetensors weight bytes SHA256 | MATCH |
| artifacts/models/dg_v1/freeze_metadata.json | long_input_policy/model_id | meta-llama/Llama-Prompt-Guard-2-22M | meta-llama/Llama-Prompt-Guard-2-22M | Model repository identity | MATCH |
| artifacts/models/dg_v1/freeze_metadata.json | long_input_policy/revision | 11614a155199674a0a95e6602d6ab0417b790ed0 | 11614a155199674a0a95e6602d6ab0417b790ed0 | Immutable model/tokenizer repository commit, not a file hash | MATCH |
| artifacts/models/dg_v1/freeze_metadata.json | long_input_policy/tokenizer_revision | 11614a155199674a0a95e6602d6ab0417b790ed0 | 11614a155199674a0a95e6602d6ab0417b790ed0 | Immutable model/tokenizer repository commit, not a file hash | MATCH |
| artifacts/models/dg_v1/model_config.json | model_id | meta-llama/Llama-Prompt-Guard-2-22M | meta-llama/Llama-Prompt-Guard-2-22M | Model repository identity | MATCH |
| artifacts/models/dg_v1/model_config.json | revision | 11614a155199674a0a95e6602d6ab0417b790ed0 | 11614a155199674a0a95e6602d6ab0417b790ed0 | Immutable model/tokenizer repository commit, not a file hash | MATCH |
| artifacts/models/dg_v1/model_config.json | tokenizer_revision | 11614a155199674a0a95e6602d6ab0417b790ed0 | 11614a155199674a0a95e6602d6ab0417b790ed0 | Immutable model/tokenizer repository commit, not a file hash | MATCH |
| artifacts/research_protocol/protocol_patches/exp_protocol_001_patch_001.json | sha256/artifacts/models/dg_v1/environment.json | e23929244cd567f6d1c236fe050a7b894bbfe12a7ae4c51f47d7aa2bbe739e2d | e23929244cd567f6d1c236fe050a7b894bbfe12a7ae4c51f47d7aa2bbe739e2d | Historical exact CRLF environment file SHA256 | historical CRLF file-byte binding |
| artifacts/research_protocol/protocol_patches/exp_protocol_001_patch_001.json | sha256/artifacts/models/dg_v1/environment.json | e23929244cd567f6d1c236fe050a7b894bbfe12a7ae4c51f47d7aa2bbe739e2d | e23929244cd567f6d1c236fe050a7b894bbfe12a7ae4c51f47d7aa2bbe739e2d | Historical exact CRLF environment file SHA256 | historical CRLF file-byte binding |
| artifacts/research_protocol/r0/r0_reproduction_import_manifest_v1.json | historical_models/dg_v1/revision | 11614a155199674a0a95e6602d6ab0417b790ed0 | 11614a155199674a0a95e6602d6ab0417b790ed0 | Immutable model/tokenizer repository commit, not a file hash | MATCH |
| artifacts/research_protocol/r2_dmb/r2_dmb_predeclaration_v1.json | preservation_sha256/artifacts/models/dg_v1/environment.json | e23929244cd567f6d1c236fe050a7b894bbfe12a7ae4c51f47d7aa2bbe739e2d | e23929244cd567f6d1c236fe050a7b894bbfe12a7ae4c51f47d7aa2bbe739e2d | Historical exact CRLF environment file SHA256 | historical CRLF file-byte binding |
| artifacts/research_protocol/r2_dmb/r2_dmb_predeclaration_v1.json | preservation_sha256/artifacts/models/dg_v1/environment.json | e23929244cd567f6d1c236fe050a7b894bbfe12a7ae4c51f47d7aa2bbe739e2d | e23929244cd567f6d1c236fe050a7b894bbfe12a7ae4c51f47d7aa2bbe739e2d | Historical exact CRLF environment file SHA256 | historical CRLF file-byte binding |
| artifacts/research_protocol/r0/r0_operational_predictions_v1.csv | source_artifact_path | ['artifacts/guard_v1/development/completion_v3/dg_v1_base_train_predictions.csv'] | ['artifacts/guard_v1/development/completion_v3/dg_v1_base_train_predictions.csv'] | Prediction provenance field; no score recomputation | MATCH |
| artifacts/research_protocol/r0/r0_operational_predictions_v1.csv | source_artifact_sha | ['2589d5c8f9da40be4104c2964966f7b1790b2370255bd87515e63760f2a624ef'] | ['2589d5c8f9da40be4104c2964966f7b1790b2370255bd87515e63760f2a624ef'] | Prediction provenance field; no score recomputation | MATCH |
| artifacts/research_protocol/r0/r0_operational_predictions_v1.csv | import_manifest_sha | ['6efb88a756bc12558f2e7bdbba72854f8fb37aca6bfd73a30b20509d9b93983b'] | ['6efb88a756bc12558f2e7bdbba72854f8fb37aca6bfd73a30b20509d9b93983b'] | Prediction provenance field; no score recomputation | MATCH |
| artifacts/research_protocol/r0/r0_operational_predictions_v1.csv | model_evidence_kind | ['FROZEN_DEVELOPMENT_INFERENCE'] | ['FROZEN_DEVELOPMENT_INFERENCE'] | Prediction provenance field; no score recomputation | MATCH |
| artifacts/research_protocol/r0/r0_operational_predictions_v1.csv | operational_threshold | ['0.21291141211986545'] | ['0.21291141211986545'] | Prediction provenance field; no score recomputation | MATCH |
| artifacts/research_protocol/r0/r0_operational_predictions_v1.csv | operating_policy_manifest_sha | ['06fa4548a62ae0e0968f9d93339910f8841a0f366b5346b0892a2be6904fb0cc'] | ['06fa4548a62ae0e0968f9d93339910f8841a0f366b5346b0892a2be6904fb0cc'] | Prediction provenance field; no score recomputation | MATCH |
| artifacts/research_protocol/r1/r1_predictions_v1.csv | model_revision | ['11614a155199674a0a95e6602d6ab0417b790ed0'] | ['11614a155199674a0a95e6602d6ab0417b790ed0'] | Prediction provenance field; no score recomputation | MATCH |
| artifacts/research_protocol/r1/r1_predictions_v1.csv | model_hash | ['5120e30bcd536ce285345d9ec104bea6bd6e8f94365b99a340c764f417ea5fa1'] | ['5120e30bcd536ce285345d9ec104bea6bd6e8f94365b99a340c764f417ea5fa1'] | Prediction provenance field; no score recomputation | MATCH |
| artifacts/research_protocol/r1/r1_predictions_v1.csv | score_direction | ['HIGHER_IS_MORE_ADVERSARIAL'] | ['HIGHER_IS_MORE_ADVERSARIAL'] | Prediction provenance field; no score recomputation | MATCH |
| artifacts/research_protocol/r1/r1_predictions_v1.csv | operational_threshold | ['0.21291141211986545'] | ['0.21291141211986545'] | Prediction provenance field; no score recomputation | MATCH |
| artifacts/research_protocol/r1/r1_predictions_v1.csv | operating_policy_manifest_sha | ['06fa4548a62ae0e0968f9d93339910f8841a0f366b5346b0892a2be6904fb0cc'] | ['06fa4548a62ae0e0968f9d93339910f8841a0f366b5346b0892a2be6904fb0cc'] | Prediction provenance field; no score recomputation | MATCH |
| artifacts/research_protocol/r2_dmb/r2_dmb_predictions_v1.csv | model_revision | ['11614a155199674a0a95e6602d6ab0417b790ed0'] | ['11614a155199674a0a95e6602d6ab0417b790ed0'] | Prediction provenance field; no score recomputation | MATCH |
| artifacts/research_protocol/r2_dmb/r2_dmb_predictions_v1.csv | model_hash | ['5120e30bcd536ce285345d9ec104bea6bd6e8f94365b99a340c764f417ea5fa1'] | ['5120e30bcd536ce285345d9ec104bea6bd6e8f94365b99a340c764f417ea5fa1'] | Prediction provenance field; no score recomputation | MATCH |
| artifacts/research_protocol/r2_dmb/r2_dmb_predictions_v1.csv | score_direction | ['HIGHER_IS_MORE_ADVERSARIAL'] | ['HIGHER_IS_MORE_ADVERSARIAL'] | Prediction provenance field; no score recomputation | MATCH |
| artifacts/research_protocol/r2_dmb/r2_dmb_predictions_v1.csv | operational_threshold | ['0.21291141211986545'] | ['0.21291141211986545'] | Prediction provenance field; no score recomputation | MATCH |
| artifacts/research_protocol/r2_dmb/r2_dmb_predictions_v1.csv | operating_policy_manifest_sha | ['06fa4548a62ae0e0968f9d93339910f8841a0f366b5346b0892a2be6904fb0cc'] | ['06fa4548a62ae0e0968f9d93339910f8841a0f366b5346b0892a2be6904fb0cc'] | Prediction provenance field; no score recomputation | MATCH |
