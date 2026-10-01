from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest
import torch
from fastapi.testclient import TestClient
from tokenizers import Tokenizer, decoders, models, pre_tokenizers, processors, trainers
from transformers import PreTrainedTokenizerFast, RobertaConfig, RobertaForSequenceClassification

from detection_service.app.contracts.detection_request import DetectionContent, DetectionRequest
from detection_service.app.core.settings import Settings
from detection_service.app.detectors.semantic.calibration import file_sha256
from detection_service.app.detectors.semantic_finetuned.config import FineTunedConfig, MANIFEST_SHA256, UPSTREAM_MODEL
from detection_service.app.detectors.semantic_finetuned.data import class_weights, load_partition, load_texts
from detection_service.app.detectors.semantic_finetuned.detector import FineTunedDetectorError, FineTunedSemanticDetector
from detection_service.app.main import create_app
from detection_service.scripts.train_semantic_finetuned import backbone_hash, fit_transformer


def recipe(**changes):
    return replace(FineTunedConfig(UPSTREAM_MODEL, "a" * 40, "a" * 40), **changes)


def request(text="Summarize the engineering meeting."):
    return DetectionRequest(request_id="synthetic", content=DetectionContent(type="user_prompt", text=text))


@pytest.fixture
def tiny_components():
    torch.manual_seed(1701)
    torch.set_num_threads(2)
    backend = Tokenizer(models.BPE(unk_token="<unk>"))
    backend.pre_tokenizer = pre_tokenizers.ByteLevel(add_prefix_space=False)
    backend.decoder = decoders.ByteLevel()
    backend.train_from_iterator(
        ["Summarize the engineering meeting. Unicode cafe security tokens " * 8],
        trainers.BpeTrainer(vocab_size=128, special_tokens=["<s>", "<pad>", "</s>", "<unk>", "<mask>"]),
    )
    backend.post_processor = processors.RobertaProcessing(("</s>", 2), ("<s>", 0), add_prefix_space=False)
    tokenizer = PreTrainedTokenizerFast(tokenizer_object=backend, bos_token="<s>", eos_token="</s>",
                                       pad_token="<pad>", unk_token="<unk>", mask_token="<mask>", model_max_length=512)
    model = RobertaForSequenceClassification(RobertaConfig(
        vocab_size=len(tokenizer), hidden_size=16, intermediate_size=32, num_hidden_layers=1,
        num_attention_heads=2, max_position_embeddings=514, pad_token_id=1,
        num_labels=2, id2label={0: "BENIGN", 1: "ATTACK"}, label2id={"BENIGN": 0, "ATTACK": 1},
    ))
    return tokenizer, model


def save_fixture(directory, config, tokenizer, model):
    directory.mkdir()
    model.save_pretrained(directory / "transformer", safe_serialization=True)
    tokenizer.save_pretrained(directory / "transformer")
    (directory / "model_config.json").write_text(json.dumps({
        "recipe": config.to_dict(), "training_status": "COMPLETE", "label_mapping": {"benign": 0, "attack": 1},
    }), encoding="utf-8")
    files = {"model_config.json": file_sha256(directory / "model_config.json")}
    files.update({"transformer/" + p.name: file_sha256(p) for p in (directory / "transformer").iterdir()})
    (directory / "integrity_manifest.json").write_text(json.dumps(files), encoding="utf-8")


def test_config_roundtrip_and_environment_parsing(monkeypatch):
    assert FineTunedConfig.from_dict(recipe().to_dict()) == recipe()
    monkeypatch.setenv("ENABLE_FINETUNED_SEMANTIC_DETECTOR", "true")
    monkeypatch.setenv("FINETUNED_SEMANTIC_MODEL_DIR", "artifacts/models/dm_b_v1")
    monkeypatch.setenv("FINETUNED_SEMANTIC_DEVICE", "cpu")
    settings = Settings.from_env()
    assert settings.enable_finetuned_semantic_detector
    assert settings.finetuned_model_dir == "artifacts/models/dm_b_v1"
    assert settings.finetuned_device == "cpu"
    assert not settings.enable_semantic_detector


@pytest.mark.parametrize("changes", [
    {"upstream_revision": "main"}, {"tokenizer_revision": "b" * 40},
    {"upstream_model": "different"}, {"max_sequence_length": 513},
    {"default_cutpoint": 0.4}, {"manifest_sha256": "wrong"}, {"precision": "float16"},
])
def test_invalid_configuration_is_rejected(changes):
    with pytest.raises(ValueError):
        recipe(**changes).validate()


def test_result_orientation_bounds_and_uncalibrated_vote(tiny_components):
    tokenizer, model = tiny_components
    with torch.no_grad():
        model.classifier.out_proj.weight.zero_()
        model.classifier.out_proj.bias.copy_(torch.tensor([-3.0, 3.0]))
    detector = FineTunedSemanticDetector(recipe(), tokenizer, model)
    result = detector.detect(request())
    assert result.detector_id == "semantic_finetuned" and result.detector_version == "dm_b_v1"
    assert 0.99 < result.raw_score <= 1
    assert result.binary_vote is True and result.calibrated_probability is None
    assert result.metadata["label_mapping"] == {"benign": 0, "attack": 1}
    assert result.metadata["cutpoint_type"] == "DEFAULT_DEVELOPMENT_CUTPOINT"
    assert result.latency_ms > 0 and result.model.model_revision == "a" * 40


def test_reversed_model_labels_fail_explicitly(tiny_components):
    tokenizer, model = tiny_components
    model.config.id2label = {0: "ATTACK", 1: "BENIGN"}
    with pytest.raises(FineTunedDetectorError, match="orientation"):
        FineTunedSemanticDetector(recipe(), tokenizer, model)


@pytest.mark.parametrize("text", ["", " ", "\t\n"])
def test_empty_whitespace_input_is_rejected(text):
    with pytest.raises(ValueError):
        request(text)


@pytest.mark.parametrize("text", ["A normal engineering agenda.", "caf\u00e9 \u0928\u092e\u0938\u094d\u0924\u0947 \u200b meeting"])
def test_normal_unicode_eval_is_deterministic(tiny_components, text):
    tokenizer, model = tiny_components
    detector = FineTunedSemanticDetector(recipe(), tokenizer, model)
    first = detector.detect(request(text))
    second = detector.detect(request(text))
    assert first.raw_score == second.raw_score
    assert not model.training and first.status == "success"


def test_truncation_boundary_and_long_input_metadata(tiny_components):
    tokenizer, model = tiny_components
    text = "engineering " * 30
    count = len(tokenizer.encode(text, add_special_tokens=True))
    exact = FineTunedSemanticDetector(recipe(max_sequence_length=count), tokenizer, model).detect(request(text))
    assert not exact.metadata["truncated"]
    truncated = FineTunedSemanticDetector(recipe(max_sequence_length=8), tokenizer, model).detect(request(text))
    assert truncated.metadata["input_tokens_including_special"] == count
    assert truncated.metadata["tokens_analyzed_including_special"] == 8
    assert truncated.metadata["truncated"] and "SEMANTIC_INPUT_TRUNCATED" in truncated.warnings


def test_batch_inference_preserves_order_and_model_reuse(tiny_components):
    tokenizer, model = tiny_components
    detector = FineTunedSemanticDetector(recipe(batch_size=2), tokenizer, model)
    requests = [request(t) for t in ("meeting", "engineering", "security")]
    first, second = detector.detect_batch(requests), detector.detect_batch(requests)
    assert [r.raw_score for r in first] == [r.raw_score for r in second]
    assert len(first) == 3 and detector.model is model
    assert detector.detect_batch([]) == []


def test_artifact_tokenizer_model_save_reload_and_single_load(tmp_path, tiny_components, monkeypatch):
    import detection_service.app.detectors.semantic_finetuned.detector as module
    tokenizer, model = tiny_components
    directory = tmp_path / "synthetic_model"
    save_fixture(directory, recipe(), tokenizer, model)
    counts = {"model": 0, "tokenizer": 0}
    real_model, real_tokenizer = module.AutoModelForSequenceClassification.from_pretrained, module.AutoTokenizer.from_pretrained

    def load_model(*args, **kwargs):
        counts["model"] += 1
        return real_model(*args, **kwargs)

    def load_tokenizer(*args, **kwargs):
        counts["tokenizer"] += 1
        return real_tokenizer(*args, **kwargs)

    monkeypatch.setattr(module.AutoModelForSequenceClassification, "from_pretrained", load_model)
    monkeypatch.setattr(module.AutoTokenizer, "from_pretrained", load_tokenizer)
    detector = FineTunedSemanticDetector.from_artifact(directory)
    a, b = detector.detect(request()), detector.detect(request())
    assert a.raw_score == b.raw_score and counts == {"model": 1, "tokenizer": 1}
    expected = FineTunedSemanticDetector(recipe(), tokenizer, model).detect(request())
    assert a.raw_score == expected.raw_score


def test_missing_or_tampered_artifact_has_no_fallback(tmp_path, tiny_components):
    with pytest.raises(FineTunedDetectorError, match="no fallback"):
        FineTunedSemanticDetector.from_artifact(tmp_path / "missing")
    tokenizer, model = tiny_components
    directory = tmp_path / "synthetic_model"
    save_fixture(directory, recipe(), tokenizer, model)
    (directory / "transformer/model.safetensors").write_bytes(b"corrupted")
    with pytest.raises(FineTunedDetectorError, match="no fallback"):
        FineTunedSemanticDetector.from_artifact(directory)


def test_model_load_failure_and_inference_failure_are_explicit(tmp_path, tiny_components, monkeypatch):
    tokenizer, model = tiny_components
    directory = tmp_path / "synthetic_model"
    save_fixture(directory, recipe(), tokenizer, model)
    monkeypatch.setattr("detection_service.app.detectors.semantic_finetuned.detector.AutoModelForSequenceClassification.from_pretrained",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("missing model")))
    with pytest.raises(FineTunedDetectorError, match="no fallback"):
        FineTunedSemanticDetector.from_artifact(directory)
    detector = FineTunedSemanticDetector(recipe(), tokenizer, model)
    monkeypatch.setattr(model, "forward", lambda **kwargs: (_ for _ in ()).throw(RuntimeError("internal error")))
    with TestClient(create_app(detector_factory=lambda: detector)) as client:
        response = client.post("/v1/detect/input", json={"request_id": "fail", "content": {"type": "user_prompt", "text": "meeting"}})
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "SEMANTIC_DETECTOR_UNAVAILABLE"
    assert "internal error" not in response.text


def test_nonfinite_logits_fail_without_dummy_probability(tiny_components, monkeypatch):
    from types import SimpleNamespace
    tokenizer, model = tiny_components
    detector = FineTunedSemanticDetector(recipe(), tokenizer, model)
    monkeypatch.setattr(model, "forward", lambda **kwargs: SimpleNamespace(logits=torch.tensor([[float("nan"), 0.0]])))
    with pytest.raises(FineTunedDetectorError, match="no fallback"):
        detector.detect(request())


def test_service_integration_retains_distinct_detector_identity(tiny_components):
    tokenizer, model = tiny_components
    detector = FineTunedSemanticDetector(recipe(), tokenizer, model)
    with TestClient(create_app(detector_factory=lambda: detector)) as client:
        response = client.post("/v1/detect/input", json={"request_id": "dm-b", "content": {"type": "user_prompt", "text": "meeting"}})
        whitespace = client.post("/v1/detect/input", json={"request_id": "empty", "content": {"type": "user_prompt", "text": " "}})
    assert response.status_code == 200 and whitespace.status_code == 422
    result = response.json()["detectors"][0]
    assert result["detector_id"] == "semantic_finetuned" and result["detector_version"] == "dm_b_v1"
    assert result["calibrated_probability"] is None and isinstance(result["binary_vote"], bool)


def test_default_service_wiring_loads_dm_b_without_substitution(tmp_path, monkeypatch):
    from detection_service.app.main import _default_detectors
    from detection_service.app.detectors.statistical.config import PerplexityConfig
    calls = []
    sentinel = object()
    monkeypatch.setattr("detection_service.app.main.StatisticalPerplexityDetector", lambda c: object())
    monkeypatch.setattr("detection_service.app.main.FineTunedSemanticDetector.from_artifact",
                        lambda path, **kwargs: (calls.append((path, kwargs)) or sentinel))
    settings = Settings("test", PerplexityConfig(), enable_finetuned_semantic_detector=True, finetuned_model_dir="dm_b")
    detectors = _default_detectors(settings)
    assert detectors[-1] is sentinel and calls == [("dm_b", {"device": "cpu"})]


def test_manifest_boundary_and_class_weights_base_train_only(tmp_path):
    manifest = Path("data_governance/manifests/development_partition_manifest_v1.csv")
    rows = load_partition(manifest, "BASE_TRAIN")
    assert len(rows) == 1135 and sum(int(r["canonical_label"]) for r in rows) == 183
    assert class_weights(rows) == [1135 / (2 * 952), 1135 / (2 * 183)]
    with pytest.raises(RuntimeError, match="cannot consume"):
        load_partition(manifest, "CALIBRATION")
    with pytest.raises(RuntimeError, match="BASE_TRAIN only"):
        class_weights([{**rows[0], "partition": "VALIDATION"}])
    changed = tmp_path / "changed.csv"
    changed.write_bytes(manifest.read_bytes() + b"\n")
    with pytest.raises(RuntimeError, match="integrity"):
        load_partition(changed, "BASE_TRAIN")


def test_loader_rejects_calibration_before_access(tmp_path):
    with pytest.raises(RuntimeError, match="calibration"):
        load_texts([{"partition": "CALIBRATION"}], tmp_path, "CALIBRATION")


def test_transformer_parameters_update_on_synthetic_fixture(tiny_components):
    tokenizer, model = tiny_components
    before = backbone_hash(model)
    config = recipe(epochs=1, batch_size=2, max_sequence_length=32, warmup_ratio=0.0)
    history = fit_transformer(model, tokenizer, ["meeting", "security"], [0, 1], config, [1.0, 1.0])
    assert backbone_hash(model) != before
    assert history[0]["batches"] == 1 and history[0]["weighted_mean_loss"] > 0


def test_authoritative_training_refuses_existing_output(tmp_path, monkeypatch):
    import detection_service.scripts.train_semantic_finetuned as script
    monkeypatch.setattr(script, "OUTPUT", tmp_path)
    with pytest.raises(RuntimeError, match="refusing training rerun"):
        script.train_once()
