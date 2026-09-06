# Phase-3 Readiness & Execution Plan

Status: **WAVE 2 FORENSICS COMPLETE - AWAITING COMMANDER REVIEW**
Workspace phase: Wave 2 final stop gate
Dataset acquisition performed: **COMMANDER-LOCAL BUNDLE INVENTORIED; NO POST-UPDATE DOWNLOAD**

Execution-state authority is recorded in `COMMANDER_DECISIONS.md`. Pilot-01 and
Wave 2 results are in `../reports/`. This original readiness
plan remains the scope baseline; the recorded Commander decisions and report
supersede its pre-authorization execution wording.

## 1. Mission Restatement

This workspace will build the evidence needed to decide a defensible dataset
constitution for the text-first adversarial-attack detection capstone. It will
freeze source versions, preserve raw artifacts, qualify schema and data quality,
measure exact, lexical, semantic, and lineage overlap, investigate privacy and
usage rights, characterize coverage, and recommend experimental roles.

The output is evidence and recommendations for Commander review. It is not a
final training, validation, test, benchmark, or quarantine decision.

## 2. Scope Boundary

### In scope

- Controlled, revision-pinned acquisition after readiness approval.
- Artifact integrity records, source snapshots, and machine-readable manifests.
- Source-preserving normalization into a canonical analytical schema.
- Data quality, exact duplicate, near-duplicate, semantic-overlap, and lineage analysis.
- Non-destructive privacy/PII screening and evidence-backed licensing review.
- Distribution, threat-coverage, and upstream-behaviour contribution analysis.
- Cross-dataset contamination matrices and experimental-role recommendations.
- Explicit reporting of uncertainty, conflicts, failures, and critical coverage gaps.

### Outside this workspace's authority

- Finalizing any training, validation, internal test, or external benchmark set.
- Moving pristine candidates into development or model-selection workflows.
- Training detectors, guard models, fusion models, or tuning thresholds.
- Generating synthetic training data or redefining the approved attack taxonomy.
- Treating attack attempts as successful compromises without source evidence.
- Declaring legal clearance, provenance, independence, or labels without evidence.
- Expanding multimodal work into the mandatory primary text scope.

## 3. Existing Dataset Portfolio

Classification below is provisional and normalizes only the supplied portfolio.
"Benchmark" describes apparent packaging or intended use, not an approved role.

| Candidate | Modality | Provisional type | Benchmark signal | Identity/provenance caution |
|---|---|---|---|---|
| WildJailbreak | Text | Dataset/aggregate | Yes | Aggregate lineage must be verified |
| WildGuardMix | Text | Dataset/aggregate | Yes | Component-level lineage must be verified |
| Tensor Trust | Text | Dataset/benchmark | Yes; pristine candidate | Preserve participant/game dependencies |
| BIPIA | Text | Dataset/benchmark | Yes; pristine candidate | Task and split lineage must be verified |
| InjecAgent | Text | Dataset/benchmark | Yes; pristine candidate | Agent/task dependencies require review |
| AgentDojo | Text | Dataset/benchmark | Yes; pristine candidate | Scenario/tool structure requires review |
| HarmBench | Text | Benchmark/behaviour suite | Yes; selected pristine candidate | TDC/JBB relationships must be verified |
| JailbreakBench / JBB | Text | Aggregate benchmark | Yes; selected pristine candidate | AdvBench, HarmBench/TDC, XSTest links |
| XSTest | Text | Hard-benign/safety benchmark | Yes; pristine candidate | JBB evaluation/judging association |
| OR-Bench | Text | Over-refusal benchmark | Yes; pristine candidate | Exact edition and components unknown |
| LLMail-Inject | Text | Adaptive-attack benchmark | Yes; pristine/adaptive candidate | Team, trajectory, temporal dependence |
| Agent Security Bench / ASB | Text | Agent-security benchmark | Yes | Exact project identity/version to verify |
| AdvBench | Text | Behaviour dataset | Yes | Upstream base for derived attacks and JBB |
| GCG-related/generated material | Text | Attack method/derived artifacts | Not inherently independent | Exact artifact identity unresolved |
| AutoDAN-related/generated material | Text | Attack method/derived artifacts | Not inherently independent | Exact artifact identity unresolved |
| SALAD | Text | Dataset/benchmark | Yes | Exact release/components to verify |
| Do-Not-Answer | Text | Safety dataset/benchmark | Yes | Label semantics and downstream reuse |
| deepset prompt-injection data | Text | Dataset | Possibly | Exact repository/config/revision unresolved |
| WASP | Text | Uncertain dataset/benchmark | Uncertain | Acronym/project identity must be resolved |
| JailBreakV-28K | Multimodal | Aggregate dataset/benchmark | Yes | MM-SafetyBench and FigStep lineage |
| CyberSecEval 3 VPI | Multimodal | Benchmark component | Yes; pristine candidate | Exact component/release to verify |
| VLSBench | Multimodal | Benchmark | Yes; pristine candidate | Provenance/licensing unresolved |
| MM-SafetyBench | Multimodal | Benchmark/source dataset | Yes | Reported upstream relation to JailBreakV |
| FigStep / SafeBench | Multimodal | Method and/or derived benchmark | Yes/uncertain | Identity and naming relation must be resolved |
| VLGuard | Multimodal | Dataset/benchmark | Yes | Dataset/model/repository rights separation |

The uncertain-classification set is therefore GCG material, AutoDAN material,
WASP, and FigStep/SafeBench until artifact identity is established. ASB, OR-Bench,
SALAD, and the deepset collection also require exact-edition resolution, but are
provisionally treated as datasets or benchmarks rather than new discoveries.

## 4. Proposed Dataset ID Registry

IDs are stable inventory identifiers only. They do not encode experimental role,
legal status, quality, priority, or independence.

| ID | Candidate | Class |
|---|---|---|
| DS-TXT-001 | WildJailbreak | text dataset/aggregate |
| DS-TXT-002 | WildGuardMix | text dataset/aggregate |
| DS-TXT-003 | Tensor Trust | text benchmark |
| DS-TXT-004 | BIPIA | text benchmark |
| DS-TXT-005 | InjecAgent | text benchmark |
| DS-TXT-006 | AgentDojo | text benchmark |
| DS-TXT-007 | HarmBench | text benchmark/suite |
| DS-TXT-008 | JailbreakBench / JBB | text aggregate benchmark |
| DS-TXT-009 | XSTest | text hard-benign benchmark |
| DS-TXT-010 | OR-Bench | text over-refusal benchmark |
| DS-TXT-011 | LLMail-Inject | text adaptive benchmark |
| DS-TXT-012 | Agent Security Bench / ASB | text agent benchmark |
| DS-TXT-013 | AdvBench | text behaviour dataset |
| DS-TXT-014 | GCG-related/generated material | text method/derived artifact |
| DS-TXT-015 | AutoDAN-related/generated material | text method/derived artifact |
| DS-TXT-016 | SALAD | text dataset/benchmark |
| DS-TXT-017 | Do-Not-Answer | text dataset/benchmark |
| DS-TXT-018 | deepset prompt-injection data | text dataset |
| DS-TXT-019 | WASP | text, classification uncertain |
| DS-MM-001 | JailBreakV-28K | multimodal aggregate benchmark |
| DS-MM-002 | CyberSecEval 3 VPI | multimodal benchmark component |
| DS-MM-003 | VLSBench | multimodal benchmark |
| DS-MM-004 | MM-SafetyBench | multimodal benchmark/source |
| DS-MM-005 | FigStep / SafeBench | multimodal method/derived artifact |
| DS-MM-006 | VLGuard | multimodal dataset/benchmark |

Registry policy: aliases remain attached to one ID until evidence establishes
distinct artifacts. If evidence later proves that an entry contains independently
versioned artifacts, child artifact IDs may be added without renumbering existing IDs.

## 5. Acquisition Order

### Gate 0: identity, terms, and source resolution

Before downloading dataset payloads, resolve authoritative source, exact artifact,
version mechanism, dataset-specific terms, and upstream-rights signals for every
candidate. Prioritize ambiguous identities (WASP, GCG material, AutoDAN material,
FigStep/SafeBench, ASB) and aggregate datasets. This prevents downloading or
misclassifying the wrong artifact.

### Wave 1: small lineage anchors and contamination controls

Investigate AdvBench, HarmBench, JailbreakBench, XSTest, GCG material, and AutoDAN
material together. They form the known text lineage cluster and are needed to
design sample-level lineage keys before aggregate acquisition. Metadata and source
evidence for pristine candidates may be inspected, but their data remains isolated.

### Wave 2: primary text aggregates and candidate development sources

Investigate WildJailbreak, WildGuardMix, SALAD, Do-Not-Answer, and deepset
prompt-injection data. Acquire only sources whose identity, revision, and lawful
research handling are sufficiently documented. Start with the smallest technically
simple artifact to validate the manifest, hashing, raw immutability, and adapter flow.

### Wave 3: pristine, adaptive, and structured-agent benchmarks

Investigate Tensor Trust, BIPIA, InjecAgent, AgentDojo, OR-Bench, LLMail-Inject,
ASB, and WASP. Their preservation status and non-row dependencies require adapters
that retain team, scenario, task, trajectory, and temporal fields. LLMail-Inject
must preserve attack-attempt and target-compromise outcomes separately.

### Wave 4: multimodal research extension

Investigate CyberSecEval 3 VPI, VLSBench, MM-SafetyBench, FigStep/SafeBench,
JailBreakV-28K, and VLGuard only after the primary text workflow is validated.
Within this wave, resolve the upstream sources before the JailBreakV aggregate.
This keeps the optional extension from delaying primary-scope evidence work.

No wave authorizes bulk acquisition. Each source remains subject to a per-source
identity, terms, revision, and storage check.

## 6. Workspace Structure

```text
PHASE-3/
|-- 00_governance/
|   `-- PHASE-3_READINESS_AND_EXECUTION_PLAN.md
|-- 01_acquisition/
|   |-- manifests/
|   |-- hashes/
|   |-- source_evidence/
|   `-- raw/                 # immutable, excluded from derived processing
|-- 02_registry/
|-- 03_schema/
|-- 04_quality/
|-- 05_exact_duplicates/
|-- 06_near_duplicates/
|-- 07_semantic_overlap/
|-- 08_provenance/
|-- 09_legal_privacy/
|-- 10_distribution/
|-- 11_contamination_matrix/
|-- 12_constitution_recommendation/
|-- configs/
|-- scripts/
|-- logs/
|-- reports/
`-- tests/
```

Planned conventions:

- Raw artifacts are content-addressed or revision-scoped and never edited in place.
- Source evidence stores dataset cards, terms, citations, and revision metadata
  separately from payloads, with source URLs and retrieval timestamps.
- Normalized records and analytical outputs live in the relevant numbered stage.
- Every run emits configuration, input/output hashes, environment metadata, and logs.
- Machine-readable artifacts use JSON/JSONL or Parquet where appropriate; CSV is
  reserved for flat review tables. Schema definitions use JSON Schema.

## 7. Canonical Schema v0.1

The canonical record is an analytical projection that references, but never
replaces, the original record. Missing claims use null plus an explicit status
where ambiguity matters. Source-provided values and analyst-derived values are
kept in separate namespaces.

### Record identity and source-preserved fields

| Field | Meaning |
|---|---|
| `schema_version` | Canonical schema version |
| `sample_id` | Deterministic internal ID derived from dataset ID, artifact revision, and source locator; never presented as a source ID |
| `source.dataset_id` | Stable registry ID |
| `source.dataset_name` | Recorded source name |
| `source.version` | Release, commit, revision, or explicit `NOT_VERIFIED` |
| `source.artifact_sha256` | Hash of immutable containing artifact |
| `source.record_locator` | Reversible file/member/row locator |
| `source.original_sample_id` | Source ID exactly as supplied, nullable |
| `source.original_record` | Lossless source record or immutable reference to it |
| `source.prompt` | Prompt text exactly as supplied, nullable |
| `source.response` | Response text exactly as supplied, nullable |
| `source.label` | Original label and representation, nullable |
| `source.metadata` | Namespaced source fields not mapped above |

### Evidence-backed normalized fields

These fields may map source semantics but retain mapping evidence and never alter
the source values: `labels.binary_label`, `labels.attack_family`,
`labels.attack_subtype`, `labels.attack_attempt`, `labels.attack_success`,
`generation.origin_type`, `generation.generator_model`, `generation.attack_method`,
`lineage.upstream_dataset`, `lineage.upstream_version`,
`lineage.original_sample_id`, `lineage.base_behavior_id`,
`lineage.transformation`, `rights.dataset_license`, `rights.upstream_license`, and
`citation`. Controlled values include `UNKNOWN` where the source cannot support a claim.

### Derived forensic fields

| Field group | Contents |
|---|---|
| `forensics.raw_text_sha256` | Hash over defined raw text bytes/encoding |
| `forensics.canonicalization_id` | Versioned normalization procedure |
| `forensics.canonical_text_sha256` | Hash used only for comparison |
| `forensics.duplicate_cluster_ids` | Raw and canonical exact clusters |
| `forensics.near_duplicate` | Method, threshold, cluster and candidate-pair references |
| `forensics.semantic_overlap` | Model revision, metric, score and candidate relation |
| `forensics.encoding_flags` | Non-destructive encoding/format observations |
| `privacy.pii_flags` | Detector type, span reference, confidence, review status |
| `quality.flags` | Parse, completeness, ID, schema and anomaly findings |
| `governance.train_allowed` | Tri-state recommendation/evidence status, not final authority |
| `governance.evaluation_only` | Tri-state recommendation/evidence status |
| `governance.quarantine_status` | Zero or more review reasons |
| `governance.provenance_status` | `COMPLETE`, `PARTIAL`, `UNKNOWN`, or `NOT_VERIFIED` |

Lineage relationships additionally carry evidence strength (`VERIFIED`,
`STRONG_EVIDENCE`, `INFERRED`, `UNKNOWN`), evidence references, reviewer status,
and timestamps. Similarity alone cannot set a lineage relationship to `VERIFIED`.

## 8. Forensic Pipeline v0.1

1. **Acquire and freeze.** Resolve an immutable revision, retrieve into a staging
   location, record transport/source metadata, compute SHA-256, verify expected
   files, and promote to read-only raw storage only after manifest validation.
2. **Inventory and raw hashing.** Hash artifacts and individual record text using
   documented UTF-8 byte construction. Preserve archive-member and row locators.
3. **Canonicalize for comparison.** Produce versioned N0 (raw decoded text) and N1
   views. Proposed N1 applies Unicode NFC and line-ending normalization; whitespace
   collapse is a separate N2 sensitivity view because spacing and Unicode can be
   attack features. Originals are never overwritten.
4. **Exact duplicates.** Group SHA-256 values for raw and each canonical view.
   Report within- and cross-dataset counts, denominators, cluster membership, and
   pairwise intersections. Do not delete duplicate records.
5. **Lexical near duplicates.** Tokenize with a documented Unicode-aware procedure,
   generate word and/or character shingles, then use MinHash + LSH for candidate
   generation and exact Jaccard scoring for verification. Initial thresholds are
   hypotheses, not decisions; evaluate sensitivity at multiple thresholds and retain
   all candidate-pair provenance.
6. **Semantic overlap.** Use a locally pinned sentence-embedding model where feasible,
   record model/revision and preprocessing, retrieve candidates with an exact or
   version-pinned ANN index, and report cosine-similarity sensitivity. Similarity
   proposes `SEMANTICALLY_RELATED`; human/evidence review determines stronger labels.
   Embedding model selection must not depend on pristine benchmark performance.
7. **Lineage reconstruction.** Combine source documentation, explicit IDs, mapping
   files, generation metadata, and verified overlap into dataset- and sample-level
   edges. Store claim, evidence URI/artifact hash, strength, and unresolved conflict.
8. **Privacy and legal review.** Run non-destructive pattern/NER candidate screening
   with span-level evidence and manual-review states. Separately record repository,
   dataset, upstream, and content terms; absence of terms yields `UNKNOWN` or
   quarantine, never implicit permission.
9. **Distribution and coverage.** Calculate record and source contributions only for
   evidence-supported labels. Report unknowns explicitly and distinguish raw volume
   from unique canonical records, duplicate clusters, and base behaviours.
10. **Contamination analysis.** Produce pairwise matrices for raw exact, canonical
    exact, verified lexical near, semantic candidates, and documented lineage.
    Matrices include raw counts, row-normalized percentages in both directions,
    denominators, methods, thresholds, and links to traceable pairs/clusters.

Candidate implementation stack: Python with standard cryptographic hashing,
`pyarrow`/Parquet for analytical tables, `jsonschema` for validation,
`datasketch` for MinHash/LSH, and a pinned sentence-transformer plus FAISS or an
exact cosine baseline for semantic candidates. Dependencies will be locked only
after environment and licensing review. Fixed seeds and runtime/hardware metadata
will be captured for stochastic or approximate procedures.

## 9. Risk Register

| ID | Risk | Consequence | Initial control | Residual status |
|---|---|---|---|---|
| R-01 | Dataset and repository licenses differ | Unauthorized use/redistribution | Evidence fields for each rights layer; quarantine unknowns | Open |
| R-02 | Mutable branches or dataset scripts | Irreproducible corpus | Pin commit/revision and hash resolved artifacts | Open |
| R-03 | Aggregate datasets hide upstream reuse | False unseen-source claims | Sample-level lineage and cross-source overlap | Open |
| R-04 | Random row splits break participant/trajectory dependence | Inflated evaluation | Preserve group/time keys; no split creation in Phase 3 readiness | Open |
| R-05 | Pristine benchmark exposure during development | Benchmark becomes development data | Isolated storage, role flags, access/run logs | Open |
| R-06 | Canonicalization erases adversarial signal | False duplicates and altered evidence | Immutable originals; versioned multi-view normalization | Open |
| R-07 | Near-duplicate threshold arbitrariness | Constitution changes with threshold | Sensitivity analysis and traceable pairs | Open |
| R-08 | Embedding similarity is mistaken for lineage | Unsupported provenance claims | Candidate-only semantics; documentary/sample mapping required | Open |
| R-09 | Embedding model has unknown benchmark exposure | Hidden analytical bias | Pin model, document training provenance where available, test alternatives | Open |
| R-10 | Attack-attempt and success labels collapse | Invalid adaptive-attack conclusions | Separate fields and source-semantic mappings | Open |
| R-11 | PII in participant or wild data | Privacy and redistribution harm | Non-destructive screening, restricted raw storage, review workflow | Open |
| R-12 | Safety content triggers scanners or unsafe handling | Operational disruption | Controlled paths, hashes, least-privilege access, no execution of content | Open |
| R-13 | Large artifacts exceed storage/compute | Incomplete or biased analysis | Metadata-first sizing, staged waves, scalable candidate generation | Open |
| R-14 | Ambiguous names resolve to wrong projects | Invalid evidence chain | Identity gate using authoritative sources before acquisition | Open |
| R-15 | Source labels/taxonomies are incompatible | Fabricated coverage comparison | Preserve originals; evidence-backed mappings with unknown state | Open |
| R-16 | Negative overlap is read as independence | Overstated generalization | Report method detection limits and `UNKNOWN`, not independence | Open |
| R-17 | Multimodal extension diverts primary scope | Delayed or diluted text study | Schedule Wave 4 after text pipeline validation | Open |
| R-18 | Raw data is accidentally modified | Broken integrity and auditability | Staging-to-immutable promotion and recurring hash verification | Open |

## 10. Blockers

Pilot-01 completed without a validity-blocking hashing failure. Embedding-based
semantic overlap remains `NOT_MEASURED` because an approved pinned inference
environment was unavailable. Dataset-specific rights and PII uncertainty remain
explicit review items. Wave 2 and all model work remain blocked by the final gate.

## 11. Decisions Recorded

1. Readiness plan and stable ID registry: **APPROVED** (`DEC-P3-001`).
2. Pristine-candidate controls: **APPROVED WITH MODIFICATION** (`DEC-P3-002`).
3. RAW/FORENSIC/EXPERIMENTAL separation and no-redistribution default:
   **APPROVED WITH MODIFICATION** (`DEC-P3-003`).
4. AdvBench/GCG/AutoDAN/HarmBench/JBB/XSTest Pilot-01 cluster:
   **APPROVED** (`DEC-P3-004`).
5. Existing Commander-local bundle made authoritative; new payload downloads
   disabled without separate approval.

These decisions do not approve a dataset constitution, split strategy, or model use.

## 12. Current Next Action

Review `../reports/PILOT-01_FORENSIC_REPORT.md`, decide whether to authorize a
pinned semantic-overlap environment, accept or revise the schema and provisional
role recommendations, and separately decide whether Wave 2 may begin.

## Commander Review Gate

**COMMANDER DECISION REQUIRED**

Pilot-01 has stopped. Do not begin Wave 2, additional payload acquisition, model
development, training, threshold tuning, synthetic-data generation, or final
dataset-role assignment without a new Commander decision.
