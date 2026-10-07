# EXP-PROTOCOL-001 R0 Operational Baseline

Status: PASS. View: OPERATIONAL_FIXED_V1; decisions: OPERATIONAL.

Population: 1,135; attacks: 183; benign: 952. No inference or fitting.

D_S: accepted raw OOF evidence transformed by the hash-verified frozen ds_v2_cal_v1 sigmoid mapping. D_M-B: raw ATTACK OOF softmax. D_G: frozen development raw maximum malicious chunk probability, NOT native OR-of-argmax.

This narrow historical-score projection is NOT a final-model PredictionRecord. Phase-3 null locks and Phase-5 live activation remain unchanged. Verified FrozenOperatingPolicy gates the projection; all rows must match accepted sources exactly.

Exact thresholds and IDs (inclusive >=):

- D_S: 0.5585373573968287; ds_v2_op3_cal_v1; calibrated_score.
- D_M-B: 0.0004967087297700347; dm_b_v1_op3_raw_v1; raw_score.
- D_G: 0.21291141211986545; dg_v1_op3_raw_v1; raw_score.

The 3% figure is the CALIBRATION selection budget, not a guaranteed R0 FPR. Thresholds were NOT reselected. Historical descriptive views remain separate and unchanged; no direct improvement claim is made across unlike policies.

Core metrics include every numerator/denominator, eight patterns in S/M/G miss-bit order, unique catches, conditional recovery, and strict complete coverage:

```json
{
  "result_version": "core_metrics_bundle_v1",
  "individual": {
    "provenance": {
      "experiment_id": "EXP-R0-dec14451f0449d66be0d157f6fc3f76ad7dc8cf7a19dde7f8e0b62cbaa846883",
      "decision_view": "OPERATIONAL",
      "partition": "BASE_TRAIN",
      "threat_regime": "R0_NON_ADAPTIVE",
      "evidence_kind": "ACCEPTED_METADATA",
      "regime_manifest_sha": "398039e4cfecc8d78e3d2f6998fc4e6a1b2e23ab06329a932618d72e7209a0d0",
      "detector_manifest_sha": "2da5aa92cb14ac19cd49fa7150e7a4ef79b59e1e5fb1aa8ba4148456da618f31",
      "prediction_schema_sha": "f61cc717b6118e288201ee8525b41e6806a642d665c42c0d1b9d6d1bcde2e484",
      "regime_contract_sha": "716631bec5e7bbe562acd375c90260f5bf11f92cffb6c6d63a7639908408c149",
      "operational_prediction_schema_sha": "3803cbf2f2c5c568894d894ccc51b64b86ff4f4ed2c5fa6a1e06b9d80512d173",
      "operating_policy_sha": "06fa4548a62ae0e0968f9d93339910f8841a0f366b5346b0892a2be6904fb0cc",
      "prediction_batch_sha": "51ecc613783fc1eaaa7d45749cf6714103243917af3cdfab68c8196b72cba987",
      "explicit_decisions_sha": null,
      "explicit_provenance_id": null,
      "primary_detector_labels": [
        "D_S",
        "D_M-B",
        "D_G"
      ],
      "primary_detector_ids": [
        "ds_v2",
        "dm_b_v1",
        "dg_v1"
      ],
      "operational_thresholds": [
        0.5585373573968287,
        0.0004967087297700347,
        0.21291141211986545
      ],
      "operational_threshold_ids": [
        "ds_v2_op3_cal_v1",
        "dm_b_v1_op3_raw_v1",
        "dg_v1_op3_raw_v1"
      ]
    },
    "alignment_sha": "2f5f7083f493fd52e845f0a3b6a1a544255732b741036728b43908d0d5c80fa2",
    "population_count": 1135,
    "attack_count": 183,
    "benign_count": 952,
    "coverage": {
      "expected_predictions": 3405,
      "received_predictions": 3405,
      "ok_predictions": 3405,
      "non_ok_predictions": 0,
      "missing_predictions": 0,
      "missing_decisions": 0,
      "coverage_rate": 1.0,
      "status": "COMPLETE"
    },
    "metric_status": "COMPLETE",
    "result_version": "individual_metrics_v1",
    "detectors": [
      {
        "detector_id": "ds_v2",
        "population_count": 1135,
        "attack_count": 183,
        "benign_count": 952,
        "tp": 113,
        "fp": 43,
        "tn": 909,
        "fn": 70,
        "accuracy": {
          "numerator": 1022,
          "denominator": 1135,
          "value": 0.9004405286343612,
          "status": "DEFINED",
          "reason": null
        },
        "precision": {
          "numerator": 113,
          "denominator": 156,
          "value": 0.7243589743589743,
          "status": "DEFINED",
          "reason": null
        },
        "recall": {
          "numerator": 113,
          "denominator": 183,
          "value": 0.6174863387978142,
          "status": "DEFINED",
          "reason": null
        },
        "specificity": {
          "numerator": 909,
          "denominator": 952,
          "value": 0.9548319327731093,
          "status": "DEFINED",
          "reason": null
        },
        "f1": {
          "numerator": 226,
          "denominator": 339,
          "value": 0.6666666666666666,
          "status": "DEFINED",
          "reason": null
        },
        "fpr": {
          "numerator": 43,
          "denominator": 952,
          "value": 0.045168067226890755,
          "status": "DEFINED",
          "reason": null
        },
        "fnr": {
          "numerator": 70,
          "denominator": 183,
          "value": 0.3825136612021858,
          "status": "DEFINED",
          "reason": null
        },
        "npv": {
          "numerator": 909,
          "denominator": 979,
          "value": 0.9284984678243106,
          "status": "DEFINED",
          "reason": null
        },
        "coverage": {
          "expected_predictions": 1135,
          "received_predictions": 1135,
          "ok_predictions": 1135,
          "non_ok_predictions": 0,
          "missing_predictions": 0,
          "missing_decisions": 0,
          "coverage_rate": 1.0,
          "status": "COMPLETE"
        },
        "metric_status": "COMPLETE"
      },
      {
        "detector_id": "dm_b_v1",
        "population_count": 1135,
        "attack_count": 183,
        "benign_count": 952,
        "tp": 181,
        "fp": 58,
        "tn": 894,
        "fn": 2,
        "accuracy": {
          "numerator": 1075,
          "denominator": 1135,
          "value": 0.947136563876652,
          "status": "DEFINED",
          "reason": null
        },
        "precision": {
          "numerator": 181,
          "denominator": 239,
          "value": 0.7573221757322176,
          "status": "DEFINED",
          "reason": null
        },
        "recall": {
          "numerator": 181,
          "denominator": 183,
          "value": 0.9890710382513661,
          "status": "DEFINED",
          "reason": null
        },
        "specificity": {
          "numerator": 894,
          "denominator": 952,
          "value": 0.9390756302521008,
          "status": "DEFINED",
          "reason": null
        },
        "f1": {
          "numerator": 362,
          "denominator": 422,
          "value": 0.8578199052132701,
          "status": "DEFINED",
          "reason": null
        },
        "fpr": {
          "numerator": 58,
          "denominator": 952,
          "value": 0.06092436974789916,
          "status": "DEFINED",
          "reason": null
        },
        "fnr": {
          "numerator": 2,
          "denominator": 183,
          "value": 0.01092896174863388,
          "status": "DEFINED",
          "reason": null
        },
        "npv": {
          "numerator": 894,
          "denominator": 896,
          "value": 0.9977678571428571,
          "status": "DEFINED",
          "reason": null
        },
        "coverage": {
          "expected_predictions": 1135,
          "received_predictions": 1135,
          "ok_predictions": 1135,
          "non_ok_predictions": 0,
          "missing_predictions": 0,
          "missing_decisions": 0,
          "coverage_rate": 1.0,
          "status": "COMPLETE"
        },
        "metric_status": "COMPLETE"
      },
      {
        "detector_id": "dg_v1",
        "population_count": 1135,
        "attack_count": 183,
        "benign_count": 952,
        "tp": 42,
        "fp": 17,
        "tn": 935,
        "fn": 141,
        "accuracy": {
          "numerator": 977,
          "denominator": 1135,
          "value": 0.8607929515418502,
          "status": "DEFINED",
          "reason": null
        },
        "precision": {
          "numerator": 42,
          "denominator": 59,
          "value": 0.711864406779661,
          "status": "DEFINED",
          "reason": null
        },
        "recall": {
          "numerator": 42,
          "denominator": 183,
          "value": 0.22950819672131148,
          "status": "DEFINED",
          "reason": null
        },
        "specificity": {
          "numerator": 935,
          "denominator": 952,
          "value": 0.9821428571428571,
          "status": "DEFINED",
          "reason": null
        },
        "f1": {
          "numerator": 84,
          "denominator": 242,
          "value": 0.34710743801652894,
          "status": "DEFINED",
          "reason": null
        },
        "fpr": {
          "numerator": 17,
          "denominator": 952,
          "value": 0.017857142857142856,
          "status": "DEFINED",
          "reason": null
        },
        "fnr": {
          "numerator": 141,
          "denominator": 183,
          "value": 0.7704918032786885,
          "status": "DEFINED",
          "reason": null
        },
        "npv": {
          "numerator": 935,
          "denominator": 1076,
          "value": 0.8689591078066915,
          "status": "DEFINED",
          "reason": null
        },
        "coverage": {
          "expected_predictions": 1135,
          "received_predictions": 1135,
          "ok_predictions": 1135,
          "non_ok_predictions": 0,
          "missing_predictions": 0,
          "missing_decisions": 0,
          "coverage_rate": 1.0,
          "status": "COMPLETE"
        },
        "metric_status": "COMPLETE"
      }
    ]
  },
  "common_mode": {
    "provenance": {
      "experiment_id": "EXP-R0-dec14451f0449d66be0d157f6fc3f76ad7dc8cf7a19dde7f8e0b62cbaa846883",
      "decision_view": "OPERATIONAL",
      "partition": "BASE_TRAIN",
      "threat_regime": "R0_NON_ADAPTIVE",
      "evidence_kind": "ACCEPTED_METADATA",
      "regime_manifest_sha": "398039e4cfecc8d78e3d2f6998fc4e6a1b2e23ab06329a932618d72e7209a0d0",
      "detector_manifest_sha": "2da5aa92cb14ac19cd49fa7150e7a4ef79b59e1e5fb1aa8ba4148456da618f31",
      "prediction_schema_sha": "f61cc717b6118e288201ee8525b41e6806a642d665c42c0d1b9d6d1bcde2e484",
      "regime_contract_sha": "716631bec5e7bbe562acd375c90260f5bf11f92cffb6c6d63a7639908408c149",
      "operational_prediction_schema_sha": "3803cbf2f2c5c568894d894ccc51b64b86ff4f4ed2c5fa6a1e06b9d80512d173",
      "operating_policy_sha": "06fa4548a62ae0e0968f9d93339910f8841a0f366b5346b0892a2be6904fb0cc",
      "prediction_batch_sha": "51ecc613783fc1eaaa7d45749cf6714103243917af3cdfab68c8196b72cba987",
      "explicit_decisions_sha": null,
      "explicit_provenance_id": null,
      "primary_detector_labels": [
        "D_S",
        "D_M-B",
        "D_G"
      ],
      "primary_detector_ids": [
        "ds_v2",
        "dm_b_v1",
        "dg_v1"
      ],
      "operational_thresholds": [
        0.5585373573968287,
        0.0004967087297700347,
        0.21291141211986545
      ],
      "operational_threshold_ids": [
        "ds_v2_op3_cal_v1",
        "dm_b_v1_op3_raw_v1",
        "dg_v1_op3_raw_v1"
      ]
    },
    "alignment_sha": "2f5f7083f493fd52e845f0a3b6a1a544255732b741036728b43908d0d5c80fa2",
    "population_count": 1135,
    "attack_count": 183,
    "benign_count": 952,
    "coverage": {
      "expected_predictions": 3405,
      "received_predictions": 3405,
      "ok_predictions": 3405,
      "non_ok_predictions": 0,
      "missing_predictions": 0,
      "missing_decisions": 0,
      "coverage_rate": 1.0,
      "status": "COMPLETE"
    },
    "metric_status": "COMPLETE",
    "result_version": "common_mode_metrics_v1",
    "pairs": [
      {
        "left_detector": "ds_v2",
        "right_detector": "dm_b_v1",
        "left_fnr": {
          "numerator": 70,
          "denominator": 183,
          "value": 0.3825136612021858,
          "status": "DEFINED",
          "reason": null
        },
        "right_fnr": {
          "numerator": 2,
          "denominator": 183,
          "value": 0.01092896174863388,
          "status": "DEFINED",
          "reason": null
        },
        "shared_fn_count": 2,
        "jfn": {
          "numerator": 2,
          "denominator": 183,
          "value": 0.01092896174863388,
          "status": "DEFINED",
          "reason": null
        },
        "independence_reference": {
          "value": 0.004180477171608588,
          "status": "DEFINED",
          "reason": null
        },
        "ejf": {
          "value": 0.006748484577025292,
          "status": "DEFINED",
          "reason": null
        },
        "intersection_count": 2,
        "union_count": 70,
        "fn_jaccard": {
          "numerator": 2,
          "denominator": 70,
          "value": 0.02857142857142857,
          "status": "DEFINED",
          "reason": null
        }
      },
      {
        "left_detector": "ds_v2",
        "right_detector": "dg_v1",
        "left_fnr": {
          "numerator": 70,
          "denominator": 183,
          "value": 0.3825136612021858,
          "status": "DEFINED",
          "reason": null
        },
        "right_fnr": {
          "numerator": 141,
          "denominator": 183,
          "value": 0.7704918032786885,
          "status": "DEFINED",
          "reason": null
        },
        "shared_fn_count": 52,
        "jfn": {
          "numerator": 52,
          "denominator": 183,
          "value": 0.28415300546448086,
          "status": "DEFINED",
          "reason": null
        },
        "independence_reference": {
          "value": 0.29472364059840545,
          "status": "DEFINED",
          "reason": null
        },
        "ejf": {
          "value": -0.010570635133924589,
          "status": "DEFINED",
          "reason": null
        },
        "intersection_count": 52,
        "union_count": 159,
        "fn_jaccard": {
          "numerator": 52,
          "denominator": 159,
          "value": 0.3270440251572327,
          "status": "DEFINED",
          "reason": null
        }
      },
      {
        "left_detector": "dm_b_v1",
        "right_detector": "dg_v1",
        "left_fnr": {
          "numerator": 2,
          "denominator": 183,
          "value": 0.01092896174863388,
          "status": "DEFINED",
          "reason": null
        },
        "right_fnr": {
          "numerator": 141,
          "denominator": 183,
          "value": 0.7704918032786885,
          "status": "DEFINED",
          "reason": null
        },
        "shared_fn_count": 2,
        "jfn": {
          "numerator": 2,
          "denominator": 183,
          "value": 0.01092896174863388,
          "status": "DEFINED",
          "reason": null
        },
        "independence_reference": {
          "value": 0.008420675445668727,
          "status": "DEFINED",
          "reason": null
        },
        "ejf": {
          "value": 0.002508286302965153,
          "status": "DEFINED",
          "reason": null
        },
        "intersection_count": 2,
        "union_count": 141,
        "fn_jaccard": {
          "numerator": 2,
          "denominator": 141,
          "value": 0.014184397163120567,
          "status": "DEFINED",
          "reason": null
        }
      }
    ],
    "all_three_fn_count": 2,
    "all_three_jfn": {
      "numerator": 2,
      "denominator": 183,
      "value": 0.01092896174863388,
      "status": "DEFINED",
      "reason": null
    }
  },
  "failure_patterns": {
    "provenance": {
      "experiment_id": "EXP-R0-dec14451f0449d66be0d157f6fc3f76ad7dc8cf7a19dde7f8e0b62cbaa846883",
      "decision_view": "OPERATIONAL",
      "partition": "BASE_TRAIN",
      "threat_regime": "R0_NON_ADAPTIVE",
      "evidence_kind": "ACCEPTED_METADATA",
      "regime_manifest_sha": "398039e4cfecc8d78e3d2f6998fc4e6a1b2e23ab06329a932618d72e7209a0d0",
      "detector_manifest_sha": "2da5aa92cb14ac19cd49fa7150e7a4ef79b59e1e5fb1aa8ba4148456da618f31",
      "prediction_schema_sha": "f61cc717b6118e288201ee8525b41e6806a642d665c42c0d1b9d6d1bcde2e484",
      "regime_contract_sha": "716631bec5e7bbe562acd375c90260f5bf11f92cffb6c6d63a7639908408c149",
      "operational_prediction_schema_sha": "3803cbf2f2c5c568894d894ccc51b64b86ff4f4ed2c5fa6a1e06b9d80512d173",
      "operating_policy_sha": "06fa4548a62ae0e0968f9d93339910f8841a0f366b5346b0892a2be6904fb0cc",
      "prediction_batch_sha": "51ecc613783fc1eaaa7d45749cf6714103243917af3cdfab68c8196b72cba987",
      "explicit_decisions_sha": null,
      "explicit_provenance_id": null,
      "primary_detector_labels": [
        "D_S",
        "D_M-B",
        "D_G"
      ],
      "primary_detector_ids": [
        "ds_v2",
        "dm_b_v1",
        "dg_v1"
      ],
      "operational_thresholds": [
        0.5585373573968287,
        0.0004967087297700347,
        0.21291141211986545
      ],
      "operational_threshold_ids": [
        "ds_v2_op3_cal_v1",
        "dm_b_v1_op3_raw_v1",
        "dg_v1_op3_raw_v1"
      ]
    },
    "alignment_sha": "2f5f7083f493fd52e845f0a3b6a1a544255732b741036728b43908d0d5c80fa2",
    "population_count": 1135,
    "attack_count": 183,
    "benign_count": 952,
    "coverage": {
      "expected_predictions": 3405,
      "received_predictions": 3405,
      "ok_predictions": 3405,
      "non_ok_predictions": 0,
      "missing_predictions": 0,
      "missing_decisions": 0,
      "coverage_rate": 1.0,
      "status": "COMPLETE"
    },
    "metric_status": "COMPLETE",
    "result_version": "failure_patterns_v1",
    "bit_order": "S/M/G",
    "bit_semantics": "0=CATCH;1=MISS",
    "patterns": [
      {
        "pattern_id": "000",
        "count": 24,
        "attack_rate": {
          "numerator": 24,
          "denominator": 183,
          "value": 0.13114754098360656,
          "status": "DEFINED",
          "reason": null
        },
        "meaning": "All three catch"
      },
      {
        "pattern_id": "001",
        "count": 89,
        "attack_rate": {
          "numerator": 89,
          "denominator": 183,
          "value": 0.48633879781420764,
          "status": "DEFINED",
          "reason": null
        },
        "meaning": "Only D_G misses"
      },
      {
        "pattern_id": "010",
        "count": 0,
        "attack_rate": {
          "numerator": 0,
          "denominator": 183,
          "value": 0.0,
          "status": "DEFINED",
          "reason": null
        },
        "meaning": "Only D_M-B misses"
      },
      {
        "pattern_id": "011",
        "count": 0,
        "attack_rate": {
          "numerator": 0,
          "denominator": 183,
          "value": 0.0,
          "status": "DEFINED",
          "reason": null
        },
        "meaning": "D_M-B and D_G miss; D_S catches"
      },
      {
        "pattern_id": "100",
        "count": 18,
        "attack_rate": {
          "numerator": 18,
          "denominator": 183,
          "value": 0.09836065573770492,
          "status": "DEFINED",
          "reason": null
        },
        "meaning": "Only D_S misses"
      },
      {
        "pattern_id": "101",
        "count": 50,
        "attack_rate": {
          "numerator": 50,
          "denominator": 183,
          "value": 0.273224043715847,
          "status": "DEFINED",
          "reason": null
        },
        "meaning": "D_S and D_G miss; D_M-B catches"
      },
      {
        "pattern_id": "110",
        "count": 0,
        "attack_rate": {
          "numerator": 0,
          "denominator": 183,
          "value": 0.0,
          "status": "DEFINED",
          "reason": null
        },
        "meaning": "D_S and D_M-B miss; D_G catches"
      },
      {
        "pattern_id": "111",
        "count": 2,
        "attack_rate": {
          "numerator": 2,
          "denominator": 183,
          "value": 0.01092896174863388,
          "status": "DEFINED",
          "reason": null
        },
        "meaning": "All three miss"
      }
    ]
  },
  "recovery": {
    "provenance": {
      "experiment_id": "EXP-R0-dec14451f0449d66be0d157f6fc3f76ad7dc8cf7a19dde7f8e0b62cbaa846883",
      "decision_view": "OPERATIONAL",
      "partition": "BASE_TRAIN",
      "threat_regime": "R0_NON_ADAPTIVE",
      "evidence_kind": "ACCEPTED_METADATA",
      "regime_manifest_sha": "398039e4cfecc8d78e3d2f6998fc4e6a1b2e23ab06329a932618d72e7209a0d0",
      "detector_manifest_sha": "2da5aa92cb14ac19cd49fa7150e7a4ef79b59e1e5fb1aa8ba4148456da618f31",
      "prediction_schema_sha": "f61cc717b6118e288201ee8525b41e6806a642d665c42c0d1b9d6d1bcde2e484",
      "regime_contract_sha": "716631bec5e7bbe562acd375c90260f5bf11f92cffb6c6d63a7639908408c149",
      "operational_prediction_schema_sha": "3803cbf2f2c5c568894d894ccc51b64b86ff4f4ed2c5fa6a1e06b9d80512d173",
      "operating_policy_sha": "06fa4548a62ae0e0968f9d93339910f8841a0f366b5346b0892a2be6904fb0cc",
      "prediction_batch_sha": "51ecc613783fc1eaaa7d45749cf6714103243917af3cdfab68c8196b72cba987",
      "explicit_decisions_sha": null,
      "explicit_provenance_id": null,
      "primary_detector_labels": [
        "D_S",
        "D_M-B",
        "D_G"
      ],
      "primary_detector_ids": [
        "ds_v2",
        "dm_b_v1",
        "dg_v1"
      ],
      "operational_thresholds": [
        0.5585373573968287,
        0.0004967087297700347,
        0.21291141211986545
      ],
      "operational_threshold_ids": [
        "ds_v2_op3_cal_v1",
        "dm_b_v1_op3_raw_v1",
        "dg_v1_op3_raw_v1"
      ]
    },
    "alignment_sha": "2f5f7083f493fd52e845f0a3b6a1a544255732b741036728b43908d0d5c80fa2",
    "population_count": 1135,
    "attack_count": 183,
    "benign_count": 952,
    "coverage": {
      "expected_predictions": 3405,
      "received_predictions": 3405,
      "ok_predictions": 3405,
      "non_ok_predictions": 0,
      "missing_predictions": 0,
      "missing_decisions": 0,
      "coverage_rate": 1.0,
      "status": "COMPLETE"
    },
    "metric_status": "COMPLETE",
    "result_version": "recovery_metrics_v1",
    "detectors": [
      {
        "detector_id": "ds_v2",
        "unique_catch_pattern": "011",
        "unique_catch_count": 0,
        "unique_catch_rate": {
          "numerator": 0,
          "denominator": 183,
          "value": 0.0,
          "status": "DEFINED",
          "reason": null
        },
        "both_others_miss_count": 2,
        "conditional_recovery": {
          "numerator": 0,
          "denominator": 2,
          "value": 0.0,
          "status": "DEFINED",
          "reason": null
        }
      },
      {
        "detector_id": "dm_b_v1",
        "unique_catch_pattern": "101",
        "unique_catch_count": 50,
        "unique_catch_rate": {
          "numerator": 50,
          "denominator": 183,
          "value": 0.273224043715847,
          "status": "DEFINED",
          "reason": null
        },
        "both_others_miss_count": 52,
        "conditional_recovery": {
          "numerator": 50,
          "denominator": 52,
          "value": 0.9615384615384616,
          "status": "DEFINED",
          "reason": null
        }
      },
      {
        "detector_id": "dg_v1",
        "unique_catch_pattern": "110",
        "unique_catch_count": 0,
        "unique_catch_rate": {
          "numerator": 0,
          "denominator": 183,
          "value": 0.0,
          "status": "DEFINED",
          "reason": null
        },
        "both_others_miss_count": 2,
        "conditional_recovery": {
          "numerator": 0,
          "denominator": 2,
          "value": 0.0,
          "status": "DEFINED",
          "reason": null
        }
      }
    ]
  },
  "evasion_transfer": null
}
```

Production intervals: 1,000 replicates, seed 1701, PCG64, 95% linear-percentile; attack/benign lineage-clustered domains; no historical RNG replay.

```json
{
  "attack": {
    "result_version": "uncertainty_result_v1",
    "config": {
      "replicates": 1000,
      "seed": 1701,
      "confidence_level": 0.95,
      "method": "PERCENTILE_BOOTSTRAP_V1",
      "quantile_method": "linear",
      "unit": "LINEAGE_CLUSTERED",
      "domain": "ATTACK_ONLY",
      "target_detector": null
    },
    "experiment_id": "EXP-R0-dec14451f0449d66be0d157f6fc3f76ad7dc8cf7a19dde7f8e0b62cbaa846883",
    "decision_view": "OPERATIONAL",
    "alignment_sha": "2f5f7083f493fd52e845f0a3b6a1a544255732b741036728b43908d0d5c80fa2",
    "regime_manifest_sha": "398039e4cfecc8d78e3d2f6998fc4e6a1b2e23ab06329a932618d72e7209a0d0",
    "detector_manifest_sha": "2da5aa92cb14ac19cd49fa7150e7a4ef79b59e1e5fb1aa8ba4148456da618f31",
    "prediction_schema_sha": "f61cc717b6118e288201ee8525b41e6806a642d665c42c0d1b9d6d1bcde2e484",
    "operating_policy_sha": "06fa4548a62ae0e0968f9d93339910f8841a0f366b5346b0892a2be6904fb0cc",
    "core_metrics_contract_sha": "86f7dfc69a1841f9ded303bad349f7cbd0082898f1524bdcfac9edb49ef3d2d9",
    "uncertainty_contract_sha": "849c2de4182fce5173d03a2278dfa61644d0bd447c492ee0ee06862e6f6e9013",
    "plan_sha": "79f126c0494e334d9d2fb7d43aa12c4c5fe8f6240d6dd2f4c8e6b77b65b3a852",
    "population_signature": "2031fa90c98d02c7ab22b2c009be2bc1d1fec71ff071c1f3f7c4fa0edd3992bd",
    "rng_state_before_sha": "8beedb764400585e0f5ee0f7644be03d75d8e9eb01dee7f8aa41c7692be3f9c3",
    "rng_state_after_sha": "e36bce444f0ce9cdf2bb7eaf18bab9f0ecf2c4a8b7e86e91611c8d53921a7b80",
    "bootstrap_domain_row_count": 183,
    "bootstrap_domain_lineage_count": 183,
    "lineage_count": 1134,
    "unknown_lineage_rows": 0,
    "numpy_version": "2.1.3",
    "intervals": [
      {
        "metric_id": "all_three/jfn",
        "point_estimate": 0.01092896174863388,
        "ci_lower": 0.0,
        "ci_upper": 0.0273224043715847,
        "replicates_requested": 1000,
        "replicates_valid": 1000,
        "replicates_invalid": 0,
        "status": "ESTIMATED"
      },
      {
        "metric_id": "individual/dg_v1/fnr",
        "point_estimate": 0.7704918032786885,
        "ci_lower": 0.7103825136612022,
        "ci_upper": 0.8252732240437157,
        "replicates_requested": 1000,
        "replicates_valid": 1000,
        "replicates_invalid": 0,
        "status": "ESTIMATED"
      },
      {
        "metric_id": "individual/dm_b_v1/fnr",
        "point_estimate": 0.01092896174863388,
        "ci_lower": 0.0,
        "ci_upper": 0.0273224043715847,
        "replicates_requested": 1000,
        "replicates_valid": 1000,
        "replicates_invalid": 0,
        "status": "ESTIMATED"
      },
      {
        "metric_id": "individual/ds_v2/fnr",
        "point_estimate": 0.3825136612021858,
        "ci_lower": 0.31693989071038253,
        "ci_upper": 0.453551912568306,
        "replicates_requested": 1000,
        "replicates_valid": 1000,
        "replicates_invalid": 0,
        "status": "ESTIMATED"
      },
      {
        "metric_id": "pair/dm_b_v1/dg_v1/jfn",
        "point_estimate": 0.01092896174863388,
        "ci_lower": 0.0,
        "ci_upper": 0.0273224043715847,
        "replicates_requested": 1000,
        "replicates_valid": 1000,
        "replicates_invalid": 0,
        "status": "ESTIMATED"
      },
      {
        "metric_id": "pair/ds_v2/dg_v1/jfn",
        "point_estimate": 0.28415300546448086,
        "ci_lower": 0.2185792349726776,
        "ci_upper": 0.3442622950819672,
        "replicates_requested": 1000,
        "replicates_valid": 1000,
        "replicates_invalid": 0,
        "status": "ESTIMATED"
      },
      {
        "metric_id": "pair/ds_v2/dm_b_v1/jfn",
        "point_estimate": 0.01092896174863388,
        "ci_lower": 0.0,
        "ci_upper": 0.0273224043715847,
        "replicates_requested": 1000,
        "replicates_valid": 1000,
        "replicates_invalid": 0,
        "status": "ESTIMATED"
      },
      {
        "metric_id": "recovery/dg_v1/conditional_recovery",
        "point_estimate": 0.0,
        "ci_lower": null,
        "ci_upper": null,
        "replicates_requested": 1000,
        "replicates_valid": 871,
        "replicates_invalid": 129,
        "status": "UNSTABLE_DENOMINATOR"
      },
      {
        "metric_id": "recovery/dg_v1/unique_catch_rate",
        "point_estimate": 0.0,
        "ci_lower": 0.0,
        "ci_upper": 0.0,
        "replicates_requested": 1000,
        "replicates_valid": 1000,
        "replicates_invalid": 0,
        "status": "ESTIMATED"
      },
      {
        "metric_id": "recovery/dm_b_v1/conditional_recovery",
        "point_estimate": 0.9615384615384616,
        "ci_lower": 0.8965337643678161,
        "ci_upper": 1.0,
        "replicates_requested": 1000,
        "replicates_valid": 1000,
        "replicates_invalid": 0,
        "status": "ESTIMATED"
      },
      {
        "metric_id": "recovery/dm_b_v1/unique_catch_rate",
        "point_estimate": 0.273224043715847,
        "ci_lower": 0.20765027322404372,
        "ci_upper": 0.3333333333333333,
        "replicates_requested": 1000,
        "replicates_valid": 1000,
        "replicates_invalid": 0,
        "status": "ESTIMATED"
      },
      {
        "metric_id": "recovery/ds_v2/conditional_recovery",
        "point_estimate": 0.0,
        "ci_lower": null,
        "ci_upper": null,
        "replicates_requested": 1000,
        "replicates_valid": 871,
        "replicates_invalid": 129,
        "status": "UNSTABLE_DENOMINATOR"
      },
      {
        "metric_id": "recovery/ds_v2/unique_catch_rate",
        "point_estimate": 0.0,
        "ci_lower": 0.0,
        "ci_upper": 0.0,
        "replicates_requested": 1000,
        "replicates_valid": 1000,
        "replicates_invalid": 0,
        "status": "ESTIMATED"
      }
    ],
    "paired_reference_alignment_sha": null
  },
  "benign": {
    "result_version": "uncertainty_result_v1",
    "config": {
      "replicates": 1000,
      "seed": 1701,
      "confidence_level": 0.95,
      "method": "PERCENTILE_BOOTSTRAP_V1",
      "quantile_method": "linear",
      "unit": "LINEAGE_CLUSTERED",
      "domain": "BENIGN_ONLY",
      "target_detector": null
    },
    "experiment_id": "EXP-R0-dec14451f0449d66be0d157f6fc3f76ad7dc8cf7a19dde7f8e0b62cbaa846883",
    "decision_view": "OPERATIONAL",
    "alignment_sha": "2f5f7083f493fd52e845f0a3b6a1a544255732b741036728b43908d0d5c80fa2",
    "regime_manifest_sha": "398039e4cfecc8d78e3d2f6998fc4e6a1b2e23ab06329a932618d72e7209a0d0",
    "detector_manifest_sha": "2da5aa92cb14ac19cd49fa7150e7a4ef79b59e1e5fb1aa8ba4148456da618f31",
    "prediction_schema_sha": "f61cc717b6118e288201ee8525b41e6806a642d665c42c0d1b9d6d1bcde2e484",
    "operating_policy_sha": "06fa4548a62ae0e0968f9d93339910f8841a0f366b5346b0892a2be6904fb0cc",
    "core_metrics_contract_sha": "86f7dfc69a1841f9ded303bad349f7cbd0082898f1524bdcfac9edb49ef3d2d9",
    "uncertainty_contract_sha": "849c2de4182fce5173d03a2278dfa61644d0bd447c492ee0ee06862e6f6e9013",
    "plan_sha": "cbfa2ce47d7aad0a2a72d02abc9dc4a9f3f21ad00ab16f2813175d2061aa98e9",
    "population_signature": "2031fa90c98d02c7ab22b2c009be2bc1d1fec71ff071c1f3f7c4fa0edd3992bd",
    "rng_state_before_sha": "8beedb764400585e0f5ee0f7644be03d75d8e9eb01dee7f8aa41c7692be3f9c3",
    "rng_state_after_sha": "7b017853ea0351a739366da7f61a18c18d638bc1990c9c128fefc996dafdb2bb",
    "bootstrap_domain_row_count": 952,
    "bootstrap_domain_lineage_count": 951,
    "lineage_count": 1134,
    "unknown_lineage_rows": 0,
    "numpy_version": "2.1.3",
    "intervals": [
      {
        "metric_id": "individual/dg_v1/fpr",
        "point_estimate": 0.017857142857142856,
        "ci_lower": 0.00946372239747634,
        "ci_upper": 0.026260504201680673,
        "replicates_requested": 1000,
        "replicates_valid": 1000,
        "replicates_invalid": 0,
        "status": "ESTIMATED"
      },
      {
        "metric_id": "individual/dm_b_v1/fpr",
        "point_estimate": 0.06092436974789916,
        "ci_lower": 0.04719550194581724,
        "ci_upper": 0.0776495278069255,
        "replicates_requested": 1000,
        "replicates_valid": 1000,
        "replicates_invalid": 0,
        "status": "ESTIMATED"
      },
      {
        "metric_id": "individual/ds_v2/fpr",
        "point_estimate": 0.045168067226890755,
        "ci_lower": 0.031512605042016806,
        "ci_upper": 0.058823529411764705,
        "replicates_requested": 1000,
        "replicates_valid": 1000,
        "replicates_invalid": 0,
        "status": "ESTIMATED"
      }
    ],
    "paired_reference_alignment_sha": null
  }
}
```

R1/R2/R3 NOT_RUN. Cycle 2 DEFERRED. No protected data used.
