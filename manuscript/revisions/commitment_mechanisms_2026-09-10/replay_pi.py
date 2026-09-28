"""Recompute a PI diagnosis from packaged inputs; no original workspace required."""
import argparse,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'aidrbench_project/src'))
import numpy as np
from aidrbench.data.frozen_scenarios import load_frozen_hourly_scenario
from aidrbench.evaluation.exhaustion import _repeated_environment_document
from aidrbench.envs.community_ai_dr_env import HourlyCommunityAIDemandResponseEnv
from pi_feasibility_core import solve_snapshot

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--data',type=Path,required=True);ap.add_argument('--previous-data',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--id',default='u65d100g10_985002_f1.0_m0.0');a=ap.parse_args()
    old=json.loads((a.data/'pi_diagnostics'/a.id/'receipt.json').read_text());task=old['task'];role='confirmation' if task['variant'].startswith('u') else 'temporal'
    path=a.previous_data/'recovery_inputs'/role/task['variant']/str(task['seed']);frozen=load_frozen_hourly_scenario(path)
    env=HourlyCommunityAIDemandResponseEnv(_repeated_environment_document(frozen,notice_h=0,requested_reduction_kw=task['request_kw']));env.reset(seed=task['seed']);s=env.full_horizon_planning_snapshot()
    active=np.concatenate([np.arange(e.start_hour,e.stop_hour) for e in s.events]);margin=np.array(s.baseline_pcc_power_kw)-np.array(s.community_power_kw)-s.fixed_dc_power_kw-.95*task['request_kw']
    a.output.mkdir(parents=True,exist_ok=True)
    if margin[active].min() < -1e-7:new=dict(classification='instantaneous_supply_infeasible',minimum_supply_margin_kw=float(margin[active].min()))
    else:
        new,hour,extra=solve_snapshot(s,task['request_kw'],task['miss_rate'],time_limit=600)
        if hour is not None:
            hour.to_parquet(a.output/'hourly_witness.parquet',index=False);extra[0].to_parquet(a.output/'execution_edges.parquet',index=False);extra[1].to_parquet(a.output/'work_groups.parquet',index=False)
    extended=a.data/'pi_diagnostics'/a.id/'extended_solve/receipt.json'
    expected=json.loads(extended.read_text())['classification'] if extended.exists() else old['classification']
    assert new['classification']==expected,(new,expected)
    new.update(status='PASS',id=a.id,scope='classification reproduced; feasible schedules may be non-unique')
    (a.output/'replay_validation.json').write_text(json.dumps(new,indent=2)+'\n');print(json.dumps(new,indent=2))

if __name__=='__main__':main()
