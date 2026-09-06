# Canonical Schema v0.2

Status: `APPROVED_WITH_CONDITION` under `DEC-P3-008`.

Schema v0.2 retains the v0.1 source, forensic, rights, lineage, and governance
namespaces and makes base behavior and adversarial prompt semantics explicit.
Normalized taxonomy fields remain `UNKNOWN` without a separately approved rule.

For scale-controlled Wave 2 outputs, `source.original_record` may be an immutable
artifact-hash plus row-locator reference. Source text, response, supplied label,
category, and non-text metadata remain directly represented. N1/N2 text is stored
only when it differs from the preceding view; all three view hashes are mandatory.

Required namespaces:

- `source`: dataset/artifact identity, revision, hash, locator, source ID,
  original-record reference, raw text/response, source label/category/metadata,
  base behavior, and adversarial prompt.
- `labels`: normalized binary, family, and subtype fields, conditionally `UNKNOWN`.
- `generation`: source-supported method/generator or `UNKNOWN`.
- `lineage`: upstream dataset/sample and evidence state.
- `forensics`: N0/N1/N2 hashes, canonicalization IDs, duplicate cluster ID.
- `rights`: license, provenance, and PII states.
- `governance`: forensic access, training permission, evaluation-only state,
  quarantine reasons, and provisional role.

Original fields and normalized claims are never overwritten or conflated.
