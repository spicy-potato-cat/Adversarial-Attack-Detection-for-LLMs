"""Explicit legacy RNG replay; the pre-R0 production PCG64 contract is unchanged."""

import platform
import random

import numpy as np

from detection_service.research_protocol.alignment import digest
from detection_service.research_protocol.core_metrics import _Accounting, evaluate_core
from detection_service.research_protocol.metric_catalog import metric_catalog
from detection_service.research_protocol.regime import require
from detection_service.research_protocol.uncertainty import (
    BootstrapConfig, Interval, _weighted_values, population_signature, sampling_units, uncertainty_contract_sha,
)


def historical_lineage_plan(table, config):
    """Reproduce the accepted Random.randrange stream on sorted whole clusters."""
    config = BootstrapConfig.model_validate(config.model_dump())
    require(config.unit == "LINEAGE_CLUSTERED" and config.domain == "ATTACK_ONLY", "HISTORICAL_PLAN_REQUIRES_ATTACK_LINEAGES")
    indices,strata = sampling_units(table,config)
    units = strata[0]
    require(bool(units),"HISTORICAL_BOOTSTRAP_EMPTY_POPULATION")
    rng = random.Random(config.seed)
    before = digest(rng.getstate())
    draws = tuple(tuple(i for _ in units for i in units[rng.randrange(len(units))]) for _ in range(config.replicates))
    metadata = dict(plan_version="historical_random_lineage_plan_v1",rng="python.random.Random/MT19937",
        python_version=platform.python_version(),seed=config.seed,replicates=config.replicates,
        unit=config.unit,domain=config.domain,domain_rows=len(indices),lineage_units=len(units),
        population_signature=population_signature(table),draw_indices_sha=digest(draws),
        rng_state_before_sha=before,rng_state_after_sha=digest(rng.getstate()),
        stream_policy="Reset Random(seed) for each budget; sorted lineage keys; randrange once per selected cluster")
    metadata["plan_sha"] = digest(metadata)
    return draws,metadata


def replay_historical_uncertainty(table, metric_ids, *, config=None):
    config = config or BootstrapConfig(unit="LINEAGE_CLUSTERED",domain="ATTACK_ONLY")
    from detection_service.research_protocol.uncertainty import validate_metric_domain
    names = tuple(sorted(metric_ids))
    observed = validate_metric_domain(names,config,table)
    draws,plan = historical_lineage_plan(table,config)
    accounting = _Accounting(table)
    values = {k:[] for k in names}
    for indices in draws:
        metrics = _weighted_values(accounting,table,indices)
        for name in names:
            if metrics[name] is not None:
                require(np.isfinite(metrics[name]),"NONFINITE_HISTORICAL_METRIC")
                values[name].append(metrics[name])
    intervals = []
    for name in names:
        count = len(values[name])
        status = "OBSERVED_UNDEFINED" if observed[name] is None else "UNSTABLE_DENOMINATOR" if 100*count < 95*config.replicates else "ESTIMATED"
        low,high = np.quantile(values[name],[.025,.975],method="linear") if status=="ESTIMATED" else (None,None)
        interval = Interval(metric_id=name,point_estimate=observed[name],ci_lower=float(low) if low is not None else None,
            ci_upper=float(high) if high is not None else None,replicates_requested=config.replicates,replicates_valid=count,
            replicates_invalid=config.replicates-count,status=status)
        intervals.append(interval.model_dump(mode="json"))
    return dict(result_version="historical_uncertainty_replay_v1",config=config.model_dump(mode="json"),
        plan=plan,alignment_sha=table.alignment_sha,regime_manifest_sha=table.provenance.regime_manifest_sha,
        decision_view=table.provenance.decision_view,experiment_id=table.provenance.experiment_id,
        estimator_reference_uncertainty_contract_sha=uncertainty_contract_sha(),intervals=intervals,
        compliance="HISTORICAL_RNG_REPLAY_NOT_PRODUCTION_PCG64",
        method_difference="Accepted Python Random.randrange stream differs from predeclared PCG64; linear percentile estimator and core metric formulas agree",
        production_contract_modified=False)
