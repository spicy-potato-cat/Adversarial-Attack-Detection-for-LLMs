# TECH-STAT-004 Short-Prompt Analysis v1

Status: **PENDING: parent ablation blocked by B1 LR convergence**.

Predeclared buckets are <16, 16-31, 32-63 and 64+ input tokens. Input count
includes the first unscored token. Length reference bins additionally split
64-127 and 128+, with explicit training-benign sparse-bin pooling.

The reporting implementation computes positive/negative counts, score
distributions, raw-rule recall/FPR and each pooled fixed-FPR frontier's bucket
recall/FPR. Bucket-specific threshold optimization is prohibited. Combined
<32 recall must not deteriorate and short-benign FPR at pooled 3% must not
increase by more than two absolute percentage points under the frozen selection
policy. These guards were declared before project block outcomes.

Frozen STAT-003 finding: **51/60 raw-rule FNs have fewer than 32 tokens**.
This is the historical motivation, not proof of improvement by the new blocks.
The frozen banks remain 60 raw FNs/203 raw FPs and are diagnostic only.

All 1,135 rows' token surprisals and v1 features were extracted successfully,
but B1 failed on its first fold before complete OOF predictions. Therefore:

- Selected-block short-positive recall: NOT AVAILABLE.
- Selected-block short-benign false-positive impact: NOT AVAILABLE.
- Recovered v1 FN/FP bank counts and new errors: NOT AVAILABLE.
- Whether length-aware features recover short attacks without more short-benign
  FPs: UNRESOLVED, not a negative or positive experimental result.

No incomplete fold scores are pooled, no semantic residuals guide redesign,
no rows are duplicated/oversampled, and no unapproved threshold is selected.
Continue only after the convergence-policy decision; do not fabricate the
required short-prompt analysis or claim STAT-004 acceptance.
