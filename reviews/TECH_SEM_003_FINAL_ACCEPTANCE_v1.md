# TECH-SEM-003 FINAL ACCEPTANCE REPORT

STATUS: **PASS**

Date: 2026-10-04. Scope: completed development-only OOF evidence closure.
Decision: **FREEZE_DM_B_V1**. No new detector training, model inference,
OOF execution, deployed threshold selection, SEM-004 or STAT-004 work.

## Provenance

| Item | Verified value |
|---|---|
| Branch | `tech/sem-003` |
| MODEL/RUN CODE commit | `5096d078b599c43ddd4e32b4fbfcaedcc83e4646` |
| Manifest SHA-256 | `9cdd5ecdd80f9ac3c8f05db63742721f4537ca2b64a2fe48f6c2b424b57483a6` |
| Fold SHA-256 | `19dc0153cc257cc2331782d6dd61b7bb9fb8cb0ed88d3e782b69d5ba05c4bb8d` |
| Preflight SHA-256 | `9f0465747c214f01cce3c5927b7ea2f8058d5d97c310ce6b3e2b6f8af9fb6dc7` |
| Active config SHA-256 | `5b50e3eccd2afeca32875905e414313b337785969abd59d9755daae94bf4e6e2` |
| Original output hashes | **9/9 PASS** |
| Baseline preservation | **96/96 PASS**, no tracked baseline diff |
| Rows / positives / negatives | **1,135 / 183 / 952** |
| Canonical lineage groups | 1,134; every sample predicted exactly once |
| ID leakage / lineage leakage | **0 / 0** |
| Original run device / seed / runtime | CPU / 1701 / 2,427.863 seconds (40.46 minutes) |

The new commit contains POST-RUN EVIDENCE/ACCEPTANCE only. The original run
metadata, start marker, completion marker and all nine authoritative outputs
are preserved byte-for-byte; none are relabeled with the evidence commit.
Resolve the evidence commit using:

```powershell
git log -1 --format=%H -- artifacts/semantic_v2/oof/acceptance_manifest_v1.json
```

The original verifier returned `PASS_COMPLETE_DEVELOPMENT_OOF` before acceptance.
Its startup provenance check intentionally requires HEAD at the pre-run freeze;
it is not changed or relaxed. The separate post-run checker allows a descendant
evidence commit only while proving frozen code/preflight bytes still match the
original run commit, the nine output hashes remain exact, and all original
diagnostics reconstruct. This does not waive STAT-004's clean-tree startup gate.

## Aggregate OOF

The raw 0.5 comparison rule reconstructs **TN 947, FP 5, FN 17, TP 166**.

| Metric | Result |
|---|---:|
| Accuracy | 0.9806167401 |
| Precision | 0.9707602339 |
| Recall | 0.9071038251 |
| Specificity | 0.9947478992 |
| F1 | 0.9378531073 |
| ROC-AUC | 0.9963493594 |
| PR-AUC (average precision) | 0.9877044339 |
| Raw FPR | 0.525210%; Wilson 95% CI **0.224541-1.223551%** |
| Raw FNR | 9.289617%; Wilson 95% CI **5.880947-14.372298%** |

## Fixed-FPR Frontier

All counts reconstruct from the frozen raw scores, using the inclusive `>=`
rule. These are descriptive development OOF operating points, not deployed
thresholds or final performance.

| Budget | TN | FP | FN | TP | Attained FPR | FPR 95% CI | FNR | FNR 95% CI | Recall |
|---|---:|---:|---:|---:|---:|---|---:|---|---:|
| <=1% | 945 | 7 | 6 | 177 | 0.735294% | 0.356625-1.509946% | 3.278689% | 1.511147-6.967409% | 96.721311% |
| <=3% | 930 | 22 | 4 | 179 | 2.310924% | 1.530979-3.474188% | 2.185792% | 0.853217-5.484487% | 97.814208% |
| <=5% | 918 | 34 | 2 | 181 | 3.571429% | 2.566851-4.949192% | 1.092896% | 0.300225-3.896627% | 98.907104% |

**D_M-B demonstrates the capacity to operate within the 1-3% FPR/FNR region
at a descriptive development-OOF operating point.**

Intervals are descriptive Wilson 95% binomial intervals. OOF predictions share
training data; observations are not perfectly independent in the modeling
sense. These intervals do not include refitting uncertainty, lineage dependence
or threshold-search uncertainty, are not final population guarantees, and do
not establish that true error is below 3%.

The pooled threshold corresponding to FPR<=3%
(`0.0008947817841544747`) was chosen descriptively using the same pooled OOF
predictions being summarized. It demonstrates ranking/operating capacity,
**not an unbiased estimate of a future independently selected threshold**.
It is not frozen or installed as a deployment threshold. Final threshold
selection remains deferred to the authorized calibration/validation
operating-point phase; neither partition was accessed in acceptance.

## Fold Stability

Percent pairs below are **recall / attained FPR**, each fold's own descriptive
frontier, not the pooled threshold applied to every fold.

| Fold | N | Positive | Negative | ROC-AUC | PR-AUC | <=1% pair | <=3% pair | <=5% pair |
|---|---:|---:|---:|---:|---:|---|---|---|
| 0 | 227 | 36 | 191 | 0.997818 | 0.988513 | 83.3333 / 0.0000 | 100.0000 / 1.5707 | 100.0000 / 1.5707 |
| 1 | 227 | 36 | 191 | 0.996800 | 0.984069 | 83.3333 / 0.5236 | 94.4444 / 1.0471 | 100.0000 / 3.6649 |
| 2 | 227 | 37 | 190 | 1.000000 | 1.000000 | 100.0000 / 0.0000 | 100.0000 / 0.0000 | 100.0000 / 0.0000 |
| 3 | 227 | 37 | 190 | 0.993883 | 0.982853 | 94.5946 / 0.5263 | 97.2973 / 2.1053 | 97.2973 / 2.1053 |
| 4 | 227 | 37 | 190 | 0.994168 | 0.985230 | 97.2973 / 0.5263 | 97.2973 / 0.5263 | 97.2973 / 0.5263 |

At <=3%: fold recall **mean 97.8078%, population SD 2.0710 percentage points,
minimum 94.4444%, maximum 100%**. Attained FPR **mean 1.049876%, population
SD 0.743161 points, minimum 0%, maximum 2.105263%**.

Fold 1 is weakest at <=3% (34/36 recalled). Folds 0 and 1 have 83.33% recall
at <=1%. Thus the pooled frontier is not uniform fold-level performance.
Small positive denominators and fold-specific score scales limit inference;
the strong ranking does not justify special-tuning a weak fold. No fold was
tuned, reweighted or retrained.

## Raw Threshold Errors

Group A: **17 raw-rule FNs**, including **12 high-confidence**, zero borderline,
and five other wrong probabilities under the existing raw-threshold definitions.
Group B: **4 persistent FNs** at the pooled <=3% descriptive point.
**13 of the 17 are recovered**, including eight high-confidence raw FNs and
all five other raw FNs. These 17 are not equally fundamental representation
failures. All four persistent FNs are high-confidence under the existing raw
rule; zero are borderline. Softmax confidence is uncalibrated and not proof of
epistemic certainty or a causal representation failure.

All 17 IDs, the 13 recovered IDs, and original confidence annotations are
retained in `dm_b_v1_raw_fn_v1.csv` and the residual JSON. The residual report
lists all 17 individually. A score exactly equal to the descriptive threshold
is correctly counted as recovered, not persistent.

## Persistent 4 FNs

Shared metadata: deepset Prompt Injection (`DS-TXT-018`), revision
`4f61ecb038e9c3fb77e21034b22511b523772cdd`; already-recorded family
`direct_prompt_injection`, mechanism `prompt_injection`, provenance `PARTIAL`,
label confidence `MEDIUM`. Generator NOT AVAILABLE; structural subtype and
original source ID UNKNOWN. Rights remain local-research use allowed with
redistribution scope unresolved, not legal clearance.

| Sample ID | Fold | Score | Distance below descriptive 3% threshold | Input/analyzed tokens | Truncated/excluded |
|---|---:|---:|---:|---:|---|
| W2-2e5c0b7b868cdf69b5d982aa | 4 | 0.000318495004 | 0.000576286780 | 19/19 | false/0 |
| W2-5ce365d631f87bfbcb320b57 | 3 | 0.000286676077 | 0.000608105707 | 19/19 | false/0 |
| W2-77cf86dae187121c639f9238 | 1 | 0.000621427433 | 0.000273354352 | 25/25 | false/0 |
| W2-dd2317a66faaf974b05e945d | 3 | 0.000651716487 | 0.000243065297 | 43/43 | false/0 |

The persistent-ID CSV also contains exact lineage groups, original source
locators, revision, signed raw logit margin and rights/provenance fields. No
prompt content was opened or copied. Source TRAIN/TEST locator names identify
original files only; all four are in the current authorized BASE_TRAIN fixture.

## Coherence

Classification: **PARTIAL_CLUSTER; NOT ACTIONABLE**.

All four share broad source/family/provenance metadata and very low scores,
but those source/family/provenance annotations also describe **all 183 positives**.
They do not identify a residual-specific mechanism. The four occupy four
distinct canonical lineage groups and folds 1, 3, 4; three are under 32 tokens,
one is 43 tokens. Fine structural subtype/generator evidence is unavailable.
No attack family is inferred manually from text; heterogeneous mechanisms
cannot be claimed from missing metadata. No specific plausible improvement
experiment is supported by this partial grouping.

## Truncation

Four truncated rows, all positive: **4 TP, 0 FN**, no truncated negatives.
Their observed FNR is 0/4, but Wilson 95% CI is **0-48.9891%**.

**NO OBSERVED ASSOCIATION BETWEEN CURRENT OOF MISSES AND EXCLUDED TOKENS IN
THIS FIXTURE.** The small group is not evidence that truncation cannot cause
future errors. B1 (256->512) is **NOT SUPPORTED AS THE NEXT MODEL-IMPROVEMENT
EXPERIMENT**. No 512-token counterfactual forward pass or training was run.

## Decision

**FREEZE_DM_B_V1.** D_M-B v1 is accepted as the semantic fine-tuned detector
for the next stack phase. Strong descriptive ranking, the absence of observed
truncation-associated misses, and lack of a specific actionable residual
mechanism do not justify chasing four OOF errors. Do not create dm_b_v2,
start SEM-004, hard-mine, duplicate/oversample errors, change loss or select
a new encoder. Existing deployed artifacts and calibration remain unchanged.

Context only, on the same QUALITY-001 fixture: D_S v1 Recall@FPR<=3% is
**32.24%**, versus D_M-B v1 **97.81%**. D_S currently shows a substantial
discrimination/representation weakness; D_M-B does not show that same class
of weakness. This is not a protected/final benchmark result or authorization
to resume intentionally blocked STAT-004.

## Isolation And Tests

CALIBRATION access: NO. VALIDATION access: NO. Protected payload access: NO.
E1-E10: NO. New detector/neural training: NO. Model inference: NO.
Threshold freeze: NO. SEM-004: NOT STARTED. STAT-004: UNMODIFIED/BLOCKED.

**120 relevant tests passed**, zero failures/errors/skips; one obsolete
pre-run-only assertion deselected because the authoritative run marker now
exists. Its frozen source was not changed. A new post-run regression verifies
the completed-run marker rejects training before any loader/fit is called.
Original semantic fold fits in unit tests use test doubles; shared statistical
regressions use tiny synthetic fixtures, not new project-detector training.
25 existing SciPy L-BFGS-B deprecation warnings are non-failing; no package
installation or environment change was required.

Detailed commands and tests: `TECH_SEM_003_POSTRUN_TEST_REPORT_v1.md`.

## Artifacts And Git

Required outputs: `dm_b_v1_fold_stability_v1.json`,
`dm_b_v1_persistent_fn_3pct_v1.csv`, `dm_b_v1_residual_failure_analysis_v1.json`,
`dm_b_v1_rate_intervals_v1.json`. Additional ID-only raw FN CSV, JUnit evidence
and `acceptance_manifest_v1.json` live in `artifacts/semantic_v2/oof/`.
Three new acceptance reports live in `reviews/`.

Acceptance tooling is separate from frozen run code. One narrow `.gitattributes`
rule preserves acceptance test bytes across checkout. No baseline, central
service, model/calibrator, STAT-004 or raw dataset file is changed.

Commit scope: the original 11 pending authoritative files plus post-run
acceptance artifacts, reports, tests and acceptance-only tooling. Commit message:
`analysis(sem): accept D_M-B OOF evidence and residual failures`.
Post-commit checks must pass with a clean working tree. No push is authorized.
