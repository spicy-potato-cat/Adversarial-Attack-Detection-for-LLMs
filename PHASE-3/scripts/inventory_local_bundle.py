#!/usr/bin/env python3
"""Read-only streaming inventory of the Commander-provided local bundle."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import platform
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_VERSION = "0.1.0"
PILOT_MAP = {
    "LLM-Attacks": ("DS-TXT-013", "AdvBench / GCG official repository"),
    "AutoDAN": ("DS-TXT-015", "AutoDAN official repository"),
    "HarmBench": ("DS-TXT-007", "HarmBench official repository"),
    "JailbreakBench": ("DS-TXT-008", "JailbreakBench official repository"),
    "XSTest": ("DS-TXT-009", "XSTest official repository"),
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def map_file(path: Path, root: Path):
    relative = path.relative_to(root)
    parts = relative.parts
    source = parts[0] if parts else "UNKNOWN"
    collection = parts[1] if len(parts) > 1 else "NOT_APPLICABLE"
    dataset_id, mapping = PILOT_MAP.get(collection, ("NOT_MAPPED_PILOT_01", "INVENTORY_ONLY"))
    return relative.as_posix(), source, collection, dataset_id, mapping


def run(root: Path, output: Path, summary_path: Path) -> None:
    started = datetime.now(timezone.utc)
    files = sorted((path for path in root.rglob("*") if path.is_file()), key=lambda p: p.as_posix().casefold())
    output.parent.mkdir(parents=True, exist_ok=True)
    counts = Counter()
    source_bytes = Counter()
    collection_bytes = Counter()
    failures = []
    with output.open("w", encoding="utf-8", newline="") as handle:
        fields = ["relative_path","source_channel","collection","dataset_id","mapping_status","size_bytes",
                  "sha256","modified_utc","attributes","inventory_status"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for path in files:
            relative, source, collection, dataset_id, mapping = map_file(path, root)
            try:
                stat = path.stat()
                digest = sha256_file(path)
                status = "HASHED_VERIFIED"
                counts["hashed_files"] += 1
                counts["total_bytes"] += stat.st_size
                source_bytes[source] += stat.st_size
                collection_bytes[f"{source}/{collection}"] += stat.st_size
                row = {"relative_path":relative,"source_channel":source,"collection":collection,
                       "dataset_id":dataset_id,"mapping_status":mapping,"size_bytes":stat.st_size,"sha256":digest,
                       "modified_utc":datetime.fromtimestamp(stat.st_mtime,timezone.utc).isoformat(),
                       "attributes":"READ_ONLY" if not os.access(path,os.W_OK) else "WRITABLE_BY_CURRENT_PROCESS",
                       "inventory_status":status}
            except Exception as exc:
                counts["failed_files"] += 1
                failures.append({"relative_path":relative,"error":str(exc)})
                row = {"relative_path":relative,"source_channel":source,"collection":collection,
                       "dataset_id":dataset_id,"mapping_status":mapping,"size_bytes":"NOT_MEASURED",
                       "sha256":"NOT_MEASURED","modified_utc":"NOT_MEASURED","attributes":"NOT_MEASURED",
                       "inventory_status":"FAILED"}
            writer.writerow(row)
    output_hash = sha256_file(output)
    completed = datetime.now(timezone.utc)
    summary = {
        "inventory_version":"0.1","run_id":"PILOT-01-LOCAL-INVENTORY-"+started.strftime("%Y%m%dT%H%M%SZ"),
        "started_at":started.isoformat(),"completed_at":completed.isoformat(),"script_version":SCRIPT_VERSION,
        "root":str(root),"root_policy":"COMMANDER_PROVIDED_RAW_READ_ONLY_INPUT","network_access":"DISABLED",
        "file_count_discovered":len(files),"hashed_files":counts["hashed_files"],"failed_files":counts["failed_files"],
        "total_bytes":counts["total_bytes"],"source_bytes":dict(sorted(source_bytes.items())),
        "collection_bytes":dict(sorted(collection_bytes.items())),"failures":failures,
        "inventory_csv":str(output),"inventory_csv_sha256":output_hash,"python":sys.version,"platform":platform.platform()
    }
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary,indent=2,ensure_ascii=True)+"\n",encoding="utf-8")


def main():
    parser=argparse.ArgumentParser(); parser.add_argument("--root",type=Path,required=True); parser.add_argument("--output",type=Path,required=True); parser.add_argument("--summary",type=Path,required=True)
    args=parser.parse_args(); run(args.root.resolve(),args.output.resolve(),args.summary.resolve())


if __name__ == "__main__": main()
