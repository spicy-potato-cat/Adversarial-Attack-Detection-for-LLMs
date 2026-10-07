"""Gate A: archived frozen D_S versus authoritative historical evidence only."""

import argparse
import ast
from collections import Counter
from contextlib import ExitStack
import csv
import hashlib
import json
from pathlib import Path
from unittest.mock import patch

from detection_service.research_protocol import detector_semantics as files
from detection_service.research_protocol import ds_runtime as runtime
from detection_service.research_protocol import protocol_lock as lock
from detection_service.research_protocol import release_validation as release
from detection_service.research_protocol.regime import require

START = "1d1f7095f57f7f33e0d23ba83e422ead596ad542"
REPORT = "reviews/R1_DS_RUNTIME_EQUIVALENCE_v1.md"
CODE = ("detection_service/research_protocol/ds_runtime.py", "detection_service/research_protocol/ds_equivalence.py",
        "detection_service/tests/test_ds_runtime_equivalence.py")
TOLERANCE = 1e-12


def compare_scores(actual, raw, calibrated):
    require(actual.status == "OK", "DS_CANONICAL_LIVE_NON_OK: " + str(actual.error_code))
    raw_delta = abs(actual.raw_score - raw)
    calibrated_delta = abs(actual.calibrated_score - calibrated)
    require(raw_delta <= TOLERANCE and calibrated_delta <= TOLERANCE, "DS_SCORE_EQUIVALENCE_FAILURE")
    require(actual.native_binary_prediction == int(calibrated >= .5), "DS_NATIVE_DECISION_MISMATCH")
    return raw_delta, calibrated_delta


def historical_inputs():
    import numpy as np
    from detection_service.scripts import statistical_feature_ablation as source
    from detection_service.scripts.calibrate_semantic_baseline import calibration_rows, load_calibration_texts
    from detection_service.quality.policy import MANIFEST_PATH
    identity = runtime.FrozenDSAdapter()._identity
    calibration_dir = (files.ROOT / identity["calibrator_artifact"]).parent
    metadata = files.read_json(calibration_dir / "ds_v2_calibration_manifest_v1.json")
    score_path = calibration_dir / "calibration_predictions_v1.csv"
    require(files.sha(score_path) == metadata["prediction_sha256"], "DS_CALIBRATION_SCORE_EVIDENCE_DRIFT")
    rows = sorted(calibration_rows(files.ROOT / MANIFEST_PATH), key=lambda r:r["record_id"])
    require(len(rows) == 233 and sum(int(r["canonical_label"]) for r in rows) == 41, "DS_CALIBRATION_MEMBERSHIP_DRIFT")
    texts, hashes = load_calibration_texts(rows, files.ROOT)
    require(hashes == metadata["source_artifact_sha256"], "DS_CALIBRATION_SOURCE_DRIFT")
    with score_path.open(encoding="utf-8", newline="") as stream:
        scores = list(csv.DictReader(stream))
    require([r["record_id"] for r in scores] == [r["record_id"] for r in rows], "DS_CALIBRATION_SCORE_ORDER_DRIFT")
    calibration = [dict(row=r,text=t,raw=float(s["raw_score"]),calibrated=float(s["calibrated_probability"]),
        evidence_kind="AUTHORITATIVE_FROZEN_CALIBRATION_SCORES") for r,t,s in zip(rows,texts,scores,strict=True)]
    baseline_rows, source_rows = source.baseline.selected_metadata()
    training = files.read_json((files.ROOT / identity["configuration_path"]).parent / "ds_v2_training_metadata_v1.json")
    evidence = source.load_cache(baseline_rows, training["numeric_cache_sha256"])
    frozen = runtime.archived_package(identity)
    model = frozen.B2Model(files.read_json(files.ROOT / identity["model_artifact_path"]),
        files.read_json(files.ROOT / identity["reference_artifact_path"]),
        files.read_json(files.ROOT / identity["configuration_path"]))
    vectors = np.asarray([model.transform(item) for item in evidence])
    require(hashlib.sha256(vectors.tobytes()).hexdigest() == training["matrix_sha256"], "DS_AUTHORITATIVE_TRAINING_FEATURE_MATRIX_DRIFT")
    raw = model.predict(vectors)
    calibrator = frozen.load_calibration(calibration_dir, (files.ROOT / identity["configuration_path"]).parent)
    probabilities = calibrator.predict(raw)
    # Selection uses accepted historical coverage/scores only, never R1 outcomes.
    chosen = set()
    for label in (0, 1):
        indices = [i for i,r in enumerate(baseline_rows) if int(r["label"]) == label]
        for key in (lambda i:evidence[i]["input_tokens"], lambda i:raw[i]):
            chosen.add(min(indices,key=lambda i:(key(i),baseline_rows[i]["sample_id"])))
            chosen.add(max(indices,key=lambda i:(key(i),baseline_rows[i]["sample_id"])))
    for low, high in ((2,32),(32,128),(128,512),(512,4096),(4096,float("inf"))):
        candidates = [i for i,item in enumerate(evidence) if low <= item["input_tokens"] < high]
        if candidates:
            chosen.add(min(candidates,key=lambda i:baseline_rows[i]["sample_id"]))
    chosen = sorted(chosen)
    selected = [source_rows[i] for i in chosen]
    all_base_texts = source.baseline.load_base_texts(source_rows, metadata)
    base_texts = [all_base_texts[i] for i in chosen]
    base = [dict(row=r,text=t,raw=float(raw[i]),calibrated=float(probabilities[i]),
        vector=vectors[i],cached=evidence[i],evidence_kind="AUTHORITATIVE_FROZEN_NUMERIC_CACHE_AND_MODEL")
        for r,t,i in zip(selected,base_texts,chosen,strict=True)]
    return calibration + base, dict(calibration_predictions_sha256=files.sha(score_path),
        calibration_membership_sha256=metadata["membership_sha256"],numeric_cache_sha256=training["numeric_cache_sha256"],
        training_matrix_sha256=training["matrix_sha256"],source_artifact_sha256=hashes,
        calibration_rows=len(calibration),base_train_rows=len(base),selection="All CALIBRATION plus deterministic BASE_TRAIN label/length/score extrema and length-bucket representatives")


def accepted_long_input():
    path = "detection_service/scripts/smoke_statistical_risk.py"
    source = lock.git("show", files.BASE + ":" + path)
    require(source == (files.ROOT/path).read_bytes(), "HISTORICAL_LONG_INPUT_SOURCE_DRIFT")
    assignment = next(n for n in ast.walk(ast.parse(source)) if isinstance(n,ast.Assign) and
        any(isinstance(t,ast.Name) and t.id == "cases" for t in n.targets))
    value = next(v for k,v in zip(assignment.value.keys,assignment.value.values) if ast.literal_eval(k) == "long")
    require(isinstance(value,ast.BinOp) and isinstance(value.op,ast.Mult), "UNSUPPORTED_HISTORICAL_LONG_INPUT_RECIPE")
    text = ast.literal_eval(value.left) * ast.literal_eval(value.right)
    logical = "artifacts/models/ds_v1/extended_smoke.json"
    inventory = files.read_json(files.ROOT/files.OUT/files.NAME)["accepted_evidence_locations"]
    require(files.sha(files.ROOT/logical) == inventory[logical]["sha256"], "HISTORICAL_LONG_EXTRACTOR_EVIDENCE_DRIFT")
    return text,files.read_json(files.ROOT/logical)["cases"]["long"],dict(source_commit=files.BASE,
        source_path=path,source_sha256=hashlib.sha256(source).hexdigest(),evidence_path=logical,evidence_sha256=files.sha(files.ROOT/logical))


class CaptureRuntime:
    def __init__(self, detector):
        self.detector = detector
        self.last = None

    def detect(self, request):
        self.last = self.detector.detect(request)
        return self.last


def run():
    import numpy as np
    from sklearn.linear_model import LogisticRegression
    from detection_service.analysis.statistical_feature_ablation import References
    from detection_service.app.detectors.semantic.calibration import SigmoidCalibrator
    from detection_service.research_protocol.operating_policy import apply_operating_policy
    from detection_service.research_protocol.r0_operational import verified_policy
    require(lock.git("rev-parse","HEAD").decode().strip() == START, "R1_START_HEAD_GATE")
    require(lock.git("branch","--show-current").decode().strip() == "exp/protocol-001", "R1_BRANCH_GATE")
    release.check_acceptance()
    paths = (runtime.BINDING,runtime.EQUIVALENCE,REPORT)
    require(not any((files.ROOT/p).exists() for p in paths), "REFUSE_DS_EQUIVALENCE_OVERWRITE")
    with release.offline(), ExitStack() as stack:
        for cls, method in ((LogisticRegression,"fit"),(References,"fit"),(SigmoidCalibrator,"fit_mapping")):
            stack.enter_context(patch.object(cls,method,side_effect=AssertionError("R1_NO_FITTING_ALLOWED")))
        population, authority = historical_inputs()
        adapter = runtime.FrozenDSAdapter()
        capture = CaptureRuntime(adapter._load_live())
        adapter._live = capture
        policy = verified_policy()
        comparisons = []
        coverage = Counter()
        for index,item in enumerate(population,1):
            row = item["row"]
            actual = adapter.predict(item["text"],sample_id=row["record_id"],truth_label=int(row["canonical_label"]))
            raw_delta, calibrated_delta = compare_scores(actual,item["raw"],item["calibrated"])
            operational = apply_operating_policy(actual, policy)
            require(operational.operational_binary_prediction == int(item["calibrated"] >= .5585373573968287), "DS_OPERATIONAL_DECISION_MISMATCH")
            feature_delta = None
            if "cached" in item:
                native = capture.last
                cached = item["cached"]
                require(native.input_coverage.input_tokens == cached["input_tokens"] and
                    native.input_coverage.tokens_analyzed == cached["tokens_analyzed"], "DS_TOKEN_ACCOUNTING_MISMATCH")
                vector = np.asarray([native.metadata["b2_features"][n] for n in capture.detector.model.manifest["feature_names"]])
                feature_delta = float(np.max(np.abs(vector-item["vector"])))
                require(feature_delta <= TOLERANCE, "DS_FEATURE_EQUIVALENCE_FAILURE")
            coverage.update(short=actual.input_tokens < 32,long=actual.input_tokens >= 512,
                windowed=capture.last.features.window_count > 1,
                lm_multichunk=capture.last.input_coverage.inference_chunks > 1,truncated=actual.truncated,
                benign=actual.truth_label == 0,attack=actual.truth_label == 1,
                low_score=item["raw"] < .5,high_score=item["raw"] >= .5)
            comparisons.append(dict(sample_id=actual.sample_id,partition=row["partition"],truth_label=actual.truth_label,
                evidence_kind=item["evidence_kind"],input_tokens=actual.input_tokens,tokens_analyzed=actual.tokens_analyzed,
                truncated=actual.truncated,raw_score_delta=raw_delta,calibrated_score_delta=calibrated_delta,
                feature_max_abs_delta=feature_delta,native_decision_mismatch=False,operational_decision_mismatch=False))
            if index % 50 == 0 or index == len(population):
                print(json.dumps(dict(gate="A",equivalence_scored=index,total=len(population))),flush=True)
        # Project records are short. Accepted long v1 evidence proves inherited
        # extractor/chunking behavior, never v2 classifier-score equivalence.
        long_text, golden, long_authority = accepted_long_input()
        long_actual = adapter.predict(long_text,sample_id="accepted-ds-v1-long-extractor-replay",truth_label=None,allow_unlabeled=True)
        require(long_actual.status == "OK", "DS_LONG_INPUT_NON_OK")
        native = capture.last
        for field in ("input_tokens","tokens_analyzed","tokens_excluded","inference_chunks","model_context_tokens","truncated"):
            require(getattr(native.input_coverage,field) == golden["input_coverage"][field], "DS_LONG_TOKEN_ACCOUNTING_MISMATCH: "+field)
        from detection_service.app.detectors.statistical_risk.schema import FEATURE_NAMES
        inherited_delta = max(abs(getattr(native.features,name)-golden["features"][name]) for name in FEATURE_NAMES)
        require(inherited_delta <= TOLERANCE and native.features.window_count == golden["features"]["window_count"], "DS_LONG_INHERITED_FEATURE_MISMATCH")
        long_projected = apply_operating_policy(long_actual,policy)
        require(long_actual.native_binary_prediction == int(long_actual.calibrated_score >= .5) and
            long_projected.operational_binary_prediction == int(long_actual.calibrated_score >= .5585373573968287), "DS_LONG_DECISION_SEMANTICS_MISMATCH")
        coverage.update(long=1,windowed=1,lm_multichunk=1,truncated=1)
        long_replay = dict(status="PASS",authority=long_authority,input_tokens=long_actual.input_tokens,
            tokens_analyzed=long_actual.tokens_analyzed,truncated=long_actual.truncated,
            inherited_feature_max_abs_delta=inherited_delta,
            score_equivalence="NOT_APPLICABLE: accepted long artifact stores ds_v1 scores, which are not compared to ds_v2",
            scope="Supplementary unchanged inherited extractor/token replay; not a substitute for 233 authoritative v2 calibration score comparisons")
        require(all(coverage[k] > 0 for k in ("short","long","windowed","lm_multichunk","truncated","benign","attack","low_score","high_score")), "DS_EQUIVALENCE_REQUIRED_COVERAGE_MISSING")
        release.check_acceptance()
        preflight = lock.verify_experiment_preflight(release.fixture_request("r1"))
    value = dict(status="PASS",gate="A",rows=len(population),authority=authority,coverage=dict(coverage),accepted_long_extractor_replay=long_replay,
        max_raw_score_delta=max(r["raw_score_delta"] for r in comparisons),
        max_calibrated_score_delta=max(r["calibrated_score_delta"] for r in comparisons),
        max_feature_delta=max(r["feature_max_abs_delta"] for r in comparisons if r["feature_max_abs_delta"] is not None),
        native_decision_mismatches=0,operational_decision_mismatches=0,tolerance=TOLERANCE,
        calibration_features_and_token_counts="Not stored in historical calibration CSV; exact stored token/feature comparisons use authoritative BASE_TRAIN cache",
        training=False,reference_refit=False,calibration_refit=False,threshold_changes=False,R1_accessed=False,
        pre_scoring_engineering_stop="Subset passed to historical all-container loader; all three frozen source hashes independently verified; corrected to unchanged full approved BASE_TRAIN loader before selecting equivalence rows; no LM scoring occurred before this correction",
        protocol_integrity="PASS",preflight=preflight,comparisons=comparisons,
        start_commit=START,code_sha256={p:files.sha(files.ROOT/p) for p in CODE})
    evidence_bytes = files.manifest_bytes(value)
    identity = adapter._identity
    binding = dict(status="PASS",implementation_provenance=dict(commit=identity["implementation_revision"],
        path=identity["implementation_path"],sha256=identity["implementation_sha256"],method="Exact accepted archive package loaded under private namespace; unchanged canonical adapter subclass loader hook"),
        model_sha256=identity["model_hash"],feature_schema_sha256=identity["feature_schema_sha256"],
        feature_reference_sha256=identity["reference_hash"],reference_lm_revision=identity["reference_model_revision"],
        calibrator_sha256=identity["calibrator_hash"],threshold_id="ds_v2_op3_cal_v1",threshold=.5585373573968287,
        preprocessing=dict(context_tokens=1024,max_analysis_tokens=4096,lm_overlap=64,lm_stride=960,feature_window=128,feature_stride=64,device="cpu"),
        equivalence_population=len(population),max_raw_score_difference=value["max_raw_score_delta"],
        max_calibrated_score_difference=value["max_calibrated_score_delta"],decision_mismatch_count=0,
        equivalence_evidence_sha256=hashlib.sha256(evidence_bytes).hexdigest(),
        binding_code_sha256=files.sha(files.ROOT/CODE[0]),code_sha256=value["code_sha256"],protocol_lock_unchanged=True)
    report = "# R1 D_S Runtime Equivalence\n\nGate A: PASS. No R1 data accessed, training, feature redesign, calibration fitting, threshold changes, or frozen protocol edits.\n\n"
    report += "Exact archived package bytes were loaded under a private namespace. The original B2 loader verified an exact-byte temporary logical-code tree; active application paths and all frozen inventories remain unchanged. The additive canonical adapter inherits prediction and validation semantics unchanged.\n\n"
    report += "All 233 authoritative CALIBRATION scores were compared at absolute tolerance 1e-12. Selected BASE_TRAIN records additionally compare live token accounting and feature vectors with the hash-verified numeric cache. These are final-model comparisons, NOT comparisons against fold-local OOF models. Full frozen training matrix was verified without fitting.\n\n"
    report += "BASE_TRAIN contains no long/chunked/truncated records (maximum 433 tokens). Supplementary long replay uses the exact previously accepted smoke recipe and v1 inherited-extractor evidence: 4502 input tokens, 4095 scored, five chunks. No v1 classifier scores are treated as v2 reference scores.\n\n```json\n" + json.dumps(dict(binding=binding,equivalence=value),indent=2) + "\n```\n"
    outputs = {runtime.BINDING:files.manifest_bytes(binding),runtime.EQUIVALENCE:evidence_bytes,REPORT:report.encode("ascii")}
    for path,data in outputs.items():
        destination = files.ROOT/path
        destination.parent.mkdir(parents=True,exist_ok=True)
        with destination.open("xb") as stream: stream.write(data)
    print(json.dumps(dict(status="PASS",rows=len(population),max_raw_score_delta=value["max_raw_score_delta"],
        max_calibrated_score_delta=value["max_calibrated_score_delta"],coverage=dict(coverage)),indent=2))


if __name__ == "__main__":
    argparse.ArgumentParser(description=__doc__).parse_args()
    run()
