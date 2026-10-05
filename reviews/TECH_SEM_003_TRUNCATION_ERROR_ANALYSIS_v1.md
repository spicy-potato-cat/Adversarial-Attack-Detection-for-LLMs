# TECH-SEM-003 Truncation And Error Analysis v1

Status: **PARTIAL - ANALYSIS IMPLEMENTED; REAL OOF RESULTS PENDING**.
No authoritative BASE_TRAIN model scores are presented as out-of-fold evidence.

The continuation's committed pre-run package and renewed evidence are documented
in `TECH_SEM_003_OOF_PRERUN_EVIDENCE_v1.md`. No actual performance or B1/B2/B3
recommendation has been substituted with synthetic test values.

## Token Coverage

For each held-out sample, retain ID, source/revision, fold, label, canonical lineage
group, full input token count, baseline max 256, analyzed tokens (attention-mask
sum), excluded tokens, truncation flag, positive probability, class-one-minus-class-
zero logit margin, prediction, error type, probability distance to .5 and confidence
category. Counts include special tokens and exclude batch padding. Truncation is
right-sided exactly as frozen v1. Input count is obtained without truncation;
analyzed count must equal min(input count, 256). No prompt text or payload location
is exported. Payload position is NOT_AVAILABLE_NOT_INFERRED.

The real synthetic smoke verifies non-truncated 6-token and truncated 1,504-token
cases, with exactly 256 analyzed and 1,248 excluded in the latter. These are
engineering checks, not project-data truncation statistics. GPT-2 coverage from
TECH-STAT-003 is not reused as RoBERTa coverage evidence.

## Truncation Analysis

Pending full OOF, the pipeline will report:

- Positive truncated count/fraction; FN counts with and without truncation.
- FNR = FN/(FN+TP) among POSITIVES within each coverage group.
- FPR = FP/(FP+TN) among NEGATIVES within each coverage group.
- Separately named joint FN incidence across all rows in the group, avoiding
  ambiguity between P(FN|truncated) and class-conditional FNR.
- Positive score distributions and token/exclusion distributions by coverage.
- Null rates/intervals for empty denominators, not fabricated zero error rates.
- Descriptive 95% Wilson intervals, explicitly ignoring shared-training and lineage
  dependence, not guarantees of population generalization or model-refit uncertainty.

Truncation-associated failures do NOT establish truncation causality. No 512-token
forward comparison is implemented: it is optional and skipped to keep this phase
focused on the frozen baseline. Neither training nor baseline scoring changes length.

## Confidence And Concentration

Predeclared, diagnostic-only confidence bins:

- Borderline wrong: absolute distance from raw cutpoint .5 <= .1.
- High-confidence wrong FN: raw attack probability <= .1.
- High-confidence wrong FP: raw attack probability >= .9.
- Other wrong: remaining errors. These bins do not change predictions or weights.

FN/FP counts, score/margin/distance distributions, and these confidence counts are
pending. Softmax probabilities are uncalibrated; confidently wrong does not prove
epistemic certainty or a particular semantic representation defect.

Source and fold groups retain class denominators and confusion counts/rates.
Input length bins: 2-31, 32-127, 128-256, 257-512 and 513+ tokens, inclusive ranges.
Fold metrics include mean/population standard deviation/min/max. Source label
composition is confounded: all positive fixture rows are deepset; Do-Not-Answer
contributes approved hard benigns. No general R1 distribution-shift claim is made.

## Failure Hypotheses And Hard IDs

Implemented markers quantify truncation association, low-margin errors,
high-confidence wrong errors (semantic hypothesis NOT verified), and short/long
input associations, with supporting IDs, FN/FP counts and subgroup denominators.
These markers overlap. An explicit unresolved marker records non-truncated,
non-borderline, non-high-confidence errors. ALL semantic root causes remain
unresolved without independent mechanism evidence, even for confidently wrong rows.
Source/fold concentration is descriptive, not a forced per-sample causal category.

Hard-example CSV will contain ID-only metadata for FN/FP rows and their confidence
category. The confidently wrong subset is identifiable without copying text.
Exactly one OOF prediction occurs per sample: repeated misses are NOT measurable.
These lists are diagnostic references, not new training data or an approved
hard-example sampling/loss policy. No IDs are manufactured before execution.

## B1 / B2 / B3

Current recommendation: **WITHHOLD UNTIL OOF RESULTS**.
B1 (same recipe, 256->512) is flagged for a controlled future experiment only if
OOF FNs actually have excluded tokens; sparse support and intervals still require
Commander review. Absence of truncated FNs yields no B1 support from this audit.
Association alone cannot predict improvement. B2 stays deferred until B1 evidence
or separate review; B3 remains deferred and is not justified merely by high scores.
No experiment, architecture change, max-length change, promotion or v2 training
occurs here. Full results and recommendations will be in the semantic OOF JSONs.
