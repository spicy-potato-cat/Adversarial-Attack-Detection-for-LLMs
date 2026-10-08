"""Model-free checks of durable transfer and recorded-feedback reconstruction."""

from copy import deepcopy
import inspect
import json

import pytest

from detection_service.research_protocol import r2_ds_completion_v2 as c
from detection_service.research_protocol import r2_ds_generator as g
from detection_service.research_protocol.r2_ds_operator_reconstruction_v2 import reconstruct

TEXT = 'ordinary testing content contains sample words across this routine language fixture'


def fixture(score):
    receipts = []

    class Oracle:
        detector_id = 'ds_v2'

        def coverage_end(self, text):
            return len(text)

        def __call__(self, text):
            result = dict(status='OK', calibrated_score=float(score(text)),
                          input_tokens=len(text), tokens_analyzed=len(text), truncated=False)
            receipts.append(dict(candidate_sha256=g.sha(text), **result))
            return result

    saved = json.loads(json.dumps(g.generate(TEXT, Oracle())))
    return saved, receipts


@pytest.mark.parametrize('value', [.8, .99])
def test_reconstruct_all_failed_stages(value):
    saved, receipts = fixture(lambda text: value)
    attempts = reconstruct(saved, receipts)
    assert len(attempts) == saved['logical_queries']
    assert sum(not row['cached'] for row in attempts) == len(receipts)
    assert {row['stage'] for row in attempts} == {'BASELINE', 'SALIENCY', 'GREEDY', 'PADDING', 'GLOBAL'}
    assert sum(row['stage'] == 'GLOBAL' for row in attempts) == 4


def test_reconstruction_early_evasion():
    saved, receipts = fixture(lambda text: .8 if text == TEXT else .01)
    attempts = reconstruct(saved, receipts)
    assert saved['success']
    assert not any(row['stage'] in ('PADDING', 'GLOBAL') for row in attempts)


def test_reconstruction_preserves_inputs():
    saved, receipts = fixture(lambda text: .8)
    before = deepcopy((saved, receipts))
    reconstruct(saved, receipts)
    assert (saved, receipts) == before


def test_reconstruction_rejects_changed_terminal():
    saved, receipts = fixture(lambda text: .8)
    saved['mechanism'] = 'UNAUTHORIZED'
    with pytest.raises(ValueError, match='OPERATOR_RECONSTRUCTION_CONFLICT'):
        reconstruct(saved, receipts)


def test_reconstruction_missing_receipt_fails():
    saved, receipts = fixture(lambda text: .8)
    with pytest.raises(KeyError):
        reconstruct(saved, receipts[1:])


def test_reconstruction_calls_no_model():
    source = inspect.getsource(reconstruct)
    assert 'adapter.predict' not in source and 'primary_adapters' not in source


def test_transfer_gate_before_adapter_construction():
    source = inspect.getsource(c.score_run)
    assert source.index('freeze.transfer_gate()') < source.index('adapters=primary_adapters()')


def test_transfer_return_persisted_before_assertion():
    source = inspect.getsource(c.score_run)
    assert source.index('durable_native(stream,row)') < source.index("p.require(row.status=='OK'")
    assert source.index('query.score(') < source.index('durable_native(stream,row)')


def test_durable_native_flushes_and_fsyncs(monkeypatch):
    events = []

    class Stream:
        def write(self, data):
            events.append(('write', data))

        def flush(self):
            events.append(('flush',))

        def fileno(self):
            return 99

    class Row:
        def deterministic_json(self):
            return '{"status":"OK"}'

    monkeypatch.setattr(c.os, 'fsync', lambda fd: events.append(('fsync', fd)))
    c.durable_native(Stream(), Row())
    assert events == [('write', b'{"status":"OK"}\n'), ('flush',), ('fsync', 99)]
