# Pilot 01 Rights and Privacy Review

Project redistribution status: `DENIED_BY_GOVERNANCE`

| Source | Repository license | Dataset/content rights | Upstream rights | Status |
|---|---|---|---|---|
| AdvBench / llm-attacks | MIT | Dataset-specific scope not established separately | UNKNOWN | `UNKNOWN`, `upstream_rights_review` |
| AutoDAN | MIT | Generated-artifact terms not separately established | AdvBench rights UNKNOWN | `QUARANTINED`, `upstream_rights_review` |
| HarmBench | MIT | Repository includes behavior data, but incorporated/upstream rights were not fully resolved | TDC/AdvBench and other components PARTIAL | `QUARANTINED`, `upstream_rights_review` |
| JailbreakBench code | MIT | Code license verified | NOT_APPLICABLE | `CLEARED` for code handling only |
| JBB-Behaviors | Dataset card declares MIT | Constituent attribution is explicit | AdvBench and TDC/HarmBench PARTIAL | `CONDITIONAL`, `upstream_rights_review` |
| JBB artifacts | MIT names team and artifact authors | Model/behavior upstream terms remain relevant | PARTIAL | `CONDITIONAL` |
| XSTest | CC BY 4.0 | Repository dataset covered by license file; attribution required | NOT_APPLICABLE | `CONDITIONAL` |

Public availability was not treated as permission. No legal conclusion is made
about commercial use or redistribution beyond the recorded source evidence.

## Privacy Screening

MEASURED: a non-destructive regex screen of the 3,060 normalized prompt records
found zero email-address, URL, IPv4-address, or phone-number candidates. This is
not proof that the corpus contains no PII. Names, handles without explicit syntax,
and contextual identifiers require separate review. PII status remains
`REVIEW_REQUIRED` for wild/user-generated material; the current Pilot 01 behavior
sets show no obvious structured participant identifiers in analyzed prompt fields.
