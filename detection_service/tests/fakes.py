from types import SimpleNamespace

import torch


class CharacterTokenizer:
    def __init__(self, model_max_length: int = 8) -> None:
        self.model_max_length = model_max_length
        self.last_text = None

    def __call__(self, text, **kwargs):
        self.last_text = text
        token_ids = [(ord(character) % 13) + 1 for character in text]
        return {"input_ids": torch.tensor([token_ids], dtype=torch.long)}

    def convert_ids_to_tokens(self, token_id):
        return f"token-{token_id}"


class FixedTokenizer(CharacterTokenizer):
    def __call__(self, text, **kwargs):
        self.last_text = text
        return {"input_ids": torch.tensor([[1, 2, 3, 4]], dtype=torch.long)}


class DeterministicCausalModel:
    def __init__(self, context: int = 8, vocab_size: int = 16) -> None:
        self.config = SimpleNamespace(max_position_embeddings=context)
        self.vocab_size = vocab_size
        self.calls = 0
        self.eval_calls = 0
        self.device = "cpu"

    def to(self, device):
        self.device = device
        return self

    def eval(self):
        self.eval_calls += 1
        return self

    def __call__(self, input_ids):
        self.calls += 1
        batch, length = input_ids.shape
        logits = torch.zeros((batch, length, self.vocab_size), dtype=torch.float32)
        for position in range(length):
            favored = (position + 2) % self.vocab_size
            logits[:, position, favored] = 5.0
        return SimpleNamespace(logits=logits)


class FailingModel(DeterministicCausalModel):
    def __call__(self, input_ids):
        raise RuntimeError("sensitive internal failure")

