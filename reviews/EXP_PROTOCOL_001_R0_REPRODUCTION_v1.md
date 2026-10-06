# EXP-PROTOCOL-001 Phase 13: Exact Accepted R0 Reproduction

Status: PASS for historical descriptive reproduction. This is NOT the Phase-5
operational view. Phase 14 and real R1/R2/R3 remain NOT STARTED.

## Authority And Import Boundary

Branch: `exp/protocol-001`.
Cycle-1 accepted base: `dc6dd3041643fb70ad5b128d32c246f8763a8044`.
Task start: `9874e5e5726b3110c4277026b5c168cf8ff41a51`.
Phase-11/12 machinery was committed with a clean working tree BEFORE importing
real R0 evidence: `9982b9bd2c5f8da7fc63a1b7977c1cccf91cfb70`.

The accepted publication manifest was compared with its exact Cycle-1 Git blob.
Its links locate the actual score, membership, fold, run, analysis, and publication
files; filenames were not inferred from remembered conventions. The import
manifest binds 123 source SHA-256 checks, absolute source paths, sizes, and
logical roles. Twenty fold training/held-out membership hashes also pass.

Population: 1,135 unique samples; 183 attacks; 952 benign; 1,134 total lineages;
183 attack lineages; zero unknown lineage IDs. Every source agrees on sample,
truth, lineage, and applicable fold membership.

Development membership SHA:
`9cdd5ecdd80f9ac3c8f05db63742721f4537ca2b64a2fe48f6c2b424b57483a6`.
Frozen fold SHA:
`19dc0153cc257cc2331782d6dd61b7bb9fb8cb0ed88d3e782b69d5ba05c4bb8d`.

## Score Semantics And Provenance

| Physical ID | Accepted source | Evidence and score semantics |
|---|---|---|
| `ds_v2` | `artifacts/statistical_v2/scorer_comparison/scorer_predictions_v1.csv`, S0 only | B2+LR OOF class-1 probability; not S1/S2, and not final fitted-model inference |
| `dm_b_v1` | `artifacts/semantic_v2/oof/dm_b_v1_recipe_oof_predictions.csv` | Recipe OOF raw class-1 softmax, 256-token prefix; not final fitted-model inference |
| `dg_v1` | `artifacts/guard_v1/development/completion_v3/dg_v1_base_train_predictions.csv` | Accepted frozen development predictions; raw maximum chunk class-1 softmax |

Respective score-source SHAs:

- D_S: `1dd23a39bb87f3f95b090a93bb7797ae6a1d84e4ddf24a55d63b9eb2609e9fed`.
- D_M-B: `cfafb1d4286a8b61e4054da337cd45a4353a44894899b034670f9413f6b1000c`.
- D_G: `2589d5c8f9da40be4104c2964966f7b1790b2370255bd87515e63760f2a624ef`.

D_S accepted run provenance remains
`f123a46c320075a52ef0af3d09e2de734e4895f9`; D_M-B remains
`5096d078b599c43ddd4e32b4fbfcaedcc83e4646`; D_G remains
`3a053f3224e56d9e7b483b72303e822af12e5741`.
The evidence commit is not substituted for any model/run commit.

The importer does not manufacture live/final-model `PredictionRecord` objects
with false final-model hashes. It builds the existing strict `AlignedEvaluation`
from verified historical rows and import-bound EXPLICIT decisions. OOF recipe
aliases are documented separately from final-artifact identities. No frozen
prediction schema or detector adapter is changed.

## Historical Explicit Decisions

There are 10,215 records: three detectors x 1,135 samples x three budgets. Each
record binds sample, truth, lineage, fold where applicable, score, source path/SHA,
evidence kind, stored cutpoint, explicit decision, and decision provenance.
No raw prompts are included.

| Budget | D_S stored cutpoint | D_M-B stored cutpoint | D_G stored cutpoint |
|---|---:|---:|---:|
| 1% | 0.9334402237345568 | 0.013269803486764431 | 0.7775133848190308 |
| 3% | 0.8501334532357456 | 0.0008947817841544747 | 0.23945845663547516 |
| 5% | 0.784023369186312 | 0.0006214274326339364 | 0.050292547792196274 |

Decisions use the accepted inclusive `score >= stored threshold` rule. The old
generic whole-tied-block frontier selector independently verifies these stored
cutpoints and counts; it does not replace them. The resulting reusable
`descriptive_frontier_v1` remains DESCRIPTIVE ONLY. Phase-5 operational
thresholds were not used or changed.

## Exact Confusion Counts

Cells are TP / FN / FP / TN. Every integer matches exactly, without tolerance.

| Budget | D_S | D_M-B | D_G |
|---|---|---|---|
| 1% | 60 / 123 / 9 / 943 | 177 / 6 / 7 / 945 | 34 / 149 / 6 / 946 |
| 3% | 100 / 83 / 28 / 924 | 179 / 4 / 22 / 930 | 42 / 141 / 17 / 935 |
| 5% | 115 / 68 / 46 / 906 | 181 / 2 / 34 / 918 | 49 / 134 / 44 / 908 |

## Common-Mode And Recovery

The unchanged frozen core computes the following 3% results. Count-derived
floating quantities match accepted machine-readable evidence within `1e-12`.

| Pair | Shared FN | JFN | Independence | EJF | FN Jaccard |
|---|---:|---:|---:|---:|---:|
| S/M | 3 | 0.01639344262295082 | 0.009913703006957509 | 0.006479739615993312 | 0.03571428571428571 |
| S/G | 61 | 0.3333333333333333 | 0.34945803099525213 | -0.01612469766191882 | 0.37423312883435583 |
| M/G | 4 | 0.02185792349726776 | 0.016841350891337453 | 0.005016572605930306 | 0.028368794326241134 |

All-three FN counts at 1% / 3% / 5%: **5 / 3 / 2**, exactly.
At 3%, all-three JFN is `3/183 = 0.01639344262295082`.

Failure bits retain the frozen S/M/G order, where 1 means miss:

| Pattern | Count |
|---|---:|
| 000 | 20 |
| 001 | 79 |
| 010 | 0 |
| 011 | 1 |
| 100 | 22 |
| 101 | 58 |
| 110 | 0 |
| 111 | 3 |

| Detector | Unique catch | Conditional recovery |
|---|---:|---|
| D_S | 1 | 1/4 = 0.25 |
| D_M-B | 58 | 58/61 = 0.9508196721311475 |
| D_G | 0 | 0/3 = 0 |

All pattern, unique-catch, and recovery counts match exactly. Negative EJF is
preserved, not clipped.

## Ranking Metrics

| Detector | ROC-AUC | Average precision |
|---|---:|---:|
| D_S | 0.896760343481655 | 0.7315865803288281 |
| D_M-B | 0.9963493594158975 | 0.9877044339233646 |
| D_G | 0.814953850392616 | 0.5006519683988974 |

The historical field named `pr_auc` is **AVERAGE_PRECISION_WHOLE_TIED_BLOCKS**,
not trapezoidal PR-AUC. Full-precision accepted publication values reproduce
within `1e-12`. No metric definition was changed to match rounded report values.

## Historical Uncertainty And Explicit RNG Difference

Accepted uncertainty used paired attack-lineage resampling: 1,000 replicates,
seed 1701, 95% percentile intervals, sorted lineage groups, and a fresh Python
`random.Random(1701)` stream per budget. The accepted code uses MT19937 and linear
percentile interpolation. Its source SHA is
`9330a1725b292acf9287c1861c0b548702358f4e40d522504baebee2bb4b3b41`.

The Phase-11 production contract instead freezes NumPy 2.1.3 PCG64 with explicit
`quantile(method="linear")`. Equal seeds do not make these RNGs produce equal
draws. This method difference is explicit and resolved from the accepted source;
neither historical evidence nor the production RNG is rewritten.

A separate additive historical replay generates the accepted indices and reuses
the new metric/interval machinery. It is labelled
`HISTORICAL_RNG_REPLAY_NOT_PRODUCTION_PCG64`, never falsely labelled production
contract compliance. Historical required CIs at all three budgets reproduce the
full-precision machine-readable evidence within `1e-12`.

| 3% metric | Exact historical Python-RNG replay CI | New production PCG64 CI |
|---|---|---|
| M/G JFN | [0.00546448087431694, 0.04371584699453552] | [0.005327868852459024, 0.04918032786885246] |
| S/G JFN | [0.2677595628415301, 0.40437158469945356] | [0.2677595628415301, 0.3989071038251366] |
| All-three JFN | [0, 0.03825136612021858] | [0, 0.03825136612021858] |

Every listed interval has 1,000 valid and zero invalid replicates. Observed point
estimates are identical and come from the frozen core, not replicate averages.
Both RNG paths record unit, domain, seed, runtime/library identity, draw/plan and
state hashes, valid/invalid counts, and input provenance.

The real R0 bundle references production PCG64 intervals. Exact historical replay
intervals remain separately labelled in `r0_uncertainty_reproduction_v1.json`.

## Cross-Regime Bundle

Real R0 is OBSERVED under `HISTORICAL_DESCRIPTIVE_3PCT_V1`, EXPLICIT decisions.
R1, R2-D_S, R2-D_M-B, R2-D_G, and R3 are NOT_RUN, not zero-valued evidence.
R2-only metrics remain NOT_APPLICABLE outside R2. No real future-regime result
was created. The operational policy hash and thresholds are not attached to this
historical descriptive view.

## Artifacts, Tests, And Preservation

Twelve deterministic R0 outputs reside in `artifacts/research_protocol/r0/`:
verified import, explicit decisions, individual metrics, common mode, patterns,
recovery, ranking, historical/production uncertainty, descriptive frontier,
cross-regime bundle/matrix, and machine-readable reproduction report.

`artifacts/research_protocol/phase11_13_artifact_hashes_v1.json` binds the
Phase-11/12 artifacts/code, prior inventory, Phase-13 code/tests, all R0 outputs,
and the four requested reports: 33 entries. The inventory does not hash itself.
The final release gate is the CLI `r0_reproduction --mode check`: hash validation
plus byte-identical reconstruction. Its executed result is reported at handoff.

Executed test totals and preservation coverage are in
`EXP_PROTOCOL_001_PHASE11_13_TEST_REPORT_v1.md`. Frozen detector verification
covers 165 files, including all 96 baseline preservation checks. Source raw
prompts were not read. Model weights were read only for cryptographic integrity
checks, not loaded for inference. No detector, model, calibrator, partition,
accepted Cycle-1 result, prior schema, operating policy, or core metric changed.

No training, rescoring, new payload acquisition, protected experiment, Cycle-2
work, verifier, real R1/R2/R3, or Phase-14 execution occurred.

## Integration Guarantee

The harness exactly reproduces accepted historical OOF/direct R0 evidence while
preserving frozen detector semantics, explicit historical decisions, populations,
and metric definitions; unrun future regimes remain explicitly NOT_RUN.
