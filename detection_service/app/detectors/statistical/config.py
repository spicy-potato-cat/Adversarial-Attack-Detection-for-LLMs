from dataclasses import dataclass


@dataclass(frozen=True)
class PerplexityConfig:
    model_id: str = "distilbert/distilgpt2"
    model_revision: str = "2290a62682d06624634c1f46a6ad5be0f47f38aa"
    tokenizer_id: str = "distilbert/distilgpt2"
    device: str = "cpu"
    max_analysis_tokens: int = 4096
    window_size: int = 128
    window_stride: int = 64
    provisional_high_surprisal_threshold: float = 8.0

    def validate(self) -> None:
        if self.max_analysis_tokens < 2:
            raise ValueError("max_analysis_tokens must be at least 2")
        if self.window_size < 1 or self.window_stride < 1:
            raise ValueError("window_size and window_stride must be positive")
        if self.provisional_high_surprisal_threshold < 0:
            raise ValueError("provisional_high_surprisal_threshold must be non-negative")
