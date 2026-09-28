"""Market-neutral DR revenue and penalty primitives."""

from __future__ import annotations

import math


def _finite_nonnegative(value: float, *, name: str) -> float:
    numeric = float(value)
    if not math.isfinite(numeric) or numeric < 0.0:
        raise ValueError(f"{name} must be a finite non-negative number")
    return numeric


def capacity_revenue(*, offered_capacity_kw: float, payment_per_kw_year: float) -> float:
    return _finite_nonnegative(offered_capacity_kw, name="offered_capacity_kw") * (
        _finite_nonnegative(payment_per_kw_year, name="payment_per_kw_year")
    )


def performance_revenue(*, capped_delivered_energy_kwh: float, payment_per_mwh: float) -> float:
    """Pay only delivered energy up to the declared DR obligation.

    Raw physical delivery can exceed the offer and remains useful as a
    diagnostic, but it is deliberately not accepted by this payment primitive.
    """

    return (
        _finite_nonnegative(
            capped_delivered_energy_kwh,
            name="capped_delivered_energy_kwh",
        )
        / 1_000.0
    ) * _finite_nonnegative(payment_per_mwh, name="payment_per_mwh")


def energy_value(*, incremental_energy_kwh: float, price_per_kwh: float) -> float:
    """Return savings relative to no-DR: negative incremental use is positive value."""

    energy = float(incremental_energy_kwh)
    if not math.isfinite(energy):
        raise ValueError("incremental_energy_kwh must be finite")
    return -energy * _finite_nonnegative(price_per_kwh, name="price_per_kwh")


def nonperformance_penalty(
    *,
    shortfall_energy_kwh: float,
    failure_probability: float,
    shortfall_penalty_per_mwh: float,
    failure_penalty_per_event: float,
) -> float:
    probability = float(failure_probability)
    if not math.isfinite(probability) or not 0.0 <= probability <= 1.0:
        raise ValueError("failure_probability must lie in [0, 1]")
    return _finite_nonnegative(
        shortfall_energy_kwh, name="shortfall_energy_kwh"
    ) / 1_000.0 * _finite_nonnegative(
        shortfall_penalty_per_mwh, name="shortfall_penalty_per_mwh"
    ) + probability * _finite_nonnegative(
        failure_penalty_per_event,
        name="failure_penalty_per_event",
    )
