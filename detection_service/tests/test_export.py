import csv
from pathlib import Path

from detection_service.app.detectors.statistical.config import PerplexityConfig
from detection_service.app.detectors.statistical.perplexity_detector import StatisticalPerplexityDetector
from detection_service.app.detectors.statistical.perplexity_engine import PerplexityEngine
from detection_service.scripts.export_features import export_features
from detection_service.tests.fakes import CharacterTokenizer, DeterministicCausalModel


def test_offline_export_contains_features_but_not_raw_text(tmp_path):
    config = PerplexityConfig(model_id="test", model_revision="revision", tokenizer_id="test")
    detector = StatisticalPerplexityDetector(
        config, PerplexityEngine(config, CharacterTokenizer(64), DeterministicCausalModel(64))
    )
    source = Path(__file__).parent / "fixtures" / "development_samples.jsonl"
    output = tmp_path / "features.csv"
    assert export_features(source, output, detector) == 2
    rows = list(csv.DictReader(output.open(encoding="utf-8")))
    assert len(rows) == 2
    assert "text" not in rows[0]
    assert float(rows[0]["whole_prompt_nll"]) > 0
    assert float(rows[0]["whole_prompt_ppl"]) > 0
    assert float(rows[0]["global_perplexity"]) > 0
    assert float(rows[0]["coverage_ratio"]) == 1.0
    assert int(rows[0]["tokens_excluded"]) == 0
    assert rows[0]["sample_id"] == "dev_001"
