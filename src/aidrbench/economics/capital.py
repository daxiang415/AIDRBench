"""Capital annualisation used only for incremental or reserved DR capacity."""

from __future__ import annotations

import math


def _finite_nonnegative(value: float, *, name: str) -> float:
    numeric = float(value)
    if not math.isfinite(numeric) or numeric < 0.0:
        raise ValueError(f"{name} must be a finite non-negative number")
    return numeric


def capital_recovery_factor(discount_rate: float, economic_life_years: float) -> float:
    """Return the standard capital-recovery factor with a stable zero-rate limit."""

    rate = _finite_nonnegative(discount_rate, name="discount_rate")
    life = _finite_nonnegative(economic_life_years, name="economic_life_years")
    if life <= 0.0:
        raise ValueError("economic_life_years must be positive")
    if rate == 0.0:
        return 1.0 / life
    growth = math.pow(1.0 + rate, life)
    return rate * growth / (growth - 1.0)


def gpu_straight_line_depreciation(
    *, gpu_count: int, unit_cost_usd: float, useful_life_years: float, salvage_fraction: float
) -> float:
    """Annual book depreciation of an in-service GPU cohort, including idle time.

    This is the cohort's total annual charge. An incremental DR charge requires
    subtracting the corresponding no-DR charge. It excludes host and network costs.
    """
    if isinstance(gpu_count, bool) or not isinstance(gpu_count, int) or gpu_count < 0:
        raise ValueError("gpu_count must be a non-negative integer")
    cost = _finite_nonnegative(unit_cost_usd, name="unit_cost_usd")
    life = _finite_nonnegative(useful_life_years, name="useful_life_years")
    salvage = _finite_nonnegative(salvage_fraction, name="salvage_fraction")
    if life == 0 or salvage > 1:
        raise ValueError("useful life must be positive and salvage fraction at most one")
    return gpu_count * cost * (1.0 - salvage) / life


def gpu_annual_equivalent_cost(
    *,
    gpu_count: int,
    unit_cost_usd: float,
    useful_life_years: float,
    salvage_fraction: float,
    discount_rate: float,
    annual_om_fraction: float,
) -> float:
    """Annual equivalent purchase and maintenance cost, an alternative to depreciation.

    Do not add book depreciation to this amount: capital recovery is already included.
    """
    gpu_straight_line_depreciation(
        gpu_count=gpu_count,
        unit_cost_usd=unit_cost_usd,
        useful_life_years=useful_life_years,
        salvage_fraction=salvage_fraction,
    )
    rate = _finite_nonnegative(discount_rate, name="discount_rate")
    om = _finite_nonnegative(annual_om_fraction, name="annual_om_fraction")
    capex = gpu_count * unit_cost_usd
    residual_pv = capex * salvage_fraction / math.pow(1.0 + rate, useful_life_years)
    return (capex - residual_pv) * capital_recovery_factor(rate, useful_life_years) + capex * om


def annualized_reserve_cost(
    *,
    reserved_capacity_kw: float,
    installed_cost_per_reserved_kw: float,
    discount_rate: float,
    economic_life_years: float,
    salvage_fraction: float,
    annual_om_fraction: float,
) -> float:
    """Annual equivalent cost of capacity reserved specifically for DR recovery.

    In economic v1, ``reserved_capacity_kw`` is an abstract PCC-side
    sensitivity coordinate.  It does not assert that this many GPU, IT or
    facility kW are purchased.  A later physical conversion from compute
    recovery headroom to IT and PCC power would be required before making that
    claim.  Passing the whole installed fleet is an accounting error, not a
    supported use case.
    """

    capacity = _finite_nonnegative(reserved_capacity_kw, name="reserved_capacity_kw")
    installed_cost = _finite_nonnegative(
        installed_cost_per_reserved_kw,
        name="installed_cost_per_reserved_kw",
    )
    salvage = _finite_nonnegative(salvage_fraction, name="salvage_fraction")
    om_fraction = _finite_nonnegative(annual_om_fraction, name="annual_om_fraction")
    if salvage > 1.0:
        raise ValueError("salvage_fraction must not exceed one")
    if capacity == 0.0:
        return 0.0

    rate = _finite_nonnegative(discount_rate, name="discount_rate")
    life = _finite_nonnegative(economic_life_years, name="economic_life_years")
    if life <= 0.0:
        raise ValueError("economic_life_years must be positive")
    capex = capacity * installed_cost
    salvage_present_value = capex * salvage / math.pow(1.0 + rate, life)
    annualized_capital = (capex - salvage_present_value) * capital_recovery_factor(rate, life)
    return annualized_capital + capex * om_fraction
