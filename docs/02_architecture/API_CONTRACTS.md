# API Contracts

**Project:** Adversarial Attack Detection for Large Language Models (LLMs)
**Status:** PROPOSAL / UNDER INVESTIGATION

## Scope

This document defines the expected interfaces for an experiment or middleware layer connecting detector outputs, policy checks, and verification routing.

## System boundary

- Input: text instance plus contextual metadata
- Output: decision bundle, risk signal, and verification recommendation
- Logging: traceable evidence for provenance and audit review

## Proposed service interfaces

### 1. Detector execution interface

Accept a normalized text sample and return detector outputs with version evidence and confidence metadata.

### 2. Aggregation interface

Accept multiple detector outputs and return agreement/disagreement metrics, consensus summaries, and false-agreement risk signals.

### 3. Verification routing interface

Accept a risk bundle and return a recommended action, such as allow, reject, or escalate.

### 4. Audit interface

Return the execution trace, data lineage, and issue metadata for governance review.

## Status

This API contract remains under design and should be considered experimental until it is used in a documented evaluation protocol.
