# Research Architecture

**Project:** Adversarial Attack Detection for Large Language Models (LLMs)
**Status:** UNDER DEVELOPMENT

This document records the current research architecture direction for the project. It is intentionally neutral about framework naming. The term "DGAD" is treated as a non-authoritative working label used in informal architecture discussions only.

## Architecture direction

The current architecture explores a heterogeneous detector stack that combines multiple detection signals and evaluates agreement, disagreement, and conditional verification requirements. The objective is to improve robustness to evasion and reduce dependence on any single detector.

## Proposed research pattern

1. Collect heterogeneous detection signals across multiple attack and benign patterns.
2. Compare detector agreement and disagreement under realistic operating conditions.
3. Investigate correlated false-benign consensus and false-agreement failure modes.
4. Route uncertain or high-risk cases to deeper verification or adjudication.
5. Evaluate tradeoffs across false positives, latency, and verification cost.

## Design posture

This architecture remains a working research direction. The project is exploring whether disagreement-aware consensus and false-agreement analysis can improve robustness, but no claim of proven advantage is recorded here.

## Relationship to project naming

The official project remains Adversarial Attack Detection for Large Language Models (LLMs). Any references to DGAD in architecture discussion are provisional and non-authoritative unless the Commander explicitly approves a formal framework name.
