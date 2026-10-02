# TECH-STAT-002 Test Report v1

Date: 2026-10-02. Status: PASS.

## Commands

All executed from repository root with existing project Python:
```powershell
.\.local-python\python.exe -m detection_service.scripts.train_statistical_risk --mode prepare
.\.local-python\python.exe -m pytest detection_service/tests/test_statistical_risk.py -q --basetemp detection_service/outputs/stat002-unit-temp
.\.local-python\python.exe -m detection_service.scripts.verify_statistical_regressions
.\.local-python\python.exe -m detection_service.scripts.train_statistical_risk --mode train
.\.local-python\python.exe -m detection_service.scripts.train_statistical_risk --mode calibrate
.\.local-python\python.exe -m detection_service.scripts.train_statistical_risk --mode validate
.\.local-python\python.exe -m detection_service.scripts.train_statistical_risk --mode smoke
.\.local-python\python.exe -m detection_service.scripts.smoke_statistical_risk
.\.local-python\python.exe -m detection_service.scripts.verify_statistical_regressions
```
Do not rerun training/calibration/validation on these frozen artifacts. Existing
start/artifact markers deliberately reject duplicate fitting/evaluation.
Training/validation pipeline hash is unchanged before/after its one actual run.

Initial new unit suite: 41 passed; initial combined suite: 192 passed.
One additional synthetic protected-source gate test was subsequently added.
Final combined suite: **193 passed, 0 failed, 0 skipped; 9 intentionally deselected**.
Final statistical-risk tests: 42. Blocked checks: none.
No existing tests were modified or weakened.
Evidence: artifacts/models/ds_v1/test_evidence.json.

| Regression Area | Passed |
|---|---:|
| Statistical engine/detector/features/export/API | 22 |
| D_M-A | 9 |
| D_M-A calibration | 18 |
| D_M-B | 26 |
| D_M-B calibration | 27 |
| D_G incl. chunk/tail | 49 |
| New statistical risk | 42 |

## Coverage And Real Smoke

Tests verify exact export order/schema/hash; unchanged extractor values and aliases;
finite/missing-feature rejection; reproducible LR fit, coefficient shape and
convergence; class-1 orientation/bounds; scorer/calibrator reload and deterministic
outputs; BASE_TRAIN-only scorer and CALIBRATION-only sigmoid fitting;
protected partition/source rejection; manifest drift; VAL once-only gate.
They cover missing/corrupt/model-incompatible scorer/calibrator; no fallbacks;
no runtime fitting; DetectorResult/JSON; calibrated-not-raw vote; model reuse;
short-input null scores; Unicode/long coverage; API errors and settings wiring.

Real authoritative CPU API smoke: PASS, repeated scores/probabilities/features
equal, model/scorer/calibrator reused. No raw text returned.
Extended smoke exercises the default factory via STATISTICAL_MODEL_DIR, not
injected fixtures: short, Unicode and long input all schema-valid and deterministic.
Long case: 4,502 original tokens, explicit 4,096-token cap, 4,095 next-token targets
analyzed across multiple LM chunks. Analyzed prefix tail preserved; extra input
explicitly excluded as already frozen in v0.1. Whitespace rejects with HTTP 422.
Evidence: service_smoke.json and extended_smoke.json.
Synthetic examples are not benchmark performance.

## Data Access And Preservation

Actual pipeline: BASE_TRAIN scorer fit only, CALIBRATION sigmoid only,
VALIDATION once after freeze; no protected data or E1-E10.
Synthetic regression runner blocks Python open against actual Dataset/PHASE-3/
data_governance/experiment_readiness roots. Attempts: zero.
Native I/O is not intercepted; selected tests were inspected for actual row access.
Nine old semantic tests consuming project manifests/calibration data are deliberately
deselected, by exact names listed in test_evidence.json and the runner.
These exclusions avoid unnecessary replay of prior model-data tests; all required
actual D_S stage integrity gates ran under the current authorization.

Five extractor source hashes and all 34 prior preservation checks remain equal.
D_M-A/B/G source/tests/model/calibration artifacts unchanged.
Seven reference snapshot files match the original exact local-cache bytes.
Scorer/calibrator/model-config/schema artifact hashes remain equal after validation
and real smoke. completion_evidence.json binds the final artifacts and checkpoints.

## Warnings And Environment

No test or training failure occurred. Existing AnyIO and SciPy optimizer
deprecation warnings remain; no dependency changes were necessary.
The real long smoke prints the tokenizer's >1024 advisory before the unchanged
engine chunks the IDs safely. Inference completes with explicit coverage.
Default Git whitespace check flags frozen calibration JSON CRLF as whitespace;
using git -c core.whitespace=cr-at-eol diff --check passes. Bytes were NOT normalized,
because doing so would invalidate the already frozen calibration hashes.

Python 3.11.9; Torch 2.6.0+cpu; Transformers 4.49.0; tokenizers 0.21.4;
Hub 0.36.2; sklearn 1.6.1; numpy 2.1.3; scipy 1.17.1; joblib 1.6.0;
pyarrow 19.0.1; FastAPI 0.115.5; Pydantic 2.10.2; pytest 8.3.4.
CPU-only installed Torch, 8 threads in actual pipeline/smoke. No GPU claim.
Caches/feature matrices/temp fixtures remain ignored and repository-local.
No raw datasets, credentials or reference model weights enter Git.
