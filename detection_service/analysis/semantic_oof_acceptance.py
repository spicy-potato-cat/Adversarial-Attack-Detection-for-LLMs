"""TECH-SEM-003 post-run evidence only: no text loading, inference, or training."""

import argparse
from collections import Counter
import csv
import io
import json
import math
import os
import subprocess
import xml.etree.ElementTree as ET

from detection_service.analysis.semantic_oof import interval, probability_metrics, require
from detection_service.quality.development_fixture import ROOT, file_hash, json_bytes
from detection_service.quality.policy import FOLD_PATH, MANIFEST_PATH
from detection_service.scripts import semantic_oof_baseline as original

RUN_COMMIT = "5096d078b599c43ddd4e32b4fbfcaedcc83e4646"
MANIFEST_SHA = "9cdd5ecdd80f9ac3c8f05db63742721f4537ca2b64a2fe48f6c2b424b57483a6"
FOLD_SHA = "19dc0153cc257cc2331782d6dd61b7bb9fb8cb0ed88d3e782b69d5ba05c4bb8d"
PREFLIGHT_SHA = "9f0465747c214f01cce3c5927b7ea2f8058d5d97c310ce6b3e2b6f8af9fb6dc7"
OUT = original.OUTPUT
SEAL = OUT / "acceptance_manifest_v1.json"
CODE = ("detection_service/analysis/semantic_oof_acceptance.py",
        "detection_service/tests/test_semantic_oof_acceptance.py")
REPORTS = tuple(f"reviews/TECH_SEM_003_{name}_v1.md" for name in
                ("FINAL_ACCEPTANCE", "RESIDUAL_FAILURE_ANALYSIS", "POSTRUN_TEST_REPORT"))
EXPECTED_OUTPUTS = {
    "dm_b_v1_error_characterization.json": "12e4bcc58c57fa3b4deef7ed82a2c4903f71c33d903550f58c89436ebd0c52d5",
    "dm_b_v1_hard_examples.csv": "bdb41ca856544fbce7e92430afa7d02984191515be7c330fe7223e03c8728ee9",
    "dm_b_v1_oof_run_metadata.json": "fb4e8c2b17bdbfe3b5491324effa39f7d0e3acf917c13041c217643283f845c4",
    "dm_b_v1_recipe_fold_metrics.json": "2edc6107c9b8bd69822f3ba207dfe765de59fd2ff12dcfd7639db4d40b139e3e",
    "dm_b_v1_recipe_oof_curves.json": "2dba9dd5de2151107e8aba9b1dd20ac4f6046b694b1fd9ff472b9cd0747cb262",
    "dm_b_v1_recipe_oof_metrics.json": "9471b40621ecb688184861476d10f2821688c40ee200f756e8695f6b12b61c59",
    "dm_b_v1_recipe_oof_predictions.csv": "cfafb1d4286a8b61e4054da337cd45a4353a44894899b034670f9413f6b1000c",
    "dm_b_v1_truncation_analysis.json": "e78973b2f4f099c25140b8e11c81dd3e19b9618998aefe199b87ea7f8116b024",
    "dm_b_v1_v2_recommendation.json": "1cc58a257729d98c11c4c8f5a405ff25faafcce0fdb4e8471de17cd129ad74bc",
}
ORIGINALS = (*EXPECTED_OUTPUTS, "completion_v1.json", "run_started_v1.json")
PERSISTENT_IDS = (
    "W2-2e5c0b7b868cdf69b5d982aa", "W2-5ce365d631f87bfbcb320b57",
    "W2-77cf86dae187121c639f9238", "W2-dd2317a66faaf974b05e945d",
)
CAVEAT = ("The pooled threshold was chosen descriptively using the same pooled OOF predictions being summarized. "
          "It demonstrates ranking/operating capacity, not an unbiased estimate of a future independently selected "
          "threshold. Final threshold selection remains deferred to the authorized calibration/validation "
          "operating-point phase. No descriptive threshold is frozen for deployment.")


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def verify_run_provenance(config):
    # HEAD may advance for acceptance; the executed code must stay at its original commit.
    require(subprocess.run(["git", "merge-base", "--is-ancestor", RUN_COMMIT, "HEAD"],
                           cwd=ROOT, capture_output=True).returncode == 0, "run commit is not an ancestor")
    require(git("log", "-1", "--format=%H", "--", "artifacts/semantic_v2/oof/preflight/oof_preflight_v1.json")
            == RUN_COMMIT, "preflight commit drift")
    paths = [*config["code_sha256"], *[p.relative_to(ROOT).as_posix()
             for p in original.PREFLIGHT.iterdir() if p.is_file()]]
    for path in paths:
        require(git("hash-object", f"--path={path}", path) == git("rev-parse", f"{RUN_COMMIT}:{path}"),
                f"frozen run bytes differ from original commit: {path}")


def authoritative_inputs():
    config, recipe, _ = original.checked_config()
    verify_run_provenance(config)
    for path, digest in ((ROOT / MANIFEST_PATH, MANIFEST_SHA), (ROOT / FOLD_PATH, FOLD_SHA),
                         (original.PREFLIGHT / "oof_preflight_v1.json", PREFLIGHT_SHA)):
        require(file_hash(path) == digest, "fixture/preflight hash drift")
    original.verify_hashes(original.PREFLIGHT, read(original.PREFLIGHT / "oof_preflight_v1.json")["evidence_sha256"])
    require(not (OUT / "failure_v1.json").exists(), "failed run")
    completion, metadata, started = (read(OUT / name) for name in
                                    ("completion_v1.json", original.RUN_METADATA_NAME, "run_started_v1.json"))
    require(completion["status"] == "COMPLETE_DEVELOPMENT_OOF" and completion["rows"] == 1135,
            "incomplete authoritative run")
    require(completion["output_sha256"] == EXPECTED_OUTPUTS, "authoritative output contract changed")
    original.verify_hashes(OUT, EXPECTED_OUTPUTS)
    for item in (completion, metadata, started):
        require(item["code_commit"] == RUN_COMMIT and item["oof_preflight_sha256"] == PREFLIGHT_SHA
                and item["analysis_config_sha256"] == file_hash(original.config_path()), "run provenance drift")
    require(all(completion[key] is False for key in ("calibration_used", "validation_used", "protected_used",
            "final_model_loaded", "dm_b_v2_trained", "E1_E10_executed")), "run isolation drift")
    require(completion["identity_leakage"] == completion["lineage_leakage"] == 0, "run leakage")
    require(metadata["packages"] == original.environment()["packages"] and metadata["manifest_sha256"] == MANIFEST_SHA
            and metadata["fold_sha256"] == FOLD_SHA and metadata["upstream_revision"] == original.REVISION
            and metadata["seed"] == 1701 and metadata["device"] == "cpu", "run environment drift")
    original.verify_hashes(OUT, metadata["output_sha256"])
    original.verify_hashes(original.evidence_root(), completion["readiness_evidence_sha256"])
    rows, sources = original.selected_rows()
    records = original.read_predictions()
    original.validate_predictions(records, rows)
    original.validate_schema(records)
    reports = read(OUT / "dm_b_v1_recipe_fold_metrics.json")["folds"]
    require([r["fold"] for r in reports] == list(range(5)), "fold coverage drift")
    for report in reports:
        fold = report["fold"]
        train = [r for r in rows if int(r["outer_fold"]) != fold]
        held = [r for r in rows if int(r["outer_fold"]) == fold]
        require(report["train_membership_sha256"] == original.digest_ids(train)
                and report["held_out_membership_sha256"] == original.digest_ids(held), "membership drift")
        require(report["recipe"] == recipe.to_dict() and report["identity_leakage"] == report["lineage_leakage"] == 0,
                "fold recipe/leakage drift")
        require(report["train_rows"] == len(train) and report["held_out_rows"] == len(held), "fold count drift")
        require(report["train_positive"] == sum(int(r["label"]) for r in train), "fold class count drift")
        selected = [r for r in records if r["fold"] == fold]
        require(report["metrics"] == probability_metrics([r["label"] for r in selected],
                                                        [r["raw_score"] for r in selected]), "fold metrics drift")
    require(len({r["initial_parameters_sha256"] for r in reports}) == 1, "initialization drift")
    for name, payload in original.analysis_products(records, reports).items():
        require(payload == read(OUT / name), f"original reconstruction failed: {name}")
    require((OUT / "dm_b_v1_hard_examples.csv").read_bytes() == original.csv_bytes(
        [r for r in records if r["error_type"] in ("FN", "FP")]), "hard example reconstruction failed")
    baseline = original.baseline_check()
    require(baseline["hash_checks"] == 96, "baseline check count drift")
    return records, sources, baseline


def describe(values):
    mean = math.fsum(values) / len(values)
    return {"mean": mean, "population_sd": math.sqrt(math.fsum((v - mean) ** 2 for v in values) / len(values)),
            "min": min(values), "max": max(values)}


def rates(fp, fn, negative, positive):
    return {"fp": fp, "fn": fn, "negative_denominator": negative, "positive_denominator": positive,
            "fpr": fp / negative, "fnr": fn / positive,
            "fpr_95pct": interval(fp, negative), "fnr_95pct": interval(fn, positive)}


def metadata_row(row, source, threshold):
    output = {key: row[key] for key in ("sample_id", "fold", "source_name", "source_revision", "lineage_group",
              "raw_score", "logit_margin", "confidence_category", "input_tokens", "tokens_analyzed", "truncated", "tokens_excluded")}
    output.update({"descriptive_3pct_threshold": threshold, "distance_below_threshold": threshold - row["raw_score"],
                   "recovered_at_3pct": row["raw_score"] >= threshold})
    for target, origin in (("source_dataset_id", "source_dataset_id"), ("record_locator", "canonical_text_reference"),
                           ("attack_family", "attack_family"), ("attack_mechanism", "attack_mechanism"),
                           ("provenance_status", "provenance_status"), ("label_confidence", "label_confidence"),
                           ("rights_status", "rights_status"), ("source_original_id", "source_record_id")):
        output[target] = source.get(origin) or "UNKNOWN"
    output["generator"] = "NOT_AVAILABLE"
    output["structural_subtype"] = "UNKNOWN"
    return output


def csv_bytes(rows):
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode("utf-8")


def products(records, sources):
    aggregate = probability_metrics([r["label"] for r in records], [r["raw_score"] for r in records])
    require(aggregate["confusion_matrix"] == {"tn": 947, "fp": 5, "fn": 17, "tp": 166}, "aggregate drift")
    negative, positive = aggregate["negative_count"], aggregate["positive_count"]
    intervals = {"raw_0_5": rates(5, 17, negative, positive)}
    for point, expected in zip(aggregate["recall_at_fixed_fpr"], ((177, 7, 6), (179, 22, 4), (181, 34, 2)), strict=True):
        threshold = point["descriptive_threshold"]
        tp = sum(r["label"] == 1 and r["raw_score"] >= threshold for r in records)
        fp = sum(r["label"] == 0 and r["raw_score"] >= threshold for r in records)
        fn = positive - tp
        require((tp, fp, fn) == expected and tp == point["tp"] and fp == point["fp"], "frontier counts drift")
        intervals[f"budget_{int(point['budget'] * 100)}pct"] = {**point, **rates(fp, fn, negative, positive),
                                                              "tp": tp, "tn": negative - fp}
    intervals["caveat"] = CAVEAT
    intervals["interval_caveat"] = ("Descriptive Wilson 95% binomial intervals. OOF predictions share training data; "
        "observations are not perfectly independent in the modeling sense. Not final population guarantees, "
        "and not proof that true error is below 3%.")
    folds = []
    for fold in range(5):
        held = [r for r in records if r["fold"] == fold]
        metric = probability_metrics([r["label"] for r in held], [r["raw_score"] for r in held])
        folds.append({"fold": fold, **{key: metric[key] for key in ("sample_count", "positive_count", "negative_count",
                     "roc_auc", "pr_auc", "confusion_matrix", "recall_at_fixed_fpr")}})
    summaries = {}
    for index, budget in enumerate((1, 3, 5)):
        summaries[f"budget_{budget}pct"] = {key: describe([f["recall_at_fixed_fpr"][index][key] for f in folds])
                                           for key in ("recall", "attained_fpr")}
    stability = {"folds": folds, "summaries": summaries,
                 "caveat": "Each frontier uses its own held-out fold scores descriptively; not independently chosen threshold performance. No fold tuning."}
    threshold = aggregate["recall_at_fixed_fpr"][1]["descriptive_threshold"]
    source_map = {s["record_id"]: s for s in sources}
    raw = [metadata_row(r, source_map[r["sample_id"]], threshold) for r in records if r["error_type"] == "FN"]
    persistent = [r for r in raw if not r["recovered_at_3pct"]]
    require(tuple(r["sample_id"] for r in persistent) == PERSISTENT_IDS, "persistent four IDs drift")
    require(len(raw) == 17 and sum(r["recovered_at_3pct"] for r in raw) == 13, "FN partition drift")
    positive_sources = [source_map[r["sample_id"]] for r in records if r["label"] == 1]
    population = {field: dict(sorted(Counter(s.get(field) or "UNKNOWN" for s in positive_sources).items()))
                  for field in ("source_dataset", "attack_family", "attack_mechanism", "provenance_status", "label_confidence")}
    truncation = original.truncation_analysis(records)
    require(truncation["positive_truncated"] == 4 and truncation["groups"]["truncated"]["confusion_matrix"]
            == {"tn": 0, "fp": 0, "fn": 0, "tp": 4}, "truncation drift")
    residual = {
        "scope": "BASE_TRAIN_METADATA_ONLY_NO_RAW_TEXT_NO_MODEL_EXECUTION", "aggregate": aggregate,
        "raw_fn_count": len(raw), "raw_high_confidence_fn": sum(r["confidence_category"] == "HIGH_CONFIDENCE_WRONG" for r in raw),
        "raw_fn_ids": [r["sample_id"] for r in raw], "recovered_ids": [r["sample_id"] for r in raw if r["recovered_at_3pct"]],
        "persistent_fn_count": len(persistent), "persistent_ids": list(PERSISTENT_IDS),
        "persistent_high_confidence": sum(r["confidence_category"] == "HIGH_CONFIDENCE_WRONG" for r in persistent),
        "persistent_borderline": sum(r["confidence_category"] == "BORDERLINE_WRONG" for r in persistent),
        "coherence_classification": "PARTIAL_CLUSTER", "actionable_cluster": False,
        "all_positive_metadata_distribution": population,
        "persistent_folds": dict(sorted(Counter(r["fold"] for r in persistent).items())),
        "persistent_distinct_lineage_groups": len({r["lineage_group"] for r in persistent}),
        "persistent_shorter_than_32_tokens": sum(r["input_tokens"] < 32 for r in persistent),
        "coherence_reason": ("Shared source, broad direct_prompt_injection family/mechanism, partial provenance and medium label confidence "
            "also describe all 183 positives; they do not isolate a residual-specific blind spot. Four distinct lineage groups, "
            "three folds, three short inputs and one 43-token input. Fine subtype and generator unavailable. "
            "A specific actionable intervention cannot be justified from this metadata; mechanisms cannot be declared heterogeneous."),
        "truncation": {"positive_truncated": 4, "fn": 0, "tp": 4, "fnr_95pct": interval(0, 4),
            "conclusion": "NO OBSERVED ASSOCIATION BETWEEN CURRENT OOF MISSES AND EXCLUDED TOKENS IN THIS FIXTURE",
            "limitation": "Only four truncated positives and no truncated negatives; truncation may cause future errors.",
            "B1_256_to_512": "NOT_SUPPORTED_AS_NEXT_MODEL_IMPROVEMENT_EXPERIMENT"},
        "decision": "FREEZE_DM_B_V1", "decision_reason": ("Strong descriptive frontier, no truncation-associated misses and "
            "no residual-specific actionable mechanism. Fold-1 weakness at 3% and folds 0/1 at 1% are retained, not tuned. "
            "Accept v1 for next stack phase; do not chase four residuals, hard-mine, retrain or create dm_b_v2."),
        "interpretation": "D_M-B demonstrates the capacity to operate within the 1-3% FPR/FNR region at a descriptive development-OOF operating point.",
        "threshold_caveat": CAVEAT,
        "isolation": {key: False for key in ("calibration_access", "validation_access", "protected_access", "E1_E10",
                                             "model_trained", "model_inference", "deployment_threshold_frozen", "SEM_004_started", "STAT_004_modified")},
    }
    return {
        "dm_b_v1_rate_intervals_v1.json": json_bytes(intervals),
        "dm_b_v1_fold_stability_v1.json": json_bytes(stability),
        "dm_b_v1_persistent_fn_3pct_v1.csv": csv_bytes(persistent),
        "dm_b_v1_raw_fn_v1.csv": csv_bytes(raw),
        "dm_b_v1_residual_failure_analysis_v1.json": json_bytes(residual),
    }


def test_evidence(path):
    require(path.resolve() == OUT / "acceptance_tests_v1.xml", "unexpected test evidence path")
    suites = ET.parse(path).getroot().findall("testsuite")
    counts = {key: sum(int(s.attrib.get(key, 0)) for s in suites) for key in ("tests", "failures", "errors", "skipped")}
    require(counts["tests"] >= 100 and counts["failures"] == counts["errors"] == counts["skipped"] == 0,
            "post-run tests failed/incomplete")
    classes = {t.attrib.get("classname", "") for s in suites for t in s.findall("testcase")}
    require(all(any(name in cls for cls in classes) for name in
                ("test_semantic_oof", "test_statistical_oof", "test_semantic_oof_acceptance")), "missing regression suite")
    return {**counts, "xml_path": path.relative_to(ROOT).as_posix(), "xml_sha256": file_hash(path),
            "deselected": 1, "deselected_test": "test_run_stops_at_preflight_before_loading_text_or_training",
            "reason": "Pre-run-only assertion requires an absent run marker; superseded after authoritative completion by post-run refusal test."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", required=True, choices=("analyze", "seal", "check"))
    args = parser.parse_args()
    require(os.path.realpath(os.getcwd()) == str(ROOT.resolve()), "execute from repository root")
    os.environ["HF_HUB_OFFLINE"] = os.environ["TRANSFORMERS_OFFLINE"] = "1"
    original.install_gate(set())  # No Dataset or PHASE-3 payload may be opened by acceptance.
    records, sources, baseline = authoritative_inputs()
    generated = products(records, sources)
    if args.mode == "analyze":
        require(not SEAL.exists() and not any((OUT / name).exists() for name in generated), "refuse overwrite")
        for name, payload in generated.items():
            with (OUT / name).open("xb") as handle:
                handle.write(payload)
    else:
        for name, payload in generated.items():
            require((OUT / name).read_bytes() == payload, f"acceptance reconstruction drift: {name}")
        if args.mode == "seal":
            require(not SEAL.exists(), "acceptance already sealed")
            evidence = {"status": "PASS_TECH_SEM_003_FINAL_ACCEPTANCE", "run_code_commit": RUN_COMMIT,
                "acceptance_commit_policy": "Post-run evidence commit, not model/run code provenance. Resolve git log -1 --format=%H -- this manifest after commit.",
                "manifest_sha256": MANIFEST_SHA, "fold_sha256": FOLD_SHA, "preflight_sha256": PREFLIGHT_SHA,
                "original_output_hash_checks": 9, "original_input_sha256": {name: file_hash(OUT / name) for name in ORIGINALS},
                "acceptance_output_sha256": {name: file_hash(OUT / name) for name in generated},
                "acceptance_code_sha256": {name: file_hash(ROOT / name) for name in CODE},
                "report_sha256": {name: file_hash(ROOT / name) for name in REPORTS},
                "baseline_preservation": baseline, "tests": test_evidence(OUT / "acceptance_tests_v1.xml"),
                "decision": "FREEZE_DM_B_V1", "isolation": json.loads(generated["dm_b_v1_residual_failure_analysis_v1.json"])["isolation"]}
            original.write(SEAL, evidence)
        else:
            evidence = read(SEAL)
            require(evidence["run_code_commit"] == RUN_COMMIT and evidence["decision"] == "FREEZE_DM_B_V1",
                    "acceptance provenance/decision drift")
            require(set(evidence["original_input_sha256"]) == set(ORIGINALS)
                    and set(evidence["acceptance_output_sha256"]) == set(generated), "seal coverage drift")
            for root, key in ((OUT, "original_input_sha256"), (OUT, "acceptance_output_sha256"),
                              (ROOT, "acceptance_code_sha256"), (ROOT, "report_sha256")):
                original.verify_hashes(root, evidence[key])
            require(evidence["tests"] == test_evidence(OUT / "acceptance_tests_v1.xml"), "test evidence drift")
            require(evidence["baseline_preservation"] == baseline, "baseline evidence drift")
    print(json.dumps({"status": "PASS_TECH_SEM_003_FINAL_ACCEPTANCE", "mode": args.mode, "rows": len(records),
                      "identity_leakage": 0, "lineage_leakage": 0, "output_hash_checks": 9,
                      "baseline_hash_checks": baseline["hash_checks"], "decision": "FREEZE_DM_B_V1",
                      "run_code_commit": RUN_COMMIT, "model_execution": False}, indent=2))


if __name__ == "__main__":
    main()
