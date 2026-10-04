"""Synthetic TECH-STAT-003 tests with project-payload and reference-weight denial."""

import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]


def main():
    evidence = {"prohibited_open_attempts": [], "counts": {}}
    forbidden = [ROOT / p for p in ("Dataset", "PHASE-3", "detection_service/outputs", "detection_service/.model-cache")]

    def audit(event, args):
        if event == "open" and isinstance(args[0], (str, bytes, os.PathLike)):
            path = Path(os.fsdecode(args[0])).resolve()
            if any(path == root or root in path.parents for root in forbidden) or path.suffix in (".safetensors", ".joblib"):
                evidence["prohibited_open_attempts"].append(str(path))
                raise RuntimeError("Synthetic OOF tests cannot open project payloads or reference weights")

    class Results:
        def pytest_terminal_summary(self, terminalreporter):
            evidence["counts"] = {k: len(terminalreporter.stats.get(k, [])) for k in ("passed", "failed", "skipped", "error")}

    sys.addaudithook(audit)
    os.environ["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    import pytest
    result = pytest.main([str(ROOT / "detection_service/tests/test_statistical_oof.py"), "-q"], plugins=[Results()])
    evidence["status"] = "PASS" if result == 0 and not evidence["prohibited_open_attempts"] else "FAIL"
    destination = ROOT / "artifacts/statistical_v2/oof/test_evidence_v1.json"
    with destination.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(evidence, handle, indent=2, sort_keys=True)
        handle.write("\n")
    print(json.dumps(evidence, indent=2))
    return result


if __name__ == "__main__":
    sys.exit(main())
