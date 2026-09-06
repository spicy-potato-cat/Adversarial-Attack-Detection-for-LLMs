#!/usr/bin/env python3
"""Controlled acquisition and immutable-raw promotion for Pilot 01."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import platform
import shutil
import stat
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_VERSION = "0.1.0"
ALLOWED_UNCERTAINTY = {"UNKNOWN", "NOT_VERIFIED", "PARTIAL", "NOT_APPLICABLE"}
REQUIRED_FIELDS = {
    "dataset_id", "artifact_id", "name", "artifact_type", "official_source",
    "paper", "repository", "dataset_card", "release", "commit", "revision",
    "resolved_revision", "retrieval_method", "license_reference",
    "upstream_rights_status", "provenance_status", "intended_pilot_action",
    "acquisition_status", "url", "filename"
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_manifest(data: dict) -> None:
    if data.get("pilot_id") != "PILOT-01":
        raise ValueError("manifest pilot_id must be PILOT-01")
    seen = set()
    for index, artifact in enumerate(data.get("artifacts", [])):
        missing = REQUIRED_FIELDS - artifact.keys()
        if missing:
            raise ValueError(f"artifact {index} missing fields: {sorted(missing)}")
        if artifact["artifact_id"] in seen:
            raise ValueError(f"duplicate artifact_id: {artifact['artifact_id']}")
        seen.add(artifact["artifact_id"])
        for key in ("release", "commit", "revision", "resolved_revision"):
            if artifact[key] == "":
                raise ValueError(f"{artifact['artifact_id']} disguises unknown {key} as empty")


def validate_structure(path: Path) -> dict:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            rows = sum(1 for _ in reader)
            fields = reader.fieldnames or []
        if not fields:
            raise ValueError(f"CSV has no header: {path}")
        return {"format": "csv", "records": rows, "fields": fields}
    if suffix == ".json":
        with path.open("r", encoding="utf-8") as handle:
            value = json.load(handle)
        size = len(value) if isinstance(value, (list, dict)) else 1
        return {"format": "json", "top_level_type": type(value).__name__, "top_level_size": size}
    if suffix == ".txt":
        text = path.read_text(encoding="utf-8")
        return {"format": "text", "characters": len(text)}
    raise ValueError(f"unsupported pilot artifact format: {suffix}")


def append_audit(log_path: Path, event: dict) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(event, sort_keys=True) + "\n")


def acquire(manifest_path: Path, workspace: Path) -> None:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    validate_manifest(manifest)
    staging = workspace / "01_acquisition" / "staging" / "PILOT-01"
    raw_root = workspace / "01_acquisition" / "raw" / "PILOT-01"
    log_path = workspace / "logs" / "PILOT-01_acquisition_audit.jsonl"
    staging.mkdir(parents=True, exist_ok=True)
    raw_root.mkdir(parents=True, exist_ok=True)
    run_id = "PILOT-01-ACQ-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    for artifact in manifest["artifacts"]:
        if artifact["acquisition_status"] == "ACQUIRED_VERIFIED":
            continue
        artifact_id = artifact["artifact_id"]
        staged_path = staging / f"{artifact_id}__{artifact['filename']}"
        raw_dir = raw_root / artifact_id
        raw_path = raw_dir / artifact["filename"]
        event_base = {"run_id": run_id, "timestamp": datetime.now(timezone.utc).isoformat(),
                      "script": __file__, "script_version": SCRIPT_VERSION,
                      "artifact_id": artifact_id, "url": artifact["url"]}
        try:
            request = urllib.request.Request(artifact["url"], headers={"User-Agent": "Phase3-Pilot01/0.1"})
            with urllib.request.urlopen(request, timeout=60) as response, staged_path.open("wb") as output:
                shutil.copyfileobj(response, output)
            staged_hash = sha256_file(staged_path)
            structure = validate_structure(staged_path)
            raw_dir.mkdir(parents=True, exist_ok=True)
            if raw_path.exists():
                os.chmod(raw_path, stat.S_IWRITE | stat.S_IREAD)
                if sha256_file(raw_path) != staged_hash:
                    raise ValueError(f"existing raw artifact hash mismatch: {raw_path}")
                staged_path.unlink()
            else:
                os.replace(staged_path, raw_path)
            os.chmod(raw_path, stat.S_IREAD)
            promoted_hash = sha256_file(raw_path)
            if promoted_hash != staged_hash:
                raise ValueError("post-promotion hash differs from staged hash")
            artifact.update({"acquisition_status": "ACQUIRED_VERIFIED", "acquired_at": event_base["timestamp"],
                             "byte_size": raw_path.stat().st_size, "sha256": promoted_hash,
                             "raw_path": raw_path.relative_to(workspace).as_posix(),
                             "structure": structure, "immutability_control": "READ_ONLY_FILE_ATTRIBUTE",
                             "immutability_limitation": "Local owner can restore write permission; integrity is enforced by SHA-256 verification."})
            append_audit(log_path, {**event_base, "event": "PROMOTED_TO_RAW", "status": "SUCCESS",
                                    "sha256": promoted_hash, "byte_size": raw_path.stat().st_size,
                                    "structure": structure})
        except Exception as exc:
            artifact.update({"acquisition_status": "FAILED", "failure": str(exc)})
            append_audit(log_path, {**event_base, "event": "ACQUISITION_FAILED", "status": "FAILED", "error": str(exc)})

    manifest["last_run"] = {"run_id": run_id, "timestamp": datetime.now(timezone.utc).isoformat(),
                            "script_version": SCRIPT_VERSION, "python": sys.version,
                            "platform": platform.platform(), "status": "COMPLETE_WITH_RECORDED_FAILURES"}
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

    hash_path = workspace / "01_acquisition" / "hashes" / "PILOT-01_hashes.csv"
    hash_path.parent.mkdir(parents=True, exist_ok=True)
    with hash_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["artifact_id", "dataset_id", "byte_size", "sha256", "raw_path", "status"])
        writer.writeheader()
        for a in manifest["artifacts"]:
            writer.writerow({"artifact_id": a["artifact_id"], "dataset_id": a["dataset_id"],
                             "byte_size": a.get("byte_size", "NOT_MEASURED"), "sha256": a.get("sha256", "NOT_MEASURED"),
                             "raw_path": a.get("raw_path", "NOT_APPLICABLE"), "status": a["acquisition_status"]})


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    acquire(args.manifest.resolve(), args.workspace.resolve())


if __name__ == "__main__":
    main()
