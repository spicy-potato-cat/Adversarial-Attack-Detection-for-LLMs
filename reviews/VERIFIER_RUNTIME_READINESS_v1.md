# Verifier runtime readiness v1

Metadata-only access is confirmed for all three frozen candidate revisions using
the existing sumitt86 credentials. Configs and tokenizer configs were retrieved;
tokenizer payload availability was checked by HEAD without downloading tokenizer
payloads. All scientific model-query counts remain zero. No weight downloads,
model loads, tensor allocation or package/environment changes occurred.

V1_READY and V2_READY mean authenticated access plus static architecture/adapter
readiness only. Live adapter loading remains blocked by preparation scaffolding.
Native per-chunk argmax mapping remains fixed; ties benign, OR across chunks.
Frozen recovery denominator and threshold policy are unchanged; empty population
remains undefined. No future failure population was opened or constructed.

V3_NOT_FEASIBLE_CURRENT_MACHINE: the inspected Python 3.12 runtime has PyTorch
2.10.0+cpu and Transformers 4.57.6, with GraniteMoe source support. The GPU is an
RTX 3070 Ti Laptop GPU with 8192 MiB total VRAM. Free capacity is a transient
snapshot during Track A, recorded in the readiness JSON. BF16 native checkpoint
bytes total 6,597,622,168; float32 parameter storage is about 13.2 GB plus overhead.
Current free RAM/VRAM cannot safely hold it, and the inspected runtime cannot use
CUDA. No model was loaded to test this. Another existing compatible runtime has
not been established; no CUDA/package or quantization changes are proposed here.

After Track A is idle, assess native loading in a separately authorized isolated
runtime with adequate headroom. If access, hardware or native loading cannot meet
the frozen design, report a dependency rather than silently substituting a model,
quantization scheme, threshold or risk definition. V3 retains the pinned native
jailbreak template and deterministic first-token Yes/No mapping, never a fabricated
probability. Native template use is described by the pinned IBM model card:
https://huggingface.co/ibm-granite/granite-guardian-3.2-3b-a800m/blob/3de033d89b499a18d9a573b5192bf3b967ef48c5/README.md
