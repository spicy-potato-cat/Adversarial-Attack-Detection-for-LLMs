"""TECH-STAT-008 diagnostic-only prepare/run/finalize/verify; no model scoring."""
import argparse
import ast
import csv
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import numpy as np
from jsonschema import validate

from detection_service.analysis import statistical_failure_atlas as atlas
from detection_service.scripts.common_mode_completion import preservation
from detection_service.analysis.common_mode import align, require
from detection_service.scripts.common_mode_development import (
    ROOT, GUARD_OUTPUT, INPUTS, MANIFEST, FOLDS, checked_hash, digest, read_json, read_csv,
    write_json, csv_output, check_hashes, markdown_table, test_receipt, canonical,
)
from detection_service.scripts.guard_development import selected_texts
from detection_service.analysis.statistical_failure_atlas import FEATURE_NAMES

START = "dc6dd3041643fb70ad5b128d32c246f8763a8044"
OUT = "artifacts/statistical_v2/failure_atlas"
COMMON = "artifacts/common_mode/development/completion_v3"
MANIFEST_PATH = "data_governance/manifests/development_partition_manifest_v1.csv"
FOLD_PATH = "artifacts/quality/quality_001/development_folds_v1.csv"
CACHE_PATH = "detection_service/outputs/stat004/token_evidence.npz"
STAT4_METADATA = "artifacts/statistical_v2/feature_ablation/resume_20000/run_metadata_v1.json"
REFERENCES = "artifacts/statistical_v2/scorer_comparison/fold_references_v1.json"
HYPOTHESES = "detection_service/configs/stat008_hypotheses.json"
CODE = ["detection_service/analysis/statistical_failure_atlas.py", "detection_service/scripts/statistical_failure_atlas.py",
        "detection_service/tests/test_statistical_failure_atlas.py"]
REPORTS = ["reviews/TECH_STAT_008_FAILURE_ATLAS_v1.md", "reviews/TECH_STAT_008_COMPLEMENTARITY_HYPOTHESES_v1.md",
           "reviews/TECH_STAT_008_TEST_REPORT_v1.md"]
DECISIONS = ["AUTHORIZE_DATA_C2_001", "AUTHORIZE_DATA_C2_001_WITH_LIMITED_HYPOTHESES",
             "RECONSIDER_STATISTICAL_COMPLEMENTARITY", "INSUFFICIENT_EVIDENCE"]
HYPOTHESIS_SCHEMA = {"type": "object", "required": ["hypotheses"], "properties": {"hypotheses": {"type": "array", "minItems": 3,
    "maxItems": 5, "items": {"type": "object", "required": ["id", "observed_phenotype", "supporting_evidence", "supporting_samples",
        "counter_evidence", "purely_statistical_mechanism", "general_representation_family", "required_new_data", "falsifiable_prediction",
        "falsification", "benign_FP_risk", "priority", "gate_eligible", "not_residual_memorization", "evidence_strength"], "properties": {
            "id": {"type": "string", "pattern": "^H-C2-0[1-5]$"}, "priority": {"enum": ["HIGH", "MEDIUM", "LOW"]},
            "supporting_samples": {"type": "integer", "minimum": 0}, "gate_eligible": {"type": "boolean"},
            "not_residual_memorization": {"const": True},
            **{key: {"type": "string", "minLength": 1} for key in ("observed_phenotype", "supporting_evidence", "counter_evidence",
                "purely_statistical_mechanism", "general_representation_family", "required_new_data", "falsifiable_prediction", "falsification", "benign_FP_risk", "evidence_strength")}}}}}}
GATE_SCHEMA = {"type": "object", "required": ["recommendation", "eligible_hypotheses", "DATA_C2_started", "cycle2_consumed", "rationale"],
    "properties": {"recommendation": {"enum": DECISIONS}, "eligible_hypotheses": {"type": "array", "items": {"type": "string"}, "uniqueItems": True},
                   "DATA_C2_started": {"const": False}, "cycle2_consumed": {"const": False}, "rationale": {"type": "string", "minLength": 1}}}


def accepted(root, name):
    original = subprocess.check_output(["git", "show", START + ":" + name], cwd=root)
    return checked_hash(root / name, hashlib.sha256(original).hexdigest())


def inputs(root=ROOT):
    require(subprocess.run(["git", "merge-base", "--is-ancestor", START, "HEAD"], cwd=root, capture_output=True).returncode == 0,
            "accepted COMMON-003 commit not ancestor")
    names = [COMMON + "/common_mode_manifest_v1.json", COMMON + "/full_analysis_v1.json", FOLD_PATH,
             STAT4_METADATA, REFERENCES, "artifacts/statistical_v2/oof/ds_v1_recipe_oof_predictions.csv",
             "artifacts/semantic_v2/oof/dm_b_v1_persistent_fn_3pct_v1.csv", *INPUTS.values(),
             GUARD_OUTPUT + "/dg_v1_base_train_predictions.csv", GUARD_OUTPUT + "/dg_v1_integrity.json",
             "detection_service/analysis/statistical_feature_ablation.py", "detection_service/scripts/calibrate_semantic_baseline.py"]
    hashes = {name: accepted(root, name) for name in sorted(set(names))}
    hashes[MANIFEST_PATH] = checked_hash(root / MANIFEST_PATH, MANIFEST)
    checked_hash(root / FOLD_PATH, FOLDS)
    core = read_json(root / COMMON / "common_mode_manifest_v1.json")
    hashes.update(check_hashes(root, COMMON, core["output_sha256"]))
    hashes.update(check_hashes(root, "", core["report_sha256"]))
    hashes.update(check_hashes(root, "", core["code_sha256"]))
    hashes.update(check_hashes(root, "", core["input_sha256"]))
    hashes[CACHE_PATH] = checked_hash(root / CACHE_PATH, read_json(root / STAT4_METADATA)["token_cache_sha256"])
    return hashes


def payload_gate(root, allowed):
    dataset, protected = (root / "Dataset").resolve(), (root / "PHASE-3").resolve()
    cache = (root / "detection_service/.model-cache").resolve()
    permitted = {(root / name).resolve() for name in allowed}
    def audit(event, args):
        if event != "open" or not isinstance(args[0], (str, bytes, os.PathLike)):
            return
        path = Path(os.fsdecode(args[0])).resolve()
        require(not path.is_relative_to(protected), "protected forensic payload refused")
        require(not path.is_relative_to(cache) and path.suffix not in {".safetensors", ".joblib", ".pt", ".pth", ".ckpt", ".onnx"}, "model weights refused in diagnostic analysis")
        if path.is_relative_to(dataset):
            require(path in permitted, "unapproved raw payload refused")
            require(not isinstance(args[1], str) or not any(c in args[1] for c in "wax+"), "raw payload write refused")
            require(not args[2] & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND), "raw write flags refused")
    sys.addaudithook(audit)


def compute(root=ROOT):
    hashes = inputs(root)
    fixture = {r["sample_id"]: r for r in read_csv(root / FOLD_PATH)}
    aligned = align({key: canonical(read_csv(root / name), key, fixture) for key, name in
                     {**INPUTS, "D_G_v1": GUARD_OUTPUT + "/dg_v1_base_train_predictions.csv"}.items()})
    accepted_analysis = read_json(root / COMMON / "full_analysis_v1.json")
    primary = next(b for b in accepted_analysis["budgets"] if b["budget"] == .03)
    keymap = {"DS": "D_S_B2_LR", "DMB": "D_M-B_v1", "DG": "D_G_v1"}
    thresholds = {key: next(r["threshold"] for r in primary["individual"] if r["detector"] == detector) for key, detector in keymap.items()}
    detectors = {key: {r["sample_id"]: r for r in aligned[detector]} for key, detector in keymap.items()}
    base = [r for r in read_csv(root / MANIFEST_PATH) if r["partition"] == "BASE_TRAIN"]
    require(len(base) == 1135 and len({r["record_id"] for r in base}) == 1135, "BASE_TRAIN selection mismatch")
    lookup = {r["record_id"]: r for r in base}
    folds = {r["sample_id"]: r for r in read_csv(root / FOLD_PATH)}
    prior = read_csv(root / "artifacts/statistical_v2/oof/ds_v1_recipe_oof_predictions.csv")
    sem = {r["sample_id"]: r for r in read_csv(root / INPUTS["D_M-B_v1"])}
    guard = {r["sample_id"]: r for r in read_csv(root / GUARD_OUTPUT / "dg_v1_base_train_predictions.csv")}
    require(set(lookup) == set(folds) == set(sem) == set(guard) == {r["sample_id"] for r in prior}, "source/cached metadata identity mismatch")
    metadata = []
    for r in prior:
        sid = r["sample_id"]
        row, f = lookup[sid], folds[sid]
        require(row["canonical_label"] == f["label"] == r["label"] and row["lineage_group_id"] == f["lineage_group"]
                and r["source_name"] == row["source_dataset"] == f["source_name"] and r["fold"] == f["outer_fold"], "manifest/OOF metadata disagreement")
        metadata.append({"sample_id": sid, "partition": "BASE_TRAIN", "label": r["label"], "source": row["source_dataset"],
            "attack_family": row["attack_family"] or "UNKNOWN", "provenance_status": row["provenance_status"], "lineage_group": f["lineage_group"],
            "fold": int(f["outer_fold"]), "source_dataset_id": row["source_dataset_id"], "source_revision": row["source_revision"],
            "record_locator": row["canonical_text_reference"], "rights_status": row["rights_status"], "label_confidence": row["label_confidence"],
            "DS_truncated": r["truncated"] == "True", "DS_tokens_excluded": int(r["tokens_excluded"]), "DS_input_tokens": int(r["input_tokens"]),
            "DMB_truncated": sem[sid]["truncated"] == "True", "DMB_tokens_excluded": int(sem[sid]["tokens_excluded"]), "DMB_input_tokens": int(sem[sid]["input_tokens"]),
            "DG_truncated": guard[sid]["truncated"] == "True", "DG_tokens_excluded": int(guard[sid]["tokens_excluded"]), "DG_input_tokens": int(guard[sid]["input_tokens"])})
    reference_rows = read_json(root / REFERENCES)
    references = {int(r["fold"]): r for r in reference_rows}
    require(set(references) == set(range(5)), "fold reference inventory")
    for fold, reference in references.items():
        require(set(reference["fit_training_ids"]) == {r["sample_id"] for r in metadata if r["fold"] != fold}, "held-out reference leakage")
        require(set(reference["benign_ids"]) == {r["sample_id"] for r in metadata if r["fold"] != fold and r["label"] == "0"}, "benign reference membership drift")
    cached = {}
    with np.load(root / CACHE_PATH, allow_pickle=False) as archive:
        require(archive["ids"].tolist() == [r["sample_id"] for r in prior], "token cache ordered identity mismatch")
        offsets, tokens = archive["offsets"], archive["surprisals"]
        require(len(offsets) == 1136 and offsets[0] == 0 and offsets[-1] == len(tokens) and (np.diff(offsets) > 0).all(), "cache offsets")
        for i, r in enumerate(prior):
            require(int(archive["input_tokens"][i]) == int(r["input_tokens"]), "cached length disagreement")
            cached[r["sample_id"]] = {"surprisals": tokens[offsets[i]:offsets[i + 1]].copy(),
                "input_tokens": int(archive["input_tokens"][i]), "tokens_analyzed": int(offsets[i + 1] - offsets[i]),
                "v1_features": [float(r[name]) for name in FEATURE_NAMES]}
    sources = read_json(root / "artifacts/statistical_v2/oof/completion_v1.json")["source_artifact_sha256"]
    module = ast.parse((root / "detection_service/scripts/calibrate_semantic_baseline.py").read_text(encoding="utf-8"))
    source_map = next(ast.literal_eval(node.value) for node in module.body if isinstance(node, ast.Assign)
                      and any(isinstance(t, ast.Name) and t.id == "SOURCE_FILES" for t in node.targets))
    payload_gate(root, sources)
    ordered_base = [lookup[r["sample_id"]] for r in metadata]
    texts = selected_texts(root, ordered_base, source_map, sources)
    diagnostics_by_id = {}
    for meta, text, old in zip(metadata, texts, prior, strict=True):
        sid = meta["sample_id"]
        diagnostics_by_id[sid] = atlas.diagnostics(cached[sid], text, references[meta["fold"]])
        require(diagnostics_by_id[sid]["character_count"] == int(old["character_length"]), "original character count disagreement")
    del texts
    rows = atlas.atlas_rows(metadata, cached, diagnostics_by_id, detectors, thresholds)
    sets = atlas.freeze_sets(rows)
    require(all(not r["DMB_prediction_3pct"] and not r["DG_prediction_3pct"] for r in rows if r["DMB_FN_3PCT"]), "residual guard mismatch")
    short = [r for r in rows if r["SHORT_ATTACKS"]]
    long = [r for r in rows if r["LONG_BENIGN"]]
    require([sum(r[key + "_prediction_3pct"] for r in short) for key in keymap] == [0, 26, 7], "short catches drift")
    require([sum(r[key + "_prediction_3pct"] for r in long) for key in keymap] == [12, 3, 0], "long FP drift")
    require("torch" not in sys.modules and "transformers" not in sys.modules, "model runtime imported in atlas")
    products = atlas.analyses(rows, diagnostics_by_id)
    return rows, diagnostics_by_id, sets, products, hashes, thresholds


def prepare(root=ROOT):
    out = root / OUT
    require(not out.exists(), "atlas already exists; do not overwrite")
    hashes = inputs(root)
    out.mkdir(parents=True)
    write_json(out / "analysis_protocol_v1.json", atlas.protocol())
    write_json(out / "preflight_v1.json", {"status": "PREDECLARED_NOT_RUN", "accepted_start_commit": START,
        "input_sha256": hashes, "protocol_sha256": digest(out / "analysis_protocol_v1.json"),
        "runtime": {"python": sys.version.split()[0], "numpy": np.__version__}, "model_loaded": False})
    print(json.dumps({"status": "PREDECLARED_NOT_RUN", "input_hash_checks": len(hashes)}))


def run(root=ROOT):
    out = root / OUT
    preflight = read_json(out / "preflight_v1.json")
    checked_hash(out / "analysis_protocol_v1.json", preflight["protocol_sha256"])
    require(read_json(out / "analysis_protocol_v1.json") == atlas.protocol(), "predeclared analysis protocol changed")
    check_hashes(root, "", preflight["input_sha256"])
    require(not (out / "run_metadata_v1.json").exists(), "analysis already complete; verify instead")
    rows, diagnostics_by_id, sets, products, hashes, thresholds = compute(root)
    csv_output(out / "sample_failure_atlas_v1.csv", rows)
    csv_output(out / "statistical_diagnostics_v1.csv", [{"sample_id": sid, **diagnostics_by_id[sid]} for sid in sorted(diagnostics_by_id)])
    write_json(out / "failure_set_manifest_v1.json", {"operating_points": thresholds, "sets": sets, "manifest_sha256": MANIFEST,
        "fold_sha256": FOLDS, "token_length_basis": "Existing D_S reference-LM tokens, including first unscored token"})
    for name, payload in products.items():
        write_json(out / name, payload)
    write_json(out / "run_metadata_v1.json", {"status": "DIAGNOSTICS_COMPLETE_AWAITING_HYPOTHESIS_GATE", "accepted_start_commit": START,
        "execution_HEAD": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(),
        "code_sha256": {name: digest(root / name) for name in CODE}, "input_sha256": hashes,
        "protocol_sha256": preflight["protocol_sha256"], "rows": len(rows), "positive": 183, "negative": 952,
        "completed_utc": datetime.now(timezone.utc).isoformat(), "governance": atlas.protocol()["governance"],
        "output_sha256": {p.name: digest(p) for p in out.iterdir() if p.is_file()}, "raw_prompt_text_saved": False,
        "reference_and_model_fits": 0, "new_model_inference": 0, "thresholds_copied_from_accepted_evidence": True})
    print(json.dumps({"status": "DIAGNOSTICS_COMPLETE", "sets": {k: v["count"] for k, v in sets.items()}}, indent=2))


def hypothesis_gate(payload):
    validate(payload, HYPOTHESIS_SCHEMA)
    require(len({h["id"] for h in payload["hypotheses"]}) == len(payload["hypotheses"]), "duplicate hypothesis ID")
    eligible = [h["id"] for h in payload["hypotheses"] if h["gate_eligible"]]
    require(all(h["priority"] in {"HIGH", "MEDIUM"} and h["supporting_samples"] > 4 for h in payload["hypotheses"] if h["gate_eligible"]), "residual-only/low-priority hypothesis cannot authorize C2")
    recommendation = "AUTHORIZE_DATA_C2_001_WITH_LIMITED_HYPOTHESES" if eligible else "INSUFFICIENT_EVIDENCE"
    gate = {"recommendation": recommendation, "eligible_hypotheses": eligible, "DATA_C2_started": False, "cycle2_consumed": False,
        "rationale": "Limited independent-data testing requirements only for evidence-backed statistical hypotheses; Commander approval still required." if eligible else
                     "No credible MEDIUM/HIGH statistical hypothesis passed the diagnostic gate; do not force Cycle 2.",
        "required_DMB_residual_denominator": "30-50+ independent attacks; prospectively report total screened and residual denominator without selection-driven headline metrics",
        "lineage_constraints": "New independent sources/base behaviours; no overlap with current fixture, four diagnostic residuals, calibration/validation or protected data; retain transformation/family/source groups",
        "data_requirements_only": True}
    validate(gate, GATE_SCHEMA)
    return gate


def finalize(root=ROOT):
    out = root / OUT
    require(not (out / "failure_atlas_manifest_v1.json").exists(), "atlas frozen; verify instead")
    run = read_json(out / "run_metadata_v1.json")
    check_hashes(root, "", run["input_sha256"])
    check_hashes(root, OUT, run["output_sha256"])
    check_hashes(root, "", run["code_sha256"])
    hypotheses = read_json(root / HYPOTHESES)
    gate = hypothesis_gate(hypotheses)
    tests = test_receipt(root / "tmp/stat008_tests.xml")
    require(tests["status"] == "PASS", "atlas tests required")
    preserved = preservation(root)
    shutil.copyfile(root / "tmp/stat008_tests.xml", out / "tests_v1.xml")
    tests = test_receipt(out / "tests_v1.xml")
    write_json(out / "test_evidence_v1.json", {"tests": tests, "preservation": preserved})
    write_json(out / "cycle2_hypotheses_v1.json", hypotheses)
    write_json(out / "cycle2_gate_decision_v1.json", gate)
    reports(root, hypotheses, gate, tests, preserved)
    write_json(out / "failure_atlas_manifest_v1.json", {"phase": "TECH-STAT-008", "status": "PASS", "recommendation": gate["recommendation"],
        "accepted_start_commit": START, "analysis_execution_HEAD": run["execution_HEAD"], "manifest_sha256": MANIFEST, "fold_sha256": FOLDS,
        "input_sha256": run["input_sha256"], "code_sha256": run["code_sha256"], "hypothesis_config_sha256": digest(root / HYPOTHESES),
        "output_sha256": {p.name: digest(p) for p in sorted(out.iterdir()) if p.is_file()},
        "report_sha256": {name: digest(root / name) for name in REPORTS}, "governance": atlas.protocol()["governance"]})
    print(json.dumps({"status": "PASS", "recommendation": gate["recommendation"], "eligible": gate["eligible_hypotheses"], "tests": tests}, indent=2))


def reports(root, hypotheses, gate, tests, preserved):
    out = root / OUT
    sets = read_json(out / "failure_set_manifest_v1.json")
    products = {name: read_json(out / name) for name in ("ds_fn_phenotypes_v1.json", "dm_b_residual_case_analysis_v1.json",
        "short_attack_analysis_v1.json", "long_benign_fp_analysis_v1.json", "cross_detector_error_patterns_v1.json", "score_margin_analysis_v1.json")}
    conclusions = hypotheses["diagnostic_conclusions"]
    table = hypotheses["primary_phenotype_table"]
    htext = "# TECH-STAT-008 Complementarity Hypotheses\n\nAll four hypotheses are untested on new independent data. No detector changes or DATA-C2 work authorized by this report.\n\n"
    for h in hypotheses["hypotheses"]:
        htext += f"## {h['id']} ({h['priority']})\n\n" + "\n\n".join(f"**{key.replace('_', ' ').title()}:** {value}" for key, value in h.items() if key != "id") + "\n\n"
    htext += "## Hard gate\n\n```json\n" + json.dumps(gate, indent=2) + "\n```\n\n## Proposed C2 tests and requirements, not a dataset plan\n\n" + hypotheses["proposed_C2_requirements"] + "\n"
    (root / REPORTS[1]).write_text(htext, encoding="utf-8", newline="\n")
    main = ("# TECH-STAT-008 Failure Atlas\n\nStatus: **PASS**. Diagnostic analysis only; Cycle 2 not consumed; DATA-C2 remains blocked.\n\n"
        f"Accepted evidence: `{START}`. Manifest `{MANIFEST}`; folds `{FOLDS}`. All 1,135 BASE_TRAIN rows (183 attacks, 952 benign). "
        "The primary points are copied from COMMON-003, not selected again. D_S and D_M-B use OOF predictions; D_G uses the single accepted frozen run. No full-BASE_TRAIN ds_v2 predictions.\n\n"
        "## Authoritative failure sets (observation)\n\n" + markdown_table([{"set": k, "count": v["count"]} for k, v in sets["sets"].items()], ["set", "count"]) + "\n\n"
        "## Primary phenotype table\n\n" + markdown_table(table, ["phenotype", "count", "DS_behavior", "DMB_behavior", "DG_behavior", "statistical_evidence", "hypothesis", "C2_action", "evidence_strength"]) + "\n\n"
        "## Statistical definitions and limitations\n\n"
        "Token surprisal values come from the hash-bound STAT-004 cache. Stored S0 training-fold benign references are reused without fitting; existing B1-B6 values are analysis-only. "
        "Means, population SD, unscaled MAD, linear quantiles, fixed top-k and frozen-reference exceedance/regions/windows are defined in analysis_protocol_v1.json. "
        "Reference token count includes the initial unscored token. Structural ratios and character entropy are analysis variables, not added D_S features. "
        "Strict controls match source/family/length region and exclude the same canonical lineage. Relaxed-length controls remain separate. Reused controls are reported with unique denominators, not independent replicates. "
        "No clustering or statistical significance tests. Existing length bins provide a transparent partition, not evidence of stable latent clusters.\n\n")
    main += "## D_M-B residuals (observation)\n\n" + conclusions["residual"] + "\n\n"
    cases = products["dm_b_residual_case_analysis_v1.json"]["cases"]
    case_table = [{"id": r["sample_id"], "source": r["source"], "family": r["attack_family"], "fold": r["fold"], "tokens": r["token_count"],
        "DS_score": r["DS_raw_score"], "DMB_score": r["DMB_raw_score"], "DG_score": r["DG_raw_score"], "DS_catch": r["DS_prediction_3pct"],
        "DMB_margin_region": r["DMB_margin_region"], "truncated": r["DMB_truncated"]} for r in cases]
    main += markdown_table(case_table, list(case_table[0])) + "\n\nAll four are diagnostic-only, never training examples, mining weights, feature rules or success criteria. Full numeric diagnostics and A/B/C controls are in the residual JSON.\n\n"
    phenotypes = products["ds_fn_phenotypes_v1.json"]["phenotypes"]
    main += "## D_S FN phenotypes (observation)\n\n" + markdown_table([{"phenotype": r["phenotype"], "count": r["count"], "fraction_of_83": r["fraction_of_83"],
        "DMB_catches": r["DMB_catches"], "DG_catches": r["DG_catches"], "common_misses": r["common_fn_count"],
        "median_nll": r["variables"]["surprisal_mean"]["median"], "median_q95_density": r["variables"]["existing_exceedance_q95_fraction"]["median"]} for r in phenotypes],
        ["phenotype", "count", "fraction_of_83", "DMB_catches", "DG_catches", "common_misses", "median_nll", "median_q95_density"]) + "\n\n"
    main += "## Short attacks (observation versus hypothesis)\n\n" + conclusions["short"] + "\n\n"
    main += "## Long-benign FPs (observation versus hypothesis)\n\n" + conclusions["long"] + "\n\n"
    patterns = products["cross_detector_error_patterns_v1.json"]["patterns"]
    main += "## Cross-detector error patterns (observation)\n\n" + markdown_table([{"pattern": r["pattern"], "attacks": r["count"], "small_group": r["small_group"]} for r in patterns],
        ["pattern", "attacks", "small_group"]) + "\n\nPatterns describe catches/misses, not a fusion policy.\n\n"
    main += ("## Margins (observation)\n\nRaw score minus fixed point and clipped diagnostic log-odds distances are retained. Near-boundary means |log-odds distance| <= ln(2). "
        "Near/far is not calibrated confidence. Raw 0.5 confidence labels from SEM-003 must not be confused with distances to the much lower descriptive 3% point.\n\n```json\n" + json.dumps(products["score_margin_analysis_v1.json"], indent=2) + "\n```\n\n")
    main += "## Hypotheses and proposed tests\n\n" + markdown_table([{"hypothesis": h["id"], "priority": h["priority"], "supporting_n": h["supporting_samples"], "gate_eligible": h["gate_eligible"],
        "prediction": h["falsifiable_prediction"]} for h in hypotheses["hypotheses"]], ["hypothesis", "priority", "supporting_n", "gate_eligible", "prediction"]) + "\n\n"
    main += "## Gate decision\n\n**" + gate["recommendation"] + "**\n\n" + gate["rationale"] + "\n\nDATA-C2-001 remains blocked pending Commander approval.\n\n"
    main += "## Proposed C2 requirements only\n\n" + hypotheses["proposed_C2_requirements"] + "\n\n"
    main += "## Governance and tests\n\n```json\n" + json.dumps({"governance": atlas.protocol()["governance"], "tests": tests, "preservation": preserved}, indent=2) + "\n```\n\nNo raw prompts are reproduced or saved. No protected/reserved prompt selection, model loads/fits, scorer changes, threshold selection, calibration, feature promotion or C2 dataset construction.\n"
    (root / REPORTS[0]).write_text(main, encoding="utf-8", newline="\n")
    (root / REPORTS[2]).write_text("# TECH-STAT-008 Test Report\n\n```json\n" + json.dumps({"tests": tests, "preservation": preserved}, indent=2)
        + "\n```\n\nTests cover exact accepted failure sets, alignment/refusals, frozen points, diagnostic determinism, margin boundaries, matched-control separation, hypothesis/gate schemas, raw access restrictions, and absence of model/reference fits.\n", encoding="utf-8", newline="\n")


def verify(root=ROOT):
    out = root / OUT
    manifest = read_json(out / "failure_atlas_manifest_v1.json")
    check_hashes(root, OUT, manifest["output_sha256"])
    check_hashes(root, "", manifest["code_sha256"])
    check_hashes(root, "", manifest["report_sha256"])
    checked_hash(root / HYPOTHESES, manifest["hypothesis_config_sha256"])
    rows, diagnostics_by_id, sets, products, hashes, points = compute(root)
    require(hashes == manifest["input_sha256"], "input inventory drift")
    require(read_json(out / "failure_set_manifest_v1.json")["sets"] == sets, "failure set reconstruction drift")
    for name, payload in products.items():
        require(read_json(out / name) == payload, "diagnostic JSON reconstruction drift: " + name)
    for name, records in (("sample_failure_atlas_v1.csv", rows), ("statistical_diagnostics_v1.csv", [{"sample_id": sid, **diagnostics_by_id[sid]} for sid in sorted(diagnostics_by_id)])):
        stored = read_csv(out / name)
        require(len(stored) == len(records) and all(s == {k: "" if v is None else str(v) for k, v in r.items()} for s, r in zip(stored, records, strict=True)), "diagnostic CSV reconstruction drift: " + name)
    require(hypothesis_gate(read_json(root / HYPOTHESES)) == read_json(out / "cycle2_gate_decision_v1.json"), "gate reconstruction drift")
    preservation(root)
    print(json.dumps({"status": "PASS_INDEPENDENT_RECONSTRUCTION", "rows": 1135, "input_hashes": len(hashes), "recommendation": manifest["recommendation"]}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    choice = parser.add_mutually_exclusive_group(required=True)
    for name in ("prepare", "run", "finalize", "verify"):
        choice.add_argument("--" + name, action="store_true")
    args = parser.parse_args()
    {"prepare": prepare, "run": run, "finalize": finalize, "verify": verify}[next(name for name in ("prepare", "run", "finalize", "verify") if getattr(args, name))]()
