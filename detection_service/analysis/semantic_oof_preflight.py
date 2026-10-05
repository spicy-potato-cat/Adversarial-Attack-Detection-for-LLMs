"""Metadata-only fold plan, synthetic metric proofs, and frozen output contracts."""

from collections import Counter
from importlib.metadata import version
import sys

from detection_service.analysis.semantic_oof import (
    BUDGETS, check_membership, digest_ids, probability_metrics, require,
)
from detection_service.analysis.statistical_oof import fixed_fpr
from detection_service.scripts.train_semantic_finetuned import packages


PRODUCT_NAMES = (
    "dm_b_v1_recipe_oof_predictions.csv", "dm_b_v1_recipe_oof_metrics.json",
    "dm_b_v1_recipe_fold_metrics.json", "dm_b_v1_recipe_oof_curves.json",
    "dm_b_v1_truncation_analysis.json", "dm_b_v1_error_characterization.json",
    "dm_b_v1_hard_examples.csv", "dm_b_v1_v2_recommendation.json",
)
RUN_METADATA_NAME = "dm_b_v1_oof_run_metadata.json"
RUN_METADATA_FIELDS = (
    "code_commit", "manifest_sha256", "fold_sha256", "upstream_revision", "tokenizer_revision",
    "seed", "device", "python_executable", "packages", "runtime_seconds", "started_at", "completed_at",
    "per_fold_runtime", "output_sha256", "analysis_config_sha256", "oof_preflight_sha256",
)


def environment():
    return {"python_executable": sys.executable, "packages": {
        **packages(), **{name: version(name) for name in ("tokenizers", "scipy", "jsonschema")}}}


def fold_execution_plan(rows):
    check_membership(rows)
    output = {"seed": 1701, "membership_policy": "Existing frozen QUALITY-001 artifact; no assignment regeneration",
              "rows": len(rows), "positive": sum(int(r["label"]) for r in rows), "folds": []}
    held_once = Counter()
    for fold in range(5):
        train = [r for r in rows if int(r["outer_fold"]) != fold]
        held = [r for r in rows if int(r["outer_fold"]) == fold]
        train_ids, held_ids = [r["sample_id"] for r in train], [r["sample_id"] for r in held]
        train_groups, held_groups = {r["lineage_group"] for r in train}, {r["lineage_group"] for r in held}
        overlap = len(set(train_ids) & set(held_ids))
        lineage_overlap = len(train_groups & held_groups)
        require(overlap == lineage_overlap == 0, "fold execution plan leakage")
        held_once.update(held_ids)
        train_positive, held_positive = sum(int(r["label"]) for r in train), sum(int(r["label"]) for r in held)
        require(0 < train_positive < len(train) and 0 < held_positive < len(held), "each planned fold needs both labels")
        output["folds"].append({
            "fold": fold, "train_rows": len(train), "held_out_rows": len(held),
            "train_positive": train_positive, "train_negative": len(train) - train_positive,
            "held_out_positive": held_positive, "held_out_negative": len(held) - held_positive,
            "train_lineage_groups": len(train_groups), "held_out_lineage_groups": len(held_groups),
            "identity_overlap": overlap, "canonical_lineage_overlap": lineage_overlap,
            "training_class_weights": [len(train) / (2 * n) for n in (len(train) - train_positive, train_positive)],
            "train_membership_sha256": digest_ids(train), "held_out_membership_sha256": digest_ids(held),
            "train_sample_ids": train_ids, "held_out_sample_ids": held_ids,
        })
    require(set(held_once) == {r["sample_id"] for r in rows} and set(held_once.values()) == {1}, "planned OOF coverage failure")
    output.update(negative=len(rows) - output["positive"], planned_once_per_sample=True,
                  identity_overlap=0, canonical_lineage_overlap=0,
                  prediction_order="Frozen sample-ID ascending order; not fold execution order")
    return output


def metric_validation():
    # These small, explicit arrays are unrelated to development fixture performance.
    labels, scores = [0, 0, 1, 1], [.1, .8, .2, .9]
    expected = {"confusion_matrix": {"tn": 1, "fp": 1, "fn": 1, "tp": 1},
                "accuracy": .5, "fpr": .5, "fnr": .5, "precision": .5, "recall": .5,
                "specificity": .5, "f1": .5, "roc_auc": .75, "pr_auc": 5 / 6}
    measured = probability_metrics(labels, scores)
    for name, value in expected.items():
        require(measured[name] == value if isinstance(value, dict) else abs(measured[name] - value) < 1e-12,
                f"synthetic metric mismatch: {name}")
    fpr_labels = [0] * 100 + [1] * 4
    fpr_scores = [.98, .97, .96, .95, .93] + [.1] * 95 + [.99, .965, .94, .05]
    points = fixed_fpr(fpr_labels, fpr_scores)
    answers = [{"budget": .01, "recall": .25, "attained_fpr": 0., "tp": 1, "fp": 0},
               {"budget": .03, "recall": .5, "attained_fpr": .02, "tp": 2, "fp": 2},
               {"budget": .05, "recall": .75, "attained_fpr": .04, "tp": 3, "fp": 4}]
    for point, answer in zip(points, answers, strict=True):
        require(all(point[key] == value for key, value in answer.items()), "synthetic fixed-FPR mismatch")
    return {"status": "PASS_SYNTHETIC_ONLY_NOT_PROJECT_PERFORMANCE", "binary_fixture": {
        "labels": labels, "scores": scores, "expected": expected,
        "actual": {name: measured[name] for name in expected},
        "independent_reasoning": "One TP/TN/FP/FN; three of four positive-negative rankings correct. AP=(1+2/3)/2=5/6."},
        "fixed_fpr_fixture": {"labels": fpr_labels, "scores": fpr_scores, "expected": answers, "actual": points,
        "independent_reasoning": "Positive ranks cross 0/2/4/100 negatives. At budgets 1/3/5%, highest attainable TP counts are 1/2/3 of four; ties prefer fewer FP."},
        "pr_auc_definition": "average_precision", "budgets": list(BUDGETS),
        "scope": "Implementation evidence only; no real OOF score or deployment threshold"}


def csv_record_schema(fields):
    integers = {"fold", "label", "binary_prediction", "input_tokens", "max_input_tokens", "tokens_analyzed", "tokens_excluded"}
    numbers = {"raw_score", "logit_margin", "threshold_distance", "latency_ms"}
    properties = {name: {"type": "integer" if name in integers else "number" if name in numbers else "string"} for name in fields}
    properties.update(
        partition={"const": "BASE_TRAIN"}, fold={"enum": list(range(5))}, label={"enum": [0, 1]},
        binary_prediction={"enum": [0, 1]}, truncated={"type": "boolean"}, max_input_tokens={"const": 256},
        calibrated_probability={"type": "null"}, error_type={"enum": ["TP", "TN", "FP", "FN"]},
        raw_score={"type": "number", "minimum": 0, "maximum": 1},
        detector_id={"const": "semantic_finetuned"}, detector_version={"const": "dm_b_v1"},
        payload_position_status={"const": "NOT_AVAILABLE_NOT_INFERRED"})
    return {"$schema": "https://json-schema.org/draft/2020-12/schema", "type": "object",
            "additionalProperties": False, "required": list(fields), "properties": properties}


def output_contract(fields):
    return {"output_root": "artifacts/semantic_v2/oof", "successful_data_outputs": list(PRODUCT_NAMES),
            "run_metadata": RUN_METADATA_NAME, "run_metadata_required_fields": list(RUN_METADATA_FIELDS),
            "completion_marker": "completion_v1.json", "started_marker": "run_started_v1.json",
            "failure_marker_on_exception_only": "failure_v1.json", "raw_text_included": False,
            "csv_fields_order": list(fields), "csv_record_schema": csv_record_schema(fields),
            "original_input_tokens_field": "input_tokens (including special tokens; padding excluded)",
            "hard_examples": "Same CSV schema; only FN/FP IDs/metadata, sample-ID order, not a new training set",
            "hash_policy": "Run metadata hashes eight data products; completion hashes those products plus metadata. No circular self-hash.",
            "results_status": "PENDING AUTHORITATIVE OOF EXECUTION"}
