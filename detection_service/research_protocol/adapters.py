"""Manifest-bound representation adapters. Live loading is explicit and lazy."""

from copy import deepcopy
import importlib
import math
from pathlib import Path
from time import perf_counter

from pydantic import ValidationError

from detection_service.app.contracts.detection_request import DetectionContent, DetectionRequest
from detection_service.research_protocol import detector_semantics as phase2
from detection_service.research_protocol.prediction import PredictionMetadata, PredictionRecord

PHASE2_SHA = "2da5aa92cb14ac19cd49fa7150e7a4ef79b59e1e5fb1aa8ba4148456da618f31"
RULE_IDS = {"D_S": "ds_v2_default_vote_v1", "D_M-B": "dm_b_v1_default_vote_v1",
            "D_G": "dg_v1_native_or_argmax_v1"}
DIAGNOSTICS = {"ValueError", "TypeError", "RuntimeError", "OSError", "UnicodeError",
               "UnicodeEncodeError", "SemanticCalibrationError", "FineTunedDetectorError", "GuardUnavailableError"}


class AdapterContractError(ValueError):
    def __init__(self, status, code):
        super().__init__(code)
        self.status, self.code = status, code


def require(condition, status="OUTPUT_VALIDATION_ERROR", code="INVALID_NATIVE_OUTPUT"):
    if not condition:
        raise AdapterContractError(status, code)


class FrozenDetectorContracts:
    def __init__(self, root=phase2.ROOT):
        self.root = Path(root).resolve()
        self.validate_frozen_identity()
        self._manifest = phase2.read_json(self.root / phase2.OUT / phase2.NAME)

    def validate_frozen_identity(self):
        try:
            path = self.root / phase2.OUT / phase2.NAME
            require(phase2.sha(path) == PHASE2_SHA, "ARTIFACT_MISMATCH", "PHASE2_MANIFEST_HASH_MISMATCH")
            phase2.check_package(self.root)
        except AdapterContractError:
            raise
        except Exception as exc:
            raise AdapterContractError("ARTIFACT_MISMATCH", "FROZEN_EVIDENCE_VERIFICATION_FAILED") from exc

    def detector(self, label):
        require(label in self._manifest["primary_detector_order"], "ARTIFACT_MISMATCH", "NOT_A_PRIMARY_DETECTOR")
        return deepcopy(next(d for d in self._manifest["detectors"] if d["stack_label"] == label))


class DetectorAdapter:
    def __init__(self, label, contracts):
        self.contracts = contracts
        self._identity = contracts.detector(label)
        self._live = None
        self.native_decision_rule_id = RULE_IDS[label]
        self._special_tokens = 0
        if label == "D_M-B":
            tokenizer = phase2.read_json(contracts.root / Path(self._identity["model_artifact_path"]).parent / "tokenizer.json")
            processor = tokenizer["post_processor"]
            require(processor["type"] == "RobertaProcessing" and set(("cls", "sep")).issubset(processor),
                    "ARTIFACT_MISMATCH", "TOKENIZER_SPECIAL_TOKEN_POLICY_MISMATCH")
            self._special_tokens = len([processor["cls"], processor["sep"]])

    @property
    def detector_id(self):
        return self._identity["detector_id"]

    @property
    def detector_role(self):
        return self._identity["detector_role"]

    @property
    def score_direction(self):
        return self._identity["canonical_score_direction"]

    @property
    def live_binding_available(self):
        return self._identity["stack_label"] != "D_S"

    def validate_frozen_identity(self):
        self.contracts.validate_frozen_identity()
        require(self._identity == self.contracts.detector(self._identity["stack_label"]),
                "ARTIFACT_MISMATCH", "ADAPTER_IDENTITY_DRIFT")

    def _metadata(self, *, evidence_kind, unlabeled, source_path=None, source_sha256=None,
                  source_locator=None, latency_basis="UNMEASURED", diagnostic_class=None):
        label = self._identity["stack_label"]
        return PredictionMetadata(
            binding_mode="LIVE" if evidence_kind == "LIVE_FROZEN_MODEL" else
                         "CONTRACT_ONLY" if evidence_kind == "SYNTHETIC_FIXTURE" else "FROZEN_EVIDENCE",
            evidence_kind=evidence_kind, phase2_manifest_sha256=PHASE2_SHA,
            runtime_detector_id=self._identity["runtime_detector_id"], runtime_detector_version=self.detector_id,
            reference_model_revision=self._identity["reference_model_revision"],
            token_count_basis="NEXT_TOKEN_TARGETS_EXCLUDING_FIRST" if label == "D_S" else
                              "CONTENT_EXCLUDING_SPECIALS" if label == "D_M-B" else "UNIQUE_CONTENT",
            special_tokens_excluded=self._special_tokens, latency_basis=latency_basis,
            unlabeled_inference=unlabeled, source_path=source_path, source_sha256=source_sha256,
            source_locator=source_locator, diagnostic_class=diagnostic_class)

    def _base(self, sample_id, truth_label, allow_unlabeled, metadata):
        require(type(sample_id) is str and 0 < len(sample_id) <= 200 and bool(sample_id.strip()),
                "INVALID_INPUT", "INVALID_SAMPLE_ID")
        require(truth_label is None or (type(truth_label) is int and truth_label in (0, 1)),
                "INVALID_INPUT", "INVALID_TRUTH_LABEL")
        require(type(allow_unlabeled) is bool, "INVALID_INPUT", "INVALID_UNLABELED_FLAG")
        require(truth_label is not None or allow_unlabeled, "INVALID_INPUT", "UNLABELED_WORKFLOW_NOT_DECLARED")
        return dict(sample_id=sample_id, truth_label=truth_label, detector_id=self.detector_id,
            detector_role=self.detector_role, model_revision=self._identity["model_revision"],
            model_hash=self._identity["model_hash"], raw_score_name=self._identity["native_score_name"],
            score_direction=self.score_direction, native_decision_rule_id=self.native_decision_rule_id,
            metadata=metadata)

    def _failure(self, base, status, code, diagnostic=None, latency=None):
        metadata = base["metadata"].model_copy(update={"diagnostic_class": diagnostic,
            "latency_basis": "UNMEASURED" if latency is None else "LIVE_WALL_CLOCK"
                if base["metadata"].evidence_kind == "LIVE_FROZEN_MODEL" else "ACCEPTED_DETECTOR_REPORTED"})
        return PredictionRecord(**{**base, "metadata": metadata}, raw_score=None, calibrated_score=None,
            calibrator_id=None, native_binary_prediction=None, status=status, error_code=code,
            latency_ms=latency, input_tokens=None, tokens_analyzed=None, truncated=None)

    def _native_identity(self, output):
        d = self._identity
        require(output.get("detector_id") == d["runtime_detector_id"] and output.get("detector_version") == self.detector_id,
                "ARTIFACT_MISMATCH", "NATIVE_DETECTOR_IDENTITY_MISMATCH")
        model = output.get("model", {})
        expected_name = d["reference_model_name"] or d["model_name"]
        expected_revision = d["reference_model_revision"] or d["model_revision"]
        require(model.get("model_id") == expected_name and model.get("model_revision") == expected_revision and
                model.get("tokenizer_id") == d["tokenizer_name"], "ARTIFACT_MISMATCH", "NATIVE_MODEL_IDENTITY_MISMATCH")

    def _coverage(self, output):
        d, meta = self._identity, output.get("metadata", {})
        label = d["stack_label"]
        if label == "D_M-B":
            before, analyzed = meta.get("input_tokens_including_special"), meta.get("tokens_analyzed_including_special")
            truncated = meta.get("truncated")
            require(type(before) is int and type(analyzed) is int and before >= self._special_tokens and
                    analyzed == min(before, d["project_input_limit"]) and type(truncated) is bool and
                    truncated == (before > d["project_input_limit"]), code="INVALID_SEMANTIC_COVERAGE")
            return before - self._special_tokens, analyzed - self._special_tokens, truncated
        coverage = output.get("input_coverage") or {}
        before, analyzed, truncated = coverage.get("input_tokens"), coverage.get("tokens_analyzed"), coverage.get("truncated")
        require(type(before) is int and type(analyzed) is int and before >= 0 and analyzed >= 0 and
                type(truncated) is bool, code="INVALID_TOKEN_COVERAGE")
        if label == "D_S":
            require(before >= 2 and analyzed == min(before, d["project_input_limit"]) - 1 and
                    truncated == (before > d["project_input_limit"]), code="INVALID_STATISTICAL_COVERAGE")
        else:
            require(before > 0 and analyzed == before and not truncated and meta.get("tail_covered") is True and
                    meta.get("final_tail_end") == before, code="INVALID_GUARD_UNIQUE_COVERAGE")
        return before, analyzed, truncated

    def _adapt(self, output, base, *, latency=None):
        try:
            if hasattr(output, "model_dump"):
                output = output.model_dump()
            require(isinstance(output, dict), code="NATIVE_OUTPUT_NOT_OBJECT")
            self._native_identity(output)
            status = output.get("status")
            if status != "success":
                require(status in ("insufficient_input", "unavailable", "not_trained"), code="UNKNOWN_NATIVE_STATUS")
                target = "INSUFFICIENT_INPUT" if status == "insufficient_input" else "UNAVAILABLE"
                return self._failure(base, target, "NATIVE_" + status.upper(), latency=latency)
            raw, calibrated, vote = output.get("raw_score"), output.get("calibrated_probability"), output.get("binary_vote")
            require(type(raw) in (float, int) and math.isfinite(raw) and 0 <= raw <= 1, code="INVALID_RAW_SCORE")
            require(type(vote) is bool, code="MISSING_OR_INVALID_NATIVE_VOTE")
            meta = output.get("metadata", {})
            require(isinstance(meta, dict), code="INVALID_NATIVE_METADATA")
            d = self._identity
            if d["stack_label"] == "D_S":
                require(meta.get("feature_schema_sha256") == d["feature_schema_sha256"] and
                        meta.get("feature_count") == d["feature_count"],
                        "ARTIFACT_MISMATCH", "STATISTICAL_FEATURE_SCHEMA_MISMATCH")
            if d["stack_label"] == "D_M-B":
                require(meta.get("tokenizer_revision") == d["tokenizer_revision"] and
                        meta.get("max_sequence_length") == d["project_input_limit"] and
                        meta.get("truncation_side") == "right" and meta.get("padding") == "longest_in_batch",
                        "ARTIFACT_MISMATCH", "SEMANTIC_INPUT_POLICY_MISMATCH")
            if d["calibrated_score_available"]:
                require(type(calibrated) in (float, int) and math.isfinite(calibrated) and 0 <= calibrated <= 1,
                        "CALIBRATION_ERROR", "MISSING_OR_INVALID_CALIBRATED_SCORE")
                require(meta.get("calibration_version") == d["calibrator_id"], "ARTIFACT_MISMATCH", "CALIBRATOR_IDENTITY_MISMATCH")
                basis = calibrated if d["threshold_input_score_type"] == "calibrated_probability" else raw
                require(vote == (basis >= d["default_threshold"]), code="NATIVE_VOTE_CONTRACT_MISMATCH")
            else:
                require(calibrated is None and meta.get("calibration_version") is None,
                        "CALIBRATION_ERROR", "UNAPPROVED_GUARD_CALIBRATION")
                require(meta.get("decision_rule") == d["aggregation_policy"]["binary_vote"] and
                        meta.get("positive_class") == d["adversarial_class"]["index"] and
                        meta.get("aggregation") == d["aggregation_policy"]["raw_score"] and
                        meta.get("context_limit") == d["context_length"] and
                        meta.get("chunk_size") == d["chunking_policy"]["content_tokens"] and
                        meta.get("overlap") == d["chunking_policy"]["overlap"] and
                        meta.get("stride") == d["chunking_policy"]["stride"],
                        "ARTIFACT_MISMATCH", "GUARD_NATIVE_POLICY_MISMATCH")
                # Preserve the emitted OR vote; never reconstruct it from max probability.
            before, analyzed, truncated = self._coverage(output)
            if latency is None and base["metadata"].evidence_kind != "SYNTHETIC_FIXTURE":
                reported = output.get("latency_ms")
                require(reported is None or (type(reported) in (int, float) and math.isfinite(reported) and reported >= 0),
                        code="INVALID_NATIVE_LATENCY")
                latency = float(reported) if reported is not None else None
            basis = "LIVE_WALL_CLOCK" if base["metadata"].evidence_kind == "LIVE_FROZEN_MODEL" else \
                    "ACCEPTED_DETECTOR_REPORTED" if latency is not None else "UNMEASURED"
            record = PredictionRecord(**{**base, "metadata": base["metadata"].model_copy(update={"latency_basis": basis})},
                raw_score=float(raw), calibrated_score=float(calibrated) if calibrated is not None else None,
                calibrator_id=d["calibrator_id"] if calibrated is not None else None,
                native_binary_prediction=int(vote), status="OK", error_code=None, latency_ms=latency,
                input_tokens=before, tokens_analyzed=analyzed, truncated=truncated)
            self.validate_prediction_record(record)
            return record
        except AdapterContractError as exc:
            return self._failure(base, exc.status, exc.code, latency=latency)
        except (TypeError, ValueError, KeyError, AttributeError, ValidationError):
            return self._failure(base, "OUTPUT_VALIDATION_ERROR", "INVALID_NATIVE_OUTPUT", latency=latency)

    def adapt_fixture(self, output, *, sample_id, truth_label, allow_unlabeled=False):
        """Synthetic engineering data only; never labeled as authoritative evidence."""
        meta = self._metadata(evidence_kind="SYNTHETIC_FIXTURE", unlabeled=truth_label is None)
        return self._adapt(output, self._base(sample_id, truth_label, allow_unlabeled, meta))

    def adapt_existing_output(self, *, source_path, source_locator="", sample_id, truth_label, allow_unlabeled=False):
        """Read an exact native-result JSON object from hash-bound Phase-2 evidence.

        Fold-local OOF tables are deliberately not relabeled with final-model hashes.
        source_locator is a JSON Pointer to a complete native DetectorResult object.
        """
        meta = self._metadata(evidence_kind="ACCEPTED_FROZEN_OUTPUT", unlabeled=truth_label is None)
        base = self._base(sample_id, truth_label, allow_unlabeled, meta)
        try:
            inventory = self.contracts._manifest["accepted_evidence_locations"]
            logical_config = next(name for name, info in inventory.items()
                                  if info["local_path"] == self._identity["configuration_path"])
            artifact_prefix = Path(logical_config).parent.as_posix() + "/"
            require(source_path in inventory and source_path.startswith(artifact_prefix),
                    "ARTIFACT_MISMATCH", "SOURCE_NOT_BOUND_FULL_MODEL_EVIDENCE")
            info = inventory[source_path]
            path = phase2.contained(self.contracts.root, info["local_path"])
            require(phase2.sha(path) == info["sha256"], "ARTIFACT_MISMATCH", "FROZEN_OUTPUT_HASH_MISMATCH")
            output = phase2.read_json(path)
            require(not source_locator or source_locator.startswith("/"), code="INVALID_JSON_POINTER")
            for segment in source_locator.split("/")[1:] if source_locator else []:
                segment = segment.replace("~1", "/").replace("~0", "~")
                if isinstance(output, list):
                    require(segment == "0" or (segment.isdecimal() and not segment.startswith("0")),
                            code="INVALID_JSON_ARRAY_INDEX")
                    output = output[int(segment)]
                else:
                    output = output[segment]
            base["metadata"] = meta.model_copy(update={"source_path": source_path, "source_sha256": info["sha256"],
                                                       "source_locator": source_locator})
            return self._adapt(output, base)
        except AdapterContractError as exc:
            return self._failure(base, exc.status, exc.code)
        except (OSError, KeyError, IndexError, ValueError, TypeError, AttributeError, StopIteration):
            return self._failure(base, "OUTPUT_VALIDATION_ERROR", "FROZEN_OUTPUT_UNREADABLE")

    def _load_live(self):
        require(self.live_binding_available, "UNAVAILABLE", "DS_FROZEN_RUNTIME_BINDING_UNAVAILABLE")
        self.validate_frozen_identity()
        d = self._identity
        module = d["implementation_logical_path"].removesuffix(".py").replace("/", ".")
        cls = getattr(importlib.import_module(module), d["implementation_class"])
        directory = self.contracts.root / Path(d["configuration_path"]).parent
        if d["stack_label"] == "D_M-B":
            return cls.from_artifact(directory, require_calibration=True)
        return cls.from_artifact(directory, workspace=self.contracts.root)

    def predict(self, text, *, sample_id, truth_label, allow_unlabeled=False):
        """Explicit lazy inference; Phase-3 tests use synthetic callables only."""
        meta = self._metadata(evidence_kind="LIVE_FROZEN_MODEL", unlabeled=truth_label is None)
        base = self._base(sample_id, truth_label, allow_unlabeled, meta)
        if type(text) is not str or not text.strip():
            return self._failure(base, "INVALID_INPUT", "INVALID_PROMPT_INPUT")
        try:
            text.encode("utf-8", errors="strict")
            request = DetectionRequest(request_id=sample_id, content=DetectionContent(type="user_prompt", text=text))
        except (UnicodeError, ValidationError):
            return self._failure(base, "INVALID_INPUT", "INVALID_PROMPT_INPUT")
        try:
            if self._live is None:
                self._live = self._load_live()
        except AdapterContractError as exc:
            return self._failure(base, exc.status, exc.code)
        except Exception as exc:
            name = type(exc).__name__
            return self._failure(base, "UNAVAILABLE", "FROZEN_MODEL_LOAD_FAILED", name if name in DIAGNOSTICS else "Exception")
        started = perf_counter()
        try:
            output = self._live.detect(request)
            return self._adapt(output, base, latency=(perf_counter() - started) * 1000)
        except AdapterContractError as exc:
            return self._failure(base, exc.status, "NATIVE_" + exc.status,
                                 latency=(perf_counter() - started) * 1000)
        except Exception as exc:
            names = {c.__name__ for c in type(exc).__mro__}
            causes, cause = set(), exc
            while cause is not None and id(cause) not in causes:
                causes.add(id(cause))
                names.update(c.__name__ for c in type(cause).__mro__)
                cause = cause.__cause__
            status = "CALIBRATION_ERROR" if "SemanticCalibrationError" in names else \
                     "TOKENIZATION_ERROR" if "UnicodeError" in names else "INFERENCE_ERROR"
            name = type(exc).__name__
            return self._failure(base, status, "NATIVE_" + status, name if name in DIAGNOSTICS else "Exception",
                                 latency=(perf_counter() - started) * 1000)

    def validate_prediction_record(self, record):
        record = PredictionRecord.model_validate(record.model_dump() if isinstance(record, PredictionRecord) else record)
        d = self._identity
        require((record.detector_id, record.detector_role, record.model_revision, record.model_hash, record.score_direction,
                 record.native_decision_rule_id, record.metadata.phase2_manifest_sha256,
                 record.metadata.runtime_detector_id, record.metadata.runtime_detector_version,
                 record.metadata.reference_model_revision, record.metadata.special_tokens_excluded) ==
                (self.detector_id, self.detector_role, d["model_revision"], d["model_hash"], self.score_direction,
                 self.native_decision_rule_id, PHASE2_SHA, d["runtime_detector_id"], self.detector_id,
                 d["reference_model_revision"], self._special_tokens),
                "ARTIFACT_MISMATCH", "CANONICAL_IDENTITY_MISMATCH")
        if record.status == "OK":
            require(record.calibrator_id == d["calibrator_id"], "ARTIFACT_MISMATCH", "CANONICAL_CALIBRATOR_MISMATCH")
            if d["threshold_input_score_type"] != "native_chunk_argmax":
                basis = record.calibrated_score if d["threshold_input_score_type"] == "calibrated_probability" else record.raw_score
                require(record.native_binary_prediction == int(basis >= d["default_threshold"]), code="CANONICAL_NATIVE_VOTE_MISMATCH")
        return record


def primary_adapters(root=phase2.ROOT):
    contracts = FrozenDetectorContracts(root)
    return tuple(DetectorAdapter(label, contracts) for label in contracts._manifest["primary_detector_order"])
