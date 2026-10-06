# TECH-COMMON-003 Test Report

## Tests and preservation

```json
{
  "tests": {
    "postrun_model_free": {
      "status": "PASS",
      "tests": 84,
      "failures": 0,
      "errors": 0,
      "skipped": 0,
      "path": "C:\\Users\\harsh\\Adversarial-Attack-Detection-for-LLMs\\tmp\\track2_postrun_common.xml",
      "sha256": "b0eab9d79faad24dfb3ffd3fb5ce6f3ede78cce27b7a5013663860fd7c5e57f3"
    },
    "postrun_guard_fixture": {
      "status": "PASS",
      "tests": 115,
      "failures": 0,
      "errors": 0,
      "skipped": 0,
      "path": "C:\\Users\\harsh\\Adversarial-Attack-Detection-for-LLMs\\tmp\\track2_postrun_guard.xml",
      "sha256": "f1c89febf61f2a4e539ea3f3890c10159aa06dc3a28c74cced8e6d515de46b52"
    }
  },
  "preservation": {
    "strict_original_suite": {
      "returncode": 0,
      "status": "PASS",
      "command": "python -m detection_service.scripts.verify_quality_preservation --mode check"
    },
    "baseline_files": 96,
    "exact_byte_matches": 96,
    "newline_only_matches": 0,
    "newline_differences": [],
    "unexplained_changes": 0,
    "tracked_detector_diff": "EMPTY",
    "original_track2_artifacts_and_reports_verified": 62,
    "historical_evidence": "BYTE_IDENTICAL",
    "stat004_sha256": {
      "artifacts/statistical_v2/feature_ablation/resume_20000/block_fold_metrics_v1.json": "2f3823da52fd0d9874fd89e14d4d7feb791225ea690ed3956d1d381f847df7c5",
      "artifacts/statistical_v2/feature_ablation/resume_20000/block_metrics_v1.json": "73a5225e6bcfdbb889014e732727d96b21bc8a59230955478908ebd677d5f64f",
      "artifacts/statistical_v2/feature_ablation/resume_20000/block_predictions_v1.csv": "32e21d581b433a422e4f438274a01d0719ccbae1c8f4788505e30f05c2414f2e",
      "artifacts/statistical_v2/feature_ablation/resume_20000/error_bank_transition_v1.json": "625e6a357d2495a4f06e992874a8eeab2699c6dfa4d9dcb61469e94a13fcc1d9",
      "artifacts/statistical_v2/feature_ablation/resume_20000/fold_references_v1.json": "38fc670b45fac1f776e3c30986ccf5e6f318276011576ef33bed196e69cac691",
      "artifacts/statistical_v2/feature_ablation/resume_20000/lr_convergence_v1.json": "6c9d80b0e029e34e966389339b8a1f83cfee54c286e075e834da7f8c6cbea7a4",
      "artifacts/statistical_v2/feature_ablation/resume_20000/paired_comparison_v1.json": "64e7aa9d17b0f181ed8cb0ec82be6666841c65963a08d3a60a097f008d3bb71c",
      "artifacts/statistical_v2/feature_ablation/resume_20000/selected_representation_v1.json": "05c0ab4f01cceb2a57e70e9ed0fe68717a0118a8d0a8cedf6bb5d26b5857adf2",
      "artifacts/statistical_v2/feature_ablation/resume_20000/short_prompt_analysis_v1.json": "f26ed7323d76562c0261c4670719acda4a054d3d4a201fab66a3a401b01d42e3"
    },
    "interpretation": "Strict preservation suite passes with exact baseline bytes."
  }
}
```
Initial combined pytest collected guard Torch imports and failed one model-free import-isolation assertion. Suites were rerun in separate processes without altering that assertion; all passed. Authoritative OOF evidence remains byte-identical and independently reconstructed. Prior final ds_v2/STACK-001 files were preserved byte-for-byte locally before the requested divergent branch switch; accepted history was not merged or rewritten.

