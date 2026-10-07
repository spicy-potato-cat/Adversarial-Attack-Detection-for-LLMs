# EXP-PROTOCOL-001 Final Validation

Status: PASS. Full required offline protocol and accepted Cycle-1 regression; zero failures/errors/skips.

Test source commit is the Phase-17/18 commit with pending validation harness/test hashes separately recorded. No model/run provenance was rewritten.

The initial combined process had 782 passes and one global sys.modules isolation failure. Semantic acceptance imports torch at collection, incompatible with the older common-mode fresh-process assertion. That failed receipt is NOT accepted. All required tests were rerun in separate fresh offline pytest processes; existing tests were not changed, skipped, or weakened. Receipt aggregation checks complete module coverage, counts, uniqueness, and zero failures/errors/skips.

Network sockets were blocked by the explicit pytest plugin and audit context. No network download/API/model inference or real future-regime activity occurred. Negative socket tests exercise the block without making connections.

Two reconstructions wrote only temporary directories and matched every frozen byte. All temporary tampering was restored/removed; accepted artifacts were never modified.

```json
{
  "evidence_version": "final_validation_evidence_v1",
  "status": "PASS",
  "source_commit": "773853e6cf39130708e9780d84d6bd9173a1613c",
  "pending_validation_code_sha": {
    "detection_service/research_protocol/release_validation.py": "10220e31dde654ec1278cd3f9a01c72c206c41068833df275a02ad178238e83d",
    "detection_service/tests/test_protocol_release_audit.py": "84cff9302378f7c052f8304d2be3d1d8aa2bf22fe57c49a8bfc84a90658bfac0"
  },
  "tests": {
    "tests": 788,
    "failures": 0,
    "errors": 0,
    "skipped": 0,
    "passed": 788,
    "receipts": [
      {
        "path": "tmp\\protocol_final_model_free.xml",
        "sha256": "e27977fd78e4128767ac76003035e89aeb18fd28a0182f10532269a4687947d5",
        "tests": 84,
        "failures": 0,
        "errors": 0,
        "skipped": 0,
        "seconds": 1.028
      },
      {
        "path": "tmp\\protocol_final_remaining.xml",
        "sha256": "4fbea325b884223172d6da320d114025ba9c5bb86c26f124644c33b946cf97f1",
        "tests": 704,
        "failures": 0,
        "errors": 0,
        "skipped": 0,
        "seconds": 739.418
      }
    ],
    "case_ids_sha": "38c8b4008df3de9eac93608189990cded026eac18497edc1026d3f3bab8cd1c4",
    "seconds": 740.446,
    "modules": [
      "detection_service.tests.test_common_mode",
      "detection_service.tests.test_common_mode_final_acceptance",
      "detection_service.tests.test_core_metrics",
      "detection_service.tests.test_cross_regime",
      "detection_service.tests.test_detector_semantics",
      "detection_service.tests.test_operating_policy",
      "detection_service.tests.test_prediction_adapters",
      "detection_service.tests.test_protocol_lock",
      "detection_service.tests.test_protocol_release",
      "detection_service.tests.test_protocol_release_audit",
      "detection_service.tests.test_r0_operational",
      "detection_service.tests.test_r0_reproduction",
      "detection_service.tests.test_regime_contract",
      "detection_service.tests.test_semantic_oof_acceptance",
      "detection_service.tests.test_statistical_feature_ablation_acceptance",
      "detection_service.tests.test_statistical_scorer_acceptance",
      "detection_service.tests.test_track2_completion",
      "detection_service.tests.test_uncertainty"
    ]
  },
  "test_commands": [
    [
      ".local-python/python.exe",
      "-m",
      "pytest",
      "detection_service/tests/test_common_mode.py",
      "detection_service/tests/test_common_mode_final_acceptance.py",
      "detection_service/tests/test_track2_completion.py",
      "-p",
      "detection_service.research_protocol.release_validation",
      "-o",
      "addopts=",
      "-q",
      "--tb=line",
      "--junitxml=tmp/protocol_final_model_free.xml"
    ],
    [
      ".local-python/python.exe",
      "-m",
      "pytest",
      "detection_service/tests/test_detector_semantics.py",
      "detection_service/tests/test_prediction_adapters.py",
      "detection_service/tests/test_regime_contract.py",
      "detection_service/tests/test_operating_policy.py",
      "detection_service/tests/test_core_metrics.py",
      "detection_service/tests/test_uncertainty.py",
      "detection_service/tests/test_cross_regime.py",
      "detection_service/tests/test_r0_reproduction.py",
      "detection_service/tests/test_r0_operational.py",
      "detection_service/tests/test_protocol_lock.py",
      "detection_service/tests/test_protocol_release.py",
      "detection_service/tests/test_protocol_release_audit.py",
      "detection_service/tests/test_semantic_oof_acceptance.py",
      "detection_service/tests/test_statistical_scorer_acceptance.py",
      "detection_service/tests/test_statistical_feature_ablation_acceptance.py",
      "-p",
      "detection_service.research_protocol.release_validation",
      "-o",
      "addopts=",
      "-q",
      "--tb=line",
      "--junitxml=tmp/protocol_final_remaining.xml"
    ]
  ],
  "initial_combined_run": {
    "tests": 783,
    "passed": 782,
    "failures": 1,
    "receipt_sha": "1739ac4b794d92a66fc6482d451ee809bd38611c1852c273acf8e396c863c1c8",
    "accepted": false,
    "failing_test": "test_common_mode.py::test_analyze_order_grouped_and_no_model_imports",
    "diagnosis": "semantic_oof_acceptance imports semantic_oof, which imports torch at collection; common_mode asserts torch absent from global sys.modules",
    "resolution": "Separate fresh pytest processes for model-free suites and remaining suites; no existing tests changed or skipped"
  },
  "baseline_preservation": {
    "status": "PASS",
    "hash_checks": 96,
    "evidence_sha256": "4b42dd44f2604f12e099f1fc60decef866c64d036c9a6554fcd3e049513b8a21",
    "tracked_baseline_diff": "EMPTY"
  },
  "frozen_detector_checks": 165,
  "lock_bindings": 101,
  "historical_R0": {
    "report_version": "r0_reproduction_report_v1",
    "status": "PASS",
    "population_count": 1135,
    "attack_count": 183,
    "benign_count": 952,
    "pre_R0_machinery_commit": "9982b9bd2c5f8da7fc63a1b7977c1cccf91cfb70",
    "import_manifest_sha": "6efb88a756bc12558f2e7bdbba72854f8fb37aca6bfd73a30b20509d9b93983b",
    "decision_artifact_sha": "5a9238e4a32bcf48fa186ffcd0b8306396bf932bde599b9ba7347e698c872aaf",
    "decision_rows": 10215,
    "integer_counts": "EXACT_AT_ALL_THREE_BUDGETS",
    "derived_metric_tolerance": 1e-12,
    "ranking_tolerance": 1e-12,
    "historical_ci_tolerance": 1e-12,
    "alignment_shas": {
      "1PCT": "bc4ea1c7679f3e316f39a1ee283be4f61c9aadfe7bbc3d6a8bd6fbfeef1be1a7",
      "3PCT": "6eda322d9bf5542c4875f697a03ace50272ceeecf081a1aff65aa8b9f685ba63",
      "5PCT": "d8829f9e6847e07273a8f8e3d8c81b02f5ee31767a4695fcba19cae42df280a0"
    },
    "historical_uncertainty": "PASS_EXPLICIT_LEGACY_RNG_REPLAY",
    "production_rng": "NUMPY_PCG64_UNCHANGED",
    "historical_rng": "PYTHON_RANDOM_MT19937",
    "method_difference": "EXPLICIT_AND_RESOLVED_NOT_IDENTICAL_RNG",
    "descriptive_frontier_reproduced": true,
    "new_model_inference": false,
    "OOF_final_model_substitution": false,
    "operational_thresholds_used": false,
    "future_regimes": {
      "R0": "OBSERVED",
      "R1": "NOT_RUN",
      "R2-D_S": "NOT_RUN",
      "R2-D_M-B": "NOT_RUN",
      "R2-D_G": "NOT_RUN",
      "R3": "NOT_RUN"
    },
    "Cycle2": "DEFERRED",
    "Phase14": "NOT_STARTED",
    "source_hash_checks": 123,
    "fold_membership_hash_checks": 20,
    "phase11_13_hash_checks": 33,
    "deterministic_reconstruction": "BYTE_IDENTICAL"
  },
  "operational_R0": {
    "status": "PASS",
    "hash_checks": 8,
    "byte_identical": true
  },
  "release_inventory": {
    "status": "PASS",
    "hash_checks": 109,
    "unique_authoritative_roles": 11,
    "byte_identical": true
  },
  "deterministic_reconstruction": {
    "status": "PASS",
    "passes": 2,
    "byte_identical": true,
    "artifacts_per_pass": 13,
    "sha256": {
      "artifacts/research_protocol/phase14_artifact_hashes_v1.json": "57792c8d4dabd9bd38c35d7ca813dca8b58683233f5fc366ccd8c7fcf336abc1",
      "artifacts/research_protocol/phase15_artifact_hashes_v1.json": "832d78be3f713af810783cf9f8fbb67854b780b111f9040813e876cbbd9cd2b7",
      "artifacts/research_protocol/phase17_18_artifact_hashes_v1.json": "52261e63697ac22f70f2586194069b129af5f370b563fb52bd58ae54389afec7",
      "artifacts/research_protocol/protocol_lock_manifest_v1.json": "d0e1f38898b4f82c93daaa6425f4ddb3592fe080fe50db6ef36f2be9dbed2353",
      "artifacts/research_protocol/r0/r0_operational_cross_regime_matrix_v1.json": "8bdb34bdc502e9fd06c39b48791d1751b4a93846b6ad4d11e076fd851dc9ecc1",
      "artifacts/research_protocol/r0/r0_operational_metrics_v1.json": "a0899a5aba12e1fb473865ae67f650ebd637b744328f7342db6f9e49af619302",
      "artifacts/research_protocol/r0/r0_operational_predictions_v1.csv": "2a40aba6e57fb62c6f843cb834488c2536911aac7c2d3eb0448c77c4f93c5a30",
      "artifacts/research_protocol/r0/r0_operational_result_bundle_v1.json": "b63b25ed4b2eafc3f6e6dd09b8cce96f4acfebff599728650260f8e786e68133",
      "artifacts/research_protocol/r0/r0_operational_uncertainty_v1.json": "5ece35c05fe3b0acf0022d75b059bcee8e15c4b5b6a04373d9387f185a2feb56",
      "artifacts/research_protocol/release/experiment_execution_template_v1.json": "e51a2587852815fdd2954453b3f4f18b58f9f0495262e31cbfac85eae0aaeaae",
      "artifacts/research_protocol/release/protocol_release_inventory_v1.json": "b04002287dfc22f5dc933f9270a5511de03b4f7877c90a72e93025ca0d75cf22",
      "artifacts/research_protocol/release/protocol_release_manifest_v1.json": "c6a6678c7c95a870812cb8d4ea4d7a547faec6465ea7b5a85d0f38914ac4a58f",
      "reviews/EXP_PROTOCOL_001_R0_OPERATIONAL_BASELINE_v1.md": "831b9ce83da128ad312315a87f36bb0ef8ab36e117e234a2b2ab03be75cd482f"
    }
  },
  "tamper": {
    "status": "PASS",
    "rejected": 16,
    "cases": [
      {
        "case": "D_S_threshold",
        "status": "REJECTED",
        "reason": "AUTHORITATIVE_ARTIFACT_DRIFT"
      },
      {
        "case": "D_M-B_threshold",
        "status": "REJECTED",
        "reason": "AUTHORITATIVE_ARTIFACT_DRIFT"
      },
      {
        "case": "D_G_threshold",
        "status": "REJECTED",
        "reason": "AUTHORITATIVE_ARTIFACT_DRIFT"
      },
      {
        "case": "threshold_id",
        "status": "REJECTED",
        "reason": "AUTHORITATIVE_ARTIFACT_DRIFT"
      },
      {
        "case": "detector_order",
        "status": "REJECTED",
        "reason": "AUTHORITATIVE_ARTIFACT_DRIFT"
      },
      {
        "case": "score_direction",
        "status": "REJECTED",
        "reason": "AUTHORITATIVE_ARTIFACT_DRIFT"
      },
      {
        "case": "operating_hash",
        "status": "REJECTED",
        "reason": "AUTHORITATIVE_ARTIFACT_DRIFT"
      },
      {
        "case": "core_contract",
        "status": "REJECTED",
        "reason": "AUTHORITATIVE_ARTIFACT_DRIFT"
      },
      {
        "case": "uncertainty_contract",
        "status": "REJECTED",
        "reason": "AUTHORITATIVE_ARTIFACT_DRIFT"
      },
      {
        "case": "cross_regime_contract",
        "status": "REJECTED",
        "reason": "AUTHORITATIVE_ARTIFACT_DRIFT"
      },
      {
        "case": "prediction_schema",
        "status": "REJECTED",
        "reason": "AUTHORITATIVE_ARTIFACT_DRIFT"
      },
      {
        "case": "regime_contract",
        "status": "REJECTED",
        "reason": "AUTHORITATIVE_ARTIFACT_DRIFT"
      },
      {
        "case": "decision_view_override",
        "status": "REJECTED"
      },
      {
        "case": "comparison_view_id_override",
        "status": "REJECTED"
      },
      {
        "case": "operating_policy_sha_override",
        "status": "REJECTED"
      },
      {
        "case": "action_override",
        "status": "REJECTED"
      }
    ],
    "real_artifacts_modified": false
  },
  "preflights": {
    "r1": {
      "status": "PASS",
      "purpose": "TEST_FIXTURE",
      "experiment_id": "EXP-R1-bca51d745bc791a55a6ec54f66732a865e4c0daef51ee6c7990bd465649f693c",
      "protocol_lock_sha": "d0e1f38898b4f82c93daaa6425f4ddb3592fe080fe50db6ef36f2be9dbed2353",
      "operating_policy_sha": "06fa4548a62ae0e0968f9d93339910f8841a0f366b5346b0892a2be6904fb0cc",
      "experiment_executed": false
    },
    "r2_ds": {
      "status": "PASS",
      "purpose": "TEST_FIXTURE",
      "experiment_id": "EXP-R2-0c9ca2a2dc30b7ab4fd5b84a4e7d3da79919bf2302d2c5f92b53d39db6001ed4",
      "protocol_lock_sha": "d0e1f38898b4f82c93daaa6425f4ddb3592fe080fe50db6ef36f2be9dbed2353",
      "operating_policy_sha": "06fa4548a62ae0e0968f9d93339910f8841a0f366b5346b0892a2be6904fb0cc",
      "experiment_executed": false
    },
    "r2_dmb": {
      "status": "PASS",
      "purpose": "TEST_FIXTURE",
      "experiment_id": "EXP-R2-87eaa4f59916cc5452d2829818052691a437ca85a985c885eb7c28902323914a",
      "protocol_lock_sha": "d0e1f38898b4f82c93daaa6425f4ddb3592fe080fe50db6ef36f2be9dbed2353",
      "operating_policy_sha": "06fa4548a62ae0e0968f9d93339910f8841a0f366b5346b0892a2be6904fb0cc",
      "experiment_executed": false
    },
    "r2_dg": {
      "status": "PASS",
      "purpose": "TEST_FIXTURE",
      "experiment_id": "EXP-R2-2e63b3e39821dad3e6b5f73269d4dd6e5d50470f24149ca715604924698ee0dc",
      "protocol_lock_sha": "d0e1f38898b4f82c93daaa6425f4ddb3592fe080fe50db6ef36f2be9dbed2353",
      "operating_policy_sha": "06fa4548a62ae0e0968f9d93339910f8841a0f366b5346b0892a2be6904fb0cc",
      "experiment_executed": false
    },
    "r3": {
      "status": "PASS",
      "purpose": "TEST_FIXTURE",
      "experiment_id": "EXP-R3-ae6c9d9108f617d1c17ed89a4102e9f07cffd9f4d0b4d13f3ceefb2298c10f51",
      "protocol_lock_sha": "d0e1f38898b4f82c93daaa6425f4ddb3592fe080fe50db6ef36f2be9dbed2353",
      "operating_policy_sha": "06fa4548a62ae0e0968f9d93339910f8841a0f366b5346b0892a2be6904fb0cc",
      "experiment_executed": false
    }
  },
  "network_activity": "NONE",
  "R1_R2_R3_activity": "NONE",
  "Cycle2": "DEFERRED",
  "Phase16": "PHASE_16_NOT_DEFINED_IN_APPROVED_PLAN"
}
```
