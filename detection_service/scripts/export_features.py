import argparse
import csv
import json
from pathlib import Path

from detection_service.app.contracts.detection_request import DetectionContent, DetectionRequest
from detection_service.app.core.settings import Settings
from detection_service.app.detectors.base import BaseDetector
from detection_service.app.detectors.statistical.perplexity_detector import (
    StatisticalPerplexityDetector,
)


FIELDNAMES = [
    "sample_id",
    "source",
    "source_label",
    "whole_prompt_nll",
    "whole_prompt_ppl",
    "global_perplexity",
    "mean_window_perplexity",
    "max_window_perplexity",
    "std_window_perplexity",
    "mean_surprisal",
    "max_surprisal",
    "surprisal_std",
    "high_surprisal_ratio",
    "input_tokens",
    "scoreable_tokens",
    "tokens_analyzed",
    "tokens_excluded",
    "coverage_ratio",
    "truncated",
    "inference_chunks",
    "latency_ms",
]


def export_features(input_path: Path, output_path: Path, detector: BaseDetector) -> int:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with input_path.open("r", encoding="utf-8") as source, output_path.open(
        "w", encoding="utf-8", newline=""
    ) as destination:
        writer = csv.DictWriter(destination, fieldnames=FIELDNAMES)
        writer.writeheader()
        for line_number, line in enumerate(source, start=1):
            if not line.strip():
                continue
            record = json.loads(line)
            text = record.get("text")
            if not isinstance(text, str):
                raise ValueError(f"line {line_number}: text must be a string")
            sample_id = str(record.get("sample_id") or f"line-{line_number}")
            result = detector.detect(
                DetectionRequest(
                    request_id=sample_id,
                    content=DetectionContent(type="user_prompt", text=text),
                )
            )
            features = result.features
            writer.writerow(
                {
                    "sample_id": sample_id,
                    "source": record.get("source", "UNKNOWN"),
                    "source_label": record.get("source_label", "UNKNOWN"),
                    "whole_prompt_nll": features.whole_prompt_nll,
                    "whole_prompt_ppl": features.whole_prompt_ppl,
                    "global_perplexity": features.global_perplexity,
                    "mean_window_perplexity": features.mean_window_perplexity,
                    "max_window_perplexity": features.max_window_perplexity,
                    "std_window_perplexity": features.std_window_perplexity,
                    "mean_surprisal": features.mean_surprisal,
                    "max_surprisal": features.max_surprisal,
                    "surprisal_std": features.surprisal_std,
                    "high_surprisal_ratio": features.high_surprisal_ratio,
                    "input_tokens": result.input_coverage.input_tokens,
                    "scoreable_tokens": result.input_coverage.scoreable_tokens,
                    "tokens_analyzed": result.input_coverage.tokens_analyzed,
                    "tokens_excluded": result.input_coverage.tokens_excluded,
                    "coverage_ratio": result.input_coverage.coverage_ratio,
                    "truncated": result.input_coverage.truncated,
                    "inference_chunks": result.input_coverage.inference_chunks,
                    "latency_ms": result.latency_ms,
                }
            )
            count += 1
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description="Export perplexity features without training a scorer.")
    parser.add_argument("--input", type=Path, required=True, help="Development JSONL input")
    parser.add_argument("--output", type=Path, required=True, help="Feature CSV output")
    args = parser.parse_args()
    settings = Settings.from_env()
    detector = StatisticalPerplexityDetector(settings.statistical)
    count = export_features(args.input, args.output, detector)
    print(json.dumps({"status": "success", "records": count, "output": str(args.output)}))


if __name__ == "__main__":
    main()
