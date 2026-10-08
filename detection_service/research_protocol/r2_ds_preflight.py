"""Bind successful offline tests and preservation checks before generation."""

import json
import subprocess
import sys
import xml.etree.ElementTree as ET

from detection_service.research_protocol import r2_ds_predeclare as p,protocol_patch_001 as patch
from detection_service.research_protocol.release_validation import check_acceptance


def run():
    path=p.ROOT/'tmp/r2_ds_preflight.xml'
    cases=list(ET.parse(path).getroot().iter('testcase'))
    p.require(len(cases)==84 and not any(c.find(tag) is not None for c in cases for tag in ('failure','error','skipped')),'PREFLIGHT_TEST_FAILURE')
    baseline=json.loads(subprocess.check_output([sys.executable,'-B','-m','detection_service.scripts.verify_quality_preservation','--mode','check'],cwd=p.ROOT))
    p.require(baseline['status']=='PASS' and baseline['hash_checks']==96,'BASELINE_FAILURE')
    p.publish(p.OUT/'r2_ds_preflight_acceptance_v1.json',dict(status='PASS',tests=dict(passed=len(cases),failed=0,skipped=0,
        receipt_path=path.relative_to(p.ROOT).as_posix(),receipt_sha256=p.files.sha(path)),
        baseline_preservation=baseline,release_preservation=check_acceptance(),
        source_preservation_checks=p.preserved(),patch_hash_checks=len(patch.verify_patch()['sha256']),
        authoritative_model_queries=0,implementation_sha256={path.name:p.files.sha(path) for path in (p.ROOT/'detection_service/research_protocol').glob('r2_ds*.py') if path.name!='r2_ds_preflight.py'}))


if __name__=='__main__':
    run()
