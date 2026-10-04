# QUALITY-001 Test Report v1

Status: **PASS**

Client date: 2026-10-04 (Asia/Calcutta)

Branch: `quality/001-development-fixture`

Start commit: `43f1405`

## Executed Checks

```powershell
.\.local-python\python.exe -m detection_service.scripts.verify_quality_fixture
.\.local-python\python.exe -m detection_service.scripts.verify_quality_preservation --mode check
.\.local-python\python.exe -m pip check
```

New suite: `detection_service/tests/test_quality_fixture.py`.
Result: **66 passed, 0 failed, 0 skipped, 0 errors, 0 blocked**.
The runner records results once in `test_evidence_v1.json` and refuses to overwrite
existing evidence. The reusable fixture checker can run repeatedly without
rewriting frozen artifacts. Test reproductions do not regenerate candidate
fixtures for improved balance.

## Coverage

- Authoritative SHA-256 and total/BASE_TRAIN/outer partition metadata counts.
- Hash mismatch stops before manifest parsing.
- BASE_TRAIN-only metadata projection and metadata-only fold columns.
- Exactly five folds; every sample once, no missing or extra rows.
- Trainable in the other four folds.
- Zero approved-lineage group splits, including the real two-row duplicate group.
- Deterministic reconstruction, including reversed input order.
- Fixed seed 1701 and fold count; invalid values rejected.
- Valid labels, sources, group fields and canonical hashes.
- Ambiguous/missing lineage, prefix collisions, duplicate identities and too few
  groups fail rather than falling back to ungrouped stratification.
- Fold bytes/hash stability and trusted integrity anchor verification.
- Frozen file drift and attempted overwrite rejected.
- Fixture schema with exact budgets 1/3/5%, two-cycle cap, and seed.
- Partition/threat-regime orthogonality and eight conceptual later combinations.
- Baseline/candidate generation distinction and prohibited phase execution flags.
- Fold/source/class statistics and bounded class imbalance.
- Valid synthetic OOF/error-analysis schema examples; no models produced them.
- Invalid labels/folds/probabilities/predictions/latencies/coverage/error types and
  raw text fields rejected.

Every minimum QUALITY-001 test requirement is covered. No pre-existing test was
edited, removed, weakened, or deselected. Existing detector regression suites were
not executed, because this phase prohibits detector/model execution; preservation
is checked by opaque-byte hashes and an empty baseline Git diff instead.

## Isolation Gate

The verification runner disables third-party pytest plugin auto-loading and
rejects imports of torch, transformers, sentence-transformers, sklearn, joblib,
detector implementations, and application startup code. It denies Python file
opens beneath Dataset, PHASE-3, detector outputs, artifact model directories,
and the local model cache.

Observed during checker/tests:

- Prohibited payload/model open attempts: **0**.
- Model/runtime imports: **0**.
- Model training: **NO**.
- Detector scoring/OOF predictions: **NO**.
- CALIBRATION/VALIDATION text accessed: **NO**.
- Protected dataset content accessed: **NO**.
- E1-E10 or threat-regime experiments: **NO**.

The audit hook covers Python open events, not arbitrary native-system I/O.
No native payload readers or ML libraries are imported by this suite. Construction
was separately inspected: it opens only the authoritative CSV metadata, policy
documents, code bytes, and generated fixture files. The manifest CSV itself holds
membership/hashes/labels/locators, not raw prompt text. Reading outer-partition
metadata for integrity is permitted; no dataset container is opened.

## Baseline Preservation

`baseline_preservation_v1.json` records **96** application/configuration and
baseline artifact file hashes for `ds_v1`, `dm_a_v1`, `dm_b_v1`, and `dg_v1`.
The separate checker verifies unchanged bytes and no tracked baseline difference
from `43f1405`. Both snapshot and final check returned PASS.

Small serialized classifiers are hashed only, never deserialized. Transformer
weights/caches are not opened. No baseline artifacts, model code, central service
files, prior reports, or existing implementation status files were modified.

The fixture checker verified 11 bound files plus its trusted integrity anchor.
The fold SHA is
`19dc0153cc257cc2331782d6dd61b7bb9fb8cb0ed88d3e782b69d5ba05c4bb8d`.

## Dependency Repair

The first freeze attempt found `jsonschema` absent in `.local-python`; no fixture
files were written. The initial sandboxed pip attempt failed because network
access was denied, not because the pinned package was unavailable. Approved
network execution installed five new schema-only packages:

- jsonschema 4.23.0
- attrs 26.1.0
- jsonschema-specifications 2025.9.1
- referencing 0.37.0
- rpds-py 2026.6.3

They are pinned in `detection_service/requirements-quality.txt`. Existing
typing-extensions was reused. No ML package was installed or upgraded.
`pip check`: **No broken requirements found**.
The JSONSchema command-line script PATH advisory does not affect module-based
execution and is not a remaining blocker.

## Interpretation

PASS establishes metadata fixture integrity and frozen policy, not improved
detector performance, full semantic lineage independence, or final system
operating-point readiness. No classifier accuracy, FPR/FNR, or predictions were
computed here. Larger lineage controls and later materiality/compute/interval
details require pre-result authorization in their relevant phases.

Recommendation: **READY FOR TECH-STAT-003 AND TECH-SEM-003 DEVELOPMENT ANALYSIS**.
Do not begin verifier/routing work or protected experiments.
