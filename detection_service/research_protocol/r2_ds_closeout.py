"""Final evidence acceptance, without model queries or search changes."""

import json
import subprocess
import sys
import xml.etree.ElementTree as ET

from detection_service.research_protocol import r2_ds_predeclare as p,r2_ds_binding as binding,protocol_patch_001 as patch
from detection_service.research_protocol.release_validation import check_acceptance


def accept():
    receipts=[]
    cases=[]
    for name in ('r2_ds_postrun.xml','r2_ds_preserved_regression.xml'):
        path=p.ROOT/'tmp'/name
        root=ET.parse(path).getroot()
        tests=list(root.iter('testcase'))
        p.require(tests and not any(c.find(tag) is not None for c in tests for tag in ('failure','error','skipped')),'POSTRUN_TEST_FAILURE')
        cases.extend(c.attrib['classname']+'::'+c.attrib['name'] for c in tests)
        receipts.append(dict(path=path.relative_to(p.ROOT).as_posix(),sha256=p.files.sha(path),passed=len(tests)))
    p.require(len(cases)==len(set(cases)),'DUPLICATE_TEST_CASE')
    expected={'r2_ds_predeclaration','r2_ds_generator','r2_ds_analysis_synthetic','r2_ds_freeze_outputs','r2_ds_results',
        'protocol_patch_001','ds_runtime_equivalence','r2_dmb_predeclaration','r2_dmb_protocol_blocker',
        'r2_dmb_generator','r2_dmb_analysis_synthetic','r2_dmb_freeze_outputs','r2_dmb_results'}
    p.require({c.split('::')[0] for c in cases}=={'detection_service.tests.test_'+name for name in expected},'POSTRUN_MODULE_COVERAGE_FAILURE')
    baseline=json.loads(subprocess.check_output([sys.executable,'-B','-m','detection_service.scripts.verify_quality_preservation','--mode','check'],cwd=p.ROOT))
    p.require(baseline['status']=='PASS' and baseline['hash_checks']==96,'BASELINE_FAILURE')
    binding.verified()
    from detection_service.research_protocol.r2_ds_freeze import validate
    frozen,_=validate()
    predictions=p.files.read_json(p.OUT/'r2_ds_prediction_manifest_v1.json')
    p.require(predictions['actual_predictions']==3*p.count() and predictions['ds_operational_mismatches']==0 and predictions['ds_max_calibrated_score_delta']<=1e-12,'REPLAY_FAILURE')
    provenance=p.files.read_json(p.OUT/'r2_ds_analysis_provenance_v1.json')
    p.require(all(p.files.sha(p.OUT/name)==value for name,value in provenance['sha256'].items()),'ANALYSIS_HASH_FAILURE')
    report=p.files.read_json(p.OUT/'r2_ds_report_binding_v1.json')
    p.require(p.digest(report['report_path'])==report['sha256'],'REPORT_HASH_FAILURE')
    destination=p.OUT/'r2_ds_final_acceptance_v1.json'
    paths=[*p.OUT.glob('*.json'),*p.OUT.glob('*.csv'),p.ROOT/report['report_path']]
    paths=[path for path in paths if path!=destination]
    value=dict(status='PASS',artifact_version='r2_ds_final_acceptance_v1',
        tests=dict(passed=len(cases),failed=0,errors=0,skipped=0,receipts=receipts),
        baseline_preservation=baseline,release_preservation=check_acceptance(),
        source_preservation_checks=p.preserved(),patch_hash_checks=len(patch.verify_patch()['sha256']),
        generator_commit=frozen['implementation_commit'],freeze_commit=predictions['freeze_commit'],
        prediction_commit=provenance['prediction_commit'],generation_queries=frozen['unique_target_queries'],
        inverse_passed=frozen['inverse_passed'],untargeted_generation_queries=0,
        ds_replay_delta=predictions['ds_max_calibrated_score_delta'],ds_decision_mismatches=0,
        verdict=report['verdict'],R3_started=False,R2_DG_started=False,models_changed=False,thresholds_changed=False,
        raw_data_committed=False,sha256={path.relative_to(p.ROOT).as_posix():p.files.sha(path) for path in paths})
    p.publish(destination,value)
    print(json.dumps({k:v for k,v in value.items() if k!='sha256'},indent=2))


if __name__=='__main__':
    accept()
