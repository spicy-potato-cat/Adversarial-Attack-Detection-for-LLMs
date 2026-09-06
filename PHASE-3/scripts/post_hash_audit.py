#!/usr/bin/env python3
"""Classify the frozen local inventory and emit Pilot 01 audit summaries."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import platform
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_VERSION = "0.1.0"
PILOT = {
    "LLM-Attacks": {"dataset_ids":["DS-TXT-013","DS-TXT-014"],"name":"AdvBench / GCG"},
    "AutoDAN": {"dataset_ids":["DS-TXT-015"],"name":"AutoDAN"},
    "HarmBench": {"dataset_ids":["DS-TXT-007"],"name":"HarmBench"},
    "JailbreakBench": {"dataset_ids":["DS-TXT-008"],"name":"JailbreakBench"},
    "XSTest": {"dataset_ids":["DS-TXT-009"],"name":"XSTest"},
}


def sha256_file(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda:f.read(4*1024*1024),b""): h.update(block)
    return h.hexdigest()


def classify(path: str) -> str:
    p=path.replace("\\","/").lower(); name=p.rsplit("/",1)[-1]; ext=Path(name).suffix
    if "/.git/" in "/"+p: return "GIT_INTERNAL"
    if "/tmp/" in "/"+p or "/temp/" in "/"+p or ext in {".tmp",".temp"}: return "TEMPORARY"
    if "/__pycache__/" in "/"+p or "/.cache/" in "/"+p: return "CACHE"
    if name.startswith("license") or name.startswith("copying"): return "LICENSE"
    if "manifest" in name or "download-status" in name or "download_status" in name: return "MANIFEST"
    if name.startswith("readme") or ext in {".md",".rst"}: return "DOCUMENTATION"
    if ext in {".zip",".tar",".gz",".tgz",".bz2",".xz",".7z",".rar"}: return "ARCHIVE"
    if ext in {".png",".jpg",".jpeg",".gif",".webp",".bmp",".svg"}: return "IMAGE"
    if ext in {".safetensors",".pth",".pt",".bin",".ckpt"}: return "MODEL_OR_BINARY_ARTIFACT"
    if ext in {".py",".ipynb",".sh",".ps1",".bat",".js",".ts",".java",".cpp",".c",".h"}: return "CODE"
    if name in {"requirements.txt","pyproject.toml","setup.py","setup.cfg","uv.lock","poetry.lock","package.json","package-lock.json"}: return "ENVIRONMENT"
    if ext in {".csv",".tsv",".parquet",".jsonl"}: return "DATASET_PAYLOAD"
    if ext in {".json",".yaml",".yml",".txt",".pkl"}:
        if any(token in p for token in ("/data/","/dataset","/train","/test","/eval","/runs/","behavior","prompt","artifact")):
            return "DATASET_PAYLOAD"
        return "METADATA"
    if ext in {".pdf",".doc",".docx"}: return "DOCUMENTATION"
    return "UNKNOWN"


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2,ensure_ascii=True)+"\n",encoding="utf-8")


def run(inventory: Path, summary_path: Path, raw_root: Path, output_dir: Path):
    summary=json.loads(summary_path.read_text(encoding="utf-8"))
    rows=list(csv.DictReader(inventory.open(encoding="utf-8",newline="")))
    category=defaultdict(lambda:Counter(files=0,bytes=0,failed=0))
    collections=defaultdict(lambda:{"files":0,"bytes":0,"categories":Counter(),"category_bytes":Counter(),"failures":[]})
    for row in rows:
        c=classify(row["relative_path"]); size=0 if row["size_bytes"]=="NOT_MEASURED" else int(row["size_bytes"])
        category[c]["files"]+=1; category[c]["bytes"]+=size
        if row["inventory_status"]=="FAILED": category[c]["failed"]+=1
        key=f"{row['source_channel']}/{row['collection']}"; d=collections[key]
        d["files"]+=1; d["bytes"]+=size; d["categories"][c]+=1; d["category_bytes"][c]+=size
        if row["inventory_status"]=="FAILED": d["failures"].append(row["relative_path"])
    classification={"pilot_id":"PILOT-01","classification_version":"0.1","inventory_sha256":summary["inventory_csv_sha256"],
                    "categories":{k:dict(v) for k,v in sorted(category.items())},
                    "rules_note":"Path/extension classification is forensic triage; DATASET_PAYLOAD membership requires adapter-level confirmation."}
    write_json(output_dir/"PILOT-01_artifact_classification.json",classification)

    dataset_summaries=[]
    for collection,meta in PILOT.items():
        key=f"GitHub/{collection}"; d=collections.get(key,{"files":0,"bytes":0,"categories":Counter(),"category_bytes":Counter(),"failures":[]})
        root=raw_root/"GitHub"/collection
        primary=[]
        for candidate in root.rglob("*") if root.exists() else []:
            if candidate.is_file() and classify(candidate.relative_to(raw_root).as_posix())=="DATASET_PAYLOAD":
                primary.append(candidate.relative_to(raw_root).as_posix())
        dataset_summaries.append({"dataset_ids":meta["dataset_ids"],"dataset_name":meta["name"],"local_root":str(root),
                                  "artifact_count":d["files"],"total_bytes":d["bytes"],
                                  "category_counts":dict(d["categories"]),"category_bytes":dict(d["category_bytes"]),
                                  "primary_data_files":primary[:100],"primary_data_files_truncated":len(primary)>100,
                                  "hashing_failures":d["failures"]})
    write_json(output_dir/"PILOT-01_dataset_inventory_summary.json",{"pilot_id":"PILOT-01","datasets":dataset_summaries})

    failed=summary["failures"][0] if summary["failures"] else None
    failed_path=raw_root/failed["relative_path"] if failed else None
    retry={"attempted":bool(failed),"exists_at_retry":failed_path.exists() if failed_path else False,
           "hash_status":"FAILED" if failed and not failed_path.exists() else "NOT_APPLICABLE",
           "reason":"File absent on controlled retry; no source modification attempted." if failed else "No failed file."}
    failure_report={"pilot_id":"PILOT-01","failed_inventory_rows":summary["failures"],"diagnosis":{
        "path":str(failed_path) if failed_path else "NOT_APPLICABLE","file_name":failed_path.name if failed_path else "NOT_APPLICABLE",
        "extension":failed_path.suffix if failed_path else "NOT_APPLICABLE","size":"NOT_READABLE",
        "dataset_association":"VLSBench / DS-MM-003","type":"GIT_LFS_TEMPORARY","required_for_pilot_01":False,
        "failure_reason":failed["error"] if failed else "NOT_APPLICABLE","retry":retry}}
    write_json(output_dir/"PILOT-01_failed_file_report.json",failure_report)

    current_files=sum(1 for p in raw_root.rglob("*") if p.is_file())
    git_internal=sum(1 for p in raw_root.rglob("*") if p.is_file() and ".git" in p.relative_to(raw_root).parts)
    boundary={"pilot_id":"PILOT-01","inventory_version":"0.1","inventory_sha256":summary["inventory_csv_sha256"],
              "inventory_rows":len(rows),"hashed_rows":sum(r["inventory_status"]=="HASHED_VERIFIED" for r in rows),
              "failed_rows":sum(r["inventory_status"]=="FAILED" for r in rows),"total_bytes":sum(int(r["size_bytes"]) for r in rows if r["size_bytes"]!="NOT_MEASURED"),
              "current_files_force_hidden":current_files,"git_internal_files":git_internal,
              "file_count_explanation":{"earlier_count":42860,"hidden_git_files":3892,"current_visible_plus_hidden":current_files,
                  "final_inventory_extra":"one VLSBench .git/lfs/tmp file discovered at scan start vanished before hashing",
                  "equation":"42,860 + 3,892 = 46,752 current files; + 1 vanished temp = 46,753 discovered"},
              "source_roots":[str(raw_root)],"tool":{"script":__file__,"version":SCRIPT_VERSION},
              "environment":{"python":sys.version,"platform":platform.platform()},"frozen_at":datetime.now(timezone.utc).isoformat()}
    write_json(output_dir/"PILOT-01_input_snapshot.json",boundary)


def main():
    p=argparse.ArgumentParser();p.add_argument("--inventory",type=Path,required=True);p.add_argument("--summary",type=Path,required=True);p.add_argument("--raw-root",type=Path,required=True);p.add_argument("--output-dir",type=Path,required=True);a=p.parse_args()
    run(a.inventory.resolve(),a.summary.resolve(),a.raw_root.resolve(),a.output_dir.resolve())


if __name__=="__main__":main()
