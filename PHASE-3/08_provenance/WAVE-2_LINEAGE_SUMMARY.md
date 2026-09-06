# Wave 2 Provenance and Lineage Summary

Status: `MEASURED_WITH_DOCUMENTARY_LIMITS`

| Source / relation | Relationship type | Evidence | State |
|---|---|---|---|
| WildJailbreak | Derived generation | Local card documents GPT-4 vanilla generation, GPT-3.5 responses, and WildTeaming transformations using Mixtral-8x7B/GPT-4 | `VERIFIED` dataset-level; row-level generator `UNKNOWN` |
| WildJailbreak -> XSTest | Conceptual motivation | Local card says XSTest motivated benign contrast categories | `VERIFIED`; not evidence of sample reuse |
| WildGuardMix | Aggregate composition | Local card reports 87% synthetic, 11% in-the-wild interactions, 2% annotator-written | `VERIFIED` percentages; component identities `UNKNOWN` |
| WildJailbreak <-> WildGuardMix | Exact text and base-behavior reuse | 18,903 shared N1 text hashes; 10,229 shared N1 base-behavior hashes | `STRONGLY_SUPPORTED`; direction/direct inclusion `UNKNOWN` |
| SALAD example <-> HarmBench / AdvBench / AutoDAN input | Exact base-question reuse | 11 shared N1 hashes with each Pilot source | `STRONGLY_SUPPORTED`; applies only to the 127-row example |
| SALAD example <-> Do-Not-Answer | Exact text reuse | 9 shared N1 hashes | `MEASURED`; documentary direction `UNKNOWN` |
| SALAD example <-> WildGuardMix | Exact text reuse | 8 shared N1 hashes | `MEASURED`; documentary direction `UNKNOWN` |
| Do-Not-Answer | Curated risky-question benchmark | Local README and selected instruction schema | `VERIFIED` dataset purpose; question-level provenance `UNKNOWN` |
| deepset Prompt Injection | Binary text classification corpus | Local card/schema provides only `text` and integer `label` | `PARTIAL`; label semantics, construction, direct/indirect distinction, and upstream lineage `UNKNOWN` |

Similarity is not treated as proof of lineage. Machine-readable exact, lexical,
and behavior-level measurements are kept separately in their numbered directories.

