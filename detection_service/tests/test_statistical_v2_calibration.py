"""Regression coverage for authoritative CALIBRATION membership, not validation counts."""

from unittest.mock import patch

import pytest

from detection_service.scripts import calibrate_statistical_v2 as runner


def test_authoritative_population_and_pre_fit_stop():
    rows = runner.population()
    assert len(rows) == 233
    assert sum(int(r["canonical_label"]) for r in rows) == 41
    assert {r["partition"] for r in rows} == {"CALIBRATION"}
    assert len(runner.verify_stop()) == 2


def test_validation_counts_cannot_pass_calibration_guard():
    rows = [{"record_id": str(i), "canonical_label": str(int(i < 39))} for i in range(233)]
    with patch.object(runner.d, "calibration_rows", return_value=rows):
        with pytest.raises(ValueError, match="population mismatch"):
            runner.population()
