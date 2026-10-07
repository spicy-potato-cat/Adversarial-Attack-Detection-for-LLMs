"""Explicit loading of accepted D_S archive bytes; no frozen file is restored in place."""

import importlib.util
from pathlib import Path
import shutil
import sys
import tempfile

from detection_service.research_protocol import detector_semantics as files
from detection_service.research_protocol import protocol_lock
from detection_service.research_protocol.adapters import DetectorAdapter, FrozenDetectorContracts
from detection_service.research_protocol.regime import require

PACKAGE = "_exp_protocol_001_frozen_ds_v2"
BINDING = files.OUT + "/runtime/ds_v2_runtime_binding_v1.json"
EQUIVALENCE = files.OUT + "/runtime/ds_v2_equivalence_evidence_v1.json"


def archived_package(identity):
    directory = (files.ROOT / identity["implementation_path"]).parent
    inventory = files.read_json(files.ROOT / files.OUT / files.NAME)["accepted_evidence_locations"]
    for name in ("__init__.py", "model.py", "detector.py"):
        logical = "detection_service/app/detectors/statistical_v2/" + name
        require(files.sha(directory / name) == inventory[logical]["sha256"], "DS_ARCHIVED_IMPLEMENTATION_DRIFT")
    if PACKAGE in sys.modules:
        require(Path(sys.modules[PACKAGE].__file__).resolve() == (directory / "__init__.py").resolve(), "DS_PACKAGE_ALIAS_CONFLICT")
        return sys.modules[PACKAGE]
    spec = importlib.util.spec_from_file_location(PACKAGE, directory / "__init__.py",
        submodule_search_locations=[str(directory)])
    module = importlib.util.module_from_spec(spec)
    sys.modules[PACKAGE] = module
    previous = sys.dont_write_bytecode
    try:
        sys.dont_write_bytecode = True
        spec.loader.exec_module(module)
    except BaseException:
        for key in list(sys.modules):
            if key == PACKAGE or key.startswith(PACKAGE + "."):
                del sys.modules[key]
        raise
    finally:
        sys.dont_write_bytecode = previous
    return module


def load_runtime(identity):
    protocol_lock.verify_lock()
    inventory = files.read_json(files.ROOT / files.OUT / files.NAME)["accepted_evidence_locations"]
    configuration = files.read_json(files.ROOT / identity["configuration_path"])
    runtime = archived_package(identity)
    # The accepted loader expects logical source paths. An exact-byte temporary
    # verification tree satisfies that check without changing active-tree inventory.
    with tempfile.TemporaryDirectory(prefix="ds-frozen-code-", dir=files.ROOT / "tmp") as temporary:
        root = Path(temporary)
        for logical, expected in configuration["runtime_code_sha256"].items():
            entry = inventory[logical]
            require(entry["sha256"] == expected, "DS_RUNTIME_SOURCE_BINDING_CONFLICT")
            source = files.ROOT / entry["local_path"]
            require(files.sha(source) == expected, "DS_RUNTIME_SOURCE_DRIFT")
            destination = root / logical
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
        detector = runtime.B2StatisticalDetector.from_artifact(
            (files.ROOT / identity["configuration_path"]).parent,
            calibration_dir=(files.ROOT / identity["calibrator_artifact"]).parent,
            workspace=root)
    require(detector.extractor.config.device == configuration["extractor_config"]["device"] == "cpu", "DS_FROZEN_DEVICE_DRIFT")
    require(not detector.extractor.engine.model.training and
        not any(p.requires_grad for p in detector.extractor.engine.model.parameters()), "DS_REFERENCE_MODEL_NOT_FROZEN")
    return detector


class FrozenDSAdapter(DetectorAdapter):
    """Additive loader hook; canonical prediction/validation logic is inherited unchanged."""

    def __init__(self, contracts=None):
        super().__init__("D_S", contracts or FrozenDetectorContracts())

    @property
    def live_binding_available(self):
        return True

    def _load_live(self):
        self.validate_frozen_identity()
        return load_runtime(self._identity)


def accepted_ds_adapter():
    """Future scoring requires the committed Gate-A proof, not only importability."""
    binding = files.read_json(files.ROOT / BINDING)
    evidence = files.read_json(files.ROOT / EQUIVALENCE)
    require(binding["status"] == evidence["status"] == "PASS", "DS_EQUIVALENCE_NOT_ACCEPTED")
    require(binding["equivalence_evidence_sha256"] == files.sha(files.ROOT / EQUIVALENCE), "DS_EQUIVALENCE_BINDING_DRIFT")
    require(binding["binding_code_sha256"] == files.sha(Path(__file__)), "DS_RUNTIME_BINDING_CODE_DRIFT")
    require(protocol_lock.git("show", "HEAD:" + BINDING) == (files.ROOT / BINDING).read_bytes() and
        protocol_lock.git("show", "HEAD:" + EQUIVALENCE) == (files.ROOT / EQUIVALENCE).read_bytes(), "COMMITTED_GATE_A_PROOF_REQUIRED")
    return FrozenDSAdapter()
