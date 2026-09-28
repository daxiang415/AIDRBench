"""Extend the preserved share study to a common-pool 10--60% workload curve."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from aidrbench.data.splits import sha256_file
from aidrbench.evaluation import flexible_share_sensitivity as original


def new_cases(spec: dict[str, Any]) -> list[original.ShareCase]:
    return [
        original.ShareCase(
            f"work_low_{round(100 * f):03d}",
            "workload_g040",
            float(f),
            float(spec["new_gpu_pool_fraction"]),
        )
        for f in spec["new_workload_fractions"]
    ]


def structural_screen(spec: dict[str, Any]) -> pd.DataFrame:
    total = int(spec["total_gpu_count"])
    g = float(spec["reference_gpu_pool_fraction"])
    rigid = total - round(total * g)
    rows = []
    for f in spec["rigid_screen_workload_fractions"]:
        demand = float(spec["total_work_gpu_h_per_hour"]) * (1 - f)
        rows.append(
            {
                "case": f"work_{round(100 * f):03d}",
                "workload_fraction": f,
                "gpu_pool_fraction": g,
                "rigid_gpu_count": rigid,
                "rigid_work_gpu_h_per_hour": demand,
                "required_rigid_utilization": demand / rigid,
                "structurally_feasible": demand <= rigid,
                "screening_status": "rigid_pool_overload" if demand > rigid else "constructible",
                "scenario_count": 0,
            }
        )
    return pd.DataFrame(rows)


def freeze_extension(spec: dict[str, Any], *, workers: int) -> None:
    root = Path(spec["extension_directory"])
    screen = structural_screen(spec)
    original._write_table(root / "structural_screen.parquet", screen)
    payloads = []
    for role in ["development", "validation"]:
        lower, upper = spec[f"{role}_seeds"]
        for case in new_cases(spec):
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
    rows = original._parallel(
        original._freeze_worker, payloads, workers=workers, label="low-share freeze/gate"
    )
    frame = pd.DataFrame(rows).sort_values(["case", "role", "episode_seed"])
    original._write_table(root / "scenario_index.parquet", frame)
    gate = (
        frame.groupby("case", sort=True)
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
    print(screen.to_string(index=False), flush=True)
    print(gate.to_string(index=False), flush=True)


def combine(spec: dict[str, Any]) -> None:
    prior, extension, root = [
        Path(spec[k]) for k in ("prior_results", "extension_directory", "output_directory")
    ]
    for filename in [
        "scenario_index.parquet",
        "service_gate.parquet",
        "pi_scenario_frontiers.parquet",
        "pi_boundaries.parquet",
        "fixed_notice_offers.parquet",
        "causal_notice_outcomes.parquet",
    ]:
        old, new = pd.read_parquet(prior / filename), pd.read_parquet(extension / filename)
        if set(old["case"]) & set(new["case"]):
            raise ValueError("extension case names overlap prior evidence")
        merged = pd.concat([old, new], ignore_index=True)
        sort = [
            k for k in ["case", "role", "duration_h", "notice_h", "episode_seed"] if k in merged
        ]
        original._write_table(root / filename, merged.sort_values(sort))
    original._write_table(root / "structural_screen.parquet", structural_screen(spec))
    original._write_json(
        root / "combined_provenance.json",
        {
            "prior": str(prior),
            "extension": str(extension),
            "prior_execution_sha256": sha256_file(prior / "execution_inputs.json"),
            "extension_execution_sha256": sha256_file(extension / "execution_inputs.json"),
            "original_rows_reused_without_recomputation": True,
        },
    )


def export_combined(spec: dict[str, Any]) -> None:
    from scipy.stats import t  # type: ignore[import-untyped]

    original.export(spec)
    root, source = Path(spec["output_directory"]), Path(spec["source_data_directory"])
    pi = pd.read_parquet(root / "pi_scenario_frontiers.parquet")
    pi = pi.loc[pi["role"] == "validation"]
    primary = spec["primary_pi_reference_case"]
    feasible = set(pi["case"])
    if primary not in feasible:
        raise ValueError("primary curve reference failed; revise protocol before inference")
    comparisons = [
        (case, "reference", "original_reference") for case in sorted(feasible - {"reference"})
    ]
    comparisons += [
        (case.name, primary, "within_g040_workload")
        for case in new_cases(spec)
        if case.name in feasible and case.name != primary
    ]
    family_size = len(comparisons) * len(spec["pi_durations_h"])
    records = []
    for case, reference, purpose in comparisons:
        for duration in spec["pi_durations_h"]:
            left = pi.loc[(pi["case"] == case) & (pi["duration_h"] == duration)]
            right = pi.loc[(pi["case"] == reference) & (pi["duration_h"] == duration)]
            pair = left.merge(
                right, on="episode_seed", suffixes=("", "_ref"), validate="one_to_one"
            )
            difference = (
                pair["perfect_information_capacity_kw"]
                - pair["perfect_information_capacity_kw_ref"]
            ).to_numpy()
            if len(difference) != 100:
                raise ValueError("incomplete paired contrast")
            mean = float(difference.mean())
            half = float(t.ppf(1 - 0.05 / (2 * family_size), 99) * np.std(difference, ddof=1) / 10)
            records.append(
                {
                    "case": case,
                    "reference_case": reference,
                    "comparison_purpose": purpose,
                    "duration_h": duration,
                    "n_paired": 100,
                    "family_size": family_size,
                    "mean_capacity_difference_kw": mean,
                    "simultaneous_ci_low_kw": mean - half,
                    "simultaneous_ci_high_kw": mean + half,
                    "method": "paired_t_bonferroni_95_percent",
                }
            )
    tables = {
        "pi_paired_contrasts": pd.DataFrame(records),
        "structural_feasibility_screen": structural_screen(spec),
    }
    manifest_path = source / "source_data_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    for name, table in tables.items():
        path = source / f"{name}.csv"
        table.to_csv(path, index=False, float_format="%.12g")
        manifest["files"][path.name] = {"rows": len(table), "sha256": sha256_file(path)}
    manifest["extension_provenance_sha256"] = sha256_file(root / "combined_provenance.json")
    original._write_json(manifest_path, manifest)


def run_stage(specification: str | Path, *, stage: str, workers: int) -> None:
    spec = original.load_spec(specification)
    extension = Path(spec["extension_directory"])
    extension.mkdir(parents=True, exist_ok=True)
    files = [
        Path(specification),
        Path(__file__),
        Path(original.__file__),
        Path(spec["protocol"]),
        Path(spec["controller_config"]),
    ]
    prior = Path(spec["prior_results"])
    files += [
        prior / name
        for name in [
            "execution_inputs.json",
            "scenario_index.parquet",
            "service_gate.parquet",
            "pi_scenario_frontiers.parquet",
            "pi_boundaries.parquet",
            "fixed_notice_offers.parquet",
            "causal_notice_outcomes.parquet",
        ]
    ]
    fingerprint = {str(p): sha256_file(p) for p in files}
    receipt = extension / "execution_inputs.json"
    if receipt.exists():
        if json.loads(receipt.read_text())["sha256"] != fingerprint:
            raise ValueError("frozen extension inputs changed")
    else:
        original._write_json(receipt, {"sha256": fingerprint, "specification": spec})
    stage_spec = {**spec, "output_directory": str(extension)}
    if stage == "freeze":
        freeze_extension(spec, workers=workers)
    elif stage == "pi":
        original.pi(stage_spec, workers=workers)
    elif stage == "causal":
        original.causal(stage_spec, workers=workers)
    elif stage == "export":
        combine(spec)
        export_combined(spec)
    else:
        raise ValueError("unknown extension stage")
