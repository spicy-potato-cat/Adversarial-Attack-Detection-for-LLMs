"""Acceptance adapter plumbing; no classifier fitting or artifact writes."""

import pytest

from detection_service.scripts import statistical_feature_ablation_acceptance as acceptance


@pytest.mark.parametrize("fail", [False, True])
def test_canonical_helper_is_bound_and_restored(monkeypatch, fail):
    baseline = acceptance.resume.baseline
    monkeypatch.delattr(baseline, "digest_ids", raising=False)
    def checker():
        assert baseline.digest_ids is acceptance.digest_ids
        assert baseline.digest_ids([{"sample_id": "synthetic-a"}]) == acceptance.digest_ids([{"sample_id": "synthetic-a"}])
        if fail:
            raise ValueError("simulated check failure")
    monkeypatch.setattr(acceptance.resume, "check", checker)
    if fail:
        with pytest.raises(ValueError, match="simulated"):
            acceptance.check()
    else:
        acceptance.check()
    assert not hasattr(baseline, "digest_ids")


def test_conflicting_digest_is_rejected(monkeypatch):
    conflicting = lambda rows: "wrong"
    monkeypatch.setattr(acceptance.resume.baseline, "digest_ids", conflicting, raising=False)
    monkeypatch.setattr(acceptance.resume, "check", lambda: pytest.fail("must reject before verification"))
    with pytest.raises(ValueError, match="conflicting"):
        acceptance.check()
    assert acceptance.resume.baseline.digest_ids is conflicting
