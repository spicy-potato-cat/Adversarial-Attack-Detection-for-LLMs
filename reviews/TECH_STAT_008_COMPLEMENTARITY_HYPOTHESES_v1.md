# TECH-STAT-008 Complementarity Hypotheses

All four hypotheses are untested on new independent data. No detector changes or DATA-C2 work authorized by this report.

## H-C2-01 (MEDIUM)

**Observed Phenotype:** Long-benign errors have elevated extreme tails and prefix surprisal with sparse length-conditioned benign references, not simply persistent anomaly runs or greater fragmentation.

**Supporting Evidence:** 12/17 long benign rows are DS FPs across all five folds, compared with 5 unique same-source/length-region TN controls. All 17 use sparse pooled bins 3,2 (64-127 with 32-63). Paired max, q99, top5 mean, SD and prefix deltas are positive for all 12 cases. Median paired q99 delta=1.577906 nats; top5=0.920980; prefix=0.547301. FP/TN median q95 density=0.046427/0.030928; both isolated-anomaly medians=1.0. Evidence: long_benign_fp_analysis_v1.json and statistical_diagnostics_v1.csv.

**Supporting Samples:** 12

**Counter Evidence:** Only five unique TN controls, reused across comparisons, from one source. Pooling is an association, not a proven cause. B1 normalization and B2 robust summaries already exist; prior B3-B6 ablation did not justify replacing B2 on pooled performance. Suppressing extremes may miss real burst-like attacks. No independent gain has been demonstrated.

**Purely Statistical Mechanism:** Length-stratified benign surprisal distributions and robust body-versus-extreme-tail summaries need no semantic embedding, lexical attack rule or residual ID.

**General Representation Family:** Adequately supported length-conditional references, robust central/body versus isolated-tail evidence, and region-aware summary reliability. Proposed family only; no feature or model implementation now.

**Required New Data:** Independent long benign instructions, dialogue, natural formatting/code/log and repetition challenges, plus length/source-matched attacks and a broad population. At least 300 benign and 300 attack rows at 64+ reference tokens across multiple independent lawful sources before a later representation experiment.

**Falsifiable Prediction:** On new independent source/length-matched data, long-benign isolated-tail errors recur and a prospectively specified robust length/body-tail representation reduces long-benign FPs by at least 20% relatively, without more than a 2 percentage-point broad attack-recall loss under an independently specified operating protocol.

**Falsification:** The phenotype fails to recur across sources, FP reduction is below the declared target, or recall loss exceeds the declared bound. These are proposed future criteria, not thresholds selected or frozen here.

**Benign Fp Risk:** Potential benefit is lower long-benign FPs; source/length overcorrection may create errors in sparse strata and conceal attack bursts.

**Priority:** MEDIUM

**Gate Eligible:** True

**Not Residual Memorization:** True

**Evidence Strength:** Credible descriptive MEDIUM-priority benign-robustness hypothesis; small, reused controls and single-source limitations remain. Not a proven intervention.

## H-C2-02 (LOW)

**Observed Phenotype:** All 26 short attacks are DS misses; finite-tail resolution is demonstrated, but blanket robust-summary degeneracy is not.

**Supporting Evidence:** 26 under-16 attacks across five folds: DS catches 0, DMB 26, DG 7. Median scored tokens=10; top10% uses one token in 14 cases and two in 12. Median MAD=2.235518 and IQR=4.368787 are nondegenerate. Supplemental source/length matching yields 48 unique short benign controls: paired prefix delta median=1.123382 (18/26 positive); mean delta=0.576679 (15/26 positive); SD signs split 13/13. This cross-label comparison was declared after initial diagnostics because attack family is inapplicable to benign controls; it is exploratory.

**Supporting Samples:** 26

**Counter Evidence:** DMB already catches every short attack, so no observed residual recovery. Character/tokenization shifts are small and overlapping. Sampling variance was not empirically estimated. All attacks come from one source. Empty initial family-matched benign controls remain preserved.

**Purely Statistical Mechanism:** Finite-length reliability, fixed micro-window/region surprisals and character/tokenization ratios require no semantic model.

**General Representation Family:** Short-sequence estimator reliability and fixed prefix/body contrasts with explicit availability/effective-token resolution; no detector branch implemented.

**Required New Data:** At least 300 new short attacks and 300 source/genre/length-matched short benign controls across multiple sources, with enough independent DMB residuals to evaluate complementarity.

**Falsifiable Prediction:** On unseen short-input sources, statistical directions recur and a prospectively evaluated short representation improves recall by at least 5 percentage points without violating an independently specified benign-FPR constraint.

**Falsification:** Matched distributions overlap without reproducible gains, directions reverse across sources, or gains only duplicate DMB catches and increase benign FPs.

**Benign Fp Risk:** Short benign commands share prefix surprisal and sparse-tail behavior; reacting to one surprising token can raise benign FPs.

**Priority:** LOW

**Gate Eligible:** False

**Not Residual Memorization:** True

**Evidence Strength:** Weak exploratory signal: SHORT_BRANCH_WEAKLY_SUPPORTED, not justified for implementation.

## H-C2-03 (LOW)

**Observed Phenotype:** The one DS-recovered DMB residual has a less isolated anomalous run, but four cases do not establish a general recovery mechanism.

**Supporting Evidence:** Recovered case: 41 DS tokens; q95 density=.125; longest-run fraction=.075; isolated fraction=.4; DS score=.864277, a near-boundary catch. Shared misses have 17,17,23 tokens, densities=0,.125,0 and isolated fractions=0,1,0. All four have exact A/B/C matched attack controls and no DMB truncation.

**Supporting Samples:** 4

**Counter Evidence:** Recovered case is longer; a shared miss has the same density and a larger max-minus-median. Shared DMB misses are two far and one near the frozen 3% point; recovered case is also near. Prior B4/B5 existed without justified pooled promotion. One-versus-three cannot define a phenotype or success criterion.

**Purely Statistical Mechanism:** Fixed run-length, isolated-versus-contiguous surprisal and region summaries describe numerical persistence without interpreting semantics.

**General Representation Family:** Fixed length-adjusted anomaly persistence and regional concentration, investigated only on independent prospectively identified residuals.

**Required New Data:** 30-50+ independent DMB residual attacks from a broader prospectively screened population, with matched DMB TPs and benign burst/formatting controls. None of the four current cases may enter C2 training, weighting or success criteria.

**Falsifiable Prediction:** Independent residuals show reproducible source-stable differences in persistence between statistically recoverable attacks and matched benign controls.

**Falsification:** Distributions overlap benign controls, fail to recur across sources, or only reproduce the single original recovered case.

**Benign Fp Risk:** Long benign text and rare-token bursts can also produce contiguous anomalies; source/length-matched benign challenges are essential.

**Priority:** LOW

**Gate Eligible:** False

**Not Residual Memorization:** True

**Evidence Strength:** INSUFFICIENT_SAMPLE_SIZE. Hypothesis generation only, not authorization to optimize against four residuals.

## H-C2-04 (LOW)

**Observed Phenotype:** Most DS misses are not merely adjacent to the point; error structure is length/source bounded and some longer misses have benign-like central tendency.

**Supporting Evidence:** DS FNs: 26 under-16, 41 at 16-31, 10 at 32-63 and 6 at 64-127, all deepset. 62/83 are far-from-boundary DS misses. DMB catches 80/83, DG 22/83. All three common FNs are 16-31. Six longer FNs have median NLL=3.509340 and length-bin NLL percentile=.104575.

**Supporting Samples:** 83

**Counter Evidence:** Length strata are not stable latent clusters; attacks are single-source and binary-error selected. Low-surprisal attacks may be statistically indistinguishable from benign text. DMB already handles most DS misses.

**Purely Statistical Mechanism:** Source/length stability checks on distributions, body/tail contrasts and shape test numerical evidence without semantic labels or source-specific rules.

**General Representation Family:** Source-invariant length-matched distribution/body-tail representations, including explicit negative conclusions when statistical separation is absent.

**Required New Data:** Broad attacks and benign prompts from independent sources and lengths, not a hard-mined current-FN bank; retain lineage uncertainty and matched DMB residual/TP strata.

**Falsifiable Prediction:** Low-central-surprisal attack strata exhibit reproducible shape or regional separation from matched benign rows on unseen sources beyond a length-only explanation.

**Falsification:** Differences vanish or reverse after source/length/genre matching, or improved standalone DS discrimination fails to recover new DMB residuals without more benign FPs.

**Benign Fp Risk:** Forcing detection of statistically benign-like attacks can substantially increase benign FPs.

**Priority:** LOW

**Gate Eligible:** False

**Not Residual Memorization:** True

**Evidence Strength:** Descriptive broad DS failure structure; weak evidence for another complementary mechanism.

## Hard gate

```json
{
  "recommendation": "AUTHORIZE_DATA_C2_001_WITH_LIMITED_HYPOTHESES",
  "eligible_hypotheses": [
    "H-C2-01"
  ],
  "DATA_C2_started": false,
  "cycle2_consumed": false,
  "rationale": "Limited independent-data testing requirements only for evidence-backed statistical hypotheses; Commander approval still required.",
  "required_DMB_residual_denominator": "30-50+ independent attacks; prospectively report total screened and residual denominator without selection-driven headline metrics",
  "lineage_constraints": "New independent sources/base behaviours; no overlap with current fixture, four diagnostic residuals, calibration/validation or protected data; retain transformation/family/source groups",
  "data_requirements_only": true
}
```

## Proposed C2 tests and requirements, not a dataset plan

Requirements only, not a dataset build or partition plan. Broad population: approximately 1,500-3,000 independent attacks and a comparable benign population across multiple lawful, non-protected sources, styles and lengths; exact totals require Commander review. Challenges: at least 300 long benign and 300 length-matched long attacks; optional short challenges only after separate approval. Benign categories: ordinary requests, hard-benign risky-but-non-injection instructions, dialogue, natural formatting/code/log-like material and repetition. Do not relabel harmful intent as injection. Attack families remain within the approved text taxonomy. Desire 30-50+ independent DMB residual attacks, prospectively retaining total screened and broad-population denominators so residual enrichment cannot masquerade as population performance. Exclude current fixture/diagnostic IDs, four residual cases, calibration/validation and pristine/protected candidates; prohibit duplicate, near-duplicate and base-behaviour lineage crossing and record unresolved semantic lineage. Resolve rights/privacy before any acquisition. No source was acquired and no C2_TRAIN/C2_DEV/C2_HOLDOUT was created. Only H-C2-01 is gate-eligible at MEDIUM priority; other hypotheses do not authorize scope expansion.
