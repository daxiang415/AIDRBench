"""Checks for study-critical clock, service and accounting conventions."""
import numpy as np
import pandas as pd
from aidrbench.evaluation.firm_flexibility import EventOutcome
import run_tradeoffs as r
from decompose_costs import quantile_components


def event():
    return EventOutcome(event_id=0,start_hour=63,duration_h=8,requested_reduction_kw=1.,
        delivery_ratio=1.,minimum_interval_delivery_ratio=1.,deadline_miss_rate=.005,
        rebound_peak_kw=0.,rebound_ratio=0.,window_peak_relief_kw=.5,
        window_peak_relief_fraction=.5,terminal_backlog_fraction=0.,recovery_time_h=1.)


def test_clock_anchor_and_complete_active_arrival_windows():
    for seed in range(984000,984100):
        a,b=r.starts(seed,16),r.starts(seed,24)
        assert a[-1]==b[-1]
        assert min(a+b)>=39 and max(a+b)+8+24<=168
        assert np.diff(a).tolist()==[16]*3 and np.diff(b).tolist()==[24]*3
    assert len({r.starts(seed,16)[-1] for seed in range(984000,984100)})>20


def test_zero_deadline_and_baseline_feasibility_are_separate():
    frame=pd.DataFrame({'missed_gpu_h':[.5], 'arrival_gpu_h':[100.]})
    base=dict(baseline_service_feasible=True,baseline_zero_service=True,baseline_miss_rate=0.)
    s=r.score([event()],frame,base)
    assert s['success_1pct'] and not s['success_zero'] and not s['success_01pct']
    base['baseline_service_feasible']=False
    s=r.score([event()],frame,base)
    assert not s['success_1pct'] and not s['success_zero']


def test_cost_quantile_attribution_retains_correlation_and_fixed_shift():
    parts=np.array([[0.,10.],[9.,0.],[3.,8.],[4.,-1.]])
    contribution=quantile_components(parts)
    assert np.isclose(contribution.sum(),np.quantile(parts.sum(axis=1),.95))
    assert not np.isclose(contribution.sum(),np.quantile(parts,.95,axis=0).sum())
    shifted=np.column_stack([parts,np.full(4,25000.)])
    assert np.isclose(quantile_components(shifted).sum()-contribution.sum(),25000.)
