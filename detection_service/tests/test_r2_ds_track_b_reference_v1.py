"""The approved branch-reference update cannot change scientific bindings."""

import inspect

import pytest

from detection_service.research_protocol import r2_ds_track_b_reference_v1 as ref
from detection_service.research_protocol import r2_ds_completed_journal_acceptance_v2 as acceptance


def test_approved_reference_restores_runtime_constant():
    before = ref.numerical.TRACK_B
    with ref.approved_reference():
        assert ref.numerical.TRACK_B == ref.APPROVED
    assert ref.numerical.TRACK_B == before


def test_reference_update_is_explicit_and_not_scientific():
    receipt = ref.verified()
    assert receipt['disposition'] == 'EXTERNAL_BRANCH_ADVANCEMENT_ACCEPTED_FOR_FINAL_GIT_GATE'
    assert not receipt['scientific_protocol_changed']
    assert not receipt['generation_receipts_rewritten']


def test_unapproved_reference_is_rejected(monkeypatch):
    receipt = dict(ref.verified(), approved_untouched_reference='0' * 40)
    monkeypatch.setattr(ref.p.files, 'read_json', lambda path: receipt)
    with pytest.raises(ValueError, match='TRACK_B_REFERENCE_NOT_AUTHORIZED'):
        ref.verified()


def test_completed_journal_acceptance_has_no_generation_or_predict_call():
    source = inspect.getsource(acceptance.run)
    assert 'generate(' not in source and '.predict(' not in source
    assert 'len(entries) == len(parents) == 698' in source
    assert "'SCIENTIFIC_BINDING_DRIFT'" in source


def test_original_run_code_hash_is_checked_before_publication():
    source = inspect.getsource(acceptance.run)
    assert source.index("'RUN_CODE_DRIFT'") < source.index('p.publish(')
    assert source.index("'SCIENTIFIC_GENERATION_INTERRUPTED'") < source.index('p.publish(')
