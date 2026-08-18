from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
import yaml

from aidrbench.data.frozen_scenarios import freeze_hourly_scenario, load_frozen_hourly_scenario
from aidrbench.evaluation.hosting_capacity import (
    CommunityPortfolio,
    compute_and_save_hosting_capacity,
    solve_frozen_hosting_capacity,
)

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/env/hourly_continuous.yaml"


def _short_pv_scenario_config() -> dict[str, object]:
    document = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    assert isinstance(document, dict)
    environment = document["env"]
    community = document["community"]
    dr = document["dr"]
    assert isinstance(environment, dict)
    assert isinstance(community, dict)
    assert isinstance(dr, dict)
    environment["episode_days"] = 1
    environment["clearance_tail_hours"] = 12
    community["pv_enabled"] = True
    dr["event_start_hours"] = [8]
    dr["event_duration_hours"] = 2
    dr["recovery_window_hours"] = 8
    return document


def test_flexible_hosting_is_at_least_rigid_with_explicit_pv_and_bess(tmp_path: Path) -> None:
    config = _short_pv_scenario_config()
    artifacts = [
        load_frozen_hourly_scenario(
            str(freeze_hourly_scenario(config, seed=seed, output_directory=tmp_path)["output"])
        )
        for seed in (81, 82)
    ]
    portfolio = CommunityPortfolio(
        pv_enabled=True,
        pv_rated_kw=300.0,
        bess_enabled=True,
        bess_power_kw=100.0,
        bess_energy_kwh=200.0,
    )

    rigid = solve_frozen_hosting_capacity(
        artifacts,
        portfolio=portfolio,
        dc_operation="rigid",
    )
    flexible = solve_frozen_hosting_capacity(
        artifacts,
        portfolio=portfolio,
        dc_operation="flexible",
    )

    assert rigid.status == "optimal"
    assert flexible.status == "optimal"
    assert 0.0 <= rigid.maximum_pcc_power_kw <= rigid.pcc_capacity_kw + 1e-6
    assert 0.0 <= flexible.maximum_pcc_power_kw <= flexible.pcc_capacity_kw + 1e-6
    assert flexible.hosting_dc_peak_kw + 1e-6 >= rigid.hosting_dc_peak_kw
    assert flexible.worst_class_peak_kw >= flexible.reference_mix_operating_peak_kw
    assert flexible.total_pv_used_kwh <= flexible.total_pv_available_kwh + 1e-6
    assert flexible.terminal_soc_deviation_kwh <= 1e-6
    background_peak = max(
        float(artifact.community["community_load_kw"].iloc[:36].max())
        for artifact in artifacts
    )
    assert flexible.minimum_background_gross_headroom_kw == pytest.approx(
        max(flexible.pcc_capacity_kw - background_peak, 0.0)
    )


def test_exclusive_bess_sensitivity_prohibits_simultaneous_dispatch(tmp_path: Path) -> None:
    config = _short_pv_scenario_config()
    artifact = load_frozen_hourly_scenario(
        str(freeze_hourly_scenario(config, seed=83, output_directory=tmp_path)["output"])
    )
    portfolio = CommunityPortfolio(
        pv_enabled=True,
        pv_rated_kw=300.0,
        bess_enabled=True,
        bess_power_kw=100.0,
        bess_energy_kwh=200.0,
        bess_dispatch_mode="milp_exclusive",
    )

    solution = solve_frozen_hosting_capacity(
        [artifact],
        portfolio=portfolio,
        dc_operation="flexible",
    )

    assert solution.bess_dispatch_mode == "milp_exclusive"
    assert solution.maximum_simultaneous_bess_charge_discharge_kw <= 1e-6


def test_hosting_matrix_exports_all_eight_portfolios(tmp_path: Path) -> None:
    config = _short_pv_scenario_config()
    scenario_directory = tmp_path / "scenarios"
    freeze_hourly_scenario(config, seed=91, output_directory=scenario_directory)
    portfolio = CommunityPortfolio(
        pv_enabled=True,
        pv_rated_kw=300.0,
        bess_enabled=True,
        bess_power_kw=100.0,
        bess_energy_kwh=200.0,
    )

    result = compute_and_save_hosting_capacity(
        scenario_directory,
        portfolio=portfolio,
        output_directory=tmp_path / "result",
    )

    frame = pd.read_parquet(result["result"])
    assert len(frame) == 8
    assert set(
        zip(frame["pv_enabled"], frame["bess_enabled"], frame["dc_operation"], strict=True)
    ) == {
        (pv, bess, operation)
        for pv in (False, True)
        for bess in (False, True)
        for operation in ("rigid", "flexible")
    }
    assert (frame["hosting_capacity_gain_vs_rigid_kw"] >= -1e-6).all()
    assert (frame["hosting_capacity_multiplier_vs_rigid"] >= 1.0 - 1e-6).all()
