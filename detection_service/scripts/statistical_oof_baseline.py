"""TECH-STAT-003: prepare/smoke/run/check one fixed BASE_TRAIN-only OOF analysis."""

import argparse
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time
from importlib.metadata import version

import numpy as np

from detection_service.quality.development_fixture import ROOT, file_hash, json_bytes, verify
from detection_service.quality.policy import ARTIFACT_DIR, FOLD_PATH, MANIFEST_PATH
from detection_service.analysis.statistical_oof import (BUCKETS, BUDGETS, COMPARISON_THRESHOLD, check_membership,
    run_folds, metrics, stability, characterize, hypotheses, curves, rate_intervals, oof_schema_projection, require)
from detection_service.app.detectors.statistical_risk.schema import FEATURE_NAMES, FEATURE_SCHEMA, schema_hash, feature_vector
from detection_service.app.detectors.statistical_risk.scorer import RECIPE, verify_hashes

OUTPUT = ROOT / "artifacts/statistical_v2/oof"
MODEL = ROOT / "artifacts/models/ds_v1"
CODE = ("detection_service/analysis/statistical_oof.py", "detection_service/scripts/statistical_oof_baseline.py")
SCHEMA_SHA256 = "2b042f88e7403985e5f94e34bb1107b377069e591322767a482a33b5e2cbf8b7"
DATASET_OPEN_LOG = set()


def write(path, value):
    with Path(path).open("xb") as handle:
        handle.write(json_bytes(value))


def baseline_check():
    result = subprocess.run([sys.executable, "-m", "detection_service.scripts.verify_quality_preservation", "--mode", "check"],
                            cwd=ROOT, capture_output=True, text=True)
    require(result.returncode == 0, "baseline preservation check failed")
    return json.loads(result.stdout)


def environment():
    return {"python": platform.python_version(), "packages": {name: version(name) for name in
            ("scikit-learn", "numpy", "scipy", "torch", "transformers", "tokenizers", "pyarrow", "jsonschema")}}


def prepare():
    require(not OUTPUT.exists(), "OOF directory already exists; inspect rather than overwrite")
    fixture = verify()
    baseline = baseline_check()
    config = json.loads((MODEL / "model_config.json").read_text(encoding="utf-8"))
    require(config["feature_schema_sha256"] == schema_hash() == SCHEMA_SHA256, "feature schema drift")
    require(config["scorer_recipe"] == RECIPE and config["detector_version"] == "ds_v1", "v1 recipe drift")
    source_hashes = json.loads((MODEL / "training_metadata.json").read_text(encoding="utf-8"))["extraction"]["source_artifact_sha256"]
    output = {
        "analysis_id": "TECH-STAT-003", "type": "DEVELOPMENT_BASELINE_AND_ERROR_ANALYSIS_ONLY",
        "manifest_sha256": config["training_manifest_sha256"], "fold_sha256": fixture["fold_sha256"],
        "quality_fixture_sha256": file_hash(ROOT / ARTIFACT_DIR / "quality_fixture_v1.json"),
        "feature_schema_sha256": SCHEMA_SHA256, "feature_names": list(FEATURE_NAMES), "scorer_recipe": RECIPE,
        "seed": 1701, "n_folds": 5, "expected_rows": 1135,
        "comparison_rule": {"raw_probability_cutpoint": COMPARISON_THRESHOLD,
                            "threshold_fitted": False, "held_out_influence": False,
                            "explanation": "Fixed before execution; no threshold data consumed. Only fold-training data fits the LR mapping. Not the calibrated deployed v1 vote."},
        "fixed_fpr_budgets": list(BUDGETS),
        "fixed_fpr_role": "Descriptive attainable ROC points only; no optimized OOF deployment threshold",
        "length_buckets": [{"name": name, "inclusive_min": low, "exclusive_max": high} for name, low, high in BUCKETS],
        "diagnostic_quantiles": [0.25, 0.5, 0.75, 0.9], "bootstrap_repetitions": 2000,
        "feature_extraction": "Fresh unchanged frozen LM features, cached once because no project-label-dependent fitting or normalization exists",
        "extractor_config": config["extractor_config"], "reference_lm": config["reference_lm"],
        "feature_extractor_sha256": config["feature_extractor_sha256"], "source_artifact_sha256": source_hashes,
        "source_scalar_selection": "BASE_TRAIN only, through approved original-container loader. Containers also hold other partitions; no unselected row is supplied to extractor/fits/diagnostics.",
        "calibration_used": False, "validation_used": False, "protected_used": False,
        "final_scorer_loaded": False, "final_calibrator_loaded": False, "new_features": False,
        "ds_v2_created": False, "E1_E10_executed": False,
        "baseline_preservation": baseline, "code_sha256": {path: file_hash(ROOT / path) for path in CODE},
        "start_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "code_provenance": "Git HEAD identifies the repository base; exact new pipeline bytes are bound independently by code_sha256.",
        "environment": environment(),
    }
    OUTPUT.mkdir(parents=True)
    write(OUTPUT / "analysis_config_v1.json", output)
    write(OUTPUT / "preflight_v1.json", {"analysis_config_sha256": file_hash(OUTPUT / "analysis_config_v1.json"),
                                      "fixture": fixture, "baseline": baseline})
    print(json.dumps({"status": "PREPARED", "analysis_config_sha256": file_hash(OUTPUT / "analysis_config_v1.json")}), flush=True)


def checked_config():
    config = json.loads((OUTPUT / "analysis_config_v1.json").read_text(encoding="utf-8"))
    preflight = json.loads((OUTPUT / "preflight_v1.json").read_text(encoding="utf-8"))
    require(file_hash(OUTPUT / "analysis_config_v1.json") == preflight["analysis_config_sha256"], "OOF config drift")
    verify()
    baseline_check()
    verify_hashes(ROOT, config["code_sha256"])
    verify_hashes(ROOT, config["feature_extractor_sha256"])
    require(schema_hash() == config["feature_schema_sha256"] == SCHEMA_SHA256, "feature ordering/schema drift")
    return config


def selected_metadata():
    with (ROOT / FOLD_PATH).open(encoding="utf-8", newline="") as handle:
        folds = list(csv.DictReader(handle))
    check_membership(folds)
    wanted = {r["sample_id"] for r in folds}
    base = {}
    with (ROOT / MANIFEST_PATH).open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row["partition"] == "BASE_TRAIN":
                require(row["record_id"] in wanted, "unassigned BASE_TRAIN source row")
                base[row["record_id"]] = row
    require(set(base) == wanted, "missing BASE_TRAIN metadata")
    return folds, [base[row["sample_id"]] for row in folds]


def install_payload_gate(config):
    allowed = {(ROOT / p).resolve() for p in config["source_artifact_sha256"]}
    dataset = (ROOT / "Dataset").resolve()
    forensic = (ROOT / "PHASE-3").resolve()

    def audit(event, args):
        if event != "open" or not isinstance(args[0], (str, bytes, os.PathLike)):
            return
        path = Path(os.fsdecode(args[0])).resolve()
        if forensic == path or forensic in path.parents:
            raise RuntimeError("TECH-STAT-003 forbids mixed normalized/protected forensic payloads")
        if dataset == path or dataset in path.parents:
            require(path in allowed, "non-approved/protected source payload")
            mode = args[1]
            require(not isinstance(mode, str) or not any(c in mode for c in "wax+"), "raw source writes forbidden")
            DATASET_OPEN_LOG.add(path.relative_to(ROOT).as_posix())

    sys.addaudithook(audit)


def load_base_texts(rows, config):
    require(bool(rows) and all(r["partition"] == "BASE_TRAIN" for r in rows), "CALIBRATION/VALIDATION/protected text selection forbidden")
    verify_hashes(ROOT, config["source_artifact_sha256"])
    from detection_service.app.detectors.semantic_finetuned.data import load_texts
    texts, hashes = load_texts(rows, ROOT, "BASE_TRAIN")
    require(hashes == config["source_artifact_sha256"], "original source hash drift")
    return texts


def extractor(config):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from detection_service.app.detectors.statistical.config import PerplexityConfig
    from detection_service.app.detectors.statistical.perplexity_detector import StatisticalPerplexityDetector
    from detection_service.app.detectors.statistical.perplexity_engine import PerplexityEngine
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    torch.manual_seed(1701)
    torch.set_num_threads(8)
    torch.use_deterministic_algorithms(True)
    reference = ROOT / config["reference_lm"]["snapshot_path"]
    verify_hashes(reference, config["reference_lm"]["file_sha256"])
    tokenizer = AutoTokenizer.from_pretrained(reference, local_files_only=True, use_fast=True, trust_remote_code=False)
    model = AutoModelForCausalLM.from_pretrained(reference, local_files_only=True, use_safetensors=True, trust_remote_code=False)
    model.requires_grad_(False)
    pcfg = PerplexityConfig(**config["extractor_config"])
    return StatisticalPerplexityDetector(pcfg, PerplexityEngine(pcfg, tokenizer, model))


def extract(rows, texts, detector, progress=False):
    from detection_service.app.contracts.detection_request import DetectionRequest, DetectionContent
    matrix, evidence = [], []
    start = time.perf_counter()
    for index, (row, text) in enumerate(zip(rows, texts, strict=True), 1):
        result = detector.detect(DetectionRequest(request_id=row["sample_id"], content=DetectionContent(type="user_prompt", text=text)))
        vector = feature_vector(result)
        coverage = result.input_coverage
        matrix.append(vector)
        evidence.append({"input_tokens": coverage.input_tokens, "tokens_analyzed": coverage.tokens_analyzed,
                         "tokens_excluded": coverage.tokens_excluded, "truncated": coverage.truncated,
                         "inference_chunks": coverage.inference_chunks, "window_count": result.features.window_count,
                         "character_length": result.metadata["character_length"], "extraction_latency_ms": result.latency_ms})
        if progress and (index % 100 == 0 or index == len(rows)):
            print(json.dumps({"extracted": index, "total": len(rows), "elapsed_seconds": round(time.perf_counter() - start, 2)}), flush=True)
    return np.asarray(matrix), evidence


def csv_bytes(records):
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=list(records[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(records)
    return stream.getvalue().encode("utf-8")


def validate_projections(records):
    import jsonschema
    schema = json.loads((ROOT / ARTIFACT_DIR / "oof_result_schema_v1.json").read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema)
    for row in records:
        validator.validate(oof_schema_projection(row))


def run():
    config = checked_config()
    require(not (OUTPUT / "run_started_v1.json").exists(), "OOF execution already started; no automatic repeat/refit")
    install_payload_gate(config)
    write(OUTPUT / "run_started_v1.json", {"scope": "BASE_TRAIN_OOF_ONLY", "code_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()})
    started = time.perf_counter()
    rows, source_rows = selected_metadata()
    texts = load_base_texts(source_rows, config)
    detector = extractor(config)
    matrix, evidence = extract(rows, texts, detector, progress=True)
    del texts
    records, fold_reports = run_folds(rows, matrix, evidence)
    validate_projections(records)
    aggregate = metrics([r["label"] for r in records], [r["raw_score"] for r in records])
    aggregate["confidence_intervals"] = rate_intervals(records, config["bootstrap_repetitions"])
    fold_output = {"folds": fold_reports, "summary": stability(fold_reports)}
    errors = characterize(records)
    gaps = hypotheses(errors)
    output_files = {
        "ds_v1_recipe_oof_predictions.csv": csv_bytes(records),
        "ds_v1_recipe_oof_metrics.json": json_bytes(aggregate),
        "ds_v1_recipe_fold_metrics.json": json_bytes(fold_output),
        "ds_v1_error_characterization.json": json_bytes(errors),
        "ds_v1_feature_gap_hypotheses.json": json_bytes(gaps),
        "ds_v1_recipe_oof_curves.json": json_bytes(curves([r["label"] for r in records], [r["raw_score"] for r in records])),
    }
    for name, value in output_files.items():
        with (OUTPUT / name).open("xb") as handle:
            handle.write(value)
    cache = ROOT / "detection_service/outputs/stat003"
    cache.mkdir(parents=True, exist_ok=True)
    np.save(cache / "base_train_features.npy", matrix)
    preservation = baseline_check()
    verify()
    manifest = {"scope": "DEVELOPMENT_OOF_ONLY", "rows": len(records), "fold_fits": 5,
                "sample_ids_unique": True, "identity_leakage": 0, "canonical_lineage_leakage": 0,
                "CALIBRATION_used": False, "VALIDATION_used": False, "protected_used": False,
                "final_scorer_loaded": False, "final_calibrator_loaded": False, "new_features": False,
                "ds_v2_created": False, "E1_E10": False, "baseline_preservation": preservation,
                "source_scalar_selection": "Only BASE_TRAIN locator text/labels are supplied to extraction, fitting or analysis; original mixed source containers are hashed and read for locating those records.",
                "source_artifact_sha256": config["source_artifact_sha256"], "observed_python_dataset_opens": sorted(DATASET_OPEN_LOG),
                "feature_matrix_sha256": file_hash(cache / "base_train_features.npy"), "feature_schema_sha256": schema_hash(),
                "reproducibility": {"code_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                                    "code_commit_role": "Repository HEAD; code_sha256 binds the exact executed pipeline including local files",
                                    "code_sha256": config["code_sha256"], "environment": environment(),
                                    "manifest_sha256": config["manifest_sha256"], "fold_sha256": config["fold_sha256"],
                                    "quality_fixture_sha256": config["quality_fixture_sha256"], "seed": 1701},
                "runtime_seconds": time.perf_counter() - started,
                "artifact_sha256": {name: file_hash(OUTPUT / name) for name in (*output_files, "analysis_config_v1.json", "preflight_v1.json", "run_started_v1.json")}}
    write(OUTPUT / "completion_v1.json", manifest)
    print(json.dumps({"status": "OOF_COMPLETE", "runtime_seconds": manifest["runtime_seconds"], "metrics": aggregate}, indent=2), flush=True)


def smoke():
    checked_config()
    from detection_service.tests.fakes import CharacterTokenizer, DeterministicCausalModel
    from detection_service.app.detectors.statistical.config import PerplexityConfig
    from detection_service.app.detectors.statistical.perplexity_detector import StatisticalPerplexityDetector
    from detection_service.app.detectors.statistical.perplexity_engine import PerplexityEngine
    rows = [{"sample_id": f"synthetic-{i:03}", "partition": "BASE_TRAIN", "label": str(i % 2),
             "lineage_group": "LG-N1-" + f"{i:024x}", "source_name": "synthetic", "outer_fold": str(i % 5)} for i in range(40)]
    pcfg = PerplexityConfig(model_id="synthetic", model_revision="synthetic", tokenizer_id="synthetic",
                           max_analysis_tokens=200, window_size=8, window_stride=4)
    det = StatisticalPerplexityDetector(pcfg, PerplexityEngine(pcfg, CharacterTokenizer(64), DeterministicCausalModel(64)))
    texts = ["ordinary synthetic note" if i % 2 == 0 else "different synthetic pattern xyz !" for i in range(40)]
    matrix, evidence = extract(rows, texts, det)
    records, reports = run_folds(rows, matrix, evidence)
    validate_projections(records)
    require(len(records) == 40 and all(f["identity_leakage"] == f["lineage_leakage"] == 0 for f in reports), "synthetic smoke leak")
    write(OUTPUT / "synthetic_smoke_v1.json", {"status": "PASS", "synthetic_rows": 40, "folds": 5,
                                            "no_project_texts": True, "no_reference_weights_loaded": True})
    print(json.dumps({"status": "SYNTHETIC_SMOKE_PASS"}), flush=True)


def check():
    checked_config()
    completion = json.loads((OUTPUT / "completion_v1.json").read_text(encoding="utf-8"))
    verify_hashes(OUTPUT, completion["artifact_sha256"])
    with (OUTPUT / "ds_v1_recipe_oof_predictions.csv").open(encoding="utf-8", newline="") as handle:
        loaded = list(csv.DictReader(handle))
    rows, _ = selected_metadata()
    require([r["sample_id"] for r in loaded] == [r["sample_id"] for r in rows], "OOF identity/order drift")
    check_membership(loaded)
    for row, fixture in zip(loaded, rows, strict=True):
        require(all(row[k] == fixture[k] for k in fixture), "OOF fixture metadata drift")
        require(row["calibrated_probability"] == "", "unauthorized calibration output")
        require(int(row["binary_prediction"]) == int(float(row["raw_score"]) >= COMPARISON_THRESHOLD), "binary rule drift")
    recorded = json.loads((OUTPUT / "ds_v1_recipe_oof_metrics.json").read_text(encoding="utf-8"))
    actual = metrics([int(r["label"]) for r in loaded], [float(r["raw_score"]) for r in loaded])
    require(all(actual[k] == recorded[k] for k in actual), "metric recomputation drift")
    print(json.dumps({"status": "PASS", "rows": len(loaded), "artifact_hash_checks": len(completion["artifact_sha256"])}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", required=True, choices=("prepare", "smoke", "run", "check"))
    args = parser.parse_args()
    {"prepare": prepare, "smoke": smoke, "run": run, "check": check}[args.mode]()


if __name__ == "__main__":
    main()
