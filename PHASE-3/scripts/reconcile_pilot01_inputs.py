#!/usr/bin/env python3
"""Reconcile Commander-local Pilot-01 files with the pinned evidence copies."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import unicodedata
from datetime import datetime, timezone
from pathlib import Path


SCRIPT_VERSION = "0.1.0"
PAIRS = (
    ("ART-P01-ADV-001", "GitHub/LLM-Attacks/data/advbench/harmful_behaviors.csv", "ART-P01-ADV-001/harmful_behaviors.csv"),
    ("ART-P01-AUTODAN-001", "GitHub/AutoDAN/data/advbench/harmful_behaviors.csv", "ART-P01-AUTODAN-001/harmful_behaviors.csv"),
    ("ART-P01-AUTODAN-002", "GitHub/AutoDAN/assets/autodan_initial_prompt.txt", "ART-P01-AUTODAN-002/autodan_initial_prompt.txt"),
    ("ART-P01-HB-001", "GitHub/HarmBench/data/behavior_datasets/harmbench_behaviors_text_all.csv", "ART-P01-HB-001/harmbench_behaviors_text_all.csv"),
    ("ART-P01-HB-002", "GitHub/HarmBench/data/behavior_datasets/extra_behavior_datasets/tdc2023_test_phase_behaviors.csv", "ART-P01-HB-002/tdc2023_test_phase_behaviors.csv"),
    ("ART-P01-HB-003", "GitHub/HarmBench/data/behavior_datasets/extra_behavior_datasets/advbench_behaviors.csv", "ART-P01-HB-003/advbench_behaviors.csv"),
    ("ART-P01-XSTEST-001", "GitHub/XSTest/xstest_prompts.csv", "ART-P01-XSTEST-001/xstest_prompts.csv"),
)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def n1(data: bytes) -> str:
    text = data.decode("utf-8")
    return unicodedata.normalize("NFC", text.replace("\r\n", "\n").replace("\r", "\n"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--local-root", type=Path, required=True)
    args = parser.parse_args()
    workspace = args.workspace.resolve()
    local_root = args.local_root.resolve()
    inventory_path = workspace / "01_acquisition" / "hashes" / "local_bundle_inventory.csv"
    with inventory_path.open(newline="", encoding="utf-8-sig") as handle:
        inventory = {row["relative_path"].replace("\\", "/"): row for row in csv.DictReader(handle)}

    comparisons = []
    for artifact_id, local_relative, pinned_relative in PAIRS:
        local_path = local_root / Path(local_relative)
        pinned_path = workspace / "01_acquisition" / "raw" / "PILOT-01" / Path(pinned_relative)
        local_bytes = local_path.read_bytes()
        pinned_bytes = pinned_path.read_bytes()
        inventory_row = inventory[local_relative]
        local_hash = sha256(local_bytes)
        comparisons.append({
            "artifact_id": artifact_id,
            "local_relative_path": local_relative,
            "pinned_relative_path": str(pinned_path.relative_to(workspace)).replace("\\", "/"),
            "local_bytes": len(local_bytes),
            "pinned_bytes": len(pinned_bytes),
            "local_sha256": local_hash,
            "pinned_sha256": sha256(pinned_bytes),
            "byte_identical": local_bytes == pinned_bytes,
            "n1_text_identical": n1(local_bytes) == n1(pinned_bytes),
            "matches_frozen_inventory": local_hash == inventory_row["sha256"],
        })

    report = {
        "pilot_id": "PILOT-01",
        "script_version": SCRIPT_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "inventory_sha256": sha256(inventory_path.read_bytes()),
        "comparisons": comparisons,
        "local_equivalent_not_identified": [
            {"artifact_id": artifact_id, "pilot_availability": "AVAILABLE_IN_PRE_UPDATE_PINNED_RAW", "download_action": "NONE"}
            for artifact_id in ("ART-P01-JBB-001", "ART-P01-JBB-002", "ART-P01-JBB-003", "ART-P01-GCG-001")
        ],
        "interpretation": "Byte differences with N1 identity are consistent with checkout line-ending conversion; this is not byte-level identity.",
    }
    output = workspace / "01_acquisition" / "manifests" / "PILOT-01_post_hash" / "PILOT-01_local_reconciliation.json"
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
