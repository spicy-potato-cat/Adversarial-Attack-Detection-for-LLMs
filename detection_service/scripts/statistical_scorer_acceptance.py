"""Post-run STAT-005 acceptance; reconstruct evidence without classifier refits."""

import argparse
import csv
import json
from unittest.mock import patch
import xml.etree.ElementTree as ET

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC

from detection_service.analysis.statistical_feature_ablation import short_bucket
from detection_service.analysis.statistical_oof import require
from detection_service.scripts import statistical_scorer_comparison as driver

OUT = driver.OUT
CODE = ("detection_service/scripts/statistical_scorer_acceptance.py",
        "detection_service/tests/test_statistical_scorer_acceptance.py")


def independently_check_records(records, rows, evidence):
    require(len(records) == 3405 and len(rows) == len(evidence) == 1135, "population mismatch")
    metrics = driver.read(OUT / "scorer_metrics_v1.json")
    groups = driver.read(OUT / "subgroup_analysis_v1.json")
    errors = driver.read(OUT / "error_transition_v1.json")
    labels = np.asarray([int(r["label"]) for r in rows])
    ids = [r["sample_id"] for r in rows]
    votes = {}
    for scorer in driver.core.SCORERS:
        selected = [r for r in records if r["scorer"] == scorer]
        require([r["sample_id"] for r in selected] == ids, "sample alignment mismatch")
        kind = "decision_function" if scorer == "S1" else "uncalibrated_class1_probability"
        for record, row, item in zip(selected, rows, evidence, strict=True):
            require(record["partition"] == "BASE_TRAIN" and int(record["fold"]) == int(row["outer_fold"])
                    and int(record["label"]) == int(row["label"])
                    and record["lineage_group"] == row["lineage_group"]
                    and int(record["input_tokens"]) == item["input_tokens"]
                    and record["B2_schema_sha256"] == driver.core.B2_SHA
                    and record["score_kind"] == kind and record["calibrated_probability"] == "", "prediction metadata mismatch")
        scores = np.asarray([float(r["raw_score"]) for r in selected])
        require(np.isfinite(scores).all(), "nonfinite score")
        for index, point in enumerate(metrics[scorer]["recall_at_fixed_fpr"]):
            predicted = np.zeros(len(rows), dtype=bool) if point["no_positive_predictions"] else scores >= point["descriptive_threshold"]
            masks = {"ALL": np.ones(len(rows), dtype=bool),
                     **{b: np.asarray([short_bucket(e["input_tokens"]) == b for e in evidence])
                        for b in driver.core.features.SHORT_BUCKETS},
                     "combined_<32": np.asarray([e["input_tokens"] < 32 for e in evidence])}
            for bucket, mask in masks.items():
                result = point if bucket == "ALL" else groups[scorer][bucket]["pooled_frontiers"][index]
                tp = int(sum(mask & (labels == 1) & predicted))
                fp = int(sum(mask & (labels == 0) & predicted))
                positive, negative = int(sum(mask & (labels == 1))), int(sum(mask & (labels == 0)))
                require((result["tp"], result["fn"], result["fp"], result["tn"]) ==
                        (tp, positive - tp, fp, negative - fp), "independent confusion counts mismatch")
                require(result["recall"] == (tp / positive if positive else None), "independent recall mismatch")
                key = "attained_fpr" if bucket == "ALL" else "fpr"
                require(result[key] == (fp / negative if negative else None), "independent FPR mismatch")
            if index == 1:
                votes[scorer] = predicted
    def bank(mask):
        return {"count": int(sum(mask)), "sample_ids": [sid for sid, v in zip(ids, mask, strict=True) if v]}
    for scorer in ("S1", "S2"):
        old, new = votes["S0"], votes[scorer]
        require(errors["versus_S0"][scorer] == {
            "LR_FN_recovered": bank((labels == 1) & ~old & new),
            "new_FN": bank((labels == 1) & old & ~new),
            "LR_FP_recovered": bank((labels == 0) & old & ~new),
            "new_FP": bank((labels == 0) & ~old & new)}, "independent transition banks mismatch")
    require(errors["shared_FN"] == bank((labels == 1) & ~np.logical_or.reduce(list(votes.values()))), "shared FN mismatch")
    for scorer in votes:
        mask = (labels == 1) & votes[scorer] & ~np.logical_or.reduce([v for s, v in votes.items() if s != scorer])
        require(errors["unique_catches"][scorer] == bank(mask), "unique catch mismatch")
    return {"prediction_metadata_checks": 3405, "independent_frontier_confusion_checks": 54,
            "exact_error_bank_checks": 12, "status": "PASS"}


def verify_evidence():
    driver.source.install_gate({"source_artifact_sha256": {}})
    with patch.object(LogisticRegression, "fit", side_effect=AssertionError("classifier refit forbidden")), \
         patch.object(SVC, "fit", side_effect=AssertionError("classifier refit forbidden")), \
         patch.object(HistGradientBoostingClassifier, "fit", side_effect=AssertionError("classifier refit forbidden")):
        driver.check()
        rows, _ = driver.baseline.selected_metadata()
        evidence = driver.source.load_cache(rows, driver.stat004.CACHE_SHA)
        with (OUT / "scorer_predictions_v1.csv").open(encoding="utf-8", newline="") as handle:
            independent = independently_check_records(list(csv.DictReader(handle)), rows, evidence)
    return independent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("record", "check"), required=True)
    args = parser.parse_args()
    path = OUT / "acceptance_evidence_v1.json"
    if args.mode == "check":
        previous = driver.read(path)
        driver.baseline.verify_hashes(driver.ROOT, previous["verification_code_sha256"])
        driver.baseline.verify_hashes(OUT, previous["verified_sha256"])
        driver.baseline.verify_hashes(driver.ROOT, previous["report_sha256"])
    independent = verify_evidence()
    if args.mode == "record":
        suite = ET.parse(OUT / "acceptance_tests_v1.xml").getroot().find("testsuite")
        require(int(suite.attrib["tests"]) == 177 and all(int(suite.attrib[k]) == 0 for k in ("failures", "errors", "skipped")), "test acceptance failed")
        metadata = driver.read(OUT / "run_metadata_v1.json")
        inputs = ("scorer_definitions_v1.json", "preflight_v1.json", "prerun_tests_v1.xml", "postrun_tests_v1.xml",
                  "acceptance_tests_v1.xml", "run_started_v1.json", "run_metadata_v1.json")
        driver.write(path, {"phase": "TECH-STAT-005", "status": "PASS", "model_run_code_commit": metadata["code_commit"],
            "recommendation": "RECOMMEND_D_S_CYCLE_2", "selected_scorer": "S0", "cycle": "1_OF_MAXIMUM_2",
            "tests": {k: suite.attrib[k] for k in ("tests", "failures", "errors", "skipped", "time")},
            "independent_reconstruction": independent, "classifier_refits": 0, "output_hash_checks": 8,
            "prior_STAT003_output_hash_checks": 9, "prior_STAT004_output_hash_checks": 9,
            "preserved_evidence_hash_checks": 101, "baseline_preservation": driver.baseline.baseline_check(),
            "identity_leakage": 0, "lineage_leakage": 0,
            "verified_sha256": {**metadata["artifact_sha256"], **{n: driver.file_hash(OUT / n) for n in inputs}},
            "verification_code_sha256": {p: driver.file_hash(driver.ROOT / p) for p in CODE},
            "report_sha256": {p.relative_to(driver.ROOT).as_posix(): driver.file_hash(p)
                              for p in (driver.ROOT / "reviews").glob("TECH_STAT_005*.md")},
            "scope": "Post-run verification only; five references/scalers reconstructed, zero classifier refits. No final model, cycle 2 or calibration."})
    else:
        require(independent == previous["independent_reconstruction"], "independent acceptance drift")
    print(json.dumps({"status": "PASS", "mode": args.mode, "independent": independent, "classifier_refits": 0}))


if __name__ == "__main__":
    main()
