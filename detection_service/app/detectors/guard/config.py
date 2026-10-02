from dataclasses import asdict, dataclass

MODEL_ID = "meta-llama/Llama-Prompt-Guard-2-22M"
REVISION = "11614a155199674a0a95e6602d6ab0417b790ed0"


@dataclass(frozen=True)
class GuardConfig:
    model_id: str = MODEL_ID
    revision: str = REVISION
    tokenizer_revision: str = REVISION
    detector_id: str = "guard_external"
    detector_version: str = "dg_v1"
    context_tokens: int = 512
    special_tokens: int = 2
    chunk_tokens: int = 510
    overlap_tokens: int = 64
    batch_size: int = 8
    positive_class: int = 1
    aggregation: str = "max_chunk_malicious_probability"
    decision: str = "OR_of_native_chunk_argmax_class_1"

    def __post_init__(self):
        expected = {
            "model_id": MODEL_ID, "revision": REVISION, "tokenizer_revision": REVISION,
            "detector_id": "guard_external", "detector_version": "dg_v1",
            "context_tokens": 512, "special_tokens": 2, "chunk_tokens": 510,
            "overlap_tokens": 64, "batch_size": 8, "positive_class": 1,
            "aggregation": "max_chunk_malicious_probability",
            "decision": "OR_of_native_chunk_argmax_class_1",
        }
        actual = asdict(self)
        if actual != expected or any(type(actual[key]) is not type(value) for key, value in expected.items()):
            raise ValueError("D_G v1 configuration differs from the frozen policy")

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, value):
        if set(value) != set(cls().to_dict()):
            raise ValueError("Invalid guard configuration fields")
        return cls(**value)

    @property
    def stride(self):
        return self.chunk_tokens - self.overlap_tokens
