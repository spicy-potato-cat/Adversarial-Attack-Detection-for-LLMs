import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import torch
from tokenizers import Tokenizer
from tokenizers.models import WordLevel
from tokenizers.pre_tokenizers import Whitespace
from tokenizers.processors import TemplateProcessing
from transformers import DebertaV2Config, DebertaV2ForSequenceClassification, DebertaV2TokenizerFast

from detection_service.app.contracts.detection_request import DetectionContent, DetectionRequest
from detection_service.app.contracts.detector_result import DetectorResult
from detection_service.app.detectors.base import BaseDetector
from detection_service.app.detectors.guard import GuardConfig, GuardDetector, GuardUnavailableError
from detection_service.app.detectors.guard.config import MODEL_ID, REVISION
from detection_service.app.detectors.guard.detector import chunk_spans
from detection_service.app.detectors.guard.model import UPSTREAM_FILES, sha256


def request(text):
    return DetectionRequest(request_id="synthetic-unit", content=DetectionContent(type="user_prompt", text=text))


@pytest.fixture
def components():
    torch.manual_seed(1)
    torch.set_num_threads(2)
    backend = Tokenizer(WordLevel({"[PAD]": 0, "[CLS]": 1, "[SEP]": 2, "[UNK]": 3, "note": 4, "override": 5}, unk_token="[UNK]"))
    backend.pre_tokenizer = Whitespace()
    backend.post_processor = TemplateProcessing(single="[CLS] $A [SEP]", special_tokens=[("[CLS]", 1), ("[SEP]", 2)])
    tokenizer = DebertaV2TokenizerFast(tokenizer_object=backend, pad_token="[PAD]", cls_token="[CLS]", sep_token="[SEP]", unk_token="[UNK]")
    model = DebertaV2ForSequenceClassification(DebertaV2Config(
        vocab_size=6, hidden_size=8, intermediate_size=16, num_attention_heads=2,
        num_hidden_layers=1, max_position_embeddings=512, num_labels=2, pad_token_id=0,
    ))
    return model, tokenizer


def save_fixture(root, components):
    model, tokenizer = components
    snapshot = root / "snapshot"
    model.save_pretrained(snapshot, safe_serialization=True)
    tokenizer.save_pretrained(snapshot)
    for name in UPSTREAM_FILES:
        path = snapshot / name
        if not path.exists():
            path.write_text("Synthetic fixture only", encoding="utf-8")
    artifact = root / "freeze"
    artifact.mkdir()
    (artifact / "model_config.json").write_text(json.dumps(GuardConfig().to_dict()), encoding="utf-8")
    freeze = {"model_id": MODEL_ID, "revision": REVISION, "tokenizer_revision": REVISION,
              "snapshot_path": "snapshot", "architecture": "DebertaV2ForSequenceClassification",
              "parameter_count": sum(p.numel() for p in model.parameters()),
              "file_sha256": {name: sha256(snapshot / name) for name in UPSTREAM_FILES}}
    (artifact / "freeze_metadata.json").write_text(json.dumps(freeze), encoding="utf-8")
    rehash(artifact)
    return artifact, snapshot


def rehash(artifact):
    (artifact / "integrity_manifest.json").write_text(json.dumps({name: sha256(artifact / name) for name in ("model_config.json", "freeze_metadata.json")}), encoding="utf-8")


def test_frozen_config_roundtrip_and_exact_identity():
    cfg = GuardConfig.from_dict(GuardConfig().to_dict())
    assert cfg.model_id == MODEL_ID and cfg.revision == cfg.tokenizer_revision == REVISION
    assert cfg.detector_version == "dg_v1" and cfg.stride == 446


@pytest.mark.parametrize("key,value", [("revision", "main"), ("positive_class", 0), ("chunk_tokens", 512), ("overlap_tokens", 0), ("batch_size", 0)])
def test_policy_changes_rejected(key, value):
    with pytest.raises(ValueError):
        GuardConfig.from_dict({**GuardConfig().to_dict(), key: value})


def test_extra_config_field_rejected():
    with pytest.raises(ValueError):
        GuardConfig.from_dict({**GuardConfig().to_dict(), "fallback": "other"})


@pytest.mark.parametrize("count,expected", [(0, 0), (1, 1), (510, 1), (511, 2), (956, 2), (957, 3), (10000, 23)])
def test_spans_full_union_no_tail_drop(count, expected):
    spans = list(chunk_spans(count))
    assert len(spans) == expected
    assert set(index for start, end in spans for index in range(start, end)) == set(range(count))
    if count:
        assert spans[-1][1] == count
        assert all(end - start <= 510 for start, end in spans)
        assert all(left[1] - right[0] == 64 for left, right in zip(spans, spans[1:]))


@pytest.mark.parametrize("args", [(-1, 510, 64), (10, 0, 0), (10, 510, 510)])
def test_invalid_spans_rejected(args):
    with pytest.raises(ValueError):
        list(chunk_spans(*args))


@pytest.mark.parametrize("text", ["note", "A synthetic engineering note.", "caf\u00e9 \u4f60\u597d \U0001f680", "note\x00override"])
def test_real_tiny_model_result_schema_and_deterministic_reuse(components, text):
    detector = GuardDetector(*components)
    assert isinstance(detector, BaseDetector)
    model_id = id(detector.model)
    first, second = detector.detect(request(text)), detector.detect(request(text))
    assert isinstance(first, DetectorResult)
    assert first.status == "success" and 0 <= first.raw_score <= 1
    assert isinstance(first.binary_vote, bool) and first.calibrated_probability is None
    assert first.raw_score == second.raw_score and first.binary_vote == second.binary_vote
    assert first.metadata == second.metadata
    assert first.input_coverage.coverage_ratio == 1 and first.input_coverage.tokens_excluded == 0
    assert first.model.model_revision == REVISION and first.metadata["tokenizer_revision"] == REVISION
    assert first.metadata["tail_covered"] and not first.metadata["truncated"]
    assert "DEFAULT MODEL DECISION" in first.metadata["decision_scope"]
    assert "text" not in first.metadata
    DetectorResult.model_validate_json(first.model_dump_json())
    assert id(detector.model) == model_id and not detector.model.training
    assert not any(p.requires_grad for p in detector.model.parameters())


@pytest.mark.parametrize("text", ["", " ", "\n\t", "\u2003"])
def test_empty_whitespace_rejected_by_authoritative_request(text):
    with pytest.raises(ValueError):
        request(text)


def test_invalid_text_type_rejected():
    with pytest.raises(ValueError):
        request(["note"])


def test_malformed_surrogate_fails_explicitly(components):
    with pytest.raises(GuardUnavailableError, match="UnicodeEncodeError"):
        GuardDetector(*components).detect(request("note\ud800"))


def test_zero_upstream_tokens_explicitly_unscored(components, monkeypatch):
    model, tokenizer = components
    monkeypatch.setattr(tokenizer, "encode", lambda *args, **kwargs: [])
    result = GuardDetector(model, tokenizer).detect(request("note"))
    assert result.status == "insufficient_input" and result.raw_score is None and result.binary_vote is None


class ControlledModel(torch.nn.Module):
    def __init__(self, mode="tail"):
        super().__init__()
        self.marker = torch.nn.Parameter(torch.zeros(1))
        self.mode = mode
        self.calls = []

    def forward(self, input_ids, attention_mask):
        self.calls.append(input_ids.detach().cpu().clone())
        if self.mode == "tie":
            logits = torch.zeros(len(input_ids), 2, device=input_ids.device)
        elif self.mode == "nan":
            logits = torch.full((len(input_ids), 2), float("nan"), device=input_ids.device)
        elif self.mode == "wrong":
            logits = torch.zeros(len(input_ids), 3, device=input_ids.device)
        else:
            malicious = (input_ids == 5).any(dim=1)
            logits = torch.stack([torch.where(malicious, -2.0, 2.0), torch.where(malicious, 2.0, -2.0)], dim=1)
        return SimpleNamespace(logits=logits)


@pytest.mark.parametrize("count", [510, 511, 10000])
def test_direct_ids_special_budget_tail_only_max_aggregation(components, count, monkeypatch):
    _, tokenizer = components
    monkeypatch.setattr(tokenizer, "decode", lambda *args, **kwargs: pytest.fail("decode/re-encode forbidden"))
    model = ControlledModel()
    detector = GuardDetector(model, tokenizer)
    text = "note " * (count - 1) + "override"
    result = detector.detect(request(text))
    assert result.raw_score == pytest.approx(torch.tensor([-2.0, 2.0]).softmax(-1)[1].item())
    assert result.binary_vote is True and result.calibrated_probability is None
    assert result.metadata["original_token_count"] == count
    spans = list(chunk_spans(count))
    assert result.metadata["max_risk_chunk_index"] == len(spans) - 1
    assert result.metadata["number_of_chunks"] == len(spans)
    assert result.metadata["final_tail_end"] == count
    assert len(model.calls) == (len(spans) + 7) // 8
    assert all(batch.shape[1] <= 512 and batch.shape[0] <= 8 for batch in model.calls)
    assert all(batch[:, 0].eq(1).all() for batch in model.calls)
    assert model.calls[-1].eq(5).any()


def test_native_argmax_tie_is_benign_not_ge_half(components):
    result = GuardDetector(ControlledModel("tie"), components[1]).detect(request("note"))
    assert result.raw_score == 0.5 and result.binary_vote is False


def test_score_orientation_class_one(components):
    detector = GuardDetector(ControlledModel(), components[1])
    benign = detector.detect(request("note"))
    malicious = detector.detect(request("override"))
    assert malicious.raw_score > benign.raw_score
    assert malicious.binary_vote is True and benign.binary_vote is False


@pytest.mark.parametrize("mode", ["nan", "wrong"])
def test_invalid_logits_explicit_no_dummy_or_fallback(components, mode):
    with pytest.raises(GuardUnavailableError, match="invalid binary logits"):
        GuardDetector(ControlledModel(mode), components[1]).detect(request("note"))


def test_inference_exception_explicit(components, monkeypatch):
    model, tokenizer = components
    def fail(**kwargs):
        raise RuntimeError("synthetic inference failure")
    monkeypatch.setattr(model, "forward", fail)
    with pytest.raises(GuardUnavailableError, match="synthetic inference failure"):
        GuardDetector(model, tokenizer).detect(request("note"))


def test_synthetic_artifact_save_reload_offline_and_reuse(tmp_path, components, monkeypatch):
    artifact, _ = save_fixture(tmp_path, components)
    from transformers import AutoModelForSequenceClassification
    original = AutoModelForSequenceClassification.from_pretrained
    calls = []
    def load(*args, **kwargs):
        assert kwargs["local_files_only"] and kwargs["use_safetensors"] and not kwargs["trust_remote_code"]
        calls.append(args)
        return original(*args, **kwargs)
    monkeypatch.setattr(AutoModelForSequenceClassification, "from_pretrained", load)
    first = GuardDetector.from_artifact(artifact, workspace=tmp_path)
    second = GuardDetector.from_artifact(artifact, workspace=tmp_path)
    one = first.detect(request("note"))
    assert one.raw_score == second.detect(request("note")).raw_score
    first.detect(request("override"))
    assert len(calls) == 2


def test_missing_artifact_explicit_no_fallback(tmp_path):
    with pytest.raises(GuardUnavailableError, match="FileNotFoundError"):
        GuardDetector.from_artifact(tmp_path / "missing", workspace=tmp_path)


@pytest.mark.parametrize("name", ["model_config.json", "freeze_metadata.json", "config.json", "tokenizer.json", "model.safetensors"])
def test_tampered_bytes_rejected_before_loading(tmp_path, components, name):
    artifact, snapshot = save_fixture(tmp_path, components)
    path = artifact / name if name in ("model_config.json", "freeze_metadata.json") else snapshot / name
    path.write_bytes(path.read_bytes() + b"corrupt")
    with pytest.raises(GuardUnavailableError, match="hash mismatch"):
        GuardDetector.from_artifact(artifact, workspace=tmp_path)


@pytest.mark.parametrize("field,value", [("revision", "main"), ("snapshot_path", "../outside"), ("parameter_count", 1), ("architecture", "OtherModel")])
def test_incompatible_or_escaped_freeze_rejected(tmp_path, components, field, value):
    artifact, _ = save_fixture(tmp_path, components)
    path = artifact / "freeze_metadata.json"
    freeze = json.loads(path.read_text(encoding="utf-8"))
    path.write_text(json.dumps({**freeze, field: value}), encoding="utf-8")
    rehash(artifact)
    with pytest.raises(GuardUnavailableError):
        GuardDetector.from_artifact(artifact, workspace=tmp_path)


def test_model_dependency_load_failure_explicit(tmp_path, components, monkeypatch):
    artifact, _ = save_fixture(tmp_path, components)
    from transformers import AutoModelForSequenceClassification
    def fail(*args, **kwargs):
        raise ImportError("synthetic dependency unavailable")
    monkeypatch.setattr(AutoModelForSequenceClassification, "from_pretrained", fail)
    with pytest.raises(GuardUnavailableError, match="ImportError"):
        GuardDetector.from_artifact(artifact, workspace=tmp_path)


def test_partial_random_weight_initialization_rejected(tmp_path, components, monkeypatch):
    artifact, _ = save_fixture(tmp_path, components)
    from transformers import AutoModelForSequenceClassification
    monkeypatch.setattr(AutoModelForSequenceClassification, "from_pretrained", lambda *args, **kwargs: (components[0], {"missing_keys": ["classifier.weight"]}))
    with pytest.raises(GuardUnavailableError, match="Incomplete"):
        GuardDetector.from_artifact(artifact, workspace=tmp_path)
