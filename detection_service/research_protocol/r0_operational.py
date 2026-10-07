"""Verified historical OOF score projection under the immutable Phase-5 policy.

This is not a live/final-model PredictionRecord. Its input provenance remains OOF
or frozen development evidence; the original native prediction lock is untouched.
"""

import argparse
import json
from pathlib import Path

import numpy as np
from scipy.special import expit
from pydantic import model_validator, ValidationInfo

from detection_service.research_protocol import detector_semantics as files
from detection_service.research_protocol import r0_reproduction as historical
from detection_service.research_protocol.alignment import (
    AlignedEvaluation, EvaluationProvenance, OP_SCHEMA_SHA, POLICY_SHA, digest,
)
from detection_service.research_protocol.core_metrics import evaluate_core
from detection_service.research_protocol.cross_regime import cross_regime_matrix, result_bundle
from detection_service.research_protocol.operating_policy import FrozenOperatingPolicy, load_frozen_operating_policy
from detection_service.research_protocol.prediction import Binary, Digest, Probability
from detection_service.research_protocol.regime import FrozenMetadata, Text, require
from detection_service.research_protocol.uncertainty import BootstrapConfig, bootstrap_metrics

OUT = files.OUT + "/r0"
POLICY = files.OUT + "/operating_point_manifest_v1.json"
HASHES = files.OUT + "/phase14_artifact_hashes_v1.json"
REPORT = "reviews/EXP_PROTOCOL_001_R0_OPERATIONAL_BASELINE_v1.md"
CODE = ("detection_service/research_protocol/r0_operational.py", "detection_service/tests/test_r0_operational.py")
THRESHOLDS = (0.5585373573968287, 0.0004967087297700347, 0.21291141211986545)
IDS = ("ds_v2_op3_cal_v1", "dm_b_v1_op3_raw_v1", "dg_v1_op3_raw_v1")


def verified_policy(root=files.ROOT):
    policy = load_frozen_operating_policy(Path(root)/POLICY, expected_sha=POLICY_SHA, root=root)
    require(tuple(p.threshold for p in policy.manifest.points) == THRESHOLDS, "FROZEN_THRESHOLDS_CHANGED")
    require(tuple(p.threshold_id for p in policy.manifest.points) == IDS, "FROZEN_THRESHOLD_IDS_CHANGED")
    return policy


def calibrate_ds(raw, policy):
    """Exactly the frozen sigmoid-on-clipped-log-odds transform; never fitting."""
    require(isinstance(policy, FrozenOperatingPolicy), "VERIFIED_OPERATING_POLICY_REQUIRED")
    identity = policy.contracts.detector("D_S")
    path = files.contained(policy.contracts.root, identity["calibrator_artifact"])
    require(files.sha(path) == identity["calibrator_hash"], "D_S_CALIBRATOR_DRIFT")
    params = files.read_json(path)
    require(params == identity["calibrator_parameters"] and params["epsilon"] == 1e-12,
            "D_S_CALIBRATION_PROVENANCE_CONFLICT")
    values = np.asarray(raw, dtype=float)
    require(values.ndim == 1 and np.isfinite(values).all() and ((values >= 0) & (values <= 1)).all(),
            "INVALID_RAW_OOF_SCORE")
    clipped = np.clip(values, params["epsilon"], 1-params["epsilon"])
    return expit(params["slope"]*(np.log(clipped)-np.log1p(-clipped))+params["intercept"])


class HistoricalOperationalScore(FrozenMetadata):
    projection_version: str = "historical_operational_score_v1"
    sample_id: Text
    truth_label: Binary
    detector_id: Text
    lineage_id: Text
    model_evidence_kind: Text
    source_artifact_path: Text
    source_artifact_sha: Digest
    import_manifest_sha: Digest
    raw_score: Probability
    calibrated_score: Probability | None
    calibrator_id: Text | None
    calibrator_sha: Digest | None
    status: Text
    operational_threshold: float | None
    operational_threshold_id: Text | None
    operational_binary_prediction: Binary | None
    operating_policy_manifest_sha: Digest

    @model_validator(mode="after")
    def policy_gate(self, info: ValidationInfo):
        policy = (info.context or {}).get("operating_policy")
        require(isinstance(policy, FrozenOperatingPolicy) and not policy.engineering_fixture,
                "VERIFIED_AUTHORITATIVE_POLICY_REQUIRED")
        require(self.projection_version == "historical_operational_score_v1", "HISTORICAL_PROJECTION_VERSION")
        require(self.operating_policy_manifest_sha == policy.file_sha == POLICY_SHA, "POLICY_BINDING_CONFLICT")
        point = policy.point(self.detector_id)
        require(point is not None, "PRIMARY_DETECTOR_REQUIRED")
        expected_kind = "FROZEN_DEVELOPMENT_INFERENCE" if self.detector_id == "dg_v1" else "OOF"
        require(self.model_evidence_kind == expected_kind, "OOF_PROVENANCE_REQUIRED")
        if self.detector_id == "ds_v2":
            require((self.calibrator_id, self.calibrator_sha) == (point.calibrator_id, point.calibrator_sha),
                    "CALIBRATOR_BINDING_CONFLICT")
            require(self.calibrated_score is not None and abs(self.calibrated_score-calibrate_ds([self.raw_score], policy)[0]) <= 1e-12,
                    "D_S_CALIBRATION_PROVENANCE_CONFLICT")
        else:
            require(self.calibrated_score is None and self.calibrator_id is None and self.calibrator_sha is None,
                    "RAW_SCORE_POLICY_REQUIRED")
        require(self.status in ("OK", "NON_OK"), "UNKNOWN_SCORE_STATUS")
        if self.status != "OK":
            require(self.operational_threshold is None and self.operational_threshold_id is None
                    and self.operational_binary_prediction is None, "NON_OK_OPERATIONAL_DECISION_FORBIDDEN")
        else:
            score = self.calibrated_score if point.stack_label == "D_S" else self.raw_score
            require((self.operational_threshold, self.operational_threshold_id) == (point.threshold, point.threshold_id),
                    "OPERATIONAL_THRESHOLD_OVERRIDE_FORBIDDEN")
            require(self.operational_binary_prediction == int(score >= point.threshold), "INCORRECT_OPERATIONAL_PREDICTION")
        return self


def score_records(history, policy):
    import_sha = files.sha(history["root"]/historical.IMPORT)
    require((history["root"]/historical.IMPORT).read_bytes() == files.manifest_bytes(history["import_manifest"]),
            "ACCEPTED_IMPORT_MANIFEST_DRIFT")
    records = []
    for name, detector_id in historical.MAPPING.items():
        source = history["detectors"][name]
        calibrated = calibrate_ds([r["score"] for r in source], policy) if detector_id == "ds_v2" else None
        point = policy.point(detector_id)
        # Inspect the actual accepted CSV, not only its normalized score view.
        original = historical.read_csv(history["root"]/history["paths"][name])
        if detector_id == "ds_v2":
            supplied = {r["sample_id"]: r for r in original if r.get("scorer") == "S0"}
            for index, row in enumerate(source):
                value = supplied.get(row["sample_id"], {})
                for key in ("calibrated_score", "calibrated_probability"):
                    if value.get(key) not in (None, ""):
                        require(abs(float(value[key])-float(calibrated[index])) <= 1e-12,
                                "D_S_CALIBRATION_PROVENANCE_CONFLICT")
        for index, row in enumerate(source):
            cal = float(calibrated[index]) if calibrated is not None else None
            score = cal if calibrated is not None else row["score"]
            payload = dict(sample_id=row["sample_id"], truth_label=row["truth_label"], detector_id=detector_id,
                lineage_id=row["lineage_group"], model_evidence_kind="FROZEN_DEVELOPMENT_INFERENCE" if detector_id == "dg_v1" else "OOF",
                source_artifact_path=history["paths"][name], source_artifact_sha=history["hashes"][history["paths"][name]],
                import_manifest_sha=import_sha, raw_score=row["score"], calibrated_score=cal,
                calibrator_id=point.calibrator_id if calibrated is not None else None,
                calibrator_sha=point.calibrator_sha if calibrated is not None else None, status="OK",
                operational_threshold=point.threshold, operational_threshold_id=point.threshold_id,
                operational_binary_prediction=int(score >= point.threshold), operating_policy_manifest_sha=policy.file_sha)
            records.append(HistoricalOperationalScore.model_validate(payload, context={"operating_policy": policy}))
    order = {v: i for i, v in enumerate(historical.MAPPING.values())}
    return tuple(sorted(records, key=lambda r: (r.sample_id, order[r.detector_id])))


def align_operational(history, records, policy):
    expected = score_records(history, policy)
    require(tuple(r.model_dump() for r in records) == tuple(r.model_dump() for r in expected),
            "STRICT_COMPLETE_HISTORICAL_SCORE_BINDING_REQUIRED")
    base = historical.align_history(history, historical.historical_decisions(history), "3PCT")
    decisions = {(r.sample_id, r.detector_id): r.operational_binary_prediction for r in records}
    provenance = base.provenance.model_dump()
    provenance.update(decision_view="OPERATIONAL", operating_policy_sha=policy.file_sha,
        operational_prediction_schema_sha=OP_SCHEMA_SHA, operational_thresholds=THRESHOLDS, operational_threshold_ids=IDS,
        prediction_batch_sha=digest([r.model_dump(mode="json") for r in records]),
        explicit_decisions_sha=None, explicit_provenance_id=None)
    payload = base.model_dump()
    payload["provenance"] = EvaluationProvenance.model_validate(provenance).model_dump()
    for row in payload["rows"]:
        row["decisions"] = tuple(decisions[(row["sample_id"], d)] for d in base.provenance.primary_detector_ids)
    payload.pop("alignment_sha")
    return AlignedEvaluation.model_validate(dict(**payload, alignment_sha=digest(payload))).require_complete()


def reconstruct(root=files.ROOT):
    history = historical.load_history(root)
    policy = verified_policy(root)
    records = score_records(history, policy)
    table = align_operational(history, records, policy)
    metrics = evaluate_core(table)
    ids = table.provenance.primary_detector_ids
    attack_names = [f"individual/{d}/fnr" for d in ids]
    attack_names += [f"pair/{p.left_detector}/{p.right_detector}/jfn" for p in metrics.common_mode.pairs]
    attack_names += ["all_three/jfn"]
    attack_names += [f"recovery/{d}/{name}" for d in ids for name in ("unique_catch_rate", "conditional_recovery")]
    attack = bootstrap_metrics(table, attack_names, BootstrapConfig(unit="LINEAGE_CLUSTERED", domain="ATTACK_ONLY"))
    benign = bootstrap_metrics(table, [f"individual/{d}/fpr" for d in ids],
        BootstrapConfig(unit="LINEAGE_CLUSTERED", domain="BENIGN_ONLY"))
    bundle = result_bundle(table, history["manifest"], "OPERATIONAL_FIXED_V1", uncertainty=(attack, benign))
    outputs = {
        OUT+"/r0_operational_predictions_v1.csv": historical.csv_bytes([r.model_dump(mode="json") for r in records]),
        OUT+"/r0_operational_metrics_v1.json": files.manifest_bytes(metrics.model_dump(mode="json")),
        OUT+"/r0_operational_uncertainty_v1.json": files.manifest_bytes({"attack": attack.model_dump(mode="json"), "benign": benign.model_dump(mode="json")}),
        OUT+"/r0_operational_result_bundle_v1.json": files.manifest_bytes(bundle.model_dump(mode="json")),
        OUT+"/r0_operational_cross_regime_matrix_v1.json": files.manifest_bytes(cross_regime_matrix((bundle,), reference_slot="R0")),
    }
    text = "# EXP-PROTOCOL-001 R0 Operational Baseline\n\n"
    text += "Status: PASS. View: OPERATIONAL_FIXED_V1; decisions: OPERATIONAL.\n\n"
    text += "Population: 1,135; attacks: 183; benign: 952. No inference or fitting.\n\n"
    text += "D_S: accepted raw OOF evidence transformed by the hash-verified frozen ds_v2_cal_v1 sigmoid mapping. D_M-B: raw ATTACK OOF softmax. D_G: frozen development raw maximum malicious chunk probability, NOT native OR-of-argmax.\n\n"
    text += "This narrow historical-score projection is NOT a final-model PredictionRecord. Phase-3 null locks and Phase-5 live activation remain unchanged. Verified FrozenOperatingPolicy gates the projection; all rows must match accepted sources exactly.\n\n"
    text += "Exact thresholds and IDs (inclusive >=):\n\n"
    for point in policy.manifest.points:
        text += f"- {point.stack_label}: {point.threshold!r}; {point.threshold_id}; {point.threshold_input_score_type}.\n"
    text += "\nThe 3% figure is the CALIBRATION selection budget, not a guaranteed R0 FPR. Thresholds were NOT reselected. Historical descriptive views remain separate and unchanged; no direct improvement claim is made across unlike policies.\n\n"
    text += "Core metrics include every numerator/denominator, eight patterns in S/M/G miss-bit order, unique catches, conditional recovery, and strict complete coverage:\n\n```json\n"
    text += json.dumps(metrics.model_dump(mode="json"), indent=2) + "\n```\n\nProduction intervals: 1,000 replicates, seed 1701, PCG64, 95% linear-percentile; attack/benign lineage-clustered domains; no historical RNG replay.\n\n```json\n"
    text += json.dumps({"attack": attack.model_dump(mode="json"), "benign": benign.model_dump(mode="json")}, indent=2) + "\n```\n\nR1/R2/R3 NOT_RUN. Cycle 2 DEFERRED. No protected data used.\n"
    outputs[REPORT] = text.encode("ascii")
    return outputs, table, metrics, bundle


def freeze(root=files.ROOT):
    root = Path(root)
    outputs, table, metrics, bundle = reconstruct(root)
    require(not any((root/p).exists() for p in (*outputs, HASHES)), "REFUSE_PHASE14_OVERWRITE")
    for path, data in outputs.items():
        (root/path).parent.mkdir(parents=True, exist_ok=True)
        with (root/path).open("xb") as stream:
            stream.write(data)
    inventory = dict(artifact_version="phase14_artifact_hashes_v1", source_commit="f533c106765041932271b56c8ccfa30d1efe691c",
        sha256={p: files.sha(root/p) for p in (*outputs, *CODE)})
    with (root/HASHES).open("xb") as stream:
        stream.write(files.manifest_bytes(inventory))
    return {"status": "PASS", "hash_checks": len(inventory["sha256"]), "population": len(table.rows),
            "individual": metrics.individual.model_dump(mode="json")}


def check(root=files.ROOT):
    root = Path(root)
    inventory = files.read_json(root/HASHES)["sha256"]
    require(all(files.sha(root/p) == h for p, h in inventory.items()), "PHASE14_ARTIFACT_DRIFT")
    outputs, _, _, _ = reconstruct(root)
    require(all((root/p).read_bytes() == b for p, b in outputs.items()), "PHASE14_RECONSTRUCTION_DRIFT")
    return {"status": "PASS", "hash_checks": len(inventory), "byte_identical": True}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("freeze", "check"), default="check")
    print(json.dumps(freeze() if parser.parse_args().mode == "freeze" else check(), indent=2))
