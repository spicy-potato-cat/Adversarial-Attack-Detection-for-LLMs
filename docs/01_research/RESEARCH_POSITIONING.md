# Research Positioning

**Project:** Adversarial Attack Detection for Large Language Models (LLMs)
**Status:** UNDER DEVELOPMENT

## Established project scope

The project builds adversarial-attack detection and middleware capabilities for LLM applications. It covers evidence gathering, dataset qualification, forensic review, detection architectures, and defensive deployment considerations.

## Current architecture work

The architecture workstream is exploring heterogeneous detection, detector consensus and disagreement, false agreement, and conditional verification. This is an active research direction rather than a finalized framework.

## Research hypothesis

Multiple heterogeneous detectors may share correlated blind spots. In such a case, unanimous benign classification may still be incorrect, especially when detectors agree on a false negative under a shared failure mode.

## Research question

Can measuring and accounting for false agreement improve detection robustness under realistic false-positive, latency, and verification-cost constraints?

## Research posture

The project should document false-agreement ideas conservatively. The following remain research/design hypotheses until implemented and experimentally evaluated:

- FalseAgreementRisk model
- adaptive consensus auditing
- ConsensusAnalysisEngine implementation
- consensus-evasion attack methodology
- false-agreement hard-negative training
- detector selection based on error correlation
- claimed performance advantages of false-agreement-aware routing

This research direction is explicitly treated as an evolving contribution within the existing project, not as a renamed project or approved framework.
