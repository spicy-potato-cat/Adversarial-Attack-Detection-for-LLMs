# TECH-GUARD-001 Qualification Report v1

Date: 2026-10-01. Status: UNDER INVESTIGATION; execution BLOCKED by model access.
Repository: existing Commander workspace; no fresh clone, per latest instruction.
Branch: tech/guard-001, based on completed calibration commit 57bcadc.

## Reconnaissance

The repository already contains the completed statistical, D_M-A, D_M-B and
semantic-calibration work. No guard package or guard model artifact was found.
BaseDetector.detect accepts DetectionRequest and returns the shared DetectorResult.
Actual decision field is binary_vote; metadata is extensible. The contract supports
raw_score, nullable calibrated_probability, ModelMetadata and input coverage.
Dependencies already include pinned Torch, Transformers and NumPy. Existing local
Python is reused; no global environment or dependency change is needed for qualification.
Central service wiring and all semantic/statistical files remain untouched.

## Candidate Comparison

| Candidate | Purpose / scope | Size / context | Access / provenance | Disposition |
|---|---|---|---|---|
| Meta Llama Prompt Guard 2 22M | Explicit instruction-override attempts: prompt injection and jailbreaks; English-oriented | Card names 22M backbone; Hub displays about 70.8M total parameters; 512-token window | Meta external classifier, DeBERTa-xsmall backbone; Llama 4 license, manual access gate | PROPOSAL for primary English scope; actual access BLOCKED |
| Meta Llama Prompt Guard 2 86M | Same binary attack scope; multilingual training | Card names 86M backbone; total count not locally verified; 512-token window | Meta external classifier, multilingual DeBERTa backbone; same license/gate | DEFERRED; larger than needed for primary English CPU role |
| ProtectAI DeBERTa-v3-base prompt-injection-v2 | Benign versus injection; card explicitly excludes jailbreak and non-English coverage | Hub describes roughly 0.2B parameters; card example uses 512 tokens | ProtectAI fine-tune of Microsoft DeBERTa; Apache-2.0; ungated; project archived | REJECTED as an automatic replacement; narrower role needs Commander approval |

Model parameter totals are not interchangeable with backbone marketing names.
An exact local count requires access to the selected model's configuration/weights.
No public benchmark rows, upstream training datasets or project datasets were opened.

## Proposed Selection and Limits

Prompt Guard 2 22M is the preferred candidate because its dedicated attack scope
matches D_G, while its English-oriented smaller backbone suits local CPU execution.
Selection is PROPOSAL, not a completed APPROVED/FIXED model freeze. The 86M variant
may be relevant to a separately approved multilingual scope; no model sweep ran.
ProtectAI is not a scientifically equivalent substitute for injection-plus-jailbreak
coverage, so its ungated availability does not authorize a silent substitution.

The Meta models are developed externally, unlike project-trained D_M-B. This is
independent developer provenance, NOT proof of disjoint upstream training data,
statistical independence, or detector superiority. Upstream benchmark exposure is
not fully known. No absence-of-contamination or legal-clearance claim is made.
ProtectAI's training documentation references public safety/attack collections;
those references were inspected as card metadata only, never as dataset rows.

## Source-Documented Score and Labels

Meta's card describes binary benign/malicious classification of attempted overrides,
not harmful-subject classification or confirmed successful compromise. Its official
inference helper uses temperature-1 softmax and class index 1 for malicious score;
the card's default label decision is logits.argmax. No project calibration exists
for D_G. Exact serialized id2label, tokenizer behavior and input accounting still
require local artifact verification; no output or mapping is fabricated here.

Future implementation must preserve raw upstream score semantics, leave calibrated
probability null, document the default model decision including tie behavior, and
scan every token of long prompts with explicit special-token accounting and tail
coverage. Any maximum-over-chunks aggregation is a documented guard policy, not a
calibrated whole-document probability. No long-input policy is frozen in this report.

## Immutable Metadata and Access Check

Hub metadata resolved these immutable revisions on the retrieval timestamp recorded
in artifacts/models/dg_v1/qualification.json:

- 22M: `11614a155199674a0a95e6602d6ab0417b790ed0`
- 86M: `a8ded8e697ce7c355e395a0df51f94adb4a2fd27`
- ProtectAI: `90c9989b1a342275dd0d1a95aad283c04e075671`

The preferred pinned config.json request returned HTTP 401 / GatedRepoError.
No Hugging Face token is available in the process environment or configured
repository-local Hugging Face home. No weights were downloaded. Merely resolving
a commit through public Hub metadata is NOT an artifact-integrity freeze.
Task STOP condition 3 applies: required model access needs unavailable credentials.
No alternate provider, mirror or model was used to bypass that gate.

## Authoritative References

- [Meta model card, 22M](https://huggingface.co/meta-llama/Llama-Prompt-Guard-2-22M)
- [Meta model card, 86M](https://huggingface.co/meta-llama/Llama-Prompt-Guard-2-86M)
- [Meta Prompt Guard documentation](https://dev.meta.ai/llama/docs/model-cards-and-prompt-formats/prompt-guard)
- [Meta inference helpers](https://github.com/meta-llama/llama-cookbook/blob/main/getting-started/responsible_ai/prompt_guard/inference.py)
- [ProtectAI model card](https://huggingface.co/protectai/deberta-v3-base-prompt-injection-v2)

Llama 4 access is subject to Meta approval, license and acceptable-use conditions.
The Commander must review/accept applicable conditions and obtain authorized
access. No acceptance form or personal-information submission was performed.
Research handling remains subject to those terms; redistribution obligations
must be reviewed separately. No generic-moderation model was chosen as a guard.

## Required Commander Action

Provide authorized access locally, not a token pasted into chat. Alternatively,
explicitly authorize an offline adapter with real-model smoke BLOCKED, or approve
the narrower ProtectAI role. Until then, implementation and model freeze stop.
