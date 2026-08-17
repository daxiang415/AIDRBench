"""Reproducibility metadata shared by formal optimization outputs."""

from __future__ import annotations

import subprocess
from collections.abc import Sequence
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from aidrbench.data.frozen_scenarios import FrozenHourlyScenario


def _package_version(name: str) -> str | None:
    try:
        return version(name)
    except PackageNotFoundError:
        return None


def _git_state() -> dict[str, object]:
    repository = Path(__file__).resolve().parents[3]
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repository,
        check=False,
        capture_output=True,
        text=True,
    )
    status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=repository,
        check=False,
        capture_output=True,
        text=True,
    )
    return {
        "commit": commit.stdout.strip() if commit.returncode == 0 else None,
        "working_tree_dirty": bool(status.stdout.strip()) if status.returncode == 0 else None,
    }


def optimization_provenance(
    artifacts: Sequence[FrozenHourlyScenario],
    *,
    solver_name: str = "HIGHS",
    numerical_tolerance: float = 1e-6,
) -> dict[str, object]:
    """Return code, solver, power-model, and immutable scenario provenance."""

    return {
        "software": {
            "git": _git_state(),
            "versions": {
                "aidrbench": _package_version("aidrbench"),
                "cvxpy": _package_version("cvxpy"),
                "highspy": _package_version("highspy"),
                "numpy": _package_version("numpy"),
                "pandas": _package_version("pandas"),
            },
        },
        "solver": {
            "name": solver_name,
            "reported_numerical_tolerance": numerical_tolerance,
        },
        "scenario_artifacts": [
            {
                "scenario_id": artifact.scenario_id,
                "scenario_hash": artifact.scenario_hash,
                "episode_seed": artifact.episode_seed,
                "file_sha256": dict(artifact.metadata["files"]),
                "power_model_sha256": artifact.metadata["power_model"]["sha256"],
                "calibration_power_case": artifact.metadata["power_model"].get(
                    "calibration_power_case", "unknown_legacy_artifact"
                ),
                "calibration_artifact_sha256": artifact.metadata["power_model"].get(
                    "calibration_artifact_sha256"
                ),
                "power_model_parameters": artifact.metadata["power_model"]["parameters"],
            }
            for artifact in artifacts
        ],
    }
