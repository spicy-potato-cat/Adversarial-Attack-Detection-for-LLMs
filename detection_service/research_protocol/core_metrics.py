"""Phases 6-10: deterministic decision accounting from one aligned population."""

from itertools import combinations
from typing import Literal

from pydantic import model_validator

from detection_service.research_protocol.alignment import AlignedEvaluation, AlignedRow, PRIMARY
from detection_service.research_protocol.metric_types import (
    CommonModeResult, Difference, FailurePattern, FailurePatternsResult, IndependenceReference, IndividualMetrics, IndividualResult,
    MEANINGS, PATTERNS, PairFailure, Recovery, RecoveryResult, TargetEvasion, Transfer, TransferResult, rate,
)
from detection_service.research_protocol.regime import FrozenMetadata, canonical_bytes, require


def failure_indicator(row: AlignedRow, detector_index: int):
    """The sole miss definition: adversarial truth and an explicit benign decision."""
    require(type(detector_index) is int and 0 <= detector_index < 3, "PRIMARY_DETECTOR_INDEX_REQUIRED")
    require(row.decisions[detector_index] is not None, "FAILURE_INDICATOR_REQUIRES_DECISION")
    return int(row.truth_label == 1 and row.decisions[detector_index] == 0)


class _Accounting:
    def __init__(self, table):
        require(isinstance(table, AlignedEvaluation), "AUTHORITATIVE_ALIGNMENT_REQUIRED")
        self.table = table.require_complete()
        self.counts = [dict(tp=0, fp=0, tn=0, fn=0) for _ in PRIMARY]
        self.patterns = dict.fromkeys(PATTERNS, 0)
        for row in table.rows:
            misses = tuple(failure_indicator(row, i) for i in range(3))
            if row.truth_label == 1:
                self.patterns["".join(str(b) for b in misses)] += 1
            for i, decision in enumerate(row.decisions):
                name = ("fn" if misses[i] else "tp") if row.truth_label else ("fp" if decision else "tn")
                self.counts[i][name] += 1
        attacks = sum(self.patterns.values())
        self.base = dict(provenance=table.provenance, alignment_sha=table.alignment_sha,
            population_count=len(table.rows), attack_count=attacks, benign_count=len(table.rows)-attacks, coverage=table.coverage)

    def individual(self):
        detectors = []
        for i, counts in enumerate(self.counts):
            tp, fp, tn, fn = (counts[k] for k in ("tp", "fp", "tn", "fn"))
            n = tp+fp+tn+fn
            detectors.append(IndividualMetrics(detector_id=self.table.provenance.primary_detector_ids[i],
                population_count=n, attack_count=tp+fn, benign_count=fp+tn, **counts,
                accuracy=rate(tp+tn, n), precision=rate(tp, tp+fp), recall=rate(tp, tp+fn), specificity=rate(tn, tn+fp),
                f1=rate(2*tp, 2*tp+fp+fn), fpr=rate(fp, fp+tn), fnr=rate(fn, fn+tp), npv=rate(tn, tn+fn),
                coverage=self.table.detector_coverage[i]))
        return IndividualResult(**self.base, detectors=tuple(detectors))

    def common(self, individual):
        n = self.base["attack_count"]
        pairs = []
        for i, j in combinations(range(3), 2):
            left, right = individual.detectors[i], individual.detectors[j]
            shared = sum(c for p, c in self.patterns.items() if p[i] == p[j] == "1")
            jfn = rate(shared, n)
            reference = IndependenceReference(value=left.fnr.value*right.fnr.value if n else None,
                status="DEFINED" if n else "UNDEFINED", reason=None if n else "ZERO_ATTACK_DENOMINATOR")
            pairs.append(PairFailure(left_detector=left.detector_id, right_detector=right.detector_id,
                left_fnr=left.fnr, right_fnr=right.fnr, shared_fn_count=shared, jfn=jfn,
                independence_reference=reference,
                ejf=Difference(value=jfn.value-reference.value if n else None,
                    status="DEFINED" if n else "UNDEFINED", reason=None if n else "ZERO_ATTACK_DENOMINATOR"),
                intersection_count=shared, union_count=left.fn+right.fn-shared,
                fn_jaccard=rate(shared, left.fn+right.fn-shared)))
        all_three = self.patterns["111"]
        return CommonModeResult(**self.base, pairs=tuple(pairs), all_three_fn_count=all_three, all_three_jfn=rate(all_three, n))

    def failure_patterns(self):
        return FailurePatternsResult(**self.base, patterns=tuple(FailurePattern(pattern_id=p, count=self.patterns[p],
            attack_rate=rate(self.patterns[p], self.base["attack_count"]), meaning=MEANINGS[i]) for i, p in enumerate(PATTERNS)))

    def recovery(self):
        detectors = []
        for detector, pattern in zip(self.table.provenance.primary_detector_ids, ("011", "101", "110")):
            unique = self.patterns[pattern]
            opportunities = unique + self.patterns["111"]
            detectors.append(Recovery(detector_id=detector, unique_catch_pattern=pattern,
                unique_catch_count=unique, unique_catch_rate=rate(unique, self.base["attack_count"]),
                both_others_miss_count=opportunities, conditional_recovery=rate(unique, opportunities)))
        return RecoveryResult(**self.base, detectors=tuple(detectors))

    def transfer(self):
        require(self.table.provenance.threat_regime == "R2_SINGLE_DETECTOR_TARGETED", "R2_TRANSFER_REQUIRES_R2_REGIME")
        require(all(r.target_detector in PRIMARY and type(r.valid_attack_attempt) is bool and r.lineage_id is not None
                    and r.attack_method is not None and r.attack_method_revision is not None for r in self.table.rows),
                "R2_TARGETED_METADATA_REQUIRED")
        targets = []
        ids = self.table.provenance.primary_detector_ids
        for i, target in enumerate(PRIMARY):
            attempts = [r for r in self.table.rows if r.target_detector == target]
            valid = [r for r in attempts if r.truth_label == 1 and r.valid_attack_attempt is True]
            evaded = [r for r in valid if failure_indicator(r, i)]
            transfers = tuple(Transfer(target_detector=ids[i], transfer_detector=ids[j], valid_attempt_count=len(valid),
                target_evasion_count=len(evaded), joint_evasion_count=sum(failure_indicator(r, j) for r in evaded),
                etr=rate(sum(failure_indicator(r, j) for r in evaded), len(evaded))) for j in range(3) if i != j)
            targets.append(TargetEvasion(target_detector=ids[i], valid_attempt_count=len(valid), target_evasion_count=len(evaded),
                target_evasion_rate=rate(len(evaded), len(valid)), unique_lineage_count=len({r.lineage_id for r in attempts}),
                valid_attempt_lineage_count=len({r.lineage_id for r in valid}),
                target_evasion_lineage_count=len({r.lineage_id for r in evaded}), transfers=transfers))
        return TransferResult(**self.base, targets=tuple(targets))


class CoreMetricsResult(FrozenMetadata):
    result_version: Literal["core_metrics_bundle_v1"] = "core_metrics_bundle_v1"
    individual: IndividualResult
    common_mode: CommonModeResult
    failure_patterns: FailurePatternsResult
    recovery: RecoveryResult
    evasion_transfer: TransferResult | None

    @model_validator(mode="after")
    def invariants(self):
        sections = (self.common_mode, self.failure_patterns, self.recovery)
        if self.evasion_transfer is not None:
            sections += (self.evasion_transfer,)
        for section in sections:
            require((section.provenance, section.alignment_sha, section.population_count, section.attack_count,
                     section.benign_count, section.coverage) ==
                    (self.individual.provenance, self.individual.alignment_sha, self.individual.population_count,
                     self.individual.attack_count, self.individual.benign_count, self.individual.coverage), "CROSS_MODULE_POPULATION_CONFLICT")
        patterns = {p.pattern_id: p.count for p in self.failure_patterns.patterns}
        require(patterns["111"] == self.common_mode.all_three_fn_count, "PATTERN_THREE_WAY_CONFLICT")
        for i, detector in enumerate(self.individual.detectors):
            fn = sum(c for p, c in patterns.items() if p[i] == "1")
            require(fn == detector.fn, "PATTERN_INDIVIDUAL_FN_CONFLICT")
            recovery = self.recovery.detectors[i]
            require(recovery.unique_catch_count == patterns[recovery.unique_catch_pattern]
                    and recovery.both_others_miss_count == recovery.unique_catch_count + patterns["111"], "PATTERN_RECOVERY_CONFLICT")
        for (i, j), pair in zip(combinations(range(3), 2), self.common_mode.pairs):
            require(pair.shared_fn_count == sum(c for p, c in patterns.items() if p[i] == p[j] == "1"), "PATTERN_PAIR_FAILURE_CONFLICT")
            require(pair.left_fnr == self.individual.detectors[i].fnr and pair.right_fnr == self.individual.detectors[j].fnr,
                    "COMMON_INDIVIDUAL_FNR_CONFLICT")
        require((self.evasion_transfer is not None) == (self.individual.provenance.threat_regime == "R2_SINGLE_DETECTOR_TARGETED"),
                "TRANSFER_REGIME_CONFLICT")
        return self

    def deterministic_bytes(self):
        return canonical_bytes(self.model_dump(mode="json")) + b"\n"


def individual_metrics(table):
    return _Accounting(table).individual()


def common_mode_metrics(table):
    accounting = _Accounting(table)
    return accounting.common(accounting.individual())


def failure_patterns(table):
    return _Accounting(table).failure_patterns()


def recovery_metrics(table):
    return _Accounting(table).recovery()


def evasion_transfer_metrics(table):
    return _Accounting(table).transfer()


def evaluate_core(table):
    """One accounting pass, shared provenance, and all cross-module assertions."""
    accounting = _Accounting(table)
    individual = accounting.individual()
    return CoreMetricsResult(individual=individual, common_mode=accounting.common(individual),
        failure_patterns=accounting.failure_patterns(), recovery=accounting.recovery(),
        evasion_transfer=accounting.transfer() if table.provenance.threat_regime == "R2_SINGLE_DETECTOR_TARGETED" else None)
