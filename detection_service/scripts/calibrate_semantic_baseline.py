from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import sys
import time
from collections import Counter, defaultdict
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path
from unittest.mock import patch

import numpy as np

from detection_service.app.detectors.semantic.calibration import (
    CALIBRATION_VERSION,
    EPSILON,
    MANIFEST_SHA256,
    METHOD,
    SigmoidCalibrator,
    file_sha256,
    model_binding,
)
from detection_service.app.detectors.semantic.classifier import LogisticRegressionSemanticClassifier
from detection_service.app.detectors.semantic.detector import SemanticBaselineDetector
from detection_service.scripts.train_semantic_baseline import git_metadata


SOURCES = {
    "Do-Not-Answer": ("DS-TXT-017", "460703484df354958a5e1cd7378a38fcb94a2f3e"),
    "deepset Prompt Injection": ("DS-TXT-018", "4f61ecb038e9c3fb77e21034b22511b523772cdd"),
}
SOURCE_FILES = {
    "ART-W2-DNA-INSTRUCTIONS": "Dataset/Raw/datasets/GitHub/Do-Not-Answer/datasets/Instruction/do_not_answer_en.csv",
    "ART-W2-DEEPSET-TRAIN": "Dataset/Raw/datasets/HuggingFace/deepset-prompt-injections/data/train-00000-of-00001-9564e8b05b4757ab.parquet",
    "ART-W2-DEEPSET-TEST": "Dataset/Raw/datasets/HuggingFace/deepset-prompt-injections/data/test-00000-of-00001-701d16158af87368.parquet",
}
FROZEN_CONFIG = {
    "detector_id": "semantic_embedding_lr", "detector_version": "dm_a_v1",
    "encoder_model": "WhereIsAI/UAE-Large-V1", "embedding_dim": 1024,
    "encoder_revision": "local-cache-model_safetensors_sha256:8ac0e0e2eb9f5371c528f5269876e33b298790699ddf3b824efeef9ded542e24",
    "tokenizer_revision": "local-cache-tokenizer_json_sha256:d241a60d5e8f04cc1b2b3e9ef7a4921b27bf526d9f6050ab90f9267a1f9e5c66",
    "pooling": "cls_token", "normalize_embeddings": True, "max_sequence_length": 512,
    "truncation_policy": "sentence-transformers tokenizer truncation to max_seq_length=512",
    "canonical_text_field": "source.raw_text",
    "whitespace_behavior": "preserve source text; no additional whitespace normalization",
    "preprocessing_version": "D_M-A-v1-source-raw-text-preserved",
    "solver": "lbfgs", "penalty": "l2", "C": 1.0, "class_weight": "balanced",
    "max_iter": 1000, "random_seed": 1701, "fit_intercept": True,
    "training_manifest_sha256": MANIFEST_SHA256,
    "label_mapping": {"benign": 0, "attack": 1}, "default_development_cutpoint": 0.5,
}


def calibration_rows(manifest: Path) -> list[dict[str, str]]:
    if file_sha256(manifest) != MANIFEST_SHA256:
        raise RuntimeError("STOP: development manifest integrity failure")
    with manifest.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if Counter(r["partition"] for r in rows) != {
        "BASE_TRAIN": 1135, "CALIBRATION": 233, "VALIDATION": 233
    }:
        raise RuntimeError("partition counts do not match the authoritative manifest")
    validate_rows(rows)
    return [r for r in rows if r["partition"] == "CALIBRATION"]


def validate_rows(rows: list[dict[str, str]]) -> None:
    groups: dict[str, set[str]] = defaultdict(set)
    seen = set()
    for row in rows:
        source = row["source_dataset"]
        if source not in SOURCES:
            raise RuntimeError("protected or non-approved source in development manifest")
        if (row["source_dataset_id"], row["source_revision"]) != SOURCES[source]:
            raise RuntimeError("approved source identity/revision mismatch")
        if row["record_id"] in seen:
            raise RuntimeError("duplicate record identity")
        seen.add(row["record_id"])
        if row["data_role"] != row["partition"] or row["partition"] not in {
            "BASE_TRAIN", "CALIBRATION", "VALIDATION"
        }:
            raise RuntimeError("partition/data role mismatch")
        if not row["rights_status"].startswith("USE_ALLOWED_LOCAL"):
            raise RuntimeError("record rights do not permit development use")
        if source == "Do-Not-Answer":
            valid_label = row["original_label"] == "RISKY_REFUSAL_PROMPT_UNLABELED" and row["canonical_label"] == "0"
        else:
            valid_label = row["original_label"] in {"0", "1"} and row["canonical_label"] == row["original_label"]
        if not valid_label:
            raise RuntimeError("label mapping violates approved taxonomy/constitution")
        if row["lineage_group_id"] != "LG-N1-" + row["normalized_hash"][:24]:
            raise RuntimeError("lineage group does not match canonical hash")
        for field in ("lineage_group_id", "exact_hash", "normalized_hash"):
            groups[field + ":" + row[field]].add(row["partition"])
    if any(len(partitions) != 1 for partitions in groups.values()):
        raise RuntimeError("lineage/hash group crosses partition boundaries")


def load_calibration_texts(rows: list[dict[str, str]], workspace: Path) -> tuple[list[str], dict[str, str]]:
    if any(r["partition"] != "CALIBRATION" for r in rows):
        raise RuntimeError("text loader accepts CALIBRATION membership only")
    import pyarrow.parquet as pq

    selected: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        artifact, locator = row["canonical_text_reference"].split("::")
        expected_source = "Do-Not-Answer" if artifact == "ART-W2-DNA-INSTRUCTIONS" else "deepset Prompt Injection"
        expected_type = "csv_row" if expected_source == "Do-Not-Answer" else "parquet_row"
        if artifact not in SOURCE_FILES or row["source_dataset"] != expected_source:
            raise RuntimeError("non-approved source artifact locator")
        if not locator.startswith(expected_type + ":") or int(locator.split(":")[1]) < 1:
            raise RuntimeError("invalid one-based source row locator")
        selected[artifact].append(row)
    texts: dict[str, str] = {}
    source_hashes: dict[str, str] = {}
    for artifact, subset in selected.items():
        path = workspace / SOURCE_FILES[artifact]
        source_hashes[SOURCE_FILES[artifact]] = file_sha256(path)
        # Decode only selected Parquet text/label values, never protected source files.
        wanted = {int(r["canonical_text_reference"].split(":")[-1]) - 1: r for r in subset}
        if artifact == "ART-W2-DNA-INSTRUCTIONS":
            with path.open(encoding="utf-8-sig", newline="") as handle:
                for index, record in enumerate(csv.DictReader(handle)):
                    if index in wanted:
                        texts[wanted[index]["record_id"]] = record["question"]
        else:
            table = pq.read_table(path, columns=["text", "label"])
            for index, row in wanted.items():
                if str(table["label"][index].as_py()) != row["original_label"]:
                    raise RuntimeError("source label does not match calibration manifest")
                texts[row["record_id"]] = table["text"][index].as_py()
        if file_sha256(path) != source_hashes[SOURCE_FILES[artifact]]:
            raise RuntimeError("source artifact changed during calibration text loading")
    ordered = []
    for row in rows:
        text = texts.get(row["record_id"])
        if not isinstance(text, str) or not text.strip():
            raise RuntimeError("missing calibration text")
        if hashlib.sha256(text.encode("utf-8")).hexdigest() != row["exact_hash"]:
            raise RuntimeError("selected source text does not match the frozen manifest")
        ordered.append(text)
    return ordered, source_hashes


def verify_encoder(config: dict) -> dict[str, str]:
    if any(config.get(k) != v for k, v in FROZEN_CONFIG.items()):
        raise RuntimeError("frozen D_M-A configuration mismatch")
    path = Path(config["encoder_local_path"])
    hashes = {}
    for filename, key in (("model.safetensors", "encoder_revision"), ("tokenizer.json", "tokenizer_revision")):
        hashes[filename] = file_sha256(path / filename)
        if hashes[filename] != config[key].split(":")[-1]:
            raise RuntimeError("frozen encoder/tokenizer integrity failure")
    pooling = json.loads((path / "1_Pooling" / "config.json").read_text(encoding="utf-8"))
    modes = {k: v for k, v in pooling.items() if k.startswith("pooling_mode")}
    if modes.get("pooling_mode_cls_token") is not True or any(v for k, v in modes.items() if k != "pooling_mode_cls_token"):
        raise RuntimeError("local encoder pooling differs from frozen CLS pooling")
    return hashes


def coefficient_hash(classifier: LogisticRegressionSemanticClassifier) -> str:
    digest = hashlib.sha256()
    for value in (classifier.model.coef_, classifier.model.intercept_, classifier.model.classes_):
        digest.update(np.asarray(value).tobytes())
    return digest.hexdigest()


def diagnostics(labels: np.ndarray, raw: np.ndarray, calibrated: np.ndarray) -> dict:
    from sklearn.metrics import brier_score_loss, log_loss

    result = {"scope": "CALIBRATION-FIT DIAGNOSTICS ONLY", "sample_count": len(labels)}
    for name, values in (("raw", raw), ("calibrated", calibrated)):
        bins = []
        memberships = np.minimum((values * 10).astype(int), 9)
        for index in range(10):
            mask = memberships == index
            bins.append({
                "lower": index / 10, "upper": (index + 1) / 10, "count": int(mask.sum()),
                "mean_probability": float(values[mask].mean()) if mask.any() else None,
                "positive_fraction": float(labels[mask].mean()) if mask.any() else None,
            })
        result[name] = {
            "brier_score": float(brier_score_loss(labels, values)),
            "log_loss": float(log_loss(labels, values, labels=[0, 1])),
            "probability_summary": {
                "min": float(values.min()), "mean": float(values.mean()), "max": float(values.max()),
                "std": float(values.std()), "quantiles": np.quantile(values, [0.1, 0.5, 0.9]).tolist(),
            },
            "bins": bins,
        }
    return result


def json_file(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def service_smoke(detector: SemanticBaselineDetector) -> dict:
    from fastapi.testclient import TestClient
    from detection_service.app.main import create_app

    payload = {"request_id": "calibration-smoke", "content": {"type": "user_prompt", "text": "Please summarize the agenda for tomorrow's meeting."}}
    with TestClient(create_app(detector_factory=lambda: [detector])) as client:
        first = client.post("/v1/detect/input", json=payload)
        second = client.post("/v1/detect/input", json=payload)
    if first.status_code != 200 or second.status_code != 200:
        raise RuntimeError("calibrated API smoke failed")
    a, b = first.json()["detectors"][0], second.json()["detectors"][0]
    assert a["status"] == "success" and a["detector_version"] == "dm_a_v1"
    assert a["calibrated_probability"] is not None and 0 <= a["calibrated_probability"] <= 1
    assert a["raw_score"] == b["raw_score"]
    assert a["calibrated_probability"] == b["calibrated_probability"]
    assert a["binary_vote"] == (a["raw_score"] >= 0.5)
    assert a["metadata"]["cutpoint_type"] == "DEFAULT_DEVELOPMENT_CUTPOINT"
    assert a["latency_ms"] > 0 and payload["content"]["text"] not in first.text
    return {"status": "PASS", "http_status": first.status_code, "detector_result": a, "repeat_deterministic": True}


def write_reports(reports: Path, metadata: dict, config: dict, metrics: dict, smoke: dict) -> None:
    reports.mkdir(parents=True, exist_ok=True)
    text = f"""# Calibration Objective

Status: PASS. D_M-A dm_a_v1 now supplies a separate calibrated probability.
Date: 2026-10-01. Classifier and encoder remain frozen.

# Frozen D_M-A Configuration

WhereIsAI/UAE-Large-V1; dimension 1024; CLS pooling; normalized embeddings;
512-token truncation; preserved source.raw_text. LR remains lbfgs/l2/C=1.0,
class_weight=balanced, max_iter=1000, seed=1701, fit_intercept=True.
Exact configuration and frozen artifact hashes are recorded in calibration metadata.

# Calibration Dataset

Only CALIBRATION member text/labels from Do-Not-Answer and deepset Prompt Injection.
BASE_TRAIN and VALIDATION membership metadata was checked for disjoint lineage;
neither partition was embedded, fitted, or evaluated in this task. Protected source
files and the mixed-source normalized archive were not opened.
Selected source text SHA-256 and deepset source labels match the manifest.
Label semantics follow LABEL_TAXONOMY_v1.md as specialized by the approved
DEVELOPMENT_DATA_CONSTITUTION_v1.md: benign/hard-benign=0; injection attempt=1.

# Calibration Manifest Hash

`{MANIFEST_SHA256}`. Verified before fitting and after execution.
Calibration membership/order hash: `{metadata['calibration_membership_sha256']}`.

# Calibration Method

`{METHOD}`; version `{CALIBRATION_VERSION}`.
Fit q = sigmoid(a * logit(clip(p, 1e-12, 1-1e-12)) + b).
Two parameters, smoothed Platt targets, positive slope constraint (>=1e-8),
unweighted cross entropy, no additional penalty. Deterministic L-BFGS-B;
maxiter=1000, ftol=1e-12, gtol=1e-10; no random-state-dependent fitting.
Method and settings were specified in code before any fit diagnostics.
No alternative methods, validation selection, or threshold search were performed.

# Method Rationale

A two-parameter sigmoid is sample-efficient for 233 examples compared with a
flexible stepwise mapping. Smoothed class targets stabilize separated samples.
The positive slope preserves ordering; calibration estimates probability under
the reserved development mixture rather than the classifier's balanced class weighting.

# Sample Counts

Total: {metadata['calibration_sample_count']}; positive: {metadata['calibration_positive_count']};
negative: {metadata['calibration_negative_count']}.
Source counts: `{json.dumps(metadata['source_counts'])}`.
Exact/canonical lineage groups are disjoint across all three manifest partitions.

# Raw Probability Definition

raw_score remains the existing LR predict_proba output for class 1.
The classifier is never fitted in this task; its fit method is guarded against calls.
Coefficient and artifact hashes match before/after. Raw probability equality after
serialization/reload is verified on all 233 calibration embeddings.

# Calibrated Probability Definition

calibrated_probability is the frozen sigmoid mapping applied to raw_score.
The binary vote continues to use raw_score >= 0.5, explicitly labeled
DEFAULT_DEVELOPMENT_CUTPOINT. No new operating threshold was selected.

# Calibration-Fit Diagnostics

These are fitting-partition diagnostics, **not independent generalization results**.

| Probability | Brier Score | Log Loss |
|---|---:|---:|
| Raw | {metrics['raw']['brier_score']:.8f} | {metrics['raw']['log_loss']:.8f} |
| Calibrated | {metrics['calibrated']['brier_score']:.8f} | {metrics['calibrated']['log_loss']:.8f} |

Ten equal-width bins include probabilities 0 and 1. Counts, mean probabilities,
positive fractions, quantiles and summaries are in calibration_fit_diagnostics.json.

# Artifact

`artifacts/models/dm_a_v1/calibration/`: calibrator.json, calibration_config.json,
calibration_metadata.json, calibration_fit_diagnostics.json, service_smoke.json.
No raw text, per-record calibration scores, or calibration embeddings are packaged.
Mapping integrity and classifier/configuration hash compatibility are checked at load.

# Service Integration

/v1/detect/input: {smoke['status']}; returns raw_score, calibrated_probability,
binary_vote, latency and calibration version/method/manifest metadata.
Repeated inference on synthetic meeting text is deterministic. Existing artifact
loading automatically loads the calibration subdirectory and fails explicitly for
invalid or incomplete calibration. require_calibration=True also rejects absence.

The default service's semantic detector wiring requires this calibration layer.
Enable it with `ENABLE_SEMANTIC_DETECTOR=true` and
`SEMANTIC_MODEL_DIR=artifacts/models/dm_a_v1`; retain `SEMANTIC_DEVICE=cpu`.
These use the existing service configuration interface.

# Limitations

Fitting diagnostics are optimistic and cannot establish improved generalization.
VALIDATION was preserved for a later approved protocol. The 41 positives give
limited calibration evidence; source labels remain MEDIUM confidence. Calibration
reflects this narrow development mixture, not deployment prevalence or the full
attack taxonomy. Exact/canonical lineage checks do not resolve all semantic or
documentary dependencies. Local encoder revisions are pinned by content hashes.

# Reproducibility

Frozen config, source hashes, selected membership hash, encoder/tokenizer hashes,
software versions, Git revision and working-tree state are in metadata.
CPU deterministic inference, eval mode, seed=1701; no embedding cache reused.
Run: `.\\.local-python\\python.exe -m detection_service.scripts.calibrate_semantic_baseline`.
The runner refuses to overwrite an existing authoritative calibration directory.
Tests and actual verification evidence are in TECH_SEM_001_CALIBRATION_TEST_REPORT_v1.md.
"""
    (reports / "TECH_SEM_001_CALIBRATION_REPORT_v1.md").write_text(text, encoding="utf-8")
    status = """# TECH IMPLEMENTATION STATUS v4

Date: 2026-10-01

| Area | Status | Evidence |
|---|---|---|
| D_S instrumentation | COMPLETE | Existing v0.1 implementation unchanged. |
| D_S scorer / calibration | ABSENT | No change in this task. |
| D_M-A frozen encoder / classifier | COMPLETE | dm_a_v1 artifacts and coefficients unchanged. |
| D_M-A calibration | COMPLETE | dm_a_v1_sigmoid_v1 fitted on 233 CALIBRATION rows only. |
| D_M-A calibration quality | FIT DIAGNOSTICS ONLY | No independent post-calibration evaluation. |
| D_M-A service / API | COMPLETE | Separate calibrated_probability returned. |
| D_M-A operating threshold | DEVELOPMENT DEFAULT ONLY | Raw-score cutpoint 0.5 retained. |
| D_M-A validation | PRESERVED | No new validation inference or evaluation in this task. |
| D_M-B / TECH-SEM-002 | ABSENT | Ready for separately authorized implementation. |
| D_G | ABSENT | No integration started. |
| Protected experiments | NOT RUN | No protected data consumed. |

Recommendation: READY FOR TECH-SEM-002. This task does not start or authorize it.
"""
    (reports / "TECH_IMPLEMENTATION_STATUS_v4.md").write_text(status, encoding="utf-8")


def execute(args: argparse.Namespace) -> None:
    import torch
    from sklearn.linear_model import LogisticRegression

    manifest = Path(args.manifest)
    model_dir = Path(args.model_dir)
    output = model_dir / "calibration"
    if output.exists():
        raise RuntimeError("authoritative calibration directory already exists; refusing overwrite")
    rows = calibration_rows(manifest)
    config = json.loads((model_dir / "model_config.json").read_text(encoding="utf-8"))
    encoder_hashes = verify_encoder(config)
    policies = [Path("experiment_readiness/LABEL_TAXONOMY_v1.md"), Path("data_governance/DEVELOPMENT_DATA_CONSTITUTION_v1.md")]
    policy_hashes = {str(p): file_sha256(p) for p in policies}
    baseline = {str(p.relative_to(model_dir)): file_sha256(p) for p in model_dir.rglob("*") if p.is_file()}
    texts, source_hashes = load_calibration_texts(rows, Path.cwd())
    labels = np.array([int(r["canonical_label"]) for r in rows], dtype=int)
    print(f"Preflight PASS: {len(rows)} CALIBRATION samples; {int(labels.sum())} positive; no other partition text loaded", flush=True)
    torch.manual_seed(1701)
    np.random.seed(1701)
    torch.use_deterministic_algorithms(True)
    with patch.object(LogisticRegression, "fit", side_effect=RuntimeError("classifier retraining is forbidden")):
        detector = SemanticBaselineDetector.from_artifact(model_dir, device="cpu")
        classifier = detector.classifier
        coefficient_before = coefficient_hash(classifier)
        started = time.perf_counter()
        embeddings = detector.encoder.encode(texts)
        embedding_seconds = time.perf_counter() - started
        if embeddings.shape != (233, 1024) or not np.isfinite(embeddings).all():
            raise RuntimeError("calibration embedding shape/values mismatch")
        raw = classifier.predict_raw(embeddings)
        metadata = {
            "detector_id": "semantic_embedding_lr", "detector_version": "dm_a_v1",
            "calibration_version": CALIBRATION_VERSION, "calibration_method": METHOD,
            "calibration_manifest_sha256": MANIFEST_SHA256,
            "calibration_membership_sha256": hashlib.sha256("\n".join(r["record_id"] for r in rows).encode()).hexdigest(),
            "label_mapping": {"benign": 0, "attack": 1},
            "source_counts": dict(Counter(r["source_dataset"] for r in rows)),
            "source_artifact_sha256": source_hashes, "policy_sha256": policy_hashes,
            "frozen_model_sha256": model_binding(model_dir), "frozen_config": config,
            "encoder_files_sha256": encoder_hashes, "coefficient_sha256": coefficient_before,
            "created_at": datetime.now(UTC).isoformat(),
            "software_versions": {p: version(p) for p in ("numpy", "scipy", "scikit-learn", "sentence-transformers", "torch", "transformers", "pyarrow")},
            "python_version": sys.version,
            "platform": platform.platform(),
            "git": git_metadata(), "embedding_seconds": embedding_seconds, "device": "cpu",
            "partitions_fitted": ["CALIBRATION"], "validation_consumed": False,
            "base_train_consumed": False, "protected_data_consumed": False,
            "classifier_retrained": False, "embedding_cache_reused": False,
            "raw_probability_sha256": hashlib.sha256(raw.tobytes()).hexdigest(),
            "method_prespecified": True,
        }
        calibrator = SigmoidCalibrator.fit_mapping(raw, labels, metadata)
        calibrated = calibrator.predict(raw)
        metrics = diagnostics(labels, raw, calibrated)
        if coefficient_before != coefficient_hash(classifier):
            raise RuntimeError("classifier coefficients changed")
        for filename, digest in baseline.items():
            if file_sha256(model_dir / filename) != digest:
                raise RuntimeError("frozen model artifact changed")
        if file_sha256(manifest) != MANIFEST_SHA256:
            raise RuntimeError("manifest changed during execution")
        calibrator.save(output)
        reloaded = SigmoidCalibrator.load(output, model_dir)
        assert np.array_equal(calibrated, reloaded.predict(raw))
        reloaded_classifier = LogisticRegressionSemanticClassifier.load(model_dir)
        assert np.array_equal(raw, reloaded_classifier.predict_raw(embeddings))
        detector.calibrator = reloaded
        smoke = service_smoke(detector)
        configuration = {
            "calibration_method": METHOD, "calibration_version": CALIBRATION_VERSION,
            "input": "logit(clip(raw_LR_probability,epsilon,1-epsilon))", "epsilon": EPSILON,
            "target_smoothing": "positive=(Npos+1)/(Npos+2); negative=1/(Nneg+2)",
            "optimizer": "L-BFGS-B", "initial_slope": 1.0, "positive_slope_lower_bound": 1e-8,
            "initial_intercept": "log((Npos+1)/(Nneg+1))", "random_state": "none; deterministic",
            "maxiter": 1000, "ftol": 1e-12, "gtol": 1e-10,
            "class_weight": None, "penalty": None, "threshold_optimized": False,
            "binary_vote_basis": "raw_score >= 0.5; DEFAULT_DEVELOPMENT_CUTPOINT",
        }
        json_file(output / "calibration_config.json", configuration)
        json_file(output / "calibration_fit_diagnostics.json", metrics)
        json_file(output / "service_smoke.json", smoke)
        write_reports(Path(args.reports_dir), calibrator.metadata, config, metrics, smoke)
    print(json.dumps({"status": "PASS", "calibrator": str(output), "embedding_seconds": embedding_seconds,
                      "slope": calibrator.slope, "intercept": calibrator.intercept,
                      "fit_diagnostics": {k: {m: metrics[k][m] for m in ("brier_score", "log_loss")} for k in ("raw", "calibrated")}}, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="Calibrate frozen D_M-A using CALIBRATION only")
    parser.add_argument("--manifest", default="data_governance/manifests/development_partition_manifest_v1.csv")
    parser.add_argument("--model-dir", default="artifacts/models/dm_a_v1")
    parser.add_argument("--reports-dir", default="reviews")
    execute(parser.parse_args())


if __name__ == "__main__":
    main()
