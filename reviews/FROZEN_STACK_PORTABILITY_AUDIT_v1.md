# Frozen-stack portability audit v1

Verdict: **LOCAL_ARTIFACTS_CRITICAL**. Static preparation only; no inference or restoration.

D_M-B fine-tuned weights are critical LOCAL_ONLY. An upstream base checkpoint cannot
replace these frozen project weights. No immutable hosted fine-tune is recorded.

D_S classifier, calibrator, feature references and archived code have exact hash-matching
blobs in accepted Git history at e6b6a2af2a78e2a31aae6d9377378993f678b073. They are deterministically
reconstructable without retraining. Their required archive destinations are ignored and
absent from a fresh Track B checkout. This audit does not restore them or change loaders.
Historic commit availability on a fresh remote clone still needs proof.

D_S reference LM and D_G weights/tokenizers have pinned upstream revisions and per-file
hashes. Remote identifiers do not prove current downloadability. D_G is gated.
Large weight files were inventoried by size/existence; no large-file rehash was performed.
Small explicitly bound runtime files were hashed read-only. See manifest for observed
hash status versus recorded expected hashes. No protected/final data was inspected.

Fresh-checkout source byte drift is listed explicitly below. Where the Git blob hash
matches the frozen hash and normalized line endings match, this is checkout line-ending
conversion, not scientific retraining. Exact-byte runtime integrity still fails until
an authorized isolated restoration supplies the frozen bytes. No expected hash was relaxed.
Any BINDING_EXPECTED_DIFFERS_FROM_BASE_BLOB entry needs separate provenance resolution;
do not assume line-ending conversion explains a frozen-hash versus Git-blob conflict.

## Required runtime inventory

| Artifact | Classification | Required runtime location | Hash check |
|---|---|---|---|
| artifacts/models/dg_v1/environment.json | GIT_TRACKED | artifacts/models/dg_v1/environment.json | MISMATCH |
| artifacts/models/dg_v1/freeze_metadata.json | GIT_TRACKED | artifacts/models/dg_v1/freeze_metadata.json | VERIFIED |
| artifacts/models/dg_v1/model_config.json | GIT_TRACKED | artifacts/models/dg_v1/model_config.json | VERIFIED |
| artifacts/models/dm_b_v1/calibration/calibration_config.json | GIT_TRACKED | artifacts/models/dm_b_v1/calibration/calibration_config.json | VERIFIED |
| artifacts/models/dm_b_v1/calibration/calibrator.json | GIT_TRACKED | artifacts/models/dm_b_v1/calibration/calibrator.json | VERIFIED |
| artifacts/models/dm_b_v1/integrity_manifest.json | GIT_TRACKED | artifacts/models/dm_b_v1/integrity_manifest.json | VERIFIED |
| artifacts/models/dm_b_v1/model_config.json | GIT_TRACKED | artifacts/models/dm_b_v1/model_config.json | VERIFIED |
| artifacts/models/dm_b_v1/transformer/config.json | GIT_TRACKED | artifacts/models/dm_b_v1/transformer/config.json | VERIFIED |
| artifacts/models/dm_b_v1/transformer/merges.txt | GIT_TRACKED | artifacts/models/dm_b_v1/transformer/merges.txt | VERIFIED |
| artifacts/models/dm_b_v1/transformer/model.safetensors | LOCAL_ONLY | artifacts/models/dm_b_v1/transformer/model.safetensors | RECORDED_NOT_REHASHED_LARGE_FILE |
| artifacts/models/dm_b_v1/transformer/special_tokens_map.json | GIT_TRACKED | artifacts/models/dm_b_v1/transformer/special_tokens_map.json | VERIFIED |
| artifacts/models/dm_b_v1/transformer/tokenizer.json | GIT_TRACKED | artifacts/models/dm_b_v1/transformer/tokenizer.json | VERIFIED |
| artifacts/models/dm_b_v1/transformer/tokenizer_config.json | GIT_TRACKED | artifacts/models/dm_b_v1/transformer/tokenizer_config.json | VERIFIED |
| artifacts/models/dm_b_v1/transformer/vocab.json | GIT_TRACKED | artifacts/models/dm_b_v1/transformer/vocab.json | VERIFIED |
| artifacts/research_protocol/detector_set_manifest_v1.json | GIT_TRACKED | artifacts/research_protocol/detector_set_manifest_v1.json | UNBOUND |
| artifacts/research_protocol/operating_points/predeclared_policy_v1.json | GIT_TRACKED | artifacts/research_protocol/operating_points/predeclared_policy_v1.json | UNBOUND |
| artifacts/research_protocol/operating_points/selected_thresholds_before_diagnostics_v1.json | GIT_TRACKED | artifacts/research_protocol/operating_points/selected_thresholds_before_diagnostics_v1.json | UNBOUND |
| artifacts/research_protocol/protocol_lock_manifest_v1.json | GIT_TRACKED | artifacts/research_protocol/protocol_lock_manifest_v1.json | UNBOUND |
| artifacts/research_protocol/protocol_patches/exp_protocol_001_patch_001.json | GIT_TRACKED | artifacts/research_protocol/protocol_patches/exp_protocol_001_patch_001.json | UNBOUND |
| artifacts/research_protocol/runtime/ds_v2_equivalence_evidence_v1.json | GIT_TRACKED | artifacts/research_protocol/runtime/ds_v2_equivalence_evidence_v1.json | UNBOUND |
| artifacts/research_protocol/runtime/ds_v2_runtime_binding_v1.json | GIT_TRACKED | artifacts/research_protocol/runtime/ds_v2_runtime_binding_v1.json | UNBOUND |
| artifacts/statistical_v2/calibration/completed_v1/ds_v2_calibration_integrity_v1.json | DETERMINISTICALLY_RECONSTRUCTABLE | detection_service/outputs/common003-preserved-stack/artifacts/statistical_v2/calibration/completed_v1/ds_v2_calibration_integrity_v1.json | VERIFIED |
| artifacts/statistical_v2/calibration/completed_v1/ds_v2_calibration_manifest_v1.json | DETERMINISTICALLY_RECONSTRUCTABLE | detection_service/outputs/common003-preserved-stack/artifacts/statistical_v2/calibration/completed_v1/ds_v2_calibration_manifest_v1.json | VERIFIED |
| artifacts/statistical_v2/final/ds_v2_feature_reference.json | DETERMINISTICALLY_RECONSTRUCTABLE | detection_service/outputs/common003-preserved-stack/artifacts/statistical_v2/final/ds_v2_feature_reference.json | VERIFIED |
| artifacts/statistical_v2/final/ds_v2_integrity_v1.json | DETERMINISTICALLY_RECONSTRUCTABLE | detection_service/outputs/common003-preserved-stack/artifacts/statistical_v2/final/ds_v2_integrity_v1.json | VERIFIED |
| artifacts/statistical_v2/final/ds_v2_model.json | DETERMINISTICALLY_RECONSTRUCTABLE | detection_service/outputs/common003-preserved-stack/artifacts/statistical_v2/final/ds_v2_model.json | VERIFIED |
| artifacts/statistical_v2/final/ds_v2_model_manifest_v1.json | DETERMINISTICALLY_RECONSTRUCTABLE | detection_service/outputs/common003-preserved-stack/artifacts/statistical_v2/final/ds_v2_model_manifest_v1.json | VERIFIED |
| artifacts/statistical_v2/final/ds_v2_training_metadata_v1.json | DETERMINISTICALLY_RECONSTRUCTABLE | detection_service/outputs/common003-preserved-stack/artifacts/statistical_v2/final/ds_v2_training_metadata_v1.json | VERIFIED |
| detection_service/.model-cache/dg_v1/snapshot-11614a155199674a0a95e6602d6ab0417b790ed0/LICENSE | REMOTE_IMMUTABLE | detection_service/.model-cache/dg_v1/snapshot-11614a155199674a0a95e6602d6ab0417b790ed0/LICENSE | VERIFIED |
| detection_service/.model-cache/dg_v1/snapshot-11614a155199674a0a95e6602d6ab0417b790ed0/MODEL_CARD.md | REMOTE_IMMUTABLE | detection_service/.model-cache/dg_v1/snapshot-11614a155199674a0a95e6602d6ab0417b790ed0/MODEL_CARD.md | VERIFIED |
| detection_service/.model-cache/dg_v1/snapshot-11614a155199674a0a95e6602d6ab0417b790ed0/README.md | REMOTE_IMMUTABLE | detection_service/.model-cache/dg_v1/snapshot-11614a155199674a0a95e6602d6ab0417b790ed0/README.md | VERIFIED |
| detection_service/.model-cache/dg_v1/snapshot-11614a155199674a0a95e6602d6ab0417b790ed0/USE_POLICY.md | REMOTE_IMMUTABLE | detection_service/.model-cache/dg_v1/snapshot-11614a155199674a0a95e6602d6ab0417b790ed0/USE_POLICY.md | VERIFIED |
| detection_service/.model-cache/dg_v1/snapshot-11614a155199674a0a95e6602d6ab0417b790ed0/config.json | REMOTE_IMMUTABLE | detection_service/.model-cache/dg_v1/snapshot-11614a155199674a0a95e6602d6ab0417b790ed0/config.json | VERIFIED |
| detection_service/.model-cache/dg_v1/snapshot-11614a155199674a0a95e6602d6ab0417b790ed0/model.safetensors | REMOTE_IMMUTABLE | detection_service/.model-cache/dg_v1/snapshot-11614a155199674a0a95e6602d6ab0417b790ed0/model.safetensors | RECORDED_NOT_REHASHED_LARGE_FILE |
| detection_service/.model-cache/dg_v1/snapshot-11614a155199674a0a95e6602d6ab0417b790ed0/special_tokens_map.json | REMOTE_IMMUTABLE | detection_service/.model-cache/dg_v1/snapshot-11614a155199674a0a95e6602d6ab0417b790ed0/special_tokens_map.json | VERIFIED |
| detection_service/.model-cache/dg_v1/snapshot-11614a155199674a0a95e6602d6ab0417b790ed0/tokenizer.json | REMOTE_IMMUTABLE | detection_service/.model-cache/dg_v1/snapshot-11614a155199674a0a95e6602d6ab0417b790ed0/tokenizer.json | VERIFIED |
| detection_service/.model-cache/dg_v1/snapshot-11614a155199674a0a95e6602d6ab0417b790ed0/tokenizer_config.json | REMOTE_IMMUTABLE | detection_service/.model-cache/dg_v1/snapshot-11614a155199674a0a95e6602d6ab0417b790ed0/tokenizer_config.json | VERIFIED |
| detection_service/.model-cache/ds_v1/snapshot-2290a62682d06624634c1f46a6ad5be0f47f38aa/config.json | REMOTE_IMMUTABLE | detection_service/.model-cache/ds_v1/snapshot-2290a62682d06624634c1f46a6ad5be0f47f38aa/config.json | VERIFIED |
| detection_service/.model-cache/ds_v1/snapshot-2290a62682d06624634c1f46a6ad5be0f47f38aa/generation_config.json | REMOTE_IMMUTABLE | detection_service/.model-cache/ds_v1/snapshot-2290a62682d06624634c1f46a6ad5be0f47f38aa/generation_config.json | VERIFIED |
| detection_service/.model-cache/ds_v1/snapshot-2290a62682d06624634c1f46a6ad5be0f47f38aa/merges.txt | REMOTE_IMMUTABLE | detection_service/.model-cache/ds_v1/snapshot-2290a62682d06624634c1f46a6ad5be0f47f38aa/merges.txt | VERIFIED |
| detection_service/.model-cache/ds_v1/snapshot-2290a62682d06624634c1f46a6ad5be0f47f38aa/model.safetensors | REMOTE_IMMUTABLE | detection_service/.model-cache/ds_v1/snapshot-2290a62682d06624634c1f46a6ad5be0f47f38aa/model.safetensors | RECORDED_NOT_REHASHED_LARGE_FILE |
| detection_service/.model-cache/ds_v1/snapshot-2290a62682d06624634c1f46a6ad5be0f47f38aa/tokenizer.json | REMOTE_IMMUTABLE | detection_service/.model-cache/ds_v1/snapshot-2290a62682d06624634c1f46a6ad5be0f47f38aa/tokenizer.json | VERIFIED |
| detection_service/.model-cache/ds_v1/snapshot-2290a62682d06624634c1f46a6ad5be0f47f38aa/tokenizer_config.json | REMOTE_IMMUTABLE | detection_service/.model-cache/ds_v1/snapshot-2290a62682d06624634c1f46a6ad5be0f47f38aa/tokenizer_config.json | VERIFIED |
| detection_service/.model-cache/ds_v1/snapshot-2290a62682d06624634c1f46a6ad5be0f47f38aa/vocab.json | REMOTE_IMMUTABLE | detection_service/.model-cache/ds_v1/snapshot-2290a62682d06624634c1f46a6ad5be0f47f38aa/vocab.json | VERIFIED |
| detection_service/analysis/statistical_feature_ablation.py | GIT_TRACKED | detection_service/analysis/statistical_feature_ablation.py | VERIFIED |
| detection_service/analysis/statistical_scorer_comparison.py | GIT_TRACKED | detection_service/analysis/statistical_scorer_comparison.py | VERIFIED |
| detection_service/app/contracts/detector_result.py | GIT_TRACKED | detection_service/app/contracts/detector_result.py | MISMATCH |
| detection_service/app/detectors/base.py | GIT_TRACKED | detection_service/app/detectors/base.py | MISMATCH |
| detection_service/app/detectors/guard/config.py | GIT_TRACKED | detection_service/app/detectors/guard/config.py | MISMATCH |
| detection_service/app/detectors/guard/detector.py | GIT_TRACKED | detection_service/app/detectors/guard/detector.py | MISMATCH |
| detection_service/app/detectors/guard/model.py | GIT_TRACKED | detection_service/app/detectors/guard/model.py | MISMATCH |
| detection_service/app/detectors/semantic/calibration.py | GIT_TRACKED | detection_service/app/detectors/semantic/calibration.py | MISMATCH |
| detection_service/app/detectors/semantic_finetuned/calibration.py | GIT_TRACKED | detection_service/app/detectors/semantic_finetuned/calibration.py | MISMATCH |
| detection_service/app/detectors/semantic_finetuned/config.py | GIT_TRACKED | detection_service/app/detectors/semantic_finetuned/config.py | MISMATCH |
| detection_service/app/detectors/semantic_finetuned/detector.py | GIT_TRACKED | detection_service/app/detectors/semantic_finetuned/detector.py | MISMATCH |
| detection_service/app/detectors/statistical/__init__.py | GIT_TRACKED | detection_service/app/detectors/statistical/__init__.py | MISMATCH |
| detection_service/app/detectors/statistical/config.py | GIT_TRACKED | detection_service/app/detectors/statistical/config.py | MISMATCH |
| detection_service/app/detectors/statistical/features.py | GIT_TRACKED | detection_service/app/detectors/statistical/features.py | MISMATCH |
| detection_service/app/detectors/statistical/perplexity_detector.py | GIT_TRACKED | detection_service/app/detectors/statistical/perplexity_detector.py | MISMATCH |
| detection_service/app/detectors/statistical/perplexity_engine.py | GIT_TRACKED | detection_service/app/detectors/statistical/perplexity_engine.py | MISMATCH |
| detection_service/app/detectors/statistical_risk/schema.py | GIT_TRACKED | detection_service/app/detectors/statistical_risk/schema.py | MISMATCH |
| detection_service/app/detectors/statistical_risk/scorer.py | GIT_TRACKED | detection_service/app/detectors/statistical_risk/scorer.py | MISMATCH |
| detection_service/app/detectors/statistical_v2/__init__.py | DETERMINISTICALLY_RECONSTRUCTABLE | detection_service/outputs/common003-preserved-stack/detection_service/app/detectors/statistical_v2/__init__.py | VERIFIED |
| detection_service/app/detectors/statistical_v2/detector.py | DETERMINISTICALLY_RECONSTRUCTABLE | detection_service/outputs/common003-preserved-stack/detection_service/app/detectors/statistical_v2/detector.py | VERIFIED |
| detection_service/app/detectors/statistical_v2/model.py | DETERMINISTICALLY_RECONSTRUCTABLE | detection_service/outputs/common003-preserved-stack/detection_service/app/detectors/statistical_v2/model.py | VERIFIED |
| detection_service/outputs/common003-preserved-stack/artifacts/statistical_v2/calibration/completed_v1/ds_v2_cal_v1.json | DETERMINISTICALLY_RECONSTRUCTABLE | detection_service/outputs/common003-preserved-stack/artifacts/statistical_v2/calibration/completed_v1/ds_v2_cal_v1.json | VERIFIED |
| detection_service/outputs/common003-preserved-stack/artifacts/statistical_v2/final/ds_v2_feature_reference.json | DETERMINISTICALLY_RECONSTRUCTABLE | detection_service/outputs/common003-preserved-stack/artifacts/statistical_v2/final/ds_v2_feature_reference.json | VERIFIED |
| detection_service/outputs/common003-preserved-stack/artifacts/statistical_v2/final/ds_v2_model.json | DETERMINISTICALLY_RECONSTRUCTABLE | detection_service/outputs/common003-preserved-stack/artifacts/statistical_v2/final/ds_v2_model.json | VERIFIED |
| detection_service/outputs/common003-preserved-stack/artifacts/statistical_v2/final/ds_v2_model_manifest_v1.json | DETERMINISTICALLY_RECONSTRUCTABLE | detection_service/outputs/common003-preserved-stack/artifacts/statistical_v2/final/ds_v2_model_manifest_v1.json | UNBOUND |
| detection_service/outputs/common003-preserved-stack/detection_service/app/detectors/statistical_v2/detector.py | DETERMINISTICALLY_RECONSTRUCTABLE | detection_service/outputs/common003-preserved-stack/detection_service/app/detectors/statistical_v2/detector.py | VERIFIED |
| detection_service/requirements-finetuned.txt | GIT_TRACKED | detection_service/requirements-finetuned.txt | UNBOUND |
| detection_service/requirements-quality.txt | GIT_TRACKED | detection_service/requirements-quality.txt | UNBOUND |
| detection_service/requirements.txt | GIT_TRACKED | detection_service/requirements.txt | UNBOUND |
| detection_service/research_protocol/adapters.py | GIT_TRACKED | detection_service/research_protocol/adapters.py | UNBOUND |
| detection_service/research_protocol/detector_semantics.py | GIT_TRACKED | detection_service/research_protocol/detector_semantics.py | UNBOUND |
| detection_service/research_protocol/ds_runtime.py | GIT_TRACKED | detection_service/research_protocol/ds_runtime.py | UNBOUND |
| detection_service/research_protocol/operating_policy.py | GIT_TRACKED | detection_service/research_protocol/operating_policy.py | UNBOUND |
| detection_service/research_protocol/prediction.py | GIT_TRACKED | detection_service/research_protocol/prediction.py | UNBOUND |
| detection_service/research_protocol/protocol_lock.py | GIT_TRACKED | detection_service/research_protocol/protocol_lock.py | UNBOUND |
| remote://D_M-B-base | REMOTE_IMMUTABLE | upstream pinned provenance | remote identifier only |

## Post-Track-A fresh-clone gate

1. Clone the accepted history on an isolated machine and prove the preserved commit is reachable.
2. Restore only exact bound D_S blobs into their expected archive destinations; verify every hash.
3. Secure an authorized immutable backup of the exact D_M-B fine-tuned weights; compare its frozen hash. Do not retrain.
4. Prove gated D_G access and retrieve pinned D_S/D_G snapshots, checking all per-file hashes.
5. Reproduce accepted dependency versions in an isolated environment; validate loaders and protocol preflight.
6. Run separately authorized fresh-clone tests after Track A is idle. No scientific result follows from this static audit.

R2-D_S: NOT_OBSERVED. R3/verifier/protected confirmation: NOT_STARTED.
No shared environment changes, cache cleanup, model moves, uploads or Track-A writes.
