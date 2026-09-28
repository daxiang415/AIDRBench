"""Orthogonal controls around the low-eligibility f10 primary configuration."""
import copy
import json
from pathlib import Path
import pandas as pd
from aidrbench.data.frozen_scenarios import freeze_hourly_scenario, load_frozen_hourly_scenario
from aidrbench.envs.community_ai_dr_env import HourlyCommunityAIDemandResponseEnv
from aidrbench.evaluation.frozen_causal_certificate import _environment_document
from aidrbench.evaluation.hourly_rollout import rollout_hourly_episode
from aidrbench.controllers.hourly import make_hourly_controller
from aidrbench.evaluation.repeat_capacity import baseline_service_gate
from aidrbench.evaluation.pi_frontier import summarize_pi_firm_boundary
import run_study_v3 as m

SPEC=Path(__file__).with_name('secondary_protocol_corrected.json')


def freeze_control(task):
    control,seed=task
    a=load_frozen_hourly_scenario(m.artifact_path('confirmation','f10',seed))
    d=copy.deepcopy(a.config_document)
    case=control['name']
    if 'flexible_gpu_fraction' in control:
        g=control['flexible_gpu_fraction'];d['virtual_datacenter']['flexible_gpu_fraction']=g
        d['virtual_datacenter']['rigid_gpu_utilization']=374.4*.9/(576-round(576*g))
    if 'rigid_proxy_power_w' in control:
        for c in ('online_inference','dev','other','unknown'):
            d['hardware']['active_power_w_per_gpu_by_class'][c]=control['rigid_proxy_power_w']
    path=m.artifact_path('confirmation',case,seed)
    if not (path/'metadata.json').exists():freeze_hourly_scenario(d,seed=seed,output_directory=path.parent)
    b=load_frozen_hourly_scenario(path)
    assert a.arrivals.equals(b.arrivals) and a.community.equals(b.community)
    assert [(x['start_hour'],x['stop_hour'],x['notice_hours']) for x in a.events]==[(x['start_hour'],x['stop_hour'],x['notice_hours']) for x in b.events]
    env=HourlyCommunityAIDemandResponseEnv(_environment_document(b,duration_h=4,notice_h=0,requested_reduction_kw=0,event_id=0))
    baseline,summary=rollout_hourly_episode(env,make_hourly_controller('no_control'),seed=seed)
    baseline=baseline.drop(columns=['controller_action_time_ms']);baseline.to_parquet(path/'no_response_full.parquet',index=False)
    gate=baseline_service_gate(baseline,float(summary['deadline_miss_rate']),1100.)
    return dict(case=case,seed=seed,artifact=str(path),scenario_hash=b.scenario_hash,
                baseline_service_feasible=gate,operating_peak_kw=env.power_model.reference_mix_operating_peak_kw,
                secondary_protocol_sha256=m.sha(SPEC))


def main():
    spec=json.loads(SPEC.read_text());controls=spec['controls'];seeds=list(range(950000,950300))
    rows=m.parallel(freeze_control,[(c,s) for c in controls for s in seeds],32,'controls freeze')
    index=pd.DataFrame(rows);index.to_csv(m.SOURCE/'control_scenario_index.csv',index=False)
    assert index.baseline_service_feasible.all()
    rows=m.parallel(m.pi_task,[('confirmation',c['name'],s) for c in controls for s in seeds[:100]],32,'controls PI')
    df=pd.concat([pd.read_parquet(x) for x in rows]);df.to_csv(m.SOURCE/'control_pi_scenarios.csv',index=False)
    bounds=[]
    for c,g in df.groupby('case'):
        b=summarize_pi_firm_boundary(g,reliability_targets=[.95],confidence_level=.95,nominal_flexibility_fraction=.5)
        b['case']=c;bounds.append(b)
    pd.concat(bounds).to_csv(m.SOURCE/'control_pi_boundaries.csv',index=False)
    selected=pd.read_csv(m.OUT/'single_selected.csv');selected=selected[selected.case=='f10'];tasks=[]
    for c in controls:
        for r in selected.to_dict('records'):
            if r['capacity_kw']>0:
                for s in seeds:tasks.append(dict(role='confirmation',case=c['name'],seed=s,duration_h=r['duration_h'],notice_h=0,capacity_kw=r['capacity_kw'],tag='fixed_primary_request'))
    rows=m.parallel(m.run_task,tasks,32,'controls fixed requests');m.summary(rows).to_csv(m.SOURCE/'control_causal_summary.csv',index=False)
    m.save(m.OUT/'control_confirm_receipts.json',rows)
    rows=m.parallel(m.renewable_task,[(c['name'],s) for c in controls for s in seeds[:100]],32,'controls renewable')
    pd.DataFrame([r for block in rows for r in block]).to_csv(m.SOURCE/'control_renewable_scenarios.csv',index=False)


if __name__=='__main__':main()
