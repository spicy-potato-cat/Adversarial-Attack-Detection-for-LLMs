"""Verification-only tests for stored authoritative STAT-005 results."""

import copy
import csv

import pytest

from detection_service.scripts import statistical_scorer_acceptance as acceptance


@pytest.fixture(scope="module")
def stored():
    driver = acceptance.driver
    rows, _ = driver.baseline.selected_metadata()
    evidence = driver.source.load_cache(rows, driver.stat004.CACHE_SHA)
    with (driver.OUT / "scorer_predictions_v1.csv").open(encoding="utf-8", newline="") as handle:
        records = list(csv.DictReader(handle))
    return records, rows, evidence


def test_independent_authoritative_counts_and_error_ids(stored):
    result = acceptance.independently_check_records(*stored)
    assert result["status"] == "PASS" and result["prediction_metadata_checks"] == 3405
    assert result["independent_frontier_confusion_checks"] == 54
    assert result["exact_error_bank_checks"] == 12


@pytest.mark.parametrize("field,value", [("partition", "VALIDATION"), ("label", "2"), ("fold", "99"),
    ("lineage_group", "wrong"), ("score_kind", "calibrated"), ("calibrated_probability", "0.5"),
    ("B2_schema_sha256", "wrong")])
def test_stored_metadata_tampering_rejected(stored, field, value):
    records, rows, evidence = stored
    changed = copy.deepcopy(records)
    changed[0][field] = value
    with pytest.raises(ValueError, match="metadata"):
        acceptance.independently_check_records(changed, rows, evidence)
