"""Correct the recovery cap to match the existing actual-delivery denominator.

The original controller and certificate runtime remain unchanged. This subclass
uses the same MPC and a stricter causal recovery cap in the new experiment.
"""
import math
import numpy as np
from aidrbench.controllers.hourly import HourlyRobustMPCController, make_hourly_controller
from aidrbench.controllers.robust_mpc_spec import load_robust_mpc_specification


class DeliveryConsistentRobustMPC(HourlyRobustMPCController):
    def act(self,env,info):
        action=super().act(env,info)
        state=info['control_state']
        if not self.service_envelope_enabled or not (state['recovery_active'] or state['event_active']):
            return action
        request=float(state['event_request_reference_kw'])
        if request<=0:return action
        if not isinstance(action,np.ndarray):
            raise ValueError('This experiment specifies continuous actions')
        # A successful call delivers at least min_delivery_ratio * request.
        # Bounding rebound against that conservative delivered level suffices
        # for a ratio whose denominator is the actual maximum delivered power.
        baseline=float(state['baseline_pcc_power_current_kw'])
        if state['event_active']:
            target=baseline-env.config.reward.min_delivery_ratio*request
        else:
            peak=max(baseline,float(state['running_window_baseline_peak_kw']))
            target=min(baseline+env.config.reward.max_rebound_ratio*env.config.reward.min_delivery_ratio*request,
                peak-env.config.reward.min_window_peak_relief_fraction*request)
        fixed=float(state['community_power_kw'])+float(state['rigid_dc_power_kw'])
        dynamic=max(float(state['worst_class_peak_kw'])-float(state['rigid_dc_power_kw']),1e-9)
        limit=float(np.clip((target-fixed)/dynamic,0.,1.))
        fraction=min(float(action[0]),limit)
        out=np.float32(fraction)
        if float(out)>fraction:out=np.nextafter(out,np.float32(0.))
        self._previous_fraction=float(out)
        return np.array([out],dtype=np.float32)


def make_study_controller(name,*,robust_mpc_specification=None):
    if name!='robust_mpc':return make_hourly_controller(name)
    if robust_mpc_specification is None:raise ValueError('Explicit controller specification required')
    return DeliveryConsistentRobustMPC.from_specification(robust_mpc_specification)
