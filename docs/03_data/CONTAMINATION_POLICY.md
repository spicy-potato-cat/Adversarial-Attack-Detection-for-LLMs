# Contamination Policy

**Project:** Adversarial Attack Detection for Large Language Models (LLMs)
**Status:** UNDER INVESTIGATION

## Policy objective

Prevent benchmark contamination and leakage from distorting conclusions. This is especially important because public benchmark families and derived attack collections frequently overlap in prompt wording, exploitation patterns, or upstream sources.

## Policy principles

- Treat benchmark self-overlap as a first-class analysis problem.
- Record exact, lexical, semantic, and lineage overlap separately.
- Do not assign final experimental status to a dataset without contamination review.
- Distinguish between candidate benchmark panels and approved evaluation roles.

## Current repository evidence

The dataset portfolio includes multiple likely related benchmark clusters, such as AdvBench, HarmBench, JailbreakBench, and XSTest, as well as derived attack-artifact families like GCG and AutoDAN-related material. These relationships are a direct reason to keep contamination policy strict.

## Status

This policy is active and conservative. It is a research governance rule, not a final approval of any dataset or benchmark for training or evaluation.
