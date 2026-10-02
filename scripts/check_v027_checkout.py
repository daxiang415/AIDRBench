"""Verify the portable paper checkout without changing the original delivery receipt."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from pathlib import Path
from typing import Any


def git_blob(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def within(root: Path, relative: str) -> Path:
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError(f"Path escapes checkout: {relative}")
    return path


def verify_manifest(root: Path, hashes: bool) -> tuple[list[str], int]:
    failures: list[str] = []
    manifest = root / "paper/v0.27/MANIFEST.csv"
    layout_path = root / "docs/checkout-layout.json"
    layout: dict[str, Any] = json.loads(layout_path.read_text(encoding="utf-8"))
    if git_blob(manifest.read_bytes()) != layout["baseline_manifest_git_blob"]:
        failures.append("The original delivery manifest has changed.")
    with manifest.open(encoding="utf-8", newline="") as stream:
        records = list(csv.DictReader(stream))
    retired = set(layout.get("retired_files", []))
    prefixes = tuple(layout.get("retired_prefixes", []))
    renamed = layout.get("renamed_files", {})
    updated = layout.get("updated_git_blobs", {})
    active: dict[str, dict[str, str]] = {}
    for row in records:
        old = row["path"]
        if old in retired or (prefixes and old.startswith(prefixes)):
            if within(root, old).exists():
                failures.append("Retired reading copy still present: " + old)
            continue
        relative = renamed.get(old, old)
        if relative in active:
            failures.append("Duplicate manifest destination: " + relative)
        active[relative] = row
    for relative in updated:
        active.setdefault(relative, {})
    lower_paths: set[str] = set()
    for relative, row in active.items():
        if relative.casefold() in lower_paths:
            failures.append("Windows case collision: " + relative)
        lower_paths.add(relative.casefold())
        if len(relative) > 200 or any(c in relative for c in '<>:"|?*'):
            failures.append("Windows-unfriendly path: " + relative)
        path = within(root, relative)
        if not path.is_file():
            failures.append("Missing release file: " + relative)
        elif hashes:
            data = path.read_bytes()
            if relative in updated:
                if git_blob(data) != updated[relative]:
                    failures.append("Changed maintained file: " + relative)
            elif hashlib.sha256(data).hexdigest() != row["sha256"]:
                failures.append("Changed release file: " + relative)
    for old, new in renamed.items():
        if within(root, old).exists():
            failures.append("Old renamed path still present: " + old)
        if new not in active:
            failures.append("Rename is not bound to the original manifest: " + new)
    return failures, len(active)


def verify_paper(root: Path) -> list[str]:
    paper = root / "paper/v0.27"
    failures: list[str] = []
    for name in (
        "latex/main.tex", "latex/main.pdf", "latex/supplement.tex", "latex/supplement.pdf",
        "figures/main/RUN_REBUILD.py", "figures/supplement/DRAW_SUPPLEMENT.py",
    ):
        if not (paper / name).is_file():
            failures.append("Missing: " + name)
    for prefix, count in (("", 6), ("Supplementary_", 10)):
        for number in range(1, count + 1):
            if not (paper / f"latex/figures/AIDRBench_{prefix}Figure_{number}.pdf").is_file():
                failures.append(f"Missing figure: {prefix}{number}")
    for name in ("main", "supplement"):
        source = paper / f"latex/{name}.tex"
        if not source.is_file():
            continue
        text = source.read_text(encoding="utf-8")
        if "/home/user/" in text or "/tmp/" in text:
            failures.append(f"Nonportable path in {source}")
        figures = re.findall(r"figures/(AIDRBench_[A-Za-z_]*\d+\.pdf)", text)
        if len(set(figures)) != (6 if name == "main" else 10):
            failures.append(f"Incorrect figure count in {source}")
    for name in ("nature_communications_article.md", "supplementary_information.md"):
        source = root / "manuscript" / name
        if not source.is_file():
            failures.append("Missing reading copy: " + name)
            continue
        for target in re.findall(r"!\[[^]]*\]\(([^)]+)\)", source.read_text(encoding="utf-8")):
            if not (source.parent / target).is_file():
                failures.append(f"Broken image: {source.name}: {target}")
    return failures


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--hashes", action="store_true", help="Verify scientific and maintained-file hashes."
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    try:
        failures, count = verify_manifest(root, args.hashes)
        failures.extend(verify_paper(root))
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise SystemExit(f"Checkout verification failed: {error}") from error
    if failures:
        raise SystemExit("\n".join(failures))
    print(json.dumps({"status": "PASS", "main_figures": 6, "supplementary_figures": 10,
                      "release_files": count, "hashes_checked": args.hashes}, indent=2))


if __name__ == "__main__":
    main()
