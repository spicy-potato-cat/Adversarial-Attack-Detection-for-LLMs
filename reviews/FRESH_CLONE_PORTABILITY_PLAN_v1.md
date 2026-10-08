# Fresh-clone portability plan v1

EXECUTION_DEFERRED_UNTIL_TRACK_A_IDLE. This procedure has not run.

Prerequisites: Track A accepted complete, clean and pushed; lead authorizes Merge
Gate 1 and isolated loader/smoke validation. D_M-B remote backup must first be
private, revision-pinned, downloaded separately and byte-verified. It is currently
BLOCKED_APPROVAL_REVIEW. Never fetch weights from arbitrary local duplicates.

1. Create a new isolated directory under Documents/Codex/work and clone
   https://github.com/spicy-potato-cat/Adversarial-Attack-Detection-for-LLMs.git .
   Fetch and checkout the final authorized integration commit. Verify a clean tree.
2. Verify accepted base 99b012e5b72fbae9273fa73ccc8d84d579a69c83 and preserved commit
   e6b6a2af2a78e2a31aae6d9377378993f678b073 exist in remote history.
3. Read fresh_clone_required_artifacts_v1.json for every exact file, hash and
   remote revision. For D_S archive destinations, extract the specified historical
   Git blobs as binary bytes using Python subprocess.check_output; never PowerShell
   text redirection, retraining, refitting or recalibration. Hash before publication.
4. Restore tracked runtime source files to exact bound Git blob bytes in this
   isolated runtime if Windows checkout normalization changed them. D_G environment
   metadata specifically requires LF-to-CRLF reconstruction. Confirm both identical
   parsed JSON and the historical CRLF SHA before writing. Supporting clarification
   does not silently relax the historical hash contract.
5. Retrieve distilbert/distilgpt2 at 2290a62682d06624634c1f46a6ad5be0f47f38aa
   into the isolated D_S cache location. Verify all snapshot hashes from the manifest.
6. Retrieve D_M-B weights ONLY from the subsequently approved private HF repository
   at its recorded immutable backup revision and path dm_b_v1/model.safetensors.
   Required SHA256: 0bb192d2c468530479fa8ec0786f35d8bf5a8287e4ee401a953292d221736844;
   required size: 328492280 bytes. Abort until the receipt supplies a real revision.
   Retain accepted tokenizer/config Git bytes under artifacts/models/dm_b_v1/transformer;
   base provenance is distilbert/distilroberta-base@fb53ab8802853c8e4fbdbcd0529f21fc6f459b2b.
   Upstream base weights never substitute for the frozen fine-tune.
7. Retrieve meta-llama/Llama-Prompt-Guard-2-22M at
   11614a155199674a0a95e6602d6ab0417b790ed0 using authorized gated access into the
   isolated snapshot location. Weight SHA256:
   5120e30bcd536ce285345d9ec104bea6bd6e8f94365b99a340c764f417ea5fa1.
   Verify every tokenizer/config/license snapshot hash in the manifest.
8. Use an independently authorized environment matching frozen runtime dependencies.
   Do not install into Track A's environment. Resolve known runtime prerequisites
   and representation differences without changing accepted detector semantics.
9. Run the model-free commands in MERGE_GATE_1_PREPARATION_v1.md in separate processes.
   Validate exact loader bindings for all three detectors. Any synthetic-input live
   smoke prediction requires explicit post-idle authorization and must be recorded
   separately from scientific experiment queries. No protected/final population.
10. Record clone commit, environment, immutable remote revisions, all downloaded
    sizes/hashes, exact archive restoration hashes and test receipts. A successful
    hash inventory is insufficient to claim runtime equivalence until loader tests
    pass. Stop on any drift or missing frozen artifact; do not repair by retraining.

Binary-safe Git extraction example (future isolated target only):

```python
import hashlib, subprocess
from pathlib import Path
payload = subprocess.check_output(["git", "show", revision + ":" + git_path], cwd=clone)
assert hashlib.sha256(payload).hexdigest() == expected_sha256
destination = (Path(clone) / required_relative_destination).resolve()
assert destination.is_relative_to(Path(clone).resolve())
destination.parent.mkdir(parents=True, exist_ok=True)
destination.write_bytes(payload)
```

Exact D_S classifier SHA256:
c5e754dc8b6e88b7437e4b81016e8f8ec23d018607d4f4e78906212b2a561157.
Exact D_S calibrator SHA256:
964cea57d98673d2026fb2f0e9d5884aec61a653e726847e0fb6ccbf36e95f23.
Full supporting files and tokenizer hashes are enumerated in the machine-readable
required-artifact manifest. No original-checkout files or raw populations are needed
for this exact-artifact recovery procedure.
