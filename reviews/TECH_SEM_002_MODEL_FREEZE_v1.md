# TECH-SEM-002 Model and Recipe Freeze v1

Status: TRAINED_RAW_MODEL_FROZEN. Date: 2026-10-01.
Project detector D_M-B; version dm_b_v1; detector_id semantic_finetuned.
No prior exact model decision was present in the repository. The earlier paper
notes retain TODO-MODEL and describe a lightweight end-to-end sequence classifier.
The current TECH-SEM-002 authorization supersedes earlier proposals permitting
validation-driven model selection: one fixed recipe, final checkpoint, one final evaluation.

## Model Provenance

Upstream: distilbert/distilroberta-base; organization: distilbert / Hugging Face.
Revision and tokenizer revision: `fb53ab8802853c8e4fbdbcd0529f21fc6f459b2b`.
Architecture: RobertaForSequenceClassification, 6 transformer layers, hidden size 768.
Exact parameter count including binary head: 82119938.
Context capacity: 512; frozen input limit: 256, including special tokens.
License: Apache-2.0, verified in the pinned model card.
Source: https://huggingface.co/distilbert/distilroberta-base/blob/fb53ab8802853c8e4fbdbcd0529f21fc6f459b2b/README.md
Retrieval UTC: 2026-10-01T11:08:13.961809+00:00.
All retrieved model/tokenizer/card/config bytes are hashed in artifacts\models\dm_b_v1_preparation.json.
This task does not claim absence of upstream exposure to future benchmark data.

## Data and Labels

Manifest: `9cdd5ecdd80f9ac3c8f05db63742721f4537ca2b64a2fe48f6c2b424b57483a6`; verified before preparation and training.
BASE_TRAIN: 1135; class counts: {'0': 952, '1': 183}.
Approved sources only: deepset Prompt Injection and Do-Not-Answer.
Labels follow the approved development constitution: benign/non-injection and
hard-benign risky/refusal = 0; direct injection attempt = 1. Harmful subject matter
alone is not an attack label. Original source text is preserved without metadata concatenation.
CALIBRATION used: NO. Protected data used: NO.
Outer partition metadata may be inspected only for integrity and lineage checks.

## Frozen Recipe

```json
{
  "upstream_model": "distilbert/distilroberta-base",
  "upstream_revision": "fb53ab8802853c8e4fbdbcd0529f21fc6f459b2b",
  "tokenizer_revision": "fb53ab8802853c8e4fbdbcd0529f21fc6f459b2b",
  "detector_id": "semantic_finetuned",
  "detector_version": "dm_b_v1",
  "max_sequence_length": 256,
  "model_context_length": 512,
  "seed": 1701,
  "epochs": 3,
  "batch_size": 8,
  "gradient_accumulation": 1,
  "learning_rate": 2e-05,
  "weight_decay": 0.01,
  "warmup_ratio": 0.1,
  "gradient_clip": 1.0,
  "optimizer": "AdamW",
  "scheduler": "linear",
  "loss": "weighted_cross_entropy",
  "class_weight_policy": "BASE_TRAIN_N/(2*N_class)",
  "checkpoint_policy": "final_epoch_only_no_validation_selection",
  "precision": "float32",
  "device": "cpu",
  "cpu_threads": 8,
  "default_cutpoint": 0.5,
  "manifest_sha256": "9cdd5ecdd80f9ac3c8f05db63742721f4537ca2b64a2fe48f6c2b424b57483a6",
  "text_field": "source.raw_text",
  "truncation_side": "right",
  "padding_side": "right",
  "padding": "longest_in_batch"
}
```

Class weights = BASE_TRAIN_N / (2 * N_class): [0.5961134453781513, 3.101092896174863].
AdamW betas=(0.9,0.999), eps=1e-8; biases and LayerNorm weights have zero decay.
Total steps: 426; linear warmup steps: 43.
No early stopping, internal validation, search, calibration, or operating threshold optimization.
Fixed final checkpoint after three epochs. Seeded random binary head is expected:
upstream MLM head weights are discarded and classification head weights initialized.
All encoder and head parameters are trainable; actual backbone changes must be verified.

## Input and Output

Fast byte-level tokenizer; add model special tokens; dynamic padding within batches;
right truncation to 256 tokens. Truncation and full token count are reported at inference.
Raw score is softmax(logits)[1], so higher means greater adversarial-input risk.
calibrated_probability remains null. binary_vote uses raw_score >= 0.5, explicitly
DEFAULT_DEVELOPMENT_CUTPOINT. Batch latency is elapsed batch time divided by batch count.

## Reproducibility and Artifact Policy

Recipe: `detection_service\configs\dm_b_v1_training.json`; preparation: `artifacts\models\dm_b_v1_preparation.json`.
Preparation binds exact recipe bytes, source hashes, software versions, hardware and Git revision.
Current environment: `{"python": "3.11.9 (tags/v3.11.9:de54cf5, Apr  2 2024, 10:12:12) [MSC v.1938 64 bit (AMD64)]", "torch_runtime": "2.6.0+cpu", "torch": "2.6.0", "transformers": "4.49.0", "numpy": "2.1.3", "scikit-learn": "1.6.1", "pyarrow": "19.0.1", "huggingface-hub": "0.36.2", "safetensors": "0.8.0"}`.
Hardware: `{"cpu": "12th Gen Intel(R) Core(TM) i7-12650H", "logical_cpus": 16, "ram_bytes": 16869548032, "cuda_available": false, "torch_cuda": null, "available_ram_bytes": 3411030016, "nvidia_smi": "NVIDIA GeForce RTX 3070 Ti Laptop GPU, 8192 MiB"}`.
Model cache is workspace-local and Git-ignored. Final artifact directory: `artifacts\models\dm_b_v1`.
Weights remain local; frozen project manifests/configuration/reports can be committed.
An existing preparation or trained artifact is never silently overwritten.
No artifact loader accepts preparation-only or partially trained models.

## Scientific Limitation

The narrow development corpus does not support comprehensive claims about
jailbreak families, indirect injection, agent/tool attacks, or adaptive attacks.
Future validation results will be DEVELOPMENT-ONLY, not E1-E10 or protected evaluation.
