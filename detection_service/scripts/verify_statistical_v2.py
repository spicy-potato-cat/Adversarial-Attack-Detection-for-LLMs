"""Verification-only correction of an invalid empty synthetic smoke fixture."""

import argparse
from unittest.mock import patch

from detection_service.app.contracts.detection_request import DetectionContent
from detection_service.scripts import freeze_statistical_v2 as frozen

ALLOWED = {"", "Summarize tomorrow's engineering meeting agenda.",
           "Please review this short synthetic request and list its key words."}


def synthetic_content(**kwargs):
    if kwargs.get("text") not in ALLOWED:
        raise ValueError("Adapter accepts only the declared synthetic smoke fixtures")
    # The public contract forbids empty strings; 'x' is a valid one-token input.
    return DetectionContent(**{**kwargs, "text": "x" if kwargs["text"] == "" else kwargs["text"]})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("smoke", "cal-smoke"), required=True)
    calibrated = parser.parse_args().mode == "cal-smoke"
    with patch.object(frozen, "DetectionContent", side_effect=synthetic_content):
        frozen.smoke(calibrated)
    directory = frozen.CAL if calibrated else frozen.FINAL
    frozen.write(directory / "verification_adapter_v1.json", {
        "status": "PASS", "scope": "Synthetic fixture correction only; no model/scorer/reference/calibrator changes or fits.",
        "initial_smoke_failure": "The contract rejected empty text before inference. No smoke acceptance file was emitted.",
        "replacement": "Valid one-token synthetic string x, preserving insufficient-input coverage.",
        "frozen_training_code_commit": frozen.read(frozen.FINAL / frozen.TRAINING_FILE)["code_commit"],
        "verification_code_sha256": {"detection_service/scripts/verify_statistical_v2.py": frozen.file_hash(frozen.ROOT / "detection_service/scripts/verify_statistical_v2.py")},
        "smoke_sha256": frozen.file_hash(directory / "synthetic_smoke_v1.json"), "calibrated": calibrated})


if __name__ == "__main__":
    main()
