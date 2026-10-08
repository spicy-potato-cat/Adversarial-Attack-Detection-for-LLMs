# Frozen-stack portability audit v2

Overall verdict: LOCAL_ARTIFACTS_CRITICAL. The exact 328,492,280-byte D_M-B weights
were rehashed read-only and match 0bb192d2c468530479fa8ec0786f35d8bf5a8287e4ee401a953292d221736844.
Private HF backup remains blocked by automatic approval review. No repository was
created, no upload/download occurred, and no REMOTE_IMMUTABLE success is claimed.

D_S classifier/calibrator and archive code remain exactly reconstructable from
accepted Git history without retraining; no restoration was executed. All v1
artifacts and accepted detector manifests remain unchanged.

D_G hash-binding clarification proves historical environment JSON used CRLF,
whereas the Git blob uses LF. The exact historical hash is recovered by this
serialization change alone, with identical parsed content. This issue has no
scientific impact. The v2 supporting manifest records an exact reconstruction
recipe and keeps historical evidence untouched. Source checkout line-ending
differences still need exact-byte restoration before strict runtime hash checks.

D_G config and tokenizer access at the pinned gated revision is authenticated.
Remote weight LFS SHA256 matches the accepted frozen weight SHA256. Weight retrieval
and fresh-clone loader tests remain deferred until Track A is idle. R3 and verifier
authoritative query counts remain zero; no protected/final samples were accessed.
