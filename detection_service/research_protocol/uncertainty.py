"""Paired percentile bootstrap using indices, never duplicated canonical manifests."""

from copy import copy
from collections import Counter
from types import SimpleNamespace
from typing import Annotated, Literal

import numpy as np
from pydantic import Field, FiniteFloat, model_validator

from detection_service.research_protocol.alignment import Coverage, PRIMARY, digest
from detection_service.research_protocol.core_metrics import _Accounting, evaluate_core, failure_indicator
from detection_service.research_protocol.metric_catalog import metric_catalog
from detection_service.research_protocol.prediction import Count, Digest
from detection_service.research_protocol.regime import FrozenMetadata, Text, canonical_bytes, require

Unit = Literal["SAMPLE_PAIRED", "LINEAGE_CLUSTERED"]
Domain = Literal["ATTACK_ONLY", "BENIGN_ONLY", "STRATIFIED_LABEL", "VALID_TARGET_ATTEMPTS"]
CORE_CONTRACT_SHA = "86f7dfc69a1841f9ded303bad349f7cbd0082898f1524bdcfac9edb49ef3d2d9"


def uncertainty_contract():
    return dict(contract_version="uncertainty_contract_v1", method="PERCENTILE_BOOTSTRAP_V1", replicates=1000,
        seed=1701, confidence_level=.95, percentiles=[.025,.975], quantile_method="linear",
        rng="numpy.Generator/PCG64", numpy_version=np.__version__, units=["SAMPLE_PAIRED","LINEAGE_CLUSTERED"],
        domains=["ATTACK_ONLY","BENIGN_ONLY","STRATIFIED_LABEL","VALID_TARGET_ATTEMPTS"],
        minimum_valid_fraction=.95, undefined_policy="Exclude undefined replicates; null CI if observed undefined or support below 95%",
        point_estimate="Observed frozen core metric, never bootstrap mean", paired_delta="B minus A on identical resampling indices",
        cluster_order="Sorted lineage IDs; all domain-selected descendants together; strata attack then benign",
        generated_descendants="R2/R3 shared lineage requires LINEAGE_CLUSTERED", mixed_label_cluster="Reject stratification that splits a lineage",
        resampling_storage="Indices only; never duplicate canonical sample IDs", core_metrics_contract_sha=CORE_CONTRACT_SHA,
        stream_policy="Default resets PCG64(seed); explicit shared PCG64 allowed only with recorded pre/post state hashes",
        inference=False, significance_tests=False)


def uncertainty_contract_sha():
    from hashlib import sha256
    from detection_service.research_protocol.detector_semantics import manifest_bytes
    return sha256(manifest_bytes(uncertainty_contract())).hexdigest()


class BootstrapConfig(FrozenMetadata):
    replicates: Annotated[Count, Field(ge=1)] = 1000
    seed: Count = 1701
    confidence_level: Literal[.95] = .95
    method: Literal["PERCENTILE_BOOTSTRAP_V1"] = "PERCENTILE_BOOTSTRAP_V1"
    quantile_method: Literal["linear"] = "linear"
    unit: Unit
    domain: Domain
    target_detector: Literal["D_S", "D_M-B", "D_G"] | None = None

    @model_validator(mode="after")
    def target(self):
        require((self.target_detector is not None) == (self.domain == "VALID_TARGET_ATTEMPTS"), "BOOTSTRAP_TARGET_DOMAIN_CONFLICT")
        return self


class ResamplingPlan(FrozenMetadata):
    config: BootstrapConfig
    population_signature: Digest
    domain_indices: tuple[Count, ...]
    resamples: tuple[tuple[Count, ...], ...]
    rng: Literal["numpy.Generator/PCG64"] = "numpy.Generator/PCG64"
    numpy_version: Text
    rng_state_before_sha: Digest
    rng_state_after_sha: Digest
    plan_sha: Digest

    @model_validator(mode="after")
    def integrity(self):
        require(len(self.resamples) == self.config.replicates and len(set(self.domain_indices)) == len(self.domain_indices), "RESAMPLE_COUNT_CONFLICT")
        require(all(set(indices) <= set(self.domain_indices) for indices in self.resamples), "RESAMPLE_OUTSIDE_DOMAIN")
        payload = self.model_dump(mode="json")
        payload.pop("plan_sha")
        require(self.plan_sha == digest(payload), "RESAMPLE_PLAN_HASH_MISMATCH")
        return self


def population_signature(table):
    return digest([{k:v for k,v in r.model_dump(mode="json").items() if k != "decisions"} for r in table.rows])


def domain_indices(table, config):
    table.require_complete()
    if config.domain == "VALID_TARGET_ATTEMPTS":
        require(table.provenance.threat_regime == "R2_SINGLE_DETECTOR_TARGETED", "TARGET_BOOTSTRAP_REQUIRES_R2")
    return tuple(i for i, r in enumerate(table.rows) if config.domain == "STRATIFIED_LABEL"
        or config.domain == "ATTACK_ONLY" and r.truth_label == 1
        or config.domain == "BENIGN_ONLY" and r.truth_label == 0
        or config.domain == "VALID_TARGET_ATTEMPTS" and r.truth_label == 1 and r.valid_attack_attempt is True
            and r.target_detector == config.target_detector)


def sampling_units(table, config):
    indices = domain_indices(table, config)
    lineages = [table.rows[i].lineage_id for i in indices]
    generated = table.provenance.threat_regime.startswith(("R2_", "R3_"))
    if generated and len([v for v in lineages if v is not None]) != len(set(v for v in lineages if v is not None)):
        require(config.unit == "LINEAGE_CLUSTERED", "GENERATED_DESCENDANTS_REQUIRE_LINEAGE_CLUSTERING")
    if config.unit == "LINEAGE_CLUSTERED":
        require(all(v is not None for v in lineages), "LINEAGE_BOOTSTRAP_REQUIRES_KNOWN_LINEAGES")
        groups = {}
        for i in indices:
            groups.setdefault(table.rows[i].lineage_id, []).append(i)
        units = tuple(tuple(groups[k]) for k in sorted(groups))
    else:
        units = tuple((i,) for i in indices)
    if config.domain == "STRATIFIED_LABEL":
        require(all(len({table.rows[i].truth_label for i in group}) == 1 for group in units), "MIXED_LABEL_LINEAGE_CANNOT_BE_SPLIT")
        return indices, tuple(tuple(g for g in units if table.rows[g[0]].truth_label == label) for label in (1, 0))
    return indices, (units,)


def make_plan(table, config, *, rng=None):
    """An explicit shared PCG64 stream supports documented sequential historical runs."""
    config = BootstrapConfig.model_validate(config.model_dump())
    indices, strata = sampling_units(table, config)
    rng = np.random.Generator(np.random.PCG64(config.seed)) if rng is None else rng
    require(isinstance(rng, np.random.Generator) and isinstance(rng.bit_generator, np.random.PCG64), "PINNED_PCG64_REQUIRED")
    before = digest(rng.bit_generator.state)
    draws = []
    for _ in range(config.replicates):
        draw = []
        for units in strata:
            if units:
                for chosen in rng.integers(0, len(units), size=len(units)):
                    draw.extend(units[int(chosen)])
        draws.append(tuple(draw))
    payload = dict(config=config.model_dump(mode="json"), population_signature=population_signature(table), domain_indices=indices,
        resamples=tuple(draws), rng="numpy.Generator/PCG64", numpy_version=np.__version__,
        rng_state_before_sha=before, rng_state_after_sha=digest(rng.bit_generator.state))
    return ResamplingPlan(**{**payload, "config": config}, plan_sha=digest(payload))


def validate_plan(table, config, plan):
    plan = ResamplingPlan.model_validate(plan.model_dump())
    indices, strata = sampling_units(table, config)
    require(plan.config == config and plan.population_signature == population_signature(table)
            and plan.domain_indices == indices and plan.numpy_version == np.__version__, "RESAMPLE_PLAN_POPULATION_BINDING_CONFLICT")
    for draw in plan.resamples:
        counts = Counter(draw)
        for units in strata:
            multiplicities = []
            for group in units:
                values = {counts[i] for i in group}
                require(len(values) == 1, "RESAMPLE_SPLITS_LINEAGE")
                multiplicities.append(values.pop())
            require(sum(multiplicities) == len(units), "RESAMPLE_STRATUM_SIZE_CONFLICT")
    return plan


def _weighted_values(observed, table, indices):
    # Reuse the frozen core formulas. Only bootstrap tally inputs change; no fake
    # canonical manifest/prediction IDs are created or persisted.
    accounting = copy(observed)
    rows = tuple(table.rows[i] for i in indices)
    n = len(rows)
    one = Coverage(expected_predictions=n, received_predictions=n, ok_predictions=n, non_ok_predictions=0,
        missing_predictions=0, missing_decisions=0, coverage_rate=1. if n else None, status="COMPLETE")
    aggregate = one.model_copy(update={"expected_predictions":3*n,"received_predictions":3*n,"ok_predictions":3*n})
    accounting.table = SimpleNamespace(rows=rows, provenance=table.provenance, detector_coverage=(one,one,one))
    accounting.counts = [dict(tp=0, fp=0, tn=0, fn=0) for _ in PRIMARY]
    accounting.patterns = dict.fromkeys(observed.patterns, 0)
    for row in rows:
        misses = tuple(failure_indicator(row, i) for i in range(3))
        if row.truth_label:
            accounting.patterns["".join(map(str, misses))] += 1
        for i, decision in enumerate(row.decisions):
            name = ("fn" if misses[i] else "tp") if row.truth_label else ("fp" if decision else "tn")
            accounting.counts[i][name] += 1
    attacks = sum(accounting.patterns.values())
    accounting.base = {**observed.base,"population_count":n,"attack_count":attacks,"benign_count":n-attacks,"coverage":aggregate}
    individual = accounting.individual()
    bundle = SimpleNamespace(individual=individual, common_mode=accounting.common(individual),
        failure_patterns=accounting.failure_patterns(), recovery=accounting.recovery(),
        evasion_transfer=accounting.transfer() if table.provenance.threat_regime == "R2_SINGLE_DETECTOR_TARGETED" else None)
    return metric_catalog(bundle)


class Interval(FrozenMetadata):
    metric_id: Text
    point_estimate: FiniteFloat | None
    ci_lower: FiniteFloat | None
    ci_upper: FiniteFloat | None
    replicates_requested: Annotated[Count, Field(ge=1)]
    replicates_valid: Count
    replicates_invalid: Count
    status: Literal["ESTIMATED", "OBSERVED_UNDEFINED", "UNSTABLE_DENOMINATOR"]

    @model_validator(mode="after")
    def policy(self):
        require(self.replicates_valid+self.replicates_invalid == self.replicates_requested, "INTERVAL_REPLICATE_COUNT_CONFLICT")
        expected = "OBSERVED_UNDEFINED" if self.point_estimate is None else "UNSTABLE_DENOMINATOR" if 100*self.replicates_valid < 95*self.replicates_requested else "ESTIMATED"
        require(self.status == expected, "INTERVAL_SUPPORT_POLICY_CONFLICT")
        require((self.ci_lower is not None) == (expected == "ESTIMATED") and
                (self.ci_upper is not None) == (expected == "ESTIMATED"), "INTERVAL_NULL_POLICY_CONFLICT")
        if expected == "ESTIMATED":
            require(self.ci_lower <= self.ci_upper, "INTERVAL_ORDER_CONFLICT")
        return self


class UncertaintyResult(FrozenMetadata):
    result_version: Literal["uncertainty_result_v1"] = "uncertainty_result_v1"
    config: BootstrapConfig
    experiment_id: Text
    decision_view: Text
    alignment_sha: Digest
    regime_manifest_sha: Digest
    detector_manifest_sha: Digest
    prediction_schema_sha: Digest
    operating_policy_sha: Digest | None
    core_metrics_contract_sha: Literal[CORE_CONTRACT_SHA] = CORE_CONTRACT_SHA
    uncertainty_contract_sha: Digest
    plan_sha: Digest
    population_signature: Digest
    rng_state_before_sha: Digest
    rng_state_after_sha: Digest
    bootstrap_domain_row_count: Count
    bootstrap_domain_lineage_count: Count
    lineage_count: Count
    unknown_lineage_rows: Count
    numpy_version: Text
    intervals: tuple[Interval, ...]
    paired_reference_alignment_sha: Digest | None = None

    @model_validator(mode="after")
    def binding(self):
        require(self.uncertainty_contract_sha == uncertainty_contract_sha(), "UNCERTAINTY_CONTRACT_HASH_MISMATCH")
        require(tuple(i.metric_id for i in self.intervals) == tuple(sorted({i.metric_id for i in self.intervals})), "INTERVAL_ORDER_CONFLICT")
        require(all(i.replicates_requested == self.config.replicates for i in self.intervals), "INTERVAL_CONFIG_CONFLICT")
        return self

    def deterministic_bytes(self):
        return canonical_bytes(self.model_dump(mode="json")) + b"\n"


def validate_metric_domain(metric_ids, config, table):
    available = metric_catalog(evaluate_core(table))
    require(bool(metric_ids) and tuple(metric_ids) == tuple(sorted(set(metric_ids))) and set(metric_ids) <= available.keys(), "UNKNOWN_OR_NONCANONICAL_METRIC_REQUEST")
    for name in metric_ids:
        if name.startswith(("target/", "transfer/")):
            require(config.domain == "VALID_TARGET_ATTEMPTS" and name.split("/")[1] == table.provenance.primary_detector_ids[PRIMARY.index(config.target_detector)], "TARGET_METRIC_DOMAIN_CONFLICT")
        elif name.startswith(("pair/", "pattern/", "recovery/", "all_three/")) or name.endswith(("/fnr", "/recall")):
            require(config.domain == "ATTACK_ONLY", "ATTACK_METRIC_DOMAIN_REQUIRED")
        elif name.endswith(("/fpr", "/specificity")):
            require(config.domain == "BENIGN_ONLY", "BENIGN_METRIC_DOMAIN_REQUIRED")
        else:
            require(config.domain == "STRATIFIED_LABEL", "MIXED_METRIC_DOMAIN_REQUIRED")
    return available


def bootstrap_metrics(table, metric_ids, config, *, paired_reference=None, plan=None):
    """Observed core point, valid-only percentile CI; optional B-minus-A paired delta."""
    config = BootstrapConfig.model_validate(config.model_dump())
    metric_ids = tuple(sorted(metric_ids))
    point = validate_metric_domain(metric_ids, config, table)
    observed = _Accounting(table)
    if paired_reference is not None:
        require(population_signature(paired_reference) == population_signature(table), "PAIRED_POPULATION_CORRESPONDENCE_REQUIRED")
        require(all(getattr(table.provenance,k) == getattr(paired_reference.provenance,k) for k in
            ("decision_view","operating_policy_sha","primary_detector_labels","primary_detector_ids","threat_regime")), "PAIRED_VIEW_OR_DETECTOR_CONFLICT")
        reference_point = validate_metric_domain(metric_ids, config, paired_reference)
        reference_accounting = _Accounting(paired_reference)
        point = {m:point[m]-reference_point[m] if point[m] is not None and reference_point[m] is not None else None for m in metric_ids}
    plan = make_plan(table, config) if plan is None else plan
    plan = validate_plan(table, config, plan)
    valid = {m:[] for m in metric_ids}
    for indices in plan.resamples:
        values = _weighted_values(observed, table, indices)
        if paired_reference is not None:
            reference = _weighted_values(reference_accounting, paired_reference, indices)
            values = {m:values[m]-reference[m] if values[m] is not None and reference[m] is not None else None for m in metric_ids}
        for name in metric_ids:
            value = values[name]
            if value is not None:
                require(np.isfinite(value), "NONFINITE_BOOTSTRAP_METRIC")
                if paired_reference is None:
                    require(-1 <= value <= 1 if name.endswith("/ejf") else 0 <= value <= 1, "OUT_OF_RANGE_BOOTSTRAP_METRIC")
                valid[name].append(value)
    intervals = []
    for name in metric_ids:
        support = len(valid[name])
        status = "OBSERVED_UNDEFINED" if point[name] is None else "UNSTABLE_DENOMINATOR" if 100*support < 95*config.replicates else "ESTIMATED"
        endpoints = np.quantile(valid[name], [.025,.975], method=config.quantile_method) if status == "ESTIMATED" else (None,None)
        intervals.append(Interval(metric_id=name, point_estimate=point[name], ci_lower=float(endpoints[0]) if endpoints[0] is not None else None,
            ci_upper=float(endpoints[1]) if endpoints[1] is not None else None, replicates_requested=config.replicates,
            replicates_valid=support, replicates_invalid=config.replicates-support, status=status))
    p = table.provenance
    return UncertaintyResult(config=config, experiment_id=p.experiment_id, decision_view=p.decision_view, alignment_sha=table.alignment_sha,
        regime_manifest_sha=p.regime_manifest_sha, detector_manifest_sha=p.detector_manifest_sha, prediction_schema_sha=p.prediction_schema_sha,
        operating_policy_sha=p.operating_policy_sha, uncertainty_contract_sha=uncertainty_contract_sha(), plan_sha=plan.plan_sha, population_signature=plan.population_signature,
        rng_state_before_sha=plan.rng_state_before_sha,rng_state_after_sha=plan.rng_state_after_sha,
        bootstrap_domain_row_count=len(plan.domain_indices),bootstrap_domain_lineage_count=len({table.rows[i].lineage_id for i in plan.domain_indices if table.rows[i].lineage_id is not None}),
        lineage_count=len({r.lineage_id for r in table.rows if r.lineage_id is not None}), unknown_lineage_rows=sum(r.lineage_id is None for r in table.rows),
        numpy_version=np.__version__, intervals=tuple(intervals), paired_reference_alignment_sha=paired_reference.alignment_sha if paired_reference else None)
