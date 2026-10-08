"""Native-output adapter scaffolding and recovery on synthetic frozen fixtures."""
from dataclasses import asdict, dataclass
import hashlib
import json
import math
import re

REVISIONS = {'V1':'a8ded8e697ce7c355e395a0df51f94adb4a2fd27',
 'V2':'90c9989b1a342275dd0d1a95aad283c04e075671',
 'V3':'3de033d89b499a18d9a573b5192bf3b967ef48c5'}
AUTHORITATIVE_QUERIES = 0

def require(condition, code):
    if not condition: raise ValueError(code)
def canonical(v):
    return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('utf-8')
def digest(v): return hashlib.sha256(canonical(v)).hexdigest()

@dataclass(frozen=True)
class FailureSample:
    sample_id: str
    lineage_id: str
    regime: str
    source: str
    attack_family: str
    parent_sample_id: str
    text: str
    truth_label: int = 1
    base_decisions: tuple = ('BENIGN','BENIGN','BENIGN')
    partition: str = 'SYNTHETIC_ONLY'

@dataclass(frozen=True)
class FailurePopulation:
    samples: tuple
    membership_sha256: str
    evidence_kind: str = 'SYNTHETIC_FIXTURE'
    frozen: bool = True

    def __post_init__(self):
        require(self.frozen is True and self.evidence_kind == 'SYNTHETIC_FIXTURE', 'VERIFIER_PREPARATION_ONLY')
        require(type(self.samples) is tuple and all(type(s) is FailureSample for s in self.samples), 'VERIFIER_IMMUTABLE_SAMPLES_REQUIRED')
        require(len({s.sample_id for s in self.samples}) == len(self.samples), 'VERIFIER_DUPLICATE_SAMPLE')
        for s in self.samples:
            require(s.truth_label == 1 and s.base_decisions == ('BENIGN',)*3, 'VERIFIER_BASE_FAILURE_REQUIRED')
            require(bool(s.sample_id and s.lineage_id and s.regime and s.source and s.parent_sample_id), 'VERIFIER_LINEAGE_METADATA_REQUIRED')
            require(s.partition == 'SYNTHETIC_ONLY', 'VERIFIER_PROTECTED_OR_REAL_POPULATION_REJECTED')
        require(self.membership_sha256 == digest([asdict(s) for s in self.samples]), 'VERIFIER_MEMBERSHIP_HASH_MISMATCH')

def synthetic_population(samples):
    rows=tuple(sorted(samples,key=lambda s:s.sample_id))
    return FailurePopulation(rows,digest([asdict(s) for s in rows]))

def load_failure_fixture(payload):
    """In-memory interface only; intentionally no filesystem population loader."""
    require(payload.get('evidence_kind') == 'SYNTHETIC_FIXTURE', 'VERIFIER_PREPARATION_ONLY')
    rows=tuple(FailureSample(**dict(s,base_decisions=tuple(s['base_decisions']))) for s in payload['samples'])
    return FailurePopulation(rows,payload['membership_sha256'])

@dataclass(frozen=True)
class VerifierPrediction:
    sample_id: str
    verifier_id: str
    model_revision: str
    raw_score: float | None
    normalized_probability: float | None
    probability_semantics: str
    decision: str | None
    status: str
    input_coverage: float
    truncation: bool
    latency_ms: float
    lineage_id: str
    regime: str
    provenance: dict
    evidence_kind: str = 'SYNTHETIC_FIXTURE'

    def __post_init__(self):
        require(self.evidence_kind == 'SYNTHETIC_FIXTURE', 'VERIFIER_PREPARATION_ONLY')
        require(self.verifier_id in REVISIONS and self.model_revision == REVISIONS[self.verifier_id], 'VERIFIER_REVISION_MISMATCH')
        require(bool(self.sample_id and self.lineage_id and self.regime), 'VERIFIER_METADATA_REQUIRED')
        require(self.status in ('OK','ERROR','INVALID_OUTPUT','INPUT_LIMIT_EXCEEDED'), 'VERIFIER_INVALID_STATUS')
        require((self.decision in ('ATTACK','BENIGN')) if self.status == 'OK' else self.decision is None, 'VERIFIER_STATUS_DECISION_CONFLICT')
        require(type(self.truncation) is bool and type(self.provenance) is dict, 'VERIFIER_INVALID_METADATA')
        for value in (self.input_coverage,self.latency_ms):
            require(type(value) in (int,float) and math.isfinite(value) and value >= 0, 'VERIFIER_INVALID_NUMERIC')
        require(self.input_coverage <= 1, 'VERIFIER_INVALID_COVERAGE')
        require(self.probability_semantics in ('NATIVE_CLASS_SOFTMAX','UNAVAILABLE'), 'VERIFIER_PROBABILITY_SEMANTICS')
        if self.raw_score is not None:
            require(type(self.raw_score) in (int,float) and math.isfinite(self.raw_score), 'VERIFIER_INVALID_SCORE')
        if self.normalized_probability is not None:
            require(type(self.normalized_probability) in (int,float) and math.isfinite(self.normalized_probability) and 0 <= self.normalized_probability <= 1, 'VERIFIER_INVALID_PROBABILITY')
        require(self.probability_semantics != 'UNAVAILABLE' or self.normalized_probability is None, 'VERIFIER_FABRICATED_PROBABILITY')

class NativeOutputAdapter:
    evidence_kind = 'SYNTHETIC_FIXTURE'
    def __init__(self, verifier_id, supplied_outputs):
        require(verifier_id in REVISIONS, 'VERIFIER_UNKNOWN_ID')
        self.verifier_id, self.supplied_outputs = verifier_id, dict(supplied_outputs)

    def load_model(self):
        raise ValueError('VERIFIER_AUTHORITATIVE_EXECUTION_STOP_LINE')

    def predict(self, sample):
        native = self.supplied_outputs[sample.sample_id]
        common=dict(sample_id=sample.sample_id,verifier_id=self.verifier_id,
            model_revision=REVISIONS[self.verifier_id],lineage_id=sample.lineage_id,regime=sample.regime,
            latency_ms=native['latency_ms'],input_coverage=native['input_coverage'],truncation=native['truncation'],
            provenance={'native_output':native,'adapter':'supplied_output_only_v1','source':sample.source,'attack_family':sample.attack_family,'parent_sample_id':sample.parent_sample_id})
        if native.get('status','OK') != 'OK':
            return VerifierPrediction(**common,status=native['status'],decision=None,raw_score=None,
                normalized_probability=None,probability_semantics='UNAVAILABLE')
        if self.verifier_id in ('V1','V2'):
            chunks=native['chunk_probabilities']
            require(bool(chunks), 'VERIFIER_EMPTY_CHUNKS')
            require(all(type(p) in (float,int) and math.isfinite(p) and 0 <= p <= 1 for p in chunks), 'VERIFIER_INVALID_CHUNK_PROBABILITY')
            p=max(chunks)
            return VerifierPrediction(**common,status='OK',decision='ATTACK' if p > .5 else 'BENIGN',
                raw_score=p,normalized_probability=p,probability_semantics='NATIVE_CLASS_SOFTMAX')
        token=native['first_token'].strip().lower()
        return VerifierPrediction(**common,status='OK' if token in ('yes','no') else 'INVALID_OUTPUT',
            decision={'yes':'ATTACK','no':'BENIGN'}.get(token),raw_score=None,
            normalized_probability=None,probability_semantics='UNAVAILABLE')

def run_synthetic_batch(population, adapter):
    require(type(population) is FailurePopulation, 'VERIFIER_FROZEN_FAILURE_POPULATION_REQUIRED')
    require(type(adapter) is NativeOutputAdapter and adapter.evidence_kind == 'SYNTHETIC_FIXTURE', 'VERIFIER_PREPARATION_ONLY')
    return tuple(adapter.predict(s) for s in population.samples)

def recovery(population, predictions, verifier_id, *, regime=None):
    require(type(population) is FailurePopulation, 'VERIFIER_FROZEN_FAILURE_POPULATION_REQUIRED')
    require(verifier_id in REVISIONS, 'VERIFIER_UNKNOWN_ID')
    all_samples={s.sample_id:s for s in population.samples}
    rows={}
    for p in predictions:
        require(type(p) is VerifierPrediction and p.verifier_id == verifier_id, 'VERIFIER_PREDICTION_ID_CONFLICT')
        require(p.sample_id in all_samples and p.sample_id not in rows, 'VERIFIER_DUPLICATE_OR_UNKNOWN_PREDICTION')
        s=all_samples[p.sample_id]
        require(p.lineage_id == s.lineage_id and p.regime == s.regime, 'VERIFIER_LINEAGE_OR_REGIME_CONFLICT')
        rows[p.sample_id]=p
    ids={s.sample_id for s in population.samples if regime is None or s.regime == regime}
    n=len(ids)
    complete=[rows[i] for i in ids if i in rows and rows[i].status == 'OK' and rows[i].input_coverage == 1 and not rows[i].truncation]
    detected=sum(p.decision == 'ATTACK' for p in complete)
    status='UNDEFINED_EMPTY_FAILURE_POPULATION' if n == 0 else 'COMPLETE' if len(complete) == n else 'INCOMPLETE'
    return dict(verifier_id=verifier_id,regime=regime,population_sha256=population.membership_sha256,
        denominator=n,detected=detected,complete_predictions=len(complete),status=status,
        recovery=detected/n if status == 'COMPLETE' else None,
        detected_fraction_lower_bound=detected/n if n else None,
        complete_case_recovery=detected/len(complete) if complete else None)
