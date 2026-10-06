"""One strict, decision-only evaluation representation; no inference or fitting."""

import hashlib
from typing import Literal

from pydantic import StrictBool, model_validator

from detection_service.research_protocol.adapters import DetectorAdapter, PHASE2_SHA
from detection_service.research_protocol.operating_policy import (
    FrozenOperatingPolicy, OperationalPredictionRecord, native_prediction,
)
from detection_service.research_protocol.prediction import Binary, Count, Digest, PredictionRecord, Probability
from detection_service.research_protocol.regime import (
    FrozenMetadata, Partition, RegimeManifest, Text, ThreatRegime, canonical_bytes, require,
)
from detection_service.research_protocol.regime_contract import FrozenRegimeContracts, PREDICTION_SHA

PRIMARY = ("D_S", "D_M-B", "D_G")
POLICY_SHA = "06fa4548a62ae0e0968f9d93339910f8841a0f366b5346b0892a2be6904fb0cc"
REGIME_SHA = "716631bec5e7bbe562acd375c90260f5bf11f92cffb6c6d63a7639908408c149"
OP_SCHEMA_SHA = "3803cbf2f2c5c568894d894ccc51b64b86ff4f4ed2c5fa6a1e06b9d80512d173"
DecisionView = Literal["OPERATIONAL", "NATIVE", "EXPLICIT"]


def digest(value):
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


class PredictionBinding(FrozenMetadata):
    """Required batch provenance: canonical predictions have no regime fields."""

    experiment_id: Text
    regime_manifest_sha: Digest
    partition: Partition
    threat_regime: ThreatRegime
    detector_manifest_sha: Digest
    prediction_schema_sha: Digest


def bind_predictions(manifest):
    """Explicitly associate a prediction batch with a canonical manifest."""
    return PredictionBinding(experiment_id=manifest.experiment_id, regime_manifest_sha=manifest.manifest_hash,
        partition=manifest.partition, threat_regime=manifest.threat_regime,
        detector_manifest_sha=manifest.primary_detector_manifest_sha, prediction_schema_sha=manifest.prediction_schema_sha)


class Coverage(FrozenMetadata):
    expected_predictions: Count
    received_predictions: Count
    ok_predictions: Count
    non_ok_predictions: Count
    missing_predictions: Count
    missing_decisions: Count
    coverage_rate: Probability | None
    status: Literal["COMPLETE", "INCOMPLETE"]

    @model_validator(mode="after")
    def relations(self):
        require(self.received_predictions == self.ok_predictions + self.non_ok_predictions,
                "COVERAGE_RECEIVED_COUNT_CONFLICT")
        require(self.expected_predictions == self.received_predictions + self.missing_predictions,
                "COVERAGE_EXPECTED_COUNT_CONFLICT")
        require(self.missing_decisions <= self.ok_predictions, "COVERAGE_MISSING_DECISION_CONFLICT")
        usable = self.ok_predictions - self.missing_decisions
        require(self.coverage_rate == (usable / self.expected_predictions if self.expected_predictions else None),
                "COVERAGE_RATE_CONFLICT")
        complete = not (self.non_ok_predictions or self.missing_predictions or self.missing_decisions)
        require(self.status == ("COMPLETE" if complete else "INCOMPLETE"), "COVERAGE_STATUS_CONFLICT")
        return self


class IncompleteEvaluationError(ValueError):
    def __init__(self, coverage):
        self.coverage = coverage
        super().__init__("STRICT_COMPLETE_REQUIRED: " + coverage.model_dump_json())


class AlignedRow(FrozenMetadata):
    sample_id: Text
    truth_label: Binary
    is_adversarial: StrictBool
    partition: Partition
    threat_regime: ThreatRegime
    lineage_id: Text | None
    parent_sample_id: Text | None
    valid_attack_attempt: StrictBool | None
    target_detector: Literal["D_S", "D_M-B", "D_G", "ALL"] | None
    attack_success_definition: Text | None
    attack_success: StrictBool | None
    attack_method: Text | None
    attack_method_revision: Text | None
    sample_metadata_sha: Digest
    decisions: tuple[Binary | None, Binary | None, Binary | None]

    @model_validator(mode="after")
    def truth(self):
        require(self.is_adversarial == bool(self.truth_label), "ALIGNED_TRUTH_CONFLICT")
        return self


class EvaluationProvenance(FrozenMetadata):
    experiment_id: Text
    decision_view: DecisionView
    partition: Partition
    threat_regime: ThreatRegime
    evidence_kind: Literal["ACCEPTED_METADATA", "SYNTHETIC_FIXTURE"]
    regime_manifest_sha: Digest
    detector_manifest_sha: Digest
    prediction_schema_sha: Digest
    regime_contract_sha: Digest
    operational_prediction_schema_sha: Digest | None
    operating_policy_sha: Digest | None
    prediction_batch_sha: Digest
    explicit_decisions_sha: Digest | None
    explicit_provenance_id: Text | None
    primary_detector_labels: tuple[Literal["D_S"], Literal["D_M-B"], Literal["D_G"]]
    primary_detector_ids: tuple[Text, Text, Text]
    # Thresholds are exposed only when directly consumed from the verified policy.
    operational_thresholds: tuple[float, float, float] | None
    operational_threshold_ids: tuple[Text, Text, Text] | None

    @model_validator(mode="after")
    def relations(self):
        require(self.detector_manifest_sha == PHASE2_SHA and self.prediction_schema_sha == PREDICTION_SHA
                and self.regime_contract_sha == REGIME_SHA, "METRIC_PROTOCOL_BINDING_CONFLICT")
        operational = self.decision_view == "OPERATIONAL"
        require((self.operating_policy_sha, self.operational_prediction_schema_sha) ==
                ((POLICY_SHA, OP_SCHEMA_SHA) if operational else (None, None)), "METRIC_OPERATING_BINDING_CONFLICT")
        require((self.operational_thresholds is not None) == operational and
                (self.operational_threshold_ids is not None) == operational, "METRIC_THRESHOLD_VIEW_CONFLICT")
        explicit = self.decision_view == "EXPLICIT"
        require((self.explicit_provenance_id is not None) == explicit and
                (self.explicit_decisions_sha is not None) == explicit, "EXPLICIT_PROVENANCE_REQUIRED")
        return self


class AlignedEvaluation(FrozenMetadata):
    table_version: Literal["aligned_evaluation_v1"] = "aligned_evaluation_v1"
    provenance: EvaluationProvenance
    rows: tuple[AlignedRow, ...]
    coverage: Coverage
    detector_coverage: tuple[Coverage, Coverage, Coverage]
    alignment_sha: Digest

    @model_validator(mode="after")
    def relations(self):
        ids = tuple(r.sample_id for r in self.rows)
        require(ids == tuple(sorted(set(ids))), "ALIGNED_ROW_ORDER_OR_DUPLICATE")
        require(all(r.partition == self.provenance.partition and r.threat_regime == self.provenance.threat_regime
                    for r in self.rows), "ALIGNED_REGIME_PARTITION_CONFLICT")
        require(self.coverage.expected_predictions == 3 * len(self.rows), "ALIGNED_POPULATION_CONFLICT")
        for i, coverage in enumerate(self.detector_coverage):
            require(coverage.expected_predictions == len(self.rows), "DETECTOR_COVERAGE_POPULATION_CONFLICT")
            require(sum(r.decisions[i] is not None for r in self.rows) == coverage.ok_predictions - coverage.missing_decisions,
                    "ALIGNED_DECISION_COVERAGE_CONFLICT")
        for key in ("received_predictions", "ok_predictions", "non_ok_predictions", "missing_predictions", "missing_decisions"):
            require(getattr(self.coverage, key) == sum(getattr(c, key) for c in self.detector_coverage),
                    "AGGREGATE_COVERAGE_CONFLICT")
        payload = self.model_dump(mode="json")
        payload.pop("alignment_sha")
        require(self.alignment_sha == digest(payload), "ALIGNMENT_HASH_MISMATCH")
        return self

    def require_complete(self):
        # Revalidate the immutable projection before publishing official metrics.
        AlignedEvaluation.model_validate(self.model_dump())
        if self.coverage.status != "COMPLETE":
            raise IncompleteEvaluationError(self.coverage)
        return self

    def deterministic_bytes(self):
        return canonical_bytes(self.model_dump(mode="json")) + b"\n"


def coverage(expected, records, missing_decisions):
    ok = sum(r.status == "OK" for r in records)
    non_ok = len(records) - ok
    missing = expected - len(records)
    return Coverage(expected_predictions=expected, received_predictions=len(records), ok_predictions=ok,
        non_ok_predictions=non_ok, missing_predictions=missing, missing_decisions=missing_decisions,
        coverage_rate=(ok - missing_decisions) / expected if expected else None,
        status="INCOMPLETE" if non_ok or missing or missing_decisions else "COMPLETE")


def align_evaluation(manifest, predictions, *, binding, decision_view, contracts,
                     operating_policy=None, explicit_decisions=None, explicit_provenance_id=None,
                     strict_complete=True):
    """Align exactly; diagnostic mode retains every row but cannot publish metrics."""
    require(decision_view in ("OPERATIONAL", "NATIVE", "EXPLICIT"), "INVALID_DECISION_VIEW")
    require(type(strict_complete) is bool, "STRICT_COMPLETE_FLAG_REQUIRED")
    regimes = FrozenRegimeContracts(contracts.root)
    manifest = regimes.validate_manifest(manifest)
    require(manifest.status in ("FROZEN", "COMPLETED"), "EVALUATION_REQUIRES_FROZEN_MEMBERSHIP")
    require(regimes.targets == PRIMARY, "PRIMARY_DETECTOR_ORDER_CONFLICT")
    binding = PredictionBinding.model_validate(binding.model_dump() if isinstance(binding, PredictionBinding) else binding)
    require(binding == bind_predictions(manifest), "PREDICTION_BATCH_REGIME_BINDING_CONFLICT")
    adapters = tuple(DetectorAdapter(label, contracts) for label in PRIMARY)
    ids = tuple(a.detector_id for a in adapters)
    require(len(set(ids)) == 3, "PRIMARY_DETECTOR_ID_CONFLICT")
    if decision_view == "OPERATIONAL":
        require(isinstance(operating_policy, FrozenOperatingPolicy), "VERIFIED_OPERATING_POLICY_REQUIRED")
        require(not operating_policy.engineering_fixture and operating_policy.file_sha == POLICY_SHA
                and operating_policy.contracts.root == contracts.root, "AUTHORITATIVE_OPERATING_POLICY_REQUIRED")
    else:
        require(operating_policy is None, "UNUSED_OPERATING_POLICY_FORBIDDEN")
    if decision_view == "EXPLICIT":
        require(isinstance(explicit_provenance_id, str) and bool(explicit_provenance_id.strip()), "EXPLICIT_PROVENANCE_REQUIRED")
        require(manifest.evidence_kind == "SYNTHETIC_FIXTURE" or not explicit_provenance_id.startswith("TEST_FIXTURE"),
                "TEST_PROVENANCE_CANNOT_AUTHORIZE_REAL_DECISIONS")
        require(isinstance(explicit_decisions, dict), "EXPLICIT_DECISION_MAP_REQUIRED")
    else:
        require(explicit_decisions is None and explicit_provenance_id is None, "UNUSED_EXPLICIT_DECISIONS_FORBIDDEN")
    samples = {r.sample_id: r for r in manifest.samples}
    records, votes = {}, {}
    for value in predictions:
        payload = value.model_dump() if isinstance(value, PredictionRecord) else value
        if decision_view == "OPERATIONAL":
            record = OperationalPredictionRecord.model_validate(payload, context={"operating_policy": operating_policy})
            native = native_prediction(record)
        else:
            native = record = PredictionRecord.model_validate(payload)
        require(record.sample_id in samples and record.detector_id in ids, "UNKNOWN_SAMPLE_OR_NON_PRIMARY_DETECTOR")
        index = ids.index(record.detector_id)
        adapters[index].validate_prediction_record(native)
        require(record.truth_label == samples[record.sample_id].truth_label, "PREDICTION_TRUTH_LABEL_CONFLICT")
        require((record.metadata.evidence_kind == "SYNTHETIC_FIXTURE") == (manifest.evidence_kind == "SYNTHETIC_FIXTURE"),
                "PREDICTION_EVIDENCE_KIND_CONFLICT")
        key = (record.sample_id, record.detector_id)
        require(key not in records, "DUPLICATE_DETECTOR_SAMPLE_PAIR")
        records[key] = record
        if record.status != "OK":
            votes[key] = None
        elif decision_view == "EXPLICIT":
            votes[key] = explicit_decisions.get(key)
        else:
            votes[key] = getattr(record, "operational_binary_prediction" if decision_view == "OPERATIONAL" else "native_binary_prediction")
    if decision_view == "EXPLICIT":
        require(set(explicit_decisions) <= set(records), "EXPLICIT_UNKNOWN_SAMPLE_OR_DETECTOR")
        require(all(type(v) is int and v in (0, 1) for v in explicit_decisions.values()), "EXPLICIT_BINARY_DECISIONS_REQUIRED")
        require(all(records[k].status == "OK" for k in explicit_decisions), "NON_OK_EXPLICIT_DECISION_FORBIDDEN")
    ordered = sorted(records, key=lambda k: (k[0], ids.index(k[1])))
    per_detector = tuple(coverage(len(samples), [r for (_, d), r in records.items() if d == detector],
        sum(r.status == "OK" and votes[key] is None for key, r in records.items() if key[1] == detector)) for detector in ids)
    total = coverage(3 * len(samples), list(records.values()), sum(r.status == "OK" and votes[k] is None for k, r in records.items()))
    provenance = EvaluationProvenance(experiment_id=manifest.experiment_id, decision_view=decision_view,
        partition=manifest.partition, threat_regime=manifest.threat_regime, evidence_kind=manifest.evidence_kind,
        regime_manifest_sha=manifest.manifest_hash, detector_manifest_sha=PHASE2_SHA, prediction_schema_sha=PREDICTION_SHA,
        regime_contract_sha=REGIME_SHA, operational_prediction_schema_sha=OP_SCHEMA_SHA if operating_policy else None,
        operating_policy_sha=POLICY_SHA if operating_policy else None,
        prediction_batch_sha=digest([records[k].model_dump(mode="json") for k in ordered]),
        explicit_decisions_sha=digest([(s, d, explicit_decisions[(s, d)]) for s, d in ordered if (s, d) in explicit_decisions])
            if decision_view == "EXPLICIT" else None,
        explicit_provenance_id=explicit_provenance_id, primary_detector_labels=PRIMARY, primary_detector_ids=ids,
        operational_thresholds=tuple(operating_policy.point(d).threshold for d in ids) if operating_policy else None,
        operational_threshold_ids=tuple(operating_policy.point(d).threshold_id for d in ids) if operating_policy else None)
    rows = tuple(AlignedRow(sample_id=s.sample_id, truth_label=s.truth_label, is_adversarial=s.is_adversarial,
        partition=s.partition, threat_regime=s.threat_regime, lineage_id=s.lineage_id, parent_sample_id=s.parent_sample_id,
        valid_attack_attempt=s.valid_attack_attempt, target_detector=s.target_detector, attack_success_definition=s.attack_success_definition,
        attack_success=s.attack_success, attack_method=s.attack_method, attack_method_revision=s.attack_method_revision,
        sample_metadata_sha=digest(s.model_dump(mode="json")), decisions=tuple(votes.get((s.sample_id, d)) for d in ids))
        for s in manifest.samples)
    payload = dict(table_version="aligned_evaluation_v1", provenance=provenance.model_dump(mode="json"),
        rows=[r.model_dump(mode="json") for r in rows], coverage=total.model_dump(mode="json"),
        detector_coverage=[c.model_dump(mode="json") for c in per_detector])
    aligned = AlignedEvaluation(provenance=provenance, rows=rows, coverage=total,
        detector_coverage=per_detector, alignment_sha=digest(payload))
    if strict_complete:
        aligned.require_complete()
    return aligned
