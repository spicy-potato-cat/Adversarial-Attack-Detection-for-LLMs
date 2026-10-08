"""Model-free generator validation, always under non-target access poisoning."""

import ast
from copy import deepcopy

import pytest

from detection_service.research_protocol import r2_ds_design as d, r2_ds_generator as g
from detection_service.research_protocol import r2_ds_generate_run as run, r2_ds_predeclare as p

TEXT='ordinary testing content contains sample words across this routine language fixture'


class FakeTarget:
    detector_id='ds_v2'

    def __init__(self,function=None):
        self.function=function or (lambda text:.8)
        self.calls=[]

    def __call__(self,text):
        self.calls.append(text)
        return dict(status='OK',calibrated_score=float(self.function(text)),input_tokens=len(text),tokens_analyzed=min(256,len(text)),truncated=len(text)>256)

    def coverage_end(self,text):
        return len(text)


@pytest.fixture(autouse=True)
def poison_untargeted():
    with run.target_isolation():
        yield


@pytest.mark.parametrize('operator',d.OPERATORS)
def test_r2_ds_inverse_reconstruction(operator):
    script=dict(edits=[g.edit(TEXT,(0,8),operator)],prefix=d.PREFIXES[1],suffix='')
    candidate=g.render(TEXT,script)
    assert g.inverse(candidate,script)==TEXT.encode('utf-8')
    assert candidate.encode('utf-8').decode('utf-8')==candidate


def test_r2_ds_no_payload_deletion():
    script=dict(edits=[g.edit(TEXT,(0,8),'DOT_INTERLEAVE')],prefix='',suffix='')
    script['edits'][0]['replacement']=''
    with pytest.raises(ValueError):
        g.render(TEXT,script)


def test_r2_ds_tampered_inverse_fails():
    script=dict(edits=[g.edit(TEXT,(0,8),'ALT_CASE')],prefix='',suffix='')
    with pytest.raises(ValueError):
        g.inverse('deleted payload',script)


def test_r2_ds_deterministic_word_spans():
    text='https://example.test ordinary name@example.com /folder/path standalone_thing sample-word 123letters safe'
    spans=g.word_spans(text,len(text))
    words=[text[a:b] for a,b in spans]
    assert 'ordinary' in words and 'safe' in words
    assert 'example' not in words and 'folder' not in words and 'letters' not in words
    assert all(b<=20 for a,b in g.word_spans(text,20))
    assert g.word_spans('/example/path',13)==[(1,8),(9,13)]


def test_r2_ds_saliency_limit_16():
    spans=[(i,i+1) for i in range(100)]
    selected=g.evenly_spaced(spans)
    assert len(selected)==16 and selected[0]==spans[0] and selected[-1]==spans[-1]
    assert len(set(selected))==16 and selected==g.evenly_spaced(spans)


def test_r2_ds_mutation_limit_8():
    result=g.generate(('routine language content sample '*10).strip(),FakeTarget())
    assert result['saliency_spans']==16 and result['ranked_spans']==8


def test_r2_ds_deterministic_saliency_order():
    result=g.generate(TEXT,FakeTarget())
    assert all(r['saliency']==0 for r in result['saliency'])
    assert [r['span'][0] for r in result['saliency']]==sorted(r['span'][0] for r in result['saliency'])


def test_r2_ds_deterministic_tie_break():
    oracle=FakeTarget(lambda text:.8 if text==TEXT else .0001)
    result=g.generate(TEXT,oracle)
    assert result['success'] and result['mechanism']=='ALT_CASE'
    assert result['script']['edits'][0]['start']==0


def test_r2_ds_query_budget_61():
    oracle=FakeTarget()
    result=g.generate(('routine language content sample '*10).strip(),oracle)
    assert result['unique_model_queries']==len(oracle.calls)<=61
    assert result['logical_queries']<=61
    assert len(oracle.calls)==len(set(oracle.calls))


def test_r2_ds_exact_query_cap_enforced():
    cache=g.QueryCache(FakeTarget())
    for i in range(61):
        cache.query('routine fixture '+str(i),'TEST')
    with pytest.raises(ValueError,match='QUERY_BUDGET_EXCEEDED'):
        cache.query('one additional unique fixture','TEST')
    cache.query('routine fixture 0','TEST')
    assert len(cache.cache)==61 and cache.logical_queries==63


def test_r2_ds_cached_duplicate_queries():
    target=FakeTarget()
    cache=g.QueryCache(target)
    assert cache.query(TEXT,'BASELINE')==cache.query(TEXT,'OTHER')
    assert len(target.calls)==1 and cache.logical_queries==2


def test_r2_ds_empty_spans():
    result=g.generate('123',FakeTarget())
    assert result['eligible_spans']==result['ranked_spans']==0
    assert result['unique_model_queries']<=9
    assert g.inverse(result['text'],result['script'])==b'123'


def test_r2_ds_confusable_not_applicable():
    assert g.mutation('bdfg','CONFUSABLE_FIRST') is None
    assert g.mutation('Abcd','CONFUSABLE_FIRST')=='\u0410bcd'


def test_r2_ds_global_from_original_only():
    target=FakeTarget(lambda text:.0001 if text.count('\u200b')>12 else .8)
    result=g.generate(TEXT,target)
    assert result['mechanism']=='GLOBAL_ZERO_WIDTH_INTERLEAVE'
    assert not result['script']['prefix'] and not result['script']['suffix']
    assert set(r['operator'] for r in result['script']['edits'])=={'ZERO_WIDTH_INTERLEAVE'}


def test_r2_ds_padding_success_tie():
    target=FakeTarget(lambda text:.0001 if text.startswith(d.PREFIXES) or text.endswith(d.SUFFIXES) else .8)
    result=g.generate(TEXT,target)
    assert result['mechanism']=='BENIGN_CONTEXT_PADDING'
    choices=[(len(t.encode('utf-8')),side,i,t) for side,items in enumerate((d.PREFIXES,d.SUFFIXES)) for i,t in enumerate(items)]
    _,side,_,padding=min(choices)
    assert result['script']['prefix' if side==0 else 'suffix']==padding
    assert result['text'].count(TEXT)==1


def test_r2_ds_generation_deterministic():
    assert g.generate(TEXT,FakeTarget())==g.generate(TEXT,FakeTarget())


@pytest.mark.parametrize('label',['D_M-B','D_G'])
def test_r2_ds_no_untargeted_adapter_creation(label):
    from detection_service.research_protocol.adapters import DetectorAdapter
    with pytest.raises(ValueError,match='TARGET_ISOLATION'):
        DetectorAdapter(label,object())


@pytest.mark.parametrize('detector',['dm_b_v1','dg_v1','ensemble'])
def test_r2_ds_no_untargeted_or_ensemble_oracle(detector):
    target=FakeTarget()
    target.detector_id=detector
    with pytest.raises(ValueError,match='TARGET_ISOLATION'):
        g.generate(TEXT,target)


def test_r2_ds_generator_dependency_boundary():
    source=(p.ROOT/'detection_service/research_protocol/r2_ds_generator.py').read_text(encoding='utf-8')
    imports=[ast.unparse(node) for node in ast.walk(ast.parse(source)) if isinstance(node,(ast.Import,ast.ImportFrom))]
    assert not any(name in '\n'.join(imports) for name in ('adapters','ds_runtime','guard','common_mode','r1_scoring','r1_analysis'))


def test_r2_ds_non_ok_stops_generation():
    target=FakeTarget()
    class Broken(FakeTarget):
        def __call__(self,text):
            return dict(status='UNAVAILABLE',calibrated_score=None)
    with pytest.raises(ValueError,match='NON_OK'):
        g.generate(TEXT,Broken())


def test_r2_ds_target_baseline_detected_required():
    with pytest.raises(ValueError,match='SEED_MISMATCH'):
        g.generate(TEXT,FakeTarget(lambda text:.0001))


def test_r2_ds_unicode_byte_exact():
    parent='ordinary caf\u00e9 \U0001f600 routine fixture'
    result=g.generate(parent,FakeTarget())
    assert g.inverse(result['text'],result['script'])==parent.encode('utf-8')


def test_ds_probes_are_reversible_case_edits():
    target=FakeTarget()
    result=g.generate(TEXT,target)
    probes=[q for q in result['query_trace'] if q['stage']=='SALIENCY']
    allowed={g.sha(g.render(TEXT,dict(edits=[g.edit(TEXT,r['span'],'ALT_CASE')],prefix='',suffix=''))) for r in result['saliency']}
    assert {q['candidate_id'] for q in probes}==allowed
    assert all('calibrated_score' in q and 'raw_score' not in q for q in result['query_trace'])


@pytest.mark.parametrize('module',['detection_service.app.detectors.semantic','detection_service.app.detectors.guard','detection_service.research_protocol.common_mode','detection_service.research_protocol.r1_scoring'])
def test_ds_isolation_blocks_untargeted_imports(module):
    with pytest.raises(ValueError,match='UNTARGETED_GENERATION_IMPORT'):
        __import__(module)

