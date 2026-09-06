# Schema Change Proposal - Pilot 01

Status: `APPROVED_WITH_CONDITION` (`DEC-P3-008`)

| Current field | Problem | Proposed change | Affected datasets | Compatibility |
|---|---|---|---|---|
| `source.prompt` | A generated attack prompt and its upstream goal are distinct. Initial field priority could analyze `goal` while appearing to analyze the adversarial prompt. | Retain `source.base_behavior_text` and `source.adversarial_prompt` separately; define which is the active analytical text per artifact mapping. | GCG, JBB judge comparison, future AutoDAN outputs | Additive |
| `source.original_sample_id` | AdvBench provides no explicit ID. | Keep null; use reversible row locator and never call the internal `sample_id` a source ID. | AdvBench, AutoDAN input copy | No break |
| governance access fields | `train_allowed` alone cannot represent Commander controls. | Retain explicit training, evaluation, and forensic access states. | JBB, XSTest, selected HarmBench components | Additive |
| lineage status | Similarity and documentary lineage require separate confidence. | Store `relationship_type`, `evidence_strength`, and evidence references independently. | All Pilot 01 sources | Additive |

DECISION: these additive fields are Canonical Schema v0.2. Normalized taxonomy
fields remain `UNKNOWN` until a separate normalization rule is approved.
