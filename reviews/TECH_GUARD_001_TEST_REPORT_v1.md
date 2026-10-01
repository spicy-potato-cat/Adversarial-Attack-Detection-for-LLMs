# TECH-GUARD-001 Test Report v1

Date: 2026-10-01. Status: BLOCKED; no guard implementation tests or CPU smoke ran.

## Qualification Checks

Existing repository clean at start; isolated tech/guard-001 branch created.
Authoritative Hub model_info resolved three candidate revisions. A pinned
hf_hub_download request for the preferred 22M config.json failed with HTTP 401,
GatedRepoError. Root cause: manual Meta access gate with no configured HF token.
The attempt downloaded no weights. Error details are in qualification.json.

These are metadata/access checks, NOT unit tests, guard predictions or scientific
performance measurements. No synthetic scores or model performance are invented.

## Environment

Existing local interpreter: `.\.local-python\python.exe`.
Python: 3.11.9. OS: Windows, build 26200. Logical CPUs: 16.
Torch: 2.6.0 CPU build; CUDA unavailable to this interpreter.
Transformers: 4.49.0. HF Hub: 0.36.2. tokenizers: 0.21.4.
safetensors: 0.8.0. NumPy: 2.1.3. pytest: 8.3.4.
No package installation or upgrade occurred. Environment evidence: environment.json.

## Model-Access Recheck

After the Commander configures an approved Hugging Face token locally, recheck
the exact proposed artifact from the repository root without exposing the token:

```powershell
$env:HF_HOME = Join-Path (Get-Location).Path '.cache\huggingface'
$env:HUGGINGFACE_HUB_CACHE = Join-Path $env:HF_HOME 'hub'
$env:TEMP = Join-Path (Get-Location).Path '.cache\tmp'
$env:TMP = $env:TEMP
.\.local-python\python.exe -c "from huggingface_hub import hf_hub_download; hf_hub_download('meta-llama/Llama-Prompt-Guard-2-22M', 'config.json', revision='11614a155199674a0a95e6602d6ab0417b790ed0', local_dir='detection_service/.model-cache/dg_v1/qualification')"
```

This only rechecks access. It is NOT the missing real-model smoke command.
No authenticated access form, privacy-information submission or license acceptance
was performed on the Commander's behalf.

## Unexecuted Acceptance Checks

Unit-test command: NOT AVAILABLE; implementation stopped before code creation.
Unit tests passed/failed/skipped: NOT RUN, not a fabricated zero-failure PASS.
Real-model smoke command/result: NOT AVAILABLE / BLOCKED BY ACCESS.
Determinism, model reuse, long-input scanning, tail coverage, probability bounds,
DetectorResult runtime compatibility and no-fallback failure path: NOT VERIFIED.
Central service integration: DEFERRED.

Project development data accessed: NO. CALIBRATION accessed: NO.
VALIDATION accessed: NO. Protected data accessed: NO. E1-E10 executed: NO.
No existing semantic tests were modified or weakened. Running the project-wide
suite would include development-data access, so it was not run in this phase.
