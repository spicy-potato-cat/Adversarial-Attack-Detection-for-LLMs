# R2-DS Acceptance Context Repair

Status: PASS (delta acceptance). Verdict: R2_DS_COMPLETE_READY_FOR_MERGE_GATE_1.
Starting HEAD: 913ee734cb48eb8404e8f6ed62456eb07950246e.

| Test | Intended invariant | Stale assumption | Minimal repair |
|---|---|---|---|
| test_r2_ds_repair.test_track_b_preservation | Preserve Track-B provenance without modifying the branch | The live tip must always equal original 0cd2d50 | Verify the original reference, approved external 6c7173b tip, authorization receipt, unchanged reflog and frozen evidence |
| test_semantic_oof.test_run_stops_at_preflight_before_loading_text_or_training | Stop before loading text or training | The real completed OOF output directory is marker-free | Isolate OUTPUT in a fresh temporary fixture; retain the accepted real marker and verify its hash |
| test_statistical_scorer_comparison.test_frozen_b2_and_fixture | Preserve B2, fixture and historical run lineage | A post-run check must invoke the tech/stat-005 training startup gate | Verify the current exp/r2-ds-001 context, required ancestors, accepted run provenance, frozen output hashes and unchanged runtime code |

## Historical Marker Finding

The attachment's absent-marker description was inverted. The real marker exists:
artifacts/semantic_v2/oof/run_started_v1.json, SHA-256
5dbf13162f43879eddc56becb8a60580b506f9e55ea03b05402be784aadc5b71.
The accepted SEM manifest explicitly records that hash and explains that the
pre-run-only test was historically deselected because the completed run marker
already existed. No missing scientific evidence was found. No marker was created,
deleted or rewritten; only the fresh unit-test output context was isolated.

## Validation And Preservation

- Three repaired tests: 3 passed, 0 failed.
- Complete directly-related modules: 103 passed, 0 failed, 0 skipped.
- Baseline: 96; release: 118; source: 503; protocol patch: 262; R1: 28;
  R2-DMB: 252 hash checks passed.
- Before/after snapshot: 56 scientific/historical files byte-identical, including
  frozen R2-D_S manifests, predictions, metrics, uncertainty and private journals.
- Track B remains at 6c7173b70a10d1506d92360b421eaceb5e56405e with an unchanged
  reflog. Original 0cd2d506380cbb3ec513207e4fa66ad422d2b3f2 remains recorded.
  Classification: AUTHORIZED_EXTERNAL_BRANCH_ADVANCEMENT.
- New scientific queries: D_S 0, D_M-B 0, D_G 0, R3 0, verifier 0.
- No generation, reseeding, terminal scoring or scientific bootstrap was rerun.
  Related-module checks use existing synthetic unit fixtures, not project models.
- The full 1,562-case suite was NOT rerun: DELTA_VALIDATION_SUFFICIENT.

Evidence: reviews/evidence/r2_ds_acceptance_context/before_v1.json and
acceptance_v1.json; exact delta JUnit copies: three_tests_v1.xml and
related_modules_v1.xml. The model-free acceptance helper resides in
detection_service/tests/r2_ds_acceptance_context.py.

This additive acceptance supersedes only the three recorded context blockers.
The original blocked report, diagnosis reports and scientific result artifacts
remain unchanged. The historical 1,559-pass/3-fail receipt is not rewritten or
misrepresented as a fresh green full-suite run. Frozen scientific outcomes remain
104/698 D_S evasions, 102/104 D_G misses, 0/104 D_M-B misses and 0/104 all-three misses.

Next authorized step: Merge Gate 1. Do not rerun R2-D_S. No merge or subsequent
experiment was performed by this repair.
