"""Freeze/check TECH-STACK-001 artifacts without model loading or dataset access."""

import argparse
import json
from pathlib import Path
import subprocess

from detection_service import stack_manifest as stack


def git(*args):
    return subprocess.check_output(["git", *args], cwd=stack.ROOT, text=True).strip()


def freeze():
    stack.require(git("rev-parse", "HEAD") == stack.START and git("branch", "--show-current") == "tech/stack-001",
                  "wrong startup HEAD/branch")
    stack.require(not stack.OUT.exists(), "stack output exists; no overwrite")
    pending = git("status", "--porcelain", "--untracked-files=all").splitlines()
    stack.require(all(line[3:].strip() in (*stack.CODE, ".gitattributes")
                      or line.split()[-1] in (*stack.CODE, ".gitattributes") for line in pending), "unrelated pending files")
    manifest = stack.build_manifest()
    report = stack.verify_manifest(manifest)
    content = (json.dumps(manifest, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")
    integrity = stack.integrity_document(manifest, report, stack.hashlib.sha256(content).hexdigest())
    stack.OUT.mkdir()
    for name, data in ((stack.MANIFEST, content), (stack.CHECKSUM, (report["canonical_sha256"] + "\n").encode("ascii")),
                       (stack.INTEGRITY, (json.dumps(integrity, indent=2, sort_keys=True) + "\n").encode("utf-8"))):
        with (stack.OUT / name).open("xb") as handle:
            handle.write(data)
    return stack.check_package()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("freeze", "check"), required=True)
    mode = parser.parse_args().mode
    stack.require(Path.cwd().resolve() == stack.ROOT, "execute from repository root")
    print(json.dumps(freeze() if mode == "freeze" else stack.check_package(), indent=2))


if __name__ == "__main__":
    main()
