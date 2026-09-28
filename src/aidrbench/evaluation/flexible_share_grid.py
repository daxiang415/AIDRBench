"""Versioned joint work-eligibility/GPU-allocation extension of frozen v2 data."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

import pandas as pd

from aidrbench.data.splits import sha256_file
from aidrbench.evaluation import flexible_share_sensitivity as original

TABLES = [
    "scenario_index.parquet",
    "service_gate.parquet",
    "pi_scenario_frontiers.parquet",
    "pi_boundaries.parquet",
    "fixed_notice_offers.parquet",
    "causal_notice_outcomes.parquet",
]


def design(spec: dict[str, Any]) -> pd.DataFrame:
    """Screen rigid-pool construction, but retain flexible mean overload for testing."""
    prior = pd.read_parquet(Path(spec["prior_results"]) / "service_gate.parquet")
    old = {
        (round(100 * r.workload_fraction), round(100 * r.gpu_pool_fraction)): str(r.case)  # type: ignore[operator, arg-type]
        for r in prior.itertuples()
    }
    prior_screen = pd.read_parquet(Path(spec["prior_results"]) / "structural_screen.parquet")
    old_screen = {
        (round(100 * r.workload_fraction), round(100 * r.gpu_pool_fraction)): str(r.case)  # type: ignore[operator, arg-type]
        for r in prior_screen.itertuples()
    }
    total, work = int(spec["total_gpu_count"]), float(spec["total_work_gpu_h_per_hour"])
    rows = []
    for f in spec["grid_workload_fractions"]:
        for g in spec["grid_gpu_pool_fractions"]:
            key = round(100 * f), round(100 * g)
            flex = round(total * g)
            rigid = total - flex
            assert flex > 0 and rigid > 0
            constructible = work * (1 - f) <= rigid + 1e-12
            name = old.get(key, old_screen.get(key, f"grid_f{key[0]:03d}_g{key[1]:03d}"))
            rows.append(
                {
                    "case": name,
                    "axis": "joint_share_grid",
                    "workload_fraction": float(f),
                    "gpu_pool_fraction": float(g),
                    "flexible_gpu_count": flex,
                    "rigid_gpu_count": rigid,
                    "flexible_work_gpu_h_per_hour": work * f,
                    "rigid_work_gpu_h_per_hour": work * (1 - f),
                    "actual_flexible_pool_utilization": work * f / flex,
                    "required_rigid_utilization": work * (1 - f) / rigid,
                    "structurally_feasible": constructible,
                    "mean_arrivals_exceed_flexible_pool": work * f > flex + 1e-12,
                    "screening_status": "constructible" if constructible else "rigid_pool_overload",
                    "reused_v2_case": key in old,
                    "reused_v2_structural_screen": key in old_screen,
                }
            )
    result = pd.DataFrame(rows)
    if result.duplicated(["workload_fraction", "gpu_pool_fraction"]).any():
        raise ValueError("duplicate grid coordinates")
    return result


def freeze(spec: dict[str, Any], *, workers: int) -> None:
    root = Path(spec["extension_directory"])
    grid = design(spec)
    original._write_table(root / "grid_design.parquet", grid)
    original._write_table(root / "structural_screen.parquet", grid.loc[~grid.structurally_feasible])
    fresh = grid.loc[grid.structurally_feasible & ~grid.reused_v2_case]
    payloads = []
    for row in fresh.to_dict(orient="records"):
        case = original.ShareCase(
            str(row["case"]),
            "joint_share_grid",
            float(row["workload_fraction"]),
            float(row["gpu_pool_fraction"]),
        )
        for role in ["development", "validation"]:
            lower, upper = spec[f"{role}_seeds"]
            for seed in range(lower, upper + 1):
                payloads.append(
                    {
                        "role": role,
                        "seed": seed,
                        "case": asdict(case),
                        "output": str(root),
                        "parent": spec[f"{role}_scenarios"],
                        "total_work": spec["total_work_gpu_h_per_hour"],
                    }
                )
    records = original._parallel(
        original._freeze_worker, payloads, workers=workers, label="joint-grid freeze/gate"
    )
    index = pd.DataFrame(records).sort_values(["case", "role", "episode_seed"])
    original._write_table(root / "scenario_index.parquet", index)
    gate = (
        index.groupby("case", sort=True)
        .agg(
            workload_fraction=("workload_fraction", "first"),
            gpu_pool_fraction=("gpu_pool_fraction", "first"),
            scenario_count=("service_feasible", "size"),
            feasible_count=("service_feasible", "sum"),
            all_service_feasible=("service_feasible", "all"),
            maximum_baseline_deadline_miss_rate=("baseline_deadline_miss_rate", "max"),
            maximum_baseline_terminal_backlog_fraction=(
                "baseline_terminal_backlog_fraction",
                "max",
            ),
            maximum_baseline_pcc_excess_kw=("baseline_pcc_excess_kw", "max"),
        )
        .reset_index()
    )
    original._write_table(root / "service_gate.parquet", gate)
    print(gate.to_string(index=False), flush=True)


def combine(spec: dict[str, Any]) -> None:
    prior, extension, root = [
        Path(spec[k]) for k in ["prior_results", "extension_directory", "output_directory"]
    ]
    for name in TABLES:
        old, new = pd.read_parquet(prior / name), pd.read_parquet(extension / name)
        if set(old["case"]) & set(new["case"]):
            raise ValueError("new cases overlap frozen evidence")
        merged = pd.concat([old, new], ignore_index=True)
        keys = [
            k for k in ["case", "role", "duration_h", "notice_h", "episode_seed"] if k in merged
        ]
        original._write_table(root / name, merged.sort_values(keys))
    for name in ["grid_design.parquet", "structural_screen.parquet"]:
        original._write_table(root / name, pd.read_parquet(extension / name))
    original._write_json(
        root / "combined_provenance.json",
        {
            "prior": str(prior),
            "extension": str(extension),
            "old_rows_reused_without_recomputation": True,
            "prior_table_hashes": {name: sha256_file(prior / name) for name in TABLES},
            "extension_execution_sha256": sha256_file(extension / "execution_inputs.json"),
        },
    )


def run_stage(specification: str | Path, *, stage: str, workers: int) -> None:
    spec = original.load_spec(specification)
    root = Path(spec["extension_directory"])
    root.mkdir(parents=True, exist_ok=True)
    files = [
        Path(specification),
        Path(__file__),
        Path(original.__file__),
        Path(spec["protocol"]),
        Path(spec["controller_config"]),
    ]
    files += [Path(spec["prior_results"]) / name for name in TABLES + ["structural_screen.parquet"]]
    hashes = {str(p): sha256_file(p) for p in files}
    receipt = root / "execution_inputs.json"
    if receipt.exists():
        if json.loads(receipt.read_text())["sha256"] != hashes:
            raise ValueError("joint-grid frozen execution inputs changed")
    else:
        original._write_json(receipt, {"sha256": hashes, "specification": spec})
    stage_spec = {**spec, "output_directory": str(root)}
    if stage == "freeze":
        freeze(spec, workers=workers)
    elif stage == "pi":
        original.pi(stage_spec, workers=workers)
    elif stage == "causal":
        original.causal(stage_spec, workers=workers)
    elif stage == "export":
        from aidrbench.evaluation.flexible_share_grid_analysis import export

        combine(spec)
        export(spec)
    else:
        raise ValueError("unknown joint-grid stage")
