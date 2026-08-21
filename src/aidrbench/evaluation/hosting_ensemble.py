"""Scenario-decomposed 2x2x2 hosting capacity with paired uncertainty."""

from __future__ import annotations

import hashlib
import json
import multiprocessing
from collections.abc import Mapping
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal, cast

import numpy as np
import pandas as pd
import yaml

from aidrbench.data.frozen_scenarios import (
    FrozenHourlyScenario,
    load_frozen_hourly_scenario,
)
from aidrbench.data.splits import sha256_file
from aidrbench.evaluation.frozen_causal_certificate import _git_commit
from aidrbench.evaluation.hosting_capacity import (
    CommunityPortfolio,
    load_community_portfolio,
    solve_frozen_hosting_capacity,
)

_RUN_STATE_NAME = "hosting_ensemble_run.json"
_SOURCE_PATHS = (
    "src/aidrbench/evaluation/hosting_capacity.py",
    "src/aidrbench/evaluation/hosting_ensemble.py",
)


def _mapping(value: object, name: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be a mapping")
    return {str(key): item for key, item in value.items()}


def _exact_fields(document: Mapping[str, Any], expected: set[str], name: str) -> None:
    observed = set(document)
    if observed != expected:
        raise ValueError(
            f"{name} fields mismatch; missing={sorted(expected - observed)}, "
            f"unknown={sorted(observed - expected)}"
        )


def _canonical_sha256(value: object) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


@dataclass(frozen=True, slots=True)
class HostingEnsembleSpecification:
    """Complete preregistration for a non-locked hosting ensemble."""

    schema_version: int
    model_a_git_commit: str
    dataset_role: Literal[
        "development_hosting_capacity",
        "validation_hosting_replication",
    ]
    independent_unit: Literal["frozen_scenario"]
    expected_scenario_count: int
    expected_episode_seed_range: tuple[int, int]
    portfolio_path: str
    portfolio_sha256: str
    solver_name: Literal["HIGHS"]
    threads_per_process: int
    headline_capacity_aggregation: Literal[
        "simultaneous_scenario_feasible_minimum"
    ]
    descriptive_quantiles: tuple[float, ...]
    paired_estimand: Literal["mean_within_scenario_contrast_kw"]
    confidence_level: float
    familywise_method: Literal["bonferroni"]
    planned_contrast_count: int
    bootstrap_resamples: int
    bootstrap_seed: int
    equivalence_margin_basis: Literal[
        "fraction_of_reference_mix_operating_peak"
    ]
    equivalence_margin_fraction: float

    def __post_init__(self) -> None:
        if self.schema_version != 1:
            raise ValueError("unsupported hosting ensemble schema_version")
        if len(self.model_a_git_commit) != 40 or any(
            value not in "0123456789abcdef" for value in self.model_a_git_commit
        ):
            raise ValueError("model_a_git_commit must be a lowercase 40-character SHA-1")
        if self.expected_scenario_count <= 1:
            raise ValueError("hosting ensemble requires more than one scenario")
        start, stop = self.expected_episode_seed_range
        if start < 0 or stop < start or stop - start + 1 != self.expected_scenario_count:
            raise ValueError("expected seed range must match expected_scenario_count")
        if len(self.portfolio_sha256) != 64:
            raise ValueError("portfolio_sha256 must be a SHA-256 digest")
        if self.threads_per_process != 1:
            raise ValueError("formal hosting ensemble requires one solver thread per process")
        if not self.descriptive_quantiles or any(
            not 0.0 < value < 1.0 for value in self.descriptive_quantiles
        ):
            raise ValueError("descriptive_quantiles must lie in (0, 1)")
        if tuple(sorted(set(self.descriptive_quantiles))) != self.descriptive_quantiles:
            raise ValueError("descriptive_quantiles must be unique and increasing")
        if not 0.0 < self.confidence_level < 1.0:
            raise ValueError("confidence_level must lie in (0, 1)")
        if self.planned_contrast_count != 8:
            raise ValueError("the 2x2x2 design predeclares exactly eight contrasts")
        if self.bootstrap_resamples < 1000:
            raise ValueError("bootstrap_resamples must be at least 1000")
        if self.bootstrap_seed < 0:
            raise ValueError("bootstrap_seed must be non-negative")
        if not 0.0 < self.equivalence_margin_fraction < 1.0:
            raise ValueError("equivalence margin fraction must lie in (0, 1)")

    def as_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["expected_episode_seed_range"] = list(self.expected_episode_seed_range)
        result["descriptive_quantiles"] = list(self.descriptive_quantiles)
        return result

    @property
    def sha256(self) -> str:
        return _canonical_sha256(self.as_dict())


def load_hosting_ensemble_specification(
    path: str | Path,
) -> HostingEnsembleSpecification:
    """Load the complete hosting-ensemble specification without defaults."""

    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    document = _mapping(raw, "hosting ensemble specification")
    _exact_fields(
        document,
        {
            "schema_version",
            "model_a_git_commit",
            "dataset_role",
            "independent_unit",
            "expected_scenario_count",
            "expected_episode_seed_range",
            "portfolio",
            "solver",
            "capacity_aggregation",
            "paired_inference",
            "interaction_equivalence_margin",
        },
        "hosting ensemble specification",
    )
    portfolio = _mapping(document["portfolio"], "portfolio")
    _exact_fields(portfolio, {"path", "sha256"}, "portfolio")
    solver = _mapping(document["solver"], "solver")
    _exact_fields(solver, {"name", "threads_per_process"}, "solver")
    aggregation = _mapping(document["capacity_aggregation"], "capacity_aggregation")
    _exact_fields(
        aggregation,
        {"headline", "descriptive_quantiles"},
        "capacity_aggregation",
    )
    inference = _mapping(document["paired_inference"], "paired_inference")
    _exact_fields(
        inference,
        {
            "estimand",
            "confidence_level",
            "familywise_method",
            "planned_contrast_count",
            "bootstrap_resamples",
            "bootstrap_seed",
        },
        "paired_inference",
    )
    equivalence = _mapping(
        document["interaction_equivalence_margin"],
        "interaction_equivalence_margin",
    )
    _exact_fields(
        equivalence,
        {"basis", "fraction"},
        "interaction_equivalence_margin",
    )
    seed_range = document["expected_episode_seed_range"]
    if not isinstance(seed_range, list) or len(seed_range) != 2:
        raise ValueError("expected_episode_seed_range must contain two integers")
    return HostingEnsembleSpecification(
        schema_version=int(document["schema_version"]),
        model_a_git_commit=str(document["model_a_git_commit"]),
        dataset_role=str(document["dataset_role"]),  # type: ignore[arg-type]
        independent_unit=str(document["independent_unit"]),  # type: ignore[arg-type]
        expected_scenario_count=int(document["expected_scenario_count"]),
        expected_episode_seed_range=(int(seed_range[0]), int(seed_range[1])),
        portfolio_path=str(portfolio["path"]),
        portfolio_sha256=str(portfolio["sha256"]),
        solver_name=str(solver["name"]),  # type: ignore[arg-type]
        threads_per_process=int(solver["threads_per_process"]),
        headline_capacity_aggregation=str(aggregation["headline"]),  # type: ignore[arg-type]
        descriptive_quantiles=tuple(
            float(value) for value in aggregation["descriptive_quantiles"]
        ),
        paired_estimand=str(inference["estimand"]),  # type: ignore[arg-type]
        confidence_level=float(inference["confidence_level"]),
        familywise_method=str(inference["familywise_method"]),  # type: ignore[arg-type]
        planned_contrast_count=int(inference["planned_contrast_count"]),
        bootstrap_resamples=int(inference["bootstrap_resamples"]),
        bootstrap_seed=int(inference["bootstrap_seed"]),
        equivalence_margin_basis=str(equivalence["basis"]),  # type: ignore[arg-type]
        equivalence_margin_fraction=float(equivalence["fraction"]),
    )


def _discover_hosting_artifacts(
    scenario_path: str | Path,
    specification: HostingEnsembleSpecification,
) -> list[FrozenHourlyScenario]:
    root = Path(scenario_path)
    labels = [part.lower() for part in root.parts]
    if any("locked" in label for label in labels):
        raise ValueError("hosting ensemble may not read a locked path")
    required_label = (
        "validation"
        if specification.dataset_role == "validation_hosting_replication"
        else "development"
    )
    if required_label not in root.name.lower():
        raise ValueError(
            f"{specification.dataset_role} requires a {required_label} scenario path"
        )
    artifacts = [
        load_frozen_hourly_scenario(child)
        for child in sorted(root.iterdir())
        if child.is_dir() and (child / "metadata.json").is_file()
    ]
    if len(artifacts) != specification.expected_scenario_count:
        raise ValueError(
            "hosting scenario count does not match the preregistered ensemble"
        )
    expected_seeds = set(
        range(
            specification.expected_episode_seed_range[0],
            specification.expected_episode_seed_range[1] + 1,
        )
    )
    if {artifact.episode_seed for artifact in artifacts} != expected_seeds:
        raise ValueError("hosting scenario seeds do not match the preregistered range")
    if len({artifact.scenario_hash for artifact in artifacts}) != len(artifacts):
        raise ValueError("hosting scenarios must have unique hashes")
    return artifacts


def _portfolio_variant(
    reference: CommunityPortfolio,
    *,
    pv_enabled: bool,
    bess_enabled: bool,
) -> CommunityPortfolio:
    return CommunityPortfolio(
        pv_enabled=pv_enabled,
        pv_rated_kw=reference.pv_rated_kw if pv_enabled else 0.0,
        bess_enabled=bess_enabled,
        bess_power_kw=reference.bess_power_kw if bess_enabled else 0.0,
        bess_energy_kwh=reference.bess_energy_kwh if bess_enabled else 0.0,
        charge_efficiency=reference.charge_efficiency,
        discharge_efficiency=reference.discharge_efficiency,
        initial_soc_fraction=reference.initial_soc_fraction,
        terminal_soc_fraction=reference.terminal_soc_fraction,
        prohibit_export=reference.prohibit_export,
        bess_dispatch_mode=reference.bess_dispatch_mode,
    )


def _solve_scenario_matrix(
    payload: tuple[str, dict[str, Any], str, str],
) -> list[dict[str, Any]]:
    artifact_path, portfolio_raw, specification_sha256, portfolio_sha256 = payload
    artifact = load_frozen_hourly_scenario(artifact_path)
    portfolio = CommunityPortfolio(**portfolio_raw)
    rows: list[dict[str, Any]] = []
    for pv_enabled in (False, True):
        for bess_enabled in (False, True):
            candidate = _portfolio_variant(
                portfolio,
                pv_enabled=pv_enabled,
                bess_enabled=bess_enabled,
            )
            for operation in ("rigid", "flexible"):
                solution = solve_frozen_hosting_capacity(
                    [artifact],
                    portfolio=candidate,
                    dc_operation=operation,
                )
                rows.append(
                    {
                        "scenario_id": artifact.scenario_id,
                        "scenario_hash": artifact.scenario_hash,
                        "episode_seed": artifact.episode_seed,
                        "specification_sha256": specification_sha256,
                        "portfolio_sha256": portfolio_sha256,
                        **solution.summary(),
                    }
                )
    return rows


def _validate_partition(
    path: Path,
    *,
    artifact: FrozenHourlyScenario,
    specification_sha256: str,
    portfolio_sha256: str,
) -> pd.DataFrame:
    frame = pd.read_parquet(path)
    if len(frame) != 8:
        raise ValueError(f"hosting partition must contain eight rows: {path}")
    expected_combinations = {
        (operation, pv, bess)
        for operation in ("rigid", "flexible")
        for pv in (False, True)
        for bess in (False, True)
    }
    observed = set(
        zip(
            frame["dc_operation"],
            frame["pv_enabled"].astype(bool),
            frame["bess_enabled"].astype(bool),
            strict=True,
        )
    )
    if observed != expected_combinations:
        raise ValueError(f"hosting partition has an invalid portfolio matrix: {path}")
    checks = {
        "scenario_hash": artifact.scenario_hash,
        "specification_sha256": specification_sha256,
        "portfolio_sha256": portfolio_sha256,
    }
    for column, expected in checks.items():
        if set(frame[column].astype(str)) != {expected}:
            raise ValueError(f"hosting partition {column} mismatch: {path}")
    return frame


def _capacity_summary(
    scenario_results: pd.DataFrame,
    specification: HostingEnsembleSpecification,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    group_columns = ["dc_operation", "pv_enabled", "bess_enabled"]
    for raw_key, selected in scenario_results.groupby(group_columns, sort=True):
        operation, pv_enabled, bess_enabled = cast(tuple[Any, Any, Any], raw_key)
        capacities = selected["hosting_dc_peak_kw"].astype(float)
        binding_index = capacities.idxmin()
        row: dict[str, Any] = {
            "dc_operation": str(operation),
            "pv_enabled": bool(pv_enabled),
            "bess_enabled": bool(bess_enabled),
            "scenario_count": len(selected),
            "simultaneous_feasible_hosting_dc_peak_kw": float(capacities.min()),
            "binding_scenario_hash": str(
                scenario_results.loc[binding_index, "scenario_hash"]
            ),
            "mean_scenario_hosting_dc_peak_kw": float(capacities.mean()),
            "minimum_scenario_hosting_dc_peak_kw": float(capacities.min()),
            "maximum_scenario_hosting_dc_peak_kw": float(capacities.max()),
        }
        for quantile in specification.descriptive_quantiles:
            label = f"q{round(100 * quantile):02d}_scenario_hosting_dc_peak_kw"
            row[label] = float(capacities.quantile(quantile))
        rows.append(row)
    summary = pd.DataFrame.from_records(rows)
    summary["hosting_gain_vs_rigid_simultaneous_kw"] = np.nan
    for _, indices in summary.groupby(["pv_enabled", "bess_enabled"]).groups.items():
        group = summary.loc[indices]
        rigid = float(
            group.loc[
                group["dc_operation"] == "rigid",
                "simultaneous_feasible_hosting_dc_peak_kw",
            ].iloc[0]
        )
        summary.loc[indices, "hosting_gain_vs_rigid_simultaneous_kw"] = (
            summary.loc[indices, "simultaneous_feasible_hosting_dc_peak_kw"] - rigid
        )
    return summary.sort_values(group_columns, ignore_index=True)


def _capacity_vector(
    indexed: pd.DataFrame,
    operation: str,
    pv_enabled: bool,
    bess_enabled: bool,
) -> np.ndarray:
    return np.asarray(
        indexed.loc[
            (slice(None), operation, pv_enabled, bess_enabled),
            "hosting_dc_peak_kw",
        ].to_numpy(dtype="float64"),
        dtype="float64",
    )


def _paired_contrast_vectors(scenario_results: pd.DataFrame) -> list[dict[str, Any]]:
    indexed = scenario_results.set_index(
        ["scenario_hash", "dc_operation", "pv_enabled", "bess_enabled"]
    ).sort_index()
    rows: list[dict[str, Any]] = []
    for pv_enabled in (False, True):
        for bess_enabled in (False, True):
            flexible = _capacity_vector(indexed, "flexible", pv_enabled, bess_enabled)
            rigid = _capacity_vector(indexed, "rigid", pv_enabled, bess_enabled)
            rows.append(
                {
                    "contrast": "AI_HOSTING_GAIN",
                    "conditioning_axis": "pv_bess_portfolio",
                    "conditioning_level": f"pv={pv_enabled},bess={bess_enabled}",
                    "values": flexible - rigid,
                }
            )
    for pv_enabled in (False, True):
        ai_without_bess = _capacity_vector(indexed, "flexible", pv_enabled, False) - (
            _capacity_vector(indexed, "rigid", pv_enabled, False)
        )
        ai_with_bess = _capacity_vector(indexed, "flexible", pv_enabled, True) - (
            _capacity_vector(indexed, "rigid", pv_enabled, True)
        )
        rows.append(
            {
                "contrast": "AI_BESS_INTERACTION",
                "conditioning_axis": "pv_enabled",
                "conditioning_level": str(pv_enabled),
                "values": ai_with_bess - ai_without_bess,
            }
        )
    for bess_enabled in (False, True):
        ai_without_pv = _capacity_vector(indexed, "flexible", False, bess_enabled) - (
            _capacity_vector(indexed, "rigid", False, bess_enabled)
        )
        ai_with_pv = _capacity_vector(indexed, "flexible", True, bess_enabled) - (
            _capacity_vector(indexed, "rigid", True, bess_enabled)
        )
        rows.append(
            {
                "contrast": "AI_PV_INTERACTION",
                "conditioning_axis": "bess_enabled",
                "conditioning_level": str(bess_enabled),
                "values": ai_with_pv - ai_without_pv,
            }
        )
    return rows


def _paired_contrast_summary(
    scenario_results: pd.DataFrame,
    specification: HostingEnsembleSpecification,
    *,
    reference_mix_operating_peak_kw: float,
) -> pd.DataFrame:
    contrasts = _paired_contrast_vectors(scenario_results)
    if len(contrasts) != specification.planned_contrast_count:
        raise RuntimeError("hosting contrast family does not match preregistration")
    alpha = 1.0 - specification.confidence_level
    tail_probability = alpha / (2.0 * specification.planned_contrast_count)
    adjusted_interval_level = 1.0 - alpha / specification.planned_contrast_count
    margin_kw = (
        specification.equivalence_margin_fraction
        * reference_mix_operating_peak_kw
    )
    rng = np.random.default_rng(specification.bootstrap_seed)
    rows: list[dict[str, Any]] = []
    for contrast in contrasts:
        values = np.asarray(contrast.pop("values"), dtype="float64")
        if not np.isfinite(values).all() or len(values) != specification.expected_scenario_count:
            raise ValueError("hosting paired contrast has invalid scenario values")
        resample_indices = rng.integers(
            0,
            len(values),
            size=(specification.bootstrap_resamples, len(values)),
        )
        bootstrap_means = values[resample_indices].mean(axis=1)
        lower = float(np.quantile(bootstrap_means, tail_probability))
        upper = float(np.quantile(bootstrap_means, 1.0 - tail_probability))
        estimate = float(values.mean())
        contrast_name = str(contrast["contrast"])
        if contrast_name == "AI_HOSTING_GAIN":
            interpretation = "positive" if lower > 0.0 else "indeterminate"
            applied_margin = 0.0
        elif lower > margin_kw:
            interpretation = "complementarity"
            applied_margin = margin_kw
        elif upper < -margin_kw:
            interpretation = "substitution"
            applied_margin = margin_kw
        elif lower >= -margin_kw and upper <= margin_kw:
            interpretation = "equivalent_within_margin"
            applied_margin = margin_kw
        else:
            interpretation = "indeterminate"
            applied_margin = margin_kw
        rows.append(
            {
                **contrast,
                "independent_unit": specification.independent_unit,
                "scenario_count": len(values),
                "estimate_mean_kw": estimate,
                "sample_standard_deviation_kw": float(values.std(ddof=1)),
                "simultaneous_ci_lower_kw": lower,
                "simultaneous_ci_upper_kw": upper,
                "familywise_confidence_level": specification.confidence_level,
                "bonferroni_adjusted_marginal_interval_level": (
                    adjusted_interval_level
                ),
                "planned_contrast_count": specification.planned_contrast_count,
                "bootstrap_resamples": specification.bootstrap_resamples,
                "equivalence_margin_kw": applied_margin,
                "interpretation": interpretation,
            }
        )
    return pd.DataFrame.from_records(rows)


def compute_hosting_ensemble(
    scenario_path: str | Path,
    *,
    specification_path: str | Path,
    output_directory: str | Path,
    workers: int = 1,
) -> dict[str, Any]:
    """Solve, checkpoint and aggregate the preregistered hosting ensemble."""

    if workers <= 0:
        raise ValueError("workers must be positive")
    specification = load_hosting_ensemble_specification(specification_path)
    portfolio_path = Path(specification.portfolio_path)
    if sha256_file(portfolio_path) != specification.portfolio_sha256:
        raise ValueError("hosting portfolio SHA-256 mismatch")
    portfolio = load_community_portfolio(portfolio_path)
    artifacts = _discover_hosting_artifacts(scenario_path, specification)
    output = Path(output_directory)
    output.mkdir(parents=True, exist_ok=True)
    partitions = output / "scenario_partitions"
    partitions.mkdir(exist_ok=True)
    run_state_path = output / _RUN_STATE_NAME
    run_state = {
        "schema_version": 1,
        "dataset_role": specification.dataset_role,
        "locked_data_read": False,
        "specification": specification.as_dict(),
        "specification_sha256": specification.sha256,
        "specification_file_sha256": sha256_file(Path(specification_path)),
        "portfolio_sha256": specification.portfolio_sha256,
        "scenario_hashes": [artifact.scenario_hash for artifact in artifacts],
    }
    if run_state_path.is_file():
        observed = json.loads(run_state_path.read_text(encoding="utf-8"))
        if observed != run_state:
            raise ValueError("hosting ensemble resume state mismatch")
    else:
        run_state_path.write_text(
            json.dumps(run_state, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    completed_frames: list[pd.DataFrame] = []
    missing: list[FrozenHourlyScenario] = []
    for artifact in artifacts:
        partition_path = partitions / f"{artifact.scenario_hash}.parquet"
        if partition_path.is_file():
            completed_frames.append(
                _validate_partition(
                    partition_path,
                    artifact=artifact,
                    specification_sha256=specification.sha256,
                    portfolio_sha256=specification.portfolio_sha256,
                )
            )
        else:
            missing.append(artifact)
    portfolio_raw = asdict(portfolio)
    if missing:
        with ProcessPoolExecutor(
            max_workers=min(workers, len(missing)),
            mp_context=multiprocessing.get_context("spawn"),
        ) as executor:
            future_by_artifact = {
                executor.submit(
                    _solve_scenario_matrix,
                    (
                        str(artifact.directory),
                        portfolio_raw,
                        specification.sha256,
                        specification.portfolio_sha256,
                    ),
                ): artifact
                for artifact in missing
            }
            for future in as_completed(future_by_artifact):
                artifact = future_by_artifact[future]
                frame = pd.DataFrame.from_records(future.result())
                partition_path = partitions / f"{artifact.scenario_hash}.parquet"
                frame.to_parquet(partition_path, index=False)
                completed_frames.append(
                    _validate_partition(
                        partition_path,
                        artifact=artifact,
                        specification_sha256=specification.sha256,
                        portfolio_sha256=specification.portfolio_sha256,
                    )
                )
    scenario_results = pd.concat(completed_frames, ignore_index=True).sort_values(
        ["episode_seed", "pv_enabled", "bess_enabled", "dc_operation"],
        ignore_index=True,
    )
    if len(scenario_results) != 8 * specification.expected_scenario_count:
        raise RuntimeError("hosting ensemble has an incomplete scenario matrix")
    reference_peaks = set(
        scenario_results["reference_mix_operating_peak_kw"].astype(float).round(9)
    )
    if len(reference_peaks) != 1:
        raise ValueError("hosting scenarios have inconsistent reference-mix peaks")
    reference_peak_kw = float(next(iter(reference_peaks)))
    capacity_summary = _capacity_summary(scenario_results, specification)
    paired_contrasts = _paired_contrast_summary(
        scenario_results,
        specification,
        reference_mix_operating_peak_kw=reference_peak_kw,
    )
    scenario_results_path = output / "scenario_hosting_capacity.parquet"
    capacity_summary_path = output / "hosting_capacity_summary.parquet"
    contrasts_path = output / "hosting_paired_contrasts.parquet"
    manifest_path = output / "hosting_ensemble.json"
    scenario_results.to_parquet(scenario_results_path, index=False)
    capacity_summary.to_parquet(capacity_summary_path, index=False)
    paired_contrasts.to_parquet(contrasts_path, index=False)
    repository_root = Path(__file__).resolve().parents[3]
    manifest_path.write_text(
        json.dumps(
            {
                **run_state,
                "model_a_git_commit": specification.model_a_git_commit,
                "analysis_git_commit": _git_commit(),
                "source_sha256": {
                    path: sha256_file(repository_root / path) for path in _SOURCE_PATHS
                },
                "workers": workers,
                "solver_threads_per_process": specification.threads_per_process,
                "outputs": {
                    "scenario_capacity": str(scenario_results_path),
                    "capacity_summary": str(capacity_summary_path),
                    "paired_contrasts": str(contrasts_path),
                },
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return {
        "manifest": str(manifest_path),
        "scenario_capacity": str(scenario_results_path),
        "capacity_summary": str(capacity_summary_path),
        "paired_contrasts": str(contrasts_path),
        "scenario_count": specification.expected_scenario_count,
        "row_count": len(scenario_results),
        "resumed_scenario_count": specification.expected_scenario_count - len(missing),
        "solved_scenario_count": len(missing),
    }
