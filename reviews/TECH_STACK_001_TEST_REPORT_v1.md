# TECH-STACK-001 Test Report v1

Status: **PASS**, metadata-only integration verification.

## Results

Pre-freeze:41 tests passed. Post-freeze: **41 passed,0 failed,0 errors,0 skipped**.
Post-freeze runtime:5.465 seconds. Test command:

```powershell
.\.local-python\python.exe -m pytest detection_service/tests/test_stack_manifest.py -q --junitxml=artifacts/stack/test_results_v1.xml
.\.local-python\python.exe -m detection_service.scripts.freeze_research_stack --mode check
```

JUnitSHA: `cd886584317d959a29b223d0b21dc8e7916eadd6063fb601174a94b17fcb5ace`.
Saved manifest verification:PASS,129 artifact hashes,96 original baseline hashes,
three ordered primary detectors and exact implementation-source hashes.
CanonicalSHA: `dce1392430198894247ca318d6c2627f024ef403742d2a0779bb7b7606847110`.

## Coverage

- Actual accepted D_S model/reference/calibration and B2 schema identity.
- Actual accepted D_M-B weights/tokenizer/config and calibration binding.
- Actual D_G local snapshot hashes, revision, no-calibration and native policy.
- Deterministic D_S,D_M-B,D_G ordering; duplicate-ID/version drift rejection.
- Higher-is-adversarial direction; required unfrozen/default-only vote metadata.
- D_M-A exclusion; promotion/addition to primary stack rejected.
- Original independent input and detector-specific tokenizer policies.
- Canonical hashing independent of JSON key ordering/pretty-print whitespace.
- Corrupt hashes, missing model/artifact/calibrator and checksum rejection.
- Wrong accepted calibrator binding rejection for both D_S and D_M-B.
- Model/revision/schema/calibration/native-vote/ensemble/fallback drift rejection.
- Separate saved-file-byte integrity, checksum and integrity-record checks.
- Dataset/forensic row table paths, traversal and absolute path rejection.
- Duplicate JSON keys, NaN and Infinity rejection.

Mutation tests cache the expected already-verified manifest where appropriate;
actual artifact verification and wrong-binding tests use the real local metadata
and hashes. Temporary corrupt/missing files are test fixtures, not modifications
to accepted artifacts. No model is loaded and no synthetic or dataset prompt is
scored. Unit tests perform no training/calibration fitting or detector calls.

An isolated Python open-audit permitted only artifact/code/package-metadata
namespaces. It recorded144 unique paths and no denied access attempts.
torch,transformers,sklearn,numpy were absent from sys.modules after the check;
package versions were read through importlib.metadata, without runtime imports.
Metadata and weight bytes are checked, never deserialized.

## Preserved Behavior And Limits

All original detector implementations, service settings/API/contract files,
model/calibration artifacts and native input/vote policies are unchanged.
No new detector registry, orchestrator, fusion, verifier or routing was added.
The stack-facing statistical alias and binary_prediction mapping are explicit
manifest declarations; runtime IDs and binary_vote remain unchanged.

No live model smoke or performance evaluation was needed or run. This verifies
local artifact identity and reproducibility, not runtime model accuracy or
cross-detector complementarity. No dataset access, protected experiments,
E1-E10, threshold selection, retraining, payload download or package installation.

Accepted decision state: thresholds/ensemble NOT_FROZEN, verifier NOT_SELECTED,
routing NOT_IMPLEMENTED. Development common-mode ingestion awaits authorization.
