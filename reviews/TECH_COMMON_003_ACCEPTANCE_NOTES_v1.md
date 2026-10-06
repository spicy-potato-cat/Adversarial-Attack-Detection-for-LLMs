# TECH-COMMON-003 Current-Machine Acceptance Notes

Status: PASS. Verdict: READY_FOR_REPORT_RESULTS_INTEGRATION.

This accepts completion of the development evidence, not a deployment decision.
The frozen external D_G has only 42/183 attack catches (22.95% recall) at the
descriptive <=3% FPR point and zero exclusive attack catches in either stack at
all three budgets. It misses all four D_M-B residual failures at 3%. These results
do not establish useful incremental attack detection from D_G on this fixture.
No tuning, alternative checkpoint, revision substitution or rescoring followed.

The D_S candidate catches one of those four residual attacks, reducing observed
all-three misses from 4/183 to 3/183. Its paired 95% JFN-delta interval includes
zero: [-0.016393, 0]. This is a small observed complementary contribution, not
strong evidence of a population improvement or causal mechanistic diversity.

At 3%, D_S/D_M-B EJF is 0.006480 and D_M-B/D_G EJF is 0.005017. Positive values
describe excess shared failure relative to the product-of-FNR independence
reference. Statistical dependence and causal dependence are not established.

The single D_G run was made from code commit
`3a053f3`; later evidence commits must not replace this run provenance.
The analysis reuses OOF scores, not the final full-BASE_TRAIN ds_v2 model.
The requested common branch predates final ds_v2/STACK-001. All 48 prior-branch
files absent there were preserved locally before switching; accepted Git history
was retained without an automatic merge. They were not used in this study.

No source container, transfer package, model cache, credentials or prompt text
is published. The final report and eight CSV/JSON tables carry measured values,
raw denominators, all three descriptive budgets and bootstrap limitations.
