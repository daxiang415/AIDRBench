from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from aidrbench.data.frozen_scenarios import freeze_hourly_scenario, load_frozen_hourly_scenario
from aidrbench.evaluation.hosting_capacity import CommunityPortfolio
from aidrbench.evaluation.renewable_integration import (
    solve_curtailment_constrained_pv_hosting,
    solve_fixed_capacity_pv_operation,
)

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/env/hourly_continuous.yaml"


def _artifact(tmp_path: Path):
    document = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    assert isinstance(document, dict)
    assert isinstance(document["env"], dict)
    assert isinstance(document["community"], dict)
    assert isinstance(document["dr"], dict)
    document["env"]["episode_days"] = 1
    document["env"]["clearance_tail_hours"] = 12
    document["community"]["pv_enabled"] = True
    document["dr"]["event_start_hours"] = [8]
    document["dr"]["event_duration_hours"] = 2
    document["dr"]["recovery_window_hours"] = 8
    path = freeze_hourly_scenario(document, seed=731, output_directory=tmp_path)["output"]
    return load_frozen_hourly_scenario(path)


def _portfolio(*, bess_enabled: bool) -> CommunityPortfolio:
    return CommunityPortfolio(
        pv_enabled=True,
        pv_rated_kw=300.0,
        bess_enabled=bess_enabled,
        bess_power_kw=100.0 if bess_enabled else 0.0,
        bess_energy_kwh=200.0 if bess_enabled else 0.0,
        bess_dispatch_mode="milp_exclusive",
    )


def test_pv_hosting_is_curtailment_constrained_and_flexibility_does_not_reduce_it(
    tmp_path: Path,
) -> None:
    artifact = _artifact(tmp_path)
    portfolio = _portfolio(bess_enabled=False)
    rigid = solve_curtailment_constrained_pv_hosting(
        artifact,
        portfolio=portfolio,
        dc_operation="rigid",
        dc_scale_of_reference_mix=0.5,
        maximum_pv_curtailment_fraction=0.05,
    )
    flexible = solve_curtailment_constrained_pv_hosting(
        artifact,
        portfolio=portfolio,
        dc_operation="flexible",
        dc_scale_of_reference_mix=0.5,
        maximum_pv_curtailment_fraction=0.05,
    )

    assert rigid is not None
    assert flexible is not None
    assert rigid.total_pv_curtailed_kwh <= 0.05 * rigid.total_pv_available_kwh + 1e-5
    assert flexible.total_pv_curtailed_kwh <= 0.05 * flexible.total_pv_available_kwh + 1e-5
    assert flexible.pv_rated_kw >= rigid.pv_rated_kw - 1e-5


def test_pv_hosting_is_weakly_monotone_in_allowed_curtailment(tmp_path: Path) -> None:
    artifact = _artifact(tmp_path)
    portfolio = _portfolio(bess_enabled=False)
    strict = solve_curtailment_constrained_pv_hosting(
        artifact,
        portfolio=portfolio,
        dc_operation="flexible",
        dc_scale_of_reference_mix=1.0,
        maximum_pv_curtailment_fraction=0.0,
    )
    relaxed = solve_curtailment_constrained_pv_hosting(
        artifact,
        portfolio=portfolio,
        dc_operation="flexible",
        dc_scale_of_reference_mix=1.0,
        maximum_pv_curtailment_fraction=0.20,
    )

    assert strict is not None
    assert relaxed is not None
    assert relaxed.pv_rated_kw >= strict.pv_rated_kw - 1e-5


def test_fixed_capacity_dispatch_reports_pv_and_service_metrics(tmp_path: Path) -> None:
    artifact = _artifact(tmp_path)
    portfolio = _portfolio(bess_enabled=True)
    solution = solve_fixed_capacity_pv_operation(
        artifact,
        portfolio=portfolio,
        dc_operation="flexible",
        dc_scale_of_reference_mix=1.0,
        pv_rated_kw=300.0,
    )

    assert solution.status == "optimal"
    assert solution.pv_rated_kw == pytest.approx(300.0)
    assert 0.0 <= solution.pv_utilisation_fraction <= 1.0 + 1e-8
    assert solution.total_pv_curtailed_kwh == pytest.approx(
        solution.total_pv_available_kwh - solution.total_pv_used_kwh,
        abs=1e-5,
    )
    assert solution.maximum_pcc_import_kw <= solution.pcc_capacity_kw + 1e-6
    assert solution.maximum_simultaneous_bess_charge_discharge_kw <= 1e-6
    assert solution.terminal_soc_deviation_kwh <= 1e-6
    assert solution.deadline_miss_fraction <= 0.01 + 1e-6


def test_renewable_analysis_rejects_relaxed_battery_dispatch(tmp_path: Path) -> None:
    artifact = _artifact(tmp_path)
    portfolio = CommunityPortfolio(
        pv_enabled=True,
        pv_rated_kw=300.0,
        bess_enabled=True,
        bess_power_kw=100.0,
        bess_energy_kwh=200.0,
        bess_dispatch_mode="convex_relaxation",
    )

    with pytest.raises(ValueError, match="milp_exclusive"):
        solve_fixed_capacity_pv_operation(
            artifact,
            portfolio=portfolio,
            dc_operation="flexible",
            dc_scale_of_reference_mix=1.0,
            pv_rated_kw=300.0,
        )
