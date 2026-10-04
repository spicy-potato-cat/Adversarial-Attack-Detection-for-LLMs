"""Construct/check QUALITY-001 from manifest metadata, never raw text or models."""

import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import io
import json
from pathlib import Path

from .policy import (ARTIFACT_DIR, FOLD_PATH, FIXTURE_VERSION, MANIFEST_PATH, MANIFEST_SHA256,
                     N_FOLDS, SEED, config_schema, fixture_config, result_schemas)

ROOT = Path(__file__).resolve().parents[2]
COLUMNS = ("sample_id", "partition", "label", "lineage_group", "source_name", "outer_fold")
SOURCES = {"Do-Not-Answer": "DS-TXT-017", "deepset Prompt Injection": "DS-TXT-018"}
POLICY_PATHS = ("data_governance/DATA_LINEAGE_POLICY_v1.md", "data_governance/DATA_PARTITION_POLICY_v1.md")


class FixtureError(ValueError):
    """A frozen fixture constraint was violated; stop rather than repair it."""


def require(condition, message):
    if not condition:
        raise FixtureError(message)


def file_hash(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def json_bytes(value):
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False) + "\n").encode("utf-8")


def validate_base(rows, expected_count=None):
    require(bool(rows), "BASE_TRAIN metadata is empty")
    if expected_count is not None:
        require(len(rows) == expected_count, "BASE_TRAIN count drift")
    seen = set()
    group_hashes = defaultdict(set)
    group_labels = defaultdict(set)
    for row in rows:
        require(row.get("partition") == "BASE_TRAIN" and row.get("data_role") == "BASE_TRAIN", "non-BASE_TRAIN row")
        sid = row.get("record_id")
        require(bool(sid) and sid not in seen, "missing or duplicate sample identity")
        seen.add(sid)
        require(row.get("canonical_label") in ("0", "1"), "invalid label")
        source = row.get("source_dataset")
        require(source in SOURCES and row.get("source_dataset_id") == SOURCES[source], "unapproved/ambiguous source")
        normalized = row.get("normalized_hash", "")
        require(len(normalized) == 64 and all(c in "0123456789abcdef" for c in normalized), "invalid normalized hash")
        group = row.get("lineage_group_id")
        require(group == "LG-N1-" + normalized[:24], "lineage grouping missing or ambiguous")
        group_hashes[group].add(normalized)
        group_labels[group].add(row["canonical_label"])
    require(all(len(v) == 1 for v in group_hashes.values()), "lineage prefix collision")
    require(all(len(v) == 1 for v in group_labels.values()), "conflicting labels within lineage group")
    require(len(group_hashes) >= N_FOLDS, "fewer than five lineage groups")


def load_manifest(path=ROOT / MANIFEST_PATH):
    require(file_hash(path) == MANIFEST_SHA256, "authoritative manifest SHA-256 mismatch")
    counts = Counter()
    base = []
    ids = set()
    groups = defaultdict(set)
    with Path(path).open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        require(bool(reader.fieldnames) and "lineage_group_id" in reader.fieldnames, "missing lineage field")
        for row in reader:
            partition = row["partition"]
            counts[partition] += 1
            require(row["record_id"] not in ids, "duplicate manifest identity")
            ids.add(row["record_id"])
            groups[row["lineage_group_id"]].add(partition)
            if partition == "BASE_TRAIN":
                # Only this metadata projection leaves the manifest reader.
                base.append({k: row[k] for k in ("record_id", "partition", "data_role", "canonical_label",
                                                "source_dataset", "source_dataset_id", "lineage_group_id", "normalized_hash")})
    require(dict(counts) == {"BASE_TRAIN": 1135, "CALIBRATION": 233, "VALIDATION": 233}, "manifest partition count drift")
    require(all(len(v) == 1 for v in groups.values()), "manifest lineage crosses partitions")
    validate_base(base, 1135)
    require(Counter(r["canonical_label"] for r in base) == {"1": 183, "0": 952}, "BASE_TRAIN label count drift")
    require(Counter(r["source_dataset"] for r in base) == {"Do-Not-Answer": 659, "deepset Prompt Injection": 476}, "BASE_TRAIN source count drift")
    return base, {"TOTAL": sum(counts.values()), **dict(counts)}


def tie_hash(value):
    return hashlib.sha256(f"{SEED}|{value}".encode("utf-8")).hexdigest()


def generate_folds(base, seed=SEED, n_folds=N_FOLDS):
    require(type(seed) is int and seed == SEED, "seed must be 1701")
    require(type(n_folds) is int and n_folds == N_FOLDS, "exactly five folds required")
    validate_base(base)
    groups = defaultdict(list)
    for row in base:
        groups[row["lineage_group_id"]].append(row)
    # Positives first; largest indivisible groups first within each label.
    order = sorted(groups, key=lambda g: (-int(groups[g][0]["canonical_label"]), -len(groups[g]), tie_hash("order|" + g)))
    label_counts = [Counter() for _ in range(N_FOLDS)]
    source_counts = [Counter() for _ in range(N_FOLDS)]
    sizes = [0] * N_FOLDS
    assignment = {}
    for group in order:
        members = groups[group]
        label = members[0]["canonical_label"]
        sources = Counter(r["source_dataset"] for r in members)
        n = len(members)

        def objective(fold):
            # Incremental squared-load costs; lexicographic priority is explicit.
            label_cost = 2 * label_counts[fold][label] * n + n * n
            source_cost = sum(2 * source_counts[fold][s] * c + c * c for s, c in sources.items())
            return (label_cost, source_cost, sizes[fold], tie_hash(f"fold|{group}|{fold}"))

        fold = min(range(N_FOLDS), key=objective)
        assignment[group] = fold
        label_counts[fold][label] += n
        source_counts[fold].update(sources)
        sizes[fold] += n
    rows = [{"sample_id": r["record_id"], "partition": "BASE_TRAIN", "label": r["canonical_label"],
             "lineage_group": r["lineage_group_id"], "source_name": r["source_dataset"],
             "outer_fold": str(assignment[r["lineage_group_id"]])} for r in sorted(base, key=lambda r: r["record_id"])]
    check_rows(rows, base, deterministic=False)
    return rows


def fold_bytes(rows):
    handle = io.StringIO(newline="")
    writer = csv.DictWriter(handle, fieldnames=COLUMNS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return handle.getvalue().encode("utf-8")


def check_rows(rows, base, deterministic=True):
    validate_base(base)
    require(all(set(row) == set(COLUMNS) for row in rows), "unexpected columns/raw text not permitted")
    ids = [r["sample_id"] for r in rows]
    expected = {r["record_id"]: r for r in base}
    require(len(ids) == len(set(ids)), "duplicate fold assignment")
    require(set(ids) == set(expected), "missing or extra BASE_TRAIN samples")
    require({r["outer_fold"] for r in rows} == {str(f) for f in range(N_FOLDS)}, "invalid/missing fold IDs")
    groups = defaultdict(set)
    for row in rows:
        source = expected[row["sample_id"]]
        require(row["partition"] == "BASE_TRAIN", "non-BASE_TRAIN fold row")
        require(row["label"] in ("0", "1") and row["label"] == source["canonical_label"], "invalid/drifted label")
        require(row["lineage_group"] == source["lineage_group_id"], "lineage metadata drift")
        require(row["source_name"] == source["source_dataset"], "source metadata drift")
        groups[row["lineage_group"]].add(row["outer_fold"])
    require(all(len(v) == 1 for v in groups.values()), "lineage group split across folds")
    if deterministic:
        require(fold_bytes(rows) == fold_bytes(generate_folds(base)), "deterministic assignment/order drift")


def fold_statistics(rows):
    folds = []
    for fold in range(N_FOLDS):
        selected = [r for r in rows if r["outer_fold"] == str(fold)]
        positive = sum(r["label"] == "1" for r in selected)
        sources = {}
        for source in sorted(SOURCES):
            members = [r for r in selected if r["source_name"] == source]
            pos = sum(r["label"] == "1" for r in members)
            sources[source] = {"rows": len(members), "positive": pos, "negative": len(members) - pos}
        folds.append({"outer_fold": fold, "rows": len(selected), "positive": positive,
                      "negative": len(selected) - positive, "lineage_groups": len({r["lineage_group"] for r in selected}),
                      "outer_training_rows": len(rows) - len(selected), "sources": sources})
    groups = defaultdict(set)
    for r in rows:
        groups[r["lineage_group"]].add(r["outer_fold"])
    return {"fixture_version": FIXTURE_VERSION, "role": "DEVELOPMENT_ONLY", "rows": len(rows),
            "lineage_groups": len(groups), "lineage_leakage": sum(len(v) > 1 for v in groups.values()),
            "folds": folds, "held_out_assignments_per_sample": 1, "training_fold_memberships_per_sample": 4}


def freeze(root=ROOT):
    import jsonschema

    root = Path(root)
    destination = root / ARTIFACT_DIR
    require(not destination.exists(), "fixture already exists: immutable freeze refuses overwrite")
    base, counts = load_manifest(root / MANIFEST_PATH)
    evidence = [{"path": p, "sha256": file_hash(root / p)} for p in POLICY_PATHS]
    rows = generate_folds(base)  # One construction; checker reproductions only verify integrity.
    payload = fold_bytes(rows)
    config = fixture_config(hashlib.sha256(payload).hexdigest(), evidence)
    schema = config_schema(config)
    jsonschema.Draft202012Validator(schema).validate(config)
    files = {"development_folds_v1.csv": payload, "quality_fixture_v1.json": json_bytes(config),
             "fold_statistics_v1.json": json_bytes(fold_statistics(rows)), "quality_fixture_schema_v1.json": json_bytes(schema),
             **{name: json_bytes(value) for name, value in result_schemas().items()}}
    destination.mkdir(parents=True, exist_ok=False)
    for name, data in files.items():
        with (destination / name).open("xb") as handle:
            handle.write(data)
    bound = {f"{ARTIFACT_DIR}/{name}": file_hash(destination / name) for name in files}
    for p in (*POLICY_PATHS, MANIFEST_PATH, "detection_service/quality/development_fixture.py", "detection_service/quality/policy.py"):
        bound[p] = file_hash(root / p)
    with (destination / "integrity_manifest_v1.json").open("xb") as handle:
        handle.write(json_bytes({"fixture_version": FIXTURE_VERSION, "sha256": bound}))
    return {"status": "FROZEN", "manifest_counts": counts, "fold_sha256": config["fold_artifact_sha256"],
            "integrity_sha256": file_hash(destination / "integrity_manifest_v1.json"), "statistics": fold_statistics(rows)}


def verify(root=ROOT):
    from .freeze_constants import INTEGRITY_SHA256
    root = Path(root)
    destination = root / ARTIFACT_DIR
    integrity = destination / "integrity_manifest_v1.json"
    require(file_hash(integrity) == INTEGRITY_SHA256, "trusted integrity anchor mismatch")
    bound = json.loads(integrity.read_text(encoding="utf-8"))
    for path, expected in bound["sha256"].items():
        require(file_hash(root / path) == expected, f"frozen hash drift: {path}")
    base, counts = load_manifest(root / MANIFEST_PATH)
    config = json.loads((destination / "quality_fixture_v1.json").read_text(encoding="utf-8"))
    schema = json.loads((destination / "quality_fixture_schema_v1.json").read_text(encoding="utf-8"))
    import jsonschema
    jsonschema.Draft202012Validator(schema).validate(config)
    require(config["manifest_sha256"] == MANIFEST_SHA256, "config manifest mismatch")
    require(file_hash(root / FOLD_PATH) == config["fold_artifact_sha256"], "fold artifact SHA-256 mismatch")
    with (root / FOLD_PATH).open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        require(tuple(reader.fieldnames or ()) == COLUMNS, "fold column drift")
        rows = list(reader)
    check_rows(rows, base)
    require((root / FOLD_PATH).read_bytes() == fold_bytes(rows), "fold serialization drift")
    recorded_stats = json.loads((destination / "fold_statistics_v1.json").read_text(encoding="utf-8"))
    require(recorded_stats == fold_statistics(rows), "statistics drift")
    return {"status": "PASS", "manifest_counts": counts, "fold_sha256": config["fold_artifact_sha256"],
            "integrity_sha256": INTEGRITY_SHA256, "hash_checks": len(bound["sha256"]), "statistics": recorded_stats}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", required=True, choices=("freeze", "check"))
    args = parser.parse_args()
    print(json.dumps(freeze() if args.mode == "freeze" else verify(), indent=2))


if __name__ == "__main__":
    main()
