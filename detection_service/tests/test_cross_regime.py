"""Six synthetic regime bundles; descriptive differences never imply pairing."""

from pydantic import ValidationError
import pytest

from detection_service.research_protocol.adapters import FrozenDetectorContracts
from detection_service.research_protocol.cross_regime import RegimeResultBundle, compare_bundles, cross_regime_matrix, SLOTS
from detection_service.research_protocol.regime import RegimeContractError, canonical_bytes
from detection_service.research_protocol.uncertainty_contract import regime_fixtures
from detection_service.research_protocol import detector_semantics as files
from detection_service.research_protocol.alignment import POLICY_SHA, align_evaluation
from detection_service.research_protocol.core_metrics_contract import synthetic_core
from detection_service.research_protocol.cross_regime import result_bundle
from detection_service.research_protocol.operating_policy import apply_operating_policy, load_frozen_operating_policy
from detection_service.research_protocol.regime import RegimeManifest
from detection_service.research_protocol.prediction import PredictionRecord
import json
import subprocess
import sys


@pytest.fixture(scope="module")
def bundles():
    return regime_fixtures(FrozenDetectorContracts())


@pytest.mark.parametrize("index,slot",list(enumerate(SLOTS)))
def test_each_regime_result_bundle_valid(bundles,index,slot):
    bundle=bundles[index]
    assert RegimeResultBundle.model_validate_json(bundle.deterministic_bytes())==bundle
    matrix=cross_regime_matrix(bundles)
    assert matrix["regime_status"][slot]=="OBSERVED"


def test_primary_detector_set_binding(bundles):
    payload=bundles[0].model_dump()
    payload["detector_manifest_hash"]="0"*64
    with pytest.raises((RegimeContractError,ValidationError)):
        RegimeResultBundle.model_validate(payload)


@pytest.mark.parametrize("field,value",[("operating_point_manifest_hash","0"*64),("decision_view","OPERATIONAL"),("comparison_view_id","OPERATIONAL_FIXED_V1")])
def test_operational_policy_mismatch_rejected(bundles,field,value):
    payload=bundles[0].model_dump()
    payload[field]=value
    with pytest.raises((RegimeContractError,ValidationError)):
        RegimeResultBundle.model_validate(payload)


def test_comparison_view_mismatch_rejected(bundles):
    other=bundles[1].model_copy(update={"comparison_view_id":"HISTORICAL_DESCRIPTIVE_1PCT_V1"})
    result=compare_bundles(bundles[0],other)
    assert result["status"]=="INCOMPATIBLE" and result["metrics"]=={}
    assert cross_regime_matrix((bundles[0],other),reference_slot="R0")["metrics"]["all_three/jfn"]["R1"]["status"]=="INCOMPATIBLE"


def test_label_semantics_mismatch_rejected(bundles):
    other=bundles[1].model_copy(update={"label_semantics":"OTHER_V1"})
    assert compare_bundles(bundles[0],other)["status"]=="INCOMPATIBLE"


def test_missing_regime_not_zero(bundles):
    matrix=cross_regime_matrix(bundles[:1])
    for slot in SLOTS[1:]:
        assert matrix["regime_status"][slot]=="NOT_RUN"
        cell=matrix["metrics"]["all_three/jfn"][slot]
        assert cell["status"]=="NOT_RUN" and cell["point_estimate"] is None


def test_not_applicable_metric(bundles):
    matrix=cross_regime_matrix(bundles)
    for slot in ("R0","R1","R3"):
        assert matrix["metrics"]["transfer/ds_v2/dm_b_v1/etr"][slot]==dict(status="NOT_APPLICABLE",point_estimate=None,uncertainty=None)


def test_cross_regime_delta(bundles):
    result=compare_bundles(bundles[0],bundles[2])
    assert result["metrics"]["individual/ds_v2/fnr"]["delta_fraction"]==42/102-.5


def test_percentage_point_delta(bundles):
    result=compare_bundles(bundles[0],bundles[2])
    assert result["metrics"]["individual/ds_v2/fnr"]["delta_percentage_points"]==100*(42/102-.5)


def test_r2_etr_matrix_placement(bundles):
    matrix=cross_regime_matrix(bundles)
    for slot,target in zip(SLOTS[2:5],("ds_v2","dm_b_v1","dg_v1")):
        assert matrix["metrics"][f"target/{target}/evasion"][slot]["point_estimate"]==.4
    assert matrix["metrics"]["transfer/ds_v2/dm_b_v1/etr"]["R2-D_S"]["point_estimate"]==.25
    assert matrix["metrics"]["transfer/ds_v2/dm_b_v1/etr"]["R2-D_G"]["status"]=="NOT_APPLICABLE"


def test_r3_has_no_r2_etr(bundles):
    assert bundles[-1].core_metrics.evasion_transfer is None


def test_unpaired_regimes_not_marked_paired(bundles):
    assert compare_bundles(bundles[0],bundles[1])["paired"] is False


def test_cross_regime_serialization_deterministic(bundles):
    assert canonical_bytes(cross_regime_matrix(bundles))==canonical_bytes(cross_regime_matrix(tuple(reversed(bundles))))


def test_duplicate_slot_rejected(bundles):
    with pytest.raises(RegimeContractError):
        cross_regime_matrix((bundles[0],bundles[0]))


def test_unobserved_reference_rejected(bundles):
    with pytest.raises(RegimeContractError):
        cross_regime_matrix(bundles[:1],reference_slot="R1")


def test_valid_operational_bundle_and_view_mismatch(bundles):
    contracts=FrozenDetectorContracts()
    fixture=synthetic_core(contracts)
    policy=load_frozen_operating_policy(files.ROOT/"artifacts/research_protocol/operating_point_manifest_v1.json",expected_sha=POLICY_SHA)
    predictions=[apply_operating_policy(PredictionRecord.model_validate_json(json.dumps(p)),policy).model_dump(mode="json") for p in fixture["predictions"]]
    table=align_evaluation(fixture["manifest"],predictions,binding=fixture["prediction_binding"],decision_view="OPERATIONAL",contracts=contracts,operating_policy=policy)
    manifest=RegimeManifest.model_validate_json(json.dumps(fixture["manifest"]))
    bundle=result_bundle(table,manifest,"OPERATIONAL_FIXED_V1")
    assert bundle.operating_point_manifest_hash==POLICY_SHA
    assert compare_bundles(bundle,bundles[1])["status"]=="INCOMPATIBLE"


def test_synthetic_engine_does_not_import_models_or_real_evidence():
    code='''
import sys
def audit(event,args):
    if event=="import" and args[0].split(".")[0] in ("torch","transformers","sklearn","sentence_transformers"):
        raise AssertionError("model import forbidden")
    if event=="open" and isinstance(args[0],(str,bytes)):
        name=str(args[0]).replace(chr(92),"/").lower()
        if "/dataset/raw/" in name or "normalized_records" in name or "r0_regime_manifest" in name or "predictions.csv" in name:
            raise AssertionError("real prompt/prediction access forbidden")
sys.addaudithook(audit)
from detection_service.research_protocol.adapters import FrozenDetectorContracts,DetectorAdapter
def forbidden(*a,**k): raise AssertionError("model execution forbidden")
DetectorAdapter.predict=forbidden
DetectorAdapter._load_live=forbidden
from detection_service.research_protocol.uncertainty_contract import fixtures
from detection_service.research_protocol.core_metrics_contract import align_fixture
from detection_service.research_protocol.uncertainty import BootstrapConfig,bootstrap_metrics
c=FrozenDetectorContracts()
t=align_fixture(fixtures(c)["sample"],c)
bootstrap_metrics(t,["all_three/jfn"],BootstrapConfig(unit="SAMPLE_PAIRED",domain="ATTACK_ONLY",replicates=2))
print("PASS")
'''
    result=subprocess.run([sys.executable,"-c",code],capture_output=True,text=True)
    assert result.returncode==0,result.stderr
