# TECH-STAT-004 FINAL REPORT

STATUS: **BLOCKED: LR convergence review required**. Acceptance gate not met.
This is an incomplete, preserved attempt, not a successful ablation or a final
D_S v2. No block outcome has been used to modify feature definitions.

## Repository And Provenance

Branch: `tech/stat-004`.
Accepted start: `9b63a230943be3f47e812f6495a8f3435fdff642`.
Run/code freeze: `2eed02d6257f0f55bd6e52e499dcc2017e8a728d`.
The starting tree was clean and STAT-003 `6e88dfe` was in ancestry. The branch
did not exist and was created normally; no gate was waived. A separate clean
tree gate was checked again after committing definitions and before execution.

Manifest SHA: `9cdd5ecdd80f9ac3c8f05db63742721f4537ca2b64a2fe48f6c2b424b57483a6`.
Fold SHA: `19dc0153cc257cc2331782d6dd61b7bb9fb8cb0ed88d3e782b69d5ba05c4bb8d`.
Definition SHA: `a560a14b9a27ebd754d8b150d600e82aee99c46c6c7c5ff7e9f4d38801f9f4c2`.
Fixture: 1,135 BASE_TRAIN, 183 positive/952 negative, five frozen folds,
seed 1701, no regenerated groups/folds.

## Completed Work And Failure

All B0-B6 definitions, ordering, schema hashes, reference rules, short buckets,
selection policy and paired-bootstrap method were committed **before project
outcomes**. B7 was explicitly skipped. New code coexists with v1; no existing
extractor/scorer/model/calibration artifact was modified.

The single frozen CPU-LM extraction completed all **1,135 rows in 56.56 seconds**.
All ten v1 features and token coverage exactly matched the frozen STAT-003
evidence for every row. Numeric surprisal evidence was cached locally, without
prompt text or token strings/IDs, to avoid repeating invariant extraction.

Fold 0 references used only its 908 training rows and training benign examples.
B0's fold-0 LR fit/prediction completed. **B1 fold 0 failed to converge at
1,000 L-BFGS iterations**. Total elapsed time at stop: **60.57 seconds**.
The ConvergenceWarning was promoted to a hard stop; unconverged scores were
not accepted and no B1-B6 performance outputs were published. The attempt was
not automatically repeated. No additional LR fit was run after failure.

The current full B0 five-fold reproduction is therefore **NOT COMPLETE**.
The original STAT-003 authoritative outputs were independently verified,
but they are not passed off as a completed new B0 run.

## Feature Blocks

| Block | Added | Total | New-run metrics / fold stability |
|---|---:|---:|---|
| B0 | 10 | 10 | Fold 0 completed; full OOF not complete |
| B1 | 6 | 16 | Blocked during fold-0 LR fit; no accepted metrics |
| B2 | 10 | 26 | Not evaluated |
| B3 | 3 | 29 | Not evaluated |
| B4 | 4 | 33 | Not evaluated |
| B5 | 14 | 47 | Not evaluated |
| B6 | 20 | 67 | Not evaluated |
| B7 | 0 | not tested | PREDECLARED-SKIPPED |

No new ROC-AUC, PR-AUC, Recall@1/3/5%, attained FPR, fold stability, short-prompt
impact or error-bank movement is claimed. Those acceptance requirements remain
pending, not zero-valued or fabricated results.

Frozen schema hashes:

| Block | SHA-256 |
|---|---|
| B0 | `bc486d0a9561540f89b7eb8414fe03de392826621cec0ba7af0bef3c1b682bb9` |
| B1 | `04099bb2ca3f7e8ae676b19d1459c2bab9d1d94b896846e2b46edee2d75b90fc` |
| B2 | `93d3892b158c35eccfadc27c879754db69ea5293782492ee5d4ff01a33bff983` |
| B3 | `aaac6a2dd25be2aa05cfe49c89229f09b6e4b4fd9f653784026fbb85e6e9d4e2` |
| B4 | `c9b7a64eb62efd7ad50a79f0f1d0b638bb2b89632672fd82d1cc4e0e568fc36e` |
| B5 | `dc5b1854282e3d6a72e2068c47da861db5e52fd0c3e50222dd69fcaede2b82ca` |
| B6 | `3eb392c02c0ed72d4505a5b8a7ae513f7f200e4477e7dcd5c47a4a5a90f96c1d` |

## Authoritative Historical Baseline

Verified STAT-003 only: TN 749, FP 203, FN 60, TP 123; ROC-AUC
0.8100863296, PR-AUC 0.5766836614. Recall@1/3/5%: 24.5902/32.2404/45.3552%;
attained FPR: 0.7353/2.9412/4.9370%. Its artifact hashes passed 9/9.
The frozen raw FN/FP banks remain 60/203; no diagnostic IDs were oversampled.

## Numerical Diagnostic And Next Decision

A post-stop read-only diagnostic on fold-0 training features confirmed all B1
values were finite. Inherited PPL features reach **1,279,062.41**, while added
percentiles are bounded by one. This large scale disparity is a plausible
optimization-conditioning issue, not a proven causal/performance conclusion.
No additional classifier was fitted to investigate it.

No scaling, C/penalty/weights/solver/iteration-cap change or feature redesign
was made after the stop. Scaling would change the effective L2 geometry and
was explicitly excluded in the predeclaration. Whether to authorize a
convergence-only iteration-cap increase is submitted to Commander review.
Such an exception must be recorded explicitly before another fit; the original
failure/start markers and run-code provenance must remain intact. No automatic
retry or use of unconverged scores is authorized by this report.

Selected representation: **NONE; pending completed ablation**.
Paired comparison: **NOT COMPUTED**; the method is frozen but no complete paired
OOF score vectors exist. Short-prompt impact/error-bank movement: **NOT COMPUTED**.

## Tests And Preservation

**142 pre-run tests passed**, zero failures/errors/skips. Feature mathematics,
ordering/hashes, full-window coverage, short-input handling, training-only
references, held-out invariance, leakage rejection, fixed-FPR calculations,
diagnostic transitions and paired-bootstrap determinism are covered. Tests do
not establish real-project LR convergence; this runtime blocker remains real.

After the stop, **96/96 baseline checks** and **54/54 preserved STAT/SEM evidence
hashes** passed. Baseline tracked diff is empty. Frozen D_M-B remains untouched.
See `TECH_STAT_004_TEST_REPORT_v1.md` for commands and warning details.

## Governance And Isolation

D_S cycle: **1/2, incomplete**; cycle 2 not started.
Logistic Regression only: YES. Complementarity: DEFERRED.
No project CALIBRATION/VALIDATION/INTERNAL_TEST/FROZEN_EXTERNAL use, protected
experiments, E1-E10, other detector outputs as features, final ds_v2, or
deployment threshold selection. Approved original mixed CSV/Parquet containers
were read only to select BASE_TRAIN texts; unselected texts never enter the LM,
reference fitting, LR or diagnostics. Raw artifacts were not modified.

## Artifacts And Git

Committed preparation: definitions, preflight, passing JUnit, separate feature
and diagnostic code, tests and predeclaration report. Failure evidence:
`run_started_v1.json`, `failure_v1.json`, `blocked_run_summary_v1.json`.
Three requested status/test/short-analysis reports document the incomplete state.

Local ignored numeric cache: `detection_service/outputs/stat004/token_evidence.npz`,
119,306 bytes, SHA `02241c0b2de1941783187f398c82ce3e8a7ec0a67655ace10f13ced7c29a70b3`.
No dataset, raw text dump, model cache, credential or temporary file is committed.
Resolve the failure-evidence commit with `git log -1 --format=%H --
artifacts/statistical_v2/feature_ablation/blocked_run_summary_v1.json`.
No push is authorized.

## Recommendation

**NOT READY FOR TECH-STAT-005 SCORER COMPARISON.** Decide whether to allow a
documented numerical convergence exception, then complete the existing frozen
blocks without redesigning them or consuming cycle 2. Do not train final ds_v2.
