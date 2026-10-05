# TECH-STAT-004 Short-Prompt Analysis - Cap-Only Continuation

Status: **PENDING - blocked by B4 fold 0 nonconvergence at 5000 iterations.**

Predeclared buckets remain `<16`, `16-31`, `32-63`, `64+` input tokens.
No definition, benign-reference calculation, feature, or selection rule changed.
The prior report and evidence remain intact.

There is no complete B0-B6 OOF artifact. Consequently short-positive recall,
short-benign FPR, raw0.5 and pooled1/3/5% comparisons, FN/FP bank recovery,
new-error counts, and paired uncertainty remain unavailable for final acceptance.
The question of recovering short adversarial prompts without increasing short
benign false positives cannot be answered from four successful fold-0 fits.

The frozen v1 error banks (60 FN / 203 FP) were not oversampled. No new error
bank, representation selection, deployment threshold, or final ds_v2 was made.
No partial improvement or regression conclusion is supported.

See `TECH_STAT_004_FEATURE_ABLATION_v2.md` and
`artifacts/statistical_v2/feature_ablation/resume_5000/lr_convergence_v1.json`
for the blocker and attempted-fit evidence. A new Commander decision is required.
