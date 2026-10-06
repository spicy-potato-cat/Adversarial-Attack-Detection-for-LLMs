# EXP-PROTOCOL-001 Phase 12: Cross-Regime Contract

Scope: six synthetic regime bundles, not six real experiments.

## Representation

`RegimeResultBundle` binds experiment, dataset revision, partition, regime,
target, decision/comparison view, detector/prediction/regime/core hashes,
operational policy when applicable, complete population/lineage accounting,
frozen core sections, and optional provenance-bound uncertainty.

Supported slots: R0, R1, R2-D_S, R2-D_M-B, R2-D_G, R3.

Supported views: `OPERATIONAL_FIXED_V1`, `NATIVE_V1`, and historical descriptive
1%, 3%, and 5% versions. Historical descriptive results do not inherit Phase-5
operational thresholds. Operational results require the exact frozen policy SHA.

## Comparison

Compatibility requires the same primary physical identities/order, detector
manifest, core definition hash, label semantics, and decision/comparison view.
Policy or view mismatch is rejected or yields `INCOMPATIBLE` without deltas.

Compatible differences are current minus reference, in fractions and percentage
points. Cross-regime differences are descriptive and unpaired; paired inference
requires a separate declared correspondence and the Phase-11 API. No conclusions
are derived from overlapping or non-overlapping CIs.

Matrix states are `OBSERVED`, `NOT_RUN`, `NOT_APPLICABLE`, `UNDEFINED`, and
`INCOMPATIBLE`. Missing experiments have null values, not zeros. Target evasion
and ETR appear only in the matching R2 target column; R0/R1/R3 are inapplicable.

## Validation

Synthetic tests cover all six slots, exact placement, missing and incompatible
results, rate deltas, serialization, complete primary binding, and an actual
synthetic operational bundle compared against a descriptive bundle. Artifacts
are under `artifacts/research_protocol/cross_regime/`; the Phase-11/12 hash
inventory freezes code, tests, fixtures, and outputs before real R0 import.

R1/R2/R3 real experiments, Cycle 2, the verifier, and Phase 14 remain unstarted.
