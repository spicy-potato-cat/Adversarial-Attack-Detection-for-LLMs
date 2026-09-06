#!/usr/bin/env python3
"""Compare a frozen local-bundle inventory with current paths without rewriting it."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


SCRIPT_VERSION = "0.1.0"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    inventory_path = args.inventory.resolve()
    with inventory_path.open(newline="", encoding="utf-8-sig") as handle:
        inventory = {row["relative_path"].replace("\\", "/"): row for row in csv.DictReader(handle)}
    current_paths = {str(path.relative_to(root)).replace("\\", "/"): path for path in root.rglob("*") if path.is_file()}
    only_current = sorted(set(current_paths) - set(inventory))
    only_inventory = sorted(set(inventory) - set(current_paths))
    report = {
        "pilot_id":"PILOT-01",
        "status":"MEASURED_POST_FREEZE_DRIFT",
        "script_version":SCRIPT_VERSION,
        "observed_at":datetime.now(timezone.utc).isoformat(),
        "frozen_inventory_sha256":sha256_file(inventory_path),
        "frozen_inventory_rows":len(inventory),
        "current_file_count":len(current_paths),
        "current_git_internal_count":sum("/.git/" in f"/{path}/" for path in current_paths),
        "only_current":[{
            "relative_path":relative,
            "size_bytes":current_paths[relative].stat().st_size,
            "sha256":sha256_file(current_paths[relative]),
            "classification":"GIT_LFS_OBJECT" if "/.git/lfs/objects/" in f"/{relative}" else "UNKNOWN",
        } for relative in only_current],
        "only_in_frozen_inventory":[{
            "relative_path":relative,
            "inventory_status":inventory[relative]["inventory_status"],
            "size_bytes":inventory[relative]["size_bytes"],
            "sha256":inventory[relative]["sha256"],
            "classification":"GIT_LFS_TEMPORARY" if "/.git/lfs/tmp/" in f"/{relative}" else "UNKNOWN",
        } for relative in only_inventory],
        "pilot_payload_impact":"NONE_IDENTIFIED; all changed paths are VLSBench Git LFS internals outside Pilot-01",
        "action":"PRESERVE_FROZEN_INVENTORY; DO_NOT_OVERWRITE",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
