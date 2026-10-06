"""Strict Phase-3 representation; no operational policies or detector behavior."""

import json
from typing import Annotated, Literal, get_args

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictFloat, StrictInt, StrictStr, model_validator

SCHEMA_VERSION = "prediction_v1"
METADATA_VERSION = "prediction_metadata_v1"
Status = Literal["OK", "INVALID_INPUT", "ARTIFACT_MISMATCH", "TOKENIZATION_ERROR",
                 "INFERENCE_ERROR", "CALIBRATION_ERROR", "OUTPUT_VALIDATION_ERROR",
                 "UNAVAILABLE", "INSUFFICIENT_INPUT"]
STATUS_VALUES = list(get_args(Status))
Binary = Annotated[StrictInt, Field(ge=0, le=1)]
Count = Annotated[StrictInt, Field(ge=0)]
Probability = Annotated[StrictFloat, Field(ge=0, le=1, allow_inf_nan=False)]
Milliseconds = Annotated[StrictFloat, Field(ge=0, allow_inf_nan=False)]
Digest = Annotated[StrictStr, Field(pattern=r"^[0-9a-f]{64}$")]
Revision = Annotated[StrictStr, Field(pattern=r"^[0-9a-f]{40}$")]


class PredictionMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    binding_mode: Literal["LIVE", "FROZEN_EVIDENCE", "CONTRACT_ONLY"]
    evidence_kind: Literal["LIVE_FROZEN_MODEL", "ACCEPTED_FROZEN_OUTPUT", "SYNTHETIC_FIXTURE"]
    phase2_manifest_sha256: Digest
    runtime_detector_id: StrictStr
    runtime_detector_version: StrictStr
    reference_model_revision: Revision | None
    token_count_basis: Literal["NEXT_TOKEN_TARGETS_EXCLUDING_FIRST", "CONTENT_EXCLUDING_SPECIALS", "UNIQUE_CONTENT"]
    special_tokens_excluded: Count
    latency_basis: Literal["LIVE_WALL_CLOCK", "ACCEPTED_DETECTOR_REPORTED", "UNMEASURED"]
    unlabeled_inference: StrictBool
    source_path: StrictStr | None = None
    source_sha256: Digest | None = None
    source_locator: StrictStr | None = None
    diagnostic_class: Annotated[StrictStr, Field(pattern=r"^[A-Za-z_][A-Za-z0-9_]*$")] | None = None


class PredictionRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    schema_version: Literal["prediction_v1"] = SCHEMA_VERSION
    sample_id: Annotated[StrictStr, Field(min_length=1, max_length=200, pattern=r"\S")]
    truth_label: Binary | None
    detector_id: Annotated[StrictStr, Field(min_length=1)]
    detector_role: Literal["PRIMARY_STATISTICAL", "PRIMARY_SEMANTIC", "PRIMARY_EXTERNAL_GUARD"]
    model_revision: Revision | None
    model_hash: Digest
    raw_score: Probability | None
    raw_score_name: Literal["raw_score"]
    score_direction: Literal["HIGHER_IS_MORE_ADVERSARIAL"]
    calibrated_score: Probability | None
    calibrator_id: StrictStr | None
    native_binary_prediction: Binary | None
    native_decision_rule_id: Annotated[StrictStr, Field(min_length=1)]
    operational_threshold: None = None
    operational_threshold_id: None = None
    operational_binary_prediction: None = None
    status: Status
    error_code: Annotated[StrictStr, Field(pattern=r"^[A-Z][A-Z0-9_]*$")] | None
    latency_ms: Milliseconds | None
    input_tokens: Count | None
    tokens_analyzed: Count | None
    truncated: StrictBool | None
    metadata_version: Literal["prediction_metadata_v1"] = METADATA_VERSION
    metadata: PredictionMetadata

    @model_validator(mode="after")
    def validate_relations(self):
        if (self.truth_label is None) != self.metadata.unlabeled_inference:
            raise ValueError("null truth requires an explicit unlabeled inference workflow")
        if self.status == "OK":
            if any(v is None for v in (self.raw_score, self.native_binary_prediction,
                                      self.input_tokens, self.tokens_analyzed, self.truncated)):
                raise ValueError("OK requires scores, native decision and token coverage")
            if self.error_code is not None:
                raise ValueError("OK cannot carry an error_code")
            if (self.calibrated_score is None) != (self.calibrator_id is None):
                raise ValueError("calibrated score and applied calibrator identity must be paired")
        else:
            if any(v is not None for v in (self.raw_score, self.calibrated_score,
                                          self.calibrator_id, self.native_binary_prediction)):
                raise ValueError("non-OK must not carry scores or a fabricated decision")
            if self.error_code is None:
                raise ValueError("non-OK requires an error_code")
        if self.input_tokens is not None and self.tokens_analyzed is not None:
            if self.tokens_analyzed > self.input_tokens:
                raise ValueError("analyzed tokens exceed unique input coverage")
        if self.latency_ms is None and self.metadata.latency_basis != "UNMEASURED":
            raise ValueError("measured latency basis requires a measurement")
        if self.latency_ms is not None and self.metadata.latency_basis == "UNMEASURED":
            raise ValueError("unmeasured latency cannot be fabricated")
        return self

    def deterministic_json(self):
        return json.dumps(self.model_dump(mode="json"), sort_keys=True, separators=(",", ":"),
                          ensure_ascii=True, allow_nan=False)


def prediction_schema():
    schema = PredictionRecord.model_json_schema()
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema["$id"] = "urn:research-protocol:prediction:v1"
    schema["required"] = list(schema["properties"])
    null = {"type": "null"}
    schema["allOf"] = [
        {"if": {"properties": {"status": {"const": "OK"}}},
         "then": {"properties": {"raw_score": {"type": "number", "minimum": 0, "maximum": 1},
             "native_binary_prediction": {"type": "integer", "minimum": 0, "maximum": 1},
             "input_tokens": {"type": "integer", "minimum": 0},
             "tokens_analyzed": {"type": "integer", "minimum": 0},
             "truncated": {"type": "boolean"}, "error_code": null}},
         "else": {"properties": {"raw_score": null, "calibrated_score": null, "calibrator_id": null,
             "native_binary_prediction": null, "error_code": {"type": "string"}}}},
        {"if": {"properties": {"truth_label": null}},
         "then": {"properties": {"metadata": {"properties": {"unlabeled_inference": {"const": True}}}}},
         "else": {"properties": {"metadata": {"properties": {"unlabeled_inference": {"const": False}}}}}},
        {"if": {"properties": {"calibrated_score": null}},
         "then": {"properties": {"calibrator_id": null}},
         "else": {"properties": {"calibrator_id": {"type": "string"}}}},
    ]
    return schema
