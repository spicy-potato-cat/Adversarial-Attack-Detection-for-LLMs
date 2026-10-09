"""Model-free snapshots and delta acceptance for the three context repairs."""
import argparse
import json
import subprocess
import sys
import xml.etree.ElementTree as ET

from detection_service.research_protocol import r2_ds_predeclare as p

START = '913ee734cb48eb8404e8f6ed62456eb07950246e'
OUT = p.ROOT / 'reviews/evidence/r2_ds_acceptance_context'
BEFORE = OUT / 'before_v1.json'


def snapshot():
    assert p.git('rev-parse', 'HEAD').decode().strip() == START
    accepted = p.files.read_json(p.OUT / 'r2_ds_final_acceptance_v2.json')
    paths = {p.ROOT / name for name in accepted['sha256']}
    paths.update(p.OUT.glob('*'))
    for directory in ('r2-ds-001', 'r2-ds-001-authoritative-v2'):
        paths.update((p.ROOT / 'detection_service/outputs' / directory).glob('*.json*'))
    paths.update(p.ROOT / name for name in (
        'reviews/DS_NUMERICAL_REPRODUCIBILITY_DIAGNOSIS_v1.md',
        'reviews/R2_DS_TARGETED_EVASION_RESULTS_v2.md',
        'artifacts/semantic_v2/oof/run_started_v1.json',
        'artifacts/semantic_v2/oof/acceptance_manifest_v1.json'))
    hashes = {path.relative_to(p.ROOT).as_posix(): p.files.sha(path)
              for path in sorted(paths) if path.is_file()}
    assert all(hashes[name] == expected for name, expected in accepted['sha256'].items())
    p.publish(BEFORE, dict(starting_HEAD=START, sha256=hashes,
        track_b=p.git('rev-parse', 'prep/r3-verifier-001').decode().strip(),
        track_b_reflog=p.git('reflog', 'show', '--format=%H %gs', 'prep/r3-verifier-001').decode()))
    print(json.dumps(dict(snapshot_files=len(hashes), path=str(BEFORE))))


def accept():
    before = p.files.read_json(BEFORE)
    assert all(p.digest(name) == expected for name, expected in before['sha256'].items()), 'SCIENTIFIC_ARTIFACT_MUTATION_DETECTED'
    assert p.git('rev-parse', 'prep/r3-verifier-001').decode().strip() == before['track_b']
    assert p.git('reflog', 'show', '--format=%H %gs', 'prep/r3-verifier-001').decode() == before['track_b_reflog']
    receipts = []
    for name in ('r2_ds_context_three.xml', 'r2_ds_context_modules.xml'):
        path = p.ROOT / 'tmp' / name
        cases = list(ET.parse(path).getroot().iter('testcase'))
        assert cases and not any(case.find(tag) is not None for case in cases
                                 for tag in ('failure', 'error', 'skipped'))
        receipts.append(dict(path=path.relative_to(p.ROOT).as_posix(),
            passed=len(cases), sha256=p.files.sha(path)))
    assert receipts[0]['passed'] == 3 and receipts[1]['passed'] == 103
    baseline = json.loads(subprocess.check_output([sys.executable, '-B', '-m',
        'detection_service.scripts.verify_quality_preservation', '--mode', 'check'], cwd=p.ROOT))
    assert baseline['status'] == 'PASS' and baseline['hash_checks'] == 96
    from detection_service.research_protocol.release_validation import check_acceptance
    from detection_service.research_protocol import protocol_patch_001, r2_dmb_predeclare
    release = check_acceptance()
    source = p.preserved()
    patch = len(protocol_patch_001.verify_patch()['sha256'])
    dmb = r2_dmb_predeclare.preserved()
    r1 = p.files.read_json(p.R1 / 'r1_gate_d_acceptance_v1.json')['sha256']
    assert all(p.digest(name) == expected for name, expected in r1.items())
    assert (source, release['hash_checks'], patch) == (503, 118, 262)
    value = dict(status='PASS', verdict='R2_DS_COMPLETE_READY_FOR_MERGE_GATE_1',
        starting_HEAD=START, delta_receipts=receipts,
        prior_full_suite=dict(passed=1559, failed=3, skipped=0, rerun=False),
        historical_report_preserved=True, acceptance_supersedes_only_test_context_blockers=True,
        baseline_preservation=baseline, release_preservation=release,
        source_hash_checks=source, protocol_patch_hash_checks=patch,
        r2_dmb_hash_checks=dmb, r1_hash_checks=len(r1),
        scientific_files_unchanged=len(before['sha256']), snapshot_sha256=p.files.sha(BEFORE),
        track_b=before['track_b'], track_b_reflog_unchanged=True,
        new_scientific_queries=dict(D_S=0, D_M_B=0, D_G=0, R3=0, verifier=0),
        bootstrap_recomputed=False, generation_rerun=False, predictions_rescored=False)
    p.publish(OUT / 'acceptance_v1.json', value)
    print(json.dumps(value, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=('snapshot', 'accept'), required=True)
    (snapshot if parser.parse_args().mode == 'snapshot' else accept)()
