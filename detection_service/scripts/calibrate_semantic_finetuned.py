"""Fit one separate sigmoid on CALIBRATION only; never train or reuse VALIDATION."""

from __future__ import annotations

import csv
import hashlib
import json
import time
from collections import Counter
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path
from unittest.mock import patch

import numpy as np
import torch

from detection_service.app.contracts.detection_request import DetectionContent, DetectionRequest
from detection_service.app.detectors.semantic.calibration import MANIFEST_SHA256, file_sha256
from detection_service.app.detectors.semantic_finetuned.calibration import (
    CALIBRATION_VERSION, INPUT_SCORE, METHOD, FineTunedCalibrator, model_binding,
)
from detection_service.app.detectors.semantic_finetuned.detector import FineTunedSemanticDetector
from detection_service.scripts.calibrate_semantic_baseline import diagnostics, load_calibration_texts, validate_rows
from detection_service.scripts.train_semantic_baseline import git_metadata
from detection_service.scripts.train_semantic_finetuned import backbone_hash, packages, write_json

MANIFEST = Path("data_governance/manifests/development_partition_manifest_v1.csv")
MODEL = Path("artifacts/models/dm_b_v1")
RECIPE = {
    "method": METHOD, "calibration_version": CALIBRATION_VERSION, "input": INPUT_SCORE,
    "epsilon": 1e-12, "target_smoothing": "positive=(Npos+1)/(Npos+2); negative=1/(Nneg+2)",
    "optimizer": "L-BFGS-B", "initial_slope": 1.0, "positive_slope_lower_bound": 1e-8,
    "initial_intercept": "log((Npos+1)/(Nneg+1))", "maxiter": 1000, "ftol": 1e-12,
    "gtol": 1e-10, "class_weight": None, "penalty": None, "seed": "none; deterministic optimizer",
    "binary_vote_basis": "unchanged raw_score >= 0.5", "final_threshold": "NOT_FROZEN",
}


def calibration_rows(manifest: Path) -> list[dict[str, str]]:
    if file_sha256(manifest) != MANIFEST_SHA256:
        raise RuntimeError("STOP: development manifest integrity failure")
    # Filter membership metadata before validating selected rows; do not process
    # BASE_TRAIN/VALIDATION labels, locators, or features in this phase.
    with manifest.open(encoding="utf-8", newline="") as handle:
        rows = [row for row in csv.DictReader(handle) if row["partition"] == "CALIBRATION"]
    if len(rows) != 233 or Counter(r["canonical_label"] for r in rows) != {"0": 192, "1": 41}:
        raise RuntimeError("STOP: authoritative CALIBRATION counts/labels mismatch")
    validate_rows(rows)
    return rows


def verify_preserved(snapshot: dict[str, str]) -> None:
    if any(file_sha256(Path(name)) != digest for name, digest in snapshot.items()):
        raise RuntimeError("STOP: a frozen model, historical result, or prior detector file changed")
    if file_sha256(MANIFEST) != MANIFEST_SHA256:
        raise RuntimeError("STOP: manifest changed")


def service_smoke(detector: FineTunedSemanticDetector) -> dict:
    from fastapi.testclient import TestClient
    from detection_service.app.main import create_app
    payload = {"request_id": "dm-b-calibration-smoke", "content": {
        "type": "user_prompt", "text": "Summarize the engineering meeting agenda."}}
    with TestClient(create_app(detector_factory=lambda: detector)) as client:
        first = client.post("/v1/detect/input", json=payload)
        second = client.post("/v1/detect/input", json=payload)
    assert first.status_code == second.status_code == 200
    a, b = first.json()["detectors"][0], second.json()["detectors"][0]
    assert a["detector_id"] == "semantic_finetuned" and a["detector_version"] == "dm_b_v1"
    assert a["raw_score"] == b["raw_score"] and a["calibrated_probability"] == b["calibrated_probability"]
    assert a["calibrated_probability"] is not None and 0 <= a["calibrated_probability"] <= 1
    assert a["binary_vote"] == (a["raw_score"] >= .5) and a["latency_ms"] > 0
    assert a["metadata"]["calibration_version"] == CALIBRATION_VERSION
    return {"status": "PASS", "deterministic": True, "result": a}


def execute() -> None:
    output = MODEL / "calibration"
    if output.exists():
        raise RuntimeError("authoritative calibration already exists; refusing overwrite or second fit")
    rows = calibration_rows(MANIFEST)
    snapshot_path = Path("detection_service/outputs/sem002-calibration-preflight.json")
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    verify_preserved(snapshot)
    binding = model_binding(MODEL)
    texts, source_hashes = load_calibration_texts(rows, Path.cwd())
    training_metadata = json.loads((MODEL / "training_metadata.json").read_text(encoding="utf-8"))
    if source_hashes != training_metadata["source_artifact_sha256"]:
        raise RuntimeError("STOP: approved source artifact hashes differ from frozen training evidence")
    labels = np.array([int(r["canonical_label"]) for r in rows])
    torch.manual_seed(1701)
    torch.set_num_threads(8)
    torch.use_deterministic_algorithms(True)
    detector = FineTunedSemanticDetector.from_artifact(MODEL)
    detector.model.requires_grad_(False)
    initial = backbone_hash(detector.model)
    if initial != training_metadata["final_backbone_sha256"]:
        raise RuntimeError("STOP: reloaded encoder differs from frozen training evidence")
    requests = [DetectionRequest(request_id=r["record_id"], content=DetectionContent(type="user_prompt", text=t))
                for r, t in zip(rows, texts)]
    print("Preflight PASS: 233 CALIBRATION only; 41 positive, 192 negative", flush=True)
    with patch.object(torch.Tensor, "backward", side_effect=RuntimeError("transformer backward forbidden")), \
         patch.object(torch.optim.AdamW, "step", side_effect=RuntimeError("transformer updates forbidden")):
        started = time.perf_counter()
        results = detector.detect_batch(requests)
        inference_seconds = time.perf_counter() - started
        raw = np.array([r.raw_score for r in results])
        assert all(r.calibrated_probability is None for r in results)
        metadata = {
            "schema_version": "1.0", "detector_id": "semantic_finetuned", "detector_version": "dm_b_v1",
            "calibration_version": CALIBRATION_VERSION, "calibration_method": METHOD,
            "input_score_definition": INPUT_SCORE, "calibration_manifest_sha256": MANIFEST_SHA256,
            "label_mapping": {"benign": 0, "attack": 1}, "partitions_fitted": ["CALIBRATION"],
            "transformer_retrained": False, "validation_consumed": False, "protected_data_consumed": False,
            "base_train_consumed": False, "frozen_model_sha256": binding, "preserved_files_sha256": snapshot,
            "calibration_membership_sha256": hashlib.sha256("\n".join(r["record_id"] for r in rows).encode()).hexdigest(),
            "source_artifact_sha256": source_hashes, "source_counts": dict(Counter(r["source_dataset"] for r in rows)),
            "created_at": datetime.now(UTC).isoformat(), "git": git_metadata(), "packages": {**packages(), "scipy": version("scipy")},
            "code_sha256": file_sha256(Path(__file__)), "device": "cpu", "inference_seconds": inference_seconds,
            "shared_fitter_code_sha256": file_sha256(Path("detection_service/app/detectors/semantic/calibration.py")),
            "raw_probability_sha256": hashlib.sha256(raw.tobytes()).hexdigest(), "recipe": RECIPE,
            "method_prespecified": True, "encoder_sha256": initial,
        }
        calibrator = FineTunedCalibrator.fit_mapping(raw, labels, metadata)
        calibrated = calibrator.predict(raw)
        metrics = diagnostics(labels, raw, calibrated)
        metrics["scope"] = "FITTING-PARTITION CALIBRATION DIAGNOSTICS; IN-SAMPLE ONLY"
        verify_preserved(snapshot)
        assert initial == backbone_hash(detector.model)
        output.mkdir()
        calibrator.save(output)
        reloaded = FineTunedCalibrator.load(output, MODEL)
        assert np.array_equal(calibrated, reloaded.predict(raw))
        write_json(output / "calibration_config.json", RECIPE)
        write_json(output / "calibration_fit_diagnostics.json", metrics)
        write_json(output / "calibration_scores.json", {"scope": "CALIBRATION_ONLY", "records": [
            {"record_id": r["record_id"], "label": int(y), "raw_score": float(p), "calibrated_probability": float(q)}
            for r, y, p, q in zip(rows, labels, raw, calibrated)]})
        detector.calibrator = reloaded
        after = detector.detect_batch(requests)
        assert np.array_equal(raw, np.array([r.raw_score for r in after]))
        assert [r.binary_vote for r in results] == [r.binary_vote for r in after]
        assert np.array_equal(calibrated, np.array([r.calibrated_probability for r in after]))
        smoke = service_smoke(detector)
        write_json(output / "service_smoke.json", smoke)
        verify_preserved(snapshot)
        assert initial == backbone_hash(detector.model) and binding == model_binding(MODEL)
    reports = Path("reviews")
    report = f"""# TECH-SEM-002 Calibration Report v1

Date: 2026-10-01. Calibration fit and integration: PASS; full regression gate is separate.
Target: semantic_finetuned / dm_b_v1. Calibration version: {CALIBRATION_VERSION}.
Method: {METHOD}. Raw score remains softmax(logits)[1], positive class = attack.
Mapping: q = sigmoid(a * {INPUT_SCORE} + b).
Slope: {calibrator.slope!r}; intercept: {calibrator.intercept!r}.
Recipe (smoothing, monotonic constraint and optimizer) is in calibration_config.json.
Only one pre-specified fit; no method search or threshold optimization.

## Data and Integrity

CALIBRATION: 233; positive: 41; negative: 192.
Manifest SHA-256: `{MANIFEST_SHA256}`.
Source text hashes and deepset labels verified against the manifest.
Source counts: {metadata['source_counts']}.
BASE_TRAIN features used: NO. VALIDATION used: NO. Protected data used: NO.
Only CALIBRATION membership rows were validated and scored. Historical validation
artifacts were hash-checked only; no rows, predictions or metrics were parsed.
All {len(snapshot)} frozen files retain their hashes; model/tokenizer binding unchanged.
Transformer retrained: NO. All parameters disabled for gradients; backward and
AdamW steps guarded; encoder hash unchanged. D_M-A and D_S remain intact.

## Fitting-Partition Calibration Diagnostics

| Score | Brier | Log Loss |
|---|---:|---:|
| Raw | {metrics['raw']['brier_score']:.10f} | {metrics['raw']['log_loss']:.10f} |
| Calibrated | {metrics['calibrated']['brier_score']:.10f} | {metrics['calibrated']['log_loss']:.10f} |

These are **in-sample fitting diagnostics**, not unbiased generalization results.
They do not establish improved out-of-sample calibration or distribution-shift quality.

## Artifacts and Integration

Artifact directory: artifacts/models/dm_b_v1/calibration/.
Contains calibrator.json, calibration_metadata.json, calibration_config.json,
calibration_fit_diagnostics.json, calibration_scores.json and service_smoke.json.
No raw text or embeddings packaged. Transparent JSON; no executable pickle.
Reload and deterministic mapping: PASS. Raw scores and raw-score votes match
before/after on all 233 calibration records. Synthetic service/API smoke: PASS.
calibrated_probability: AVAILABLE. Base detector version remains dm_b_v1.
Existing model loading auto-attaches calibration when present; absent calibration
returns None only when require_calibration=False. Service wiring requires calibration.
Missing, incomplete, corrupt or model-incompatible calibration fails explicitly.
No raw-as-calibrated, identity, dummy, or D_M-A fallback is permitted.
Default binary vote remains raw_score >= 0.5. Final operating threshold: NOT FROZEN.

## Scientific Limits

The approved development corpus is narrow. No protected evaluation, E1-E10,
D_G integration, ensemble or shared-failure experiment occurred. Calibration
quality under distribution shift remains unknown until a separately approved evaluation.
Command: `.\\.local-python\\python.exe -m detection_service.scripts.calibrate_semantic_finetuned`.
The runner refuses an existing authoritative calibration directory.
"""
    (reports / "TECH_SEM_002_CALIBRATION_REPORT_v1.md").write_text(report, encoding="utf-8")
    print(json.dumps({"status": "CALIBRATION_FIT_AND_SMOKE_PASS", "slope": calibrator.slope,
                      "intercept": calibrator.intercept, "inference_seconds": inference_seconds,
                      "diagnostics": {k: {m: metrics[k][m] for m in ("brier_score", "log_loss")}
                                      for k in ("raw", "calibrated")}}, indent=2))


if __name__ == "__main__":
    execute()
