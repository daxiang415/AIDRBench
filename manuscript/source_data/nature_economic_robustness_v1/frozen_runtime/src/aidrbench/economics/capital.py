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
