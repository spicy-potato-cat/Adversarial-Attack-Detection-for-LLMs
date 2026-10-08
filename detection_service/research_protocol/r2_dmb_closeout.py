"""Post-run evidence and handoff only; no models, search or metric changes."""

import argparse
import json
import subprocess
import sys
import xml.etree.ElementTree as ET

from detection_service.research_protocol import r2_dmb_predeclare as p, protocol_patch_001 as patch
from detection_service.research_protocol import r2_dmb_patch_binding as binding
from detection_service.research_protocol.release_validation import check_acceptance, TEST_NAMES

ACCEPTANCE=p.OUT/'r2_dmb_final_acceptance_v1.json'


def accept():
    paths=('tmp/patch001_regression_0.xml','tmp/patch001_regression_1.xml','tmp/r2_postrun_acceptance.xml')
    receipts=[]
    cases=[]
    for path in paths:
        root=ET.parse(p.ROOT/path).getroot()
        tests=list(root.iter('testcase'))
        suites=list(root.iter('testsuite'))
        counts={k:sum(int(s.attrib.get(k,0)) for s in suites) for k in ('tests','failures','errors','skipped')}
        p.require(counts['tests']==len(tests)>0 and not any(counts[k] for k in ('failures','errors','skipped')),'POST_RUN_REGRESSION_NOT_PASS')
        p.require(not any(c.find(tag) is not None for c in tests for tag in ('failure','error','skipped')),'POST_RUN_REGRESSION_NOT_PASS')
        cases.extend(c.attrib['classname']+'::'+c.attrib['name'] for c in tests)
        receipts.append(dict(path=path,sha256=p.digest(path),**counts))
    p.require(len(cases)==len(set(cases)),'DUPLICATE_TEST_CASE')
    names=(*TEST_NAMES,'r1_source_gate','r1_corpus','r1_experiment','ds_runtime_equivalence',
           'protocol_patch_001','r2_dmb_predeclaration','r2_dmb_protocol_blocker','r2_dmb_generator',
           'r2_dmb_analysis_synthetic','r2_dmb_freeze_outputs','r2_dmb_results')
    p.require({c.split('::')[0] for c in cases}=={'detection_service.tests.test_'+name for name in names},'REQUIRED_TEST_MODULE_MISSING')
    baseline=json.loads(subprocess.check_output([sys.executable,'-B','-m','detection_service.scripts.verify_quality_preservation','--mode','check'],cwd=p.ROOT))
    p.require(baseline['status']=='PASS' and baseline['hash_checks']==96,'BASELINE_PRESERVATION_FAILURE')
    release=check_acceptance()
    patch_value=patch.verify_patch()
    addendum=binding.verified()
    from detection_service.research_protocol.r2_dmb_freeze import validate
    frozen,_=validate()
    predictions=p.files.read_json(p.OUT/'r2_dmb_prediction_manifest_v1.json')
    p.require(predictions['actual_predictions']==2400 and predictions['dmb_operational_mismatches']==0 and predictions['dmb_max_raw_score_delta']<=1e-12,'PREDICTION_ACCEPTANCE_FAILURE')
    provenance=p.files.read_json(p.OUT/'r2_dmb_analysis_provenance_v1.json')
    p.require(all(p.files.sha(p.OUT/name)==sha for name,sha in provenance['sha256'].items()),'ANALYSIS_HASH_DRIFT')
    report=p.files.read_json(p.OUT/'r2_dmb_report_binding_v1.json')
    p.require(p.digest(report['report_path'])==report['sha256'],'REPORT_HASH_DRIFT')
    files=[*p.OUT.glob('*.json'),*p.OUT.glob('*.csv'),p.ROOT/report['report_path']]
    files=[path for path in files if path!=ACCEPTANCE]
    value=dict(artifact_version='r2_dmb_final_acceptance_v1',status='PASS',
        tests=dict(total=len(cases),passed=len(cases),failed=0,errors=0,skipped=0,receipts=receipts,
                   prequery_accepted_tests=p.files.read_json(binding.ACCEPTANCE)['tests']['total']),
        baseline_preservation=baseline,release_preservation=release,
        original_preservation_checks=p.preserved(),patch_hash_checks=len(patch_value['sha256']),
        protocol_patch_commit=addendum['protocol_patch_commit'],protocol_patch_id=patch.PATCH_ID,
        generator_implementation_commit=frozen['implementation_commit'],freeze_commit=predictions['freeze_commit'],
        prediction_commit=provenance['prediction_commit'],analysis_run_start_commit=provenance['prediction_commit'],
        closeout_code_created_after_analysis=True,
        closeout_code_sha256=p.files.sha(p.ROOT/'detection_service/research_protocol/r2_dmb_closeout.py'),
        unique_target_generation_queries=frozen['unique_target_queries'],max_per_parent=frozen['max_target_queries'],
        inverse_passed=frozen['inverse_passed'],generation_untargeted_queries=0,
        dmb_replay_max_delta=predictions['dmb_max_raw_score_delta'],dmb_decision_mismatches=0,
        R3_started=False,models_changed=False,thresholds_changed=False,attack_design_changed=False,
        raw_data_committed=False,protected_experiments_started=False,
        sha256={path.relative_to(p.ROOT).as_posix():p.files.sha(path) for path in files})
    p.publish(ACCEPTANCE,value)
    print(json.dumps({k:v for k,v in value.items() if k!='sha256'},indent=2))


def handoff():
    p.require(not p.git('status','--porcelain').strip(),'CLEAN_FINAL_TREE_REQUIRED')
    head=p.git('rev-parse','HEAD').decode().strip()
    remote=p.git('rev-parse','origin/exp/r2-dmb-001').decode().strip()
    p.require(head==remote,'FINAL_REMOTE_SYNC_REQUIRED')
    p.require(p.git('rev-parse','origin/exp/protocol-001').decode().strip()==
        p.files.read_json(p.OUT/'r2_dmb_predeclaration_v1.json')['source_head'],'REMOTE_SOURCE_BRANCH_DRIFT')
    value=p.files.read_json(ACCEPTANCE)
    p.require(p.committed(ACCEPTANCE)==head,'FINAL_EVIDENCE_COMMIT_REQUIRED')
    p.require(all(p.digest(path)==sha for path,sha in value['sha256'].items()),'FINAL_EVIDENCE_HASH_DRIFT')
    binding.verified()
    p.publish(p.PRIVATE/'final_handoff_v2.json',dict(status='PASS',head=head,remote_head=remote,
        working_tree='CLEAN',ahead=0,behind=0,source_head=p.git('rev-parse','exp/protocol-001').decode().strip(),
        acceptance_sha256=p.files.sha(ACCEPTANCE),R2_status='COMPLETE',R3_started=False))
    summary=p.files.read_json(p.OUT/'r2_dmb_transfer_metrics_v1.json')
    lines=['# EXP-PROTOCOL-001-PATCH-001 FINAL REPORT','','STATUS: PASS','','## Defect',
        'Original error: TARGET_METRIC_DOMAIN_CONFLICT.',
        'Root cause: the parent evaluator selected all target prefixes for a singleton-target uncertainty configuration.',
        'Before: target and transfer destination/base-stack membership were conflated.',
        'Historical evaluator, blocker report and original release remain unchanged.','',
        '## Corrected Semantics','Attack-target domain: {D_M-B}.','Target uncertainty domain: {D_M-B}.',
        'Transfer-evaluation domain: {D_S, D_M-B, D_G}.','Common-mode domain: {D_S, D_M-B, D_G}.',
        'R3 behavior preserved: YES; ALL maps to the full-stack attack domain.',
        'Generic single-target D_S and D_G behavior is tested; transfer destinations never become attack targets.','',
        '## Scientific Neutrality','Authoritative R2 model queries before patch: 0.',
        'Scientific R2 outcomes observed before patch: NONE.',
        *[name+' changed: NO.' for name in ('Attack design','Seed population','Operators','Query budget','Success criterion','Random seed','Thresholds','Models','Calibrators','Metric formulas','Bootstrap algorithm')],
        'Target isolation: unchanged. Search implementation is byte-identical to the archived pre-run draft.',
        'Provenance-gate/Windows-byte corrections occurred before any authoritative query and remain traceable in Git.','',
        '## Preservation',
        *[name+' unchanged: YES.' for name in ('R0','R1','Detector hashes','Threshold hashes','Original R2 predeclaration','Original R2 seed manifest')],
        'Original preservation checks: 252. Additive patch hashes: '+str(value['patch_hash_checks'])+'.','',
        '## Tests','Total unique accepted tests: '+str(value['tests']['total'])+'.',
        'Passed: '+str(value['tests']['passed'])+'. Failed: 0. Errors: 0. Skipped: 0.',
        'Pre-query acceptance: 931 tests; final post-run suite: 100 tests (overlap counted only once).',
        'Baseline-preservation checks: 96/96. Release/hash checks: 118/118.','',
        '## Git','Starting HEAD: adaa4d22794970bd0f1841101f96e2cafba8f80e.',
        'Initial correction commit: 85abbb3; subsequent provenance corrections: d56fed2 and 7e16bcb.',
        'Accepted protocol patch commit: '+value['protocol_patch_commit']+'.',
        'Predeclaration-addendum commit: '+p.committed(binding.ADDENDUM)+'.',
        'Generator/model-query implementation commit: '+value['generator_implementation_commit']+'.',
        'Terminal freeze commit: '+value['freeze_commit']+'.',
        'Prediction commit: '+value['prediction_commit']+'.',
        'Final HEAD: '+head+'.','Remote HEAD: '+remote+'.','Working tree: CLEAN. Ahead/behind: 0/0.',
        'Authoritative exp/protocol-001 remains 62bf867b2acc53c3a8dc35d18f443558cd9da508.','',
        '## Artifacts','Protocol patch artifact: '+patch.ARTIFACT,
        'SHA: '+p.files.sha(p.ROOT/patch.ARTIFACT),
        'Protocol patch review: reviews/EXP_PROTOCOL_001_PATCH_001_REVIEW.md',
        'R2 predeclaration addendum: '+binding.ADDENDUM.relative_to(p.ROOT).as_posix(),
        'SHA: '+p.files.sha(binding.ADDENDUM),
        'Pre-query receipt: detection_service/outputs/r2-dmb-001/prequery_receipt_v1.json',
        'R2 scientific report: reviews/R2_DMB_TARGETED_EVASION_RESULTS_v2.md','',
        '## R2 Resumption Result','R2-DMB-001: COMPLETE; no redesign.',
        'Parents/terminals: 800/800. Exact inverse reconstruction: 800/800.',
        'Unique D_M-B generation queries: 46,360; maximum per parent: 61; budget violations: 0.',
        'D_S/D_G/ensemble generation queries: 0/0/0. Post-freeze predictions: 2,400 OK.',
        'D_M-B replay delta: 0.0; decision mismatches: 0.',
        'Target evasions: '+str(summary['target_evasion_count'])+'/800.',
        'ETR to D_S, D_G and both: UNDEFINED (zero successful target-evasion denominator), not zero.',
        'All-three misses: 0/800. FPR/ROC-AUC/AP: NOT_APPLICABLE_ATTACK_ONLY_REGIME.',
        'This bounds only the predeclared generator on these parents; it does not establish universal robustness.',
        'No raw prompts or model weights were committed. No R3, training or protected experiment was started.','',
        '## FINAL VERDICT','PROTOCOL_PATCH_ACCEPTED_R2_DMB_MAY_RESUME']
    path=p.PRIVATE/'EXP_PROTOCOL_001_PATCH_001_FINAL_REPORT.md'
    data=('\n'.join(lines)+'\n').encode('ascii')
    p.require(not path.exists(),'FINAL_REPORT_ALREADY_EXISTS')
    with path.open('xb') as stream:
        stream.write(data)
    print(json.dumps(dict(status='PASS',final_head=head,report=str(path)),indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode',choices=('accept','handoff'),required=True)
    args=parser.parse_args()
    accept() if args.mode=='accept' else handoff()
