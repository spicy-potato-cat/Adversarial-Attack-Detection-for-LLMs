# Pilot 01 Git Artifact Classification

## Recommended for Git

- `PHASE-3/00_governance/`
- Small manifests and inventory summaries, excluding local absolute-path concerns
- `PHASE-3/02_registry/`, schema specifications, configs, scripts, and tests
- Quality, exact-overlap, near-overlap, lineage, rights/privacy, and report artifacts
- Compact logs with no exposed sensitive prompt content

## Do Not Track in Git

- `Dataset/Raw/` and `PHASE-3/01_acquisition/raw/`
- Large archives, images, model weights, embedding matrices, and future ANN indexes
- `.git/`, Git LFS temporary data, caches, virtual environments, and `__pycache__/`
- `PHASE-3/03_schema/PILOT-01_normalized_records.jsonl` if repository distribution
  could expose restricted or harmful source content

## Review Before Git

- `PHASE-3/01_acquisition/hashes/local_bundle_inventory.csv` (large and contains
  machine-local paths/structure)
- Pair-level overlap files that include record references
- Acquisition audit logs containing source URLs or local paths
- Any report containing prompt excerpts or potential PII

No `.gitignore` change or Git initialization was performed by Pilot 01.
