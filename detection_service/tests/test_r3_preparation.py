import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from detection_service.research_protocol import r3_preparation as r

ROOT = Path(__file__).resolve().parents[2]
class Stub:
    evidence_kind = 'SYNTHETIC_FIXTURE'
    def __init__(self, detector, ratio=1.2):
        self.detector, self.ratio, self.calls = detector, ratio, 0
    def __call__(self, text):
        self.calls += 1
        i = r.DOMAIN.index(self.detector)
        return {'status':'OK',r.FIELDS[i]:r.THRESHOLDS[i]*self.ratio}
    def coverage_end(self, text): return len(text)

def oracles(): return {d:Stub(d) for d in r.DOMAIN}
def scores(ratio): return {d:t*ratio for d,t in zip(r.DOMAIN,r.THRESHOLDS)}

class R3Tests(unittest.TestCase):
    def test_r3_target_domain_all(self):
        value=json.loads((ROOT/'artifacts/research_protocol/r3/r3_predeclaration_v1.json').read_text())
        self.assertEqual(value['target_detector'],'ALL')
        self.assertEqual(tuple(value['attack_target_domain']),r.DOMAIN)
    def test_r3_success_requires_all_three_benign(self):
        self.assertTrue(r.success(scores(.9),reversible=True))
        self.assertFalse(r.success(scores(.9),reversible=False))
        for detector,threshold in zip(r.DOMAIN,r.THRESHOLDS):
            mixed=scores(.9); mixed[detector]=threshold
            self.assertFalse(r.success(mixed,reversible=True))
    def direction(self,i):
        low=scores(.5); high=dict(low); high[r.DOMAIN[i]]=r.THRESHOLDS[i]*1.1
        self.assertLess(r.operational_margins(low)[i],0)
        self.assertGreater(r.operational_margins(high)[i],0)
    def test_r3_margin_direction_ds(self): self.direction(0)
    def test_r3_margin_direction_dmb(self): self.direction(1)
    def test_r3_margin_direction_dg(self): self.direction(2)
    def test_r3_objective_deterministic(self):
        s=scores(.7); self.assertEqual(r.objective(s),r.objective(dict(reversed(list(s.items())))))
        self.assertEqual(r.generate_synthetic('Example ordinary words here.',oracles()),r.generate_synthetic('Example ordinary words here.',oracles()))
    def test_r3_query_budget_enforced(self):
        e=r.CandidateEvaluator(oracles(),limit=1); e.query('a','TEST'); e.query('a','CACHE')
        with self.assertRaisesRegex(ValueError,'BUDGET'): e.query('b','TEST')
        self.assertEqual(e.budget.individual_queries,3)
        self.assertEqual(e.budget.candidate_evaluations,1)
        result=r.generate_synthetic(' '.join('exampleword'+str(i) for i in range(30)),oracles())
        self.assertLessEqual(result['candidate_evaluations'],61)
        self.assertEqual(result['individual_detector_queries'],3*result['candidate_evaluations'])
    def test_r3_operator_registry_frozen(self):
        self.assertEqual(r.OPERATORS,r.legacy.OPERATORS)
        with self.assertRaises(ValueError): r.edit('example',(0,7),'TRANSLATE')
    def test_r3_inverse_reconstruction(self):
        parent='Example café\r\nordinary Unicode 😀 words.'
        for op in r.OPERATORS:
            script=dict(edits=[r.edit(parent,(0,7),op)],prefix=r.legacy.PREFIXES[0],suffix='')
            self.assertEqual(r.inverse(r.render(parent,script),script),parent.encode('utf-8'))
        result=r.generate_synthetic(parent,oracles())
        self.assertEqual(r.inverse(result['text'],result['script']),parent.encode('utf-8'))
    def test_r3_lineage_inheritance(self):
        p=dict(sample_id='p',lineage_id='L',source='S',dataset_id='D',dataset_revision='rev',attack_family='F')
        c=r.inherit_lineage(p,'c'); self.assertEqual(c['lineage_id'],'L'); self.assertEqual(c['parent_sample_id'],'p')
    def test_r3_no_authoritative_queries_in_preparation(self):
        os=oracles(); os['D_S'].evidence_kind='AUTHORITATIVE'
        with self.assertRaisesRegex(ValueError,'AUTHORITATIVE'): r.CandidateEvaluator(os)
        self.assertEqual(os['D_S'].calls,0)
        self.assertEqual(r.AUTHORITATIVE_QUERIES,dict.fromkeys(r.DOMAIN,0))
    def test_r3_predeclaration_serialization(self):
        for path in (ROOT/'artifacts/research_protocol/r3').glob('*.json'):
            v=json.loads(path.read_text()); self.assertEqual(json.loads(r.canonical_json(v)),v)
    def test_r3_protocol_patch_compatible(self):
        from detection_service.research_protocol.protocol_patch_001 import validate_domains
        m=SimpleNamespace(threat_regime='R3_ENSEMBLE_TARGETED',samples=[SimpleNamespace(target_detector='ALL')])
        self.assertEqual(validate_domains(m).attack_target_domain,r.DOMAIN)
    def test_non_ok_aborts_and_charges_attempt(self):
        class Broken(Stub):
            def __call__(self,text): return {'status':'ERROR'}
        os=oracles(); os['D_M-B']=Broken('D_M-B'); e=r.CandidateEvaluator(os)
        with self.assertRaisesRegex(ValueError,'NON_OK'): e.query('x','TEST')
        self.assertEqual(e.budget.individual_queries,2)
        self.assertEqual(os['D_G'].calls,0)
        with self.assertRaisesRegex(ValueError,'ABORTED'): e.query('x','TEST')
    def test_seed_selection_balanced_independent_and_lineage_unique(self):
        ps=[dict(sample_id=str(i),source='A' if i<5 else 'B',lineage_id='L'+str(i//2),
                 truth_label=1,partition='INTERNAL_TEST',threat_regime='R1_SHIFTED_UNSEEN') for i in range(10)]
        ds={p['sample_id']:dict(zip(r.DOMAIN,('ATTACK','BENIGN','BENIGN'))) for p in ps}
        a=r.select_seeds(ps,ds,limit=4); b=r.select_seeds(list(reversed(ps)),ds,limit=4)
        self.assertEqual(a,b); self.assertEqual(len({p['lineage_id'] for p in a}),len(a))
        self.assertEqual([p['source'] for p in a[:2]],['A','B'])
    def test_invalid_score_rejected(self):
        for value in (float('nan'),float('inf'),-1,True):
            s=scores(.5); s['D_S']=value
            with self.assertRaises(ValueError): r.objective(s)

if __name__ == '__main__': unittest.main()
