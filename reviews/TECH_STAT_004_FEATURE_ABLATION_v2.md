# TECH-STAT-004 FINAL REPORT - Authorized Cap-Only Continuation

Status: **BLOCKED - convergence at B4 fold 0 requires Commander decision.**

This report supersedes v1 only as the latest status. The original v1 reports,
preflight, definition freeze, run-start marker, and failure remain unchanged.

## Repository And Provenance

- Branch: `tech/stat-004`; clean startup confirmed at
  `2369c3c2155b5765b2f51a7c63ea231774fc0be0`.
- Original feature-definition/run-code freeze ancestor:
  `2eed02d6257f0f55bd6e52e499dcc2017e8a728d`.
- Numerical fix committed before execution:
  `526ea0684331c0a8418df57a7a7e02b4a9828a96`.
- Resumed run-code provenance remains that fix commit. A later evidence commit
  records this stop/report; it is not the model-run commit.
- Clean-tree run gate passed; no waiver. No push performed.
- D_S substantive improvement cycle remains **1 / 2**.

## Numerical Convergence

Original max_iter: **1000**. Original failure: **B1 fold 0**.
Authorized correction: **5000**, used for every attempted B0-B6 fit.
Scientific/scorer parameters changed: **NO**, apart from this authorized
iteration ceiling. LogisticRegression, lbfgs, L2, C=1, balanced class weights,
seed 1701, fit_intercept=True, and default tolerance 1e-4 remain unchanged.
No scaling, solver/tolerance change, feature change, or threshold tuning.

| Block | Feature Count | Fold 0 n_iter_ | Converged | Fit Seconds | Folds 1-4 |
|---|---:|---:|---|---:|---|
| B0 | 10 | 334 | YES | 0.074941 | NOT RUN |
| B1 | 16 | 2670 | YES | 0.818632 | NOT RUN |
| B2 | 26 | 4586 | YES | 1.305840 | NOT RUN |
| B3 | 29 | 4922 | YES | 1.404855 | NOT RUN |
| B4 | 33 | 5000 | **NO** | 1.294986 | NOT RUN |
| B5 | 47 | NOT RUN | NOT RUN | - | NOT RUN |
| B6 | 67 | NOT RUN | NOT RUN | - | NOT RUN |

All final fits converged: **NO**. Five of 35 fits attempted; four converged.
Maximum observed n_iter_: **5000**. B4 raised the documented
`ConvergenceWarning`: `TOTAL NO. OF ITERATIONS REACHED LIMIT`.
No predictions from the unconverged B4 model were accepted. No B5/B6 or later
fold fits occurred. Total timed authoritative rerun: **5.845705 seconds**,
excluding startup verification and post-stop tests.

The iteration-cap increase was a convergence-only numerical correction and
did not constitute a new model-selection or feature-engineering cycle.

The stop rule was obeyed immediately. No retry, 10000 cap, StandardScaler,
solver change, tolerance relaxation, C change, or feature removal was made.

## Frozen Inputs And Definitions

BASE_TRAIN only: 1135 rows, 183 positives, 952 negatives; frozen five
QUALITY-001 folds and 1134 canonical lineage groups. Fold 0 refit references
used its four training folds only; held-out identities were forbidden.
No partial model results were reused. All attempted LR fits were new.
Only deterministic token evidence was reused after integrity verification:

`02241c0b2de1941783187f398c82ce3e8a7ec0a67655ace10f13ced7c29a70b3`

The byte-for-byte frozen definition hash remains:

`a560a14b9a27ebd754d8b150d600e82aee99c46c6c7c5ff7e9f4d38801f9f4c2`

The definition artifact retains the historical recipe (1000); the actual
5000 numerical override is explicit in the separate resume preflight.
All seven block schema hashes, feature definitions, and selection rules
remain unchanged, including B7 predeclared skipped.

## Analysis And Acceptance

Full B0 reproduction: **NOT COMPLETED**. Fold 0 alone cannot establish the
required 1135-row OOF reproduction. The frozen STAT-003 baseline itself was
reverified, not rerun: TN749 / FP203 / FN60 / TP123; ROC-AUC0.8100863,
PR-AUC0.5766837, Recall@1/3/5%=24.5902/32.2404/45.3552%.

For every B0-B6 block, accepted aggregate ROC-AUC, PR-AUC, Recall@1/3/5%,
attained FPR, error counts, and fold stability are **PENDING**. No partial
fold results are presented as final comparisons.

Short-prompt impact, v1 FN/FP recovery and new errors, paired uncertainty,
selected representation, and final selection schema hash: **NOT COMPLETED**.
No selection artifact or final ds_v2 exists. No improvement claim is made.

Acceptance: **BLOCKED**. STAT-005 readiness: **NO**.
Recommendation: obtain a new Commander decision about the B4-fold-0 numerical
failure. No further optimizer or feature change is authorized by this phase.

## Tests And Preservation

- Pre-run tests: **145 passed**, zero failures/errors/skips.
- Post-stop tests: **145 passed**, zero failures/errors/skips. LR fits here
  use synthetic unit fixtures only, not another authoritative dataset run.
- Test coverage includes cap5000, unchanged scientific parameters/tolerance,
  exact feature-definition hash, all 35 synthetic fit records, and hard-stop
  behavior without predicting or starting another fit after nonconvergence.
- STAT-003 authoritative output hashes: **9/9**.
- Baseline preservation checks: **96/96**, tracked baseline diff empty.
- Opaque STAT/SEM evidence preservation: **54/54**.
- Original STAT-004 evidence preservation: **10/10**.
- Acceptance checker correctly refuses the failure marker; this expected
  refusal is not a successful completed-ablation acceptance.
- Known Starlette/AnyIO and SciPy optimizer deprecations remain non-blocking;
  no package change or installation was made.

## Artifacts And Isolation

New evidence lives only in:
`artifacts/statistical_v2/feature_ablation/resume_5000/`:
preflight, pre-run/post-stop JUnit XML, run-start, failure, LR convergence,
and blocked-run summary with SHA-256 checksums.
Companion reports: `TECH_STAT_004_SHORT_PROMPT_ANALYSIS_v2.md` and
`TECH_STAT_004_TEST_REPORT_v2.md`.

CALIBRATION, VALIDATION, INTERNAL_TEST, FROZEN_EXTERNAL/FINAL_TEST,
protected experiments, E1-E10, other detector features/scores, semantic
residuals, STAT-005, and final ds_v2: **NOT USED / NOT STARTED**.
The rerun did not reopen raw dataset payloads or load the frozen LM for inference; it used
approved BASE_TRAIN metadata and the integrity-checked numerical cache.
Frozen D_S v1, D_M-A, D_M-B, D_G, calibration artifacts, and central service
files remain untouched. No raw text dumps or model checkpoints were created.
