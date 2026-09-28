"""Check the portable v0.27 paper, data and Windows-compatible file layout."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hashes", action="store_true", help="Check unchanged release inputs.")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    paper = root / "paper/v0.27"
    failures: list[str] = []
    required = [
        "latex/main.tex",
        "latex/main.pdf",
        "latex/supplement.tex",
        "latex/supplement.pdf",
        "chinese/main_zh.md",
        "chinese/supplement_zh.md",
        "figures/main/RUN_REBUILD.py",
        "figures/supplement/DRAW_SUPPLEMENT.py",
    ]
    for name in required:
        if not (paper / name).is_file():
            failures.append("Missing: " + name)
    for prefix, count in [("", 6), ("Supplementary_", 10)]:
        for number in range(1, count + 1):
            if not (paper / f"latex/figures/AIDRBench_{prefix}Figure_{number}.pdf").is_file():
                failures.append(f"Missing figure: {prefix}{number}")
    for name in ["main", "supplement"]:
        source = paper / f"latex/{name}.tex"
        text = source.read_text(encoding="utf-8")
        if "/home/user/" in text or "/tmp/" in text:
            failures.append(f"Nonportable path in {source}")
        figure_names = re.findall(r"figures/(AIDRBench_[A-Za-z_]*\d+\.pdf)", text)
        expected = 6 if name == "main" else 10
        if len(set(figure_names)) != expected:
            failures.append(f"Incorrect figure count in {source}")
    reading = [
        paper / "chinese/main_zh.md",
        paper / "chinese/supplement_zh.md",
        root / "manuscript/nature_communications_article.md",
        root / "manuscript/supplementary_information.md",
    ]
    for source in reading:
        for target in re.findall(r"!\[[^]]*\]\(([^)]+)\)", source.read_text(encoding="utf-8")):
            if not (source.parent / target).is_file():
                failures.append(f"Broken image: {source.name}: {target}")
    manifest = paper / "MANIFEST.csv"
    with manifest.open(encoding="utf-8", newline="") as stream:
        records = list(csv.DictReader(stream))
    lower_paths: set[str] = set()
    for row in records:
        relative = row["path"]
        if relative.casefold() in lower_paths:
            failures.append("Windows case collision: " + relative)
        lower_paths.add(relative.casefold())
        path = root / relative
        if not path.is_file():
            failures.append("Missing release file: " + relative)
        elif args.hashes and hashlib.sha256(path.read_bytes()).hexdigest() != row["sha256"]:
            failures.append("Changed release file: " + relative)
        if len(relative) > 200 or any(c in relative for c in '<>:"|?*'):
            failures.append("Windows-unfriendly path: " + relative)
    if failures:
        raise SystemExit("\n".join(failures))
    print(
        json.dumps(
            {
                "status": "PASS",
                "main_figures": 6,
                "supplementary_figures": 10,
                "release_files": len(records),
                "hashes_checked": args.hashes,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
