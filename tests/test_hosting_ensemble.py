from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
import yaml

from aidrbench.data.frozen_scenarios import (
    freeze_hourly_scenarios,
    load_frozen_hourly_scenario,
)
from aidrbench.data.splits import sha256_file
from aidrbench.evaluation.hosting_capacity import (
    load_community_portfolio,
    solve_frozen_hosting_capacity,
)
from aidrbench.evaluation.hosting_ensemble import (
    compute_hosting_ensemble,
    load_hosting_ensemble_specification,
)

ROOT = Path(__file__).resolve().parents[1]


def _short_pv_scenario_config() -> dict[str, object]:
    document = yaml.safe_load(
        (ROOT / "configs/env/hourly_continuous.yaml").read_text(encoding="utf-8")
    )
    assert isinstance(document, dict)
    assert isinstance(document["env"], dict)
    assert isinstance(document["community"], dict)
    assert isinstance(document["dr"], dict)
    document["env"]["episode_days"] = 1
    document["env"]["clearance_tail_hours"] = 12
    document["env"]["episode_seed_range"] = [91, 92]
    document["community"]["pv_enabled"] = True
    document["dr"]["event_start_hours"] = [8]
    document["dr"]["event_duration_hours"] = 2
    document["dr"]["recovery_window_hours"] = 8
    return document


def _write_specification(
    tmp_path: Path,
    *,
    dataset_role: str = "development_hosting_capacity",
) -> Path:
    portfolio_path = ROOT / "configs/community/pv_bess.yaml"
    document = {
        "schema_version": 1,
        "model_a_git_commit": "a" * 40,
        "dataset_role": dataset_role,
        "independent_unit": "frozen_scenario",
        "expected_scenario_count": 2,
        "expected_episode_seed_range": [91, 92],
        "portfolio": {
            "path": str(portfolio_path),
            "sha256": sha256_file(portfolio_path),
        },
        "solver": {"name": "HIGHS", "threads_per_process": 1},
        "capacity_aggregation": {
            "headline": "simultaneous_scenario_feasible_minimum",
            "descriptive_quantiles": [0.05, 0.50, 0.95],
        },
        "paired_inference": {
            "estimand": "mean_within_scenario_contrast_kw",
            "confidence_level": 0.95,
            "familywise_method": "bonferroni",
            "planned_contrast_count": 8,
            "bootstrap_resamples": 1000,
            "bootstrap_seed": 123,
        },
        "interaction_equivalence_margin": {
            "basis": "fraction_of_reference_mix_operating_peak",
            "fraction": 0.05,
        },
    }
    path = tmp_path / "hosting_specification.yaml"
    path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    return path


def test_hosting_ensemble_specification_rejects_implicit_fields(tmp_path: Path) -> None:
    path = _write_specification(tmp_path)
    specification = load_hosting_ensemble_specification(path)
    assert specification.planned_contrast_count == 8

    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    document["solver"]["implicit_default"] = True
    path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    with pytest.raises(ValueError, match="fields mismatch"):
        load_hosting_ensemble_specification(path)


def test_validation_hosting_requires_validation_scenario_path(tmp_path: Path) -> None:
    scenarios = tmp_path / "development_scenarios"
    freeze_hourly_scenarios(
        _short_pv_scenario_config(),
        seeds=[91, 92],
        output_directory=scenarios,
    )
    specification = _write_specification(
        tmp_path,
        dataset_role="validation_hosting_replication",
    )

    with pytest.raises(ValueError, match="requires a validation scenario path"):
        compute_hosting_ensemble(
            scenarios,
            specification_path=specification,
            output_directory=tmp_path / "hosting",
            workers=1,
        )


def test_validation_hosting_replication_uses_same_paired_matrix(tmp_path: Path) -> None:
    scenarios = tmp_path / "validation_scenarios"
    freeze_hourly_scenarios(
        _short_pv_scenario_config(),
        seeds=[91, 92],
        output_directory=scenarios,
    )
    specification = _write_specification(
        tmp_path,
        dataset_role="validation_hosting_replication",
    )

    summary = compute_hosting_ensemble(
        scenarios,
        specification_path=specification,
        output_directory=tmp_path / "hosting",
        workers=1,
    )

    assert summary["scenario_count"] == 2
    assert summary["row_count"] == 16
    manifest = Path(summary["manifest"]).read_text(encoding="utf-8")
    assert '"dataset_role": "validation_hosting_replication"' in manifest


def test_hosting_ensemble_is_paired_checkpointed_and_resumable(tmp_path: Path) -> None:
    scenarios = tmp_path / "development_scenarios"
    freeze_hourly_scenarios(
        _short_pv_scenario_config(),
        seeds=[91, 92],
        output_directory=scenarios,
    )
    specification = _write_specification(tmp_path)
    output = tmp_path / "hosting"

    first = compute_hosting_ensemble(
        scenarios,
        specification_path=specification,
        output_directory=output,
        workers=1,
    )
    second = compute_hosting_ensemble(
        scenarios,
        specification_path=specification,
        output_directory=output,
        workers=1,
    )

    scenario_capacity = pd.read_parquet(first["scenario_capacity"])
    capacity_summary = pd.read_parquet(first["capacity_summary"])
    contrasts = pd.read_parquet(first["paired_contrasts"])
    assert len(scenario_capacity) == 16
    assert len(capacity_summary) == 8
    assert len(contrasts) == 8
    assert set(contrasts["contrast"]) == {
        "AI_HOSTING_GAIN",
        "AI_BESS_INTERACTION",
        "AI_PV_INTERACTION",
    }
    assert (contrasts["planned_contrast_count"] == 8).all()
    assert (contrasts["simultaneous_ci_lower_kw"] <= contrasts["estimate_mean_kw"]).all()
    assert (contrasts["estimate_mean_kw"] <= contrasts["simultaneous_ci_upper_kw"]).all()
    assert first["solved_scenario_count"] == 2
    assert second["solved_scenario_count"] == 0
    assert second["resumed_scenario_count"] == 2

    artifacts = [
        load_frozen_hourly_scenario(path)
        for path in sorted(scenarios.glob("hourly_seed_*"))
    ]
    portfolio = load_community_portfolio(ROOT / "configs/community/pv_bess.yaml")
    joint = solve_frozen_hosting_capacity(
        artifacts,
        portfolio=portfolio,
        dc_operation="flexible",
    )
    decomposed = capacity_summary.loc[
        (capacity_summary["dc_operation"] == "flexible")
        & capacity_summary["pv_enabled"]
        & capacity_summary["bess_enabled"],
        "simultaneous_feasible_hosting_dc_peak_kw",
    ].iloc[0]
    assert float(decomposed) == pytest.approx(joint.hosting_dc_peak_kw, abs=1e-5)
