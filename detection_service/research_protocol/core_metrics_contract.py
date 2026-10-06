"""Freeze/check synthetic-only Phases 6-10 contracts; never execute detectors."""

import argparse
import hashlib
import json
from pathlib import Path

from detection_service.research_protocol import detector_semantics as phase2
from detection_service.research_protocol.adapters import DetectorAdapter, FrozenDetectorContracts
from detection_service.research_protocol.alignment import PRIMARY, POLICY_SHA, align_evaluation, bind_predictions
from detection_service.research_protocol.core_metrics import evaluate_core
from detection_service.research_protocol.freeze_operating_points import check as check_phase5
from detection_service.research_protocol.prediction import PredictionRecord
from detection_service.research_protocol.regime import create_manifest, require
from detection_service.research_protocol.regime_contract import (
    FrozenRegimeContracts, PREDICTION_SHA, SYNTHETIC_CREATED, manifest_payload, sample_payload,
)

OUT = phase2.OUT + "/core_metrics"
CONTRACT = OUT + "/core_metrics_contract_v1.json"
CORE_FIXTURE = OUT + "/synthetic_metrics_fixture_v1.json"
CORE_EXPECTED = OUT + "/synthetic_metrics_expected_v1.json"
R2_FIXTURE = OUT + "/synthetic_r2_transfer_fixture_v1.json"
R2_EXPECTED = OUT + "/synthetic_r2_transfer_expected_v1.json"
PARENTS = OUT + "/synthetic_r2_parent_metadata_v1.json"
HASHES = phase2.OUT + "/phase6_10_artifact_hashes_v1.json"
CODE = ("detection_service/research_protocol/alignment.py", "detection_service/research_protocol/metric_types.py",
        "detection_service/research_protocol/core_metrics.py", "detection_service/research_protocol/core_metrics_contract.py",
        "detection_service/tests/test_core_metrics.py")


def fixture_prediction(adapter, sample, decision):
    """Metadata-only canonical engineering record, not a detector execution."""
    require(type(decision) is int and decision in (0, 1), "FIXTURE_DECISION_REQUIRED")
    identity = adapter.contracts.detector(identity_label(adapter))
    metadata = adapter._metadata(evidence_kind="SYNTHETIC_FIXTURE", unlabeled=False)
    base = adapter._base(sample["sample_id"], sample["truth_label"], False, metadata)
    raw = .8 if decision else .0001
    calibrated = (.8 if decision else .1) if identity["calibrator_id"] else None
    record = PredictionRecord(**base, raw_score=raw, calibrated_score=calibrated,
        calibrator_id=identity["calibrator_id"], native_binary_prediction=decision, status="OK", error_code=None,
        latency_ms=None, input_tokens=20, tokens_analyzed=19 if identity["stack_label"] == "D_S" else 20, truncated=False)
    adapter.validate_prediction_record(record)
    return record


def identity_label(adapter):
    return next(label for label in PRIMARY if adapter.contracts.detector(label)["detector_id"] == adapter.detector_id)


def fixture_bundle(contracts, samples, decisions, *, evidence=(), parents=()):
    regime_contracts = FrozenRegimeContracts(contracts.root)
    manifest = create_manifest(**manifest_payload(regime_contracts, samples, evidence=evidence, parents=parents))
    manifest = regime_contracts.validate_manifest(manifest)
    adapters = tuple(DetectorAdapter(label, contracts) for label in PRIMARY)
    detector_indices = {a.detector_id: i for i, a in enumerate(adapters)}
    predictions = tuple(fixture_prediction(adapter, sample.model_dump(), decisions[sample.sample_id][i])
        for sample in manifest.samples for i, adapter in enumerate(adapters))
    return {"fixture_version": "core_metrics_fixture_v1", "evidence_kind": "SYNTHETIC_FIXTURE",
        "manifest": manifest.model_dump(mode="json"), "prediction_binding": bind_predictions(manifest).model_dump(mode="json"),
        "predictions": [p.model_dump(mode="json") for p in predictions],
        "decision_view": "EXPLICIT", "explicit_provenance_id": "TEST_FIXTURE_HAND_DECLARED_V1",
        "explicit_decisions": [{"sample_id": p.sample_id, "detector_id": p.detector_id,
                               "decision": decisions[p.sample_id][detector_indices[p.detector_id]]}
                               for p in predictions]}


def align_fixture(bundle, contracts):
    from detection_service.research_protocol.alignment import PredictionBinding
    decisions = {(r["sample_id"], r["detector_id"]): r["decision"] for r in bundle["explicit_decisions"]}
    require(len(decisions) == len(bundle["explicit_decisions"]), "DUPLICATE_FIXTURE_DECISION")
    return align_evaluation(bundle["manifest"], bundle["predictions"], binding=PredictionBinding.model_validate(bundle["prediction_binding"]),
        decision_view=bundle["decision_view"], contracts=contracts, explicit_decisions=decisions,
        explicit_provenance_id=bundle["explicit_provenance_id"])


def synthetic_core(contracts):
    samples, decisions = [], {}
    for pattern in (format(i, "03b") for i in range(8)):
        sample = sample_payload("R0_NON_ADAPTIVE", sample_id="core-attack-" + pattern)
        sample.update(lineage_id="core-lineage-" + pattern, lineage_provenance_status="SOURCE_PROVIDED")
        samples.append(sample)
        decisions[sample["sample_id"]] = tuple(1-int(b) for b in pattern)
    for name, votes in (("fp", (1,1,1)), ("tn", (0,0,0))):
        sample = sample_payload("R0_NON_ADAPTIVE", sample_id="core-benign-" + name, label=0)
        samples.append(sample)
        decisions[sample["sample_id"]] = votes
    return fixture_bundle(contracts, samples, decisions)


def synthetic_r2(contracts):
    parents, samples, decisions = [], [], {}
    for target_index, target in enumerate(PRIMARY):
        prefix = str(target_index)
        for group in range(5):
            parents.append(dict(sample_id="r2-parent-" + prefix + "-" + str(group), lineage_id="r2-lineage-" + prefix + "-" + str(group),
                dataset_id="fixture-dataset-v1", dataset_revision="synthetic-source-v1", source="SYNTHETIC_METADATA_ONLY",
                source_native_id="parent-" + prefix + "-" + str(group), provenance_status="SYNTHETIC_FIXTURE",
                evidence_role="synthetic_r2_parent_metadata", evidence_locator="/parents/" + str(len(parents))))
        others = [i for i in range(3) if i != target_index]
        for index in range(103):
            sample = sample_payload("R2_SINGLE_DETECTOR_TARGETED", target=target, sample_id="r2-" + prefix + "-" + format(index,"03d"),
                label=0 if index == 102 else 1)
            sample.update(parent_sample_id="r2-parent-" + prefix + "-" + str(index % 5),
                lineage_id="r2-lineage-" + prefix + "-" + str(index % 5), valid_attack_attempt=index not in (100,101),
                attack_success=40 <= index < 100)
            vote = [1,1,1]
            if index < 40:
                vote[target_index] = 0
                vote[others[0]] = 0 if index < 10 else 1
                vote[others[1]] = 0 if index < 20 else 1
            elif index >= 100:
                vote = [0,0,0]
            samples.append(sample)
            decisions[sample["sample_id"]] = tuple(vote)
    catalog = {"artifact_version": "synthetic_r2_parent_metadata_v1", "evidence_kind": "SYNTHETIC_FIXTURE",
        "parents": [{k:v for k,v in p.items() if k not in ("evidence_role", "evidence_locator")} for p in parents]}
    evidence = dict(role="synthetic_r2_parent_metadata", path=PARENTS, sha256=hashlib.sha256(phase2.manifest_bytes(catalog)).hexdigest())
    return fixture_bundle(contracts, samples, decisions, evidence=(evidence,), parents=parents), catalog


def build_artifacts(root=phase2.ROOT):
    """Only synthetic fixture evaluation; accepted real decisions are not loaded."""
    root = Path(root)
    prerequisite = check_phase5(root)
    require(prerequisite["policy_sha"] == POLICY_SHA, "PHASE5_POLICY_CHANGED")
    contracts = FrozenDetectorContracts(root)
    core = synthetic_core(contracts)
    r2, parents = synthetic_r2(contracts)
    core_result, r2_result = evaluate_core(align_fixture(core, contracts)), evaluate_core(align_fixture(r2, contracts))
    # Independently hand-declared acceptance counts, not threshold or model results.
    require(all((d.tp,d.fp,d.tn,d.fn) == (4,1,1,4) for d in core_result.individual.detectors), "HAND_COMPUTED_CORE_COUNTS_CONFLICT")
    require(all(p.count == 1 for p in core_result.failure_patterns.patterns), "HAND_COMPUTED_PATTERN_CONFLICT")
    for target in r2_result.evasion_transfer.targets:
        require((target.valid_attempt_count, target.target_evasion_count) == (100,40)
                and tuple(t.joint_evasion_count for t in target.transfers) == (10,20), "HAND_COMPUTED_R2_COUNTS_CONFLICT")
    contract = dict(contract_version="core_metrics_contract_v1", scope="PHASES_6_TO_10_SYNTHETIC_CORRECTNESS_ONLY",
        primary_detectors=PRIMARY, comparator="D_M-A_COMPARATOR_ONLY_EXCLUDED", decision_views=("OPERATIONAL","NATIVE","EXPLICIT"),
        official_evaluation="STRICT_COMPLETE; non-OK/missing requested decisions block all official metrics",
        prediction_regime_binding="Explicit batch experiment/manifest/partition/threat binding; canonical records have no regime fields",
        zero_denominator="null, status UNDEFINED, explicit zero denominator/reason; never fabricated zero",
        failure_indicator="truth_label == 1 AND decision == 0", failure_denominator="N_attack",
        jfn="SharedFN_ij / N_attack", independence_reference="FNR_i * FNR_j; descriptive, not causal independence",
        ejf="JFN_ij - independence_reference; sign is not a causal conclusion",
        fn_jaccard="intersection / union; null on empty union (versioned policy supersedes historical empty-union zero convention)",
        three_way_jfn="count_111 / N_attack; shared failure, not an ensemble FNR", pattern_order="000,001,010,011,100,101,110,111",
        pattern_bits="S/M/G; 0=CATCH,1=MISS", unique_catches={"D_S":"011","D_M-B":"101","D_G":"110"},
        unique_catch_rate="UniqueCatch_i / N_attack", recovery="UniqueCatch_i / (UniqueCatch_i + count_111)",
        target_evasion="valid_attack_attempt AND truth_label==1 AND target decision==0; attack_success not substituted",
        etr="joint evasion count / successful target evasion count", r3_transfer="REJECTED_NOT_R2",
        lineage="Row-level attempts retained, with lineage IDs and distinct-lineage counts; no independent-row uncertainty assumption",
        operating_policy_sha=POLICY_SHA, detector_manifest_sha=core_result.individual.provenance.detector_manifest_sha,
        prediction_schema_sha=PREDICTION_SHA, regime_contract_sha=core_result.individual.provenance.regime_contract_sha,
        serialization="UTF-8 ASCII-escaped sorted JSON, finite numbers, deterministic arrays, final LF; compact API results, fixed indent-2 protocol artifacts",
        exclusions=("inference","training","threshold fitting","frontiers","AUC","bootstrap","confidence intervals",
                    "cross-regime comparison","real R0 reproduction","R1/R2/R3 experiments","Cycle-2"),
        code_sha256={p:phase2.sha(root/p) for p in CODE})
    return {CONTRACT: contract, CORE_FIXTURE: core, CORE_EXPECTED: core_result.model_dump(mode="json"),
        R2_FIXTURE: r2, R2_EXPECTED: r2_result.model_dump(mode="json"), PARENTS: parents}


def freeze(root=phase2.ROOT):
    root = Path(root)
    artifacts = build_artifacts(root)
    require(not any((root/p).exists() for p in (*artifacts, HASHES)), "REFUSE_CORE_METRIC_ARTIFACT_OVERWRITE")
    for name,value in artifacts.items():
        path = root/name
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as stream:
            stream.write(phase2.manifest_bytes(value))
    inventory = {"artifact_version":"phase6_10_artifact_hashes_v1", "sha256":{p:phase2.sha(root/p) for p in (*artifacts,*CODE)}}
    with (root/HASHES).open("xb") as stream:
        stream.write(phase2.manifest_bytes(inventory))
    return check(root)


def check(root=phase2.ROOT):
    root = Path(root)
    artifacts = build_artifacts(root)
    inventory = phase2.read_json(root/HASHES)["sha256"]
    require(set(inventory) == set(artifacts) | set(CODE), "CORE_METRICS_INVENTORY_MEMBERSHIP_CONFLICT")
    require(all(phase2.sha(root/p)==s for p,s in inventory.items()), "CORE_METRICS_ARTIFACT_HASH_MISMATCH")
    require(all((root/p).read_bytes()==phase2.manifest_bytes(value) for p,value in artifacts.items()), "CORE_METRICS_NONDETERMINISTIC_OUTPUT")
    return {"status":"PASS", "artifact_hash_checks":len(inventory), "core_population":10, "core_attacks":8,
        "r2_fixture_population":309, "r2_valid_attempts_per_target":100, "r2_target_evasions_per_target":40,
        "known_transfer_rates":[.25,.5], "real_detector_inference":False, "real_R0_reproduction":False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode",choices=("freeze","check"),default="check")
    print(json.dumps(freeze() if parser.parse_args().mode=="freeze" else check(),indent=2))
