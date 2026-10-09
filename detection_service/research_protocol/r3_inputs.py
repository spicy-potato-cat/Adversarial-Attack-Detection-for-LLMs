"""Read-only frozen R1 selection and Phase-1 R3 input gates."""
from collections import Counter
import csv
import hashlib
import json

from detection_service.research_protocol import r2_ds_predeclare as p, r3_preparation as design
from detection_service.research_protocol.r3_integration import OUT, PARENT, TRACK_B
from detection_service.research_protocol.operating_policy import OperationalPredictionRecord
from detection_service.research_protocol.r0_operational import verified_policy
from detection_service.research_protocol.regime import require
from detection_service.research_protocol.r3_readonly_cache import verified_reads

PRIVATE = p.ROOT / 'detection_service/outputs/r3-001'
BASELINE = OUT / 'phase1_integration_baseline_v1.json'
SEEDS = OUT / 'r3_seed_manifest_v1.json'
LABELS = dict(ds_v2='D_S', dm_b_v1='D_M-B', dg_v1='D_G')


def gate():
    value = p.files.read_json(BASELINE)
    baseline_commit = p.committed(BASELINE)
    require(value['status'] == 'PASS' and value['R3_authoritative_queries'] == 0, 'INTEGRATION_GATE_FAILED')
    require(p.git('merge-base', '--is-ancestor', baseline_commit, 'origin/exp/r3-001') == b'',
            'PUBLISHED_INTEGRATION_REQUIRED')
    require(p.git('branch', '--show-current').decode().strip() == 'exp/r3-001', 'R3_BRANCH_REQUIRED')
    require(p.git('rev-parse', 'exp/r2-ds-001').decode().strip() == PARENT and
            p.git('rev-parse', 'prep/r3-verifier-001').decode().strip() == TRACK_B, 'ACCEPTED_BRANCH_DRIFT')
    require(all(p.digest(name) == expected for name, expected in value['preservation']['sha256'].items()),
            'OLD_SCIENTIFIC_EVIDENCE_MUTATION')
    for name in ('r3_predeclaration_v1.json', 'r3_seed_policy_v1.json', 'r3_generator_contract_v1.json'):
        path = OUT / name
        p.committed(path)
        require(all(p.digest(key) == expected for key, expected in
                    p.files.read_json(path)['source_sha256'].items()), 'R3_SOURCE_CONTRACT_DRIFT')
    return baseline_commit


def read_predictions(path, policy=None):
    policy = policy or verified_policy()
    integers = {'truth_label', 'native_binary_prediction', 'operational_binary_prediction', 'input_tokens', 'tokens_analyzed'}
    floats = {'raw_score', 'calibrated_score', 'operational_threshold', 'latency_ms'}
    rows = []
    with path.open(encoding='utf-8', newline='') as stream:
        for row in csv.DictReader(stream):
            data = {k: None if v == '' else int(v) if k in integers else float(v) if k in floats else
                v == 'true' if k == 'truncated' else json.loads(v) if k == 'metadata' else v for k, v in row.items()}
            rows.append(OperationalPredictionRecord.model_validate(data, context={'operating_policy': policy}))
    return tuple(rows)


def select():
    policy = verified_policy()
    original = p.files.read_json(p.R1 / 'r1_dataset_manifest_v1.json')
    parents = [r for r in original['samples'] if r['truth_label'] == 1]
    require(len(parents) == 800, 'R1_ATTACK_POPULATION_DRIFT')
    records = read_predictions(p.R1 / 'r1_predictions_v1.csv', policy)
    from detection_service.research_protocol.r2_ds_transfer_run import aligned
    from detection_service.research_protocol.regime import RegimeManifest
    table = aligned(RegimeManifest.model_validate_json((p.R1 / 'r1_dataset_manifest_v1.json').read_bytes()), records, policy)
    require(table.coverage.status == 'COMPLETE', 'R1_COVERAGE_INVALID')
    by_parent = {}
    wanted = {r['sample_id'] for r in parents}
    for record in records:
        if record.sample_id not in wanted:
            continue
        require(record.status == 'OK', 'R3_NON_OK_PARENT')
        detector = LABELS[record.detector_id]
        group = by_parent.setdefault(record.sample_id, {})
        require(detector not in group, 'R3_DUPLICATE_PARENT_DETECTOR')
        group[detector] = record
    decisions = {sid: {label: 'ATTACK' if r.operational_binary_prediction else 'BENIGN'
        for label, r in group.items()} for sid, group in by_parent.items()}
    metadata = {r['sample_id']: r for r in p.files.read_json(p.R1 / 'r1_sample_manifest_v1.json')['samples']}
    selected = design.select_seeds(parents, decisions)
    result = []
    for parent in selected:
        sid = parent['sample_id']
        scores = {label: r.calibrated_score if label == 'D_S' else r.raw_score
                  for label, r in by_parent[sid].items()}
        require(design.objective(scores) >= 0, 'R3_BASELINE_DECISION_CONFLICT')
        result.append(dict(parent, parent_text_sha256=metadata[sid]['text_sha256'],
            baseline_scores=scores, baseline_decisions=decisions[sid],
            baseline_coverage={label: {k: getattr(r, k) for k in ('input_tokens', 'tokens_analyzed', 'truncated')}
                               for label, r in by_parent[sid].items()}))
    return result


def freeze():
    baseline_commit = gate()
    require(not SEEDS.exists() and not p.git('diff', '--name-only').decode().strip(), 'CLEAN_SEED_START_REQUIRED')
    with verified_reads():
        parents = select()
    require(0 < len(parents) <= 800 and len({r['lineage_id'] for r in parents}) == len(parents), 'R3_SEED_POLICY_CONFLICT')
    inputs = {path.relative_to(p.ROOT).as_posix(): p.files.sha(path) for path in (
        p.R1 / 'r1_dataset_manifest_v1.json', p.R1 / 'r1_sample_manifest_v1.json',
        p.R1 / 'r1_predictions_v1.csv', OUT / 'r3_seed_policy_v1.json',
        p.ROOT / 'detection_service/research_protocol/r3_preparation.py')}
    value = dict(artifact_version='r3_seed_manifest_v1', status='FROZEN_PRE_QUERY',
        integration_baseline_commit=baseline_commit, selection_algorithm='r3_seed_policy_v1/select_seeds',
        selection_inputs_sha256=inputs, r1_attack_parents=800, actual_parents=len(parents),
        source_counts=dict(Counter(r['source'] for r in parents)), inherited_lineages=len(parents),
        maximum_parents=800, candidate_evaluation_ceiling=61 * len(parents), detector_call_ceiling=183 * len(parents),
        membership_sha256=hashlib.sha256(p.files.canonical_bytes([r['sample_id'] for r in parents])).hexdigest(),
        authoritative_queries_before_freeze=0, selection_uses_R2_or_future_outcomes=False, parents=parents)
    p.publish(SEEDS, value)
    print(json.dumps({k: v for k, v in value.items() if k != 'parents'}, indent=2))


def frozen_parents():
    gate()
    p.committed(SEEDS)
    value = p.files.read_json(SEEDS)
    require(all(p.digest(name) == expected for name, expected in value['selection_inputs_sha256'].items()), 'SELECTION_INPUT_DRIFT')
    with verified_reads():
        require(select() == value['parents'], 'R3_SEED_MEMBERSHIP_NOT_REPRODUCIBLE')
    return value['parents']


def private_texts():
    parents = frozen_parents()
    entry = p.files.read_json(p.R1 / 'r1_sample_manifest_v1.json')['private_input']
    require(p.digest(entry['path']) == entry['sha256'], 'R1_PRIVATE_INPUT_DRIFT')
    wanted = {r['sample_id']: r['parent_text_sha256'] for r in parents}
    texts = {}
    for line in (p.ROOT / entry['path']).read_bytes().splitlines():
        row = json.loads(line)
        if row['sample_id'] in wanted:
            require(row['sample_id'] not in texts and design.sha(row['text']) == wanted[row['sample_id']], 'R3_PARENT_TEXT_DRIFT')
            texts[row['sample_id']] = row['text']
    require(set(texts) == set(wanted), 'R3_MISSING_PRIVATE_PARENT')
    return texts


if __name__ == '__main__':
    freeze()
