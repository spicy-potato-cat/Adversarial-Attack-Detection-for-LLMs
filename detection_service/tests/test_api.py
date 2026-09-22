from fastapi.testclient import TestClient

from detection_service.app.contracts.detector_result import (
    DetectorResult,
    ModelMetadata,
    SemanticFeatures,
)
from detection_service.app.core.settings import Settings
from detection_service.app.detectors.base import BaseDetector
from detection_service.app.detectors.semantic.detector import SemanticDetectorError
from detection_service.app.detectors.statistical.config import PerplexityConfig
from detection_service.app.detectors.statistical.perplexity_detector import StatisticalPerplexityDetector
from detection_service.app.detectors.statistical.perplexity_engine import PerplexityEngine
from detection_service.app.main import create_app
from detection_service.tests.fakes import CharacterTokenizer, DeterministicCausalModel, FailingModel


class FakeSemanticDetector(BaseDetector):
    def detect(self, request):
        return DetectorResult(
            detector_id="semantic_embedding_lr",
            detector_version="v0.1",
            status="success",
            raw_score=0.75,
            semantic_features=SemanticFeatures(
                embedding_dim=2,
                embedding_model_id="fake",
                embedding_model_revision="revision",
                normalized_embeddings=True,
                classifier_type="logistic_regression",
                classifier_version="synthetic-test",
            ),
            model=ModelMetadata(
                model_id="fake",
                model_revision="revision",
                tokenizer_id="fake",
                device="cpu",
            ),
            latency_ms=1.0,
            warnings=[],
        )


class FailingSemanticDetector(BaseDetector):
    def detect(self, request):
        raise SemanticDetectorError("semantic model missing")


def build_app(model=None):
    config = PerplexityConfig(
        model_id="test", model_revision="revision", tokenizer_id="test", max_analysis_tokens=200,
        window_size=8, window_stride=4,
    )
    tokenizer = CharacterTokenizer(64)
    resolved_model = model or DeterministicCausalModel(64)
    calls = {"factory": 0}

    def factory():
        calls["factory"] += 1
        engine = PerplexityEngine(config, tokenizer, resolved_model)
        return StatisticalPerplexityDetector(config, engine)

    return create_app(Settings("dev-v0.1", config), factory), calls, tokenizer, resolved_model


def test_api_success_preserves_privacy_and_reuses_startup_model():
    app, calls, tokenizer, model = build_app()
    prompt = "hello \u200bworld caf\u00e9 \u0928\u092e\u0938\u094d\u0924\u0947"
    with TestClient(app) as client:
        first = client.post("/v1/detect/input", json={"request_id":"one","content":{"type":"user_prompt","text":prompt}})
        second = client.post("/v1/detect/input", json={"request_id":"two","content":{"type":"user_prompt","text":prompt}})
    assert first.status_code == 200
    body = first.json()
    assert body["detectors"][0]["status"] == "success"
    assert body["detectors"][0]["raw_score"] is None
    assert body["detectors"][0]["calibrated_probability"] is None
    assert body["detectors"][0]["binary_vote"] is None
    assert body["detectors"][0]["features"]["whole_prompt_nll"] is not None
    assert body["detectors"][0]["features"]["whole_prompt_ppl"] is not None
    assert body["detectors"][0]["input_coverage"]["coverage_ratio"] == 1.0
    assert prompt not in first.text
    assert tokenizer.last_text == prompt
    assert calls["factory"] == 1
    assert model.eval_calls == 1
    assert model.calls == 2
    assert first.json()["detectors"][0]["features"] == second.json()["detectors"][0]["features"]


def test_empty_prompt_is_rejected_cleanly():
    app, _, _, _ = build_app()
    with TestClient(app) as client:
        response = client.post("/v1/detect/input", json={"request_id":"empty","content":{"type":"user_prompt","text":"  "}})
    assert response.status_code == 422


def test_inference_failure_does_not_return_raw_stack_trace():
    app, _, _, _ = build_app(FailingModel(64))
    with TestClient(app) as client:
        response = client.post("/v1/detect/input", json={"request_id":"failure","content":{"type":"user_prompt","text":"safe text"}})
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "STATISTICAL_DETECTOR_UNAVAILABLE"
    assert "sensitive internal failure" not in response.text
    assert "Traceback" not in response.text


def test_service_can_route_statistical_and_semantic_detectors_together():
    config = PerplexityConfig(
        model_id="test", model_revision="revision", tokenizer_id="test", max_analysis_tokens=200,
        window_size=8, window_stride=4,
    )
    tokenizer = CharacterTokenizer(64)
    model = DeterministicCausalModel(64)

    def factory():
        engine = PerplexityEngine(config, tokenizer, model)
        return [StatisticalPerplexityDetector(config, engine), FakeSemanticDetector()]

    app = create_app(Settings("dev-v0.1", config), factory)
    with TestClient(app) as client:
        response = client.post(
            "/v1/detect/input",
            json={"request_id": "multi", "content": {"type": "user_prompt", "text": "hello"}},
        )
    assert response.status_code == 200
    body = response.json()
    assert [item["detector_id"] for item in body["detectors"]] == [
        "statistical_perplexity",
        "semantic_embedding_lr",
    ]
    assert body["detectors"][1]["raw_score"] == 0.75


def test_semantic_detector_failure_is_structured_service_error():
    config = PerplexityConfig(model_id="test", model_revision="revision", tokenizer_id="test")
    app = create_app(Settings("dev-v0.1", config), lambda: [FailingSemanticDetector()])
    with TestClient(app) as client:
        response = client.post(
            "/v1/detect/input",
            json={"request_id": "semantic-failure", "content": {"type": "user_prompt", "text": "hello"}},
        )
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "SEMANTIC_DETECTOR_UNAVAILABLE"
