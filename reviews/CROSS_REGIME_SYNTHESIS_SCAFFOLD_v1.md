# Cross-regime synthesis scaffold v1

Baseline: `71e3a5239cb24a3e59e99d271c6aa46841dbc084`. Pre-R3-only preparation, R3 `AWAITING_FROZEN_R3_BUNDLE`.
The baseline SHA is the published commit that first adds the named integration receipt; the receipt has no self-referential SHA field. Its R3/verifier query counts are zero and protected access is false.

## RQ1: How does detector behavior change under distribution shift?

Machine-generated descriptive operational evidence:

| Regime | Attacks | Benign | DS recall / FPR | DMB recall / FPR | DG recall / FPR | All-three FN |
|---|---:|---:|---|---|---|---:|
| R0 | 183 | 952 | 61.7486% / 4.5168% | 98.9071% / 6.0924% | 22.9508% / 1.7857% | 2 |
| R1 | 800 | 1000 | 87.2500% / 2.8000% | 100.0000% / 13.2000% | 4.5000% / 20.7000% | 0 |
| R2-DMB | 800 | 0 | 94.8750% / NOT_APPLICABLE | 100.0000% / NOT_APPLICABLE | 3.7500% / NOT_APPLICABLE | 0 |
| R2-D_S | 698 | 0 | 85.1003% / NOT_APPLICABLE | 100.0000% / NOT_APPLICABLE | 4.4413% / NOT_APPLICABLE | 0 |
| R3 | NOT_YET_OBSERVED | NOT_YET_OBSERVED | NOT_YET_OBSERVED | NOT_YET_OBSERVED | NOT_YET_OBSERVED | NOT_YET_OBSERVED |

R0 and R1 have different populations and are unpaired. R2 regimes contain attacks only, so benign FPR, ROC-AUC and AP are NOT_APPLICABLE. Compare FNR descriptively while retaining sample composition and lineage support; do not attribute rate differences to a single cause. Frozen score-ranking metrics are carried separately from operating-threshold metrics in Table A.

R3 evidence and distribution-shift interpretation: **NOT_YET_OBSERVED**.

## RQ2: Do heterogeneous detectors develop overlapping/common-mode failures under targeted/adaptive attack?

Tables B/C carry all three pairwise JFN, the FNR-product reference, EJF, FN Jaccard, and all-three JFN with stored 95% intervals. The FNR product is a reference quantity, not an independence assumption. Table D carries target evasion and ETR; Table E preserves frozen paired parent-child transitions.

R2-DMB has 0 target evasions, so its ETRs remain UNDEFINED. Frozen R2-D_S has 104 target evasions in 698 attacks; 102 also evade DG and 0 evade DMB. The two frozen targeted populations have all-three FN counts 0 and 0. These observations do not establish immunity under future adaptive attack. R0 has 2 common-mode misses; R1 has 0.

R3 pairwise/common-mode conclusions: **NOT_YET_OBSERVED**. Verifier recovery: **NOT_YET_OBSERVED**. No substitute failure population will be introduced if the final R3 all-three population is empty.

## Reproducible artifacts

Run `python -B -m detection_service.research_protocol.phase1_synthesis --output artifacts/research_protocol/synthesis/generated` from this isolated checkout. The loader reads only its explicit Git-object allowlist at the integration SHA. `regime_registry_pre_r3_v1.json` records paths, hashes, and stored interval/config provenance. `generated/tables_v1.json` contains Tables A–E; `generated/figure_data_v1.json` supplies nine SVG exports.

Frozen intervals are copied unchanged. The existing full-bundle validator derives an uncertainty hash using runtime NumPy; this loader validates core relations separately and checks stored interval points/provenance without replacing the generating-version hash or rerunning bootstrap. Source analysis retains original lineage/support cautions. Future R3 ingestion is an explicit Phase 2 call through the committed-reader freeze gate.

## Remaining interpretation slots

R3 source/family support, all-three uncertainty, adaptive terminal behavior, and verifier recovery must be populated from Track A's final frozen handoff. No R3 outcomes were read in Phase 1. Any causal comparison, significance claim, or protected confirmation requires its separately authorized protocol.
