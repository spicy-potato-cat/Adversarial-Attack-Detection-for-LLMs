"""Read frozen OOF CSVs; produce a development-only partial/full failure study.

Run: python -m detection_service.scripts.common_mode_development
No model imports, payload reads, training, threshold deployment or fusion.
"""
import argparse
import csv
import hashlib
from importlib.metadata import PackageNotFoundError, version
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import xml.etree.ElementTree as ET

from detection_service.analysis.common_mode import DIRECTION, align, analyze, require

ROOT = Path(__file__).resolve().parents[2]
BASE = "4d9d694bec959e082b8675f36a0b89488890837e"
MANIFEST = "9cdd5ecdd80f9ac3c8f05db63742721f4537ca2b64a2fe48f6c2b424b57483a6"
FOLDS = "19dc0153cc257cc2331782d6dd61b7bb9fb8cb0ed88d3e782b69d5ba05c4bb8d"
REVISION = "11614a155199674a0a95e6602d6ab0417b790ed0"
MODEL = "meta-llama/Llama-Prompt-Guard-2-22M"
STACKS = {"DEVELOPMENT_STACK_V1": ["D_S_v1", "D_M-B_v1", "D_G_v1"],
          "DEVELOPMENT_STACK_CANDIDATE": ["D_S_B2_LR", "D_M-B_v1", "D_G_v1"]}
COMPARISON = {"baseline": "D_S_v1", "candidate": "D_S_B2_LR", "others": ["D_M-B_v1", "D_G_v1"],
              "stack_names": ("DEVELOPMENT_STACK_V1", "DEVELOPMENT_STACK_CANDIDATE")}
INPUTS = {
    "D_S_v1": "artifacts/statistical_v2/oof/ds_v1_recipe_oof_predictions.csv",
    "D_S_B2_LR": "artifacts/statistical_v2/scorer_comparison/scorer_predictions_v1.csv",
    "D_M-B_v1": "artifacts/semantic_v2/oof/dm_b_v1_recipe_oof_predictions.csv",
}
OUTPUT = "artifacts/common_mode/development"
GUARD_OUTPUT = "artifacts/guard_v1/development"


def digest(path):
    """Hash bytes without parsing or opening any raw data records."""
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path):
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8", newline="\n")


def check_hashes(root, directory, expected):
    """Refuse drift in any authoritative artifact inventory."""
    return {str((Path(directory) / name).as_posix()): checked_hash(root / directory / name, value)
            for name, value in expected.items()}


def checked_hash(path, expected):
    require(path.is_file(), "missing required evidence: " + str(path))
    actual = digest(path)
    require(actual == expected, "hash mismatch: " + str(path))
    return actual


def provenance(root):
    """Verify committed evidence; missing local manifest is a live-data blocker."""
    evidence = {}
    quality = read_json(root / "artifacts/quality/quality_001/integrity_manifest_v1.json")
    unavailable = []
    for name, expected in quality["sha256"].items():
        if (root / name).is_file():
            evidence[name] = checked_hash(root / name, expected)
        else:
            unavailable.append({"path": name, "expected_sha256": expected})
    evidence["artifacts/quality/quality_001/development_folds_v1.csv"] = checked_hash(root / "artifacts/quality/quality_001/development_folds_v1.csv", FOLDS)
    stat = read_json(root / "artifacts/statistical_v2/oof/completion_v1.json")
    require(stat["reproducibility"]["manifest_sha256"] == MANIFEST and stat["reproducibility"]["fold_sha256"] == FOLDS, "STAT-003 provenance mismatch")
    evidence.update(check_hashes(root, "artifacts/statistical_v2/oof", stat["artifact_sha256"]))
    scorer = read_json(root / "artifacts/statistical_v2/scorer_comparison/run_metadata_v1.json")
    require(scorer["manifest_sha256"] == MANIFEST and scorer["fold_sha256"] == FOLDS, "STAT-005 provenance mismatch")
    evidence.update(check_hashes(root, "artifacts/statistical_v2/scorer_comparison", scorer["artifact_sha256"]))
    selected = read_json(root / "artifacts/statistical_v2/scorer_comparison/selected_scorer_v1.json")
    require(selected["selected_scorer"] == "S0" and selected["candidate_recipe"]["family"] == "LogisticRegression", "candidate selection drift")
    sem = read_json(root / "artifacts/semantic_v2/oof/acceptance_manifest_v1.json")
    require(sem["manifest_sha256"] == MANIFEST and sem["fold_sha256"] == FOLDS and sem["decision"] == "FREEZE_DM_B_V1", "SEM-003 provenance mismatch")
    evidence.update(check_hashes(root, "artifacts/semantic_v2/oof", sem["original_input_sha256"]))
    evidence.update(check_hashes(root, "artifacts/semantic_v2/oof", sem["acceptance_output_sha256"]))
    guard_integrity = read_json(root / "artifacts/models/dg_v1/integrity_manifest.json")
    evidence.update(check_hashes(root, "artifacts/models/dg_v1", guard_integrity))
    freeze = read_json(root / "artifacts/models/dg_v1/freeze_metadata.json")
    require(freeze["model_id"] == MODEL and freeze["revision"] == REVISION and freeze["tokenizer_revision"] == REVISION, "D_G freeze drift")
    # Bind every consumed inventory itself to the manifest as well.
    inventories = ["artifacts/quality/quality_001/integrity_manifest_v1.json", "artifacts/statistical_v2/oof/completion_v1.json",
                   "artifacts/statistical_v2/scorer_comparison/run_metadata_v1.json", "artifacts/semantic_v2/oof/acceptance_manifest_v1.json",
                   "artifacts/models/dg_v1/integrity_manifest.json"]
    evidence.update({name: digest(root / name) for name in inventories})
    return evidence, unavailable, stat["source_artifact_sha256"], freeze


def canonical(raw, key, fixture):
    """Adapt a named frozen CSV recipe, checking metadata before enrichment."""
    result = []
    for r in raw:
        if key == "D_S_B2_LR" and r["scorer"] != "S0":
            continue
        sid = r["sample_id"]
        require(sid in fixture, "extra sample ID")
        f = fixture[sid]
        require(r["partition"] == "BASE_TRAIN" and r["label"] == f["label"], "partition/label mismatch")
        require(r["lineage_group"] == f["lineage_group"] and int(r["fold"]) == int(f["outer_fold"]), "lineage/fold mismatch")
        if r.get("source_name"):
            require(r["source_name"] == f["source_name"], "source mismatch")
        expected = {"D_S_v1": ("statistical_perplexity", "ds_v1"), "D_S_B2_LR": ("statistical_perplexity", "B2_S0_LR_development_candidate"),
                    "D_M-B_v1": ("semantic_finetuned", "dm_b_v1"), "D_G_v1": ("guard_external", "dg_v1")}[key]
        if key == "D_S_B2_LR":
            require(r["score_kind"] == "uncalibrated_class1_probability", "unknown candidate score semantics")
        else:
            require((r["detector_id"], r["detector_version"]) == expected, "detector semantics mismatch")
        score = float(r["raw_score"])
        require(0 <= score <= 1, "invalid class1 probability")
        result.append({"sample_id": sid, "truth_label": int(r["label"]), "partition": "BASE_TRAIN",
                       "detector_id": expected[0], "detector_version": expected[1], "score": score,
                       "score_direction": DIRECTION, "source": f["source_name"], "lineage_group": f["lineage_group"],
                       "fold": int(f["outer_fold"]), "attack_family": None,
                       "metadata": {"source_provenance": "hash-verified QUALITY-001 fold CSV; S0 has no source column",
                                    "evidence_kind": "externally_frozen" if key == "D_G_v1" else "fold_local_OOF"}})
    require(len(result) == 1135, "incomplete selected prediction population")
    return result


def gates(root, unavailable, sources, freeze):
    """Check local availability without reading any raw prompt text."""
    missing_sources = [{"path": name, "expected_sha256": sha} for name, sha in sources.items() if not (root / name).is_file()]
    manifest_path = root / "data_governance/manifests/development_partition_manifest_v1.csv"
    manifest_available = manifest_path.is_file()
    if manifest_available:
        checked_hash(manifest_path, MANIFEST)
    snapshot = root / freeze["snapshot_path"]
    hub = Path(os.environ.get("HF_HUB_CACHE", str(Path(os.environ.get("HF_HOME", str(Path.home() / ".cache/huggingface"))) / "hub")))
    cached = hub / "models--meta-llama--Llama-Prompt-Guard-2-22M/snapshots" / REVISION
    snapshot_missing = [name for name in freeze["file_sha256"] if not (snapshot / name).is_file()]
    data_status = "AVAILABLE_NOT_SCORED" if manifest_available and not missing_sources else "BLOCKED_MISSING_AUTHORITATIVE_DEVELOPMENT_DATA"
    return {"status": data_status, "model_status": "BLOCKED_MISSING_PINNED_MODEL" if snapshot_missing else "AVAILABLE_NOT_LOADED",
            "model_id": MODEL, "revision": REVISION, "manifest_sha256": MANIFEST,
            "manifest_path": str(manifest_path), "manifest_available": manifest_available,
            "missing_source_files": missing_sources, "missing_quality_metadata": unavailable,
            "snapshot_path": str(snapshot), "missing_snapshot_files": snapshot_missing,
            "hf_cache_checked": str(cached), "hf_cache_present": cached.is_dir(),
            "hf_access": "NOT_LOGGED_IN (hf auth whoami checked locally before implementation)",
            "restore_data": "No repository-supported bootstrap found that reproduces the authoritative manifest. Restore the exact manifest and approved source files from the authoritative machine; verify the listed SHA-256 values. Do not reconstruct or download substitutes.",
            "authentication": "hf auth login; request/accept access in browser at https://huggingface.co/meta-llama/Llama-Prompt-Guard-2-22M if needed; hf auth whoami",
            "materialize_model_command": f'hf download {MODEL} --revision {REVISION} --local-dir "{snapshot}"',
            "model_verification": "Verify every downloaded file against artifacts/models/dg_v1/freeze_metadata.json file_sha256, then call existing load_frozen; do not rerun prepare_guard or overwrite the freeze.",
            "native_metrics": None, "fixed_fpr_metrics": None, "live_rows_scored": 0,
            "raw_prompt_text_saved": False}


def csv_output(path, rows):
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields or ["status"])
        writer.writeheader()
        writer.writerows(rows)


def markdown_table(rows, fields):
    def value(v):
        if v is None:
            return "UNMEASURED"
        return f"{v:.6f}" if isinstance(v, float) else str(v).replace("|", "/")
    return "| " + " | ".join(fields) + " |\n|" + "|".join("---" for _ in fields) + "|\n" + "\n".join("| " + " | ".join(value(r.get(k)) for k in fields) + " |" for r in rows) + "\n"


def test_receipt(path):
    """Bind test outcome to its XML without claiming missing tests passed."""
    if not path.is_file():
        return {"status": "NOT_RUN"}
    tree = ET.parse(path)
    cases = list(tree.iter("testcase"))
    return {"status": "PASS" if not list(tree.iter("failure")) and not list(tree.iter("error")) else "FAIL",
            "tests": len(cases), "failures": len(list(tree.iter("failure"))), "errors": len(list(tree.iter("error"))),
            "skipped": len(list(tree.iter("skipped"))), "path": str(path), "sha256": digest(path)}


def run(root=ROOT, repetitions=1000):
    """Generate verifiable evidence atomically after all alignment checks pass."""
    hashes, unavailable, sources, freeze = provenance(root)
    folds = read_csv(root / "artifacts/quality/quality_001/development_folds_v1.csv")
    require(len(folds) == len({r["sample_id"] for r in folds}) == 1135, "fixture membership mismatch")
    require(sum(r["label"] == "1" for r in folds) == 183 and sum(r["label"] == "0" for r in folds) == 952, "fixture class counts mismatch")
    require({r["outer_fold"] for r in folds} == set("01234") and all(r["partition"] == "BASE_TRAIN" for r in folds), "fixture folds/partition mismatch")
    fixture = {r["sample_id"]: r for r in folds}
    detectors = {key: canonical(read_csv(root / name), key, fixture) for key, name in INPUTS.items()}
    guard = gates(root, unavailable, sources, freeze)
    # Only accept a completed, integrity-bound future guard characterization.
    guard_file = root / GUARD_OUTPUT / "dg_v1_base_train_predictions.csv"
    if guard_file.exists():
        metadata = read_json(root / GUARD_OUTPUT / "dg_v1_run_metadata.json")
        require(metadata["model_id"] == MODEL and metadata["revision"] == REVISION and metadata["manifest_sha256"] == MANIFEST
                and metadata["fold_sha256"] == FOLDS and metadata["rows"] == 1135 and metadata["status"] == "COMPLETE", "D_G run provenance mismatch")
        integrity = read_json(root / GUARD_OUTPUT / "dg_v1_integrity.json")
        hashes.update(check_hashes(root, GUARD_OUTPUT, integrity["sha256"]))
        require("dg_v1_base_train_predictions.csv" in integrity["sha256"], "unbound D_G predictions")
        detectors["D_G_v1"] = canonical(read_csv(guard_file), "D_G_v1", fixture)
    result = analyze(detectors, STACKS, COMPARISON, repetitions=repetitions)
    # Check reconstructed operating points against the frozen reported results.
    for key, name in {"D_S_v1": "artifacts/statistical_v2/oof/ds_v1_recipe_oof_metrics.json", "D_M-B_v1": "artifacts/semantic_v2/oof/dm_b_v1_recipe_oof_metrics.json"}.items():
        reference = read_json(root / name)
        for index, budget in enumerate(result["budgets"]):
            actual = next(r for r in budget["individual"] if r["detector"] == key)
            expected = reference["recall_at_fixed_fpr"][index]
            require(actual["tp"] == expected["tp"] and actual["fp"] == expected["fp"], "frozen frontier reconstruction mismatch")
    status = "PASS" if "D_G_v1" in detectors else "PARTIAL_D_G_UNMEASURED"
    out = root / OUTPUT
    out.mkdir(parents=True, exist_ok=True)
    alignment = {"status": "PASS_AVAILABLE_OOF_ALIGNMENT", "aligned_samples": 1135, "positive": 183, "negative": 952,
                 "detectors": sorted(detectors), "missing_detectors": sorted({"D_G_v1"} - detectors.keys()),
                 "fold_sha256": FOLDS, "expected_manifest_sha256": MANIFEST,
                 "manifest_verified_locally": guard["manifest_available"], "population_authority": "hash-verified frozen fold membership",
                 "canonical_lineage_leakage": 0, "identity_leakage": 0,
                 "sample_id_order_sha256": hashlib.sha256("\n".join(sorted(fixture)).encode()).hexdigest(),
                 "source_enrichment": "S0 source copied only from matched authoritative fold row; label/lineage/fold checked first",
                 "attack_family": "UNAVAILABLE_IN_CONSUMED_PREDICTION_AND_FOLD_METADATA; not inferred",
                 "input_sha256": hashes}
    write_json(out / "detector_alignment_v1.json", alignment)
    for filename, category in (("individual_metrics", "individual"), ("pairwise_failure_metrics", "pairwise"),
                               ("stack_failure_metrics", "stacks"), ("unique_catches", "unique"),
                               ("ds_improvement_effect", "effect"), ("grouped_metrics", "grouped"), ("bootstrap_intervals", "bootstrap")):
        data = [{"budget": b["budget"], "metrics": b[category]} for b in result["budgets"]]
        write_json(out / (filename + "_v1.json"), {"scope": result["scope"], "status": status, "results": data})
        if category not in ("grouped", "bootstrap"):
            csv_output(out / (filename + "_v1.csv"), [{"budget": b["budget"], **r} for b in result["budgets"] for r in b[category]])
    environment = {"python": platform.python_version(), "platform": platform.platform(), "device": "CPU; no model execution",
                   "packages": {}, "runtime": sys.executable, "model_dependencies_installed": False}
    for package in ("pytest", "pydantic", "torch", "transformers", "scikit-learn", "tokenizers"):
        try:
            environment["packages"][package] = version(package)
        except PackageNotFoundError:
            environment["packages"][package] = "NOT_INSTALLED_IN_ANALYSIS_ENVIRONMENT"
    tests = {"existing_lightweight": test_receipt(root / "tmp/common_prerun_tests.xml"),
             "common_mode": test_receipt(root / "tmp/common_mode_tests.xml")}
    write_json(out / "test_evidence_v1.json", tests)
    if "D_G_v1" not in detectors:
        guard_dir = root / GUARD_OUTPUT
        guard_dir.mkdir(parents=True, exist_ok=True)
        write_json(guard_dir / "dg_v1_availability_v1.json", guard)
    reviews = root / "reviews"
    reviews.mkdir(exist_ok=True)
    intro = ("# TECH-COMMON-001 DEVELOPMENT COMMON-MODE CHARACTERIZATION\n\n"
             f"Status: **{status}**. Not final/protected research performance.\n\n"
             "1,135 aligned BASE_TRAIN samples: 183 positive, 952 negative. D_S v1, B2+LR and D_M-B v1 are frozen OOF predictions; each sample was held out from its scoring model. Same five QUALITY-001 folds, zero canonical-lineage leakage. D_G is externally frozen without project BASE_TRAIN fitting, but its scores are unavailable here.\n\n"
             "Whole tied score blocks, inclusive >=, maximal recall under each budget, then minimum FPR, then highest threshold. Every detector selects its own descriptive point; no deployment threshold is frozen. FN Jaccard is zero for empty unions; conditional recovery is null for empty denominators. Counts and rates refer to attacks; unique-catch rates use all 183 attacks. Independence is an algebraic reference, not an asserted model of detector independence.\n\n"
             "The candidate is DEVELOPMENT_STACK_CANDIDATE, not final research_stack_v2. Three-detector stack JFN and unique catches remain UNMEASURED; pairwise D_S/D_M-B evidence does not answer guard complementarity. Source/fold breakdowns apply unchanged pooled thresholds. Attack family is unavailable in consumed metadata and was not manufactured. Source comparisons are not frozen R1 experiments.\n\n")
    tables = []
    for b in result["budgets"]:
        tables.append(f'## At {b["budget"]:.0%} FPR budget\n\nTABLE A — individual (rates are fractions).\n\n' + markdown_table(b["individual"], ["detector", "fpr", "fnr", "recall", "tp", "fp", "fn", "tn"]))
        tables.append("\nTABLE B — pairwise (D_S-v1 versus B2 is representation transition context).\n\n" + markdown_table(b["pairwise"], ["left", "right", "fnr_i", "fnr_j", "jfn_count", "jfn", "independence_reference", "ejf", "fn_jaccard"]))
        tables.append("\nTABLE C — primary stack.\n\n" + markdown_table(b["stacks"], ["stack", "all_detector_jfn", "all_detector_fn_count"]))
        tables.append("\nTABLE D — unique catches.\n\n" + markdown_table(b["unique"], ["stack", "detector", "unique_catch_count", "unique_catch_rate", "recovery_given_others_miss"]))
        tables.append("\nTABLE E — candidate minus v1.\n\n" + markdown_table(b["effect"], ["metric", "other", "baseline", "candidate", "delta"]))
    uncertainty = ("\n## Uncertainty\n\n1,000 paired canonical attack-lineage percentile bootstrap replicates, seed 1701; same attacks in each detector/candidate comparison. Fixed pooled points are held unchanged. Conditional development uncertainty excludes model refitting, threshold selection, development selection and dependence from overlapping training folds. The canonical lineage minimum does not resolve full upstream semantic dependence. Small-count deltas must not be treated as robust population gains. Exact intervals are in bootstrap_intervals_v1.json.\n\n"
                   "## Isolation\n\nDetector training, CALIBRATION payloads, VALIDATION payloads, protected payloads, E1-E10, R2/R3 generation and verifier/router work: **NO**. No fusion or ensemble decision policy implemented. Existing detector source and evidence unchanged.\n")
    (reviews / "TECH_COMMON_001_DEVELOPMENT_COMMON_MODE_v1.md").write_text(intro + "\n".join(tables) + uncertainty, encoding="utf-8", newline="\n")
    effects = "# TECH-COMMON-001 D_S Improvement Effect\n\nDEVELOPMENT COMMON-MODE CHARACTERIZATION. Candidate-minus-baseline deltas.\n\n"
    for b in result["budgets"]:
        effects += f'## {b["budget"]:.0%} FPR budget\n\n' + markdown_table(b["effect"], ["metric", "other", "baseline", "candidate", "delta"]) + "\n"
    effects += "Improved standalone D_S discrimination does not by itself establish preserved statistical complementarity. Measured D_S/D_M-B joint failures and overlap are descriptive evidence only. D_S/D_G JFN/EJF/Jaccard, all-detector JFN and D_S exclusive catches cannot be concluded without D_G. No causal or final-performance claim is supported. NOT READY FOR FULL REPORT RESULTS INTEGRATION; partial two-detector development tables may be used only with this limitation.\n"
    (reviews / "TECH_COMMON_001_D_S_IMPROVEMENT_EFFECT_v1.md").write_text(effects, encoding="utf-8", newline="\n")
    (reviews / "TECH_COMMON_001_TEST_REPORT_v1.md").write_text("# TECH-COMMON-001 Test Report\n\n" + json.dumps(tests, indent=2) + "\n\nSynthetic analytic truth tables cover all requested metrics, alignment refusals, deterministic fixed-FPR ties and 1/3/5% budgets, lineage leakage, paired deltas, bootstrap repeatability and model-free imports. Full ML/protected test suites were not run. Frozen frontier counts reconstruct for both original OOF detectors. Every available input-inventory hash checked before analysis. Missing QUALITY-001 metadata is explicitly recorded, not counted as passing.\n", encoding="utf-8", newline="\n")
    if "D_G_v1" not in detectors:
        guard_report = "# TECH-GUARD-002 Development Characterization\n\nStatus: **BLOCKED_MISSING_AUTHORITATIVE_DEVELOPMENT_DATA**; pinned model also absent; HF CLI reports Not logged in.\n\nDEVELOPMENT characterization only; zero rows scored. All native/ranking/frontier/fold metrics: UNMEASURED. No alternate corpus/model used.\n\n```json\n" + json.dumps(guard, indent=2) + "\n```\n\nDo not recreate the missing manifest or change frozen D_G. Restore exact inputs, verify hashes, authenticate locally and materialize only the pinned snapshot. The existing prepare_guard command refuses to overwrite this already committed freeze and must not be rerun. No repository-supported exact data restoration command was found.\n"
        (reviews / "TECH_GUARD_002_DEVELOPMENT_CHARACTERIZATION_v1.md").write_text(guard_report, encoding="utf-8", newline="\n")
        (reviews / "TECH_GUARD_002_TEST_REPORT_v1.md").write_text("# TECH-GUARD-002 Test Report\n\nLive characterization: BLOCKED, not passed. Committed D_G freeze configuration/integrity hashes verified. Existing guard code unchanged. No model loaded or scored. Model-dependent guard regression tests not run in this minimal environment.\n", encoding="utf-8", newline="\n")
    files = sorted(p for p in out.iterdir() if p.is_file() and p.name != "common_mode_manifest_v1.json")
    metadata = {"scope": result["scope"], "status": status, "branch": subprocess.check_output(["git", "branch", "--show-current"], cwd=root, text=True).strip(),
                "base_commit": BASE, "execution_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(),
                "environment": environment, "aligned_samples": 1135, "positive": 183, "negative": 952,
                "expected_manifest_sha256": MANIFEST, "fold_sha256": FOLDS, "seed": 1701, "bootstrap_repetitions": repetitions,
                "input_sha256": hashes, "output_sha256": {p.name: digest(p) for p in files},
                "code_sha256": {name: digest(root / name) for name in ("detection_service/analysis/common_mode.py", "detection_service/scripts/common_mode_development.py", "detection_service/tests/test_common_mode.py")},
                "report_sha256": {p.relative_to(root).as_posix(): digest(p) for p in reviews.glob("TECH_COMMON_001_*v1.md")},
                "missing_quality_metadata": unavailable, "guard_gate": guard,
                "isolation": {k: False for k in ("detector_training", "calibration_payload", "validation_payload", "protected_payload", "E1_E10", "verifier_router", "fusion_policy")},
                "recommendation": "READY" if status == "PASS" else "NOT_READY_FOR_FULL_REPORT_RESULTS_INTEGRATION"}
    write_json(out / "common_mode_manifest_v1.json", metadata)
    print(json.dumps({"status": status, "aligned_samples": 1135, "input_hash_checks": len(hashes), "budgets": [{"budget": b["budget"], "individual": b["individual"], "effect": b["effect"]} for b in result["budgets"]]}, indent=2))
    return metadata


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bootstrap-repetitions", type=int, default=1000)
    args = parser.parse_args()
    run(repetitions=args.bootstrap_repetitions)
