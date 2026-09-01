# Metrics

**Project:** Adversarial Attack Detection for Large Language Models (LLMs)
**Status:** UNDER INVESTIGATION

## Core metrics

The project will eventually need a metric set that balances detection quality, operational cost, and decision quality under uncertainty. For the current documentation stage, metrics remain provisional and must be tied to a specific evaluation protocol.

### Recommended provisional categories

- Attack detection recall and precision
- False benign rate and false positive rate
- Agreement/disagreement consistency across detectors
- Conditional verification utilization rate
- Verification latency and end-to-end cost
- Counterfactual robustness under prompt perturbation

## Measurement principles

- Measure both detection quality and decision cost.
- Separate raw detector outputs from adjudicated final outcomes.
- Record confidence, abstention, and escalation separately when present.
- Report uncertainty and dataset overlap when known.

## Status note

This is not a finalized metrics specification. A final metric package requires approved experimental design and a stable dataset constitution.
