# R1 Source Clearance

Status: **ALL THREE SOURCES CLEARED WITH LOCAL-ONLY RESTRICTION**.
Gate B: acceptance PASS; scoring still requires the separate pre-scoring commit.
This authorization prospectively supersedes the historical source-governance
blocker, without rewriting the old register, report, or blocker evidence.

## Source Rights And Identity

| Source | Pinned upstream | Rights | R1 role |
|---|---|---|---|
| LLMail-Inject | Microsoft HF, `1063bdf01ec8762b812d5e06ee768a06faa5a6f7` | Dataset card MIT | 400 attack attempts |
| InjecAgent | UIUC GitHub, `f19c9f2c79a41046eb13c03c51a24c567a8ffa07` | MIT, Qiusi Zhan 2023 | 400 BASE tool-response attacks |
| OR-Bench | Original HF `bench-llm/or-bench`, `e36d8b80e81837c8a8f264bbb2a49f1b32c7e272` | Dataset CC-BY-4.0, distinct from code Apache-2.0 | 1,000 hard-benign inputs |

Reviewed public licenses permit local academic evaluation. No narrower data
terms were found in the pinned cards/data documentation reviewed; this is not
legal clearance of every underlying user-authored item. MIT notices must be
preserved. Cite LLMail-Inject (Abdelnabi et al., 2025) and InjecAgent's authors
and pinned source. OR-Bench attribution must identify Cui, Chiang, Stoica and
Hsieh (2024), link the source and CC-BY-4.0, and identify extraction/sampling.
This task authorizes no dataset redistribution regardless of license permissions.

Primary evidence:
[LLMail official dataset](https://huggingface.co/datasets/microsoft/llmail-inject-challenge),
[InjecAgent pinned licence](https://github.com/uiuc-kang-lab/InjecAgent/blob/f19c9f2c79a41046eb13c03c51a24c567a8ffa07/LICENCE),
[OR original dataset](https://huggingface.co/datasets/bench-llm/or-bench),
[CC-BY-4.0](https://creativecommons.org/licenses/by/4.0/).
Complete local evidence paths, sizes, hashes and source files are in
`artifacts/research_protocol/r1/r1_source_clearance_v1.json`.

## Mirror Verification

The LLMail user bucket is not an authoritative source and has no Git history.
It is bound by a content-addressed snapshot of selected file paths, sizes and
SHA-256 values, not a fabricated revision. Its labelled and raw phase-2 files
match the official pinned release's LFS SHA-256 object IDs exactly. The two
small descriptor files match pinned upstream Git blob IDs. Large official
payloads were not redundantly downloaded for a second copy.

| LLMail file | Bytes | SHA-256 |
|---|---:|---|
| labelled_unique_submissions_phase2.json | 68586935 | `f89af984e345430c3b357903890e30867bf4676f4ef10c138cc7bad218e890b8` |
| raw_submissions_phase2.jsonl | 263506099 | `a9207e1d893ccb74ca6f9cc5eecea433bc49c23a26bed88088afd385c7ab18b6` |
| levels_descriptions.json | 884 | `d1391d6fa8bb074b1603bb20699df6c1ada3c6add64db495e1a39faebc0cd400` |
| objectives_descriptions.json | 379 | `daed5cacc5126790073e1a8dfc650b8024c903c415f1e11a189a8171c0c0f183` |

The initially named OR bucket returned 404. The Commander's newest explicit
dataset URL `bench-llms/or-bench` is used instead, pinned to
`fd6ee135ee63ff6c4f3ff72c0e39627bf0a7f314`.
Its hard CSV is byte-identical to the original upstream hard CSV:
169255 bytes, SHA-256
`a6e2f1166416efe5901f3bb05c47dc92ab3aca3acfe143693d38b8057d841e6d`.
No toxic or 80k payload is used.

InjecAgent's existing local clone is at the accepted upstream commit. All five
requested data files match its Git objects after the documented Windows CRLF
checkout transformation; local and upstream object SHA-256 values are both
recorded. This is not falsely described as byte-identical LF checkout.
Decoded JSON input strings are preserved verbatim. No original file changed.

## Schema And Extraction

LLMail labelled-unique phase 2 is a dictionary from complete formatted email
text to annotations: 37,303 unique prompts; 19,038 string `True`, 1,969 boolean
`true`, 13,796 `Unclear`, and 2,500 `False`. The positive pool is 21,007 explicit
attempts, all matched to raw submission metadata using the documented subject
and body formatting. Eleven multi-team prompt keys are excluded by predeclared
lineage eligibility. Success is not a positive-label condition. One selected
prompt has a missing upstream success observation, retained as null rather than
failure; source outcomes remain in metadata, never detector input.

InjecAgent has 510 direct-harm and 544 data-stealing BASE cases. Input is exactly
`Tool Response`; injected instructions are verified present. Attacker and user
base-case joins preserve tool identities and attack type without passing answer
keys, expected achievements, thoughts or outcome annotations to detectors.
There are no source-native test-case IDs: file/row locators are internal IDs,
not invented original IDs. Enhanced attacks are excluded.

The pinned OR hard file actually contains 1,319 rows, despite its hard-1k name.
The predeclared seeded-hash ordering deterministically selects 1,000. Every row
has truth 0, no attack family, and source OR_BENCH_HARD.

## Contamination

All 23,380 candidates were compared with all 1,601 accepted development rows:
BASE_TRAIN 1,135, CALIBRATION 233, VALIDATION 233. Raw hashes and all 1,601 N1
normalized hashes were reconstructed with the accepted loaders. There are zero
raw or N1 exact matches. Source-scoped native IDs have no comparable shared
domain; internal row numbers are not native identity evidence. No documented
project-development lineage is shared; hidden upstream/pretraining reuse remains
unknown, not disproven.

The approved Unicode casefold word-threegram exact Jaccard scores were checked
at 0.7/0.8/0.9. Candidate enumeration is exhaustive through an inverted index,
not an approximate MinHash-LSH result. One LLMail candidate has Jaccard
709/730 = 0.9712328767 with a development record. It was not selected by the
score-blind seeded procedure; selected near matches are zero at all three levels.
No semantic model or new similarity threshold was introduced.

## Sampling And Lineage

Seed 1701; stable SHA-256 ordering; no scores inspected. LLMail selection rotates
over 96 teams and source scenarios, at most five selected prompts per team.
InjecAgent selection is 200 direct-harm and 200 data-stealing across all 17 user
tools. The source-level/high-level family mapping is protocol-declared:
LLMail INDIRECT_PROMPT_INJECTION; InjecAgent AGENT_TOOL_INJECTION.

Lineage is the transitive union of hashed LLMail team dependencies, shared
InjecAgent attacker OR user base cases, and N1 duplicate links. There are 1,097
components: 96 LLMail team components, one 400-row InjecAgent component, and
1,000 OR singleton fallbacks. The giant InjecAgent cluster is intentional:
ignoring shared user cases would understate dependency. Production clustered
bootstrap is frozen before scores; source-specific InjecAgent inference has only
one independent cluster and must be treated descriptively. OR singleton fallback
does not establish independence of model-generated records.

## Privacy And Limits

Payloads, formatted emails, raw team UUIDs and user-generated outputs stay only
in ignored local directories. Committed metadata has hashes, locators, source
categories and tool names, not prompts or participant identities. Email-pattern
screening flags candidate-sensitive input text; it is not exhaustive PII review.
No public prompt redistribution is authorized. Existing local files are read-only
inputs; no permission attributes or bytes are modified.

LLMail is adaptive to upstream disclosed challenge defenses, not to this stack.
InjecAgent deliberately reuses simulated base cases. OR hard rows were selected
for over-refusal under other models. Source labels and selection have limitations;
none establishes unseen foundation-model pretraining or universal harmlessness.
No protected benchmark payload, model fitting, calibration, threshold selection,
R2/R3 generation, router, verifier or Cycle-2 work occurs here.
