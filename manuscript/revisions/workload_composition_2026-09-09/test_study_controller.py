"""Regression for a delivery-normalised rebound cap, including float32 actions."""
from types import SimpleNamespace
import numpy as np
from aidrbench.controllers.hourly import HourlyRobustMPCController
from study_controller_v4 import DeliveryConsistentRobustMPC


def test_recovery_cap_respects_actual_delivery_denominator(monkeypatch):
    monkeypatch.setattr(HourlyRobustMPCController,'act',lambda self,env,info:np.array([1.],dtype=np.float32))
    env=SimpleNamespace(config=SimpleNamespace(reward=SimpleNamespace(max_rebound_ratio=.25,min_delivery_ratio=.95,min_window_peak_relief_fraction=.5)))
    controller=DeliveryConsistentRobustMPC()
    state=dict(recovery_active=True,event_active=False,event_request_reference_kw=10.,
        baseline_pcc_power_current_kw=600.,running_window_baseline_peak_kw=650.,community_power_kw=400.,rigid_dc_power_kw=150.,worst_class_peak_kw=250.)
    action=controller.act(env,dict(control_state=state))
    rebound=(550.+100.*float(action[0]))-600.
    assert rebound/(.95*10.)<=.25+1e-12
    assert abs(float(action[0])-.52375)<1e-6
    assert (602.5-600.)/(.95*10.)>.25  # The former requested-power cap fails.


def test_non_recovery_action_is_unchanged(monkeypatch):
    proposed=np.array([.5],dtype=np.float32)
    monkeypatch.setattr(HourlyRobustMPCController,'act',lambda self,env,info:proposed)
    controller=DeliveryConsistentRobustMPC()
    assert controller.act(None,dict(control_state=dict(recovery_active=False,event_active=False))) is proposed


def test_event_guard_rounds_float32_to_feasible_side(monkeypatch):
    monkeypatch.setattr(HourlyRobustMPCController,'act',lambda self,env,info:np.array([1.],dtype=np.float32))
    env=SimpleNamespace(config=SimpleNamespace(reward=SimpleNamespace(min_delivery_ratio=.95)))
    state=dict(recovery_active=False,event_active=True,event_request_reference_kw=10.,
        baseline_pcc_power_current_kw=600.,community_power_kw=400.,rigid_dc_power_kw=150.,worst_class_peak_kw=250.)
    a=DeliveryConsistentRobustMPC().act(env,dict(control_state=state))
    assert 600-(550+100*float(a[0]))>=9.5
