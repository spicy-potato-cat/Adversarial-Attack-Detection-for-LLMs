from __future__ import annotations

import re
from dataclasses import asdict, dataclass


MANIFEST_SHA256 = "9cdd5ecdd80f9ac3c8f05db63742721f4537ca2b64a2fe48f6c2b424b57483a6"
UPSTREAM_MODEL = "distilbert/distilroberta-base"


@dataclass(frozen=True)
class FineTunedConfig:
    upstream_model: str
    upstream_revision: str
    tokenizer_revision: str
    detector_id: str = "semantic_finetuned"
    detector_version: str = "dm_b_v1"
    max_sequence_length: int = 256
    model_context_length: int = 512
    seed: int = 1701
    epochs: int = 3
    batch_size: int = 8
    gradient_accumulation: int = 1
    learning_rate: float = 2e-5
    weight_decay: float = 0.01
    warmup_ratio: float = 0.1
    gradient_clip: float = 1.0
    optimizer: str = "AdamW"
    scheduler: str = "linear"
    loss: str = "weighted_cross_entropy"
    class_weight_policy: str = "BASE_TRAIN_N/(2*N_class)"
    checkpoint_policy: str = "final_epoch_only_no_validation_selection"
    precision: str = "float32"
    device: str = "cpu"
    cpu_threads: int = 8
    default_cutpoint: float = 0.5
    manifest_sha256: str = MANIFEST_SHA256
    text_field: str = "source.raw_text"
    truncation_side: str = "right"
    padding_side: str = "right"
    padding: str = "longest_in_batch"

    def validate(self) -> None:
        if self.upstream_model != UPSTREAM_MODEL:
            raise ValueError("unapproved D_M-B upstream model")
        if not re.fullmatch(r"[0-9a-f]{40}", self.upstream_revision):
            raise ValueError("D_M-B requires an immutable model commit")
        if self.tokenizer_revision != self.upstream_revision:
            raise ValueError("tokenizer revision must match the frozen model revision")
        if self.detector_id != "semantic_finetuned" or self.detector_version != "dm_b_v1":
            raise ValueError("D_M-B version identity mismatch")
        if self.manifest_sha256 != MANIFEST_SHA256:
            raise ValueError("D_M-B manifest identity mismatch")
        if not 2 <= self.max_sequence_length <= self.model_context_length == 512:
            raise ValueError("D_M-B sequence/context length is invalid")
        if self.device not in {"cpu", "cuda"} or self.precision != "float32":
            raise ValueError("unsupported D_M-B device or precision")
        if self.batch_size < 1 or self.epochs < 1 or self.cpu_threads < 1:
            raise ValueError("batch size, epochs and thread count must be positive")
        if self.gradient_accumulation != 1 or self.optimizer != "AdamW" or self.scheduler != "linear":
            raise ValueError("unsupported D_M-B optimizer/scheduler recipe")
        if self.learning_rate <= 0 or self.weight_decay < 0 or not 0 <= self.warmup_ratio < 1:
            raise ValueError("invalid D_M-B optimizer settings")
        if self.gradient_clip <= 0 or self.default_cutpoint != 0.5:
            raise ValueError("invalid gradient clip or development cutpoint")
        if (self.loss, self.class_weight_policy, self.checkpoint_policy) != (
            "weighted_cross_entropy", "BASE_TRAIN_N/(2*N_class)", "final_epoch_only_no_validation_selection"
        ):
            raise ValueError("unsupported D_M-B loss/checkpoint recipe")
        if (self.text_field, self.truncation_side, self.padding_side, self.padding) != (
            "source.raw_text", "right", "right", "longest_in_batch"
        ):
            raise ValueError("unsupported D_M-B preprocessing")

    def to_dict(self) -> dict:
        self.validate()
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict) -> "FineTunedConfig":
        value = cls(**payload)
        value.validate()
        return value
