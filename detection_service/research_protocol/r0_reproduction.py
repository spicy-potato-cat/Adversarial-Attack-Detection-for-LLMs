"""Hash-verified historical R0 import and reconstruction; no model execution."""

import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import subprocess

from detection_service.research_protocol import detector_semantics as files
from detection_service.research_protocol.adapters import FrozenDetectorContracts, PHASE2_SHA
from detection_service.research_protocol.alignment import AlignedEvaluation, AlignedRow, EvaluationProvenance, PRIMARY, REGIME_SHA, coverage, digest
from detection_service.research_protocol.core_metrics import evaluate_core
from detection_service.research_protocol.cross_regime import cross_regime_matrix, result_bundle
from detection_service.research_protocol.historical_uncertainty import replay_historical_uncertainty
from detection_service.research_protocol.regime import RegimeManifest, require
from detection_service.research_protocol.regime_contract import FrozenRegimeContracts, MEMBERSHIP, FOLDS, PREDICTION_SHA, R0
from detection_service.research_protocol.uncertainty import BootstrapConfig, bootstrap_metrics

PRE_R0_COMMIT = "9982b9bd2c5f8da7fc63a1b7977c1cccf91cfb70"
CYCLE1 = "dc6dd3041643fb70ad5b128d32c246f8763a8044"
PUB = "artifacts/common_mode/development/completion_v3/publication"
ANCHOR = PUB+"/full_stack_manifest_v1.json"
BASE = "artifacts/common_mode/development/completion_v3"
OUT = files.OUT+"/r0"
IMPORT = OUT+"/r0_reproduction_import_manifest_v1.json"
DECISIONS = OUT+"/r0_historical_descriptive_decisions_v1.csv"
HASHES = files.OUT+"/phase11_13_artifact_hashes_v1.json"
CODE = ("detection_service/research_protocol/r0_reproduction.py","detection_service/research_protocol/historical_uncertainty.py",
        "detection_service/tests/test_r0_reproduction.py")
REPORTS = tuple("reviews/EXP_PROTOCOL_001_"+name+"_v1.md" for name in
    ("UNCERTAINTY","CROSS_REGIME","R0_REPRODUCTION","PHASE11_13_TEST_REPORT"))
MAPPING = {"D_S_B2_LR":"ds_v2","D_M-B_v1":"dm_b_v1","D_G_v1":"dg_v1"}
MEMBERSHIP_SHA = "9cdd5ecdd80f9ac3c8f05db63742721f4537ca2b64a2fe48f6c2b424b57483a6"
FOLD_SHA = "19dc0153cc257cc2331782d6dd61b7bb9fb8cb0ed88d3e782b69d5ba05c4bb8d"


def read_csv(path):
    with path.open(encoding="utf-8",newline="") as stream:
        return list(csv.DictReader(stream))


def csv_bytes(rows):
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer,fieldnames=tuple(rows[0]),lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8")


def unique_path(inventory, suffix):
    matches = [p for p in inventory if p.endswith("/"+suffix)]
    require(len(matches)==1,"AMBIGUOUS_HISTORICAL_SOURCE: "+suffix)
    return matches[0]


def verify_sources(root):
    """Anchor in accepted Cycle-1 Git bytes, then follow its declared hash links."""
    root = Path(root)
    FrozenDetectorContracts(root)
    blob = subprocess.check_output(["git","show",CYCLE1+":"+ANCHOR],cwd=root)
    require((root/ANCHOR).read_bytes()==blob,"ACCEPTED_PUBLICATION_GIT_BYTES_CHANGED")
    publication = files.read_json(root/ANCHOR)
    require(publication["status"]=="PASS" and publication["fixture_manifest_sha256"]==MEMBERSHIP_SHA
            and publication["fold_sha256"]==FOLD_SHA,"PUBLICATION_PROVENANCE_CONFLICT")
    expected = {ANCHOR:hashlib.sha256(blob).hexdigest(),BASE+"/common_mode_manifest_v1.json":publication["core_manifest_sha256"]}
    def add(entries,prefix=""):
        for p,h in entries.items():
            path = prefix+"/"+p if prefix else p
            require(path not in expected or expected[path]==h,"CONFLICTING_HISTORICAL_HASH")
            expected[path]=h
    add(publication["output_sha256"],PUB)
    add(publication["report_sha256"])
    add(publication["authoritative_oof_sha256"])
    require(files.sha(root/(BASE+"/common_mode_manifest_v1.json"))==publication["core_manifest_sha256"],"HISTORICAL_CORE_MANIFEST_DRIFT")
    core = files.read_json(root/(BASE+"/common_mode_manifest_v1.json"))
    require(core["status"]=="PASS" and (core["rows"],core["positive"],core["negative"],core["seed"],core["bootstrap_repetitions"])
            == (1135,183,952,1701,1000),"HISTORICAL_CORE_SCOPE_CONFLICT")
    add(core["input_sha256"])
    add(core["output_sha256"],BASE)
    add(core["code_sha256"])
    add(core["report_sha256"])
    # The importer reuses this accepted metadata-only adapter, never OOF fitting code.
    adapter = "detection_service/scripts/common_mode_development.py"
    expected[adapter] = hashlib.sha256(subprocess.check_output(["git","show",CYCLE1+":"+adapter],cwd=root)).hexdigest()
    for p,h in expected.items():
        require(files.sha(files.contained(root,p))==h,"HISTORICAL_SOURCE_HASH_MISMATCH: "+p)
    phase4 = files.read_json(root/(files.OUT+"/phase4_artifact_hashes_v1.json"))["sha256"]
    require(R0 in phase4 and files.sha(root/R0)==phase4[R0],"FROZEN_R0_MANIFEST_DRIFT")
    expected[R0]=phase4[R0]
    return publication,core,expected


def membership_proof(manifest, folds, partition_rows):
    selected = [r for r in partition_rows if r["partition"]=="BASE_TRAIN"]
    ids = [r["record_id"] for r in selected]
    fold_ids = [r["sample_id"] for r in folds]
    require(len(ids)==len(set(ids))==len(fold_ids)==len(set(fold_ids))==1135,"R0_POPULATION_OR_DUPLICATE_CONFLICT")
    require(set(ids)==set(fold_ids)=={s.sample_id for s in manifest.samples},"R0_MEMBERSHIP_ALIGNMENT_CONFLICT")
    originals = {r["record_id"]:r for r in selected}
    by_id = {r["sample_id"]:r for r in folds}
    groups = {}
    for sample in manifest.samples:
        f,source = by_id[sample.sample_id],originals[sample.sample_id]
        require(f["partition"]=="BASE_TRAIN" and sample.partition=="BASE_TRAIN","R0_RESERVED_PARTITION_FORBIDDEN")
        require(sample.truth_label==int(f["label"])==int(source["canonical_label"]),"R0_LABEL_ALIGNMENT_CONFLICT")
        require(sample.lineage_id==f["lineage_group"]==source["lineage_group_id"],"R0_LINEAGE_ALIGNMENT_CONFLICT")
        require(sample.outer_fold==int(f["outer_fold"]),"R0_FOLD_ALIGNMENT_CONFLICT")
        groups.setdefault(sample.lineage_id,set()).add(sample.outer_fold)
    require(sum(s.truth_label for s in manifest.samples)==183 and manifest.benign_count==952,"R0_CLASS_COUNT_CONFLICT")
    require({int(f["outer_fold"]) for f in folds}==set(range(5)) and all(len(v)==1 for v in groups.values()),"R0_LINEAGE_FOLD_LEAKAGE")
    return by_id


def fold_proof(folds, ds_references, semantic_folds):
    ids = {r["sample_id"] for r in folds}
    results = []
    for refs in (ds_references,semantic_folds):
        require({r["fold"] for r in refs}==set(range(5)) and len(refs)==5,"OOF_FOLD_REFERENCE_INCOMPLETE")
        for ref in refs:
            training = sorted(r["sample_id"] for r in folds if int(r["outer_fold"])!=ref["fold"])
            heldout = sorted(ids-set(training))
            for key,values in (("train_membership_sha256",training),("held_out_membership_sha256",heldout)):
                require(hashlib.sha256("\n".join(values).encode()).hexdigest()==ref[key],"OOF_MEMBERSHIP_HASH_CONFLICT")
            if "fit_training_ids" in ref:
                require(set(ref["fit_training_ids"])==set(training) and set(ref["benign_ids"])<=set(training),"OOF_REFERENCE_FIT_LEAKAGE")
            require(not set(training)&set(heldout),"OOF_IDENTITY_LEAKAGE")
            results.append(dict(fold=ref["fold"],train_count=len(training),heldout_count=len(heldout),
                train_membership_sha256=ref["train_membership_sha256"],held_out_membership_sha256=ref["held_out_membership_sha256"]))
    return results


def load_history(root=files.ROOT):
    root = Path(root)
    publication,core,hashes = verify_sources(root)
    manifest = FrozenRegimeContracts(root).validate_manifest(files.read_json(root/R0))
    require(manifest.threat_regime=="R0_NON_ADAPTIVE" and manifest.evidence_kind=="ACCEPTED_METADATA","R0_MANIFEST_SEMANTICS_CONFLICT")
    folds = read_csv(root/FOLDS)
    fixture = membership_proof(manifest,folds,read_csv(root/MEMBERSHIP))
    inventory = core["input_sha256"]
    paths = {"D_S_B2_LR":unique_path(inventory,"scorer_predictions_v1.csv"),
        "D_M-B_v1":unique_path(inventory,"dm_b_v1_recipe_oof_predictions.csv"),
        "D_G_v1":unique_path(inventory,"dg_v1_base_train_predictions.csv")}
    from detection_service.scripts.common_mode_development import canonical
    detectors = {name:sorted(canonical(read_csv(root/p),name,fixture),key=lambda r:r["sample_id"]) for name,p in paths.items()}
    for rows in detectors.values():
        require({r["sample_id"] for r in rows}==set(fixture),"HISTORICAL_SCORE_POPULATION_CONFLICT")
    ds_run = files.read_json(root/unique_path(inventory,"run_metadata_v1.json"))
    sem_run = files.read_json(root/unique_path(inventory,"dm_b_v1_oof_run_metadata.json"))
    dg_run = files.read_json(root/unique_path(inventory,"dg_v1_run_metadata.json"))
    for run in (ds_run,sem_run,dg_run):
        require(run["manifest_sha256"]==MEMBERSHIP_SHA and run["fold_sha256"]==FOLD_SHA,"SCORE_RUN_PROVENANCE_CONFLICT")
    require(sem_run["code_commit"]=="5096d078b599c43ddd4e32b4fbfcaedcc83e4646","SEMANTIC_OOF_RUN_PROVENANCE_CHANGED")
    require(ds_run["final_ds_v2_trained"] is False and ds_run["calibration_used"] is False,"DS_FINAL_IN_SAMPLE_SUBSTITUTION")
    require(dg_run["revision"]=="11614a155199674a0a95e6602d6ab0417b790ed0" and dg_run["status"]=="COMPLETE"
        and dg_run["score_direction"]=="higher_is_more_adversarial" and not any(dg_run["isolation"].values()),"FROZEN_GUARD_PROVENANCE_CONFLICT")
    proof = fold_proof(folds,files.read_json(root/unique_path(inventory,"fold_references_v1.json")),
        files.read_json(root/unique_path(inventory,"dm_b_v1_recipe_fold_metrics.json"))["folds"])
    points = files.read_json(root/(BASE+"/detector_operating_points_v1.json"))["results"]
    require(tuple(p["budget"] for p in points)==(.01,.03,.05),"HISTORICAL_BUDGETS_CHANGED")
    roles = {p:name for name,p in paths.items()}
    sources = [dict(logical_role=roles.get(p,"ACCEPTED_PROVENANCE_OR_REFERENCE"),source_path=p,sha256=h,
        size_bytes=(root/p).stat().st_size) for p,h in sorted(hashes.items())]
    import_manifest = dict(import_version="r0_reproduction_import_manifest_v1",pre_R0_machinery_commit=PRE_R0_COMMIT,
        accepted_cycle1_commit=CYCLE1,accepted_publication=ANCHOR,accepted_publication_sha=hashes[ANCHOR],sources=sources,
        manifest_sha=MEMBERSHIP_SHA,fold_sha=FOLD_SHA,population_count=1135,attack_count=183,benign_count=952,
        frozen_regime_manifest_file_sha=hashes[R0],frozen_regime_manifest_hash=manifest.manifest_hash,
        detector_mapping=MAPPING,primary_order=list(PRIMARY),fold_proof=proof,
        historical_models={"ds_v2":dict(evidence_kind="OOF",recipe="B2+S0 LogisticRegression",source_path=paths["D_S_B2_LR"],
            source_sha=hashes[paths["D_S_B2_LR"]],run_code_commit=ds_run["code_commit"],score_semantics="UNCALIBRATED_CLASS1_PROBABILITY",not_final_model_inference=True),
            "dm_b_v1":dict(evidence_kind="OOF",source_path=paths["D_M-B_v1"],source_sha=hashes[paths["D_M-B_v1"]],
                run_code_commit=sem_run["code_commit"],score_semantics="UNCALIBRATED_CLASS1_SOFTMAX_256_TOKEN_PREFIX",not_final_model_inference=True),
            "dg_v1":dict(evidence_kind="FROZEN_DIRECT_DEVELOPMENT",source_path=paths["D_G_v1"],source_sha=hashes[paths["D_G_v1"]],
                run_code_commit=dg_run["code_commit"],revision=dg_run["revision"],score_semantics="MAX_CHUNK_MALICIOUS_CLASS_SOFTMAX",native_vote="OR_CHUNK_ARGMAX_CLASS1")},
        score_direction="higher_is_more_adversarial",decision_provenance="Accepted stored pooled descriptive thresholds; inclusive >=; no Phase-5 thresholds",
        historical_adapter="Strict metadata-only historical score import into AlignedEvaluation; NOT a final-model PredictionRecord or a live DetectorAdapter result",
        native_fields="Source records preserved byte-identically; historical decisions are separate explicit decisions, not overwritten native predictions",
        historical_rng="python.random.Random/MT19937; seed reset per budget; sorted lineage keys and randrange",production_rng="numpy.Generator/PCG64",
        rng_difference_resolved="Explicit separately identified legacy draw replay; production contract and defaults unchanged",new_inference=False,protected_data=False)
    return dict(root=root,publication=publication,core=core,hashes=hashes,manifest=manifest,detectors=detectors,paths=paths,points=points,import_manifest=import_manifest)


def historical_decisions(history):
    import_sha = hashlib.sha256(files.manifest_bytes(history["import_manifest"])).hexdigest()
    samples = {s.sample_id:s for s in history["manifest"].samples}
    rows = []
    for budget in history["points"]:
        budget_id = str(round(100*budget["budget"]))+"PCT"
        points = {p["detector"]:p for p in budget["metrics"]}
        for name,detector_id in MAPPING.items():
            point = points[name]
            for row in history["detectors"][name]:
                threshold = point["threshold"]
                rows.append(dict(sample_id=row["sample_id"],truth_label=row["truth_label"],detector_id=detector_id,budget_id=budget_id,
                    score=row["score"],explicit_binary_decision=int(threshold is not None and row["score"]>=threshold),
                    explicit_decision_provenance_id="HISTORICAL_DESCRIPTIVE_"+budget_id+"_V1::"+import_sha,
                    source_artifact_sha=history["hashes"][history["paths"][name]],lineage_id=samples[row["sample_id"]].lineage_id,
                    historical_threshold=threshold,source_artifact_path=history["paths"][name],fold=samples[row["sample_id"]].outer_fold,
                    model_evidence_kind=history["import_manifest"]["historical_models"][detector_id]["evidence_kind"]))
    order = {v:i for i,v in enumerate(MAPPING.values())}
    return sorted(rows,key=lambda r:(int(r["budget_id"][:-3]),r["sample_id"],order[r["detector_id"]]))


def align_history(history, decisions, budget_id):
    manifest = history["manifest"]
    selected = [r for r in decisions if r["budget_id"]==budget_id]
    ids = tuple(MAPPING.values())
    by_key = {(r["sample_id"],r["detector_id"]):r for r in selected}
    require(len(by_key)==len(selected)==3*len(manifest.samples),"HISTORICAL_DECISIONS_INCOMPLETE_OR_DUPLICATE")
    import_sha = hashlib.sha256(files.manifest_bytes(history["import_manifest"])).hexdigest()
    provenance_id = "HISTORICAL_DESCRIPTIVE_"+budget_id+"_V1::"+import_sha
    expected = {(s.sample_id,d) for s in manifest.samples for d in ids}
    require(set(by_key)==expected,"HISTORICAL_DECISION_MEMBERSHIP_CONFLICT")
    rows = []
    for sample in manifest.samples:
        votes = []
        for detector_id in ids:
            record = by_key[sample.sample_id,detector_id]
            require(record["explicit_decision_provenance_id"]==provenance_id,"HISTORICAL_EXPLICIT_PROVENANCE_REQUIRED")
            require(type(record["explicit_binary_decision"]) is int and record["explicit_binary_decision"] in (0,1),"HISTORICAL_BINARY_DECISION_REQUIRED")
            require(record["truth_label"]==sample.truth_label and record["lineage_id"]==sample.lineage_id and record["fold"]==sample.outer_fold,"HISTORICAL_DECISION_METADATA_CONFLICT")
            model = history["import_manifest"]["historical_models"][detector_id]
            require(record["source_artifact_sha"]==model["source_sha"] and record["source_artifact_path"]==model["source_path"]
                    and record["model_evidence_kind"]==model["evidence_kind"],"HISTORICAL_MODEL_PROVENANCE_CONFLICT")
            source_name = next(k for k,v in MAPPING.items() if v==detector_id)
            source_scores = {r["sample_id"]:r["score"] for r in history["detectors"][source_name]}
            point = next(p for b in history["points"] if round(100*b["budget"])==int(budget_id[:-3]) for p in b["metrics"] if p["detector"]==source_name)
            require(record["score"]==source_scores[sample.sample_id] and record["historical_threshold"]==point["threshold"],"HISTORICAL_SCORE_OR_THRESHOLD_CHANGED")
            require(record["explicit_binary_decision"]==int(point["threshold"] is not None and record["score"]>=point["threshold"]),"HISTORICAL_EXPLICIT_DECISION_CHANGED")
            votes.append(record["explicit_binary_decision"])
        rows.append(AlignedRow(sample_id=sample.sample_id,truth_label=sample.truth_label,is_adversarial=sample.is_adversarial,
            partition=sample.partition,threat_regime=sample.threat_regime,lineage_id=sample.lineage_id,parent_sample_id=sample.parent_sample_id,
            valid_attack_attempt=sample.valid_attack_attempt,target_detector=sample.target_detector,attack_success_definition=sample.attack_success_definition,
            attack_success=sample.attack_success,attack_method=sample.attack_method,attack_method_revision=sample.attack_method_revision,
            sample_metadata_sha=digest(sample.model_dump(mode="json")),decisions=tuple(votes)))
    class AcceptedOK:
        status="OK"
    one=coverage(len(rows),[AcceptedOK() for _ in rows],0)
    total=coverage(3*len(rows),[AcceptedOK() for _ in range(3*len(rows))],0)
    provenance=EvaluationProvenance(experiment_id=manifest.experiment_id,decision_view="EXPLICIT",partition=manifest.partition,
        threat_regime=manifest.threat_regime,evidence_kind=manifest.evidence_kind,regime_manifest_sha=manifest.manifest_hash,
        detector_manifest_sha=PHASE2_SHA,prediction_schema_sha=PREDICTION_SHA,regime_contract_sha=REGIME_SHA,
        operational_prediction_schema_sha=None,operating_policy_sha=None,prediction_batch_sha=digest(selected),
        explicit_decisions_sha=digest([(r["sample_id"],r["detector_id"],r["explicit_binary_decision"]) for r in selected]),
        explicit_provenance_id=provenance_id,primary_detector_labels=PRIMARY,primary_detector_ids=ids,
        operational_thresholds=None,operational_threshold_ids=None)
    payload=dict(provenance=provenance,rows=tuple(rows),coverage=total,detector_coverage=(one,one,one))
    plain=dict(table_version="aligned_evaluation_v1",**{k:[r.model_dump(mode="json") for r in v] if isinstance(v,tuple) else v.model_dump(mode="json") for k,v in payload.items()})
    return AlignedEvaluation(**payload,alignment_sha=digest(plain)).require_complete()


def assert_close(actual, expected, name):
    require(actual is not None and expected is not None and abs(actual-expected)<=1e-12,"R0_FLOAT_REPRODUCTION_MISMATCH: "+name)


def reproduce(history, decisions, *, include_uncertainty=True):
    from detection_service.analysis.common_mode import fixed_fpr
    from detection_service.analysis.development_characterization import characterization
    root = history["root"]
    accepted = files.read_json(root/(BASE+"/full_analysis_v1.json"))
    tables,results = {},{}
    for budget_id in ("1PCT","3PCT","5PCT"):
        table = align_history(history,decisions,budget_id)
        result = evaluate_core(table)
        tables[budget_id],results[budget_id] = table,result
        budget = next(b for b in accepted["budgets"] if round(b["budget"]*100)==int(budget_id[:-3]))
        for name,detector_id in MAPPING.items():
            expected = next(p for p in budget["individual"] if p["detector"]==name)
            actual = next(d for d in result.individual.detectors if d.detector_id==detector_id)
            require(all(getattr(actual,k)==expected[k] for k in ("tp","fn","fp","tn")),"R0_INTEGER_REPRODUCTION_MISMATCH: "+budget_id+"/"+name)
        for pair in result.common_mode.pairs:
            names = {k for k,v in MAPPING.items() if v in (pair.left_detector,pair.right_detector)}
            reference = next(p for p in budget["pairwise"] if {p["left"],p["right"]}==names)
            require(pair.shared_fn_count==reference["jfn_count"],"R0_SHARED_FN_INTEGER_MISMATCH")
            for name in ("jfn","independence_reference","ejf","fn_jaccard"):
                assert_close(getattr(pair,name).value,reference[name],budget_id+"/"+name)
        stack = next(s for s in budget["stacks"] if s["stack"]=="DEVELOPMENT_STACK_CANDIDATE")
        require(result.common_mode.all_three_fn_count==stack["all_detector_fn_count"],"R0_ALL_THREE_INTEGER_MISMATCH")
        for name,detector_id in MAPPING.items():
            ref=next(r for r in budget["unique"] if r["stack"]=="DEVELOPMENT_STACK_CANDIDATE" and r["detector"]==name)
            actual=next(d for d in result.recovery.detectors if d.detector_id==detector_id)
            require((actual.unique_catch_count,actual.both_others_miss_count)==(ref["unique_catch_count"],ref["other_members_miss_count"]),"R0_RECOVERY_INTEGER_MISMATCH")
            assert_close(actual.conditional_recovery.value,ref["recovery_given_others_miss"],budget_id+"/recovery")
    # Freeze a reusable descriptive selector only after exact stored-threshold reproduction.
    frontier = {}
    ranking = {}
    publication_rows=files.read_json(root/(PUB+"/table_2_individual.json"))["rows"]
    for name,detector_id in MAPPING.items():
        rows=history["detectors"][name]
        labels,scores = [r["truth_label"] for r in rows],[r["score"] for r in rows]
        points=fixed_fpr(labels,scores)
        stored=[next(p for p in b["metrics"] if p["detector"]==name) for b in history["points"]]
        require(all(p["threshold"]==s["threshold"] and all(p[k]==s[k] for k in ("tp","fn","fp","tn")) for p,s in zip(points,stored)),"DESCRIPTIVE_FRONTIER_REQUIRES_REVIEW")
        frontier[detector_id]=points
        metrics=characterization(labels,scores,[False]*len(labels))
        reference=next(r for r in publication_rows if r["detector"]==name)
        for key in ("roc_auc","pr_auc"):
            assert_close(metrics[key],reference[key],detector_id+"/"+key)
        ranking[detector_id]=dict(roc_auc=metrics["roc_auc"],average_precision=metrics["pr_auc"],
            historical_field="pr_auc",pr_metric_definition="AVERAGE_PRECISION_WHOLE_TIED_BLOCKS",score_source_sha=history["hashes"][history["paths"][name]])
    uncertainty={}
    production=None
    if include_uncertainty:
        names=("pair/dm_b_v1/dg_v1/jfn","pair/ds_v2/dg_v1/jfn","all_three/jfn")
        legacy_names={names[0]:"jfn/D_G_v1/D_M-B_v1",names[1]:"jfn/D_G_v1/D_S_B2_LR",names[2]:"all_detector_jfn/DEVELOPMENT_STACK_CANDIDATE"}
        for budget_id,table in tables.items():
            replay=replay_historical_uncertainty(table,names)
            reference=next(b for b in accepted["budgets"] if round(b["budget"]*100)==int(budget_id[:-3]))["bootstrap"]
            for interval in replay["intervals"]:
                ref=reference["intervals"][legacy_names[interval["metric_id"]]]
                for a,b in (("point_estimate","estimate"),("ci_lower","lower"),("ci_upper","upper")):
                    assert_close(interval[a],ref[b],budget_id+"/historical_ci/"+a)
            replay["historical_reproduction_status"]="PASS"
            uncertainty[budget_id]=replay
        production=bootstrap_metrics(tables["3PCT"],names,BootstrapConfig(unit="LINEAGE_CLUSTERED",domain="ATTACK_ONLY"))
    bundle=result_bundle(tables["3PCT"],history["manifest"],"HISTORICAL_DESCRIPTIVE_3PCT_V1",uncertainty=(production,) if production else ())
    return dict(tables=tables,results=results,ranking=ranking,frontier=frontier,historical_uncertainty=uncertainty,
        production_uncertainty=production,bundle=bundle,matrix=cross_regime_matrix((bundle,),reference_slot="R0"))


def artifacts(root=files.ROOT, *, history=None):
    history=load_history(root) if history is None else history
    decisions=historical_decisions(history)
    result=reproduce(history,decisions)
    outputs={IMPORT:files.manifest_bytes(history["import_manifest"]),DECISIONS:csv_bytes(decisions)}
    for name,section in (("individual","individual"),("common_mode","common_mode"),("failure_patterns","failure_patterns"),("recovery","recovery")):
        outputs[OUT+"/r0_"+name+"_reproduction_v1.json"]=files.manifest_bytes({k:getattr(v,section).model_dump(mode="json") for k,v in result["results"].items()})
    outputs[OUT+"/r0_score_metrics_reproduction_v1.json"]=files.manifest_bytes(result["ranking"])
    outputs[OUT+"/r0_uncertainty_reproduction_v1.json"]=files.manifest_bytes(dict(historical_replay=result["historical_uncertainty"],
        phase11_production_PCG64=result["production_uncertainty"].model_dump(mode="json"),rng_method_difference_resolved=True,production_contract_unchanged=True))
    outputs[OUT+"/r0_descriptive_frontier_v1.json"]=files.manifest_bytes(dict(frontier_version="descriptive_frontier_v1",
        selector_source="detection_service.analysis.common_mode.fixed_fpr",selector_source_sha=history["hashes"]["detection_service/analysis/common_mode.py"],
        policy="Inclusive >= whole tied blocks; maximize recall subject to budget; minimize FPR; highest threshold on tied counts; None means no positive predictions",
        scope="DESCRIPTIVE_ONLY_NOT_OPERATIONAL",points=result["frontier"],stored_thresholds_reproduced=True))
    outputs[OUT+"/r0_cross_regime_bundle_v1.json"]=files.manifest_bytes(result["bundle"].model_dump(mode="json"))
    outputs[OUT+"/r0_cross_regime_matrix_v1.json"]=files.manifest_bytes(result["matrix"])
    report=dict(report_version="r0_reproduction_report_v1",status="PASS",population_count=1135,attack_count=183,benign_count=952,
        pre_R0_machinery_commit=PRE_R0_COMMIT,import_manifest_sha=hashlib.sha256(outputs[IMPORT]).hexdigest(),
        decision_artifact_sha=hashlib.sha256(outputs[DECISIONS]).hexdigest(),decision_rows=len(decisions),
        integer_counts="EXACT_AT_ALL_THREE_BUDGETS",derived_metric_tolerance=1e-12,ranking_tolerance=1e-12,historical_ci_tolerance=1e-12,
        alignment_shas={k:v.alignment_sha for k,v in result["tables"].items()},historical_uncertainty="PASS_EXPLICIT_LEGACY_RNG_REPLAY",
        production_rng="NUMPY_PCG64_UNCHANGED",historical_rng="PYTHON_RANDOM_MT19937",method_difference="EXPLICIT_AND_RESOLVED_NOT_IDENTICAL_RNG",
        descriptive_frontier_reproduced=True,new_model_inference=False,OOF_final_model_substitution=False,operational_thresholds_used=False,
        future_regimes=result["matrix"]["regime_status"],Cycle2="DEFERRED",Phase14="NOT_STARTED",
        source_hash_checks=len(history["hashes"]),fold_membership_hash_checks=20)
    outputs[OUT+"/r0_reproduction_report_v1.json"]=files.manifest_bytes(report)
    return outputs,report


def freeze(root=files.ROOT):
    root=Path(root)
    history=load_history(root)
    require((root/IMPORT).read_bytes()==files.manifest_bytes(history["import_manifest"]),"VERIFIED_IMPORT_MANIFEST_REQUIRED_BEFORE_DECISIONS")
    outputs,report=artifacts(root,history=history)
    require(not any((root/p).exists() for p in (*[p for p in outputs if p!=IMPORT],HASHES)),"REFUSE_R0_REPRODUCTION_OVERWRITE")
    for p,data in outputs.items():
        if p==IMPORT:
            continue
        with (root/p).open("xb") as stream:
            stream.write(data)
    from detection_service.research_protocol.uncertainty_contract import HASHES as PRE_HASHES
    prior=files.read_json(root/PRE_HASHES)["sha256"]
    inventory=dict(artifact_version="phase11_13_artifact_hashes_v1",pre_R0_machinery_commit=PRE_R0_COMMIT,
        sha256={**prior,PRE_HASHES:files.sha(root/PRE_HASHES),**{p:files.sha(root/p) for p in (*outputs,*CODE,*REPORTS)}})
    with (root/HASHES).open("xb") as stream:
        stream.write(files.manifest_bytes(inventory))
    return report


def freeze_import(root=files.ROOT):
    root=Path(root)
    history=load_history(root)
    with (root/IMPORT).open("xb") as stream:
        stream.write(files.manifest_bytes(history["import_manifest"]))
    return dict(status="VERIFIED_IMPORT_MANIFEST_FROZEN",source_hash_checks=len(history["hashes"]),
        path=IMPORT,sha256=files.sha(root/IMPORT),rows=1135,positive=183,negative=952,new_inference=False)


def check(root=files.ROOT):
    root=Path(root)
    inventory=files.read_json(root/HASHES)["sha256"]
    require(all(files.sha(root/p)==h for p,h in inventory.items()),"PHASE11_13_ARTIFACT_HASH_MISMATCH")
    outputs,report=artifacts(root)
    require(all((root/p).read_bytes()==data for p,data in outputs.items()),"R0_REPRODUCTION_NONDETERMINISTIC")
    return dict(**report,phase11_13_hash_checks=len(inventory),deterministic_reconstruction="BYTE_IDENTICAL")


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode",choices=("import","freeze","check"),default="check")
    mode=parser.parse_args().mode
    print(json.dumps(freeze_import() if mode=="import" else freeze() if mode=="freeze" else check(),indent=2))
