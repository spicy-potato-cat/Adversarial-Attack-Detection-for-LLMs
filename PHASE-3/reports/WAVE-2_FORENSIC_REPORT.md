# Phase-3 Wave 2 Forensic Report

Status: **COMPLETE - COMMANDER REVIEW REQUIRED**  
Wave: `WAVE-2`  
Report date: 2026-09-06  
Final dataset constitution: **NOT APPROVED**

State labels are literal: `FACT`, `MEASURED`, `VERIFIED`, `INFERENCE`,
`RECOMMENDATION`, `UNKNOWN`, `NOT_MEASURED`, and `NOT_APPLICABLE`.

## 1. Executive Summary

- `VERIFIED`: all five authorized local roots were identified. Eight selected
  record-bearing files total 589,202,969 bytes and match the frozen Commander inventory.
- `MEASURED`: 353,981 source rows were read; 353,967 had analyzable text. Fourteen
  empty WildGuardMix prompts are retained by hash and locator in a separate ledger.
- `MEASURED`: WildJailbreak and WildGuardMix are not text-independent: 18,903
  N1 hashes are shared, covering 7.1688% and 56.1727% of their valid records.
- `MEASURED`: the local SALAD payload is only a 127-row example. Eleven rows
  exactly match each of HarmBench, AdvBench, and the Pilot AutoDAN input copy.
- `NOT_MEASURED`: semantic overlap remains unavailable under `DEC-P3-007`.
- `RECOMMENDATION`: keep every role provisional; quarantine SALAD from promotion,
  resolve WildGuardMix components and rights, and do not treat overlaps as independent evidence.

## 2. Scope

`FACT`: Wave 2 covers only `DS-TXT-001`, `002`, `016`, `017`, and `018` and
compares them with Pilot-01 AdvBench, GCG, AutoDAN, HarmBench, JBB, and XSTest.

## 3. Commander Constraints

`VERIFIED`: no dataset payload or model was downloaded. No raw file was modified.
No Wave 3, multimodal work, training, split construction, calibration, threshold
selection, model selection, or final role assignment was performed.

## 4. Local Artifact Resolution

| Dataset | Selected files | Source rows | Payload bytes | Local state |
|---|---:|---:|---:|---|
| WildJailbreak | 2 | 263,769 | 532,662,460 | present |
| WildGuardMix | 2 | 88,484 | 56,003,328 | present |
| SALAD | 1 | 127 | 155,319 | `MISSING_FULL_DATASET`; example only |
| Do-Not-Answer | 1 | 939 | 330,647 | present |
| deepset Prompt Injection | 2 | 662 | 51,215 | present |

The manifest records all eight paths, SHA-256 values, support files, root counts,
source URLs, and missing fields. SALAD's missing full payload was reported; no
download was attempted.

## 5. Dataset Identity / Version Summary

| Dataset | Authoritative source | Revision state |
|---|---|---|
| WildJailbreak | `allenai/wildjailbreak` | dataset revision `UNKNOWN`; identity `PARTIAL` |
| WildGuardMix | `allenai/wildguardmix` | dataset revision `UNKNOWN`; identity `PARTIAL` |
| SALAD | `OpenSafetyLab/SALAD-BENCH` | clean Git HEAD `575d5369...`; data revision `UNKNOWN` |
| Do-Not-Answer | `Libr-AI/do-not-answer` | clean Git HEAD `46070348...`; data release `UNKNOWN` |
| deepset | `deepset/prompt-injections` | Git/HF revision `4f61ecb0...` `VERIFIED` |

## 6. Canonical Schema Results

`MEASURED`: schema v0.2 produced 353,967 deterministic gzip JSONL records. Each
contains source identity/revision/hash/locator and immutable original-record
reference; raw text/response; source labels/category/metadata; separate base and
adversarial fields; generation/lineage; N0/N1/N2 hashes; rights/PII/governance.
All normalized binary/family/subtype values remain `UNKNOWN` as required.

The 14 empty-text rows are not silently deleted: they appear in
`04_quality/WAVE-2_non_analyzable_records.json` and reconcile canonical records
to all 353,981 source rows. They are excluded from text-overlap denominators.

## 7. Data Quality

| Artifact | Rows | Valid | Empty | Missing IDs | Missing labels | Length min/median/p95/max |
|---|---:|---:|---:|---:|---:|---|
| WildJailbreak train | 261,559 | 261,559 | 0 | 261,559 | 0 | 2/609/1,468/5,000 |
| WildJailbreak eval | 2,210 | 2,210 | 0 | 2,210 | 0 | 66/671/1,577/3,105 |
| WildGuardMix train | 86,759 | 86,745 | 14 | 86,745 | 0 | 1/243/1,490/12,814 |
| WildGuardMix test | 1,725 | 1,725 | 0 | 1,725 | 0 | 27/254/1,440/3,013 |
| SALAD example | 127 | 127 | 0 | 127 | 0 | 10/53/163/796 |
| Do-Not-Answer | 939 | 939 | 0 | 0 | 939 | 19/53/112/197 |
| deepset train/test | 662 | 662 | 0 | 662 | 0 | 7/65/339/4,545 overall |

No malformed record, schema mismatch, encoding error, or duplicate source ID was
observed. The WildJailbreak card documents a `tactics` field absent from the local
train TSV. Do-Not-Answer's selected question file has taxonomy but no row label.

## 8. Exact Duplicates

Across the expanded Wave 2 plus Pilot corpus, N0 and N1 each produced 23,586
duplicate clusters with 82,631 participating records. N2 produced 23,740 clusters
with 83,039 records. Within-source N1 results were: WildJailbreak 25 clusters/53
records; WildGuardMix 18,914/57,808; SALAD 2/4; Do-Not-Answer 1/2; deepset 0/0.

## 9. Cross-Dataset Exact Overlap

Nonzero N1 cells are shown below. N0 is identical; N2 changes only the
WildJailbreak/WildGuardMix cell to 19,149 hashes (7.2620% / 56.6757%).

| A / B | Shared N1 hashes | A to B | B to A |
|---|---:|---:|---:|
| WildJailbreak / WildGuardMix | 18,903 | 7.1688% | 56.1727% |
| WildGuardMix / SALAD example | 8 | 0.0090% | 6.2992% |
| WildGuardMix / Do-Not-Answer | 1 | 0.0011% | 0.1065% |
| SALAD example / Do-Not-Answer | 9 | 7.0866% | 0.9585% |
| WildJailbreak / JBB | 1 | 0.0004% | 0.2000% |
| WildJailbreak / XSTest | 3 | 0.0011% | 0.6667% |
| SALAD example / HarmBench | 11 | 8.6614% | 1.1340% |
| SALAD example / AdvBench | 11 | 8.6614% | 2.1154% |
| SALAD example / AutoDAN input | 11 | 8.6614% | 2.1154% |

All omitted Wave 2 target cells are measured zero, not proof of independence.

## 10. Near-Duplicate Analysis

`MEASURED`: accepted Pilot settings were reused: Unicode-aware casefolded word
3-grams, deterministic 128-permutation MinHash, 32x4 LSH, seed 1701, then exact
Jaccard verification at 0.7/0.8/0.9. There were 297,982 unique N1 entities,
79,638 candidates, and 495/344/273 verified distinct-entity pairs. Exact identity
is included in directional record rates but excluded from those distinct-pair totals.

At 0.8, WildJailbreak/WildGuardMix was 7.2874% / 56.6972%. Other important cells
were SALAD/HarmBench 8.6614% / 1.1340%, SALAD/AdvBench and SALAD/AutoDAN each
8.6614% / 2.1154%, WildJailbreak/JBB 0.0011% / 0.4%, and
WildJailbreak/XSTest 0.0019% / 0.8889%. Threshold 0.8 is not finalized.

## 11. Semantic Status

`NOT_MEASURED`: no approved pinned semantic environment exists. No model or large
ML stack was installed and no lexical result is described as semantic evidence.

## 12. Provenance

WildJailbreak's card documents synthetic GPT-4/GPT-3.5 construction and
WildTeaming transformations with Mixtral-8x7B/GPT-4, plus XSTest conceptual
motivation. WildGuardMix documents 87% synthetic, 11% in-the-wild interaction,
and 2% annotator-written composition but not component identities. Do-Not-Answer
is a curated risky-question/refusal benchmark, not inherently adversarial data.
The deepset card does not define its label semantics or construction.

## 13. Lineage

`STRONGLY_SUPPORTED`: WildJailbreak/WildGuardMix share 18,903 active-text and
10,229 base-behavior N1 hashes, but direction/direct inclusion remains `UNKNOWN`.
`STRONGLY_SUPPORTED`: the SALAD example reuses 11 questions present in each of
HarmBench, AdvBench, and AutoDAN input. Similarity alone was not upgraded to
documented lineage, and shared topics are not treated as reuse.

## 14. Wave 2 to Pilot-01 Contamination

The expanded matrix contains all 40 required pairs and separates N0/N1/N2 exact,
verified lexical near, semantic `NOT_MEASURED`, documented lineage, behavior
identity, and evidence state. Besides the SALAD and WildJailbreak cells above,
Wave 2 to Pilot cells are zero at N1. Machine-readable directional denominators
are retained for every cell.

## 15. Licensing / Rights

WildJailbreak and WildGuardMix are `CONDITIONAL` due to ODC-BY plus gated AI2
responsible-use terms and unresolved upstream rights. SALAD is `UNKNOWN` because
repository Apache-2.0 does not establish separate Salad-Data rights. Do-Not-Answer
dataset content is CC BY-NC-SA 4.0 while code is Apache-2.0. deepset is `UNKNOWN`
because its card declares both CC BY 4.0 and Apache-2.0 without scope resolution.
All are blocked from finalized promotion under `DEC-P3-010`.

## 16. Privacy / PII

`MEASURED`: regex candidate counts are retained in the privacy JSON. WildJailbreak
had 553 email, 2,429 URL, 9 IPv4, and 2,461 phone-like records; WildGuardMix had
216/680/38/742; SALAD had 1/0/0/2; Do-Not-Answer and deepset had zero. These are
not confirmed PII, regex cannot prove absence, and all sources remain `REVIEW_REQUIRED`.

## 17. Dataset-Role Recommendations

| Dataset | `RECOMMENDATION` only |
|---|---|
| WildJailbreak | `TRAINING_CANDIDATE`, conditional on rights/privacy/revision and overlap controls |
| WildGuardMix | `TRAINING_CANDIDATE`, treated as an aggregate and not independent of WildJailbreak |
| SALAD | `QUARANTINE`; incomplete example-only payload and benchmark reuse |
| Do-Not-Answer | `INTERNAL_TEST_CANDIDATE`; risky-question/refusal evidence, not assumed adversarial |
| deepset | `TRAINING_CANDIDATE`, conditional on label/license/provenance resolution |

## 18. Unknowns

Immutable WildJailbreak/WildGuardMix revisions; WildGuardMix component mapping;
full SALAD payload/revision/rights; row-level generation and upstream mappings;
deepset label, license, and direct/indirect semantics; contextual PII; normalized
taxonomy; and semantic overlap remain `UNKNOWN` or `NOT_MEASURED`.

## 19. Risks

The main risks are double-counting WildJailbreak/WildGuardMix, treating the SALAD
example as a full or pristine benchmark, inferring lineage direction from equality,
using source labels as normalized taxonomy, ignoring gated/noncommercial terms,
and interpreting regex screening or zero overlap as proof of safety/independence.

## 20. Reproducibility Artifacts

Produced: Wave 2 manifest and registry; source evidence; schema v0.2 and 271,573,141-byte
canonical gzip; quality and non-analyzable ledgers; exact and near summaries;
source distributions; behavior/lineage summaries; rights/privacy results; full
contamination matrix; role recommendations; config, script, run log, and test log.
The canonical SHA-256 is `9bd68cb028c8155b555fdfbf7288bf3e761510ad1e9283d09d1db85ac8df736a`.
The frozen inventory SHA-256 remains
`2bbead4df3737b1f626ea0dc8fb40f3c5a276973015c7091abba76bf2246f723`.

Run `WAVE-2-FORENSICS-20260906T153600Z` succeeded in 961.277 seconds with Python
3.11.7 and DuckDB CLI v1.4.1. Its before/after hashes match for all raw inputs.
Post-run QA added only the explicit 14-row ledger and corresponding reproducibility
code (`wave2_forensics.py` v0.1.1); overlap results and canonical data were unchanged.

## 21. Tests

`VERIFIED`: `python -m unittest discover -s PHASE-3/tests -q` ran 16 tests in
21.585 seconds, all passing. Tests parse every canonical record, enforce required
schema/taxonomy policy, reconcile 353,967 canonical plus 14 non-analyzable rows,
verify deterministic canonicalization/MinHash, enforce comparison scope, and
live-rehash all eight selected raw artifacts.

## 22. Methodology Assessment

`VERIFIED`: the Pilot method scaled without a redesign, held candidate detail to
compact summaries, and preserved the separation among exact text, lexical near,
base behavior, documentary lineage, and semantic status. `PARTIAL`: semantic,
rights, contextual privacy, and several source-version/component claims remain open.

## 23. Commander Decisions Required

1. Accept or revise this Wave 2 evidence and provisional recommendations.
2. Decide whether WildJailbreak, WildGuardMix, or a deduplicated/grouped combination
   should proceed to later constitution work; they must not count as independent.
3. Keep SALAD quarantined or separately authorize acquisition of the missing full
   dataset after identity/rights review.
4. Resolve deepset license and label semantics before promotion.
5. Decide whether deeper rights/privacy and a pinned semantic stage precede any next wave.

## 24. Recommended Next Step

`RECOMMENDATION`: preserve the current outputs, review the five decisions above,
and perform no promotion or expansion until a new Commander authorization.

# STOP

Wave 2 forensic analysis is complete. **COMMANDER DECISION REQUIRED.** No Wave 3,
multimodal analysis, training, split construction, calibration, threshold/model
selection, or final dataset constitution begins automatically.
