# Wave 2 Source Evidence

Status: `VERIFIED_LOCAL_EVIDENCE`  
Review date: 2026-09-06  
Payload downloads: `NONE`

The frozen Commander inventory, SHA-256
`2bbead4df3737b1f626ea0dc8fb40f3c5a276973015c7091abba76bf2246f723`,
is the acquisition baseline. Dataset payload files were read but not modified.

| Dataset | Authoritative identity | Revision evidence | Local documentary evidence | Status |
|---|---|---|---|---|
| DS-TXT-001 WildJailbreak | `allenai/wildjailbreak` | No immutable HF revision in bundle | README lines 2, 22-43, 111-124 document ODC-BY, gated responsible-use terms, synthetic construction, XSTest motivation, and WildTeaming | `PARTIAL` |
| DS-TXT-002 WildGuardMix | `allenai/wildguardmix` | No immutable HF revision in bundle | README lines 2, 29-38, 63-78, 102-107 document ODC-BY, gated terms, 87/11/2 composition, response generation, and labels | `PARTIAL` |
| DS-TXT-016 SALAD | `OpenSafetyLab/SALAD-BENCH` | Clean local Git HEAD `575d5369c5355c0ed76e27860a889aa2f3c3e0e5` | README lines 14 and 38 identify separate Salad-Data and describe 21K base questions; repository LICENSE is Apache-2.0 | `PARTIAL`; full data `MISSING` |
| DS-TXT-017 Do-Not-Answer | `Libr-AI/do-not-answer` | Clean local Git HEAD `460703484df354958a5e1cd7378a38fcb94a2f3e` | README lines 17-32 documents curated risky prompts, 939 instructions, and response assessment; line 176 separates dataset CC BY-NC-SA 4.0 from source-code Apache-2.0 | `PARTIAL` |
| DS-TXT-018 deepset Prompt Injection | `deepset/prompt-injections` | Local Git HEAD `4f61ecb038e9c3fb77e21034b22511b523772cdd` | Card lists 546 train and 116 test examples but conflicting `cc-by-4.0` and `apache-2.0` license metadata and no task/construction details | `VERIFIED` revision; rights `UNKNOWN` |

The complete artifact paths, sizes, hashes, supporting files, missing information,
and source URLs are in `01_acquisition/manifests/WAVE-2_manifest.json`.

