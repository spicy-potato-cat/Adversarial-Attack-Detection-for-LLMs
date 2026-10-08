"""Deterministic reversible search; accepts only a D_S calibrated-score oracle."""

import hashlib
import math
import re
from copy import deepcopy

from detection_service.research_protocol import r2_ds_design as d


def sha(text):
    return hashlib.sha256(text.encode('utf-8',errors='strict')).hexdigest()


def require(condition,code):
    if not condition:
        raise ValueError(code)


def word_spans(text,coverage_end):
    ordinary=[(m.start(),m.end()) for m in re.finditer(d.DESIGN['span_regex'],text) if m.end()<=coverage_end]
    excluded=d.DESIGN['excluded_adjacent_characters']
    def standalone(a,b):
        neighbours=(text[a-1] if a else '',text[b] if b<len(text) else '')
        return not any(c and (c.isalnum() or c in excluded) for c in neighbours)
    selected=[(a,b) for a,b in ordinary if standalone(a,b)]
    return selected or ordinary


def evenly_spaced(spans,limit=16):
    require(limit==16,'FROZEN_SALIENCY_LIMIT')
    if len(spans)<=limit:
        return list(spans)
    indexes=dict.fromkeys((2*i*(len(spans)-1)+limit-1)//(2*(limit-1)) for i in range(limit))
    return [spans[i] for i in indexes]


def mutation(word,operator):
    require(operator in d.OPERATORS,'FROZEN_OPERATOR_REGISTRY')
    if operator=='ALT_CASE':
        return ''.join(c.upper() if i%2==0 else c.lower() for i,c in enumerate(word))
    if operator=='CONFUSABLE_FIRST':
        for i,c in enumerate(word):
            if c in d.CONFUSABLES:
                return word[:i]+d.CONFUSABLES[c]+word[i+1:]
        return None
    return ('\u200b' if operator=='ZERO_WIDTH_INTERLEAVE' else '.').join(word)


def edit(parent,span,operator):
    a,b=span
    word=parent[a:b]
    replacement=mutation(word,operator)
    if replacement is None:
        return None
    return dict(start=a,end=b,original=word,replacement=replacement,operator=operator,
        insertion_offsets=list(range(1,len(word))) if operator in ('ZERO_WIDTH_INTERLEAVE','DOT_INTERLEAVE') else [])


def render(parent,script):
    cursor=0
    parts=[]
    for row in sorted(script['edits'],key=lambda r:r['start']):
        require(cursor<=row['start']<row['end']<=len(parent),'OVERLAPPING_OR_INVALID_EDIT')
        require(parent[row['start']:row['end']]==row['original'],'ORIGINAL_EDIT_SPAN_CONFLICT')
        require(edit(parent,(row['start'],row['end']),row['operator'])==row,'INVALID_OPERATOR_EDIT')
        parts.extend((parent[cursor:row['start']],row['replacement']))
        cursor=row['end']
    parts.append(parent[cursor:])
    require(script['prefix'] in ('',*d.PREFIXES) and script['suffix'] in ('',*d.SUFFIXES),'UNAPPROVED_PADDING')
    require(not(script['prefix'] and script['suffix']),'COMBINED_PADDING_FORBIDDEN')
    return script['prefix']+''.join(parts)+script['suffix']


def inverse(candidate,script):
    prefix,suffix=script['prefix'],script['suffix']
    require(prefix in ('',*d.PREFIXES) and suffix in ('',*d.SUFFIXES),'UNAPPROVED_PADDING')
    require(not(prefix and suffix),'COMBINED_PADDING_FORBIDDEN')
    require(candidate.startswith(prefix) and candidate.endswith(suffix),'PADDING_RECONSTRUCTION_CONFLICT')
    body=candidate[len(prefix):len(candidate)-len(suffix) if suffix else len(candidate)]
    shift=0
    adjusted=[]
    for row in sorted(script['edits'],key=lambda r:r['start']):
        a=row['start']+shift
        b=a+len(row['replacement'])
        require(body[a:b]==row['replacement'],'EDIT_RECONSTRUCTION_CONFLICT')
        adjusted.append((a,b,row['original']))
        shift+=len(row['replacement'])-(row['end']-row['start'])
    for a,b,word in reversed(adjusted):
        body=body[:a]+word+body[b:]
    require(render(body,script)==candidate,'INVERSE_ALLOWED_EDIT_VALIDATION_FAILED')
    return body.encode('utf-8',errors='strict')


class QueryCache:
    def __init__(self,oracle):
        require(getattr(oracle,'detector_id',None)==d.DETECTOR_ID,'BLOCKED_R2_TARGET_ISOLATION')
        self.oracle=oracle
        self.cache={}
        self.logical_queries=0
        self.trace=[]

    def query(self,text,stage):
        self.logical_queries+=1
        key=sha(text)
        cached=text in self.cache
        if not cached:
            require(len(self.cache)<61,'QUERY_BUDGET_EXCEEDED')
            result=self.oracle(text)
            require(result['status']=='OK','GENERATION_NON_OK')
            score=result['calibrated_score']
            require(type(score) is float and math.isfinite(score) and 0<=score<=1,'INVALID_CALIBRATED_TARGET_SCORE')
            self.cache[text]=result
        result=self.cache[text]
        self.trace.append(dict(stage=stage,candidate_id=key,cached=cached,calibrated_score=result['calibrated_score']))
        return result


def generate(parent,oracle):
    query=QueryCache(oracle)
    baseline=query.query(parent,'BASELINE')
    require(baseline['calibrated_score']>=d.THRESHOLD,'BLOCKED_R2_SEED_MISMATCH')
    coverage_end=oracle.coverage_end(parent)
    spans=word_spans(parent,coverage_end)
    probes=[]
    for span in evenly_spaced(spans):
        a,b=span
        probe=dict(edits=[edit(parent,span,'ALT_CASE')],prefix='',suffix='')
        text=render(parent,probe)
        require(inverse(text,probe)==parent.encode('utf-8'),'INVALID_REVERSIBLE_PROBE')
        score=query.query(text,'SALIENCY')['calibrated_score']
        probes.append(dict(span=span,saliency=baseline['calibrated_score']-score))
    ranked=sorted(probes,key=lambda r:(-r['saliency'],r['span'][0]))[:8]
    empty=dict(edits=[],prefix='',suffix='')
    current=(parent,empty,baseline,'UNCHANGED')
    def candidate(script,mechanism,stage):
        text=render(parent,script)
        require(inverse(text,script)==parent.encode('utf-8'),'INVALID_REVERSIBLE_CANDIDATE')
        return (text,script,query.query(text,stage),mechanism)
    def score(row):
        return row[2]['calibrated_score']
    for item in ranked:
        variants=[]
        seen=set()
        for priority,operator in enumerate(d.OPERATORS,1):
            change=edit(parent,item['span'],operator)
            if change is None:
                continue
            script=deepcopy(current[1])
            script['edits'].append(change)
            text=render(parent,script)
            if text in seen:
                continue
            seen.add(text)
            row=candidate(script,operator,'GREEDY')
            variants.append((row,priority))
        successful=[(row,priority) for row,priority in variants if score(row)<d.THRESHOLD]
        if successful:
            current=min(successful,key=lambda x:(x[1],score(x[0]),sha(x[0][0])))[0]
            break
        if variants:
            best=min(variants,key=lambda x:(score(x[0]),x[1],sha(x[0][0])))[0]
            if score(best)<score(current):
                current=best
    if score(current)>=d.THRESHOLD:
        variants=[]
        for side,paddings in enumerate((d.PREFIXES,d.SUFFIXES)):
            for number,padding in enumerate(paddings,1):
                script=deepcopy(current[1])
                script['prefix' if side==0 else 'suffix']=padding
                row=candidate(script,'BENIGN_CONTEXT_PADDING','PADDING')
                variants.append((row,len(padding.encode('utf-8')),side,number))
        successful=[v for v in variants if score(v[0])<d.THRESHOLD]
        if successful:
            current=min(successful,key=lambda v:(v[1],score(v[0]),v[2],v[3]))[0]
        else:
            current=min(variants,key=lambda v:(score(v[0]),v[2],v[3]))[0]
    if score(current)>=d.THRESHOLD:
        variants=[]
        for priority,operator in enumerate(d.OPERATORS,1):
            script=deepcopy(empty)
            script['edits']=[row for row in (edit(parent,span,operator) for span in spans) if row is not None]
            row=candidate(script,'GLOBAL_'+operator,'GLOBAL')
            variants.append((row,priority))
        successful=[v for v in variants if score(v[0])<d.THRESHOLD]
        if successful:
            current=min(successful,key=lambda v:(v[1],score(v[0])))[0]
        else:
            best=min(variants,key=lambda v:(score(v[0]),v[1]))[0]
            if score(best)<score(current):
                current=best
    text,script,terminal,mechanism=current
    require(inverse(text,script)==parent.encode('utf-8'),'INVALID_TERMINAL_RECONSTRUCTION')
    return dict(text=text,script=script,baseline=baseline,terminal=terminal,mechanism=mechanism,
        success=score(current)<d.THRESHOLD,logical_queries=query.logical_queries,unique_model_queries=len(query.cache),
        coverage_end=coverage_end,eligible_spans=len(spans),saliency_spans=len(probes),ranked_spans=len(ranked),
        saliency=probes,query_trace=query.trace,validity_status=d.DESIGN['validity'])
