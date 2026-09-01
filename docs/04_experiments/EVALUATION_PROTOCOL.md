# Evaluation Protocol

**Project:** Adversarial Attack Detection for Large Language Models (LLMs)
**Status:** EXPERIMENTAL

## Protocol objective

Define a reproducible evaluation process for detector disagreement, conditional verification, and adversarial prompt detection without assuming a final dataset constitution.

## Proposed sequence

1. Freeze candidate source and derived evidence manifests.
2. Normalize all samples into a common schema with provenance metadata.
3. Record detector outputs and model or rule versions.
4. Analyze agreement, disagreement, and false-agreement patterns.
5. Evaluate tradeoffs between detection quality, latency, and verification cost.
6. Report uncertainty and contamination risk explicitly.

## Constraints

- Final dataset roles remain outside current authorization.
- No result should be presented as final performance evidence without a stable, reviewed evidence base.
- All evaluation must be auditable and reproducible.

## Status note

This protocol is experimental. It creates a disciplined structure for future evaluation but does not imply approved results or benchmark selection.
