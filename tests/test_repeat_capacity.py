from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from aidrbench.evaluation.repeat_capacity import (
    baseline_service_gate,
    deadline_features,
    event_starts,
    series_ledger,
)


def test_no_response_gate_uses_physical_limit_not_a_declined_dr_contract() -> None:
    frame = pd.DataFrame(
        {
            "pcc_power_kw": [800.0, 820.0],
            "limit_violation_kw": [40.0, 40.0],
            "terminal_backlog_excess_fraction": [0.0, 0.0],
        }
    )
    assert baseline_service_gate(frame, 0.0, 1000.0)
    assert not baseline_service_gate(frame, 0.02, 1000.0)
    assert not baseline_service_gate(frame, 0.0, 810.0)


def test_equal_backlog_does_not_imply_equal_deadline_pressure() -> None:
    urgent = np.zeros(48)
    patient = np.zeros(48)
    urgent[0] = patient[23] = 200.0
    urgent_state = deadline_features(urgent, 100.0, 4)
    patient_state = deadline_features(patient, 100.0, 4)
    assert urgent_state["deadline_pressure"] == 2.0
    assert patient_state["deadline_pressure"] == pytest.approx(1 / 12)
    assert urgent_state["event_due_fraction"] == 1.0
    assert patient_state["event_due_fraction"] == 0.0


def test_four_call_series_ledger_integrates_shared_recovery_hours_once() -> None:
    baseline = pd.DataFrame(
        {
            "hour": range(6),
            "baseline_pcc_power_kw": [10.0] * 6,
            "pcc_power_kw": [10.0] * 6,
            "arrival_gpu_h": [1.0] * 6,
            "community_power_kw": [5.0] * 6,
            "backlog_gpu_h": [0.0] * 6,
            "executed_gpu_h": [1.0] * 6,
            "missed_gpu_h": [0.0] * 6,
        }
    )
    controlled = baseline.copy()
    controlled["event_active"] = [False, True, True, True, True, False]
    controlled["pcc_power_kw"] = [10, 8, 8, 8, 8, 18]
    controlled["backlog_gpu_h"] = [0, 1, 2, 3, 4, 0]
    controlled["executed_gpu_h"] = [1, 0, 0, 0, 0, 5]
    ledger = series_ledger(controlled, baseline, 2.0, 1)
    assert ledger["event_hours"] == 4
    assert ledger["delay_exposure_gpu_h_h"] == 10
    assert ledger["incremental_energy_kwh"] == 0
    assert ledger["capped_delivered_energy_kwh"] == 8
    assert ledger["deferred_work_gpu_h"] == 4
    assert ledger["terminal_incremental_backlog_gpu_h"] == 0
    baseline.loc[1, "arrival_gpu_h"] = 2
    with pytest.raises(ValueError, match="paired inputs mismatch"):
        series_ledger(controlled, baseline, 2.0, 1)


def test_repeated_clock_schedule_keeps_last_call_in_main_horizon() -> None:
    assert event_starts(8, 24) == [63, 95, 127, 159]
    with pytest.raises(ValueError, match="last event exceeds"):
        event_starts(8, 25)
