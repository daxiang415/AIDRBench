"""Export direct Figure 1 panel rows from frozen evidence; never solve or fit."""

from __future__ import annotations

import csv
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "docs/figure1_revision/v1"
SENSITIVITY = ROOT / "manuscript/source_data/nature_flexible_share_v2"
MAINLINE = ROOT / "manuscript/source_data/nature_mainline_v1"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def write(name: str, rows: list[dict[str, object]]) -> None:
    with (PACKAGE / "data" / name).open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    copied = {}
    sensitivity_manifest = json.loads((SENSITIVITY / "source_data_manifest.json").read_text())
    mainline_manifest = json.loads((MAINLINE / "source_data_manifest.json").read_text())
    for filename, metadata in sensitivity_manifest["files"].items():
        assert sha(SENSITIVITY / filename) == metadata["sha256"], filename
        assert len(read(SENSITIVITY / filename)) == metadata["rows"], filename
    for name in ["fig1_fig2_pi_firm_boundaries.csv", "fig1_calibration_run_means.csv"]:
        metadata = next(t for t in mainline_manifest["tables"] if t["output"] == name)
        assert sha(MAINLINE / name) == metadata["output_sha256"]
        assert len(read(MAINLINE / name)) == metadata["row_count"]
    for folder, files in [
        ("sensitivity_v2", sorted(SENSITIVITY.glob("*"))),
        (
            "reference",
            [
                MAINLINE / "fig1_fig2_pi_firm_boundaries.csv",
                MAINLINE / "fig1_calibration_run_means.csv",
                MAINLINE / "source_data_manifest.json",
            ],
        ),
    ]:
        target = PACKAGE / "source_data" / folder
        target.mkdir(parents=True, exist_ok=True)
        for path in files:
            if path.is_file():
                shutil.copy2(path, target / path.name)
                copied[str((target / path.name).relative_to(PACKAGE))] = {
                    "original": str(path.relative_to(ROOT)),
                    "sha256": sha(path),
                }

    grid = read(SENSITIVITY / "plot_pi_capacity_complete_grid.csv")

    def direct(row: dict[str, str], x: float) -> dict[str, object]:
        assert row["all_service_feasible"] == "True"
        assert row["role"] == "validation"
        assert row["scenario_count_y"] == "100"
        return {
            "case": row["case"],
            "x_percent": x,
            "y_kw": row["perfect_information_firm_capacity_kw"],
            "work_share_percent": float(row["workload_fraction"]) * 100,
            "flexible_gpu_percent": float(row["gpu_pool_fraction"]) * 100,
            "duration_h": row["duration_h"],
            "n_scenarios": row["scenario_count_y"],
            "reliability_target": row["reliability_target"],
            "confidence_level": row["confidence_level"],
            "tolerance_rank": row["tolerance_order_statistic_rank"],
            "ensemble": row["role"],
            "point_status": row["point_status"],
        }

    selected_a = sorted(
        [r for r in grid if r["case"].startswith("work_low_") and r["duration_h"] == "4"],
        key=lambda r: float(r["workload_fraction"]),
    )
    assert len(selected_a) == 6
    write(
        "panel_a_work_share.csv",
        [direct(r, float(r["workload_fraction"]) * 100) for r in selected_a],
    )
    selected_b = sorted(
        [
            r
            for r in grid
            if float(r["workload_fraction"]) == 0.6
            and r["duration_h"] == "4"
            and float(r["gpu_pool_fraction"]) in [0.4, 0.6]
        ],
        key=lambda r: float(r["gpu_pool_fraction"]),
    )
    assert len(selected_b) == 2
    write(
        "panel_b_gpu_allocation.csv",
        [direct(r, float(r["gpu_pool_fraction"]) * 100) for r in selected_b],
    )
    reference = sorted(
        [
            r
            for r in read(MAINLINE / "fig1_fig2_pi_firm_boundaries.csv")
            if float(r["reliability_target"]) == 0.95
        ],
        key=lambda r: float(r["duration_h"]),
    )
    assert len(reference) == 6
    write(
        "panel_c_reference_duration.csv",
        [
            {
                "duration_h": r["duration_h"],
                "pi_lower_bound_kw": r["perfect_information_firm_capacity_kw"],
                "nominal_comparator_kw": r["nominal_flexibility_kw"],
                "reference_peak_kw": r["reference_mix_operating_peak_kw"],
                "gap_below_nominal_percent": 100
                * (
                    1
                    - float(r["perfect_information_firm_capacity_kw"])
                    / float(r["nominal_flexibility_kw"])
                ),
                "n_scenarios": r["scenario_count"],
                "reliability_target": r["reliability_target"],
                "confidence_level": r["confidence_level"],
                "tolerance_rank": r["tolerance_order_statistic_rank"],
                "ensemble": "development",
            }
            for r in reference
        ],
    )
    calibration = read(MAINLINE / "fig1_calibration_run_means.csv")
    assert len(calibration) == 30
    direct_power = []
    for r in calibration:
        category = ("Train" if r["mode"] == "training" else "Infer") + " " + r["gpu_count"]
        same_run = [
            v for v in calibration if all(v[k] == r[k] for k in ["mode", "gpu_count", "repeat"])
        ]
        direct_power.append(
            {
                **r,
                "category": category,
                "held_out": int(r["repeat"]) == 3,
                "run_mean_power_w": sum(float(v["mean_power_w"]) for v in same_run) / len(same_run),
            }
        )
    write("panel_d_power.csv", direct_power)
    manifest = {
        "status": "web_gpt6_input_ready_local_review_only",
        "scope": "Figure 1 opening Results revision; no new simulations",
        "source_files": copied,
        "panel_files": {
            str(p.relative_to(PACKAGE)): {"sha256": sha(p), "rows": len(read(p))}
            for p in sorted((PACKAGE / "data").glob("*.csv"))
        },
        "selection": {
            "a": "6/132 complete-grid rows: six work_low cases, H=4",
            "b": "2/132 complete-grid rows: work=60%, GPU=40% or 60%, H=4",
            "c": "6/18 reference rows: q=0.95, all six evaluated durations",
            "d": "30/30 board observations; 12 independent runs; no sampling",
            "full_evidence": "All 15 sensitivity CSVs and both full reference tables retained",
        },
    }
    (PACKAGE / "input_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest["panel_files"], indent=2))


if __name__ == "__main__":
    main()
