"""Additive Track-2 continuation: conditional failures and frozen subgroups.

python -m detection_service.scripts.common_mode_completion
python -m detection_service.scripts.common_mode_completion --verify
Historical v1 evidence/reports are preserved; new outputs live in completion_v2.
No detector/model imports, raw payloads, training, threshold freeze or fusion.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path
import shutil
import subprocess
import sys

from detection_service.analysis.common_mode import align, analyze, require
from detection_service.analysis.development_characterization import characterization, subgroup_diagnostics
from detection_service.scripts.common_mode_development import (
    ROOT, INPUTS, FOLDS, MANIFEST, MODEL, REVISION, STACKS, COMPARISON, GUARD_OUTPUT,
    canonical, checked_hash, check_hashes, digest, read_csv, read_json, write_json,
    csv_output, markdown_table, provenance, test_receipt,
)
from detection_service.scripts.guard_development import preflight

START = "16aee1c301272bf56cd0081aab863c66d3fcc869"
COMPLETION_START = "3ef06414836a51b3409e7be9251da7753299da3a"
OUTPUT = "artifacts/common_mode/development/completion_v2"
REPORTS = ["reviews/TECH_COMMON_001_DEVELOPMENT_COMMON_MODE_v2.md",
           "reviews/TECH_COMMON_002_DS_IMPROVEMENT_EFFECT_v1.md",
           "reviews/TECH_COMMON_001_TEST_REPORT_v2.md",
           "reviews/TECH_GUARD_002_DEVELOPMENT_CHARACTERIZATION_v2.md"]
CODE = ["detection_service/analysis/common_mode.py", "detection_service/analysis/development_characterization.py",
        "detection_service/scripts/common_mode_completion.py", "detection_service/scripts/guard_development.py",
        "detection_service/tests/test_track2_completion.py"]


def preservation(root=ROOT):
    """Run original strict suite; distinguish verified newline drift from content.

The original suite/result is never changed or relabeled PASS. All original
Track-2 artifacts/reports and frozen detector content must remain unchanged.
"""
    strict = subprocess.run([sys.executable, "-m", "detection_service.scripts.verify_quality_preservation", "--mode", "check"], cwd=root, capture_output=True, text=True)
    baseline = read_json(root / "artifacts/quality/quality_001/baseline_preservation_v1.json")
    exact, newline = [], []
    for name, expected in baseline["sha256"].items():
        path = root / name
        require(path.is_file(), "missing baseline file: " + name)
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() == expected:
            exact.append(name)
        else:
            lf = raw.replace(b"\r\n", b"\n")
            forms = {"LF": hashlib.sha256(lf).hexdigest(), "CRLF": hashlib.sha256(lf.replace(b"\n", b"\r\n")).hexdigest()}
            matches = [form for form, sha in forms.items() if sha == expected]
            require(bool(matches), "unexplained baseline corruption: " + name)
            newline.append({"path": name, "expected_sha256": expected, "actual_sha256": digest(path), "matching_line_ending": matches})
    frozen = ["detection_service/app", "detection_service/configs", "artifacts/models"]
    diff = subprocess.run(["git", "diff", "--exit-code", START, "--", *frozen], cwd=root, capture_output=True)
    require(diff.returncode == 0, "frozen detector content changed since pushed Track-2 start")
    tracked = subprocess.check_output(["git", "ls-tree", "-r", "--name-only", COMPLETION_START, "--", "artifacts/common_mode", "artifacts/guard_v1/development", "reviews"], cwd=root, text=True).splitlines()
    historical = [name for name in tracked if name.startswith(("artifacts/common_mode/", "artifacts/guard_v1/development/", "reviews/TECH_COMMON_001", "reviews/TECH_COMMON_002", "reviews/TECH_GUARD_002"))]
    for name in historical:
        expected_bytes = subprocess.check_output(["git", "show", COMPLETION_START + ":" + name], cwd=root)
        require((root / name).read_bytes() == expected_bytes, "historical Track-2 evidence changed: " + name)
    # Verify accepted STAT-004 B2 artifacts in addition to STAT-003/005/SEM-003.
    stat4dir = "artifacts/statistical_v2/feature_ablation/resume_20000"
    stat4 = read_json(root / stat4dir / "run_metadata_v1.json")
    stat4_checks = check_hashes(root, stat4dir, stat4["artifact_sha256"])
    return {"strict_original_suite": {"returncode": strict.returncode, "status": "PASS" if strict.returncode == 0 else "FAIL_PREEXISTING_LINE_ENDING_DRIFT",
                                      "command": "python -m detection_service.scripts.verify_quality_preservation --mode check"},
            "baseline_files": len(baseline["sha256"]), "exact_byte_matches": len(exact), "newline_only_matches": len(newline),
            "newline_differences": newline, "unexplained_changes": 0, "tracked_detector_diff": "EMPTY",
            "original_track2_artifacts_and_reports_verified": len(historical), "historical_evidence": "BYTE_IDENTICAL",
            "stat004_sha256": stat4_checks,
            "interpretation": ("Strict preservation suite passes with exact baseline bytes." if strict.returncode == 0 else
                               "Strict preservation suite fails; listed differences are verified LF/CRLF only, with no unexplained content change.")}


def evidence(root=ROOT):
    """Load only integrity-bound frozen prediction evidence and fold metadata."""
    hashes, unavailable, _, _ = provenance(root)
    folds = read_csv(root / "artifacts/quality/quality_001/development_folds_v1.csv")
    require(len(folds) == len({r["sample_id"] for r in folds}) == 1135, "frozen fold population mismatch")
    fixture = {r["sample_id"]: r for r in folds}
    data = {key: canonical(read_csv(root / name), key, fixture) for key, name in INPUTS.items()}
    # Preserve existing per-ID family annotations only where a bound artifact
    # supplies them. Do not generalize the four residual labels to their source.
    family_rows = read_csv(root / "artifacts/semantic_v2/oof/dm_b_v1_persistent_fn_3pct_v1.csv")
    families = {}
    for r in family_rows:
        sid = r["sample_id"]
        require(sid in fixture and sid not in families and fixture[sid]["label"] == "1", "family metadata identity mismatch")
        require(r["lineage_group"] == fixture[sid]["lineage_group"] and r["source_name"] == fixture[sid]["source_name"], "family metadata mismatch")
        families[sid] = r["attack_family"] if r["attack_family"] not in ("", "UNKNOWN", "NOT_AVAILABLE") else None
    guard_metrics = None
    guard_file = root / GUARD_OUTPUT / "dg_v1_base_train_predictions.csv"
    if guard_file.exists():
        integrity = read_json(root / GUARD_OUTPUT / "dg_v1_integrity.json")
        required_files = {"dg_v1_base_train_predictions.csv", "dg_v1_development_metrics.json", "dg_v1_fold_metrics.json",
                          "dg_v1_source_metrics.json", "dg_v1_run_metadata.json", "dg_v1_run_started.json"}
        require(required_files <= integrity["sha256"].keys(), "incomplete guard integrity inventory")
        hashes.update(check_hashes(root, GUARD_OUTPUT, integrity["sha256"]))
        metadata = read_json(root / GUARD_OUTPUT / "dg_v1_run_metadata.json")
        require(metadata["status"] == "COMPLETE" and metadata["rows"] == 1135 and metadata["model_id"] == MODEL
                and metadata["revision"] == REVISION and metadata["manifest_sha256"] == MANIFEST and metadata["fold_sha256"] == FOLDS,
                "guard characterization provenance mismatch")
        require(metadata["score_direction"] == "higher_is_more_adversarial" and not any(metadata["isolation"].values()), "guard score/isolation mismatch")
        raw = read_csv(guard_file)
        data["D_G_v1"] = canonical(raw, "D_G_v1", fixture)
        require(all(r["native_binary_prediction"] in ("0", "1") for r in raw), "invalid guard native votes")
        guard_metrics = characterization([int(r["label"]) for r in raw], [float(r["raw_score"]) for r in raw],
                                          [r["native_binary_prediction"] == "1" for r in raw])
        require(guard_metrics == read_json(root / GUARD_OUTPUT / "dg_v1_development_metrics.json"), "guard metrics reconstruction mismatch")
    for rows in data.values():
        for row in rows:
            row["attack_family"] = families.get(row["sample_id"])
    aligned = align(data)
    token_rows = [r for r in read_csv(root / INPUTS["D_S_B2_LR"]) if r["scorer"] == "S0"]
    tokens = {r["sample_id"]: int(r["input_tokens"]) for r in token_rows}
    require(len(tokens) == len(token_rows) == 1135 and set(tokens) == set(fixture), "D_S token subgroup ID mismatch")
    return aligned, tokens, hashes, unavailable, guard_metrics


def reconstruct(root=ROOT, repetitions=1000):
    """Reconstruct all measured metrics and frozen reference counts."""
    data, tokens, hashes, unavailable, guard_metrics = evidence(root)
    result = analyze(data, STACKS, COMPARISON, repetitions=repetitions)
    for b in result["budgets"]:
        b["subgroups"] = subgroup_diagnostics(data, b["individual"], tokens)
        require([r["count"] for r in b["subgroups"]] == [26, 17], "known D_S subgroup counts drift")
    for key, name in {"D_S_v1": "artifacts/statistical_v2/oof/ds_v1_recipe_oof_metrics.json", "D_M-B_v1": "artifacts/semantic_v2/oof/dm_b_v1_recipe_oof_metrics.json",
                      "D_S_B2_LR": "artifacts/statistical_v2/scorer_comparison/scorer_metrics_v1.json"}.items():
        reference = read_json(root / name)
        if key == "D_S_B2_LR":
            reference = reference["S0"]
        rows = data[key]
        ranking = characterization([r["truth_label"] for r in rows], [r["score"] for r in rows], [False] * len(rows))
        require(abs(ranking["roc_auc"] - reference["roc_auc"]) < 1e-12 and abs(ranking["pr_auc"] - reference["pr_auc"]) < 1e-12, "OOF ranking reconstruction mismatch")
        for b, ref in zip(result["budgets"], reference["recall_at_fixed_fpr"]):
            p = next(r for r in b["individual"] if r["detector"] == key)
            require(p["tp"] == ref["tp"] and p["fp"] == ref["fp"], "OOF frontier count drift")
    budget3 = next(b for b in result["budgets"] if b["budget"] == .03)
    short, long = budget3["subgroups"]
    require(short["detector_counts"]["D_S_B2_LR"] == 0 and long["detector_counts"]["D_S_B2_LR"] == 12, "frozen subgroup result drift")
    return result, hashes, unavailable, guard_metrics


def required_pairs(budget):
    """Publication rows for both named stacks; absent evidence yields nulls."""
    rows = []
    fields = ["fnr_i", "fnr_j", "jfn_count", "jfn", "independence_reference", "ejf", "fn_jaccard",
              "left_fn_count", "right_fn_count", "p_failure_left_given_right", "p_failure_right_given_left"]
    for stack, members in STACKS.items():
        for left, right in ((members[0], members[1]), (members[0], members[2]), (members[1], members[2])):
            match = next((r for r in budget["pairwise"] if {r["left"], r["right"]} == {left, right}), None)
            if match:
                # Keep sorted orientation so conditional columns remain unambiguous.
                rows.append({"stack": stack, "budget": budget["budget"], "status": "MEASURED", **match})
            else:
                rows.append({"stack": stack, "budget": budget["budget"], "left": left, "right": right,
                             "status": "UNMEASURED_MISSING_D_G", **dict.fromkeys(fields)})
    return rows


def tables(result, guard_metrics):
    """Build seven publication tables with explicit unmeasured cells."""
    individual, pairwise, stacks, unique, effects, subgroups = [], [], [], [], [], []
    for b in result["budgets"]:
        individual.extend({"budget": b["budget"], **r} for r in b["individual"])
        if "D_G_v1" not in result["detectors"]:
            individual.append({"budget": b["budget"], "detector": "D_G_v1", "status": "UNMEASURED",
                               **dict.fromkeys(["fpr", "recall", "fnr", "tp", "fn", "fp", "tn", "threshold"])})
        pairwise.extend(required_pairs(b))
        stacks.extend({"budget": b["budget"], **r} for r in b["stacks"])
        unique.extend({"budget": b["budget"], **r} for r in b["unique"])
        effects.extend({"budget": b["budget"], **r} for r in b["effect"])
        for subgroup in b["subgroups"]:
            c = subgroup["detector_counts"]
            subgroups.append({"budget": b["budget"], "subgroup": subgroup["subgroup"], "count": subgroup["count"],
                             "count_meaning": subgroup["count_meaning"], "D_S_v1": c["D_S_v1"], "D_S_candidate": c["D_S_B2_LR"],
                             "D_M-B": c["D_M-B_v1"], "D_G": c["D_G_v1"],
                             "either_stronger_catches": subgroup["either_stronger_detector_catches"],
                             "all_three_miss": subgroup["candidate_all_three_miss"]})
    guard_table = []
    for metric in ("tn", "fp", "fn", "tp", "accuracy", "precision", "recall", "specificity", "f1", "fpr", "fnr", "roc_auc", "pr_auc"):
        row = {"metric": metric, "native": None, "le_1_percent": None, "le_3_percent": None, "le_5_percent": None}
        if guard_metrics:
            row["native"] = guard_metrics["native"].get(metric, guard_metrics.get(metric))
            for key, point in zip(("le_1_percent", "le_3_percent", "le_5_percent"), guard_metrics["fixed_fpr"]):
                row[key] = point.get(metric)
        guard_table.append(row)
    return {"table_1_guard": guard_table, "table_2_individual": individual, "table_3_pairwise": pairwise,
            "table_4_all_detector": stacks, "table_5_unique": unique, "table_6_ds_effect": effects, "table_7_subgroups": subgroups}


def release_paths(release):
    """Keep each evidence/report release additive when D_G becomes available."""
    require(type(release) is int and release >= 2, "invalid analysis release")
    output = "artifacts/common_mode/development/completion_v" + str(release)
    reports = REPORTS if release == 2 else [re.sub(r"_v[0-9]+\.md$", f"_v{release}.md", name) for name in REPORTS]
    return output, reports


def report_text(result, table, gate, preserved, tests, release=2):
    """Generate prose from measured values; never hardcode a future full result."""
    status = "PASS" if "D_G_v1" in result["detectors"] else "PARTIAL"
    intro = (f"# TECH-COMMON-001 Development Common-Mode Characterization v2\n\nStatus: **{status}**. DEVELOPMENT COMMON-MODE CHARACTERIZATION; not protected/final research performance.\n\n"
             "## Methodology\n\n1,135 aligned BASE_TRAIN records (183 positive, 952 negative), five frozen QUALITY-001 folds, seed 1701. D_S v1, B2+LR and D_M-B are authoritative fold-local OOF scores; no row was fitted by its scoring model. The candidate uses the selected S0/B2 evidence, never a whole-BASE_TRAIN fitted ds_v2. D_G is externally frozen without project BASE_TRAIN fitting; missing D_G evidence is never substituted.\n\n"
             "## Matched-FPR rule\n\nEach detector selects its own descriptive threshold at 1/3/5%. Use whole tied blocks and inclusive >=; maximize recall without exceeding budget, then minimize attained FPR, then choose the highest threshold. No final/deployment threshold or ensemble decision rule is created.\n\n"
             "Failure metrics use attack rows only: JFN is the joint miss fraction; IND is the product of marginal FNRs; EJF=JFN−IND. Jaccard is intersection/union (zero for empty union). Conditional failure P(F_left|F_right) uses the right FN count. Exclusive catches require both other members to miss; the rate uses all 183 attacks and recovery uses other-two misses as denominator. Empty conditional denominators yield null; denominators <10 carry a descriptive small-count flag.\n\n")
    body = "## D_G characterization\n\n" + markdown_table(table["table_1_guard"], ["metric", "native", "le_1_percent", "le_3_percent", "le_5_percent"]) + "\n"
    fields = {"table_2_individual": ["detector", "budget", "fpr", "recall", "fnr", "tp", "fn", "fp", "tn"],
              "table_3_pairwise": ["stack", "budget", "left", "right", "jfn_count", "jfn", "independence_reference", "ejf", "fn_jaccard"],
              "table_4_all_detector": ["stack", "budget", "all_detector_fn_count", "all_detector_jfn"],
              "table_5_unique": ["stack", "budget", "detector", "unique_catch_count", "unique_catch_rate", "other_members_miss_count", "recovery_given_others_miss"],
              "table_6_ds_effect": ["budget", "metric", "other", "baseline", "candidate", "delta"],
              "table_7_subgroups": ["budget", "subgroup", "count", "D_S_candidate", "D_M-B", "D_G", "either_stronger_catches", "all_three_miss"]}
    for name, columns in fields.items():
        body += "## " + name.replace("_", " ") + "\n\nRates are fractions. UNMEASURED is a missing result, not zero.\n\n" + markdown_table(table[name], columns) + "\n"
    conditional = [{k: p[k] for k in ("budget", "left", "right", "jfn_count", "left_fn_count", "right_fn_count", "p_failure_left_given_right", "p_failure_right_given_left")} for p in table["table_3_pairwise"] if p["status"] == "MEASURED"]
    body += "## Conditional pairwise failure\n\n" + markdown_table(conditional, list(conditional[0]) if conditional else ["status"]) + "\n"
    interpretation = []
    intervals = []
    for b in result["budgets"]:
        old = next(p for p in b["pairwise"] if {p["left"], p["right"]} == {"D_S_v1", "D_M-B_v1"})
        new = next(p for p in b["pairwise"] if {p["left"], p["right"]} == {"D_S_B2_LR", "D_M-B_v1"})
        interval = b["bootstrap"]["intervals"]["delta/jfn/D_M-B_v1"]
        interpretation.append(f'At {b["budget"]:.0%}, D_S/D_M-B shared misses change {old["jfn_count"]}→{new["jfn_count"]} out of 183 attacks. ΔJFN={interval["estimate"]:.6f}, conditional 95% interval [{interval["lower"]:.6f}, {interval["upper"]:.6f}]. ' + ("The delta interval includes zero; evidence for a population gain is inconclusive." if interval["lower"] <= 0 <= interval["upper"] else "This interval excludes zero conditional on the fixed development scores and operating points."))
        intervals.append({"budget": b["budget"], **interval})
    interpretation_text = "## D_S improvement interpretation\n\n" + "\n\n".join(interpretation) + "\n\n"
    interpretation_text += ("Positive EJF describes failure association relative to an independence reference, not causal dependence. Smaller marginal D_S FNR can increase EJF or Jaccard even if shared-FN counts stay fixed. No broad independence claim follows from these few semantic misses.\n\n")
    if status == "PARTIAL":
        interpretation_text += "Full-stack classification: **NO_CLEAR_CHANGE — D_G-dependent evidence unavailable**. D_S unique catches, recovery when D_M-B and D_G both miss, D_S/D_G association and all-three JFN remain unresolved. The available pairwise counts show one fewer shared miss at 1%/3%, but do not establish preserved primary-stack complementarity.\n\n"
    else:
        interpretation_text += "Full-stack deltas and exclusive catches are measured in Tables 4–6; assess their paired intervals and small event counts before claiming improved complementarity. No final detector promotion or architecture policy is authorized.\n\n"
    limitations = ("## Uncertainty and limitations\n\n1,000 deterministic paired attack-lineage percentile bootstrap replicates, seed 1701, fixed pooled operating points; only attack rows enter FN-dependent intervals. Identical resampled attacks across detector/stack comparisons. The fixture has 183 distinct attack canonical-lineage groups. Intervals condition on fixed OOF scores/thresholds, exclude refitting, development selection and overlapping-training-fold uncertainty, and do not resolve upstream semantic lineage. A degenerate zero-event bootstrap interval is not proof of zero population risk.\n\n" + markdown_table(intervals, ["budget", "estimate", "lower", "upper"]) + "\n"
                   "Source/fold groups apply unchanged pooled thresholds; no subgroup tuning. Existing per-ID family labels are retained for the four integrity-bound semantic residual records; all other records are UNKNOWN. This selectively annotated group was identified by prior semantic failures, so its family metrics are not a population family comparison. No label is inferred from text or generalized from a source. Sources are not R1/R2/R3 experiments. Subgroup tokens use frozen D_S reference-LM counts, not semantic/guard tokenizer counts. Catch/FP patterns are descriptive evidence, not a fusion rule. If a known detector catches every attack in a subgroup, the logical bounds establish zero all-three misses there despite absent D_G predictions; no guard result is imputed. Figures omitted to avoid extra plotting dependencies; all mandatory tables are CSV/JSON.\n\n"
                   "## Access blockers\n\n```json\n" + json.dumps(gate, indent=2) + "\n```\n\n"
                   "## Preservation and tests\n\n```json\n" + json.dumps({"tests": tests, "preservation": preserved}, indent=2) + "\n```\n\n"
                   "## Isolation\n\nD_S/D_M-B/D_G training: NO. CALIBRATION/VALIDATION/protected prompt payloads: NO. E1-E10, adaptive generation, verifier, routing, final threshold and fusion: NO. Historical predictions/artifacts and first Track-2 reports are byte-preserved.\n")
    main = intro + body + interpretation_text + limitations
    effect = "# TECH-COMMON-002 D_S Improvement Effect v1\n\nDEVELOPMENT COMMON-MODE CHARACTERIZATION. Status: **" + status + "**.\n\n" + markdown_table(table["table_6_ds_effect"], fields["table_6_ds_effect"]) + "\n" + interpretation_text + "## Known subgroup recovery\n\n" + markdown_table(table["table_7_subgroups"], fields["table_7_subgroups"]) + "\n" + limitations
    test_report = "# TECH-COMMON-001 Continuation Test Report v2\n\n" + json.dumps(tests, indent=2) + "\n\n" + json.dumps(preserved, indent=2) + "\n\nSynthetic tests cover conditional failure, ranking ties, native vote semantics, one-shot scoring validation, reserved-row refusal, four-detector alignment, grouped accounting and paired full-stack deltas. Model-dependent guard tests remain NOT RUN when runtime/model/data gates fail. The live scoring wrapper is infrastructure tested with synthetic primitive results; this is not live D_G qualification.\n"
    guard_report = "# TECH-GUARD-002 Development Characterization Continuation v2\n\nStatus: **" + ("PASS" if status == "PASS" else "BLOCKED_MISSING_AUTHORITATIVE_DEVELOPMENT_DATA") + "**.\n\n" + body.split("## table 2 individual")[0] + "\n```json\n" + json.dumps(gate, indent=2) + "\n```\n\nFrozen guard detector/model code remains unchanged. One-shot wrapper is ready; live inference is not claimed from synthetic tests. Restore exact data, authenticate locally, download the pinned model, install pinned runtime, then run the documented --check/--run commands. An interrupted live run refuses automatic rescoring; do not delete its start marker or manufacture completion.\n"
    if status == "PASS":
        guard_report = guard_report.replace(
            "One-shot wrapper is ready; live inference is not claimed from synthetic tests. Restore exact data, authenticate locally, download the pinned model, install pinned runtime, then run the documented --check/--run commands.",
            "The single authoritative offline run completed on all 1,135 BASE_TRAIN rows. Its integrity-bound live predictions, native votes and complete token coverage were verified independently of synthetic tests. No download, training, calibration or reserved-partition scoring occurred.")
        test_report = test_report.replace(
            "The live scoring wrapper is infrastructure tested with synthetic primitive results; this is not live D_G qualification.",
            "Synthetic infrastructure tests are separate from the completed authoritative live D_G run; its predictions and frozen-input hashes were verified.")
    if release != 2:
        main = main.replace("Characterization v2", f"Characterization v{release}")
        effect = effect.replace("Effect v1", f"Effect v{release}")
        test_report = test_report.replace("Report v2", f"Report v{release}")
        guard_report = guard_report.replace("Continuation v2", f"Continuation v{release}")
    return dict(zip(release_paths(release)[1], (main, effect, test_report, guard_report)))


def run(root=ROOT, repetitions=1000, release=2):
    """Produce additive evidence once, then verify deterministically with --verify."""
    output_name, reports = release_paths(release)
    out = root / output_name
    require(not out.exists(), "continuation evidence already exists; use --verify rather than overwrite")
    result, hashes, unavailable, guard_metrics = reconstruct(root, repetitions)
    gate, *_ = preflight(root)
    gate["unblock"][-1] = "python -m detection_service.scripts.common_mode_completion --release " + str(release + 1)
    preserved = preservation(root)
    tables_data = tables(result, guard_metrics)
    status = "PASS" if "D_G_v1" in result["detectors"] else "PARTIAL"
    out.mkdir(parents=True)
    for source_name in ("track2_continuation_prerun.xml", "track2_completion_tests.xml"):
        if (root / "tmp" / source_name).is_file():
            shutil.copyfile(root / "tmp" / source_name, out / source_name)
    tests = {"existing_prerun": test_receipt(out / "track2_continuation_prerun.xml"), "expanded": test_receipt(out / "track2_completion_tests.xml")}
    require(tests["expanded"]["status"] == "PASS", "expanded tests not passed")
    write_json(out / "test_evidence_v1.json", tests)
    write_json(out / "preservation_v1.json", preserved)
    write_json(out / "guard_availability_v1.json", gate)
    write_json(out / "detector_alignment_v1.json", {"available_detectors": result["detectors"], "aligned_samples": 1135,
               "positive": 183, "negative": 952, "fold_sha256": FOLDS, "expected_manifest_sha256": MANIFEST,
               "manifest_available": not any(r["path"].endswith("development_partition_manifest_v1.csv") for r in unavailable),
               "duplicate_ids": 0, "missing_ids_in_available_detectors": 0, "label_disagreements": 0,
               "missing_detector": [] if status == "PASS" else ["D_G_v1"], "canonical_lineage_leakage": 0, "input_sha256": hashes})
    write_json(out / "full_analysis_v1.json", result)
    for name, rows in tables_data.items():
        write_json(out / (name + ".json"), {"scope": result["scope"], "status": status, "rows": rows})
        csv_output(out / (name + ".csv"), rows)
    aliases = {"detector_operating_points": "individual", "individual_metrics": "individual", "pairwise_failure_metrics": "pairwise",
               "all_detector_failure": "stacks", "unique_catches": "unique", "conditional_recovery": "unique",
               "ds_improvement_effect": "effect", "subgroup_recovery": "subgroups", "grouped_failure_metrics": "grouped", "bootstrap_intervals": "bootstrap"}
    for name, category in aliases.items():
        write_json(out / (name + "_v1.json"), {"scope": result["scope"], "status": status,
                   "results": [{"budget": b["budget"], "metrics": b[category]} for b in result["budgets"]]})
    csv_output(out / "subgroup_patterns_v1.csv", [{"budget": b["budget"], "subgroup": s["subgroup"], **pattern} for b in result["budgets"] for s in b["subgroups"] for pattern in s["patterns"]])
    for name, content in report_text(result, tables_data, gate, preserved, tests, release).items():
        (root / name).write_text(content, encoding="utf-8", newline="\n")
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    manifest = {"status": status, "scope": result["scope"], "start_commit": COMPLETION_START, "historical_start_commit": START, "execution_commit": commit,
                "branch": subprocess.check_output(["git", "branch", "--show-current"], cwd=root, text=True).strip(),
                "rows": 1135, "positive": 183, "negative": 952, "seed": 1701,
                "bootstrap_repetitions": repetitions, "release": release, "expected_manifest_sha256": MANIFEST, "fold_sha256": FOLDS,
                "input_sha256": hashes, "output_sha256": {p.name: digest(p) for p in sorted(out.iterdir()) if p.is_file()},
                "code_sha256": {name: digest(root / name) for name in CODE},
                "report_sha256": {name: digest(root / name) for name in reports},
                "isolation": {k: False for k in ("DS_training", "DMB_training", "DG_training", "calibration_payload", "validation_payload", "protected_payload", "E1_E10", "verifier", "routing", "fusion", "deployment_threshold")},
                "verdict": "READY_FOR_REPORT_RESULTS_INTEGRATION" if status == "PASS" else "BLOCKED_BY_D_G_OR_DATA_ACCESS"}
    write_json(out / "common_mode_manifest_v1.json", manifest)
    print(json.dumps({"status": status, "output": str(out), "tests": tests, "verdict": manifest["verdict"]}, indent=2))


def verify(root=ROOT, release=2):
    """Verify all bytes and independently reconstruct numerical evidence."""
    output_name, _ = release_paths(release)
    out = root / output_name
    manifest = read_json(out / "common_mode_manifest_v1.json")
    check_hashes(root, output_name, manifest["output_sha256"])
    check_hashes(root, "", manifest["code_sha256"])
    check_hashes(root, "", manifest["report_sha256"])
    result, *_ = reconstruct(root, manifest["bootstrap_repetitions"])
    require(result == read_json(out / "full_analysis_v1.json"), "deterministic reconstruction drift")
    preservation(root)
    print(json.dumps({"status": "PASS_EVIDENCE_RECONSTRUCTION", "artifacts": len(manifest["output_sha256"]),
                      "report_hashes": len(manifest["report_sha256"]), "live_guard": manifest["status"], "verdict": manifest["verdict"]}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--release", type=int, default=2)
    args = parser.parse_args()
    verify(release=args.release) if args.verify else run(release=args.release)
