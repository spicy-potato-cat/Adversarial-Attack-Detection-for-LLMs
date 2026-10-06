# EXP-PROTOCOL-001 Phase 11: Deterministic Uncertainty

Scope: synthetic correctness and additive uncertainty around the frozen
Phases 6-10 formulas. No detector execution, training, threshold fitting, or real
R1/R2/R3 data. Real accepted R0 import is prohibited until the Phase-11/12 commit.

## Contract

- `PERCENTILE_BOOTSTRAP_V1`: 1,000 replicates, seed 1701, 95% confidence.
- NumPy 2.1.3 `Generator(PCG64)`, explicit `quantile(method="linear")` at
  0.025 and 0.975. The contract binds the NumPy version.
- Explicit `SAMPLE_PAIRED` and `LINEAGE_CLUSTERED`; detector columns stay
  together. Resampling uses indices, never duplicate persisted canonical IDs.
- Explicit attack-only, benign-only, stratified-label, and valid-target-attempt
  domains. Shared R2/R3 descendants require clustering. Mixed-label lineages
  cannot be split for stratification.
- Report the observed frozen-core metric, not the bootstrap mean.
- Exclude undefined replicates. An undefined observed point has null CI.
  Defined points need at least 95% valid replicates; otherwise the interval is
  null with `UNSTABLE_DENOMINATOR`. Other experiment metrics remain usable.
- Rates remain bounded; negative EJF is preserved.
- Paired deltas are current B minus reference A on identical indices, requiring
  exact sample/lineage/metadata correspondence and compatible decision views.
- An explicitly supplied shared PCG64 stream supports documented historical
  sequential resampling. Record before/after RNG-state hashes and the plan hash;
  default calls reset the generator from the declared seed.

## Implementation And Validation

`uncertainty.py` reuses the frozen `_Accounting` formulas on ephemeral weighted
tallies. It does not modify core code or publish bootstrap replicas as canonical
experiments. The observed point always uses `evaluate_core` on the complete,
hash-validated alignment.

Synthetic fixtures cover ordinary paired rows, multiple descendants per lineage,
sparse recovery, R2 evasion/transfer, and paired deltas. Tests include corrupted
plans, wrong domains, undefined points, zero target evasions, strict support
boundaries, nonfinite values, deterministic serialization, and an inference/raw-
data access prohibition. The hash inventory binds code, tests, and expected
outputs. Final executed test totals are recorded in the Phase-11/13 test report.

Artifacts: `artifacts/research_protocol/uncertainty/` and
`phase11_12_artifact_hashes_v1.json`.

No p-values, significance labels, causal interpretation, or Phase-14 execution.
