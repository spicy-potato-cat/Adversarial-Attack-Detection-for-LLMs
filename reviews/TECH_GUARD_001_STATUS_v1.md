# TECH-GUARD-001 Standalone Status v1

Date: 2026-10-02. Status: PASS.
Recommendation: READY FOR TECH-INTEGRATION-002. NOT READY FOR E1-E10.

Existing workspace reused, branch tech/guard-001, continuation start dd82539.
Original blocked assessment preserved in Git and qualification history.
sumitt86 authenticated pinned access now passes; candidate unchanged:
meta-llama/Llama-Prompt-Guard-2-22M,
revision 11614a155199674a0a95e6602d6ab0417b790ed0.
D_G / guard_external / dg_v1.

## Acceptance

| Gate | Result |
|---|---|
| Authorized access/exact pinned snapshot | PASS |
| Candidate unchanged/provenance and hashes frozen | PASS |
| Standalone BaseDetector/DetectorResult | PASS |
| Documented class-1 softmax/native default decision | PASS |
| calibrated_probability=None | PASS |
| Explicit chunks/overlap/special accounting/full tail | PASS |
| Max aggregation/model reuse | PASS |
| Explicit failures/no fallback | PASS |
| Real pinned CPU smoke/determinism | PASS |
| Guard units | 49 PASS |
| Existing-detector synthetic regressions | 102 PASS |
| Combined | 151 PASS, 0 FAIL, 0 SKIP, 9 data-reading tests deselected |
| D_G training/fine-tuning/project calibration | NO |
| Project/protected data used | NO |
| E1-E10/protected evaluation/threshold optimization | NO |

No package installation needed. Compatible installed CPU-only Torch.
D_S/D_M-A/D_M-B implementations/tests/calibrations/artifacts, main/API/shared
contracts, semantic completion reports and shared status v6 remain unchanged.
Central default service wiring: DEFERRED to TECH-INTEGRATION-002.

## Evidence And Limits

artifacts/models/dg_v1/: model_config.json, freeze_metadata.json,
integrity_manifest.json, smoke_evidence.json, test_evidence.json.
Five finalized guard-specific reports accompany this evidence.
Weights/caches/tokens/raw data/virtual environments are not committed.
Local implementation/evidence commit only; no push authorized.

Synthetic checks are not scientific performance. External performance is not yet
benchmarked in this project. Default decisions are not final experimental operating
points. Max chunk score is not project-calibrated whole-document probability.
English-oriented training, distribution shifts, adaptive attacks and unknown
upstream benchmark exposure remain limitations. No successful-compromise,
disjoint-data, independence, superiority or legal-clearance claim.
Distribution/attribution obligations require separate review.

Next separately authorized work: minimal settings/startup/error/routing integration
documented in the implementation report. No experiment starts in this phase.
