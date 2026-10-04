"""QUALITY-001 metadata-only checks; no dataset text or model execution."""

import copy
import csv
import hashlib
import json
from pathlib import Path

import jsonschema
import pytest

from detection_service.quality.development_fixture import (
    COLUMNS, POLICY_PATHS, ROOT, FixtureError, check_rows, file_hash, fold_bytes,
    fold_statistics, freeze, generate_folds, load_manifest, verify,
)
from detection_service.quality.policy import (
    ARTIFACT_DIR, BASELINE_VERSIONS, CANDIDATE_VERSIONS, FOLD_PATH, MANIFEST_PATH,
    MANIFEST_SHA256, N_FOLDS, PARTITIONS, SEED, THREAT_REGIMES,
)


@pytest.fixture(scope="module")
def metadata():
    return load_manifest()


@pytest.fixture(scope="module")
def rows():
    with (ROOT / FOLD_PATH).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


@pytest.fixture(scope="module")
def config():
    return json.loads((ROOT / ARTIFACT_DIR / "quality_fixture_v1.json").read_text(encoding="utf-8"))


@pytest.fixture
def frozen_copy(tmp_path):
    destination = ROOT / ARTIFACT_DIR
    integrity = json.loads((destination / "integrity_manifest_v1.json").read_text(encoding="utf-8"))
    paths = [*integrity["sha256"], ARTIFACT_DIR + "/integrity_manifest_v1.json"]
    for path in paths:
        target = tmp_path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / path).read_bytes())
    return tmp_path


def test_manifest_sha256():
    assert file_hash(ROOT / MANIFEST_PATH) == MANIFEST_SHA256


def test_manifest_hash_drift_stops_before_parsing(tmp_path):
    path = tmp_path / "metadata.csv"
    path.write_bytes(b"not the authoritative manifest")
    with pytest.raises(FixtureError, match="SHA-256"):
        load_manifest(path)


def test_authoritative_counts(metadata):
    base, counts = metadata
    assert counts == {"TOTAL": 1601, "BASE_TRAIN": 1135, "CALIBRATION": 233, "VALIDATION": 233}
    assert len(base) == 1135
    assert sum(r["canonical_label"] == "1" for r in base) == 183
    assert sum(r["canonical_label"] == "0" for r in base) == 952


def test_only_base_metadata_projection(metadata):
    base, _ = metadata
    expected = {"record_id", "partition", "data_role", "canonical_label", "source_dataset", "source_dataset_id",
                "lineage_group_id", "normalized_hash"}
    assert all(set(r) == expected and r["partition"] == "BASE_TRAIN" for r in base)


def test_five_folds_base_only(rows):
    assert {r["outer_fold"] for r in rows} == {"0", "1", "2", "3", "4"}
    assert {r["partition"] for r in rows} == {"BASE_TRAIN"}


def test_every_sample_once_and_no_missing(metadata, rows):
    base, _ = metadata
    assert len(rows) == len({r["sample_id"] for r in rows}) == 1135
    assert {r["sample_id"] for r in rows} == {r["record_id"] for r in base}


def test_lineage_groups_never_split(metadata, rows):
    check_rows(rows, metadata[0])
    stats = fold_statistics(rows)
    assert stats["lineage_leakage"] == 0
    assert stats["lineage_groups"] == 1134
    assert sum(f["lineage_groups"] for f in stats["folds"]) == 1134


def test_trainable_in_other_four_folds(rows):
    for row in rows:
        assert sum(str(f) != row["outer_fold"] for f in range(5)) == 4


def test_deterministic_reproduction_not_new_fixture(metadata, rows):
    assert fold_bytes(generate_folds(metadata[0])) == fold_bytes(rows)
    assert fold_bytes(generate_folds(list(reversed(metadata[0])))) == fold_bytes(rows)


@pytest.mark.parametrize("seed", [0, 1702, True, "1701"])
def test_fixed_seed_rejects_variations(metadata, seed):
    with pytest.raises(FixtureError, match="seed"):
        generate_folds(metadata[0], seed=seed)


@pytest.mark.parametrize("folds", [4, 6, True])
def test_exact_fold_count(metadata, folds):
    with pytest.raises(FixtureError, match="five folds"):
        generate_folds(metadata[0], n_folds=folds)


@pytest.mark.parametrize("mutation,reason", [
    ("missing", "missing or extra"), ("extra", "missing or extra"), ("duplicate", "duplicate"),
    ("partition", "non-BASE_TRAIN"), ("label", "label"), ("label_flip", "label"),
    ("lineage", "lineage metadata"), ("source", "source metadata"), ("fold", "fold IDs"),
    ("text", "unexpected columns"), ("order", "deterministic assignment"),
])
def test_fold_drift_rejected(metadata, rows, mutation, reason):
    changed = copy.deepcopy(rows)
    if mutation == "missing":
        changed.pop()
    elif mutation == "extra":
        changed.append({**changed[0], "sample_id": "unknown"})
    elif mutation == "duplicate":
        changed.append(changed[0])
    elif mutation == "partition":
        changed[0]["partition"] = "VALIDATION"
    elif mutation == "label":
        changed[0]["label"] = "2"
    elif mutation == "label_flip":
        changed[0]["label"] = str(1 - int(changed[0]["label"]))
    elif mutation == "lineage":
        changed[0]["lineage_group"] = "LG-N1-" + "0" * 24
    elif mutation == "source":
        changed[0]["source_name"] = "protected source"
    elif mutation == "fold":
        changed[0]["outer_fold"] = "5"
    elif mutation == "text":
        changed[0]["prompt"] = "synthetic forbidden column"
    elif mutation == "order":
        changed.reverse()
    with pytest.raises(FixtureError, match=reason):
        check_rows(changed, metadata[0])


def test_real_duplicate_lineage_split_is_rejected(metadata, rows):
    changed = copy.deepcopy(rows)
    for row in changed:
        matches = [r for r in changed if r["lineage_group"] == row["lineage_group"]]
        if len(matches) > 1:
            matches[0]["outer_fold"] = str((int(matches[0]["outer_fold"]) + 1) % 5)
            break
    else:
        pytest.fail("expected actual duplicate group")
    with pytest.raises(FixtureError, match="split across folds"):
        check_rows(changed, metadata[0])


@pytest.mark.parametrize("mutation,reason", [
    ("missing_lineage", "lineage grouping"), ("bad_hash", "normalized hash"),
    ("label", "invalid label"), ("source", "source"), ("duplicate", "duplicate sample"),
    ("partition", "non-BASE_TRAIN"), ("prefix_collision", "prefix collision"),
])
def test_ambiguous_metadata_stops(metadata, mutation, reason):
    base = copy.deepcopy(metadata[0])
    if mutation == "missing_lineage":
        base[0]["lineage_group_id"] = ""
    elif mutation == "bad_hash":
        base[0]["normalized_hash"] = "invalid"
    elif mutation == "label":
        base[0]["canonical_label"] = "UNKNOWN"
    elif mutation == "source":
        base[0]["source_dataset_id"] = "DS-TXT-009"
    elif mutation == "duplicate":
        base.append(base[0])
    elif mutation == "partition":
        base[0]["partition"] = "CALIBRATION"
    elif mutation == "prefix_collision":
        base[1]["normalized_hash"] = base[0]["normalized_hash"][:24] + "f" * 40
        base[1]["lineage_group_id"] = base[0]["lineage_group_id"]
    with pytest.raises(FixtureError, match=reason):
        generate_folds(base)


def test_fewer_than_five_groups_stops(metadata):
    with pytest.raises(FixtureError, match="fewer than five"):
        generate_folds(metadata[0][:4])


def test_fold_hash_stability(rows, config):
    assert hashlib.sha256(fold_bytes(rows)).hexdigest() == config["fold_artifact_sha256"]
    assert (ROOT / FOLD_PATH).read_bytes() == fold_bytes(rows)


def test_complete_frozen_integrity_check():
    assert verify()["status"] == "PASS"


def test_frozen_copy_verifies_without_data_or_models(frozen_copy):
    assert verify(frozen_copy)["status"] == "PASS"


@pytest.mark.parametrize("path", ["development_folds_v1.csv", "quality_fixture_v1.json", "fold_statistics_v1.json",
                                  "oof_result_schema_v1.json", "error_analysis_schema_v1.json", "integrity_manifest_v1.json"])
def test_hash_drift_fails_loudly(frozen_copy, path):
    target = frozen_copy / ARTIFACT_DIR / path
    target.write_bytes(target.read_bytes() + b" ")
    with pytest.raises(FixtureError, match="hash drift|anchor mismatch"):
        verify(frozen_copy)


def test_existing_fixture_cannot_be_overwritten():
    with pytest.raises(FixtureError, match="refuses overwrite"):
        freeze()


def test_config_schema_and_exact_policy(config):
    schema = json.loads((ROOT / ARTIFACT_DIR / "quality_fixture_schema_v1.json").read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator.check_schema(schema)
    jsonschema.validate(config, schema)
    assert config["seed"] == SEED == 1701
    assert config["n_folds"] == N_FOLDS == 5
    assert config["fpr_budgets"] == [0.01, 0.03, 0.05]
    assert config["max_improvement_cycles"] == 2
    for key, value in (("seed", 3), ("fpr_budgets", [0.02]), ("max_improvement_cycles", 3), ("partition_not_threat_regime", False)):
        changed = copy.deepcopy(config)
        changed[key] = value
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(changed, schema)


def test_partition_and_threat_regime_are_orthogonal(config):
    assert set(PARTITIONS).isdisjoint(THREAT_REGIMES)
    assert set(THREAT_REGIMES) == {"R0", "R1", "R2", "R3"}
    assert config["partition_not_threat_regime"] is True
    assert len(config["allowed_later_combinations"]) == 8
    assert {r[0] for r in config["allowed_later_combinations"]} == {"INTERNAL_TEST", "FINAL_TEST"}
    assert all(r[1] in THREAT_REGIMES for r in config["allowed_later_combinations"])


def test_baseline_and_candidate_generations(config):
    assert config["baseline_versions"] == BASELINE_VERSIONS
    assert config["candidate_versions"] == CANDIDATE_VERSIONS
    assert set(BASELINE_VERSIONS.values()).isdisjoint(CANDIDATE_VERSIONS.values())
    assert set(config["generation_definitions"]) == {"research_stack_v1", "research_stack_v2"}


def test_no_execution_authorized(config):
    assert all(value is False for value in config["phase_execution"].values())
    assert config["verifier_router_boundary"]["implementation_authorized"] is False
    assert config["dm_b_promotion_policy"]["single_point_estimate_sufficient"] is False
    assert config["ds_promotion_policy"]["standalone_FNR_sufficient"] is False
    assert len(config["ds_promotion_policy"]["prohibited_features"]) == 5


def test_source_label_balance_and_stats(rows):
    stats = fold_statistics(rows)
    assert sum(f["rows"] for f in stats["folds"]) == 1135
    assert sum(f["positive"] for f in stats["folds"]) == 183
    assert sum(f["negative"] for f in stats["folds"]) == 952
    assert max(f["positive"] for f in stats["folds"]) - min(f["positive"] for f in stats["folds"]) <= 1
    assert max(f["negative"] for f in stats["folds"]) - min(f["negative"] for f in stats["folds"]) <= 1
    assert all(sum(s["rows"] for s in f["sources"].values()) == f["rows"] for f in stats["folds"])


def sample_oof():
    return {"sample_id": "synthetic-id", "fold": 0, "label": 1, "source_name": "synthetic-source",
            "lineage_group": "LG-N1-" + "a" * 24, "detector_id": "synthetic", "detector_version": "synthetic_v1",
            "candidate_id": "synthetic_recipe", "raw_score": 0.8, "calibrated_probability": None,
            "binary_prediction": 1, "input_tokens": None, "tokens_analyzed": None, "truncated": None,
            "latency_ms": 0.1, "error_type": "TP", "metadata": {"partition": "BASE_TRAIN"}}


def read_schema(name):
    schema = json.loads((ROOT / ARTIFACT_DIR / name).read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator.check_schema(schema)
    return schema


@pytest.mark.parametrize("label,prediction,error", [(1, 1, "TP"), (0, 0, "TN"), (0, 1, "FP"), (1, 0, "FN")])
def test_oof_schema_synthetic_records(label, prediction, error):
    row = {**sample_oof(), "label": label, "binary_prediction": prediction, "error_type": error}
    jsonschema.validate(row, read_schema("oof_result_schema_v1.json"))


@pytest.mark.parametrize("field,value", [("fold", 5), ("label", 2), ("calibrated_probability", 1.1),
                                        ("binary_prediction", 2), ("latency_ms", -1), ("input_tokens", -1),
                                        ("error_type", "FN"), ("prompt", "synthetic text")])
def test_invalid_oof_records_rejected(field, value):
    row = {**sample_oof(), field: value}
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(row, read_schema("oof_result_schema_v1.json"))


def test_error_analysis_schema_synthetic_only():
    oof = sample_oof()
    record = {k: oof[k] for k in ("sample_id", "fold", "label", "source_name", "lineage_group", "detector_id",
                                  "detector_version", "candidate_id", "error_type", "metadata")}
    record["statistical"] = {"whole_prompt_ppl": 5.0, "mean_surprisal": None,
                             "surprisal_quantiles": {"q50": 0.5}, "feature_family_tags": ["token_distribution"]}
    record["semantic"] = {"input_tokens": 20, "tokens_analyzed": 20, "truncated": False,
                          "attack_family": None, "attack_payload_position_token": None}
    schema = read_schema("error_analysis_schema_v1.json")
    jsonschema.validate(record, schema)
    record["semantic"]["raw_text"] = "synthetic forbidden field"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(record, schema)


def test_raw_text_absent_from_fold_artifact(rows):
    assert set(COLUMNS) == {"sample_id", "partition", "label", "lineage_group", "source_name", "outer_fold"}
    assert all(set(r) == set(COLUMNS) for r in rows)


def test_lineage_evidence_and_scope(config):
    assert config["lineage"]["field"] == "lineage_group_id"
    assert {e["path"] for e in config["lineage"]["evidence"]} == set(POLICY_PATHS)
    assert "not full documentary/semantic lineage" in config["lineage"]["scope"]
    assert "not a population guarantee" in config["comparison_policy"]["finite_sample_limit"]
