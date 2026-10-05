# TECH-SEM-003 Test Report v1

Status: **INFRASTRUCTURE TESTS PASS; FULL PHASE PARTIAL / OOF RUN PENDING**.

Continuation: latest evidence is under `artifacts/semantic_v2/oof/preflight/`:
57 semantic tests (original 47 plus 10 preflight tests), 37 statistical tests,
94 passed, zero failures/errors/skips. Short real-upstream smoke was renewed on
the superseding code/config; measured training/prediction interval 5.544696 seconds.
Coverage remained 6->6 and 1,504->256 with 1,248 excluded; project data used NO.
The detailed pre-run freeze report is `TECH_SEM_003_OOF_PRERUN_EVIDENCE_v1.md`.
The original evidence/commands below describe the first preparation, not the active
post-continuation freeze. Do not regenerate or overwrite evidence after commit.

## Executed Checks

```powershell
.\.local-python\python.exe -m pytest detection_service/tests/test_semantic_oof.py -q --junitxml=artifacts/semantic_v2/oof/test_results_v1.xml
.\.local-python\python.exe -m detection_service.scripts.semantic_oof_baseline --mode record-tests --test-xml artifacts/semantic_v2/oof/test_results_v1.xml
.\.local-python\python.exe -m detection_service.scripts.semantic_oof_baseline --mode smoke
.\.local-python\python.exe -m detection_service.scripts.semantic_oof_baseline --mode check
```

47 tests, zero failures, zero errors, zero skipped. Readiness evidence binds the
JUnit XML and analysis config by SHA-256. `check` explicitly returns
PARTIAL_PIPELINE_PREPARED_OOF_NOT_RUN, not full-phase PASS.

Tests cover:

- QUALITY-001 manifest/fold hashes, expected counts and canonical-group identity.
- Complete frozen recipe, including revision, 256 input limit and optimizer settings.
- Drift rejection: length, epochs, batch size, LR, revision, weight decay, warmup,
  gradient clip and thread count.
- Synthetic five-fold control: disjoint train/held-out texts and labels, correct
  training-only class weights, fresh model per fold, one ordered prediction per ID.
- Seed reset before each initialization; differing upstream parameter hashes reject.
- Reserved/mixed CALIBRATION, VALIDATION and protected selections reject before
  loader or training invocation. Duplicate IDs, lineage splits, missing scores reject.
- Prediction corruption, invalid probability, coverage/calibration/fold and confidence
  metadata reject; no invented results after failure.
- Hand-calculated confusion, ROC-AUC and average precision; attainable fixed-FPR
  behavior, score ties, and no-positive-prediction ROC point.
- Class-conditional truncation denominators, empty-support nulls and Wilson intervals.
- Confidence boundaries/count conservation, length buckets, subgroup/stability output.
- QUALITY OOF schema projection, stable CSV ordering, no prompt fields in exports.
- Path/hash drift and Python-level raw/protected/authoritative-write gates.
- 96 original baseline metadata/code hashes and absence of final-artifact loading,
  download, or original train_once calls in the new execution path.
- Actual prediction function using synthetic tokenizer/model doubles: attention-mask
  counts exclude padding and include specials; exact 256/257 boundary and logit margin.

The synthetic five-fold tests exercise orchestration with model doubles; they do
NOT claim five real transformer refits or real-data predictive performance.

Additional regression: 37 existing TECH-STAT-003 tests passed (84 tests total across
the two commands). Its read-only verifier passed all nine frozen OOF output hashes
and 1,135-row metric reconstruction. scikit-learn emitted a SciPy L-BFGS-B option
deprecation warning; no test failure or current package-install requirement results.
Final semantic preflight verification still returns explicit OOF-not-run status.

## Real Upstream Training Smoke

Cached pinned DistilRoBERTa was loaded offline with a freshly seeded binary head;
82,119,938 parameters verified. Eight synthetic short texts, batch eight, three
epochs, original weighted-loss training function with synthetic balanced weights;
three optimizer steps, finite loss and changed parameters. No project model saved.
The synthetic classifier was scored at max 256, in eval/inference mode, and repeated
scores agreed exactly. Short coverage 6 tokens; long coverage 1,504 input, 256
analyzed, 1,248 excluded. No Dataset path opened in this mode.

Measured training/prediction interval: 5.892882 seconds, excluding model setup and
preservation checks. This is NOT an extrapolation from a worst-length training batch
or a full OOF runtime. Prior authoritative runtime supplies the long-run estimate.
Expected newly initialized head warning is not a dependency failure.

## Preservation And Environment

CPU execution, installed Torch 2.6.0+cpu; physical RTX 3070 Ti visible but CUDA
unavailable. Frozen package dictionary matches original preparation. No additional
package installation is genuinely required for this CPU pipeline.
Original dm_b_v1 integrity manifest verifies opaque file hashes including weights;
no authoritative checkpoint/calibrator is deserialized. Original app/config paths,
D_S, D_M-A, D_M-B, D_G metadata and prior D_M-B reports are unchanged. Existing
TECH-STAT-003 output hashes are also protected by this phase's preservation map.

Manifest/fold hashes remain as in the authorization. No raw file modification,
protected payload access, reserved-row scoring, E1-E10 or dm_b_v2 training occurred.
The later full run permits ONLY BASE_TRAIN selected scalars from the three approved
source containers. This does not imply physical byte isolation from reserved rows
inside those mixed CSV/Parquet files. Audit gates are not a native-library sandbox.

## Remaining Acceptance Evidence

The actual five-fold run, 1,135 real OOF predictions, actual fold training histories,
aggregate/per-fold metrics, Recall@1/3/5% FPR, truncation/confidence/source analyses,
hard IDs and B1 support must still be measured. No final acceptance or READY FOR
TECH-SEM-004 claim is made. Commander command is in the OOF Baseline report;
return its completed output, then verify and update these new phase reports.
