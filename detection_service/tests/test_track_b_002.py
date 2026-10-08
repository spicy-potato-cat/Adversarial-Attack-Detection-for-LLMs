import hashlib,json,subprocess,unittest
from pathlib import Path
from detection_service.research_protocol import track_b_002_validation as v

ROOT=Path(__file__).resolve().parents[2]
BASE='99b012e5b72fbae9273fa73ccc8d84d579a69c83'
START='0cd2d506380cbb3ec513207e4fa66ad422d2b3f2'
def read(name):return v.read(ROOT,'artifacts/research_protocol/'+name)
def git(*args):return subprocess.check_output(['git','-C',str(ROOT),*args]).decode().strip()

class TrackB002Tests(unittest.TestCase):
    def test_portability_manifest_schema(self):
        d=read('portability/frozen_stack_portability_manifest_v2.json');v.validate_portability(d)
        d['artifacts'][0]['classification']='MADE_UP'
        with self.assertRaisesRegex(ValueError,'CLASSIFICATION'):v.validate_portability(d)
    def test_dmb_authoritative_hash_expected(self):
        r=read('portability/dmb_remote_backup_receipt_v1.json')
        self.assertEqual(r['source_sha256'],v.DMB_SHA);self.assertEqual(r['expected_sha256'],v.DMB_SHA)
        self.assertTrue(r['hash_match']);self.assertEqual(r['source_size_bytes'],328492280)
    def remote(self):
        r=read('portability/dmb_remote_backup_receipt_v1.json')
        if r['status']!='REMOTE_IMMUTABLE':self.skipTest('Private remote backup blocked by automatic approval review; no success fabricated')
        return r
    def test_dmb_remote_manifest_revision_pinned(self):
        r=self.remote();self.assertRegex(r['remote_immutable_revision'],'^[0-9a-f]{40}$');self.assertTrue(r['private'])
    def test_dmb_verification_copy_hash(self):
        r=self.remote();self.assertTrue(r['byte_identical']);self.assertEqual(r['verification_download_sha256'],v.DMB_SHA)
        with Path(r['verification_local_path']).open('rb') as stream:actual=hashlib.file_digest(stream,'sha256').hexdigest()
        self.assertEqual(actual,v.DMB_SHA);self.assertEqual(Path(r['verification_local_path']).stat().st_size,r['source_size_bytes'])
    def test_dg_clarification_preserves_model_identity(self):
        d=read('portability/dg_hash_binding_clarification_v1.json');v.validate_dg(d);self.assertEqual(d['frozen_model'],v.DG_MODEL)
        blob=subprocess.check_output(['git','-C',str(ROOT),'show',BASE+':artifacts/models/dg_v1/environment.json'])
        reconstructed=blob.replace(b'\n',b'\r\n')
        self.assertEqual(hashlib.sha256(reconstructed).hexdigest(),d['original_environment_recorded_sha256'])
        self.assertEqual(json.loads(blob),json.loads(reconstructed))
    def test_dg_clarification_preserves_revision(self):
        d=read('portability/dg_hash_binding_clarification_v1.json');self.assertEqual(d['frozen_revision'],v.DG_REV)
        self.assertFalse(d['weights_affected']);self.assertFalse(d['historical_scientific_results_affected'])
    def test_verifier_readiness_schema(self):
        d=read('verifier/verifier_runtime_readiness_v1.json');v.validate_readiness(d)
        d['models'][0]['live_execution_ready']=True
        with self.assertRaisesRegex(ValueError,'UNTESTED'):v.validate_readiness(d)
    def pinned(self,k):
        r=next(r for r in read('verifier/verifier_runtime_readiness_v1.json')['models'] if r['candidate_id']==k)
        self.assertEqual(r['revision'],v.REVISIONS[k]);self.assertEqual(r['resolved_revision'],r['revision'])
    def test_verifier_v1_revision_pinned(self):self.pinned('V1')
    def test_verifier_v2_revision_pinned(self):self.pinned('V2')
    def test_verifier_v3_revision_pinned(self):self.pinned('V3')
    def test_verifier_no_authoritative_queries(self):
        v.validate_readiness(read('verifier/verifier_runtime_readiness_v1.json'))
        from detection_service.research_protocol.verifier_preparation import NativeOutputAdapter
        with self.assertRaisesRegex(ValueError,'STOP_LINE'):NativeOutputAdapter('V1',{}).load_model()
    def test_r3_no_authoritative_queries(self):
        d=read('r3/r3_predeclaration_v1.json');self.assertEqual(d['authoritative_queries'],dict.fromkeys(('D_S','D_M-B','D_G'),0))
        self.assertEqual(git('diff','--name-only',START,'HEAD','--','artifacts/research_protocol/r3','detection_service/research_protocol/r3_preparation.py'),'')
    def test_track_a_not_modified(self):
        base=set(git('ls-tree','-r','--name-only',BASE).splitlines())
        changes=git('diff','--name-only',BASE,'HEAD').splitlines()
        self.assertFalse(base.intersection(changes));self.assertFalse(any(p.startswith('artifacts/research_protocol/r2_ds/') for p in changes))
        plan=read('portability/merge_gate_1_plan_v1.json');self.assertFalse(plan['merge_executed'])
    def test_protected_data_not_accessed(self):
        d=read('portability/merge_gate_1_plan_v1.json');self.assertFalse(d['protected_data_accessed'])
        self.assertEqual(read('verifier/verifier_runtime_readiness_v1.json')['failure_population'],'NOT_OPENED_NOT_CONSTRUCTED')
    def test_merge_plan_all_track_b_commits_accounted(self):
        p=read('portability/merge_gate_1_plan_v1.json')
        actual=set(git('rev-list',BASE+'..HEAD').splitlines());declared={r['commit'] for r in p['commits'] if r['commit']}
        missing=actual-declared
        for sha in missing:self.assertEqual(git('show','-s','--format=%s',sha),'docs(integration): prepare merge gate and R2-DG decision')
        self.assertEqual(len(p['commits']),8);self.assertEqual(p['direct_overlap_paths'],[])
        self.assertTrue(p['semantic_test_dependencies'])
    def test_fresh_clone_plan_hash_complete(self):
        d=read('portability/fresh_clone_required_artifacts_v1.json');v.validate_fresh_clone(d)
        d['required_artifacts'][0]['expected_sha256']=None
        with self.assertRaisesRegex(ValueError,'HASH_MISSING'):v.validate_fresh_clone(d)
    def test_post_idle_load_check_stops_without_gate(self):
        from detection_service.research_protocol.track_b_post_idle_load_check import load_only
        with self.assertRaisesRegex(ValueError,'AUTHORIZATION_REQUIRED'):load_only('')

if __name__=='__main__':unittest.main()
