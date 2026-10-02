"""One fixed D_S recipe: prepare, BASE_TRAIN fit, CALIBRATION fit, one VALIDATION."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import shutil
import subprocess
import time
from collections import Counter
from dataclasses import asdict
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

import joblib
import numpy as np
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from detection_service.app.contracts.detection_request import DetectionContent, DetectionRequest
from detection_service.app.detectors.semantic.calibration import MANIFEST_SHA256, file_sha256
from detection_service.app.detectors.statistical.config import PerplexityConfig
from detection_service.app.detectors.statistical.perplexity_detector import StatisticalPerplexityDetector
from detection_service.app.detectors.statistical.perplexity_engine import PerplexityEngine
from detection_service.app.detectors.statistical_risk import ScoredStatisticalDetector, StatisticalScorer
from detection_service.app.detectors.statistical_risk.schema import FEATURE_SCHEMA, feature_vector, json_bytes, schema_hash
from detection_service.app.detectors.statistical_risk.scorer import RECIPE, CALIBRATION_VERSION, METHOD, fit_calibrator, load_calibrator, verify_hashes
from detection_service.scripts.calibrate_semantic_baseline import validate_rows, load_calibration_texts, diagnostics
from detection_service.app.detectors.semantic_finetuned.data import load_texts
from detection_service.scripts.train_semantic_baseline import evaluate_validation

ROOT = Path(__file__).resolve().parents[2]
MODEL = ROOT / "artifacts/models/ds_v1"
MANIFEST = ROOT / "data_governance/manifests/development_partition_manifest_v1.csv"
COUNT = {"BASE_TRAIN": 1135, "CALIBRATION": 233, "VALIDATION": 233}
SCORER_FILES = ("model_config.json", "feature_schema.json", "scorer.joblib", "training_metadata.json")
CALIBRATION_RECIPE = {
    "version": CALIBRATION_VERSION, "method": METHOD,
    "input": "logit(clip(raw_LR_class_1_probability,1e-12,1-1e-12))",
    "target_smoothing": "positive=(Npos+1)/(Npos+2); negative=1/(Nneg+2)",
    "positive_slope_lower_bound": 1e-8, "optimizer": "L-BFGS-B", "maxiter": 1000,
    "ftol": 1e-12, "gtol": 1e-10, "class_weight": None, "penalty": None,
    "default_vote": "calibrated_probability >= 0.5; DEFAULT DEVELOPMENT CUTPOINT",
    "final_operating_point": "NOT_FROZEN",
}


def write(path, value):
    path.write_bytes(json_bytes(value))


def now():
    return datetime.now(timezone.utc).isoformat()


def environment():
    return {"python": platform.python_version(), "os": platform.platform(), "torch_runtime": torch.__version__,
            "cuda_available": torch.cuda.is_available(), "cpu_threads": 8,
            "packages": {n: version(n) for n in ("torch", "transformers", "tokenizers", "huggingface-hub", "scikit-learn", "numpy", "scipy", "joblib", "pyarrow", "fastapi", "pydantic", "pytest")}}


def selected_rows(path, partition, expected=MANIFEST_SHA256):
    if partition not in COUNT:
        raise RuntimeError("Protected/non-development partition forbidden")
    if file_sha256(path) != expected:
        raise RuntimeError("STOP: development manifest integrity failure")
    with path.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    if Counter(r["partition"] for r in rows) != COUNT:
        raise RuntimeError("STOP: authoritative partition counts differ")
    validate_rows(rows)
    return [r for r in rows if r["partition"] == partition]


def config():
    return json.loads((MODEL / "model_config.json").read_text(encoding="utf-8"))


def check_preserved(cfg):
    verify_hashes(ROOT, cfg["feature_extractor_sha256"])
    reference = cfg["reference_lm"]
    verify_hashes(ROOT / reference["snapshot_path"], reference["file_sha256"])
    snapshot = json.loads((ROOT / "detection_service/outputs/integration_preflight.json").read_text(encoding="utf-8"))
    if snapshot["status"] != "PASS":
        raise RuntimeError("Prior preservation preflight did not pass")
    for record in snapshot["records"]:
        if file_sha256(Path(record["path"])) != record["expected"]:
            raise RuntimeError("STOP: preserved detector artifact drift")
    if file_sha256(MANIFEST) != MANIFEST_SHA256:
        raise RuntimeError("STOP: manifest drift")


def prepare():
    if MODEL.exists():
        raise RuntimeError("D_S recipe directory already exists; refusing overwrite")
    selected_rows(MANIFEST, "BASE_TRAIN")  # Membership metadata only; no text/feature extraction.
    preflight = json.loads((ROOT / "detection_service/outputs/stat002-preflight.json").read_text(encoding="utf-8"))
    verify_hashes(ROOT, preflight["feature_extractor_sha256"])
    cfg = PerplexityConfig()
    original = Path.home() / ".cache/huggingface/hub/models--distilbert--distilgpt2/snapshots" / cfg.model_revision
    snapshot = ROOT / "detection_service/.model-cache/ds_v1" / ("snapshot-" + cfg.model_revision)
    if snapshot.exists():
        raise RuntimeError("Reference snapshot target already exists; inspect before preparing")
    names = ("config.json", "generation_config.json", "model.safetensors", "merges.txt", "vocab.json", "tokenizer.json", "tokenizer_config.json")
    hashes = {name: file_sha256(original / name) for name in names}
    snapshot.mkdir(parents=True)
    for name in names:
        shutil.copyfile(original / name, snapshot / name)
    verify_hashes(snapshot, hashes)
    payload = {
        "detector_id": "statistical_perplexity", "detector_version": "ds_v1",
        "feature_extractor_version": "v0.1", "feature_extractor_sha256": preflight["feature_extractor_sha256"],
        "feature_schema_sha256": schema_hash(), "scorer_recipe": RECIPE,
        "extractor_config": asdict(cfg), "training_manifest_sha256": MANIFEST_SHA256,
        "reference_lm": {"model_id": cfg.model_id, "revision": cfg.model_revision,
                         "snapshot_path": snapshot.relative_to(ROOT).as_posix(), "file_sha256": hashes},
        "raw_score": "LR predict_proba class 1; higher = adversarial risk",
        "calibration_version": CALIBRATION_VERSION, "calibration_recipe": CALIBRATION_RECIPE,
        "default_binary_vote": "calibrated_probability >= 0.5; DEFAULT DEVELOPMENT CUTPOINT",
        "final_operating_point": "NOT_FROZEN", "source_git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "created_at_utc": now(), "environment": environment(),
    }
    MODEL.mkdir()
    write(MODEL / "model_config.json", payload)
    write(MODEL / "feature_schema.json", FEATURE_SCHEMA)
    write(MODEL / "preparation.json", {"recipe_frozen_before_text_extraction": True,
                                      "recipe_sha256": file_sha256(MODEL / "model_config.json"),
                                      "feature_schema_sha256": schema_hash(), "reference_hashes_verified": True})
    check_preserved(payload)
    print(json.dumps({"status": "PREPARED", "feature_count": FEATURE_SCHEMA["feature_count"], "schema_sha256": schema_hash()}), flush=True)


def extractor(cfg):
    reference = ROOT / cfg["reference_lm"]["snapshot_path"]
    tokenizer = AutoTokenizer.from_pretrained(reference, local_files_only=True, use_fast=True, trust_remote_code=False)
    model = AutoModelForCausalLM.from_pretrained(reference, local_files_only=True, use_safetensors=True, trust_remote_code=False)
    model.requires_grad_(False)
    pcfg = PerplexityConfig(**cfg["extractor_config"])
    return StatisticalPerplexityDetector(pcfg, PerplexityEngine(pcfg, tokenizer, model))


def extract_partition(detector, partition):
    rows = selected_rows(MANIFEST, partition)
    # Original immutable containers are read; only selected membership text is scored.
    texts, hashes = (load_calibration_texts(rows, ROOT) if partition == "CALIBRATION" else load_texts(rows, ROOT, partition))
    expected = json.loads((ROOT / "artifacts/models/dm_b_v1/calibration/calibration_metadata.json").read_text(encoding="utf-8"))["source_artifact_sha256"]
    if hashes != expected:
        raise RuntimeError("STOP: approved raw source artifact hash drift")
    matrix = []
    start = time.perf_counter()
    for index, (row, text) in enumerate(zip(rows, texts, strict=True), start=1):
        result = detector.detect(DetectionRequest(request_id=row["record_id"], content=DetectionContent(type="user_prompt", text=text)))
        try:
            matrix.append(feature_vector(result))
        except Exception as exc:
            write(MODEL / (partition.lower() + "_extraction_failure.json"), {
                "status": "STOP", "partition": partition, "record_id": row["record_id"],
                "processed_before_failure": index - 1, "failure_type": type(exc).__name__, "message": str(exc),
                "input_tokens": result.input_coverage.input_tokens, "feature_values": result.features.model_dump(),
            })
            raise
        if index % 50 == 0 or index == len(rows):
            print(json.dumps({"partition": partition, "processed": index, "total": len(rows), "elapsed_seconds": round(time.perf_counter() - start, 2)}), flush=True)
    x = np.asarray(matrix)
    cache = ROOT / "detection_service/outputs/stat002-features"
    cache.mkdir(exist_ok=True)
    np.save(cache / (partition.lower() + ".npy"), x)
    return rows, x, {"partition": partition, "sample_count": len(rows), "feature_count": x.shape[1],
                     "feature_schema_sha256": schema_hash(), "row_order_sha256": hashlib.sha256("\n".join(r["record_id"] for r in rows).encode()).hexdigest(),
                     "source_artifact_sha256": hashes, "matrix_sha256": file_sha256(cache / (partition.lower() + ".npy")),
                     "extraction_seconds": time.perf_counter() - start, "nonfinite_values": 0, "failures": 0}


def train():
    if (MODEL / "training_started.json").exists():
        raise RuntimeError("Training was already started; no automatic repeat fit")
    cfg = config()
    check_preserved(cfg)
    preparation = json.loads((MODEL / "preparation.json").read_text())
    if preparation["recipe_sha256"] != file_sha256(MODEL / "model_config.json"):
        raise RuntimeError("Frozen pretraining recipe drift")
    write(MODEL / "training_started.json", {"started_at_utc": now(), "partition": "BASE_TRAIN"})
    det = extractor(cfg)
    rows, matrix, extraction = extract_partition(det, "BASE_TRAIN")
    start = time.perf_counter()
    scorer = StatisticalScorer.fit(matrix, rows)
    training_seconds = time.perf_counter() - start
    joblib.dump(scorer.model, MODEL / "scorer.joblib")
    metadata = {"detector_version": "ds_v1", "partitions_fitted": ["BASE_TRAIN"], "sample_count": len(rows),
                "training_code_sha256": file_sha256(Path(__file__)),
                "fit_git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                "positive_count": sum(int(r["canonical_label"]) for r in rows),
                "negative_count": sum(r["canonical_label"] == "0" for r in rows),
                "feature_names": FEATURE_SCHEMA["feature_names"], "feature_schema_sha256": schema_hash(),
                "extraction": extraction, "recipe": RECIPE, "converged": True,
                "n_iter": scorer.model.n_iter_.tolist(), "coefficients": scorer.model.coef_.tolist(),
                "intercept": scorer.model.intercept_.tolist(), "training_seconds": training_seconds,
                "scorer_sha256": file_sha256(MODEL / "scorer.joblib"), "created_at_utc": now(),
                "calibration_used_for_scorer": False, "validation_used_for_fitting": False, "protected_data_used": False}
    write(MODEL / "training_metadata.json", metadata)
    write(MODEL / "integrity_manifest.json", {name: file_sha256(MODEL / name) for name in SCORER_FILES})
    loaded, _ = StatisticalScorer.load(MODEL)
    if not np.array_equal(scorer.predict(matrix), loaded.predict(matrix)):
        raise RuntimeError("Scorer serialization changed probabilities")
    check_preserved(cfg)
    print(json.dumps({"status": "SCORER_FROZEN", "n_iter": metadata["n_iter"], "training_seconds": training_seconds}), flush=True)


def calibrate():
    output = MODEL / "calibration"
    if output.exists():
        raise RuntimeError("Calibration already exists; refusing a second fit")
    scorer, cfg = StatisticalScorer.load(MODEL)
    check_preserved(cfg)
    output.mkdir()
    write(output / "calibration_started.json", {"started_at_utc": now(), "partition": "CALIBRATION"})
    rows, matrix, extraction = extract_partition(extractor(cfg), "CALIBRATION")
    raw = scorer.predict(matrix)
    metadata = {"detector_version": "ds_v1", "calibration_version": CALIBRATION_VERSION, "calibration_method": METHOD,
                "calibration_code_sha256": file_sha256(Path(__file__)),
                "shared_fitter_sha256": file_sha256(ROOT / "detection_service/app/detectors/semantic/calibration.py"),
                "partitions_fitted": ["CALIBRATION"], "feature_schema_sha256": schema_hash(),
                "frozen_scorer_sha256": {name: file_sha256(MODEL / name) for name in (*SCORER_FILES, "integrity_manifest.json")},
                "manifest_sha256": MANIFEST_SHA256, "recipe": CALIBRATION_RECIPE, "extraction": extraction,
                "created_at_utc": now(), "scorer_retrained": False, "validation_used": False, "protected_data_used": False}
    calibrator = fit_calibrator(raw, rows, metadata)
    calibrator.save(output)
    write(output / "calibration_config.json", CALIBRATION_RECIPE)
    write(output / "integrity_manifest.json", {name: file_sha256(output / name) for name in ("calibrator.json", "calibration_metadata.json", "calibration_config.json")})
    loaded = load_calibrator(output, MODEL)
    calibrated = calibrator.predict(raw)
    if not np.array_equal(calibrated, loaded.predict(raw)):
        raise RuntimeError("Calibration serialization changed probabilities")
    metrics = diagnostics(np.array([int(r["canonical_label"]) for r in rows]), raw, calibrated)
    metrics["scope"] = "FITTING-PARTITION CALIBRATION DIAGNOSTICS; NOT GENERALIZATION"
    write(output / "calibration_fit_diagnostics.json", metrics)
    check_preserved(cfg)
    print(json.dumps({"status": "CALIBRATOR_FROZEN", "slope": calibrator.slope, "intercept": calibrator.intercept}), flush=True)


def validate():
    if (MODEL / "validation_started.json").exists():
        raise RuntimeError("VALIDATION already started; exactly-once evaluation cannot be repeated")
    scorer, cfg = StatisticalScorer.load(MODEL)
    calibrator = load_calibrator(MODEL / "calibration", MODEL)
    check_preserved(cfg)
    write(MODEL / "validation_started.json", {"started_at_utc": now(), "scorer_and_calibrator_frozen": True,
                                              "decision_frozen": cfg["default_binary_vote"]})
    rows, matrix, extraction = extract_partition(extractor(cfg), "VALIDATION")
    scores = calibrator.predict(scorer.predict(matrix))
    metrics = evaluate_validation(rows, scores, 0.5)
    metrics.update(scope="DEVELOPMENT-ONLY VALIDATION; NOT E1-E10", score_basis="calibrated_probability",
                   extraction=extraction, evaluation_count=1, scorer_retrained=False, recalibrated=False,
                   protected_data_used=False, final_operating_point="NOT_FROZEN")
    write(MODEL / "validation_metrics.json", metrics)
    check_preserved(cfg)
    print(json.dumps({"status": "VALIDATION_COMPLETE", "metrics": metrics}, indent=2), flush=True)


def smoke():
    from fastapi.testclient import TestClient
    from detection_service.app.core.settings import Settings
    from detection_service.app.main import create_app
    detector = ScoredStatisticalDetector.from_artifact(MODEL)
    identity = (id(detector.extractor.engine.model), id(detector.scorer), id(detector.calibrator))
    with TestClient(create_app(Settings("ds_v1_engineering", PerplexityConfig(), statistical_model_dir=str(MODEL)), lambda: detector)) as client:
        payload = {"request_id": "ds-v1-smoke", "content": {"type": "user_prompt", "text": "Summarize the engineering agenda for tomorrow."}}
        a = client.post("/v1/detect/input", json=payload)
        b = client.post("/v1/detect/input", json=payload)
    assert a.status_code == b.status_code == 200
    one, two = a.json()["detectors"][0], b.json()["detectors"][0]
    assert one["detector_version"] == "ds_v1" and one["features"]["whole_prompt_nll"] is not None
    for key in ("raw_score", "calibrated_probability", "binary_vote", "features", "input_coverage"):
        assert one[key] == two[key]
    assert 0 <= one["raw_score"] <= 1 and 0 <= one["calibrated_probability"] <= 1
    assert one["binary_vote"] == (one["calibrated_probability"] >= .5)
    assert identity == (id(detector.extractor.engine.model), id(detector.scorer), id(detector.calibrator))
    check_preserved(config())
    write(MODEL / "service_smoke.json", {"status": "PASS", "scope": "SYNTHETIC ENGINEERING ONLY", "repeat_deterministic": True,
                                       "model_scorer_calibrator_reused": True, "result": one})
    print(json.dumps({"status": "SERVICE_SMOKE_PASS"}), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("prepare", "train", "calibrate", "validate", "smoke"), required=True)
    args = parser.parse_args()
    torch.manual_seed(1701)
    torch.set_num_threads(8)
    torch.use_deterministic_algorithms(True)
    {"prepare": prepare, "train": train, "calibrate": calibrate, "validate": validate, "smoke": smoke}[args.mode]()


if __name__ == "__main__":
    main()
