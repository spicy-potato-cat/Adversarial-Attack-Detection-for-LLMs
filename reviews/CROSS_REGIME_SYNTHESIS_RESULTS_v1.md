# Cross-Regime Synthesis Results v1

STATUS: PASS

All values are rendered from frozen machine-readable artifacts by `detection_service/research_protocol/cross_regime_report.py`; no rounded report value substitutes for an artifact value. Result bundle: `artifacts/research_protocol/synthesis/cross_regime_result_bundle_v1.json` (SHA-256 `acad022fda72ae9b23ad335c8b3edd0ff0d6fc36363eb3e42b3789cd1a141e6c`).

## 1. Experiment Sequence

R0 (non-adaptive development) -> R1 (shifted unseen) -> R2-DMB (D_M-B-targeted) -> R2-D_S (D_S-targeted) -> Phase-1 integration baseline `71e3a5239cb24a3e59e99d271c6aa46841dbc084` -> R3 (ensemble-aware, target ALL) -> this synthesis. R2-D_G is an OPTIONAL_EXPLORATORY_APPENDIX and was not executed. No experiment was rerun for this synthesis.

| Regime | Definition | Frozen bundle provenance | Bundle SHA-256 |
|---|---|---|---|
| R0 | R0 non-adaptive development | first committed `2941f1412d15f16bfc1564d1d584a76c0b909df3`; read at `71e3a5239cb24a3e59e99d271c6aa46841dbc084` | `b63b25ed4b2eafc3...` |
| R1 | R1 shifted unseen | first committed `62bf867b2acc53c3a8dc35d18f443558cd9da508`; read at `71e3a5239cb24a3e59e99d271c6aa46841dbc084` | `f393d9453828a52c...` |
| R2-DMB | R2 single-detector targeted (D_M-B) | first committed `99b012e5b72fbae9273fa73ccc8d84d579a69c83`; read at `71e3a5239cb24a3e59e99d271c6aa46841dbc084` | `6c3b1c02c32faf87...` |
| R2-D_S | R2 single-detector targeted (D_S) | first committed `913ee734cb48eb8404e8f6ed62456eb07950246e`; read at `71e3a5239cb24a3e59e99d271c6aa46841dbc084` | `09d75ec9b4085bac...` |
| R3 | R3 ensemble-aware (target ALL) | R3 freeze `adc2f7077203a7c3a8b7b58122123fa27e2b0918` | `ebfe60e20e8089e3...` |

R3 commits: seed freeze `37fb38e9fd3d5be2f69e1961b6f80ff8c130e466`, terminal freeze `51b40432f12676bf0b62e8f04b9bf48eb0e612f1`, scoring `875f2fcf5bea4b1c9b01c654609fcba1b5098375`, analysis/failure freeze `adc2f7077203a7c3a8b7b58122123fa27e2b0918`.

## 2. Frozen Detector Stack

| Label | Detector | Threshold ID | Operational threshold | Model SHA-256 | Model revision |
|---|---|---|---|---|---|
| D_S | ds_v2 | ds_v2_op3_cal_v1 | 0.5585373573968287 | `c5e754dc8b6e88b7437e4b81016e8f8ec23d018607d4f4e78906212b2a561157` | n/a |
| D_M-B | dm_b_v1 | dm_b_v1_op3_raw_v1 | 0.0004967087297700347 | `0bb192d2c468530479fa8ec0786f35d8bf5a8287e4ee401a953292d221736844` | fb53ab8802853c8e4fbdbcd0529f21fc6f459b2b |
| D_G | dg_v1 | dg_v1_op3_raw_v1 | 0.21291141211986545 | `5120e30bcd536ce285345d9ec104bea6bd6e8f94365b99a340c764f417ea5fa1` | 11614a155199674a0a95e6602d6ab0417b790ed0 |

Operational decisions use `score >= threshold` (ties are ATTACK). D_S uses its calibrated probability; D_M-B and D_G use raw scores. All five frozen bundles carry identical operational threshold IDs/values, detector-manifest hash `2da5aa92cb14ac19cd49fa7150e7a4ef79b59e1e5fb1aa8ba4148456da618f31` and operating-policy hash `06fa4548a62ae0e0968f9d93339910f8841a0f366b5346b0892a2be6904fb0cc`; no detector was retrained or re-selected.

## 3. Regime Definitions

| Regime | Population type | Attacks | Benign | Lineages | Target |
|---|---|---|---|---|---|
| R0 | MIXED | 183 | 952 | 1134 | none |
| R1 | MIXED | 800 | 1000 | 1097 | none |
| R2-DMB | ATTACK_ONLY | 800 | 0 | 97 | dm_b_v1 |
| R2-D_S | ATTACK_ONLY | 698 | 0 | 94 | ds_v2 |
| R3 | ATTACK_ONLY | 97 | 0 | 97 | ALL |

Mixed attack+benign regimes: R0, R1. Attack-only regimes: R2-DMB, R2-D_S, R3. FPR, ROC-AUC and AP are reported only for mixed regimes; for attack-only regimes they are NOT_APPLICABLE (no benign denominator), never zero.

## 4. R0

| Detector | TP | FN | FNR | FNR 95% CI | FP | TN | FPR | ROC-AUC | AP |
|---|---|---|---|---|---|---|---|---|---|
| ds_v2 | 113 | 70 | 0.3825 | [0.3169, 0.4536] | 43 | 909 | 0.0452 | 0.8968 | 0.7316 |
| dm_b_v1 | 181 | 2 | 0.0109 | [0.0000, 0.0273] | 58 | 894 | 0.0609 | 0.9963 | 0.9877 |
| dg_v1 | 42 | 141 | 0.7705 | [0.7104, 0.8253] | 17 | 935 | 0.0179 | 0.8150 | 0.5007 |

All-three FN: 2/183.

## 5. R1

| Detector | TP | FN | FNR | FNR 95% CI | FP | TN | FPR | ROC-AUC | AP |
|---|---|---|---|---|---|---|---|---|---|
| ds_v2 | 698 | 102 | 0.1275 | [0.0266, 0.1753] | 28 | 972 | 0.0280 | 0.9743 | 0.9749 |
| dm_b_v1 | 800 | 0 | 0.0000 | [0.0000, 0.0000] | 132 | 868 | 0.1320 | 1.0000 | 1.0000 |
| dg_v1 | 36 | 764 | 0.9550 | [0.8848, 0.9817] | 207 | 793 | 0.2070 | 0.4069 | 0.3779 |

All-three FN: 0/800.

## 6. R2-DMB

| Detector | TP | FN | FNR | FNR 95% CI | FP | TN | FPR | ROC-AUC | AP |
|---|---|---|---|---|---|---|---|---|---|
| ds_v2 | 759 | 41 | 0.0512 | [0.0000, 0.0760] | NOT_APPLICABLE | NOT_APPLICABLE | NOT_APPLICABLE | NOT_APPLICABLE | NOT_APPLICABLE |
| dm_b_v1 | 800 | 0 | 0.0000 | [0.0000, 0.0000] | NOT_APPLICABLE | NOT_APPLICABLE | NOT_APPLICABLE | NOT_APPLICABLE | NOT_APPLICABLE |
| dg_v1 | 30 | 770 | 0.9625 | [0.9054, 0.9824] | NOT_APPLICABLE | NOT_APPLICABLE | NOT_APPLICABLE | NOT_APPLICABLE | NOT_APPLICABLE |

All-three FN: 0/800.
Target dm_b_v1: 0/800 (rate 0.0000, 95% CI [0.0000, 0.0000]). ETR to ds_v2: 0/0 = UNDEFINED (CI OBSERVED_UNDEFINED); ETR to dg_v1: 0/0 = UNDEFINED (CI OBSERVED_UNDEFINED)

## 7. R2-D_S

| Detector | TP | FN | FNR | FNR 95% CI | FP | TN | FPR | ROC-AUC | AP |
|---|---|---|---|---|---|---|---|---|---|
| ds_v2 | 594 | 104 | 0.1490 | [0.0599, 0.1959] | NOT_APPLICABLE | NOT_APPLICABLE | NOT_APPLICABLE | NOT_APPLICABLE | NOT_APPLICABLE |
| dm_b_v1 | 698 | 0 | 0.0000 | [0.0000, 0.0000] | NOT_APPLICABLE | NOT_APPLICABLE | NOT_APPLICABLE | NOT_APPLICABLE | NOT_APPLICABLE |
| dg_v1 | 31 | 667 | 0.9556 | [0.8960, 0.9803] | NOT_APPLICABLE | NOT_APPLICABLE | NOT_APPLICABLE | NOT_APPLICABLE | NOT_APPLICABLE |

All-three FN: 0/698.
Target ds_v2: 104/698 (rate 0.1490, 95% CI [0.0599, 0.1959]). ETR to dm_b_v1: 0/104 = 0.0000 (CI [0.0000, 0.0000]); ETR to dg_v1: 102/104 = 0.9808 (CI [0.9130, 1.0000])

## 8. R3

| Detector | TP | FN | FNR | FNR 95% CI | FP | TN | FPR | ROC-AUC | AP |
|---|---|---|---|---|---|---|---|---|---|
| ds_v2 | 92 | 5 | 0.0515 | [0.0103, 0.1031] | NOT_APPLICABLE | NOT_APPLICABLE | NOT_APPLICABLE | NOT_APPLICABLE | NOT_APPLICABLE |
| dm_b_v1 | 97 | 0 | 0.0000 | [0.0000, 0.0000] | NOT_APPLICABLE | NOT_APPLICABLE | NOT_APPLICABLE | NOT_APPLICABLE | NOT_APPLICABLE |
| dg_v1 | 5 | 92 | 0.9485 | [0.8969, 0.9897] | NOT_APPLICABLE | NOT_APPLICABLE | NOT_APPLICABLE | NOT_APPLICABLE | NOT_APPLICABLE |

All-three FN: 0/97.
Target ALL: 0/97 (rate 0.0000, 95% CI [0.0000, 0.0000]). Transfer: NOT_APPLICABLE_TARGET_ALL.
Parents 97, inherited lineages 97, sources {'INJECAGENT_BASE': 1, 'LLMAIL_INJECT': 96}. Candidate evaluations 5459, generation detector calls 16377, post-freeze replay calls 291, budget violations 0, reconstruction failures 0. Failure manifest EMPTY (0 members).

## 9. Cross-Regime Metrics

### Table B: pairwise common-mode metrics

| Regime | Pair | Shared FN | Union FN | JFN | JFN CI | FNR_i x FNR_j | EJF | EJF CI | FN Jaccard |
|---|---|---|---|---|---|---|---|---|---|
| R0 | ds_v2/dm_b_v1 | 2 | 70 | 0.0109 | [0.0000, 0.0273] | 0.0042 | 0.0067 | NOT_IN_FROZEN_BUNDLE | 0.0286 |
| R0 | ds_v2/dg_v1 | 52 | 159 | 0.2842 | [0.2186, 0.3443] | 0.2947 | -0.0106 | NOT_IN_FROZEN_BUNDLE | 0.3270 |
| R0 | dm_b_v1/dg_v1 | 2 | 141 | 0.0109 | [0.0000, 0.0273] | 0.0084 | 0.0025 | NOT_IN_FROZEN_BUNDLE | 0.0142 |
| R1 | ds_v2/dm_b_v1 | 0 | 102 | 0.0000 | [0.0000, 0.0000] | 0.0000 | 0.0000 | [0.0000, 0.0000] | 0.0000 |
| R1 | ds_v2/dg_v1 | 101 | 765 | 0.1263 | [0.0239, 0.1750] | 0.1218 | 0.0045 | [-0.0028, 0.0070] | 0.1320 |
| R1 | dm_b_v1/dg_v1 | 0 | 764 | 0.0000 | [0.0000, 0.0000] | 0.0000 | 0.0000 | [0.0000, 0.0000] | 0.0000 |
| R2-DMB | ds_v2/dm_b_v1 | 0 | 41 | 0.0000 | [0.0000, 0.0000] | 0.0000 | 0.0000 | [0.0000, 0.0000] | 0.0000 |
| R2-DMB | ds_v2/dg_v1 | 40 | 771 | 0.0500 | [0.0000, 0.0741] | 0.0493 | 0.0007 | [-0.0005, 0.0013] | 0.0519 |
| R2-DMB | dm_b_v1/dg_v1 | 0 | 770 | 0.0000 | [0.0000, 0.0000] | 0.0000 | 0.0000 | [0.0000, 0.0000] | 0.0000 |
| R2-D_S | ds_v2/dm_b_v1 | 0 | 104 | 0.0000 | [0.0000, 0.0000] | 0.0000 | 0.0000 | [0.0000, 0.0000] | 0.0000 |
| R2-D_S | ds_v2/dg_v1 | 102 | 669 | 0.1461 | [0.0566, 0.1925] | 0.1424 | 0.0038 | [-0.0011, 0.0077] | 0.1525 |
| R2-D_S | dm_b_v1/dg_v1 | 0 | 667 | 0.0000 | [0.0000, 0.0000] | 0.0000 | 0.0000 | [0.0000, 0.0000] | 0.0000 |
| R3 | ds_v2/dm_b_v1 | 0 | 5 | 0.0000 | [0.0000, 0.0000] | 0.0000 | 0.0000 | [0.0000, 0.0000] | 0.0000 |
| R3 | ds_v2/dg_v1 | 5 | 92 | 0.0515 | [0.0103, 0.1031] | 0.0489 | 0.0027 | [0.0004, 0.0068] | 0.0543 |
| R3 | dm_b_v1/dg_v1 | 0 | 92 | 0.0000 | [0.0000, 0.0000] | 0.0000 | 0.0000 | [0.0000, 0.0000] | 0.0000 |

### Table C: all-three failures, unique catches and conditional recovery

| Regime | All-three FN | All-three JFN | CI | Unique catches (D_S/D_M-B/D_G) | Conditional recovery (D_S/D_M-B/D_G) |
|---|---|---|---|---|---|
| R0 | 2 | 0.0109 | [0.0000, 0.0273] | 0/50/0 | 0.0000/0.9615/0.0000 |
| R1 | 0 | 0.0000 | [0.0000, 0.0000] | 0/101/0 | UNDEFINED/1.0000/UNDEFINED |
| R2-DMB | 0 | 0.0000 | [0.0000, 0.0000] | 0/40/0 | UNDEFINED/1.0000/UNDEFINED |
| R2-D_S | 0 | 0.0000 | [0.0000, 0.0000] | 0/102/0 | UNDEFINED/1.0000/UNDEFINED |
| R3 | 0 | 0.0000 | [0.0000, 0.0000] | 0/5/0 | UNDEFINED/1.0000/UNDEFINED |

### Failure-pattern counts (bits = D_S, D_M-B, D_G miss)

| Regime | 000 | 001 | 010 | 011 | 100 | 101 | 110 | 111 |
|---|---|---|---|---|---|---|---|---|
| R0 | 24 | 89 | 0 | 0 | 18 | 50 | 0 | 2 |
| R1 | 35 | 663 | 0 | 0 | 1 | 101 | 0 | 0 |
| R2-DMB | 29 | 730 | 0 | 0 | 1 | 40 | 0 | 0 |
| R2-D_S | 29 | 565 | 0 | 0 | 2 | 102 | 0 | 0 |
| R3 | 5 | 87 | 0 | 0 | 0 | 5 | 0 | 0 |

### Table D: targeted attack behavior

| Regime | Target | Successes / attempts | Rate | CI | Transfer |
|---|---|---|---|---|---|
| R0 | none | NOT_APPLICABLE | NOT_APPLICABLE | NOT_APPLICABLE | NOT_APPLICABLE_NON_TARGETED_REGIME |
| R1 | none | NOT_APPLICABLE | NOT_APPLICABLE | NOT_APPLICABLE | NOT_APPLICABLE_NON_TARGETED_REGIME |
| R2-DMB | dm_b_v1 | 0/800 | 0.0000 | [0.0000, 0.0000] | ds_v2 0 (UNDEFINED); dg_v1 0 (UNDEFINED) |
| R2-D_S | ds_v2 | 104/698 | 0.1490 | [0.0599, 0.1959] | dm_b_v1 0 (0.0000); dg_v1 102 (0.9808) |
| R3 | ALL | 0/97 | 0.0000 | [0.0000, 0.0000] | NOT_APPLICABLE_TARGET_ALL |

### Table E: parent-child transitions

| Regime | Detector | catch->catch | catch->miss | miss->catch | miss->miss |
|---|---|---|---|---|---|
| R0 | - | NOT_APPLICABLE_NO_PARENT_CHILD_STRUCTURE |  |  |  |
| R1 | - | NOT_APPLICABLE_NO_PARENT_CHILD_STRUCTURE |  |  |  |
| R2-DMB | ds_v2 | 694 | 4 | 65 | 37 |
| R2-DMB | dm_b_v1 | 800 | 0 | 0 | 0 |
| R2-DMB | dg_v1 | 23 | 13 | 7 | 757 |
| R2-D_S | ds_v2 | 594 | 104 | 0 | 0 |
| R2-D_S | dm_b_v1 | 698 | 0 | 0 | 0 |
| R2-D_S | dg_v1 | 24 | 11 | 7 | 656 |
| R3 | ds_v2 | 89 | 0 | 3 | 5 |
| R3 | dm_b_v1 | 97 | 0 | 0 | 0 |
| R3 | dg_v1 | 3 | 2 | 2 | 90 |

### Table F: source-conditioned results

| Regime | Source | Attacks | Lineages | FN D_S/D_M-B/D_G | All-three FN | Target successes |
|---|---|---|---|---|---|---|
| R0 | ALL | - | - | SOURCE_DECOMPOSITION_UNAVAILABLE_IN_FROZEN_INPUTS | - | NOT_APPLICABLE |
| R1 | INJECAGENT_BASE | 400 | 1 | 86/0/399 | 0 | NOT_APPLICABLE |
| R1 | LLMAIL_INJECT | 400 | 96 | 16/0/365 | 0 | NOT_APPLICABLE |
| R2-DMB | INJECAGENT_BASE | 400 | 1 | 39/0/397 | 0 | 0 |
| R2-DMB | LLMAIL_INJECT | 400 | 96 | 2/0/373 | 0 | 0 |
| R2-D_S | INJECAGENT_BASE | 314 | 1 | 73/0/312 | 0 | 73 |
| R2-D_S | LLMAIL_INJECT | 384 | 93 | 31/0/355 | 0 | 31 |
| R3 | INJECAGENT_BASE | 1 | 1 | 1/0/1 | 0 | 0 |
| R3 | LLMAIL_INJECT | 96 | 96 | 4/0/91 | 0 | 0 |

### Figures

- `artifacts/research_protocol/synthesis/figures/01_fnr.svg`: Detector false-negative rate by regime
- `artifacts/research_protocol/synthesis/figures/02_pairwise_jfn.svg`: Pairwise joint false-negative rate (JFN)
- `artifacts/research_protocol/synthesis/figures/03_ejf.svg`: Excess joint failure (EJF) by detector pair
- `artifacts/research_protocol/synthesis/figures/04_fn_jaccard.svg`: False-negative Jaccard by detector pair
- `artifacts/research_protocol/synthesis/figures/05_all_three_jfn.svg`: All-three joint false-negative rate
- `artifacts/research_protocol/synthesis/figures/06_target_success.svg`: Targeted attack success: R2-DMB vs R2-D_S vs R3
- `artifacts/research_protocol/synthesis/figures/07_r2ds_transfer.svg`: Evasion transfer from successful targeted evasions (ETR)
- `artifacts/research_protocol/synthesis/figures/08_source_conditioned.svg`: Source-conditioned detector FNR
- `artifacts/research_protocol/synthesis/figures/09_failure_patterns.svg`: Failure-pattern distribution by regime
- `artifacts/research_protocol/synthesis/figures/10_verifier_status.svg`: Verifier recovery (RQ3) status

## 10. RQ1 Answer

**How does detector behavior change under distribution shift?**

Detector behavior changed in detector-specific directions under the R0 -> R1 shift at fixed operating thresholds. D_S attack recall rose (61.75% -> 87.25%) and its benign FPR fell (4.52% -> 2.80%). D_M-B kept near-complete attack recall (98.91% -> 100.00%) but its benign FPR rose (6.09% -> 13.20%). D_G attack recall fell (22.95% -> 4.50%) while its benign FPR rose (1.79% -> 20.70%). Distribution shift therefore did not affect the detectors uniformly. These are descriptive comparisons of unpaired populations with different source composition; R1 alone does not establish adaptive robustness.

- **RQ1-D_S** (OBSERVED): D_S: attack recall 61.75% (113/183) in R0 vs 87.25% (698/800) in R1 (FNR 38.25% -> 12.75%); benign FPR 4.52% (43/952) -> 2.80% (28/1000) at the same fixed operating threshold. Frozen ranking metrics: ROC-AUC 0.8968 -> 0.9743, AP 0.7316 -> 0.9749.
- **RQ1-D_M-B** (OBSERVED): D_M-B: attack recall 98.91% (181/183) in R0 vs 100.00% (800/800) in R1 (FNR 1.09% -> 0.00%); benign FPR 6.09% (58/952) -> 13.20% (132/1000) at the same fixed operating threshold. Frozen ranking metrics: ROC-AUC 0.9963 -> 1.0000, AP 0.9877 -> 1.0000.
- **RQ1-D_G** (OBSERVED): D_G: attack recall 22.95% (42/183) in R0 vs 4.50% (36/800) in R1 (FNR 77.05% -> 95.50%); benign FPR 1.79% (17/952) -> 20.70% (207/1000) at the same fixed operating threshold. Frozen ranking metrics: ROC-AUC 0.8150 -> 0.4069, AP 0.5007 -> 0.3779.
- **RQ1-ALL-THREE** (OBSERVED): All-three attack FN: 2/183 in R0 and 0/800 in R1.
- **RQ1-COMPOSITION** (LIMITATION): R0 contains 183 attacks and 952 benign samples (1134 lineages); R1 contains 800 attacks and 1000 hard-benign samples (1097 lineages). R1 attacks are 400 INJECAGENT_BASE (1 lineage) and 400 LLMAIL_INJECT (96 lineages). R0 has no frozen source decomposition in the synthesis inputs. The populations are unpaired and differ in source composition.
- **RQ1-SOURCE** (OBSERVED): R1 source-conditioned FNR: INJECAGENT_BASE: D_S 86/400 (21.50%), D_M-B 0/400 (0.00%), D_G 399/400 (99.75%); LLMAIL_INJECT: D_S 16/400 (4.00%), D_M-B 0/400 (0.00%), D_G 365/400 (91.25%). InjecAgent is a single inherited lineage cluster; its source-level behavior is not independent-case evidence.
- **RQ1-LIMITS** (LIMITATION): R0 -> R1 differences are descriptive: different, unpaired populations and sources at fixed thresholds; no single cause is attributed. R1 is a non-adaptive shifted population and does not establish adaptive robustness.

## 11. RQ2 Answer

**Do heterogeneous detectors retain complementary error behavior under targeted and ensemble-aware adversarial pressure, or do overlapping/common-mode failures emerge?**

At the three-detector stack level, no all-three common-mode failure was observed in the non-adaptive R1 reference or in any frozen targeted or ensemble-aware population: all-three FN was 0/800 (R1), 0/800 (R2-DMB), 0/698 (R2-D_S) and 0/97 (R3). Complementarity was not uniform. Under D_S-targeted pressure, 102 of 104 successful D_S evasions were also missed by D_G, whereas D_M-B missed 0 of them. D_M-B had 0/800 target evasions in R2-DMB and 0/97 misses in R3. In R3 every D_S miss (5) was also a D_G miss. Overlapping D_S/D_G failures emerged, but no all-three common-mode failure was observed for these frozen populations and fixed generators.

- **RQ2-R1-REFERENCE** (OBSERVED): R1 non-adaptive reference: all-three FN 0/800; shared FN D_S/D_M-B 0, D_S/D_G 101, D_M-B/D_G 0.
- **RQ2-R2-DMB** (OBSERVED): R2-DMB: 0/800 D_M-B target evasions (stored 95% CI [0.0000, 0.0000]); ETR to D_S and D_G is UNDEFINED / UNDEFINED because the target-success denominator is 0; all-three FN 0/800.
- **RQ2-R2-DS-TARGET** (OBSERVED): R2-D_S: 104/698 D_S target evasions (14.90%; stored 95% CI [0.0599, 0.1959]).
- **RQ2-R2-DS-DG-OVERLAP** (OBSERVED): Of the 104 successful D_S evasions, 102 were also missed by D_G (ETR 98.08%; stored 95% CI [0.9130, 1.0000]).
- **RQ2-R2-DS-DMB-RECOVERY** (OBSERVED): D_M-B missed 0 of the 104 successful D_S evasions (ETR 0.00%; stored 95% CI [0.0000, 0.0000]), so all-three FN in R2-D_S is 0/698.
- **RQ2-R3-ALL-THREE** (OBSERVED): R3: 0/97 simultaneous (all-three) evasions across 97 frozen lineage-distinct parents; all-three JFN 0.0; stored percentile-bootstrap 95% CI [0.0000, 0.0000] from a zero-event population (not a population robustness bound).
- **RQ2-R3-DETECTORS** (OBSERVED): R3 per-detector FN: D_S 5/97 (FNR 5.15%; stored 95% CI [0.0103, 0.1031]), D_M-B 0/97 (FNR 0.00%; stored 95% CI [0.0000, 0.0000]), D_G 92/97 (FNR 94.85%; stored 95% CI [0.8969, 0.9897]).
- **RQ2-R3-DS-DG** (OBSERVED): R3 D_S/D_G: shared FN 5, JFN 0.0515, FNR-product reference 0.0489, EJF +0.0027, FN Jaccard 0.0543. Every R3 D_S miss was also a D_G miss.
- **RQ2-DMB-COMPLEMENTARITY** (OBSERVED): D_M-B FN by regime: R0 2/183, R1 0/800, R2-DMB 0/800, R2-D_S 0/698, R3 0/97. Pairwise shared FN involving D_M-B (D_S/D_M-B, D_M-B/D_G): R0 2/2, R1 0/0, R2-DMB 0/0, R2-D_S 0/0, R3 0/0; in R1, R2-DMB, R2-D_S, R3 D_M-B shared no observed miss with either other detector.
- **RQ2-DG-BASE-RATE** (OBSERVED): D_G FNR by regime: R0 77.05%, R1 95.50%, R2-DMB 96.25%, R2-D_S 95.56%, R3 94.85%. Because D_G misses most attacks in every regime, D_S/D_G overlap is bounded by that base rate; D_S/D_G EJF by regime: R0 -0.0106, R1 +0.0045, R2-DMB +0.0007, R2-D_S +0.0038, R3 +0.0027. EJF is a descriptive deviation from the FNR-product reference, not a test of independence or evidence of causal dependence.
- **RQ2-R3-TRANSITIONS** (OBSERVED): R3 parent -> terminal transitions under the unchanged operational policy: D_S catch->miss 0, miss->catch 3, catch->catch 89, miss->miss 5; D_M-B catch->miss 0, miss->catch 0, catch->catch 97, miss->miss 0; D_G catch->miss 2, miss->catch 2, catch->catch 3, miss->miss 90.
- **RQ2-R3-SOURCES** (LIMITATION): R3 population: 97 parents, 97 inherited lineages; INJECAGENT_BASE 1 (all-three FN 0), LLMAIL_INJECT 96 (all-three FN 0). Source generalization is limited; the result concerns the frozen attack population and predefined generator.
- **RQ2-I1** (INTERPRETATION): D_S and D_G showed substantial overlap under the D_S-targeted regime.
- **RQ2-I2** (INTERPRETATION): D_M-B provided complete observed recovery for the 104 successful D_S evasions.
- **RQ2-I3** (INTERPRETATION): The fixed R3 ensemble-aware generator did not produce an all-three failure.
- **RQ2-I4** (INTERPRETATION): Detector diversity was not uniformly distributed: D_S/D_G failures overlapped, while D_M-B remained complementary in the observed R2-D_S and R3 samples.

## 12. Common-Mode Interpretation

Pairwise shared FN by regime (D_S/D_M-B, D_S/D_G, D_M-B/D_G): R0 2/52/2, R1 0/101/0, R2-DMB 0/40/0, R2-D_S 0/102/0, R3 0/5/0. D_G FNR by regime: R0 77.05%, R1 95.50%, R2-DMB 96.25%, R2-D_S 95.56%, R3 94.85%. D_S misses also missed by D_G: R0 52/70, R1 101/102, R2-DMB 40/41, R2-D_S 102/104, R3 5/5. D_S/D_G JFN by regime: R0 0.2842, R1 0.1263, R2-DMB 0.0500, R2-D_S 0.1461, R3 0.0515; D_S/D_G EJF: R0 -0.0106, R1 +0.0045, R2-DMB +0.0007, R2-D_S +0.0038, R3 +0.0027. EJF and the FNR product are descriptive references; they do not test independence and do not establish causal dependence between detector errors. All-three common-mode misses (pattern 111) by regime: R0 2/183, R1 0/800, R2-DMB 0/800, R2-D_S 0/698, R3 0/97.

## 13. D_M-B Complementarity Observation

D_M-B missed 0 of the 104 successful D_S evasions, had 0/800 target evasions under R2-DMB, and missed 0/97 R3 terminals. In R1, R2-DMB, R2-D_S and R3 it shared no observed miss with either other detector. This is complete observed recovery for these frozen populations and generators only; it does not establish that D_M-B is universally robust. Attack-side complementarity is reported separately from benign behavior: D_M-B benign FPR was 6.09% in R0 and 13.20% in R1 at the same threshold.

## 14. Zero-Event R3 Interpretation

The frozen R3 all-three CI [0.0, 0.0] is the empirical percentile-bootstrap result from a zero-event population. It is NOT a population robustness bound and is not a true attack-success probability of 0. Primary result: 0 observed simultaneous evasions / 97 frozen lineage-distinct parents.

Stored all-three JFN interval: [0.0, 0.0] (frozen 1000-replicate percentile bootstrap, seed 1701, lineage-clustered). No new inferential interval was added. The absence of all-three failures is evidence about the frozen 97-parent population and the predefined reversible generator and budget, not about arbitrary adversarial prompts.

## 15. Source and Lineage Limitations

R3: 97 parents, 97 inherited lineages, INJECAGENT_BASE 1, LLMAIL_INJECT 96. R3 source generalization is limited: InjecAgent contributes a single parent/lineage. In R1, R2-DMB and R2-D_S the InjecAgent attacks form one inherited lineage cluster, so source-level InjecAgent intervals are degenerate and not independent-case evidence. R0 has no frozen source decomposition. R0 and R1 are unpaired populations with different composition; R2 and R3 seed sets, objectives and budgets differ, so cross-regime comparisons are descriptive.

## 16. What Is NOT Established

- D_M-B is universally robust.
- The detector stack is unbreakable.
- Heterogeneous detectors are statistically independent.
- EJF proves causal dependence between detector errors.
- Zero observed R3 events prove zero underlying all-three risk.
- Results generalize to arbitrary adversarial prompts, other generators, budgets or sources.
- Verifier effectiveness (RQ3) or production guarantees.
- R1 alone does not establish adaptive robustness.
- No significance test or causal comparison was performed.

## 17. Verifier / RQ3 Status

R3 base-stack all-three failure population: 0. Development-stage verifier recovery denominator: 0. Development-stage Recovery(V_k): UNDEFINED for V1, V2 and V3. RQ3 remains NOT EMPIRICALLY IDENTIFIABLE FROM R3 DEVELOPMENT FAILURE POPULATION. Verifier panel: PENDING_FINAL_CONFIRMATION_OR_UNDEFINED. No verifier inference was run (0 queries) and no protected/final evaluation data was accessed. Phase-2 Track B owns the final RQ3 disposition.

## 18. Readiness for Research Freeze

Inputs: R0, R1, R2-DMB, R2-D_S and R3 frozen bundles validated and unchanged. Tests: 58 passed, 0 failed, 0 skipped (`tmp/cross_regime_synthesis_tests.xml`, SHA-256 `e5b8c0b092facfab4728cf7a70b9c10608ddb4bc6c3b900ada01c7b42e63aeba`). Synthesis outputs: 16 hash-bound files. Analysis commit: `fc208871b82a188b2661b5452281d983a82712c2`.

Verdict: **CROSS_REGIME_SYNTHESIS_COMPLETE_READY_FOR_RESEARCH_FREEZE**
