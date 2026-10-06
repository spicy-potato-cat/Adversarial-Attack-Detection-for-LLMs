# EXP-PROTOCOL-001 Phases 6-10: Test Report

Status: **PASS**. Synthetic correctness only; no real experiment results.
Final verdict: **PHASES_6_TO_10_COMPLETE_READY_FOR_PHASE_11**.
Phase 11 is not started.

## Prerequisites

Local and fetched remote starting HEAD both matched
`c7799a578dea767368b93605bd64a29fed6d8fb1`; working tree was clean.
All nine requested detector/schema/adapter/regime/operating-policy/score/evidence
hashes matched before implementation. There was no regeneration of prior artifacts.

## Final Regression

```powershell
.\.local-python\python.exe -m pytest detection_service/tests/test_detector_semantics.py detection_service/tests/test_prediction_adapters.py detection_service/tests/test_regime_contract.py detection_service/tests/test_operating_policy.py detection_service/tests/test_core_metrics.py -q -p no:cacheprovider --junitxml=artifacts/research_protocol/phase6_10_tests_v1.xml
```

**440 tests; 440 passed; 0 failed; 0 errors; 0 skipped**.
This is 344 earlier protocol tests plus 96 new core-metric cases.
Runtime: 352.355 seconds.
Receipt SHA-256:
`3645355ef88d7268a37337ec765f520bcac93bf6a91b7c14f6c0f96cfd313f92`.

The initial synthetic run had 93 passes, one failure, and one temporary skip.
The failure was a test expecting a raw contract exception when Pydantic correctly
wrapped rejection of a tampered alignment hash as `ValidationError`. The
assertion was corrected; the rejection was not weakened. The temporary skip
was the not-yet-created contract artifact check; it ran and passed after freeze.
A numerical review also made the independence reference explicitly multiply the
reported FNR values, with a non-binary-exact decimal test. Four focused repair
checks passed before the final regression. Temporary receipts were removed;
the authoritative final receipt and this history are retained.

## Coverage

| Area | Verified |
|---|---|
| Alignment | Canonical IDs/order, exact labels, batch experiment/hash/partition/threat binding, evidence kind, schema, roles/models, comparator exclusion |
| Strict coverage | Missing/non-OK/requested-decision failures, diagnostic null preservation, every metric entry point blocks incomplete tables |
| Decision views | Only OPERATIONAL/NATIVE/EXPLICIT, named explicit provenance, strict binary values, no implicit score-to-decision conversion |
| Operational | Exact verified Phase-5 policy, score/threshold/ID/hash binding, rejected overrides, failure nulls, no automatic fitting |
| Individual | Exact confusion counts, accuracy, precision, recall, specificity, F1, FPR, FNR, NPV, correct denominators |
| Undefined rates | Zero precision/attack/benign/union/recovery/transfer denominators, empty populations, explicit null/status/reason |
| Common-mode | One failure indicator, matching individual FNRs, shared counts/JFN, product reference, positive/negative EJF, Jaccard, three-way JFN |
| Patterns | All eight bit patterns, S/M/G order, 0 catch/1 miss, sum/marginal/pair/111 invariants, exhaustive single-attack binary cases |
| Recovery | 011/101/110 unique catches, attack-rate denominator, both-other-miss denominators, zero opportunity null |
| R2 | All three targets and six transfer directions, 100/40/10/20 known counts, invalid/benign exclusions, zero evasions/valid attempts, attack-success separation |
| Lineage | 309 rows preserved, 15 shared lineages, parents preserved, per-target valid/evasion lineage counts |
| R3 | R2 transfer entry point rejects R3; no invented R3 ETR |
| Provenance | Context/hash binding for every versioned result envelope, inconsistent counts rejected, immutable alignment hash validation |
| Determinism | Input-order invariance, repeated fixture results, JSON roundtrip, canonical ordering and terminal LF |
| No inference | Import audit rejects ML libraries/raw prompts/R0 manifest access; detector `predict` and live loading patched to fail during synthetic evaluation |

## Independent Acceptance Accounting

Saved synthetic outputs were checked independently against hand-declared counts,
without invoking metric functions or any detector:

- Core: 10 total / 8 attacks / 2 benign; each detector TP/FP/TN/FN = 4/1/1/4.
- Each failure pattern count = 1; total = 8.
- Every primary pair: shared FN = 2, union = 6, JFN = 1/4, EJF = 0.
- All-three FN = 1, JFN = 1/8; each unique catch = 1; recovery = 1/2.
- Each R2 target: 100 valid adversarial attempts, 40 target evasions,
  joint transfers 10 and 20; target rate = 40%, ETR = 25% and 50%.

`core_metrics_contract --mode freeze` returned PASS. Its read-only checker
verified 11 artifact/code/test hashes and rebuilt synthetic artifacts
byte-identically; the final regression repeated this check. It does not compute
accepted real R0 metrics. Parent catalog bytes have their own manifest evidence hash.

## Preservation

165/165 accepted Cycle-1 integrity checks passed, including all 96 baseline
preservation checks. Phase-3 inventory: 6/6; Phase-4 inventory: 14/14;
Phase-5 inventory: 12/12. The operating manifest hash remains
`06fa4548a62ae0e0968f9d93339910f8841a0f366b5346b0892a2be6904fb0cc`.
All three Phase-5 thresholds, calibrators, native rules, schemas, model weights,
and earlier code remain unchanged. Only new metric code/tests/evidence/reports
and three narrow `.gitattributes` byte-preservation entries are included.

Existing Phase-4 regression tests verify historical R0 membership metadata only.
No accepted R0 confusion matrices/JFN results were reproduced, no real detector
inference ran, and no protected data was supplied to metrics. Integrity hashing
of accepted files is preservation work, not performance analysis.

No package installation, training, recalibration, threshold reselection,
statistical detector restoration, R1 acquisition, R2 real attack generation,
R3 experiment, Cycle-2 work, verifier/router, bootstrap, confidence intervals,
cross-regime comparison, or Phase-13 real R0 reproduction occurred.

## Publication

The synthetic contract, fixtures, expected outputs, parent metadata, five new
code/test files, final regression receipt, and two required reports are the
publication scope. No raw datasets/prompts or model weights are staged.
All 39 acceptance criteria pass. Final commit and normal push/fetch synchronization
are verified and reported in the final response; prior run provenance is untouched.
