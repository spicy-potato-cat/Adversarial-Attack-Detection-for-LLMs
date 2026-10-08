import hashlib
import json
from pathlib import Path
import subprocess
import unittest
from detection_service.research_protocol.track_b_portability import BASE, CLASSES, PRESERVED

ROOT=Path(__file__).resolve().parents[2]
class PortabilityTests(unittest.TestCase):
    def manifest(self):
        return json.loads((ROOT/'artifacts/research_protocol/portability/frozen_stack_portability_manifest_v1.json').read_text())
    def test_static_portability_classifications(self):
        v=self.manifest(); self.assertTrue(all(r['classification'] in CLASSES for r in v['artifacts']))
        self.assertEqual(v['overall_status'],'LOCAL_ARTIFACTS_CRITICAL')
        self.assertEqual(v['critical_local_only'],['artifacts/models/dm_b_v1/transformer/model.safetensors'])
    def test_ds_exact_git_restoration_proven_without_retraining(self):
        v=self.manifest()
        for suffix in ('ds_v2_model.json','ds_v2_cal_v1.json'):
            row=next(r for r in v['artifacts'] if r['logical_path'].endswith(suffix))
            self.assertEqual(row['classification'],'DETERMINISTICALLY_RECONSTRUCTABLE')
            b=subprocess.check_output(['git','-C',str(ROOT),'show',PRESERVED+':'+row['exact_restoration']['git_path']])
            self.assertEqual(hashlib.sha256(b).hexdigest(),row['expected_sha256'])
        self.assertFalse(v['restoration_executed']); self.assertFalse(v['retraining_permitted'])
    def test_remote_snapshot_revisions_immutable(self):
        for r in self.manifest()['artifacts']:
            if r['classification']=='REMOTE_IMMUTABLE':
                self.assertRegex(r['remote']['revision'],r'^[0-9a-f]{40}$')
                self.assertEqual(r['remote_availability'],'NEEDS_POST_TRACK_A_FRESH_CLONE_TEST')
    def test_no_protected_or_track_a_artifact_inventory(self):
        v=self.manifest()
        self.assertFalse(v['protected_data_opened'])
        for row in v['artifacts']:
            self.assertNotIn('r2_ds/',row['logical_path'])
            self.assertNotIn('final_test',row['logical_path'].lower())
        self.assertTrue(all(q==0 for q in v['authoritative_queries'].values()))
    def test_no_existing_base_files_changed(self):
        files=subprocess.check_output(['git','-C',str(ROOT),'diff','--name-only',BASE,'HEAD']).decode().splitlines()
        base=set(subprocess.check_output(['git','-C',str(ROOT),'ls-tree','-r','--name-only',BASE]).decode().splitlines())
        self.assertFalse(set(files)&base)
    def test_predeclaration_source_bindings_unchanged(self):
        value=json.loads((ROOT/'artifacts/research_protocol/r3/r3_predeclaration_v1.json').read_text())
        for name,expected in value['source_sha256'].items():
            self.assertEqual(hashlib.sha256((ROOT/name).read_bytes()).hexdigest(),expected,name)

if __name__=='__main__': unittest.main()
