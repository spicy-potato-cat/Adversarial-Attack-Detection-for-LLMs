"""Pre-result QUALITY-001 policy and schemas, without model execution."""

FIXTURE_VERSION = "quality_001_development_folds_v1"
SEED = 1701
N_FOLDS = 5
MANIFEST_PATH = "data_governance/manifests/development_partition_manifest_v1.csv"
MANIFEST_SHA256 = "9cdd5ecdd80f9ac3c8f05db63742721f4537ca2b64a2fe48f6c2b424b57483a6"
ARTIFACT_DIR = "artifacts/quality/quality_001"
FOLD_PATH = ARTIFACT_DIR + "/development_folds_v1.csv"
BASELINE_VERSIONS = {"D_S": "ds_v1", "D_M-A": "dm_a_v1", "D_M-B": "dm_b_v1", "D_G": "dg_v1"}
CANDIDATE_VERSIONS = {"D_S": "ds_v2", "D_M-B": "dm_b_v2"}
PARTITIONS = {
    "BASE_TRAIN": "Development engineering and fixed lineage-aware CV; not unbiased final testing.",
    "CALIBRATION": "Separate calibration fitting only when later explicitly authorized; excluded from CV engineering.",
    "VALIDATION": "Later authorized candidate promotion/calibration-threshold-policy gate; not model engineering.",
    "INTERNAL_TEST": "Internal research measurement; must not influence detector tuning.",
    "FROZEN_EXTERNAL": "Final untouched external system evaluation; conceptual alias of FINAL_TEST.",
    "FINAL_TEST": "Final untouched system evaluation with confidence intervals.",
}
THREAT_REGIMES = {
    "R0": "Standard / non-adaptive attacks",
    "R1": "Unseen / distribution-shifted attacks",
    "R2": "Single-detector adaptive attacks",
    "R3": "Ensemble-aware adaptive attacks",
}
SELECTION_METRICS = ["Recall@FPR<=0.01", "Recall@FPR<=0.03", "Recall@FPR<=0.05"]


def fixture_config(fold_sha256, lineage_evidence):
    return {
        "fixture_version": FIXTURE_VERSION,
        "manifest_path": MANIFEST_PATH,
        "manifest_sha256": MANIFEST_SHA256,
        "expected_counts": {"TOTAL": 1601, "BASE_TRAIN": 1135, "CALIBRATION": 233, "VALIDATION": 233,
                            "BASE_TRAIN_positive": 183, "BASE_TRAIN_negative": 952},
        "seed": SEED,
        "n_folds": N_FOLDS,
        "fold_ids": [0, 1, 2, 3, 4],
        "fold_artifact_path": FOLD_PATH,
        "fold_artifact_sha256": fold_sha256,
        "assignment_method": "quality_001_group_greedy_v1",
        "assignment_priority": ["lineage_isolation", "label_balance", "source_balance", "row_balance", "sha256_tie_break"],
        "construction_runs": 1,
        "fixture_role": "DEVELOPMENT_ONLY_NOT_UNBIASED_TEST",
        "lineage": {
            "field": "lineage_group_id",
            "rule": "LG-N1-<first_24_hex_chars_of_normalized_text_sha256>",
            "evidence": lineage_evidence,
            "scope": "Approved exact canonical duplicate lineage minimum only; not full documentary/semantic lineage.",
            "residual_risk": "Near-duplicate/template/semantic and upstream lineage remain unresolved; no independence claim.",
        },
        "quality_objective": "min FNR_system subject to FPR_system <= alpha",
        "fpr_budgets": [0.01, 0.03, 0.05],
        "final_operating_point": "NOT_SELECTED",
        "max_improvement_cycles": 2,
        "cycle_policy": {
            "scope": ["D_S", "D_M-B"],
            "counts_as_cycle": "Meaningful feature/model redesign followed by development evaluation",
            "not_cycles": ["bug_fix", "deterministic_reproduction_fix", "serialization_fix"],
            "stop": "After two substantive unsuccessful cycles, stop tuning and report limitations.",
        },
        "dm_b_primary_selection_metrics": SELECTION_METRICS,
        "dm_b_promotion_policy": {
            "primary": "Improve recall at one or more fixed FPR budgets, not arbitrary cutpoint 0.5 dominance.",
            "nondegradation_gates": ["PR-AUC", "ROC-AUC", "cross_fold_stability", "latency_compute_practicality", "complementary_error_behavior"],
            "materiality_and_compute_limits": "Must be preregistered in later candidate authorization before candidate results; not invented here.",
            "requires_paired_evidence": True,
            "single_point_estimate_sufficient": False,
        },
        "ds_primary_selection_metrics": SELECTION_METRICS,
        "ds_promotion_policy": {
            "standalone_FNR_sufficient": False,
            "statistical_only": True,
            "prohibited_features": ["semantic_transformer_embeddings", "D_M_logits", "D_G_scores", "LLM_judge_scores", "semantic_classifier_outputs"],
            "complementarity_metrics": ["UniqueCatchRate_S", "P(F_S_intersect_F_M)", "P(F_S_intersect_F_G)",
                                        "P(F_S_intersect_F_M_intersect_F_G)", "FN_set_overlap", "FN_set_Jaccard"],
            "F_definition": "Attack false-negative event, on matched permitted samples at recorded operating points.",
            "M_definition": "Exact semantic membership must be frozen during integration; not selected here.",
            "unique_catch_definition": "Fraction of positive samples caught by S and missed by all other specified base detectors; report denominator and counts.",
            "requires_complementary_failure_evidence": True,
        },
        "diversity_rule": "DO NOT OPTIMIZE INDIVIDUAL DETECTORS AT THE EXPENSE OF COMPLEMENTARY FAILURE BEHAVIOR.",
        "calibration_metrics": ["Brier_score", "log_loss"],
        "calibration_policy": {
            "ECE": "Optional only with a consistently preregistered binning procedure",
            "ranking_sanity_checks": ["ROC-AUC", "PR-AUC"],
            "monotonic_mapping_expected_to_improve_ranking": False,
            "discrimination_improvement_requires_evidence": True,
        },
        "comparison_policy": {
            "paired_same_fixture": True,
            "deltas": ["Recall@fixed_FPR", "FPR", "FNR", "ROC-AUC", "PR-AUC"],
            "confidence_intervals": "Paired lineage-group bootstrap where supported; resample identical groups for baseline/candidate.",
            "repeated_significance_testing": "PROHIBITED",
            "fixed_FPR": "Empirical attainable thresholds using whole tied-score blocks, no interpolation/randomized tie splitting; choose maximal recall satisfying budget. Report FP counts, negative denominator, threshold and per-fold variation.",
            "finite_sample_limit": "At small negative counts, 1% budgets are coarse; empirical compliance is not a population guarantee.",
        },
        "confidence_interval_policy": {
            "required_where_feasible": ["FPR", "FNR", "Recall", "system_level_rates", "paired_candidate_deltas"],
            "level": 0.95,
            "method": "Preregister dependence-aware methods later; use lineage-group paired bootstrap where supported; counts/denominators and interval assumptions mandatory.",
            "stretch_target": "1-3% FPR/FNR is a stretch system-level engineering target to be evaluated on a sufficiently large untouched benchmark with confidence intervals.",
        },
        "partition_definitions": PARTITIONS,
        "threat_regime_definitions": THREAT_REGIMES,
        "partition_not_threat_regime": True,
        "allowed_later_combinations": [[p, r] for p in ("INTERNAL_TEST", "FINAL_TEST") for r in THREAT_REGIMES],
        "baseline_versions": BASELINE_VERSIONS,
        "candidate_versions": CANDIDATE_VERSIONS,
        "generation_definitions": {"research_stack_v1": "Original detector generation", "research_stack_v2": "Improved detector generation"},
        "ensemble_membership": "TO_BE_FROZEN_SEPARATELY_DURING_INTEGRATION",
        "oof_rules": {
            "held_out_fold": "Each BASE_TRAIN sample is held out exactly once and trainable in the other four folds.",
            "fit_scope": "All learned preprocessing/model/calibration must be fold-local using only outer-training rows; inner splits remain lineage-aware.",
            "baseline": "Later authorized OOF baselines require fold-local recipe reproductions; a whole-BASE_TRAIN fitted v1 model cannot yield honest OOF predictions. Original v1 artifacts remain untouched.",
            "external_guard": "Externally frozen guard needs no project-data fitting; any later execution requires authorization.",
            "CALIBRATION_and_VALIDATION": "Excluded from five-fold engineering",
            "engineering_thresholds": "Development choices only; never final operating-point claims",
        },
        "verifier_router_boundary": {
            "sequence": "Verifier recovery before routing optimization",
            "verifier_selection": "P(V_k detects attack | base stack failed)",
            "disagreement_only_detects_all_common_mode_FN": False,
            "future_policies_not_selected": ["A: disagreement/low-margin", "B: A plus coverage/truncation anomalies",
                                             "C: B plus novelty/anomaly triggers", "D: C plus small random benign-consensus audit"],
            "implementation_authorized": False,
        },
        "phase_execution": {k: False for k in ("model_training", "detector_scoring", "CALIBRATION_content", "VALIDATION_content",
                                               "protected_content", "R0_R3_experiments", "E1_E10", "verifier_selection", "routing")},
    }


def _shape(value):
    """Exact preregistered policy shape; only generated hashes may vary."""
    if isinstance(value, dict):
        return {"type": "object", "properties": {k: _shape(v) for k, v in value.items()},
                "required": list(value), "additionalProperties": False}
    return {"const": value}


def config_schema(config):
    schema = _shape(config)
    sha = {"type": "string", "pattern": "^[0-9a-f]{64}$"}
    schema["properties"]["fold_artifact_sha256"] = sha
    for evidence in schema["properties"]["lineage"]["properties"]["evidence"]["const"]:
        if set(evidence) != {"path", "sha256"}:
            raise ValueError("invalid lineage evidence")
    # Policy source hashes are frozen along with the generated fixture.
    return {"$schema": "https://json-schema.org/draft/2020-12/schema", **schema}


def result_schemas():
    string = {"type": "string", "minLength": 1}
    nonnegative = {"type": "number", "minimum": 0}
    nullable_number = {"type": ["number", "null"]}
    nullable_count = {"type": ["integer", "null"], "minimum": 0}
    probability = {"type": ["number", "null"], "minimum": 0, "maximum": 1}
    nullable_bool = {"type": ["boolean", "null"]}
    identity = {
        "sample_id": string, "fold": {"type": "integer", "enum": [0, 1, 2, 3, 4]},
        "label": {"type": "integer", "enum": [0, 1]}, "source_name": string,
        "lineage_group": {"type": "string", "pattern": "^LG-N1-[0-9a-f]{24}$"},
        "detector_id": string, "detector_version": string, "candidate_id": string,
    }
    metadata = {"type": "object", "additionalProperties": False, "properties": {
        "partition": {"const": "BASE_TRAIN"}, "threat_regime": {"enum": [None, *THREAT_REGIMES]},
        "source_revision": string, "calibration_version": {"type": ["string", "null"]},
        "feature_schema_version": string, "operating_point_id": string,
        "raw_score_semantics": string,
    }, "required": ["partition"]}
    props = {**identity, "raw_score": {"type": "number"}, "calibrated_probability": probability,
             "binary_prediction": {"type": "integer", "enum": [0, 1]},
             "input_tokens": nullable_count, "tokens_analyzed": nullable_count,
             "truncated": nullable_bool, "latency_ms": nonnegative,
             "error_type": {"enum": ["TP", "TN", "FP", "FN"]}, "metadata": metadata}
    consistency = []
    for label, prediction, error in ((1, 1, "TP"), (0, 0, "TN"), (0, 1, "FP"), (1, 0, "FN")):
        consistency.append({"if": {"properties": {"label": {"const": label}, "binary_prediction": {"const": prediction}}},
                            "then": {"properties": {"error_type": {"const": error}}}})
    oof = {"$schema": "https://json-schema.org/draft/2020-12/schema", "title": "Development OOF record v1",
           "type": "object", "properties": props, "required": list(props), "additionalProperties": False,
           "allOf": consistency,
           "$comment": "Schema only. Successful scored records; failures require a separate explicit failure log, never invented predictions. Validate sample membership against fixture separately. No raw text."}
    stats = {k: nullable_number for k in ("whole_prompt_ppl", "mean_surprisal", "max_surprisal", "mean_window_ppl",
                                         "max_window_ppl", "std_window_ppl", "high_surprisal_ratio")}
    stats.update({"surprisal_quantiles": {"type": "object", "additionalProperties": False,
                                          "properties": {k: nullable_number for k in ("q25", "q50", "q75", "q90", "q95", "q99")}},
                  "prompt_length_tokens": nullable_count, "anomaly_position_token": nullable_count,
                  "feature_family_tags": {"type": "array", "items": string, "uniqueItems": True}})
    semantic = {"input_tokens": nullable_count, "tokens_analyzed": nullable_count, "truncated": nullable_bool,
                "attack_payload_position_token": nullable_count, "confidence": probability,
                "margin": nullable_number, "attack_family": {"type": ["string", "null"]},
                "payload_position_evidence": {"type": ["string", "null"]}}
    error_props = {**identity, "error_type": {"enum": ["TP", "TN", "FP", "FN"]}, "metadata": metadata,
                   "statistical": {"type": "object", "properties": stats, "additionalProperties": False},
                   "semantic": {"type": "object", "properties": semantic, "additionalProperties": False}}
    error = {"$schema": "https://json-schema.org/draft/2020-12/schema", "title": "Development error-analysis record v1",
             "type": "object", "properties": error_props, "required": [*identity, "error_type", "metadata"],
             "additionalProperties": False,
             "allOf": [{"if": {"properties": {"label": {"const": 0}}},
                        "then": {"properties": {"error_type": {"enum": ["TN", "FP"]}}},
                        "else": {"properties": {"error_type": {"enum": ["TP", "FN"]}}}}],
             "$comment": "Unknown diagnostics remain null/absent. Payload position/attack family require permitted evidence, not analyst-inferred labels. No prompt/response text."}
    return {"oof_result_schema_v1.json": oof, "error_analysis_schema_v1.json": error}
