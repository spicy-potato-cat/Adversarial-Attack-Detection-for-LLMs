# TECH-STAT-006 Test Report v1

Status: **PASS**. Final training code commit:
`0fcc476be03d2cb3e3ed20924034c8c34b04f396`.

## Suites

163/163 pre-run tests, 0 failures/errors/skips, 10.662 seconds; XML:
`artifacts/statistical_v2/final/prerun_tests_v1.xml`.
168/168 post-run tests, 0 failures/errors/skips, 11.745 seconds; XML:
`artifacts/statistical_v2/final/postrun_tests_v1.xml`.

The suite covers `test_statistical_v2.py`, existing statistical-risk, OOF and
feature-ablation tests; post-run also includes `test_statistical_v2_verification.py`.
Classifier fixtures are synthetic, not additional project model fits.
No package was installed or upgraded.

The restricted Windows sandbox stalled the existing TestClient test inside
asyncio socketpair/accept before detector execution. Two diagnostic attempts
were interrupted, with no completed XML claimed. The same full suite passed
with local loopback permissions. This required no application-code changes.
The environment note preserves this exception. Warnings are existing
Starlette/AnyIO and SciPy deprecated-option warnings, not convergence failures.

## Coverage

- Manifest/fold/schema hashes and exact fixed B2/LR recipe.
- JSON serialization preserves sklearn raw probabilities exactly.
- Reloaded references produce the exact original feature matrix without fitting.
- BASE_TRAIN-only reference fitting rejects reserved partitions.
- Schema/recipe/class-order/coefficient-shape/reference-bin corruption is rejected.
- Raw-score orientation is class1; nonfinite/wrong-width matrices fail without imputation.
- DetectorResult identity, 26 named B2 features, unchanged raw-score semantics and explicit unfrozen operating policy.
- Deterministic inference; insufficient token evidence does not create a fake vote.
- Positive-slope sigmoid serialization/ranking and strict model binding; changed model bytes fail loudly.
- Synthetic smoke adapter produces genuine validated request objects, cannot transform undeclared/project inputs and preserves training-code/model hashes.
- Existing ds_v1 scorer/calibration/contract and statistical feature regressions.

## Authoritative Checks

One final fit, BASE_TRAIN1135/positive183/negative952, B2 width26, finite ordered
matrix. Converged in5492 iterations, below20000, no convergence warnings.
Before/after JSON reload scores were exactly identical on the final matrix.

```powershell
.\.local-python\python.exe -m detection_service.scripts.verify_statistical_v2 --mode smoke
.\.local-python\python.exe -m detection_service.scripts.freeze_statistical_v2 --mode check
```

Real local-LM synthetic smoke passes repeat/reload equality, class1 scores,
26-feature schema, valid one-token insufficient input and ds_v1 compatibility.
References.fit and LogisticRegression.fit are patched to raise during inference
and acceptance reconstruction. No silent refitting or fallback exists.

The initial smoke-helper empty fixture violated the pre-existing request schema.
The verification-only adapter corrects that fixture, not preprocessing/training.
The subsequent accepted smoke and adapter bytes are separately hashed. The
training provenance and model/reference files remain unchanged.

`--mode check`: PASS; final matrix reconstruction exact, original96 baseline
hashes PASS, original tracked diff EMPTY, prior126 evidence hashes PASS.
The historical exact-membership checker remains unchanged; the phase-specific
adapter allows only the three newly authorized ds_v2 modules in addition to
its original96 files. No original hash was changed or ignored.

No raw payload was reopened for final fitting, no CALIBRATION/VALIDATION/protected
row was used for classifier/reference fitting, no LM retraining or reference
extraction occurred for BASE_TRAIN, no feature search or threshold fit occurred.
Only the Commander-authorized single project LR candidate was fitted.
Cycle2 remains DEFERRED; calibration awaits the separate STAT-006 commit.
