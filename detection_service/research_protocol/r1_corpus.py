"""Pre-score, metadata-only R1 publication; payloads stay in ignored local storage."""

import csv
import hashlib
import json
import re
import subprocess
import unicodedata
from collections import Counter, defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path

from detection_service.research_protocol import detector_semantics as files
from detection_service.research_protocol.regime import create_manifest, require
from detection_service.research_protocol.regime_contract import FrozenRegimeContracts, sample_payload

ROOT = files.ROOT
PRIVATE = ROOT / "detection_service/outputs/r1-clearance-001"
OUT = ROOT / files.OUT / "r1"
MEMBERSHIP = "data_governance/manifests/development_partition_manifest_v1.csv"
MEMBERSHIP_SHA = "9cdd5ecdd80f9ac3c8f05db63742721f4537ca2b64a2fe48f6c2b424b57483a6"
REVISIONS = {
    "LLMAIL_INJECT": "1063bdf01ec8762b812d5e06ee768a06faa5a6f7",
    "INJECAGENT_BASE": "f19c9f2c79a41046eb13c03c51a24c567a8ffa07",
    "OR_BENCH_HARD": "e36d8b80e81837c8a8f264bbb2a49f1b32c7e272",
}
IDS = {"LLMAIL_INJECT": "DS-TXT-011", "INJECAGENT_BASE": "DS-TXT-005", "OR_BENCH_HARD": "DS-TXT-010"}
RULES = dict(seed=1701, target_counts={"LLMAIL_INJECT": 400, "INJECAGENT_BASE": 400, "OR_BENCH_HARD": 1000},
    llmail="Phase-2 labelled unique; explicit bool True or string True; require exactly one joined team; round-robin teams, then scenarios; team-level dependency union",
    injecagent="BASE Tool Response verbatim; 200 direct-harm and 200 data-stealing; round-robin User Tool/Attack Type; union shared attacker OR user base case",
    or_bench="hard-1k only; full qualified subset up to 1000; source singleton fallback unless canonical duplicate",
    ordering="Ascending SHA256 of canonical JSON [1701,domain,stable_source_locator]; no detector scores",
    overlap="Exclude all raw exact or N1 canonical development matches; approved word-threegram casefold Jaccard thresholds 0.7/0.8/0.9 reported, not new semantic thresholds",
    bootstrap_unit="LINEAGE_CLUSTERED", detectors_scored=False)


def sha(value):
    return hashlib.sha256(value.encode("utf-8") if isinstance(value, str) else value).hexdigest()


def n1(text):
    return unicodedata.normalize("NFC", text).replace("\r\n", "\n").replace("\r", "\n")


def shingles(text):
    tokens = re.findall(r"\w+", text.casefold(), flags=re.UNICODE)
    return {tuple(tokens[i:i+3]) for i in range(len(tokens)-2)} if len(tokens) >= 3 else ({tuple(tokens)} if tokens else set())


def attempted(value):
    return value is True or isinstance(value, str) and value == "True"


def rank(domain, locator):
    return sha(files.canonical_bytes([1701, domain, locator]))


def publish(path, value):
    data = files.manifest_bytes(value)
    require(not path.exists() or path.read_bytes() == data, "REFUSE_DIFFERENT_FROZEN_BYTES:" + str(path))
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as stream:
            stream.write(data)
    return sha(data)


def info(path, role):
    return dict(role=role, path=path.relative_to(ROOT).as_posix(), size=path.stat().st_size, sha256=files.sha(path))


def provenance():
    evidence = PRIVATE / "source_evidence"
    upstream = {r["path"]: r for r in files.read_json(evidence / "llmail_upstream_tree.json")}
    selected = defaultdict(list)
    for name in ("labelled_unique_submissions_phase2.json", "raw_submissions_phase2.jsonl", "levels_descriptions.json", "objectives_descriptions.json"):
        path = PRIVATE / "llmail_bucket/data" / name
        row = info(path, "data/" + name)
        authoritative = upstream[row["role"]]
        require(row["size"] == authoritative["size"], "LLMAIL_SIZE_MISMATCH")
        if "lfs" in authoritative:
            require(row["sha256"] == authoritative["lfs"]["oid"], "LLMAIL_LFS_SHA_MISMATCH")
            row["comparison"] = "SHA256_EQUALS_PINNED_UPSTREAM_LFS_OBJECT; no redundant upstream payload download"
        else:
            blob = path.read_bytes()
            require(hashlib.sha1(b"blob " + str(len(blob)).encode() + b"\0" + blob).hexdigest() == authoritative["oid"], "LLMAIL_GIT_BLOB_MISMATCH")
            row["comparison"] = "BYTES_MATCH_PINNED_UPSTREAM_GIT_BLOB"
        selected["LLMAIL_INJECT"].append(row)
    mirror = PRIVATE / "or_given/or-bench-hard-1k.csv"
    original = PRIVATE / "or_official/or-bench-hard-1k.csv"
    require(mirror.read_bytes() == original.read_bytes(), "OR_MIRROR_DIFFERS")
    require(files.sha(original) == "a6e2f1166416efe5901f3bb05c47dc92ab3aca3acfe143693d38b8057d841e6d", "OR_SOURCE_DRIFT")
    selected["OR_BENCH_HARD"].append({**info(mirror, "or-bench-hard-1k.csv"), "comparison": "BYTE_IDENTICAL_PINNED_ORIGINAL_AND_USER_MIRROR", "upstream_copy": info(original, "upstream_comparison_copy")})
    clone = ROOT / "Dataset/Raw/datasets/GitHub/InjecAgent"
    require(subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=clone).decode().strip() == REVISIONS["INJECAGENT_BASE"], "INJEC_COMMIT_MISMATCH")
    for name in ("attacker_cases_dh.jsonl", "attacker_cases_ds.jsonl", "user_cases.jsonl", "test_cases_dh_base.json", "test_cases_ds_base.json"):
        path = clone / "data" / name
        original = subprocess.check_output(["git", "show", "HEAD:data/" + name], cwd=clone)
        require(path.read_bytes().replace(b"\r\n", b"\n") == original.replace(b"\r\n", b"\n"), "INJEC_LOCAL_SOURCE_MODIFIED")
        selected["INJECAGENT_BASE"].append({**info(path, "data/" + name), "upstream_git_object_sha256": sha(original), "comparison": "GIT_COMMIT_VERIFIED; Windows CRLF checkout; decoded JSON values unchanged"})
    require("license: mit" in (evidence / "llmail_official_README.md").read_text(encoding="utf-8"), "LLMAIL_TERMS_MISSING")
    require('license: "cc-by-4.0"' in (evidence / "or_official_README.md").read_text(encoding="utf-8"), "OR_TERMS_MISSING")
    require("MIT License" in (evidence / "injec_LICENCE").read_text(encoding="utf-8"), "INJEC_TERMS_MISSING")
    return selected


def record(source, locator, text, label, groups, metadata):
    require(isinstance(text, str) and bool(text.strip()), "EMPTY_OR_NON_TEXT_SOURCE_INPUT")
    return dict(source=source, locator=locator, text=text, truth_label=label, groups=groups,
                text_sha256=sha(text), n1_sha256=sha(n1(text)), metadata=metadata,
                sample_id="R1-" + IDS[source] + "-" + rank(source, locator))


def extract():
    labels = files.read_json(PRIVATE / "llmail_bucket/data/labelled_unique_submissions_phase2.json")
    positive = {p: v for p, v in labels.items() if attempted(v["attack_attempt"])}
    joins = defaultdict(lambda: dict(teams=set(), scenarios=set(), raw_count=0, first=None, last=None, objective_hashes=set(), success_values=set()))
    with (PRIVATE / "llmail_bucket/data/raw_submissions_phase2.jsonl").open(encoding="utf-8") as stream:
        for index, line in enumerate(stream, 1):
            row = json.loads(line)
            prompt = "Subject of the email: " + row["subject"] + ".   Body: " + row["body"]
            if prompt not in positive:
                continue
            joined = joins[prompt]
            joined["teams"].add(sha("LLMAIL_TEAM_V1\0" + row["team_id"]))
            joined["scenarios"].add(row["scenario"])
            joined["raw_count"] += 1
            stamp = row["Timestamp"]
            if stamp is not None:
                joined["first"] = min(joined["first"] or stamp, stamp)
                joined["last"] = max(joined["last"] or stamp, stamp)
            joined["objective_hashes"].add(sha(row["objectives"]))
            objectives = json.loads(row["objectives"]) if isinstance(row["objectives"], str) else row["objectives"]
            success = objectives.get("exfil.sent")
            require(success is None or type(success) is bool, "UNEXPECTED_UPSTREAM_SUCCESS_VALUE")
            joined["success_values"].add(success)
    require(set(positive) == set(joins), "UNMAPPED_LLMAIL_ATTACK_LABEL")
    candidates = []
    for prompt, annotation in positive.items():
        j = joins[prompt]
        candidates.append(record("LLMAIL_INJECT", "prompt-sha256:" + sha(prompt), prompt, 1,
            ["LLTEAM-" + t for t in sorted(j["teams"])], dict(team_count=len(j["teams"]), scenarios=sorted(j["scenarios"]),
            raw_submission_count=j["raw_count"], first_timestamp=j["first"], last_timestamp=j["last"],
            attack_attempt=True, original_attempt_representation=type(annotation["attack_attempt"]).__name__,
            upstream_exfil_sent_observed=sorted(j["success_values"], key=str), source_annotation_sha256=sha(files.canonical_bytes(annotation)),
            objective_annotation_hashes=sorted(j["objective_hashes"]))))
    schema = dict(labelled_unique_rows=len(labels), explicit_positive_rows=len(positive), labels_by_type=Counter(type(v["attack_attempt"]).__name__ + ":" + str(v["attack_attempt"]) for v in labels.values()),
                  positive_team_cardinality=Counter(str(len(j["teams"])) for j in joins.values()))
    data = ROOT / "Dataset/Raw/datasets/GitHub/InjecAgent/data"
    attacker_fields = ("Attacker Tools", "Modifed", "Attacker Instruction", "Expected Achievements", "Attack Type")
    user_fields = ("User Tool", "User Instruction", "Tool Parameters", "Tool Response Template", "Thought")
    attackers = {}
    for group in ("dh", "ds"):
        with (data / f"attacker_cases_{group}.jsonl").open(encoding="utf-8") as stream:
            attackers[group] = {sha(files.canonical_bytes({k: r[k] for k in attacker_fields})) for r in map(json.loads, stream)}
    with (data / "user_cases.jsonl").open(encoding="utf-8") as stream:
        users = {sha(files.canonical_bytes({k: r[k] for k in user_fields})) for r in map(json.loads, stream)}
    for group in ("dh", "ds"):
        for index, row in enumerate(files.read_json(data / f"test_cases_{group}_base.json"), 1):
            attacker = sha(files.canonical_bytes({k: row[k] for k in attacker_fields}))
            user = sha(files.canonical_bytes({k: row[k] for k in user_fields}))
            require(attacker in attackers[group] and user in users, "INJEC_BASE_LINEAGE_JOIN_FAILURE")
            require(row["Attacker Instruction"] in row["Tool Response"], "INJEC_BASE_INSTRUCTION_MISSING")
            candidates.append(record("INJECAGENT_BASE", f"data/test_cases_{group}_base.json::row:{index}", row["Tool Response"], 1,
                ["INJATT-" + attacker, "INJUSER-" + user], dict(setting="BASE", harm_group=group, user_tool=row["User Tool"],
                attacker_tools=row["Attacker Tools"], attack_type=row["Attack Type"], source_native_id=None,
                base_attacker_case_sha256=attacker, base_user_case_sha256=user)))
    with (PRIVATE / "or_given/or-bench-hard-1k.csv").open(encoding="utf-8", newline="") as stream:
        for index, row in enumerate(csv.DictReader(stream), 1):
            candidates.append(record("OR_BENCH_HARD", f"or-bench-hard-1k.csv::csv_row:{index}", row["prompt"], 0, [], dict(category=row["category"])))
    return candidates, schema


def development():
    from detection_service.app.detectors.semantic_finetuned.data import load_texts
    from detection_service.scripts.calibrate_semantic_baseline import load_calibration_texts
    require(files.sha(ROOT / MEMBERSHIP) == MEMBERSHIP_SHA, "DEVELOPMENT_MEMBERSHIP_DRIFT")
    with (ROOT / MEMBERSHIP).open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    require(Counter(r["partition"] for r in rows) == {"BASE_TRAIN": 1135, "CALIBRATION": 233, "VALIDATION": 233}, "DEVELOPMENT_COUNT_DRIFT")
    texts = {}
    source_hashes = {}
    for part in ("BASE_TRAIN", "CALIBRATION", "VALIDATION"):
        subset = [r for r in rows if r["partition"] == part]
        loaded, hashes = load_calibration_texts(subset, ROOT) if part == "CALIBRATION" else load_texts(subset, ROOT, part)
        texts.update(zip((r["record_id"] for r in subset), loaded))
        source_hashes.update(hashes)
    require(all(sha(n1(texts[r["record_id"]])) == r["normalized_hash"] for r in rows), "APPROVED_N1_RECONSTRUCTION_MISMATCH")
    return rows, texts, source_hashes


def contamination(candidates):
    dev, texts, source_hashes = development()
    raw = defaultdict(list)
    canonical = defaultdict(list)
    index = defaultdict(list)
    grams = []
    for i, row in enumerate(dev):
        raw[row["exact_hash"]].append(row["record_id"])
        canonical[row["normalized_hash"]].append(row["record_id"])
        value = shingles(texts[row["record_id"]])
        grams.append(value)
        for gram in value:
            index[gram].append(i)
    pairs = []
    exclusions = []
    counts = defaultdict(Counter)
    eligible = []
    for serial, row in enumerate(candidates):
        source = row["source"]
        counts[source]["candidate_rows"] += 1
        matches = sorted(set(raw[row["text_sha256"]] + canonical[row["n1_sha256"]]))
        if raw[row["text_sha256"]]:
            counts[source]["raw_exact_rows"] += 1
        if canonical[row["n1_sha256"]]:
            counts[source]["canonical_exact_rows"] += 1
        reason = "DEVELOPMENT_EXACT_OR_CANONICAL" if matches else "MULTI_TEAM_LABEL" if source == "LLMAIL_INJECT" and row["metadata"]["team_count"] != 1 else None
        if reason:
            exclusions.append(dict(sample_id=row["sample_id"], source=source, reason=reason, development_record_ids=matches))
        else:
            eligible.append(row)
        value = shingles(row["text"])
        intersections = Counter(i for gram in value for i in index.get(gram, ()))
        hit_levels = set()
        for i, intersection in intersections.items():
            union = len(value) + len(grams[i]) - intersection
            score = intersection / union if union else 1.0
            if score >= 0.7:
                pairs.append(dict(sample_id=row["sample_id"], source=source, development_record_id=dev[i]["record_id"],
                                  jaccard=score, intersection=intersection, union=union))
                hit_levels.update(t for t in (0.7, 0.8, 0.9) if score >= t)
        for t in hit_levels:
            counts[source][f"near_rows_at_{t}"] += 1
        if serial % 2000 == 0:
            print(json.dumps(dict(stage="CONTAMINATION", candidate_rows_checked=serial, total=len(candidates))), flush=True)
    audit = dict(artifact_version="r1_contamination_audit_v1", development_manifest_sha256=MEMBERSHIP_SHA,
        development_partitions=Counter(r["partition"] for r in dev), development_population=len(dev), source_artifact_sha256=source_hashes,
        canonicalization="Approved N1: NFC then CRLF/CR to LF; all 1601 normalized hashes reconstructed",
        near_method="Approved Unicode casefold word-threegram exact Jaccard; exhaustive inverted-index enumeration, not approximate MinHash-LSH; original thresholds unchanged",
        approved_method_evidence={p: files.sha(ROOT / p) for p in ("PHASE-3/logs/PILOT-01_forensic_run.json", "PHASE-3/logs/WAVE-2_forensic_run.json")},
        thresholds=[0.7, 0.8, 0.9], candidate_counts=dict(counts), exclusions=exclusions, near_pairs=pairs,
        source_native_id_overlap=dict(status="NO_COMPARABLE_SOURCE_NATIVE_IDS", detail="Source-scoped IDs disjoint from DS-TXT-017/018; internal row numbers are not native IDs"),
        lineage_overlap=dict(status="NO_DOCUMENTED_SHARED_PROJECT_DEVELOPMENT_LINEAGE", limitation="Negative hashes/IDs do not prove unseen pretraining or hidden documentary independence"),
        semantic_similarity="NOT_RUN; no new semantic threshold", remaining_selected_raw_exact=0, remaining_selected_canonical_exact=0,
        selection_not_scored=True)
    return eligible, audit


def round_robin(rows, count, key, domain):
    buckets = defaultdict(list)
    for row in rows:
        buckets[key(row)].append(row)
    queues = []
    for group in sorted(buckets, key=lambda g: rank(domain, g)):
        queues.append(deque(sorted(buckets[group], key=lambda r: rank(domain, r["locator"]))))
    result = []
    while len(result) < count and any(queues):
        for queue in queues:
            if queue and len(result) < count:
                result.append(queue.popleft())
    require(len(result) == count, "INSUFFICIENT_QUALIFIED_SOURCE")
    return result


def select(rows):
    ll = [r for r in rows if r["source"] == "LLMAIL_INJECT"]
    by_team = defaultdict(list)
    for r in ll:
        by_team[r["groups"][0]].append(r)
    # Within a team, spread choices over observed source scenarios before ordering prompts.
    teams = sorted(by_team, key=lambda t: rank("LL_TEAM", t))
    queues = {t: deque(round_robin(by_team[t], len(by_team[t]), lambda r: r["metadata"]["scenarios"][0], "LL_SCENARIO")) for t in teams}
    picked = []
    while len(picked) < 400:
        before = len(picked)
        for t in teams:
            if queues[t] and len(picked) < 400:
                picked.append(queues[t].popleft())
        require(len(picked) > before, "INSUFFICIENT_LLMAIL")
    for group in ("dh", "ds"):
        pool = [r for r in rows if r["source"] == "INJECAGENT_BASE" and r["metadata"]["harm_group"] == group]
        picked.extend(round_robin(pool, 200, lambda r: (r["metadata"]["user_tool"], r["metadata"]["attack_type"]), "INJ_" + group))
    benign = [r for r in rows if r["source"] == "OR_BENCH_HARD"]
    require(len(benign) >= 600, "OR_QUALIFIED_COUNT_OUT_OF_SCOPE")
    picked.extend(sorted(benign, key=lambda r: rank("OR", r["locator"]))[:1000])
    return sorted(picked, key=lambda r: r["sample_id"])


def assign_lineages(rows):
    parent = {r["sample_id"]: r["sample_id"] for r in rows}
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    groups = defaultdict(list)
    for r in rows:
        for g in r["groups"] + ["N1-" + r["n1_sha256"]]:
            groups[g].append(r["sample_id"])
    for members in groups.values():
        for member in members[1:]:
            a, b = find(members[0]), find(member)
            parent[max(a, b)] = min(a, b)
    components = defaultdict(list)
    for r in rows:
        components[find(r["sample_id"])].append(r["sample_id"])
    for r in rows:
        members = sorted(components[find(r["sample_id"])])
        r["lineage_id"] = "R1-LG-" + sha(files.canonical_bytes(members))
        r["lineage_size"] = len(members)
    return dict(component_count=len(components), sizes=sorted(map(len, components.values()), reverse=True),
                construction="Union source-hashed LLMail teams; shared InjecAgent attacker OR user base case; N1 duplicate links; disconnected OR singletons. Transitive union includes both source dependencies; no semantic independence claim.")


def freeze():
    require(not (OUT / "r1_dataset_manifest_v1.json").exists(), "R1_ALREADY_FROZEN")
    created = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if (PRIVATE / "pre_score_rules_v1.json").exists():
        previous = files.read_json(PRIVATE / "pre_score_rules_v1.json")
        require({k: v for k, v in previous.items() if k != "created_at"} == RULES, "PRE_SCORE_RULE_DRIFT")
        created = previous["created_at"]
    selected_files = provenance()
    publish(PRIVATE / "pre_score_rules_v1.json", dict(created_at=created, **RULES))
    candidates, schema = extract()
    eligible, audit = contamination(candidates)
    rows = select(eligible)
    lineages = assign_lineages(rows)
    require(len({r["sample_id"] for r in rows}) == len(rows), "DUPLICATE_SELECTED_ID")
    audit["selected_near_pairs"] = [p for p in audit["near_pairs"] if p["sample_id"] in {r["sample_id"] for r in rows}]
    audit["selected_source_counts"] = Counter(r["source"] for r in rows)
    audit["selected_near_rows_at_threshold"] = {str(t): len({p["sample_id"] for p in audit["selected_near_pairs"] if p["jaccard"] >= t}) for t in (0.7, 0.8, 0.9)}
    pii = {}
    for source in REVISIONS:
        pool = [r for r in rows if r["source"] == source]
        pii[source] = dict(selected_rows=len(pool), email_pattern_rows=sum(bool(re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", r["text"])) for r in pool),
                           status="RESTRICTED_LOCAL_TEXT_ONLY; candidate screening not exhaustive PII clearance")
    clearance = []
    locations = {"LLMAIL_INJECT": "hf://buckets/sumitt86/llmail-inject-challenge-bucket", "OR_BENCH_HARD": "hf://datasets/bench-llms/or-bench", "INJECAGENT_BASE": "Dataset/Raw/datasets/GitHub/InjecAgent"}
    upstreams = {"LLMAIL_INJECT": "https://huggingface.co/datasets/microsoft/llmail-inject-challenge", "OR_BENCH_HARD": "https://huggingface.co/datasets/bench-llm/or-bench", "INJECAGENT_BASE": "https://github.com/uiuc-kang-lab/InjecAgent"}
    evidence = PRIVATE / "source_evidence"
    terms = {"LLMAIL_INJECT": ["llmail_official_README.md", "llmail_bucket_README.md", "llmail_code_LICENSE"], "OR_BENCH_HARD": ["or_official_README.md", "or_given_README.md"], "INJECAGENT_BASE": ["injec_LICENCE", "injec_README.md"]}
    for source in REVISIONS:
        clearance.append(dict(source_id=IDS[source], source=source, local_location=locations[source], authoritative_upstream=upstreams[source],
            upstream_revision=REVISIONS[source], local_revision=("CONTENT_ADDRESSED_BUCKET_SNAPSHOT:" + sha(files.canonical_bytes(selected_files[source]))) if source == "LLMAIL_INJECT" else "fd6ee135ee63ff6c4f3ff72c0e39627bf0a7f314" if source == "OR_BENCH_HARD" else REVISIONS[source],
            license="CC-BY-4.0" if source == "OR_BENCH_HARD" else "MIT", separate_data_specific_terms="Official dataset card MIT / CC-BY-4.0; no narrower terms found in reviewed pinned card/data documentation; not a legal opinion",
            evaluation_use_status="PERMITTED_BY_REVIEWED_PUBLIC_LICENSE; Commander-authorized local academic evaluation",
            redistribution_status="PROJECT_RESTRICTED_LOCAL_ONLY; license permits reuse subject to attribution/notice, but this task authorizes no payload redistribution or PII release",
            attribution_requirement="OR-Bench authors Cui, Chiang, Stoica and Hsieh (2024); original dataset and CC-BY-4.0 link; indicate extraction/sampling" if source == "OR_BENCH_HARD" else "Preserve MIT copyright/permission notices; cite LLMail-Inject Abdelnabi et al. (2025)" if source == "LLMAIL_INJECT" else "Preserve MIT copyright/permission notice (Qiusi Zhan 2023); cite InjecAgent authors/paper and pinned source",
            privacy_status=pii[source], selected_files=selected_files[source], file_hashes={f["role"]: f["sha256"] for f in selected_files[source]},
            contamination_status={**audit["candidate_counts"][source], "selected_exact_or_canonical_development_overlap": 0, "pretraining_or_hidden_source_overlap": "UNKNOWN"},
            clearance_state="CLEARED_WITH_LOCAL_ONLY_RESTRICTION", clearance_evidence=[info(evidence / p, p) for p in terms[source]]))
    qualification = dict(artifact_version="r1_source_clearance_v1", created_at=created, sources=clearance, llmail_schema=schema,
        llmail_labelled_release_inventory=[{k: v for k, v in r.items() if k in ("path", "size", "lfs", "oid", "lastCommit")} for r in files.read_json(evidence / "llmail_upstream_tree.json") if "labelled_unique" in r["path"]],
        mirror_caveats=["HF buckets have no Git revision: content-addressed file snapshot instead; no fabricated commit", "Original OR bucket returned 404; newest explicit user URL bench-llms/or-bench is used and byte-verified against original bench-llm"],
        known_upstream_contamination=["LLMail intentionally adaptive to disclosed upstream defenses (Prompt Shield/TaskTracker/judge); not targeted at our stack", "InjecAgent reuses attacker/user base cases across tools; transitive source lineage union", "OR hard subset model-selected for over-refusal; public seed/pretraining reuse cannot be ruled out"],
        protected_source_payloads_opened=False, detector_scoring=False, historical_gate_b_blocker_superseded_prospectively=True)
    local = PRIVATE / "r1_inputs_v1.jsonl"
    with local.open("xb") as stream:
        for r in rows:
            stream.write(files.canonical_bytes(dict(sample_id=r["sample_id"], text=r["text"])) + b"\n")
    metadata = [{k: v for k, v in r.items() if k != "text"} for r in rows]
    publish(OUT / "r1_source_clearance_v1.json", qualification)
    publish(OUT / "r1_contamination_audit_v1.json", audit)
    publish(OUT / "r1_sample_manifest_v1.json", dict(artifact_version="r1_sample_manifest_v1", created_at=created, samples=metadata,
        private_input=info(local, "local_only_detector_inputs"), lineage=lineages))
    publish(OUT / "r1_source_selection_v1.json", dict(artifact_version="r1_source_selection_v1", created_at=created, rules=RULES,
        pre_score_rule_sha256=files.sha(PRIVATE / "pre_score_rules_v1.json"), source_counts=Counter(r["source"] for r in rows),
        selected_ids=[r["sample_id"] for r in rows], llmail_team_counts=Counter(r["groups"][0] for r in rows if r["source"] == "LLMAIL_INJECT"),
        injec_user_tool_counts=Counter(r["metadata"]["user_tool"] for r in rows if r["source"] == "INJECAGENT_BASE"),
        detector_scores_inspected=False))
    samples = []
    for r in rows:
        payload = sample_payload("R1_SHIFTED_UNSEEN", sample_id=r["sample_id"], label=r["truth_label"])
        singleton = r["source"] == "OR_BENCH_HARD" and r["lineage_size"] == 1
        payload.update(dataset_id=IDS[r["source"]], dataset_revision=REVISIONS[r["source"]], source=r["source"], source_native_id=None,
            attack_family="INDIRECT_PROMPT_INJECTION" if r["source"] == "LLMAIL_INJECT" else "AGENT_TOOL_INJECTION" if r["truth_label"] else None,
            attack_family_provenance="PROTOCOL_DECLARED" if r["truth_label"] else "NOT_APPLICABLE",
            lineage_id=r["lineage_id"], lineage_provenance_status="SINGLETON_FALLBACK" if singleton else "SOURCE_PROVIDED" if r["groups"] else "CANONICAL_DUPLICATE_GROUP",
            lineage_justification="Source dependencies unioned with N1 duplicates; OR singleton fallback where no documented parent; not proof of independence.", created_at=created, provenance_status="PARTIAL")
        samples.append(payload)
    contracts = FrozenRegimeContracts()
    evidence_refs = [dict(role=name, path=(OUT / (name + "_v1.json")).relative_to(ROOT).as_posix(), sha256=files.sha(OUT / (name + "_v1.json"))) for name in
                     ("r1_source_clearance", "r1_sample_manifest", "r1_source_selection", "r1_contamination_audit")]
    manifest = create_manifest(dataset_id="R1-CORE-LLMAIL-INJEC-OR-v1", dataset_revision=sha(files.canonical_bytes([r["sample_id"] for r in rows])),
        partition="INTERNAL_TEST", threat_regime="R1_SHIFTED_UNSEEN", dataset_source="COMMANDER_R1_CLEARANCE_001", dataset_source_revision=files.sha(OUT / "r1_source_clearance_v1.json"),
        dataset_sources=[dict(dataset_id=IDS[s], dataset_revision=v, source=s, source_revision=v) for s, v in REVISIONS.items()],
        created_at=created, primary_detector_set_id=contracts.detectors["stack_id"], primary_detector_manifest_sha="2da5aa92cb14ac19cd49fa7150e7a4ef79b59e1e5fb1aa8ba4148456da618f31",
        prediction_schema_version="prediction_v1", prediction_schema_sha="f61cc717b6118e288201ee8525b41e6806a642d665c42c0d1b9d6d1bcde2e484", status="FROZEN", evidence_kind="ACCEPTED_METADATA",
        notes=["Source labels are attack attempts, not success. Existing public releases, no newly generated attacks.", "Input text verbatim; source annotations/keys never passed to detectors. Raw payloads local only.", "LINEAGE_CLUSTERED frozen pre-score; source/user dependencies may produce large clusters; pretraining unknown."],
        evidence=evidence_refs, external_parents=[], samples=samples)
    contracts.validate_manifest(manifest)
    publish(OUT / "r1_dataset_manifest_v1.json", manifest.model_dump(mode="json"))
    print(json.dumps(dict(status="FROZEN_PENDING_TESTS_AND_COMMIT", sample_count=len(rows), source_counts=Counter(r["source"] for r in rows),
                         lineage=lineages, selected_near=audit["selected_near_rows_at_threshold"])), flush=True)


if __name__ == "__main__":
    freeze()
