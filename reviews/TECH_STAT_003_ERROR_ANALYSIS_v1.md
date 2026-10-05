# TECH-STAT-003 Statistical Error Analysis v1

Status: **PASS - descriptive development analysis only**

Client date: 2026-10-04 (Asia/Calcutta)

All counts refer to the fixed raw-probability 0.5 comparison rule, not the
deployed calibrated v1 vote. Positives/negatives are inherited manifest labels;
no semantic relabeling, attack success adjudication, or manually inferred attack
categories were performed.

## False Negatives: 60

- **51/60 (85%) have fewer than 32 input tokens**, versus 34/123 (27.64%) TP.
  Short-positive FNR is 51/85 = 60%; for other positives, 9/98 = 9.18%.
- **40/60 (66.67%) have max surprisal at/below the positive-class q25**, versus
  6/123 (4.88%) TP. Median max surprisal: FN 10.7199, TP 13.8264.
- All FN have one window and zero window-PPL standard deviation. However,
  105/123 TP also have zero window variation; this is primarily representation /
  coverage evidence, not proof of a causal FN mechanism.
- Low whole-PPL/mean-surprisal is **not enriched**: 15/60 FN (25%) versus
  31/123 TP (25.20%). Median PPL: FN 169.000, TP 165.320. Do not describe low
  average surprise as the dominant failure explanation.
- FN maximum input length is 69 tokens. No FN is long or truncated. No retained
  anomaly-position evidence supports a tail-anomaly explanation.

These statistical associations do not imply that the positive prompts are
semantically fluent, successful attacks, or any particular attack mechanism.

## False Positives: 203

- High max surprisal (at/above negative q90): **52/203 (25.62%) FP**, versus
  44/749 (5.87%) TN. Median maximum: FP 12.9857, TN 10.6938.
- Aggregate-spike proxy (high max, relatively low mean): **50/203 (24.63%) FP**,
  versus 18/749 (2.40%) TN. This proxy does not locate a spike or establish a run.
- High whole-PPL: 66/203 FP (32.51%), versus 172/749 TN (22.96%). This is modest
  enrichment, not a universal FP explanation. Median PPL: FP 216.252, TN 156.706.
- High surprisal variation is **not enriched**: 45/203 FP (22.17%), versus
  193/749 TN (25.77%). Do not claim high variance is the dominant FP driver.
- 158/203 FP (77.83%) are short, but 734/749 TN (98.00%) are short too. Counts
  alone do not imply short negatives are riskier. The 32-127-token negative
  subgroup has 45/60 FP (75%), versus 158/892 FP (17.71%) below 32 tokens;
  small, source-confounded strata limit interpretation.

## Important Degenerate-Quantile Caveat

Negative-class q75 of window-PPL standard deviation is **zero**. The frozen
`>=q75` diagnostic consequently matches every FP **and every TN**. Its name
`high_window_variation` must not be read literally as high variance or enrichment.

All 263 errors, and all 952 negatives, have one window. Their window std is zero;
whole/global/mean-window/max-window PPL coincide. Together with the NLL/mean-
surprisal alias, the 10-column representation contains substantial redundancy
in this cohort. Nothing was dropped or transformed in the scorer.

The pipeline's original support-count ranking was retained unchanged. A separate
`ds_v1_diagnostic_caveats_v1.json` qualifies these degenerate rules rather than
rewriting predictions, refitting, or presenting zero variance as high variance.
No new model features or token diagnostics were calculated.

## Source And Length Diagnostics

| Source | Rows | Negative | Positive | FP | FN | FPR |
|---|---:|---:|---:|---:|---:|---:|
| Do-Not-Answer | 659 | 659 | 0 | 104 | 0 | 15.78% |
| deepset Prompt Injection | 476 | 293 | 183 | 99 | 60 | 33.79% |

Every positive is from deepset. Source and label composition are confounded;
this is not evidence of general distribution shift. DNA FNR/recall is undefined,
not zero, because it contains no positives under the approved mapping.

| Input Tokens | Rows | Positive | Negative | FN | FP |
|---|---:|---:|---:|---:|---:|
| 2-31 | 977 | 85 | 892 | 51 | 158 |
| 32-127 | 140 | 80 | 60 | 9 | 45 |
| 128-511 | 18 | 18 | 0 | 0 | 0 |
| >=512 | 0 | 0 | 0 | 0 | 0 |

The maximum length is 433 tokens. No truncation occurred. Longer cohort rows are
positive-only; apparent perfect recall in that stratum is not a general length
advantage. Long-prompt dilution, prefix/middle/tail effects, and anomaly runs
cannot be assessed from this cohort's retained evidence.

## Ranked Development Hypotheses For TECH-STAT-004

The rank is a deterministic **coverage count**, not feature importance or measured
candidate benefit. Counts overlap; no feature utility or promotion is established.

1. **Window representation/robustness (263 matching error IDs).** The dominant
   observation is one-window degeneracy, not high variation. Merely adding
   median-window PPL, variance, or max/median ratio cannot help a single-window
   representation: those would remain redundant/zero. Any later authorized
   window design must address that limitation before testing these aggregates.
   Existing max-window PPL is already present, not a missing feature.
2. **Length-aware statistical normalization (209 IDs).** Strong short-positive FN
   concentration and differing negative-length error rates justify controlled
   length-conditioned statistical hypotheses. Source confounding and subgroup
   denominators must be monitored; metadata is not a scorer feature here.
3. **Robust distribution shape (138 IDs).** Low-max FN enrichment and elevated
   extrema in some FP motivate testing token-surprisal quantiles, median, MAD,
   IQR, skewness/kurtosis rather than redundant averages. Within-prompt shape
   was not measured; improvement remains unproven.
4. **Multiple exceedance ratios (92 IDs).** v1 uses only the existing threshold 8
   ratio. Contrasting low-max FN with high-max FP motivates testing alternative
   statistical distribution summaries later. No FN has zero threshold-8
   exceedance, so lack of any exceedance is not supported as a failure mechanism.
5. **Anomaly run descriptors (80 IDs, indirect support).** FP aggregate-spike/max
   associations motivate longest-run/run-count hypotheses; current extrema cannot
   distinguish isolated from sustained anomalies. No runs were computed.
6. **Regional/position descriptors (0 direct supporting IDs).** Prefix/middle/tail,
   tail-minus-prefix and anomaly-position features are information gaps only.
   No long/tail-error claim is justified; lower priority without new evidence.

No feature family was implemented, no scorer was compared, and no ds_v2 was
created. This reproduction is not a substantive candidate-improvement cycle.
The two-cycle cap and complementarity requirement remain in force.

## Recommendation

**READY FOR TECH-STAT-004 FEATURE ENGINEERING.** Prioritize the observed short-
input/maximum-surprise and representation-degeneracy issues as hypotheses,
not proven solutions. Do not create D_S v2, tune a policy on OOF labels, use
reserved/protected partitions, or start verifier/routing work in this phase.
