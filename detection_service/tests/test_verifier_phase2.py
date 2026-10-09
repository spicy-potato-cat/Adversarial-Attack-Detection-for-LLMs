import copy
from dataclasses import asdict
import unittest
from unittest.mock import patch
from detection_service.tests.test_phase1_synthesis import synthetic_handoff
from detection_service.research_protocol import verifier_phase2 as v
from detection_service.research_protocol import verifier_preparation as p

def sample(sid='s1',lineage='l1'):
    return p.FailureSample(sid,lineage,'R3','synthetic','synthetic','parent-'+sid,'synthetic text')

def native(**extra):
    return dict(latency_ms=1.,input_coverage=1.,truncation=False,**extra)

class VerifierPhase2Tests(unittest.TestCase):
    def test_freeze_receipt_required(self):
        h,r=synthetic_handoff()
        payload=v.validate_r3_handoff(h,r)
        with self.assertRaisesRegex(ValueError,'FREEZE_RECEIPT_REQUIRED'):
            v.validate_population_manifest(payload['all_three_failure_manifest'],None,manifest_sha='0'*64,freeze_commit_sha='1'*40)
    def test_empty_population_loader(self):
        h,r=synthetic_handoff();pop=v.load_failure_population(h,r)
        self.assertEqual(pop['status'],v.EMPTY);self.assertEqual(pop['population_count'],0);self.assertFalse(pop['text_resolved'])
    def test_empty_denominator(self):
        pop=p.synthetic_population([]);out=v.analyze_synthetic(pop,{'V1':(),'V2':()})
        for result in out['recovery'].values():self.assertEqual(result['status'],v.EMPTY);self.assertIsNone(result['recovery'])
    def test_v1_mapping(self):
        self.assertEqual(p.NativeOutputAdapter('V1',{'s1':native(chunk_probabilities=[.2,.9])}).predict(sample()).decision,'ATTACK')
    def test_v2_mapping(self):
        self.assertEqual(p.NativeOutputAdapter('V2',{'s1':native(chunk_probabilities=[.2,.9])}).predict(sample()).decision,'ATTACK')
    def test_native_tie_rule(self):
        for vid in ('V1','V2'):self.assertEqual(p.NativeOutputAdapter(vid,{'s1':native(chunk_probabilities=[.5])}).predict(sample()).decision,'BENIGN')
    def test_v3_mapping(self):
        for token,decision in [(' Yes ','ATTACK'),('No','BENIGN')]:
            out=p.NativeOutputAdapter('V3',{'s1':native(first_token=token)}).predict(sample())
            self.assertEqual(out.decision,decision);self.assertIsNone(out.normalized_probability)
    def test_v3_invalid_output(self):
        out=p.NativeOutputAdapter('V3',{'s1':native(first_token='maybe')}).predict(sample())
        self.assertEqual(out.status,'INVALID_OUTPUT');self.assertIsNone(out.decision)
    def test_error_status(self):
        for status in ('ERROR','INPUT_LIMIT_EXCEEDED'):
            out=p.NativeOutputAdapter('V1',{'s1':native(status=status)}).predict(sample())
            self.assertEqual(out.status,status);self.assertIsNone(out.decision)
    def test_batch_order_and_ids(self):
        pop=p.synthetic_population([sample('z'),sample('a')])
        out=p.run_synthetic_batch(pop,p.NativeOutputAdapter('V2',{x.sample_id:native(chunk_probabilities=[.9]) for x in pop.samples}))
        self.assertEqual([x.sample_id for x in out],['a','z'])
    def test_independent_v1_v2_pending_v3(self):
        pop=p.synthetic_population([sample('a'),sample('b','l2')]); supplied={}
        for vid,probs in [('V1',[.9,.2]),('V2',[.9,.9])]:
            supplied[vid]=p.run_synthetic_batch(pop,p.NativeOutputAdapter(vid,{x.sample_id:native(chunk_probabilities=[q]) for x,q in zip(pop.samples,probs)}))
        out=v.analyze_synthetic(pop,supplied)
        self.assertEqual(out['pending_verifier_ids'],['V3']);self.assertEqual(out['recovery']['V1']['recovery'],.5)
        self.assertEqual(out['overlap'][0]['shared_catches'],1)
        self.assertEqual(next(x for x in out['unique_recovery'] if x['verifier_id']=='V2')['unique_catches'],1)
        self.assertEqual(out['unrecovered_sample_ids'],[])
        self.assertTrue(out['source_analysis'])
    def test_incomplete_denominator_not_shrunk(self):
        pop=p.synthetic_population([sample('a'),sample('b')])
        pred=p.NativeOutputAdapter('V1',{'a':native(chunk_probabilities=[.9])}).predict(sample('a'))
        out=v.analyze_synthetic(pop,{'V1':(pred,)})['recovery']['V1']
        self.assertEqual(out['population_count'],2);self.assertEqual(out['status'],'INCOMPLETE');self.assertIsNone(out['recovery'])
    def test_duplicate_predictions_rejected(self):
        pop=p.synthetic_population([sample()]);pred=p.NativeOutputAdapter('V1',{'s1':native(chunk_probabilities=[.9])}).predict(sample())
        with self.assertRaises(ValueError):v.analyze_synthetic(pop,{'V1':(pred,pred)})
    def test_invalid_chunks_rejected(self):
        for chunks in ([],[1.1],[float('nan')]):
            with self.assertRaises(ValueError):p.NativeOutputAdapter('V1',{'s1':native(chunk_probabilities=chunks)}).predict(sample())
    def test_queries_zero_model_loading_blocked(self):
        self.assertEqual(v.AUTHORITATIVE_QUERIES,0);self.assertEqual(p.AUTHORITATIVE_QUERIES,0)
        with self.assertRaisesRegex(ValueError,'STOP_LINE'):p.NativeOutputAdapter('V1',{}).load_model()
    def fixture_manifest(self):
        h,r=synthetic_handoff();payload=v.validate_r3_handoff(h,r)
        manifest=payload['all_three_failure_manifest'];receipt=payload['freeze_receipt']['failure_population_freeze_receipt']
        manifest['samples']=[dict(sample_id='a',lineage_id='l1',parent_sample_id='p1',source='synthetic',attack_family=None,
            regime='R3',partition='INTERNAL_TEST',truth_label=1,base_decisions=['BENIGN']*3,text_ref={'path':'local.txt','sha256':'0'*64})]
        manifest['population_count']=1
        return manifest,receipt
    def test_population_unique_and_lineage_valid(self):
        manifest,receipt=self.fixture_manifest()
        for mutation in ('duplicate','lineage','base_decisions','text'):
            bad=copy.deepcopy(manifest)
            if mutation=='duplicate':bad['samples']*=2;bad['population_count']=2
            elif mutation=='lineage':bad['samples'][0]['lineage_id']=''
            elif mutation=='base_decisions':bad['samples'][0]['base_decisions'][0]='ATTACK'
            else:bad['samples'][0]['text']='premature raw text'
            with self.assertRaises(ValueError):v.validate_population_manifest(bad,receipt,manifest_sha=receipt['manifest_sha256'],freeze_commit_sha='1'*40)
    def test_manifest_hash_mismatch(self):
        manifest,receipt=self.fixture_manifest()
        with self.assertRaisesRegex(ValueError,'HASH_MISMATCH'):v.validate_population_manifest(manifest,receipt,manifest_sha='0'*64,freeze_commit_sha='1'*40)
    def test_prerun_freeze(self):
        manifest,receipt=self.fixture_manifest()
        with self.assertRaisesRegex(ValueError,'FROZEN_AFTER_QUERIES'):v.validate_population_manifest(manifest,receipt,manifest_sha=receipt['manifest_sha256'],freeze_commit_sha='1'*40,first_verifier_query_at='2026-10-08T00:00:00Z')
    def test_no_text_resolved_during_loading(self):
        manifest,receipt=self.fixture_manifest()
        with patch.object(v.Path,'read_bytes',side_effect=AssertionError('premature text access')):
            pop=v.validate_population_manifest(manifest,receipt,manifest_sha=receipt['manifest_sha256'],freeze_commit_sha='1'*40)
        self.assertFalse(pop['text_resolved'])
        with self.assertRaisesRegex(ValueError,'AUTHORIZATION'):v.resolve_local_text(pop,'.')
    def test_population_mutation_rejected(self):
        manifest,receipt=self.fixture_manifest()
        pop=v.validate_population_manifest(manifest,receipt,manifest_sha=receipt['manifest_sha256'],freeze_commit_sha='1'*40)
        pop['samples'][0]['sample_id']='changed'
        with self.assertRaisesRegex(ValueError,'MUTATED'):v.resolve_local_text(pop,'.',phase2_authorized=True)

if __name__=='__main__':unittest.main()
