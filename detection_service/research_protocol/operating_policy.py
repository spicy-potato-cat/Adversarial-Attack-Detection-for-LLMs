"""Read-only frozen-policy consumption. Never imports or fits a selector."""

from dataclasses import dataclass, field
import math
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, ValidationInfo, model_validator

from detection_service.research_protocol import detector_semantics as phase2
from detection_service.research_protocol.adapters import DetectorAdapter, FrozenDetectorContracts, PHASE2_SHA, RULE_IDS
from detection_service.research_protocol.prediction import Binary, Count, Digest, PredictionRecord, Probability
from pydantic import StrictBool
from detection_service.research_protocol.regime import FrozenMetadata, Text, Timestamp, manifest_hash, require
from detection_service.research_protocol.regime_contract import FrozenRegimeContracts, PREDICTION_SHA

POLICY_ID = "operating_policy_v1"
FIELDS = {"D_S": "calibrated_score", "D_M-B": "raw_score", "D_G": "raw_score"}
THRESHOLD_IDS = {"D_S": "ds_v2_op3_cal_v1", "D_M-B": "dm_b_v1_op3_raw_v1", "D_G": "dg_v1_op3_raw_v1"}
REGIME_SHA = "716631bec5e7bbe562acd375c90260f5bf11f92cffb6c6d63a7639908408c149"
MEMBERSHIP_SHA = "9cdd5ecdd80f9ac3c8f05db63742721f4537ca2b64a2fe48f6c2b424b57483a6"
Threshold = Annotated[float, Field(strict=True, ge=0, le=math.nextafter(1.0, math.inf), allow_inf_nan=False)]
_VERIFIED_LOAD = object()


class OperatingPoint(FrozenMetadata):
    stack_label: Literal["D_S", "D_M-B", "D_G"]
    detector_id: Text
    threshold_input_score_type: Literal["calibrated_score", "raw_score"]
    calibrator_id: Text | None
    calibrator_sha: Digest | None
    calibration_used_for_threshold: StrictBool
    model_revision: Text | None
    model_sha: Digest
    threshold: Threshold
    threshold_id: Text
    boundary_score: Probability
    boundary_ties: Count
    benign_count: Literal[192]
    max_allowed_fp: Literal[5]
    attained_fp: Annotated[Count, Field(le=5)]
    attained_fpr: Probability
    diagnostic_positive_count: Literal[41]
    diagnostic_tp: Annotated[Count, Field(le=41)]
    diagnostic_fn: Annotated[Count, Field(le=41)]
    diagnostic_recall: Probability
    score_evidence_artifact: Text
    score_evidence_sha: Digest
    freeze_status: Literal["FROZEN"]

    @model_validator(mode="after")
    def relations(self):
        require(self.threshold_input_score_type == FIELDS[self.stack_label], "THRESHOLD_SCORE_TYPE_MISMATCH")
        require(self.calibration_used_for_threshold == (self.stack_label == "D_S"), "CALIBRATOR_INPUT_POLICY_MISMATCH")
        require(self.threshold_id == THRESHOLD_IDS[self.stack_label] and self.threshold_id != RULE_IDS[self.stack_label], "THRESHOLD_ID_MISMATCH")
        require(self.threshold == math.nextafter(self.boundary_score, math.inf) and self.boundary_ties >= 1, "BOUNDARY_SUCCESSOR_MISMATCH")
        require(self.attained_fpr == self.attained_fp / 192, "ATTAINED_FPR_MISMATCH")
        require(self.diagnostic_tp + self.diagnostic_fn == 41 and self.diagnostic_recall == self.diagnostic_tp / 41,
                "POST_FREEZE_DIAGNOSTIC_COUNT_MISMATCH")
        return self


class OperatingManifest(FrozenMetadata):
    manifest_version: Literal["operating_point_manifest_v1"]
    policy_id: Literal["operating_policy_v1"]
    algorithm_id: Literal["benign_empirical_fpr_budget_v1"]
    status: Literal["FROZEN"]
    target_fpr: Literal[0.03]
    alpha_rational: Literal["3/100"]
    decision_operator: Literal[">="]
    tie_policy: Literal["binary64_nextafter_boundary_toward_positive_infinity"]
    selection_partition: Literal["CALIBRATION"]
    selection_population_id: Text
    selection_population_revision: Digest
    selection_manifest_hash: Digest
    selection_membership_sha: Digest
    selection_sample_count: Literal[233]
    selection_benign_count: Literal[192]
    selection_attack_count: Literal[41]
    detector_set_manifest_sha: Digest
    prediction_schema_sha: Digest
    regime_contract_sha: Digest
    evidence_kind: Literal["AUTHORITATIVE_CALIBRATION", "SYNTHETIC_FIXTURE"]
    predeclared_commit: Annotated[Text, Field(pattern=r"^[0-9a-f]{40}$")]
    predeclared_policy_sha: Digest
    execution_commit: Annotated[Text, Field(pattern=r"^[0-9a-f]{40}$")]
    created_at: Timestamp
    manifest_hash: Digest
    points: tuple[OperatingPoint, ...]

    @model_validator(mode="after")
    def relations(self):
        require(tuple(p.stack_label for p in self.points) == ("D_S", "D_M-B", "D_G"), "PRIMARY_OPERATING_POINTS_REQUIRED")
        require(self.manifest_hash == manifest_hash(self.model_dump(mode="json")), "OPERATING_MANIFEST_SELF_HASH_MISMATCH")
        return self


@dataclass(frozen=True)
class FrozenOperatingPolicy:
    manifest: OperatingManifest
    file_sha: str
    contracts: FrozenDetectorContracts
    engineering_fixture: bool = False
    _verified_load: object = field(default=None, repr=False, compare=False)

    def __post_init__(self):
        proof = self._verified_load
        require(isinstance(proof, tuple) and len(proof) == 5 and proof[0] is _VERIFIED_LOAD
                and proof[1] == self.file_sha and proof[2] == self.manifest.manifest_hash
                and proof[3] is self.contracts and proof[4] == self.engineering_fixture,
                "POLICY_MUST_BE_LOADED_AND_HASH_VERIFIED")

    def point(self, detector_id):
        return next((p for p in self.manifest.points if p.detector_id == detector_id), None)

    def validate_native(self, record):
        require(isinstance(record, PredictionRecord), "NATIVE_PREDICTION_RECORD_REQUIRED")
        require(not self.engineering_fixture or record.metadata.evidence_kind == "SYNTHETIC_FIXTURE", "FIXTURE_POLICY_CANNOT_SCORE_REAL_EVIDENCE")
        point = self.point(record.detector_id)
        require(point is not None, "NOT_A_PRIMARY_OPERATING_DETECTOR")
        DetectorAdapter(point.stack_label, self.contracts).validate_prediction_record(record)
        return point


def load_frozen_operating_policy(path, *, expected_sha, root=phase2.ROOT, engineering_fixture=False):
    """Caller supplies an independently trusted published file hash; no auto-fit."""
    require(type(expected_sha) is str and len(expected_sha) == 64, "EXPECTED_POLICY_HASH_REQUIRED")
    path = Path(path)
    require(path.is_file(), "FROZEN_OPERATING_POLICY_MISSING")
    require(phase2.sha(path) == expected_sha, "OPERATING_POLICY_FILE_HASH_MISMATCH")
    value = phase2.read_json(path)
    value["points"] = tuple(value["points"])
    manifest = OperatingManifest.model_validate(value)
    frozen = FrozenDetectorContracts(root)
    FrozenRegimeContracts(root)
    require(phase2.sha(Path(root) / phase2.OUT / "regime_contract_manifest_v1.json") == REGIME_SHA, "REGIME_CONTRACT_BINDING_MISMATCH")
    require(manifest.detector_set_manifest_sha == PHASE2_SHA, "DETECTOR_MANIFEST_BINDING_MISMATCH")
    require(manifest.prediction_schema_sha == PREDICTION_SHA and manifest.regime_contract_sha == REGIME_SHA, "PROTOCOL_BINDING_MISMATCH")
    require(manifest.selection_manifest_hash == MEMBERSHIP_SHA and manifest.selection_population_revision == MEMBERSHIP_SHA,
            "SELECTION_MANIFEST_BINDING_MISMATCH")
    require(manifest.evidence_kind == ("SYNTHETIC_FIXTURE" if engineering_fixture else "AUTHORITATIVE_CALIBRATION"), "UNAPPROVED_POLICY_EVIDENCE")
    for point in manifest.points:
        identity = frozen.detector(point.stack_label)
        require((point.detector_id, point.model_revision, point.model_sha, point.calibrator_id, point.calibrator_sha) ==
                (identity["detector_id"], identity["model_revision"], identity["model_hash"],
                 identity["calibrator_id"], identity["calibrator_hash"]), "OPERATING_MODEL_CALIBRATOR_BINDING_MISMATCH")
        if not engineering_fixture:
            evidence = phase2.contained(Path(root), point.score_evidence_artifact)
            require(phase2.sha(evidence) == point.score_evidence_sha, "CALIBRATION_SCORE_EVIDENCE_HASH_MISMATCH")
    return FrozenOperatingPolicy(manifest, expected_sha, frozen, engineering_fixture,
                                 (_VERIFIED_LOAD, expected_sha, manifest.manifest_hash, frozen, engineering_fixture))


class OperationalPredictionRecord(PredictionRecord):
    """Explicit versioned projection; the original prediction_v1 remains null-only."""
    schema_version: Literal["prediction_operational_v1"] = "prediction_operational_v1"
    operating_policy_manifest_sha: Digest
    operational_threshold: Threshold | None
    operational_threshold_id: Text | None
    operational_binary_prediction: Binary | None

    @model_validator(mode="after")
    def verified_policy_only(self, info: ValidationInfo):
        policy = (info.context or {}).get("operating_policy")
        require(isinstance(policy, FrozenOperatingPolicy), "VERIFIED_OPERATING_POLICY_REQUIRED")
        require(self.operating_policy_manifest_sha == policy.file_sha, "OPERATING_POLICY_REFERENCE_MISMATCH")
        native = native_prediction(self)
        point = policy.validate_native(native)
        if self.status != "OK":
            require(all(v is None for v in (self.operational_threshold, self.operational_threshold_id,
                                            self.operational_binary_prediction)), "NON_OK_OPERATIONAL_DECISION_FORBIDDEN")
        else:
            score = getattr(self, point.threshold_input_score_type)
            require(score is not None, "THRESHOLD_INPUT_SCORE_MISSING")
            require(self.operational_threshold == point.threshold and self.operational_threshold_id == point.threshold_id,
                    "OPERATIONAL_THRESHOLD_OVERRIDE_FORBIDDEN")
            require(self.operational_binary_prediction == int(score >= point.threshold), "INCORRECT_OPERATIONAL_PREDICTION")
        return self

    def model_copy(self, *, update=None, deep=False):
        require(not update, "FROZEN_OPERATIONAL_PREDICTION_MUTATION")
        return super().model_copy(deep=deep)


def native_prediction(record):
    payload = record.model_dump()
    payload.pop("operating_policy_manifest_sha")
    payload.update(schema_version="prediction_v1", operational_threshold=None,
                   operational_threshold_id=None, operational_binary_prediction=None)
    return PredictionRecord.model_validate(payload)


def apply_operating_policy(record, policy):
    require(isinstance(policy, FrozenOperatingPolicy), "VERIFIED_OPERATING_POLICY_REQUIRED")
    point = policy.validate_native(record)
    payload = record.model_dump()
    payload.update(schema_version="prediction_operational_v1", operating_policy_manifest_sha=policy.file_sha)
    if record.status == "OK":
        score = getattr(record, point.threshold_input_score_type)
        require(score is not None, "THRESHOLD_INPUT_SCORE_MISSING")
        payload.update(operational_threshold=point.threshold, operational_threshold_id=point.threshold_id,
                       operational_binary_prediction=int(score >= point.threshold))
    return OperationalPredictionRecord.model_validate(payload, context={"operating_policy": policy})


def operational_schema(policy):
    require(isinstance(policy, FrozenOperatingPolicy), "VERIFIED_OPERATING_POLICY_REQUIRED")
    schema = OperationalPredictionRecord.model_json_schema()
    schema.update({"$schema": "https://json-schema.org/draft/2020-12/schema", "$id": "urn:research-protocol:prediction-operational:v1",
        "description": "Policy-bound structural projection; full validation additionally requires a verified operating policy context."})
    schema["required"] = list(schema["properties"])
    schema["properties"]["operating_policy_manifest_sha"]["const"] = policy.file_sha
    schema["properties"]["detector_id"]["enum"] = [p.detector_id for p in policy.manifest.points]
    schema["allOf"] = [{"if": {"properties": {"status": {"not": {"const": "OK"}}}},
        "then": {"properties": {k: {"type": "null"} for k in
            ("operational_threshold", "operational_threshold_id", "operational_binary_prediction")}}}]
    for point in policy.manifest.points:
        schema["allOf"].append({"if": {"properties": {"status": {"const": "OK"}, "detector_id": {"const": point.detector_id}}},
            "then": {"properties": {"operational_threshold": {"const": point.threshold},
                                     "operational_threshold_id": {"const": point.threshold_id}},
                "allOf": [{"if": {"properties": {point.threshold_input_score_type: {"type": "number", "minimum": point.threshold}}},
                    "then": {"properties": {"operational_binary_prediction": {"const": 1}}},
                    "else": {"properties": {"operational_binary_prediction": {"const": 0}}}}]}})
    return schema
