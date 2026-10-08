# DS-NUMERICAL-001 FINAL REPORT

STATUS: UNRESOLVED

## 243-Record Historical Equivalence Recheck

Records: 243. Historical equivalence still reproducible: YES.

Raw maximum/median/p95: 3.4861002973229915e-14 / 2.2204460492503131e-16 / 5.2999271638043344e-15.

Calibrated maximum/median/p95: 1.902644708451362e-14 / 9.0205620750793969e-17 / 2.8782531913407164e-15.

Raw >1e-12: 0; calibrated >1e-12: 0. Native mismatches: 0; operational mismatches: 0.

Exact original 233 CALIBRATION plus 10 BASE_TRAIN records, no supplementary long query. All 243 use one LM chunk; 238 short/single-feature-window and five medium/multiple-feature-window records. No >1024, >4096 or truncated records in this corpus; those strata cannot establish long-input reproduction.

## First Seed Repeatability

Same-process runs: 100. Raw min/max: 0.9254972378912807 / 0.9254972378912807; calibrated min/max: 0.844565288092724 / 0.844565288092724. Each has one distinct binary64 value and exact range zero.

Raw mathematical population stddev: 0; calibrated: 0. The NumPy summary reports raw stddev 2.22e-16 from mean-reduction rounding of identical values; this is not observed score variation.

Cross-process runs: 10 distinct fresh processes. Raw/calibrated maximum deltas: 0.0 / 0.0. Each has one distinct binary64 value; stddev values in the JSON summary include ordinary reduction rounding. Runtime deterministic: YES in these observations, not a universal guarantee.

The first seed exactly matches frozen R1 raw 0.9254972378912807 and calibrated 0.844565288092724 in every present-day repeat. Its profile is 101 input tokens, 100 analyzed, one LM chunk, one feature window, no truncation.

## Runtime

Python: 3.11.9 (tags/v3.11.9:de54cf5, Apr  2 2024, 10:12:12) [MSC v.1938 64 bit (AMD64)]

- numpy: 2.1.3
- scikit-learn: 1.6.1
- scipy: 1.17.1
- torch: 2.6.0
- transformers: 4.49.0

Device: CPU. Reference LM/logits/log-softmax: float32. Input IDs: int64. Token tensor values widen exactly to Python binary64; statistical reductions, 26 features, LR coefficients/intercept/probability and calibration are float64. No float16/bfloat16 transition.

model.eval confirmed during all forward passes; active dropout absent; inference_mode enabled; gradients disabled inside forward; parameters require_grad false. Tokenizer/preprocessing source uses deterministic tokenization/prefix/chunk selection, not sampling. CPU architecture/BLAS build and random-state hashes are stored in ds_runtime_environment_v1.json. NumPy/Python seed origin UNKNOWN; diagnostic did not seed either.

The unchanged accepted loader sets torch seed 1701, eight threads and deterministic algorithms True. Before/after settings, cuDNN and TF32 flags are recorded without diagnostic changes. TF32 is irrelevant to observed CPU execution. No installs or environment-variable changes performed.

## Device / Precision Findings

CPU vs normal-path delta: NOT_APPLICABLE_ALREADY_CPU.

Same captured logits, float64 diagnostic log-softmax: raw signed delta 2.0933414252022331e-06; calibrated signed delta 4.9371045438562078e-06; max token-surprisal delta 3.721801357581267e-05. No extra LM invocation or substitution into accepted D_S.

Feature sensitivity sufficient in scale to explain ~1e-7 drift: YES as plausibility, NOT causal attribution. One-float32-epsilon independent-feature L1 first-order bound: 4.4625029910473969e-07. Correlated features and CDF boundaries limit this estimate. NumPy mean vs statistics.fmean delta on the same widened surprisals: 0.0. Reduction-order difference alone did not explain the prior discrepancy in this comparison.

Feature index/name/value/binary64 hex, LR derivative and upstream calculation are in ds_feature_sensitivity_v1.json; all 26 and inherited window statistics are retained.

## R1 Diagnostic Samples

Samples replayed: 9. Raw >1e-12: 0; calibrated >1e-12: 0. Largest raw/calibrated deltas: 0 / 0. Native/operational mismatches: 0 / 0.

Selection was persisted before scoring and uses first-parent membership and source/token-length metadata only, never replay outcomes. Source-specific minima/medians/maxima and additional length coverage are retained; max ten samples, not all 698.

```json
{
  "by_source": {
    "INJECAGENT_BASE": {
      "calibrated": {
        "above_tolerance": 0,
        "maximum": 0.0,
        "median": 0.0,
        "p95": 0.0
      },
      "count": 5,
      "native_mismatches": 0,
      "operational_mismatches": 0,
      "raw": {
        "above_tolerance": 0,
        "maximum": 0.0,
        "median": 0.0,
        "p95": 0.0
      }
    },
    "LLMAIL_INJECT": {
      "calibrated": {
        "above_tolerance": 0,
        "maximum": 0.0,
        "median": 0.0,
        "p95": 0.0
      },
      "count": 4,
      "native_mismatches": 0,
      "operational_mismatches": 0,
      "raw": {
        "above_tolerance": 0,
        "maximum": 0.0,
        "median": 0.0,
        "p95": 0.0
      }
    }
  },
  "length_window": {
    "gt1024": {
      "calibrated": {
        "above_tolerance": 0,
        "maximum": 0.0,
        "median": 0.0,
        "p95": 0.0
      },
      "count": 2,
      "native_mismatches": 0,
      "operational_mismatches": 0,
      "raw": {
        "above_tolerance": 0,
        "maximum": 0.0,
        "median": 0.0,
        "p95": 0.0
      }
    },
    "gt4096": {
      "calibrated": {
        "above_tolerance": 0,
        "maximum": 0.0,
        "median": 0.0,
        "p95": 0.0
      },
      "count": 1,
      "native_mismatches": 0,
      "operational_mismatches": 0,
      "raw": {
        "above_tolerance": 0,
        "maximum": 0.0,
        "median": 0.0,
        "p95": 0.0
      }
    },
    "medium_128_1024": {
      "calibrated": {
        "above_tolerance": 0,
        "maximum": 0.0,
        "median": 0.0,
        "p95": 0.0
      },
      "count": 3,
      "native_mismatches": 0,
      "operational_mismatches": 0,
      "raw": {
        "above_tolerance": 0,
        "maximum": 0.0,
        "median": 0.0,
        "p95": 0.0
      }
    },
    "multiple_feature_windows": {
      "calibrated": {
        "above_tolerance": 0,
        "maximum": 0.0,
        "median": 0.0,
        "p95": 0.0
      },
      "count": 5,
      "native_mismatches": 0,
      "operational_mismatches": 0,
      "raw": {
        "above_tolerance": 0,
        "maximum": 0.0,
        "median": 0.0,
        "p95": 0.0
      }
    },
    "multiple_lm_chunks": {
      "calibrated": {
        "above_tolerance": 0,
        "maximum": 0.0,
        "median": 0.0,
        "p95": 0.0
      },
      "count": 2,
      "native_mismatches": 0,
      "operational_mismatches": 0,
      "raw": {
        "above_tolerance": 0,
        "maximum": 0.0,
        "median": 0.0,
        "p95": 0.0
      }
    },
    "not_truncated": {
      "calibrated": {
        "above_tolerance": 0,
        "maximum": 0.0,
        "median": 0.0,
        "p95": 0.0
      },
      "count": 8,
      "native_mismatches": 0,
      "operational_mismatches": 0,
      "raw": {
        "above_tolerance": 0,
        "maximum": 0.0,
        "median": 0.0,
        "p95": 0.0
      }
    },
    "short_lt128": {
      "calibrated": {
        "above_tolerance": 0,
        "maximum": 0.0,
        "median": 0.0,
        "p95": 0.0
      },
      "count": 4,
      "native_mismatches": 0,
      "operational_mismatches": 0,
      "raw": {
        "above_tolerance": 0,
        "maximum": 0.0,
        "median": 0.0,
        "p95": 0.0
      }
    },
    "single_feature_window": {
      "calibrated": {
        "above_tolerance": 0,
        "maximum": 0.0,
        "median": 0.0,
        "p95": 0.0
      },
      "count": 4,
      "native_mismatches": 0,
      "operational_mismatches": 0,
      "raw": {
        "above_tolerance": 0,
        "maximum": 0.0,
        "median": 0.0,
        "p95": 0.0
      }
    },
    "single_lm_chunk": {
      "calibrated": {
        "above_tolerance": 0,
        "maximum": 0.0,
        "median": 0.0,
        "p95": 0.0
      },
      "count": 7,
      "native_mismatches": 0,
      "operational_mismatches": 0,
      "raw": {
        "above_tolerance": 0,
        "maximum": 0.0,
        "median": 0.0,
        "p95": 0.0
      }
    },
    "truncated": {
      "calibrated": {
        "above_tolerance": 0,
        "maximum": 0.0,
        "median": 0.0,
        "p95": 0.0
      },
      "count": 1,
      "native_mismatches": 0,
      "operational_mismatches": 0,
      "raw": {
        "above_tolerance": 0,
        "maximum": 0.0,
        "median": 0.0,
        "p95": 0.0
      }
    }
  }
}
```

## Historical R1 Environment

Device known: YES (CPU). Dependency versions known: NO for the inference process. Accepted entrypoint/loader/run-code hashes are known; exact shell invocation, machine ID, backend build, container and process-specific package receipt are UNKNOWN. Training receipts and R1 uncertainty NumPy version are not substituted for inference evidence.

Earlier repair receipt: OMP_NUM_THREADS=4, MKL_NUM_THREADS=4. Current shell: both unset. Both receipts show matching package versions, CPU, float32, eight torch threads, deterministic algorithms True. These observed setting differences are candidates, not an isolated A/B proof. The task forbids changing this environment, so no four-thread-shell reproduction was attempted.

## Root Cause

Classification: INSUFFICIENT_HISTORICAL_EVIDENCE

First causal stage: NOT PROVEN. Earliest observed difference between prior and current numeric captures is token surprisal, before feature construction/LR/calibration: 82/100 tokens differ, max 8.58306884765625e-06; feature max delta 3.814697265625e-06. Prior LM logits are missing, so forward-kernel versus log-softmax origin cannot be separated.

Current original-corpus and first-parent reproduction rule out a blanket present-runtime failure, and repeats found no current nondeterminism. They do not explain why the earlier repair execution differed, nor prove historical dependencies were identical.

## Scientific Meaning

Score reproducibility preserved: YES for current authorized diagnostic records; NO for the previously recorded mismatching repair replay. Decision reproducibility preserved: YES for observed comparisons. Evidence detector behavior materially changed: NO in these records, UNKNOWN outside them. No use of decision agreement to waive the frozen 1e-12 score gate.

## Integrity

Tolerance, threshold, model, calibrator, feature schema, reference revision and attack generator changed: NO. R2 generation restarted: NO. D_M-B/D_G/ensemble queries: 0. R3 started: NO. Track B modified: NO. R1 evidence overwritten: NO. Raw prompts/token IDs remain local and ignored, not committed.

Diagnostic-only D_S calls: 362 = 243 equivalence + 100 same-process + 10 fresh-process + 9 R1 baselines. Separate previous repair calls: 1. Historical failed attempt count remains UNKNOWN, bounded 1-61. Accepted R2 terminals: 0. Every current call has an fsync-backed logical request and returned-score receipt using the unchanged 35b88f7 journal.

## Tests

Passed: 200; failed: 0; skipped: 0. Baseline preservation 96/96; release 118/118; source preservation 503/503; protocol patch 262/262. No preexisting tracked file changed relative to start.

## Git

Start HEAD: 35b88f7fd445e209434e77474862818211c2043c

Diagnostic scoring-code commit: 0697ccdea0306f8f209b8594aba0bc4ba205c074

Evidence is a separate post-run commit on exp/r2-ds-001. Its final/remote SHA and clean-tree confirmation are returned in the chat closeout, because this report cannot contain its own commit SHA. Track B remains 0cd2d506380cbb3ec513207e4fa66ad422d2b3f2.

## FINAL RECOMMENDATION

D. INSUFFICIENT_EVIDENCE_KEEP_R2_DS_BLOCKED

THE OBSERVED 1e-7 SCORE DIFFERENCE IS MOST CONSISTENT WITH:
Small deterministic upstream numerical variation between execution contexts, with shell thread settings a documented lead but not an established cause.

THE NEXT CHANGE, IF ANY, SHOULD BE:
Seek separate authorization for an isolated thread/backend A/B reproduction with immutable environment receipts; do not relax tolerance or resume generation.

That next change has NOT been implemented. R2 remains BLOCKED.
