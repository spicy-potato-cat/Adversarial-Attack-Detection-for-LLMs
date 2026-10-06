"""Strict versioned decision-metric outputs and explicit undefined arithmetic."""

from typing import Annotated, Literal

from pydantic import Field, model_validator

from detection_service.research_protocol.alignment import Coverage, EvaluationProvenance
from detection_service.research_protocol.prediction import Count, Digest, Probability
from detection_service.research_protocol.regime import FrozenMetadata, Text, canonical_bytes, require


class Rate(FrozenMetadata):
    numerator: Count
    denominator: Count
    value: Probability | None
    status: Literal["DEFINED", "UNDEFINED"]
    reason: Literal["ZERO_DENOMINATOR"] | None

    @model_validator(mode="after")
    def arithmetic(self):
        require(self.numerator <= self.denominator, "RATE_COUNT_CONFLICT")
        require(self.value == (self.numerator / self.denominator if self.denominator else None), "RATE_VALUE_CONFLICT")
        require((self.status, self.reason) == (("DEFINED", None) if self.denominator else ("UNDEFINED", "ZERO_DENOMINATOR")),
                "RATE_STATUS_CONFLICT")
        return self


def rate(numerator, denominator):
    return Rate(numerator=numerator, denominator=denominator, value=numerator / denominator if denominator else None,
                status="DEFINED" if denominator else "UNDEFINED", reason=None if denominator else "ZERO_DENOMINATOR")


class Difference(FrozenMetadata):
    value: Annotated[float, Field(strict=True, ge=-1, le=1, allow_inf_nan=False)] | None
    status: Literal["DEFINED", "UNDEFINED"]
    reason: Literal["ZERO_ATTACK_DENOMINATOR"] | None


class IndependenceReference(FrozenMetadata):
    value: Probability | None
    status: Literal["DEFINED", "UNDEFINED"]
    reason: Literal["ZERO_ATTACK_DENOMINATOR"] | None


class IndividualMetrics(FrozenMetadata):
    detector_id: Text
    population_count: Count
    attack_count: Count
    benign_count: Count
    tp: Count
    fp: Count
    tn: Count
    fn: Count
    accuracy: Rate
    precision: Rate
    recall: Rate
    specificity: Rate
    f1: Rate
    fpr: Rate
    fnr: Rate
    npv: Rate
    coverage: Coverage
    metric_status: Literal["COMPLETE"] = "COMPLETE"

    @model_validator(mode="after")
    def relations(self):
        require(self.tp + self.fn == self.attack_count and self.fp + self.tn == self.benign_count
                and self.population_count == self.attack_count + self.benign_count, "CONFUSION_COUNT_CONFLICT")
        expected = {"accuracy": (self.tp+self.tn, self.population_count), "precision": (self.tp, self.tp+self.fp),
            "recall": (self.tp, self.attack_count), "specificity": (self.tn, self.benign_count),
            "f1": (2*self.tp, 2*self.tp+self.fp+self.fn), "fpr": (self.fp, self.benign_count),
            "fnr": (self.fn, self.attack_count), "npv": (self.tn, self.tn+self.fn)}
        require(all(getattr(self, name) == rate(*counts) for name, counts in expected.items()), "INDIVIDUAL_RATE_CONFLICT")
        require(self.coverage.status == "COMPLETE" and self.coverage.expected_predictions == self.population_count,
                "INDIVIDUAL_COVERAGE_CONFLICT")
        return self


class MetricResult(FrozenMetadata):
    provenance: EvaluationProvenance
    alignment_sha: Digest
    population_count: Count
    attack_count: Count
    benign_count: Count
    coverage: Coverage
    metric_status: Literal["COMPLETE"] = "COMPLETE"

    @model_validator(mode="after")
    def population(self):
        require(self.population_count == self.attack_count + self.benign_count and self.coverage.status == "COMPLETE"
                and self.coverage.expected_predictions == 3*self.population_count, "METRIC_POPULATION_COVERAGE_CONFLICT")
        return self

    def deterministic_bytes(self):
        return canonical_bytes(self.model_dump(mode="json")) + b"\n"


class IndividualResult(MetricResult):
    result_version: Literal["individual_metrics_v1"] = "individual_metrics_v1"
    detectors: tuple[IndividualMetrics, IndividualMetrics, IndividualMetrics]

    @model_validator(mode="after")
    def order(self):
        require(tuple(d.detector_id for d in self.detectors) == self.provenance.primary_detector_ids, "INDIVIDUAL_DETECTOR_ORDER_CONFLICT")
        require(all((d.population_count, d.attack_count, d.benign_count) ==
                    (self.population_count, self.attack_count, self.benign_count) for d in self.detectors), "INDIVIDUAL_POPULATION_CONFLICT")
        return self


class PairFailure(FrozenMetadata):
    left_detector: Text
    right_detector: Text
    left_fnr: Rate
    right_fnr: Rate
    shared_fn_count: Count
    jfn: Rate
    independence_reference: IndependenceReference
    ejf: Difference
    intersection_count: Count
    union_count: Count
    fn_jaccard: Rate

    @model_validator(mode="after")
    def relations(self):
        n = self.left_fnr.denominator
        left, right = self.left_fnr.numerator, self.right_fnr.numerator
        require(self.right_fnr.denominator == n and self.shared_fn_count <= min(left, right), "PAIR_FAILURE_COUNT_CONFLICT")
        require(self.intersection_count == self.shared_fn_count and self.union_count == left + right - self.shared_fn_count,
                "PAIR_SET_COUNT_CONFLICT")
        require(self.jfn == rate(self.shared_fn_count, n) and self.fn_jaccard == rate(self.intersection_count, self.union_count)
                and self.independence_reference == IndependenceReference(value=self.left_fnr.value*self.right_fnr.value if n else None,
                    status="DEFINED" if n else "UNDEFINED", reason=None if n else "ZERO_ATTACK_DENOMINATOR"), "PAIR_FAILURE_RATE_CONFLICT")
        require(self.ejf == Difference(value=self.jfn.value-self.independence_reference.value if n else None,
                status="DEFINED" if n else "UNDEFINED", reason=None if n else "ZERO_ATTACK_DENOMINATOR"), "EJF_CONFLICT")
        return self


class CommonModeResult(MetricResult):
    result_version: Literal["common_mode_metrics_v1"] = "common_mode_metrics_v1"
    pairs: tuple[PairFailure, PairFailure, PairFailure]
    all_three_fn_count: Count
    all_three_jfn: Rate

    @model_validator(mode="after")
    def relations(self):
        s, m, g = self.provenance.primary_detector_ids
        require(tuple((p.left_detector, p.right_detector) for p in self.pairs) == ((s,m), (s,g), (m,g)), "PRIMARY_PAIR_ORDER_CONFLICT")
        require(self.all_three_jfn == rate(self.all_three_fn_count, self.attack_count), "THREE_WAY_RATE_CONFLICT")
        require(all(p.jfn.denominator == self.attack_count and self.all_three_fn_count <= p.shared_fn_count
                    for p in self.pairs), "THREE_WAY_COUNT_CONFLICT")
        return self


PATTERNS = tuple(format(i, "03b") for i in range(8))
MEANINGS = ("All three catch", "Only D_G misses", "Only D_M-B misses", "D_M-B and D_G miss; D_S catches",
            "Only D_S misses", "D_S and D_G miss; D_M-B catches", "D_S and D_M-B miss; D_G catches", "All three miss")


class FailurePattern(FrozenMetadata):
    pattern_id: Literal["000", "001", "010", "011", "100", "101", "110", "111"]
    count: Count
    attack_rate: Rate
    meaning: Text

    @model_validator(mode="after")
    def relations(self):
        require(self.attack_rate.numerator == self.count and self.meaning == MEANINGS[PATTERNS.index(self.pattern_id)], "PATTERN_MEANING_CONFLICT")
        return self


class FailurePatternsResult(MetricResult):
    result_version: Literal["failure_patterns_v1"] = "failure_patterns_v1"
    bit_order: Literal["S/M/G"] = "S/M/G"
    bit_semantics: Literal["0=CATCH;1=MISS"] = "0=CATCH;1=MISS"
    patterns: tuple[FailurePattern, ...]

    @model_validator(mode="after")
    def relations(self):
        require(tuple(p.pattern_id for p in self.patterns) == PATTERNS and sum(p.count for p in self.patterns) == self.attack_count
                and all(p.attack_rate.denominator == self.attack_count for p in self.patterns), "PATTERN_POPULATION_CONFLICT")
        return self


class Recovery(FrozenMetadata):
    detector_id: Text
    unique_catch_pattern: Literal["011", "101", "110"]
    unique_catch_count: Count
    unique_catch_rate: Rate
    both_others_miss_count: Count
    conditional_recovery: Rate

    @model_validator(mode="after")
    def relations(self):
        require(self.unique_catch_rate.numerator == self.unique_catch_count and
                self.conditional_recovery == rate(self.unique_catch_count, self.both_others_miss_count), "RECOVERY_COUNT_CONFLICT")
        return self


class RecoveryResult(MetricResult):
    result_version: Literal["recovery_metrics_v1"] = "recovery_metrics_v1"
    detectors: tuple[Recovery, Recovery, Recovery]

    @model_validator(mode="after")
    def relations(self):
        require(tuple(d.detector_id for d in self.detectors) == self.provenance.primary_detector_ids
                and tuple(d.unique_catch_pattern for d in self.detectors) == ("011", "101", "110")
                and all(d.unique_catch_rate.denominator == self.attack_count for d in self.detectors), "RECOVERY_ORDER_CONFLICT")
        return self


class Transfer(FrozenMetadata):
    target_detector: Text
    transfer_detector: Text
    valid_attempt_count: Count
    target_evasion_count: Count
    joint_evasion_count: Count
    etr: Rate

    @model_validator(mode="after")
    def relations(self):
        require(self.target_evasion_count <= self.valid_attempt_count and self.target_detector != self.transfer_detector
                and self.etr == rate(self.joint_evasion_count, self.target_evasion_count), "TRANSFER_COUNT_CONFLICT")
        return self


class TargetEvasion(FrozenMetadata):
    target_detector: Text
    valid_attempt_count: Count
    target_evasion_count: Count
    target_evasion_rate: Rate
    unique_lineage_count: Count
    valid_attempt_lineage_count: Count
    target_evasion_lineage_count: Count
    transfers: tuple[Transfer, Transfer]

    @model_validator(mode="after")
    def relations(self):
        require(self.target_evasion_rate == rate(self.target_evasion_count, self.valid_attempt_count), "TARGET_EVASION_COUNT_CONFLICT")
        require(self.target_evasion_lineage_count <= self.valid_attempt_lineage_count <= self.unique_lineage_count
                and self.valid_attempt_lineage_count <= self.valid_attempt_count
                and self.target_evasion_lineage_count <= self.target_evasion_count, "TARGET_LINEAGE_COUNT_CONFLICT")
        require(all((t.target_detector, t.valid_attempt_count, t.target_evasion_count) ==
                    (self.target_detector, self.valid_attempt_count, self.target_evasion_count) for t in self.transfers), "TARGET_TRANSFER_CONFLICT")
        return self


class TransferResult(MetricResult):
    result_version: Literal["evasion_transfer_metrics_v1"] = "evasion_transfer_metrics_v1"
    targets: tuple[TargetEvasion, TargetEvasion, TargetEvasion]

    @model_validator(mode="after")
    def relations(self):
        ids = self.provenance.primary_detector_ids
        require(self.provenance.threat_regime == "R2_SINGLE_DETECTOR_TARGETED"
                and tuple(t.target_detector for t in self.targets) == ids, "R2_TARGET_ORDER_CONFLICT")
        for target in self.targets:
            require(tuple(t.transfer_detector for t in target.transfers) == tuple(d for d in ids if d != target.target_detector),
                    "TRANSFER_DETECTOR_ORDER_CONFLICT")
        return self
