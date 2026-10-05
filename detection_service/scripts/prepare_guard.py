"""Freeze an already downloaded, exact-revision local guard snapshot; never download."""
from __future__ import annotations

import json
import os
import platform
import subprocess
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

import torch

from detection_service.app.detectors.guard.config import GuardConfig
from detection_service.app.detectors.guard.model import UPSTREAM_FILES, load_frozen, sha256

ROOT = Path(__file__).resolve().parents[2]


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=True) + "\n", encoding="utf-8", newline="\n")


def main():
    cfg = GuardConfig()
    artifact = ROOT / "artifacts/models/dg_v1"
    snapshot = ROOT / f"detection_service/.model-cache/dg_v1/snapshot-{cfg.revision}"
    if (artifact / "freeze_metadata.json").exists():
        raise RuntimeError("Guard freeze already exists; refusing to overwrite")
    hashes = {name: sha256(snapshot / name) for name in UPSTREAM_FILES}
    raw_config = json.loads((snapshot / "config.json").read_text(encoding="utf-8"))
    if raw_config["hidden_size"] != 384 or raw_config["num_hidden_layers"] != 12:
        raise RuntimeError("Unexpected pinned guard dimensions")
    access = json.loads((ROOT / "detection_service/outputs/guard_access_continuation.json").read_text(encoding="utf-8"))
    if access["status"] != "ACCESS_PASS" or access["revision"] != cfg.revision:
        raise RuntimeError("Missing authorized pinned access evidence")
    frozen = {
        "project_model": "D_G", "project_version": "dg_v1", "provider": "Meta",
        "model_id": cfg.model_id, "revision": cfg.revision, "tokenizer_revision": cfg.tokenizer_revision,
        "snapshot_path": snapshot.relative_to(ROOT).as_posix(), "file_sha256": hashes,
        "architecture": "DebertaV2ForSequenceClassification", "parameter_count": 70830722,
        "backbone_including_embeddings_parameter_count": 70682112,
        "context_tokens": 512, "serialized_id2label": {"0": "LABEL_0", "1": "LABEL_1"},
        "documented_class_meaning": {"0": "benign", "1": "malicious_instruction_override_attempt"},
        "score_orientation": "Higher class-1 softmax means higher upstream malicious risk",
        "label_evidence": "https://raw.githubusercontent.com/meta-llama/llama-cookbook/3c106f3e6ee79d6df51ae706bc7ef2d734ec3ded/getting-started/responsible_ai/prompt_guard/inference.py",
        "label_evidence_commit": "3c106f3e6ee79d6df51ae706bc7ef2d734ec3ded",
        "label_evidence_sha256": "29afa64415b07811c22b3c2e27330ee40f9e8edff0a7faf4940b8cfc1c74d424",
        "label_evidence_note": "Provider helper get_jailbreak_score returns softmax class 1 at temperature 1; serialized config labels are generic",
        "license": "Llama 4 Community License Agreement; Acceptable Use Policy applies",
        "license_note": "Authorized gated access; no legal clearance or redistribution authorization asserted",
        "retrieval_and_freeze_date_utc": datetime.now(timezone.utc).isoformat(),
        "source_repository_git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "authenticated_access": {"status": "PASS", "user": access["authenticated_user"]},
        "dependencies": {name: version(name) for name in ("torch", "transformers", "huggingface-hub", "tokenizers", "safetensors", "numpy", "pytest")},
        "hardware": {"os": platform.platform(), "python": platform.python_version(), "logical_cpus": os.cpu_count(),
                     "torch_cuda_available": torch.cuda.is_available(), "torch_runtime": torch.__version__,
                     "execution_device": "cpu", "dtype": "float32"},
        "tokenizer": {"type": "DebertaV2TokenizerFast", "specials": {"cls": 1, "sep": 2, "pad": 0},
                      "model_max_length_note": "Unbounded sentinel ignored; model context 512 is authoritative",
                      "normalization": "Unmodified upstream Strip/precompiled/space removal/NFKC normalizer; preserved by tokenizer.json hash"},
        "training_performed": False, "fine_tuning_performed": False,
        "project_data_used": False, "protected_data_used": False,
        "project_calibration": None, "default_decision": cfg.decision,
        "long_input_policy": cfg.to_dict(), "upstream_training_overlap": "UNKNOWN",
    }
    artifact.mkdir(parents=True, exist_ok=True)
    write_json(artifact / "model_config.json", cfg.to_dict())
    write_json(artifact / "freeze_metadata.json", frozen)
    write_json(artifact / "integrity_manifest.json", {name: sha256(artifact / name) for name in ("model_config.json", "freeze_metadata.json")})
    torch.set_num_threads(8)
    _, model, _, _ = load_frozen(artifact, ROOT)
    if model.training or any(p.requires_grad for p in model.parameters()):
        raise RuntimeError("Guard must remain frozen and in eval mode")
    print(json.dumps({"status": "FROZEN_LOAD_PASS", "parameters": frozen["parameter_count"], "hashes": hashes}, indent=2))


if __name__ == "__main__":
    main()
