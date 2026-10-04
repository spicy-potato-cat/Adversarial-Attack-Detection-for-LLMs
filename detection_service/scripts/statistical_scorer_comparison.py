"""Freeze, run and reconstruct one STAT-005 BASE_TRAIN scorer comparison."""

import argparse
import csv
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import subprocess
import time

import numpy as np
from sklearn.preprocessing import StandardScaler

from detection_service.analysis import statistical_scorer_comparison as core
from detection_service.analysis import statistical_scorer_results as results
from detection_service.analysis.statistical_oof import require
from detection_service.quality.development_fixture import ROOT, file_hash, json_bytes, verify
from detection_service.scripts import statistical_feature_ablation as source
from detection_service.scripts import statistical_feature_ablation_resume as stat004

START = "b09beb5340a4d6c21e165f4cb1b596cfc3657216"
OUT = ROOT / "artifacts/statistical_v2/scorer_comparison"
CODE = ("detection_service/analysis/statistical_scorer_comparison.py", "detection_service/analysis/statistical_scorer_results.py",
        "detection_service/scripts/statistical_scorer_comparison.py", "detection_service/tests/test_statistical_scorer_comparison.py")
read, write, git, baseline = source.read, source.write, source.git, source.baseline


def preserved():
    paths = source.preservation_paths()
    for root in (stat004.HISTORY,):
        paths.update({p.relative_to(ROOT).as_posix(): file_hash(p) for p in root.rglob("*") if p.is_file()})
    paths.update({p.relative_to(ROOT).as_posix(): file_hash(p) for p in (ROOT / "reviews").glob("TECH_STAT_004*.md")})
    metadata = read(stat004.OUT / "run_metadata_v1.json")
    paths.update(metadata["code_sha256"])
    paths.update(read(stat004.OUT / "acceptance_evidence_v1.json")["verification_code_sha256"])
    return paths


def verify_source():
    require(git("branch", "--show-current") == "tech/stat-005", "wrong branch")
    require(subprocess.run(["git", "merge-base", "--is-ancestor", START, "HEAD"], cwd=ROOT,
                           capture_output=True).returncode == 0, "accepted STAT004 not ancestor")
    selected = read(stat004.OUT / "selected_representation_v1.json")
    require(selected["selected_block"] == "B2" and selected["feature_count"] == 26
            and selected["schema_sha256"] == core.B2_SHA, "wrong B2 source")
    prior = read(stat004.OUT / "preflight_v1.json")
    baseline.verify_hashes(ROOT, prior["code_sha256"])
    baseline.verify_hashes(ROOT, prior["preserved_sha256"])
    baseline.verify_hashes(ROOT, prior["historical_sha256"])
    baseline.verify_hashes(stat004.OUT, read(stat004.OUT / "run_metadata_v1.json")["artifact_sha256"])
    acceptance = read(stat004.OUT / "acceptance_evidence_v1.json")
    baseline.verify_hashes(stat004.OUT, acceptance["verified_sha256"])
    baseline.verify_hashes(ROOT, acceptance["verification_code_sha256"])
    require(file_hash(source.CACHE) == stat004.CACHE_SHA, "token cache drift; never re-extract")
    require(core.definitions()["feature_names"] == selected["feature_names"], "B2 order drift")
    require(read(stat004.HISTORY / "feature_block_definitions_v1.json") == core.features.definitions(), "B2 definition drift")
    fixture = verify()
    config = baseline.checked_config()
    require(fixture["fold_sha256"] == source.FOLDS and config["manifest_sha256"] == source.MANIFEST, "fixture drift")
    return config


def prepare():
    require(git("rev-parse", "HEAD") == START and not OUT.exists(), "startup/output gate failed")
    pending = subprocess.check_output(["git", "status", "--porcelain", "--untracked-files=all"], cwd=ROOT, text=True)
    require(all(line[3:].replace("\\", "/") in (*CODE, ".gitattributes") for line in pending.splitlines()), "unrelated changes")
    verify_source()
    baseline.check()
    OUT.mkdir()
    write(OUT / "scorer_definitions_v1.json", core.definitions())
    write(OUT / "preflight_v1.json", {"phase": "TECH-STAT-005", "start_commit": START,
        "branch": "tech/stat-005", "cycle": "1_OF_MAXIMUM_2", "clean_startup": "OBSERVED_BEFORE_PHASE_EDITS",
        "rows": 1135, "positive": 183, "negative": 952, "manifest_sha256": source.MANIFEST, "fold_sha256": source.FOLDS,
        "B2_schema_sha256": core.B2_SHA, "scorer_definitions_sha256": file_hash(OUT / "scorer_definitions_v1.json"),
        "code_sha256": {p: file_hash(ROOT / p) for p in CODE}, "preserved_sha256": preserved(),
        "token_cache_sha256": stat004.CACHE_SHA, "environment": baseline.environment(),
        "baseline_preservation": baseline.baseline_check(), "runtime_estimate_seconds": [40, 120], "stop_seconds": 300,
        "S0_score_absolute_tolerance": 1e-6, "S0_auc_absolute_tolerance": 1e-6,
        "S0_frontier_counts": "EXACT", "payload_policy": "Numeric cache and BASE_TRAIN metadata only; raw payload and LM loading forbidden.",
        "reference_policy": "Recompute five training-fold-only B2 references. Only SVM fits training-only StandardScaler."})
    print(json.dumps({"status": "PREDECLARED_NOT_RUN", "estimated_seconds": [40, 120], "fits": 15}))


def checked():
    verify_source()
    p = read(OUT / "preflight_v1.json")
    require(p["start_commit"] == START and p["manifest_sha256"] == source.MANIFEST and p["fold_sha256"] == source.FOLDS,
            "preflight provenance drift")
    require(p["environment"] == baseline.environment() and file_hash(OUT / "scorer_definitions_v1.json") == p["scorer_definitions_sha256"]
            and read(OUT / "scorer_definitions_v1.json") == core.definitions(), "scorer/environment freeze drift")
    baseline.verify_hashes(ROOT, p["code_sha256"])
    baseline.verify_hashes(ROOT, p["preserved_sha256"])
    return p


def reproduce_S0(rows, scores):
    with (stat004.OUT / "block_predictions_v1.csv").open(encoding="utf-8", newline="") as handle:
        prior = [r for r in csv.DictReader(handle) if r["block"] == "B2"]
    require([r["sample_id"] for r in prior] == [r["sample_id"] for r in rows], "S0 reference alignment drift")
    previous = np.asarray([float(r["raw_score"]) for r in prior])
    require(np.allclose(previous, scores["S0"], rtol=0, atol=1e-6), "material S0 divergence; STOP")
    current = results.metrics([int(r["label"]) for r in rows], scores["S0"])
    base = read(stat004.OUT / "block_metrics_v1.json")["B2"]
    require(all(abs(current[k] - base[k]) <= 1e-6 for k in ("roc_auc", "pr_auc")), "S0 AUC drift")
    for actual, reference in zip(current["recall_at_fixed_fpr"], base["recall_at_fixed_fpr"], strict=True):
        require(all(actual[k] == reference[k] for k in ("budget", "tp", "fp", "recall", "attained_fpr")), "S0 frontier drift")
    return {"status": "PASS", "max_score_absolute_difference": float(np.max(np.abs(previous - scores["S0"])))}


def products(rows, evidence, scores, reports, comparisons):
    aggregate, folds, subgroups, errors = results.analyze(rows, evidence, scores, reports)
    selected = results.select(aggregate, folds, subgroups, comparisons)
    records = [{"scorer": s, "sample_id": r["sample_id"], "partition": "BASE_TRAIN", "fold": int(r["outer_fold"]),
        "label": int(r["label"]), "lineage_group": r["lineage_group"], "input_tokens": evidence[i]["input_tokens"],
        "raw_score": float(scores[s][i]), "score_kind": "decision_function" if s == "S1" else "uncalibrated_class1_probability",
        "calibrated_probability": "", "B2_schema_sha256": core.B2_SHA} for s in core.SCORERS for i, r in enumerate(rows)]
    return {"scorer_metrics_v1.json": json_bytes(aggregate), "scorer_fold_metrics_v1.json": json_bytes(folds),
        "scorer_predictions_v1.csv": source.csv_bytes(records), "subgroup_analysis_v1.json": json_bytes(subgroups),
        "error_transition_v1.json": json_bytes(errors), "paired_comparison_v1.json": json_bytes(comparisons),
        "selected_scorer_v1.json": json_bytes(selected)}


def run():
    p = checked()
    require(not git("status", "--porcelain", "--untracked-files=all"), "clean-tree execution required")
    require(not (OUT / "run_started_v1.json").exists(), "comparison already started; no automatic retry")
    commit = git("rev-parse", "HEAD")
    for path in (*CODE, "artifacts/statistical_v2/scorer_comparison/scorer_definitions_v1.json",
                 "artifacts/statistical_v2/scorer_comparison/preflight_v1.json"):
        require(git("hash-object", f"--path={path}", path) == git("rev-parse", f"HEAD:{path}"), "uncommitted run code")
    source.install_gate({"source_artifact_sha256": {}})
    write(OUT / "run_started_v1.json", {"code_commit": commit, "start_commit": START,
        "preflight_sha256": file_hash(OUT / "preflight_v1.json"), "started_at": datetime.now(UTC).isoformat()})
    started, fits = time.perf_counter(), []
    try:
        rows, _ = baseline.selected_metadata()
        evidence = source.load_cache(rows, stat004.CACHE_SHA)
        def progress(scorer, report):
            fits.append({"scorer": scorer, **report})
            print(json.dumps({"scorer": scorer, "fold": report["fold"], "fit_seconds": report["fit_seconds"],
                              "n_iter": report["n_iter"], "elapsed_seconds": time.perf_counter() - started}), flush=True)
            require(time.perf_counter() - started < p["stop_seconds"], "unexpected long-run STOP; no retry")
        scores, reports, references = core.evaluate(rows, evidence, progress)
        reproduction = reproduce_S0(rows, scores)
        comparisons = results.paired(rows, scores)
        output = products(rows, evidence, scores, reports, comparisons)
        output["fold_references_v1.json"] = json_bytes(references)
        baseline.verify_hashes(ROOT, p["preserved_sha256"])
        preservation = baseline.baseline_check()
        for name, content in output.items():
            write(OUT / name, content)
        write(OUT / "run_metadata_v1.json", {"status": "COMPLETE_DEVELOPMENT_SCORER_COMPARISON", "start_commit": START,
            "code_commit": commit, "code_sha256": p["code_sha256"], "definitions_sha256": p["scorer_definitions_sha256"],
            "manifest_sha256": source.MANIFEST, "fold_sha256": source.FOLDS, "B2_schema_sha256": core.B2_SHA,
            "token_cache_sha256": stat004.CACHE_SHA, "environment": baseline.environment(),
            "completed_at": datetime.now(UTC).isoformat(), "runtime_seconds": time.perf_counter() - started,
            "rows_per_scorer": 1135, "scorer_fits": 15, "reference_fits": 5, "scaler_fits": 5,
            "identity_leakage": 0, "lineage_leakage": 0, "S0_reproduction": reproduction,
            "baseline_preservation": preservation, "observed_dataset_opens": sorted(baseline.DATASET_OPEN_LOG),
            "cycle": "1_OF_MAXIMUM_2", "calibration_used": False, "validation_used": False, "protected_used": False,
            "other_detector_outputs_used": False, "E1_E10": False, "final_ds_v2_trained": False,
            "artifact_sha256": {name: file_hash(OUT / name) for name in output}})
        print(json.dumps({"status": "COMPLETE", "selected": read(OUT / "selected_scorer_v1.json")["selected_scorer"]}), flush=True)
    except Exception as exc:
        write(OUT / "failure_v1.json", {"status": "STOP_FOR_REVIEW", "exception_type": type(exc).__name__,
            "message": str(exc), "code_commit": commit, "elapsed_seconds": time.perf_counter() - started,
            "completed_fits": fits})
        raise


def check():
    p = checked()
    require(not (OUT / "failure_v1.json").exists(), "failure evidence present")
    m = read(OUT / "run_metadata_v1.json")
    baseline.verify_hashes(OUT, m["artifact_sha256"])
    require(m["status"] == "COMPLETE_DEVELOPMENT_SCORER_COMPARISON" and m["scorer_fits"] == 15
            and m["reference_fits"] == m["scaler_fits"] == 5 and m["rows_per_scorer"] == 1135, "incomplete run")
    require(m["code_sha256"] == p["code_sha256"] and m["definitions_sha256"] == p["scorer_definitions_sha256"], "run freeze drift")
    start = read(OUT / "run_started_v1.json")
    require(start["code_commit"] == m["code_commit"] and start["preflight_sha256"] == file_hash(OUT / "preflight_v1.json"), "run provenance drift")
    require(subprocess.run(["git", "merge-base", "--is-ancestor", m["code_commit"], "HEAD"], cwd=ROOT,
                           capture_output=True).returncode == 0, "run commit not ancestor")
    for path in CODE:
        require(git("hash-object", f"--path={path}", path) == git("rev-parse", f"{m['code_commit']}:{path}"), "model-run code drift")
    require(m["identity_leakage"] == m["lineage_leakage"] == 0 and all(m[k] is False for k in
        ("calibration_used", "validation_used", "protected_used", "other_detector_outputs_used", "E1_E10", "final_ds_v2_trained")), "isolation drift")
    rows, _ = baseline.selected_metadata()
    evidence = source.load_cache(rows, stat004.CACHE_SHA)
    with (OUT / "scorer_predictions_v1.csv").open(encoding="utf-8", newline="") as handle:
        records = list(csv.DictReader(handle))
    require(len(records) == len(rows) * 3, "prediction coverage drift")
    scores = {}
    reports = {s: read(OUT / "scorer_fold_metrics_v1.json")[s]["folds"] for s in core.SCORERS}
    for scorer in core.SCORERS:
        selected = [r for r in records if r["scorer"] == scorer]
        require([r["sample_id"] for r in selected] == [r["sample_id"] for r in rows], "OOF alignment drift")
        scores[scorer] = np.asarray([float(r["raw_score"]) for r in selected])
    require(m["S0_reproduction"] == reproduce_S0(rows, scores), "S0 reconstruction drift")
    comparisons = results.paired(rows, scores)
    for name, content in products(rows, evidence, scores, reports, comparisons).items():
        require((OUT / name).read_bytes() == content, f"reconstructed product drift: {name}")
    references = read(OUT / "fold_references_v1.json")
    require([r["fold"] for r in references] == list(range(5)), "reference coverage drift")
    for fold in range(5):
        matrix, train, held, ref = core.fold_features(rows, evidence, fold)
        require(ref == references[fold], "reference fitting reconstruction drift")
        scale = StandardScaler().fit(matrix[train])
        expected_scale = {"training_rows": len(train), "mean": scale.mean_.tolist(), "var": scale.var_.tolist(), "scale": scale.scale_.tolist()}
        labels = np.asarray([int(rows[i]["label"]) for i in train])
        weights = {str(c): len(train) / (2 * int(sum(labels == c))) for c in (0, 1)}
        for scorer in core.SCORERS:
            report = reports[scorer][fold]
            require(report["fold"] == fold and report["reference_sha256"] == core.digest(ref)
                    and report["train_membership_sha256"] == ref["train_membership_sha256"]
                    and report["held_out_membership_sha256"] == ref["held_out_membership_sha256"]
                    and report["identity_leakage"] == report["lineage_leakage"] == 0
                    and report["training_class_weights"] == weights and report["completed"] is True
                    and not report["convergence_warnings"], "fold binding/weight/leakage drift")
            require(report["scaler"] == (expected_scale if scorer == "S1" else None), "scaler held-out leakage/drift")
            require(report["train_rows"] == len(train) and report["held_out_rows"] == len(held)
                    and all(np.isfinite(report[k]) and report[k] >= 0 for k in ("fit_seconds", "inference_seconds", "inference_ms_per_row")),
                    "runtime/population drift")
            if scorer == "S0":
                require(max(report["n_iter"]) < 20000, "LR nonconvergence")
            elif scorer == "S2":
                require(report["n_iter"] == [100], "HGB iteration drift")
            else:
                variance = scale.transform(matrix[train]).var()
                gamma = 1 / (26 * variance) if variance else 1.
                require(report["actual_class_weights"] == [weights["0"], weights["1"]]
                        and report["effective_gamma"] == gamma, "SVM training-derived weight/gamma drift")
    baseline.check()
    print(json.dumps({"status": "PASS", "output_hash_checks": len(m["artifact_sha256"]), "scorer_fits": 15,
        "rows_per_scorer": 1135, "leakage": 0, "preserved_files": len(p["preserved_sha256"]),
        "baseline_preservation": baseline.baseline_check(), "classifier_refits": 0}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("prepare", "run", "check"), required=True)
    args = parser.parse_args()
    require(Path.cwd().resolve() == ROOT, "execute from repository root")
    os.environ["HF_HUB_OFFLINE"] = os.environ["TRANSFORMERS_OFFLINE"] = "1"
    {"prepare": prepare, "run": run, "check": check}[args.mode]()


if __name__ == "__main__":
    main()
