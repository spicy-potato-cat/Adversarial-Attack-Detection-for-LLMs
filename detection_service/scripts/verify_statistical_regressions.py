"""Synthetic combined regressions; do not open development/protected rows."""
import json
import os
import sys
from pathlib import Path

import pytest

from detection_service.scripts.verify_guard_regressions import Evidence, EXCLUDED


def main():
    root = Path(__file__).resolve().parents[2]
    violations = []
    blocked = [root / name for name in ("Dataset", "PHASE-3", "data_governance", "experiment_readiness")]
    def audit(event, args):
        if event == "open" and isinstance(args[0], (str, bytes, os.PathLike)):
            path = Path(os.fsdecode(args[0])).resolve()
            if any(path.is_relative_to(directory) for directory in blocked):
                violations.append(str(path))
                raise RuntimeError("Actual project/protected data reads forbidden in synthetic regressions")
    sys.addaudithook(audit)
    evidence = Evidence()
    code = pytest.main(["detection_service/tests", "-q", "-k", " and ".join("not " + name for name in EXCLUDED),
                        "--basetemp", str(root / "detection_service/outputs/stat002-regression-temp"),
                        "--junitxml", str(root / "detection_service/outputs/stat002-tests.xml")], plugins=[evidence])
    result = {"exit_code": int(code), "passed": sum(r["outcome"] == "passed" for r in evidence.reports),
              "failed": sum(r["outcome"] == "failed" for r in evidence.reports),
              "skipped": sum(r["outcome"] == "skipped" for r in evidence.reports),
              "deselected": evidence.deselected, "reports": evidence.reports, "project_data_access_attempts": violations,
              "scope": "Synthetic regression only; Python open audit enforced; native I/O not intercepted"}
    output = root / "detection_service/outputs/stat002-test-evidence.json"
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    raise SystemExit(code)


if __name__ == "__main__":
    main()
