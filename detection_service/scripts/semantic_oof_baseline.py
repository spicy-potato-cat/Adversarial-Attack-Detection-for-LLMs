"""TECH-SEM-003: offline prepare, synthetic smoke, Commander-run OOF, and verify."""

import argparse
import csv
from datetime import UTC, datetime
import io
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

import jsonschema
import torch

from detection_service.analysis.semantic_oof import (
    BUDGETS, BORDERLINE_DISTANCE, HIGH_CONFIDENCE, LENGTH_BUCKETS, RECIPE_SHA256, FOLD_SHA256,
    REVISION, characterize, check_membership, curves, initialize, parameter_hash, predict,
    probability_metrics, recommendations, require, run_folds, schema_projection, stability,
    truncation_analysis, validate_predictions, validate_recipe, digest_ids,
)
from detection_service.quality.development_fixture import ROOT, file_hash, json_bytes, verify
from detection_service.quality.policy import ARTIFACT_DIR, FOLD_PATH, MANIFEST_PATH
from detection_service.analysis.semantic_oof_preflight import (
    PRODUCT_NAMES, RUN_METADATA_NAME, environment, fold_execution_plan, metric_validation, output_contract,
)
from detection_service.scripts.statistical_oof_baseline import baseline_check, selected_metadata
from detection_service.scripts.train_semantic_finetuned import (
    RECIPE, PREPARATION, deterministic, fit_transformer, hardware, packages, read_preparation,
)

OUTPUT = ROOT / "artifacts/semantic_v2/oof"
PREFLIGHT = OUTPUT / "preflight"
BASELINE = ROOT / "artifacts/models/dm_b_v1"
CODE = ("detection_service/analysis/semantic_oof.py", "detection_service/scripts/semantic_oof_baseline.py",
        "detection_service/tests/test_semantic_oof.py", "detection_service/scripts/train_semantic_finetuned.py",
        "detection_service/scripts/statistical_oof_baseline.py", "detection_service/analysis/statistical_oof.py")
CODE += ("detection_service/analysis/semantic_oof_preflight.py", "detection_service/tests/test_statistical_oof.py")
CSV_FIELDS = ("sample_id", "partition", "fold", "label", "source_name", "source_revision", "lineage_group",
              "detector_id", "detector_version", "candidate_id", "raw_score", "logit_margin",
              "calibrated_probability", "binary_prediction", "error_type", "threshold_distance",
              "confidence_category", "input_tokens", "max_input_tokens", "tokens_analyzed", "tokens_excluded",
              "truncated", "payload_position_status", "latency_ms")
OPENED_SOURCES = set()


def write(path, value):
    with Path(path).open("xb") as handle:
        handle.write(json_bytes(value))


def verify_hashes(root, mapping):
    for name, digest in mapping.items():
        path = (root / name).resolve()
        require(path.is_relative_to(root.resolve()) and file_hash(path) == digest, f"integrity drift: {name}")


def preserved_files():
    paths = [p for p in BASELINE.rglob("*") if p.is_file() and "__pycache__" not in p.parts]
    paths += [ROOT / RECIPE, ROOT / PREPARATION]
    paths += list((ROOT / "reviews").glob("TECH_SEM_002*.md"))
    paths += list((ROOT / "artifacts/statistical_v2/oof").glob("*"))
    return {p.relative_to(ROOT).as_posix(): file_hash(p) for p in sorted(set(paths)) if p.is_file()}


def local_recipe():
    require(file_hash(ROOT / RECIPE) == RECIPE_SHA256, "frozen recipe bytes differ")
    config, preparation = read_preparation()
    validate_recipe(config)
    require(preparation["revision"] == preparation["tokenizer_revision"] == REVISION, "preparation revision drift")
    snapshot = Path(preparation["snapshot_path"]).resolve()
    require(snapshot.is_relative_to((ROOT / "detection_service/.model-cache/dm_b_v1").resolve()), "wrong upstream snapshot location")
    verify_hashes(snapshot, preparation["upstream_files_sha256"])
    integrity = json.loads((BASELINE / "integrity_manifest.json").read_text(encoding="utf-8"))
    verify_hashes(BASELINE, integrity)  # Opaque byte hashes only; no final classifier is loaded.
    return config, preparation


def prepare():
    require(not OUTPUT.exists(), "analysis directory exists; refuse overwrite")
    fixture = verify()
    require(file_hash(ROOT / FOLD_PATH) == FOLD_SHA256, "frozen fold hash differs")
    baseline = baseline_check()
    config, preparation = local_recipe()
    folds, selected = selected_rows()
    prior = json.loads((BASELINE / "training_metadata.json").read_text(encoding="utf-8"))
    steps = [math.ceil(sum(int(r["outer_fold"]) != f for r in folds) / 8) * 3 for f in range(5)]
    estimate = prior["runtime_seconds"] * sum(steps) / (math.ceil(1135 / 8) * 3)
    payload = {
        "phase": "TECH-SEM-003", "scope": "DEVELOPMENT_OOF_NOT_E1_E10", "expected_rows": 1135,
        "manifest_sha256": config.manifest_sha256, "fold_sha256": FOLD_SHA256,
        "quality_fixture_sha256": file_hash(ROOT / ARTIFACT_DIR / "quality_fixture_v1.json"),
        "recipe": config.to_dict(), "recipe_sha256": RECIPE_SHA256,
        "preparation_sha256": file_hash(ROOT / PREPARATION), "upstream_revision": REVISION,
        "source_artifact_sha256": prior["source_artifact_sha256"],
        "threshold_rule": {"raw_cutpoint": .5, "fitted": False, "held_out_influence": False,
                           "rationale": "Data-independent existing raw development cutpoint fixed before scoring; no calibration."},
        "fixed_fpr_budgets": list(BUDGETS), "fixed_fpr_role": "DESCRIPTIVE_ONLY_NOT_DEPLOYED_THRESHOLD",
        "confidence_rules": {"borderline_distance_inclusive": BORDERLINE_DISTANCE, "confident_wrong_probability": HIGH_CONFIDENCE},
        "length_buckets": list(LENGTH_BUCKETS), "optional_512_forward": "SKIPPED_TO_AVOID_SCOPE_EXPANSION",
        "preserved_file_sha256": preserved_files(), "baseline_preservation": baseline,
        "code_sha256": {name: file_hash(ROOT / name) for name in CODE}, "packages": packages(),
        "hardware": hardware(), "fold_training_steps": steps, "prior_training_seconds": prior["runtime_seconds"],
        "estimated_training_seconds": estimate,
        "estimate_limitations": "Linear optimizer-step scaling (~73min), plus loading/prediction; actual batch lengths, RAM pressure and CPU load vary.",
        "long_run_delegated_to_commander": True, "final_model_loaded": False, "calibrator_loaded": False,
        "calibration_used": False, "validation_used": False, "protected_used": False, "dm_b_v2_trained": False,
        "source_selection": "Only BASE_TRAIN scalar locators selected; approved CSV/Parquet containers physically include other partitions.",
        "start_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "code_provenance": "New uncommitted analysis bytes are independently frozen by code_sha256.",
    }
    OUTPUT.mkdir(parents=True)
    write(OUTPUT / "analysis_config_v1.json", payload)
    write(OUTPUT / "preflight_v1.json", {"analysis_config_sha256": file_hash(OUTPUT / "analysis_config_v1.json"),
                                       "fixture": fixture, "baseline": baseline, "selected_BASE_TRAIN_rows": len(selected)})
    print(json.dumps({"status": "PREPARED_NOT_RUN", "device": config.device, "estimated_training_minutes": estimate / 60}, indent=2))


def checked_config():
    config = json.loads(config_path().read_text(encoding="utf-8"))
    anchor = PREFLIGHT / "config_anchor_v1.json" if config_path().parent == PREFLIGHT else OUTPUT / "preflight_v1.json"
    preflight = json.loads(anchor.read_text(encoding="utf-8"))
    require(file_hash(config_path()) == preflight["analysis_config_sha256"], "analysis config drift")
    verify()
    baseline_check()
    verify_hashes(ROOT, config["code_sha256"])
    verify_hashes(ROOT, config["preserved_file_sha256"])
    frozen, preparation = local_recipe()
    require(frozen.to_dict() == config["recipe"] and packages() == config["packages"], "recipe/environment differs from preflight")
    require(file_hash(ROOT / PREPARATION) == config["preparation_sha256"], "preparation drift")
    require(file_hash(ROOT / FOLD_PATH) == config["fold_sha256"] == FOLD_SHA256, "fold drift")
    if "environment" in config:
        require(config["environment"] == environment(), "pre-run package/executable drift")
        verify_hashes(OUTPUT, config["historical_evidence_sha256"])
    return config, frozen, preparation


def config_path():
    newer = PREFLIGHT / "analysis_config_v2.json"
    return newer if newer.exists() else OUTPUT / "analysis_config_v1.json"


def evidence_root():
    return PREFLIGHT if config_path().parent == PREFLIGHT else OUTPUT


def prepare_prerun():
    require(not PREFLIGHT.exists(), "pre-run package exists; refusing overwrite")
    require(not (OUTPUT / "run_started_v1.json").exists(), "run already started")
    old = json.loads((OUTPUT / "analysis_config_v1.json").read_text(encoding="utf-8"))
    old_anchor = json.loads((OUTPUT / "preflight_v1.json").read_text(encoding="utf-8"))
    require(file_hash(OUTPUT / "analysis_config_v1.json") == old_anchor["analysis_config_sha256"], "historical config drift")
    verify_hashes(ROOT, old["preserved_file_sha256"])
    fixture, baseline = verify(), baseline_check()
    recipe, preparation = local_recipe()
    require(recipe.to_dict() == old["recipe"] and packages() == old["packages"], "historical recipe/environment drift")
    rows, _ = selected_rows()
    plan = fold_execution_plan(rows)
    contract = output_contract(CSV_FIELDS)
    config = {**old, "configuration_version": 2, "supersedes": "../analysis_config_v1.json",
              "code_sha256": {name: file_hash(ROOT / name) for name in CODE},
              "environment": environment(), "hardware": hardware(), "baseline_preservation": baseline,
              "output_contract": contract, "fold_execution_plan": "fold_execution_plan.json",
              "historical_evidence_sha256": {name: file_hash(OUTPUT / name) for name in
                  ("analysis_config_v1.json", "preflight_v1.json", "synthetic_smoke_v1.json", "test_evidence_v1.json", "test_results_v1.xml")},
              "planned_command": [sys.executable, "-m", "detection_service.scripts.semantic_oof_baseline", "--mode", "run"],
              "runtime_estimate_minutes_range": [75, 100],
              "code_provenance": "Run requires clean HEAD containing the committed pre-run package; code_commit is captured at execution, never guessed before commit."}
    PREFLIGHT.mkdir()
    write(PREFLIGHT / "analysis_config_v2.json", config)
    write(PREFLIGHT / "config_anchor_v1.json", {"analysis_config_sha256": file_hash(config_path())})
    write(PREFLIGHT / "fold_execution_plan.json", plan)
    write(PREFLIGHT / "output_contract_v1.json", contract)
    write(PREFLIGHT / "metric_validation_v1.json", metric_validation())
    write(PREFLIGHT / "fixture_verification_v1.json", {"fixture": fixture, "baseline": baseline,
         "original_baseline_files_checked": baseline["hash_checks"], "mismatches": 0})
    print(json.dumps({"status": "PRERUN_SPECIFIED_NOT_RUN", "fold_counts": [
        {k: r[k] for k in ("fold", "train_rows", "held_out_rows", "train_positive", "train_negative", "held_out_positive", "held_out_negative", "train_lineage_groups", "held_out_lineage_groups")}
        for r in plan["folds"]]}, indent=2))


def readiness_evidence():
    root = evidence_root()
    for name in ("synthetic_smoke_v1.json", "test_evidence_v1.json"):
        evidence = json.loads((root / name).read_text(encoding="utf-8"))
        require(evidence["analysis_config_sha256"] == file_hash(config_path()), "stale readiness evidence")
        if "status" in evidence:
            require(evidence["status"] == "PASS_SYNTHETIC_ONLY" and not evidence["project_data_used"], "smoke failed")
        else:
            require(evidence["tests"] >= 84 and evidence["failures"] == evidence["errors"] == evidence["skipped"] == 0, "tests failed or incomplete")
            verify_hashes(ROOT, {evidence["xml_path"]: evidence["xml_sha256"]})


def freeze_prerun():
    analysis, recipe, _ = checked_config()
    require(evidence_root() == PREFLIGHT, "superseding pre-run config required")
    require(not (OUTPUT / "run_started_v1.json").exists(), "authoritative execution already started")
    readiness_evidence()
    names = ("analysis_config_v2.json", "config_anchor_v1.json", "fold_execution_plan.json", "output_contract_v1.json",
             "metric_validation_v1.json", "fixture_verification_v1.json", "synthetic_smoke_v1.json",
             "test_evidence_v1.json", "test_results_v1.xml")
    rows, _ = selected_rows()
    require(json.loads((PREFLIGHT / "fold_execution_plan.json").read_text()) == fold_execution_plan(rows), "planned membership drift")
    require(json.loads((PREFLIGHT / "metric_validation_v1.json").read_text()) == metric_validation(), "metric proof drift")
    require(json.loads((PREFLIGHT / "output_contract_v1.json").read_text()) == output_contract(CSV_FIELDS) == analysis["output_contract"], "output contract drift")
    evidence = {"phase": "TECH-SEM-003", "status": "PRE_RUN_VERIFIED_COMMIT_REQUIRED", "authoritative_oof_executed": False,
        "manifest_sha256": recipe.manifest_sha256, "fold_sha256": FOLD_SHA256, "upstream_revision": REVISION,
        "max_length": 256, "seed": 1701, "evidence_sha256": {name: file_hash(PREFLIGHT / name) for name in names},
        "baseline_files_checked": analysis["baseline_preservation"]["hash_checks"], "baseline_mismatches": 0,
        "performance_results": "PENDING AUTHORITATIVE OOF EXECUTION", "runtime_estimate_minutes": [75, 100],
        "code_commit_policy": "HEAD must equal the commit containing this pre-run manifest; resolved after commit to avoid self-reference.",
        "future_output_contract": analysis["output_contract"]}
    write(PREFLIGHT / "oof_preflight_v1.json", evidence)
    digest = file_hash(PREFLIGHT / "oof_preflight_v1.json")
    with (PREFLIGHT / "oof_preflight_v1.sha256").open("xb") as handle:
        handle.write(f"{digest}  oof_preflight_v1.json\n".encode("ascii"))
    print(json.dumps({"status": evidence["status"], "oof_preflight_sha256": digest}))


def committed_freeze(require_clean):
    path = (PREFLIGHT / "oof_preflight_v1.json").relative_to(ROOT).as_posix()
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    freeze_commit = subprocess.check_output(["git", "log", "-1", "--format=%H", "--", path], cwd=ROOT, text=True).strip()
    require(head == freeze_commit and bool(freeze_commit), "HEAD is not the pre-run freeze commit")
    if require_clean:
        status = subprocess.check_output(["git", "status", "--porcelain", "--untracked-files=all"], cwd=ROOT, text=True)
        require(not status.strip(), "working tree must be clean before the authoritative OOF run")
    config, _, _ = checked_config()
    files = [*config["code_sha256"], *[p.relative_to(ROOT).as_posix() for p in PREFLIGHT.iterdir() if p.is_file()]]
    for name in files:
        # Git applies the tracked attributes; runtime byte SHA checks remain separate.
        actual = subprocess.check_output(["git", "hash-object", f"--path={name}", name], cwd=ROOT, text=True).strip()
        committed = subprocess.check_output(["git", "rev-parse", f"HEAD:{name}"], cwd=ROOT, text=True).strip()
        require(actual == committed, f"uncommitted code/evidence: {name}")
    return head


def check_prerun(require_commit=True):
    checked_config()
    readiness_evidence()
    payload = json.loads((PREFLIGHT / "oof_preflight_v1.json").read_text(encoding="utf-8"))
    verify_hashes(PREFLIGHT, payload["evidence_sha256"])
    checksum = (PREFLIGHT / "oof_preflight_v1.sha256").read_text(encoding="ascii").split()[0]
    require(checksum == file_hash(PREFLIGHT / "oof_preflight_v1.json"), "pre-run manifest checksum drift")
    rows, _ = selected_rows()
    require(json.loads((PREFLIGHT / "fold_execution_plan.json").read_text()) == fold_execution_plan(rows), "fold plan drift")
    require(json.loads((PREFLIGHT / "metric_validation_v1.json").read_text()) == metric_validation(), "metric proof drift")
    head = committed_freeze(require_clean=True) if require_commit else None
    require(not any((OUTPUT / name).exists() for name in (*PRODUCT_NAMES, RUN_METADATA_NAME, "run_started_v1.json", "completion_v1.json")), "run output already exists; not pre-run")
    result = {"status": "READY_FOR_LONG_RUN" if head else "PRE_RUN_VERIFIED_COMMIT_PENDING", "code_commit": head,
              "oof_preflight_sha256": checksum, "authoritative_oof_executed": False}
    print(json.dumps(result, indent=2))
    return result


def selected_rows():
    folds, sources = selected_metadata()
    require(len(folds) == 1135 and sum(int(r["label"]) for r in folds) == 183, "fixture count drift")
    for fold, source in zip(folds, sources, strict=True):
        require(fold["sample_id"] == source["record_id"] and fold["label"] == source["canonical_label"] and
                fold["source_name"] == source["source_dataset"] and fold["lineage_group"] == source["lineage_group_id"], "source/fold join drift")
        fold["source_revision"] = source["source_revision"]
    check_membership(folds)
    return folds, sources


def build_run_metadata(config, freeze, reports, started_at, elapsed_seconds):
    return {"code_commit": freeze["code_commit"], "manifest_sha256": config.manifest_sha256,
            "fold_sha256": FOLD_SHA256, "upstream_revision": REVISION, "tokenizer_revision": config.tokenizer_revision,
            "seed": config.seed, "device": config.device, **environment(),
            "runtime_seconds": elapsed_seconds, "started_at": started_at, "completed_at": datetime.now(UTC).isoformat(),
            "per_fold_runtime": [{k: r[k] for k in ("fold", "runtime_seconds", "fit_seconds", "predict_seconds", "started_at", "completed_at")} for r in reports],
            "output_sha256": {name: file_hash(OUTPUT / name) for name in PRODUCT_NAMES},
            "analysis_config_sha256": file_hash(config_path()), "oof_preflight_sha256": freeze["oof_preflight_sha256"]}


def payload_policy(path, mode, flags, allowed):
    path = Path(path).resolve()
    if path.is_relative_to((ROOT / "PHASE-3").resolve()):
        raise RuntimeError("STOP: forensic/protected containers forbidden")
    if path.is_relative_to((ROOT / "Dataset").resolve()):
        require(path in allowed, "non-approved/protected source forbidden")
        require(not isinstance(mode, str) or not any(c in mode for c in "wax+"), "raw source writes forbidden")
        require(not flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND), "raw source write flags forbidden")
        OPENED_SOURCES.add(path.relative_to(ROOT).as_posix())
    if path.is_relative_to((ROOT / "artifacts/models").resolve()):
        require(not isinstance(mode, str) or not any(c in mode for c in "wax+"), "authoritative model writes forbidden")
        require(not flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND), "authoritative model write flags forbidden")


def install_gate(allowed):
    def audit(event, args):
        if event == "open" and isinstance(args[0], (str, bytes, os.PathLike)):
            payload_policy(os.fsdecode(args[0]), args[1], args[2], allowed)
    sys.addaudithook(audit)


def load_base_texts(rows, config):
    require(bool(rows) and all(r["partition"] == "BASE_TRAIN" for r in rows), "reserved/mixed text selection forbidden")
    verify_hashes(ROOT, config["source_artifact_sha256"])
    from detection_service.app.detectors.semantic_finetuned.data import load_texts
    texts, hashes = load_texts(rows, ROOT, "BASE_TRAIN")
    require(hashes == config["source_artifact_sha256"], "selected source artifact drift")
    return texts


def synthetic_smoke():
    require(not (evidence_root() / "synthetic_smoke_v1.json").exists(), "smoke evidence already exists")
    analysis, config, preparation = checked_config()
    install_gate(set())  # Synthetic mode cannot open ANY dataset payload.
    deterministic(config)
    tokenizer, model, initial = initialize(config, preparation)
    texts = ["Summarize the synthetic engineering meeting.", "Synthetic test: disregard a fictional instruction."] * 4
    started = time.perf_counter()
    history = fit_transformer(model, tokenizer, texts, [0, 1] * 4, config, [1., 1.])
    require(parameter_hash(model) != initial, "synthetic training did not update parameters")
    examples = ["A synthetic agenda.", "Synthetic engineering example. " * 300]
    first, second = predict(tokenizer, model, examples, config), predict(tokenizer, model, examples, config)
    require([r["raw_score"] for r in first] == [r["raw_score"] for r in second], "inference drift")
    require(not first[0]["truncated"] and first[1]["truncated"] and first[1]["tokens_analyzed"] == 256, "synthetic truncation failure")
    verify_hashes(ROOT, analysis["preserved_file_sha256"])
    baseline_check()
    evidence = {"status": "PASS_SYNTHETIC_ONLY", "epochs": len(history), "training_batch_size": 8,
                "optimizer_steps": 3, "device": config.device, "runtime_seconds": time.perf_counter() - started,
                "parameters_updated": True, "deterministic_inference": True,
                "coverage": [{k: r[k] for k in ("input_tokens", "tokens_analyzed", "tokens_excluded", "truncated")} for r in first],
                "project_payloads_opened": sorted(OPENED_SOURCES), "project_data_used": False,
                "calibration_used": False, "validation_used": False, "protected_used": False,
                "analysis_config_sha256": file_hash(config_path())}
    write(evidence_root() / "synthetic_smoke_v1.json", evidence)
    print(json.dumps(evidence, indent=2))


def record_tests(xml_path):
    checked_config()
    root = ET.parse(xml_path).getroot()
    suites = [root] if root.tag == "testsuite" else list(root.findall("testsuite"))
    counts = {k: sum(int(s.attrib.get(k, 0)) for s in suites) for k in ("tests", "failures", "errors", "skipped")}
    require(counts["tests"] > 0 and counts["failures"] == counts["errors"] == counts["skipped"] == 0, "tests not all passed")
    classes = {t.attrib.get("classname", "") for s in suites for t in s.findall("testcase")}
    require(all(any(name in cls for name in ("test_semantic_oof", "test_statistical_oof")) for cls in classes), "unexpected test suite")
    require(any("test_semantic_oof" in cls for cls in classes) and any("test_statistical_oof" in cls for cls in classes), "both semantic and statistical regressions required")
    xml_path = Path(xml_path).resolve()
    require(xml_path.is_relative_to(OUTPUT), "test evidence must live in analysis directory")
    write(evidence_root() / "test_evidence_v1.json", {**counts, "xml_path": xml_path.relative_to(ROOT).as_posix(),
        "xml_sha256": file_hash(xml_path), "analysis_config_sha256": file_hash(config_path())})
    print(json.dumps(counts))


def csv_bytes(records):
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=CSV_FIELDS, extrasaction="ignore", lineterminator="\n")
    writer.writeheader()
    writer.writerows(records)
    return output.getvalue().encode("utf-8")


def write_csv(path, records):
    with path.open("xb") as handle:
        handle.write(csv_bytes(records))


def analysis_products(records, reports):
    truncation, errors = truncation_analysis(records), characterize(records)
    return {
        "dm_b_v1_recipe_oof_metrics.json": probability_metrics([r["label"] for r in records], [r["raw_score"] for r in records]),
        "dm_b_v1_recipe_fold_metrics.json": {"folds": reports, "stability": stability(reports)},
        "dm_b_v1_recipe_oof_curves.json": curves([r["label"] for r in records], [r["raw_score"] for r in records]),
        "dm_b_v1_truncation_analysis.json": truncation, "dm_b_v1_error_characterization.json": errors,
        "dm_b_v1_v2_recommendation.json": recommendations(truncation, errors),
    }


def validate_schema(records):
    schema = json.loads((ROOT / ARTIFACT_DIR / "oof_result_schema_v1.json").read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema)
    for row in records:
        validator.validate(schema_projection(row))


def run():
    require(not (OUTPUT / "run_started_v1.json").exists(), "run already started; no rerun/resume without review")
    freeze = check_prerun()
    analysis, config, preparation = checked_config()
    install_gate({(ROOT / p).resolve() for p in analysis["source_artifact_sha256"]})
    rows, sources = selected_rows()
    started = time.perf_counter()
    started_at = datetime.now(UTC).isoformat()
    write(OUTPUT / "run_started_v1.json", {"started_at": started_at, "device": config.device,
        "code_commit": freeze["code_commit"], "oof_preflight_sha256": freeze["oof_preflight_sha256"],
        "analysis_config_sha256": file_hash(config_path())})
    try:
        texts = load_base_texts(sources, analysis)
        records, reports = run_folds(rows, texts, config, preparation)
        del texts
        validate_schema(records)
        products = analysis_products(records, reports)
        verify_hashes(ROOT, analysis["preserved_file_sha256"])
        baseline_check()
        verify()
        for name, payload in products.items():
            write(OUTPUT / name, payload)
        write_csv(OUTPUT / "dm_b_v1_recipe_oof_predictions.csv", records)
        hard = [r for r in records if r["error_type"] in ("FN", "FP")]
        write_csv(OUTPUT / "dm_b_v1_hard_examples.csv", hard)
        require(set(products) | {"dm_b_v1_recipe_oof_predictions.csv", "dm_b_v1_hard_examples.csv"} == set(PRODUCT_NAMES), "successful output contract drift")
        names = list(PRODUCT_NAMES)
        metadata = build_run_metadata(config, freeze, reports, started_at, time.perf_counter() - started)
        write(OUTPUT / RUN_METADATA_NAME, metadata)
        names.append(RUN_METADATA_NAME)
        completion = {"status": "COMPLETE_DEVELOPMENT_OOF", "completed_at": datetime.now(UTC).isoformat(),
            "runtime_seconds": time.perf_counter() - started, "device": config.device, "rows": len(records),
            "identity_leakage": 0, "lineage_leakage": 0, "calibration_used": False, "validation_used": False,
            "protected_used": False, "final_model_loaded": False, "dm_b_v2_trained": False, "E1_E10_executed": False,
            "approved_containers_opened": sorted(OPENED_SOURCES), "preservation": "PASS",
            "code_commit": freeze["code_commit"], "oof_preflight_sha256": freeze["oof_preflight_sha256"],
            "readiness_evidence_sha256": {name: file_hash(evidence_root() / name) for name in ("synthetic_smoke_v1.json", "test_evidence_v1.json")},
            "analysis_config_sha256": file_hash(config_path()),
            "output_sha256": {name: file_hash(OUTPUT / name) for name in names}}
        write(OUTPUT / "completion_v1.json", completion)
        print(json.dumps({"status": completion["status"], "runtime_seconds": completion["runtime_seconds"],
                          "metrics": products["dm_b_v1_recipe_oof_metrics.json"],
                          "truncation": products["dm_b_v1_truncation_analysis.json"],
                          "recommendation": products["dm_b_v1_v2_recommendation.json"]}, indent=2), flush=True)
    except Exception as exc:
        write(OUTPUT / "failure_v1.json", {"status": "FAILED_STOP_FOR_REVIEW", "exception_type": type(exc).__name__,
                                          "elapsed_seconds": time.perf_counter() - started})
        raise


def read_predictions():
    with (OUTPUT / "dm_b_v1_recipe_oof_predictions.csv").open(encoding="utf-8", newline="") as handle:
        result = list(csv.DictReader(handle))
    for row in result:
        for key in ("fold", "label", "binary_prediction", "input_tokens", "max_input_tokens", "tokens_analyzed", "tokens_excluded"):
            row[key] = int(row[key])
        for key in ("raw_score", "logit_margin", "threshold_distance", "latency_ms"):
            row[key] = float(row[key])
        require(row["truncated"] in ("True", "False") and row["calibrated_probability"] == "", "invalid serialized coverage/calibration")
        row["truncated"] = row["truncated"] == "True"
        row["calibrated_probability"] = None
    return result


def check():
    checked_config()
    if not (OUTPUT / "completion_v1.json").exists():
        require(not (OUTPUT / "run_started_v1.json").exists(), "incomplete/failed OOF run; stop for review")
        print(json.dumps({"status": "PARTIAL_PIPELINE_PREPARED_OOF_NOT_RUN"}))
        return
    require(not (OUTPUT / "failure_v1.json").exists(), "OOF failure recorded")
    completion = json.loads((OUTPUT / "completion_v1.json").read_text(encoding="utf-8"))
    require(completion["status"] == "COMPLETE_DEVELOPMENT_OOF" and completion["rows"] == 1135, "incomplete coverage")
    require(completion["analysis_config_sha256"] == file_hash(config_path()), "completion config drift")
    require(completion["code_commit"] == committed_freeze(require_clean=False), "execution code commit drift")
    require(completion["oof_preflight_sha256"] == file_hash(PREFLIGHT / "oof_preflight_v1.json"), "execution preflight drift")
    verify_hashes(OUTPUT, completion["output_sha256"])
    verify_hashes(evidence_root(), completion["readiness_evidence_sha256"])
    metadata = json.loads((OUTPUT / RUN_METADATA_NAME).read_text())
    require(metadata["code_commit"] == completion["code_commit"] and metadata["packages"] == environment()["packages"] and
            metadata["manifest_sha256"] == file_hash(ROOT / MANIFEST_PATH) and metadata["fold_sha256"] == FOLD_SHA256 and
            metadata["upstream_revision"] == REVISION and metadata["seed"] == 1701 and metadata["device"] == "cpu", "run provenance drift")
    verify_hashes(OUTPUT, metadata["output_sha256"])
    rows, _ = selected_rows()
    records = read_predictions()
    validate_predictions(records, rows)
    validate_schema(records)
    fold_payload = json.loads((OUTPUT / "dm_b_v1_recipe_fold_metrics.json").read_text(encoding="utf-8"))
    reports = fold_payload["folds"]
    require([r["fold"] for r in reports] == list(range(5)), "fold report coverage drift")
    analysis, recipe, _ = checked_config()
    for report in reports:
        fold = report["fold"]
        train = [r for r in rows if int(r["outer_fold"]) != fold]
        held = [r for r in rows if int(r["outer_fold"]) == fold]
        require(report["train_membership_sha256"] == digest_ids(train) and report["held_out_membership_sha256"] == digest_ids(held), "fold membership proof drift")
        require(report["recipe"] == recipe.to_dict() and report["identity_leakage"] == report["lineage_leakage"] == 0, "fold recipe/leakage drift")
        require(report["metrics"] == probability_metrics([r["label"] for r in records if r["fold"] == fold],
                                                         [r["raw_score"] for r in records if r["fold"] == fold]), "per-fold metric drift")
    require(len({r["initial_parameters_sha256"] for r in reports}) == 1, "fold initializer mismatch")
    for name, product in analysis_products(records, reports).items():
        require(product == json.loads((OUTPUT / name).read_text(encoding="utf-8")), f"recomputed diagnostics differ: {name}")
    require((OUTPUT / "dm_b_v1_hard_examples.csv").read_bytes() == csv_bytes([r for r in records if r["error_type"] in ("FN", "FP")]), "hard IDs mismatch")
    print(json.dumps({"status": "PASS_COMPLETE_DEVELOPMENT_OOF", "rows": len(records), "leakage": 0,
                      "output_hash_checks": len(completion["output_sha256"])}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", required=True, choices=("prepare", "prepare-prerun", "smoke", "run", "check", "record-tests", "freeze-prerun", "check-prerun", "verify-prerun"))
    parser.add_argument("--test-xml", type=Path)
    args = parser.parse_args()
    require(Path.cwd().resolve() == ROOT, "execute from repository root")
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    if args.mode == "record-tests":
        require(args.test_xml is not None, "test XML required")
        record_tests(args.test_xml)
    else:
        {"prepare": prepare, "prepare-prerun": prepare_prerun, "smoke": synthetic_smoke,
         "run": run, "check": check, "freeze-prerun": freeze_prerun, "check-prerun": check_prerun,
         "verify-prerun": lambda: check_prerun(require_commit=False)}[args.mode]()


if __name__ == "__main__":
    main()
