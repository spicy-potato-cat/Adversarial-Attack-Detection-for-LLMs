# TECH-GUARD-001 Model Freeze v1

Date: 2026-10-01. Status: BLOCKED; this is NOT a completed artifact freeze.

Proposed project ID: external_guard; version: dg_v1. These are not yet FIXED.
Preferred upstream: meta-llama/Llama-Prompt-Guard-2-22M; developer: Meta.
Public metadata revision: `11614a155199674a0a95e6602d6ab0417b790ed0`.
Tokenizer revision target: same commit, but tokenizer bytes are NOT VERIFIED.
Artifact/config/tokenizer hashes: UNAVAILABLE because pinned config access is gated.
Exact architecture/configuration/parameter count: NOT LOCALLY VERIFIED.
Documented backbone: DeBERTa-xsmall, named 22M; total Hub display about 70.8M.
Documented context: 512 tokens; exact special-token budget NOT VERIFIED.
Labels: documented benign/malicious; exact id2label NOT LOCALLY VERIFIED.
Score proposal: temperature-1 softmax malicious class 1, following Meta helper.
Default decision proposal: upstream argmax, not a tuned project operating point.
Project calibrated_probability: must remain None; no project calibration performed.
Long-input/token-overlap/aggregation configuration: NOT FROZEN.

Public Hub metadata and the blocked access result are recorded in
`artifacts/models/dg_v1/qualification.json`. Environment is in environment.json.
License: Llama 4 community terms and acceptable-use policy; manual access gate.
No terms accepted and no claim of legal clearance. No weights acquired.

Current environment: Python 3.11.9, Torch 2.6.0 CPU build, Transformers 4.49.0,
Hugging Face Hub 0.36.2, tokenizers 0.21.4, safetensors 0.8.0, NumPy 2.1.3.
All intended caches and temporary output paths are repository-local and ignored.
Existing repository-local Python is reused; no machine-wide changes occurred.

External training provenance is documented only at provider/card level. Disjoint
upstream training data and independence from all future project benchmarks remain
UNKNOWN. Project training: NO. Fine-tuning: NO. Project dataset access: NO.

After access is authorized: retrieve model/tokenizer/license/card at this exact
revision, verify labels/context/architecture, hash all used bytes, count parameters,
freeze a guard configuration, then implement and run standalone synthetic tests.
No weights or huge caches should enter Git. Do not call this model frozen before
those steps actually pass.
