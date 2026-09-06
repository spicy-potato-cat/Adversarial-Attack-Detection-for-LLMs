#!/usr/bin/env python3
"""Bounded Wave 2 extension of the Pilot-01 forensic workflow."""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import json
import mmap
import os
import platform
import re
import statistics
import struct
import subprocess
import sys
import tempfile
import time
from array import array
from collections import Counter, defaultdict
from functools import lru_cache
from itertools import combinations
from pathlib import Path

from pilot01_forensics import CANON_IDS, canonicalize, jaccard, shingles, write_json


SCRIPT_VERSION = "0.1.1"
csv.field_size_limit(min(sys.maxsize, 2_147_483_647))
WAVE2_IDS = ["DS-TXT-001", "DS-TXT-002", "DS-TXT-016", "DS-TXT-017", "DS-TXT-018"]
PILOT_IDS = ["DS-TXT-007", "DS-TXT-008", "DS-TXT-009", "DS-TXT-013", "DS-TXT-014", "DS-TXT-015"]
DATASET_IDS = WAVE2_IDS + PILOT_IDS
DATASET_INDEX = {value:index for index,value in enumerate(DATASET_IDS)}
WAVE2_MASK = (1 << len(WAVE2_IDS)) - 1
LEDGER = struct.Struct("<B32s32s32s")
SIGNATURE = struct.Struct("<128Q")
EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
URL = re.compile(r"\b(?:https?://|www\.)\S+", re.IGNORECASE)
IPV4 = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
PHONE = re.compile(r"(?<!\w)(?:\+?\d[\d .()\-]{7,}\d)(?!\w)")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(value: str) -> bytes:
    return hashlib.sha256(value.encode("utf-8")).digest()


def percentile(values: list[int], fraction: float):
    if not values:
        return "NOT_MEASURED"
    return sorted(values)[min(len(values) - 1, int(fraction * len(values)))]


def dataset_pairs():
    pairs = list(combinations(range(len(WAVE2_IDS)), 2))
    pairs.extend((left, right) for left in range(len(WAVE2_IDS)) for right in range(len(WAVE2_IDS), len(DATASET_IDS)))
    return pairs


TARGET_PAIRS = dataset_pairs()
TARGET_PAIR_SET = {frozenset(pair) for pair in TARGET_PAIRS}


def bits(mask: int):
    while mask:
        low = mask & -mask
        yield low.bit_length() - 1
        mask ^= low


def has_target_pair(left_mask: int, right_mask: int) -> bool:
    if not ((left_mask | right_mask) & WAVE2_MASK):
        return False
    return any(left != right and frozenset((left, right)) in TARGET_PAIR_SET
               for left in bits(left_mask) for right in bits(right_mask))


def parquet_rows(path: Path, artifact_id: str, duckdb: Path, temp_root: Path):
    output = temp_root / f"{artifact_id}.jsonl"
    if output.exists():
        output.unlink()
    source = str(path.resolve()).replace("\\", "/").replace("'", "''")
    target = str(output.resolve()).replace("\\", "/").replace("'", "''")
    query = f"COPY (SELECT * FROM read_parquet('{source}')) TO '{target}' (FORMAT JSON, ARRAY false);"
    completed = subprocess.run([str(duckdb), "-c", query], capture_output=True, text=True)
    if completed.returncode:
        raise RuntimeError(f"DuckDB failed for {artifact_id}: {completed.stderr.strip()}")
    try:
        with output.open("r", encoding="utf-8") as handle:
            for index, line in enumerate(handle, start=1):
                yield f"parquet_row:{index}", json.loads(line)
    finally:
        output.unlink(missing_ok=True)


def source_rows(path: Path, artifact: dict, duckdb: Path, temp_root: Path):
    file_format = artifact["format"]
    if file_format in {"csv", "tsv"}:
        delimiter = "\t" if file_format == "tsv" else ","
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            for index, row in enumerate(csv.DictReader(handle, delimiter=delimiter), start=1):
                yield f"{file_format}_row:{index}", row
    elif file_format == "jsonl":
        with path.open("r", encoding="utf-8") as handle:
            for index, line in enumerate(handle, start=1):
                if line.strip():
                    yield f"jsonl_row:{index}", json.loads(line)
    elif file_format == "parquet":
        yield from parquet_rows(path, artifact["artifact_id"], duckdb, temp_root)
    else:
        raise ValueError(f"unsupported format: {file_format}")


def adapt(artifact_id: str, row: dict) -> dict:
    if artifact_id == "ART-W2-WJ-TRAIN":
        adversarial = row.get("adversarial") or ""
        vanilla = row.get("vanilla") or ""
        return {"text":adversarial or vanilla,"response":row.get("completion"),"source_id":None,
                "label":row.get("data_type"),"category":None,"base":vanilla or None,
                "adversarial":adversarial or None,
                "metadata":{"data_type":row.get("data_type")},
                "generation_method":"WildTeaming" if adversarial else "SYNTHETIC_VANILLA",
                "generator":"UNKNOWN","upstream":"UNKNOWN"}
    if artifact_id == "ART-W2-WJ-EVAL":
        return {"text":row.get("adversarial"),"response":None,"source_id":None,
                "label":{"label":row.get("label"),"data_type":row.get("data_type")},"category":None,
                "base":None,"adversarial":row.get("adversarial"),"metadata":{"data_type":row.get("data_type")},
                "generation_method":"WildTeaming","generator":"UNKNOWN","upstream":"UNKNOWN"}
    if artifact_id in {"ART-W2-WGM-TRAIN", "ART-W2-WGM-TEST"}:
        is_adversarial = row.get("adversarial") is True
        label = {key:row.get(key) for key in ("prompt_harm_label","response_refusal_label","response_harm_label")}
        metadata = {key:value for key,value in row.items() if key not in {"prompt","response"}}
        return {"text":row.get("prompt"),"response":row.get("response"),"source_id":None,
                "label":label,"category":row.get("subcategory"),
                "base":None if is_adversarial else row.get("prompt"),
                "adversarial":row.get("prompt") if is_adversarial else None,"metadata":metadata,
                "generation_method":"UNKNOWN","generator":"UNKNOWN","upstream":"UNKNOWN"}
    if artifact_id == "ART-W2-SALAD-EXAMPLE":
        return {"text":row.get("question"),"response":row.get("answer"),"source_id":None,
                "label":row.get("label"),"category":None,"base":row.get("question"),"adversarial":None,
                "metadata":{},"generation_method":"UNKNOWN","generator":"UNKNOWN","upstream":"UNKNOWN"}
    if artifact_id == "ART-W2-DNA-INSTRUCTIONS":
        return {"text":row.get("question"),"response":None,"source_id":str(row.get("id")) if row.get("id") not in (None, "") else None,
                "label":None,"category":row.get("risk_area"),"base":row.get("question"),"adversarial":None,
                "metadata":{key:row.get(key) for key in ("risk_area","types_of_harm","specific_harms")},
                "generation_method":"CURATED_AND_FILTERED","generator":"NOT_APPLICABLE","upstream":"UNKNOWN"}
    if artifact_id in {"ART-W2-DEEPSET-TRAIN", "ART-W2-DEEPSET-TEST"}:
        return {"text":row.get("text"),"response":None,"source_id":None,
                "label":row.get("label"),"category":None,"base":row.get("text"),"adversarial":None,
                "metadata":{},"generation_method":"UNKNOWN","generator":"UNKNOWN","upstream":"UNKNOWN"}
    raise KeyError(artifact_id)


def expected_fields(artifact_id: str) -> set[str]:
    return {
        "ART-W2-WJ-TRAIN":{"vanilla","adversarial","completion","data_type"},
        "ART-W2-WJ-EVAL":{"adversarial","label","data_type"},
        "ART-W2-WGM-TRAIN":{"prompt","adversarial","response","prompt_harm_label","response_refusal_label","response_harm_label","subcategory"},
        "ART-W2-WGM-TEST":{"prompt","adversarial","response","prompt_harm_label","response_refusal_label","response_harm_label","subcategory"},
        "ART-W2-SALAD-EXAMPLE":{"question","answer","label"},
        "ART-W2-DNA-INSTRUCTIONS":{"id","risk_area","types_of_harm","specific_harms","question"},
        "ART-W2-DEEPSET-TRAIN":{"text","label"},
        "ART-W2-DEEPSET-TEST":{"text","label"},
    }[artifact_id]


def minhash_coefficients(num_perm: int, seed: int):
    prime = (1 << 61) - 1
    result = []
    for index in range(num_perm):
        a = int.from_bytes(hashlib.sha256(f"{seed}:a:{index}".encode()).digest()[:8], "big") % (prime - 1) + 1
        b = int.from_bytes(hashlib.sha256(f"{seed}:b:{index}".encode()).digest()[:8], "big") % prime
        result.append((a, b))
    return prime, result


def minhash_signature(text: str, prime: int, coefficients: list[tuple[int,int]]):
    values = shingles(text)
    if not values:
        return tuple([prime] * len(coefficients))
    base = [int.from_bytes(hashlib.sha256("\0".join(value).encode("utf-8")).digest()[:8], "big") % prime for value in values]
    return tuple(min((a * value + b) % prime for value in base) for a,b in coefficients)


def write_gzip_jsonl(path: Path, records):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
            with io.TextIOWrapper(compressed, encoding="utf-8", newline="\n") as text:
                for record in records:
                    text.write(json.dumps(record, sort_keys=True, ensure_ascii=True, separators=(",", ":")) + "\n")


def run(args) -> None:
    started = time.time()
    workspace = args.workspace.resolve()
    local_root = args.local_root.resolve()
    duckdb = args.duckdb.resolve()
    manifest_path = args.manifest.resolve()
    config_path = args.config.resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    config = json.loads(config_path.read_text(encoding="utf-8"))
    inventory_path = workspace / "01_acquisition" / "hashes" / "local_bundle_inventory.csv"
    if sha256_file(inventory_path) != config["inventory_sha256"]:
        raise RuntimeError("frozen inventory hash mismatch")
    if sha256_file(duckdb) != config["parquet_reader"]["sha256"]:
        raise RuntimeError("DuckDB tool hash mismatch")

    artifacts = []
    dataset_info = {}
    for dataset in manifest["datasets"]:
        dataset_info[dataset["dataset_id"]] = dataset
        for artifact in dataset["record_bearing_files"]:
            item = dict(artifact)
            item["dataset_id"] = dataset["dataset_id"]
            item["dataset_name"] = dataset["dataset_name"]
            item["repository_revision"] = dataset["repository_revision"]
            item["dataset_revision"] = dataset["dataset_revision"]
            artifacts.append(item)

    initial_hashes = {}
    for artifact in artifacts:
        path = local_root / artifact["path"]
        actual = sha256_file(path)
        if actual != artifact["sha256"]:
            raise RuntimeError(f"raw integrity mismatch: {artifact['artifact_id']}")
        initial_hashes[artifact["artifact_id"]] = actual

    quality = {}
    privacy = {dataset_id:Counter(records_screened=0,email_candidates=0,url_candidates=0,
                                  ipv4_candidates=0,phone_candidates=0,identifier_records=0)
               for dataset_id in WAVE2_IDS}
    for artifact in artifacts:
        quality[artifact["artifact_id"]] = {
            "artifact_id":artifact["artifact_id"],"dataset_id":artifact["dataset_id"],
            "expected_records":artifact["records"],"counts":Counter(total_records=0,valid_records=0,
            null_text=0,empty_text=0,missing_ids=0,missing_source_labels=0,
            schema_mismatch_records=0,malformed_records=0,encoding_errors=0,
            records_with_unknown_metadata=0),"ids":Counter(),"lengths":[],"observed_fields":set()
        }

    entity_index = {}
    entity_hashes = []
    entity_texts = []
    entity_masks = array("H")
    entity_counts = [array("I") for _ in DATASET_IDS]
    behavior_counts = [Counter() for _ in DATASET_IDS]
    dataset_record_counts = Counter()
    non_analyzable = []

    with tempfile.TemporaryDirectory(prefix="wave2-forensics-") as temp_name:
        temp_root = Path(temp_name)
        ledger_path = temp_root / "hash-ledger.bin"
        with ledger_path.open("wb") as ledger:
            for artifact in artifacts:
                path = local_root / artifact["path"]
                state = quality[artifact["artifact_id"]]
                for locator, row in source_rows(path, artifact, duckdb, temp_root):
                    state["counts"]["total_records"] += 1
                    state["observed_fields"].update(str(key) for key in row)
                    if not expected_fields(artifact["artifact_id"]).issubset(row):
                        state["counts"]["schema_mismatch_records"] += 1
                    mapped = adapt(artifact["artifact_id"], row)
                    value = mapped["text"]
                    if value is None:
                        state["counts"]["null_text"] += 1
                        non_analyzable.append({
                            "dataset_id":artifact["dataset_id"], "artifact_id":artifact["artifact_id"],
                            "original_row_locator":locator, "reason":"NULL_ACTIVE_TEXT",
                            "original_record":{"type":"IMMUTABLE_REFERENCE", "artifact_sha256":artifact["sha256"], "locator":locator}
                        })
                        continue
                    if not isinstance(value, str) or not value.strip():
                        state["counts"]["empty_text"] += 1
                        non_analyzable.append({
                            "dataset_id":artifact["dataset_id"], "artifact_id":artifact["artifact_id"],
                            "original_row_locator":locator, "reason":"EMPTY_ACTIVE_TEXT",
                            "original_record":{"type":"IMMUTABLE_REFERENCE", "artifact_sha256":artifact["sha256"], "locator":locator}
                        })
                        continue
                    state["counts"]["valid_records"] += 1
                    state["lengths"].append(len(value))
                    if mapped["source_id"] is None:
                        state["counts"]["missing_ids"] += 1
                    else:
                        state["ids"][mapped["source_id"]] += 1
                    label_missing = mapped["label"] in (None, "") or (
                        isinstance(mapped["label"], dict) and all(value in (None, "") for value in mapped["label"].values())
                    )
                    if label_missing:
                        state["counts"]["missing_source_labels"] += 1
                    if mapped["generator"] == "UNKNOWN" or mapped["upstream"] == "UNKNOWN":
                        state["counts"]["records_with_unknown_metadata"] += 1

                    n0 = canonicalize(value, "N0")
                    n1 = canonicalize(value, "N1")
                    n2 = canonicalize(value, "N2")
                    hashes = (sha256_text(n0), sha256_text(n1), sha256_text(n2))
                    dataset_idx = DATASET_INDEX[artifact["dataset_id"]]
                    ledger.write(LEDGER.pack(dataset_idx, *hashes))
                    dataset_record_counts[artifact["dataset_id"]] += 1
                    index = entity_index.get(hashes[1])
                    if index is None:
                        index = len(entity_texts)
                        entity_index[hashes[1]] = index
                        entity_hashes.append(hashes[1])
                        entity_texts.append(n1)
                        entity_masks.append(0)
                        for counts in entity_counts:
                            counts.append(0)
                    entity_masks[index] |= 1 << dataset_idx
                    entity_counts[dataset_idx][index] += 1
                    base = mapped["base"]
                    if base:
                        behavior_counts[dataset_idx][sha256_text(canonicalize(str(base), "N1"))] += 1

                    combined = value + "\n" + (mapped["response"] or "")
                    screen = privacy[artifact["dataset_id"]]
                    screen["records_screened"] += 1
                    screen["email_candidates"] += bool(EMAIL.search(combined))
                    screen["url_candidates"] += bool(URL.search(combined))
                    screen["ipv4_candidates"] += bool(IPV4.search(combined))
                    screen["phone_candidates"] += bool(PHONE.search(combined))
                    screen["identifier_records"] += mapped["source_id"] is not None
                print(f"PASS1 {artifact['artifact_id']} records={state['counts']['total_records']}", flush=True)

            pilot_path = workspace / "03_schema" / "PILOT-01_normalized_records.jsonl"
            with pilot_path.open("r", encoding="utf-8") as handle:
                for line in handle:
                    record = json.loads(line)
                    dataset_id = record["source"]["dataset_id"]
                    dataset_idx = DATASET_INDEX[dataset_id]
                    raw_hash = bytes.fromhex(record["forensics"]["raw_text_sha256"])
                    n1_hash = bytes.fromhex(record["forensics"]["N1_sha256"])
                    n2_hash = bytes.fromhex(record["forensics"]["N2_sha256"])
                    ledger.write(LEDGER.pack(dataset_idx, raw_hash, n1_hash, n2_hash))
                    dataset_record_counts[dataset_id] += 1
                    index = entity_index.get(n1_hash)
                    if index is None:
                        value = record["source"].get("raw_text") or record["source"].get("prompt")
                        index = len(entity_texts)
                        entity_index[n1_hash] = index
                        entity_hashes.append(n1_hash)
                        entity_texts.append(canonicalize(value, "N1"))
                        entity_masks.append(0)
                        for counts in entity_counts:
                            counts.append(0)
                    entity_masks[index] |= 1 << dataset_idx
                    entity_counts[dataset_idx][index] += 1
                    base = record["source"].get("base_behavior_text")
                    if base:
                        behavior_counts[dataset_idx][sha256_text(canonicalize(str(base), "N1"))] += 1

        quality_output = []
        for artifact in artifacts:
            state = quality[artifact["artifact_id"]]
            lengths = state.pop("lengths")
            identifiers = state.pop("ids")
            state["counts"]["duplicate_ids"] = sum(1 for count in identifiers.values() if count > 1)
            state["counts"]["duplicate_id_records"] = sum(count - 1 for count in identifiers.values() if count > 1)
            state["counts"] = dict(state["counts"])
            state["record_count_status"] = "VERIFIED" if state["counts"]["total_records"] == state["expected_records"] else "MISMATCH"
            state["observed_fields"] = sorted(state["observed_fields"])
            state["length_definition"] = "Unicode code points in active N0 text"
            state["lengths"] = {"minimum":min(lengths) if lengths else "NOT_MEASURED",
                                "median":statistics.median(lengths) if lengths else "NOT_MEASURED",
                                "p95":percentile(lengths, .95),"maximum":max(lengths) if lengths else "NOT_MEASURED"}
            if artifact["artifact_id"] == "ART-W2-WJ-TRAIN":
                state["documented_schema_difference"] = "README lists tactics; local TSV header does not contain tactics"
            quality_output.append(state)

        exact = {"wave":"WAVE-2","scope":"WAVE2_WITH_PILOT01","dataset_record_counts":dict(dataset_record_counts),"views":{}}
        for view_index, view in enumerate(("N0","N1","N2")):
            counters = [Counter() for _ in DATASET_IDS]
            with ledger_path.open("rb") as handle:
                while block := handle.read(LEDGER.size):
                    unpacked = LEDGER.unpack(block)
                    counters[unpacked[0]][unpacked[view_index + 1]] += 1
            combined = Counter()
            for counter in counters:
                combined.update(counter)
            sizes = Counter(count for count in combined.values() if count > 1)
            within = {}
            for index,dataset_id in enumerate(DATASET_IDS):
                cluster_counts = [count for count in counters[index].values() if count > 1]
                within[dataset_id] = {"cluster_count":len(cluster_counts),"participating_records":sum(cluster_counts)}
            pairwise = {}
            for left,right in TARGET_PAIRS:
                shared = counters[left].keys() & counters[right].keys()
                left_count = sum(counters[left][key] for key in shared)
                right_count = sum(counters[right][key] for key in shared)
                pairwise[f"{DATASET_IDS[left]}|{DATASET_IDS[right]}"] = {
                    "shared_unique_hashes":len(shared),
                    "a_to_b":{"count":left_count,"denominator":dataset_record_counts[DATASET_IDS[left]],
                              "percent":round(100*left_count/dataset_record_counts[DATASET_IDS[left]], 4)},
                    "b_to_a":{"count":right_count,"denominator":dataset_record_counts[DATASET_IDS[right]],
                              "percent":round(100*right_count/dataset_record_counts[DATASET_IDS[right]], 4)},
                }
            representatives = []
            for key,count in sorted(combined.items(), key=lambda item:(-item[1], item[0]))[:100]:
                if count < 2:
                    break
                representatives.append({"cluster_id":f"DUP-{view}-{key.hex()[:16]}","records":count,
                                        "datasets":{DATASET_IDS[index]:counters[index][key] for index in range(len(DATASET_IDS)) if counters[index][key]}})
            exact["views"][view] = {"cluster_count":sum(sizes.values()),"participating_records":sum(size*count for size,count in sizes.items()),
                                    "cluster_size_distribution":{str(size):count for size,count in sorted(sizes.items())},
                                    "within_dataset":within,"pairwise":pairwise,"representative_clusters":representatives}
            print(f"EXACT {view} clusters={exact['views'][view]['cluster_count']}", flush=True)

        canonical_path = workspace / "03_schema" / "WAVE-2_normalized_records.jsonl.gz"
        def canonical_records():
            for artifact in artifacts:
                path = local_root / artifact["path"]
                info = dataset_info[artifact["dataset_id"]]
                source_version = info["dataset_revision"] if info["dataset_revision"] != "UNKNOWN" else info["repository_revision"]
                if source_version == "NOT_APPLICABLE":
                    source_version = "UNKNOWN"
                rights_status = {"DS-TXT-001":"CONDITIONAL","DS-TXT-002":"CONDITIONAL","DS-TXT-016":"UNKNOWN",
                                 "DS-TXT-017":"CONDITIONAL","DS-TXT-018":"UNKNOWN"}[artifact["dataset_id"]]
                for locator,row in source_rows(path, artifact, duckdb, temp_root):
                    mapped = adapt(artifact["artifact_id"], row)
                    value = mapped["text"]
                    if not isinstance(value, str) or not value.strip():
                        continue
                    n0,n1,n2 = (canonicalize(value, view) for view in ("N0","N1","N2"))
                    hashes = (sha256_text(n0), sha256_text(n1), sha256_text(n2))
                    index = entity_index[hashes[1]]
                    material = f"{artifact['dataset_id']}\0{artifact['artifact_id']}\0{artifact['sha256']}\0{locator}".encode()
                    sample_id = "W2-" + hashlib.sha256(material).hexdigest()[:24]
                    base_same = mapped["base"] == value
                    quarantine = ["rights_review","provenance_review","pii_review"]
                    if artifact["dataset_id"] == "DS-TXT-016":
                        quarantine.append("missing_full_dataset")
                    yield {
                        "schema_version":"0.2","sample_id":sample_id,
                        "source":{"dataset_id":artifact["dataset_id"],"dataset_name":artifact["dataset_name"],
                                  "artifact_id":artifact["artifact_id"],"source_revision":source_version,
                                  "artifact_sha256":artifact["sha256"],"original_row_locator":locator,
                                  "original_sample_id":mapped["source_id"],
                                  "original_record":{"type":"IMMUTABLE_REFERENCE","artifact_sha256":artifact["sha256"],"locator":locator},
                                  "original_label":mapped["label"],"original_category":mapped["category"],
                                  "original_metadata":mapped["metadata"],"raw_text":value,"raw_response":mapped["response"],
                                  "base_behavior_text":None if base_same else mapped["base"],
                                  "base_behavior_relation":"RAW_TEXT_IS_BASE_BEHAVIOR" if base_same else "SEPARATE_OR_UNKNOWN",
                                  "adversarial_prompt":mapped["adversarial"]},
                        "labels":{"normalized_binary_label":"UNKNOWN","normalized_attack_family":"UNKNOWN","normalized_attack_subtype":"UNKNOWN"},
                        "generation":{"generation_method":mapped["generation_method"],"generator":mapped["generator"]},
                        "lineage":{"upstream_dataset":mapped["upstream"],"upstream_sample_id":"UNKNOWN","evidence_state":"UNKNOWN"},
                        "forensics":{"canonicalization_ids":CANON_IDS,"N0_sha256":hashes[0].hex(),"N1_sha256":hashes[1].hex(),"N2_sha256":hashes[2].hex(),
                                     "duplicate_cluster_id":f"DUP-N1-{hashes[1].hex()[:16]}" if sum(counts[index] for counts in entity_counts) > 1 else None},
                        "derived":{"N1_text":n1 if n1 != n0 else None,"N2_text":n2 if n2 != n1 else None},
                        "rights":{"license_status":rights_status,"provenance_status":info["revision_status"],"PII_status":"REVIEW_REQUIRED"},
                        "governance":{"forensic_analysis_access":"ALLOWED","train_allowed":"FALSE","evaluation_only":"UNKNOWN",
                                      "experimental_role":"NOT_ASSIGNED","quarantine_reason":quarantine}
                    }
                print(f"PASS2 {artifact['artifact_id']}", flush=True)
        write_gzip_jsonl(canonical_path, canonical_records())

        near_config = config["near_duplicate"]
        prime, coefficients = minhash_coefficients(near_config["num_perm"], near_config["random_seed"])
        signature_path = temp_root / "minhash-signatures.bin"
        with signature_path.open("wb") as signature_file:
            for index,text in enumerate(entity_texts, start=1):
                signature_file.write(SIGNATURE.pack(*minhash_signature(text, prime, coefficients)))
                if index % 10000 == 0:
                    print(f"MINHASH {index}/{len(entity_texts)}", flush=True)

        candidates = set()
        with signature_path.open("rb") as handle:
            mapped_signatures = mmap.mmap(handle.fileno(), 0, access=mmap.ACCESS_READ)
            try:
                for band in range(near_config["bands"]):
                    buckets = {}
                    band_offset = band * near_config["rows_per_band"] * 8
                    for index in range(len(entity_texts)):
                        values = struct.unpack_from("<4Q", mapped_signatures, index * SIGNATURE.size + band_offset)
                        key = 1469598103934665603
                        for value in values:
                            key = ((key ^ value) * 1099511628211) & 0xFFFFFFFFFFFFFFFF
                        previous = buckets.get(key)
                        if previous is None:
                            buckets[key] = index
                            continue
                        previous_items = (previous,) if isinstance(previous, int) else previous
                        for other in previous_items:
                            if has_target_pair(entity_masks[index], entity_masks[other]):
                                left,right = (other,index) if other < index else (index,other)
                                candidates.add((left << 32) | right)
                                if len(candidates) > near_config["candidate_cap"]:
                                    raise RuntimeError("near-duplicate candidate cap exceeded")
                        if isinstance(previous, int):
                            buckets[key] = [previous,index]
                        else:
                            previous.append(index)
                    print(f"LSH band={band+1}/{near_config['bands']} candidates={len(candidates)}", flush=True)
            finally:
                mapped_signatures.close()

        thresholds = near_config["candidate_thresholds"]
        matched = {str(threshold):defaultdict(set) for threshold in thresholds}
        exact_identity_entities = Counter()
        for index,mask in enumerate(entity_masks):
            present = list(bits(mask))
            for left,right in combinations(present, 2):
                pair = frozenset((left,right))
                if pair not in TARGET_PAIR_SET:
                    continue
                exact_identity_entities[f"{DATASET_IDS[min(left,right)]}|{DATASET_IDS[max(left,right)]}"] += 1
                for threshold in thresholds:
                    matched[str(threshold)][(left,right)].add(index)
                    matched[str(threshold)][(right,left)].add(index)

        @lru_cache(maxsize=50000)
        def entity_shingles(index: int):
            return shingles(entity_texts[index])

        threshold_pair_counts = Counter()
        representatives = []
        for candidate_number,encoded in enumerate(candidates, start=1):
            left = encoded >> 32
            right = encoded & 0xFFFFFFFF
            score = jaccard(entity_shingles(left), entity_shingles(right))
            if score < thresholds[0]:
                continue
            representatives.append({"left_n1_sha256":entity_hashes[left].hex(),"right_n1_sha256":entity_hashes[right].hex(),"score":round(score,8)})
            left_datasets = list(bits(entity_masks[left]))
            right_datasets = list(bits(entity_masks[right]))
            for threshold in thresholds:
                if score < threshold:
                    continue
                threshold_pair_counts[str(threshold)] += 1
                for dataset_a in left_datasets:
                    for dataset_b in right_datasets:
                        if dataset_a == dataset_b or frozenset((dataset_a,dataset_b)) not in TARGET_PAIR_SET:
                            continue
                        matched[str(threshold)][(dataset_a,dataset_b)].add(left)
                        matched[str(threshold)][(dataset_b,dataset_a)].add(right)
            if candidate_number % 100000 == 0:
                print(f"JACCARD {candidate_number}/{len(candidates)}", flush=True)
        representatives = sorted(representatives, key=lambda item:(-item["score"], item["left_n1_sha256"], item["right_n1_sha256"]))[:near_config["representative_pair_limit"]]

        near_pairwise = {}
        for left,right in TARGET_PAIRS:
            cell = {}
            for threshold in thresholds:
                key = str(threshold)
                left_count = sum(entity_counts[left][index] for index in matched[key][(left,right)])
                right_count = sum(entity_counts[right][index] for index in matched[key][(right,left)])
                cell[key] = {"a_to_b":{"count":left_count,"denominator":dataset_record_counts[DATASET_IDS[left]],
                                       "percent":round(100*left_count/dataset_record_counts[DATASET_IDS[left]],4)},
                             "b_to_a":{"count":right_count,"denominator":dataset_record_counts[DATASET_IDS[right]],
                                       "percent":round(100*right_count/dataset_record_counts[DATASET_IDS[right]],4)}}
            near_pairwise[f"{DATASET_IDS[left]}|{DATASET_IDS[right]}"] = cell
        near = {"wave":"WAVE-2","status":"MEASURED","configuration":near_config,"unique_n1_entities":len(entity_texts),
                "candidate_pairs_evaluated":len(candidates),"verified_distinct_entity_pairs":dict(threshold_pair_counts),
                "exact_identity_entities_by_dataset_pair":dict(exact_identity_entities),"pairwise":near_pairwise,
                "representative_pairs":representatives,
                "pair_count_note":"Verified distinct-entity counts exclude exact-identical N1 entities; directional rates include exact identity."}

        behavior_pairwise = {}
        for left,right in TARGET_PAIRS:
            shared = behavior_counts[left].keys() & behavior_counts[right].keys()
            left_count = sum(behavior_counts[left][key] for key in shared)
            right_count = sum(behavior_counts[right][key] for key in shared)
            left_denom = sum(behavior_counts[left].values())
            right_denom = sum(behavior_counts[right].values())
            behavior_pairwise[f"{DATASET_IDS[left]}|{DATASET_IDS[right]}"] = {
                "status":"MEASURED","relationship":"IDENTICAL_N1_BASE_BEHAVIOR_TEXT",
                "shared_unique_hashes":len(shared),
                "a_to_b":{"count":left_count,"denominator":left_denom,"percent":round(100*left_count/left_denom,4) if left_denom else "NOT_MEASURED"},
                "b_to_a":{"count":right_count,"denominator":right_denom,"percent":round(100*right_count/right_denom,4) if right_denom else "NOT_MEASURED"},
            }
        behavior = {"wave":"WAVE-2","method":"N1 identity of source-preserved base behavior; similarity alone does not prove lineage",
                    "eligible_records":{DATASET_IDS[index]:sum(counter.values()) for index,counter in enumerate(behavior_counts)},
                    "pairwise":behavior_pairwise}

        documented = {
            "DS-TXT-001|DS-TXT-009":{"status":"VERIFIED","relationship":"WildJailbreak documents XSTest as conceptual motivation for benign contrast construction, not sample reuse."}
        }
        contamination_pairs = []
        for left,right in TARGET_PAIRS:
            pair_key = f"{DATASET_IDS[left]}|{DATASET_IDS[right]}"
            doc = documented.get(pair_key, {"status":"UNKNOWN","relationship":"UNKNOWN"})
            exact_cell = {view:exact["views"][view]["pairwise"][pair_key] for view in ("N0","N1","N2")}
            measured_match = exact_cell["N1"]["shared_unique_hashes"] > 0 or near_pairwise[pair_key]["0.8"]["a_to_b"]["count"] > 0 or behavior_pairwise[pair_key]["shared_unique_hashes"] > 0
            contamination_pairs.append({"dataset_a":DATASET_IDS[left],"dataset_b":DATASET_IDS[right],
                                        "exact":exact_cell,"lexical_near":near_pairwise[pair_key],
                                        "semantic":{"status":"NOT_MEASURED","decision":"DEC-P3-007"},
                                        "documented_lineage":doc,"behavior_level":behavior_pairwise[pair_key],
                                        "evidence_state":"DOCUMENTED_AND_MEASURED" if doc["status"] != "UNKNOWN" and measured_match else
                                                         "DOCUMENTED" if doc["status"] != "UNKNOWN" else "MEASURED"})
        contamination = {"wave":"WAVE-2","scope":"WITHIN_WAVE2_AND_WAVE2_TO_PILOT01","pairs":contamination_pairs,
                         "directional_definition":"A records with at least one verified B relation / all eligible A records",
                         "semantic_status":"NOT_MEASURED"}

        final_hashes = {artifact["artifact_id"]:sha256_file(local_root / artifact["path"]) for artifact in artifacts}
        if final_hashes != initial_hashes:
            raise RuntimeError("selected raw artifact changed during Wave 2 run")

        outputs = {}
        outputs["quality"] = write_json(workspace/"04_quality"/"WAVE-2_quality.json", {"wave":"WAVE-2","artifacts":quality_output})
        outputs["non_analyzable"] = write_json(
            workspace/"04_quality"/"WAVE-2_non_analyzable_records.json",
            {"wave":"WAVE-2", "status":"MEASURED", "records":non_analyzable,
             "handling":"Excluded from text-comparison denominators; preserved by immutable artifact hash and row locator."}
        )
        outputs["exact"] = write_json(workspace/"05_exact_duplicates"/"WAVE-2_exact_overlap.json", exact)
        outputs["near"] = write_json(workspace/"06_near_duplicates"/"WAVE-2_lexical_overlap.json", near)
        outputs["behavior"] = write_json(workspace/"08_provenance"/"WAVE-2_behavior_lineage.json", behavior)
        outputs["contamination"] = write_json(workspace/"11_contamination_matrix"/"WAVE-2_contamination_matrix.json", contamination)
        outputs["canonical_records"] = sha256_file(canonical_path)
        outputs["manifest"] = sha256_file(manifest_path)
        outputs["config"] = sha256_file(config_path)
        outputs["inventory"] = sha256_file(inventory_path)
        run_log = {"run_id":f"WAVE-2-FORENSICS-{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}",
                   "script_version":SCRIPT_VERSION,"status":"SUCCESS","duration_seconds":round(time.time()-started,3),
                   "python":sys.version,"platform":platform.platform(),"duckdb_version":"v1.4.1",
                   "wave2_record_count":sum(dataset_record_counts[dataset_id] for dataset_id in WAVE2_IDS),
                   "expanded_record_count":sum(dataset_record_counts.values()),"selected_raw_hashes_before":initial_hashes,
                   "selected_raw_hashes_after":final_hashes,"outputs":outputs}
        write_json(workspace/"logs"/"WAVE-2_forensic_run.json", run_log)
        write_json(workspace/"09_legal_privacy"/"WAVE-2_privacy_screen.json",
                   {"wave":"WAVE-2","method":"non-destructive regex candidate screen over active text plus response",
                    "datasets":{dataset_id:dict(counts) for dataset_id,counts in privacy.items()},
                    "interpretation":"Candidate counts are not confirmed PII; zero candidates does not prove absence.",
                    "overall_status":"REVIEW_REQUIRED"})
        print(json.dumps({"status":"SUCCESS","wave2_records":run_log["wave2_record_count"],
                          "unique_n1_entities":len(entity_texts),"candidates":len(candidates),
                          "duration_seconds":run_log["duration_seconds"]}), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--local-root", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--duckdb", type=Path, required=True)
    run(parser.parse_args())


if __name__ == "__main__":
    main()
