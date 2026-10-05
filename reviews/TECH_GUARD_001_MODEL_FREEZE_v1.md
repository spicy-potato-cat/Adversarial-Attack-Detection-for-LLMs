# TECH-GUARD-001 Model Freeze v1

Date: 2026-10-02. Status: PASS. Built with Llama.

## Frozen Identity

D_G / guard_external / dg_v1; provider Meta.
Upstream: meta-llama/Llama-Prompt-Guard-2-22M.
Model and tokenizer revision: 11614a155199674a0a95e6602d6ab0417b790ed0.
DebertaV2ForSequenceClassification: 12 layers, hidden size 384, two logits.
Total parameters: 70,830,722. Backbone including embeddings: 70,682,112.
The upstream 22M name is not the total parameter count.
Context: 512 including CLS and SEP. Authenticated access: PASS, sumitt86.
Freeze source Git commit: dd82539; full SHA/UTC date in freeze_metadata.json.

Machine-readable artifact root: artifacts/models/dg_v1/.
model_config.json freezes the policy; freeze_metadata.json records provenance.
integrity_manifest.json binds both files. All nine upstream files are SHA-256 bound.
Snapshot: detection_service/.model-cache/dg_v1/snapshot-11614a155199674a0a95e6602d6ab0417b790ed0.
Weights/cache/credentials are ignored and NOT committed.
qualification.json/environment.json remain original blocked-history evidence;
current freeze and smoke supersede their old access/download status.

## SHA-256

| File | SHA-256 |
|---|---|
| model.safetensors | 5120e30bcd536ce285345d9ec104bea6bd6e8f94365b99a340c764f417ea5fa1 |
| config.json | 1dc4742d04507072cafffb7235dc5dba5af9ba126f7a9830b95ed7ec00fd9104 |
| tokenizer.json | 6eb983352e73f1697b883a8c3f6b66bdfa336ab3d29dd3687f8316d0ff2789c1 |
| tokenizer_config.json | 557b3d33d3f41b81ad769244e506549e98a1857d41dd58160aacd4d98d710b5a |
| special_tokens_map.json | 9463f61e1b109a8eb4688b829260d7c6b1e6dff04c98ff7269bb89e2b92369b9 |

Card, README, license and acceptable-use hashes also appear in freeze_metadata.json.

## Score, Decision And Coverage

Serialized id2label is 0=LABEL_0, 1=LABEL_1. Semantic meanings are documented
separately: benign versus malicious instruction-override attempt (injection/jailbreak).
The official helper explicitly scores class 1 at temperature 1. Evidence pinned to
cookbook commit 3c106f3e6ee79d6df51ae706bc7ef2d734ec3ded and hashed in metadata.
raw_score = temperature-1 softmax class 1, maximum across chunks.
Higher means higher upstream malicious risk, not successful compromise.
calibrated_probability = None; no project calibration exists.
binary_vote = OR of native chunk logits.argmax == 1. Logit ties select class 0.
Scope: DEFAULT MODEL DECISION, NOT FINAL THRESHOLD. No project threshold tuning.

Text is tokenized once, without specials/truncation/project preprocessing.
Direct content-ID slices avoid decode/re-encode loss. Content chunk=510,
overlap=64, stride=446; add CLS=1 and SEP=2; PAD=0; batch size=8.
Final span ends at exact content-token count; no dropped tail or window cap.
Score aggregation is a pre-specified engineering policy, not a calibrated
document probability. First maximum-risk chunk wins metadata ties.
Coverage counts unique upstream content tokens, not repeated overlap or specials.
The unbounded tokenizer length sentinel is ignored; model context 512 is enforced.
DebertaV2TokenizerFast's upstream strip/precompiled/space-removal/NFKC normalizer
is unchanged and hash-bound.

## Environment, Terms And Boundaries

Python 3.11.9; torch 2.6.0+cpu (distribution 2.6.0); transformers 4.49.0;
Hub 0.36.2; tokenizers 0.21.4; safetensors 0.8.0; numpy 2.1.3; pytest 8.3.4.
No package installation/upgrade needed; optional hf_xet is not required.
Intel i7-12650H, 16 logical CPUs; RAM 16,869,548,032 bytes.
Torch CUDA unavailable; CPU float32 smoke uses 8 threads. No GPU result claimed.
Library code does not alter global thread/determinism policy.

Llama 4 Community License and pinned Acceptable Use Policy apply.
Authorized gated access is not legal clearance or redistribution permission.
Distribution/service attribution and other obligations need separate review.
Credentials stayed in memory; no token printed or stored in committed files.

D_G training: NO. Fine-tuning: NO. Project calibration: NO.
Project data: NO. Protected data: NO. E1-E10: NO.
External training overlap/benchmark exposure: UNKNOWN.
