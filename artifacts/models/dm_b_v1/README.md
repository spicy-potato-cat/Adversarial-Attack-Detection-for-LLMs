# D_M-B dm_b_v1 Frozen Raw Classifier

TECH-SEM-002 is complete. This is the fixed final checkpoint after three epochs
on 1,135 BASE_TRAIN rows (952 benign, 183 direct-injection attempts). All encoder
and classification-head parameters were trainable. The initial and final encoder
hashes differ, and the reloaded artifact matches the recorded final encoder hash.

Upstream: distilbert/distilroberta-base, model/tokenizer revision
`fb53ab8802853c8e4fbdbcd0529f21fc6f459b2b`. Binary RoBERTa classifier with
82,119,938 parameters. Frozen input limit is 256 tokens including special tokens;
right truncation, dynamic right padding. Truncation is reported in results.

## Output and Service

Detector ID: `semantic_finetuned`; version: `dm_b_v1`.
Raw score is softmax class-1 probability; higher means greater adversarial risk.
`calibrated_probability` is null. `binary_vote` uses raw score >= 0.5, a DEFAULT
DEVELOPMENT CUTPOINT, not a final operating threshold.

To enable the independent detector in the existing service, set:

```powershell
$env:ENABLE_FINETUNED_SEMANTIC_DETECTOR = "true"
$env:FINETUNED_SEMANTIC_MODEL_DIR = "artifacts/models/dm_b_v1"
$env:FINETUNED_SEMANTIC_DEVICE = "cpu"
```

Other detector settings remain separate. D_M-A is preserved and is not replaced.
The loader requires the completed model and exact hashes; no fallback is allowed.

## Integrity and Retention

`integrity_manifest.json` binds the model configuration and model/tokenizer files.
Trained weights: `transformer/model.safetensors`, SHA-256:
`0bb192d2c468530479fa8ec0786f35d8bf5a8287e4ee401a953292d221736844`.
Weights remain local and Git-ignored under the repository's large-artifact policy.
Git alone is therefore not a complete deployable model backup: retain a secure
copy of the entire frozen directory, and verify these hashes when restoring it.
Do not replace the weights with the upstream model or run training again.

Training metadata records recipe, source hashes, software, hardware, loss history,
and preserved D_M-A/D_S hashes. Training runtime: 1,088.37 seconds on CPU.
The frozen recipe and upstream preparation are in the parent artifact directory
and `detection_service/configs/dm_b_v1_training.json`.

## Evidence and Scope

One 233-row VALIDATION run occurred after artifact freeze: 39 positive, 194
negative; TN=191, FP=3, FN=4, TP=35. Metrics are DEVELOPMENT-ONLY, not E1-E10.
No CALIBRATION features or protected datasets were consumed. No threshold
optimization, calibration, ensemble experiments, or checkpoint selection occurred.
Post-training verification uses synthetic text only and does not repeat validation.
JUnit and `post_training_verification.json` record final acceptance checks.

The narrow approved corpus does not establish comprehensive coverage of jailbreak
families, indirect injection, agent/tool attacks, or adaptive attacks.
Recommendation: READY FOR TECH-SEM-002-CALIBRATION; calibration requires separate
authorization. This is not readiness for E1-E10.
