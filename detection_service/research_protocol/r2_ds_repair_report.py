"""Close the narrow unresolved repair without authorizing another model call."""

import json
import subprocess
import sys
import xml.etree.ElementTree as ET

from detection_service.research_protocol import r2_ds_predeclare as p,r2_ds_replay_diagnosis as diag,protocol_patch_001 as patch
from detection_service.research_protocol.release_validation import check_acceptance


def run():
    first=p.files.read_json(diag.OUT/'ds_baseline_replay_first_seed_v1.json')
    trace=p.files.read_json(diag.OUT/'ds_baseline_pipeline_comparison_v1.json')
    audit=p.files.read_json(diag.OUT/'ds_baseline_replay_all_seeds_v1.json')
    p.require(trace['primary_root_cause']=='UNKNOWN' and audit['status']=='NOT_RUN','UNRESOLVED_CLOSEOUT_REQUIRED')
    receipts=[]
    cases=[]
    for name,expected in (('r2_ds_repair_tests.xml',109),('r2_ds_repair_preservation_tests.xml',72)):
        path=p.ROOT/'tmp'/name
        tests=list(ET.parse(path).getroot().iter('testcase'))
        p.require(len(tests)==expected and not any(t.find(tag) is not None for t in tests for tag in ('failure','error','skipped')),'REPAIR_REGRESSION_NOT_PASS')
        cases.extend(t.attrib['classname']+'::'+t.attrib['name'] for t in tests)
        receipts.append(dict(path=path.relative_to(p.ROOT).as_posix(),sha256=p.files.sha(path),passed=len(tests)))
    p.require(len(cases)==len(set(cases)),'DUPLICATE_TEST_CASE')
    baseline=json.loads(subprocess.check_output([sys.executable,'-B','-m','detection_service.scripts.verify_quality_preservation','--mode','check'],cwd=p.ROOT))
    p.require(baseline['status']=='PASS' and baseline['hash_checks']==96,'BASELINE_FAILURE')
    p.require(p.git('rev-parse','prep/r3-verifier-001').decode().strip()=='0cd2d506380cbb3ec513207e4fa66ad422d2b3f2','TRACK_B_DRIFT')
    for binding in ('query_journal','pipeline_capture'):
        p.require(p.digest(first[binding]['path'])==first[binding]['sha256'],'DIAGNOSTIC_BINDING_DRIFT')
    archive=diag.PRIVATE/'diagnostic_query_journal_code_v1.py'
    p.require(p.files.sha(archive)==first['code_sha256']['r2_ds_query_journal.py'],'DIAGNOSTIC_CODE_ARCHIVE_DRIFT')
    snapshot=p.files.read_json(p.OUT/'r2_ds_predeclaration_v1.json')['preservation_sha256']
    artifact_paths=p.git('ls-tree','-r','--name-only','5f5e6f4','--','artifacts/research_protocol/r2_ds','reviews/R2_DS_TARGETED_EVASION_RESULTS_v1.md').decode().splitlines()
    p.require(all((p.ROOT/path).read_bytes()==p.git('show','5f5e6f4:'+path) for path in artifact_paths),'PRIOR_DS_EVIDENCE_DRIFT')
    evidence=dict(status='BLOCKED',final_verdict='R2_DS_BASELINE_REPLAY_STILL_UNRESOLVED',
        starting_head='5f5e6f4b159fb2aa75bec9a3f26360b776e4afc0',branch='exp/r2-ds-001',
        primary_root_cause='UNKNOWN',first_observed_divergence=trace['first_observed_divergence'],first_causal_divergence='UNKNOWN',
        historical_failed_attempt_queries='UNKNOWN_EXACT_COUNT_BOUNDED_1_TO_61',current_diagnostic_queries=1,
        baseline_audit_queries=0,authoritative_restart_attack_queries=0,D_M_B_generation_queries=0,D_G_generation_queries=0,ensemble_generation_queries=0,
        diagnostic_logical_queries=1,diagnostic_unique_model_queries=1,
        journal_schema_version='r2_ds_query_journal_v1',journal_schema_sha256=p.files.sha(diag.OUT/'ds_query_journal_schema_v1.json'),
        journal_durability='Exclusive new run file, append-only unbuffered JSONL, complete-write loop and os.fsync before post-query gates; separate fsync-backed logical-request ledger for future calls/cache hits.',
        first_diagnostic_code_archive=dict(path=archive.relative_to(p.ROOT).as_posix(),sha256=p.files.sha(archive)),
        query_journal=first['query_journal'],all_seed_audit=audit,
        tests=dict(passed=len(cases),failed=0,errors=0,skipped=0,receipts=receipts,
            note='The all-seed audit predicate tests use synthetic engineering rows; no real 698-seed audit was run.'),
        preservation=dict(source_hash_checks=p.preserved(),baseline=baseline,release=check_acceptance(),patch_hash_checks=len(patch.verify_patch()['sha256']),
            prior_ds_artifacts_unchanged=len(artifact_paths),Track_B_head='0cd2d506380cbb3ec513207e4fa66ad422d2b3f2'),
        scientific_changes=False,packages_changed=False,tolerance_changed=False,
        full_generation_journal_wiring_tested_synthetically=True,live_all_seed_audit_passed=False,
        restart_receipt_created=False,generation_resumed=False,terminal_freeze_commit=None,transfer_scoring_commit=None,analysis_result_commit=None,
        R2_DG_started=False,R3_started=False,verifier_started=False,protected_evaluation_started=False,
        diagnostic_sha256={path.name:p.files.sha(path) for path in diag.OUT.glob('*.json')},
        repair_code_sha256={name:p.files.sha(p.ROOT/'detection_service/research_protocol'/name) for name in
            ('r2_ds_generate_run.py','r2_ds_generator.py','r2_ds_query_journal.py','r2_ds_repair_evidence.py','r2_ds_replay_diagnosis.py','r2_ds_repair_report.py')})
    p.publish(diag.OUT/'ds_repair_acceptance_v1.json',evidence)
    text='# R2-DS-001 REPAIR AND RESUMPTION REPORT\n\nSTATUS: BLOCKED\n\n'
    text+='## Root Cause\n\nPrimary category: **UNKNOWN**. No input-identity or accepted-runtime-binding mismatch was found. The first observed difference is raw class-1 probability (stage P), but the first causal divergence cannot be localized: R1 did not retain this seed\'s token IDs, surprisals or 26-feature vector. Live LR reconstruction and both stored/live Platt reconstructions match exactly. Numerical-environment variation is not proven; no package or runtime changes were made to chase a matching score.\n\n'
    text+='Secondary contributor: incomplete historical intermediate/environment telemetry limits diagnosis. This is not evidence that frozen R1 is defective. The historical first-parent search ran before its baseline gate; none of its unpersisted candidate outcomes were inspected or used to modify the algorithm.\n\n'
    text+='## First-Seed Replay\n\n'
    for label,key in [('Sample ID','sample_id'),('Parent UTF-8 SHA-256','input_sha256'),('Input bytes','input_byte_length'),('Frozen R1 raw score','raw_frozen_r1_score'),('Live raw score','raw_live_score'),('Raw delta','raw_absolute_delta'),('Frozen R1 calibrated score','calibrated_frozen_r1_score'),('Live calibrated score','calibrated_live_score'),('Calibrated delta','calibrated_absolute_delta')]:
        text+=label+': `'+str(first[key])+'`.\n\n'
    text+='Native and operational decisions match (1/1). Token counts match: 101 input, 100 analyzed; no truncation. Raw/calibrated tolerance remains **1e-12**; this replay FAILS both score checks. Unchanged decisions do not waive the gate. Input, request and engine text hashes are identical. Frozen model/reference/tokenizer/schema/calibrator identities and numerical environment are recorded in the first-seed diagnostic.\n\n'
    text+='## Pipeline Evidence\n\n```json\n'+json.dumps(trace,indent=2,sort_keys=True)+'\n```\n\n'
    text+='## All-Seed Replay Audit\n\nExpected seeds: 698. Replayed in the all-seed audit: **0**. Audit verdict: **NOT_RUN**, because the root cause is UNKNOWN and Section 13 requires stopping. Maximum/median deltas, count above tolerance and decision mismatches for the all-seed population are unavailable, not zero. The single first-seed diagnostic is counted separately. No first-seed fix or all-seed PASS is claimed.\n\n'
    text+='## Query Accounting\n\nHistorical failed attempt exact count known: NO; bound 1-61 remains UNKNOWN_EXACT_COUNT_BOUNDED_1_TO_61. Current diagnostic baseline calls: **1**, logical requests: 1, unique model calls: 1. All-seed audit calls: 0. Authoritative restart attack calls: **0**. D_M-B/D_G/ensemble generation calls: **0/0/0**.\n\n'
    text+='Durable model journal: YES, `'+first['query_journal']['path']+'`; SHA `'+first['query_journal']['sha256']+'`. New journal schema: `r2_ds_query_journal_v1`, SHA `'+evidence['journal_schema_sha256']+'`. Returned scores are fsynced before status/replay checks; subsequent logical requests and cache hits have a separate fsynced ledger. The first diagnostic used the preceding model-return ledger version, whose exact code bytes are archived locally and hash-bound; it made only one logical request and one model call. No original diagnostic receipt was rewritten after the logical-ledger enhancement.\n\n'
    text+='## Accounting Repair\n\nGeneration now logs returned raw/calibrated scores before assertions and checks frozen raw/calibrated/native/operational baseline equivalence before saliency. Cache-hit logical receipts do not add model calls. The entry point rejects an UNKNOWN diagnosis or non-PASS all-seed audit. Restart gating requires seed 1; previous invocation files remain preserved, not resumed or merged. Full restart receipt/bookkeeping is NOT created because the prerequisite audit did not pass. No live repaired generation was run.\n\n'
    text+='## Scientific Integrity\n\nSeed membership, objective, operators/order, padding, saliency, ranking/ties, 61-query budget, threshold, success criterion, validity, lineage and random seed: UNCHANGED. No tolerance relaxation, score rounding, clipping change, retraining, calibration fit, source normalization or package upgrade/downgrade. R0/R1/R2-DMB and the accepted protocol patch remain unchanged. Track B remains `0cd2d506380cbb3ec513207e4fa66ad422d2b3f2`; no worktree or merge change. No R2-DG/R3/verifier/protected evaluation.\n\n'
    text+='## Repair Git\n\nStarting HEAD: `'+evidence['starting_head']+'`. Branch: `exp/r2-ds-001`. Diagnosis/accounting evidence commit and final HEAD are reported externally after commit/push to avoid self-reference. This is a BLOCKED diagnosis/accounting commit, not an accepted all-seed runtime repair. Restart-receipt, terminal-freeze, transfer-scoring and accepted-result analysis commits: NONE. No raw prompts, model weights or private pipeline/journal contents are committed.\n\n'
    text+='## R2-D_S Final Result\n\n**NOT_RUN**. No authoritative restart, accepted terminals, evasion rates/CIs, transfer rates/CIs or common-mode result exists.\n\n'
    text+='## Tests And Preservation\n\n```json\n'+json.dumps(dict(tests=evidence['tests'],preservation=evidence['preservation']),indent=2)+'\n```\n\n'
    text+='Tests include all requested narrow-repair predicates and synthetic failure injection. Synthetic 698-row validation is not relabeled as real replay. Original R2-DS blocked-state artifacts and report remain byte-identical.\n\n'
    text+='## FINAL VERDICT\n\n**R2_DS_BASELINE_REPLAY_STILL_UNRESOLVED**\n\nTHE ROOT CAUSE WAS: UNKNOWN; the replay divergence is confirmed upstream of calibration, but the first causal stage is not supported by retained R1 intermediate evidence.\n\nTHE REPAIR DID NOT CHANGE THE EXPERIMENT BECAUSE: Only diagnostic capture, durable query/logical accounting and fail-closed pre-query gates changed; every frozen scientific choice and accepted artifact is preserved.\n\nNEXT AUTHORIZED STEP: Stop and request review of a separately scoped numerical/runtime diagnosis; do not start R2-DG, R3 or a generation restart.\n'
    path=p.ROOT/'reviews/R2_DS_REPAIR_AND_RESUMPTION_REPORT_v1.md'
    p.require(not path.exists(),'REPAIR_REPORT_EXISTS')
    with path.open('xb') as stream:
        stream.write(text.encode('ascii'))
    p.publish(diag.OUT/'ds_repair_report_binding_v1.json',dict(path=path.relative_to(p.ROOT).as_posix(),sha256=p.files.sha(path)))
    print(json.dumps({key:evidence[key] for key in ('status','final_verdict','tests','preservation','current_diagnostic_queries')},indent=2))


if __name__=='__main__':
    run()
