# D_M-B Calibration dm_b_v1_cal_v1

Separate mapping attached to the unchanged dm_b_v1 model. Base model metadata,
weights, tokenizer and training evidence remain frozen; the parent README is
historical raw-model documentation from TECH-SEM-002.

Raw score p remains softmax(logits)[1]. The mapping is:

```text
q = sigmoid(0.5342020363895714 * logit(clip(p, 1e-12, 1-1e-12))
            + 0.9137732043262331)
```

q populates calibrated_probability. Binary vote still uses raw p >= 0.5, the
DEFAULT DEVELOPMENT CUTPOINT. No final operating threshold has been frozen.

The existing D_M-B environment settings are unchanged. Enabled service wiring
requires calibration. Independent from_artifact loads it automatically when
present, fails for corrupt/incomplete/model-incompatible files, and can return
None only when calibration is absent and require_calibration=False. No identity,
raw-probability-as-calibrated, D_M-A or other fallback is supported.

calibrator.json contains slope, intercept and epsilon. calibration_metadata.json
binds its SHA-256 to exact frozen model/tokenizer hashes, manifest, 233 selected
CALIBRATION records (41 positive, 192 negative), score transform, code, software,
Git state and creation time. Retain both files with the frozen model directory.
Weights remain Git-ignored; a Git checkout alone is not a deployable model backup.

calibration_scores.json stores the required selected IDs, labels, raw scores and
calibrated scores, but no raw text or embeddings. Other files record the fixed
method, in-sample diagnostics, actual model/API verification, source-bound test
evidence and JUnit results. The fitting runner refuses an existing calibration
directory, preventing an accidental second fit or authoritative overwrite.

Only CALIBRATION features were consumed. BASE_TRAIN, VALIDATION and protected
features were not consumed; historical validation files were hash-checked only.
The mapping was fitted once using smoothed Platt targets, positive slope and
deterministic L-BFGS-B, with no calibration-method search or threshold tuning.
Fitting diagnostics are optimistic and do not establish generalization or
distribution-shift calibration quality. No protected or E1-E10 experiment ran.
