# Ablation Plan

**Project:** Adversarial Attack Detection for Large Language Models (LLMs)
**Status:** EXPERIMENTAL

## Goal

Identify which design factors matter most for disagreement-aware adversarial detection and conditional verification performance.

## Proposed ablations

- single-detector baseline vs. heterogeneous detector stack
- agreement-only routing vs. disagreement-aware routing
- threshold variation under different false-positive priorities
- inclusion vs. exclusion of false-agreement risk signals
- verification escalation with fixed vs. adaptive budgets
- contamination-sensitive vs. contamination-controlled evaluation subsets

## Reporting requirement

Ablation results must be accompanied by provenance and overlap information. A single favorable ablation does not imply a generalizable conclusion if the evidence base is unstable.

## Status

This is an experimental ablation plan. It is intended to structure research questions rather than claim validated improvements.
