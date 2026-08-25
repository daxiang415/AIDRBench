"""Non-locked zero-deadline-miss sensitivity for renewable planning."""

from __future__ import annotations

import hashlib
import json
import multiprocessing
from collections.abc import Mapping
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict
from pathlib import Path
from typing import Any, cast

import numpy as np
import pandas as pd
import yaml

from aidrbench.data.frozen_scenarios import (
    FrozenHourlyScenario,
    load_frozen_hourly_scenario,
)
from aidrbench.data.splits import sha256_file
from aidrbench.evaluation.hosting_capacity import CommunityPortfolio, load_community_portfolio
from aidrbench.evaluation.renewable_ensemble import _portfolio_variant
from aidrbench.evaluation.renewable_integration import (
    RenewableIntegrationSolution,
    solve_curtailment_constrained_pv_hosting,
    solve_fixed_capacity_pv_operation,
)


def _mapping(value: object, name: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be a mapping")
    return {str(key): item for key, item in value.items()}


def _canonical_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _load_specification(path: str | Path) -> tuple[dict[str, Any], str]:
    document = _mapping(yaml.safe_load(Path(path).read_text(encoding="utf-8")), "specification")
    expected = {
        "schema_version",
        "evidence_scope",
        "locked_sets_used",
        "scenario_sets",
        "portfolio",
        "service",
        "analyses",
        "solver",
        "reporting",
    }
    if set(document) != expected:
        raise ValueError("zero-miss sensitivity specification fields mismatch")
    if (
        document["schema_version"] != 1
        or document["evidence_scope"]
        != "development_and_validation_sensitivity_only"
        or document["locked_sets_used"] is not False
    ):
        raise ValueError("zero-miss sensitivity must be non-locked development/validation only")
    service = _mapping(document["service"], "service")
    if set(service) != {"maximum_deadline_miss_fraction", "terminal_backlog_policy"}:
        raise ValueError("zero-miss service fields mismatch")
    if float(service["maximum_deadline_miss_fraction"]) != 0.0:
        raise ValueError("this sensitivity requires maximum_deadline_miss_fraction=0")
    if service["terminal_backlog_policy"] != "inherit_model_a":
        raise ValueError("terminal backlog policy must inherit Model A")
    solver = _mapping(document["solver"], "solver")
    if solver != {
        "name": "HIGHS",
        "threads_per_process": 1,
        "bess_dispatch_mode": "milp_exclusive",
    }:
        raise ValueError("zero-miss sensitivity solver must be fully specified")
    scenario_sets = _mapping(document["scenario_sets"], "scenario_sets")
    if set(scenario_sets) != {"development", "validation"}:
        raise ValueError("zero-miss sensitivity requires development and validation sets")
    for role, entry_raw in scenario_sets.items():
        entry = _mapping(entry_raw, f"scenario_sets.{role}")
        if set(entry) != {
            "path",
            "episode_seed_range",
            "scenario_count",
            "rigid_baseline_results",
        }:
            raise ValueError(f"scenario_sets.{role} fields mismatch")
        path_value = Path(str(entry["path"]))
        if "locked" in str(path_value).lower() or role not in path_value.name.lower():
            raise ValueError(f"scenario_sets.{role} must point to a matching non-locked path")
        seeds = entry["episode_seed_range"]
        if not isinstance(seeds, list) or len(seeds) != 2:
            raise ValueError(f"scenario_sets.{role}.episode_seed_range is invalid")
        if int(seeds[1]) - int(seeds[0]) + 1 != int(entry["scenario_count"]):
            raise ValueError(f"scenario_sets.{role} count does not match its seed range")
        baseline = _mapping(
            entry["rigid_baseline_results"],
            f"scenario_sets.{role}.rigid_baseline_results",
        )
        if set(baseline) != {"path", "sha256"}:
            raise ValueError(f"scenario_sets.{role}.rigid_baseline_results fields mismatch")
        if "locked" in str(baseline["path"]).lower():
            raise ValueError("zero-miss sensitivity cannot read locked baseline results")
    return document, _canonical_sha256(document)


def _discover(role: str, entry: Mapping[str, Any]) -> list[FrozenHourlyScenario]:
    root = Path(str(entry["path"]))
    artifacts = [
        load_frozen_hourly_scenario(child)
        for child in sorted(root.iterdir())
        if child.is_dir() and (child / "metadata.json").is_file()
    ]
    expected_count = int(entry["scenario_count"])
    seed_range = cast(list[int], entry["episode_seed_range"])
    expected_seeds = set(range(int(seed_range[0]), int(seed_range[1]) + 1))
    observed_seeds = {item.episode_seed for item in artifacts}
    if len(artifacts) != expected_count or observed_seeds != expected_seeds:
        raise ValueError(f"{role} scenarios do not match the zero-miss specification")
    return artifacts


def _row(
    role: str,
    artifact: FrozenHourlyScenario,
    analysis: str,
    operation: str,
    bess_enabled: bool,
    solution: RenewableIntegrationSolution | None,
) -> dict[str, Any]:
    common = {
        "dataset_role": role,
        "scenario_id": artifact.scenario_id,
        "scenario_hash": artifact.scenario_hash,
        "episode_seed": artifact.episode_seed,
        "analysis_variant": analysis,
        "dc_operation": operation,
        "bess_enabled": bess_enabled,
        "maximum_deadline_miss_fraction": 0.0,
    }
    if solution is None:
        return {**common, "status": "infeasible", "pv_rated_kw": np.nan}
    return {**common, **solution.summary()}


def _solve_payload(
    payload: tuple[str, str, dict[str, Any], dict[str, Any]],
) -> list[dict[str, Any]]:
    role, artifact_path, portfolio_raw, analyses = payload
    artifact = load_frozen_hourly_scenario(artifact_path)
    reference = CommunityPortfolio(**portfolio_raw)
    hosting = _mapping(analyses["pv_hosting"], "analyses.pv_hosting")
    operation_spec = _mapping(analyses["fixed_pv_operation"], "analyses.fixed_pv_operation")
    rows: list[dict[str, Any]] = []
    for bess_enabled in (False, True):
        portfolio = _portfolio_variant(
            reference,
            bess_enabled=bess_enabled,
            dispatch_mode="milp_exclusive",
        )
        hosting_solution = solve_curtailment_constrained_pv_hosting(
            artifact,
            portfolio=portfolio,
            dc_operation="flexible",
            dc_scale_of_reference_mix=float(hosting["dc_scale_of_reference_mix"]),
            maximum_pv_curtailment_fraction=float(
                hosting["maximum_pv_curtailment_fraction"]
            ),
            max_deadline_miss_rate=0.0,
        )
        rows.append(
            _row(
                role,
                artifact,
                "zero_miss_pv_hosting",
                "flexible",
                bess_enabled,
                hosting_solution,
            )
        )
        fixed_solution = solve_fixed_capacity_pv_operation(
            artifact,
            portfolio=portfolio,
            dc_operation="flexible",
            dc_scale_of_reference_mix=float(
                operation_spec["dc_scale_of_reference_mix"]
            ),
            pv_rated_kw=float(operation_spec["pv_rated_kw"]),
            near_pcc_limit_fraction=float(operation_spec["near_pcc_limit_fraction"]),
            lexicographic_tolerance_kwh=float(
                operation_spec["lexicographic_tolerance_kwh"]
            ),
            max_deadline_miss_rate=0.0,
        )
        rows.append(
            _row(
                role,
                artifact,
                "zero_miss_fixed_pv_operation",
                "flexible",
                bess_enabled,
                fixed_solution,
            )
        )
    return rows


def _load_rigid_baselines(
    role: str,
    entry: Mapping[str, Any],
    scenario_hashes: set[str],
) -> pd.DataFrame:
    baseline_entry = _mapping(
        entry["rigid_baseline_results"],
        f"scenario_sets.{role}.rigid_baseline_results",
    )
    path = Path(str(baseline_entry["path"]))
    if sha256_file(path) != str(baseline_entry["sha256"]):
        raise ValueError(f"{role} rigid baseline result hash mismatch")
    frame = pd.read_parquet(path)
    hosting = frame.loc[
        (frame["analysis_variant"] == "headline_pv_hosting_envelope")
        & (frame["dc_operation"] == "rigid")
        & (frame["dc_scale_of_reference_mix"] == 1.0)
        & (frame["maximum_pv_curtailment_fraction"] == 0.05)
    ].copy()
    fixed = frame.loc[
        (frame["analysis_variant"] == "fixed_capacity_pv_operation")
        & (frame["dc_operation"] == "rigid")
        & (frame["dc_scale_of_reference_mix"] == 1.0)
    ].copy()
    hosting["analysis_variant"] = "zero_miss_pv_hosting"
    fixed["analysis_variant"] = "zero_miss_fixed_pv_operation"
    selected = pd.concat((hosting, fixed), ignore_index=True)
    selected["dataset_role"] = role
    selected["maximum_deadline_miss_fraction"] = 0.0
    if (
        len(selected) != 4 * len(scenario_hashes)
        or set(selected["scenario_hash"]) != scenario_hashes
        or float(selected["deadline_miss_gpu_h"].max()) > 1e-6
    ):
        raise ValueError(f"{role} rigid baseline rows are incomplete or not zero-miss")
    return selected


def _summarize(results: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    summaries: list[dict[str, Any]] = []
    contrasts: list[dict[str, Any]] = []
    for (role, analysis, bess_enabled, operation), group in results.groupby(
        ["dataset_role", "analysis_variant", "bess_enabled", "dc_operation"],
        sort=True,
    ):
        feasible = group.loc[group["status"].isin(["optimal", "optimal_inaccurate"])]
        summaries.append(
            {
                "dataset_role": role,
                "analysis_variant": analysis,
                "bess_enabled": bess_enabled,
                "dc_operation": operation,
                "scenario_count": len(group),
                "feasible_scenario_count": len(feasible),
                "simultaneous_pv_hosting_kw": (
                    float(feasible["pv_rated_kw"].min())
                    if analysis == "zero_miss_pv_hosting" and len(feasible) == len(group)
                    else np.nan
                ),
                "mean_pv_rated_kw": float(feasible["pv_rated_kw"].mean()),
                "mean_total_pv_used_kwh": float(feasible["total_pv_used_kwh"].mean()),
                "maximum_deadline_miss_gpu_h": float(
                    feasible["deadline_miss_gpu_h"].max()
                ),
            }
        )
    for (role, analysis, bess_enabled), group in results.groupby(
        ["dataset_role", "analysis_variant", "bess_enabled"], sort=True
    ):
        pivot = group.pivot(index="scenario_hash", columns="dc_operation")
        rigid_status = pivot["status"]["rigid"].isin(["optimal", "optimal_inaccurate"])
        flexible_status = pivot["status"]["flexible"].isin(["optimal", "optimal_inaccurate"])
        paired = rigid_status & flexible_status
        rigid_pv = pivot["pv_rated_kw"]["rigid"].loc[paired]
        flexible_pv = pivot["pv_rated_kw"]["flexible"].loc[paired]
        rigid_used = pivot["total_pv_used_kwh"]["rigid"].loc[paired]
        flexible_used = pivot["total_pv_used_kwh"]["flexible"].loc[paired]
        contrasts.append(
            {
                "dataset_role": role,
                "analysis_variant": analysis,
                "bess_enabled": bess_enabled,
                "paired_scenario_count": int(paired.sum()),
                "paired_mean_pv_hosting_gain_kw": (
                    float((flexible_pv - rigid_pv).mean())
                    if analysis == "zero_miss_pv_hosting" and bool(paired.any())
                    else np.nan
                ),
                "paired_mean_pv_use_gain_kwh": (
                    float((flexible_used - rigid_used).mean())
                    if analysis == "zero_miss_fixed_pv_operation" and bool(paired.any())
                    else np.nan
                ),
            }
        )
    return pd.DataFrame(summaries), pd.DataFrame(contrasts)


def compute_zero_miss_renewable_sensitivity(
    specification_path: str | Path,
    output_directory: str | Path,
    *,
    workers: int = 1,
) -> dict[str, object]:
    """Run the declared development/validation zero-miss renewable slice."""

    if workers <= 0:
        raise ValueError("workers must be positive")
    specification, specification_sha256 = _load_specification(specification_path)
    scenario_sets = _mapping(specification["scenario_sets"], "scenario_sets")
    portfolio_entry = _mapping(specification["portfolio"], "portfolio")
    portfolio_path = Path(str(portfolio_entry["path"]))
    if sha256_file(portfolio_path) != str(portfolio_entry["sha256"]):
        raise ValueError("zero-miss portfolio hash mismatch")
    portfolio = load_community_portfolio(portfolio_path)
    output = Path(output_directory)
    output.mkdir(parents=True, exist_ok=True)
    partitions = output / "partitions"
    partitions.mkdir(exist_ok=True)
    run_state = {
        "schema_version": 1,
        "specification_sha256": specification_sha256,
        "specification_file_sha256": sha256_file(specification_path),
        "portfolio_sha256": str(portfolio_entry["sha256"]),
        "locked_sets_used": False,
    }
    run_state_path = output / "zero_miss_run.json"
    if run_state_path.is_file():
        if json.loads(run_state_path.read_text(encoding="utf-8")) != run_state:
            raise ValueError("zero-miss sensitivity resume state mismatch")
    else:
        run_state_path.write_text(json.dumps(run_state, indent=2) + "\n", encoding="utf-8")
    payloads: list[tuple[str, str, dict[str, Any], dict[str, Any]]] = []
    artifacts_by_role: dict[str, list[FrozenHourlyScenario]] = {}
    completed: list[pd.DataFrame] = []
    for role, entry_raw in scenario_sets.items():
        entry = _mapping(entry_raw, f"scenario_sets.{role}")
        artifacts = _discover(role, entry)
        artifacts_by_role[role] = artifacts
        role_partitions = partitions / role
        role_partitions.mkdir(exist_ok=True)
        for artifact in artifacts:
            partition_path = role_partitions / f"{artifact.scenario_hash}.parquet"
            if partition_path.is_file():
                frame = pd.read_parquet(partition_path)
                if (
                    len(frame) != 4
                    or set(frame["scenario_hash"]) != {artifact.scenario_hash}
                    or set(frame["dc_operation"]) != {"flexible"}
                ):
                    raise ValueError(f"invalid zero-miss checkpoint: {partition_path}")
                completed.append(frame)
            else:
                payloads.append(
                    (
                        role,
                        str(artifact.directory),
                        asdict(portfolio),
                        _mapping(specification["analyses"], "analyses"),
                    )
                )
    solved_count = 0
    if payloads:
        with ProcessPoolExecutor(
            max_workers=min(workers, len(payloads)),
            mp_context=multiprocessing.get_context("spawn"),
        ) as executor:
            futures = {
                executor.submit(_solve_payload, payload): payload for payload in payloads
            }
            for future in as_completed(futures):
                payload = futures[future]
                frame = pd.DataFrame.from_records(future.result())
                scenario_hash = str(frame["scenario_hash"].iloc[0])
                partition_path = partitions / payload[0] / f"{scenario_hash}.parquet"
                frame.to_parquet(partition_path, index=False)
                completed.append(frame)
                solved_count += 1
    flexible = pd.concat(completed, ignore_index=True)
    if len(flexible) != 4 * sum(len(items) for items in artifacts_by_role.values()):
        raise RuntimeError("zero-miss flexible sensitivity has an incomplete matrix")
    baselines = [
        _load_rigid_baselines(
            role,
            _mapping(scenario_sets[role], f"scenario_sets.{role}"),
            {artifact.scenario_hash for artifact in artifacts},
        )
        for role, artifacts in artifacts_by_role.items()
    ]
    results = pd.concat((flexible, *baselines), ignore_index=True).sort_values(
        ["dataset_role", "episode_seed", "analysis_variant", "bess_enabled", "dc_operation"],
        ignore_index=True,
    )
    total_scenario_count = sum(len(items) for items in artifacts_by_role.values())
    if len(results) != 8 * total_scenario_count:
        raise RuntimeError("zero-miss renewable sensitivity has an incomplete matrix")
    summary, contrasts = _summarize(results)
    paths = {
        "scenario_results": output / "zero_miss_scenario_results.parquet",
        "summary": output / "zero_miss_summary.csv",
        "contrasts": output / "zero_miss_contrasts.csv",
    }
    results.to_parquet(paths["scenario_results"], index=False)
    summary.to_csv(paths["summary"], index=False)
    contrasts.to_csv(paths["contrasts"], index=False)
    manifest = {
        "schema_version": 1,
        "evidence_scope": specification["evidence_scope"],
        "locked_sets_used": False,
        "specification_sha256": specification_sha256,
        "specification_file_sha256": sha256_file(specification_path),
        "workers": workers,
        "scenario_count": total_scenario_count,
        "row_count": len(results),
        "solved_scenario_count": solved_count,
        "resumed_scenario_count": total_scenario_count - solved_count,
        "rigid_baselines_reused": True,
        "outputs": {
            name: {"path": str(path), "sha256": sha256_file(path)}
            for name, path in paths.items()
        },
        "interpretation_guardrails": [
            "descriptive_service_sensitivity_not_a_new_headline_estimand",
            "perfect_information_planning_not_causal_controller_replay",
            "locked_id_and_locked_ood_not_read",
        ],
    }
    manifest_path = output / "zero_miss_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return {**manifest, "manifest_path": str(manifest_path)}
