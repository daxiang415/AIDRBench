"""Export complete joint-grid data and direct Figure 1 inputs without new analysis."""

from __future__ import annotations

import csv
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "docs/figure1_revision/v2"
SOURCE = ROOT / "manuscript/source_data/nature_flexible_share_v3"
OLD = ROOT / "docs/figure1_revision/v1"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    (PACKAGE / "data").mkdir(parents=True, exist_ok=True)
    copied = {}
    manifest = json.loads((SOURCE / "source_data_manifest.json").read_text())
    for name, info in manifest["files"].items():
        assert sha(SOURCE / name) == info["sha256"]
    for folder, files in [
        ("sensitivity_v3", list(SOURCE.glob("*"))),
        ("reference", list((OLD / "source_data/reference").glob("*"))),
    ]:
        target = PACKAGE / "source_data" / folder
        target.mkdir(parents=True, exist_ok=True)
        for path in files:
            if path.is_file():
                dest = target / path.name
                shutil.copy2(path, dest)
                copied[str(dest.relative_to(PACKAGE))] = {
                    "original": str(path.relative_to(ROOT)),
                    "sha256": sha(dest),
                }
    with (SOURCE / "plot_joint_share_grid.csv").open() as handle:
        grid = list(csv.DictReader(handle))
    status = [row for row in grid if float(row["duration_h"]) == 4]
    capacity = [row for row in status if row["all_service_feasible"] == "True"]
    assert len(status) == 54 and len(capacity) == 23
    for name, rows in [
        ("panel_a_joint_capacity.csv", capacity),
        ("panel_b_grid_status.csv", status),
    ]:
        with (PACKAGE / "data" / name).open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    for name in ["panel_c_reference_duration.csv", "panel_d_power.csv"]:
        shutil.copy2(OLD / "data" / name, PACKAGE / "data" / name)
    panel_files = {}
    for path in sorted((PACKAGE / "data").glob("*.csv")):
        with path.open() as handle:
            rows = len(list(csv.DictReader(handle)))
        panel_files[str(path.relative_to(PACKAGE))] = {"sha256": sha(path), "rows": rows}
    output = {
        "status": "web_gpt6_input_ready_local_review_only",
        "source_files": copied,
        "panel_files": panel_files,
        "selection": {
            "a": (
                "All 23 service-feasible grid configurations at H=4; "
                "the mean-overload point is retained separately."
            ),
            "b": (
                "All 54 statuses supplied; plot the 23 service-feasible positions. "
                "Missing capacity is not zero."
            ),
            "c": "Six original development duration bounds at q=0.95, unchanged from v1.",
            "d": "All 30 board observations in 12 independent runs, unchanged from v1.",
            "full_evidence": (
                "Every v3 table, all durations, all old/new cases and failures retained."
            ),
        },
    }
    (PACKAGE / "input_manifest.json").write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps(panel_files, indent=2))


if __name__ == "__main__":
    main()
