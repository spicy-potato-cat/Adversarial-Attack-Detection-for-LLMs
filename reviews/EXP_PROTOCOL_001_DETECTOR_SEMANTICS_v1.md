# EXP-PROTOCOL-001 Phase 2: Frozen Detector Semantics

Status: **PASS (metadata/provenance contract only)**. Branch `exp/protocol-001`;
Cycle-1 base `dc6dd3041643fb70ad5b128d32c246f8763a8044`. No detector import,
model execution, dataset access, training, calibration fitting, R0 rescoring,
operational threshold selection, Cycle-2 work, or R1/R2/R3 execution occurred.
No Phase-3 prediction schema or Phase-4 regime schema was created.

## Primary Inventory

| Detector | Role | Model/revision | Artifact hash | Raw score | Score direction | Calibration | Threshold-input score | Binary semantics | Context/truncation/chunking | Operational threshold status |
|---|---|---|---|---|---|---|---|---|---|---|
| D_S (`ds_v2`) | PRIMARY_STATISTICAL | B2 + LR; reference DistilGPT2 at `2290a62682d06624634c1f46a6ad5be0f47f38aa` | `c5e754dc8b6e88b7437e4b81016e8f8ec23d018607d4f4e78906212b2a561157` | Uncalibrated LR class-1 probability | Higher = more adversarial | `ds_v2_cal_v1` | Calibrated probability (raw only when no calibrator supplied) | Probability >= 0.5; development convenience | 1024 LM context; first 4096 content tokens; LM overlap 64/stride 960; feature windows 128/64 | NOT_FROZEN |
| D_M-B (`dm_b_v1`) | PRIMARY_SEMANTIC | DistilRoBERTa at `fb53ab8802853c8e4fbdbcd0529f21fc6f459b2b` | `0bb192d2c468530479fa8ec0786f35d8bf5a8287e4ee401a953292d221736844` | Uncalibrated softmax class-1 ATTACK probability | Higher = more adversarial | `dm_b_v1_cal_v1` | Raw probability | Raw >= 0.5; unchanged by calibration; development convenience | Usable context 512; right truncation at 256 including specials; no chunking | NOT_FROZEN |
| D_G (`dg_v1`) | PRIMARY_EXTERNAL_GUARD | Meta Prompt Guard 2 22M at `11614a155199674a0a95e6602d6ab0417b790ed0` | Weights file: `5120e30bcd536ce285345d9ec104bea6bd6e8f94365b99a340c764f417ea5fa1` | Maximum temperature-1 malicious-class softmax over chunks | Higher = more adversarial | NONE | Native chunk argmax | OR(class-1 argmax); ties select class 0 | 512 context; 510 content + 2 specials; overlap 64/stride 446; full tail | NOT_FROZEN |

Primary order is exactly **D_S, D_M-B, D_G**. Detector identity, runtime ID, and
role are separately represented. `dm_a_v1` is **COMPARATOR_ONLY**, excluded from
primary membership and all-three metrics. Native ranges are [0,1]. All native
directions already agree with `HIGHER_IS_MORE_ADVERSARIAL`; no adapter inversion
or new transformed score is implemented.

## Provenance And Layout

The accepted common-003 preservation inventory explicitly records that its
branch predates final `ds_v2`/STACK-001. The final model, reference, calibration,
code and stack manifest remain byte-identical in accepted source commit
`e6b6a2af2a78e2a31aae6d9377378993f678b073` and the local archive
`detection_service/outputs/common003-preserved-stack/`.

This phase records both logical paths and actual archive locations. It does
**not** auto-merge that code, modify existing entry points, silently substitute
`ds_v1`, or claim the final D_S is importable at its logical active-tree path.
That known layout constraint must be addressed explicitly before a later
runtime harness can invoke the final D_S. It does not block static semantics
verification, and no runtime restoration is authorized by this inventory.

D_S implementation is `B2StatisticalDetector.detect`, with
`B2StatisticalDetector.from_artifact`, `B2Model.transform`, `B2Model.predict`,
and `load_calibration` in the preserved `statistical_v2` modules. Shared frozen
LM extraction is `statistical_oof_baseline.extractor`,
`PerplexityEngine.score/_score_chunk`, and `References.transform(item, 'B2')`.
D_M-B is `FineTunedSemanticDetector.from_artifact/detect/detect_batch` in
`detection_service/app/detectors/semantic_finetuned/detector.py`.
D_G is `GuardDetector.from_artifact/detect/_detect` and `guard.model.load_frozen`
in `detection_service/app/detectors/guard/`. All entry points, configuration,
model and calibration locations are recorded in the machine-readable inventory.
Implementation revisions identify accepted source bytes, not new model runs.

## D_S Notes

B2 schema `stat004_B2_v1`: 26 ordered features; SHA
`93d3892b158c35eccfadc27c879754db69ea5293782492ee5d4ff01a33bff983`.
Its feature-reference artifact SHA is
`fd26774585223913d12b8c20556a8fc1a50fa5dea7a3a75068a7bb30efce76ec`;
this is not the LM weights hash. Separate LM per-file hashes are preserved.
LR: L2, C=1, balanced weights, lbfgs, seed 1701, tol=0.0001,
max_iter=20000; accepted full-BASE_TRAIN fit converged in 5492 iterations.

Surprisal is negative natural-log next-token probability: logits at positions
`[:-1]` predict IDs `[1:]`. No special tokens are added. The first content token
is unscored; overlapping LM context does not duplicate target scores. The retained
prefix receives full tail coverage. Feature windows are distinct from LM context
chunks and include the final partial window. Fewer than two content tokens yield
`insufficient_input` without a fabricated score or vote. Frozen benign length-bin
references are never refitted at inference; B2 adds six length-conditioned and ten
distributional features to the original ten features. No extra scaling/imputation.

Calibration SHA:
`964cea57d98673d2026fb2f0e9d5884aec61a653e726847e0fb6ccbf36e95f23`.
Input is logit(clip(raw LR class-1 probability, 1e-12, 1-1e-12)); output is
sigmoid(1.2387924053209722 * input - 1.4285349476179108). Binding to all five
frozen D_S model/reference/manifest/training/integrity files verifies.

## D_M-B Notes

Class 0 is BENIGN; class 1 is ATTACK. Frozen training evidence is BASE_TRAIN,
1135 rows (183 attack/952 benign), three epochs, AdamW, learning rate 2e-5,
batch size 8, seed 1701. No training occurred in this phase.
The tokenizer uses the frozen upstream revision and artifact tokenizer files;
right padding is to longest in batch. Counts include boundary special tokens,
not padding. The config has 514 positional embeddings but 512 usable context;
the project input budget stays 256.

Calibration SHA:
`7af044ff8e0e29020450bffa93f92c973da4cc4a4888067d88938eefbb2566b9`.
Input is logit(clip(raw softmax class-1 probability, 1e-12, 1-1e-12)); output is
sigmoid(0.5342020363895714 * input + 0.9137732043262331).
All nine frozen model/tokenizer/integrity binding entries verify. It emits
`calibrated_probability` separately and does not change the native raw-0.5 vote.
Neither calibrator is asserted to be perfectly calibrated or valid under shift.

## D_G Notes

Serialized labels are generic LABEL_0/LABEL_1. Class 1's malicious meaning comes
from accepted freeze metadata and its pinned provider-helper evidence at
`3c106f3e6ee79d6df51ae706bc7ef2d734ec3ded`, not from assuming label names.
The runtime selects class 1 explicitly. CLS=1/SEP=2 consume two positions;
PAD=0. The upstream fast tokenizer's normalization is retained. Token IDs are
sliced without decode/re-encode; no whole-input truncation. Zero content tokens
yield `insufficient_input` with no score or vote. Chunk score uses temperature 1;
max risk and OR decisions are separate aggregations, with ties benign.
All nine accepted snapshot-file hashes verify. No global snapshot hash is invented.

## Ranking Versus Decisions

Existing ROC/PR analyses rank raw class-1 scores. R0's D_S and D_M-B results
are fold-local OOF recipe scores, not the final models' calibrated inference.
Its 1/3/5% descriptive FPR points are not frozen operational thresholds.
This inventory records current implementation behavior without choosing any new
threshold or constructing a prediction schema.

## Validation And Preservation

**40 focused tests pass; 0 failures/errors/skips.** Receipt:
`artifacts/research_protocol/phase2_tests_v1.xml`.
Static integrity verification passes **165 accepted file hashes**, including
**96 baseline preservation checks**, and verifies preserved D_S runtime code
against its accepted Git blobs. Tests cover all requested inventory guarantees,
wrong IDs/order/directions/bindings/revisions/threshold status, unsafe and Cycle-2
paths, simulated hash drift, unchanged implementations, deterministic bytes and
an audit-gated subprocess proving no dataset access or model-library imports.
These are Phase-2 checks, not a rerun of the historical 199 acceptance tests.

Manifest: `artifacts/research_protocol/detector_set_manifest_v1.json`.
Byte SHA: `2da5aa92cb14ac19cd49fa7150e7a4ef79b59e1e5fb1aa8ba4148456da618f31`.
Stack canonical SHA:
`dce1392430198894247ca318d6c2627f024ef403742d2a0779bb7b7606847110`.
Stack file-byte SHA:
`4bd076dfc07717555034732b55a9a65c0bc531bb17beab58659b088254247dae`.
The canonical checksum and file-byte checksum intentionally differ; the accepted
STACK-001 code/report specifies canonical JSON hashing. The new inventory's
sidecar checksum is explicitly its file-byte hash.

Only the protocol manifest/checksum/test receipt, validation module, focused tests,
this report, and narrow `.gitattributes` byte-preservation rules changed. Frozen
detector/model/calibration files remain unchanged. Commit/push identifiers belong
to this protocol inventory only and are returned after synchronization; no older
run provenance was rewritten.

**PHASE_2_COMPLETE_READY_FOR_PHASE_3 (protocol metadata only).** Phase 3 has not
started. Final D_S runtime materialization remains explicit future integration
work; no claim of runtime harness readiness is made.
