"""Pre-score corpus acceptance; never imports/executes a detector."""

from collections import Counter
import json
import re

import pytest

from detection_service.research_protocol import r1_corpus as c, protocol_lock
from detection_service.research_protocol.regime import RegimeManifest, RegimeContractError


def manifest():
    return RegimeManifest.model_validate_json((c.OUT / 'r1_dataset_manifest_v1.json').read_bytes())


def evidence(name):
    return c.files.read_json(c.OUT / (name + '_v1.json'))


@pytest.fixture(scope='module')
def extracted():
    return c.extract()[0]


def test_r1_manifest_regime():
    value = manifest()
    assert value.threat_regime == 'R1_SHIFTED_UNSEEN'
    assert all(s.threat_regime == value.threat_regime for s in value.samples)
    assert (value.sample_count, value.attack_count, value.benign_count) == (1800, 800, 1000)


def test_r1_target_null():
    assert all(s.target_detector is None for s in manifest().samples)


def test_r1_no_training_partition():
    assert manifest().partition == 'INTERNAL_TEST'
    assert all(s.partition == 'INTERNAL_TEST' for s in manifest().samples)


def test_r1_source_revisions_pinned():
    value = manifest()
    assert {s.source:s.dataset_revision for s in value.samples} == c.REVISIONS
    assert Counter(s.source for s in value.samples) == c.RULES['target_counts']


def test_r1_exact_overlap_removed():
    audit = evidence('r1_contamination_audit')
    assert audit['remaining_selected_raw_exact'] == 0
    assert sum(v.get('raw_exact_rows',0) for v in audit['candidate_counts'].values()) == 0
    assert audit['development_population'] == 1601


def test_r1_canonical_overlap_removed():
    audit = evidence('r1_contamination_audit')
    assert audit['remaining_selected_canonical_exact'] == 0
    assert sum(v.get('canonical_exact_rows',0) for v in audit['candidate_counts'].values()) == 0
    assert audit['selected_near_rows_at_threshold'] == {'0.7':0,'0.8':0,'0.9':0}


def test_approved_canonicalization():
    assert c.n1('e\u0301\r\n X\r') == '\u00e9\n X\n'
    assert c.n1('a  b') == 'a  b'
    assert c.shingles('ONE two THREE four') == {('one','two','three'),('two','three','four')}


def test_r1_lineage_valid():
    rows = manifest().samples
    assert all(s.lineage_id is not None for s in rows)
    assert len({s.lineage_id for s in rows}) == 1097
    injec = [s for s in rows if s.source == 'INJECAGENT_BASE']
    assert len({s.lineage_id for s in injec}) == 1
    assert sum(s.lineage_provenance_status == 'SINGLETON_FALLBACK' for s in rows) == 1000


def test_r1_preflight_pass():
    result = protocol_lock.verify_experiment_preflight(protocol_lock.ExperimentRequest(manifest=manifest(),bootstrap_unit='LINEAGE_CLUSTERED'))
    assert result['status'] == 'PASS' and result['experiment_executed'] is False


def test_r1_evidence_hashes():
    for ref in manifest().evidence:
        assert c.files.sha(c.ROOT/ref.path) == ref.sha256


def test_r1_source_clearance():
    value = evidence('r1_source_clearance')
    assert len(value['sources']) == 3
    assert all(r['clearance_state'] == 'CLEARED_WITH_LOCAL_ONLY_RESTRICTION' for r in value['sources'])
    assert not value['protected_source_payloads_opened']
    for row in value['sources']:
        for f in row['selected_files']+row['clearance_evidence']:
            assert c.files.sha(c.ROOT/f['path']) == f['sha256']
            assert (c.ROOT/f['path']).stat().st_size == f['size']


def test_r1_mirror_provenance():
    actual = c.provenance()
    value = evidence('r1_source_clearance')
    assert {r['source']:r['selected_files'] for r in value['sources']} == dict(actual)
    assert value['sources'][0]['local_revision'].startswith('CONTENT_ADDRESSED_BUCKET_SNAPSHOT:')


def test_r1_attempt_not_success():
    assert c.attempted(True) and c.attempted('True')
    assert not any(c.attempted(v) for v in (False,'False','Unclear',None,1,'true'))
    rows = evidence('r1_sample_manifest')['samples']
    ll = [s for s in rows if s['source']=='LLMAIL_INJECT']
    assert all(s['metadata']['attack_attempt'] is True for s in ll)
    assert any(False in s['metadata']['upstream_exfil_sent_observed'] for s in ll)
    assert sum(None in s['metadata']['upstream_exfil_sent_observed'] for s in ll) == 1
    assert all(s.attack_success is None for s in manifest().samples)


def test_r1_family_mapping():
    value=manifest()
    assert Counter(s.attack_family for s in value.samples)=={'INDIRECT_PROMPT_INJECTION':400,'AGENT_TOOL_INJECTION':400,None:1000}
    assert all(s.attack_family_provenance=='NOT_APPLICABLE' for s in value.samples if not s.truth_label)


def test_r1_sampling_deterministic(extracted):
    removed={r['sample_id'] for r in evidence('r1_contamination_audit')['exclusions']}
    rows=[r for r in extracted if r['sample_id'] not in removed]
    first=c.select(rows)
    second=c.select(list(reversed(rows)))
    expected=[s.sample_id for s in manifest().samples]
    assert [r['sample_id'] for r in first]==[r['sample_id'] for r in second]==expected
    c.assign_lineages(first)
    assert {r['sample_id']:r['lineage_id'] for r in first}=={s.sample_id:s.lineage_id for s in manifest().samples}


def test_r1_llmail_team_balance():
    counts=evidence('r1_source_selection')['llmail_team_counts']
    assert len(counts)==96 and max(counts.values())<=5
    assert sum(counts.values())==400


def test_r1_injec_base_only(extracted):
    rows=[r for r in extracted if r['source']=='INJECAGENT_BASE']
    assert len(rows)==1054 and all(r['metadata']['setting']=='BASE' for r in rows)
    chosen=[r for r in evidence('r1_sample_manifest')['samples'] if r['source']=='INJECAGENT_BASE']
    assert Counter(r['metadata']['harm_group'] for r in chosen)=={'dh':200,'ds':200}
    assert len({r['metadata']['user_tool'] for r in chosen})==17


def test_r1_inputs_are_exact_source_text(extracted):
    texts={r['sample_id']:r['text'] for r in extracted}
    metadata=evidence('r1_sample_manifest')
    private=c.ROOT/metadata['private_input']['path']
    assert c.files.sha(private)==metadata['private_input']['sha256']
    local=[json.loads(line) for line in private.read_bytes().splitlines()]
    assert len(local)==1800
    assert all(r['text']==texts[r['sample_id']] for r in local)
    assert {r['sample_id']:c.sha(r['text']) for r in local}=={r['sample_id']:r['text_sha256'] for r in metadata['samples']}


def test_r1_privacy_metadata_only():
    rows=evidence('r1_sample_manifest')['samples']
    forbidden={'text','prompt','body','subject','team_id','RowKey','output','judge_answer','Attacker Instruction','Expected Achievements','Thought'}
    assert all(not (forbidden & r.keys()) and not (forbidden & r['metadata'].keys()) for r in rows)
    assert all(not re.search(r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}',json.dumps(r)) for r in rows)


def test_r1_deterministic_serialization():
    value=manifest()
    assert (c.OUT/'r1_dataset_manifest_v1.json').read_bytes()==c.files.manifest_bytes(value.model_dump(mode='json'))
    assert RegimeManifest.model_validate_json(value.deterministic_json())==value


def test_r1_no_threshold_override():
    with pytest.raises(Exception):
        protocol_lock.ExperimentRequest(manifest=manifest(),bootstrap_unit='LINEAGE_CLUSTERED',threshold=0.9)


def test_r1_frozen_mutation_rejected():
    with pytest.raises(RegimeContractError,match='FROZEN_MANIFEST_MUTATION'):
        manifest().model_copy(update={'sample_count':1})
