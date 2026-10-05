# TECH-SEM-003 Residual Failure Analysis v1

Status: PASS. Scope: authorized BASE_TRAIN OOF predictions and existing manifest
metadata only. No prompt content, CALIBRATION, VALIDATION or protected payloads
opened; no training, model inference, hard mining or threshold deployment.
Run code provenance: `5096d078b599c43ddd4e32b4fbfcaedcc83e4646`.

## Two Distinct Error Sets

Raw comparison cutpoint: 0.5, fixed before the run. Raw FNs: **17**.
Existing confidence: **12 HIGH_CONFIDENCE_WRONG**, zero BORDERLINE_WRONG,
five OTHER_WRONG. These are uncalibrated probability categories, not proven
causal mechanisms or evidence that every FN is a fundamental blind spot.

Pooled descriptive <=3% frontier cutpoint: `0.0008947817841544747`.
Inclusive `score >= threshold`; equality is recovered. This frontier yields
179 TP, 22 FP, 4 FN, 930 TN. **13 raw FNs recover; four persist.**
This cutpoint summarizes the same pooled OOF scores and is not independently
chosen threshold performance or a deployed/frozen policy.

## All 17 Raw FNs

| Sample ID | Fold | Raw score | Existing confidence | Recovered at descriptive <=3% |
|---|---:|---:|---|---|
| W2-2ad1d1769b8c4f91cfa39d67 | 4 | 0.100000955164 | OTHER_WRONG | YES |
| W2-2e5c0b7b868cdf69b5d982aa | 4 | 0.000318495004 | HIGH_CONFIDENCE_WRONG | NO |
| W2-2ed0f5f420e8459fecdf3214 | 0 | 0.126234844327 | OTHER_WRONG | YES |
| W2-303f4b2a371e72661137710d | 1 | 0.000894781784 | HIGH_CONFIDENCE_WRONG | YES (equal threshold) |
| W2-3516b6590258e0cec95eff08 | 0 | 0.022705703974 | HIGH_CONFIDENCE_WRONG | YES |
| W2-4abb2dd48ec62f908edf0fa4 | 0 | 0.108853191137 | OTHER_WRONG | YES |
| W2-5ce365d631f87bfbcb320b57 | 3 | 0.000286676077 | HIGH_CONFIDENCE_WRONG | NO |
| W2-6dec1d1e760ab9c2a6513bb5 | 2 | 0.019945183769 | HIGH_CONFIDENCE_WRONG | YES |
| W2-77cf86dae187121c639f9238 | 1 | 0.000621427433 | HIGH_CONFIDENCE_WRONG | NO |
| W2-805d39d74af0ea5b2434c65b | 0 | 0.038086559623 | HIGH_CONFIDENCE_WRONG | YES |
| W2-895c82b8380970b81ad5ffc3 | 0 | 0.027416536584 | HIGH_CONFIDENCE_WRONG | YES |
| W2-9572e34c7ec6f3af9501ac0f | 3 | 0.257723301649 | OTHER_WRONG | YES |
| W2-d8e69ad880a8eab96770ca48 | 2 | 0.059182126075 | HIGH_CONFIDENCE_WRONG | YES |
| W2-dd2317a66faaf974b05e945d | 3 | 0.000651716487 | HIGH_CONFIDENCE_WRONG | NO |
| W2-e9e6d1223268b99b4c3ec855 | 0 | 0.355798184872 | OTHER_WRONG | YES |
| W2-ea8a6cc0602cdb6dd81b006b | 3 | 0.001047652448 | HIGH_CONFIDENCE_WRONG | YES |
| W2-f675d5868a2f79a121ab5ba7 | 1 | 0.013269803487 | HIGH_CONFIDENCE_WRONG | YES |

## Persistent Four

All four are high-confidence under the existing raw definition, not borderline;
all are fully analyzed, zero excluded tokens, no truncation.

| Sample ID | Fold | Tokens | Distance below 3% cutpoint | Original source locator | Canonical lineage group |
|---|---:|---:|---:|---|---|
| W2-2e5c0b7b868cdf69b5d982aa | 4 | 19 | 0.000576286780 | ART-W2-DEEPSET-TEST::parquet_row:90 | LG-N1-9cd5921fab7c695c055609de |
| W2-5ce365d631f87bfbcb320b57 | 3 | 19 | 0.000608105707 | ART-W2-DEEPSET-TRAIN::parquet_row:306 | LG-N1-3dee279691ac925a40d719d8 |
| W2-77cf86dae187121c639f9238 | 1 | 25 | 0.000273354352 | ART-W2-DEEPSET-TEST::parquet_row:86 | LG-N1-5a92a13ce02b50595c6233b7 |
| W2-dd2317a66faaf974b05e945d | 3 | 43 | 0.000243065297 | ART-W2-DEEPSET-TRAIN::parquet_row:290 | LG-N1-73bd2b1851b7034127348eff |

All belong to BASE_TRAIN in the governed fixture. The TRAIN/TEST strings here
identify original deepset files, not access to current VALIDATION/CALIBRATION.
The CSV preserves raw scores and signed logit margins at full precision.

## Coherence Assessment

Classification: **PARTIAL_CLUSTER; NOT ACTIONABLE**.

Shared source: deepset Prompt Injection (`DS-TXT-018`), source revision
`4f61ecb038e9c3fb77e21034b22511b523772cdd`. Shared existing attack family:
`direct_prompt_injection`; mechanism `prompt_injection`; provenance PARTIAL;
label confidence MEDIUM. Rights: local research allowed, redistribution scope
unresolved. Generator NOT AVAILABLE, fine structural subtype UNKNOWN,
original source ID UNKNOWN. No family/subtype was inferred from prompt text.

The shared broad source/family/provenance/confidence also describes **all 183
positive examples** in this fixture. It cannot distinguish a residual-specific
representation defect or systematic family omission. Four distinct canonical
groups, three folds, two original source components and lengths 19, 19, 25, 43
provide only partial clustering. Similar low scores describe the outcome, not
the cause. Generator and structural subtype are missing; no claim of known
heterogeneous mechanisms or verified blind spot is supported.

Fold 1 is weakest at <=3% (94.44% recall); folds 0/1 at <=1% reach 83.33%.
The <=3% fold recall mean is 97.81% with population SD 2.07 points. Retain these
limitations; do not tune a weak fold or equate pooled and per-fold thresholds.

Truncation cannot explain these observed residuals: four truncated positives
were all TP, while every persistent and raw-rule FN was non-truncated. Only four
truncated positives were observed (0/4 FN; Wilson upper bound 48.99%), so this
does not exclude future truncation failures. No 512-token experiment is supported.

## Decision

**FREEZE_DM_B_V1** for the next stack phase. Strong descriptive operating
capacity and no specific actionable residual mechanism do not justify one
SEM-004 intervention. Do not reweight, duplicate, oversample or otherwise train
on these diagnostic IDs. No dm_b_v2, stronger encoder, 512-token training,
loss change or final threshold is authorized by this acceptance.
