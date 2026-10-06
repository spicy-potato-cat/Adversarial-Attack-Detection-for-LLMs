"""Provenance-bound regime bundles and descriptive, unpaired comparisons."""

from typing import Literal

from pydantic import model_validator

from detection_service.research_protocol.alignment import PRIMARY, POLICY_SHA
from detection_service.research_protocol.core_metrics import CoreMetricsResult, evaluate_core
from detection_service.research_protocol.metric_catalog import metric_catalog
from detection_service.research_protocol.prediction import Count, Digest
from detection_service.research_protocol.regime import FrozenMetadata, Partition, RegimeManifest, Text, ThreatRegime, canonical_bytes, require
from detection_service.research_protocol.uncertainty import CORE_CONTRACT_SHA, UncertaintyResult, uncertainty_contract_sha

SLOTS = ("R0", "R1", "R2-D_S", "R2-D_M-B", "R2-D_G", "R3")
VIEWS = ("OPERATIONAL_FIXED_V1", "NATIVE_V1", "HISTORICAL_DESCRIPTIVE_1PCT_V1",
         "HISTORICAL_DESCRIPTIVE_3PCT_V1", "HISTORICAL_DESCRIPTIVE_5PCT_V1")


def cross_regime_contract():
    return dict(contract_version="cross_regime_contract_v1", regimes=list(SLOTS), comparison_views=list(VIEWS),
        states=["OBSERVED","NOT_RUN","NOT_APPLICABLE","UNDEFINED","INCOMPATIBLE"],
        primary_detectors=list(PRIMARY), core_metrics_contract_sha=CORE_CONTRACT_SHA,
        label_semantics="BINARY_ATTACK_1_BENIGN_0_V1", definition_version="core_metrics_bundle_v1",
        difference="current minus reference; fraction and percentage points; descriptive, unpaired",
        compatibility="Same primary IDs/order, detector manifest, label semantics, core hash and decision/comparison view; same operational policy if operational",
        missing="NOT_RUN with null point, never zero", r2_scope="Target evasion and ETR only for matching R2 target",
        uncertainty="Carry provenance-bound intervals; no significance or causal conclusions", real_future_experiments=False)


class RegimeResultBundle(FrozenMetadata):
    result_version: Literal["regime_result_bundle_v1"] = "regime_result_bundle_v1"
    experiment_id: Text
    dataset_id: Text
    dataset_revision: Text
    partition: Partition
    threat_regime: ThreatRegime
    target_detector: Literal["D_S", "D_M-B", "D_G", "ALL"] | None
    decision_view: Literal["EXPLICIT", "NATIVE", "OPERATIONAL"]
    comparison_view_id: Literal[*VIEWS]
    label_semantics: Text = "BINARY_ATTACK_1_BENIGN_0_V1"
    regime_manifest_hash: Digest
    detector_manifest_hash: Digest
    prediction_schema_hash: Digest
    core_metrics_contract_hash: Digest = CORE_CONTRACT_SHA
    operating_point_manifest_hash: Digest | None
    uncertainty_contract_hash: Digest | None
    population_count: Count
    attack_count: Count
    benign_count: Count
    lineage_count: Count
    unknown_lineage_rows: Count
    core_metrics: CoreMetricsResult
    uncertainty: tuple[UncertaintyResult, ...] = ()
    status: Literal["OBSERVED"] = "OBSERVED"

    @model_validator(mode="after")
    def relations(self):
        result = self.core_metrics.individual
        p = result.provenance
        require(p.primary_detector_ids == ("ds_v2","dm_b_v1","dg_v1") and result.coverage.status == "COMPLETE", "AUTHORITATIVE_PRIMARY_COMPLETE_BUNDLE_REQUIRED")
        require((self.experiment_id,self.partition,self.threat_regime,self.decision_view,self.regime_manifest_hash,
                 self.detector_manifest_hash,self.prediction_schema_hash,self.operating_point_manifest_hash) ==
                (p.experiment_id,p.partition,p.threat_regime,p.decision_view,p.regime_manifest_sha,
                 p.detector_manifest_sha,p.prediction_schema_sha,p.operating_policy_sha), "BUNDLE_PROVENANCE_CONFLICT")
        require((self.population_count,self.attack_count,self.benign_count) ==
                (result.population_count,result.attack_count,result.benign_count), "BUNDLE_POPULATION_CONFLICT")
        require(self.lineage_count+self.unknown_lineage_rows <= self.population_count, "BUNDLE_LINEAGE_COUNT_CONFLICT")
        require(self.core_metrics_contract_hash == CORE_CONTRACT_SHA, "CORE_METRICS_CONTRACT_CHANGED")
        expected_view = "OPERATIONAL" if self.comparison_view_id == "OPERATIONAL_FIXED_V1" else "NATIVE" if self.comparison_view_id == "NATIVE_V1" else "EXPLICIT"
        require(self.decision_view == expected_view, "COMPARISON_DECISION_VIEW_CONFLICT")
        if expected_view == "OPERATIONAL":
            require(self.operating_point_manifest_hash == POLICY_SHA, "OPERATIONAL_POLICY_HASH_REQUIRED")
        else:
            require(self.operating_point_manifest_hash is None, "DESCRIPTIVE_VIEW_HAS_OPERATIONAL_POLICY")
        r2 = self.threat_regime == "R2_SINGLE_DETECTOR_TARGETED"
        require(self.target_detector in PRIMARY if r2 else self.target_detector == ("ALL" if self.threat_regime.startswith("R3_") else None), "BUNDLE_TARGET_CONFLICT")
        require(self.uncertainty_contract_hash == (uncertainty_contract_sha() if self.uncertainty else None), "BUNDLE_UNCERTAINTY_HASH_CONFLICT")
        values = metric_catalog(self.core_metrics)
        keys = []
        for uncertainty in self.uncertainty:
            require(uncertainty.alignment_sha == result.alignment_sha and uncertainty.config.target_detector in (None,self.target_detector)
                    and uncertainty.paired_reference_alignment_sha is None, "BUNDLE_UNCERTAINTY_POPULATION_CONFLICT")
            for interval in uncertainty.intervals:
                require(interval.metric_id in values and interval.point_estimate == values[interval.metric_id], "BUNDLE_UNCERTAINTY_POINT_CONFLICT")
                keys.append(interval.metric_id)
        require(len(set(keys)) == len(keys), "DUPLICATE_BUNDLE_INTERVAL")
        return self

    def deterministic_bytes(self):
        return canonical_bytes(self.model_dump(mode="json")) + b"\n"


def result_bundle(table, manifest, comparison_view_id, *, uncertainty=()):
    table.require_complete()
    manifest = RegimeManifest.model_validate_json(manifest.model_dump_json())
    require((manifest.manifest_hash,manifest.experiment_id) == (table.provenance.regime_manifest_sha,table.provenance.experiment_id), "BUNDLE_MANIFEST_BINDING_CONFLICT")
    targets = {r.target_detector for r in table.rows}
    require(len(targets) == 1, "BUNDLE_REQUIRES_SINGLE_REGIME_TARGET")
    p = table.provenance
    return RegimeResultBundle(experiment_id=p.experiment_id,dataset_id=manifest.dataset_id,dataset_revision=manifest.dataset_revision,
        partition=p.partition,threat_regime=p.threat_regime,target_detector=targets.pop(),decision_view=p.decision_view,
        comparison_view_id=comparison_view_id,regime_manifest_hash=p.regime_manifest_sha,detector_manifest_hash=p.detector_manifest_sha,
        prediction_schema_hash=p.prediction_schema_sha,operating_point_manifest_hash=p.operating_policy_sha,
        uncertainty_contract_hash=uncertainty_contract_sha() if uncertainty else None,
        population_count=len(table.rows),attack_count=sum(r.truth_label for r in table.rows),benign_count=sum(not r.truth_label for r in table.rows),
        lineage_count=len({r.lineage_id for r in table.rows if r.lineage_id is not None}),unknown_lineage_rows=sum(r.lineage_id is None for r in table.rows),
        core_metrics=evaluate_core(table),uncertainty=tuple(uncertainty))


def compatibility(reference, current):
    for bundle in (reference,current):
        RegimeResultBundle.model_validate(bundle.model_dump())
    fields = ("detector_manifest_hash","core_metrics_contract_hash","label_semantics","decision_view","comparison_view_id")
    reasons = [k for k in fields if getattr(reference,k) != getattr(current,k)]
    for k in ("primary_detector_ids","primary_detector_labels"):
        if getattr(reference.core_metrics.individual.provenance,k) != getattr(current.core_metrics.individual.provenance,k):
            reasons.append(k)
    if reference.decision_view == "OPERATIONAL" and reference.operating_point_manifest_hash != current.operating_point_manifest_hash:
        reasons.append("operating_point_manifest_hash")
    return tuple(reasons)


def compare_bundles(reference, current):
    reasons = compatibility(reference,current)
    base = dict(comparison_version="cross_regime_comparison_v1",reference_experiment_id=reference.experiment_id,
        current_experiment_id=current.experiment_id,paired=False,interpretation="DESCRIPTIVE_UNPAIRED_RATE_DIFFERENCE",
        status="INCOMPATIBLE" if reasons else "OBSERVED",incompatibilities=list(reasons),metrics={})
    if reasons:
        return base
    left, right = metric_catalog(reference.core_metrics), metric_catalog(current.core_metrics)
    for name in sorted(left.keys() | right.keys()):
        if name not in left or name not in right:
            state, delta = "NOT_APPLICABLE", None
        elif left[name] is None or right[name] is None:
            state, delta = "UNDEFINED", None
        else:
            state, delta = "OBSERVED", right[name]-left[name]
        base["metrics"][name] = dict(status=state,delta_fraction=delta,delta_percentage_points=100*delta if delta is not None else None)
    return base


def slot(bundle):
    return "R2-"+bundle.target_detector if bundle.threat_regime.startswith("R2_") else bundle.threat_regime.split("_")[0]


def cross_regime_matrix(bundles, *, reference_slot=None):
    indexed = {}
    for bundle in bundles:
        RegimeResultBundle.model_validate(bundle.model_dump())
        key = slot(bundle)
        require(key not in indexed, "DUPLICATE_REGIME_SLOT")
        indexed[key] = bundle
    require(reference_slot is None or reference_slot in indexed, "MATRIX_REFERENCE_NOT_OBSERVED")
    catalogs = {key:metric_catalog(bundle.core_metrics) for key,bundle in indexed.items()}
    interval_maps = {key:{i.metric_id:i for u in bundle.uncertainty for i in u.intervals} for key,bundle in indexed.items()}
    incompatible_slots = {key for key,bundle in indexed.items() if reference_slot is not None and compatibility(indexed[reference_slot],bundle)}
    metrics = set()
    for bundle in bundles:
        metrics.update(metric_catalog(bundle.core_metrics))
    # Represent R2-only applicability even when no R2 experiment exists.
    ids = ("ds_v2","dm_b_v1","dg_v1")
    for target in ids:
        metrics.add(f"target/{target}/evasion")
        metrics.update(f"transfer/{target}/{other}/etr" for other in ids if other != target)
    rows = {}
    for name in sorted(metrics):
        cells = {}
        for key in SLOTS:
            r2_only = name.startswith(("target/","transfer/"))
            applicable = not r2_only or key.startswith("R2-") and name.split("/")[1] == ids[PRIMARY.index(key[3:])]
            bundle = indexed.get(key)
            incompatible = key in incompatible_slots
            value = catalogs.get(key,{}).get(name)
            status = "NOT_APPLICABLE" if not applicable else "NOT_RUN" if bundle is None else "INCOMPATIBLE" if incompatible else "UNDEFINED" if value is None else "OBSERVED"
            interval = interval_maps.get(key,{}).get(name)
            cells[key] = dict(status=status,point_estimate=value if status=="OBSERVED" else None,
                uncertainty=interval.model_dump(mode="json") if interval is not None and status=="OBSERVED" else None)
        rows[name] = cells
    return dict(matrix_version="cross_regime_matrix_v1",columns=list(SLOTS),reference_slot=reference_slot,paired=False,
        regime_status={k:"OBSERVED" if k in indexed else "NOT_RUN" for k in SLOTS},metrics=rows)
