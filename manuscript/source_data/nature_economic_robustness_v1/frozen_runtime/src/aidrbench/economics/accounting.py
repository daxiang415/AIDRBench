"""Transparent annual operator-economics accounting for a fixed DR offer."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal

from aidrbench.economics.capital import annualized_reserve_cost
from aidrbench.economics.opportunity_cost import (
    delay_cost,
    incremental_opportunity_cost,
    service_cost,
)
from aidrbench.economics.tariffs import (
    capacity_revenue,
    energy_value,
    performance_revenue,
)

ParticipationRegime = Literal[
    "slack_backed",
    "reserved_headroom",
    "throughput_displacing",
]


@dataclass(frozen=True, slots=True)
class AnnualEconomicInputs:
    """All quantities needed for one annualised technical-economic draw.

    Event metrics are aggregate annual quantities; all currency values must be
    in the declared common currency year. ``annual_capped_delivered_energy_kwh``
    is the paid quantity after interval-level capping at the offer; raw physical
    over-delivery is intentionally excluded from accounting. The class contains
    no fleet-wide depreciation input.
    """

    regime: ParticipationRegime
    offered_capacity_kw: float
    technical_capacity_ceiling_kw: float
    annual_event_count: int
    annual_capped_delivered_energy_kwh: float
    annual_shortfall_energy_kwh: float
    annual_deferred_gpu_h: float
    annual_backlog_area_gpu_h_h: float
    annual_incremental_energy_kwh: float
    annual_missed_gpu_h: float
    annual_terminal_backlog_gpu_h: float
    annual_failure_count: float
    capacity_payment_per_kw_year: float
    performance_payment_per_mwh: float
    electricity_price_per_kwh: float
    flexible_connection_value_per_year: float
    fixed_site_enablement_annual_cost: float
    variable_enablement_cost_per_offer_kw: float
    checkpoint_cost_per_event: float
    reserved_capacity_fraction: float
    installed_cost_per_reserved_kw: float
    discount_rate: float
    economic_life_years: float
    salvage_fraction: float
    annual_om_fraction: float
    opportunity_exposure_alpha: float
    value_per_gpu_h: float
    delay_cost_per_gpu_h_h: float
    missed_work_cost_per_gpu_h: float
    terminal_backlog_cost_per_gpu_h: float
    shortfall_penalty_per_mwh: float
    failure_penalty_per_event: float

    def __post_init__(self) -> None:
        if self.offered_capacity_kw < 0.0:
            raise ValueError("offered_capacity_kw must be non-negative")
        if self.technical_capacity_ceiling_kw < 0.0:
            raise ValueError("technical_capacity_ceiling_kw must be non-negative")
        if self.offered_capacity_kw > self.technical_capacity_ceiling_kw + 1e-9:
            raise ValueError("economically offered capacity cannot exceed the technical ceiling")
        if self.annual_event_count <= 0:
            raise ValueError("annual_event_count must be positive")
        if self.fixed_site_enablement_annual_cost < 0.0:
            raise ValueError("fixed_site_enablement_annual_cost must be non-negative")
        if self.variable_enablement_cost_per_offer_kw < 0.0:
            raise ValueError("variable_enablement_cost_per_offer_kw must be non-negative")
        if not 0.0 <= self.reserved_capacity_fraction <= 1.0:
            raise ValueError("reserved_capacity_fraction must lie in [0, 1]")
        if not 0.0 <= self.opportunity_exposure_alpha <= 1.0:
            raise ValueError("opportunity_exposure_alpha must lie in [0, 1]")
        if self.regime == "slack_backed" and (
            self.reserved_capacity_fraction != 0.0 or self.opportunity_exposure_alpha != 0.0
        ):
            raise ValueError("slack_backed participation cannot reserve or displace compute")
        if self.regime == "reserved_headroom" and self.opportunity_exposure_alpha != 0.0:
            raise ValueError("reserved_headroom cannot also charge displaced compute")
        if self.regime == "throughput_displacing" and self.reserved_capacity_fraction != 0.0:
            raise ValueError("throughput_displacing cannot also charge reserve capital")
        if self.opportunity_exposure_alpha > 0.0 and (
            self.missed_work_cost_per_gpu_h > 0.0 or self.terminal_backlog_cost_per_gpu_h > 0.0
        ):
            raise ValueError(
                "opportunity exposure and missed/terminal service pricing overlap; "
                "declare one economic treatment for the same work"
            )

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def annual_economic_value(inputs: AnnualEconomicInputs) -> dict[str, float]:
    """Return an identity-checkable annual revenue and incremental-cost ledger."""

    reserve_capacity_kw = inputs.offered_capacity_kw * inputs.reserved_capacity_fraction
    reserve_cost = annualized_reserve_cost(
        reserved_capacity_kw=reserve_capacity_kw,
        installed_cost_per_reserved_kw=inputs.installed_cost_per_reserved_kw,
        discount_rate=inputs.discount_rate,
        economic_life_years=inputs.economic_life_years,
        salvage_fraction=inputs.salvage_fraction,
        annual_om_fraction=inputs.annual_om_fraction,
    )
    opportunity = incremental_opportunity_cost(
        deferred_gpu_h=inputs.annual_deferred_gpu_h,
        economically_displaced_fraction=inputs.opportunity_exposure_alpha,
        value_per_gpu_h=inputs.value_per_gpu_h,
    )
    delay = delay_cost(
        backlog_area_gpu_h_h=inputs.annual_backlog_area_gpu_h_h,
        value_per_gpu_h_h=inputs.delay_cost_per_gpu_h_h,
    )
    sla = service_cost(
        missed_gpu_h=inputs.annual_missed_gpu_h,
        terminal_backlog_gpu_h=inputs.annual_terminal_backlog_gpu_h,
        missed_work_cost_per_gpu_h=inputs.missed_work_cost_per_gpu_h,
        terminal_backlog_cost_per_gpu_h=inputs.terminal_backlog_cost_per_gpu_h,
    )
    penalty = (
        inputs.annual_shortfall_energy_kwh / 1_000.0 * inputs.shortfall_penalty_per_mwh
        + inputs.annual_failure_count * inputs.failure_penalty_per_event
    )
    capacity = capacity_revenue(
        offered_capacity_kw=inputs.offered_capacity_kw,
        payment_per_kw_year=inputs.capacity_payment_per_kw_year,
    )
    performance = performance_revenue(
        capped_delivered_energy_kwh=inputs.annual_capped_delivered_energy_kwh,
        payment_per_mwh=inputs.performance_payment_per_mwh,
    )
    energy = energy_value(
        incremental_energy_kwh=inputs.annual_incremental_energy_kwh,
        price_per_kwh=inputs.electricity_price_per_kwh,
    )
    checkpoint = inputs.annual_event_count * inputs.checkpoint_cost_per_event
    fixed_site_enablement = (
        inputs.fixed_site_enablement_annual_cost if inputs.offered_capacity_kw > 0.0 else 0.0
    )
    variable_enablement = (
        inputs.variable_enablement_cost_per_offer_kw * inputs.offered_capacity_kw
    )
    enablement = fixed_site_enablement + variable_enablement
    revenues = capacity + performance + energy + inputs.flexible_connection_value_per_year
    costs = (
        enablement
        + reserve_cost
        + opportunity
        + delay
        + sla
        + checkpoint
        + penalty
    )
    delivered_mwh = inputs.annual_capped_delivered_energy_kwh / 1_000.0
    non_capacity_net_cost = costs - (
        performance + energy + inputs.flexible_connection_value_per_year
    )
    non_performance_net_cost = costs - (
        capacity + energy + inputs.flexible_connection_value_per_year
    )
    costs_excluding_fixed_site = costs - fixed_site_enablement
    non_capacity_net_cost_excluding_fixed_site = (
        non_capacity_net_cost - fixed_site_enablement
    )
    non_performance_net_cost_excluding_fixed_site = (
        non_performance_net_cost - fixed_site_enablement
    )
    break_even_capacity = (
        max(non_capacity_net_cost / inputs.offered_capacity_kw, 0.0)
        if inputs.offered_capacity_kw > 0.0
        else float("inf")
    )
    break_even_performance = (
        max(non_performance_net_cost / delivered_mwh, 0.0) if delivered_mwh > 0.0 else float("inf")
    )
    break_even_capacity_excluding_fixed_site = (
        max(non_capacity_net_cost_excluding_fixed_site / inputs.offered_capacity_kw, 0.0)
        if inputs.offered_capacity_kw > 0.0
        else float("inf")
    )
    break_even_performance_excluding_fixed_site = (
        max(non_performance_net_cost_excluding_fixed_site / delivered_mwh, 0.0)
        if delivered_mwh > 0.0
        else float("inf")
    )
    annual_net = revenues - costs
    identity_error = annual_net - (revenues - costs)
    return {
        "capacity_revenue": capacity,
        "performance_revenue": performance,
        "energy_value": energy,
        "flexible_connection_value": inputs.flexible_connection_value_per_year,
        "annual_revenue": revenues,
        "fixed_site_enablement_cost": fixed_site_enablement,
        "variable_enablement_cost": variable_enablement,
        "enablement_cost": enablement,
        "enablement_cost_excluding_fixed_site": variable_enablement,
        "fixed_site_enablement_cost_per_offer_kw": (
            fixed_site_enablement / inputs.offered_capacity_kw
            if inputs.offered_capacity_kw > 0.0
            else 0.0
        ),
        "reserve_annual_cost": reserve_cost,
        "opportunity_cost": opportunity,
        "delay_cost": delay,
        "sla_cost": sla,
        "checkpoint_cost": checkpoint,
        "penalty_cost": penalty,
        "annual_incremental_cost": costs,
        "annual_incremental_cost_excluding_fixed_site": costs_excluding_fixed_site,
        "annual_net_value": annual_net,
        "annual_net_value_excluding_fixed_site": annual_net + fixed_site_enablement,
        "break_even_capacity_payment_per_kw_year": break_even_capacity,
        "break_even_capacity_payment_excluding_fixed_site_per_kw_year": (
            break_even_capacity_excluding_fixed_site
        ),
        "break_even_performance_payment_per_mwh": break_even_performance,
        "break_even_performance_payment_excluding_fixed_site_per_mwh": (
            break_even_performance_excluding_fixed_site
        ),
        "effective_displaced_compute_value_per_gpu_h": (
            inputs.opportunity_exposure_alpha * inputs.value_per_gpu_h
        ),
        "accounting_identity_error": identity_error,
    }
