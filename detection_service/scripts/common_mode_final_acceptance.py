"""Publish release-3 evidence without model imports or new metric definitions."""
import argparse
import json
import subprocess

from detection_service.analysis.common_mode import require
from detection_service.scripts.common_mode_completion import (
    COMPLETION_START, release_paths, preservation,
)
from detection_service.scripts.common_mode_development import (
    ROOT, GUARD_OUTPUT, MODEL, REVISION, MANIFEST, FOLDS, INPUTS,
    read_json, digest, checked_hash, check_hashes, csv_output, write_json,
    markdown_table, test_receipt,
)

OUTPUT = "artifacts/common_mode/development/completion_v3/publication"
REPORT = "reviews/TECH_COMMON_003_FULL_STACK_COMPLETION_v1.md"
TEST_REPORT = "reviews/TECH_COMMON_003_TEST_REPORT_v1.md"
EFFECT_REPORT = "reviews/TECH_COMMON_002_DS_IMPROVEMENT_EFFECT_v2.md"


def long_agreement(subgroup):
    """Aggregate existing diagnostic patterns, not an ensemble decision rule."""
    rows = subgroup["patterns"]
    counts = {key: 0 for key in ("all_three_fp", "ds_only_fp", "ds_dm_overlap", "ds_dg_overlap", "dm_dg_overlap")}
    for row in rows:
        flags = {key: value == "1" for key, value in (part.split("=") for part in row["pattern"].split("|"))}
        ds, dm, dg = (flags[key] for key in ("D_S_B2_LR", "D_M-B_v1", "D_G_v1"))
        for key, present in zip(counts, (ds and dm and dg, ds and not dm and not dg, ds and dm, ds and dg, dm and dg)):
            counts[key] += row["count"] * present
    require(sum(row["count"] for row in rows) == subgroup["count"], "long subgroup pattern accounting")
    return counts


def classifications(budget):
    effects = {(r["metric"], r["other"]): r for r in budget["effect"]}
    shared = effects["all_detector_fn_count", "primary_stack"]
    unique = effects["unique_catch_count", "primary_stack"]
    result = []
    if shared["delta"] < 0:
        result.append("REDUCED_SHARED_FAILURE")
    if unique["candidate"] > 0 and unique["delta"] >= 0:
        result.append("PRESERVED_COMPLEMENTARITY")
    if unique["delta"] < 0:
        result.append("REDUCED_COMPLEMENTARITY")
    return result or ["NO_CLEAR_CHANGE"]


def publish(root=ROOT):
    base = root / release_paths(3)[0]
    out = root / OUTPUT
    require(not out.exists(), "publication exists; verify rather than overwrite")
    core = read_json(base / "common_mode_manifest_v1.json")
    require(core["status"] == "PASS" and core["bootstrap_repetitions"] == 1000 and core["seed"] == 1701,
            "full-stack completion not accepted")
    check_hashes(root, release_paths(3)[0], core["output_sha256"])
    check_hashes(root, "", core["code_sha256"])
    check_hashes(root, "", core["report_sha256"])
    result = read_json(base / "full_analysis_v1.json")
    dg = read_json(root / GUARD_OUTPUT / "dg_v1_development_metrics.json")
    run = read_json(root / GUARD_OUTPUT / "dg_v1_run_metadata.json")
    guarded = read_json(root / GUARD_OUTPUT / "dg_v1_integrity.json")
    check_hashes(root, GUARD_OUTPUT, guarded["sha256"])
    preserved = preservation(root)
    transfer_path = root / "detection_service/outputs/track2-authoritative-transfer/track2_authoritative_input_transfer_manifest.json"
    checked_hash(transfer_path, "252506fc1512a826c555ec56018b084bd2491ab1b9c82f18798dde55562eb402")
    transfer = read_json(transfer_path)
    for row in transfer["required_files"] + transfer["D_G"]["verified_files"] + transfer["evidence_sources"]:
        checked_hash(root / row["relative_path"], row["sha256"])
    zip_sha = checked_hash(root / "detection_service/outputs/track2-authoritative-transfer/track2_authoritative_inputs.zip",
                           "348a70c168bd5feb60d337b7b12eabcd8d0e29b991abc13745a535383496d7d7")
    tests = {"postrun_model_free": test_receipt(root / "tmp/track2_postrun_common.xml"),
             "postrun_guard_fixture": test_receipt(root / "tmp/track2_postrun_guard.xml")}
    require(all(r["status"] == "PASS" for r in tests.values()), "post-run tests required")
    backup = root / "detection_service/outputs/common003-preserved-stack"
    prior_commit = "e6b6a2af2a78e2a31aae6d9377378993f678b073"
    frozen_backup = {}
    for path in sorted(backup.rglob("*")):
        if not path.is_file():
            continue
        name = path.relative_to(backup).as_posix()
        original = subprocess.check_output(["git", "show", prior_commit + ":" + name], cwd=root)
        actual = path.read_bytes()
        require(actual == original or actual.replace(b"\r\n", b"\n") == original.replace(b"\r\n", b"\n"),
                "prior stack backup content changed: " + name)
        frozen_backup[name] = {"sha256": digest(path), "git_blob_byte_identical": actual == original}
    require(len(frozen_backup) == 48, "prior stack backup incomplete")
    table_data = {name: read_json(base / (name + ".json"))["rows"] for name in
                  ("table_1_guard", "table_2_individual", "table_3_pairwise", "table_4_all_detector", "table_5_unique", "table_6_ds_effect")}
    ranking = {"D_G_v1": dg}
    for key, name in {"D_S_v1": "artifacts/statistical_v2/oof/ds_v1_recipe_oof_metrics.json",
                      "D_M-B_v1": "artifacts/semantic_v2/oof/dm_b_v1_recipe_oof_metrics.json",
                      "D_S_B2_LR": "artifacts/statistical_v2/scorer_comparison/scorer_metrics_v1.json"}.items():
        metrics = read_json(root / name)
        ranking[key] = metrics["S0"] if key == "D_S_B2_LR" else metrics
    for row in table_data["table_2_individual"]:
        row.update({key: ranking[row["detector"]][key] for key in ("roc_auc", "pr_auc")})
    short_rows, long_rows, uncertainty = [], [], []
    for budget in result["budgets"]:
        short, long = budget["subgroups"]
        short_rows.append({"budget": budget["budget"], "attacks": short["count"], **short["detector_counts"],
                           "either_stronger_catches": short["either_stronger_detector_catches"], "all_three_miss": short["candidate_all_three_miss"]})
        long_rows.append({"budget": budget["budget"], "benign": long["count"], **long["detector_counts"], **long_agreement(long)})
        intervals = budget["bootstrap"]["intervals"]
        for pair in budget["pairwise"]:
            if "D_G_v1" in (pair["left"], pair["right"]) and "D_S_v1" not in (pair["left"], pair["right"]):
                key = f'jfn/{pair["left"]}/{pair["right"]}'
                uncertainty.append({"budget": budget["budget"], "metric": key, "event_count": pair["jfn_count"], "denominator": 183, **intervals[key]})
        for stack in budget["stacks"]:
            key = "all_detector_jfn/" + stack["stack"]
            uncertainty.append({"budget": budget["budget"], "metric": key, "event_count": stack["all_detector_fn_count"], "denominator": 183, **intervals[key]})
        for metric in ("all_detector_jfn", "recovery_given_others_miss"):
            key = "delta/" + metric + "/primary_stack"
            if key in intervals:
                uncertainty.append({"budget": budget["budget"], "metric": key, "event_count": None, "denominator": None, **intervals[key]})
    table_data["table_7_under_16_attacks"] = short_rows
    table_data["table_8_long_benign"] = long_rows
    out.mkdir()
    for name, rows in table_data.items():
        csv_output(out / (name + ".csv"), rows)
        write_json(out / (name + ".json"), {"scope": result["scope"], "rows": rows})
    write_json(out / "uncertainty_v1.json", {"replicates": 1000, "seed": 1701, "rows": uncertainty,
        "note": "Tiny event counts imply fragile intervals. Absolute conditional-recovery intervals are not implemented by the frozen engine; paired recovery-delta intervals are reported without inventing a new estimator."})
    write_json(out / "frozen_stack_preservation_v1.json", {"source_commit": prior_commit, "local_ignored_backup": str(backup), "files": frozen_backup,
        "note": "Common branch predates final ds_v2/STACK-001. No auto-merge; frozen files preserved locally and in accepted Git history. Final ds_v2 never scored for this study."})
    sections = ["# FULL THREE-DETECTOR DEVELOPMENT FINAL REPORT\n\nSTATUS: **PASS**\n",
        f"## Repository and provenance\n\nBranch: tech/common-003-dg-completion. Completion start: `{COMPLETION_START}`. "
        f"D_G model/run code commit: `{run['code_commit']}`. Common analysis execution: `{core['execution_commit']}`. "
        "Later commits contain post-run acceptance evidence, not retroactive run provenance. Publication commit/push identifiers are returned after synchronization.\n",
        "## Environment\n\n```json\n" + json.dumps(run["environment"], indent=2) + "\n```\n\nDevice: CPU; exact local snapshot, HF_HUB_OFFLINE=1 and TRANSFORMERS_OFFLINE=1. No package installation or model download.\n",
        f"## Authoritative fixture\n\n1,135 BASE_TRAIN rows; 183 positive, 952 negative. Manifest `{MANIFEST}`; folds `{FOLDS}`. "
        "Unique IDs, missing IDs, labels, canonical lineage and exact selected source-text hashes pass. Source containers include other partitions, but only BASE_TRAIN scalars were selected. No reserved/protected prompt scoring.\n",
        f"## D_G characterization\n\nModel `{MODEL}`, revision `{REVISION}`. Frozen 512-token capacity, 510-token content chunks, overlap 64, stride 446, complete tail coverage. "
        "Raw=max malicious-class chunk softmax; native=OR of malicious chunk argmax. No calibration.\n"]
    columns = {"table_1_guard": ["metric", "native", "le_1_percent", "le_3_percent", "le_5_percent"],
               "table_2_individual": ["budget", "detector", "fpr", "recall", "fnr", "tp", "fn", "fp", "tn", "roc_auc", "pr_auc"],
               "table_3_pairwise": ["budget", "stack", "left", "right", "jfn_count", "jfn", "independence_reference", "ejf", "fn_jaccard"],
               "table_4_all_detector": ["budget", "stack", "all_detector_fn_count", "all_detector_jfn"],
               "table_5_unique": ["budget", "stack", "detector", "unique_catch_count", "unique_catch_rate", "other_members_miss_count", "recovery_given_others_miss"],
               "table_6_ds_effect": ["budget", "metric", "other", "baseline", "candidate", "delta"],
               "table_7_under_16_attacks": list(short_rows[0]), "table_8_long_benign": list(long_rows[0])}
    for name, rows in table_data.items():
        sections.append("## " + name.replace("_", " ").title() + "\n\n" + markdown_table(rows, columns[name]) + "\n")
    for group in ("fold", "source"):
        rows = read_json(root / GUARD_OUTPUT / f"dg_v1_{group}_metrics.json")
        flattened = [{group: r[group], "rows": r["rows"], "positive": r["positive"], "negative": r["negative"],
                      "roc_auc": r["roc_auc"], "pr_auc": r["pr_auc"],
                      "fixed_fpr": r["fixed_fpr"], "native": r["native"]} for r in rows]
        sections.append(f"## D_G {group} characterization\n\n```json\n" + json.dumps(flattened, indent=2) + "\n```\n")
    sections.append("## Uncertainty\n\n" + markdown_table(uncertainty, ["budget", "metric", "event_count", "denominator", "estimate", "lower", "upper"]) + "\n"
        "1,000 paired canonical attack-lineage percentile bootstrap replicates, seed 1701. Fixed scores and pooled thresholds; no threshold reselection, refitting, selection uncertainty or training-fold dependence modeled. "
        "Only 183 attack groups. Tiny shared-event and conditional denominators make intervals fragile; a zero-event interval is not proof of zero population risk. "
        "The unchanged engine supplies a paired recovery-delta interval, not an absolute conditional-recovery interval. Raw conditional numerators/denominators are in Table 5.\n")
    primary = next(b for b in result["budgets"] if b["budget"] == .03)
    pair = next(p for p in primary["pairwise"] if {p["left"], p["right"]} == {"D_M-B_v1", "D_G_v1"})
    ds = next(u for u in primary["unique"] if u["stack"] == "DEVELOPMENT_STACK_CANDIDATE" and u["detector"] == "D_S_B2_LR")
    change = next(e for e in primary["effect"] if e["metric"] == "all_detector_fn_count")
    finding = (f"At the descriptive 3% FPR budget, D_S B2+LR catches {ds['unique_catch_count']}/{ds['other_members_miss_count']} attacks missed by both D_M-B and D_G, "
               f"and all-three shared misses change from {change['baseline']} to {change['candidate']} out of 183 attacks.")
    sections.append("## Research answers\n\n"
        f"1. Independence is a reference, not established: D_M-B/D_G shared misses={pair['jfn_count']}/183, JFN={pair['jfn']:.6f}, IND={pair['independence_reference']:.6f}, EJF={pair['ejf']:.6f} at 3%. "
        "Positive EJF is observed excess failure association, not causal dependence.\n"
        f"2. D_S candidate recovers {ds['unique_catch_count']}/{ds['other_members_miss_count']} attacks missed by both stronger guards.\n"
        f"3. All-three shared misses change {change['baseline']} -> {change['candidate']} at 3%; paired uncertainty is reported above.\n"
        f"4. Observed failure-diversity classification at 3%: {', '.join(classifications(primary))}. This describes counts, not proof of distinct causal mechanisms.\n"
        "5. Development evidence supports carrying the measured heterogeneous candidate into later Commander review; it does not authorize those later experiments or establish production, protected-benchmark or adaptive robustness.\n")
    sections.append("## Tests and preservation\n\n```json\n" + json.dumps({"tests": tests, "preservation": preserved}, indent=2) + "\n```\n"
        "Initial combined pytest collected guard Torch imports and failed one model-free import-isolation assertion. Suites were rerun in separate processes without altering that assertion; all passed. "
        "Authoritative OOF evidence remains byte-identical and independently reconstructed. Prior final ds_v2/STACK-001 files were preserved byte-for-byte locally before the requested divergent branch switch; accepted history was not merged or rewritten.\n")
    sections.append("## Governance\n\nD_S cycle 2 DEFERRED; final thresholds NOT FROZEN; fusion NOT IMPLEMENTED; verifier NOT SELECTED; routing NOT IMPLEMENTED; "
        "training/calibration/VALIDATION/protected/E1-E10/R1-R3 NO. Fixed-FPR points are descriptive and detector-specific, not frozen deployment decisions.\n"
        "## Final verdict\n\n**READY_FOR_REPORT_RESULTS_INTEGRATION**\n\nTHE SINGLE MOST IMPORTANT EMPIRICAL FINDING:\n\n" + finding + "\n")
    (root / REPORT).write_text("\n".join(sections), encoding="utf-8", newline="\n")
    (root / TEST_REPORT).write_text("# TECH-COMMON-003 Test Report\n\n" + next(s for s in sections if s.startswith("## Tests and preservation")) + "\n", encoding="utf-8", newline="\n")
    (root / EFFECT_REPORT).write_text("# TECH-COMMON-002 D_S Improvement Effect v2\n\n" + markdown_table(table_data["table_6_ds_effect"], columns["table_6_ds_effect"]) + "\n\n"
        + "\n".join(f"At {b['budget']:.0%}: {', '.join(classifications(b))}." for b in result["budgets"])
        + "\n\n" + finding + "\n\nObserved development failure association only; use the full completion report for paired intervals and limitations.\n", encoding="utf-8", newline="\n")
    manifest = {"status": "PASS", "verdict": "READY_FOR_REPORT_RESULTS_INTEGRATION", "start_commit": COMPLETION_START,
                "dg_run_code_commit": run["code_commit"], "common_analysis_execution_commit": core["execution_commit"],
                "fixture_manifest_sha256": MANIFEST, "fold_sha256": FOLDS, "transfer_manifest_sha256": digest(transfer_path), "transfer_zip_sha256": zip_sha,
                "core_manifest_sha256": digest(base / "common_mode_manifest_v1.json"), "guard_integrity_sha256": digest(root / GUARD_OUTPUT / "dg_v1_integrity.json"),
                "authoritative_oof_sha256": {name: digest(root / name) for name in INPUTS.values()},
                "test_receipts": tests, "finding": finding, "classifications": {str(b["budget"]): classifications(b) for b in result["budgets"]},
                "output_sha256": {p.name: digest(p) for p in sorted(out.iterdir()) if p.is_file()},
                "report_sha256": {name: digest(root / name) for name in (REPORT, TEST_REPORT, EFFECT_REPORT)},
                "publisher_sha256": digest(root / "detection_service/scripts/common_mode_final_acceptance.py")}
    write_json(out / "full_stack_manifest_v1.json", manifest)
    print(json.dumps({"status": "PASS", "report": REPORT, "finding": finding, "classifications": manifest["classifications"]}, indent=2))


def verify(root=ROOT):
    manifest = read_json(root / OUTPUT / "full_stack_manifest_v1.json")
    check_hashes(root, OUTPUT, manifest["output_sha256"])
    check_hashes(root, "", manifest["report_sha256"])
    check_hashes(root, "", manifest["authoritative_oof_sha256"])
    checked_hash(root / "detection_service/scripts/common_mode_final_acceptance.py", manifest["publisher_sha256"])
    checked_hash(root / release_paths(3)[0] / "common_mode_manifest_v1.json", manifest["core_manifest_sha256"])
    checked_hash(root / GUARD_OUTPUT / "dg_v1_integrity.json", manifest["guard_integrity_sha256"])
    preservation(root)
    print(json.dumps({"status": "PASS_PUBLICATION_HASHES", "artifacts": len(manifest["output_sha256"]), "reports": len(manifest["report_sha256"])}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    verify() if args.verify else publish()
