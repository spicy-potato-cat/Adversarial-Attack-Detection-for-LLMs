"""One-time CALIBRATION operating-point freeze. No evaluation-time fitting."""

import argparse
from collections import Counter
import csv
from datetime import UTC, datetime
import hashlib
from importlib.metadata import version
import io
import json
from pathlib import Path
import platform
import struct
import subprocess
from time import perf_counter

from detection_service.research_protocol import detector_semantics as phase2
from detection_service.research_protocol import regime_contract as phase4
from detection_service.research_protocol.adapters import DetectorAdapter, FrozenDetectorContracts, PHASE2_SHA
from detection_service.research_protocol.operating_policy import (
    FIELDS, MEMBERSHIP_SHA, POLICY_ID, REGIME_SHA, THRESHOLD_IDS, OperatingManifest, load_frozen_operating_policy,
)
from detection_service.research_protocol.prediction import PredictionRecord
from detection_service.research_protocol.regime import manifest_hash, require
from detection_service.research_protocol.threshold_selection import ALGORITHM, TIE_POLICY, select_threshold

OUT = phase2.OUT + "/operating_points"
PREREG = OUT + "/predeclared_policy_v1.json"
POLICY = phase2.OUT + "/operating_point_manifest_v1.json"
SCORES = OUT + "/calibration_operating_scores_v1.csv"
DG_SCORES = OUT + "/dg_calibration_predictions_v1.json"
DG_RUN = OUT + "/dg_calibration_run_v1.json"
SELECTED = OUT + "/selected_thresholds_before_diagnostics_v1.json"
EVIDENCE = OUT + "/threshold_freeze_evidence_v1.json"
HASHES = phase2.OUT + "/phase5_artifact_hashes_v1.json"
SCHEMA = phase2.OUT + "/schemas/prediction_operational_schema_v1.json"
CODE = ("detection_service/research_protocol/threshold_selection.py", "detection_service/research_protocol/operating_policy.py",
        "detection_service/research_protocol/freeze_operating_points.py", "detection_service/tests/test_operating_policy.py")
DS_CSV = "artifacts/statistical_v2/calibration/completed_v1/calibration_predictions_v1.csv"
DS_META = "artifacts/statistical_v2/calibration/completed_v1/ds_v2_calibration_manifest_v1.json"
DM_SCORES = "artifacts/models/dm_b_v1/calibration/calibration_scores.json"
DM_META = "artifacts/models/dm_b_v1/calibration/calibration_metadata.json"


def now():
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def git(root, *args):
    return subprocess.check_output(["git", *args], cwd=root).decode("utf-8").strip()


def write_new(root, name, value):
    content = value if isinstance(value, bytes) else phase2.manifest_bytes(value)
    path = Path(root) / name
    require(not path.exists(), "REFUSE_FROZEN_OUTPUT_OVERWRITE")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(content)
    return hashlib.sha256(content).hexdigest()


def prerequisite_checks(root):
    contracts = FrozenDetectorContracts(root)
    phase4.FrozenRegimeContracts(root)
    expected = {phase4.MANIFEST_SCHEMA: "96b3139f49f81bb1b8af284f70754b8bd64e8d060edb443ea88f14fe851acdbc",
                phase4.SAMPLE_SCHEMA: "368b767eefe3346d5b75499ad3bb6c87682fc2736759e0aae859d6ec9ababd69",
                phase4.CONTRACT: REGIME_SHA}
    for name, sha in expected.items():
        require(phase2.sha(Path(root) / name) == sha, "PHASE4_PREREQUISITE_HASH_MISMATCH")
    inventory = phase2.read_json(Path(root) / phase4.HASHES)
    require(all(phase2.sha(Path(root) / name) == sha for name, sha in inventory["sha256"].items()), "PHASE4_PRESERVATION_HASH_MISMATCH")
    return contracts


def accepted_source(contracts, name):
    item = contracts._manifest["accepted_evidence_locations"][name]
    path = phase2.contained(contracts.root, item["local_path"])
    require(path.is_file() and phase2.sha(path) == item["sha256"], "ACCEPTED_CALIBRATION_SCORE_HASH_MISMATCH")
    return path, item["sha256"]


def calibration_membership(root):
    path = Path(root) / phase4.MEMBERSHIP
    require(phase2.sha(path) == MEMBERSHIP_SHA, "CALIBRATION_MANIFEST_HASH_MISMATCH")
    with path.open(encoding="utf-8", newline="") as stream:
        rows = [r for r in csv.DictReader(stream) if r["partition"] == "CALIBRATION"]
    require(len(rows) == 233 and Counter(r["canonical_label"] for r in rows) == {"0": 192, "1": 41}, "CALIBRATION_POPULATION_MISMATCH")
    require(len({r["record_id"] for r in rows}) == 233 and all(r["data_role"] == "CALIBRATION" for r in rows), "CALIBRATION_MEMBERSHIP_CONFLICT")
    return rows


def membership_hash(rows):
    return hashlib.sha256(phase2.canonical_bytes(sorted((r["record_id"], int(r["canonical_label"])) for r in rows))).hexdigest()


def preregistration(root):
    c = prerequisite_checks(root)
    sources = {}
    for role, name in (("ds_scores", DS_CSV), ("ds_metadata", DS_META), ("dm_scores", DM_SCORES), ("dm_metadata", DM_META)):
        path, sha = accepted_source(c, name)
        sources[role] = {"path": path.relative_to(Path(root)).as_posix(), "sha256": sha}
    return {"artifact_version": "operating_policy_predeclaration_v1", "policy_id": POLICY_ID, "algorithm_id": ALGORITHM,
        "target_fpr": .03, "alpha_rational": "3/100", "selection_partition": "CALIBRATION",
        "population": {"total": 233, "attack": 41, "benign": 192}, "K": "floor(3*n_benign/100); n=192 => K=5",
        "comparison": ">=", "tie_policy": TIE_POLICY,
        "edge_policy": "Reject empty/missing/non-finite/duplicate/wrong-partition evidence; bounded probability scores; nextafter(1,+inf) is permitted; never drop rows",
        "threshold_input_fields": FIELDS, "threshold_ids": THRESHOLD_IDS,
        "positive_label_policy": "Positive scores cannot select thresholds; diagnostics only after immutable thresholds are persisted",
        "detector_manifest_sha": PHASE2_SHA, "prediction_schema_sha": phase4.PREDICTION_SHA, "regime_contract_sha": REGIME_SHA,
        "selection_manifest_sha": MEMBERSHIP_SHA, "accepted_sources": sources,
        "dg_inventory": "Only BASE_TRAIN historical predictions found; authorized one-time 233-row CALIBRATION inference required, no download",
        "operational_activation": "Explicit verified policy, prediction_operational_v1 projection; prediction_v1 null lock unchanged",
        "code_sha256": {p: phase2.sha(Path(root) / p) for p in CODE},
        "no_validation_or_future_regime_selection": True, "no_retraining_recalibration_or_ds_reconstruction": True}


def verify_predeclaration(root):
    require(phase2.read_json(Path(root) / PREREG) == preregistration(root), "PREDECLARATION_CODE_OR_POLICY_DRIFT")
    commit = git(root, "log", "-1", "--format=%H", "--", PREREG)
    require(len(commit) == 40, "ALGORITHM_MUST_BE_COMMITTED_BEFORE_REAL_SCORING")
    for path in (*CODE, PREREG):
        blob = subprocess.check_output(["git", "show", commit + ":" + path], cwd=root)
        require((Path(root) / path).read_bytes() == blob, "PREDECLARED_COMMITTED_BYTES_MISMATCH")
    return commit


def align_rows(rows, membership):
    expected = {r["record_id"]: int(r["canonical_label"]) for r in membership}
    actual = {r["sample_id"]: r for r in rows}
    require(len(actual) == len(rows) == 233 and actual.keys() == expected.keys(), "CALIBRATION_SCORE_ID_ALIGNMENT_FAILED")
    require(all(r["partition"] == "CALIBRATION" and type(r["truth_label"]) is int and
                r["truth_label"] == expected[sid] for sid, r in actual.items()), "CALIBRATION_SCORE_LABEL_OR_PARTITION_CONFLICT")
    return [actual[sid] for sid in sorted(actual)]


def historical_scores(contracts, membership):
    ds_path, ds_sha = accepted_source(contracts, DS_CSV)
    ds_meta_path, _ = accepted_source(contracts, DS_META)
    dm_path, dm_sha = accepted_source(contracts, DM_SCORES)
    dm_meta_path, _ = accepted_source(contracts, DM_META)
    ds_meta, dm_meta = phase2.read_json(ds_meta_path), phase2.read_json(dm_meta_path)
    ds = contracts.detector("D_S")
    dm = contracts.detector("D_M-B")
    require(ds_meta["detector_version"] == ds["detector_id"] and ds_meta["calibration_version"] == ds["calibrator_id"]
            and ds_meta["model_binding"]["ds_v2_model.json"] == ds["model_hash"] and ds_meta["prediction_sha256"] == ds_sha
            and ds_meta["manifest_sha256"] == MEMBERSHIP_SHA and ds_meta["partitions_fitted"] == ["CALIBRATION"], "DS_CALIBRATION_PROVENANCE_CONFLICT")
    require(dm_meta["detector_version"] == dm["detector_id"] and dm_meta["calibration_version"] == dm["calibrator_id"]
            and dm_meta["frozen_model_sha256"]["transformer/model.safetensors"] == dm["model_hash"]
            and dm_meta["calibration_manifest_sha256"] == MEMBERSHIP_SHA and dm_meta["partitions_fitted"] == ["CALIBRATION"], "DM_CALIBRATION_PROVENANCE_CONFLICT")
    with ds_path.open(encoding="utf-8", newline="") as stream:
        ds_rows = [dict(sample_id=r["record_id"], truth_label=int(r["label"]), partition=r["partition"],
            score=float(r["calibrated_probability"]), raw_score=float(r["raw_score"]), locator="csv_row:" + str(i + 1))
            for i, r in enumerate(csv.DictReader(stream))]
    dm_value = phase2.read_json(dm_path)
    require(dm_value["scope"] == "CALIBRATION_ONLY", "DM_SCORE_SCOPE_MISMATCH")
    require(hashlib.sha256(b"".join(struct.pack("<d", r["raw_score"]) for r in dm_value["records"])).hexdigest() ==
            dm_meta["raw_probability_sha256"], "DM_RAW_SCORE_PROVENANCE_MISMATCH")
    dm_rows = [dict(sample_id=r["record_id"], truth_label=r["label"], partition="CALIBRATION", score=r["raw_score"],
                   calibrated_score=r["calibrated_probability"], locator="/records/" + str(i)) for i, r in enumerate(dm_value["records"])]
    # Strict finite validation without selecting a threshold or inspecting recall.
    from detection_service.research_protocol.threshold_selection import SelectionScore
    for row in (*ds_rows, *dm_rows):
        SelectionScore.model_validate({k: row[k] for k in ("sample_id", "truth_label", "partition", "score")})
    ds_rows, dm_rows = align_rows(ds_rows, membership), align_rows(dm_rows, membership)
    return ds_rows, dm_rows, {"D_S": {"path": ds_path.relative_to(contracts.root).as_posix(), "sha256": ds_sha},
                             "D_M-B": {"path": dm_path.relative_to(contracts.root).as_posix(), "sha256": dm_sha}}


def acquire_guard_scores(contracts, membership, precommit):
    root = contracts.root
    require(not (root / DG_SCORES).exists() and not (root / DG_RUN).exists(), "GUARD_CALIBRATION_OUTPUT_ALREADY_EXISTS_NO_AUTO_RESCORE")
    # Reuse the source-preserving selected-row loader, never its fitting/training commands.
    from detection_service.scripts.calibrate_semantic_baseline import load_calibration_texts, validate_rows
    validate_rows(membership)
    expected_sources = phase2.read_json(accepted_source(contracts, DM_META)[0])["source_artifact_sha256"]
    require(all(phase2.sha(root / path) == sha for path, sha in expected_sources.items()), "APPROVED_SOURCE_HASH_MISMATCH")
    texts, source_hashes = load_calibration_texts(membership, root)
    require(source_hashes == expected_sources, "CALIBRATION_SOURCE_PROVENANCE_CONFLICT")
    import torch
    torch.manual_seed(1701)
    torch.set_num_threads(8)
    torch.use_deterministic_algorithms(True)
    adapter = DetectorAdapter("D_G", contracts)
    started_at, started = now(), perf_counter()
    records = []
    for i, (row, text) in enumerate(zip(membership, texts)):
        record = adapter.predict(text, sample_id=row["record_id"], truth_label=int(row["canonical_label"]))
        require(record.status == "OK", "GUARD_CALIBRATION_INFERENCE_FAILED_NO_ROW_DROPPING")
        adapter.validate_prediction_record(record)
        records.append(record.model_dump(mode="json"))
        if (i + 1) % 50 == 0:
            print(json.dumps({"phase": "CALIBRATION_GUARD_INFERENCE", "completed": i + 1, "total": 233}), flush=True)
    require(len(records) == 233, "GUARD_CALIBRATION_COUNT_MISMATCH")
    payload = {"artifact_version": "dg_calibration_predictions_v1", "scope": "CALIBRATION_ONLY", "records": records}
    sha = write_new(root, DG_SCORES, payload)
    d = contracts.detector("D_G")
    run = dict(artifact_version="dg_calibration_run_v1", started_at=started_at, completed_at=now(), runtime_seconds=perf_counter() - started,
        execution_commit=git(root, "rev-parse", "HEAD"), predeclared_commit=precommit,
        score_evidence_sha=sha, source_artifact_sha256=source_hashes, selection_manifest_sha=MEMBERSHIP_SHA,
        membership_sha=membership_hash(membership), population={"total": 233, "attack": 41, "benign": 192},
        detector_id=d["detector_id"], model_revision=d["model_revision"], model_sha=d["model_hash"], device="cpu",
        chunking=d["chunking_policy"], aggregation=d["aggregation_policy"], positive_class=d["adversarial_class"],
        preprocessing="UNCHANGED_FROZEN_NATIVE", python=platform.python_version(), packages={k: version(k) for k in ("torch", "transformers", "tokenizers", "pyarrow")},
        model_download=False, training=False, calibration=False, validation_used=False, protected_or_R1_R2_R3_used=False)
    write_new(root, DG_RUN, run)
    aligned = align_rows([dict(sample_id=r["sample_id"], truth_label=r["truth_label"], partition="CALIBRATION", score=r["raw_score"],
        native_vote=r["native_binary_prediction"], locator="/records/" + str(i)) for i, r in enumerate(records)], membership)
    return aligned, {"path": DG_SCORES, "sha256": sha}


def csv_bytes(rows):
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode("utf-8")


def freeze(root=phase2.ROOT):
    root = Path(root).resolve()
    contracts = prerequisite_checks(root)
    precommit = verify_predeclaration(root)
    require(not git(root, "status", "--porcelain"), "CLEAN_PREDECLARED_TREE_REQUIRED_BEFORE_SCORING")
    require(not any((root / p).exists() for p in (POLICY, SCORES, DG_SCORES, DG_RUN, SELECTED, EVIDENCE, HASHES)), "OPERATING_POINTS_ALREADY_STARTED_NO_OVERWRITE")
    membership = calibration_membership(root)
    ds, dm, sources = historical_scores(contracts, membership)
    dg, sources["D_G"] = acquire_guard_scores(contracts, membership, precommit)
    selections = {}
    for label, rows in (("D_S", ds), ("D_M-B", dm), ("D_G", dg)):
        selections[label] = select_threshold([{k: r[k] for k in ("sample_id", "truth_label", "partition", "score")} for r in rows])
    # Persist every selected threshold before accessing positive diagnostic performance.
    write_new(root, SELECTED, {"artifact_version": "selected_thresholds_before_diagnostics_v1", "algorithm_id": ALGORITHM,
        "created_at": now(), "selection_manifest_sha": MEMBERSHIP_SHA, "predeclared_commit": precommit,
        "points": {k: v.model_dump(mode="json") for k, v in selections.items()}})
    print("All three benign-only thresholds persisted; positive diagnostics begin now.", flush=True)
    table = []
    for s, m, g in zip(ds, dm, dg):
        require(s["sample_id"] == m["sample_id"] == g["sample_id"], "ALIGNED_SCORE_ORDER_MISMATCH")
        table.append(dict(sample_id=s["sample_id"], truth_label=s["truth_label"], partition="CALIBRATION",
            ds_calibrated_score=s["score"], dm_b_raw_score=m["score"], dg_raw_score=g["score"], dg_native_vote=g["native_vote"],
            ds_source_locator=s["locator"], dm_b_source_locator=m["locator"], dg_source_locator=g["locator"]))
    score_sha = write_new(root, SCORES, csv_bytes(table))
    points = []
    for label, rows in (("D_S", ds), ("D_M-B", dm), ("D_G", dg)):
        selected = selections[label]
        d = contracts.detector(label)
        tp = sum(r["score"] >= selected.threshold for r in rows if r["truth_label"] == 1)
        points.append(dict(stack_label=label, detector_id=d["detector_id"], threshold_input_score_type=FIELDS[label],
            calibrator_id=d["calibrator_id"], calibrator_sha=d["calibrator_hash"], calibration_used_for_threshold=label == "D_S",
            model_revision=d["model_revision"], model_sha=d["model_hash"], threshold=selected.threshold, threshold_id=THRESHOLD_IDS[label],
            boundary_score=selected.boundary_score, boundary_ties=selected.boundary_ties, benign_count=192, max_allowed_fp=5,
            attained_fp=selected.attained_fp, attained_fpr=selected.attained_fpr, diagnostic_positive_count=41,
            diagnostic_tp=tp, diagnostic_fn=41-tp, diagnostic_recall=tp/41, score_evidence_artifact=SCORES,
            score_evidence_sha=score_sha, freeze_status="FROZEN"))
    value = dict(manifest_version="operating_point_manifest_v1", policy_id=POLICY_ID, algorithm_id=ALGORITHM, status="FROZEN",
        target_fpr=.03, alpha_rational="3/100", decision_operator=">=", tie_policy=TIE_POLICY, selection_partition="CALIBRATION",
        selection_population_id="DATA-PROMOTION-001-CALIBRATION-v1", selection_population_revision=MEMBERSHIP_SHA,
        selection_manifest_hash=MEMBERSHIP_SHA, selection_membership_sha=membership_hash(membership), selection_sample_count=233,
        selection_benign_count=192, selection_attack_count=41, detector_set_manifest_sha=PHASE2_SHA,
        prediction_schema_sha=phase4.PREDICTION_SHA, regime_contract_sha=REGIME_SHA, evidence_kind="AUTHORITATIVE_CALIBRATION",
        predeclared_commit=precommit, predeclared_policy_sha=phase2.sha(root / PREREG), execution_commit=git(root, "rev-parse", "HEAD"),
        created_at=now(), points=points)
    value["manifest_hash"] = manifest_hash(value)
    parsed = OperatingManifest.model_validate({**value, "points": tuple(points)})
    policy_sha = write_new(root, POLICY, parsed.model_dump(mode="json"))
    evidence = dict(artifact_version="threshold_freeze_evidence_v1", algorithm_id=ALGORITHM, alpha=.03, alpha_rational="3/100",
        n_benign=192, K=5, maximum_empirical_fpr=5/192, comparison=">=", tie_policy=TIE_POLICY,
        population_integrity={"total": 233, "attack": 41, "benign": 192, "duplicates": 0, "missing": 0, "label_disagreements": 0},
        source_evidence=sources, threshold_selection_before_diagnostics_sha=phase2.sha(root / SELECTED),
        operating_point_manifest_sha=policy_sha, points=points, selection_attempts=1, positive_performance_used_for_selection=False,
        validation_used=False, R1_R2_R3_used=False)
    write_new(root, EVIDENCE, evidence)
    from detection_service.research_protocol.operating_policy import operational_schema
    policy = load_frozen_operating_policy(root / POLICY, expected_sha=policy_sha, root=root)
    write_new(root, SCHEMA, operational_schema(policy))
    outputs = (POLICY, SCORES, DG_SCORES, DG_RUN, SELECTED, EVIDENCE, SCHEMA, PREREG, *CODE)
    write_new(root, HASHES, {"artifact_version": "phase5_artifact_hashes_v1", "sha256": {p: phase2.sha(root / p) for p in outputs}})
    prerequisite_checks(root)
    load_frozen_operating_policy(root / POLICY, expected_sha=policy_sha, root=root)
    return {"status": "PASS", "policy_sha": policy_sha, "points": points, "predeclared_commit": precommit}


def check(root=phase2.ROOT):
    root = Path(root)
    prerequisite_checks(root)
    inventory = phase2.read_json(root / HASHES)["sha256"]
    require(all(phase2.sha(root / p) == sha for p, sha in inventory.items()), "PHASE5_ARTIFACT_HASH_MISMATCH")
    policy = load_frozen_operating_policy(root / POLICY, expected_sha=inventory[POLICY], root=root)
    return {"status": "PASS", "artifact_hash_checks": len(inventory), "policy_sha": inventory[POLICY],
            "points": [p.model_dump(mode="json") for p in policy.manifest.points]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("predeclare", "freeze", "check"), default="check")
    args = parser.parse_args()
    if args.mode == "predeclare":
        print(json.dumps({"status": "PREDECLARED", "sha": write_new(phase2.ROOT, PREREG, preregistration(phase2.ROOT))}, indent=2))
    else:
        print(json.dumps(freeze() if args.mode == "freeze" else check(), indent=2))
