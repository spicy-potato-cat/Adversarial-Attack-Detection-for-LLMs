from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class SurfaceAnomalyFeatures(BaseModel):
    non_ascii_ratio: float
    punctuation_ratio: float
    zero_width_count: int
    longest_token_ratio: float
    single_character_token_ratio: float
    character_entropy: float


class StatisticalFeatures(BaseModel):
    whole_prompt_nll: float | None
    whole_prompt_ppl: float | None
    global_perplexity: float | None
    window_count: int
    mean_window_perplexity: float | None
    max_window_perplexity: float | None
    std_window_perplexity: float | None
    mean_surprisal: float | None
    max_surprisal: float | None
    surprisal_std: float | None
    high_surprisal_ratio: float | None
    surface_anomaly: SurfaceAnomalyFeatures | None = None


class SemanticFeatures(BaseModel):
    embedding_dim: int
    embedding_model_id: str
    embedding_model_revision: str
    normalized_embeddings: bool
    classifier_type: str
    classifier_version: str


class InputCoverage(BaseModel):
    input_tokens: int
    scoreable_tokens: int
    tokens_analyzed: int
    tokens_excluded: int
    coverage_ratio: float
    truncated: bool
    inference_chunks: int
    model_context_tokens: int
    window_strategy: Literal["sliding"] = "sliding"
    window_size: int
    window_stride: int


class ModelMetadata(BaseModel):
    model_id: str
    model_revision: str
    tokenizer_id: str
    device: str


class DetectorResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    detector_id: str
    detector_version: str
    status: Literal["success", "insufficient_input", "unavailable", "not_trained"]
    raw_score: float | None = None
    calibrated_probability: float | None = None
    binary_vote: bool | None = None
    features: StatisticalFeatures | None = None
    semantic_features: SemanticFeatures | None = None
    input_coverage: InputCoverage | None = None
    model: ModelMetadata
    latency_ms: float
    warnings: list[str]
    metadata: dict[str, Any] = Field(default_factory=dict)


class DetectionResponse(BaseModel):
    request_id: str
    pipeline_version: str
    detectors: list[DetectorResult]
