"""One frozen recipe, BASE_TRAIN fine-tuning, then one final VALIDATION run."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import random
import subprocess
import sys
import time
from collections import Counter
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path

import numpy as np
import torch
from huggingface_hub import HfApi, snapshot_download
from transformers import AutoModelForSequenceClassification, AutoTokenizer, get_linear_schedule_with_warmup

from detection_service.app.detectors.semantic.calibration import file_sha256
from detection_service.app.detectors.semantic_finetuned.config import FineTunedConfig, MANIFEST_SHA256, UPSTREAM_MODEL
from detection_service.app.detectors.semantic_finetuned.data import class_weights, load_partition, load_texts
from detection_service.app.detectors.semantic_finetuned.detector import FineTunedSemanticDetector
from detection_service.scripts.train_semantic_baseline import evaluate_validation, git_metadata


MANIFEST = Path("data_governance/manifests/development_partition_manifest_v1.csv")
RECIPE = Path("detection_service/configs/dm_b_v1_training.json")
PREPARATION = Path("artifacts/models/dm_b_v1_preparation.json")
OUTPUT = Path("artifacts/models/dm_b_v1")
REPORTS = Path("reviews")
LABELS = {0: "BENIGN", 1: "ATTACK"}


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n", encoding="utf-8", newline="\n")


def packages() -> dict:
    return {"python": sys.version, "torch_runtime": torch.__version__, **{
        p: version(p) for p in ("torch", "transformers", "numpy", "scikit-learn", "pyarrow", "huggingface-hub", "safetensors")
    }}


def hardware() -> dict:
    import ctypes

    class MemoryStatus(ctypes.Structure):
        _fields_ = [("length", ctypes.c_ulong), ("load", ctypes.c_ulong)] + [
            (name, ctypes.c_ulonglong) for name in ("total", "available", "total_page", "available_page", "total_virtual", "available_virtual", "extended")
        ]

    info = {"cpu": platform.processor() or os.environ.get("PROCESSOR_IDENTIFIER", "UNKNOWN"),
            "logical_cpus": os.cpu_count(), "ram_bytes": None,
            "cuda_available": torch.cuda.is_available(), "torch_cuda": torch.version.cuda}
    if os.name == "nt":
        try:
            import winreg
            key_path = "HARDWARE/DESCRIPTION/System/CentralProcessor/0".replace("/", chr(92))
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as key:
                info["cpu"] = winreg.QueryValueEx(key, "ProcessorNameString")[0]
            memory = MemoryStatus()
            memory.length = ctypes.sizeof(memory)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(memory)):
                info["ram_bytes"] = int(memory.total)
                info["available_ram_bytes"] = int(memory.available)
        except OSError as exc:
            info["cpu_memory_query_error"] = str(exc)
    if torch.cuda.is_available():
        gpu = torch.cuda.get_device_properties(0)
        info.update(gpu=gpu.name, vram_bytes=gpu.total_memory)
    try:
        info["nvidia_smi"] = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"], text=True, stderr=subprocess.STDOUT
        ).strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        info["nvidia_smi"] = f"UNAVAILABLE: {exc}"
    return info


def deterministic(config: FineTunedConfig) -> None:
    random.seed(config.seed)
    np.random.seed(config.seed)
    torch.manual_seed(config.seed)
    torch.set_num_threads(config.cpu_threads)
    if config.device == "cuda":
        if not torch.cuda.is_available():
            raise RuntimeError("frozen CUDA recipe cannot run on this torch build")
        os.environ["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"
        torch.cuda.manual_seed_all(config.seed)
        torch.backends.cuda.matmul.allow_tf32 = False
        torch.backends.cudnn.allow_tf32 = False
        torch.backends.cudnn.benchmark = False
    torch.use_deterministic_algorithms(True)


def upstream(config: FineTunedConfig, preparation: dict):
    path = Path(preparation["snapshot_path"])
    for name, digest in preparation["upstream_files_sha256"].items():
        if file_sha256(path / name) != digest:
            raise RuntimeError("upstream model/tokenizer integrity failure")
    tokenizer = AutoTokenizer.from_pretrained(path, use_fast=True, local_files_only=True)
    tokenizer.truncation_side, tokenizer.padding_side = "right", "right"
    model = AutoModelForSequenceClassification.from_pretrained(
        path, num_labels=2, id2label=LABELS, label2id={v: k for k, v in LABELS.items()},
        local_files_only=True, use_safetensors=True,
    )
    if model.config.model_type != "roberta" or model.config.num_hidden_layers != 6:
        raise RuntimeError("upstream architecture differs from DistilRoBERTa")
    return tokenizer, model.to(config.device)


def preserved_snapshot() -> dict:
    paths = []
    for directory in (Path("artifacts/models/dm_a_v1"), Path("detection_service/app/detectors/semantic"), Path("detection_service/app/detectors/statistical")):
        paths.extend(p for p in directory.rglob("*") if p.is_file() and "__pycache__" not in p.parts)
    return {str(p): file_sha256(p) for p in paths}


def check_preserved(snapshot: dict) -> None:
    if any(file_sha256(Path(name)) != digest for name, digest in snapshot.items()):
        raise RuntimeError("STOP: D_M-A or D_S integrity regression")
    if file_sha256(MANIFEST) != MANIFEST_SHA256:
        raise RuntimeError("STOP: development manifest changed")


def backbone_hash(model) -> str:
    digest = hashlib.sha256()
    for name, param in model.base_model.named_parameters():
        digest.update(name.encode())
        digest.update(param.detach().cpu().contiguous().numpy().tobytes())
    return digest.hexdigest()


def optimizer_for(model, config: FineTunedConfig):
    decay, no_decay = [], []
    for name, parameter in model.named_parameters():
        if not parameter.requires_grad:
            raise RuntimeError("D_M-B requires all transformer and head parameters trainable")
        target = no_decay if name.endswith("bias") or "LayerNorm.weight" in name else decay
        target.append(parameter)
    return torch.optim.AdamW(
        [{"params": decay, "weight_decay": config.weight_decay}, {"params": no_decay, "weight_decay": 0.0}],
        lr=config.learning_rate, betas=(0.9, 0.999), eps=1e-8,
    )


def freeze_report(config: FineTunedConfig, preparation: dict, rows: list[dict]) -> None:
    REPORTS.mkdir(exist_ok=True)
    text = f"""# TECH-SEM-002 Model and Recipe Freeze v1

Status: RECIPE_FROZEN; AUTHORITATIVE_TRAINING_PENDING. Date: 2026-10-01.
Project detector D_M-B; version dm_b_v1; detector_id semantic_finetuned.
No prior exact model decision was present in the repository. The earlier paper
notes retain TODO-MODEL and describe a lightweight end-to-end sequence classifier.
The current TECH-SEM-002 authorization supersedes earlier proposals permitting
validation-driven model selection: one fixed recipe, final checkpoint, one final evaluation.

## Model Provenance

Upstream: {config.upstream_model}; organization: distilbert / Hugging Face.
Revision and tokenizer revision: `{config.upstream_revision}`.
Architecture: RobertaForSequenceClassification, 6 transformer layers, hidden size 768.
Exact parameter count including binary head: {preparation['parameter_count']}.
Context capacity: 512; frozen input limit: {config.max_sequence_length}, including special tokens.
License: Apache-2.0, verified in the pinned model card.
Source: https://huggingface.co/{config.upstream_model}/blob/{config.upstream_revision}/README.md
Retrieval UTC: {preparation['retrieved_at']}.
All retrieved model/tokenizer/card/config bytes are hashed in {PREPARATION}.
This task does not claim absence of upstream exposure to future benchmark data.

## Data and Labels

Manifest: `{MANIFEST_SHA256}`; verified before preparation and training.
BASE_TRAIN: {len(rows)}; class counts: {dict(Counter(r['canonical_label'] for r in rows))}.
Approved sources only: deepset Prompt Injection and Do-Not-Answer.
Labels follow the approved development constitution: benign/non-injection and
hard-benign risky/refusal = 0; direct injection attempt = 1. Harmful subject matter
alone is not an attack label. Original source text is preserved without metadata concatenation.
CALIBRATION used: NO. Protected data used: NO.
Outer partition metadata may be inspected only for integrity and lineage checks.

## Frozen Recipe

```json
{json.dumps(config.to_dict(), indent=2)}
```

Class weights = BASE_TRAIN_N / (2 * N_class): {class_weights(rows)}.
AdamW betas=(0.9,0.999), eps=1e-8; biases and LayerNorm weights have zero decay.
Total steps: {preparation['total_steps']}; linear warmup steps: {preparation['warmup_steps']}.
No early stopping, internal validation, search, calibration, or operating threshold optimization.
Fixed final checkpoint after three epochs. Seeded random binary head is expected:
upstream MLM head weights are discarded and classification head weights initialized.
All encoder and head parameters are trainable; actual backbone changes must be verified.

## Input and Output

Fast byte-level tokenizer; add model special tokens; dynamic padding within batches;
right truncation to 256 tokens. Truncation and full token count are reported at inference.
Raw score is softmax(logits)[1], so higher means greater adversarial-input risk.
calibrated_probability remains null. binary_vote uses raw_score >= 0.5, explicitly
DEFAULT_DEVELOPMENT_CUTPOINT. Batch latency is elapsed batch time divided by batch count.

## Reproducibility and Artifact Policy

Recipe: `{RECIPE}`; preparation: `{PREPARATION}`.
Preparation binds exact recipe bytes, source hashes, software versions, hardware and Git revision.
Current environment: `{json.dumps(preparation['packages'])}`.
Hardware: `{json.dumps(preparation['hardware'])}`.
Model cache is workspace-local and Git-ignored. Final artifact directory: `{OUTPUT}`.
Weights remain local; frozen project manifests/configuration/reports can be committed.
An existing preparation or trained artifact is never silently overwritten.
No artifact loader accepts preparation-only or partially trained models.

## Scientific Limitation

The narrow development corpus does not support comprehensive claims about
jailbreak families, indirect injection, agent/tool attacks, or adaptive attacks.
Future validation results will be DEVELOPMENT-ONLY, not E1-E10 or protected evaluation.
"""
    (REPORTS / "TECH_SEM_002_MODEL_FREEZE_v1.md").write_text(text, encoding="utf-8")


def prepare(device: str) -> None:
    if RECIPE.exists() or PREPARATION.exists() or OUTPUT.exists():
        raise RuntimeError("D_M-B preparation/artifact already exists; refusing overwrite")
    before = preserved_snapshot()
    rows = load_partition(MANIFEST, "BASE_TRAIN")
    info = HfApi(token=False).model_info(UPSTREAM_MODEL)
    revision = info.sha
    config = FineTunedConfig(upstream_model=UPSTREAM_MODEL, upstream_revision=revision, tokenizer_revision=revision, device=device)
    config.validate()
    deterministic(config)
    snapshot = Path(snapshot_download(
        UPSTREAM_MODEL, revision=revision, token=False,
        cache_dir="detection_service/.model-cache/dm_b_v1",
        local_dir=f"detection_service/.model-cache/dm_b_v1/snapshot-{revision}",
        allow_patterns=["config.json", "model.safetensors", "tokenizer.json", "tokenizer_config.json",
                        "special_tokens_map.json", "merges.txt", "vocab.json", "README.md", "LICENSE"],
    )).resolve()
    card = (snapshot / "README.md").read_text(encoding="utf-8")
    if "license: apache-2.0" not in card:
        raise RuntimeError("model card does not establish the expected Apache-2.0 license")
    files = {p.name: file_sha256(p) for p in snapshot.iterdir() if p.is_file()}
    preparation = {"snapshot_path": str(snapshot), "upstream_files_sha256": files}
    tokenizer, model = upstream(config, preparation)
    counts = Counter(int(r["canonical_label"]) for r in rows)
    preparation.update(
        status="PREPARED_NOT_TRAINED", upstream_model=UPSTREAM_MODEL, revision=revision,
        tokenizer_revision=revision, license="apache-2.0", model_card_url=f"https://huggingface.co/{UPSTREAM_MODEL}/blob/{revision}/README.md",
        retrieved_at=datetime.now(UTC).isoformat(), parameter_count=sum(p.numel() for p in model.parameters()),
        architecture=type(model).__name__, num_hidden_layers=model.config.num_hidden_layers,
        hidden_size=model.config.hidden_size, max_position_embeddings=model.config.max_position_embeddings,
        packages=packages(), hardware=hardware(), git=git_metadata(), manifest_sha256=MANIFEST_SHA256,
        base_train_count=len(rows), base_train_class_counts=dict(counts), class_weights=class_weights(rows),
        total_steps=math.ceil(len(rows) / config.batch_size) * config.epochs,
        calibration_used=False, protected_data_used=False,
        partition_membership_sha256=hashlib.sha256("\n".join(r["record_id"] for r in rows).encode()).hexdigest(),
        initialization_warning="Upstream MLM head discarded; binary classifier head initialized from seed 1701.",
    )
    preparation["warmup_steps"] = math.ceil(preparation["total_steps"] * config.warmup_ratio)
    write_json(RECIPE, config.to_dict())
    preparation["recipe_sha256"] = file_sha256(RECIPE)
    write_json(PREPARATION, preparation)
    freeze_report(config, preparation, rows)
    check_preserved(before)
    print(json.dumps({"status": "PREPARED_NOT_TRAINED", "revision": revision,
                      "parameters": preparation["parameter_count"], "device": config.device,
                      "total_steps": preparation["total_steps"]}, indent=2))


def read_preparation() -> tuple[FineTunedConfig, dict]:
    config = FineTunedConfig.from_dict(json.loads(RECIPE.read_text(encoding="utf-8")))
    preparation = json.loads(PREPARATION.read_text(encoding="utf-8"))
    if file_sha256(RECIPE) != preparation["recipe_sha256"] or config.upstream_revision != preparation["revision"]:
        raise RuntimeError("frozen recipe/revision integrity failure")
    if packages() != preparation["packages"]:
        raise RuntimeError("software environment differs from the frozen recipe; review before training")
    deterministic(config)
    return config, preparation


def synthetic_smoke() -> None:
    config, preparation = read_preparation()
    before = preserved_snapshot()
    tokenizer, model = upstream(config, preparation)
    initial = backbone_hash(model)
    optimizer = optimizer_for(model, config)
    texts = ["This is a synthetic engineering example for a meeting agenda. " * 80] * config.batch_size
    inputs = tokenizer(texts, padding=True, truncation=True, max_length=config.max_sequence_length, return_tensors="pt").to(config.device)
    labels = torch.tensor([i % 2 for i in range(config.batch_size)], device=config.device)
    model.train()
    started = time.perf_counter()
    logits = model(**inputs).logits
    loss = torch.nn.functional.cross_entropy(logits, labels)
    if not torch.isfinite(loss):
        raise RuntimeError("non-finite synthetic training loss")
    loss.backward()
    gradient_norm = torch.nn.utils.clip_grad_norm_(model.parameters(), config.gradient_clip, error_if_nonfinite=True)
    optimizer.step()
    if config.device == "cuda":
        torch.cuda.synchronize()
    seconds = time.perf_counter() - started
    changed = initial != backbone_hash(model)
    if not changed:
        raise RuntimeError("synthetic step failed to update the transformer")
    detector = FineTunedSemanticDetector(config, tokenizer, model)
    from detection_service.app.contracts.detection_request import DetectionRequest, DetectionContent
    request = DetectionRequest(request_id="synthetic", content=DetectionContent(type="user_prompt", text="Summarize the meeting agenda."))
    first, second = detector.detect(request), detector.detect(request)
    assert first.raw_score == second.raw_score and first.calibrated_probability is None
    check_preserved(before)
    evidence = {"status": "PASS_SYNTHETIC_ONLY", "device": config.device,
                "batch_size": config.batch_size, "tokens_per_example": int(inputs["input_ids"].shape[1]),
                "synthetic_loss": float(loss.detach()), "gradient_norm": float(gradient_norm),
                "transformer_parameters_updated": changed, "step_seconds": seconds,
                "estimated_max_length_training_minutes": seconds * preparation["total_steps"] / 60,
                "estimate_scope": "one worst-length synthetic step; estimate, not measured authoritative runtime",
                "deterministic_inference": True, "project_data_used": False,
                "authoritative_model_trained": False, "recipe_sha256": preparation["recipe_sha256"]}
    write_json(Path("artifacts/models/dm_b_v1_pipeline_smoke.json"), evidence)
    print(json.dumps(evidence, indent=2))


def fit_transformer(model, tokenizer, texts: list[str], labels: list[int], config: FineTunedConfig, weights: list[float]) -> list[dict]:
    optimizer = optimizer_for(model, config)
    total_steps = math.ceil(len(texts) / config.batch_size) * config.epochs
    scheduler = get_linear_schedule_with_warmup(optimizer, math.ceil(total_steps * config.warmup_ratio), total_steps)
    criterion = torch.nn.CrossEntropyLoss(weight=torch.tensor(weights, dtype=torch.float32, device=config.device))
    generator = torch.Generator().manual_seed(config.seed)
    history = []
    for epoch in range(config.epochs):
        model.train()
        order = torch.randperm(len(texts), generator=generator).tolist()
        numerator, denominator, batches = 0.0, 0.0, 0
        for start in range(0, len(order), config.batch_size):
            indices = order[start:start + config.batch_size]
            inputs = tokenizer([texts[i] for i in indices], add_special_tokens=True, padding=True,
                               truncation=True, max_length=config.max_sequence_length, return_tensors="pt").to(config.device)
            target = torch.tensor([labels[i] for i in indices], dtype=torch.long, device=config.device)
            optimizer.zero_grad(set_to_none=True)
            loss = criterion(model(**inputs).logits, target)
            if not torch.isfinite(loss):
                raise RuntimeError("STOP: non-finite authoritative training loss")
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), config.gradient_clip, error_if_nonfinite=True)
            optimizer.step()
            scheduler.step()
            batch_weight = sum(weights[labels[i]] for i in indices)
            numerator += float(loss.detach()) * batch_weight
            denominator += batch_weight
            batches += 1
        history.append({"epoch": epoch + 1, "batches": batches, "weighted_mean_loss": numerator / denominator,
                        "learning_rate_after_epoch": scheduler.get_last_lr()[0]})
        print(json.dumps(history[-1]), flush=True)
    return history


def api_smoke(detector) -> dict:
    from fastapi.testclient import TestClient
    from detection_service.app.main import create_app
    payload = {"request_id": "dm-b-smoke", "content": {"type": "user_prompt", "text": "Summarize our engineering meeting."}}
    with TestClient(create_app(detector_factory=lambda: detector)) as client:
        first = client.post("/v1/detect/input", json=payload)
        second = client.post("/v1/detect/input", json=payload)
    assert first.status_code == second.status_code == 200
    a, b = first.json()["detectors"][0], second.json()["detectors"][0]
    assert a["raw_score"] == b["raw_score"] and a["calibrated_probability"] is None
    assert a["detector_version"] == "dm_b_v1" and 0 <= a["raw_score"] <= 1 and a["latency_ms"] > 0
    return {"status": "PASS", "deterministic": True, "result": a}


def train_once() -> None:
    if OUTPUT.exists():
        raise RuntimeError("D_M-B output already exists; refusing training rerun or checkpoint replacement")
    config, preparation = read_preparation()
    rows = load_partition(MANIFEST, "BASE_TRAIN")
    weights = class_weights(rows)
    if weights != preparation["class_weights"]:
        raise RuntimeError("BASE_TRAIN weights differ from frozen preparation")
    before = preserved_snapshot()
    texts, sources = load_texts(rows, Path.cwd(), "BASE_TRAIN")
    tokenizer, model = upstream(config, preparation)
    original = backbone_hash(model)
    OUTPUT.mkdir(parents=True)
    started_at, started = datetime.now(UTC).isoformat(), time.perf_counter()
    write_json(OUTPUT / "run_state.json", {"status": "TRAINING", "started_at": started_at, "recipe_sha256": file_sha256(RECIPE)})
    history = fit_transformer(model, tokenizer, texts, [int(r["canonical_label"]) for r in rows], config, weights)
    duration = time.perf_counter() - started
    final = backbone_hash(model)
    if final == original:
        raise RuntimeError("STOP: transformer weights were not fine-tuned")
    check_preserved(before)
    model.eval()
    model.save_pretrained(OUTPUT / "transformer", safe_serialization=True)
    tokenizer.save_pretrained(OUTPUT / "transformer")
    write_json(OUTPUT / "model_config.json", {"recipe": config.to_dict(), "training_status": "COMPLETE",
               "label_mapping": {"benign": 0, "attack": 1}, "calibrated_probability": None})
    metadata = {"phase": "TECH-SEM-002", "status": "TRAINED_RAW_MODEL_FROZEN",
                "command": " ".join([sys.executable, "-m", "detection_service.scripts.train_semantic_finetuned", "--mode", "train"]),
                "started_at": started_at, "ended_at": datetime.now(UTC).isoformat(), "runtime_seconds": duration,
                "recipe": config.to_dict(), "recipe_sha256": file_sha256(RECIPE), "git": git_metadata(),
                "packages": packages(), "hardware": hardware(), "base_train_count": len(rows),
                "class_counts": dict(Counter(r["canonical_label"] for r in rows)), "class_weights": weights,
                "source_artifact_sha256": sources, "preparation_sha256": file_sha256(PREPARATION),
                "initial_backbone_sha256": original, "final_backbone_sha256": final,
                "transformer_parameters_updated": True, "loss_history": history,
                "calibration_used": False, "protected_data_used": False, "validation_used_for_training": False,
                "initialization_warning": preparation["initialization_warning"], "preserved_artifacts_sha256": before}
    write_json(OUTPUT / "training_metadata.json", metadata)
    integrity = {str(p.relative_to(OUTPUT)).replace(chr(92), "/"): file_sha256(p)
                 for p in (OUTPUT / "transformer").iterdir() if p.is_file()}
    integrity["model_config.json"] = file_sha256(OUTPUT / "model_config.json")
    write_json(OUTPUT / "integrity_manifest.json", integrity)
    detector = FineTunedSemanticDetector.from_artifact(OUTPUT)
    smoke = api_smoke(detector)
    write_json(OUTPUT / "service_smoke.json", smoke)
    # The final artifact is frozen before VALIDATION text is reconstructed.
    write_json(OUTPUT / "validation_started.json", {"started_at": datetime.now(UTC).isoformat(), "checkpoint_policy": config.checkpoint_policy})
    validation_rows = load_partition(MANIFEST, "VALIDATION")
    validation_texts, validation_sources = load_texts(validation_rows, Path.cwd(), "VALIDATION")
    from detection_service.app.contracts.detection_request import DetectionContent, DetectionRequest
    requests = [DetectionRequest(request_id=r["record_id"], content=DetectionContent(type="user_prompt", text=t))
                for r, t in zip(validation_rows, validation_texts)]
    probabilities = np.array([r.raw_score for r in detector.detect_batch(requests)])
    metrics = evaluate_validation(validation_rows, probabilities, 0.5)
    metrics.update(scope="DEVELOPMENT-ONLY VALIDATION; NOT E1-E10", source_artifact_sha256=validation_sources)
    write_json(OUTPUT / "validation_metrics.json", metrics)
    for name, digest in integrity.items():
        if file_sha256(OUTPUT / name) != digest:
            raise RuntimeError("frozen D_M-B artifact changed during validation")
    check_preserved(before)
    write_json(OUTPUT / "run_state.json", {"status": "TRAINING_AND_VALIDATION_COMPLETE", "ended_at": datetime.now(UTC).isoformat()})
    (REPORTS / "TECH_SEM_002_TRAINING_REPORT_v1.md").write_text(
        "# TECH-SEM-002 Training Report v1\n\nTraining: COMPLETE. BASE_TRAIN only.\n\n```json\n" + json.dumps(metadata, indent=2) + "\n```\n\nAll model layers updated. Fixed final checkpoint; no validation-driven selection.\n", encoding="utf-8")
    (REPORTS / "TECH_SEM_002_VALIDATION_REPORT_v1.md").write_text(
        "# TECH-SEM-002 DEVELOPMENT-ONLY VALIDATION\n\n233 rows; final frozen checkpoint; raw-score cutpoint 0.5.\n\n```json\n" + json.dumps(metrics, indent=2) + "\n```\n\nThese results are not E1-E10 and are not protected evaluation results.\nThe approved development corpus is narrow; no comprehensive attack-taxonomy claim.\nCALIBRATION was not consumed. No retraining or threshold optimization follows.\n", encoding="utf-8")
    report = REPORTS / "TECH_SEM_002_MODEL_FREEZE_v1.md"
    report.write_text(report.read_text(encoding="utf-8").replace(
        "RECIPE_FROZEN; AUTHORITATIVE_TRAINING_PENDING", "TRAINED_RAW_MODEL_FROZEN"
    ), encoding="utf-8")
    # Completion status is gated on actual regression evidence, not training alone.
    evidence_path = Path("artifacts/models/dm_b_v1_test_evidence.json")
    if evidence_path.exists():
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
        current_sources = {str(p).replace(chr(92), "/"): file_sha256(p) for p in
                           list(Path("detection_service/app").rglob("*.py")) +
                           list(Path("detection_service/scripts").glob("*.py")) +
                           list(Path("detection_service/tests").glob("*.py"))}
        if evidence.get("failed") == 0 and evidence.get("source_sha256") == current_sources:
            (REPORTS / "TECH_IMPLEMENTATION_STATUS_v5.md").write_text(
                "# TECH IMPLEMENTATION STATUS v5\n\nTECH-SEM-002: PASS.\n\n"
                "D_M-B dm_b_v1 trained end to end on 1,135 BASE_TRAIN rows only.\n"
                "Final checkpoint frozen and reloaded; one 233-row DEVELOPMENT-ONLY VALIDATION run.\n"
                "CALIBRATION/protected data consumed: NO. E1-E10 executed: NO.\n"
                "Raw score available; calibrated_probability null; default raw cutpoint 0.5.\n"
                "D_M-A classifier and calibration and D_S preserved by byte hashes and regression tests.\n"
                "Real final-model API smoke and deterministic inference PASS.\n"
                "Regression evidence: artifacts/models/dm_b_v1_test_evidence.json.\n"
                "Scope remains narrow direct-injection development; no comprehensive taxonomy claim.\n\n"
                "Recommendation: READY FOR TECH-SEM-002-CALIBRATION.\n", encoding="utf-8")
            with (REPORTS / "TECH_SEM_002_TEST_REPORT_v1.md").open("a", encoding="utf-8") as handle:
                handle.write("\n## Final Authoritative Artifact Verification\n\n"
                             "Actual trained dm_b_v1 save/reload, real-model API smoke and repeated eval-mode predictions PASS.\n"
                             "All D_M-A/D_S hashes remain unchanged. Training and validation are complete; v5 status is now emitted.\n")
    print(json.dumps({"status": "TRAINING_AND_VALIDATION_COMPLETE", "artifact": str(OUTPUT),
                      "runtime_seconds": duration, "metrics": metrics}, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["prepare", "smoke", "train"], required=True)
    parser.add_argument("--device", choices=["cpu", "cuda"], default="cpu", help="preparation only; later modes use frozen recipe")
    args = parser.parse_args()
    try:
        if args.mode == "prepare":
            prepare(args.device)
        elif args.mode == "smoke":
            synthetic_smoke()
        else:
            train_once()
    except Exception as exc:
        if args.mode == "train" and OUTPUT.exists():
            state_path = OUTPUT / "run_state.json"
            state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}
            if state.get("status") == "TRAINING":
                write_json(state_path, {**state, "status": "FAILED_STOP_FOR_REVIEW", "error": str(exc),
                                       "ended_at": datetime.now(UTC).isoformat()})
        raise


if __name__ == "__main__":
    main()
