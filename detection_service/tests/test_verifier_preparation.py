from dataclasses import asdict, replace
import json
from pathlib import Path
import unittest
from detection_service.research_protocol import verifier_preparation as v

ROOT=Path(__file__).resolve().parents[2]
def sample(id='a',regime='R3_ENSEMBLE_TARGETED'):
    return v.FailureSample(id,'lineage-'+id,regime,'synthetic','unknown','parent-'+id,'synthetic text')
def native(p=.8):
    return dict(chunk_probabilities=[p],input_coverage=1.,truncation=False,latency_ms=1.)
def prediction(s,id='V1'):
    return v.NativeOutputAdapter(id,{s.sample_id:native() if id!='V3' else dict(native(),first_token='Yes')}).predict(s)

class VerifierTests(unittest.TestCase):
    def test_verifier_contract_schema(self):
        schema=json.loads((ROOT/'artifacts/research_protocol/verifier/verifier_prediction_schema_v1.json').read_text())
        p=prediction(sample())
        self.assertEqual(set(schema['required']),set(asdict(p)))
        with self.assertRaises(ValueError): replace(p,normalized_probability=2.)
        with self.assertRaises(ValueError): replace(p,status='ERROR')
    def test_verifier_failure_population_required(self):
        with self.assertRaisesRegex(ValueError,'POPULATION_REQUIRED'): v.recovery(None,[],'V1')
        with self.assertRaisesRegex(ValueError,'BASE_FAILURE'): v.synthetic_population([replace(sample(),base_decisions=('ATTACK','BENIGN','BENIGN'))])
    def test_verifier_recovery_formula(self):
        a,b=sample('a'),sample('b'); pop=v.synthetic_population([a,b])
        ps=[prediction(a),replace(prediction(b),decision='BENIGN')]
        self.assertEqual(v.recovery(pop,ps,'V1')['recovery'],.5)
    def test_verifier_undefined_empty_failure_population(self):
        result=v.recovery(v.synthetic_population([]),[],'V1')
        self.assertIsNone(result['recovery']); self.assertEqual(result['denominator'],0)
    def test_verifier_threshold_policy_explicit(self):
        d=json.loads((ROOT/'artifacts/research_protocol/verifier/verifier_study_predeclaration_v1.json').read_text())
        self.assertEqual(set(d['threshold_policy']),set(v.REVISIONS))
        a=sample(); adapter=v.NativeOutputAdapter('V2',{a.sample_id:native(.5)})
        self.assertEqual(adapter.predict(a).decision,'BENIGN')
    def test_verifier_no_future_failure_tuning(self):
        d=json.loads((ROOT/'artifacts/research_protocol/verifier/verifier_study_predeclaration_v1.json').read_text())
        self.assertFalse(d['failure_population_tuning']); self.assertEqual(d['threshold_source'],'DOCUMENTED_NATIVE_DEFAULT')
    def test_verifier_regime_conditioning(self):
        a,b=sample(),sample('b','R2_SINGLE_DETECTOR_TARGETED')
        pop=v.synthetic_population([a,b]); ps=[prediction(a),replace(prediction(b),decision='BENIGN')]
        self.assertEqual(v.recovery(pop,ps,'V1',regime=a.regime)['recovery'],1.)
        self.assertEqual(v.recovery(pop,ps,'V1',regime=b.regime)['recovery'],0.)
    def test_verifier_lineage_metadata_preserved(self):
        a=sample(); p=prediction(a); self.assertEqual(p.lineage_id,a.lineage_id)
        with self.assertRaisesRegex(ValueError,'LINEAGE'): v.recovery(v.synthetic_population([a]),[replace(p,lineage_id='other')],'V1')
    def test_verifier_no_authoritative_queries_in_preparation(self):
        self.assertEqual(v.AUTHORITATIVE_QUERIES,0)
        with self.assertRaisesRegex(ValueError,'STOP_LINE'): v.NativeOutputAdapter('V1',{}).load_model()
        with self.assertRaisesRegex(ValueError,'PREPARATION_ONLY'): v.load_failure_fixture({'evidence_kind':'REAL'})
    def test_missing_predictions_never_shrink_primary_denominator(self):
        a,b=sample(),sample('b'); result=v.recovery(v.synthetic_population([a,b]),[prediction(a)],'V1')
        self.assertIsNone(result['recovery']); self.assertEqual(result['denominator'],2)
        self.assertEqual(result['detected_fraction_lower_bound'],.5)
    def test_native_guard_category_is_not_probability(self):
        p=prediction(sample(),'V3'); self.assertEqual(p.decision,'ATTACK'); self.assertIsNone(p.normalized_probability)
        with self.assertRaisesRegex(ValueError,'FABRICATED'): replace(p,normalized_probability=.9)
    def test_population_hash_and_protected_rejection(self):
        pop=v.synthetic_population([sample()])
        with self.assertRaisesRegex(ValueError,'HASH'): replace(pop,membership_sha256='0'*64)
        with self.assertRaisesRegex(ValueError,'PROTECTED'): v.synthetic_population([replace(sample(),partition='FINAL_TEST')])
    def test_batch_and_incomplete_coverage(self):
        a=sample(); pop=v.synthetic_population([a]); adapter=v.NativeOutputAdapter('V1',{a.sample_id:dict(native(),input_coverage=.8,truncation=True)})
        ps=v.run_synthetic_batch(pop,adapter); self.assertEqual(len(ps),1)
        self.assertIsNone(v.recovery(pop,ps,'V1')['recovery'])

if __name__ == '__main__': unittest.main()
