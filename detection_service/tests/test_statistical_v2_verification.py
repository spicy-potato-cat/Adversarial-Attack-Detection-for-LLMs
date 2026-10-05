"""Verification fixture adaptation cannot alter project inputs or training code."""

import pytest

from detection_service.app.contracts.detection_request import DetectionContent
from detection_service.scripts import verify_statistical_v2 as verifier


@pytest.mark.parametrize("text", sorted(verifier.ALLOWED))
def test_adapter_returns_real_validated_contract(text):
    result = verifier.synthetic_content(type="user_prompt", text=text)
    assert isinstance(result, DetectionContent)
    assert result.text == ("x" if text == "" else text)


def test_adapter_cannot_transform_project_input():
    with pytest.raises(ValueError, match="synthetic"):
        verifier.synthetic_content(type="user_prompt", text="Any undeclared project prompt")


def test_frozen_training_code_and_model_remain_intact():
    driver = verifier.frozen
    p = driver.checked()
    driver.baseline.verify_hashes(driver.ROOT, p["code_sha256"])
    driver.B2Model.load(driver.FINAL)
