#!/usr/bin/env python3
"""Deterministic pilot adapters and overlap analysis using the standard library."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import re
import statistics
import sys
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path

SCRIPT_VERSION = "0.1.0"
CANON_IDS = {"N0":"CANON-N0-v0.1", "N1":"CANON-N1-v0.1", "N2":"CANON-N2-v0.1"}
TEXT_KEYS = ("Goal", "goal", "Behavior", "behavior", "prompt", "Prompt", "adversarial_prompt", "query")
ID_KEYS = ("BehaviorID", "behavior_id", "Behavior", "behavior", "id", "Index", "index")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def canonicalize(text: str, view: str) -> str:
    if view == "N0":
        return text
    value = unicodedata.normalize("NFC", text).replace("\r\n", "\n").replace("\r", "\n")
    if view == "N1":
        return value
    if view == "N2":
        return re.sub(r"\s+", " ", value, flags=re.UNICODE).strip()
    raise ValueError(f"unknown canonicalization view: {view}")


def manifest_validate(manifest: dict) -> None:
    if manifest.get("pilot_id") != "PILOT-01":
        raise ValueError("wrong pilot manifest")
    for item in manifest.get("artifacts", []):
        if item.get("acquisition_status") == "ACQUIRED_VERIFIED":
            for field in ("sha256", "raw_path", "byte_size"):
                if field not in item:
                    raise ValueError(f"verified artifact lacks {field}: {item['artifact_id']}")


def locate(raw_path: Path, locator: str) -> dict:
    kind, number = locator.split(":", 1)
    index = int(number)
    if raw_path.suffix.lower() == ".csv" and kind == "csv_row":
        with raw_path.open("r", encoding="utf-8-sig", newline="") as handle:
            for i, row in enumerate(csv.DictReader(handle), start=1):
                if i == index:
                    return row
    if raw_path.suffix.lower() == ".json" and kind == "json_record":
        rows = json_records(json.loads(raw_path.read_text(encoding="utf-8")))
        return rows[index]
    raise KeyError(locator)


def json_records(value):
    rows = []
    def visit(node):
        if isinstance(node, list):
            for child in node:
                visit(child)
        elif isinstance(node, dict):
            if any(key in node for key in TEXT_KEYS):
                rows.append(node)
            else:
                for child in node.values():
                    if isinstance(child, (list, dict)):
                        visit(child)
    visit(value)
    return rows


def source_rows(path: Path):
    if path.suffix.lower() == ".csv":
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            for i, row in enumerate(csv.DictReader(handle), start=1):
                yield f"csv_row:{i}", row
    elif path.suffix.lower() == ".json":
        for i, row in enumerate(json_records(json.loads(path.read_text(encoding="utf-8")))):
            yield f"json_record:{i}", row


def select_text(row: dict, artifact_id: str):
    keys = ("prompt", "adversarial_prompt", "Goal", "goal", "Behavior", "behavior", "Prompt", "query") \
        if artifact_id in {"ART-P01-JBB-003", "ART-P01-GCG-001"} else TEXT_KEYS
    for key in keys:
        value = row.get(key)
        if isinstance(value, str) and value != "":
            return key, value
    return None, None


def select_id(row: dict):
    for key in ID_KEYS:
        value = row.get(key)
        if value not in (None, ""):
            return str(value)
    return None


def tokenize(text: str):
    return re.findall(r"\w+", text.casefold(), flags=re.UNICODE)


def shingles(text: str, n: int = 3):
    tokens = tokenize(text)
    if len(tokens) < n:
        return {tuple(tokens)} if tokens else set()
    return {tuple(tokens[i:i+n]) for i in range(len(tokens)-n+1)}


def jaccard(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if a or b else 1.0


def minhash_signature(values: set, num_perm: int = 128, seed: int = 1701):
    prime = (1 << 61) - 1
    if not values:
        return tuple([prime] * num_perm)
    base = [int.from_bytes(hashlib.sha256("\0".join(v).encode("utf-8")).digest()[:8], "big") % prime for v in values]
    signature=[]
    for i in range(num_perm):
        a=int.from_bytes(hashlib.sha256(f"{seed}:a:{i}".encode()).digest()[:8],"big") % (prime-1) + 1
        b=int.from_bytes(hashlib.sha256(f"{seed}:b:{i}".encode()).digest()[:8],"big") % prime
        signature.append(min((a*x+b)%prime for x in base))
    return tuple(signature)


def lsh_candidates(signatures: dict, bands: int, rows_per_band: int, record_by_id: dict):
    if bands * rows_per_band > len(next(iter(signatures.values()), ())):
        raise ValueError("LSH bands exceed signature length")
    buckets=defaultdict(list)
    for sample_id, signature in signatures.items():
        for band in range(bands):
            start=band*rows_per_band
            buckets[(band,signature[start:start+rows_per_band])].append(sample_id)
    candidates=set()
    for members in buckets.values():
        for left,right in combinations(sorted(set(members)),2):
            if record_by_id[left]["source"]["dataset_id"] != record_by_id[right]["source"]["dataset_id"]:
                candidates.add((left,right))
    return candidates


def write_json(path: Path, value) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(value, indent=2, ensure_ascii=True) + "\n").encode("utf-8")
    path.write_bytes(data)
    return sha256_bytes(data)


def run(workspace: Path, manifest_path: Path, config_path: Path) -> None:
    started = datetime.now(timezone.utc)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    config = json.loads(config_path.read_text(encoding="utf-8"))
    manifest_validate(manifest)
    normalized = []
    quality = []
    by_artifact = {}
    for artifact in manifest["artifacts"]:
        if artifact.get("acquisition_status") != "ACQUIRED_VERIFIED":
            quality.append({"artifact_id":artifact["artifact_id"],"status":"NOT_MEASURED","reason":"artifact not acquired"})
            continue
        path = workspace / artifact["raw_path"]
        actual_hash = sha256_bytes(path.read_bytes())
        if actual_hash != artifact["sha256"]:
            raise ValueError(f"raw integrity failure: {artifact['artifact_id']}")
        if path.suffix.lower() == ".txt":
            quality.append({"artifact_id":artifact["artifact_id"],"status":"NOT_APPLICABLE","reason":"generation seed preserved but not adapted as dataset records","byte_size":path.stat().st_size})
            continue
        counts = Counter(total_records=0, valid_records=0, records_with_text=0, null_text=0,
                         empty_text=0, malformed_records=0, encoding_issues=0,
                         missing_source_id=0, missing_source_label=0, unknown_source_label=0,
                         unexpected_schema=0, very_short_samples=0, very_long_samples=0)
        fields = set()
        source_ids = Counter()
        text_lengths = []
        for locator, row in source_rows(path):
            counts["total_records"] += 1
            fields.update(row.keys())
            text_key, text = select_text(row, artifact["artifact_id"])
            source_id = select_id(row)
            if text is None:
                candidate_values = [row.get(key) for key in TEXT_KEYS if key in row]
                if not candidate_values or all(value is None for value in candidate_values):
                    counts["null_text"] += 1
                else:
                    counts["empty_text"] += 1
                counts["unexpected_schema"] += 1
                continue
            counts["valid_records"] += 1
            counts["records_with_text"] += 1
            text_lengths.append(len(text))
            if len(text) < 4:
                counts["very_short_samples"] += 1
            if len(text) > 4096:
                counts["very_long_samples"] += 1
            if source_id is None:
                counts["missing_source_id"] += 1
            else:
                source_ids[source_id] += 1
            source_label = row.get("type") or row.get("Source") or row.get("label")
            if source_label in (None, ""):
                counts["missing_source_label"] += 1
            elif str(source_label).upper() == "UNKNOWN":
                counts["unknown_source_label"] += 1
            n0, n1, n2 = (canonicalize(text, view) for view in ("N0","N1","N2"))
            stable_material = f"{artifact['dataset_id']}\0{artifact['artifact_id']}\0{artifact['sha256']}\0{locator}".encode()
            original_label = row.get("type") or row.get("Source") or row.get("label")
            original_category = row.get("Category") or row.get("category") or row.get("SemanticCategory")
            base_behavior_text = row.get("Goal") or row.get("goal") or row.get("Behavior") or row.get("behavior") or \
                                 (row.get("prompt") if artifact["artifact_id"] == "ART-P01-XSTEST-001" else None)
            generation_method = "GCG" if artifact["artifact_id"] == "ART-P01-GCG-001" else "UNKNOWN"
            rights_status = "CONDITIONAL" if artifact["dataset_id"] in {"DS-TXT-008","DS-TXT-009","DS-TXT-014"} else "UNKNOWN"
            evaluation_only = "TRUE" if artifact["dataset_id"] in {"DS-TXT-007","DS-TXT-008","DS-TXT-009","DS-TXT-014"} else "UNKNOWN"
            train_allowed = "FALSE" if artifact["dataset_id"] in {"DS-TXT-007","DS-TXT-008","DS-TXT-009"} else "UNKNOWN"
            record = {
                "schema_version":"0.1","sample_id":"P01-"+sha256_bytes(stable_material)[:24],
                "source":{"dataset_id":artifact["dataset_id"],"dataset_name":artifact["name"],"artifact_id":artifact["artifact_id"],
                          "version":artifact["resolved_revision"],"artifact_sha256":artifact["sha256"],"record_locator":locator,
                          "original_sample_id":source_id,"text_field":text_key,"prompt":text,"response":row.get("response"),
                          "raw_text":text,"raw_response":row.get("response"),"label":original_label,
                          "original_label":original_label,"original_category":original_category,
                          "original_metadata":row,"base_behavior_text":base_behavior_text,
                          "adversarial_prompt":row.get("prompt") or row.get("adversarial_prompt"),
                          "original_record":row},
                "forensics":{"canonicalization_ids":CANON_IDS,"raw_text_sha256":sha256_bytes(n0.encode("utf-8")),
                              "N1_sha256":sha256_bytes(n1.encode("utf-8")),"N2_sha256":sha256_bytes(n2.encode("utf-8")),
                              "canonical_hash":sha256_bytes(n1.encode("utf-8")),"duplicate_cluster_id":None},
                "labels":{"normalized_binary_label":"UNKNOWN","normalized_attack_family":"UNKNOWN","normalized_attack_subtype":"UNKNOWN"},
                "generation":{"generator":"UNKNOWN","generation_method":generation_method},
                "lineage":{"base_behavior_id":row.get("BehaviorID") or row.get("behavior_id") or "UNKNOWN",
                           "upstream_dataset":"UNKNOWN","upstream_sample_id":"UNKNOWN"},
                "rights":{"license_status":rights_status,"provenance_status":artifact["provenance_status"],"PII_status":"REVIEW_REQUIRED"},
                "governance":{"experimental_role":"NOT_ASSIGNED","train_allowed":train_allowed,"evaluation_only":evaluation_only,
                              "training_access":"DENIED" if train_allowed == "FALSE" else "NOT_AUTHORIZED",
                              "forensic_analysis_access":"ALLOWED","quarantine_reason":["upstream_rights_review"] if artifact["upstream_rights_status"] in {"UNKNOWN","PARTIAL"} else [],
                              "quarantine_status":["upstream_rights_review"] if artifact["upstream_rights_status"] in {"UNKNOWN","PARTIAL"} else []},
                "derived":{"N1":n1,"N2":n2}
            }
            normalized.append(record)
        by_artifact[artifact["artifact_id"]] = counts["total_records"]
        duplicate_source_ids = sum(1 for count in source_ids.values() if count > 1)
        duplicate_id_records = sum(count - 1 for count in source_ids.values() if count > 1)
        lengths = sorted(text_lengths)
        quality.append({
            "artifact_id":artifact["artifact_id"],
            "status":"MEASURED",
            "counts":dict(counts),
            "source_fields":sorted(fields),
            "duplicate_source_ids":duplicate_source_ids,
            "duplicate_id_records":duplicate_id_records,
            "length_definition":"Unicode code points in N0 text; very short <4; very long >4096",
            "lengths":{
                "minimum":min(lengths) if lengths else "NOT_MEASURED",
                "median":statistics.median(lengths) if lengths else "NOT_MEASURED",
                "p95":lengths[min(len(lengths)-1, int(0.95*len(lengths)))] if lengths else "NOT_MEASURED",
                "maximum":max(lengths) if lengths else "NOT_MEASURED",
            },
            "normalized_label_status":"NOT_MEASURED",
            "invalid_reference_status":"NOT_MEASURED",
        })

    normalized.sort(key=lambda r: r["sample_id"])
    n1_groups = defaultdict(list)
    for record in normalized:
        n1_groups[record["forensics"]["N1_sha256"]].append(record)
    for n1_hash, members in n1_groups.items():
        if len(members) > 1:
            cluster_id = "DUP-N1-" + n1_hash[:16]
            for member in members:
                member["forensics"]["duplicate_cluster_id"] = cluster_id
    norm_path = workspace / "03_schema" / "PILOT-01_normalized_records.jsonl"
    norm_path.parent.mkdir(parents=True, exist_ok=True)
    with norm_path.open("w", encoding="utf-8", newline="\n") as handle:
        for record in normalized:
            handle.write(json.dumps(record, sort_keys=True, ensure_ascii=True)+"\n")

    exact = {"pilot_id":"PILOT-01","canonicalization_ids":CANON_IDS,"views":{}}
    for view, key in (("RAW","raw_text_sha256"),("N0","raw_text_sha256"),("N1","N1_sha256"),("N2","N2_sha256")):
        groups = defaultdict(list)
        for record in normalized:
            groups[record["forensics"][key]].append(record["sample_id"])
        clusters = [{"hash":h,"members":members} for h,members in sorted(groups.items()) if len(members)>1]
        within_dataset = {}
        for dataset_id in sorted({record["source"]["dataset_id"] for record in normalized}):
            dataset_groups = defaultdict(list)
            for record in normalized:
                if record["source"]["dataset_id"] == dataset_id:
                    dataset_groups[record["forensics"][key]].append(record["sample_id"])
            dataset_clusters = [members for members in dataset_groups.values() if len(members) > 1]
            within_dataset[dataset_id] = {
                "cluster_count": len(dataset_clusters),
                "participating_records": sum(len(members) for members in dataset_clusters),
            }
        exact["views"][view] = {
            "duplicate_clusters":clusters,
            "cluster_count":len(clusters),
            "participating_records":sum(len(c["members"]) for c in clusters),
            "within_dataset":within_dataset,
        }

    record_by_id = {r["sample_id"]:r for r in normalized}
    threshold_counts = {str(t):0 for t in config["near_duplicate"]["candidate_thresholds"]}
    near_pairs = []
    shingle_sets = {r["sample_id"]:shingles(r["derived"]["N1"]) for r in normalized}
    near_config=config["near_duplicate"]
    signatures={sample_id:minhash_signature(values,near_config["num_perm"],config["random_seed"]) for sample_id,values in shingle_sets.items()}
    candidates=lsh_candidates(signatures,near_config["bands"],near_config["rows_per_band"],record_by_id)
    minimum = min(config["near_duplicate"]["candidate_thresholds"])
    for left,right in sorted(candidates):
        score = jaccard(shingle_sets[left], shingle_sets[right])
        for threshold in config["near_duplicate"]["candidate_thresholds"]:
            if score >= threshold:
                threshold_counts[str(threshold)] += 1
        if score >= minimum:
            near_pairs.append({"left":left,"right":right,"left_dataset":record_by_id[left]["source"]["dataset_id"],
                               "right_dataset":record_by_id[right]["source"]["dataset_id"],"score":round(score,8)})

    datasets = ["DS-TXT-013","DS-TXT-014","DS-TXT-015","DS-TXT-007","DS-TXT-008","DS-TXT-009"]
    eligible = Counter(r["source"]["dataset_id"] for r in normalized)
    matrix = {"pilot_id":"PILOT-01","directional_definition":"A records with >=1 matching B record / eligible A records","datasets":datasets,"eligible_records":dict(eligible),"metrics":{}}
    for view,key in (("RAW_EXACT","raw_text_sha256"),("N0_EXACT","raw_text_sha256"),("CANONICAL_EXACT_N1","N1_sha256"),("CANONICAL_EXACT_N2","N2_sha256")):
        matched = defaultdict(set)
        groups = defaultdict(list)
        for r in normalized: groups[r["forensics"][key]].append(r)
        for members in groups.values():
            for a,b in combinations(members,2):
                da,db=a["source"]["dataset_id"],b["source"]["dataset_id"]
                if da != db:
                    matched[(da,db)].add(a["sample_id"]); matched[(db,da)].add(b["sample_id"])
        cells={}
        for a in datasets:
            for b in datasets:
                if a==b: cells[f"{a}->{b}"]={"status":"NOT_APPLICABLE"}; continue
                denom=eligible[a]; count=len(matched[(a,b)])
                cells[f"{a}->{b}"]={"status":"MEASURED" if denom else "NOT_MEASURED","count":count if denom else "NOT_MEASURED","denominator":denom,"percent":round(100*count/denom,4) if denom else "NOT_MEASURED"}
        matrix["metrics"][view]=cells
    lexical_matched=defaultdict(set)
    for pair in near_pairs:
        if pair["score"] >= 0.8:
            lexical_matched[(pair["left_dataset"],pair["right_dataset"])].add(pair["left"])
            lexical_matched[(pair["right_dataset"],pair["left_dataset"])].add(pair["right"])
    cells={}
    for a in datasets:
        for b in datasets:
            if a==b: cells[f"{a}->{b}"]={"status":"NOT_APPLICABLE"}; continue
            denom=eligible[a]; count=len(lexical_matched[(a,b)])
            cells[f"{a}->{b}"]={"status":"MEASURED" if denom else "NOT_MEASURED","threshold":0.8,"count":count if denom else "NOT_MEASURED","denominator":denom,"percent":round(100*count/denom,4) if denom else "NOT_MEASURED"}
    matrix["metrics"]["LEXICAL_NEAR_WORD3_JACCARD"]=cells
    matrix["metrics"]["SEMANTIC_CANDIDATES"]={"status":"NOT_MEASURED","reason":config["semantic_overlap"]["reason"]}
    matrix["metrics"]["DOCUMENTED_LINEAGE"]={"status":"SEE_LINEAGE_EVIDENCE","artifact":"08_provenance/PILOT-01_lineage_hypotheses.json"}

    behavior_groups = defaultdict(list)
    behavior_eligible = Counter()
    for record in normalized:
        behavior_text = record["source"].get("base_behavior_text")
        if behavior_text:
            dataset_id = record["source"]["dataset_id"]
            behavior_eligible[dataset_id] += 1
            behavior_groups[sha256_bytes(canonicalize(str(behavior_text), "N1").encode("utf-8"))].append(record)
    behavior_matched = defaultdict(set)
    behavior_shared_hashes = defaultdict(set)
    for behavior_hash, members in behavior_groups.items():
        member_datasets = {member["source"]["dataset_id"] for member in members}
        for dataset_a in member_datasets:
            for dataset_b in member_datasets:
                if dataset_a == dataset_b:
                    continue
                behavior_shared_hashes[(dataset_a, dataset_b)].add(behavior_hash)
                for member in members:
                    if member["source"]["dataset_id"] == dataset_a:
                        behavior_matched[(dataset_a, dataset_b)].add(member["sample_id"])
    behavior_cells = {}
    for dataset_a in datasets:
        for dataset_b in datasets:
            key = f"{dataset_a}->{dataset_b}"
            if dataset_a == dataset_b:
                behavior_cells[key] = {"status":"NOT_APPLICABLE"}
                continue
            denominator = behavior_eligible[dataset_a]
            count = len(behavior_matched[(dataset_a, dataset_b)])
            behavior_cells[key] = {
                "status":"MEASURED" if denominator else "NOT_MEASURED",
                "relationship":"IDENTICAL_N1_BASE_BEHAVIOR_TEXT",
                "matched_records":count if denominator else "NOT_MEASURED",
                "eligible_records":denominator,
                "percent":round(100*count/denominator,4) if denominator else "NOT_MEASURED",
                "shared_unique_behavior_hashes":len(behavior_shared_hashes[(dataset_a,dataset_b)]),
            }
    behavior_report = {
        "pilot_id":"PILOT-01",
        "status":"MEASURED",
        "method":"N1 identity of source-preserved base_behavior_text; this does not by itself prove lineage",
        "eligible_records":dict(behavior_eligible),
        "directional_relationships":behavior_cells,
    }

    documented_pair_relationships = {
        frozenset(("DS-TXT-013","DS-TXT-014")): "AdvBench is documented as an input behavior source for GCG experiments.",
        frozenset(("DS-TXT-013","DS-TXT-015")): "AutoDAN contains the AdvBench behavior input and documents llm-attacks dependence.",
        frozenset(("DS-TXT-013","DS-TXT-007")): "HarmBench contains an explicitly named AdvBench behavior subset.",
        frozenset(("DS-TXT-013","DS-TXT-008")): "JBB documents an AdvBench constituent subset.",
        frozenset(("DS-TXT-007","DS-TXT-008")): "JBB documents a TDC/HarmBench constituent subset.",
        frozenset(("DS-TXT-009","DS-TXT-008")): "JBB judge comparison documents use of 100 XSTest benign examples.",
        frozenset(("DS-TXT-014","DS-TXT-008")): "JBB documents GCG-generated prompts and publishes a GCG artifact.",
        frozenset(("DS-TXT-015","DS-TXT-007")): "HarmBench documents and implements AutoDAN as a method dependency.",
    }
    hash_sets = {}
    for view, key in (("N0","raw_text_sha256"),("N1","N1_sha256"),("N2","N2_sha256")):
        hash_sets[view] = {
            dataset_id:{record["forensics"][key] for record in normalized if record["source"]["dataset_id"] == dataset_id}
            for dataset_id in datasets
        }
    pairwise_summary = []
    for dataset_a, dataset_b in combinations(datasets, 2):
        key_ab = f"{dataset_a}->{dataset_b}"
        key_ba = f"{dataset_b}->{dataset_a}"
        documentary = documented_pair_relationships.get(frozenset((dataset_a,dataset_b)), "UNKNOWN")
        behavior_ab = behavior_cells[key_ab]
        behavior_ba = behavior_cells[key_ba]
        measured_relation = any(
            matrix["metrics"][metric][key_ab].get("count", 0) or matrix["metrics"][metric][key_ba].get("count", 0)
            for metric in ("RAW_EXACT","CANONICAL_EXACT_N1","CANONICAL_EXACT_N2","LEXICAL_NEAR_WORD3_JACCARD")
        ) or behavior_ab.get("matched_records", 0) not in (0,"NOT_MEASURED")
        pairwise_summary.append({
            "dataset_a":dataset_a,
            "dataset_b":dataset_b,
            "record_counts":{"a":eligible[dataset_a],"b":eligible[dataset_b]},
            "exact":{
                view:{
                    "shared_unique_hashes":len(hash_sets[view][dataset_a] & hash_sets[view][dataset_b]),
                    "a_to_b":matrix["metrics"]["RAW_EXACT" if view == "N0" else f"CANONICAL_EXACT_{view}"][key_ab],
                    "b_to_a":matrix["metrics"]["RAW_EXACT" if view == "N0" else f"CANONICAL_EXACT_{view}"][key_ba],
                }
                for view in ("N0","N1","N2")
            },
            "lexical_near":{
                "configuration":"deterministic_minhash_lsh_v0.1 + exact word-3-gram Jaccard verification",
                "a_to_b":matrix["metrics"]["LEXICAL_NEAR_WORD3_JACCARD"][key_ab],
                "b_to_a":matrix["metrics"]["LEXICAL_NEAR_WORD3_JACCARD"][key_ba],
            },
            "semantic_overlap":{"status":"NOT_MEASURED"},
            "documented_lineage":{"status":"DOCUMENTED" if documentary != "UNKNOWN" else "UNKNOWN","relationship":documentary},
            "behavior_level_relationship":{"a_to_b":behavior_ab,"b_to_a":behavior_ba},
            "evidence_state":"DOCUMENTED_AND_MEASURED" if documentary != "UNKNOWN" and measured_relation else
                             "DOCUMENTED" if documentary != "UNKNOWN" else "MEASURED" if measured_relation else "UNKNOWN",
        })
    matrix["pairwise_summary"] = pairwise_summary

    outputs = {}
    outputs["quality"] = write_json(workspace/"04_quality"/"PILOT-01_quality.json", {"pilot_id":"PILOT-01","artifacts":quality})
    outputs["exact"] = write_json(workspace/"05_exact_duplicates"/"PILOT-01_exact_overlap.json", exact)
    outputs["near"] = write_json(workspace/"06_near_duplicates"/"PILOT-01_lexical_overlap.json", {"pilot_id":"PILOT-01","configuration":config["near_duplicate"],"candidate_pairs_evaluated":len(candidates),"threshold_pair_counts":threshold_counts,"pairs_at_minimum_threshold":near_pairs})
    outputs["behavior_lineage"] = write_json(workspace/"08_provenance"/"PILOT-01_behavior_lineage.json", behavior_report)
    outputs["matrix"] = write_json(workspace/"11_contamination_matrix"/"PILOT-01_contamination_matrix.json", matrix)
    run_record={"run_id":"PILOT-01-FORENSICS-"+started.strftime("%Y%m%dT%H%M%SZ"),"timestamp":started.isoformat(),"script":__file__,"script_version":SCRIPT_VERSION,
                "input_manifest_sha256":sha256_bytes(manifest_path.read_bytes()),"configuration":config,"python":sys.version,"platform":platform.platform(),
                "record_count":len(normalized),"normalized_output_sha256":sha256_bytes(norm_path.read_bytes()),"outputs":outputs,"status":"SUCCESS"}
    write_json(workspace/"logs"/"PILOT-01_forensic_run.json",run_record)


def main():
    parser=argparse.ArgumentParser(); parser.add_argument("--workspace",type=Path,required=True); parser.add_argument("--manifest",type=Path,required=True); parser.add_argument("--config",type=Path,required=True)
    args=parser.parse_args(); run(args.workspace.resolve(),args.manifest.resolve(),args.config.resolve())


if __name__ == "__main__": main()
