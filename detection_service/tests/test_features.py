import math

from detection_service.app.detectors.statistical.features import (
    extract_features,
    extract_surface_anomaly_features,
)


def test_feature_math_and_windowing():
    result = extract_features([1.0, 2.0, 3.0, 4.0], 3, 2, 2.5)
    assert result.whole_prompt_nll == 2.5
    assert result.whole_prompt_ppl == math.exp(2.5)
    assert result.global_perplexity == math.exp(2.5)
    assert result.window_count == 2
    assert result.max_window_perplexity == math.exp(3.5)
    assert result.mean_surprisal == 2.5
    assert result.max_surprisal == 4.0
    assert result.high_surprisal_ratio == 0.5


def test_empty_surprisal_sequence_is_explicit():
    result = extract_features([], 128, 64, 8.0)
    assert result.whole_prompt_nll is None
    assert result.whole_prompt_ppl is None
    assert result.global_perplexity is None
    assert result.window_count == 0
    assert result.high_surprisal_ratio is None


def test_surface_anomaly_features_preserve_raw_unicode_signals():
    result = extract_surface_anomaly_features("A \u200b B !!! cafe\u0301")
    assert result.non_ascii_ratio > 0
    assert result.punctuation_ratio > 0
    assert result.zero_width_count == 1
    assert result.longest_token_ratio > 0
    assert 0 <= result.character_entropy <= 1


def test_statistical_features_can_include_surface_anomaly_block():
    result = extract_features([1.0, 2.0], 2, 1, 1.5, raw_text="x \u200by")
    assert result.surface_anomaly is not None
    assert result.surface_anomaly.zero_width_count == 1
