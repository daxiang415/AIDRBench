"""Auditable operator-economics primitives for AIDRBench.

The package deliberately separates a technically feasible demand-response
commitment from the incremental cost of offering that commitment.  It does not
assign the depreciation of an already-installed fleet to each dispatched event.
"""

from aidrbench.economics.accounting import AnnualEconomicInputs, annual_economic_value
from aidrbench.economics.capital import annualized_reserve_cost, capital_recovery_factor
from aidrbench.economics.opportunity_cost import incremental_opportunity_cost

__all__ = [
    "AnnualEconomicInputs",
    "annual_economic_value",
    "annualized_reserve_cost",
    "capital_recovery_factor",
    "incremental_opportunity_cost",
]
