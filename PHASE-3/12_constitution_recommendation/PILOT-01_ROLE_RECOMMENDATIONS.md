# Pilot 01 Experimental-Role Recommendations

These are recommendations only. Final constitution status: `NOT_APPROVED`.

| Dataset | Recommendation | Basis | Required review |
|---|---|---|---|
| AdvBench | `QUARANTINE`; possible future development candidate | Complete reuse in AutoDAN input and HarmBench AdvBench subset; dataset-specific rights unresolved | Rights and contamination-aware split policy |
| GCG generated artifact | `ADAPTIVE_STRESS_TEST` candidate, evaluation-only during early development | Generated adversarial prompts preserve explicit base behaviors; not independent of JBB behaviors | Upstream rights and artifact-selection policy |
| AutoDAN | `QUARANTINE` pending generated-output acquisition/provenance | Local material contains method code, seed, and AdvBench input but no qualified generated output set | Identity of intended generated artifact |
| HarmBench | `PRISTINE_EXTERNAL_BENCHMARK` candidate for selected contamination-controlled components | Benchmark framework with explicit AdvBench/TDC components | Component-level lineage and rights |
| JailbreakBench | `PRISTINE_EXTERNAL_BENCHMARK` candidate | Explicit aggregate provenance and strong dependencies on Pilot sources | Prevent development feedback; component-aware reporting |
| XSTest | `HARD_BENIGN_FPR_BENCHMARK` and pristine candidate | 250 safe plus 200 unsafe contrast prompts; 100 safe prompts reused by JBB judge comparison | Preserve benchmark audit controls |

No training, validation, test, or calibration assignment is approved by this file.
