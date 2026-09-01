# Data Model

**Project:** Adversarial Attack Detection for Large Language Models (LLMs)
**Status:** PROPOSAL / UNDER INVESTIGATION

## Core entities

- `TextSample`: normalized text instance with source and provenance metadata
- `DetectorResult`: prediction, confidence, version, and execution metadata
- `AgreementSummary`: pairwise or aggregate disagreement metrics
- `RiskContext`: false-agreement signal, uncertainty, and escalation recommendation
- `EvidenceRecord`: provenance, raw hash, and lineage references

## Relationship principles

- Each text sample must retain its provenance.
- Each detector result must be tied to a specific detector version.
- Consensus analysis must not overwrite provenance or evidence metadata.
- Derived analysis must remain separable from raw immutable artifacts.

## Status note

This data model is intended for architecture and audit support. It is not a finalized application schema.
