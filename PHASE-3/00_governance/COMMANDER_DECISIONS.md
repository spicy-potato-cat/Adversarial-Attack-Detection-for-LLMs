# Commander Decisions

## Pilot 01 Authorization

Pilot run identifier: `PILOT-01`  
Authorization received: 2026-09-02  
Authorization scope: AdvBench / GCG / AutoDAN / HarmBench / JailbreakBench / XSTest lineage cluster

## DEC-P3-001 - Readiness Plan & Dataset Registry

Status: **APPROVED**

- The Phase-3 Readiness & Execution Plan and stable dataset ID registry are approved.
- IDs are permanent inventory identifiers and do not imply role, legal clearance,
  independence, quality, or training eligibility.
- Existing IDs must not be recycled or renumbered.
- Child artifact IDs may be introduced only when evidence establishes independently
  versioned artifacts under an existing entry.

Pilot IDs:

| Dataset ID | Entry |
|---|---|
| `DS-TXT-007` | HarmBench |
| `DS-TXT-008` | JailbreakBench / JBB |
| `DS-TXT-009` | XSTest |
| `DS-TXT-013` | AdvBench |
| `DS-TXT-014` | GCG-related/generated material |
| `DS-TXT-015` | AutoDAN-related/generated material |

## DEC-P3-002 - Pristine Benchmark Preservation

Status: **APPROVED WITH MODIFICATION**

Pristine benchmark membership remains provisional. Forensic, metadata,
provenance, and quality analysis are allowed. Model evaluation is not authorized.

| Governance field | Required state |
|---|---|
| `benchmark_status` | `PRISTINE_CANDIDATE` where applicable |
| `training_access` | `DENIED` |
| `fine_tuning_access` | `DENIED` |
| `fusion_training_access` | `DENIED` |
| `calibration_access` | `DENIED` |
| `threshold_tuning_access` | `DENIED` |
| `hyperparameter_selection_access` | `DENIED` |
| `model_selection_access` | `DENIED` |
| `forensic_analysis_access` | `ALLOWED` |
| `metadata_analysis_access` | `ALLOWED` |
| `provenance_analysis_access` | `ALLOWED` |
| `quality_analysis_access` | `ALLOWED` |

Future benchmark access and execution must be auditable because repeated model
evaluation can contaminate a benchmark through development feedback.

## DEC-P3-003 - Raw Data Access & Retention

Status: **APPROVED WITH MODIFICATION**

Three logically separated layers are required:

1. `RAW`: exact, revision-pinned and SHA-256-recorded artifacts; immutable after
   validation; least-privilege local access; never modified, silently sanitized,
   executed, or automatically treated as experimental data.
2. `FORENSIC / DERIVED`: traceable canonical records, hashes, quality findings,
   overlap candidates, lineage evidence, privacy/legal findings, distributions,
   and contamination results.
3. `EXPERIMENTAL`: only data explicitly approved by a future Commander decision
   for a defined experimental role.

Project redistribution default: **NO REDISTRIBUTION**. This is a governance rule,
not a legal conclusion. Rights and PII uncertainty must use explicit quarantine
states including `license_review`, `provenance_review`, `pii_review`, and
`upstream_rights_review`.

## DEC-P3-004 - First Forensic Pilot

Status: **APPROVED**

Pilot 01 covers only AdvBench, GCG-related/generated material,
AutoDAN-related/generated material, HarmBench, JailbreakBench/JBB, and XSTest.
Its purpose is to validate acquisition and forensic methodology on a
lineage-sensitive cluster. It does not authorize corpus construction, data
splitting, model development, model evaluation, or expansion to Waves 2-4.

## Active Execution Boundary

Authorized work is limited to source and identity resolution, documentary lineage,
manifest construction, minimal legally supportable acquisition, hashing and raw
promotion, pilot adapters and forensic analyses, reproducibility infrastructure,
and reporting. All uncertainties must remain explicit.

At completion, Pilot 01 stops for Commander review. Expansion beyond Pilot 01
requires a separate authorization.

## Commander Update - Local Bundle Acquisition Input

Status: **AUTHORITATIVE UPDATE RECEIVED 2026-09-02**

- Dataset payloads were manually acquired by the Commander under `Dataset/Raw`.
- Existing local files are the acquisition input for Phase 3 and must not be
  modified.
- Network payload acquisition is disabled unless separately approved.
- Acquisition work is documentary and forensic: inventory, source/ID mapping,
  revision evidence, SHA-256, size/structure validation, rights evidence, and
  immutable-RAW preservation.
- Canonicalization and analysis outputs must be written only under derived
  Phase-3 directories.
- Missing Pilot 01 artifacts must be reported as `MISSING` before any proposed
  download.
- All earlier governance, pristine-benchmark, STOP, and Pilot 01 scope controls
  remain active.

Implementation note: the initial minimal network acquisition completed immediately
before this update was received. Its 11 small artifacts, hashes, and audit log are
retained as pre-update evidence. No network acquisition is permitted after this
update, and the Commander bundle is the preferred local source for continued work.

## Wave 2 Authorization

Authorization received: 2026-09-06  
Scope: `DS-TXT-001`, `DS-TXT-002`, `DS-TXT-016`, `DS-TXT-017`, `DS-TXT-018`

## DEC-P3-005 - Pilot-01 Acceptance

Status: **APPROVED**

Pilot-01 methodology and its forensic report are accepted for bounded expansion.

## DEC-P3-006 - Pre-Update Evidence Isolation

Status: **APPROVED WITH ISOLATION**

The four pre-update JBB/GCG artifacts remain `PILOT_EVIDENCE_ONLY`, with
`SOURCE = PRE_UPDATE_PINNED` and `NO_COMMANDER_BUNDLE_EQUIVALENT`. They are not
promoted into the main corpus. The immutable overlay is recorded in
`../01_acquisition/manifests/PILOT-01_isolation_overlay.json`.

## DEC-P3-007 - Pilot Semantic Limitation

Status: **ACCEPTED LIMITATION**

Pilot-01 semantic overlap remains `NOT_MEASURED`. Wave 2 does not authorize a
large ML dependency installation or model download.

## DEC-P3-008 - Working Schema v0.2

Status: **APPROVED WITH CONDITION**

Canonical schema v0.2 is the working Phase-3 schema. Normalized binary, attack
family, and attack subtype fields remain `UNKNOWN` until a separate taxonomy rule
is approved.

## DEC-P3-009 - Provisional Roles Only

Status: **PROVISIONAL ONLY**

Role recommendations may support planning but do not establish final dataset roles.
The dataset constitution remains `NOT APPROVED`.

## DEC-P3-010 - Rights and Privacy Continuation

Status: **APPROVED**

Unresolved rights/privacy does not block forensic analysis, but blocks promotion
into finalized training, validation, test, pristine-benchmark, or redistributable roles.

## DEC-P3-011 - Wave 2 Forensic Analysis

Status: **APPROVED**

Wave 2 is limited to WildJailbreak, WildGuardMix, SALAD, Do-Not-Answer, and
deepset Prompt Injection. No Wave 3, multimodal analysis, training, split
construction, calibration, model selection, threshold selection, or final
constitution is authorized. The Commander-local bundle remains the only payload
input; missing data must be reported and not downloaded.

## Active Wave 2 Boundary

Authorized work is source/version resolution, inventory extraction, raw-integrity
verification, schema v0.2 adaptation, quality and overlap analysis, lineage,
rights/privacy review, provisional role recommendations, testing, and reporting.
Wave 2 stops for Commander review when its report is complete.
