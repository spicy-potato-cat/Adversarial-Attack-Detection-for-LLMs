# QUALITY-001 Development Fixture And Promotion Protocol v1

Status: **PASS**

Project: Adversarial Attack Detection for Large Language Models (LLMs)

Client date: 2026-10-04 (Asia/Calcutta)

Branch: `quality/001-development-fixture`

Start commit: `43f140590b05435504a49dca86a5955f47c07090`

## Scope And Isolation

This phase freezes development methodology before `ds_v2` or `dm_b_v2`
engineering. It does not establish detector performance or a final operating
point. Only the existing development manifest and governance metadata were
read for construction. No raw/normalized dataset payload was opened. Outer
partition membership/count metadata was checked, not CALIBRATION/VALIDATION text.

- NO MODEL TRAINING
- NO DETECTOR SCORING
- NO VALIDATION CONTENT ACCESSED
- NO CALIBRATION CONTENT ACCESSED
- NO PROTECTED DATA ACCESSED
- NO R0-R3 EXPERIMENTS EXECUTED
- NO E1-E10 EXECUTED
- NO VERIFIER SELECTION OR ROUTING IMPLEMENTATION

Baseline artifact preservation additionally hashes small serialized classifiers
and metadata as opaque bytes; it does not deserialize models, open model weights,
or execute detectors. Existing model metrics are not recomputed or used to choose
this fixture.

## Authoritative Manifest

Path: `data_governance/manifests/development_partition_manifest_v1.csv`

SHA-256:
`9cdd5ecdd80f9ac3c8f05db63742721f4537ca2b64a2fe48f6c2b424b57483a6`

Verified counts: TOTAL 1,601; BASE_TRAIN 1,135; CALIBRATION 233; VALIDATION 233.
BASE_TRAIN contains 183 positives and 952 negatives, across 1,134 lineage groups.
Source counts: Do-Not-Answer 659 (all canonical label 0), deepset Prompt Injection
476 (183 positive, 293 negative). Labels are inherited from the authorized
manifest; QUALITY-001 makes no new semantic label judgments.

The matching manifest and two original policy documents remain local governance
inputs. They are not copied into Git or reconstructed from raw datasets. A new
checkout must receive those exact Commander-governed metadata files before using
the checker; absent/mismatched inputs stop execution.

## Lineage Authority And Limits

Authority: `data_governance/DATA_LINEAGE_POLICY_v1.md` and
`data_governance/DATA_PARTITION_POLICY_v1.md`, both hash-bound in the freeze.

The existing field is `lineage_group_id`, with the approved minimum rule:
`LG-N1-<first_24_hex_chars_of_normalized_text_sha256>`.
No replacement group IDs were invented. Full normalized hashes are checked for
prefix collisions, and inconsistent group labels fail construction. Manifest
groups are also checked for cross-partition membership.

**Zero leakage means zero splits of these approved N1 canonical-duplicate
groups. It does not establish semantic, template, documentary, or upstream
lineage independence.** Those residual risks remain as documented by the original
governance. Broader sources or protected benchmark freezes require their own
additional lineage review.

## Deterministic Construction

Fixture: `quality_001_development_folds_v1`; seed `1701`; folds `0..4`.
Method: `quality_001_group_greedy_v1`, using Python standard-library arithmetic.

1. Treat each authoritative lineage group as indivisible.
2. Process positive groups first, then negative groups; larger groups first
   within each label. Break group-order ties with SHA-256 of
   `1701|order|<lineage_group>`.
3. Select the fold minimizing the lexicographic tuple of incremental squared
   label-count cost, incremental squared source-count cost, current total rows,
   and SHA-256 of `1701|fold|<lineage_group>|<fold>`.
4. Serialize metadata-only rows in sample-ID order, UTF-8 with LF line endings.

Lineage isolation takes priority over label balance, which takes priority over
source balance. There was one successful artifact construction and no balance
rerolls. An initial attempt encountered missing `jsonschema` before writing any
artifact; dependency repair reproduced the same deterministic procedure. Checker
and test reproductions verify the frozen assignment, not alternate candidates.

## Frozen Fold Statistics

| Fold | Held-Out Rows | Positive | Negative | Lineage Groups | Train Rows | DNA Rows | deepset Rows |
|---|---:|---:|---:|---:|---:|---:|---:|
| 0 | 227 | 36 | 191 | 227 | 908 | 132 | 95 |
| 1 | 227 | 36 | 191 | 226 | 908 | 132 | 95 |
| 2 | 227 | 37 | 190 | 227 | 908 | 132 | 95 |
| 3 | 227 | 37 | 190 | 227 | 908 | 131 | 96 |
| 4 | 227 | 37 | 190 | 227 | 908 | 132 | 95 |

DNA contributes only negatives. Per-fold deepset negative counts are
59, 59, 58, 59, 58 respectively; its positive counts are the table's positive
counts. The single two-row lineage group remains together in fold 1.

Every BASE_TRAIN row appears in exactly one held-out fold and is eligible for
training in the other four. Missing rows: 0; extra rows: 0; duplicate
assignments: 0; lineage groups split: **0**.

## Frozen Development And Promotion Rules

The five folds are **DEVELOPMENT data**, usable for OOF baselines, error
characterization, feature/model engineering, controlled comparisons, and promotion
decisions. Repeated inspection prevents treating them as unbiased final tests.
They cannot support final research/system FPR/FNR claims.

Objective: minimize `FNR_system` subject to `FPR_system <= alpha`.
Development budgets: **1%, 3%, 5%**; no final budget or operating point selected.

For D_M-B, compare recall at those fixed budgets, not literal FPR/FNR dominance
at cutpoint 0.5. Improvement at one or more budgets must not materially degrade
PR-AUC, ROC-AUC, cross-fold stability, latency/compute practicality, or
complementary failure behavior. The later candidate authorization must specify
materiality and compute limits before results; this phase does not invent them.
An attractive isolated point estimate is insufficient.

For D_S, standalone recall at those budgets is necessary evidence but not a
sufficient promotion argument. Later matched-sample analysis must assess
`UniqueCatchRate_S`, pairwise S/M and S/G joint false-negative events, all-detector
joint failure, and FN-set overlap/Jaccard. Exact semantic/ensemble membership is
frozen separately during integration. The unique-catch denominator is positive
samples, with counts and operating points recorded.

**Do not optimize individual detectors at the expense of complementary failure
behavior.** D_S v2 remains statistical/token-distribution based. Semantic
transformer embeddings, D_M logits, D_G scores, LLM judge scores, and semantic
classifier outputs are prohibited as D_S features.

Maximum: **two substantive improvement cycles per D_S and D_M-B**. A meaningful
feature/model redesign followed by development evaluation counts; bug,
deterministic reproduction, and serialization fixes do not. After two substantive
unsuccessful cycles, stop tuning and report the limitation.

OOF fitting must be fold-local for all learned preprocessing, models, and
calibrators; any inner splits remain lineage-aware. Whole-BASE_TRAIN fitted v1
models cannot produce honest OOF baseline predictions on these same rows. Later
baseline OOF work must reproduce authorized frozen recipes within outer-training
folds without overwriting v1 artifacts. No such fitting/prediction occurred here.

## Calibration And Statistical Reporting

Calibration is assessed primarily by Brier score and negative log likelihood /
log loss. ECE is optional only with a consistent preregistered binning rule.
AUROC/PR-AUC are sanity checks; a monotonic calibrator is not expected to improve
ranking and receives no discrimination credit without evidence.

Use paired comparisons on identical folds/samples: delta recall at fixed FPR,
FPR, FNR, ROC-AUC, and PR-AUC. Use paired lineage-group bootstrap intervals where
supported later. No p-hacking or repeated significance testing.
Empirical fixed-FPR comparisons use attainable whole tied-score blocks, without
interpolation/randomized tie splitting. Report thresholds, denominators, FP
counts, and cross-fold variation. Small negative counts make 1% coarse; empirical
budget compliance is not a population guarantee.

Point estimates require confidence intervals where feasible, especially FPR,
FNR, recall, system rates, and paired deltas. The configured confidence level is
95%; dependence-aware interval procedures must be preregistered before later
evaluation. No intervals or detector rates are computed in QUALITY-001.

**1-3% FPR/FNR is a stretch system-level engineering target to be evaluated on a
sufficiently large untouched benchmark with confidence intervals.** It is not a
guaranteed result.

## Partition And Threat-Regime Governance

`partition != threat_regime`.

- R0: standard / non-adaptive attacks.
- R1: unseen / distribution-shifted attacks.
- R2: single-detector adaptive attacks.
- R3: ensemble-aware adaptive attacks.

R0-R3 are not partitions, protected-dataset synonyms, or partition file paths.
The config explicitly permits future INTERNAL_TEST or FINAL_TEST crossed with
each regime. This does not authorize those experiments.

BASE_TRAIN CV is development/candidate engineering. CALIBRATION is reserved for
separately authorized calibration, outside CV. VALIDATION is a later explicitly
defined candidate promotion/calibration-threshold-policy gate, not engineering.
INTERNAL_TEST measures internal research performance without driving tuning.
FROZEN_EXTERNAL / FINAL_TEST remains untouched final system evaluation.

Preserved generations: `ds_v1`, `dm_a_v1`, `dm_b_v1`, `dg_v1`. Future `ds_v2` and
`dm_b_v2` coexist rather than overwrite. `research_stack_v1` and
`research_stack_v2` denote original and improved generations; exact primary
ensemble membership remains separately frozen during integration.

Verifier recovery precedes routing optimization. Future selection should measure
`P(V_k detects attack | base stack failed)`, not standalone accuracy.
Disagreement-only verification cannot detect every common-mode false negative.
The configured future A/B/C/D trigger policies are possibilities only, not
implemented or selected policies.

## Schemas And Integrity

`oof_result_schema_v1.json` and `error_analysis_schema_v1.json` define records
only. No project predictions or error-analysis records were generated. Successful
OOF records require identity, fold, label, detector/candidate versions, scores,
prediction, coverage, latency, consistent TP/TN/FP/FN, and restricted metadata.
Execution failures require explicit separate failure reporting, never invented
predictions. Error schemas retain unknown diagnostics as null/absent; the policy
requires permitted evidence for payload-position/attack-family claims. Neither permits raw
prompt/response fields. Fixture membership must also be checked by later consumers.

The checker verifies manifest hash/counts, approved lineage metadata, exact
membership, unique assignment, valid labels/folds, metadata compatibility,
group isolation, deterministic reconstruction/serialization, config schema,
statistics, and frozen hashes. The trusted integrity SHA is in
`detection_service/quality/freeze_constants.py`; changing JSON hashes alone cannot
bypass it. Freeze refuses an existing destination. Git byte-preservation rules
prevent platform newline conversion of hash-bound fixture files and core code.

```powershell
.\.local-python\python.exe -m detection_service.quality.development_fixture --mode check
.\.local-python\python.exe -m detection_service.scripts.verify_quality_preservation --mode check
```

## Artifact Hashes

All files below are in `artifacts/quality/quality_001/`.

| File | SHA-256 |
|---|---|
| development_folds_v1.csv | `19dc0153cc257cc2331782d6dd61b7bb9fb8cb0ed88d3e782b69d5ba05c4bb8d` |
| quality_fixture_v1.json | `7b010b4e536cf04fd510c7a7a16a80fa9429c798c3d155e01ddfe56b45657c0c` |
| fold_statistics_v1.json | `2ae3c7e5e6866e0d08667b2746fc405a741b019320a8ff6a6df44fcf987587ea` |
| quality_fixture_schema_v1.json | `569e78547a1c2d60e0d46bda0c29f45488b97faa4e89b7b580743dd1cbc3cbc3` |
| oof_result_schema_v1.json | `b9cf6f772d8c7bf658fcdb7b29a7ec51f15113d61bbb404ffb823ab18f09af57` |
| error_analysis_schema_v1.json | `e3b0c6516a29d40e9788c8df9b367931fb327bd7039738cd8e53398df61e153d` |
| integrity_manifest_v1.json | `312fd7edf21f075f5d158a6317c634282d7b0652b8b500ceec9dd4da4a0cfc26` |
| baseline_preservation_v1.json | `4b42dd44f2604f12e099f1fc60decef866c64d036c9a6554fcd3e049513b8a21` |
| test_evidence_v1.json | `c0bbcaa6ef8c2b9e47ae7d55b12d41abb98fe374a5b7df0b3ac0bf011a915a2e` |

## Acceptance And Recommendation

Manifest/counts/lineage metadata: PASS. Five folds and deterministic frozen
assignment: PASS. All BASE_TRAIN rows assigned once: PASS. Lineage splits: 0.
Config, budgets, promotion/complementarity policies, two-cycle cap, calibration
semantics, partition/regime distinction, and generation distinction: PASS.
Tests: 66 passed, 0 failed, 0 skipped, 0 blocked. Existing baselines preserved.

**READY FOR TECH-STAT-003 AND TECH-SEM-003 DEVELOPMENT ANALYSIS.**
This does not authorize training, verifier/routing work, or protected experiments.
