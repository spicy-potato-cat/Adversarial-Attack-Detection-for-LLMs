# TECH-STAT-007 Test And Acceptance Report v1

Status: **PASS**. One calibration fit; no classifier/reference retraining.

## Automated Tests

Corrected pre-run: **170 tests, 0 failures, 0 errors, 0 skips**.
Post-run: **170 tests, 0 failures, 0 errors, 0 skips**, 11.281 seconds.
Suite includes `test_statistical_v2`, `test_statistical_v2_verification`,
`test_statistical_v2_calibration`, `test_statistical_risk`,
`test_statistical_oof`, and `test_statistical_feature_ablation`.
Post-run JUnit XML: `artifacts/statistical_v2/calibration/completed_v1/postrun_tests_v1.xml`.
SHA: `589432b07e33d9ff271b11b6fb388bd8407fbce0ce6f22b2edc550d230c159e8`.

Tests cover exact B2 schema/recipe, serialization, reference membership, no-refit
inference, finite/order checks, reserved-partition rejection, score orientation,
model integrity/binding rejection, no fallback and original statistical behavior.
Two new regressions assert authoritative CALIBRATION41/192 membership and reject
the erroneous39/194 assertion. Synthetic test fits are not project model fits.
Known Starlette/AnyIO and SciPy optimizer deprecation warnings remain; there was
no authoritative convergence warning. No package installation was required.

## Real Artifact Verification

`calibrate_statistical_v2 --mode cal-check`: **STAT007_PASS**.
All233 record IDs, CALIBRATION membership and labels reconstruct exactly.
Stored raw scores -> reloaded calibrator reproduces every calibrated probability.
Brier, NLL and existing ten-bin summaries reconstruct exactly; ranking metrics
are identical before/after. No additional calibration fit or raw-text scoring
was used for reconstruction.

Three calibration payload/manifest/metric integrity hashes and prediction CSV
hash match. Five final model-binding hashes match; frozen runtime code hashes
match. Both historical pre-fit stop records are preserved and bound.
Prior preserved evidence/code/reports: **126/126**. Original baseline hashes:
**96/96**, original tracked diff EMPTY. Only the three authorized new ds_v2
runtime modules extend the namespace. The historical exact96-file checker and
snapshot were not changed or falsely claimed to pass expanded membership.

## Real Local-LM Smoke

`calibrate_statistical_v2 --mode cal-smoke`: **SMOKE_PASS**.
Only two declared safe synthetic strings and valid one-token `x` were used.

| Synthetic ID | Unchanged raw | Calibrated |
|---|---:|---:|
| 0 | 0.1498065090799355 | 0.027140132291331692 |
| 1 | 0.31378245919738507 | 0.08333423240936702 |
| 2, insufficient | null | null |

Scores/probabilities/feature values/coverage/metadata are identical on repeat and
reload. DetectorResult versionds_v2, 26 B2 features and unfrozen/default-only
vote metadata pass. No classifier or reference fits; ds_v1 compatibility passes.
No model/classifier/reference/calibrator fallback is provided.

## Acceptance Gates

Frozen ds_v2 unchanged: PASS. CALIBRATION only: PASS,233/41/192.
Calibrator serialized/reloaded: PASS. Wrong-model binding fails: PASS.
Brier/NLL before/after: reported, fit-only. Final threshold: NOT FROZEN.
Classifier/B2/LM/tokenizer retraining: NO. VALIDATION prompt evaluation: NO.
Protected sources/E1-E10: NO. Cycle2: DEFERRED. Default service: unchanged.
No additional algorithm comparison, verifier/routing, payload download or push.

See `TECH_STAT_007_CALIBRATION_REPORT_v1.md` for complete scientific limitations
and the initial pre-fit population-guard correction, preserved without overwrite.
