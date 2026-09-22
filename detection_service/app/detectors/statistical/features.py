import math
import statistics
import sys

from detection_service.app.contracts.detector_result import StatisticalFeatures, SurfaceAnomalyFeatures


ZERO_WIDTH_CHARACTERS = ("\u200b", "\u200c", "\u200d", "\u2060", "\ufeff")


def _finite_exp(value: float) -> float:
    return math.exp(min(value, math.log(sys.float_info.max)))


def _windows(values: list[float], size: int, stride: int) -> list[list[float]]:
    result = []
    start = 0
    while start < len(values):
        result.append(values[start : start + size])
        if start + size >= len(values):
            break
        start += stride
    return result


def extract_surface_anomaly_features(text: str) -> SurfaceAnomalyFeatures:
    if not text:
        return SurfaceAnomalyFeatures(
            non_ascii_ratio=0.0,
            punctuation_ratio=0.0,
            zero_width_count=0,
            longest_token_ratio=0.0,
            single_character_token_ratio=0.0,
            character_entropy=0.0,
        )

    text_length = len(text)
    tokens = text.split()
    encoded = text.encode("utf-8", "ignore")
    byte_counts = {}
    for byte in encoded:
        byte_counts[byte] = byte_counts.get(byte, 0) + 1
    entropy = 0.0
    if encoded:
        for count in byte_counts.values():
            probability = count / len(encoded)
            entropy -= probability * math.log2(probability)

    return SurfaceAnomalyFeatures(
        non_ascii_ratio=sum(1 for character in text if ord(character) > 127) / text_length,
        punctuation_ratio=sum(
            1 for character in text if not character.isalnum() and not character.isspace()
        )
        / text_length,
        zero_width_count=sum(text.count(character) for character in ZERO_WIDTH_CHARACTERS),
        longest_token_ratio=max((len(token) for token in tokens), default=0) / text_length,
        single_character_token_ratio=(
            sum(1 for token in tokens if len(token) == 1) / len(tokens) if tokens else 0.0
        ),
        character_entropy=entropy / 8.0,
    )


def extract_features(
    surprisals: list[float],
    window_size: int,
    window_stride: int,
    high_surprisal_threshold: float,
    raw_text: str | None = None,
) -> StatisticalFeatures:
    surface_anomaly = (
        extract_surface_anomaly_features(raw_text) if raw_text is not None else None
    )
    if not surprisals:
        return StatisticalFeatures(
            whole_prompt_nll=None,
            whole_prompt_ppl=None,
            global_perplexity=None,
            window_count=0,
            mean_window_perplexity=None,
            max_window_perplexity=None,
            std_window_perplexity=None,
            mean_surprisal=None,
            max_surprisal=None,
            surprisal_std=None,
            high_surprisal_ratio=None,
            surface_anomaly=surface_anomaly,
        )

    mean_surprisal = statistics.fmean(surprisals)
    whole_prompt_ppl = _finite_exp(mean_surprisal)
    window_perplexities = [
        _finite_exp(statistics.fmean(window))
        for window in _windows(surprisals, window_size, window_stride)
    ]
    return StatisticalFeatures(
        whole_prompt_nll=mean_surprisal,
        whole_prompt_ppl=whole_prompt_ppl,
        global_perplexity=whole_prompt_ppl,
        window_count=len(window_perplexities),
        mean_window_perplexity=statistics.fmean(window_perplexities),
        max_window_perplexity=max(window_perplexities),
        std_window_perplexity=statistics.pstdev(window_perplexities),
        mean_surprisal=mean_surprisal,
        max_surprisal=max(surprisals),
        surprisal_std=statistics.pstdev(surprisals),
        high_surprisal_ratio=sum(value > high_surprisal_threshold for value in surprisals)
        / len(surprisals),
        surface_anomaly=surface_anomaly,
    )
