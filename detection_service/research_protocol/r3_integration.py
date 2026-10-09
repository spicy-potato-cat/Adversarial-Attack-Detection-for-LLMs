"""Model-free Phase-1 integration receipt and immutable preservation gate."""
import hashlib
import json
import subprocess
import sys
import xml.etree.ElementTree as ET

from detection_service.research_protocol import r2_ds_predeclare as p
from detection_service.research_protocol import protocol_patch_001, r2_dmb_predeclare
from detection_service.research_protocol.release_validation import check_acceptance
from detection_service.research_protocol.regime import require

PARENT = 'b95c7f26ce4d448f124fefec7302bf7977febcff'
TRACK_B = '6c7173b70a10d1506d92360b421eaceb5e56405e'
OUT = p.ROOT / p.files.OUT / 'r3'
PICKS = ('e37c91d', 'c4d0830', 'b70a3d4', '0cd2d50',
         '463e88a', '3ed1ad4', 'c754839', '6c7173b')


def preservation():
    checks = {}
    checkout_conversions = []
    names = p.git('ls-tree', '-r', '--name-only', PARENT).decode().splitlines()
    prefixes = ('artifacts/', 'detection_service/research_protocol/',
                'detection_service/app/', 'detection_service/configs/', 'reviews/')
    for name in names:
        if name.startswith(prefixes):
            original = p.git('show', PARENT + ':' + name)
            actual = (p.ROOT / name).read_bytes()
            if actual != original:
                require(actual.replace(b'\r\n', b'\n') == original.replace(b'\r\n', b'\n') and
                        not p.git('diff', PARENT, '--', name), 'R3_OLD_BYTE_MUTATION:' + name)
                checkout_conversions.append(name)
            checks[name] = hashlib.sha256(actual).hexdigest()
    require(p.git('rev-parse', 'exp/r2-ds-001').decode().strip() == PARENT,
            'R3_TRACK_A_PARENT_DRIFT')
    require(p.git('rev-parse', 'prep/r3-verifier-001').decode().strip() == TRACK_B,
            'R3_TRACK_B_REFERENCE_DRIFT')
    baseline = json.loads(subprocess.check_output([sys.executable, '-B', '-m',
        'detection_service.scripts.verify_quality_preservation', '--mode', 'check'], cwd=p.ROOT))
    require(baseline['status'] == 'PASS' and baseline['hash_checks'] == 96, 'BASELINE_DRIFT')
    r1 = p.files.read_json(p.R1 / 'r1_gate_d_acceptance_v1.json')['sha256']
    before = p.files.read_json(p.ROOT / 'reviews/evidence/r2_ds_acceptance_context/before_v1.json')['sha256']
    dmb = p.files.read_json(p.ROOT / p.files.OUT / 'r2_dmb/r2_dmb_final_acceptance_v1.json')['sha256']
    for group in (r1, before, dmb):
        require(all(p.digest(name) == value for name, value in group.items()), 'REGIME_EVIDENCE_DRIFT')
    return dict(status='PASS', baseline=baseline, release=check_acceptance(),
        source_hash_checks=p.preserved(), protocol_patch_hash_checks=len(protocol_patch_001.verify_patch()['sha256']),
        r2_dmb_source_hash_checks=r2_dmb_predeclare.preserved(), r2_dmb_evidence_hash_checks=len(dmb),
        r1_evidence_hash_checks=len(r1), r2_ds_historical_hash_checks=len(before),
        old_tracked_files=len(checks), sha256=checks, checkout_only_line_endings=checkout_conversions,
        R0='PASS', R1='PASS', R2_DMB='PASS', R2_DS='PASS')


def freeze():
    require(p.git('branch', '--show-current').decode().strip() == 'exp/r3-001', 'R3_BRANCH_REQUIRED')
    receipt = p.ROOT / 'tmp/r3_integration_synthetic.xml'
    cases = list(ET.parse(receipt).getroot().iter('testcase'))
    require(len(cases) == 29 and not any(c.find(tag) is not None for c in cases
        for tag in ('failure', 'error', 'skipped')), 'INTEGRATION_SYNTHETIC_TEST_FAILURE')
    mapped = []
    commits = p.git('rev-list', '--reverse', PARENT + '..HEAD').decode().splitlines()
    require(len(commits) == len(PICKS), 'ORDERED_INTEGRATION_COMMIT_COUNT')
    for original, integrated in zip(PICKS, commits):
        original = p.git('rev-parse', original).decode().strip()
        a = p.git('diff-tree', '--no-commit-id', '--name-only', '-r', original).decode().splitlines()
        b = p.git('diff-tree', '--no-commit-id', '--name-only', '-r', integrated).decode().splitlines()
        require(a == b and all(p.git('show', original + ':' + name) ==
                              p.git('show', integrated + ':' + name) for name in a), 'CHERRY_PICK_BYTE_DRIFT')
        mapped.append(dict(original=original, integrated=integrated, changed_paths=a))
    value = dict(artifact_version='phase1_integration_baseline_v1', status='PASS',
        track_a_parent=PARENT, track_b_integrated_HEAD=TRACK_B, ordered_cherry_picks=mapped,
        reconciliation_performed=[], preservation=preservation(),
        synthetic_tests=dict(passed=29, failed=0, skipped=0, receipt_sha256=p.files.sha(receipt)),
        R3_authoritative_queries=0, verifier_authoritative_queries=0,
        protected_evaluation_accessed=False, portability_gate='DEFERRED_NOT_BLOCKING_PHASE1')
    p.publish(OUT / 'phase1_integration_baseline_v1.json', value)
    print(json.dumps({k: v for k, v in value.items() if k != 'preservation'}, indent=2))


if __name__ == '__main__':
    freeze()
