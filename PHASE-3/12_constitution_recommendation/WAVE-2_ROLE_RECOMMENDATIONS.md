# Wave 2 Provisional Role Recommendations

Status: `PROVISIONAL`; final dataset constitution is `NOT APPROVED`.

| Dataset | Recommendation | Conditions |
|---|---|---|
| DS-TXT-001 WildJailbreak | `TRAINING_CANDIDATE` | Resolve immutable revision, terms/upstream rights, PII, and deduplicate/group against WildGuardMix and benchmark matches |
| DS-TXT-002 WildGuardMix | `TRAINING_CANDIDATE` | Treat as an aggregate, not an independent source; resolve component lineage and choose deliberately between it and overlapping WildJailbreak material |
| DS-TXT-016 SALAD | `QUARANTINE` | Only a 127-row example is local, full Salad-Data is `MISSING`, rights are unresolved, and Pilot benchmark overlap prevents pristine treatment |
| DS-TXT-017 Do-Not-Answer | `INTERNAL_TEST_CANDIDATE` | Use as risky-question/refusal evidence, not as inherently adversarial prompts; respect CC BY-NC-SA and resolve privacy/provenance |
| DS-TXT-018 deepset Prompt Injection | `TRAINING_CANDIDATE` | First resolve label semantics, license conflict, construction provenance, and direct/indirect structure |

No split, promotion, threshold, or final role assignment was made.

