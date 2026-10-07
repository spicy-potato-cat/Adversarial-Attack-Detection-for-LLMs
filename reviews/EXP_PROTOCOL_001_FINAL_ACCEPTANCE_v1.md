# EXP-PROTOCOL-001 Final Acceptance

STATUS: PASS

Phases 0-15, 17-20: PASS. Phase 16: PHASE_16_NOT_DEFINED_IN_APPROVED_PLAN.

## Authoritative Commit Chain

Cycle-1: dc6dd3041643fb70ad5b128d32c246f8763a8044

Phase 13: f533c106765041932271b56c8ccfa30d1efe691c

- phase14_commit: 2941f1412d15f16bfc1564d1d584a76c0b909df3
- phase15_commit: d98fc5a64e09b756ef8652301e79d1d97755639c
- phase17_18_commit: 773853e6cf39130708e9780d84d6bd9173a1613c
- phase19_commit: d7e4397a05d5b08ba1df3c73a19a38315f59697b

The Phase-20 evidence commit is external to these self-hashed artifacts and reported at handoff. Model/run commits remain unchanged.

## Frozen Thresholds

- D_S: 0.5585373573968287; ds_v2_op3_cal_v1; calibrated_score; >=.
- D_M-B: 0.0004967087297700347; dm_b_v1_op3_raw_v1; raw_score; >=.
- D_G: 0.21291141211986545; dg_v1_op3_raw_v1; raw_score; >=.

## R0 And Validation

Historical descriptive 1/3/5% evidence reproduces exactly, including separately labelled historical RNG replay. Operational baseline uses accepted OOF/OOF/frozen-development scores, the frozen D_S calibrator and fixed policy. The CALIBRATION 3% budget does not guarantee 3% R0 FPR. No thresholds were reselected.

```json
{
  "operational_metrics": {
    "common_mode": {
      "alignment_sha": "2f5f7083f493fd52e845f0a3b6a1a544255732b741036728b43908d0d5c80fa2",
      "all_three_fn_count": 2,
      "all_three_jfn": {
        "denominator": 183,
        "numerator": 2,
        "reason": null,
        "status": "DEFINED",
        "value": 0.01092896174863388
      },
      "attack_count": 183,
      "benign_count": 952,
      "coverage": {
        "coverage_rate": 1.0,
        "expected_predictions": 3405,
        "missing_decisions": 0,
        "missing_predictions": 0,
        "non_ok_predictions": 0,
        "ok_predictions": 3405,
        "received_predictions": 3405,
        "status": "COMPLETE"
      },
      "metric_status": "COMPLETE",
      "pairs": [
        {
          "ejf": {
            "reason": null,
            "status": "DEFINED",
            "value": 0.006748484577025292
          },
          "fn_jaccard": {
            "denominator": 70,
            "numerator": 2,
            "reason": null,
            "status": "DEFINED",
            "value": 0.02857142857142857
          },
          "independence_reference": {
            "reason": null,
            "status": "DEFINED",
            "value": 0.004180477171608588
          },
          "intersection_count": 2,
          "jfn": {
            "denominator": 183,
            "numerator": 2,
            "reason": null,
            "status": "DEFINED",
            "value": 0.01092896174863388
          },
          "left_detector": "ds_v2",
          "left_fnr": {
            "denominator": 183,
            "numerator": 70,
            "reason": null,
            "status": "DEFINED",
            "value": 0.3825136612021858
          },
          "right_detector": "dm_b_v1",
          "right_fnr": {
            "denominator": 183,
            "numerator": 2,
            "reason": null,
            "status": "DEFINED",
            "value": 0.01092896174863388
          },
          "shared_fn_count": 2,
          "union_count": 70
        },
        {
          "ejf": {
            "reason": null,
            "status": "DEFINED",
            "value": -0.010570635133924589
          },
          "fn_jaccard": {
            "denominator": 159,
            "numerator": 52,
            "reason": null,
            "status": "DEFINED",
            "value": 0.3270440251572327
          },
          "independence_reference": {
            "reason": null,
            "status": "DEFINED",
            "value": 0.29472364059840545
          },
          "intersection_count": 52,
          "jfn": {
            "denominator": 183,
            "numerator": 52,
            "reason": null,
            "status": "DEFINED",
            "value": 0.28415300546448086
          },
          "left_detector": "ds_v2",
          "left_fnr": {
            "denominator": 183,
            "numerator": 70,
            "reason": null,
            "status": "DEFINED",
            "value": 0.3825136612021858
          },
          "right_detector": "dg_v1",
          "right_fnr": {
            "denominator": 183,
            "numerator": 141,
            "reason": null,
            "status": "DEFINED",
            "value": 0.7704918032786885
          },
          "shared_fn_count": 52,
          "union_count": 159
        },
        {
          "ejf": {
            "reason": null,
            "status": "DEFINED",
            "value": 0.002508286302965153
          },
          "fn_jaccard": {
            "denominator": 141,
            "numerator": 2,
            "reason": null,
            "status": "DEFINED",
            "value": 0.014184397163120567
          },
          "independence_reference": {
            "reason": null,
            "status": "DEFINED",
            "value": 0.008420675445668727
          },
          "intersection_count": 2,
          "jfn": {
            "denominator": 183,
            "numerator": 2,
            "reason": null,
            "status": "DEFINED",
            "value": 0.01092896174863388
          },
          "left_detector": "dm_b_v1",
          "left_fnr": {
            "denominator": 183,
            "numerator": 2,
            "reason": null,
            "status": "DEFINED",
            "value": 0.01092896174863388
          },
          "right_detector": "dg_v1",
          "right_fnr": {
            "denominator": 183,
            "numerator": 141,
            "reason": null,
            "status": "DEFINED",
            "value": 0.7704918032786885
          },
          "shared_fn_count": 2,
          "union_count": 141
        }
      ],
      "population_count": 1135,
      "provenance": {
        "decision_view": "OPERATIONAL",
        "detector_manifest_sha": "2da5aa92cb14ac19cd49fa7150e7a4ef79b59e1e5fb1aa8ba4148456da618f31",
        "evidence_kind": "ACCEPTED_METADATA",
        "experiment_id": "EXP-R0-dec14451f0449d66be0d157f6fc3f76ad7dc8cf7a19dde7f8e0b62cbaa846883",
        "explicit_decisions_sha": null,
        "explicit_provenance_id": null,
        "operating_policy_sha": "06fa4548a62ae0e0968f9d93339910f8841a0f366b5346b0892a2be6904fb0cc",
        "operational_prediction_schema_sha": "3803cbf2f2c5c568894d894ccc51b64b86ff4f4ed2c5fa6a1e06b9d80512d173",
        "operational_threshold_ids": [
          "ds_v2_op3_cal_v1",
          "dm_b_v1_op3_raw_v1",
          "dg_v1_op3_raw_v1"
        ],
        "operational_thresholds": [
          0.5585373573968287,
          0.0004967087297700347,
          0.21291141211986545
        ],
        "partition": "BASE_TRAIN",
        "prediction_batch_sha": "51ecc613783fc1eaaa7d45749cf6714103243917af3cdfab68c8196b72cba987",
        "prediction_schema_sha": "f61cc717b6118e288201ee8525b41e6806a642d665c42c0d1b9d6d1bcde2e484",
        "primary_detector_ids": [
          "ds_v2",
          "dm_b_v1",
          "dg_v1"
        ],
        "primary_detector_labels": [
          "D_S",
          "D_M-B",
          "D_G"
        ],
        "regime_contract_sha": "716631bec5e7bbe562acd375c90260f5bf11f92cffb6c6d63a7639908408c149",
        "regime_manifest_sha": "398039e4cfecc8d78e3d2f6998fc4e6a1b2e23ab06329a932618d72e7209a0d0",
        "threat_regime": "R0_NON_ADAPTIVE"
      },
      "result_version": "common_mode_metrics_v1"
    },
    "evasion_transfer": null,
    "failure_patterns": {
      "alignment_sha": "2f5f7083f493fd52e845f0a3b6a1a544255732b741036728b43908d0d5c80fa2",
      "attack_count": 183,
      "benign_count": 952,
      "bit_order": "S/M/G",
      "bit_semantics": "0=CATCH;1=MISS",
      "coverage": {
        "coverage_rate": 1.0,
        "expected_predictions": 3405,
        "missing_decisions": 0,
        "missing_predictions": 0,
        "non_ok_predictions": 0,
        "ok_predictions": 3405,
        "received_predictions": 3405,
        "status": "COMPLETE"
      },
      "metric_status": "COMPLETE",
      "patterns": [
        {
          "attack_rate": {
            "denominator": 183,
            "numerator": 24,
            "reason": null,
            "status": "DEFINED",
            "value": 0.13114754098360656
          },
          "count": 24,
          "meaning": "All three catch",
          "pattern_id": "000"
        },
        {
          "attack_rate": {
            "denominator": 183,
            "numerator": 89,
            "reason": null,
            "status": "DEFINED",
            "value": 0.48633879781420764
          },
          "count": 89,
          "meaning": "Only D_G misses",
          "pattern_id": "001"
        },
        {
          "attack_rate": {
            "denominator": 183,
            "numerator": 0,
            "reason": null,
            "status": "DEFINED",
            "value": 0.0
          },
          "count": 0,
          "meaning": "Only D_M-B misses",
          "pattern_id": "010"
        },
        {
          "attack_rate": {
            "denominator": 183,
            "numerator": 0,
            "reason": null,
            "status": "DEFINED",
            "value": 0.0
          },
          "count": 0,
          "meaning": "D_M-B and D_G miss; D_S catches",
          "pattern_id": "011"
        },
        {
          "attack_rate": {
            "denominator": 183,
            "numerator": 18,
            "reason": null,
            "status": "DEFINED",
            "value": 0.09836065573770492
          },
          "count": 18,
          "meaning": "Only D_S misses",
          "pattern_id": "100"
        },
        {
          "attack_rate": {
            "denominator": 183,
            "numerator": 50,
            "reason": null,
            "status": "DEFINED",
            "value": 0.273224043715847
          },
          "count": 50,
          "meaning": "D_S and D_G miss; D_M-B catches",
          "pattern_id": "101"
        },
        {
          "attack_rate": {
            "denominator": 183,
            "numerator": 0,
            "reason": null,
            "status": "DEFINED",
            "value": 0.0
          },
          "count": 0,
          "meaning": "D_S and D_M-B miss; D_G catches",
          "pattern_id": "110"
        },
        {
          "attack_rate": {
            "denominator": 183,
            "numerator": 2,
            "reason": null,
            "status": "DEFINED",
            "value": 0.01092896174863388
          },
          "count": 2,
          "meaning": "All three miss",
          "pattern_id": "111"
        }
      ],
      "population_count": 1135,
      "provenance": {
        "decision_view": "OPERATIONAL",
        "detector_manifest_sha": "2da5aa92cb14ac19cd49fa7150e7a4ef79b59e1e5fb1aa8ba4148456da618f31",
        "evidence_kind": "ACCEPTED_METADATA",
        "experiment_id": "EXP-R0-dec14451f0449d66be0d157f6fc3f76ad7dc8cf7a19dde7f8e0b62cbaa846883",
        "explicit_decisions_sha": null,
        "explicit_provenance_id": null,
        "operating_policy_sha": "06fa4548a62ae0e0968f9d93339910f8841a0f366b5346b0892a2be6904fb0cc",
        "operational_prediction_schema_sha": "3803cbf2f2c5c568894d894ccc51b64b86ff4f4ed2c5fa6a1e06b9d80512d173",
        "operational_threshold_ids": [
          "ds_v2_op3_cal_v1",
          "dm_b_v1_op3_raw_v1",
          "dg_v1_op3_raw_v1"
        ],
        "operational_thresholds": [
          0.5585373573968287,
          0.0004967087297700347,
          0.21291141211986545
        ],
        "partition": "BASE_TRAIN",
        "prediction_batch_sha": "51ecc613783fc1eaaa7d45749cf6714103243917af3cdfab68c8196b72cba987",
        "prediction_schema_sha": "f61cc717b6118e288201ee8525b41e6806a642d665c42c0d1b9d6d1bcde2e484",
        "primary_detector_ids": [
          "ds_v2",
          "dm_b_v1",
          "dg_v1"
        ],
        "primary_detector_labels": [
          "D_S",
          "D_M-B",
          "D_G"
        ],
        "regime_contract_sha": "716631bec5e7bbe562acd375c90260f5bf11f92cffb6c6d63a7639908408c149",
        "regime_manifest_sha": "398039e4cfecc8d78e3d2f6998fc4e6a1b2e23ab06329a932618d72e7209a0d0",
        "threat_regime": "R0_NON_ADAPTIVE"
      },
      "result_version": "failure_patterns_v1"
    },
    "individual": {
      "alignment_sha": "2f5f7083f493fd52e845f0a3b6a1a544255732b741036728b43908d0d5c80fa2",
      "attack_count": 183,
      "benign_count": 952,
      "coverage": {
        "coverage_rate": 1.0,
        "expected_predictions": 3405,
        "missing_decisions": 0,
        "missing_predictions": 0,
        "non_ok_predictions": 0,
        "ok_predictions": 3405,
        "received_predictions": 3405,
        "status": "COMPLETE"
      },
      "detectors": [
        {
          "accuracy": {
            "denominator": 1135,
            "numerator": 1022,
            "reason": null,
            "status": "DEFINED",
            "value": 0.9004405286343612
          },
          "attack_count": 183,
          "benign_count": 952,
          "coverage": {
            "coverage_rate": 1.0,
            "expected_predictions": 1135,
            "missing_decisions": 0,
            "missing_predictions": 0,
            "non_ok_predictions": 0,
            "ok_predictions": 1135,
            "received_predictions": 1135,
            "status": "COMPLETE"
          },
          "detector_id": "ds_v2",
          "f1": {
            "denominator": 339,
            "numerator": 226,
            "reason": null,
            "status": "DEFINED",
            "value": 0.6666666666666666
          },
          "fn": 70,
          "fnr": {
            "denominator": 183,
            "numerator": 70,
            "reason": null,
            "status": "DEFINED",
            "value": 0.3825136612021858
          },
          "fp": 43,
          "fpr": {
            "denominator": 952,
            "numerator": 43,
            "reason": null,
            "status": "DEFINED",
            "value": 0.045168067226890755
          },
          "metric_status": "COMPLETE",
          "npv": {
            "denominator": 979,
            "numerator": 909,
            "reason": null,
            "status": "DEFINED",
            "value": 0.9284984678243106
          },
          "population_count": 1135,
          "precision": {
            "denominator": 156,
            "numerator": 113,
            "reason": null,
            "status": "DEFINED",
            "value": 0.7243589743589743
          },
          "recall": {
            "denominator": 183,
            "numerator": 113,
            "reason": null,
            "status": "DEFINED",
            "value": 0.6174863387978142
          },
          "specificity": {
            "denominator": 952,
            "numerator": 909,
            "reason": null,
            "status": "DEFINED",
            "value": 0.9548319327731093
          },
          "tn": 909,
          "tp": 113
        },
        {
          "accuracy": {
            "denominator": 1135,
            "numerator": 1075,
            "reason": null,
            "status": "DEFINED",
            "value": 0.947136563876652
          },
          "attack_count": 183,
          "benign_count": 952,
          "coverage": {
            "coverage_rate": 1.0,
            "expected_predictions": 1135,
            "missing_decisions": 0,
            "missing_predictions": 0,
            "non_ok_predictions": 0,
            "ok_predictions": 1135,
            "received_predictions": 1135,
            "status": "COMPLETE"
          },
          "detector_id": "dm_b_v1",
          "f1": {
            "denominator": 422,
            "numerator": 362,
            "reason": null,
            "status": "DEFINED",
            "value": 0.8578199052132701
          },
          "fn": 2,
          "fnr": {
            "denominator": 183,
            "numerator": 2,
            "reason": null,
            "status": "DEFINED",
            "value": 0.01092896174863388
          },
          "fp": 58,
          "fpr": {
            "denominator": 952,
            "numerator": 58,
            "reason": null,
            "status": "DEFINED",
            "value": 0.06092436974789916
          },
          "metric_status": "COMPLETE",
          "npv": {
            "denominator": 896,
            "numerator": 894,
            "reason": null,
            "status": "DEFINED",
            "value": 0.9977678571428571
          },
          "population_count": 1135,
          "precision": {
            "denominator": 239,
            "numerator": 181,
            "reason": null,
            "status": "DEFINED",
            "value": 0.7573221757322176
          },
          "recall": {
            "denominator": 183,
            "numerator": 181,
            "reason": null,
            "status": "DEFINED",
            "value": 0.9890710382513661
          },
          "specificity": {
            "denominator": 952,
            "numerator": 894,
            "reason": null,
            "status": "DEFINED",
            "value": 0.9390756302521008
          },
          "tn": 894,
          "tp": 181
        },
        {
          "accuracy": {
            "denominator": 1135,
            "numerator": 977,
            "reason": null,
            "status": "DEFINED",
            "value": 0.8607929515418502
          },
          "attack_count": 183,
          "benign_count": 952,
          "coverage": {
            "coverage_rate": 1.0,
            "expected_predictions": 1135,
            "missing_decisions": 0,
            "missing_predictions": 0,
            "non_ok_predictions": 0,
            "ok_predictions": 1135,
            "received_predictions": 1135,
            "status": "COMPLETE"
          },
          "detector_id": "dg_v1",
          "f1": {
            "denominator": 242,
            "numerator": 84,
            "reason": null,
            "status": "DEFINED",
            "value": 0.34710743801652894
          },
          "fn": 141,
          "fnr": {
            "denominator": 183,
            "numerator": 141,
            "reason": null,
            "status": "DEFINED",
            "value": 0.7704918032786885
          },
          "fp": 17,
          "fpr": {
            "denominator": 952,
            "numerator": 17,
            "reason": null,
            "status": "DEFINED",
            "value": 0.017857142857142856
          },
          "metric_status": "COMPLETE",
          "npv": {
            "denominator": 1076,
            "numerator": 935,
            "reason": null,
            "status": "DEFINED",
            "value": 0.8689591078066915
          },
          "population_count": 1135,
          "precision": {
            "denominator": 59,
            "numerator": 42,
            "reason": null,
            "status": "DEFINED",
            "value": 0.711864406779661
          },
          "recall": {
            "denominator": 183,
            "numerator": 42,
            "reason": null,
            "status": "DEFINED",
            "value": 0.22950819672131148
          },
          "specificity": {
            "denominator": 952,
            "numerator": 935,
            "reason": null,
            "status": "DEFINED",
            "value": 0.9821428571428571
          },
          "tn": 935,
          "tp": 42
        }
      ],
      "metric_status": "COMPLETE",
      "population_count": 1135,
      "provenance": {
        "decision_view": "OPERATIONAL",
        "detector_manifest_sha": "2da5aa92cb14ac19cd49fa7150e7a4ef79b59e1e5fb1aa8ba4148456da618f31",
        "evidence_kind": "ACCEPTED_METADATA",
        "experiment_id": "EXP-R0-dec14451f0449d66be0d157f6fc3f76ad7dc8cf7a19dde7f8e0b62cbaa846883",
        "explicit_decisions_sha": null,
        "explicit_provenance_id": null,
        "operating_policy_sha": "06fa4548a62ae0e0968f9d93339910f8841a0f366b5346b0892a2be6904fb0cc",
        "operational_prediction_schema_sha": "3803cbf2f2c5c568894d894ccc51b64b86ff4f4ed2c5fa6a1e06b9d80512d173",
        "operational_threshold_ids": [
          "ds_v2_op3_cal_v1",
          "dm_b_v1_op3_raw_v1",
          "dg_v1_op3_raw_v1"
        ],
        "operational_thresholds": [
          0.5585373573968287,
          0.0004967087297700347,
          0.21291141211986545
        ],
        "partition": "BASE_TRAIN",
        "prediction_batch_sha": "51ecc613783fc1eaaa7d45749cf6714103243917af3cdfab68c8196b72cba987",
        "prediction_schema_sha": "f61cc717b6118e288201ee8525b41e6806a642d665c42c0d1b9d6d1bcde2e484",
        "primary_detector_ids": [
          "ds_v2",
          "dm_b_v1",
          "dg_v1"
        ],
        "primary_detector_labels": [
          "D_S",
          "D_M-B",
          "D_G"
        ],
        "regime_contract_sha": "716631bec5e7bbe562acd375c90260f5bf11f92cffb6c6d63a7639908408c149",
        "regime_manifest_sha": "398039e4cfecc8d78e3d2f6998fc4e6a1b2e23ab06329a932618d72e7209a0d0",
        "threat_regime": "R0_NON_ADAPTIVE"
      },
      "result_version": "individual_metrics_v1"
    },
    "recovery": {
      "alignment_sha": "2f5f7083f493fd52e845f0a3b6a1a544255732b741036728b43908d0d5c80fa2",
      "attack_count": 183,
      "benign_count": 952,
      "coverage": {
        "coverage_rate": 1.0,
        "expected_predictions": 3405,
        "missing_decisions": 0,
        "missing_predictions": 0,
        "non_ok_predictions": 0,
        "ok_predictions": 3405,
        "received_predictions": 3405,
        "status": "COMPLETE"
      },
      "detectors": [
        {
          "both_others_miss_count": 2,
          "conditional_recovery": {
            "denominator": 2,
            "numerator": 0,
            "reason": null,
            "status": "DEFINED",
            "value": 0.0
          },
          "detector_id": "ds_v2",
          "unique_catch_count": 0,
          "unique_catch_pattern": "011",
          "unique_catch_rate": {
            "denominator": 183,
            "numerator": 0,
            "reason": null,
            "status": "DEFINED",
            "value": 0.0
          }
        },
        {
          "both_others_miss_count": 52,
          "conditional_recovery": {
            "denominator": 52,
            "numerator": 50,
            "reason": null,
            "status": "DEFINED",
            "value": 0.9615384615384616
          },
          "detector_id": "dm_b_v1",
          "unique_catch_count": 50,
          "unique_catch_pattern": "101",
          "unique_catch_rate": {
            "denominator": 183,
            "numerator": 50,
            "reason": null,
            "status": "DEFINED",
            "value": 0.273224043715847
          }
        },
        {
          "both_others_miss_count": 2,
          "conditional_recovery": {
            "denominator": 2,
            "numerator": 0,
            "reason": null,
            "status": "DEFINED",
            "value": 0.0
          },
          "detector_id": "dg_v1",
          "unique_catch_count": 0,
          "unique_catch_pattern": "110",
          "unique_catch_rate": {
            "denominator": 183,
            "numerator": 0,
            "reason": null,
            "status": "DEFINED",
            "value": 0.0
          }
        }
      ],
      "metric_status": "COMPLETE",
      "population_count": 1135,
      "provenance": {
        "decision_view": "OPERATIONAL",
        "detector_manifest_sha": "2da5aa92cb14ac19cd49fa7150e7a4ef79b59e1e5fb1aa8ba4148456da618f31",
        "evidence_kind": "ACCEPTED_METADATA",
        "experiment_id": "EXP-R0-dec14451f0449d66be0d157f6fc3f76ad7dc8cf7a19dde7f8e0b62cbaa846883",
        "explicit_decisions_sha": null,
        "explicit_provenance_id": null,
        "operating_policy_sha": "06fa4548a62ae0e0968f9d93339910f8841a0f366b5346b0892a2be6904fb0cc",
        "operational_prediction_schema_sha": "3803cbf2f2c5c568894d894ccc51b64b86ff4f4ed2c5fa6a1e06b9d80512d173",
        "operational_threshold_ids": [
          "ds_v2_op3_cal_v1",
          "dm_b_v1_op3_raw_v1",
          "dg_v1_op3_raw_v1"
        ],
        "operational_thresholds": [
          0.5585373573968287,
          0.0004967087297700347,
          0.21291141211986545
        ],
        "partition": "BASE_TRAIN",
        "prediction_batch_sha": "51ecc613783fc1eaaa7d45749cf6714103243917af3cdfab68c8196b72cba987",
        "prediction_schema_sha": "f61cc717b6118e288201ee8525b41e6806a642d665c42c0d1b9d6d1bcde2e484",
        "primary_detector_ids": [
          "ds_v2",
          "dm_b_v1",
          "dg_v1"
        ],
        "primary_detector_labels": [
          "D_S",
          "D_M-B",
          "D_G"
        ],
        "regime_contract_sha": "716631bec5e7bbe562acd375c90260f5bf11f92cffb6c6d63a7639908408c149",
        "regime_manifest_sha": "398039e4cfecc8d78e3d2f6998fc4e6a1b2e23ab06329a932618d72e7209a0d0",
        "threat_regime": "R0_NON_ADAPTIVE"
      },
      "result_version": "recovery_metrics_v1"
    },
    "result_version": "core_metrics_bundle_v1"
  },
  "operational_uncertainty": {
    "attack": {
      "alignment_sha": "2f5f7083f493fd52e845f0a3b6a1a544255732b741036728b43908d0d5c80fa2",
      "bootstrap_domain_lineage_count": 183,
      "bootstrap_domain_row_count": 183,
      "config": {
        "confidence_level": 0.95,
        "domain": "ATTACK_ONLY",
        "method": "PERCENTILE_BOOTSTRAP_V1",
        "quantile_method": "linear",
        "replicates": 1000,
        "seed": 1701,
        "target_detector": null,
        "unit": "LINEAGE_CLUSTERED"
      },
      "core_metrics_contract_sha": "86f7dfc69a1841f9ded303bad349f7cbd0082898f1524bdcfac9edb49ef3d2d9",
      "decision_view": "OPERATIONAL",
      "detector_manifest_sha": "2da5aa92cb14ac19cd49fa7150e7a4ef79b59e1e5fb1aa8ba4148456da618f31",
      "experiment_id": "EXP-R0-dec14451f0449d66be0d157f6fc3f76ad7dc8cf7a19dde7f8e0b62cbaa846883",
      "intervals": [
        {
          "ci_lower": 0.0,
          "ci_upper": 0.0273224043715847,
          "metric_id": "all_three/jfn",
          "point_estimate": 0.01092896174863388,
          "replicates_invalid": 0,
          "replicates_requested": 1000,
          "replicates_valid": 1000,
          "status": "ESTIMATED"
        },
        {
          "ci_lower": 0.7103825136612022,
          "ci_upper": 0.8252732240437157,
          "metric_id": "individual/dg_v1/fnr",
          "point_estimate": 0.7704918032786885,
          "replicates_invalid": 0,
          "replicates_requested": 1000,
          "replicates_valid": 1000,
          "status": "ESTIMATED"
        },
        {
          "ci_lower": 0.0,
          "ci_upper": 0.0273224043715847,
          "metric_id": "individual/dm_b_v1/fnr",
          "point_estimate": 0.01092896174863388,
          "replicates_invalid": 0,
          "replicates_requested": 1000,
          "replicates_valid": 1000,
          "status": "ESTIMATED"
        },
        {
          "ci_lower": 0.31693989071038253,
          "ci_upper": 0.453551912568306,
          "metric_id": "individual/ds_v2/fnr",
          "point_estimate": 0.3825136612021858,
          "replicates_invalid": 0,
          "replicates_requested": 1000,
          "replicates_valid": 1000,
          "status": "ESTIMATED"
        },
        {
          "ci_lower": 0.0,
          "ci_upper": 0.0273224043715847,
          "metric_id": "pair/dm_b_v1/dg_v1/jfn",
          "point_estimate": 0.01092896174863388,
          "replicates_invalid": 0,
          "replicates_requested": 1000,
          "replicates_valid": 1000,
          "status": "ESTIMATED"
        },
        {
          "ci_lower": 0.2185792349726776,
          "ci_upper": 0.3442622950819672,
          "metric_id": "pair/ds_v2/dg_v1/jfn",
          "point_estimate": 0.28415300546448086,
          "replicates_invalid": 0,
          "replicates_requested": 1000,
          "replicates_valid": 1000,
          "status": "ESTIMATED"
        },
        {
          "ci_lower": 0.0,
          "ci_upper": 0.0273224043715847,
          "metric_id": "pair/ds_v2/dm_b_v1/jfn",
          "point_estimate": 0.01092896174863388,
          "replicates_invalid": 0,
          "replicates_requested": 1000,
          "replicates_valid": 1000,
          "status": "ESTIMATED"
        },
        {
          "ci_lower": null,
          "ci_upper": null,
          "metric_id": "recovery/dg_v1/conditional_recovery",
          "point_estimate": 0.0,
          "replicates_invalid": 129,
          "replicates_requested": 1000,
          "replicates_valid": 871,
          "status": "UNSTABLE_DENOMINATOR"
        },
        {
          "ci_lower": 0.0,
          "ci_upper": 0.0,
          "metric_id": "recovery/dg_v1/unique_catch_rate",
          "point_estimate": 0.0,
          "replicates_invalid": 0,
          "replicates_requested": 1000,
          "replicates_valid": 1000,
          "status": "ESTIMATED"
        },
        {
          "ci_lower": 0.8965337643678161,
          "ci_upper": 1.0,
          "metric_id": "recovery/dm_b_v1/conditional_recovery",
          "point_estimate": 0.9615384615384616,
          "replicates_invalid": 0,
          "replicates_requested": 1000,
          "replicates_valid": 1000,
          "status": "ESTIMATED"
        },
        {
          "ci_lower": 0.20765027322404372,
          "ci_upper": 0.3333333333333333,
          "metric_id": "recovery/dm_b_v1/unique_catch_rate",
          "point_estimate": 0.273224043715847,
          "replicates_invalid": 0,
          "replicates_requested": 1000,
          "replicates_valid": 1000,
          "status": "ESTIMATED"
        },
        {
          "ci_lower": null,
          "ci_upper": null,
          "metric_id": "recovery/ds_v2/conditional_recovery",
          "point_estimate": 0.0,
          "replicates_invalid": 129,
          "replicates_requested": 1000,
          "replicates_valid": 871,
          "status": "UNSTABLE_DENOMINATOR"
        },
        {
          "ci_lower": 0.0,
          "ci_upper": 0.0,
          "metric_id": "recovery/ds_v2/unique_catch_rate",
          "point_estimate": 0.0,
          "replicates_invalid": 0,
          "replicates_requested": 1000,
          "replicates_valid": 1000,
          "status": "ESTIMATED"
        }
      ],
      "lineage_count": 1134,
      "numpy_version": "2.1.3",
      "operating_policy_sha": "06fa4548a62ae0e0968f9d93339910f8841a0f366b5346b0892a2be6904fb0cc",
      "paired_reference_alignment_sha": null,
      "plan_sha": "79f126c0494e334d9d2fb7d43aa12c4c5fe8f6240d6dd2f4c8e6b77b65b3a852",
      "population_signature": "2031fa90c98d02c7ab22b2c009be2bc1d1fec71ff071c1f3f7c4fa0edd3992bd",
      "prediction_schema_sha": "f61cc717b6118e288201ee8525b41e6806a642d665c42c0d1b9d6d1bcde2e484",
      "regime_manifest_sha": "398039e4cfecc8d78e3d2f6998fc4e6a1b2e23ab06329a932618d72e7209a0d0",
      "result_version": "uncertainty_result_v1",
      "rng_state_after_sha": "e36bce444f0ce9cdf2bb7eaf18bab9f0ecf2c4a8b7e86e91611c8d53921a7b80",
      "rng_state_before_sha": "8beedb764400585e0f5ee0f7644be03d75d8e9eb01dee7f8aa41c7692be3f9c3",
      "uncertainty_contract_sha": "849c2de4182fce5173d03a2278dfa61644d0bd447c492ee0ee06862e6f6e9013",
      "unknown_lineage_rows": 0
    },
    "benign": {
      "alignment_sha": "2f5f7083f493fd52e845f0a3b6a1a544255732b741036728b43908d0d5c80fa2",
      "bootstrap_domain_lineage_count": 951,
      "bootstrap_domain_row_count": 952,
      "config": {
        "confidence_level": 0.95,
        "domain": "BENIGN_ONLY",
        "method": "PERCENTILE_BOOTSTRAP_V1",
        "quantile_method": "linear",
        "replicates": 1000,
        "seed": 1701,
        "target_detector": null,
        "unit": "LINEAGE_CLUSTERED"
      },
      "core_metrics_contract_sha": "86f7dfc69a1841f9ded303bad349f7cbd0082898f1524bdcfac9edb49ef3d2d9",
      "decision_view": "OPERATIONAL",
      "detector_manifest_sha": "2da5aa92cb14ac19cd49fa7150e7a4ef79b59e1e5fb1aa8ba4148456da618f31",
      "experiment_id": "EXP-R0-dec14451f0449d66be0d157f6fc3f76ad7dc8cf7a19dde7f8e0b62cbaa846883",
      "intervals": [
        {
          "ci_lower": 0.00946372239747634,
          "ci_upper": 0.026260504201680673,
          "metric_id": "individual/dg_v1/fpr",
          "point_estimate": 0.017857142857142856,
          "replicates_invalid": 0,
          "replicates_requested": 1000,
          "replicates_valid": 1000,
          "status": "ESTIMATED"
        },
        {
          "ci_lower": 0.04719550194581724,
          "ci_upper": 0.0776495278069255,
          "metric_id": "individual/dm_b_v1/fpr",
          "point_estimate": 0.06092436974789916,
          "replicates_invalid": 0,
          "replicates_requested": 1000,
          "replicates_valid": 1000,
          "status": "ESTIMATED"
        },
        {
          "ci_lower": 0.031512605042016806,
          "ci_upper": 0.058823529411764705,
          "metric_id": "individual/ds_v2/fpr",
          "point_estimate": 0.045168067226890755,
          "replicates_invalid": 0,
          "replicates_requested": 1000,
          "replicates_valid": 1000,
          "status": "ESTIMATED"
        }
      ],
      "lineage_count": 1134,
      "numpy_version": "2.1.3",
      "operating_policy_sha": "06fa4548a62ae0e0968f9d93339910f8841a0f366b5346b0892a2be6904fb0cc",
      "paired_reference_alignment_sha": null,
      "plan_sha": "cbfa2ce47d7aad0a2a72d02abc9dc4a9f3f21ad00ab16f2813175d2061aa98e9",
      "population_signature": "2031fa90c98d02c7ab22b2c009be2bc1d1fec71ff071c1f3f7c4fa0edd3992bd",
      "prediction_schema_sha": "f61cc717b6118e288201ee8525b41e6806a642d665c42c0d1b9d6d1bcde2e484",
      "regime_manifest_sha": "398039e4cfecc8d78e3d2f6998fc4e6a1b2e23ab06329a932618d72e7209a0d0",
      "result_version": "uncertainty_result_v1",
      "rng_state_after_sha": "7b017853ea0351a739366da7f61a18c18d638bc1990c9c128fefc996dafdb2bb",
      "rng_state_before_sha": "8beedb764400585e0f5ee0f7644be03d75d8e9eb01dee7f8aa41c7692be3f9c3",
      "uncertainty_contract_sha": "849c2de4182fce5173d03a2278dfa61644d0bd447c492ee0ee06862e6f6e9013",
      "unknown_lineage_rows": 0
    }
  },
  "final_validation": {
    "Cycle2": "DEFERRED",
    "Phase16": "PHASE_16_NOT_DEFINED_IN_APPROVED_PLAN",
    "R1_R2_R3_activity": "NONE",
    "baseline_preservation": {
      "evidence_sha256": "4b42dd44f2604f12e099f1fc60decef866c64d036c9a6554fcd3e049513b8a21",
      "hash_checks": 96,
      "status": "PASS",
      "tracked_baseline_diff": "EMPTY"
    },
    "deterministic_reconstruction": {
      "artifacts_per_pass": 13,
      "byte_identical": true,
      "passes": 2,
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
      },
      "status": "PASS"
    },
    "evidence_version": "final_validation_evidence_v1",
    "frozen_detector_checks": 165,
    "historical_R0": {
      "Cycle2": "DEFERRED",
      "OOF_final_model_substitution": false,
      "Phase14": "NOT_STARTED",
      "alignment_shas": {
        "1PCT": "bc4ea1c7679f3e316f39a1ee283be4f61c9aadfe7bbc3d6a8bd6fbfeef1be1a7",
        "3PCT": "6eda322d9bf5542c4875f697a03ace50272ceeecf081a1aff65aa8b9f685ba63",
        "5PCT": "d8829f9e6847e07273a8f8e3d8c81b02f5ee31767a4695fcba19cae42df280a0"
      },
      "attack_count": 183,
      "benign_count": 952,
      "decision_artifact_sha": "5a9238e4a32bcf48fa186ffcd0b8306396bf932bde599b9ba7347e698c872aaf",
      "decision_rows": 10215,
      "derived_metric_tolerance": 1e-12,
      "descriptive_frontier_reproduced": true,
      "deterministic_reconstruction": "BYTE_IDENTICAL",
      "fold_membership_hash_checks": 20,
      "future_regimes": {
        "R0": "OBSERVED",
        "R1": "NOT_RUN",
        "R2-D_G": "NOT_RUN",
        "R2-D_M-B": "NOT_RUN",
        "R2-D_S": "NOT_RUN",
        "R3": "NOT_RUN"
      },
      "historical_ci_tolerance": 1e-12,
      "historical_rng": "PYTHON_RANDOM_MT19937",
      "historical_uncertainty": "PASS_EXPLICIT_LEGACY_RNG_REPLAY",
      "import_manifest_sha": "6efb88a756bc12558f2e7bdbba72854f8fb37aca6bfd73a30b20509d9b93983b",
      "integer_counts": "EXACT_AT_ALL_THREE_BUDGETS",
      "method_difference": "EXPLICIT_AND_RESOLVED_NOT_IDENTICAL_RNG",
      "new_model_inference": false,
      "operational_thresholds_used": false,
      "phase11_13_hash_checks": 33,
      "population_count": 1135,
      "pre_R0_machinery_commit": "9982b9bd2c5f8da7fc63a1b7977c1cccf91cfb70",
      "production_rng": "NUMPY_PCG64_UNCHANGED",
      "ranking_tolerance": 1e-12,
      "report_version": "r0_reproduction_report_v1",
      "source_hash_checks": 123,
      "status": "PASS"
    },
    "initial_combined_run": {
      "accepted": false,
      "diagnosis": "semantic_oof_acceptance imports semantic_oof, which imports torch at collection; common_mode asserts torch absent from global sys.modules",
      "failing_test": "test_common_mode.py::test_analyze_order_grouped_and_no_model_imports",
      "failures": 1,
      "passed": 782,
      "receipt_sha": "1739ac4b794d92a66fc6482d451ee809bd38611c1852c273acf8e396c863c1c8",
      "resolution": "Separate fresh pytest processes for model-free suites and remaining suites; no existing tests changed or skipped",
      "tests": 783
    },
    "lock_bindings": 101,
    "network_activity": "NONE",
    "operational_R0": {
      "byte_identical": true,
      "hash_checks": 8,
      "status": "PASS"
    },
    "pending_validation_code_sha": {
      "detection_service/research_protocol/release_validation.py": "10220e31dde654ec1278cd3f9a01c72c206c41068833df275a02ad178238e83d",
      "detection_service/tests/test_protocol_release_audit.py": "84cff9302378f7c052f8304d2be3d1d8aa2bf22fe57c49a8bfc84a90658bfac0"
    },
    "preflights": {
      "r1": {
        "experiment_executed": false,
        "experiment_id": "EXP-R1-bca51d745bc791a55a6ec54f66732a865e4c0daef51ee6c7990bd465649f693c",
        "operating_policy_sha": "06fa4548a62ae0e0968f9d93339910f8841a0f366b5346b0892a2be6904fb0cc",
        "protocol_lock_sha": "d0e1f38898b4f82c93daaa6425f4ddb3592fe080fe50db6ef36f2be9dbed2353",
        "purpose": "TEST_FIXTURE",
        "status": "PASS"
      },
      "r2_dg": {
        "experiment_executed": false,
        "experiment_id": "EXP-R2-2e63b3e39821dad3e6b5f73269d4dd6e5d50470f24149ca715604924698ee0dc",
        "operating_policy_sha": "06fa4548a62ae0e0968f9d93339910f8841a0f366b5346b0892a2be6904fb0cc",
        "protocol_lock_sha": "d0e1f38898b4f82c93daaa6425f4ddb3592fe080fe50db6ef36f2be9dbed2353",
        "purpose": "TEST_FIXTURE",
        "status": "PASS"
      },
      "r2_dmb": {
        "experiment_executed": false,
        "experiment_id": "EXP-R2-87eaa4f59916cc5452d2829818052691a437ca85a985c885eb7c28902323914a",
        "operating_policy_sha": "06fa4548a62ae0e0968f9d93339910f8841a0f366b5346b0892a2be6904fb0cc",
        "protocol_lock_sha": "d0e1f38898b4f82c93daaa6425f4ddb3592fe080fe50db6ef36f2be9dbed2353",
        "purpose": "TEST_FIXTURE",
        "status": "PASS"
      },
      "r2_ds": {
        "experiment_executed": false,
        "experiment_id": "EXP-R2-0c9ca2a2dc30b7ab4fd5b84a4e7d3da79919bf2302d2c5f92b53d39db6001ed4",
        "operating_policy_sha": "06fa4548a62ae0e0968f9d93339910f8841a0f366b5346b0892a2be6904fb0cc",
        "protocol_lock_sha": "d0e1f38898b4f82c93daaa6425f4ddb3592fe080fe50db6ef36f2be9dbed2353",
        "purpose": "TEST_FIXTURE",
        "status": "PASS"
      },
      "r3": {
        "experiment_executed": false,
        "experiment_id": "EXP-R3-ae6c9d9108f617d1c17ed89a4102e9f07cffd9f4d0b4d13f3ceefb2298c10f51",
        "operating_policy_sha": "06fa4548a62ae0e0968f9d93339910f8841a0f366b5346b0892a2be6904fb0cc",
        "protocol_lock_sha": "d0e1f38898b4f82c93daaa6425f4ddb3592fe080fe50db6ef36f2be9dbed2353",
        "purpose": "TEST_FIXTURE",
        "status": "PASS"
      }
    },
    "release_inventory": {
      "byte_identical": true,
      "hash_checks": 109,
      "status": "PASS",
      "unique_authoritative_roles": 11
    },
    "source_commit": "773853e6cf39130708e9780d84d6bd9173a1613c",
    "status": "PASS",
    "tamper": {
      "cases": [
        {
          "case": "D_S_threshold",
          "reason": "AUTHORITATIVE_ARTIFACT_DRIFT",
          "status": "REJECTED"
        },
        {
          "case": "D_M-B_threshold",
          "reason": "AUTHORITATIVE_ARTIFACT_DRIFT",
          "status": "REJECTED"
        },
        {
          "case": "D_G_threshold",
          "reason": "AUTHORITATIVE_ARTIFACT_DRIFT",
          "status": "REJECTED"
        },
        {
          "case": "threshold_id",
          "reason": "AUTHORITATIVE_ARTIFACT_DRIFT",
          "status": "REJECTED"
        },
        {
          "case": "detector_order",
          "reason": "AUTHORITATIVE_ARTIFACT_DRIFT",
          "status": "REJECTED"
        },
        {
          "case": "score_direction",
          "reason": "AUTHORITATIVE_ARTIFACT_DRIFT",
          "status": "REJECTED"
        },
        {
          "case": "operating_hash",
          "reason": "AUTHORITATIVE_ARTIFACT_DRIFT",
          "status": "REJECTED"
        },
        {
          "case": "core_contract",
          "reason": "AUTHORITATIVE_ARTIFACT_DRIFT",
          "status": "REJECTED"
        },
        {
          "case": "uncertainty_contract",
          "reason": "AUTHORITATIVE_ARTIFACT_DRIFT",
          "status": "REJECTED"
        },
        {
          "case": "cross_regime_contract",
          "reason": "AUTHORITATIVE_ARTIFACT_DRIFT",
          "status": "REJECTED"
        },
        {
          "case": "prediction_schema",
          "reason": "AUTHORITATIVE_ARTIFACT_DRIFT",
          "status": "REJECTED"
        },
        {
          "case": "regime_contract",
          "reason": "AUTHORITATIVE_ARTIFACT_DRIFT",
          "status": "REJECTED"
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
      "real_artifacts_modified": false,
      "rejected": 16,
      "status": "PASS"
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
    "tests": {
      "case_ids_sha": "38c8b4008df3de9eac93608189990cded026eac18497edc1026d3f3bab8cd1c4",
      "errors": 0,
      "failures": 0,
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
      ],
      "passed": 788,
      "receipts": [
        {
          "errors": 0,
          "failures": 0,
          "path": "tmp\\protocol_final_model_free.xml",
          "seconds": 1.028,
          "sha256": "e27977fd78e4128767ac76003035e89aeb18fd28a0182f10532269a4687947d5",
          "skipped": 0,
          "tests": 84
        },
        {
          "errors": 0,
          "failures": 0,
          "path": "tmp\\protocol_final_remaining.xml",
          "seconds": 739.418,
          "sha256": "4fbea325b884223172d6da320d114025ba9c5bb86c26f124644c33b946cf97f1",
          "skipped": 0,
          "tests": 704
        }
      ],
      "seconds": 740.446,
      "skipped": 0,
      "tests": 788
    }
  }
}
```

## Release Hashes

- protocol_lock_sha: d0e1f38898b4f82c93daaa6425f4ddb3592fe080fe50db6ef36f2be9dbed2353
- release_inventory_sha: b04002287dfc22f5dc933f9270a5511de03b4f7877c90a72e93025ca0d75cf22
- release_manifest_sha: c6a6678c7c95a870812cb8d4ea4d7a547faec6465ea7b5a85d0f38914ac4a58f
- final_validation_evidence_sha: 875c1b4f7b2128aa44d154d7bdfcfce93900422f4da78a14f6afd549107862c7
- Final release artifact: 62f1826330a66ef036bdf182a90888e3acfbf9181d6bdca3239b2914959b6325

The final inventory binds this report and the final release; its own file SHA is reported externally to avoid recursive hashing.

## Self-Rejection Audit

PASS: unique authoritative roles; single policy/threshold source; exact score/calibrator identities; D_M-A comparator-only; no auto-fit/override route in official API; strict status/coverage and target/lineage validation; correct ETR denominators; operational/descriptive separation; explicit NOT_RUN; preserved historical evidence; two byte-identical reconstructions; hash-bound release references; nonrecursive self-hashes; no raw prompts/weights/future/protected data in release. Git cleanliness/synchronization is the final handoff gate.

R1 HAS NOT STARTED

NO FUTURE REGIME DATA WAS USED TO MODIFY THE PROTOCOL

EXP-PROTOCOL-001 IS FROZEN BEFORE R1.

R2/R3 NOT_STARTED; Cycle 2 DEFERRED; protected/final and verifier experiments NOT_STARTED.

The pre-existing D_S live adapter remains unavailable; future scoring must resolve that execution prerequisite under separate authorization, without silently substituting runtime or changing the frozen recipe. This release freezes evaluation semantics and evidence, not a claim that live R1 scoring has already succeeded.

## FINAL VERDICT

EXP_PROTOCOL_001_COMPLETE_READY_FOR_R1

THE SINGLE MOST IMPORTANT FINAL GUARANTEE:

The protocol is frozen before unseen-regime evidence, with immutable operational policy and fail-closed provenance/metric/lineage checks.

NEXT AUTHORIZED RESEARCH STEP: R1_SHIFTED_UNSEEN. Do not begin R1 in this closeout.
