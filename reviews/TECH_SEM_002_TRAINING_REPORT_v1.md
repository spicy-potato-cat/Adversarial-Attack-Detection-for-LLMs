# TECH-SEM-002 Training Report v1

Date: 2026-10-01
Status: PREPARED; AUTHORITATIVE TRAINING NOT STARTED

## Resource Handoff

Section 14 of the Commander authorization requires preparation, a small pipeline
smoke test, an exact PowerShell command, and a stop for completed output when
training is expected to take significant time. That condition applies here.

Hardware verified: Intel Core i7-12650H, 10 cores/16 logical processors,
16,869,548,032 bytes physical RAM, NVIDIA RTX 3070 Ti Laptop GPU with 8,192 MiB VRAM.
The workspace has torch 2.6.0+cpu: CUDA is unavailable to this interpreter despite
the physical GPU. No GPU runtime was installed or detector environment upgraded.
The frozen v1 recipe uses CPU, float32 and eight torch threads.

## Frozen Training Recipe

Model: distilbert/distilroberta-base.
Revision: fb53ab8802853c8e4fbdbcd0529f21fc6f459b2b.
Binary sequence-classifier parameters: 82,119,938.
Seed: 1701. Epochs: 3. Batch size: 8. Gradient accumulation: 1.
AdamW: learning rate 2e-5; weight decay 0.01, except bias/LayerNorm;
betas=(0.9,0.999); eps=1e-8. Linear scheduler; 426 steps; 43 warmup steps.
Gradient clipping: 1.0. Loss: weighted cross entropy.
Class weights: 1135/(2*952) for class 0 and 1135/(2*183) for class 1,
derived only from BASE_TRAIN. Fixed final checkpoint; no early stopping/search.
Token limit: 256 including special tokens; right truncation and dynamic padding.

Manifest SHA-256:
`9cdd5ecdd80f9ac3c8f05db63742721f4537ca2b64a2fe48f6c2b424b57483a6`.
All 1,135 BASE_TRAIN texts reconstruct from the three approved source files and
match the manifest exact hashes. Training labels: 952 negative, 183 positive.
CALIBRATION and VALIDATION text has not been loaded for this preparation.
The mixed-source normalized archive and protected dataset payloads were not accessed.

## Synthetic Pipeline Evidence

Actual pinned upstream model loaded, a seeded binary head initialized, and one
batch of eight synthetic 256-token examples used for a backward/optimizer step.
Transformer backbone hashes differ before/after: genuine encoder updates verified.
The scratch model was discarded; it is not an authoritative trained checkpoint.
No project rows were used for this synthetic step.

- Synthetic loss: 0.7193474769592285.
- Gradient norm before clipping: 2.417553424835205.
- Step time: 12.4812508 seconds.
- Deterministic eval inference: PASS.
- Estimated 426-step full-length training: 88.62 minutes, plus final validation.

This is an estimate from one worst-length synthetic step, not measured training
runtime. Dynamic padding and shorter real inputs may reduce actual duration.

## Commander Command

```powershell
Set-Location C:\Users\harsh\Adversarial-Attack-Detection-for-LLMs
.\.local-python\python.exe -m detection_service.scripts.train_semantic_finetuned --mode train
```

This command performs one BASE_TRAIN-only training run, saves the final frozen
checkpoint, verifies reload and the real-model API, and only then runs one final
233-row DEVELOPMENT-ONLY VALIDATION evaluation. It never fits calibration or
selects a threshold. Output: `artifacts/models/dm_b_v1/`.

The runner refuses to overwrite preparation/model artifacts or rerun training over
an existing output directory. A failure requires review, not a new trial chosen
from validation results. Do not change the frozen recipe or software environment
before this command; the runner checks both. Epoch loss summaries and final
results are printed; no prompts or per-record calibration data are printed.

## Current Outcome

Authoritative epochs/batches completed: 0. Training runtime/loss: unavailable.
Final authoritative checkpoint: NOT CREATED. D_M-B is not ready for calibration.
Model cache is workspace-local and ignored by Git. No extra package is required
for the frozen CPU command; optional GPU acceleration would need a separately
recorded CUDA-capable torch environment and a revised pre-training device freeze.

## Warnings and Limitations

The first upstream snapshot attempt hit Windows symlink privilege error 1314;
the completed snapshot uses ordinary files. Hugging Face also reported missing
optional hf_xet acceleration; regular HTTP download succeeded, so it is unnecessary.
The classification head initialization warning is expected for a pretrained MLM;
those head parameters and all transformer parameters will be trained.

No claim of convergence or scientific detection performance is made from the
synthetic test. The approved corpus is narrow direct-injection development and
does not establish broad jailbreak, indirect, agentic or adaptive coverage.
