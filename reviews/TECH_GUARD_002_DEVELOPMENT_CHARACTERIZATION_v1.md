# TECH-GUARD-002 Development Characterization

Status: **BLOCKED_MISSING_AUTHORITATIVE_DEVELOPMENT_DATA**; pinned model also absent; HF CLI reports Not logged in.

DEVELOPMENT characterization only; zero rows scored. All native/ranking/frontier/fold metrics: UNMEASURED. No alternate corpus/model used.

```json
{
  "status": "BLOCKED_MISSING_AUTHORITATIVE_DEVELOPMENT_DATA",
  "model_status": "BLOCKED_MISSING_PINNED_MODEL",
  "model_id": "meta-llama/Llama-Prompt-Guard-2-22M",
  "revision": "11614a155199674a0a95e6602d6ab0417b790ed0",
  "manifest_sha256": "9cdd5ecdd80f9ac3c8f05db63742721f4537ca2b64a2fe48f6c2b424b57483a6",
  "manifest_path": "C:\\Users\\Asus\\Adversarial-Attack-Detection-for-LLMs\\data_governance\\manifests\\development_partition_manifest_v1.csv",
  "manifest_available": false,
  "missing_source_files": [
    {
      "path": "Dataset/Raw/datasets/GitHub/Do-Not-Answer/datasets/Instruction/do_not_answer_en.csv",
      "expected_sha256": "8585dc135d3b8692b2e464151a313f5164e30f06416e03aa5d11e6c3a21d980e"
    },
    {
      "path": "Dataset/Raw/datasets/HuggingFace/deepset-prompt-injections/data/test-00000-of-00001-701d16158af87368.parquet",
      "expected_sha256": "39ac797cabc157eeed58435a08593b2952bb6cb16fc394a2d383f447cc7b246e"
    },
    {
      "path": "Dataset/Raw/datasets/HuggingFace/deepset-prompt-injections/data/train-00000-of-00001-9564e8b05b4757ab.parquet",
      "expected_sha256": "2e10bc7ab30f542c97e4e83e2a5683000b5057d25ec10908784c631d44124c04"
    }
  ],
  "missing_quality_metadata": [
    {
      "path": "data_governance/DATA_LINEAGE_POLICY_v1.md",
      "expected_sha256": "32ebd1c851a0085f4754971ae4e84206d488d1ef604d0021b4ef629f6b692e26"
    },
    {
      "path": "data_governance/DATA_PARTITION_POLICY_v1.md",
      "expected_sha256": "4fe0ca6cf5b3cb729f6205a862984d5545a0309ffdeea2d32d1312fe6da48b51"
    },
    {
      "path": "data_governance/manifests/development_partition_manifest_v1.csv",
      "expected_sha256": "9cdd5ecdd80f9ac3c8f05db63742721f4537ca2b64a2fe48f6c2b424b57483a6"
    }
  ],
  "snapshot_path": "C:\\Users\\Asus\\Adversarial-Attack-Detection-for-LLMs\\detection_service\\.model-cache\\dg_v1\\snapshot-11614a155199674a0a95e6602d6ab0417b790ed0",
  "missing_snapshot_files": [
    "config.json",
    "LICENSE",
    "model.safetensors",
    "MODEL_CARD.md",
    "README.md",
    "special_tokens_map.json",
    "tokenizer.json",
    "tokenizer_config.json",
    "USE_POLICY.md"
  ],
  "hf_cache_checked": "C:\\Users\\Asus\\.cache\\huggingface\\hub\\models--meta-llama--Llama-Prompt-Guard-2-22M\\snapshots\\11614a155199674a0a95e6602d6ab0417b790ed0",
  "hf_cache_present": false,
  "hf_access": "NOT_LOGGED_IN (hf auth whoami checked locally before implementation)",
  "restore_data": "No repository-supported bootstrap found that reproduces the authoritative manifest. Restore the exact manifest and approved source files from the authoritative machine; verify the listed SHA-256 values. Do not reconstruct or download substitutes.",
  "authentication": "hf auth login; request/accept access in browser at https://huggingface.co/meta-llama/Llama-Prompt-Guard-2-22M if needed; hf auth whoami",
  "materialize_model_command": "hf download meta-llama/Llama-Prompt-Guard-2-22M --revision 11614a155199674a0a95e6602d6ab0417b790ed0 --local-dir \"C:\\Users\\Asus\\Adversarial-Attack-Detection-for-LLMs\\detection_service\\.model-cache\\dg_v1\\snapshot-11614a155199674a0a95e6602d6ab0417b790ed0\"",
  "model_verification": "Verify every downloaded file against artifacts/models/dg_v1/freeze_metadata.json file_sha256, then call existing load_frozen; do not rerun prepare_guard or overwrite the freeze.",
  "native_metrics": null,
  "fixed_fpr_metrics": null,
  "live_rows_scored": 0,
  "raw_prompt_text_saved": false
}
```

Do not recreate the missing manifest or change frozen D_G. Restore exact inputs, verify hashes, authenticate locally and materialize only the pinned snapshot. The existing prepare_guard command refuses to overwrite this already committed freeze and must not be rerun. No repository-supported exact data restoration command was found.
