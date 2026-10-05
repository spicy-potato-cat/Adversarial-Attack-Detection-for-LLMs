"""Fold-local D_M-B reproduction and non-causal development diagnostics."""

from collections import Counter
from datetime import UTC, datetime
import hashlib
import math
import time

import numpy as np
import torch

from detection_service.analysis.statistical_oof import (
    BUDGETS, check_membership, curves, describe, digest_ids, error_type,
    metrics as shared_metrics, require, stability, subgroup,
)
from detection_service.scripts.train_semantic_finetuned import (
    deterministic, fit_transformer, upstream,
)
from detection_service.app.detectors.semantic_finetuned.config import FineTunedConfig

REVISION = "fb53ab8802853c8e4fbdbcd0529f21fc6f459b2b"
RECIPE_SHA256 = "2b5b41ce90ff931caf6a6fbddcd2beed19ea802cf657125b996dbdf0c96b0484"
FOLD_SHA256 = "19dc0153cc257cc2331782d6dd61b7bb9fb8cb0ed88d3e782b69d5ba05c4bb8d"
PARAMETERS = 82119938
CUTPOINT = 0.5
BORDERLINE_DISTANCE = 0.1
HIGH_CONFIDENCE = 0.9
LENGTH_BUCKETS = (("2-31", 2, 32), ("32-127", 32, 128), ("128-256", 128, 257),
                  ("257-512", 257, 513), ("513+", 513, None))


def validate_recipe(config):
    config.validate()
    expected = FineTunedConfig(upstream_model="distilbert/distilroberta-base",
                              upstream_revision=REVISION, tokenizer_revision=REVISION,
                              device=config.device)
    require(config.to_dict() == expected.to_dict(), "complete v1 recipe drift")
    require(config.upstream_model == "distilbert/distilroberta-base" and
            config.upstream_revision == config.tokenizer_revision == REVISION, "upstream revision drift")
    require(config.max_sequence_length == 256 and config.model_context_length == 512, "baseline token limit drift")
    require(config.seed == 1701 and config.epochs == 3 and config.batch_size == 8 and
            config.learning_rate == 2e-5 and config.optimizer == "AdamW" and
            config.checkpoint_policy == "final_epoch_only_no_validation_selection", "baseline recipe drift")


def parameter_hash(model):
    digest = hashlib.sha256()
    for name, parameter in model.named_parameters():
        digest.update(name.encode("utf-8"))
        digest.update(parameter.detach().cpu().contiguous().numpy().tobytes())
    return digest.hexdigest()


def initialize(config, preparation):
    tokenizer, model = upstream(config, preparation)
    require(sum(p.numel() for p in model.parameters()) == PARAMETERS, "parameter count drift")
    require(tokenizer.truncation_side == tokenizer.padding_side == "right", "tokenizer direction drift")
    return tokenizer, model, parameter_hash(model)


def predict(tokenizer, model, texts, config):
    """Uncalibrated held-out inference; counts include special tokens, exclude padding."""
    validate_recipe(config)
    result = []
    model.eval()
    with torch.inference_mode():
        for start in range(0, len(texts), config.batch_size):
            batch = texts[start:start + config.batch_size]
            started = time.perf_counter()
            counts = [len(tokenizer.encode(t, add_special_tokens=True, truncation=False, verbose=False)) for t in batch]
            inputs = tokenizer(batch, add_special_tokens=True, padding=True, truncation=True,
                               max_length=256, return_tensors="pt").to(config.device)
            analyzed = inputs["attention_mask"].sum(dim=1).cpu().tolist()
            logits = model(**inputs).logits
            require(logits.shape == (len(batch), 2) and bool(torch.isfinite(logits).all()), "invalid held-out logits")
            scores = torch.softmax(logits, dim=-1)[:, 1].cpu().tolist()
            margins = (logits[:, 1] - logits[:, 0]).cpu().tolist()
            latency = (time.perf_counter() - started) * 1000 / len(batch)
            for count, seen, score, margin in zip(counts, analyzed, scores, margins, strict=True):
                require(seen == min(count, 256), "token coverage disagrees with frozen right truncation")
                result.append({"raw_score": float(score), "logit_margin": float(margin),
                               "input_tokens": count, "tokens_analyzed": int(seen),
                               "tokens_excluded": count - int(seen), "truncated": count > 256,
                               "max_input_tokens": 256, "latency_ms": latency,
                               "payload_position_status": "NOT_AVAILABLE_NOT_INFERRED"})
    return result


def probability_metrics(labels, scores):
    output = shared_metrics(labels, scores)
    output["comparison_rule"] = "raw_softmax_class_1_probability >= 0.5; DATA_INDEPENDENT_DEVELOPMENT_ONLY"
    return output


def confidence(row):
    if abs(row["raw_score"] - CUTPOINT) <= BORDERLINE_DISTANCE + 1e-12:
        return "BORDERLINE_WRONG" if row["error_type"] in ("FN", "FP") else "BORDERLINE_CORRECT"
    if ((row["error_type"] == "FN" and row["raw_score"] <= 1 - HIGH_CONFIDENCE + 1e-12) or
            (row["error_type"] == "FP" and row["raw_score"] >= HIGH_CONFIDENCE)):
        return "HIGH_CONFIDENCE_WRONG"
    return "OTHER_WRONG" if row["error_type"] in ("FN", "FP") else "OTHER_CORRECT"


def validate_predictions(records, rows):
    require(len(records) == len(rows), "OOF row count mismatch")
    require([r["sample_id"] for r in records] == [r["sample_id"] for r in rows], "OOF identity/order mismatch")
    require(len({r["sample_id"] for r in records}) == len(rows), "OOF duplicate identity")
    for record, row in zip(records, rows, strict=True):
        require(record["fold"] == int(row["outer_fold"]) and record["label"] == int(row["label"]) and
                record["source_name"] == row["source_name"] and record["lineage_group"] == row["lineage_group"], "OOF metadata drift")
        score = record["raw_score"]
        require(math.isfinite(score) and 0 <= score <= 1 and math.isfinite(record["logit_margin"]), "invalid raw score/margin")
        require(record["binary_prediction"] == int(score >= CUTPOINT) and
                record["error_type"] == error_type(record["label"], record["binary_prediction"]), "inconsistent prediction")
        count, analyzed = record["input_tokens"], record["tokens_analyzed"]
        require(type(count) is int and count >= 2 and analyzed == min(count, 256) and
                record["tokens_excluded"] == count - analyzed and record["truncated"] == (count > 256), "invalid coverage")
        require(record["calibrated_probability"] is None and record["partition"] == "BASE_TRAIN" and
                record["max_input_tokens"] == 256, "reserved calibration or changed coverage")
        require(record["detector_id"] == "semantic_finetuned" and record["detector_version"] == "dm_b_v1" and
                record["candidate_id"] == "dm_b_v1_recipe_fold_local_baseline", "wrong detector identity")
        require(record["latency_ms"] >= 0 and math.isfinite(record["latency_ms"]), "invalid latency")
        require(record["threshold_distance"] == abs(score - CUTPOINT) and
                record["confidence_category"] == confidence(record), "confidence metadata drift")


def run_folds(rows, texts, config, preparation, *, build=initialize, fit=fit_transformer, score=predict):
    check_membership(rows)
    validate_recipe(config)
    require(len(texts) == len(rows) and all(isinstance(t, str) and t.strip() for t in texts), "invalid selected texts")
    predictions, reports, initial_reference = {}, [], None
    for fold in range(5):
        train = [i for i, r in enumerate(rows) if int(r["outer_fold"]) != fold]
        held = [i for i, r in enumerate(rows) if int(r["outer_fold"]) == fold]
        training, heldout = [rows[i] for i in train], [rows[i] for i in held]
        require(not ({r["sample_id"] for r in training} & {r["sample_id"] for r in heldout}), "identity leakage")
        require(not ({r["lineage_group"] for r in training} & {r["lineage_group"] for r in heldout}), "lineage leakage")
        labels = [int(rows[i]["label"]) for i in train]
        counts = Counter(labels)
        require(set(counts) == {0, 1}, "fold training needs both labels")
        weights = [len(train) / (2 * counts[i]) for i in (0, 1)]
        fold_started_at, fold_started = datetime.now(UTC).isoformat(), time.perf_counter()
        # Reset before constructing both the upstream backbone and random binary head.
        deterministic(config)
        tokenizer, model, initial = build(config, preparation)
        if initial_reference is None:
            initial_reference = initial
        require(initial == initial_reference, "fold initialization is not the same seeded upstream checkpoint")
        started = time.perf_counter()
        history = fit(model, tokenizer, [texts[i] for i in train], labels, config, weights)
        fit_seconds = time.perf_counter() - started
        require(len(history) == 3, "incomplete frozen epochs")
        started = time.perf_counter()
        evidence = score(tokenizer, model, [texts[i] for i in held], config)
        predict_seconds = time.perf_counter() - started
        require(len(evidence) == len(held), "missing held-out scores")
        for index, observation in zip(held, evidence, strict=True):
            row = rows[index]
            sid = row["sample_id"]
            require(sid not in predictions, "duplicate OOF prediction")
            vote = int(observation["raw_score"] >= CUTPOINT)
            record = {**row, **observation, "fold": fold, "label": int(row["label"]),
                      "detector_id": "semantic_finetuned", "detector_version": "dm_b_v1",
                      "candidate_id": "dm_b_v1_recipe_fold_local_baseline", "calibrated_probability": None,
                      "binary_prediction": vote, "error_type": error_type(row["label"], vote),
                      "threshold_distance": abs(observation["raw_score"] - CUTPOINT)}
            record["confidence_category"] = confidence(record)
            predictions[sid] = record
        fold_records = [predictions[r["sample_id"]] for r in heldout]
        reports.append({"fold": fold, "train_rows": len(train), "held_out_rows": len(held),
                        "train_positive": counts[1], "train_negative": counts[0], "class_weights": weights,
                        "train_membership_sha256": digest_ids(training), "held_out_membership_sha256": digest_ids(heldout),
                        "initial_parameters_sha256": initial, "recipe": config.to_dict(),
                        "identity_leakage": 0, "lineage_leakage": 0, "history": history,
                        "started_at": fold_started_at, "completed_at": datetime.now(UTC).isoformat(),
                        "runtime_seconds": time.perf_counter() - fold_started,
                        "fit_seconds": fit_seconds, "predict_seconds": predict_seconds,
                        "metrics": probability_metrics([r["label"] for r in fold_records], [r["raw_score"] for r in fold_records])})
        del model, tokenizer
        if config.device == "cuda":
            torch.cuda.empty_cache()
        print(f"Completed frozen OOF fold {fold + 1}/5", flush=True)
    result = [predictions[r["sample_id"]] for r in rows]
    validate_predictions(result, rows)
    return result, reports


def bucket(tokens):
    for name, low, high in LENGTH_BUCKETS:
        if tokens >= low and (high is None or tokens < high):
            return name
    raise ValueError("invalid token count")


def interval(successes, total):
    if not total:
        return None
    z = 1.959963984540054
    p = successes / total
    denom = 1 + z * z / total
    center = (p + z * z / (2 * total)) / denom
    half = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denom
    return {"lower": max(0., center - half), "upper": min(1., center + half), "level": .95,
            "method": "Wilson descriptive binomial; ignores shared-training/lineage dependence; not a population guarantee"}


def with_intervals(records):
    result = subgroup(records)
    cm = result["confusion_matrix"]
    result["fnr_interval"] = interval(cm["fn"], result["positive"])
    result["fpr_interval"] = interval(cm["fp"], result["negative"])
    return result


def truncation_analysis(records):
    result = {"max_input_tokens": 256, "counts_include_special_tokens": True, "padding_excluded": True,
              "payload_position_status": "NOT_AVAILABLE_NOT_INFERRED", "groups": {},
              "interpretation": "Associations only. No counterfactual intervention; truncation does not prove causality."}
    for truncated in (False, True):
        chosen = [r for r in records if r["truncated"] == truncated]
        key = "truncated" if truncated else "not_truncated"
        result["groups"][key] = {**with_intervals(chosen),
            "positive_score_distribution": describe([r["raw_score"] for r in chosen if r["label"] == 1]),
            "input_tokens": describe([r["input_tokens"] for r in chosen]),
            "tokens_excluded": describe([r["tokens_excluded"] for r in chosen]),
            "joint_FN_incidence_among_all_group_rows": sum(r["error_type"] == "FN" for r in chosen) / len(chosen) if chosen else None}
    positives = [r for r in records if r["label"] == 1]
    result["positive_samples"] = len(positives)
    result["positive_truncated"] = sum(r["truncated"] for r in positives)
    result["positive_truncated_fraction"] = result["positive_truncated"] / len(positives) if positives else None
    result["FNR_denominator"] = "Positive-class rows within each coverage group; joint FN incidence is separately named."
    return result


def characterize(records):
    errors = [r for r in records if r["error_type"] in ("FN", "FP")]
    output = {"scope": "DEVELOPMENT_DIAGNOSTICS_NOT_CAUSAL_OR_GENERAL_DISTRIBUTION_SHIFT",
              "confidence_rules": {"cutpoint": CUTPOINT, "borderline_distance_inclusive": BORDERLINE_DISTANCE,
                                   "confident_wrong_probability": HIGH_CONFIDENCE},
              "confidence": {}, "source_groups": {}, "fold_groups": {}, "length_groups": {}, "patterns": []}
    for error in ("FN", "FP"):
        chosen = [r for r in errors if r["error_type"] == error]
        output["confidence"][error] = {
            "count": len(chosen), "borderline": sum(confidence(r) == "BORDERLINE_WRONG" for r in chosen),
            "high_confidence": sum(confidence(r) == "HIGH_CONFIDENCE_WRONG" for r in chosen),
            "other": sum(confidence(r) == "OTHER_WRONG" for r in chosen),
            "raw_positive_probability": describe([r["raw_score"] for r in chosen]),
            "logit_margin": describe([r["logit_margin"] for r in chosen]),
            "threshold_distance": describe([abs(r["raw_score"] - CUTPOINT) for r in chosen])}
    for key, field in (("source_groups", "source_name"), ("fold_groups", "fold")):
        output[key] = {str(v): with_intervals([r for r in records if r[field] == v]) for v in sorted({r[field] for r in records})}
    output["length_groups"] = {name: with_intervals([r for r in records if bucket(r["input_tokens"]) == name]) for name, _, _ in LENGTH_BUCKETS}
    rules = [("truncation_associated", lambda r: r["truncated"]),
             ("low_margin", lambda r: confidence(r) == "BORDERLINE_WRONG"),
             ("high_confidence_wrong_semantic_hypothesis_not_verified", lambda r: confidence(r) == "HIGH_CONFIDENCE_WRONG"),
             ("short_input_association", lambda r: r["input_tokens"] < 32),
             ("long_input_association", lambda r: r["input_tokens"] > 256)]
    for name, rule in rules:
        output["patterns"].append({"category": name, "error_count": sum(rule(r) for r in errors),
                                   "FN_count": sum(rule(r) for r in errors if r["error_type"] == "FN"),
                                   "FP_count": sum(rule(r) for r in errors if r["error_type"] == "FP"),
                                   "supporting_sample_ids": [r["sample_id"] for r in errors if rule(r)]})
    unresolved = [r["sample_id"] for r in errors if not r["truncated"] and confidence(r) == "OTHER_WRONG"]
    output["unresolved_no_coverage_or_confidence_marker"] = {"count": len(unresolved), "sample_ids": unresolved}
    output["limitations"] = ["Patterns overlap, not mutually exclusive causal assignments.",
        "All semantic root causes remain unresolved without independent mechanism evidence, including confidently wrong errors.",
        "Source label composition is confounded; no general R1 distribution-shift claim.",
        "Exactly one OOF prediction per sample; repeated misses are not measurable.",
        "Uncalibrated softmax confidence is descriptive, not calibrated epistemic certainty."]
    return output


def recommendations(truncation, characterization):
    truncated_fn = truncation["groups"]["truncated"]["confusion_matrix"]["fn"]
    return {"B1": "SUPPORTED_FOR_CONTROLLED_DIAGNOSTIC_EXPERIMENT_NOT_PROMOTION" if truncated_fn else "NOT_SUPPORTED_BY_TRUNCATED_FN_EVIDENCE",
            "reason": f"{truncated_fn} OOF false negatives have excluded tokens. Association does not establish that 512 tokens would correct them.",
            "B2": "DEFER_UNTIL_B1_EVIDENCE_OR_COMMANDER_REVIEW; hard IDs are diagnostic-only, not new training data",
            "B3": "DEFER; stronger encoder is not justified solely by confidently wrong probabilities",
            "high_confidence_FN": characterization["confidence"]["FN"]["high_confidence"],
            "trained_or_promoted_v2": False, "optional_512_forward": "SKIPPED_TO_KEEP_FROZEN_BASELINE_SCOPE"}


def schema_projection(row):
    fields = ("sample_id", "fold", "label", "source_name", "lineage_group", "detector_id", "detector_version",
              "candidate_id", "raw_score", "calibrated_probability", "binary_prediction", "input_tokens",
              "tokens_analyzed", "truncated", "latency_ms", "error_type")
    return {**{name: row[name] for name in fields}, "metadata": {
        "partition": "BASE_TRAIN", "calibration_version": None, "source_revision": row["source_revision"],
        "operating_point_id": "RAW_0_5_FIXED_DATA_INDEPENDENT_DEVELOPMENT_ONLY",
        "raw_score_semantics": "uncalibrated_softmax_class_1_probability"}}
