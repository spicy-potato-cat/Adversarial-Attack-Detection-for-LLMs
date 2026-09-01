# Novelty and Contribution

**Project:** Adversarial Attack Detection for Large Language Models (LLMs)
**Status:** PROPOSAL / UNDER INVESTIGATION

## Possible novelty

The project explores a detection architecture that treats detector disagreement and correlated false agreement as operationally relevant signals instead of as noise. If such patterns are real and stable, they may enable more nuanced verification routing and fewer unsafe false benign decisions.

## Why this is non-trivial

Many detection systems are built around a single model, a single score, or a simple consensus threshold. That approach can hide correlated blind spots where multiple detectors agree on the same wrong outcome. The project examines whether a heterogeneous detector stack can improve situational awareness by recording agreement, disagreement, and disagreement-conditioned risk.

## Contribution direction

The intended contribution is not a final framework yet. It is a research direction investigating whether disagreement-aware detection and false-agreement analysis can improve robustness under realistic constraints of latency, false positives, and verification cost.

## Contribution boundary

At this stage, the repository records a proposal rather than a validated outcome. The contribution claim remains provisional until it is backed by evidence from data qualification, experiments, and reproducible evaluation.
