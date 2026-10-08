# Merge Gate 1 preparation v1

Status: PREPARATION_ONLY; no merge/cherry-pick performed.

Committed Track A snapshot: `bdecf702b09db2a2bdc9447d42e1bc83642c8dfb`; common ancestor: `99b012e5b72fbae9273fa73ccc8d84d579a69c83`.
Only Git refs, filenames and committed test source were inspected. Live scientific outcomes were not read.
Track A may advance. Refresh and repeat the overlap analysis after its accepted final closeout.

## Proposed integration order

1. e37c91dfce79f15a50d8cc12288b9f19cd01c9c7 â€” exp(r3): predeclare ensemble-aware evasion experiment â€” SAFE_CHERRY_PICK
2. c4d0830fdb69a704bc2213e4b461dc983ecd5012 â€” feat(r3): prepare ensemble attack infrastructure with synthetic tests â€” SAFE_CHERRY_PICK
3. b70a3d42aff2907e61fd1b2aa03cceb7dbe2b773 â€” research(verifier): predeclare recovery study and prepare adapters â€” SAFE_CHERRY_PICK
4. 0cd2d506380cbb3ec513207e4fa66ad422d2b3f2 â€” docs(repro): audit frozen-stack artifact portability â€” SAFE_CHERRY_PICK
5. 463e88a972ce31b4c1c66c9f5e92beaaba9d6d3b â€” docs(repro): verify frozen DMB bytes and record blocked remote backup â€” SAFE_CHERRY_PICK
6. 3ed1ad4fdf8f7a7288351382ee7cf3880a998131 â€” docs(repro): resolve DG provenance hash binding â€” SAFE_CHERRY_PICK
7. c75483939b635b31261f3bf6a83555db76bc7718 â€” chore(verifier): validate runtime and access readiness â€” SAFE_CHERRY_PICK
8. B8_SELF (resolve exact title after commit) â€” docs(integration): prepare merge gate and R2-DG decision â€” SAFE_CHERRY_PICK

No direct committed path overlaps at this snapshot. Every changed file, its commit
and import dependency check appears in merge_gate_1_plan_v1.json. These are structural
checks, not a claim that final integration tests have run. No existing Track B files
were modified; accepted R3/verifier design remains frozen. B5 truthfully records a
blocked backup, so cherry-picking it does not establish remote portability.

## MODEL_FREE_REQUIRED

Run every command separately after Track A finishes, in its accepted runtime:

`python -B -m pytest detection_service/tests/test_r2_ds_predeclaration.py -q`
`python -B -m pytest detection_service/tests/test_r2_ds_generator.py -q`
`python -B -m pytest detection_service/tests/test_r2_ds_authoritative_v2.py -q`
`python -B -m pytest detection_service/tests/test_r2_ds_repair.py -q`
`python -B -m pytest detection_service/tests/test_r2_ds_analysis_synthetic.py -q`
`python -B -m pytest detection_service/tests/test_r2_ds_freeze_outputs.py -q`
`python -B -m pytest detection_service/tests/test_r2_ds_results.py -q`
`python -B -m pytest detection_service/tests/test_ds_numerical_disposition.py -q`
`python -B -m pytest detection_service/tests/test_ds_numerical_diagnosis.py -q`
`python -B -m pytest detection_service/tests/test_r2_dmb_predeclaration.py -q`
`python -B -m pytest detection_service/tests/test_r2_dmb_generator.py -q`
`python -B -m pytest detection_service/tests/test_r2_dmb_analysis_synthetic.py -q`
`python -B -m pytest detection_service/tests/test_r2_dmb_freeze_outputs.py -q`
`python -B -m pytest detection_service/tests/test_r2_dmb_results.py -q`
`python -B -m pytest detection_service/tests/test_r1_corpus.py -q`
`python -B -m pytest detection_service/tests/test_r1_experiment.py -q`
`python -B -m pytest detection_service/tests/test_r1_source_gate.py -q`
`python -B -m pytest detection_service/tests/test_r0_operational.py -q`
`python -B -m pytest detection_service/tests/test_r0_reproduction.py -q`
`python -B -m pytest detection_service/tests/test_protocol_lock.py -q`
`python -B -m pytest detection_service/tests/test_protocol_patch_001.py -q`
`python -B -m pytest detection_service/tests/test_protocol_release.py -q`
`python -B -m pytest detection_service/tests/test_protocol_release_audit.py -q`
`python -B -m unittest detection_service.tests.test_r3_preparation -v`
`python -B -m unittest detection_service.tests.test_verifier_preparation -v`
`python -B -m unittest detection_service.tests.test_track_b_portability -v`
`python -B -m unittest detection_service.tests.test_track_b_002 -v`

Refresh this list for any additional R2-D_S preservation tests introduced by final
closeout. Evidence fixtures must exist and match hashes; a missing prerequisite is
a failed integration gate, not a reason to regenerate evidence. R2-D_S, DMB, R1,
R0, protocol patch and release hash preservation are mandatory.

## MODEL_RUNTIME_REQUIRED

After authorization, exact frozen artifact loader/hash preflight for DS/DMB/DG with no fitting.
FrozenDSAdapter identity validation and accepted_ds_adapter() live load; DetectorAdapter(D_M-B) and DetectorAdapter(D_G) exact artifact loads.
Run authorized synthetic-input smoke predictions only if separately authorized after Track A; never protected samples or scientific verifier population.
V1/V2/V3 native loading and synthetic-input smoke require separate authorization/resource headroom; do not call preparation-only load_model() expecting live support.

## OPTIONAL_FRESH_CLONE

Follow FRESH_CLONE_PORTABILITY_PLAN_v1.md only after idle and authorization.
D_M-B remote backup is currently a blocker. No runtime execution or scientific inference was performed.


## Semantic test dependency (requires manual reconciliation)

Committed test_r2_ds_repair.py::test_track_b_preservation pins the mutable Track B
branch tip to 0cd2d506380cbb3ec513207e4fa66ad422d2b3f2. B5-B8 advance that branch
under this task's authorization, so the assertion becomes stale even with zero
direct file overlap. No Track A test was changed. After scientific closeout, the
lead must authorize semantic reconciliation to immutable original-snapshot
ancestry and hash preservation; do not blindly update a tip literal or relax
accepted scientific hashes. Preserve original preflight/diagnostic receipts.

Recommended integration strategy: MANUAL_RECONCILIATION with ordered cherry-picks.
B1-B4 are structurally SAFE_CHERRY_PICK; B5-B8 require the above test reconciliation.

Exact deferred model-runtime command (load-only; no scoring):

`python -B -m detection_service.research_protocol.track_b_post_idle_load_check --post-idle-authorized-gate-id <LEAD_AUTHORIZED_GATE_ID>`

This command loads one frozen detector at a time and performs no predict/detect
call, no sample access and no scientific equivalence claim. It has not run.
