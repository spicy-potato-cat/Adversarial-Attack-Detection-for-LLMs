# TECH-STAT-006 D_S v2 Candidate Freeze v1

Status: **PASS**. Commander decision: freeze B2 + LR; substantive cycle 2 is
**DEFERRED**, not rejected. No claim of optimality or stack-level value is made.

## Repository And Provenance

Branch: `tech/stat-006`, starting at accepted STAT-005 evidence commit
`4d9d694bec959e082b8675f36a0b89488890837e`.
Final model training occurred from the clean pre-run implementation commit
`0fcc476be03d2cb3e3ed20924034c8c34b04f396`.
The later candidate acceptance commit is separate from the model-run provenance.
STAT-005 run code remains `f123a46c320075a52ef0af3d09e2de734e4895f9`.

## Frozen Recipe And Fixture

B2, 26 features, schema version `stat004_B2_v1`, SHA:
`93d3892b158c35eccfadc27c879754db69ea5293782492ee5d4ff01a33bff983`.
No feature definition/order, length bin, quantile, top-k or reference rule changed.
One final LR: lbfgs, L2, C=1, balanced weights, seed1701, tol=0.0001,
max_iter=20000, intercept enabled, no scaler or search.

BASE_TRAIN: **1135 rows, positive183 / negative952**. Manifest SHA:
`9cdd5ecdd80f9ac3c8f05db63742721f4537ca2b64a2fe48f6c2b424b57483a6`.
Frozen fold SHA: `19dc0153cc257cc2331782d6dd61b7bb9fb8cb0ed88d3e782b69d5ba05c4bb8d`.
This final fit uses all BASE_TRAIN after OOF selection; it is not another OOF
experiment or candidate comparison. CALIBRATION and VALIDATION did not fit
references or the classifier.

Exactly one final reference fit uses all BASE_TRAIN membership and the frozen
benign-only reference semantics. Exactly one final LR fit completed.
The verified numeric cache was reused; no raw dataset files or training prompts
were reopened and no LM extraction was repeated for final training.
Cached evidence SHA: `02241c0b2de1941783187f398c82ce3e8a7ec0a67655ace10f13ced7c29a70b3`.
Final 1135x26 matrix: finite, ordered, SHA over float64 bytes:
`684de61e6ce71bc83216179319e8c6cd0d23dd306f00abaf7e973b0e7b49458c`.

## Final Fit And Artifacts

Converged: **YES**, `n_iter_=[5492]`, no convergence warnings.
LR fit: **2.322690 seconds**. Reference/fit/package preparation: **3.497200 seconds**
as recorded before final reload/preservation checks. No optimizer changes or retries.

Package: `artifacts/statistical_v2/final/`.
Model: `ds_v2_model.json`; SHA:
`c5e754dc8b6e88b7437e4b81016e8f8ec23d018607d4f4e78906212b2a561157`.
Feature reference: `ds_v2_feature_reference.json`; SHA:
`fd26774585223913d12b8c20556a8fc1a50fa5dea7a3a75068a7bb30efce76ec`.
Data-only JSON stores the exact float64 LR coefficients/intercept, class
orientation [0,1] and full recipe; there is no executable pickle payload.
The manifest binds schema/order, reference LM/tokenizer, extractor configuration,
runtime-code hashes, training manifest/counts, seed and environment.
`ds_v2_integrity_v1.json` binds model, reference, manifest and training metadata.

Reference LM/tokenizer remain `distilbert/distilgpt2`, revision
`2290a62682d06624634c1f46a6ad5be0f47f38aa`, using the existing verified local
ds_v1 snapshot. LM gradients are disabled. No model/tokenizer download or training.
Python3.11.9, sklearn1.6.1, numpy2.1.3; full environment is recorded.

## Inference And Compatibility

Opt-in `B2StatisticalDetector.from_artifact` loads the frozen references and
coefficients, then existing local LM/token evidence -> exact B2 transform -> LR.
No BASE_TRAIN access or reference fitting is needed during inference.
`raw_score` remains uncalibrated LR class1 probability, higher = more adversarial.
The public DetectorResult is preserved; all 26 B2 values are named in metadata.
Missing/corrupt/mismatched artifacts fail loudly, without lexical/evidence fallback.

Real-LM synthetic smoke: **PASS**. Repeated and reloaded raw scores were exactly
equal: 0.1498065090799355 and 0.31378245919738507 on two declared safe strings.
A valid one-token synthetic input returns `insufficient_input`, with no fabricated
score/probability/vote. Zero reference/classifier refits were enforced by mocks.
ds_v1 inference compatibility: **PASS**; v1 and v2 coexist. Service defaults,
main.py, existing detectors and their artifacts were not changed.

The frozen smoke helper initially supplied an empty string, which the existing
request contract rejects. A separately hashed verification-only adapter replaces
that declared synthetic fixture with the valid one-token string `x`; it rejects
undeclared/project inputs. Training code/model/reference hashes were not rewritten,
and no second model fit was performed. Use `verify_statistical_v2 --mode smoke`,
not the historical helper's invalid empty fixture, for this package.

Binary compatibility rule only: raw>=0.5 before calibration, calibrated>=0.5
after calibration. Metadata explicitly says
`DEVELOPMENT_DEFAULT_NOT_FINAL_OPERATING_POINT`; the final threshold is **NOT FROZEN**.
No descriptive OOF threshold was promoted to a deployment policy.

## Preservation And Limitations

Original 96 baseline hashes: PASS; original tracked-file diff: EMPTY.
Preflight-preserved prior evidence/code/reports: **126/126**. Frozen historical
STAT/SEM/guard/model/calibration evidence remains unchanged.
The historical checker requires exactly96 files and rejects application additions.
It and its snapshot remain untouched. The phase adapter verifies those exact
96 originals and permits only the three new statistical_v2 application modules.
This is an explicit namespace extension, not a baseline-hash waiver.

Prior development OOF is not unbiased final performance: ROC0.8968/AP0.7316,
Recall@1/3/5=32.79/54.64/62.84%. All scorers missed **0 detected / 26 attacks
under16** at pooled<=3%; LR flagged **12/17 long-benign** examples there.
The latter subgroup is small. These limitations remain, and cross-detector
complementarity/common-mode failure is not yet evaluated.

## Acceptance

Pre-run tests163/163; post-run tests168/168; zero failures/errors/skips.
Final package, matrix reconstruction, real-LM repeat/reload, no-refit inference,
class orientation, schema/order and ds_v1 preservation all pass.
CALIBRATION used for model training: NO. VALIDATION/protected/E1-E10: NO.
Cycle2: DEFERRED. STAT-007 may now calibrate this exact package after the separate
STAT-006 acceptance commit. No new scorer, feature experiment or threshold fit.
