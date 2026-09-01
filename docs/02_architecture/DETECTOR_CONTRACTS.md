# Detector Contracts

**Project:** Adversarial Attack Detection for Large Language Models (LLMs)
**Status:** PROPOSAL / UNDER INVESTIGATION

## Purpose

Define a common operating contract for heterogeneous detectors so that outputs can be compared, aggregated, and audited.

## Required output fields

Each detector should, at minimum, provide:

- input identifier
- detector identifier
- model or rule version
- prediction label
- confidence score
- abstention status if applicable
- timestamp or reproducible execution evidence
- provenance metadata for the model, rule, or dataset version

## Optional output fields

- explanation or rationale
- feature-level signal summary
- risk band or severity estimate
- verification recommendation

## Contract constraints

- The detector output must remain traceable to a specific version or rule set.
- Uncertainty must be explicit rather than implicit.
- The contract must allow both deterministic and probabilistic outputs.
- The contract must support downstream disagreement analysis rather than only a final binary label.

## Status note

The detector contract is a design artifact for research architecture work. It is not treated as a finalized production system contract.
