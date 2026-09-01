# Baselines

**Project:** Adversarial Attack Detection for Large Language Models (LLMs)
**Status:** UNDER INVESTIGATION

## Candidate baseline categories

1. Single-detector thresholds
2. Majority-vote ensembles
3. Rule-based sensitive-content filters
4. Static safety classifiers
5. Benchmark-derived reference scores from publicly available prompts

## Baseline selection principle

A baseline should be selected only when evidence supports its provenance, intended use, and independence from the candidate evaluation dataset. Benchmark packaging alone is not sufficient evidence for an approved baseline.

## Current project posture

The repository references many public benchmark families, including AdvBench, HarmBench, JailbreakBench, XSTest, and others. These are considered provisional evidence sources and not automatically approved baselines for final model comparison.

## Evaluation caveat

Any baseline claim must be accompanied by disclosure of likely contamination risk, dataset overlap, and licensing or provenance uncertainty.
