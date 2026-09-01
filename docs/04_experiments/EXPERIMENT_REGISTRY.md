# Experiment Registry

**Project:** Adversarial Attack Detection for Large Language Models (LLMs)
**Status:** UNDER INVESTIGATION

## Registry purpose

The experiment registry tracks proposed experiments, their evidence basis, and their governance status. It does not authorize execution or final acceptance of a benchmark or dataset role.

## Current entries

The following experiment identifiers are documentation and planning labels only. They do not constitute approval of methodology, datasets, thresholds, model choices, evaluation protocol, or execution.

### EXP-001: Heterogeneous detector agreement audit

**Status:** PROPOSED

Purpose: compare multiple detector outputs on the same prompt set and document agreement, disagreement, and false agreement patterns.

### EXP-002: Conditional verification routing study

**Status:** PLANNED

Purpose: evaluate whether routing uncertain or high-risk cases to deeper verification improves safety without unacceptable latency cost.

### EXP-003: Contamination and lineage sensitivity check

**Status:** EXPERIMENTAL

Purpose: measure how overlap and lineage issues affect reported detector performance.

## Registry rule

Any experiment must be traceable to a controlled evidence set and reviewed against provenance and contamination constraints before a result is treated as a strong claim. No experiment identifier implies Commander approval, execution, or completion.
