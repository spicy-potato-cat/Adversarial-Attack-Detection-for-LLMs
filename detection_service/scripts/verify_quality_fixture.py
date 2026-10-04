"""Run QUALITY-001 checks/tests under a model-import and payload-open deny gate."""

import importlib.abc
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
DENIED_ROOTS = (ROOT / "Dataset", ROOT / "PHASE-3", ROOT / "detection_service/outputs",
                ROOT / "artifacts/models", ROOT / "detection_service/.model-cache")
DENIED_IMPORTS = ("torch", "transformers", "sentence_transformers", "sklearn", "joblib",
                  "detection_service.app.detectors", "detection_service.app.main")


class NoModelImports(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if any(fullname == name or fullname.startswith(name + ".") for name in DENIED_IMPORTS):
            raise RuntimeError(f"QUALITY-001 prohibits model imports: {fullname}")
        return None


def main():
    evidence = {"denied_payload_open_attempts": [], "model_imports": [], "tests": {}}

    def audit(event, args):
        if event != "open" or not isinstance(args[0], (str, bytes, os.PathLike)):
            return
        path = Path(os.fsdecode(args[0])).resolve()
        if any(path == root or root in path.parents for root in DENIED_ROOTS):
            evidence["denied_payload_open_attempts"].append(str(path))
            raise RuntimeError("QUALITY-001 prohibits payload/model access")

    class Results:
        def pytest_terminal_summary(self, terminalreporter):
            for key in ("passed", "failed", "skipped", "error"):
                evidence["tests"][key] = len(terminalreporter.stats.get(key, []))

    sys.addaudithook(audit)
    sys.meta_path.insert(0, NoModelImports())
    os.environ["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    from detection_service.quality.development_fixture import verify
    evidence["integrity"] = verify()
    import pytest
    result = pytest.main([str(ROOT / "detection_service/tests/test_quality_fixture.py"), "-q"], plugins=[Results()])
    evidence["model_imports"] = sorted(name for name in sys.modules
                                        if any(name == prefix or name.startswith(prefix + ".") for prefix in DENIED_IMPORTS))
    evidence["status"] = "PASS" if result == 0 and not evidence["denied_payload_open_attempts"] and not evidence["model_imports"] else "FAIL"
    destination = ROOT / "artifacts/quality/quality_001/test_evidence_v1.json"
    if destination.exists():
        raise RuntimeError("test evidence already exists; refuse overwrite")
    with destination.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(evidence, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")
    print(json.dumps(evidence, indent=2))
    return 0 if evidence["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
