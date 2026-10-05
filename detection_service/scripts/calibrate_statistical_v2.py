"""STAT-007 runner corrected to the hash-verified CALIBRATION class counts."""

import argparse
import hashlib
import time
from unittest.mock import patch

import numpy as np
from sklearn.metrics import average_precision_score, roc_auc_score

from detection_service.scripts import freeze_statistical_v2 as d
from detection_service.scripts.verify_statistical_v2 import synthetic_content

HISTORY = d.CAL
OUT = HISTORY / "completed_v1"
CODE = ("detection_service/scripts/calibrate_statistical_v2.py",
        "detection_service/tests/test_statistical_v2_calibration.py")


def population():
    rows = sorted(d.calibration_rows(d.ROOT / d.baseline.MANIFEST_PATH), key=lambda r: r["record_id"])
    d.require(len(rows) == 233 and sum(int(r["canonical_label"]) for r in rows) == 41,
              "authoritative CALIBRATION population mismatch")
    return rows


def verify_stop():
    failure = d.read(HISTORY / "calibration_failure_v1.json")
    d.require(failure == {"code_commit": "30d3781f23651bc4317ce621ac916896bf47dc66",
                          "error": "STOP: calibration population drift", "status": "STOP"},
              "unexpected historical failure; do not resume")
    d.require({p.name for p in HISTORY.iterdir() if p.is_file()} ==
              {"calibration_started_v1.json", "calibration_failure_v1.json"},
              "prior attempt advanced beyond its population guard")
    return d.hashes(HISTORY, ("calibration_started_v1.json", "calibration_failure_v1.json"))


def calibrate():
    d.checked()
    history = verify_stop()
    rows = population()
    commit = d.clean_code()
    for path in CODE:
        d.require(d.git("hash-object", f"--path={path}", path) == d.git("rev-parse", f"HEAD:{path}"),
                  "corrected runner must be committed")
    binding = d.hashes(d.FINAL, d.FROZEN_FILES)
    for name in d.FROZEN_FILES:
        path = (d.FINAL / name).relative_to(d.ROOT).as_posix()
        d.require(d.git("hash-object", f"--path={path}", path) == d.git("rev-parse", f"HEAD:{path}"),
                  "STAT006 package must be committed")
    d.require(not OUT.exists(), "corrected calibration already started; no retry")
    OUT.mkdir()
    d.write(OUT / "calibration_started_v1.json", {"code_commit": commit, "model_binding": binding,
            "historical_pre_fit_stop_sha256": history, "partition": "CALIBRATION"})
    started = time.perf_counter()
    try:
        approved = d.read(d.baseline.OUTPUT / "analysis_config_v1.json")["source_artifact_sha256"]
        d.source.install_gate({"source_artifact_sha256": approved})
        with patch.object(d.LogisticRegression, "fit", side_effect=AssertionError("no LR refit")), \
             patch.object(d.features.References, "fit", side_effect=AssertionError("no reference refit")):
            texts, observed = d.load_calibration_texts(rows, d.ROOT)
            d.require(observed == approved, "raw source hash drift")
            model = d.B2Model.load(d.FINAL)
            config = model.manifest
            extractor = d.baseline.extractor(config)
            x = []
            for i, text in enumerate(texts, 1):
                obs = extractor.engine.score(text)
                values = d.source.extract_features(obs.surprisals, config["extractor_config"]["window_size"],
                    config["extractor_config"]["window_stride"],
                    config["extractor_config"]["provisional_high_surprisal_threshold"])
                x.append(model.transform({"surprisals": obs.surprisals, "input_tokens": obs.input_tokens,
                    "tokens_analyzed": obs.tokens_analyzed, "v1_features": [getattr(values, n) for n in d.FEATURE_NAMES]}))
                if i % 50 == 0 or i == len(texts):
                    print({"CALIBRATION_scored": i, "total": 233, "seconds": time.perf_counter() - started}, flush=True)
                d.require(time.perf_counter() - started < 300, "unexpected long extraction; STOP")
            raw = model.predict(np.asarray(x))
            labels = np.asarray([int(r["canonical_label"]) for r in rows])
            calibration = d.SigmoidCalibrator.fit_mapping(raw, labels, {"partitions_fitted": ["CALIBRATION"]})
            probability = calibration.predict(raw)
            metrics = d.diagnostics(labels, raw, probability)
            metrics["ranking_sanity"] = {key: {"roc_auc": float(roc_auc_score(labels, scores)),
                "pr_auc": float(average_precision_score(labels, scores))}
                for key, scores in (("raw", raw), ("calibrated", probability))}
            predictions = d.source.csv_bytes([{"record_id": r["record_id"], "partition": "CALIBRATION",
                "label": int(r["canonical_label"]), "raw_score": float(a), "calibrated_probability": float(b)}
                for r, a, b in zip(rows, raw, probability, strict=True)])
            d.write(OUT / d.CAL_FILE, {"slope": calibration.slope, "intercept": calibration.intercept, "epsilon": d.EPSILON})
            d.write(OUT / d.CAL_METRICS, metrics)
            d.write(OUT / d.CAL_MANIFEST, {"status": "PASS", "phase": "TECH-STAT-007", "detector_version": "ds_v2",
                "calibration_version": "ds_v2_cal_v1", "method": d.METHOD, "partitions_fitted": ["CALIBRATION"],
                "code_commit": commit, "code_sha256": {**d.checked()["code_sha256"], **d.hashes(d.ROOT, CODE)},
                "environment": d.baseline.environment(), "feature_schema_sha256": d.prior.core.B2_SHA,
                "model_binding": binding, "manifest_sha256": d.source.MANIFEST,
                "calibration_rows": len(rows), "positive": int(labels.sum()), "negative": int((labels == 0).sum()),
                "membership_sha256": hashlib.sha256("\n".join(r["record_id"] for r in rows).encode()).hexdigest(),
                "prediction_sha256": hashlib.sha256(predictions).hexdigest(),
                "source_selection_policy": "Approved mixed containers; only selected CALIBRATION texts enter LM/transforms/fit.",
                "optimizer": calibration.metadata, "runtime_seconds": time.perf_counter() - started,
                "recipe": d.read(d.FINAL / "preflight_v1.json")["calibration_recipe"],
                "source_artifact_sha256": observed, "observed_dataset_opens": sorted(d.baseline.DATASET_OPEN_LOG),
                "classifier_refits": 0, "reference_refits": 0, "reference_LM_finetuned": False,
                "validation_used": False, "protected_used": False, "E1_E10": False,
                "final_operating_point": "NOT_FROZEN", "cycle_2": "DEFERRED",
                "historical_pre_fit_stop_sha256": history,
                "correction": "Prior guard mistakenly used VALIDATION 39/194 counts; immutable CALIBRATION is 41/192. Prior stop preceded raw text access and calibration fitting."})
            d.write(OUT / d.CAL_INTEGRITY, d.hashes(OUT, (d.CAL_FILE, d.CAL_MANIFEST, d.CAL_METRICS)))
            d.require(np.array_equal(probability, d.load_calibration(OUT, d.FINAL).predict(raw)), "reload drift")
            d.write(OUT / "calibration_predictions_v1.csv", predictions)
        d.baseline.verify_hashes(d.FINAL, binding)
        d.baseline.verify_hashes(HISTORY, history)
        d.checked()
        print({"status": "CALIBRATION_FROZEN", "metrics": metrics}, flush=True)
    except Exception as exc:
        d.write(OUT / "calibration_failure_v1.json", {"status": "STOP", "error": str(exc), "code_commit": commit})
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("calibrate", "cal-smoke", "cal-check"), required=True)
    mode = parser.parse_args().mode
    d.require(d.Path.cwd().resolve() == d.ROOT, "execute from repository root")
    with patch.object(d, "CAL", OUT):
        if mode == "calibrate":
            calibrate()
        elif mode == "cal-smoke":
            with patch.object(d, "DetectionContent", side_effect=synthetic_content):
                d.smoke(True)
        else:
            population()
            metadata = d.read(OUT / d.CAL_MANIFEST)
            d.baseline.verify_hashes(d.ROOT, metadata["code_sha256"])
            d.baseline.verify_hashes(HISTORY, metadata["historical_pre_fit_stop_sha256"])
            d.check_cal()


if __name__ == "__main__":
    main()
