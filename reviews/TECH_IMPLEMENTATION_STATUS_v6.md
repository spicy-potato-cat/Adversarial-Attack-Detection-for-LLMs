# TECH IMPLEMENTATION STATUS v6

Date: 2026-10-01. TECH-SEM-002-CALIBRATION: PASS.

D_M-B base model remains dm_b_v1; separate calibration version dm_b_v1_cal_v1.
Platt sigmoid on clipped raw softmax class-1 log-odds; slope 0.5342020363895714,
intercept 0.9137732043262331. Fit once on 233 CALIBRATION rows, 41 positive and
192 negative. Manifest SHA-256 verified. No transformer retraining.

calibrated_probability is available. Raw softmax score and raw_score >= 0.5
binary vote are unchanged. Final operating threshold: NOT FROZEN. Required
service loading rejects missing, corrupt or incompatible calibration; no fallback.

104 tests passed, 0 failed, 0 skipped, 0 blocked; 7 legacy validation-membership
tests deliberately deselected and left unchanged. Actual calibrated dm_b_v1
reload, deterministic inference and configured service/API smoke passed.
D_M-A and its calibration passed real-model regression; D_S tests passed.
All 46 preflight-frozen files retain their hashes. v5 is preserved unchanged.

VALIDATION used: NO. Protected data used: NO. E1-E10/ensembles/D_G: NOT RUN.
Fitting-partition Brier/log loss diagnostics do not establish generalization or
distribution-shift calibration quality. The approved development corpus is narrow.

Evidence: artifacts/models/dm_b_v1/calibration/verification.json,
test_evidence.json, test_results.xml; TECH_SEM_002_CALIBRATION_REPORT_v1.md and
TECH_SEM_002_CALIBRATION_TEST_REPORT_v1.md.

Recommendation: READY FOR DETECTOR STACK INTEGRATION AFTER TECH-GUARD-001.
This does not authorize or establish readiness for E1-E10.
