"""Verify an extracted figure-recovery package using Python's standard library."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath


def verify(directory: Path) -> dict[str, object]:
    root = directory.resolve()
    entries = (root / "CHECKSUMS_SHA256.txt").read_text(encoding="utf-8").splitlines()
    checked = set()
    for line in entries:
        digest, name = line.split(maxsplit=1)
        relative = PurePosixPath(name)
        if relative.is_absolute() or ".." in relative.parts or name in checked:
            raise ValueError(f"unsafe or duplicate checksum path: {name}")
        file = (root / name).resolve()
        file.relative_to(root)
        if hashlib.sha256(file.read_bytes()).hexdigest() != digest:
            raise ValueError(f"file checksum mismatch: {name}")
        checked.add(name)
    return {"verified_files": len(checked), "status": "pass", "scope": "listed original files"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    print(json.dumps(verify(parser.parse_args().directory)))
