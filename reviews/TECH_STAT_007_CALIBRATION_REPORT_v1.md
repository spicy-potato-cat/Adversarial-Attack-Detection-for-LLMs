# TECH-STAT-007 D_S v2 Probability Calibration v1

Status: **PASS**. Candidate `ds_v2` remains frozen. Calibration version:
`ds_v2_cal_v1`. Cycle 2 is **DEFERRED**. Final operating threshold is **NOT FROZEN**.

## Provenance And Pre-Fit Correction

Branch: `tech/stat-006`, starting at `4d9d694bec959e082b8675f36a0b89488890837e`.
Final model-run code: `0fcc476be03d2cb3e3ed20924034c8c34b04f396`.
STAT-006 candidate acceptance: `30d3781f23651bc4317ce621ac916896bf47dc66`.
Corrected calibration run code: `4ca18288c2cda32c9c9d29dbd6b040e55a7d9e44`.
The later STAT-007 evidence commit is not the model/calibration run-code commit.

The original calibration runner stopped at its population guard, before loading
raw text, extracting LM evidence or fitting a calibrator. It mistakenly expected
the VALIDATION class counts, 39/194. The hash-verified CALIBRATION partition has
**233 rows: positive41 / negative192**. No rows or labels were changed.
The original start/failure records and frozen runner remain intact in
`artifacts/statistical_v2/calibration/`. A separately committed runner and two
regression tests correct only the population assertion/count reporting.
Exactly **one calibration fit** occurred, in `calibration/completed_v1/`.

Manifest SHA:
`9cdd5ecdd80f9ac3c8f05db63742721f4537ca2b64a2fe48f6c2b424b57483a6`.
Sorted CALIBRATION record membership SHA:
`3583d4a4d4547b97e6373bb932ac3c973a59df43c4ff793bf6477a3109422acb`.

## Method And Isolation

Existing `platt_sigmoid_on_lr_log_odds`: clip raw probabilities at epsilon1e-12,
then sigmoid(slope * logit(raw) + intercept). Positive slope constraint1e-8,
Platt-smoothed targets, L-BFGS-B maxiter1000, ftol1e-12, gtol1e-10;
no class weighting, penalty, method comparison or threshold selection.
Slope: **1.2387924053209722**. Intercept: **-1.4285349476179108**.
Optimizer: **converged, 8 iterations**. Recorded runtime: **35.267118 seconds**.

Only the approved Do-Not-Answer CSV and two deepset Parquet containers were opened.
Their hashes and selected source-text/label hashes matched the frozen manifest.
These are mixed-partition containers; only CALIBRATION scalar texts entered
LM extraction, B2 transformation or calibration fitting. Manifest validation
reads partition metadata, not VALIDATION prompts. No protected source was opened.

LR and reference fitting were patched to raise throughout scoring/calibration.
The frozen B2 reference state, LR coefficients, LM/tokenizer and all five model
binding files are unchanged. No LM/tokenizer training or downloads occurred.
Python3.11.9/sklearn1.6.1/torch2.6.0 and full code/environment hashes are recorded.

## Calibration-Fit Diagnostics

| Metric | Raw | Calibrated |
|---|---:|---:|
| Brier score | 0.08817214759280138 | 0.059504681552583 |
| NLL / log loss | 0.3014315232850654 | 0.208086588754964 |
| ROC-AUC, sanity only | 0.9439786585365854 | 0.9439786585365854 |
| PR-AUC / average precision, sanity only | 0.8428186736354086 | 0.8428186736354086 |

These are **CALIBRATION-FIT DIAGNOSTICS ONLY**, not held-out performance or proof
of generalization. Ranking is unchanged, as expected for positive-slope sigmoid.
Existing ten-bin reliability diagnostics are recorded; no new ECE is claimed.
The prediction CSV contains IDs, labels, raw scores and calibrated probabilities,
not source prompt text. All 233 probabilities and diagnostics reconstruct exactly.

## Artifacts And Binding

Accepted directory: `artifacts/statistical_v2/calibration/completed_v1/`.
Calibrator: `ds_v2_cal_v1.json`; SHA:
`964cea57d98673d2026fb2f0e9d5884aec61a653e726847e0fb6ccbf36e95f23`.
Manifest: `ds_v2_calibration_manifest_v1.json`; SHA:
`6ad2a6d42a81f4b51f2390bc14a126dfe9236b3c04b01e4eabbc0c3479d54d94`.
Model SHA remains:
`c5e754dc8b6e88b7437e4b81016e8f8ec23d018607d4f4e78906212b2a561157`.
Feature-reference SHA remains:
`fd26774585223913d12b8c20556a8fc1a50fa5dea7a3a75068a7bb30efce76ec`.

The calibrator binds all five frozen package files, including the reference state
and manifest, and fails loudly on wrong/missing/tampered bindings. No fallback.
Use `B2StatisticalDetector.from_artifact(final_dir, calibration_dir=completed_dir)`
for opt-in inference; default service wiring and ds_v1 remain unchanged.
The corrected CLI is `python -m detection_service.scripts.calibrate_statistical_v2`;
verification modes are `cal-smoke` and `cal-check`. Do not refit accepted outputs.

Real local-LM synthetic smoke passes repeat/reload, 26 named B2 features, public
DetectorResult contract, unchanged raw scores, calibrated probabilities and
ds_v1 compatibility. The valid one-token synthetic input remains insufficient,
with null score/probability/vote. The previous empty-fixture correction is reused.

## Governance And Recommendation

Binary vote compatibility only: calibrated>=0.5, explicitly
`DEVELOPMENT_DEFAULT_NOT_FINAL_OPERATING_POINT`. No final threshold is frozen.
No VALIDATION prompt evaluation, protected data, E1-E10, verifier/routing or push.

Known development OOF limitations remain: all scorers detected0/26 under16-token
attacks at pooled<=3% FPR; LR flagged12/17 in the small 64+ benign subgroup.
OOF informed recipe selection and is not unbiased final evaluation. Standalone
value does not establish stack value; complementarity/common-mode analysis awaits
separate authorization. Cycle2 remains deferred, not rejected.

Recommendation: **READY FOR STACK/COMMON-MODE INTEGRATION**.
