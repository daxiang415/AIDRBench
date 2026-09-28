"""Export joint-grid evidence and the prospectively specified paired contrasts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from aidrbench.data.splits import sha256_file
from aidrbench.evaluation import flexible_share_sensitivity as original
from aidrbench.evaluation.flexible_share_grid import design


def contrast_plan(
    spec: dict[str, Any], grid: pd.DataFrame, feasible: set[str]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Use service gates only to select applicable contrasts, never effect sizes."""
    records: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    seen = set()
    names = {
        (
            round(100 * float(str(r.workload_fraction))),
            round(100 * float(str(r.gpu_pool_fraction))),
        ): str(r.case)
        for r in grid.itertuples()
    }
    fs = [round(100 * f) for f in spec["grid_workload_fractions"]]
    gs = [round(100 * g) for g in spec["grid_gpu_pool_fractions"]]
    gref = round(100 * spec["grid_gpu_comparison_reference"])

    def add(purpose: str, label: str, terms: dict[str, int]) -> None:
        if not set(terms).issubset(feasible):
            skipped.append(
                {
                    "comparison_purpose": purpose,
                    "label": label,
                    "missing_service_feasible_cases": ";".join(sorted(set(terms) - feasible)),
                }
            )
            return
        key = tuple(sorted(terms.items()))
        if key in seen:
            return
        seen.add(key)
        records.append({"comparison_purpose": purpose, "label": label, "terms": terms})

    for case in sorted(feasible - {"reference"}):
        add("original_reference", f"{case} minus reference", {case: 1, "reference": -1})
    base = names[(fs[0], gref)]
    for f in fs[1:]:
        add(
            "within_g040_workload",
            f"work {f}% minus {fs[0]}%, GPU {gref}%",
            {names[(f, gref)]: 1, base: -1},
        )
    for f in fs:
        for g in gs:
            if g != gref:
                add(
                    "within_workload_gpu_allocation",
                    f"GPU {g}% minus {gref}%, work {f}%",
                    {names[(f, g)]: 1, names[(f, gref)]: -1},
                )
    for g in gs:
        for lo, hi in zip(fs[:-1], fs[1:], strict=True):
            add(
                "adjacent_work_share",
                f"work {hi}% minus {lo}%, GPU {g}%",
                {names[(hi, g)]: 1, names[(lo, g)]: -1},
            )
    for flo, fhi in zip(fs[:-1], fs[1:], strict=True):
        for glo, ghi in zip(gs[:-1], gs[1:], strict=True):
            add(
                "adjacent_grid_interaction",
                f"work {flo}-{fhi}%, GPU {glo}-{ghi}%",
                {
                    names[(fhi, ghi)]: 1,
                    names[(flo, ghi)]: -1,
                    names[(fhi, glo)]: -1,
                    names[(flo, glo)]: 1,
                },
            )
    return records, skipped


def complete_grid(spec: dict[str, Any]) -> pd.DataFrame:
    root = Path(spec["output_directory"])
    gate = pd.read_parquet(root / "service_gate.parquet")
    index = pd.read_parquet(root / "scenario_index.parquet")
    bounds = pd.read_parquet(root / "pi_boundaries.parquet")
    grid = design(spec)
    parameters = index.drop_duplicates("case")[
        [
            "case",
            "flexible_gpu_count",
            "rigid_gpu_count",
            "flexible_work_gpu_h_per_hour",
            "rigid_work_gpu_h_per_hour",
            "actual_flexible_pool_utilization",
            "rigid_gpu_utilization",
        ]
    ]
    base = gate.merge(parameters, on="case", validate="one_to_one")
    base = base.rename(columns={"scenario_count": "baseline_scenario_count"})
    base["constructible"] = True
    base["mean_arrivals_exceed_flexible_pool"] = base.actual_flexible_pool_utilization > 1 + 1e-12
    base["point_status"] = "finite_horizon_service_feasible"
    base.loc[base.mean_arrivals_exceed_flexible_pool, "point_status"] = (
        "mean_overload_requires_clearance_tail"
    )
    base.loc[~base.all_service_feasible, "point_status"] = (
        "baseline_service_failed_no_capacity_reported"
    )
    base = base.merge(pd.DataFrame({"duration_h": spec["pi_durations_h"]}), how="cross")
    selected = bounds.loc[bounds.role == "validation"].copy()
    base = base.merge(
        selected,
        on=["case", "duration_h", "workload_fraction", "gpu_pool_fraction"],
        how="left",
        validate="one_to_one",
    )
    failure = grid.loc[~grid.structurally_feasible].copy()
    failure["constructible"] = False
    failure["all_service_feasible"] = False
    failure["baseline_scenario_count"] = 0
    failure["point_status"] = "rigid_pool_overload_not_simulated"
    failure = failure.merge(pd.DataFrame({"duration_h": spec["pi_durations_h"]}), how="cross")
    complete = pd.concat([base, failure], ignore_index=True)
    complete["in_primary_grid"] = complete.case.isin(grid.case)
    complete["work_share_percent"] = complete.workload_fraction * 100
    complete["flexible_gpu_percent"] = complete.gpu_pool_fraction * 100
    complete["y_kw"] = complete.perfect_information_firm_capacity_kw
    return complete.sort_values(["workload_fraction", "gpu_pool_fraction", "duration_h"])


def export(spec: dict[str, Any]) -> None:
    from scipy.stats import t  # type: ignore[import-untyped]

    original.export(spec)
    root, source = Path(spec["output_directory"]), Path(spec["source_data_directory"])
    pi = pd.read_parquet(root / "pi_scenario_frontiers.parquet")
    pi = pi.loc[pi.role == "validation"]
    grid = design(spec)
    plan, skipped = contrast_plan(spec, grid, set(pi.case))
    family_size = len(plan) * len(spec["pi_durations_h"])
    contrasts = []
    for duration in spec["pi_durations_h"]:
        pivot = pi.loc[pi.duration_h == duration].pivot(
            index="episode_seed", columns="case", values="perfect_information_capacity_kw"
        )
        if pivot.isna().any().any() or len(pivot) != 100:
            raise ValueError("paired grid inference requires the same 100 complete scenarios")
        for number, item in enumerate(plan):
            difference = sum(
                coefficient * pivot[case] for case, coefficient in item["terms"].items()
            )
            values = np.asarray(difference, dtype=float)
            mean = float(np.mean(values))
            half = float(t.ppf(1 - 0.05 / (2 * family_size), 99) * np.std(values, ddof=1) / 10)
            contrasts.append(
                {
                    "contrast_id": f"contrast_{number:03d}_h{duration}",
                    "comparison_purpose": item["comparison_purpose"],
                    "label": item["label"],
                    "term_coefficients_json": json.dumps(item["terms"], sort_keys=True),
                    "duration_h": duration,
                    "n_paired": 100,
                    "family_size": family_size,
                    "mean_capacity_difference_kw": mean,
                    "simultaneous_ci_low_kw": mean - half,
                    "simultaneous_ci_high_kw": mean + half,
                    "method": "paired_t_bonferroni_95_percent",
                }
            )
    full = complete_grid(spec)
    primary = full.loc[full.in_primary_grid].copy()
    ranges = []
    for (f, duration), group in primary.groupby(["work_share_percent", "duration_h"]):
        valid = group.loc[group.all_service_feasible]
        if valid.empty:
            continue
        minimum, maximum = float(valid.y_kw.min()), float(valid.y_kw.max())
        ranges.append(
            {
                "work_share_percent": f,
                "duration_h": duration,
                "evaluated_gpu_allocations": len(group),
                "service_feasible_allocations": len(valid),
                "minimum_reported_lower_bound_kw": minimum,
                "maximum_reported_lower_bound_kw": maximum,
                "gpu_percent_at_observed_minimum": ";".join(
                    str(v)
                    for v in valid.loc[
                        np.isclose(valid.y_kw, minimum, atol=1e-9, rtol=0), "flexible_gpu_percent"
                    ]
                ),
                "gpu_percent_at_observed_maximum": ";".join(
                    str(v)
                    for v in valid.loc[
                        np.isclose(valid.y_kw, maximum, atol=1e-9, rtol=0), "flexible_gpu_percent"
                    ]
                ),
                "interpretation": (
                    "observed_discrete_grid_extrema_not_an_optimised_allocation_or_certificate"
                ),
            }
        )
    tables = {
        "grid_design": grid,
        "structural_feasibility_screen": grid.loc[~grid.structurally_feasible],
        "plot_pi_capacity_complete_grid": full,
        "plot_joint_share_grid": primary,
        "joint_grid_capacity_ranges": pd.DataFrame(ranges),
        "pi_paired_contrasts": pd.DataFrame(contrasts),
        "pi_contrast_not_applicable": pd.DataFrame(skipped),
    }
    manifest_path = source / "source_data_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    for name, frame in tables.items():
        path = source / f"{name}.csv"
        frame.to_csv(path, index=False, float_format="%.12g")
        manifest["files"][path.name] = {"rows": len(frame), "sha256": sha256_file(path)}
    manifest["grid_analysis_code_sha256"] = sha256_file(__file__)
    manifest["extension_provenance_sha256"] = sha256_file(root / "combined_provenance.json")
    manifest["pi_contrast_family_size"] = family_size
    original._write_json(manifest_path, manifest)
    original._write_json(
        root / "export_summary.json",
        {
            "primary_grid_points": len(grid),
            "complete_points_with_legacy": full.case.nunique(),
            "primary_service_feasible": int(
                primary.loc[primary.duration_h == 4].all_service_feasible.sum()
            ),
            "primary_structural_failures": int((~grid.structurally_feasible).sum()),
            "primary_baseline_service_failures": int(
                (
                    primary.loc[primary.duration_h == 4, "point_status"]
                    == "baseline_service_failed_no_capacity_reported"
                ).sum()
            ),
            "pi_contrast_family_size": family_size,
            "contrast_categories": pd.DataFrame(contrasts)
            .comparison_purpose.value_counts()
            .to_dict(),
            "source_data_manifest_sha256": sha256_file(manifest_path),
        },
    )
    print(json.dumps({name: len(frame) for name, frame in tables.items()}, indent=2), flush=True)
