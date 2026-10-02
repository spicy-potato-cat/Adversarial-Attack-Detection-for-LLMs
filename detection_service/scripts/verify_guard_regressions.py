"""Run synthetic regression checks with an audit barrier against project-data reads."""
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

EXCLUDED = (
    "test_development_manifest_hash_and_partition_boundaries",
    "test_manifest_integrity_count_and_calibration_membership",
    "test_cross_partition_lineage_is_rejected",
    "test_protected_source_and_bad_label_mapping_are_rejected",
    "test_text_loader_rejects_non_calibration_rows_before_file_access",
    "test_text_loader_reads_only_approved_files_and_verifies_selected_text",
    "test_manifest_boundary_and_class_weights_base_train_only",
    "test_calibration_partition_count_and_manifest_integrity",
    "test_selected_calibration_texts_only_and_approved_source_access",
)


class Evidence:
    def __init__(self):
        self.reports = []
        self.deselected = []

    def pytest_runtest_logreport(self, report):
        if report.when == "call" or (report.when in ("setup", "teardown") and report.failed):
            self.reports.append({"nodeid": report.nodeid, "outcome": report.outcome, "duration": report.duration})

    def pytest_deselected(self, items):
        self.deselected.extend(item.nodeid for item in items)


def main():
    root = Path(__file__).resolve().parents[2]
    blocked = [root / name for name in ("Dataset", "PHASE-3", "data_governance", "experiment_readiness")]
    violations = []
    def audit(event, args):
        if event == "open" and isinstance(args[0], (str, bytes, os.PathLike)):
            path = Path(os.fsdecode(args[0])).resolve()
            if any(path.is_relative_to(directory) for directory in blocked):
                violations.append(str(path.relative_to(root)))
                raise RuntimeError("Project-data access forbidden during guard verification")
    sys.addaudithook(audit)
    evidence = Evidence()
    code = pytest.main([
        "detection_service/tests", "-q", "-k", " and ".join("not " + name for name in EXCLUDED),
        "--basetemp", str(root / "detection_service/outputs/guard-regression-temp"),
        "--junitxml", str(root / "detection_service/outputs/guard-regressions.xml"),
    ], plugins=[evidence])
    result = {
        "exit_code": int(code), "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "Synthetic engineering regression only; project-data tests intentionally deselected",
        "passed": sum(r["outcome"] == "passed" for r in evidence.reports),
        "failed": sum(r["outcome"] == "failed" for r in evidence.reports),
        "skipped": sum(r["outcome"] == "skipped" for r in evidence.reports),
        "deselected": evidence.deselected, "reports": evidence.reports,
        "project_data_access_attempts": violations,
        "audit_barrier": "Python open audit denies actual Dataset/PHASE-3/data_governance/experiment_readiness roots; native I/O not intercepted",
    }
    (root / "artifacts/models/dg_v1/test_evidence.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8", newline="\n")
    raise SystemExit(code)


if __name__ == "__main__":
    main()
