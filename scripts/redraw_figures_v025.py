"""Redraw the eleven v0.25 figures using only included CSV/JSON summaries."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "results/redraw_v025")
    parser.add_argument(
        "--verify",
        action="store_true",
        help=(
            "Also compare all PNGs with the frozen v0.25 artwork; omit wh"
            "en intentionally editing data or style."
        ),
    )
    args = parser.parse_args()
    output = args.output.resolve()
    data = ROOT / "manuscript/source_data"
    base = data / "nature_workload_composition_v1"
    scripts = ROOT / "scripts/figures_v025"
    # The early stages draw some historical panels. The last stage replaces
    # those panels, using the same final rendering order as the full v14 package.
    stages = [
        ("plot_results.py", ["--data", base, "--through", "5"]),
        ("plot_supplement.py", ["--data", base, "--through", "2"]),
        (
            "plot_mechanisms.py",
            [
                "--data",
                data / "nature_commitment_mechanisms_v1",
                "--previous-data",
                data / "nature_operating_tradeoffs_v1",
            ],
        ),
        ("plot_narrative.py", ["--data", data / "nature_commitment_narrative_v1"]),
    ]
    for filename, options in stages:
        subprocess.run(
            [sys.executable, str(scripts / filename), *map(str, options), "--output", str(output)],
            check=True,
        )

    rows = []
    reference = ROOT / "docs/figures/commitment_narrative_v1/artwork"
    for prefix, count in [("AIDRBench_Figure_", 6), ("AIDRBench_Supplementary_Figure_", 5)]:
        for n in range(1, count + 1):
            name = f"{prefix}{n}"
            exports = {}
            for ext in ["png", "pdf", "svg", "tiff"]:
                path = output / f"{name}.{ext}"
                if not path.is_file():
                    raise RuntimeError(f"Missing expected output: {path}")
                exports[ext] = {"bytes": path.stat().st_size, "sha256": digest(path)}
            matches = exports["png"]["sha256"] == digest(reference / f"{name}.png")
            if args.verify and not matches:
                raise RuntimeError(f"{name}.png differs from the frozen artwork")
            rows.append({"figure": name, "png_matches_reference": matches, "outputs": exports})
    report = {
        "status": "PASS",
        "manuscript": "v0.25",
        "figures": len(rows),
        "new_simulations": 0,
        "all_pngs_match_reference": all(r["png_matches_reference"] for r in rows),
        "comparisons": rows,
    }
    (output / "redraw_validation.json").write_text(json.dumps(report, indent=2) + "\n")
    print(f"Recreated all {len(rows)} figures in {output}")
    if args.verify:
        print("All eleven PNG hashes match the checked v0.25 artwork.")


if __name__ == "__main__":
    main()
