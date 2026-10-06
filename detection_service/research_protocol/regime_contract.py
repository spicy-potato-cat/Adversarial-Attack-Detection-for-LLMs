"""Bind/freeze Phase-4 metadata. No model imports, prompts, predictions or metrics."""

import argparse
import csv
import hashlib
import json
from pathlib import Path
import subprocess
from typing import get_args

from detection_service.research_protocol import detector_semantics as phase2
from detection_service.research_protocol import prediction_contract as phase3
from detection_service.research_protocol.adapters import DetectorAdapter, FrozenDetectorContracts, PHASE2_SHA
from detection_service.research_protocol.prediction import PredictionRecord
from detection_service.research_protocol.regime import (
    Partition, RegimeManifest, RegimeSample, Target, ThreatRegime, create_manifest,
    manifest_schema, require, sample_schema,
)

PREDICTION_SHA = "f61cc717b6118e288201ee8525b41e6806a642d665c42c0d1b9d6d1bcde2e484"
ADAPTER_SHA = "43bdae201bc7faf23ea8a2ecadda69e28eeb4d775d0f12a6c005a894d958b9b3"
OUT = phase2.OUT
MANIFEST_SCHEMA = OUT + "/schemas/regime_manifest_schema_v1.json"
SAMPLE_SCHEMA = OUT + "/schemas/regime_sample_schema_v1.json"
CONTRACT = OUT + "/regime_contract_manifest_v1.json"
HASHES = OUT + "/phase4_artifact_hashes_v1.json"
R0 = OUT + "/r0/r0_regime_manifest_v1.json"
FIXTURES = OUT + "/fixtures/phase4"
PARENTS = FIXTURES + "/parent_metadata_v1.json"
CREATED = "2026-10-06T19:17:37Z"
SYNTHETIC_CREATED = "2000-01-01T00:00:00Z"
CODE = ("detection_service/research_protocol/regime.py", "detection_service/research_protocol/regime_contract.py",
        "detection_service/tests/test_regime_contract.py")
MEMBERSHIP = "data_governance/manifests/development_partition_manifest_v1.csv"
FOLDS = "artifacts/quality/quality_001/development_folds_v1.csv"
ALIGNMENT = "artifacts/common_mode/development/completion_v3/detector_alignment_v1.json"


class FrozenRegimeContracts:
    def __init__(self, root=phase2.ROOT):
        self.root = Path(root).resolve()
        for path, sha in ((OUT + "/" + phase2.NAME, PHASE2_SHA), (phase3.SCHEMA, PREDICTION_SHA), (phase3.CONTRACT, ADAPTER_SHA)):
            require(phase2.sha(self.root / path) == sha, "AUTHORITATIVE_INPUT_HASH_MISMATCH")
        phase3.check(self.root)
        self.detectors = phase2.read_json(self.root / OUT / phase2.NAME)
        self.targets = tuple(self.detectors["primary_detector_order"])
        require(set(get_args(Target)) == set(self.targets) | {"ALL"}, "PRIMARY_TARGET_ENUM_CONFLICT")
        self.detector_ids = tuple(d["detector_id"] for d in self.detectors["detectors"])

    def validate_manifest(self, manifest):
        payload = manifest.model_dump() if isinstance(manifest, RegimeManifest) else manifest
        value = RegimeManifest.model_validate(payload)
        require(value.primary_detector_manifest_sha == PHASE2_SHA, "DETECTOR_MANIFEST_BINDING_MISMATCH")
        require(value.prediction_schema_sha == PREDICTION_SHA, "PREDICTION_SCHEMA_BINDING_MISMATCH")
        require(value.primary_detector_set_id == self.detectors["stack_id"], "DETECTOR_SET_ID_MISMATCH")
        for row in value.samples:
            if row.threat_regime.startswith("R2_"):
                require(row.target_detector in self.targets, "R2_PRIMARY_TARGET_MISMATCH")
        return value


def validate_prediction_join(manifest, predictions, contracts, *, require_complete=True):
    """Validate identity/uniqueness/labels; preserve non-OK results, never score them."""
    manifest = contracts.validate_manifest(manifest)
    samples = {r.sample_id: r for r in manifest.samples}
    frozen = FrozenDetectorContracts(contracts.root)
    adapters = {a.detector_id: a for a in (DetectorAdapter(label, frozen) for label in contracts.targets)}
    seen = set()
    result = []
    for prediction in predictions:
        payload = prediction.model_dump() if isinstance(prediction, PredictionRecord) else prediction
        record = PredictionRecord.model_validate(payload)
        require(record.sample_id in samples, "PREDICTION_SAMPLE_NOT_IN_MANIFEST")
        require(record.detector_id in adapters, "PREDICTION_NOT_PRIMARY_DETECTOR")
        adapters[record.detector_id].validate_prediction_record(record)
        pair = (record.sample_id, record.detector_id)
        require(pair not in seen, "DUPLICATE_DETECTOR_SAMPLE_PAIR")
        require(record.truth_label is None or record.truth_label == samples[record.sample_id].truth_label, "PREDICTION_TRUTH_LABEL_CONFLICT")
        seen.add(pair)
        result.append(record)
    if require_complete:
        require(seen == {(sample, detector) for sample in samples for detector in adapters}, "MISSING_EXPECTED_PREDICTIONS")
    return tuple(sorted(result, key=lambda r: (r.sample_id, contracts.detector_ids.index(r.detector_id))))


def sample_payload(regime, *, target=None, sample_id="fixture-001", label=1):
    targeted = regime.startswith(("R2_", "R3_"))
    return dict(record_version="regime_sample_v1", sample_id=sample_id, dataset_id="fixture-dataset-v1",
        dataset_revision="synthetic-source-v1", partition="INTERNAL_TEST", threat_regime=regime,
        source="SYNTHETIC_METADATA_ONLY", source_native_id=sample_id, truth_label=label, is_adversarial=bool(label),
        attack_family="FIXTURE_FAMILY" if targeted else "UNKNOWN", attack_family_provenance="PROTOCOL_DECLARED" if targeted else "UNKNOWN",
        target_detector=target, attack_method="fixture-rule" if targeted else None,
        attack_method_revision="fixture-method-v1" if targeted else None,
        generator_type="RULE_BASED" if targeted else None, generator_model=None,
        generator_system="fixture-system" if targeted else None, generator_revision="fixture-system-v1" if targeted else None,
        generated_sample=targeted, generation_evaluation_status="COMPLETED" if targeted else "NOT_APPLICABLE",
        parent_sample_id="fixture-parent-001" if targeted else None, lineage_id="fixture-lineage-001" if targeted else None,
        lineage_provenance_status="DERIVED_FROM_PARENT" if targeted else "UNKNOWN", lineage_justification=None,
        attack_success_definition="FIXTURE_ONLY_SUCCESS_V1" if targeted else None,
        attack_success=False if targeted else None, valid_attack_attempt=True if targeted else None,
        created_at=SYNTHETIC_CREATED, provenance_status="SYNTHETIC_FIXTURE", outer_fold=None)


def manifest_payload(contracts, samples, *, evidence=(), parents=()):
    first = samples[0]
    sources = {(r["dataset_id"], r["dataset_revision"], r["source"]) for r in samples}
    return dict(dataset_id="fixture-dataset-v1", dataset_revision="synthetic-source-v1", partition=first["partition"],
        threat_regime=first["threat_regime"], dataset_source="SYNTHETIC_METADATA_ONLY", dataset_source_revision="synthetic-source-v1",
        dataset_sources=[dict(dataset_id=d, dataset_revision=v, source=s, source_revision=v) for d, v, s in sorted(sources)],
        created_at=SYNTHETIC_CREATED, primary_detector_set_id=contracts.detectors["stack_id"],
        primary_detector_manifest_sha=PHASE2_SHA, prediction_schema_version="prediction_v1", prediction_schema_sha=PREDICTION_SHA,
        status="FROZEN", evidence_kind="SYNTHETIC_FIXTURE", notes=("Engineering metadata fixture; not an authorized or completed experiment.",),
        evidence=evidence, external_parents=parents, samples=samples)


def synthetic_fixtures(contracts):
    parent = dict(sample_id="fixture-parent-001", lineage_id="fixture-lineage-001", dataset_id="fixture-dataset-v1",
        dataset_revision="synthetic-source-v1", source="SYNTHETIC_METADATA_ONLY", source_native_id="P1",
        provenance_status="SYNTHETIC_FIXTURE", evidence_role="synthetic_parent_metadata", evidence_locator="/parents/0")
    catalog = {"artifact_version": "synthetic_parent_metadata_v1", "evidence_kind": "SYNTHETIC_FIXTURE",
               "parents": [{k: v for k, v in parent.items() if k not in ("evidence_role", "evidence_locator")}]}
    evidence = dict(role="synthetic_parent_metadata", path=PARENTS, sha256=hashlib.sha256(phase2.manifest_bytes(catalog)).hexdigest())
    fixtures = {PARENTS: catalog}
    for name, regime, target in (("r0", "R0_NON_ADAPTIVE", None), ("r1", "R1_SHIFTED_UNSEEN", None),
        ("r2_ds", "R2_SINGLE_DETECTOR_TARGETED", "D_S"), ("r2_dmb", "R2_SINGLE_DETECTOR_TARGETED", "D_M-B"),
        ("r2_dg", "R2_SINGLE_DETECTOR_TARGETED", "D_G"), ("r3", "R3_ENSEMBLE_TARGETED", "ALL")):
        rows = [sample_payload(regime, target=target, sample_id="fixture-" + str(i), label=(i % 2 if target is None else 1))
                for i in range(1, 4)]
        m = create_manifest(**manifest_payload(contracts, rows, evidence=(evidence,) if target else (), parents=(parent,) if target else ()))
        fixtures[FIXTURES + "/" + name + "_manifest_v1.json"] = contracts.validate_manifest(m).model_dump(mode="json")
    return fixtures


def read_csv(path):
    with Path(path).open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def accepted_r0(contracts):
    root = contracts.root
    anchor = subprocess.check_output(["git", "show", phase2.BASE + ":" + ALIGNMENT], cwd=root)
    require((root / ALIGNMENT).read_bytes() == anchor, "R0_ALIGNMENT_DIFFERS_FROM_ACCEPTED_CYCLE1")
    alignment = phase2.read_json(root / ALIGNMENT)
    evidence = []
    accepted_hashes = {}
    for role, path in (("membership", MEMBERSHIP), ("folds", FOLDS), ("historical_alignment", ALIGNMENT),
                       ("lineage_policy", "data_governance/DATA_LINEAGE_POLICY_v1.md"),
                       ("partition_policy", "data_governance/DATA_PARTITION_POLICY_v1.md")):
        accepted_hashes[path] = hashlib.sha256(anchor).hexdigest() if path == ALIGNMENT else alignment["input_sha256"][path]
        require(phase2.sha(root / path) == accepted_hashes[path], "R0_METADATA_HASH_MISMATCH")
        evidence.append(dict(role=role, path=path, sha256=accepted_hashes[path]))
    require(alignment["expected_manifest_sha256"] == accepted_hashes[MEMBERSHIP]
            and alignment["fold_sha256"] == accepted_hashes[FOLDS], "R0_ACCEPTED_REVISION_CONFLICT")
    membership = [r for r in read_csv(root / MEMBERSHIP) if r["partition"] == "BASE_TRAIN"]
    folds_list = read_csv(root / FOLDS)
    folds = {r["sample_id"]: r for r in folds_list}
    require(len(folds) == len(folds_list) and len({r["record_id"] for r in membership}) == len(membership), "R0_DUPLICATE_ID")
    require({r["record_id"] for r in membership} == set(folds), "R0_SAMPLE_MEMBERSHIP_CONFLICT")
    samples = []
    for row in membership:
        fold = folds[row["record_id"]]
        require(row["canonical_label"] in ("0", "1") and fold["label"] == row["canonical_label"]
                and fold["lineage_group"] == row["lineage_group_id"] and fold["source_name"] == row["source_dataset"]
                and fold["partition"] == row["partition"] and fold["outer_fold"] in ("0", "1", "2", "3", "4"), "R0_SAMPLE_IDENTITY_CONFLICT")
        require(row["lineage_group_id"] == "LG-N1-" + row["normalized_hash"][:24], "R0_LINEAGE_POLICY_CONFLICT")
        value = sample_payload("R0_NON_ADAPTIVE", sample_id=row["record_id"], label=int(row["canonical_label"]))
        value.update(dataset_id=row["source_dataset_id"], dataset_revision=row["source_revision"], partition="BASE_TRAIN",
            source=row["source_dataset"], source_native_id=row["source_record_id"] or None,
            attack_family=row["attack_family"] or ("UNKNOWN" if row["canonical_label"] == "1" else None),
            attack_family_provenance="ACCEPTED_METADATA" if row["attack_family"] else
                ("UNKNOWN" if row["canonical_label"] == "1" else "NOT_APPLICABLE"),
            lineage_id=row["lineage_group_id"], lineage_provenance_status="CANONICAL_DUPLICATE_GROUP",
            lineage_justification="Accepted N1 normalized-hash grouping; not proof of semantic or documentary independence.",
            created_at=CREATED, provenance_status=row["provenance_status"], outer_fold=int(fold["outer_fold"]))
        samples.append(value)
    payload = manifest_payload(contracts, samples, evidence=evidence)
    payload.update(dataset_id="QUALITY-001-DEVELOPMENT-v1", dataset_revision=accepted_hashes[MEMBERSHIP],
        dataset_source="DATA-PROMOTION-001/QUALITY-001", dataset_source_revision=accepted_hashes[MEMBERSHIP],
        created_at=CREATED, status="COMPLETED", evidence_kind="ACCEPTED_METADATA",
        notes=("Metadata-only representation of historical R0 BASE_TRAIN membership; no inference or results recalculation.",
               "Source provenance remains PARTIAL. N1 lineage controls exact canonical duplicates only.",
               "R0 metadata hashes are bound through alignment evidence in accepted Cycle-1 Git commit " + phase2.BASE + ".",
               "Detector-set binding identifies the stack; it does not relabel fold-local OOF predictions with final-model hashes.",
               "created_at dates this Phase-4 metadata representation, not original samples or historical model execution."))
    manifest = contracts.validate_manifest(create_manifest(**payload))
    require((manifest.sample_count, manifest.attack_count, manifest.benign_count) ==
            (alignment["aligned_samples"], alignment["positive"], alignment["negative"]) == (1135, 183, 952), "R0_ACCEPTED_COUNTS_CONFLICT")
    return manifest.model_dump(mode="json")


def build_artifacts(root=phase2.ROOT):
    contracts = FrozenRegimeContracts(root)
    schema = manifest_schema()
    schema["properties"]["primary_detector_set_id"]["const"] = contracts.detectors["stack_id"]
    schema["properties"]["primary_detector_manifest_sha"]["const"] = PHASE2_SHA
    schema["properties"]["prediction_schema_sha"]["const"] = PREDICTION_SHA
    artifacts = {MANIFEST_SCHEMA: schema, SAMPLE_SCHEMA: sample_schema(), **synthetic_fixtures(contracts), R0: accepted_r0(contracts)}
    artifacts[CONTRACT] = dict(contract_version="regime_contract_v1", manifest_version="regime_manifest_v1", sample_version="regime_sample_v1",
        detector_manifest_sha256=PHASE2_SHA, prediction_schema_sha256=PREDICTION_SHA, adapter_manifest_sha256=ADAPTER_SHA,
        primary_target_aliases=list(contracts.targets), threat_regimes=list(get_args(ThreatRegime)), partitions=list(get_args(Partition)),
        schema_paths={"manifest": MANIFEST_SCHEMA, "sample": SAMPLE_SCHEMA}, real_r0_path=R0,
        synthetic_fixture_paths=[p for p in artifacts if p.startswith(FIXTURES) and p != PARENTS],
        serialization="UTF-8 sorted keys, compact separators, ensure_ascii=true, allow_nan=false, explicit nulls; no newline for canonical hash; stored JSON is indented with one LF",
        hashing="manifest_hash is SHA-256 of canonical manifest excluding only manifest_hash; file SHA is separately recorded",
        experiment_identity="EXP-Rn-<full SHA256>; all manifest content except experiment_id/manifest_hash/created_at/status/notes and sample created_at; includes membership, lineage, method revisions and bound protocol/stack",
        ordering="samples sorted by sample_id; dataset sources by (dataset_id,dataset_revision); evidence by role; external parents by sample_id",
        lineage="Immediate parent; stable shared lineage; acyclic parent graph; external parents require metadata and a hash-bound evidence role; N1 groups are not semantic independence claims",
        success="Versioned definition reference only; fixture definition does not authorize real attack evaluation; completed outcomes require valid_attempt and success booleans",
        join="sample_id + primary detector_id; unique pairs; compatible truth labels; full coverage by default; non-OK predictions remain failures",
        validation="Use FrozenRegimeContracts.validate_manifest for cryptographic input binding; Python additionally checks graph, counts, timestamps, self-hash and experiment identity beyond JSON Schema",
        frozen_mutation="Immutable nested models/tuples; frozen manifest assignment and model_copy(update=...) rejected; a changed identity requires a newly validated revision",
        scope={"metadata_only": True, "model_execution": False, "dataset_acquisition": False, "metrics": False,
               "operational_thresholds": False, "R1_R2_R3_execution": False, "Cycle_2": False, "Phase_5": False})
    return artifacts


def expected_hashes(root, artifacts):
    return {"artifact_version": "phase4_artifact_hashes_v1", "sha256": {
        **{p: hashlib.sha256(phase2.manifest_bytes(value)).hexdigest() for p, value in artifacts.items()},
        **{p: phase2.sha(Path(root) / p) for p in CODE}}}


def check(root=phase2.ROOT):
    artifacts = build_artifacts(root)
    hashes = expected_hashes(root, artifacts)
    require(phase2.read_json(Path(root) / HASHES) == hashes, "PHASE4_HASH_INVENTORY_DRIFT")
    for path, value in artifacts.items():
        require((Path(root) / path).read_bytes() == phase2.manifest_bytes(value), "PHASE4_DETERMINISTIC_ARTIFACT_DRIFT")
    return {"status": "PASS", "artifact_hash_checks": len(hashes["sha256"]), "schema_hashes": {p: hashes["sha256"][p]
        for p in (MANIFEST_SCHEMA, SAMPLE_SCHEMA, CONTRACT)}, "hash_inventory_sha256": phase2.sha(Path(root) / HASHES),
        "r0_counts": {k: artifacts[R0][k] for k in ("sample_count", "attack_count", "benign_count")},
        "prior_contracts_unchanged": True}


def freeze(root=phase2.ROOT):
    artifacts = build_artifacts(root)
    artifacts[HASHES] = expected_hashes(root, artifacts)
    # Preflight every path before publishing any file; never overwrite frozen evidence.
    for name, value in artifacts.items():
        path = Path(root) / name
        require(not path.exists() or path.read_bytes() == phase2.manifest_bytes(value), "REFUSE_DIFFERENT_FROZEN_BYTES")
    for name, value in artifacts.items():
        path = Path(root) / name
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("xb") as stream:
                stream.write(phase2.manifest_bytes(value))
    return check(root)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("freeze", "check"), default="check")
    args = parser.parse_args()
    print(json.dumps(freeze() if args.mode == "freeze" else check(), indent=2))
