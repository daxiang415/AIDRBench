"""Prospective low-eligibility and explicitly counterfactual high-share extension.

Every simulation has a resumable, hash-bound receipt; previously viewed locked
sets are never used. Run init, pilot, freeze, pi, single_dev, single_select,
single_confirm, repeat_dev, repeat_select, repeat_confirm, renewable in order.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
import multiprocessing
import shutil
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from aidrbench.controllers.hourly import make_hourly_controller
from aidrbench.controllers.robust_mpc_spec import load_robust_mpc_specification
from aidrbench.data.frozen_scenarios import freeze_hourly_scenario, load_frozen_hourly_scenario
from aidrbench.envs.community_ai_dr_env import HourlyCommunityAIDemandResponseEnv
from aidrbench.evaluation.exhaustion import _rollout_exhaustion_program
from aidrbench.evaluation.firm_flexibility import FirmFlexibilityCriteria, derive_event_outcomes, wilson_lower_bound
from aidrbench.evaluation.frozen_causal_certificate import _environment_document
from aidrbench.evaluation.hourly_rollout import rollout_hourly_episode
from aidrbench.evaluation.pi_frontier import solve_frozen_pi_frontier, summarize_pi_firm_boundary
from aidrbench.evaluation.repeat_capacity import series_ledger, baseline_service_gate
from aidrbench.evaluation.hosting_capacity import CommunityPortfolio
from aidrbench.evaluation.renewable_integration import solve_curtailment_constrained_pv_hosting, solve_fixed_capacity_pv_operation

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
OUT=ROOT/'results/nature_mainline/workload_composition_v2'
SOURCE=ROOT/'manuscript/source_data/nature_workload_composition_v1'
PROTOCOL=HERE/'protocol.json'
CRITERIA=FirmFlexibilityCriteria()
CONTROLLER=ROOT/'configs/controller/nature_robust_mpc_v1.yaml'


def sha(path):
    with Path(path).open('rb') as f: return hashlib.file_digest(f,'sha256').hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix('.tmp')
    tmp.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')
    tmp.replace(path)


def protocol(): return json.loads(PROTOCOL.read_text())


def init():
    assert not PROTOCOL.exists(), 'Protocol already frozen; do not overwrite'
    audit=json.loads((SOURCE/'source_audit.json').read_text())
    p=dict(status='prospective_extension_after_v0_19_not_original_preregistration',
        fractions=[.05,.10,.20,.40,.60], source_audit=audit,
        pool_rule='flexible_GPU_fraction_equals_deferrable_work_fraction; integer rounding retained',
        low_share_rule='common_permission_fraction_of_LP_training_and_LP_offline_inference',
        high_40_rule='all_LP_batch_plus_equal_permission_fraction_of_remaining_batch_work; no_online_deferral',
        high_60_rule='counterfactual_replace_online_work_by_offline_work_until_batch_share_is_60%; all_batch_eligible',
        total_gpus=576, total_work_gpu_h_per_hour=374.4,
        rigid_online_and_other_active_power_w=300.0221737132353,
        rigid_power_evidence='engineering_proxy_equal_to_measured_offline_coefficient; not_online_measurement',
        job_shape_scope='existing_LP_class_sampler_and_synthetic_deadlines_for_all_scenarios; HP_opt_in_and_60%_composition_are_counterfactual',
        pairing='generate_f60_job_templates_once_per_seed_then_scale_class_GPUhours; retain_release_times_deadlines_community_and_event_anchor',
        development_seeds=[930000,930099], confirmation_seeds=[940000,940299],
        pilot_seeds=[949998,949999], durations_h=[4,8], notices_h=[0,2,6],
        fractions_of_development_PI_bound=[.5,.75,.9,1.0],
        selection='largest_tested_offer_with_development_one_sided_Wilson95_lower_bound_at_least_0.95; no_confirmation_reselection',
        repeat_programs=[dict(duration_h=4,gap_h=8),dict(duration_h=8,gap_h=12)],
        repeat_first_start=63, repeat_event_count=4,
        repeat_fractions_of_selected_single=[.25,.5,.75,1.0],
        repeat_confirmation=['original_selected_single_offer_repeated','development_selected_repeat_offer','four_separate_same_clock_fresh_calls'],
        renewable_confirmation_seeds=[940000,940099], renewable_pv_kw=500,
        renewable_curtailment=.05, renewable_zero_deadline_miss=True,
        economics=dict(facility_mw=1.,fixed_site_usd_year=25000.,energy_usd_kwh=.1,
            performance_usd_mwh=50.,delay_usd_gpu_h_h=.005,single_annual_calls=50,
            repeat_annual_series=12,bootstrap_draws=2000,risk_quantile=.95,
            regimes=['slack','reserve_15pct_4year','hypothetical_displacement_0.5_USD_per_deferred_GPUh']),
        controller_sha256=sha(CONTROLLER), runner_sha256=sha(__file__),
        source_files={str(x.relative_to(ROOT)):sha(x) for x in [ROOT/'configs/env/nature_mainline_development.yaml',ROOT/'configs/env/nature_mainline_validation.yaml',ROOT/'data/calibration/rtx6000pro_4gpu_v1.yaml']})
    save(PROTOCOL,p)
    print('Protocol frozen',sha(PROTOCOL))


def case_definition(f):
    p=protocol(); a=p['source_audit']; shares=dict(a['shares']); lp=a['lp_batch_shares']
    batch=['training','offline_inference']; eligible={c:0. for c in shares}
    limit=sum(lp.values()); total_batch=sum(shares[c] for c in batch)
    if f<=limit:
        for c in batch: eligible[c]=lp[c]*f/limit
        scope='LP_batch_permission_scenario'
    elif f<=total_batch:
        eta=(f-limit)/(total_batch-limit)
        for c in batch: eligible[c]=lp[c]+eta*(shares[c]-lp[c])
        scope='near_all_batch_opt_in_counterfactual'
    else:
        transfer=f-total_batch
        shares['online_inference']-=transfer; shares['offline_inference']+=transfer
        for c in batch: eligible[c]=shares[c]
        scope='batch_enriched_composition_counterfactual'
    assert abs(sum(eligible.values())-f)<1e-12 and eligible['online_inference']==0
    return dict(name=f'f{round(f*100):02d}',fraction=f,scope=scope,shares=shares,
                flexible_fractions={c:eligible[c]/shares[c] for c in shares},eligible_shares=eligible)


def make_document(f,role,seed):
    p=protocol(); case=case_definition(f)
    file='development' if role in ('development','pilot') else 'validation'
    d=yaml.safe_load((ROOT/f'configs/env/nature_mainline_{file}.yaml').read_text())
    d.pop('scenario',None); d['env']['episode_seed_range']=[seed,seed]
    d['community']['pcc_capacity_kw']=p.get('common_pcc_capacity_kw',1000.)
    dc=d['virtual_datacenter']; work=d['workload']; dc['flexible_gpu_fraction']=f
    nflex=round(576*f); dc['rigid_gpu_utilization']=374.4*(1-f)/(576-nflex)
    assert dc['rigid_gpu_utilization']<=1
    work.pop('target_total_utilization',None); work['flexible_arrival_utilization']=.65
    work['workload_mix']={k:case[k] for k in ('shares','flexible_fractions')}
    cal=yaml.safe_load((ROOT/'data/calibration/rtx6000pro_4gpu_v1.yaml').read_text())['parameters']
    powers={c:p['rigid_online_and_other_active_power_w'] for c in case['shares']}
    for c in ('training','offline_inference'): powers[c]=cal['active_power_w_per_gpu_by_class'][c]['estimate_w']
    d['hardware']=dict(require_calibration_artifact=False,active_power_w_per_gpu_by_class=powers,
        fallback_idle_power_w_per_gpu=cal['idle_power_w_per_gpu']['estimate_w'],
        fallback_node_overhead_w=cal['node_fixed_overhead_w']['estimate_w'])
    return d,case


def artifact_path(role,case,seed,program='single'):
    return OUT/role/case/'scenarios'/program/f'hourly_seed_{seed}'


def template_task(task):
    role,seed=task;d,_=make_document(.6,role,seed)
    path=OUT/'templates'/role/f'hourly_seed_{seed}'
    if not (path/'metadata.json').exists():freeze_hourly_scenario(d,seed=seed,output_directory=path.parent)
    return str(path)


def clone_program(parent,path,h,gap):
    if (path/'metadata.json').exists(): return load_frozen_hourly_scenario(path)
    path.mkdir(parents=True,exist_ok=True)
    meta=copy.deepcopy(parent.metadata)
    for name in meta['files']: shutil.copyfile(parent.directory/name,path/name)
    starts=[63+i*(h+gap) for i in range(4)]
    meta['events']=[dict(event_id=i,source_event_id=f'mix_repeat_{i}',start_hour=t,stop_hour=t+h,
        requested_reduction_kw=1.,notice_hours=0.) for i,t in enumerate(starts)]
    meta.pop('scenario_hash'); meta['scenario_hash']=digest(meta)
    save(path/'metadata.json',meta)
    result=load_frozen_hourly_scenario(path)
    for name in ('arrivals.parquet','community.parquet','baseline.parquet'):
        assert result.metadata['files'][name]==parent.metadata['files'][name]
    return result


def freeze_task(task):
    f,role,seed=task; d,c=make_document(f,role,seed); path=artifact_path(role,c['name'],seed)
    parent=load_frozen_hourly_scenario(OUT/'templates'/role/f'hourly_seed_{seed}')
    weights={k:c['eligible_shares'][k]/case_definition(.6)['eligible_shares'][k] for k in ('training','offline_inference')}
    arrivals=parent.arrivals.copy();arrivals['arrival_gpu_h']*=arrivals.job_class.map(weights)
    arrival_path=OUT/role/c['name']/'inputs'/f'{seed}.parquet'
    arrival_path.parent.mkdir(parents=True,exist_ok=True);arrivals.to_parquet(arrival_path,index=False)
    d['workload']['arrivals_path']=str(arrival_path)
    if not (path/'metadata.json').exists(): freeze_hourly_scenario(d,seed=seed,output_directory=path.parent)
    a=load_frozen_hourly_scenario(path)
    assert a.config_document==d
    assert a.arrivals.equals(arrivals) and a.community.equals(parent.community)
    assert a.events[0]['start_hour']==parent.events[0]['start_hour']
    expected=374.4*168*f
    assert abs(a.arrivals.arrival_gpu_h.sum()-expected)<1e-6
    assert set(a.arrivals.job_class)<= {'training','offline_inference'}
    env=HourlyCommunityAIDemandResponseEnv(_environment_document(a,duration_h=4,notice_h=0,requested_reduction_kw=0,event_id=0))
    baseline_path=path/'no_response_full.parquet'
    if baseline_path.exists():
        baseline=pd.read_parquet(baseline_path)
        miss=float(baseline.missed_gpu_h.sum())/expected
    else:
        baseline,summary=rollout_hourly_episode(env,make_hourly_controller('no_control'),seed=seed)
        baseline=baseline.drop(columns=['controller_action_time_ms'])
        baseline.to_parquet(baseline_path,index=False); miss=float(summary['deadline_miss_rate'])
    gate=baseline_service_gate(baseline,miss,env.config.pcc_capacity_kw)
    for item in protocol()['repeat_programs']:
        h,gap=item['duration_h'],item['gap_h']
        clone_program(a,artifact_path(role,c['name'],seed,f'H{h}G{gap}'),h,gap)
    return dict(case=c['name'],fraction=f,role=role,seed=seed,artifact=str(path),
        scenario_hash=a.scenario_hash,baseline_service_feasible=gate,baseline_deadline_miss_rate=miss,
        operating_peak_kw=env.power_model.reference_mix_operating_peak_kw,
        flexible_gpu_count=round(576*f),rigid_gpu_count=576-round(576*f),
        total_flexible_gpu_h=expected,scope=c['scope'])


def pi_task(task):
    role,case,seed=task; path=OUT/role/case/'pi'/f'{seed}.parquet'
    if not path.exists():
        a=load_frozen_hourly_scenario(artifact_path(role,case,seed))
        df=solve_frozen_pi_frontier(a,durations_h=[4,8])
        df['case']=case;df['role']=role
        path.parent.mkdir(parents=True,exist_ok=True);df.to_parquet(path,index=False)
    return str(path)


def run_task(t):
    role,case,seed=t['role'],t['case'],t['seed']; h=t['duration_h']; program=t.get('program','single')
    tag=t['tag']; path=OUT/role/case/'runs'/f'{program}_{tag}_H{h}_N{t.get("notice_h",0)}_{seed}.json'
    identity=digest(dict(task=t,protocol_sha256=sha(PROTOCOL)))
    if path.exists():
        r=json.loads(path.read_text()); assert r['identity']==identity
        assert sha(r['trace_path'])==r['trace_sha256']; return r
    a=load_frozen_hourly_scenario(artifact_path(role,case,seed,program))
    if program=='single':
        env=HourlyCommunityAIDemandResponseEnv(_environment_document(a,duration_h=h,
            notice_h=t.get('notice_h',0),requested_reduction_kw=t['capacity_kw'],event_id=0))
        controller=make_hourly_controller('robust_mpc',robust_mpc_specification=load_robust_mpc_specification(CONTROLLER))
        frame,_=rollout_hourly_episode(env,controller,seed=seed)
        outcomes=derive_event_outcomes(frame,env.event_manifest,recovery_tolerance_gpu_h=
            env.config.recovery_backlog_tolerance_fraction*env.power_model.flexible_capacity_gpu_h)
    else:
        frame,outcomes=_rollout_exhaustion_program(a,capacity_kw=t['capacity_kw'],
            controller_config=str(CONTROLLER),event_ids=t.get('event_ids'))
    frame=frame.drop(columns=['controller_action_time_ms'])
    baseline=pd.read_parquet(artifact_path(role,case,seed)/'no_response_full.parquet')
    events=[dict(**asdict(o),success=o.success(CRITERIA)[0],failures=list(o.success(CRITERIA)[1])) for o in outcomes]
    path.parent.mkdir(parents=True,exist_ok=True);trace=path.with_suffix('.parquet');frame.to_parquet(trace,index=False)
    r=dict(identity=identity,task=t,scenario_hash=a.scenario_hash,success=all(e['success'] for e in events),
        events=events,ledger=series_ledger(frame,baseline,t['capacity_kw'],outcomes[0].start_hour),
        trace_path=str(trace),trace_sha256=sha(trace))
    save(path,r);return r


def parallel(fn,tasks,workers,label):
    start=time.monotonic(); rows=[]
    with ProcessPoolExecutor(max_workers=workers,mp_context=multiprocessing.get_context('spawn')) as pool:
        futures=[pool.submit(fn,t) for t in tasks]
        for future in as_completed(futures):
            rows.append(future.result())
            if len(rows)%max(1,len(tasks)//20)==0 or len(rows)==len(tasks):
                print(f'{label}: {len(rows)}/{len(tasks)}; {time.monotonic()-start:.1f}s',flush=True)
    return rows


def renewable_task(t):
    case,seed=t;path=OUT/'renewable'/case/f'{seed}.json'
    if path.exists():return json.loads(path.read_text())
    a=load_frozen_hourly_scenario(artifact_path('confirmation',case,seed));rows=[]
    for bess in (False,True):
        port=CommunityPortfolio(pv_enabled=True,pv_rated_kw=500.,bess_enabled=bess,
            bess_power_kw=100. if bess else 0.,bess_energy_kwh=200. if bess else 0.,bess_dispatch_mode='milp_exclusive')
        for operation in ('rigid','flexible'):
            for analysis in ('hosting','operation'):
                opts=dict(portfolio=port,dc_operation=operation,dc_scale_of_reference_mix=1.,max_deadline_miss_rate=0.)
                result=(solve_curtailment_constrained_pv_hosting(a,maximum_pv_curtailment_fraction=.05,**opts)
                    if analysis=='hosting' else solve_fixed_capacity_pv_operation(a,pv_rated_kw=500.,**opts))
                row=dict(case=case,seed=seed,bess_enabled=bess,dc_operation=operation,analysis=analysis)
                row.update(result.summary() if result else dict(status='infeasible'))
                rows.append(row)
    save(path,rows);return rows


def summary(rows):
    records=[]
    for r in rows:
        t=r['task']; records.append({k:v for k,v in t.items() if k!='event_ids'}|dict(success=r['success']))
    d=pd.DataFrame(records);keys=[k for k in ('case','duration_h','program','tag','notice_h','capacity_kw') if k in d]
    d[keys]=d[keys].fillna({'program':'single','notice_h':0})
    s=d.groupby(keys,dropna=False).success.agg(['sum','size']).reset_index().rename(columns={'sum':'successes','size':'trials'})
    s['wilson_lower']=s.apply(lambda r:wilson_lower_bound(int(r.successes),int(r.trials),.95),axis=1)
    s['qualified']=s.wilson_lower>=.95
    return s


def main():
    parser=argparse.ArgumentParser();parser.add_argument('stage');parser.add_argument('--workers',type=int,default=24)
    args=parser.parse_args();stage=args.stage
    if stage=='init':init();return
    p=protocol();OUT.mkdir(parents=True,exist_ok=True)
    cases=[case_definition(f)['name'] for f in p['fractions']]
    seeds={r:list(range(p[r+'_seeds'][0],p[r+'_seeds'][1]+1)) for r in ('development','confirmation')}
    if stage=='pilot':
        for f in [.1,.6]:
            c=case_definition(f)['name'];seed=949999;template_task(('pilot',seed));print(freeze_task((f,'pilot',seed)),flush=True)
            print(pi_task(('pilot',c,seed)),flush=True)
            for h in (4,8):print(run_task(dict(role='pilot',case=c,seed=seed,duration_h=h,capacity_kw=3.,tag='pilot'))['success'],flush=True)
        return
    if stage=='templates':
        parallel(template_task,[(r,s) for r in seeds for s in seeds[r]],args.workers,stage)
    elif stage=='freeze':
        rows=parallel(freeze_task,[(f,r,s) for r in seeds for s in seeds[r] for f in p['fractions']],args.workers,stage)
        d=pd.DataFrame(rows).sort_values(['role','case','seed']);d.to_parquet(OUT/'scenario_index.parquet',index=False)
        assert d.baseline_service_feasible.all(), 'Retain failures; do not proceed silently'
    elif stage=='pi':
        rows=parallel(pi_task,[(r,c,s) for r in seeds for c in cases for s in seeds[r][:100]],args.workers,stage)
        d=pd.concat([pd.read_parquet(x) for x in rows],ignore_index=True);d.to_parquet(OUT/'pi_scenarios.parquet',index=False)
        tables=[]
        for (c,r),g in d.groupby(['case','role']):
            b=summarize_pi_firm_boundary(g,reliability_targets=[.95],confidence_level=.95,nominal_flexibility_fraction=.5)
            b['case']=c;b['role']=r;tables.append(b)
        pd.concat(tables).to_csv(OUT/'pi_boundaries.csv',index=False)
    elif stage in ('single_dev','single_confirm','repeat_dev','repeat_confirm'):
        tasks=[];dev=stage.endswith('dev');role='development' if dev else 'confirmation'
        if stage=='single_dev':
            caps=pd.read_csv(OUT/'pi_boundaries.csv');caps=caps[caps.role=='development']
            for row in caps.to_dict('records'):
                for frac in p['fractions_of_development_PI_bound']:
                    for s in seeds[role]:tasks.append(dict(role=role,case=row['case'],seed=s,duration_h=row['duration_h'],
                        capacity_kw=row['perfect_information_firm_capacity_kw']*frac,tag=f'fraction{frac}'))
        else:
            single=pd.read_csv(OUT/'single_selected.csv')
            for row in single.to_dict('records'):
                if row['capacity_kw']<=0:continue
                c,h,cap=row['case'],row['duration_h'],row['capacity_kw']
                if stage=='single_confirm':
                    for notice in p['notices_h']:
                        for s in seeds[role]:tasks.append(dict(role=role,case=c,seed=s,duration_h=h,capacity_kw=cap,notice_h=notice,tag='selected'))
                else:
                    item=next(x for x in p['repeat_programs'] if x['duration_h']==h);program=f'H{h}G{item["gap_h"]}'
                    if stage=='repeat_dev':
                        for frac in p['repeat_fractions_of_selected_single']:
                            for s in seeds[role]:tasks.append(dict(role=role,case=c,seed=s,duration_h=h,program=program,capacity_kw=cap*frac,tag=f'fraction{frac}'))
                    else:
                        rep=pd.read_csv(OUT/'repeat_selected.csv');chosen=rep[(rep.case==c)&(rep.duration_h==h)].iloc[0].capacity_kw
                        for s in seeds[role]:
                            tasks.append(dict(role=role,case=c,seed=s,duration_h=h,program=program,capacity_kw=cap,tag='single_offer_repeated'))
                            if chosen>0 and abs(chosen-cap)>1e-12:tasks.append(dict(role=role,case=c,seed=s,duration_h=h,program=program,capacity_kw=chosen,tag='selected_repeat'))
                            for eid in range(4):tasks.append(dict(role=role,case=c,seed=s,duration_h=h,program=program,capacity_kw=cap,tag=f'fresh{eid}',event_ids=[eid]))
        rows=parallel(run_task,tasks,args.workers,stage);summary(rows).to_csv(OUT/f'{stage}_summary.csv',index=False)
        save(OUT/f'{stage}_receipts.json',rows)
    elif stage in ('single_select','repeat_select'):
        name=stage.split('_')[0];d=pd.read_csv(OUT/f'{name}_dev_summary.csv');selected=[]
        for (c,h),g in d.groupby(['case','duration_h']):
            ok=g[g.qualified];cap=float(ok.capacity_kw.max()) if len(ok) else 0.
            selected.append(dict(case=c,duration_h=int(h),capacity_kw=cap,development_source_sha256=sha(OUT/f'{name}_dev_summary.csv')))
        pd.DataFrame(selected).to_csv(OUT/f'{name}_selected.csv',index=False)
        print(pd.DataFrame(selected).to_string(index=False),flush=True)
    elif stage=='renewable':
        rows=parallel(renewable_task,[(c,s) for c in cases for s in seeds['confirmation'][:100]],args.workers,stage)
        pd.DataFrame([r for block in rows for r in block]).to_csv(OUT/'renewable_scenarios.csv',index=False)
    else:raise ValueError(stage)


if __name__=='__main__':main()
