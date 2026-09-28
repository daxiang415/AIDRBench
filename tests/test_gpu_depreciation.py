"""Guard the distinction between total fleet cost and incremental DR cost."""
import math

import pytest

from aidrbench.economics.capital import (
    gpu_annual_equivalent_cost,
    gpu_straight_line_depreciation,
)


def test_fleet_charge_continues_during_idle_time_but_shared_cost_cancels():
    kwargs = dict(gpu_count=576, unit_cost_usd=10000, useful_life_years=4, salvage_fraction=.1)
    no_dr = gpu_straight_line_depreciation(**kwargs)
    with_dr = gpu_straight_line_depreciation(**kwargs)
    assert no_dr == 1_296_000
    assert with_dr - no_dr == 0


def test_one_four_gpu_node_adds_only_its_own_depreciation():
    common = dict(unit_cost_usd=10000, useful_life_years=4, salvage_fraction=.1)
    assert (
        gpu_straight_line_depreciation(gpu_count=580, **common)
        - gpu_straight_line_depreciation(gpu_count=576, **common)
    ) == 9000


def test_unfinanced_capital_recovery_equals_depreciation():
    kwargs = dict(gpu_count=4, unit_cost_usd=10000, useful_life_years=4, salvage_fraction=.1)
    assert gpu_annual_equivalent_cost(
        **kwargs, discount_rate=0, annual_om_fraction=0
    ) == gpu_straight_line_depreciation(**kwargs)
    funded = gpu_annual_equivalent_cost(**kwargs, discount_rate=.08, annual_om_fraction=.03)
    # Discounted recovery payments plus the salvage proceeds recover the purchase.
    recovered = sum((funded - 1200) / 1.08**year for year in range(1, 5)) + 4000 / 1.08**4
    assert recovered == pytest.approx(40000)


@pytest.mark.parametrize('change', [
    {'gpu_count': -1}, {'gpu_count': 1.5}, {'gpu_count': True},
    {'unit_cost_usd': math.nan}, {'useful_life_years': 0}, {'salvage_fraction': 1.1},
])
def test_invalid_asset_assumptions_are_rejected(change):
    kwargs = dict(gpu_count=576, unit_cost_usd=10000, useful_life_years=4, salvage_fraction=.1)
    with pytest.raises(ValueError):
        gpu_straight_line_depreciation(**(kwargs | change))
