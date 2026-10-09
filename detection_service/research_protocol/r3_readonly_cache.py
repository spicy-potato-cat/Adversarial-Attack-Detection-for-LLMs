"""Scoped immutable-file reads; exact bytes verified before use and on exit."""
from contextlib import contextmanager
from pathlib import Path

from detection_service.research_protocol import detector_semantics as files
from detection_service.research_protocol.regime import require


@contextmanager
def verified_reads():
    original_sha, original_json = files.sha, files.read_json
    hashes, objects = {}, {}

    def fingerprint(path):
        stat = path.stat()
        return stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns

    def sha(path):
        path = Path(path).resolve()
        stamp = fingerprint(path)
        if path not in hashes:
            digest = original_sha(path)
            require(fingerprint(path) == stamp, 'R3_FILE_CHANGED_DURING_HASH')
            hashes[path] = (stamp, digest)
        require(hashes[path][0] == stamp, 'R3_READ_ONLY_ARTIFACT_CHANGED')
        return hashes[path][1]

    def read_json(path):
        path = Path(path).resolve()
        sha(path)
        if path not in objects:
            value = original_json(path)
            objects[path] = (value, files.canonical_bytes(value))
        return objects[path][0]

    files.sha, files.read_json = sha, read_json
    try:
        yield
    finally:
        files.sha, files.read_json = original_sha, original_json
        for path, (stamp, expected) in hashes.items():
            require(fingerprint(path) == stamp and original_sha(path) == expected,
                    'R3_READ_ONLY_EXIT_BYTE_DRIFT:' + str(path))
        require(all(files.canonical_bytes(value) == before for value, before in objects.values()),
                'R3_CACHED_JSON_MUTATION')
