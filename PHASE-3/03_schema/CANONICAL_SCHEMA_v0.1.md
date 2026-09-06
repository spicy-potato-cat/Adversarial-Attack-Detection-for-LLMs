# Canonical Schema v0.1 - Pilot 01 Validation

Status: `WORKABLE_WITH_CHANGE_PROPOSAL`

The analytical record preserves the source record and stores derived values in
separate namespaces. A record is traceable through `source.dataset_id`,
`source.artifact_id`, `source.artifact_sha256`, and `source.record_locator`.

## Source-Preserved Fields

- `source.dataset_id`, `source.dataset_name`, `source.artifact_id`, `source.version`
- `source.artifact_sha256`, `source.record_locator`, `source.original_sample_id`
- `source.prompt`, `source.response`, `source.raw_text`, `source.raw_response`
- `source.label`, `source.original_label`, `source.original_category`
- `source.original_metadata`, `source.original_record`
- `source.base_behavior_text`, `source.adversarial_prompt`

Null means the source does not supply the field. `UNKNOWN` is used for a claim
whose value cannot be established. Neither state is converted into an inferred label.

## Derived Fields

- `forensics.raw_text_sha256`, `forensics.N1_sha256`, `forensics.N2_sha256`
- `forensics.canonicalization_ids`, `forensics.canonical_hash`
- `forensics.duplicate_cluster_id`
- `derived.N1`, `derived.N2`
- `labels.normalized_binary_label`, `labels.normalized_attack_family`
- `labels.normalized_attack_subtype`
- `generation.generator`, `generation.generation_method`
- `lineage.base_behavior_id`, `lineage.upstream_dataset`, `lineage.upstream_sample_id`
- `rights.license_status`, `rights.provenance_status`, `rights.PII_status`
- `governance.experimental_role`, `governance.train_allowed`
- `governance.evaluation_only`, `governance.training_access`
- `governance.forensic_analysis_access`, `governance.quarantine_reason`

## Canonicalization

- `CANON-N0-v0.1`: source-faithful decoded text.
- `CANON-N1-v0.1`: Unicode NFC plus CRLF/CR to LF normalization.
- `CANON-N2-v0.1`: N1 plus Unicode-aware whitespace-run collapse and trim.

N2 is comparison-only. Case, punctuation, homoglyphs, zero-width characters,
and other potentially adversarial features are preserved.

## Pilot Mapping

| Artifact | Analyzed prompt field | Base behavior | Source ID |
|---|---|---|---|
| AdvBench | `goal` | `goal` | unavailable |
| AutoDAN AdvBench input | `goal` | `goal` | unavailable |
| HarmBench behavior files | `Behavior` | `Behavior` | `BehaviorID` |
| JBB harmful/benign | `Goal` | `Goal` | `Index` |
| JBB judge comparison | `prompt` | `goal` | `Index` |
| JBB GCG artifact | `prompt` | `goal`/`behavior` | `index` |
| XSTest | `prompt` | `prompt` | `id` |

## Validation Result

MEASURED: 3,060 analytical records were produced from ten record-bearing
artifacts. The AutoDAN seed text was preserved but is not treated as a dataset row.
All record locators are deterministic and reversible under the tests.
