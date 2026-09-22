import math

from detection_service.app.contracts.detection_request import DetectionContent, DetectionRequest
from detection_service.app.detectors.statistical.config import PerplexityConfig
from detection_service.app.detectors.statistical.perplexity_detector import StatisticalPerplexityDetector
from detection_service.app.detectors.statistical.perplexity_engine import PerplexityEngine
from detection_service.tests.fakes import CharacterTokenizer, DeterministicCausalModel


def test_normal_sentence_returns_finite_measurements():
    config = PerplexityConfig(
        model_id="test", model_revision="revision", tokenizer_id="test", max_analysis_tokens=200,
        window_size=8, window_stride=4,
    )
    detector = StatisticalPerplexityDetector(
        config, PerplexityEngine(config, CharacterTokenizer(64), DeterministicCausalModel(64))
    )
    text = "The meeting is scheduled for tomorrow afternoon."
    result = detector.detect(
        DetectionRequest(
            request_id="normal",
            content=DetectionContent(type="user_prompt", text=text),
        )
    )
    assert result.status == "success"
    assert math.isfinite(result.features.whole_prompt_nll)
    assert math.isfinite(result.features.whole_prompt_ppl)
    assert math.isfinite(result.features.global_perplexity)
    assert math.isfinite(result.features.mean_surprisal)
    assert result.features.whole_prompt_nll == result.features.mean_surprisal
    assert result.features.whole_prompt_ppl == result.features.global_perplexity
    assert result.input_coverage.scoreable_tokens == result.input_coverage.input_tokens - 1
    assert result.input_coverage.tokens_analyzed == result.input_coverage.input_tokens - 1
    assert result.input_coverage.tokens_excluded == 0
    assert result.input_coverage.coverage_ratio == 1.0
    assert result.raw_score is None
    assert result.calibrated_probability is None
    assert result.binary_vote is None
    assert result.metadata["character_length"] == len(text)


def test_code_like_text_returns_schema_valid_features():
    config = PerplexityConfig(
        model_id="test", model_revision="revision", tokenizer_id="test", max_analysis_tokens=200,
        window_size=8, window_stride=4,
    )
    detector = StatisticalPerplexityDetector(
        config, PerplexityEngine(config, CharacterTokenizer(64), DeterministicCausalModel(64))
    )
    result = detector.detect(
        DetectionRequest(
            request_id="code",
            content=DetectionContent(
                type="user_prompt",
                text="def handle(x):\n    return {'ok': x != None, 'items': [1, 2, 3]}",
            ),
        )
    )
    assert result.status == "success"
    assert result.features.surface_anomaly.punctuation_ratio > 0
    assert result.input_coverage.coverage_ratio == 1.0


def test_single_token_result_is_explicitly_insufficient_without_ppl():
    config = PerplexityConfig(
        model_id="test", model_revision="revision", tokenizer_id="test", max_analysis_tokens=200,
        window_size=8, window_stride=4,
    )
    detector = StatisticalPerplexityDetector(
        config, PerplexityEngine(config, CharacterTokenizer(64), DeterministicCausalModel(64))
    )
    result = detector.detect(
        DetectionRequest(
            request_id="short",
            content=DetectionContent(type="user_prompt", text="x"),
        )
    )
    assert result.status == "insufficient_input"
    assert result.features.whole_prompt_nll is None
    assert result.features.whole_prompt_ppl is None
    assert result.input_coverage.scoreable_tokens == 0
    assert result.input_coverage.tokens_analyzed == 0
    assert result.input_coverage.coverage_ratio == 0.0
    assert result.raw_score is None
    assert result.calibrated_probability is None
    assert result.binary_vote is None
