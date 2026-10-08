"""Accept fresh, unique regression receipts before any R2 model query."""

import json
import subprocess
import sys
import xml.etree.ElementTree as ET

from detection_service.research_protocol import protocol_patch_001 as patch
from detection_service.research_protocol import r2_dmb_predeclare as p
from detection_service.research_protocol.release_validation import check_acceptance

RECEIPTS = ('tmp/patch001_regression_0.xml','tmp/patch001_regression_1.xml',
            'tmp/patch001_domains.xml','tmp/r2_resume_implementation.xml')


def accept():
    cases=[]
    receipts=[]
    for path in RECEIPTS:
        root=ET.parse(p.ROOT/path).getroot()
        suites=list(root.iter('testsuite'))
        tests=list(root.iter('testcase'))
        counts={k:sum(int(s.attrib.get(k,0)) for s in suites) for k in ('tests','failures','errors','skipped')}
        p.require(counts['tests']==len(tests)>0 and counts['failures']==counts['errors']==counts['skipped']==0,'PATCH_REGRESSION_NOT_PASS')
        p.require(not any(c.find(tag) is not None for c in tests for tag in ('failure','error','skipped')),'PATCH_REGRESSION_NOT_PASS')
        cases.extend(c.attrib['classname']+'::'+c.attrib['name'] for c in tests)
        receipts.append(dict(path=path,sha256=p.digest(path),**counts))
    p.require(len(cases)==len(set(cases)),'DUPLICATE_REGRESSION_TEST')
    p.require(not any((p.PRIVATE/name).exists() for name in ('invocation_v1.json','generation_v1.jsonl')),'PATCH_TIMING_CONFLICT')
    baseline=json.loads(subprocess.check_output([sys.executable,'-B','-m','detection_service.scripts.verify_quality_preservation','--mode','check'],cwd=p.ROOT))
    p.require(baseline['status']=='PASS' and baseline['hash_checks']==96,'PATCH_PRESERVATION_FAILURE')
    release=check_acceptance()
    p.require(release['hash_checks']==118,'PATCH_PRESERVATION_FAILURE')
    frozen=patch.verify_patch(require_committed=False)
    value=dict(artifact_version='exp_protocol_001_patch_001_acceptance',status='PASS',
        verdict='PROTOCOL_PATCH_ACCEPTED_R2_DMB_MAY_RESUME',
        patch_id=patch.PATCH_ID,patch_sha256=p.files.sha(p.ROOT/patch.ARTIFACT),
        tests=dict(total=len(cases),passed=len(cases),failed=0,errors=0,skipped=0,receipts=receipts),
        baseline_preservation=baseline,release_preservation=release,original_preservation_checks=p.preserved(),
        additive_patch_hash_checks=len(frozen['sha256']),
        authoritative_R2_queries_before_patch=0,scientific_R2_outcomes_before_patch='NONE',
        source_branch=p.git('rev-parse','exp/protocol-001').decode().strip(),
        scientific_design_changed=False,models_thresholds_calibrators_changed=False,
        R0_R1_evidence_changed=False,formulas_bootstrap_changed=False,
        generator_sha256=p.files.sha(p.ROOT/'detection_service/research_protocol/r2_dmb_generator.py'),
        generator_archive_identical=True,R3_started=False)
    p.require(value['generator_sha256']=='6a59ba6a1163c85d9ebd964f2c90511d4d76004ee31b77e06223f51612ebd592','ATTACK_DESIGN_DRIFT')
    p.publish(p.ROOT/'artifacts/research_protocol/protocol_patches/exp_protocol_001_patch_001_acceptance_v2.json',value)
    print(json.dumps(value,indent=2))


if __name__=='__main__':
    accept()
