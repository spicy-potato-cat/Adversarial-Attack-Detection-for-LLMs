from __future__ import annotations

from itertools import islice
from pathlib import Path
from threading import RLock
from time import perf_counter

import torch

from ...contracts.detection_request import DetectionRequest
from ...contracts.detector_result import DetectorResult, InputCoverage, ModelMetadata
from ..base import BaseDetector
from .config import GuardConfig
from .model import GuardUnavailableError, load_frozen


def chunk_spans(token_count: int, chunk_tokens: int = 510, overlap_tokens: int = 64):
    if token_count < 0 or not 0 <= overlap_tokens < chunk_tokens:
        raise ValueError("Invalid guard chunk dimensions")
    start = 0
    while start < token_count:
        end = min(start + chunk_tokens, token_count)
        yield start, end
        if end == token_count:
            break
        start += chunk_tokens - overlap_tokens


class GuardDetector(BaseDetector):
    """External frozen guard; injected components are for engineering fixtures only."""

    def __init__(self, model, tokenizer, config: GuardConfig | None = None, *, device="cpu"):
        self.config = config or GuardConfig()
        self.model = model.to(device=device, dtype=torch.float32).eval()
        self.model.requires_grad_(False)
        self.tokenizer = tokenizer
        self.device = device
        self._lock = RLock()

    @classmethod
    def from_artifact(cls, artifact=None, *, workspace=None, device="cpu"):
        root = Path(workspace or Path(__file__).resolve().parents[4]).resolve()
        artifact = Path(artifact or root / "artifacts/models/dg_v1")
        config, model, tokenizer, _ = load_frozen(artifact, root, device)
        return cls(model, tokenizer, config, device=device)

    def detect(self, request: DetectionRequest) -> DetectorResult:
        started = perf_counter()
        try:
            with self._lock, torch.inference_mode():
                return self._detect(request, started)
        except GuardUnavailableError:
            raise
        except Exception as exc:
            raise GuardUnavailableError(f"D_G inference failed: {type(exc).__name__}: {exc}") from exc

    def _detect(self, request, started):
        cfg = self.config
        # Preserve upstream tokenization, then slice IDs without decode/re-encode loss.
        text = request.content.text
        text.encode("utf-8", errors="strict")
        ids = self.tokenizer.encode(text, add_special_tokens=False, truncation=False)
        count = len(ids)
        base = dict(
            detector_id=cfg.detector_id, detector_version=cfg.detector_version,
            model=ModelMetadata(model_id=cfg.model_id, model_revision=cfg.revision,
                                tokenizer_id=cfg.model_id, device=str(self.device)),
            calibrated_probability=None, warnings=[],
        )
        metadata = {
            "original_token_count": count, "token_count_basis": "upstream_content_tokens_without_specials",
            "context_limit": cfg.context_tokens, "special_tokens_per_chunk": cfg.special_tokens,
            "chunk_size": cfg.chunk_tokens, "overlap": cfg.overlap_tokens, "stride": cfg.stride,
            "aggregation": cfg.aggregation, "decision_rule": cfg.decision,
            "decision_scope": "DEFAULT MODEL DECISION; NOT FINAL THRESHOLD",
            "positive_class": 1, "score_semantics": "temperature_1_softmax_class_1; max_across_chunks",
            "tokenizer_revision": cfg.tokenizer_revision, "truncated": False,
            "long_input_used": count > cfg.chunk_tokens,
        }
        if not count:
            return DetectorResult(**{**base, "warnings": ["Upstream tokenizer produced no content tokens"]},
                                  status="insufficient_input", latency_ms=(perf_counter() - started) * 1000,
                                  metadata={**metadata, "number_of_chunks": 0})
        spans = iter(chunk_spans(count, cfg.chunk_tokens, cfg.overlap_tokens))
        best_score, best_index, best_span, chunks, vote, tail = -1.0, None, None, 0, False, 0
        while batch_spans := list(islice(spans, cfg.batch_size)):
            records = []
            for start, end in batch_spans:
                chunk = self.tokenizer.build_inputs_with_special_tokens(ids[start:end])
                if len(chunk) != end - start + cfg.special_tokens or len(chunk) > cfg.context_tokens:
                    raise GuardUnavailableError("Invalid special-token or context accounting")
                records.append({"input_ids": chunk, "attention_mask": [1] * len(chunk)})
            inputs = self.tokenizer.pad(records, padding=True, return_tensors="pt")
            inputs = {key: value.to(self.device) for key, value in inputs.items()}
            self.model.eval()
            logits = self.model(**inputs).logits
            if tuple(logits.shape) != (len(records), 2) or not torch.isfinite(logits).all():
                raise GuardUnavailableError("Guard produced invalid binary logits")
            scores = logits.float().softmax(dim=-1)[:, 1].cpu().tolist()
            decisions = logits.argmax(dim=-1).cpu().tolist()
            for span, score, decision in zip(batch_spans, scores, decisions):
                if not 0 <= score <= 1:
                    raise GuardUnavailableError("Guard produced invalid probability")
                if score > best_score:
                    best_score, best_index, best_span = score, chunks, span
                vote = vote or decision == cfg.positive_class
                chunks += 1
                tail = span[1]
        metadata.update(number_of_chunks=chunks, max_risk_chunk_index=best_index,
                        max_risk_chunk_span=list(best_span), aggregate_score=best_score,
                        final_tail_end=tail, tail_covered=tail == count)
        return DetectorResult(
            **base, status="success", raw_score=best_score, binary_vote=bool(vote),
            latency_ms=(perf_counter() - started) * 1000, metadata=metadata,
            input_coverage=InputCoverage(
                input_tokens=count, scoreable_tokens=count, tokens_analyzed=count, tokens_excluded=0,
                coverage_ratio=1.0, truncated=False, inference_chunks=chunks,
                model_context_tokens=cfg.context_tokens, window_size=cfg.chunk_tokens, window_stride=cfg.stride,
            ),
        )
