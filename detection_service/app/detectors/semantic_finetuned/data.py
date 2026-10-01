from __future__ import annotations

import csv
import hashlib
from collections import Counter, defaultdict
from pathlib import Path

from detection_service.app.detectors.semantic.calibration import file_sha256
from detection_service.app.detectors.semantic_finetuned.config import MANIFEST_SHA256
from detection_service.scripts.calibrate_semantic_baseline import SOURCE_FILES, validate_rows


def load_partition(manifest: Path, partition: str) -> list[dict[str, str]]:
    if partition not in {"BASE_TRAIN", "VALIDATION"}:
        raise RuntimeError("D_M-B cannot consume CALIBRATION or protected partitions")
    if file_sha256(manifest) != MANIFEST_SHA256:
        raise RuntimeError("STOP: development manifest integrity failure")
    with manifest.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if Counter(r["partition"] for r in rows) != {"BASE_TRAIN": 1135, "CALIBRATION": 233, "VALIDATION": 233}:
        raise RuntimeError("authoritative partition counts differ")
    validate_rows(rows)
    return [r for r in rows if r["partition"] == partition]


def load_texts(rows: list[dict[str, str]], workspace: Path, partition: str) -> tuple[list[str], dict[str, str]]:
    if partition not in {"BASE_TRAIN", "VALIDATION"} or any(r["partition"] != partition for r in rows):
        raise RuntimeError("D_M-B text loader rejects calibration or mixed partitions")
    import pyarrow.parquet as pq

    selected = defaultdict(dict)
    for row in rows:
        artifact, locator = row["canonical_text_reference"].split("::")
        if artifact not in SOURCE_FILES:
            raise RuntimeError("non-approved source artifact")
        source = "Do-Not-Answer" if artifact == "ART-W2-DNA-INSTRUCTIONS" else "deepset Prompt Injection"
        expected_type = "csv_row" if source == "Do-Not-Answer" else "parquet_row"
        kind, number = locator.split(":")
        if row["source_dataset"] != source or kind != expected_type or int(number) < 1:
            raise RuntimeError("source/locator mismatch")
        index = int(number) - 1
        if index in selected[artifact]:
            raise RuntimeError("duplicate source locator")
        selected[artifact][index] = row
    texts, source_hashes = {}, {}
    for artifact, wanted in selected.items():
        path = workspace / SOURCE_FILES[artifact]
        source_hashes[SOURCE_FILES[artifact]] = file_sha256(path)
        if artifact == "ART-W2-DNA-INSTRUCTIONS":
            with path.open(encoding="utf-8-sig", newline="") as handle:
                for index, record in enumerate(csv.DictReader(handle)):
                    if index in wanted:
                        texts[wanted[index]["record_id"]] = record["question"]
        else:
            table = pq.read_table(path, columns=["text", "label"])
            for index, row in wanted.items():
                if str(table["label"][index].as_py()) != row["original_label"]:
                    raise RuntimeError("source label differs from frozen manifest")
                texts[row["record_id"]] = table["text"][index].as_py()
        if file_sha256(path) != source_hashes[SOURCE_FILES[artifact]]:
            raise RuntimeError("source changed while loading selected records")
    ordered = []
    for row in rows:
        text = texts.get(row["record_id"])
        if not isinstance(text, str) or not text.strip():
            raise RuntimeError("selected development text is missing")
        if hashlib.sha256(text.encode("utf-8")).hexdigest() != row["exact_hash"]:
            raise RuntimeError("selected text hash differs from manifest")
        ordered.append(text)
    return ordered, source_hashes


def class_weights(rows: list[dict[str, str]]) -> list[float]:
    if not rows or any(r["partition"] != "BASE_TRAIN" for r in rows):
        raise RuntimeError("class weights may use BASE_TRAIN only")
    counts = Counter(int(r["canonical_label"]) for r in rows)
    if set(counts) != {0, 1}:
        raise RuntimeError("both approved binary labels are required")
    return [len(rows) / (2 * counts[i]) for i in (0, 1)]
