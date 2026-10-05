# TECH-GUARD-001 Implementation Report v1

Date: 2026-10-02. Standalone status: PASS. Central default wiring: DEFERRED.

## Files And Ownership

Added detection_service/app/detectors/guard/{__init__,config,model,detector}.py.
Added scripts prepare_guard.py, smoke_guard.py, verify_guard_regressions.py.
Added detection_service/tests/test_guard.py.
Added dg_v1 policy, freeze metadata, integrity manifest, smoke/test evidence.
Modified .gitattributes only for exact dg_v1 bytes; updated five guard reports.
Original qualification/environment JSON preserves historical blocked evidence.
No requirements/.gitignore/main/API/shared-contract changes. Existing statistical/
semantic implementations, tests, calibrations, artifacts and completion/status
reports remain untouched. No project dataset/manifests were opened.

## Lifecycle And Inference

GuardDetector implements BaseDetector. Authoritative standalone entry point:
```python
from detection_service.app.detectors.guard import GuardDetector
guard = GuardDetector.from_artifact()
result = guard.detect(request)  # DetectionRequest -> DetectorResult
```
Root resolves from module path. Runtime never downloads: local_files_only=True,
trust_remote_code=False, safetensors-only. All nine snapshot files and both freeze
documents are verified before loading. Paths must stay inside workspace.
Revision, tokenizer, architecture, parameter count, context, labels and special
IDs are checked. Any missing/unexpected/mismatched weights or loading errors fail;
no newly initialized classifier is accepted.
Persistent model/tokenizer are reused, eval/float32/no-grad, with locked inference.
Injected components are for isolated synthetic engineering fixtures only.
prepare_guard freezes an already downloaded exact snapshot, never downloads, and
refuses to overwrite an existing freeze. A new checkout still needs authorized
local weights. No training or fine-tuning occurs.

Strict UTF-8 validation precedes unmodified upstream tokenization. Direct IDs
are chunked at 510 content tokens, 64 overlap, 446 stride; two specials give 512.
Batch size 8; masks/padding preserve IDs. No decode/re-encode/truncation/tail drop.
Finite two-class logits required. raw_score=max temperature-1 class-1 softmax.
binary_vote=OR of native argmax class 1; ties are benign, not score >= 0.5.
No project calibration or tuned operating point.

DetectorResult: guard_external/dg_v1, success, raw_score, bool binary_vote,
calibrated_probability=None, measured latency, ModelMetadata, InputCoverage,
bounded metadata. Statistical/semantic feature blocks are None.
Coverage counts distinct content tokens, excludes none, reports ratio=1 and
truncated=False. Metadata includes token/chunk count, context, specials, overlap,
stride, long-input flag, max-risk chunk index/span, aggregate score and tail.
No raw text or unbounded per-chunk score list is returned.

## Errors And Edges

Unchanged request schema rejects empty/whitespace or invalid-type inputs.
Unicode/NUL-bearing valid strings use the pinned tokenizer.
Unpaired surrogates raise explicit GuardUnavailableError.
Zero upstream content tokens produce insufficient_input with null score/vote.
Missing/corrupt/incompatible artifacts, device/dependency failures, tokenizer/model
exceptions, wrong-shaped/nonfinite logits fail with GuardUnavailableError.
No lexical/keyword/regex/dummy score, semantic detector or alternative guard fallback.
Standalone callers must handle explicit errors.

## Deferred Integration

D_G is not enabled in the central default detector factory yet.
Future TECH-INTEGRATION-002 wiring:
1. Add guard enable/artifact/device settings without changing existing defaults.
2. Instantiate one GuardDetector.from_artifact at startup and append to the existing
   BaseDetector sequence, preserving distinct detector identity and all calibrators.
3. Add GuardUnavailableError to the API structured unavailable-error mapping;
   do not expose loader details or raw text.
4. Add synthetic startup/routing/error tests with all existing detectors retained.

No orchestration redesign, fusion, protected experiment, dataset use or threshold
optimization is authorized here. Standalone acceptance is complete.
