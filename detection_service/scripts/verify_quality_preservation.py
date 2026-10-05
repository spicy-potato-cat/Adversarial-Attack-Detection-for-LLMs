"""Hash baseline files without deserializing models or executing detectors."""

import argparse
import json
from pathlib import Path
import subprocess

from detection_service.quality.development_fixture import ROOT, file_hash, json_bytes, require
from detection_service.quality.policy import ARTIFACT_DIR

BASELINE_PATHS = ["detection_service/app", "detection_service/configs",
                  *[f"artifacts/models/{name}" for name in ("ds_v1", "dm_a_v1", "dm_b_v1", "dg_v1")]]
EVIDENCE = ROOT / ARTIFACT_DIR / "baseline_preservation_v1.json"


def paths():
    # Weight/cache files are not opened. Small serialized classifiers are hashed,
    # never loaded. All application code and frozen metadata are included.
    return sorted({p.relative_to(ROOT).as_posix() for folder in BASELINE_PATHS
                   for p in (ROOT / folder).rglob("*")
                   if p.is_file() and p.suffix in (".py", ".json", ".joblib")
                   and "__pycache__" not in p.parts})


def check_git():
    result = subprocess.run(["git", "diff", "--exit-code", "43f1405", "--", *BASELINE_PATHS],
                            cwd=ROOT, capture_output=True, text=True, check=False)
    require(result.returncode == 0, "baseline tracked files differ from start commit")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", required=True, choices=("snapshot", "check"))
    args = parser.parse_args()
    check_git()
    actual = {p: file_hash(ROOT / p) for p in paths()}
    if args.mode == "snapshot":
        require(not EVIDENCE.exists(), "preservation evidence already exists")
        EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
        payload = {"start_commit": "43f1405", "sha256": actual, "model_weights_opened": False,
                   "models_deserialized": False, "tracked_baseline_diff": "EMPTY"}
        with EVIDENCE.open("xb") as handle:
            handle.write(json_bytes(payload))
    else:
        payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
        require(actual == payload["sha256"], "baseline preservation drift")
    print(json.dumps({"status": "PASS", "hash_checks": len(actual),
                      "evidence_sha256": file_hash(EVIDENCE), "tracked_baseline_diff": "EMPTY"}, indent=2))


if __name__ == "__main__":
    main()
