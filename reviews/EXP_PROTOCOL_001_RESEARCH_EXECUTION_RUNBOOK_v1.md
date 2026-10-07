# EXP-PROTOCOL-001 Research Execution Runbook v1

This is a future workflow specification, not authorization to acquire data or run
R1/R2/R3 now. Release exp_protocol_001_v1; primary view OPERATIONAL_FIXED_V1.

1. Create/validate the canonical regime manifest; freeze membership, sources,
   revisions, truth, partition, generation/target/lineage and validity metadata.
2. Run protocol preflight before accessing model runtime or publishing results.
   `python -m detection_service.research_protocol.protocol_lock --request REQUEST.json`
   REQUEST is a strict ExperimentRequest with declared bootstrap_unit; no overrides.
3. Verify dataset/sample/lineage integrity and dataset-specific authorization.
   Preflight does not supply a missing dataset approval or establish independence.
4. Run the frozen detector adapters only under the experiment's separate execution
   authorization. Preserve actual runtime failures and exact model/code hashes.
5. Validate canonical prediction records and join every primary detector/sample.
   D_M-A is comparator-only; unknown/missing/non-OK rows are not benign predictions.
6. Apply the verified Phase-5 frozen operating policy, using D_S calibrated score,
   D_M-B raw softmax, D_G raw maximum chunk score and exact inclusive thresholds.
7. Verify STRICT_COMPLETE alignment. Refuse official metrics on incomplete coverage.
8. Compute unchanged core metrics, retaining counts and all denominators.
9. Compute production uncertainty using the predeclared unit and domain. Generated
   descendants require LINEAGE_CLUSTERED; record valid/invalid replicate counts.
10. Create the hash/provenance-bound regime result bundle with OPERATIONAL_FIXED_V1.
11. Compare with the compatible frozen R0 operational baseline. Dataset deltas are
    unpaired; do not compare to historical descriptive R0 as though policies match.
12. Optionally compute a secondary descriptive frontier only if separately
    authorized, under its own versioned view. It never changes operational fields.
13. Hash all input/output/code/policy evidence; use deterministic serialization.
14. Freeze the experiment result bundle, report failures/uncertainty, and preserve
    model/run versus evidence commit provenance separately.

No threshold fitting, calibration fitting, training, detector selection, or
definition changes may occur between any steps.

## R1
R1_SHIFTED_UNSEEN; target_detector null. Primary purpose: unseen/distribution-shift
generalization. Declare the bootstrap unit from actual lineage before interpreting
results; retain unknowns rather than assume independence. Secondary descriptive
analysis needs authorization. Do not adapt after seeing R1.

## R2
R2_SINGLE_DETECTOR_TARGETED; one target D_S, D_M-B, or D_G per experiment.
Record attack method/revision, generator/revision where applicable, parent,
lineage, valid-attempt state, target and attack-success definition. Use
LINEAGE_CLUSTERED for descendants. Analyze TargetEvasionRate over valid attempts,
ETR over valid target evasions to each untargeted detector, individual metrics,
common mode, patterns, unique catch and recovery.

## R3
R3_ENSEMBLE_TARGETED; target ALL. Record generation and lineage provenance;
cluster descendants. Analyze individual failures, pairwise JFN/EJF/Jaccard,
all-three JFN, patterns and recovery. R2 target-to-detector ETR is NOT_APPLICABLE.

## Runtime And Governance Boundaries
Frozen adapters remain unchanged. In particular, D_S live loading is explicitly
unavailable in the active Phase-3 adapter; its accepted implementation/artifacts
remain preserved locally. This runbook does not silently reconstruct that runtime.
A future live-scoring authorization must resolve that execution prerequisite
without changing the frozen recipe or replacing OOF evidence with in-sample scores.
R0 historical reproduction and this closeout require no live adapters.

Stop on any failed preflight, missing frozen evidence, runtime prerequisite,
incomplete prediction, drift, unexpected download, provenance conflict, or leakage.
Do not change policy to recover a run. Verifier experiments are separate, after
base-stack R1/R2/R3 evidence; no V1/V2/V3 selection or router is included here.

R1 HAS NOT STARTED. R2/R3 NOT_STARTED. Cycle 2 DEFERRED. Protected/final and verifier
experiments NOT_STARTED. No future-regime data was used to modify this protocol.
