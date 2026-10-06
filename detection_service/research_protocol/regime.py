"""Strict metadata-only regime, provenance and lineage contracts."""

from datetime import datetime
import hashlib
import json
from typing import Annotated, Literal, get_args

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictStr, field_validator, model_validator

from detection_service.research_protocol.prediction import Binary, Count, Digest

MANIFEST_VERSION = "regime_manifest_v1"
RECORD_VERSION = "regime_sample_v1"
PROTOCOL_VERSION = "EXP-PROTOCOL-001_PHASE-4_v1"
ThreatRegime = Literal["R0_NON_ADAPTIVE", "R1_SHIFTED_UNSEEN", "R2_SINGLE_DETECTOR_TARGETED", "R3_ENSEMBLE_TARGETED"]
Partition = Literal["BASE_TRAIN", "CALIBRATION", "VALIDATION", "META_TRAIN", "INTERNAL_TEST",
                    "FROZEN_EXTERNAL", "FINAL_TEST", "ATTACK_GENERATION", "QUARANTINE"]
Target = Literal["D_S", "D_M-B", "D_G", "ALL"]
LineageStatus = Literal["SOURCE_PROVIDED", "DERIVED_FROM_PARENT", "CANONICAL_DUPLICATE_GROUP", "SINGLETON_FALLBACK", "UNKNOWN"]
ProvenanceStatus = Literal["COMPLETE", "PARTIAL", "UNKNOWN", "NOT_VERIFIED", "SYNTHETIC_FIXTURE"]
Text = Annotated[StrictStr, Field(min_length=1, max_length=500, pattern=r"\S")]
SampleID = Annotated[StrictStr, Field(min_length=1, max_length=200, pattern=r"\S")]
Timestamp = Annotated[StrictStr, Field(pattern=r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")]
Definition = Annotated[StrictStr, Field(pattern=r"^[A-Z][A-Z0-9_]*_V[1-9][0-9]*$")]


class RegimeContractError(ValueError):
    pass


def require(condition, code):
    if not condition:
        raise RegimeContractError(code)


def canonical_bytes(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=True, allow_nan=False,
                      separators=(",", ":")).encode("utf-8")


def manifest_hash(payload):
    return hashlib.sha256(canonical_bytes({k: v for k, v in payload.items() if k != "manifest_hash"})).hexdigest()


def experiment_id(payload):
    # Timestamps/lifecycle/notes do not define experimental membership or identity.
    identity = {k: v for k, v in payload.items() if k not in
                ("experiment_id", "manifest_hash", "created_at", "status", "notes")}
    identity["samples"] = [{k: v for k, v in row.items() if k != "created_at"}
                           for row in identity["samples"]]
    return "EXP-" + payload["threat_regime"].split("_")[0] + "-" + hashlib.sha256(canonical_bytes(identity)).hexdigest()


class FrozenMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True, revalidate_instances="always")

    def model_copy(self, *, update=None, deep=False):
        require(not update or getattr(self, "status", None) != "FROZEN", "FROZEN_MANIFEST_MUTATION")
        if update:
            return type(self).model_validate({**self.model_dump(), **update})
        return super().model_copy(deep=deep)

    @field_validator("created_at", check_fields=False)
    @classmethod
    def valid_timestamp(cls, value):
        datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
        return value


class EvidenceReference(FrozenMetadata):
    role: Text
    path: Text
    sha256: Digest

    @field_validator("path")
    @classmethod
    def relative_path(cls, value):
        from pathlib import PurePosixPath
        require(not PurePosixPath(value).is_absolute() and ".." not in PurePosixPath(value).parts
                and ":" not in value and "\\" not in value, "INVALID_EVIDENCE_PATH")
        return value


class DatasetSource(FrozenMetadata):
    dataset_id: Text
    dataset_revision: Text
    source: Text
    source_revision: Text


class ParentReference(FrozenMetadata):
    sample_id: SampleID
    lineage_id: Text
    dataset_id: Text
    dataset_revision: Text
    source: Text
    source_native_id: Text | None
    provenance_status: ProvenanceStatus
    evidence_role: Text
    evidence_locator: Text


class RegimeSample(FrozenMetadata):
    record_version: Literal["regime_sample_v1"] = RECORD_VERSION
    sample_id: SampleID
    dataset_id: Text
    dataset_revision: Text
    partition: Partition
    threat_regime: ThreatRegime
    source: Text
    source_native_id: Text | None
    truth_label: Binary
    is_adversarial: StrictBool
    attack_family: Text | None
    attack_family_provenance: Literal["SOURCE_PROVIDED", "PROTOCOL_DECLARED", "ACCEPTED_METADATA", "UNKNOWN", "NOT_APPLICABLE"]
    target_detector: Target | None
    attack_method: Text | None
    attack_method_revision: Text | None
    generator_type: Literal["MODEL", "RULE_BASED", "HUMAN", "DATASET_SOURCE", "OTHER"] | None
    generator_model: Text | None
    generator_system: Text | None
    generator_revision: Text | None
    generated_sample: StrictBool
    generation_evaluation_status: Literal["NOT_APPLICABLE", "PENDING", "COMPLETED"]
    parent_sample_id: SampleID | None
    lineage_id: Text | None
    lineage_provenance_status: LineageStatus
    lineage_justification: Text | None
    attack_success_definition: Definition | None
    attack_success: StrictBool | None
    valid_attack_attempt: StrictBool | None
    created_at: Timestamp
    provenance_status: ProvenanceStatus
    outer_fold: Count | None

    @model_validator(mode="after")
    def relations(self):
        require(self.is_adversarial == bool(self.truth_label), "TRUTH_LABEL_CONFLICT")
        targeted = self.threat_regime.startswith(("R2_", "R3_"))
        if not targeted:
            require(self.target_detector is None, "NON_TARGETED_REGIME_HAS_TARGET")
        elif self.threat_regime.startswith("R2_"):
            require(self.target_detector in ("D_S", "D_M-B", "D_G"), "R2_REQUIRES_SINGLE_PRIMARY_TARGET")
        else:
            require(self.target_detector == "ALL", "R3_REQUIRES_ALL_TARGET")
        require((self.attack_method is None) == (self.attack_method_revision is None), "ATTACK_METHOD_REVISION_PAIR")
        if targeted:
            require(all(v is not None for v in (self.attack_method, self.attack_method_revision,
                self.lineage_id, self.valid_attack_attempt, self.attack_success_definition)), "TARGETED_ATTACK_METADATA_REQUIRED")
            require(self.generation_evaluation_status != "NOT_APPLICABLE", "TARGETED_EVALUATION_STATE_REQUIRED")
        if self.generation_evaluation_status == "COMPLETED":
            require(self.attack_success is not None and self.valid_attack_attempt is not None, "COMPLETED_ATTACK_OUTCOME_REQUIRED")
        elif self.generation_evaluation_status == "PENDING":
            require(self.attack_success is None, "PENDING_ATTACK_HAS_OUTCOME")
        else:
            require(self.attack_success is None and self.valid_attack_attempt is None
                    and self.attack_success_definition is None, "INAPPLICABLE_ATTACK_HAS_OUTCOME")
        if self.attack_success is not None:
            require(self.attack_success_definition is not None, "ATTACK_SUCCESS_DEFINITION_REQUIRED")
        if self.attack_success is True:
            require(self.valid_attack_attempt is True, "SUCCESS_REQUIRES_VALID_ATTEMPT")
        if self.generator_type == "MODEL":
            require(self.generator_model is not None and self.generator_revision is not None
                    and self.generator_system is None, "MODEL_GENERATOR_IDENTITY_REQUIRED")
        elif self.generator_type is None:
            require(all(v is None for v in (self.generator_model, self.generator_system, self.generator_revision)), "GENERATOR_TYPE_REQUIRED")
        else:
            require(self.generator_model is None, "NON_MODEL_GENERATOR_HAS_MODEL")
            require((self.generator_system is None) == (self.generator_revision is None), "GENERATOR_REVISION_PAIR")
            if self.generator_type in ("RULE_BASED", "OTHER"):
                require(self.generator_system is not None, "SYSTEM_GENERATOR_IDENTITY_REQUIRED")
        if self.generated_sample:
            require(self.parent_sample_id is not None and self.lineage_id is not None
                    and self.generator_type is not None, "GENERATED_DESCENDANT_PROVENANCE_REQUIRED")
            require(self.lineage_provenance_status == "DERIVED_FROM_PARENT", "GENERATED_LINEAGE_STATUS_REQUIRED")
        require(self.parent_sample_id != self.sample_id, "SELF_PARENT_FORBIDDEN")
        if self.parent_sample_id is not None:
            require(self.lineage_id is not None and self.lineage_provenance_status == "DERIVED_FROM_PARENT", "PARENT_LINEAGE_REQUIRED")
        if self.lineage_provenance_status == "DERIVED_FROM_PARENT":
            require(self.parent_sample_id is not None, "DERIVED_LINEAGE_PARENT_REQUIRED")
        if self.lineage_provenance_status == "UNKNOWN":
            require(self.lineage_id is None and self.parent_sample_id is None, "UNKNOWN_LINEAGE_HAS_ID")
        else:
            require(self.lineage_id is not None, "KNOWN_LINEAGE_ID_REQUIRED")
        if self.lineage_provenance_status == "SINGLETON_FALLBACK":
            require(not targeted and self.parent_sample_id is None and self.lineage_justification is not None,
                    "SINGLETON_JUSTIFICATION_REQUIRED")
        if self.attack_family_provenance == "UNKNOWN":
            require(self.attack_family == "UNKNOWN", "UNKNOWN_ATTACK_FAMILY_REQUIRED")
        elif self.attack_family_provenance == "NOT_APPLICABLE":
            require(self.attack_family is None, "INAPPLICABLE_ATTACK_FAMILY_HAS_VALUE")
        else:
            require(self.attack_family is not None, "ATTACK_FAMILY_PROVENANCE_REQUIRES_VALUE")
        return self


class RegimeManifest(FrozenMetadata):
    manifest_version: Literal["regime_manifest_v1"] = MANIFEST_VERSION
    protocol_version: Literal["EXP-PROTOCOL-001_PHASE-4_v1"] = PROTOCOL_VERSION
    experiment_id: Text
    dataset_id: Text
    dataset_revision: Text
    partition: Partition
    threat_regime: ThreatRegime
    dataset_source: Text
    dataset_source_revision: Text
    dataset_sources: tuple[DatasetSource, ...]
    created_at: Timestamp
    manifest_hash: Digest
    sample_count: Count
    attack_count: Count
    benign_count: Count
    primary_detector_set_id: Text
    primary_detector_manifest_sha: Digest
    prediction_schema_version: Literal["prediction_v1"]
    prediction_schema_sha: Digest
    status: Literal["DRAFT", "FROZEN", "COMPLETED", "INVALID", "ARCHIVED"]
    evidence_kind: Literal["ACCEPTED_METADATA", "SYNTHETIC_FIXTURE"]
    notes: tuple[Text, ...]
    evidence: tuple[EvidenceReference, ...]
    external_parents: tuple[ParentReference, ...]
    samples: tuple[RegimeSample, ...]

    @field_validator("samples", "dataset_sources", "evidence", "external_parents", "notes", mode="before")
    @classmethod
    def immutable_sequences(cls, value):
        require(isinstance(value, (list, tuple)), "METADATA_SEQUENCE_REQUIRED")
        return tuple(value)

    @model_validator(mode="after")
    def relations(self):
        rows = {r.sample_id: r for r in self.samples}
        require(len(rows) == len(self.samples), "DUPLICATE_SAMPLE_ID")
        require(self.sample_count == len(rows) and self.attack_count == sum(r.truth_label for r in self.samples)
                and self.benign_count == sum(1 - r.truth_label for r in self.samples), "MANIFEST_COUNT_CONFLICT")
        require(tuple(sorted(rows)) == tuple(rows), "NON_CANONICAL_SAMPLE_ORDER")
        sources = {(d.dataset_id, d.dataset_revision): d for d in self.dataset_sources}
        require(len(sources) == len(self.dataset_sources) and bool(sources), "DATASET_SOURCE_ID_CONFLICT")
        require(tuple(sorted(sources)) == tuple(sources), "NON_CANONICAL_SOURCE_ORDER")
        evidence = {e.role: e for e in self.evidence}
        require(len(evidence) == len(self.evidence), "DUPLICATE_EVIDENCE_ROLE")
        require(tuple(sorted(evidence)) == tuple(evidence), "NON_CANONICAL_EVIDENCE_ORDER")
        parents = {p.sample_id: p for p in self.external_parents}
        require(len(parents) == len(self.external_parents) and not (parents.keys() & rows.keys()), "PARENT_ID_CONFLICT")
        require(tuple(sorted(parents)) == tuple(parents), "NON_CANONICAL_PARENT_ORDER")
        for parent in parents.values():
            require(parent.evidence_role in evidence, "PARENT_EVIDENCE_MISSING")
            require((parent.provenance_status == "SYNTHETIC_FIXTURE") == (self.evidence_kind == "SYNTHETIC_FIXTURE"), "PARENT_EVIDENCE_KIND_CONFLICT")
        used_parents = set()
        lineages = {}
        for row in self.samples:
            require(row.partition == self.partition and row.threat_regime == self.threat_regime, "SAMPLE_REGIME_PARTITION_CONFLICT")
            source = sources.get((row.dataset_id, row.dataset_revision))
            require(source is not None and row.source == source.source, "SAMPLE_DATASET_SOURCE_CONFLICT")
            require((row.provenance_status == "SYNTHETIC_FIXTURE") == (self.evidence_kind == "SYNTHETIC_FIXTURE"), "SYNTHETIC_EVIDENCE_CONFLICT")
            if row.parent_sample_id is not None:
                parent = rows.get(row.parent_sample_id) or parents.get(row.parent_sample_id)
                require(parent is not None and parent.lineage_id == row.lineage_id, "PARENT_LINEAGE_CONFLICT")
                if row.parent_sample_id in parents:
                    used_parents.add(row.parent_sample_id)
            if row.lineage_id is not None:
                lineages.setdefault(row.lineage_id, []).append(row)
        require(used_parents == parents.keys(), "UNREFERENCED_EXTERNAL_PARENT")
        for lineage in lineages.values():
            require(len(lineage) == 1 or not any(r.lineage_provenance_status == "SINGLETON_FALLBACK" for r in lineage), "SINGLETON_LINEAGE_SHARED")
        for row in self.samples:
            seen = set()
            current = row
            while current.parent_sample_id in rows:
                require(current.sample_id not in seen, "CYCLIC_PARENT_GRAPH")
                seen.add(current.sample_id)
                current = rows[current.parent_sample_id]
        payload = self.model_dump(mode="json")
        require(self.experiment_id == experiment_id(payload), "EXPERIMENT_ID_MISMATCH")
        require(self.manifest_hash == manifest_hash(payload), "MANIFEST_HASH_MISMATCH")
        return self

    def deterministic_json(self):
        return canonical_bytes(self.model_dump(mode="json")).decode("utf-8")


def create_manifest(**payload):
    """Create a new revision, never edit an already frozen object in place."""
    rows = tuple(sorted((RegimeSample.model_validate(r) for r in payload["samples"]), key=lambda r: r.sample_id))
    payload["samples"] = [r.model_dump(mode="json") for r in rows]
    payload["dataset_sources"] = sorted((d.model_dump(mode="json") if isinstance(d, DatasetSource) else d
                                          for d in payload["dataset_sources"]), key=lambda d: (d["dataset_id"], d["dataset_revision"]))
    for name, cls in (("evidence", EvidenceReference), ("external_parents", ParentReference)):
        payload[name] = sorted((v.model_dump(mode="json") if isinstance(v, cls) else v for v in payload[name]),
                               key=lambda v: v["role" if name == "evidence" else "sample_id"])
    payload.setdefault("manifest_version", MANIFEST_VERSION)
    payload.setdefault("protocol_version", PROTOCOL_VERSION)
    payload.setdefault("sample_count", len(rows))
    payload.setdefault("attack_count", sum(r.truth_label for r in rows))
    payload.setdefault("benign_count", sum(1 - r.truth_label for r in rows))
    payload["experiment_id"] = experiment_id(payload)
    payload["manifest_hash"] = manifest_hash(payload)
    return RegimeManifest.model_validate(payload)


def sample_schema():
    schema = RegimeSample.model_json_schema()
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema["$id"] = "urn:research-protocol:regime-sample:v1"
    schema["required"] = list(schema["properties"])
    nonnull = lambda: {"not": {"type": "null"}}
    schema["allOf"] = []
    for regime in get_args(ThreatRegime):
        targeted = regime.startswith(("R2_", "R3_"))
        properties = {"target_detector": ({"enum": ["D_S", "D_M-B", "D_G"]} if regime.startswith("R2_") else
                         {"const": "ALL"}) if targeted else {"type": "null"}}
        if targeted:
            properties.update({k: nonnull() for k in ("attack_method", "attack_method_revision", "lineage_id",
                                                       "valid_attack_attempt", "attack_success_definition")})
            properties["generation_evaluation_status"] = {"enum": ["PENDING", "COMPLETED"]}
        schema["allOf"].append({"if": {"properties": {"threat_regime": {"const": regime}}}, "then": {"properties": properties}})
    for label in (0, 1):
        schema["allOf"].append({"if": {"properties": {"truth_label": {"const": label}}},
                               "then": {"properties": {"is_adversarial": {"const": bool(label)}}}})
    schema["allOf"].extend([
        {"if": {"properties": {"generated_sample": {"const": True}}}, "then": {"properties": {
            **{k: nonnull() for k in ("parent_sample_id", "lineage_id", "generator_type")},
            "lineage_provenance_status": {"const": "DERIVED_FROM_PARENT"}}}},
        {"if": {"properties": {"attack_success": {"type": "boolean"}}}, "then": {"properties": {"attack_success_definition": nonnull()}}},
        {"if": {"properties": {"attack_success": {"const": True}}}, "then": {"properties": {"valid_attack_attempt": {"const": True}}}},
        {"if": {"properties": {"generator_type": {"const": "MODEL"}}}, "then": {"properties": {
            "generator_model": nonnull(), "generator_revision": nonnull(), "generator_system": {"type": "null"}}}},
        {"if": {"properties": {"generation_evaluation_status": {"const": "COMPLETED"}}}, "then": {"properties": {
            "attack_success": {"type": "boolean"}, "valid_attack_attempt": {"type": "boolean"}}}},
        {"if": {"properties": {"generation_evaluation_status": {"const": "PENDING"}}}, "then": {"properties": {"attack_success": {"type": "null"}}}},
        {"if": {"properties": {"generation_evaluation_status": {"const": "NOT_APPLICABLE"}}}, "then": {"properties": {
            k: {"type": "null"} for k in ("attack_success", "attack_success_definition", "valid_attack_attempt")}}},
        {"if": {"properties": {"generator_type": {"type": "null"}}}, "then": {"properties": {
            k: {"type": "null"} for k in ("generator_model", "generator_system", "generator_revision")}}},
        {"if": {"properties": {"generator_type": {"enum": ["RULE_BASED", "HUMAN", "DATASET_SOURCE", "OTHER"]}}},
         "then": {"properties": {"generator_model": {"type": "null"}}}},
        {"if": {"properties": {"generator_type": {"enum": ["RULE_BASED", "OTHER"]}}},
         "then": {"properties": {"generator_system": nonnull(), "generator_revision": nonnull()}}},
        {"if": {"properties": {"lineage_provenance_status": {"const": "UNKNOWN"}}},
         "then": {"properties": {"lineage_id": {"type": "null"}, "parent_sample_id": {"type": "null"}}},
         "else": {"properties": {"lineage_id": nonnull()}}},
        {"if": {"properties": {"parent_sample_id": {"type": "string"}}},
         "then": {"properties": {"lineage_id": nonnull(), "lineage_provenance_status": {"const": "DERIVED_FROM_PARENT"}}}},
        {"if": {"properties": {"lineage_provenance_status": {"const": "DERIVED_FROM_PARENT"}}},
         "then": {"properties": {"parent_sample_id": nonnull()}}},
        {"if": {"properties": {"lineage_provenance_status": {"const": "SINGLETON_FALLBACK"}}},
         "then": {"properties": {"lineage_justification": nonnull(), "parent_sample_id": {"type": "null"},
             "threat_regime": {"enum": ["R0_NON_ADAPTIVE", "R1_SHIFTED_UNSEEN"]}}}},
        {"if": {"properties": {"attack_family_provenance": {"const": "UNKNOWN"}}},
         "then": {"properties": {"attack_family": {"const": "UNKNOWN"}}}},
        {"if": {"properties": {"attack_family_provenance": {"const": "NOT_APPLICABLE"}}},
         "then": {"properties": {"attack_family": {"type": "null"}}}},
        {"if": {"properties": {"attack_family_provenance": {"enum": ["SOURCE_PROVIDED", "PROTOCOL_DECLARED", "ACCEPTED_METADATA"]}}},
         "then": {"properties": {"attack_family": nonnull()}}},
    ])
    for left, right in (("attack_method", "attack_method_revision"), ("generator_system", "generator_revision")):
        condition = {"properties": {left: {"type": "null"}}}
        if left == "generator_system":
            condition["properties"]["generator_type"] = {"not": {"const": "MODEL"}}
        schema["allOf"].append({"if": condition, "then": {"properties": {right: {"type": "null"}}}})
        schema["allOf"].append({"if": {"properties": {left: {"type": "string"}}},
                               "then": {"properties": {right: nonnull()}}})
        reverse = {"properties": {right: {"type": "string"}}}
        if left == "generator_system":
            reverse["properties"]["generator_type"] = {"not": {"const": "MODEL"}}
        schema["allOf"].append({"if": reverse, "then": {"properties": {left: nonnull()}}})
    return schema


def manifest_schema():
    schema = RegimeManifest.model_json_schema()
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema["$id"] = "urn:research-protocol:regime-manifest:v1"
    schema["required"] = list(schema["properties"])
    sample = sample_schema()
    schema["$defs"]["RegimeSample"].update({k: v for k, v in sample.items() if not k.startswith("$")})
    for definition in schema["$defs"].values():
        if "properties" in definition:
            definition["required"] = list(definition["properties"])
    return schema
