from dataclasses import dataclass, field
from threading import Lock
from typing import Any

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from detection_service.app.detectors.statistical.config import PerplexityConfig


class PerplexityEngineError(RuntimeError):
    pass


class DeviceUnavailableError(PerplexityEngineError):
    pass


@dataclass
class TokenDiagnostic:
    position: int
    token_id: int
    token: str
    surprisal: float


@dataclass
class InferenceEvidence:
    surprisals: list[float]
    input_tokens: int
    tokens_analyzed: int
    truncated: bool
    inference_chunks: int
    model_context_tokens: int
    warnings: list[str] = field(default_factory=list)
    token_diagnostics: list[TokenDiagnostic] | None = None


class PerplexityEngine:
    load_count = 0

    def __init__(
        self,
        config: PerplexityConfig,
        tokenizer: Any | None = None,
        model: Any | None = None,
    ) -> None:
        config.validate()
        self.config = config
        self._lock = Lock()
        if config.device.startswith("cuda") and not torch.cuda.is_available():
            raise DeviceUnavailableError(f"configured device is unavailable: {config.device}")
        try:
            self.tokenizer = tokenizer or AutoTokenizer.from_pretrained(
                config.tokenizer_id,
                revision=config.model_revision,
            )
            self.model = model or AutoModelForCausalLM.from_pretrained(
                config.model_id,
                revision=config.model_revision,
            )
            if model is None:
                type(self).load_count += 1
            self.model.to(config.device)
            self.model.eval()
        except DeviceUnavailableError:
            raise
        except Exception as exc:
            raise PerplexityEngineError("reference model initialization failed") from exc
        self.model_context_tokens = self._resolve_context_limit()

    def _resolve_context_limit(self) -> int:
        limits = []
        tokenizer_limit = getattr(self.tokenizer, "model_max_length", None)
        if isinstance(tokenizer_limit, int) and 1 < tokenizer_limit < 1_000_000:
            limits.append(tokenizer_limit)
        model_config = getattr(self.model, "config", None)
        for name in ("max_position_embeddings", "n_positions", "n_ctx"):
            value = getattr(model_config, name, None)
            if isinstance(value, int) and value > 1:
                limits.append(value)
        if not limits:
            raise PerplexityEngineError("reference model context length is unavailable")
        return min(limits)

    def _tokenize(self, text: str) -> torch.Tensor:
        try:
            encoded = self.tokenizer(
                text,
                add_special_tokens=False,
                return_tensors="pt",
                truncation=False,
            )
            input_ids = encoded["input_ids"]
            if input_ids.ndim != 2 or input_ids.shape[0] != 1:
                raise ValueError("tokenizer returned an unexpected input shape")
            return input_ids
        except Exception as exc:
            raise PerplexityEngineError("tokenization failed") from exc

    def _score_chunk(
        self,
        input_ids: torch.Tensor,
        global_start: int,
        keep_from: int,
        include_diagnostics: bool,
    ) -> tuple[list[float], list[TokenDiagnostic]]:
        if input_ids.shape[1] < 2:
            return [], []
        try:
            with self._lock, torch.inference_mode():
                outputs = self.model(input_ids=input_ids.to(self.config.device))
                shift_logits = outputs.logits[:, :-1, :]
                shift_labels = input_ids[:, 1:].to(self.config.device)
                log_probabilities = torch.log_softmax(shift_logits, dim=-1)
                values = -log_probabilities.gather(2, shift_labels.unsqueeze(-1)).squeeze(-1)
                values = values[0].detach().cpu().tolist()
        except Exception as exc:
            raise PerplexityEngineError("model inference failed") from exc

        kept = []
        diagnostics = []
        target_ids = input_ids[0, 1:].tolist()
        for offset, (token_id, surprisal) in enumerate(zip(target_ids, values), start=1):
            position = global_start + offset
            if position < keep_from:
                continue
            score = float(surprisal)
            kept.append(score)
            if include_diagnostics:
                token = self.tokenizer.convert_ids_to_tokens(int(token_id))
                diagnostics.append(TokenDiagnostic(position, int(token_id), str(token), score))
        return kept, diagnostics

    def score(self, text: str, include_diagnostics: bool = False) -> InferenceEvidence:
        input_ids = self._tokenize(text)
        input_tokens = int(input_ids.shape[1])
        analysis_tokens = min(input_tokens, self.config.max_analysis_tokens)
        truncated = analysis_tokens < input_tokens
        warnings = []
        if truncated:
            warnings.append("INPUT_TRUNCATED_TO_CONFIGURED_MAX_ANALYSIS_TOKENS")
        if analysis_tokens < 2:
            warnings.append("TOO_SHORT_TO_SCORE_NEXT_TOKEN_PROBABILITY")
            return InferenceEvidence(
                surprisals=[],
                input_tokens=input_tokens,
                tokens_analyzed=0,
                truncated=truncated,
                inference_chunks=0,
                model_context_tokens=self.model_context_tokens,
                warnings=warnings,
                token_diagnostics=[] if include_diagnostics else None,
            )

        selected_ids = input_ids[:, :analysis_tokens]
        surprisals = []
        diagnostics = []
        chunks = 0
        chunk_start = 0
        keep_from = 1
        overlap = min(self.config.window_stride, self.model_context_tokens - 1)
        while keep_from < analysis_tokens:
            chunk_end = min(chunk_start + self.model_context_tokens, analysis_tokens)
            chunk_scores, chunk_diagnostics = self._score_chunk(
                selected_ids[:, chunk_start:chunk_end],
                global_start=chunk_start,
                keep_from=keep_from,
                include_diagnostics=include_diagnostics,
            )
            surprisals.extend(chunk_scores)
            diagnostics.extend(chunk_diagnostics)
            chunks += 1
            keep_from = chunk_end
            if chunk_end == analysis_tokens:
                break
            chunk_start = chunk_end - overlap

        return InferenceEvidence(
            surprisals=surprisals,
            input_tokens=input_tokens,
            tokens_analyzed=len(surprisals),
            truncated=truncated,
            inference_chunks=chunks,
            model_context_tokens=self.model_context_tokens,
            warnings=warnings,
            token_diagnostics=diagnostics if include_diagnostics else None,
        )

