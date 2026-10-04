"""One authorized STAT-004 cap-only rerun; preserve the original blocked attempt."""

import argparse
import csv
from datetime import UTC, datetime
import hashlib
import json
import os
import subprocess
import time

import numpy as np

from detection_service.analysis.statistical_feature_ablation import BLOCKS, MAX_ITER, RECIPE, definitions, evaluate
from detection_service.analysis.statistical_ablation_results import paired_bootstrap
from detection_service.analysis.statistical_oof import require
from detection_service.quality.development_fixture import ROOT, file_hash, json_bytes, verify
from detection_service.scripts import statistical_feature_ablation as original

START = "5670f7780f084ce40545fa8c6b8a61100598d6a5"
FREEZE = "2eed02d6257f0f55bd6e52e499dcc2017e8a728d"
HISTORY = original.OUT
OUT = HISTORY / "resume_20000"
CACHE_SHA = "02241c0b2de1941783187f398c82ce3e8a7ec0a67655ace10f13ced7c29a70b3"
CODE = (*original.CODE, "detection_service/scripts/statistical_feature_ablation_resume.py")
read, write, git, baseline = original.read, original.write, original.git, original.baseline


def history_checks():
    prior = read(HISTORY / "preflight_v1.json")
    require(git("branch", "--show-current") == "tech/stat-004", "wrong branch")
    for ancestor in (START, FREEZE):
        require(subprocess.run(["git", "merge-base", "--is-ancestor", ancestor, "HEAD"], cwd=ROOT,
                               capture_output=True).returncode == 0, "missing historical ancestor")
    for path, digest in prior["code_sha256"].items():
        blob = subprocess.check_output(["git", "show", f"{FREEZE}:{path}"], cwd=ROOT)
        require(original.features_digest(read(HISTORY / "feature_block_definitions_v1.json")) == prior["definitions_sha256"],
                "historical definitions hash drift")
        require(hashlib.sha256(blob).hexdigest() == digest, "historical code provenance drift")
    require(file_hash(HISTORY / "feature_block_definitions_v1.json") == prior["definitions_sha256"]
            and definitions() == read(HISTORY / "feature_block_definitions_v1.json"), "feature definitions drift")
    baseline.verify_hashes(ROOT, prior["preserved_sha256"])
    require(file_hash(original.CACHE) == CACHE_SHA, "cache changed; no automatic extraction")
    require(baseline.environment() == prior["environment"], "environment drift")
    config = baseline.checked_config()
    require(config["manifest_sha256"] == original.MANIFEST and config["fold_sha256"] == original.FOLDS, "fixture drift")
    verify()
    return prior


def prepare():
    require(git("rev-parse", "HEAD") == START, "wrong resume startup commit")
    require(not OUT.exists(), "resume evidence exists; never overwrite")
    pending = subprocess.check_output(["git", "status", "--porcelain", "--untracked-files=all"], cwd=ROOT, text=True)
    require(all(line[3:].replace("\\", "/") in (*CODE, ".gitattributes") for line in pending.splitlines()),
            "unrelated pending changes")
    prior = history_checks()
    baseline.check()
    paths = [p for p in HISTORY.iterdir() if p.is_file()]
    paths += [p for p in (HISTORY / "resume_5000").rglob("*") if p.is_file()]
    paths += [p for p in (ROOT / "reviews").glob("TECH_STAT_004*.md") if p.is_file()]
    OUT.mkdir()
    write(OUT / "preflight_v1.json", {**prior, "resume_start_commit": START, "original_run_code_commit": FREEZE,
        "historical_sha256": {p.relative_to(ROOT).as_posix(): file_hash(p) for p in sorted(paths)},
        "code_sha256": {p: file_hash(ROOT / p) for p in CODE}, "token_cache_sha256": CACHE_SHA,
        "numerical_correction": {"original_max_iter": 1000, "second_max_iter": 5000, "max_iter": MAX_ITER, "tol": 1e-4,
            "actual_recipe": {**RECIPE, "max_iter": MAX_ITER}, "all_blocks_all_folds": True,
            "feature_schema_recipe": "Historical 1000 retained byte-for-byte; numerical override recorded here.",
            "scientific_parameters_changed": False, "new_model_selection_cycle": False},
        "B0_acceptance": {"score_absolute_tolerance": 1e-6, "auc_absolute_tolerance": 1e-6,
                          "raw_confusion_and_fixed_fpr_counts": "EXACT"},
        "cache_policy": "Integrity-checked deterministic token cache only; no partial fitted model reuse.",
        "runtime_estimate_seconds": [60, 240], "baseline_preservation": baseline.baseline_check()})
    print(json.dumps({"status": "RESUME_PREFLIGHT_FROZEN", "max_iter": MAX_ITER, "cycle": "1/2"}))


def checked():
    prior = history_checks()
    payload = read(OUT / "preflight_v1.json")
    baseline.verify_hashes(ROOT, payload["historical_sha256"])
    baseline.verify_hashes(ROOT, payload["code_sha256"])
    require(payload["definitions_sha256"] == prior["definitions_sha256"] and payload["token_cache_sha256"] == CACHE_SHA,
            "resume freeze drift")
    require(payload["numerical_correction"]["actual_recipe"] == {**RECIPE, "max_iter": 20000}
            and MAX_ITER == 20000, "authorized numerical recipe drift")
    return payload


def reproduce_B0(rows, scores):
    previous = np.asarray([float(r["raw_score"]) for r in original.original_records()])
    require(np.allclose(scores["B0"], previous, rtol=0, atol=1e-6), "material B0 score divergence; STOP")
    actual = baseline.metrics([int(r["label"]) for r in rows], scores["B0"])
    prior = read(baseline.OUTPUT / "ds_v1_recipe_oof_metrics.json")
    require(actual["confusion_matrix"] == prior["confusion_matrix"], "material B0 confusion divergence; STOP")
    require(all(abs(actual[k] - prior[k]) <= 1e-6 for k in ("roc_auc", "pr_auc")), "material B0 AUC divergence; STOP")
    require(actual["recall_at_fixed_fpr"] == prior["recall_at_fixed_fpr"], "material B0 frontier divergence; STOP")
    return {"status": "PASS", "max_score_absolute_difference": float(np.max(np.abs(scores["B0"] - previous))),
            "confusion_matrix": actual["confusion_matrix"], "roc_auc": actual["roc_auc"], "pr_auc": actual["pr_auc"]}


def convergence_payload(records):
    return {"original_max_iter": 1000, "second_max_iter": 5000, "max_iter": 20000, "fits": records, "attempted_fits": len(records),
            "all_final_fits_converged": len(records) == 35 and all(r["converged"] for r in records),
            "maximum_observed_n_iter": max((max(r["n_iter"]) for r in records), default=0)}


def run():
    payload = checked()
    require(not git("status", "--porcelain", "--untracked-files=all"), "clean-tree gate; no waiver")
    require(not (OUT / "run_started_v1.json").exists(), "one resume already started; no repeat")
    commit = git("rev-parse", "HEAD")
    for path in (*CODE, (OUT / "preflight_v1.json").relative_to(ROOT).as_posix()):
        require(git("hash-object", f"--path={path}", path) == git("rev-parse", f"HEAD:{path}"), "uncommitted run code")
    config = baseline.checked_config()
    original.install_gate(config)
    started = time.perf_counter()
    records = []
    write(OUT / "run_started_v1.json", {"code_commit": commit, "accepted_start_commit": original.START,
        "resume_start_commit": START, "started_at": datetime.now(UTC).isoformat(),
        "preflight_sha256": file_hash(OUT / "preflight_v1.json"), "definitions_sha256": payload["definitions_sha256"]})
    try:
        rows, _ = baseline.selected_metadata()
        evidence = original.load_cache(rows, CACHE_SHA)
        def record_fit(record):
            records.append(record)
            print(json.dumps(record), flush=True)
        def progress(fold, block):
            require(time.perf_counter() - started < payload["long_run_stop_seconds"], "long-run STOP for Commander")
        scores, reports, references = evaluate(rows, evidence, progress, record_fit)
        reproduction = reproduce_B0(rows, scores)
        products = original.analysis_products(rows, evidence, scores, reports)
        products["fold_references_v1.json"] = json_bytes(references)
        products["paired_comparison_v1.json"] = json_bytes(paired_bootstrap(rows, scores))
        products["lr_convergence_v1.json"] = json_bytes(convergence_payload(records))
        baseline.verify_hashes(ROOT, payload["preserved_sha256"])
        baseline.verify_hashes(ROOT, payload["historical_sha256"])
        preservation = baseline.baseline_check()
        for name, content in products.items():
            write(OUT / name, content)
        write(OUT / "run_metadata_v1.json", {"status": "COMPLETE_FEATURE_ABLATION_DEVELOPMENT_ONLY",
            "accepted_start_commit": original.START, "resume_start_commit": START, "original_run_code_commit": FREEZE,
            "code_commit": commit, "code_sha256": payload["code_sha256"], "definitions_sha256": payload["definitions_sha256"],
            "manifest_sha256": original.MANIFEST, "fold_sha256": original.FOLDS, "environment": baseline.environment(),
            "numerical_correction": payload["numerical_correction"], "runtime_seconds": time.perf_counter() - started,
            "completed_at": datetime.now(UTC).isoformat(), "rows_per_block": 1135, "blocks": list(BLOCKS), "LR_fits": 35,
            "reference_fits": 5, "identity_leakage": 0, "canonical_lineage_leakage": 0,
            "B0_reproduced": True, "B0_reproduction": reproduction, "baseline_preservation": preservation,
            "token_cache_path": original.CACHE.relative_to(ROOT).as_posix(), "token_cache_sha256": CACHE_SHA,
            "observed_dataset_opens": sorted(baseline.DATASET_OPEN_LOG), "cycle": "1_OF_MAXIMUM_2", "B7": "PREDECLARED_SKIPPED",
            "CALIBRATION_used": False, "VALIDATION_used": False, "protected_used": False, "E1_E10": False,
            "other_detector_outputs_used": False, "final_ds_v2_created": False, "deployment_threshold_selected": False,
            "artifact_sha256": {name: file_hash(OUT / name) for name in products}})
        print(json.dumps({"status": "COMPLETE", "runtime_seconds": time.perf_counter() - started,
                          "selected": read(OUT / "selected_representation_v1.json")["selected_block"]}), flush=True)
    except Exception as exc:
        if not (OUT / "lr_convergence_v1.json").exists():
            write(OUT / "lr_convergence_v1.json", convergence_payload(records))
        write(OUT / "failure_v1.json", {"status": "STOP_FOR_REVIEW", "exception_type": type(exc).__name__,
            "message": str(exc), "elapsed_seconds": time.perf_counter() - started,
            "last_fit": records[-1] if records else None, "code_commit": commit})
        raise


def check():
    checked()
    original.OUT, original.CODE, original.checked, original.reproduce_B0 = OUT, CODE, checked, reproduce_B0
    original.check()
    convergence = read(OUT / "lr_convergence_v1.json")
    records = convergence["fits"]
    require([(r["fold"], r["block"]) for r in records] == [(f, b) for f in range(5) for b in BLOCKS], "fit coverage drift")
    require(convergence == convergence_payload(records) and convergence["all_final_fits_converged"], "nonconverged final fits")
    folds = read(OUT / "block_fold_metrics_v1.json")
    for r in records:
        require(r["max_iter"] == 20000 and not r["convergence_warnings"] and max(r["n_iter"]) < 20000
                and r["fit_seconds"] >= 0, "convergence evidence drift")
        require(all(folds[r["block"]]["folds"][r["fold"]][k] == v for k, v in r.items() if k != "block"), "fit binding drift")
    rows, _ = baseline.selected_metadata()
    with (OUT / "block_predictions_v1.csv").open(encoding="utf-8", newline="") as handle:
        predictions = list(csv.DictReader(handle))
    scores = {b: np.asarray([float(r["raw_score"]) for r in predictions if r["block"] == b]) for b in BLOCKS}
    require(json_bytes(paired_bootstrap(rows, scores)) == (OUT / "paired_comparison_v1.json").read_bytes(), "bootstrap reconstruction drift")
    print(json.dumps({"status": "PASS", "converged_fits": 35, "historical_evidence": "UNCHANGED", "paired_reconstruction": "PASS"}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("prepare", "run", "check"), required=True)
    args = parser.parse_args()
    require(os.path.normcase(os.getcwd()) == os.path.normcase(str(ROOT)), "execute from repository root")
    os.environ["HF_HUB_OFFLINE"] = os.environ["TRANSFORMERS_OFFLINE"] = "1"
    {"prepare": prepare, "run": run, "check": check}[args.mode]()


if __name__ == "__main__":
    main()
