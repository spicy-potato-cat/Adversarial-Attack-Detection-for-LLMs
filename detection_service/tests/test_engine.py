import math

import pytest
import torch

from detection_service.app.detectors.statistical.config import PerplexityConfig
from detection_service.app.detectors.statistical.perplexity_engine import (
    DeviceUnavailableError,
    PerplexityEngine,
)
from detection_service.tests.fakes import CharacterTokenizer, DeterministicCausalModel, FixedTokenizer


class KnownProbabilityModel:
    def __init__(self) -> None:
        self.config = type("Config", (), {"max_position_embeddings": 16})()
        self.calls = 0
        self.eval_calls = 0
        self.target_probabilities = [0.5, 0.25, 0.125]

    def to(self, device):
        return self

    def eval(self):
        self.eval_calls += 1
        return self

    def __call__(self, input_ids):
        self.calls += 1
        batch, length = input_ids.shape
        vocab_size = 8
        logits = torch.full((batch, length, vocab_size), fill_value=-20.0)
        target_ids = input_ids[0, 1:].tolist()
        for position, (target_id, probability) in enumerate(
            zip(target_ids, self.target_probabilities)
        ):
            other_probability = (1.0 - probability) / (vocab_size - 1)
            logits[:, position, :] = torch.log(torch.full((vocab_size,), other_probability))
            logits[:, position, target_id] = math.log(probability)
        return type("Output", (), {"logits": logits})()


def config(**overrides):
    values = {
        "model_id": "test-causal-lm",
        "model_revision": "test-revision",
        "tokenizer_id": "test-tokenizer",
        "device": "cpu",
        "max_analysis_tokens": 20,
        "window_size": 6,
        "window_stride": 3,
        "provisional_high_surprisal_threshold": 8.0,
    }
    values.update(overrides)
    return PerplexityConfig(**values)


def test_correct_causal_shift_scores_next_token():
    engine = PerplexityEngine(config(), FixedTokenizer(), DeterministicCausalModel())
    evidence = engine.score("ignored")
    assert evidence.tokens_analyzed == 3
    assert max(evidence.surprisals) < 0.2


def test_known_logits_verify_shift_n_minus_one_nll_and_ppl():
    engine = PerplexityEngine(config(), FixedTokenizer(), KnownProbabilityModel())
    evidence = engine.score("ignored")
    expected_surprisals = [math.log(2), math.log(4), math.log(8)]
    assert evidence.tokens_analyzed == 3
    assert evidence.surprisals == pytest.approx(expected_surprisals)
    nll = sum(evidence.surprisals) / evidence.tokens_analyzed
    assert nll == pytest.approx(math.log(4))
    assert math.exp(nll) == pytest.approx(4.0)


def test_unicode_is_passed_to_tokenizer_unchanged():
    tokenizer = CharacterTokenizer()
    engine = PerplexityEngine(config(), tokenizer, DeterministicCausalModel())
    text = "hello \u200bworld caf\u00e9 \u0928\u092e\u0938\u094d\u0924\u0947"
    evidence = engine.score(text)
    assert tokenizer.last_text == text
    assert evidence.tokens_analyzed > 0


def test_long_input_uses_chunks_and_reports_configured_truncation():
    model = DeterministicCausalModel(context=8)
    engine = PerplexityEngine(config(max_analysis_tokens=20), CharacterTokenizer(8), model)
    evidence = engine.score("a" * 30)
    assert evidence.input_tokens == 30
    assert evidence.tokens_analyzed == 19
    assert evidence.truncated is True
    assert evidence.inference_chunks > 1
    assert "INPUT_TRUNCATED_TO_CONFIGURED_MAX_ANALYSIS_TOKENS" in evidence.warnings


def test_chunking_scores_tail_token_without_omission():
    engine = PerplexityEngine(
        config(max_analysis_tokens=17, window_stride=3),
        CharacterTokenizer(5),
        DeterministicCausalModel(context=5),
    )
    evidence = engine.score("abcdefghijklmnopq", include_diagnostics=True)
    assert evidence.input_tokens == 17
    assert evidence.tokens_analyzed == 16
    assert evidence.truncated is False
    assert evidence.inference_chunks > 1
    assert [diagnostic.position for diagnostic in evidence.token_diagnostics] == list(range(1, 17))


def test_short_input_does_not_divide_by_zero_or_call_model():
    model = DeterministicCausalModel()
    evidence = PerplexityEngine(config(), CharacterTokenizer(), model).score("x")
    assert evidence.tokens_analyzed == 0
    assert evidence.inference_chunks == 0
    assert model.calls == 0
    assert "TOO_SHORT_TO_SCORE_NEXT_TOKEN_PROBABILITY" in evidence.warnings


def test_empty_direct_engine_input_is_explicitly_unscored():
    model = DeterministicCausalModel()
    evidence = PerplexityEngine(config(), CharacterTokenizer(), model).score("")
    assert evidence.input_tokens == 0
    assert evidence.tokens_analyzed == 0
    assert evidence.inference_chunks == 0
    assert model.calls == 0
    assert "TOO_SHORT_TO_SCORE_NEXT_TOKEN_PROBABILITY" in evidence.warnings


def test_deterministic_inference():
    engine = PerplexityEngine(config(), CharacterTokenizer(), DeterministicCausalModel())
    first = engine.score("deterministic prompt")
    second = engine.score("deterministic prompt")
    assert first.surprisals == pytest.approx(second.surprisals, rel=0, abs=0)
    assert all(math.isfinite(value) for value in first.surprisals)


def test_unavailable_device_fails_cleanly(monkeypatch):
    monkeypatch.setattr("torch.cuda.is_available", lambda: False)
    with pytest.raises(DeviceUnavailableError, match="configured device is unavailable"):
        PerplexityEngine(config(device="cuda"), CharacterTokenizer(), DeterministicCausalModel())
