import copy
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from detection_service.research_protocol import phase1_synthesis as s
from detection_service.research_protocol.phase1_synthesis import CommittedR3Reader

class SyntheticReader:
    evidence_kind='SYNTHETIC_FIXTURE'
    def __init__(self,data): self.data=data; self.calls=[]
    def __call__(self,commit,path): self.calls.append((commit,path)); return self.data[path]

def synthetic_handoff():
    # Derive a synthetic adapter fixture from accepted R1 metadata; no R3 read.
    b=json.loads(s.git_bytes('artifacts/research_protocol/'+s.BUNDLES['R1']))
    b['target_detector']='ALL'; b['threat_regime']='R3_ENSEMBLE_TARGETED'
    for v in b['core_metrics'].values():
        if isinstance(v,dict) and 'provenance' in v: v['provenance']['threat_regime']=b['threat_regime']
    manifest=dict(status='ACCEPTED',regime='R3',partition='INTERNAL_TEST',population_count=0,samples=[])
    objects=dict(result_bundle=b,common_mode=b['core_metrics']['common_mode'],failure_patterns=b['core_metrics']['failure_patterns'],
                 uncertainty=b['uncertainty'],prediction_manifest={'prediction_batch_sha':b['core_metrics']['individual']['provenance']['prediction_batch_sha']},
                 all_three_failure_manifest=manifest)
    desc={};data={}
    for role,v in objects.items():
        path='artifacts/research_protocol/r3/synthetic_'+role+'.json'
        raw=s.bytes_json(v); data[path]=raw;desc[role]=dict(path=path,sha256=s.sha256(raw))
    freeze=dict(status='ACCEPTED',frozen=True,verifier_authoritative_queries_at_freeze=0,protected_evaluation_accessed=False,
        artifact_hashes={r:desc[r]['sha256'] for r in s.R3_ROLES},failure_population_freeze_receipt=dict(
            status='ACCEPTED',frozen=True,r3_status='ACCEPTED',manifest_sha256=desc['all_three_failure_manifest']['sha256'],
            frozen_at='2026-10-09T00:00:00Z',verifier_authoritative_queries_at_freeze=0,protected_evaluation_accessed=False))
    path='artifacts/research_protocol/r3/synthetic_freeze_receipt.json';raw=s.bytes_json(freeze)
    data[path]=raw;desc['freeze_receipt']=dict(path=path,sha256=s.sha256(raw))
    return dict(status='ACCEPTED',frozen=True,freeze_commit_sha='1'*40,artifacts=desc,evidence_kind='SYNTHETIC_FIXTURE'),SyntheticReader(data)

class SynthesisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.registry=s.load_pre_r3(); cls.records={r['regime_id']:r for r in cls.registry['records']}
    def test_r0_load(self): self.assertEqual(self.records['R0']['attack_count'],183)
    def test_r1_load(self): self.assertEqual(self.records['R1']['attack_count'],800)
    def test_r2_dmb_load(self): self.assertEqual(self.records['R2-DMB']['attack_count'],800)
    def test_r2_ds_load(self): self.assertEqual(self.records['R2-D_S']['attack_count'],698)
    def test_attack_only_guard(self):
        for rid in ('R2-DMB','R2-D_S'):
            r=self.records[rid]
            for d in r['detectors']:
                for name in ('fpr','roc_auc','ap'): self.assertEqual(d[name],s.cell(None,'NOT_APPLICABLE'))
            changed=copy.deepcopy(r);changed['detectors'][0]['fpr']=s.cell(0)
            with self.assertRaises(ValueError): s.RegimeRecord.model_validate(changed)
    def test_pair_jfn(self):
        for r in self.registry['records'][:-1]:
            for p in r['pairs']: self.assertEqual(p['jfn']['value'],p['shared_fn']/r['attack_count'])
    def test_independence_reference(self):
        for r in self.registry['records'][:-1]:
            d={d['detector_id']:d for d in r['detectors']}
            for p in r['pairs']: self.assertAlmostEqual(p['independence_reference']['value'],d[p['left_detector']]['fnr']['value']*d[p['right_detector']]['fnr']['value'])
    def test_ejf(self):
        for r in self.registry['records'][:-1]:
            for p in r['pairs']: self.assertAlmostEqual(p['ejf']['value'],p['jfn']['value']-p['independence_reference']['value'])
    def test_jaccard(self):
        for r in self.registry['records'][:-1]:
            for p in r['pairs']: self.assertEqual(p['fn_jaccard']['value'],s.ratio(p['shared_fn'],p['union_fn']))
    def test_all_three(self):
        for r in self.registry['records'][:-1]: self.assertEqual(r['all_three_jfn']['value'],r['all_three_fn']/r['attack_count'])
    def test_etr_undefined(self):
        for t in self.records['R2-DMB']['targeted']:
            for x in t['transfers']: self.assertEqual(x['etr']['status'],'UNDEFINED');self.assertIsNone(x['etr']['value'])
    def test_r3_placeholder(self):
        self.assertEqual(self.records['R3']['status'],'AWAITING_FROZEN_R3_BUNDLE')
        for rows in s.figure_data(self.registry).values():
            for r in rows:
                if r['regime']=='R3': self.assertEqual(r['status'],s.NOT_OBSERVED);self.assertIsNone(r['value'])
    def test_partial_r3_rejected(self):
        h,reader=synthetic_handoff();del h['artifacts']['prediction_manifest']
        with self.assertRaisesRegex(ValueError,'PARTIAL'): s.validate_r3_handoff(h,reader)
        self.assertFalse(reader.calls)
    def test_unfrozen_r3_rejected(self):
        h,reader=synthetic_handoff();h['frozen']=False
        with self.assertRaisesRegex(ValueError,'FROZEN'): s.validate_r3_handoff(h,reader)
        self.assertFalse(reader.calls)
    def test_missing_r3_freeze_receipt_rejected(self):
        h,reader=synthetic_handoff();del h['artifacts']['freeze_receipt']
        with self.assertRaisesRegex(ValueError,'PARTIAL'):s.validate_r3_handoff(h,reader)
        self.assertFalse(reader.calls)
    def test_nonexistent_commit_rejected(self):
        reader=CommittedR3Reader(s.ROOT,phase2_authorized=True)
        with self.assertRaises(subprocess.CalledProcessError):reader('0'*40,'artifacts/research_protocol/r3/synthetic_only.json')
    def test_uncommitted_r3_rejected(self):
        h,reader=synthetic_handoff();h['freeze_commit_sha']='working-tree'
        with self.assertRaisesRegex(ValueError,'COMMITTED'): s.validate_r3_handoff(h,reader)
    def test_missing_hash_rejected(self):
        h,reader=synthetic_handoff();del h['artifacts']['common_mode']['sha256']
        with self.assertRaisesRegex(ValueError,'HASH_REQUIRED'): s.validate_r3_handoff(h,reader)
    def test_wrong_hash_rejected(self):
        h,reader=synthetic_handoff();h['artifacts']['result_bundle']['sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'HASH_MISMATCH'): s.validate_r3_handoff(h,reader)
    def test_valid_synthetic_handoff(self):
        h,reader=synthetic_handoff();self.assertEqual(s.validate_r3_handoff(h,reader)['all_three_failure_manifest']['population_count'],0)
    def test_arbitrary_reader_rejected(self):
        h,reader=synthetic_handoff();h.pop('evidence_kind')
        with self.assertRaisesRegex(ValueError,'COMMITTED_READER'):s.validate_r3_handoff(h,reader)
    def test_real_r3_reader_requires_phase2(self):
        with self.assertRaisesRegex(ValueError,'AUTHORIZATION'):CommittedR3Reader(s.ROOT)
    def test_no_r3_or_protected_reads(self):
        self.assertEqual({x['path'] for x in self.registry['read_receipt']},s.ALLOWED)
        self.assertTrue(all('/r3/' not in x['path'] and 'protected' not in x['path'].lower() for x in self.registry['read_receipt']))
        for path in ('artifacts/research_protocol/r3/r3_result_bundle_v1.json','data/protected/test.csv'):
            with patch.object(s.subprocess,'check_output') as proc:
                with self.assertRaises(ValueError):s.git_bytes(path)
                proc.assert_not_called()
    def test_queries_zero(self): self.assertEqual(set(self.registry['authoritative_queries'].values()),{0});self.assertFalse(self.registry['protected_access'])
    def test_old_branch_unchanged(self):
        self.assertEqual(subprocess.check_output(['git','rev-parse','prep/r3-verifier-001'],cwd=s.ROOT).decode().strip(),s.OLD_TRACK_B_SHA)
    def test_frozen_intervals_unchanged(self):
        for rid,path in s.BUNDLES.items():
            raw=json.loads(s.git_bytes('artifacts/research_protocol/'+path));self.assertEqual(self.records[rid]['uncertainty'],raw['uncertainty'])
    def test_bad_counts_rejected(self):
        raw=json.loads(s.git_bytes('artifacts/research_protocol/'+s.BUNDLES['R1']));raw['core_metrics']['common_mode']['pairs'][0]['shared_fn_count']=1
        with self.assertRaises(ValueError):s.normalize('R1',raw)
    def test_export_deterministic(self):
        with tempfile.TemporaryDirectory() as tmp:
            s.export(self.registry,tmp,plot=False);first={p.name:p.read_bytes() for p in Path(tmp).iterdir()}
            s.export(self.registry,tmp,plot=False);self.assertEqual(first,{p.name:p.read_bytes() for p in Path(tmp).iterdir()})
    def test_tables_and_figures(self):
        self.assertEqual(set(s.tables(self.registry)),set('ABCDE'));self.assertEqual(len(s.figure_data(self.registry)),9)

if __name__=='__main__':unittest.main()
