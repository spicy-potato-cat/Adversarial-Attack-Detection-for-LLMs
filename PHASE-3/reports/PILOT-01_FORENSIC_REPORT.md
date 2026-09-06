# Phase-3 Pilot-01 Forensic Report

Status: **COMPLETE - COMMANDER REVIEW REQUIRED**  
Pilot: `PILOT-01`  
Report date: 2026-09-06  
Final constitution: **NOT APPROVED**

State labels in this report have their literal governance meanings: `FACT`,
`MEASURED`, `VERIFIED`, `INFERENCE`, `RECOMMENDATION`, `UNKNOWN`,
`NOT_MEASURED`, and `NOT_APPLICABLE`.

## 1. Executive Summary

- `MEASURED`: the Commander bundle inventory contains 46,753 discovered paths,
  46,752 successfully hashed files, one failed transient path, and
  27,212,988,016 bytes.
- `VERIFIED`: inventory CSV SHA-256 is
  `2bbead4df3737b1f626ea0dc8fb40f3c5a276973015c7091abba76bf2246f723`;
  row, status, and byte totals reconcile with the summary.
- `VERIFIED`: the sole failure was a vanished VLSBench Git LFS temporary file.
  It is unrelated to Pilot-01 and does not invalidate this pilot.
- `MEASURED`: 3,060 records from ten record-bearing artifacts were adapted
  without changing source files. One AutoDAN seed file was retained but was not
  treated as a dataset record.
- `MEASURED`: N0, N1, and N2 each produced 649 duplicate clusters containing
  1,834 records. Cross-source reuse is substantial and directionally asymmetric.
- `MEASURED`: deterministic MinHash/LSH evaluated 4,580 candidate pairs; exact
  word-3-gram Jaccard verification found 1,830, 1,768, and 1,706 pairs at
  thresholds 0.7, 0.8, and 0.9.
- `NOT_MEASURED`: embedding-based semantic overlap was not run because no
  approved pinned inference stack was available. No proxy is mislabeled as a
  semantic result.
- `RECOMMENDATION`: accept the forensic method with the semantic stage and
  dataset-specific rights review recorded as incomplete. Stop before Wave 2.

## 2. Scope

`FACT`: Pilot-01 is limited to `DS-TXT-013` AdvBench, `DS-TXT-014` GCG,
`DS-TXT-015` AutoDAN, `DS-TXT-007` HarmBench, `DS-TXT-008` JailbreakBench,
and `DS-TXT-009` XSTest. The purpose is methodology validation and lineage
analysis, not corpus constitution.

## 3. Commander Constraints

`FACT`: no Wave 2, training, calibration, model selection, threshold selection,
benchmark consumption for development, redistribution, destructive cleanup, or
final split/role assignment was authorized. Existing raw files were read only.
No dataset payload was downloaded after the Commander made the local bundle the
authoritative acquisition input.

## 4. Local Acquisition State

`FACT`: the Commander-provided root is `Dataset/Raw/datasets`. It contains the
full local bundle inventoried below. A minimal 11-artifact, 997,784-byte pinned
acquisition completed immediately before the local-bundle update; it is retained
under `PHASE-3/01_acquisition/raw/PILOT-01` as transparent pre-update evidence.

`VERIFIED`: seven equivalent key files in the Commander bundle match those
pinned copies under N1. Three are byte-identical; four differ only at the byte
level due to line endings. Separate JBB behavior, judge-comparison, and GCG
artifact equivalents were not identified in the Commander bundle, but the
pre-update pinned copies remain locally available. No replacement download was
attempted.

## 5. Hashing Summary

| Field | Result |
|---|---:|
| Started | `2026-09-01T21:12:13.481181Z` |
| Completed | `2026-09-01T21:34:49.263345Z` (`2026-09-02 03:04:49` IST) |
| Discovered | 46,753 |
| Hashed | 46,752 |
| Failed | 1 |
| Total bytes | 27,212,988,016 |
| Inventory version | `0.1` |
| Inventory SHA-256 | `2bbead4df3737b1f626ea0dc8fb40f3c5a276973015c7091abba76bf2246f723` |

All values are `MEASURED` and retained in
`01_acquisition/manifests/local_bundle_inventory_summary.json`.

## 6. Failed File Analysis

| Field | Finding |
|---|---|
| Path | `HuggingFace/VLSBench/.git/lfs/tmp/2703061825` |
| Name / extension | `2703061825` / none |
| Type | `GIT_LFS_TEMPORARY` |
| Size | `NOT_READABLE` |
| Dataset | VLSBench, `DS-MM-003` |
| Error | `[WinError 2] The system cannot find the file specified` |
| Pilot-01 required | No |
| Controlled retry | File absent; no source modification attempted |
| Final status | `HASH_STATUS = FAILED` |

`VERIFIED`: this was a transient Git LFS path, not Pilot-01 dataset evidence.

## 7. File-Count Change Explanation

`MEASURED`: the earlier 42,860 count excluded hidden repository metadata. At
the hash boundary, inclusion of 3,892 current `.git` paths plus one VLSBench
`.git/lfs/tmp` entry that vanished before hashing explains 46,753 discoveries:
`42,860 + 3,892 + 1 = 46,753`. No generated Phase-3 output was inside the root.

A versioned check on 2026-09-06 found 46,748 current files. Six frozen-inventory
paths are now absent, all VLSBench Git LFS temporary paths (five had hashed and
one had failed), while one 918,861,900-byte Git LFS object path now exists outside
the frozen inventory. `INFERENCE`: this is consistent with Git LFS transfer/
cleanup activity, but no one-to-one temp/object mapping is claimed. It confirms
that repository internals are a mutable acquisition-workspace layer, not stable
dataset evidence.

## 8. Artifact Classification

Classification is `MEASURED` triage based on path and extension. It does not by
itself establish dataset membership.

| Category | Files | Bytes |
|---|---:|---:|
| `ARCHIVE` | 6 | 2,917,940,665 |
| `CODE` | 901 | 19,511,619 |
| `DATASET_PAYLOAD` | 37,018 | 3,905,683,615 |
| `DOCUMENTATION` | 111 | 12,207,699 |
| `ENVIRONMENT` | 23 | 1,085,158 |
| `GIT_INTERNAL` | 3,893 | 14,689,966,594 |
| `IMAGE` | 4,436 | 4,346,855,245 |
| `LICENSE` | 19 | 101,241 |
| `MANIFEST` | 6 | 17,907 |
| `METADATA` | 148 | 1,248,704,566 |
| `MODEL_OR_BINARY_ARTIFACT` | 21 | 31,609,203 |
| `UNKNOWN` | 171 | 39,304,504 |

No `__pycache__`, `node_modules`, virtual-environment, cache, or Phase-3 output
category was found as a material separate population. Repository internals are
the main non-payload mass and were intentionally retained, not deleted.

## 9. Inventory Integrity

`VERIFIED`: the CSV has 46,753 data rows: 46,752 `HASHED_VERIFIED` and one
failed row. Summed bytes equal 27,212,988,016. Re-hashing the inventory produced
the recorded SHA-256. Seven key Pilot-01 local files still match their frozen
inventory hashes. The existing inventory was not overwritten. `MEASURED`: the
current root differs only at the seven VLSBench Git LFS internal paths described
in Section 7; this drift is preserved in a new report, not folded into version 0.1.

## 10. Pilot Input Snapshot

`VERIFIED`: `PILOT-01_input_snapshot_v0.2.json` binds the inventory hash, six
dataset IDs, root, timestamp, full and selected artifact/byte totals, failures,
manifest and config hashes, tool versions, Python 3.11.7, Windows platform,
reconciliation, and post-freeze drift record. The original v0.1 snapshot is
preserved. The forensic run additionally records output hashes and its run ID.

## 11. Dataset Identity Summary

| IDs | Identity / local root | Files | Bytes | Revision status |
|---|---|---:|---:|---|
| `DS-TXT-013`, `014` | AdvBench/GCG, `GitHub/LLM-Attacks` | 66 | 469,635 | repository commit `VERIFIED`; generated artifact local equivalent `MISSING` |
| `DS-TXT-015` | AutoDAN, `GitHub/AutoDAN` | 44 | 1,196,273 | repository commit `VERIFIED`; generated output set `UNKNOWN` |
| `DS-TXT-007` | HarmBench, `GitHub/HarmBench` | 459 | 490,320,645 | repository commit `VERIFIED`; component versions `PARTIAL` |
| `DS-TXT-008` | JailbreakBench, `GitHub/JailbreakBench` | 80 | 3,814,390 | code commit `VERIFIED`; separate data revision from pinned evidence |
| `DS-TXT-009` | XSTest, `GitHub/XSTest` | 52 | 6,687,824 | repository commit `VERIFIED` |

The v0.2 detailed summary lists source URLs, revisions, primary data, support,
license, documentation, archive, unknown, missing, and failure fields in
`01_acquisition/manifests/PILOT-01_post_hash/PILOT-01_dataset_inventory_summary_v0.2.json`.
The original root-level v0.1 summary is preserved.

## 12. Version / Revision Evidence

| Source layer | Revision | State |
|---|---|---|
| llm-attacks repository | `098262edf85f807224e70ecd87b9d83716bf6b73` | `VERIFIED`, local clean HEAD |
| AutoDAN repository | `34062e964185693e81a6775b4f0d00bfd7507612` | `VERIFIED`, local clean HEAD |
| HarmBench repository | `8e1604d1171fe8a48d8febecd22f600e462bdcdd` | `VERIFIED`, local clean HEAD |
| JailbreakBench code repository | `23dbdf6b19650521604456229bc1d9c4156c85c1` | `VERIFIED`, local clean HEAD |
| JBB-Behaviors dataset | `886acc352a31533ffbcf4ef22c744658688086fc` | `VERIFIED` for pinned evidence; local bundle equivalent not identified |
| JBB artifact repository | `909e68c01d94222b8ad2e397a017e2e12e2adb73` | `VERIFIED` for pinned evidence; local bundle equivalent not identified |
| XSTest repository | `d7bb5bd738c1fcbc36edd83d5e7d1b71a3e2d84d` | `VERIFIED`, local clean HEAD |

Repository commit, dataset revision, paper version, and artifact bytes are kept
separate. Formal dataset release dates and independent dataset version labels are
`UNKNOWN` where the sources do not prove them.

## 13. Raw Immutability

`VERIFIED`: processing re-hashed each selected pinned raw artifact before use and
aborted on mismatch. The pre-update Pilot files carry read-only attributes and
SHA-256 controls. The five Pilot-01 Commander repository working trees remain
clean at their recorded HEADs. Seven key current local hashes match the frozen
inventory. `MEASURED`: VLSBench Git LFS internals outside Pilot-01 changed after
the freeze; no selected Pilot payload change was identified.

The reconciliation found three byte-identical pairs and four byte-different but
N1-identical pairs: AdvBench, the AutoDAN AdvBench copy, the AutoDAN seed, and
XSTest have CRLF checkout differences. This is not claimed as byte identity.
All outputs were written under `PHASE-3`; no raw file was rewritten.

## 14. Canonical Schema Results

`MEASURED`: 3,060 JSONL analytical records were created. Each includes a
deterministic sample ID, source dataset/artifact/revision/hash/locator, original
record and labels, raw text/response, base behavior and adversarial prompt fields,
explicit normalized-label `UNKNOWN` states, generation and lineage fields,
rights/PII/governance states, canonical hashes, and an optional deterministic
N1 duplicate-cluster ID.

`VERIFIED`: JBB judge and GCG records analyze `prompt` as adversarial text while
preserving `goal` as base behavior. This avoids conflating transformed attacks
with their upstream behaviors. Schema status is `WORKABLE_WITH_CHANGE_PROPOSAL`.

## 15. N0/N1/N2 Canonicalization

- `N0`, `CANON-N0-v0.1`: source-faithful decoded text.
- `N1`, `CANON-N1-v0.1`: Unicode NFC plus CRLF/CR to LF.
- `N2`, `CANON-N2-v0.1`: N1 plus Unicode-aware whitespace-run collapse and trim.

`VERIFIED`: case, punctuation, homoglyphs, zero-width characters, and other
potential attack features are preserved. N2 is comparison-only. Original text is
never overwritten.

## 16. Data Quality Results

| Artifact group | Records | Valid | Null/empty | Missing IDs | N0 length range |
|---|---:|---:|---:|---:|---:|
| AdvBench | 520 | 520 | 0 | 520 | 32-156 |
| AutoDAN AdvBench input | 520 | 520 | 0 | 520 | 32-156 |
| HarmBench all / TDC / AdvBench | 970 | 970 | 0 | 0 | 23-209 |
| JBB harmful / benign / judge | 500 | 500 | 0 | 0 | 14-2,236 |
| JBB GCG artifact | 100 | 100 | 0 | 0 | 121-257 |
| XSTest | 450 | 450 | 0 | 0 | 12-99 |

`MEASURED`: zero malformed, encoding-failed, unexpected-schema, under-four-
character, over-4,096-character, or duplicate-ID records were observed in the
adapted inputs. AdvBench supplies no source IDs, so reversible row locators are
used. Source-label absence is recorded but is often `NOT_APPLICABLE`; normalized
label qualification and invalid-reference checks remain `NOT_MEASURED`. The
AutoDAN 300-byte seed is `NOT_APPLICABLE` as a row dataset.

## 17. Exact Duplicate Results

`MEASURED`: N0, N1, and N2 each produced 649 clusters and 1,834 participating
records. Cluster sizes were: 124 size-two, 514 size-three, and 11 size-four.
Within a nominal dataset ID, only HarmBench had duplicates: 22 clusters and 46
participating records. The other five dataset IDs had none internally. Most
duplication therefore reflects cross-artifact or cross-dataset reuse.

## 18. Cross-Dataset Exact Overlap

Intersections are unique shared hashes. Percentages are N1 directional matched
records; N0 and N2 percentages are identical for this pilot.

| A | B | A n | B n | N0 | N1 | N2 | A to B | B to A |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| AdvBench | GCG | 520 | 100 | 0 | 0 | 0 | 0% | 0% |
| AdvBench | AutoDAN | 520 | 520 | 520 | 520 | 520 | 100% | 100% |
| AdvBench | HarmBench | 520 | 970 | 520 | 520 | 520 | 100% | 53.61% |
| AdvBench | JBB | 520 | 500 | 11 | 11 | 11 | 2.12% | 2.20% |
| AdvBench | XSTest | 520 | 450 | 0 | 0 | 0 | 0% | 0% |
| GCG | AutoDAN | 100 | 520 | 0 | 0 | 0 | 0% | 0% |
| GCG | HarmBench | 100 | 970 | 0 | 0 | 0 | 0% | 0% |
| GCG | JBB | 100 | 500 | 0 | 0 | 0 | 0% | 0% |
| GCG | XSTest | 100 | 450 | 0 | 0 | 0 | 0% | 0% |
| AutoDAN | HarmBench | 520 | 970 | 520 | 520 | 520 | 100% | 53.61% |
| AutoDAN | JBB | 520 | 500 | 11 | 11 | 11 | 2.12% | 2.20% |
| AutoDAN | XSTest | 520 | 450 | 0 | 0 | 0 | 0% | 0% |
| HarmBench | JBB | 970 | 500 | 21 | 21 | 21 | 2.47% | 4.20% |
| HarmBench | XSTest | 970 | 450 | 0 | 0 | 0 | 0% | 0% |
| JBB | XSTest | 500 | 450 | 100 | 100 | 100 | 20.00% | 22.22% |

JBB's denominator combines harmful, benign, and judge-comparison artifacts;
HarmBench combines all-text, TDC, and AdvBench component files. Percentages must
not be read as independent benchmark-wide prevalence estimates.

## 19. Near-Duplicate Results

`MEASURED`: tokenizer `unicode_word_casefold_v0.1`, word 3-grams, 128-permutation
deterministic MinHash, 32 bands of four rows, seed 1701, LSH candidate generation,
then exact Jaccard verification. LSH candidates are not results until verified.

At the reporting sensitivity point 0.8, nonzero directional overlap was:

| Pair | A to B | B to A |
|---|---:|---:|
| AdvBench / AutoDAN | 100% | 100% |
| AdvBench / HarmBench | 100% | 53.61% |
| AdvBench / JBB | 2.50% | 2.40% |
| AutoDAN / HarmBench | 100% | 53.61% |
| AutoDAN / JBB | 2.50% | 2.40% |
| HarmBench / JBB | 2.89% | 4.60% |
| JBB / XSTest | 20.00% | 22.22% |

All other pairs were zero at 0.8. Threshold 0.8 is not a final global decision.

## 20. Semantic-Overlap Results

`NOT_MEASURED`: a cached `WhereIsAI/UAE-Large-V1` directory was observed, but
the active environment lacks an approved pinned inference stack (`torch`,
`transformers`, `sentence-transformers`, `tokenizers`, `safetensors`, and ONNX
Runtime were unavailable). Installing dependencies or accessing the network was
not authorized. No lexical score is relabeled as semantic evidence. This result
does not imply semantic independence.

## 21. Provenance Findings

- `VERIFIED`: llm-attacks is the official GCG implementation and documents
  AdvBench as an experiment input.
- `VERIFIED`: AutoDAN documents llm-attacks dependence and includes an AdvBench
  input copy.
- `VERIFIED`: HarmBench contains an explicitly named AdvBench subset and method
  implementations for GCG/AutoDAN.
- `VERIFIED`: JBB attributes harmful behaviors to Original, AdvBench, and
  TDC/HarmBench sources; measured counts are 55, 18, and 27.
- `VERIFIED`: JBB judge documentation uses 100 benign XSTest examples and GCG
  attack prompts.
- `MEASURED`: the selected GCG artifact has 100 records, including 80 source-
  reported `jailbroken=True` and 20 `False`. This source label was not independently
  re-evaluated.

## 22. Lineage Findings

`VERIFIED` documentary and sample evidence supports AdvBench to AutoDAN input,
AdvBench to HarmBench subset, AdvBench/TDC-HarmBench to JBB behaviors, XSTest to
JBB judge comparison, and GCG to JBB artifact relationships. HarmBench's AutoDAN
relationship is a method-implementation dependency, not proof of shared generated
samples. No minimal qualified AutoDAN generated-output dataset was identified;
its generated-sample lineage is `UNKNOWN`.

Exact or near similarity alone was not upgraded to lineage. Conversely, zero
transformed-prompt equality does not negate documented behavior-level lineage.

## 23. Behavior-Level Relationships

Behavior identity uses N1 hashes of the separately preserved base behavior, not
the adversarial prompt.

| Pair | Shared behaviors | A matched | B matched | Meaning |
|---|---:|---:|---:|---|
| AdvBench / AutoDAN | 520 | 520/520 | 520/520 | identical behavior input |
| AdvBench / HarmBench | 520 | 520/520 | 520/970 | explicit reused subset |
| AdvBench / JBB | 97 | 97/520 | 161/500 | reused base behavior across JBB components |
| GCG / JBB | 95 | 95/100 | 113/500 | transformed GCG prompts retain JBB base goals |
| HarmBench / JBB | 107 | 110/970 | 171/500 | TDC/HarmBench and repeated component relations |
| JBB / XSTest | 100 | 100/500 | 100/450 | judge-related XSTest reuse |

`MEASURED`: GCG and JBB have zero exact adversarial-prompt overlap yet 95 shared
base behaviors. This demonstrates why text identity, transformation, and behavior
lineage must remain separate.

## 24. Contamination Matrix

`VERIFIED`: the machine-readable matrix contains all 15 pairs and separates raw
exact, N0/N1/N2 exact, verified lexical near, semantic status, documentary
lineage, behavior identity, and evidence state. Principal findings are:

| Pair | Exact shared | Near at 0.8 | Behavior shared | Documentary state |
|---|---:|---|---:|---|
| AdvBench / GCG | 0 | 0% / 0% | 11 | `DOCUMENTED_AND_MEASURED` method/input relation |
| AdvBench / AutoDAN | 520 | 100% / 100% | 520 | `DOCUMENTED_AND_MEASURED` |
| AdvBench / HarmBench | 520 | 100% / 53.61% | 520 | `DOCUMENTED_AND_MEASURED` |
| AdvBench / JBB | 11 | 2.50% / 2.40% | 97 | `DOCUMENTED_AND_MEASURED` |
| GCG / JBB | 0 | 0% / 0% | 95 | `DOCUMENTED_AND_MEASURED` |
| HarmBench / JBB | 21 | 2.89% / 4.60% | 107 | `DOCUMENTED_AND_MEASURED` |
| JBB / XSTest | 100 | 20.00% / 22.22% | 100 | `DOCUMENTED_AND_MEASURED` |

Other pairs remain `MEASURED` shared-upstream effects or `UNKNOWN`; the complete
zero and nonzero cells are in `11_contamination_matrix/PILOT-01_contamination_matrix.json`.

## 25. Licensing / Rights Findings

| Source | Evidence | State |
|---|---|---|
| llm-attacks / AdvBench | repository MIT; separate data scope unresolved | `UNKNOWN` |
| AutoDAN | repository MIT; AdvBench/generated-artifact rights unresolved | `QUARANTINE` |
| HarmBench | repository MIT; component/upstream rights incomplete | `QUARANTINE` |
| JBB code | MIT | `CONDITIONAL`, code only |
| JBB-Behaviors | card declares MIT; upstream rights partial | `CONDITIONAL` |
| JBB artifacts | repository MIT; behavior/model upstream terms remain | `CONDITIONAL` |
| XSTest | CC BY 4.0 with attribution | `CONDITIONAL` |

`FACT`: public availability was not treated as permission. Commercial-use and
redistribution conclusions remain `UNKNOWN`; project redistribution remains
denied by governance.

## 26. Privacy / PII Findings

`MEASURED`: a non-destructive regex screen across 3,060 analyzed prompt records
found zero email, URL, IPv4, or phone candidates. No raw PII is reproduced here.
This is not proof of absence: names, handles, contextual identifiers, and privacy
provenance remain unresolved. Overall `PII_STATUS = REVIEW_REQUIRED`; no major
Pilot-01 exposure was observed.

## 27. Dataset-Role Recommendations

These are `RECOMMENDATION` only; final constitution is `NOT_APPROVED`.

| Dataset | Recommendation |
|---|---|
| AdvBench | `QUARANTINE`; possible future development candidate after rights/split review |
| GCG artifact | `ADAPTIVE_STRESS_TEST` candidate; evaluation-only during early development |
| AutoDAN | `QUARANTINE` until a generated-output artifact and provenance are qualified |
| HarmBench | component-controlled `PRISTINE_EXTERNAL_BENCHMARK` candidate |
| JailbreakBench | aggregate-aware `PRISTINE_EXTERNAL_BENCHMARK` candidate |
| XSTest | `HARD_BENIGN_FPR_BENCHMARK` and pristine candidate |

## 28. Unknowns / Unverified Claims

- Exact dataset releases and release dates distinct from repository commits.
- AdvBench's dataset/content license scope and incorporated upstream rights.
- Full component rights for HarmBench and JBB.
- Identity and configuration of an intended AutoDAN generated-output set.
- Generator model/configuration for records where the source does not supply it.
- Normalized binary, attack-family, and subtype labels.
- Comprehensive PII status.
- Embedding-based semantic overlap.
- Independence of any nominal dataset not supported by the measured/documented graph.

## 29. Risks

Primary residual risks are rights uncertainty, aggregate-source contamination,
JBB/HarmBench denominator interpretation, absent AutoDAN generated outputs,
semantic-stage incompleteness, threshold sensitivity, contextual PII missed by
regex, and accidental treatment of 14.69 GB of mutable Git internals as payload.
Post-freeze VLSBench LFS path drift shows that a future inventory should freeze
dataset artifacts separately from working-copy internals. The four line-ending-
different local files also show why byte identity and text equivalence must remain
distinct.

## 30. Reproducibility Artifacts

Produced or updated:

- acquisition manifest and hashes: `01_acquisition/manifests/PILOT-01_manifest.json`,
  `01_acquisition/hashes/PILOT-01_hashes.csv`
- full inventory and summary: `01_acquisition/hashes/local_bundle_inventory.csv`,
  `01_acquisition/manifests/local_bundle_inventory_summary.json`
- post-hash classification, failure, snapshot, dataset summary, and reconciliation:
  `01_acquisition/manifests/PILOT-01_post_hash/`
- versioned post-freeze boundary drift:
  `01_acquisition/manifests/PILOT-01_post_hash/PILOT-01_inventory_drift_20260906.json`
- source evidence and registry: `01_acquisition/source_evidence/PILOT-01/sources.json`,
  `02_registry/PILOT-01_registry.json`
- schema and normalized records: `03_schema/`
- quality, exact, near, semantic, lineage, rights/privacy, role, and contamination
  outputs in numbered stage directories
- configuration: `configs/PILOT-01_forensics.json`
- acquisition and forensic logs: `logs/`
- scripts: `scripts/pilot01_acquire.py`, `inventory_local_bundle.py`,
  `post_hash_audit.py`, `reconcile_pilot01_inputs.py`,
  `audit_inventory_drift.py`, `pilot01_forensics.py`
- tests: `tests/test_pilot01.py`

Latest forensic run status is `SUCCESS`; normalized output SHA-256 is recorded in
`logs/PILOT-01_forensic_run.json`. Ten unit/infrastructure tests pass.

## 31. Git Artifact Classification

`RECOMMENDATION`: track scripts, configs, schemas, small manifests, hash tables,
source metadata, reports, and tests. Do not track raw payloads, archives, model
weights, embedding matrices, indexes, temporary files, or caches. Review the
3.7 MB normalized JSONL and large exact/near pair-detail JSON before Git. The
detailed classification is `reports/PILOT-01_GIT_ARTIFACT_CLASSIFICATION.md`.
No `.gitignore` modification or Git initialization was performed by Pilot-01.

## 32. Pilot Methodology Assessment

`VERIFIED` successful: immutable versioned inventory evidence, explicit failure handling, source
and revision capture, raw integrity checks, source-preserving schema, measurable
quality, exact overlap, reproducible MinHash/LSH plus exact verification,
directional contamination, lineage/similarity separation, and honest legal/privacy
states.

`PARTIAL`: the acquisition root itself is not static because it contains live Git
LFS internals; dataset-level release proof, comprehensive rights/PII qualification,
and semantic overlap are also incomplete. The methodology is useful and reproducible
for the tested stages, but future inventories should separate payload evidence from
repository state and resolve the semantic dependency and schema v0.2 decisions.

## 33. Commander Decisions Required

1. Accept, revise, or reject Pilot-01 methodology and this report.
2. Confirm whether the four pre-update JBB/GCG pinned artifacts may remain the
   controlled Pilot inputs where no Commander-bundle equivalent was identified.
3. Approve a pinned local semantic inference environment, or explicitly accept
   `NOT_MEASURED` for Pilot-01.
4. Accept or revise the schema v0.2 proposal and role recommendations.
5. Decide whether rights/PII review should deepen before any expansion.
6. Separately authorize Wave 2 if and only if the pilot is accepted.

## 34. Recommended Next Step

`RECOMMENDATION`: Commander reviews the five substantive decisions above,
preserves the current inventory hash and Pilot artifacts, and either authorizes a
bounded semantic completion run or accepts that limitation. Do not change dataset
roles or expand acquisition during review.

# STOP

Pilot-01 forensic analysis is complete. **COMMANDER DECISION REQUIRED.** No Wave
2, training, split construction, calibration, or pristine benchmark development
use begins automatically.
