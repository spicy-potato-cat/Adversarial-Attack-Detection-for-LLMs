# TECH-SEM-003 Post-Run Test Report v1

Status: PASS. Scope: frozen OOF evidence verification and post-run analysis.
MODEL/RUN CODE provenance remains `5096d078b599c43ddd4e32b4fbfcaedcc83e4646`.
The acceptance commit is separate and never written into original run records.

## Authoritative And Preservation Checks

Before acceptance commit:

```powershell
.\.local-python\python.exe -m detection_service.scripts.semantic_oof_baseline --mode check
.\.local-python\python.exe -m detection_service.scripts.verify_quality_preservation --mode check
```

Results: `PASS_COMPLETE_DEVELOPMENT_OOF`, 1,135 rows, zero leakage, **9/9**
original output hashes; baseline `PASS`, **96/96** hashes, empty tracked diff.
Manifest/fold/preflight hashes match Commander authorization.

Separate post-run checker (works at the original or descendant evidence HEAD):

```powershell
.\.local-python\python.exe -m detection_service.analysis.semantic_oof_acceptance --mode analyze
.\.local-python\python.exe -m detection_service.analysis.semantic_oof_acceptance --mode seal
.\.local-python\python.exe -m detection_service.analysis.semantic_oof_acceptance --mode check
```

Analyze reconstructs artifacts without model execution; exclusive creation
prevents accidental overwrite. Seal binds all 11 original run files, five
acceptance artifacts, two acceptance code/test files, three reports and JUnit
bytes. Check performs read-only deterministic reconstruction, original nine
output hashes and 96 baseline checks again. Git ancestry and original Git blob
identity prove frozen run code/preflight still matches the original run commit.
The original pre-run checker/gates remain untouched and still require their
original HEAD. No clean-tree gate is waived.

## Regression Command

```powershell
.\.local-python\python.exe -m pytest detection_service/tests/test_semantic_oof.py detection_service/tests/test_statistical_oof.py detection_service/tests/test_semantic_oof_acceptance.py -k 'not test_run_stops_at_preflight_before_loading_text_or_training' --junitxml=artifacts/semantic_v2/oof/acceptance_tests_v1.xml -q
```

**120 passed; 0 failed; 0 errors; 0 skipped; 1 deselected.**
Composition: 56 existing semantic, 37 existing statistical and 27 new acceptance
tests. The frozen pre-run-only test expects an absent authoritative start marker
and an intentionally uncommitted preflight. That assertion is now inapplicable,
so it is deselected, not altered or silently counted as passed. Its original
pre-run success remains in frozen evidence. A new post-run test verifies the
existing completed-run marker refuses a rerun before preflight, loader or fold
training can be called.

25 non-failing warnings originate from existing SciPy L-BFGS-B deprecated
`disp`/`iprint` options in shared statistical synthetic-fixture regressions.
No additional dependency installation is required.

Semantic model fitting/inference in existing unit tests uses test doubles;
shared statistical tests exercise tiny synthetic Logistic Regression fixtures.
No new project detector, transformer, authoritative OOF model or checkpoint
is trained/scored in this phase.

## Coverage

Checks reconstruct raw confusion/ranking metrics, all fixed-FPR counts with
inclusive threshold equality, all fold frontiers and population SD, eight Wilson
rate intervals, raw 17-FN partition into 13 recovered/four persistent, original
high-confidence annotations, exact ID-only metadata joins, truncation and
non-actionable coherence/freeze decision. Predictions are unique, BASE_TRAIN
only, uncalibrated and canonical-lineage disjoint across folds.

Isolation checks deny all Dataset/PHASE-3 payload opens and frozen-model writes.
Acceptance code has no loader, predictor or trainer call and runs offline;
authorized manifest metadata is used without consuming reserved-partition
texts. Baseline model files are checked as opaque hashes, not loaded for use.
No CALIBRATION, VALIDATION or protected payload use, E1-E10, threshold freeze,
SEM-004 or STAT-004 modification occurs.

After evidence commit, rerun the post-run checker and baseline preservation
command read-only, verify `git status` clean and `git log -3 --oneline`.
Use the separate post-run checker after commit: the original checker correctly
refuses a changed HEAD and must not be weakened to conceal this distinction.
