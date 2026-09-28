from types import SimpleNamespace
import numpy as np
from recovery_controller import AllWindowController


def environment():
    return SimpleNamespace(config=SimpleNamespace(recovery_window_hours=24,
        reward=SimpleNamespace(min_delivery_ratio=.95,min_window_peak_relief_fraction=.5,max_rebound_ratio=.25)))


def state(baseline,event_id=-1,remaining=0):
    return dict(event_active=event_id>=0,event_id=event_id,event_remaining_hours=remaining,
        requested_reduction_kw=10.,baseline_pcc_power_current_kw=baseline,
        community_power_kw=0.,rigid_dc_power_kw=0.,worst_class_peak_kw=1000.)


def test_all_window_ceiling_survives_overlapping_window_state():
    c=AllWindowController();e=environment()
    c.act(e,{'control_state':state(600.,0,1)})
    c.act(e,{'control_state':state(580.,1,1)})
    a=c.act(e,{'control_state':state(580.)})
    # A previously higher baseline peak must not hide the newer 580-kW window.
    assert float(a[0])*1000<=575.
    assert c.audit[-1]['observed_active_windows']==2


def test_window_expires_and_controller_reset_forgets_history():
    c=AllWindowController();e=environment()
    c.act(e,{'control_state':state(600.,0,1)})
    for _ in range(24):c.act(e,{'control_state':state(600.)})
    a=c.act(e,{'control_state':state(600.)})
    assert float(a[0])==1. and c.audit[-1]['observed_active_windows']==0
    c.reset()
    assert c.calls=={} and c.hour==0 and c.audit==[]


def test_current_call_is_only_source_of_call_knowledge():
    c=AllWindowController();e=environment()
    for _ in range(6):c.act(e,{'control_state':state(600.)})
    assert c.calls=={}
    action=c.act(e,{'control_state':state(600.,0,8)})
    assert c.calls[0].stop_hour==14
    assert action.dtype==np.float32 and float(action[0])*1000<=590.5
