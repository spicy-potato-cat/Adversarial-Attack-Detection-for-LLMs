from __future__ import annotations

import hashlib
import json
from pathlib import Path

import torch

from .config import GuardConfig

UPSTREAM_FILES = (
    "config.json", "LICENSE", "model.safetensors", "MODEL_CARD.md", "README.md",
    "special_tokens_map.json", "tokenizer.json", "tokenizer_config.json", "USE_POLICY.md",
)


class GuardUnavailableError(RuntimeError):
    """Frozen guard cannot be loaded or cannot produce a valid result."""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def contained_path(root: Path, relative: str) -> Path:
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError("Guard artifact path escapes workspace")
    return path


def load_frozen(artifact: Path, workspace: Path, device: str = "cpu"):
    try:
        artifact = artifact.resolve()
        if not artifact.is_relative_to(workspace.resolve()):
            raise ValueError("Guard freeze directory must be inside workspace")
        integrity = json.loads((artifact / "integrity_manifest.json").read_text(encoding="utf-8"))
        if set(integrity) != {"model_config.json", "freeze_metadata.json"}:
            raise ValueError("Unexpected guard integrity manifest")
        for name, digest in integrity.items():
            if sha256(artifact / name) != digest:
                raise ValueError(f"Guard freeze hash mismatch: {name}")
        config = GuardConfig.from_dict(json.loads((artifact / "model_config.json").read_text(encoding="utf-8")))
        freeze = json.loads((artifact / "freeze_metadata.json").read_text(encoding="utf-8"))
        if freeze["model_id"] != config.model_id or freeze["revision"] != config.revision:
            raise ValueError("Guard revision mismatch")
        if freeze["tokenizer_revision"] != config.tokenizer_revision:
            raise ValueError("Guard tokenizer revision mismatch")
        snapshot = contained_path(workspace, freeze["snapshot_path"])
        if set(freeze["file_sha256"]) != set(UPSTREAM_FILES):
            raise ValueError("Incomplete guard snapshot hash inventory")
        for name, digest in freeze["file_sha256"].items():
            if sha256(snapshot / name) != digest:
                raise ValueError(f"Guard snapshot hash mismatch: {name}")
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        tokenizer = AutoTokenizer.from_pretrained(
            snapshot, local_files_only=True, use_fast=True, trust_remote_code=False,
        )
        model, info = AutoModelForSequenceClassification.from_pretrained(
            snapshot, local_files_only=True, use_safetensors=True, trust_remote_code=False,
            output_loading_info=True,
        )
        if any(info.get(key) for key in ("missing_keys", "unexpected_keys", "mismatched_keys", "error_msgs")):
            raise ValueError("Incomplete or incompatible guard weights")
        if type(model).__name__ != freeze["architecture"] or model.config.num_labels != 2:
            raise ValueError("Guard architecture or output mismatch")
        if sum(p.numel() for p in model.parameters()) != freeze["parameter_count"]:
            raise ValueError("Guard parameter count mismatch")
        if model.config.max_position_embeddings != config.context_tokens:
            raise ValueError("Guard context mismatch")
        if model.config.id2label != {0: "LABEL_0", 1: "LABEL_1"}:
            raise ValueError("Unexpected serialized guard labels")
        if type(tokenizer).__name__ != "DebertaV2TokenizerFast" or not tokenizer.is_fast:
            raise ValueError("Unexpected guard tokenizer")
        if tokenizer.num_special_tokens_to_add(pair=False) != config.special_tokens:
            raise ValueError("Guard special-token budget mismatch")
        if tokenizer.build_inputs_with_special_tokens([3]) != [1, 3, 2] or tokenizer.pad_token_id != 0:
            raise ValueError("Unexpected guard special-token IDs")
        model = model.to(device=device, dtype=torch.float32)
        model.eval()
        model.requires_grad_(False)
        return config, model, tokenizer, freeze
    except Exception as exc:
        raise GuardUnavailableError(f"Frozen D_G unavailable: {type(exc).__name__}: {exc}") from exc
