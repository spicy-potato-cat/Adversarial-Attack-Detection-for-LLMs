"""Post-freeze real CPU synthetic edge/API checks; never read development text."""
import json
from pathlib import Path

import torch
from fastapi.testclient import TestClient

from detection_service.app.contracts.detector_result import DetectorResult
from detection_service.app.core.settings import Settings
from detection_service.app.detectors.statistical.config import PerplexityConfig
from detection_service.app.main import create_app
from detection_service.scripts.train_statistical_risk import check_preserved, config, MODEL, write


def main():
    torch.set_num_threads(8)
    torch.use_deterministic_algorithms(True)
    cases = {
        "short": "Summarize the engineering agenda.",
        "unicode": "A Unicode engineering note: caf\u00e9 \u03bb \u4f60\u597d.",
        "long": "agenda " * 4500,
    }
    settings = Settings("ds_v1_engineering", PerplexityConfig(), statistical_model_dir=str(MODEL))
    app = create_app(settings)  # Exercise the real default factory, not injection.
    results = {}
    with TestClient(app) as client:
        assert len(app.state.detectors) == 1
        detector = app.state.detectors[0]
        identities = (id(detector.extractor.engine.model), id(detector.scorer), id(detector.calibrator))
        for name, text in cases.items():
            payload = {"request_id": "ds-edge-smoke", "content": {"type": "user_prompt", "text": text}}
            first = client.post("/v1/detect/input", json=payload)
            second = client.post("/v1/detect/input", json=payload)
            assert first.status_code == second.status_code == 200
            a, b = first.json()["detectors"][0], second.json()["detectors"][0]
            for key in ("raw_score", "calibrated_probability", "binary_vote", "features", "input_coverage"):
                assert a[key] == b[key]
            assert a["detector_version"] == "ds_v1" and a["status"] == "success"
            assert 0 <= a["raw_score"] <= 1 and 0 <= a["calibrated_probability"] <= 1
            assert a["binary_vote"] == (a["calibrated_probability"] >= .5)
            DetectorResult.model_validate(a)
            if name == "long":
                coverage = a["input_coverage"]
                assert coverage["input_tokens"] > 4096 and coverage["truncated"]
                assert coverage["tokens_analyzed"] == 4095 and coverage["inference_chunks"] > 1
                assert "INPUT_TRUNCATED_TO_CONFIGURED_MAX_ANALYSIS_TOKENS" in a["warnings"]
            results[name] = a
        assert identities == (id(detector.extractor.engine.model), id(detector.scorer), id(detector.calibrator))
        empty = client.post("/v1/detect/input", json={"request_id": "empty", "content": {"type": "user_prompt", "text": " "}})
        assert empty.status_code == 422
    check_preserved(config())
    write(MODEL / "extended_smoke.json", {"status": "PASS", "scope": "REAL CPU SYNTHETIC ENGINEERING ONLY",
                                         "default_factory": "PASS", "repeat_deterministic": True, "model_reuse": True,
                                         "cases": results, "whitespace_rejection_http_status": 422,
                                         "project_text_used": False, "protected_data_used": False})
    print(json.dumps({"status": "PASS", "default_factory": "PASS", "cases": list(cases), "long_tokens": results["long"]["input_coverage"]["input_tokens"]}))


if __name__ == "__main__":
    main()
