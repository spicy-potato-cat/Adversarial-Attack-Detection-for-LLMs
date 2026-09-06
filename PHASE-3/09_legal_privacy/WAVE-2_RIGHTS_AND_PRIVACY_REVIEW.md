# Wave 2 Rights and Privacy Review

Status: `REVIEW_REQUIRED` under `DEC-P3-010`.

| Dataset | Rights evidence | Promotion status |
|---|---|---|
| WildJailbreak | Card says ODC-BY; access is conditioned on AI2 Responsible Use Guidelines; upstream content rights unresolved | `CONDITIONAL`; blocked from finalized role |
| WildGuardMix | Card says ODC-BY with the same gated terms; in-the-wild/upstream component rights unresolved | `CONDITIONAL`; blocked from finalized role |
| SALAD example | Repository is Apache-2.0, but that does not establish rights for separate Salad-Data or upstream questions | `UNKNOWN`; `QUARANTINE` for promotion |
| Do-Not-Answer | README assigns datasets CC BY-NC-SA 4.0 and code Apache-2.0 | `CONDITIONAL`; noncommercial/share-alike constraints apply |
| deepset Prompt Injection | Card simultaneously declares CC BY 4.0 and Apache-2.0 without scope explanation | `UNKNOWN`; `QUARANTINE` for promotion |

The lightweight regex screen covered valid active text and responses. Candidate
record counts were: WildJailbreak 553 email, 2,429 URL, 9 IPv4, 2,461 phone;
WildGuardMix 216 email, 680 URL, 38 IPv4, 742 phone; SALAD example 1 email and
2 phone; Do-Not-Answer and deepset produced zero pattern candidates. The 939
Do-Not-Answer records contain source identifier fields.

These are candidates, not confirmed PII. Safety examples can resemble phone
numbers, addresses, or URLs, and regex has false negatives. Every dataset remains
`PII_STATUS = REVIEW_REQUIRED`; contextual/user-generated-content review is unresolved.

