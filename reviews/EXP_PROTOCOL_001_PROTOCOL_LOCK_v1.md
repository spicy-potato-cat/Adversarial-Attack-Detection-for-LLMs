# EXP-PROTOCOL-001 Protocol Lock

Status: FROZEN; release exp_protocol_001_v1; READY_FOR_EXPERIMENT_PREFLIGHT.

The lock binds exact Phase-14 Git-source hashes, all prior inventories/code, OOF/direct R0 baselines, schemas, detector order, score/calibration semantics, exact thresholds/IDs/operator, and production defaults. Its nonrecursive self-hash excludes only manifest_hash.

Official verification anchors the lock and Phase-15 code/inventory/report to the direct accepted child of the Phase-14 commit on first-parent history. A mutable adjacent hash file is not a trust anchor. No official evaluation can run before that commit exists.

ExperimentRequest is strict and forbids extra keys. Official evaluation exposes no detector, threshold, fitting, calibration, metric, or bootstrap-default overrides. It calls preflight before consuming canonical predictions, applies only the verified frozen policy, requires STRICT_COMPLETE, then reuses frozen core/uncertainty/bundle contracts. No fit/load/download/persistence path exists.

Synthetic R1, three R2 targets, and R3 exercise preflight only. TEST_FIXTURE cannot publish official results. R2/R3 require clustered lineage and attack/validity provenance. Protected evaluation may be read-only; any fitting/adaptation action is rejected for every partition.

D_M-A remains comparator-only. Operational/descriptive view mixing is forbidden. No partitions or frozen files change; R1/R2/R3 are NOT_STARTED; Cycle 2 DEFERRED.
