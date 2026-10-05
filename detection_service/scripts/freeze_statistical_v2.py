"""STAT-006 one final BASE_TRAIN fit, then STAT-007 CALIBRATION-only sigmoid."""

import argparse
import csv
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import subprocess
import time
from unittest.mock import patch

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score

from detection_service.analysis import statistical_feature_ablation as features
from detection_service.analysis.statistical_oof import digest_ids, require
from detection_service.app.contracts.detection_request import DetectionContent, DetectionRequest
from detection_service.app.detectors.semantic.calibration import EPSILON, METHOD, SigmoidCalibrator
from detection_service.app.detectors.statistical_risk.schema import FEATURE_NAMES
from detection_service.app.detectors.statistical_v2 import B2Model, B2StatisticalDetector, load_calibration
from detection_service.app.detectors.statistical_v2.model import (MODEL_FILE, REFERENCE_FILE, MANIFEST_FILE,
    TRAINING_FILE, INTEGRITY_FILE, FROZEN_FILES, CAL_FILE, CAL_MANIFEST, CAL_METRICS, CAL_INTEGRITY)
from detection_service.scripts import statistical_scorer_comparison as prior
from detection_service.scripts.calibrate_semantic_baseline import calibration_rows, load_calibration_texts, diagnostics

ROOT, baseline, source = prior.ROOT, prior.baseline, prior.source
read, write, git, file_hash = prior.read, prior.write, prior.git, prior.file_hash
START = "4d9d694bec959e082b8675f36a0b89488890837e"
FINAL = ROOT / "artifacts/statistical_v2/final"
CAL = ROOT / "artifacts/statistical_v2/calibration"
RUNTIME = tuple(f"detection_service/app/detectors/statistical_v2/{n}.py" for n in ("__init__", "model", "detector"))
CODE = (*RUNTIME, "detection_service/scripts/freeze_statistical_v2.py", "detection_service/tests/test_statistical_v2.py")


def hashes(root, files):
    return {p: file_hash(root / p) for p in files}


def preservation():
    from detection_service.scripts.verify_quality_preservation import EVIDENCE, paths
    frozen = read(EVIDENCE)
    require(len(frozen["sha256"]) == 96, "historical baseline manifest drift")
    baseline.verify_hashes(ROOT, frozen["sha256"])
    require(set(paths()) == set(frozen["sha256"]) | set(RUNTIME), "unexpected baseline namespace additions/removals")
    result = subprocess.run(["git", "diff", "--exit-code", frozen["start_commit"], "--", *frozen["sha256"]],
                            cwd=ROOT, capture_output=True, text=True)
    require(result.returncode == 0, "original baseline tracked files changed")
    return {"status": "PASS", "original_hash_checks": 96, "original_tracked_diff": "EMPTY",
            "authorized_additions": list(RUNTIME), "evidence_sha256": file_hash(EVIDENCE),
            "scope": "Original snapshot unchanged; only three new ds_v2 application modules allowed. Historical exact-membership checker remains unmodified."}


def extractor_config():
    cfg = read(baseline.OUTPUT / "analysis_config_v1.json")
    p = read(baseline.OUTPUT / "preflight_v1.json")
    require(file_hash(baseline.OUTPUT / "analysis_config_v1.json") == p["analysis_config_sha256"], "extractor config drift")
    baseline.verify()
    preservation()
    baseline.verify_hashes(ROOT, cfg["code_sha256"])
    baseline.verify_hashes(ROOT, cfg["feature_extractor_sha256"])
    require(cfg["manifest_sha256"] == source.MANIFEST and cfg["fold_sha256"] == source.FOLDS, "fixture identity drift")
    return cfg


def verify_prior():
    accepted = read(prior.OUT / "acceptance_evidence_v1.json")
    require(accepted["status"] == "PASS" and accepted["selected_scorer"] == "S0", "STAT005 not accepted")
    baseline.verify_hashes(prior.OUT, accepted["verified_sha256"])
    baseline.verify_hashes(ROOT, accepted["verification_code_sha256"])
    baseline.verify_hashes(ROOT, accepted["report_sha256"])
    p = read(prior.OUT / "preflight_v1.json")
    baseline.verify_hashes(ROOT, p["code_sha256"])
    baseline.verify_hashes(ROOT, p["preserved_sha256"])
    selected = read(prior.OUT / "selected_scorer_v1.json")
    require(selected["B2_schema_sha256"] == prior.core.B2_SHA and selected["candidate_recipe"] == prior.core.definitions()["scorers"]["S0"], "candidate drift")
    return p


def prepare():
    require(git("rev-parse", "HEAD") == START and git("branch", "--show-current") == "tech/stat-006", "startup ancestry/branch mismatch")
    require(not FINAL.exists() and not CAL.exists(), "output exists; no overwrite")
    pending = git("status", "--porcelain", "--untracked-files=all").splitlines()
    # git() strips leading spaces from the first entry; use its final path field.
    require(all(line.split()[-1].replace("\\", "/") in (*CODE, ".gitattributes") for line in pending), "unrelated edits")
    old = verify_prior()
    config = extractor_config()
    preserved = dict(old["preserved_sha256"])
    preserved.update(old["code_sha256"])
    a = read(prior.OUT / "acceptance_evidence_v1.json")
    preserved.update(a["verification_code_sha256"])
    preserved.update(a["report_sha256"])
    preserved.update({p.relative_to(ROOT).as_posix(): file_hash(p) for p in prior.OUT.iterdir() if p.is_file()})
    FINAL.mkdir()
    write(FINAL / "preflight_v1.json", {"phase": "TECH-STAT-006", "start_commit": START,
        "code_sha256": hashes(ROOT, CODE), "preserved_sha256": preserved,
        "manifest_sha256": source.MANIFEST, "fold_sha256": source.FOLDS,
        "schema_sha256": prior.core.B2_SHA, "recipe": prior.core.estimator("S0").get_params(),
        "extractor": config, "environment": baseline.environment(), "final_fits_authorized": 1,
        "runtime_estimate_seconds": {"training_from_numeric_cache": [5, 30], "synthetic_real_LM_smoke": [5, 60],
                                     "CALIBRATION_233_rows": [15, 150]},
        "cycle_2": "DEFERRED", "final_operating_point": "NOT_FROZEN",
        "calibration_recipe": {**read(baseline.MODEL / "model_config.json")["calibration_recipe"],
            "version": "ds_v2_cal_v1", "default_vote": "calibrated_probability>=0.5; DEVELOPMENT_DEFAULT_NOT_FINAL_OPERATING_POINT"}})
    print(json.dumps({"status": "PREPARED_NOT_TRAINED", "fits": 1, "B2_features": 26}), flush=True)


def checked():
    p = read(FINAL / "preflight_v1.json")
    require(git("branch", "--show-current") == "tech/stat-006", "wrong phase branch")
    git("merge-base", "--is-ancestor", START, "HEAD")
    require(p["environment"] == baseline.environment() and p["recipe"] == prior.core.estimator("S0").get_params(), "environment/recipe drift")
    baseline.verify_hashes(ROOT, p["code_sha256"])
    baseline.verify_hashes(ROOT, p["preserved_sha256"])
    preservation()
    require(file_hash(source.CACHE) == prior.stat004.CACHE_SHA, "numeric cache drift")
    baseline.verify()
    return p


def clean_code():
    require(not git("status", "--porcelain", "--untracked-files=all"), "clean-tree execution required")
    for path in CODE:
        require(git("hash-object", f"--path={path}", path) == git("rev-parse", f"HEAD:{path}"), "run code not committed")
    return git("rev-parse", "HEAD")


def train():
    p = checked()
    commit = clean_code()
    require(not (FINAL / "training_started_v1.json").exists(), "one final fit already started; no retry")
    source.install_gate({"source_artifact_sha256": {}})
    write(FINAL / "training_started_v1.json", {"code_commit": commit, "started_at": datetime.now(UTC).isoformat()})
    started = time.perf_counter()
    try:
        rows, _ = baseline.selected_metadata()
        evidence = source.load_cache(rows, prior.stat004.CACHE_SHA)
        require(len(rows) == 1135 and sum(int(r["label"]) for r in rows) == 183, "training population drift")
        refs = features.References.fit(rows, evidence)
        matrix = np.asarray([refs.transform(e, "B2") for e in evidence])
        require(matrix.shape == (1135, 26) and np.isfinite(matrix).all(), "final matrix drift")
        fit_record = {}
        model = features.fit_lr(matrix, np.asarray([int(r["label"]) for r in rows]), fit_record.update)
        require(model.get_params() == p["recipe"], "final LR recipe drift")
        payload = {"classes": model.classes_.tolist(), "coefficients": model.coef_.tolist(),
                   "intercept": model.intercept_.tolist(), "recipe": model.get_params()}
        cfg = p["extractor"]
        dependencies = ("detection_service/analysis/statistical_feature_ablation.py",
            "detection_service/analysis/statistical_scorer_comparison.py",
            "detection_service/app/detectors/statistical_risk/schema.py",
            "detection_service/app/detectors/statistical_risk/scorer.py",
            "detection_service/app/detectors/semantic/calibration.py")
        runtime = {**cfg["feature_extractor_sha256"], **hashes(ROOT, (*RUNTIME, *dependencies))}
        manifest = {"detector_id": "statistical_perplexity", "detector_version": "ds_v2",
            "representation": "B2", "feature_count": 26, "feature_names": list(features.names("B2")),
            "feature_schema_version": "stat004_B2_v1", "feature_schema_sha256": prior.core.B2_SHA,
            "runtime_code_sha256": runtime, "reference_lm": cfg["reference_lm"], "extractor_config": cfg["extractor_config"],
            "training_manifest_sha256": source.MANIFEST, "fold_sha256": source.FOLDS, "seed": 1701,
            "training_rows": 1135, "positive": 183, "negative": 952, "environment": p["environment"],
            "raw_score": "LR class1 probability; higher=more adversarial; uncalibrated",
            "compatibility_vote": "raw>=0.5 until calibrated; calibrated>=0.5 thereafter",
            "cutpoint_type": "DEVELOPMENT_DEFAULT_NOT_FINAL_OPERATING_POINT", "final_operating_point": "NOT_FROZEN",
            "cycle_2": "DEFERRED", "complementarity": "NOT_EVALUATED"}
        in_memory = B2Model(payload, refs.payload, manifest)
        require(np.array_equal(model.predict_proba(matrix)[:, 1], in_memory.predict(matrix)), "LR serialization semantics differ")
        write(FINAL / MODEL_FILE, payload)
        write(FINAL / REFERENCE_FILE, refs.payload)
        write(FINAL / MANIFEST_FILE, manifest)
        write(FINAL / TRAINING_FILE, {"status": "PASS", "phase": "TECH-STAT-006", "code_commit": commit,
            "code_sha256": p["code_sha256"], "environment": p["environment"], "partition": "BASE_TRAIN",
            "rows": 1135, "positive": 183, "negative": 952, "features": 26,
            "schema_sha256": prior.core.B2_SHA, "recipe": p["recipe"], **fit_record,
            "final_fit_count": 1, "reference_fit_partition": "BASE_TRAIN", "training_membership_sha256": digest_ids(rows),
            "matrix_sha256": hashlib.sha256(matrix.tobytes()).hexdigest(), "numeric_cache_sha256": prior.stat004.CACHE_SHA,
            "runtime_seconds": time.perf_counter() - started, "calibration_used": False, "validation_used": False,
            "protected_used": False, "E1_E10": False, "raw_dataset_opens": sorted(baseline.DATASET_OPEN_LOG)})
        write(FINAL / INTEGRITY_FILE, hashes(FINAL, FROZEN_FILES[:-1]))
        loaded = B2Model.load(FINAL)
        require(np.array_equal(in_memory.predict(matrix), loaded.predict(matrix)), "reload changes raw scores")
        checked()
        print(json.dumps({"status": "FINAL_MODEL_FROZEN", **fit_record, "model_sha256": file_hash(FINAL / MODEL_FILE)}), flush=True)
    except Exception as exc:
        write(FINAL / "training_failure_v1.json", {"status": "STOP", "error": str(exc), "fit": fit_record if 'fit_record' in locals() else {}, "code_commit": commit})
        raise


def smoke(calibrated=False):
    checked()
    source.install_gate({"source_artifact_sha256": {}})
    with patch.object(LogisticRegression, "fit", side_effect=AssertionError("no classifier refit")), \
         patch.object(features.References, "fit", side_effect=AssertionError("no reference refit")):
        model = B2Model.load(FINAL)
        extractor = baseline.extractor(model.manifest)
        cal = load_calibration(CAL, FINAL) if calibrated else None
        one = B2StatisticalDetector(extractor, model, cal)
        two = B2StatisticalDetector(extractor, B2Model.load(FINAL), load_calibration(CAL, FINAL) if calibrated else None)
        results = []
        for i, text in enumerate(("Summarize tomorrow's engineering meeting agenda.", "Please review this short synthetic request and list its key words.", "")):
            request = DetectionRequest(request_id=f"ds-v2-smoke-{i}", content=DetectionContent(type="user_prompt", text=text))
            a, b, c = one.detect(request), one.detect(request), two.detect(request)
            for key in ("raw_score", "calibrated_probability", "binary_vote", "features", "input_coverage", "metadata"):
                require(getattr(a, key) == getattr(b, key) == getattr(c, key), "real LM smoke/reload nondeterminism")
            require(a.detector_version == "ds_v2" and a.metadata["final_operating_point"] == "NOT_FROZEN", "contract/policy drift")
            if a.status == "success":
                require(len(a.metadata["b2_features"]) == 26 and a.raw_score is not None, "schema/raw score missing")
            else:
                require(a.raw_score is a.calibrated_probability is a.binary_vote is None, "insufficient-input fallback")
            results.append({"synthetic_id": i, "status": a.status, "raw_score": a.raw_score,
                            "calibrated_probability": a.calibrated_probability, "feature_count": a.metadata["feature_count"]})
        from detection_service.app.detectors.statistical_risk import ScoredStatisticalDetector, StatisticalScorer
        from detection_service.app.detectors.statistical_risk.scorer import load_calibrator
        v1, _ = StatisticalScorer.load(baseline.MODEL)
        v1_result = ScoredStatisticalDetector(extractor, v1, load_calibrator(baseline.MODEL / "calibration", baseline.MODEL)).detect(request.model_copy(update={"content": DetectionContent(type="user_prompt", text="Summarize tomorrow's engineering meeting agenda.")}))
        require(v1_result.detector_version == "ds_v1" and v1_result.raw_score is not None, "ds_v1 compatibility failed")
    directory = CAL if calibrated else FINAL
    write(directory / "synthetic_smoke_v1.json", {"status": "PASS", "real_local_LM": True,
        "repeat_and_reload_identical": True, "reference_refits": 0, "classifier_refits": 0,
        "schema_features": 26, "ds_v1_compatibility": "PASS", "results": results,
        "scope": "SYNTHETIC_STRINGS_ONLY_NO_PROJECT_EVALUATION", "calibrated": calibrated})
    checked()
    print(json.dumps({"status": "SMOKE_PASS", "calibrated": calibrated}), flush=True)


def check():
    p = checked()
    require(not (FINAL / "training_failure_v1.json").exists(), "training failure present")
    m = read(FINAL / TRAINING_FILE)
    require(m["status"] == "PASS" and m["final_fit_count"] == 1 and m["converged"] and max(m["n_iter"]) < 20000, "final training incomplete")
    git("merge-base", "--is-ancestor", m["code_commit"], "HEAD")
    with patch.object(LogisticRegression, "fit", side_effect=AssertionError("no refit")), \
         patch.object(features.References, "fit", side_effect=AssertionError("no reference refit")):
        model = B2Model.load(FINAL)
        rows, _ = baseline.selected_metadata()
        evidence = source.load_cache(rows, prior.stat004.CACHE_SHA)
        require(model.references.payload["fit_training_ids"] == [r["sample_id"] for r in rows]
                and model.references.payload["benign_ids"] == [r["sample_id"] for r in rows if int(r["label"]) == 0], "reference membership drift")
        x = np.asarray([model.transform(e) for e in evidence])
        require(hashlib.sha256(x.tobytes()).hexdigest() == m["matrix_sha256"] and x.shape == (1135, 26), "final matrix reconstruction drift")
        require(model.predict(x).shape == (1135,), "scorer reconstruction drift")
    require(read(FINAL / "synthetic_smoke_v1.json")["status"] == "PASS", "smoke not accepted")
    print(json.dumps({"status": "STAT006_PASS", "preserved_files": len(p["preserved_sha256"]), "baseline": preservation(), "classifier_refits": 0}), flush=True)


def calibrate():
    checked()
    require(not CAL.exists(), "calibration already started; no retry")
    commit = clean_code()
    require(read(FINAL / "synthetic_smoke_v1.json")["status"] == "PASS", "STAT006 smoke missing")
    for name in FROZEN_FILES:
        path = (FINAL / name).relative_to(ROOT).as_posix()
        require(git("hash-object", f"--path={path}", path) == git("rev-parse", f"HEAD:{path}"), "STAT006 must be committed first")
    binding = hashes(FINAL, FROZEN_FILES)
    CAL.mkdir()
    write(CAL / "calibration_started_v1.json", {"code_commit": commit, "partition": "CALIBRATION", "model_binding": binding})
    started = time.perf_counter()
    try:
        config = read(FINAL / MANIFEST_FILE)
        approved = read(baseline.OUTPUT / "analysis_config_v1.json")["source_artifact_sha256"]
        source.install_gate({"source_artifact_sha256": approved})
        with patch.object(LogisticRegression, "fit", side_effect=AssertionError("calibration cannot retrain LR")), \
             patch.object(features.References, "fit", side_effect=AssertionError("calibration cannot refit B2")):
            rows = sorted(calibration_rows(ROOT / baseline.MANIFEST_PATH), key=lambda r: r["record_id"])
            require(len(rows) == 233 and sum(int(r["canonical_label"]) for r in rows) == 39, "calibration population drift")
            texts, observed = load_calibration_texts(rows, ROOT)
            require(observed == approved, "calibration raw source hash drift")
            model, extractor = B2Model.load(FINAL), baseline.extractor(config)
            x = []
            for i, text in enumerate(texts, 1):
                obs = extractor.engine.score(text)
                values = source.extract_features(obs.surprisals, config["extractor_config"]["window_size"],
                    config["extractor_config"]["window_stride"], config["extractor_config"]["provisional_high_surprisal_threshold"])
                item = {"surprisals": obs.surprisals, "input_tokens": obs.input_tokens, "tokens_analyzed": obs.tokens_analyzed,
                        "v1_features": [getattr(values, n) for n in FEATURE_NAMES]}
                x.append(model.transform(item))
                if i % 50 == 0 or i == len(texts):
                    print(json.dumps({"CALIBRATION_scored": i, "total": 233, "seconds": time.perf_counter() - started}), flush=True)
                require(time.perf_counter() - started < 300, "unexpected long calibration extraction; STOP")
            raw = model.predict(np.asarray(x))
            labels = np.asarray([int(r["canonical_label"]) for r in rows])
            calibration = SigmoidCalibrator.fit_mapping(raw, labels, {"partitions_fitted": ["CALIBRATION"]})
            probability = calibration.predict(raw)
            records = [{"record_id": r["record_id"], "partition": "CALIBRATION", "label": int(r["canonical_label"]),
                        "raw_score": float(a), "calibrated_probability": float(b)} for r, a, b in zip(rows, raw, probability, strict=True)]
            predictions_bytes = source.csv_bytes(records)
            metrics = diagnostics(labels, raw, probability)
            metrics["ranking_sanity"] = {s: {"roc_auc": float(roc_auc_score(labels, scores)), "pr_auc": float(average_precision_score(labels, scores))}
                for s, scores in (("raw", raw), ("calibrated", probability))}
            write(CAL / CAL_FILE, {"slope": calibration.slope, "intercept": calibration.intercept, "epsilon": EPSILON})
            write(CAL / CAL_METRICS, metrics)
            write(CAL / CAL_MANIFEST, {"status": "PASS", "phase": "TECH-STAT-007", "detector_version": "ds_v2",
                "calibration_version": "ds_v2_cal_v1", "method": METHOD, "partitions_fitted": ["CALIBRATION"],
                "code_commit": commit, "code_sha256": checked()["code_sha256"], "environment": baseline.environment(),
                "feature_schema_sha256": prior.core.B2_SHA, "model_binding": binding, "manifest_sha256": source.MANIFEST,
                "calibration_rows": 233, "positive": 39, "negative": 194,
                "membership_sha256": hashlib.sha256("\n".join(r["record_id"] for r in rows).encode()).hexdigest(),
                "prediction_sha256": hashlib.sha256(predictions_bytes).hexdigest(),
                "source_selection_policy": "Approved original mixed containers only; selected CALIBRATION scalar texts alone enter LM/transforms/calibrator. No unselected row is scored.",
                "optimizer": calibration.metadata, "runtime_seconds": time.perf_counter() - started,
                "recipe": read(FINAL / "preflight_v1.json")["calibration_recipe"], "source_artifact_sha256": observed,
                "observed_dataset_opens": sorted(baseline.DATASET_OPEN_LOG), "classifier_refits": 0, "reference_refits": 0,
                "reference_LM_finetuned": False, "validation_used": False, "protected_used": False, "E1_E10": False,
                "final_operating_point": "NOT_FROZEN", "cycle_2": "DEFERRED"})
            write(CAL / CAL_INTEGRITY, hashes(CAL, (CAL_FILE, CAL_MANIFEST, CAL_METRICS)))
            loaded = load_calibration(CAL, FINAL)
            require(np.array_equal(probability, loaded.predict(raw)), "calibrator reload drift")
            write(CAL / "calibration_predictions_v1.csv", predictions_bytes)
        baseline.verify_hashes(FINAL, binding)
        checked()
        print(json.dumps({"status": "CALIBRATION_FROZEN", "slope": calibration.slope, "intercept": calibration.intercept,
            "brier": [metrics[k]["brier_score"] for k in ("raw", "calibrated")], "nll": [metrics[k]["log_loss"] for k in ("raw", "calibrated")]}), flush=True)
    except Exception as exc:
        write(CAL / "calibration_failure_v1.json", {"status": "STOP", "error": str(exc), "code_commit": commit})
        raise


def check_cal():
    checked()
    require(not (CAL / "calibration_failure_v1.json").exists(), "calibration failed")
    with patch.object(LogisticRegression, "fit", side_effect=AssertionError("no LR refit")), \
         patch.object(features.References, "fit", side_effect=AssertionError("no B2 refit")), \
         patch.object(SigmoidCalibrator, "fit_mapping", side_effect=AssertionError("no calibration refit")):
        cal = load_calibration(CAL, FINAL)
        metadata = read(CAL / CAL_MANIFEST)
        require(file_hash(CAL / "calibration_predictions_v1.csv") == metadata["prediction_sha256"], "calibration prediction hash drift")
        git("merge-base", "--is-ancestor", metadata["code_commit"], "HEAD")
        rows = sorted(calibration_rows(ROOT / baseline.MANIFEST_PATH), key=lambda r: r["record_id"])
        with (CAL / "calibration_predictions_v1.csv").open(encoding="utf-8", newline="") as handle:
            predictions = list(csv.DictReader(handle))
        require([r["record_id"] for r in predictions] == [r["record_id"] for r in rows]
                and all(r["partition"] == "CALIBRATION" and int(r["label"]) == int(s["canonical_label"])
                        for r, s in zip(predictions, rows, strict=True)), "calibration prediction population drift")
        y = np.asarray([int(r["canonical_label"]) for r in rows])
        raw = np.asarray([float(r["raw_score"]) for r in predictions])
        prob = np.asarray([float(r["calibrated_probability"]) for r in predictions])
        require(np.array_equal(cal.predict(raw), prob), "calibration prediction reconstruction drift")
        original = read(CAL / CAL_METRICS)
        rebuilt = diagnostics(y, raw, prob)
        require(all(original[k] == v for k, v in rebuilt.items()), "calibration metrics drift")
        require(read(CAL / "synthetic_smoke_v1.json")["status"] == "PASS", "calibrated smoke missing")
    print(json.dumps({"status": "STAT007_PASS", "model_unchanged": True, "rows": 233, "refits": 0,
                      "baseline": preservation()}), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("prepare", "train", "smoke", "check", "calibrate", "cal-smoke", "cal-check"), required=True)
    mode = parser.parse_args().mode
    require(Path.cwd().resolve() == ROOT, "execute from repository root")
    {"prepare": prepare, "train": train, "smoke": smoke, "check": check, "calibrate": calibrate,
     "cal-smoke": lambda: smoke(True), "cal-check": check_cal}[mode]()


if __name__ == "__main__":
    main()
