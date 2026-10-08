# R1_SHIFTED_UNSEEN Results v2

Status: **COMPLETE**, OPERATIONAL_FIXED_V1. This prospectively supersedes the unchanged v1 blocked report.

## 1. R1 Dataset Constitution

Gate B PASS. Dataset `R1-CORE-LLMAIL-INJEC-OR-v1`: 1,800 rows, 800 attacks and 1,000 benign inputs. 400 LLMail-Inject explicit attack attempts, 400 InjecAgent BASE responses (200 direct-harm, 200 data-stealing), and 1,000 OR-Bench hard-benign prompts. Pre-scoring freeze commit `eeafd52b097b43e8afbda6f08c97fa96fdeaecec`. Dataset manifest file SHA-256 `44990563b0835c16b19c596fad6a91c3581a6b6c285468f9153a3a9df29244fa`. No detector score informed source selection or sampling. All sources are cleared with local-only restriction; raw text is excluded from Git.

## 2. Unseen-Source Justification

No R1 source was used in the accepted BASE_TRAIN, CALIBRATION or VALIDATION constitution (deepset Prompt Injection and Do-Not-Answer). LLMail is human/adaptive indirect injection against disclosed upstream defenses; InjecAgent is textual external/tool injection; OR-Bench is a model-selected over-defence shift. This is source-disjoint project development evaluation, not proof of unseen foundation-model pretraining. LLMail is not a new R2 attack against this stack. See [source clearance](R1_SOURCE_CLEARANCE_v1.md) and its exact revision/license/mirror evidence.

## 3. Contamination Audit

All 23,380 candidates were compared with all 1,601 development rows. Raw exact and approved N1 matches: zero. Source-native IDs are not comparable across these source domains; no documented shared development lineage, hidden reuse UNKNOWN. Approved lexical threegram Jaccard census at 0.7/0.8/0.9 found one unselected LLMail candidate at 0.97123; selected near matches: zero. Eleven multi-team LLMail candidates were excluded before score-blind sampling. No new semantic threshold. Originals were not modified.

## 4. Lineage Structure

1,097 lineage components: 96 hashed LLMail teams, one 400-row InjecAgent transitive attacker/user dependency component, and 1,000 OR singleton fallbacks. LLMail max five selected prompts per team; all 17 InjecAgent user tools represented. Source relations and N1 duplicates are unioned conservatively. LINEAGE_CLUSTERED was frozen pre-score. The giant InjecAgent cluster limits pooled inference and forbids pretending 400 independent cases. OR singleton fallback does not prove independence.

## 5. Frozen Detector Identities

| Detector | Frozen Identity | Operational Score | Threshold |
|---|---|---|---|
| D_S | ds_v2 + ds_v2_cal_v1 | calibrated_score | 0.5585373573968287 |
| D_M-B | dm_b_v1 + frozen calibration | raw_score | 0.0004967087297700347 |
| D_G | Meta Prompt Guard 2 22M; 11614a155199674a0a95e6602d6ab0417b790ed0 | raw_score | 0.21291141211986545 |
Inclusive >=, exact frozen IDs; native votes remain separate. D_S accepted archive provenance/equivalence is preserved. All runtimes use existing frozen loaders, revisions, tokenization, windows and weights. No resource/device overrides.

## 6. Operational Performance

| Detector | TP | FN | FP | TN | Accuracy | Precision | Recall | Specificity | F1 | FPR | FNR |
|---|---|---|---|---|---|---|---|---|---|---|---|
| ds_v2 | 698 | 102 | 28 | 972 | 92.778% | 96.143% | 87.250% | 97.200% | 91.481% | 2.800% | 12.750% |
| dm_b_v1 | 800 | 0 | 132 | 868 | 92.667% | 85.837% | 100.000% | 86.800% | 92.379% | 13.200% | 0.000% |
| dg_v1 | 36 | 764 | 207 | 793 | 46.056% | 14.815% | 4.500% | 79.300% | 6.903% | 20.700% | 95.500% |
Gate C PASS: 5400/5,400 canonical predictions, no missing, duplicate or non-OK rows. After an interrupted invocation, the unchanged resume-safe scorer validated all three complete native journals and finalized the receipt without new inference. The receipt start/completion timestamps and runtime describe that resumed finalization invocation, not total original inference time; native per-row latencies are preserved. Operational thresholds are transported from calibration; 3% calibration budget is not a guarantee of 3% R1 FPR.

## 7. Descriptive Frontier

| Detector | Budget | Raw Threshold | Recall | Attained FPR | TP | FN | FP | TN |
|---|---|---|---|---|---|---|---|---|
| dg_v1 | 1.000% | 0.9891414642333984 | 1.625% | 0.300% | 13 | 787 | 3 | 997 |
| dg_v1 | 3.000% | 0.9605088829994202 | 2.375% | 2.700% | 19 | 781 | 27 | 973 |
| dg_v1 | 5.000% | 0.8984565734863281 | 2.750% | 4.800% | 22 | 778 | 48 | 952 |
| dm_b_v1 | 1.000% | 0.9989068508148193 | 100.000% | 0.000% | 800 | 0 | 0 | 1000 |
| dm_b_v1 | 3.000% | 0.9989068508148193 | 100.000% | 0.000% | 800 | 0 | 0 | 1000 |
| dm_b_v1 | 5.000% | 0.9989068508148193 | 100.000% | 0.000% | 800 | 0 | 0 | 1000 |
| ds_v2 | 1.000% | 0.845165738165399 | 79.875% | 1.000% | 639 | 161 | 10 | 990 |
| ds_v2 | 3.000% | 0.7878432442707937 | 88.250% | 3.000% | 706 | 94 | 30 | 970 |
| ds_v2 | 5.000% | 0.7493022625470236 | 90.250% | 5.000% | 722 | 78 | 50 | 950 |
SECONDARY descriptive_frontier_v1 only. Whole tied blocks; no threshold or operational decision changed.

## 8. Ranking Metrics

| Detector | R0 ROC-AUC | R1 ROC-AUC | R0 AP | R1 AP |
|---|---|---|---|---|
| dg_v1 | 0.814953850392616 | 0.40694875 | 0.5006519683988974 | 0.37789020357305086 |
| dm_b_v1 | 0.9963493594158975 | 1.0 | 0.9877044339233646 | 0.9999999999999911 |
| ds_v2 | 0.896760343481655 | 0.97433625 | 0.7315865803288281 | 0.9748953375370448 |
Frozen Phase-13 whole-tied-block ROC-AUC and Average Precision, raw-score basis. AP changes are prevalence-sensitive: R0 attack prevalence 183/1135; R1 800/1800. R0 ranking metadata is loaded through the release inventory, not reconstructed manually.

## 9. Pairwise Shared Failure

| Pair | Shared FN | JFN | 95% CI JFN | Independence Reference | EJF | FN Jaccard |
|---|---|---|---|---|---|---|
| ds_v2/dm_b_v1 | 0 | 0.000% | [0.000%, 0.000%] | 0.000% | 0.000% | 0.000% |
| ds_v2/dg_v1 | 101 | 12.625% | [2.391%, 17.504%] | 12.176% | 0.449% | 13.203% |
| dm_b_v1/dg_v1 | 0 | 0.000% | [0.000%, 0.000%] | 0.000% | 0.000% | 0.000% |
Independence products are references, not assumptions. EJF is joint failure minus the product of marginal FNRs.

## 10. All-Three Failure

All-three FN: 0/800. JFN: 0.000%. 95% CI: [0.000%, 0.000%].

## 11. Failure Patterns

| Miss Pattern S/M/G | Attack Count | Attack Rate |
|---|---|---|
| 000 | 35 | 4.375% |
| 001 | 663 | 82.875% |
| 010 | 0 | 0.000% |
| 011 | 0 | 0.000% |
| 100 | 1 | 0.125% |
| 101 | 101 | 12.625% |
| 110 | 0 | 0.000% |
| 111 | 0 | 0.000% |
0 means caught; 1 means missed. Thus 000 is caught by all and 111 is missed by all. No ensemble or router decision is created.

## 12. Unique Catches

| Detector | Unique Catch Count | Rate / All 800 Attacks | 95% CI |
|---|---|---|---|
| ds_v2 | 0 | 0.000% | [0.000%, 0.000%] |
| dm_b_v1 | 101 | 12.625% | [2.391%, 17.504%] |
| dg_v1 | 0 | 0.000% | [0.000%, 0.000%] |

## 13. Conditional Recovery

| Detector | Recovered | Both Others Miss | Recovery | 95% CI / Status |
|---|---|---|---|---|
| ds_v2 | 0 | 0 | UNDEFINED | OBSERVED_UNDEFINED |
| dm_b_v1 | 101 | 101 | 100.000% | [100.000%, 100.000%] |
| dg_v1 | 0 | 0 | UNDEFINED | OBSERVED_UNDEFINED |
Undefined/unstable denominators remain explicit; these are conditional descriptive rates, not verifier performance.

## 14. Family-Conditioned Analysis

| Source / High-Level Family | N | Lineages | S FNR | M FNR | G FNR | S/M JFN | S/G JFN | M/G JFN | All FN | All JFN |
|---|---|---|---|---|---|---|---|---|---|---|
| INJECAGENT_BASE | 400 | 1 | 21.500% | 0.000% | 99.750% | 0.000% | 21.500% | 0.000% | 0 | 0.000% |
| LLMAIL_INJECT | 400 | 96 | 4.000% | 0.000% | 91.250% | 0.000% | 3.750% | 0.000% | 0 | 0.000% |

Worst-family/source observations:

| Metric | Worst Source | N | Rate |
|---|---|---|---|
| all_three/jfn | INJECAGENT_BASE | 400 | 0.000% |
| fnr/dg_v1 | INJECAGENT_BASE | 400 | 99.750% |
| fnr/dm_b_v1 | INJECAGENT_BASE | 400 | 0.000% |
| fnr/ds_v2 | INJECAGENT_BASE | 400 | 21.500% |
| jfn/dm_b_v1/dg_v1 | INJECAGENT_BASE | 400 | 0.000% |
| jfn/ds_v2/dg_v1 | INJECAGENT_BASE | 400 | 21.500% |
| jfn/ds_v2/dm_b_v1 | INJECAGENT_BASE | 400 | 0.000% |
Source and high-level family coincide here. Both groups have 400 positives; no detailed subtype inference. InjecAgent has only one dependency cluster, so source-level results are descriptive, not independent-case inference. Equal-rate worst-source ties are listed deterministically, not as uniquely worse sources. Complete source-conditioned eight-pattern and pairwise accounting is in r1_family_analysis_v1.json. n<20 would be LOW_SUPPORT_DESCRIPTIVE_ONLY; no such attack group here.

## 15. Uncertainty

Production defaults unchanged: 1,000 replicates, PCG64 seed 1701, 95% percentile intervals, LINEAGE_CLUSTERED, attack and benign domains separate. All requested FNR/FPR, pairwise/three-way JFN, unique catch and recovery intervals are retained with their valid-replicate statuses.

| Detector | FNR 95% CI | FPR 95% CI |
|---|---|---|
| ds_v2 | [2.663%, 17.532%] | [1.800%, 3.800%] |
| dm_b_v1 | [0.000%, 0.000%] | [11.098%, 15.200%] |
| dg_v1 | [88.480%, 98.172%] | [18.300%, 23.202%] |
The 400-row InjecAgent cluster is sampled whole and can be absent or repeated; pooled source mixture and denominators vary. These conditional empirical CIs do not account for training-set, unseen-source or foundation-model exposure uncertainty. Singleton OR fallback is a modelling limitation.

## 16. R0 Versus R1 Comparison

| Metric | R0 | R1 | Delta Fraction | Delta Percentage Points |
|---|---|---|---|---|
| all_three/jfn | 0.01092896174863388 | 0.0 | -0.01092896174863388 | -1.092896174863388 |
| individual/dg_v1/fnr | 0.7704918032786885 | 0.955 | 0.18450819672131147 | 18.450819672131146 |
| individual/dg_v1/fpr | 0.017857142857142856 | 0.207 | 0.18914285714285714 | 18.914285714285715 |
| individual/dm_b_v1/fnr | 0.01092896174863388 | 0.0 | -0.01092896174863388 | -1.092896174863388 |
| individual/dm_b_v1/fpr | 0.06092436974789916 | 0.132 | 0.07107563025210084 | 7.107563025210084 |
| individual/ds_v2/fnr | 0.3825136612021858 | 0.1275 | -0.25501366120218577 | -25.501366120218577 |
| individual/ds_v2/fpr | 0.045168067226890755 | 0.028 | -0.017168067226890755 | -1.7168067226890755 |
| pair/dm_b_v1/dg_v1/ejf | 0.002508286302965153 | 0.0 | -0.002508286302965153 | -0.2508286302965153 |
| pair/dm_b_v1/dg_v1/jfn | 0.01092896174863388 | 0.0 | -0.01092896174863388 | -1.092896174863388 |
| pair/ds_v2/dg_v1/ejf | -0.010570635133924589 | 0.004487500000000005 | 0.015058135133924594 | 1.5058135133924595 |
| pair/ds_v2/dg_v1/jfn | 0.28415300546448086 | 0.12625 | -0.15790300546448086 | -15.790300546448085 |
| pair/ds_v2/dm_b_v1/ejf | 0.006748484577025292 | 0.0 | -0.006748484577025292 | -0.6748484577025292 |
| pair/ds_v2/dm_b_v1/jfn | 0.01092896174863388 | 0.0 | -0.01092896174863388 | -1.092896174863388 |
| recovery/dg_v1/conditional_recovery | 0.0 | UNDEFINED | UNDEFINED | UNDEFINED |
| recovery/dg_v1/unique_catch_rate | 0.0 | 0.0 | 0.0 | 0.0 |
| recovery/dm_b_v1/conditional_recovery | 0.9615384615384616 | 1.0 | 0.038461538461538436 | 3.8461538461538436 |
| recovery/dm_b_v1/unique_catch_rate | 0.273224043715847 | 0.12625 | -0.14697404371584702 | -14.697404371584701 |
| recovery/ds_v2/conditional_recovery | 0.0 | UNDEFINED | UNDEFINED | UNDEFINED |
| recovery/ds_v2/unique_catch_rate | 0.0 | 0.0 | 0.0 | 0.0 |
Every delta is R1 minus R0. Descriptive and unpaired; no sample/lineage correspondence, paired significance test or causal attribution. R0 statistical/semantic evidence is fold-local OOF; R1 uses frozen final models. Sources, attack mix, lengths, prevalence and model execution provenance differ; no causal or paired inference.

## 17. Operating-Point Drift Versus Ranking Degradation

| Detector | Operational FNR Delta | Operational FPR Delta | ROC-AUC Delta | 3% Frontier Recall Delta |
|---|---|---|---|---|
| dg_v1 | 0.18450819672131147 | 0.18914285714285714 | -0.408005100392616 | -0.2057581967213115 |
| dm_b_v1 | -0.01092896174863388 | 0.07107563025210084 | 0.0036506405841024714 | 0.021857923497267784 |
| ds_v2 | -0.25501366120218577 | -0.017168067226890755 | 0.077575906518345 | 0.3360519125683059 |
Frozen policy drift and discrimination are distinct measurements. A low transported threshold can raise FPR without proving poor ranking; a falling ROC-AUC/frontier supports discrimination degradation. AP also depends on changed prevalence. Source mix, input length/coverage and OOF-versus-final-model provenance prevent isolating a single cause; no calibration refit is proposed from R1.

## 18. Limitations

Source-attempt labels may contain judge noise; hard benign labels are benchmark labels, not universal harmlessness. LLMail excludes uncertain labels/multi-team keys and uses only phase-2 files. Model pretraining and hidden source reuse are UNKNOWN. Large InjecAgent dependency cluster and generated OR singleton fallback limit uncertainty. R0 is historical development OOF for S/M; R1 uses final models and a different source/label/length mix. Source/family analysis is not a controlled causal comparison. Text-only tool-response screening is not end-to-end agent safety or attack-success measurement. Token coverage/truncation is frozen, not repaired after outcomes.

| Detector | Truncated Rows | Max Input Tokens |
|---|---|---|
| dg_v1 | 0 | 6390 |
| dm_b_v1 | 117 | 7144 |
| ds_v2 | 1 | 7144 |
Raw prompts and participant IDs remain local-only. No protected/final benchmark payload was used.

## 19. Research Interpretation

All-three JFN moved from 1.093% to 0.000% (-1.093 percentage points). There is no observed increase in all-three shared failure in this R1 population. Pairwise EJF and exclusive-catch changes must be read alongside marginal errors, ranking and source-conditioned results; a single changed JFN does not establish diversity collapse. Unique-catch changes: {"recovery/dg_v1/unique_catch_rate": 0.0, "recovery/dm_b_v1/unique_catch_rate": -0.14697404371584702, "recovery/ds_v2/unique_catch_rate": 0.0}. No significance or broad safety claim is made.

ds_v2: operational recall 87.250% and FPR 2.800%; raw ROC-AUC 0.974336; descriptive 3%-budget recall 88.250% at attained FPR 3.000%.

dm_b_v1: operational recall 100.000% and FPR 13.200%; raw ROC-AUC 1.000000; descriptive 3%-budget recall 100.000% at attained FPR 0.000%.

Perfect empirical ranking is confined to this curated source mixture. It is compatible with operational false positives under a transported threshold and does not establish general unseen-attack robustness.

dg_v1: operational recall 4.500% and FPR 20.700%; raw ROC-AUC 0.406949; descriptive 3%-budget recall 2.375% at attained FPR 2.700%.

ROC-AUC below 0.5 and the weak low-FPR frontier indicate poor discrimination in the frozen score direction on this population, not just transported-threshold drift. This does not establish its cause; score direction, model and policy remain unchanged.

Zero all-three misses here is driven by D_M-B catching every observed attack; it is not evidence that every stack member adds exclusive coverage. D_S and D_G have no exclusive catches in this population. Zero-event percentile intervals do not bound future unseen-source risk.

## 20. No Post-R1 Adaptation

No detector, model, feature, tokenizer, preprocessing, reference LM, calibration, operational threshold, metric definition, bootstrap definition, prediction semantics, regime semantics, R0 evidence or protocol lock was changed after observing R1. No retraining, fitting, targeted attack generation, protected/final evaluation, router, verifier, R2 or R3 was begun. Cycle 2 remains DEFERRED. Gate-B and Gate-C commits remain separate. Full artifact/test/hash receipts accompany acceptance.
