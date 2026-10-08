# EXP-PROTOCOL-001-PATCH-001 Review

The parent evaluator selects every target/transfer metric prefix while its R2
bootstrap configuration declares one target. The unchanged validator correctly
rejects this with TARGET_METRIC_DOMAIN_CONFLICT. This is a pre-generation protocol
defect, not an experimental outcome: authoritative R2 queries and outcomes are zero.

The prospective evaluator uses an explicit MetricDomains contract. R2 requires
exactly one common declared target across all rows; its attack-target and target
uncertainty domains are that singleton. Transfer and common-mode domains remain
D_S, D_M-B, D_G. Transfer metric prefixes are indexed by the originating target,
not their destination detector. Extra targets and mismatched uncertainty domains
are rejected. R3 continues to require ALL with the full-stack attack domain.

Before: all three target prefixes sent to one target-specific uncertainty config.
After: only the declared target's target/transfer prefixes sent to that config.
All-stack attack/common-mode and benign metric selection is unchanged.

No formulas, bootstrap code/defaults, metric catalog, policy, models, calibrators,
thresholds, preprocessing, seeds, operators, query budget or success definitions
change. The new evaluator calls the same frozen functions. The old lock, evaluator,
release inventory, R0/R1 outputs, original R2 predeclaration, and historical blocker
remain byte-identical and available for reproduction. No outcome-informed choice
was possible; no generated attacks existed at correction time.

The additive patch inventory binds 252 original preservation files, both original
R2 artifacts, new code/tests and this review. Original inventories are not rewritten.
Acceptance requires current reruns of the 96 baseline checks, 118 release checks,
all existing protocol/R0/R1/R2 preflight tests and new domain tests, with zero
failures/errors/skips. Actual receipts and commit IDs are recorded separately after
testing; this review does not claim a pending test has already passed.

R2 must bind this patch through a separate predeclaration addendum and a pre-query
receipt before resumption. No experiment, model inference or R3 is run by this patch.

The initial correction commit's post-commit gate rejected historical model
environment metadata whose accepted local serialization differs from its Git
serialization. Its original SHA-256 was unchanged. The follow-up gate correction
preserves that existing local-byte hash authority and additionally Git-anchors
only new patch files and the patch manifest, to the manifest's latest committed
revision. This is provenance validation only, before any R2 query. Original
acceptances v1/v2 and Git history remain available; acceptance v3 binds the final
gate and self-protected root attributes. Scoped attributes preserve new hash-bound
files across Windows checkouts, including the attribute files themselves.
