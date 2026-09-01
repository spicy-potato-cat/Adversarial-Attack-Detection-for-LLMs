# Provenance and Lineage

**Project:** Adversarial Attack Detection for Large Language Models (LLMs)
**Status:** UNDER INVESTIGATION

## Objective

Establish whether benchmark families, attack collections, and safety datasets are independent, related, or derived from one another. This is required before any final claim on dataset constitution or evaluation fairness.

## Key lineage questions

- Does a dataset originate from a benchmark’s canonical source or from a derivative generated artifact?
- Are multiple entries the same corpus under different packaging or labels?
- Does an attack benchmark share prompts or templates with a distinct safety benchmark?
- Are generated artifacts from known attack methods (for example GCG or AutoDAN) merged with benchmark prompts without clear traceability?

## Repository evidence

The Phase-3 readiness plan identifies known candidates with unresolved provenance status, including AdvBench, HarmBench, JailbreakBench, and XSTest, as well as attack-material families and multimodal datasets with uncertain lineage. These unresolved relations make lineage review mandatory before any final evaluation structure is defined.

## Status note

Provenance and lineage analysis is active and under investigation. No final lineage conclusions are assumed.
