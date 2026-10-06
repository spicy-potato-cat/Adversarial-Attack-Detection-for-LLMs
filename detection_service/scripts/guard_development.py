"""One-shot frozen D_G BASE_TRAIN characterization; never train or calibrate.

python -m detection_service.scripts.guard_development --check
python -m detection_service.scripts.guard_development --run
Checks finish before payload loading/model imports. Interrupted runs are never
silently repeated: a persistent exclusive start marker prevents duplicate scores.
"""
import argparse
import csv
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
import json
import math
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys

from detection_service.analysis.common_mode import require
from detection_service.analysis.development_characterization import characterization
from detection_service.scripts.common_mode_development import (
    ROOT, MODEL, REVISION, MANIFEST, FOLDS, GUARD_OUTPUT, checked_hash, digest,
    read_csv, read_json, write_json, csv_output, check_hashes,
)

MANIFEST_PATH = "data_governance/manifests/development_partition_manifest_v1.csv"
FOLD_PATH = "artifacts/quality/quality_001/development_folds_v1.csv"
PACKAGES = {"torch": "2.6.0", "transformers": "4.49.0", "tokenizers": "0.21.4",
            "scikit-learn": "1.6.1", "numpy": "2.1.3", "pyarrow": "19.0.1"}


def environment():
    """Report versions without loading ML packages or credentials."""
    packages = {}
    for name in PACKAGES:
        try:
            packages[name] = version(name)
        except PackageNotFoundError:
            packages[name] = None
    visible = shutil.which("nvidia-smi")
    return {"python": platform.python_version(), "platform": platform.platform(), "packages": packages,
            "device": "cpu", "cuda_runtime_visibility": "NOT_PROBED_WITHOUT_MODEL_RUNTIME",
            "nvidia_smi_visible": bool(visible), "cpu_count": os.cpu_count()}


def hf_status():
    """Probe CLI authentication; return a status only, never token/account data."""
    executable = shutil.which("hf")
    if not executable:
        candidate = Path.home() / "OneDrive/문서/ChatGPT/capstone/dgad-repo/main/.venv/Scripts/hf.exe"
        executable = str(candidate) if candidate.is_file() else None
    if executable is None:
        return {"status": "CLI_NOT_INSTALLED", "command": "hf auth login"}
    try:
        response = subprocess.run([executable, "auth", "whoami"], capture_output=True, text=True, timeout=20)
        combined = response.stdout + response.stderr
        if "Not logged in" in combined:
            status = "NOT_LOGGED_IN"
        else:
            status = "AUTHENTICATED" if response.returncode == 0 else "ACCESS_CHECK_UNAVAILABLE"
        return {"status": status, "cli": executable, "command": "hf auth login"}
    except (OSError, subprocess.TimeoutExpired):
        return {"status": "ACCESS_CHECK_UNAVAILABLE", "command": "hf auth login"}


def preflight(root=ROOT, auth=None):
    """Verify exact inputs before any prompt scalar or detector is accessed."""
    require(subprocess.check_output(["git", "branch", "--show-current"], cwd=root, text=True).strip()
            in {"tech/common-001", "tech/common-003-dg-completion"}, "wrong Track-2 branch")
    freeze_dir = "artifacts/models/dg_v1"
    integrity = read_json(root / freeze_dir / "integrity_manifest.json")
    check_hashes(root, freeze_dir, integrity)
    freeze = read_json(root / freeze_dir / "freeze_metadata.json")
    config = read_json(root / freeze_dir / "model_config.json")
    require(freeze["model_id"] == config["model_id"] == MODEL and freeze["revision"] == config["revision"] == REVISION,
            "frozen guard revision mismatch")
    require(config["chunk_tokens"] == 510 and config["overlap_tokens"] == 64 and config["context_tokens"] == 512
            and config["aggregation"] == "max_chunk_malicious_probability" and config["decision"] == "OR_of_native_chunk_argmax_class_1", "guard policy mismatch")
    sources = read_json(root / "artifacts/statistical_v2/oof/completion_v1.json")["source_artifact_sha256"]
    # Derive source locator keys from the frozen loader's literal map, without
    # importing its detector/training dependencies. Unknown keys are refused.
    import ast
    module = ast.parse((root / "detection_service/scripts/calibrate_semantic_baseline.py").read_text(encoding="utf-8"))
    source_map = next(ast.literal_eval(node.value) for node in module.body if isinstance(node, ast.Assign)
                      and any(isinstance(t, ast.Name) and t.id == "SOURCE_FILES" for t in node.targets))
    require(set(source_map.values()) == set(sources), "approved source inventory mismatch")
    missing = []
    verified = {}
    for name, expected in {MANIFEST_PATH: MANIFEST, FOLD_PATH: FOLDS, **sources}.items():
        if not (root / name).is_file():
            missing.append({"path": name, "sha256": expected})
        else:
            verified[name] = checked_hash(root / name, expected)
    snapshot = (root / freeze["snapshot_path"]).resolve()
    require(snapshot.is_relative_to(root.resolve()), "snapshot escapes repository")
    model_missing = []
    for name, expected in freeze["file_sha256"].items():
        if not (snapshot / name).is_file():
            model_missing.append({"file": name, "sha256": expected})
        else:
            verified[(snapshot / name).relative_to(root).as_posix()] = checked_hash(snapshot / name, expected)
    env = environment()
    mismatches = {name: {"expected": expected, "actual": env["packages"][name]} for name, expected in PACKAGES.items()
                  if (env["packages"][name] or "").split("+")[0] != expected}
    python_ok = sys.version_info[:2] == (3, 11)
    hub = Path(os.environ.get("HF_HUB_CACHE", str(Path(os.environ.get("HF_HOME", str(Path.home() / ".cache/huggingface"))) / "hub")))
    cache = hub / "models--meta-llama--Llama-Prompt-Guard-2-22M/snapshots" / REVISION
    status = "READY" if not missing and not model_missing and not mismatches and python_ok else "BLOCKED"
    base_rows = []
    folds = read_csv(root / FOLD_PATH)
    require(len(folds) == 1135 and len({r["sample_id"] for r in folds}) == 1135, "fold population mismatch")
    require(all(r["partition"] == "BASE_TRAIN" and r["label"] in ("0", "1") for r in folds)
            and sum(r["label"] == "1" for r in folds) == 183 and {r["outer_fold"] for r in folds} == set("01234"), "fold partition/count mismatch")
    lineage_folds = {}
    for row in folds:
        require(row["lineage_group"] not in lineage_folds or lineage_folds[row["lineage_group"]] == row["outer_fold"], "canonical-lineage fold leakage")
        lineage_folds[row["lineage_group"]] = row["outer_fold"]
    if (root / MANIFEST_PATH).is_file():
        # Parse only manifest metadata; never reserved prompt payloads.
        with (root / MANIFEST_PATH).open(encoding="utf-8", newline="") as stream:
            base_rows = [r for r in csv.DictReader(stream) if r["partition"] == "BASE_TRAIN"]
        require(len(base_rows) == 1135 and sum(r["canonical_label"] == "1" for r in base_rows) == 183
                and sum(r["canonical_label"] == "0" for r in base_rows) == 952, "manifest BASE_TRAIN counts mismatch")
        lookup = {r["record_id"]: r for r in base_rows}
        require(len(lookup) == 1135 and set(lookup) == {r["sample_id"] for r in folds}, "manifest identity mismatch")
        for fold in folds:
            row = lookup[fold["sample_id"]]
            require(row["canonical_label"] == fold["label"] and row["lineage_group_id"] == fold["lineage_group"]
                    and row["source_dataset"] == fold["source_name"], "manifest/fold metadata mismatch")
        base_rows = [lookup[r["sample_id"]] for r in sorted(folds, key=lambda r: r["sample_id"])]
    gate = {"status": status, "data_status": "BLOCKED_MISSING_AUTHORITATIVE_DEVELOPMENT_DATA" if missing else "VERIFIED",
            "model_status": "BLOCKED_MISSING_PINNED_MODEL" if model_missing else "VERIFIED",
            "missing_inputs": missing, "missing_snapshot_files": model_missing, "snapshot_path": str(snapshot),
            "hf_cache_checked": str(cache), "hf_cache_present": cache.is_dir(), "hf_access": auth if auth is not None else hf_status(),
            "package_mismatches": mismatches, "python_3_11": python_ok, "environment": env,
            "model_id": MODEL, "revision": REVISION, "manifest_sha256": MANIFEST, "fold_sha256": FOLDS,
            "verified_sha256": verified, "live_rows_scored": 0,
            "unblock": ["Restore exact authoritative manifest and three approved source files; verify listed hashes. No supported exact bootstrap was found.",
                        "hf auth login; hf auth whoami. Obtain access at https://huggingface.co/meta-llama/Llama-Prompt-Guard-2-22M if needed.",
                        f'hf download {MODEL} --revision {REVISION} --local-dir "{snapshot}"',
                        "Install detection_service/requirements.txt and pyarrow==19.0.1 tokenizers==0.21.4 in Python 3.11; keep frozen versions.",
                        "python -m detection_service.scripts.guard_development --check",
                        "python -m detection_service.scripts.guard_development --run",
                        "python -m detection_service.scripts.common_mode_completion"],
            "no_raw_prompt_text_saved": True, "scope": "DEVELOPMENT_ONLY"}
    return gate, base_rows, folds, source_map, sources


def install_payload_gate(root, allowed):
    """Deny non-approved Dataset and all forensic/protected payload opens."""
    dataset, forensic = (root / "Dataset").resolve(), (root / "PHASE-3").resolve()
    paths = {(root / name).resolve() for name in allowed}
    def audit(event, args):
        if event != "open" or not isinstance(args[0], (str, bytes, os.PathLike)):
            return
        path = Path(os.fsdecode(args[0])).resolve()
        require(not (path == forensic or forensic in path.parents), "forensic/protected payload access refused")
        if path == dataset or dataset in path.parents:
            require(path in paths, "non-approved dataset payload access refused")
            require(not isinstance(args[1], str) or not any(c in args[1] for c in "wax+"), "raw payload write refused")
    sys.addaudithook(audit)


def selected_texts(root, rows, source_map, source_hashes):
    """Materialize only approved BASE_TRAIN text scalars from original containers.

Original approved containers include other project partitions. This follows
the accepted scalar-selection policy: only indexed BASE_TRAIN prompt strings
are selected, validated, handed to the detector or reported. No source text is
printed or copied to artifacts. No reconstructed/downloaded corpus is accepted.
"""
    require(all(r["partition"] == "BASE_TRAIN" for r in rows), "reserved text selection")
    wanted = {}
    for row in rows:
        artifact, locator = row["canonical_text_reference"].split("::")
        require(artifact in source_map, "unknown source locator")
        kind, number = locator.split(":")
        expected_kind = "csv_row" if source_map[artifact].endswith(".csv") else "parquet_row"
        require(kind == expected_kind and int(number) > 0, "invalid source locator")
        selection = wanted.setdefault(artifact, {})
        index = int(number) - 1
        require(index not in selection, "duplicate source locator")
        selection[index] = row
    texts = {}
    for artifact, selection in wanted.items():
        name = source_map[artifact]
        path = root / name
        checked_hash(path, source_hashes[name])
        if path.suffix == ".csv":
            with path.open(encoding="utf-8-sig", newline="") as stream:
                for index, record in enumerate(csv.DictReader(stream)):
                    if index in selection:
                        texts[selection[index]["record_id"]] = record["question"]
        else:
            import pyarrow.parquet as pq
            table = pq.read_table(path, columns=["text", "label"])
            for index, row in selection.items():
                require(str(table["label"][index].as_py()) == row["original_label"], "selected source label mismatch")
                texts[row["record_id"]] = table["text"][index].as_py()
        checked_hash(path, source_hashes[name])
    import hashlib
    for row in rows:
        text = texts.get(row["record_id"])
        require(isinstance(text, str) and text.strip(), "missing selected text")
        require(hashlib.sha256(text.encode("utf-8")).hexdigest() == row["exact_hash"], "selected text hash mismatch")
    return [texts[r["record_id"]] for r in rows]


def score_records(rows, folds, texts, detect):
    """Invoke one detector exactly once per authorized, unique sample.

The detect callback returns primitive result fields. Production uses the
unchanged GuardDetector; test injection is confined to synthetic unit tests.
"""
    require(len(rows) == len(texts) and bool(rows), "scoring membership mismatch")
    require(all(r["partition"] == "BASE_TRAIN" for r in rows), "reserved scoring population")
    require(all(isinstance(text, str) and text.strip() for text in texts), "invalid scoring input")
    require(all(r["partition"] == "BASE_TRAIN" for r in folds), "reserved scoring fold")
    require(len({r["record_id"] for r in rows}) == len(rows), "duplicate scoring identity")
    lookup = {r["sample_id"]: r for r in folds}
    require(len(lookup) == len(folds) and set(lookup) == {r["record_id"] for r in rows}, "scoring fold identity mismatch")
    for row in rows:
        fold = lookup[row["record_id"]]
        require(row["canonical_label"] == fold["label"] and row["lineage_group_id"] == fold["lineage_group"], "scoring metadata mismatch")
    for row, text in zip(rows, texts):
        require(isinstance(text, str) and text.strip(), "invalid scoring input")
        raw = detect(row["record_id"], text)
        require(raw["status"] == "success" and raw["detector_id"] == "guard_external" and raw["detector_version"] == "dg_v1", "invalid frozen guard result")
        require(raw["model_revision"] == REVISION, "scored model revision mismatch")
        require(type(raw["raw_score"]) in (int, float) and math.isfinite(raw["raw_score"]) and 0 <= raw["raw_score"] <= 1, "invalid guard risk score")
        require(type(raw["binary_vote"]) is bool and math.isfinite(raw["latency_ms"]) and raw["latency_ms"] >= 0, "invalid native/latency result")
        coverage = raw["input_coverage"]
        require(coverage["coverage_ratio"] == 1 and coverage["tokens_excluded"] == 0 and not coverage["truncated"], "frozen guard coverage changed")
        require(coverage["tokens_analyzed"] == coverage["input_tokens"] and coverage["inference_chunks"] >= 1, "incomplete guard coverage")
        yield {"sample_id": row["record_id"], "partition": "BASE_TRAIN", "label": int(row["canonical_label"]),
               "source_name": row["source_dataset"], "lineage_group": row["lineage_group_id"],
               "fold": int(lookup[row["record_id"]]["outer_fold"]), "detector_id": "guard_external", "detector_version": "dg_v1",
               "raw_score": raw["raw_score"], "native_binary_prediction": int(raw["binary_vote"]),
               "input_tokens": coverage["input_tokens"], "tokens_analyzed": coverage["tokens_analyzed"],
               "tokens_excluded": 0, "inference_chunks": coverage["inference_chunks"], "coverage_ratio": 1.,
               "truncated": False, "latency_ms": raw["latency_ms"]}


def run_live(root=ROOT):
    """Run once only after data, model bytes, runtime and branch gates pass."""
    gate, rows, folds, source_map, sources = preflight(root)
    require(gate["status"] == "READY", "live D_G blocked; run --check for exact missing inputs")
    output = root / GUARD_OUTPUT
    output.mkdir(parents=True, exist_ok=True)
    require(not (output / "dg_v1_run_started.json").exists() and not (output / "dg_v1_base_train_predictions.csv").exists(), "D_G run already started; no automatic rescoring")
    install_payload_gate(root, sources)
    texts = selected_texts(root, rows, source_map, sources)
    import torch
    from detection_service.app.detectors.guard.detector import GuardDetector
    from detection_service.app.contracts.detection_request import DetectionContent, DetectionRequest
    torch.set_num_threads(min(8, os.cpu_count() or 1))
    detector = GuardDetector.from_artifact(workspace=root, device="cpu")
    require(not detector.model.training and not any(p.requires_grad for p in detector.model.parameters()), "guard not frozen")
    def detect(sid, text):
        result = detector.detect(DetectionRequest(request_id=sid, content=DetectionContent(type="user_prompt", text=text)))
        raw = result.model_dump()
        raw["model_revision"] = result.model.model_revision
        return raw
    with (output / "dg_v1_run_started.json").open("x", encoding="utf-8") as stream:
        json.dump({"status": "STARTED_DO_NOT_RESCORE", "started_utc": datetime.now(timezone.utc).isoformat(),
                   "revision": REVISION, "rows": len(rows), "scope": "BASE_TRAIN_ONLY"}, stream)
    records = []
    with (output / "dg_v1_base_train_predictions.csv").open("x", encoding="utf-8", newline="") as stream:
        writer = None
        for row in score_records(rows, folds, texts, detect):
            if writer is None:
                writer = csv.DictWriter(stream, fieldnames=list(row))
                writer.writeheader()
            writer.writerow(row)
            stream.flush()
            records.append(row)
    del texts
    require(len(records) == 1135, "guard scoring incomplete")
    # Reverify source/model bytes after scoring before publishing COMPLETE.
    repeat, *_ = preflight(root, auth=gate["hf_access"])
    require(repeat["verified_sha256"] == gate["verified_sha256"], "inputs changed during guard run")
    def summarize(selected):
        return characterization([r["label"] for r in selected], [r["raw_score"] for r in selected], [bool(r["native_binary_prediction"]) for r in selected])
    write_json(output / "dg_v1_development_metrics.json", summarize(records))
    write_json(output / "dg_v1_fold_metrics.json", [{"fold": fold, **summarize([r for r in records if r["fold"] == fold])} for fold in range(5)])
    write_json(output / "dg_v1_source_metrics.json", [{"source": source, **summarize([r for r in records if r["source_name"] == source])} for source in sorted({r["source_name"] for r in records})])
    metadata = {"status": "COMPLETE", "model_id": MODEL, "revision": REVISION, "manifest_sha256": MANIFEST,
                "fold_sha256": FOLDS, "rows": len(records), "positive": 183, "negative": 952,
                "environment": gate["environment"], "torch_runtime": torch.__version__, "cuda_available": torch.cuda.is_available(),
                "device": "cpu", "completed_utc": datetime.now(timezone.utc).isoformat(),
                "code_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(),
                "runner_sha256": digest(root / "detection_service/scripts/guard_development.py"),
                "input_sha256": gate["verified_sha256"], "score_direction": "higher_is_more_adversarial",
                "native_vote": "OR_of_native_chunk_argmax_class_1", "scope": "DEVELOPMENT_ONLY",
                "isolation": {k: False for k in ("training", "calibration", "validation_payload", "protected_payload", "deployment_threshold")}}
    write_json(output / "dg_v1_run_metadata.json", metadata)
    files = ["dg_v1_base_train_predictions.csv", "dg_v1_development_metrics.json", "dg_v1_fold_metrics.json",
             "dg_v1_source_metrics.json", "dg_v1_run_metadata.json", "dg_v1_run_started.json"]
    write_json(output / "dg_v1_integrity.json", {"sha256": {name: digest(output / name) for name in files}})
    print(json.dumps({"status": "COMPLETE", "rows": len(records)}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    choice = parser.add_mutually_exclusive_group(required=True)
    choice.add_argument("--check", action="store_true")
    choice.add_argument("--run", action="store_true")
    args = parser.parse_args()
    if args.check:
        gate, *_ = preflight()
        out = ROOT / GUARD_OUTPUT
        out.mkdir(parents=True, exist_ok=True)
        write_json(out / "dg_v1_availability_v2.json", gate)
        print(json.dumps(gate, indent=2))
    else:
        run_live()
