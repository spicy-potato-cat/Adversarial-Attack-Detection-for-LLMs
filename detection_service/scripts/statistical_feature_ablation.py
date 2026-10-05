"""STAT-004 prepare/run/check; isolated BASE_TRAIN feature ablation, no final model."""

import argparse
import csv
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import numpy as np

from detection_service.analysis.statistical_feature_ablation import BLOCKS, definitions, evaluate, names
from detection_service.analysis.statistical_ablation_results import paired_bootstrap, select, summarize
from detection_service.analysis.statistical_oof import require
from detection_service.app.detectors.statistical.features import extract_features
from detection_service.app.detectors.statistical_risk.schema import FEATURE_NAMES
from detection_service.quality.development_fixture import ROOT, file_hash, json_bytes, verify
from detection_service.scripts import statistical_oof_baseline as baseline

START = "9b63a230943be3f47e812f6495a8f3435fdff642"
MANIFEST = "9cdd5ecdd80f9ac3c8f05db63742721f4537ca2b64a2fe48f6c2b424b57483a6"
FOLDS = "19dc0153cc257cc2331782d6dd61b7bb9fb8cb0ed88d3e782b69d5ba05c4bb8d"
OUT = ROOT / "artifacts/statistical_v2/feature_ablation"
CACHE = ROOT / "detection_service/outputs/stat004/token_evidence.npz"
CODE = ("detection_service/analysis/statistical_feature_ablation.py", "detection_service/analysis/statistical_ablation_results.py",
        "detection_service/scripts/statistical_feature_ablation.py", "detection_service/tests/test_statistical_feature_ablation.py")


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, payload):
    with path.open("xb") as handle:
        handle.write(payload if isinstance(payload, bytes) else json_bytes(payload))


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def preservation_paths():
    roots = (baseline.OUTPUT, ROOT / "artifacts/semantic_v2/oof")
    paths = [p for root in roots for p in root.rglob("*") if p.is_file()]
    paths += [p for p in (ROOT / "reviews").glob("TECH_SEM_003*.md") if p.is_file()]
    return {p.relative_to(ROOT).as_posix(): file_hash(p) for p in sorted(paths)}


def original_records():
    with (baseline.OUTPUT / "ds_v1_recipe_oof_predictions.csv").open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def install_gate(config):
    baseline.install_payload_gate(config)
    def audit(event, args):
        if event == "open" and isinstance(args[0], (str, bytes, os.PathLike)):
            path = Path(os.fsdecode(args[0])).resolve()
            if path.is_relative_to((ROOT / "artifacts/models").resolve()):
                require(not isinstance(args[1], str) or not any(c in args[1] for c in "wax+"), "frozen model writes forbidden")
                require(not args[2] & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND), "frozen model write flags forbidden")
    sys.addaudithook(audit)


def prepare():
    require(git("rev-parse", "HEAD") == START and git("branch", "--show-current") == "tech/stat-004", "wrong authoritative startup HEAD/branch")
    require(not OUT.exists(), "ablation evidence exists; inspect, never overwrite")
    # Initial clean gate was observed before implementation. Only this phase may now be pending.
    pending = subprocess.check_output(["git", "status", "--porcelain", "--untracked-files=all"], cwd=ROOT, text=True)
    require(all(line[3:].replace("\\", "/") in (*CODE, ".gitattributes") for line in pending.splitlines()), "unrelated changes at preparation")
    fixture = verify()
    require(fixture["fold_sha256"] == FOLDS, "fold drift")
    config = baseline.checked_config()
    require(config["manifest_sha256"] == MANIFEST and config["fold_sha256"] == FOLDS, "fixture drift")
    baseline.check()
    OUT.mkdir()
    write(OUT / "feature_block_definitions_v1.json", definitions())
    write(OUT / "preflight_v1.json", {"phase": "TECH-STAT-004", "accepted_start_commit": START,
        "clean_startup": "PASS_OBSERVED_BEFORE_PHASE_EDITS", "branch": "tech/stat-004", "cycle": "1_OF_MAXIMUM_2",
        "manifest_sha256": MANIFEST, "fold_sha256": FOLDS, "rows": 1135, "positive": 183, "negative": 952,
        "definitions_sha256": file_hash(OUT / "feature_block_definitions_v1.json"),
        "code_sha256": {path: file_hash(ROOT / path) for path in CODE}, "preserved_sha256": preservation_paths(),
        "baseline_preservation": baseline.baseline_check(), "environment": baseline.environment(),
        "runtime_estimate_seconds": [120, 240], "prior_stat003_seconds": 58.6148605, "long_run_stop_seconds": 300,
        "cache_policy": "One phase-local frozen-LM pass, BASE_TRAIN only, surprisal floats only; no token strings/IDs or prompt dumps. Fold references fitted afterward within training folds.",
        "B7": "PREDECLARED_SKIPPED", "new_detector_features": "STATISTICAL_ONLY_NO_OTHER_DETECTOR_OUTPUTS"})
    print(json.dumps({"status": "PREDECLARED_NOT_RUN", "feature_counts": {b: len(names(b)) for b in BLOCKS}, "estimated_seconds": [120, 240]}))


def checked():
    payload = read(OUT / "preflight_v1.json")
    require(payload["accepted_start_commit"] == START and payload["fold_sha256"] == FOLDS and payload["manifest_sha256"] == MANIFEST, "preflight provenance drift")
    require(subprocess.run(["git", "merge-base", "--is-ancestor", START, "HEAD"], cwd=ROOT, capture_output=True).returncode == 0, "accepted start not ancestor")
    require(file_hash(OUT / "feature_block_definitions_v1.json") == payload["definitions_sha256"]
            and read(OUT / "feature_block_definitions_v1.json") == definitions(), "feature definitions changed after freeze")
    baseline.verify_hashes(ROOT, payload["code_sha256"])
    baseline.verify_hashes(ROOT, payload["preserved_sha256"])
    require(payload["environment"] == baseline.environment(), "environment drift")
    baseline.checked_config()
    verify()
    return payload


def extract_evidence(rows, sources, config):
    require(not CACHE.exists(), "phase token cache exists; review rather than re-extract")
    texts = baseline.load_base_texts(sources, config)
    detector = baseline.extractor(config)
    original = original_records()
    require([r["sample_id"] for r in original] == [r["sample_id"] for r in rows], "baseline identity/order mismatch")
    evidence, flat, offsets = [], [], [0]
    started = time.perf_counter()
    for i, (row, text, prior) in enumerate(zip(rows, texts, original, strict=True)):
        observation = detector.engine.score(text)
        features = extract_features(observation.surprisals, config["extractor_config"]["window_size"],
                                    config["extractor_config"]["window_stride"], config["extractor_config"]["provisional_high_surprisal_threshold"])
        vector = [float(prior[name]) for name in FEATURE_NAMES]
        fresh = [getattr(features, name) for name in FEATURE_NAMES]
        require(np.array_equal(fresh, vector), f"unchanged LM/v1 extraction drift: {row['sample_id']}")
        require(observation.input_tokens == int(prior["input_tokens"]) and observation.tokens_analyzed == int(prior["tokens_analyzed"])
                and observation.truncated == (prior["truncated"] == "True"), "baseline coverage drift")
        evidence.append({"surprisals": observation.surprisals, "input_tokens": observation.input_tokens,
                         "tokens_analyzed": observation.tokens_analyzed, "v1_features": vector})
        flat.extend(observation.surprisals)
        offsets.append(len(flat))
        if (i + 1) % 100 == 0 or i + 1 == len(rows):
            print(json.dumps({"token_evidence_rows": i + 1, "total": len(rows), "seconds": time.perf_counter() - started}), flush=True)
        require(time.perf_counter() - started < 150, "extraction unexpectedly long; stop for Commander, do not repeat automatically")
    del texts, detector
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    with CACHE.open("xb") as handle:
        np.savez_compressed(handle, surprisals=np.asarray(flat), offsets=np.asarray(offsets),
                            ids=np.asarray([r["sample_id"] for r in rows]), input_tokens=np.asarray([e["input_tokens"] for e in evidence]))
    return evidence


def load_cache(rows, expected_sha):
    require(file_hash(CACHE) == expected_sha, "phase cache drift")
    original = original_records()
    with np.load(CACHE, allow_pickle=False) as archive:
        require(archive["ids"].tolist() == [r["sample_id"] for r in rows], "cached identity mismatch")
        offsets, tokens = archive["offsets"], archive["surprisals"]
        require(len(offsets) == len(rows) + 1 and offsets[0] == 0 and offsets[-1] == len(tokens)
                and (np.diff(offsets) > 0).all(), "cache offsets malformed")
        return [{"surprisals": tokens[offsets[i]:offsets[i + 1]].tolist(), "input_tokens": int(archive["input_tokens"][i]),
                 "tokens_analyzed": int(offsets[i + 1] - offsets[i]), "v1_features": [float(prior[n]) for n in FEATURE_NAMES]}
                for i, prior in enumerate(original)]


def csv_bytes(rows):
    return baseline.csv_bytes(rows)


def analysis_products(rows, evidence, scores, reports):
    aggregate, folds, short, errors = summarize(rows, evidence, scores, reports)
    selected = select(rows, evidence, scores, aggregate, folds)
    records = [{"block": b, "sample_id": r["sample_id"], "partition": "BASE_TRAIN", "fold": int(r["outer_fold"]),
        "label": int(r["label"]), "lineage_group": r["lineage_group"], "input_tokens": evidence[i]["input_tokens"],
        "raw_score": float(scores[b][i]), "calibrated_probability": "", "raw_0_5_vote": int(scores[b][i] >= .5),
        "schema_sha256": aggregate[b]["schema_sha256"]} for b in BLOCKS for i, r in enumerate(rows)]
    return {"block_metrics_v1.json": json_bytes(aggregate), "block_fold_metrics_v1.json": json_bytes(folds),
            "block_predictions_v1.csv": csv_bytes(records), "short_prompt_analysis_v1.json": json_bytes(short),
            "error_bank_transition_v1.json": json_bytes(errors), "selected_representation_v1.json": json_bytes(selected)}


def reproduce_B0(rows, scores):
    records = original_records()
    previous = np.asarray([float(r["raw_score"]) for r in records])
    require(np.allclose(scores["B0"], previous, rtol=0, atol=1e-12), "B0 predictions did not reproduce frozen v1")
    actual = baseline.metrics([int(r["label"]) for r in rows], scores["B0"])
    prior = read(baseline.OUTPUT / "ds_v1_recipe_oof_metrics.json")
    require(all(actual[k] == prior[k] for k in actual), "B0 metrics did not reproduce")


def run():
    payload = checked()
    require(git("branch", "--show-current") == "tech/stat-004" and not git("status", "--porcelain", "--untracked-files=all"), "clean-tree run gate failed; no waiver")
    require(not (OUT / "run_started_v1.json").exists(), "ablation already started; no automatic repeat")
    run_commit = git("rev-parse", "HEAD")
    for path in (*CODE, "artifacts/statistical_v2/feature_ablation/feature_block_definitions_v1.json", "artifacts/statistical_v2/feature_ablation/preflight_v1.json"):
        require(git("hash-object", f"--path={path}", path) == git("rev-parse", f"HEAD:{path}"), "uncommitted run definitions/code")
    config = baseline.checked_config()
    install_gate(config)
    start = time.perf_counter()
    write(OUT / "run_started_v1.json", {"code_commit": run_commit, "accepted_start_commit": START, "started_at": datetime.now(UTC).isoformat(),
                                      "preflight_sha256": file_hash(OUT / "preflight_v1.json"), "definitions_sha256": payload["definitions_sha256"]})
    rows, sources = baseline.selected_metadata()
    try:
        evidence = extract_evidence(rows, sources, config)
        def progress(fold, block):
            elapsed = time.perf_counter() - start
            print(json.dumps({"completed_fold": fold, "block": block, "elapsed_seconds": elapsed}), flush=True)
            require(elapsed < payload["long_run_stop_seconds"], "long-run limit exceeded; stop for Commander")
        scores, reports, references = evaluate(rows, evidence, progress)
        reproduce_B0(rows, scores)
        products = analysis_products(rows, evidence, scores, reports)
        products["fold_references_v1.json"] = json_bytes(references)
        products["paired_comparison_v1.json"] = json_bytes(paired_bootstrap(rows, scores))
        baseline.verify_hashes(ROOT, payload["preserved_sha256"])
        preservation = baseline.baseline_check()
        for name, content in products.items():
            write(OUT / name, content)
        write(OUT / "run_metadata_v1.json", {"status": "COMPLETE_FEATURE_ABLATION_DEVELOPMENT_ONLY", "accepted_start_commit": START,
            "code_commit": run_commit, "code_sha256": payload["code_sha256"], "definitions_sha256": payload["definitions_sha256"],
            "manifest_sha256": MANIFEST, "fold_sha256": FOLDS, "environment": baseline.environment(), "runtime_seconds": time.perf_counter() - start,
            "completed_at": datetime.now(UTC).isoformat(), "rows_per_block": 1135, "blocks": list(BLOCKS), "LR_fits": 35, "reference_fits": 5,
            "identity_leakage": 0, "canonical_lineage_leakage": 0, "B0_reproduced": True, "baseline_preservation": preservation,
            "token_cache_path": CACHE.relative_to(ROOT).as_posix(), "token_cache_sha256": file_hash(CACHE),
            "source_artifact_sha256": config["source_artifact_sha256"], "observed_dataset_opens": sorted(baseline.DATASET_OPEN_LOG),
            "source_selection_caveat": "Approved original containers include other partitions; only BASE_TRAIN scalar locators/texts supplied to LM/references/LR/diagnostics.",
            "complementarity": "DEFERRED", "cycle": "1_OF_MAXIMUM_2", "B7": "PREDECLARED_SKIPPED",
            "CALIBRATION_used": False, "VALIDATION_used": False, "protected_used": False, "E1_E10": False,
            "other_detector_outputs_used": False, "final_ds_v2_created": False, "deployment_threshold_selected": False,
            "artifact_sha256": {name: file_hash(OUT / name) for name in products}})
        print(json.dumps({"status": "COMPLETE", "runtime_seconds": time.perf_counter() - start,
                          "selected": read(OUT / "selected_representation_v1.json")["selected_block"]}), flush=True)
    except Exception as exc:
        write(OUT / "failure_v1.json", {"status": "STOP_FOR_REVIEW", "exception_type": type(exc).__name__, "message": str(exc), "elapsed_seconds": time.perf_counter() - start})
        raise


def check():
    payload = checked()
    require(not (OUT / "failure_v1.json").exists(), "run failure recorded")
    metadata = read(OUT / "run_metadata_v1.json")
    baseline.verify_hashes(OUT, metadata["artifact_sha256"])
    require(metadata["definitions_sha256"] == payload["definitions_sha256"] and metadata["code_sha256"] == payload["code_sha256"], "run code/definitions drift")
    require(metadata["accepted_start_commit"] == START and metadata["identity_leakage"] == metadata["canonical_lineage_leakage"] == 0,
            "run provenance/leakage drift")
    require(metadata["status"] == "COMPLETE_FEATURE_ABLATION_DEVELOPMENT_ONLY" and metadata["rows_per_block"] == 1135
            and metadata["blocks"] == list(BLOCKS) and metadata["LR_fits"] == 35 and metadata["reference_fits"] == 5, "incomplete run")
    require(all(metadata[key] is False for key in ("CALIBRATION_used", "VALIDATION_used", "protected_used", "E1_E10",
                "other_detector_outputs_used", "final_ds_v2_created", "deployment_threshold_selected")), "run isolation drift")
    started = read(OUT / "run_started_v1.json")
    require(started["code_commit"] == metadata["code_commit"] and started["definitions_sha256"] == payload["definitions_sha256"]
            and started["preflight_sha256"] == file_hash(OUT / "preflight_v1.json"), "run-start provenance drift")
    require(subprocess.run(["git", "merge-base", "--is-ancestor", metadata["code_commit"], "HEAD"], cwd=ROOT,
                           capture_output=True).returncode == 0, "run commit not ancestor")
    for path in CODE:
        require(git("hash-object", f"--path={path}", path) == git("rev-parse", f"{metadata['code_commit']}:{path}"), "run code changed")
    rows, _ = baseline.selected_metadata()
    evidence = load_cache(rows, metadata["token_cache_sha256"])
    labels = np.asarray([int(r["label"]) for r in rows])
    with (OUT / "block_predictions_v1.csv").open(encoding="utf-8", newline="") as handle:
        records = list(csv.DictReader(handle))
    require(len(records) == len(rows) * len(BLOCKS) and {r["block"] for r in records} == set(BLOCKS), "block coverage drift")
    scores = {}
    fold_payload = read(OUT / "block_fold_metrics_v1.json")
    reports = {b: fold_payload[b]["folds"] for b in BLOCKS}
    for block in BLOCKS:
        selected = [r for r in records if r["block"] == block]
        require([r["sample_id"] for r in selected] == [r["sample_id"] for r in rows], "OOF identity/order drift")
        require(all(r["partition"] == "BASE_TRAIN" and r["calibrated_probability"] == "" and
                    int(r["fold"]) == int(source["outer_fold"]) and int(r["label"]) == int(source["label"])
                    and r["lineage_group"] == source["lineage_group"] for r, source in zip(selected, rows, strict=True)), "reserved/drifted OOF rows")
        scores[block] = np.asarray([float(r["raw_score"]) for r in selected])
        for report in reports[block]:
            mask = np.asarray([int(r["outer_fold"]) == report["fold"] for r in rows])
            require(report["metrics"] == baseline.metrics(labels[mask], scores[block][mask]), "fold metrics drift")
    reproduce_B0(rows, scores)
    for name, content in analysis_products(rows, evidence, scores, reports).items():
        require((OUT / name).read_bytes() == content, f"recomputed artifact drift: {name}")
    # Verify reference memberships and learned values again without fitting any classifier.
    from detection_service.analysis.statistical_feature_ablation import References
    references = read(OUT / "fold_references_v1.json")
    require([r["fold"] for r in references] == list(range(5)), "reference fold coverage drift")
    for reference in references:
        fold = reference["fold"]
        train = [i for i, r in enumerate(rows) if int(r["outer_fold"]) != fold]
        held = [r["sample_id"] for r in rows if int(r["outer_fold"]) == fold]
        recomputed = References.fit([rows[i] for i in train], [evidence[i] for i in train], held).payload
        require(all(reference[k] == v for k, v in recomputed.items()), "fold-local reference reconstruction failed")
        require(reference["training_membership_sha256"] == baseline.digest_ids([rows[i] for i in train])
                and reference["held_out_membership_sha256"] == baseline.digest_ids([r for r in rows if int(r["outer_fold"]) == fold]),
                "reference membership digest drift")
        digest = features_digest(recomputed)
        for block in BLOCKS:
            report = reports[block][fold]
            require(report["fold"] == fold and report["reference_sha256"] == digest
                    and report["train_membership_sha256"] == reference["training_membership_sha256"]
                    and report["held_out_membership_sha256"] == reference["held_out_membership_sha256"]
                    and report["identity_leakage"] == report["lineage_leakage"] == 0, "fold reference binding/leakage drift")
    print(json.dumps({"status": "PASS", "rows_per_block": len(rows), "blocks": len(BLOCKS), "original_baseline_preservation": baseline.baseline_check(),
                      "preserved_semantic_stat_files": len(payload["preserved_sha256"]), "output_hash_checks": len(metadata["artifact_sha256"]), "leakage": 0}))


def features_digest(payload):
    import hashlib
    return hashlib.sha256(json_bytes(payload)).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("prepare", "run", "check"), required=True)
    args = parser.parse_args()
    require(Path.cwd().resolve() == ROOT, "execute from repository root")
    os.environ["HF_HUB_OFFLINE"] = os.environ["TRANSFORMERS_OFFLINE"] = "1"
    {"prepare": prepare, "run": run, "check": check}[args.mode]()


if __name__ == "__main__":
    main()
