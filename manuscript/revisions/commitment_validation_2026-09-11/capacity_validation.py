"""Conditional empirical-week offer selection with held-out simulation draws."""
from __future__ import annotations
import argparse, json, sys
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.path.insert(0,str(HERE.parent/'operating_tradeoffs_2026-09-09'))
import run_tradeoffs as r

OUT=ROOT/'results/nature_mainline/commitment_validation_v1'
SOURCE=ROOT/'manuscript/source_data/nature_commitment_validation_v1'
LOCK=HERE/'capacity_protocol.json'
SELECTION=HERE/'capacity_selection.json'
WEIGHTS=['job_count','resource_gpu_h']
GRID=[1/64,1/32,1/16,1/8,1/4,3/8,1/2,3/4,1.]
COUNTS=ROOT/'manuscript/source_data/nature_commitment_mechanisms_v1/production_hourly_work.csv'
r.OUT=OUT; r.PROTOCOL=LOCK

def week_for(seed):
    return int(np.random.default_rng(seed+2000000).integers(0,8))

def freeze_seed(payload):
    role,seed=payload; week=week_for(seed)
    doc,_=r.m.make_document(.6,role,seed)
    env=r.m.HourlyCommunityAIDemandResponseEnv(doc);env.reset(seed=seed)
    original=env._arrivals.copy(); case=r.m.case_definition(.1)
    hours=pd.read_csv(COUNTS).query('week_index == @week')
    receipts=[]
    for weight in WEIGHTS:
        name=weight; path=r.scenario(role,name,seed)
        if (path/'baseline_receipt.json').exists():
            receipts.append(json.loads((path/'baseline_receipt.json').read_text()));continue
        jobs=original.copy();shape=hours[weight].to_numpy(dtype=float);shape/=shape.mean()
        for cls in ['training','offline_inference']:
            mask=jobs.job_class==cls
            marginal=jobs[mask].groupby('timestamp_index').arrival_gpu_h.sum().reindex(range(168),fill_value=0.)
            assert (marginal>0).all()
            target=shape*(374.4*case['eligible_shares'][cls])
            jobs.loc[mask,'arrival_gpu_h']*=jobs.loc[mask,'timestamp_index'].map(dict(enumerate(target/marginal.to_numpy())))
        jobs=jobs[jobs.arrival_gpu_h>0].sort_values(['timestamp_index','job_class','slack_hours']).reset_index(drop=True)
        jobs['source_mode']='alibaba2020_'+weight+'_conditional_week_mixture'
        input_path=OUT/'arrivals'/role/str(seed)/(weight+'.parquet')
        input_path.parent.mkdir(parents=True,exist_ok=True);jobs.to_parquet(input_path,index=False)
        d,_=r.m.make_document(.1,role,seed);d['workload']['arrivals_path']=str(input_path)
        for key in ['event_start_hour_choices','event_duration_choices','event_notice_choices','event_reduction_fraction_range']:d['dr'].pop(key,None)
        d['dr'].update(source='configured',events_path=None,event_start_hours=r.starts(seed,16),event_duration_hours=8,event_notice_hours=0,event_reduction_kw=1.,event_start_jitter_hours=0)
        r.m.freeze_hourly_scenario(d,seed=seed,output_directory=path.parent)
        parent=r.m.load_frozen_hourly_scenario(path)
        baseline_env=r.m.HourlyCommunityAIDemandResponseEnv(r.m._repeated_environment_document(parent,notice_h=0,requested_reduction_kw=0))
        baseline,summary=r.m.rollout_hourly_episode(baseline_env,r.m.make_hourly_controller('no_control'),seed=seed)
        baseline=baseline.drop(columns=['controller_action_time_ms']);baseline.to_parquet(path/'no_response_full.parquet',index=False)
        receipt=dict(name=name,role=role,seed=seed,week=week,weight=weight,ordering='chronological',gpu_share=.1,utilization=.65,slack_multiplier=1.,
            baseline_missed_gpu_h=float(baseline.missed_gpu_h.sum()),baseline_miss_rate=float(summary['deadline_miss_rate']),
            baseline_service_feasible=r.m.baseline_service_gate(baseline,float(summary['deadline_miss_rate']),baseline_env.config.pcc_capacity_kw),
            baseline_zero_service=float(baseline.missed_gpu_h.sum())<=1e-7,operating_peak_kw=baseline_env.power_model.reference_mix_operating_peak_kw,
            flexible_gpu_count=58,phase=r.starts(seed,16)[-1]-111,total_arrival_gpu_h=float(parent.arrivals.arrival_gpu_h.sum()),
            source=str(path),scenario_hash=parent.scenario_hash,baseline_sha256=r.m.sha(path/'no_response_full.parquet'))
        r.m.save(path/'baseline_receipt.json',receipt);receipts.append(receipt)
    assert abs(receipts[0]['total_arrival_gpu_h']-receipts[1]['total_arrival_gpu_h'])<1e-7
    return receipts

def task(seed,role,weight,fraction):
    return dict(role=role,variant=weight,seed=seed,program='H8P16',fraction=float(fraction),kind='repeated')

def evaluate(task):
    result=r.evaluate(task)
    result['row']['week']=week_for(task['seed'])
    result['row'].update(trace_path=result['trace_path'],trace_sha256=result['trace_sha256'],scenario_path=result['scenario_path'],scenario_hash=result['scenario_hash'])
    return result

def summarize(data):
    rows=[]
    for (weight,fraction),g in data.groupby(['variant','fraction']):
        for endpoint in ['success_1pct','success_zero']:
            n=len(g);s=int(g[endpoint].sum());lb=r.m.wilson_lower_bound(s,n,.95)
            rows.append(dict(weight=weight,fraction=fraction,capacity_kw=r.REFERENCE*fraction,endpoint=endpoint,trials=n,successes=s,wilson_lower=lb,qualified=lb>=.95,
                baseline_failures=int((~g.baseline_service_feasible).sum()),baseline_nonzero=int((~g.baseline_zero_service).sum()),supply_shortages=int((g.instantaneous_supply_shortfall_hours>0).sum())))
    return pd.DataFrame(rows)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('stage',choices=['freeze','development','select','confirmation','analyse']);ap.add_argument('--workers',type=int,default=32);args=ap.parse_args()
    SOURCE.mkdir(parents=True,exist_ok=True);OUT.mkdir(parents=True,exist_ok=True)
    if args.stage=='freeze':
        assert not LOCK.exists() and not (OUT/'runs').exists()
        r.m.save(LOCK,dict(frozen_at_utc=datetime.now(timezone.utc).isoformat(),design_sha256=r.m.sha(HERE/'DESIGN_ZH.md'),runner_sha256=r.m.sha(__file__),parent_runner_sha256=r.m.sha(r.__file__),controller_sha256=r.m.sha(HERE.parent/'repeat_mechanism_2026-09-09/recovery_controller.py'),source_weights_sha256=r.m.sha(COUNTS),
            development_seeds=[1010000,1010099],confirmation_seeds=[1011000,1011299],grid=GRID,reference_capacity_kw=r.REFERENCE,weights=WEIGHTS,week_sampling='independent uniform integer [0,8), RNG seed = simulation seed + 2000000',
            selection='largest grid point with development one-sided Wilson95 >= .95, separately for 1% and zero deadlines; no confirmation reselection',confirmation_comparators=[.5],
            scope='pointwise qualification conditional on eight fixed observed weeks, synthetic job templates and community profiles; not population production-week reliability'))
        print('Protocol frozen',r.m.sha(LOCK),flush=True);return
    p=json.loads(LOCK.read_text());assert p['runner_sha256']==r.m.sha(__file__) and p['parent_runner_sha256']==r.m.sha(r.__file__) and p['source_weights_sha256']==r.m.sha(COUNTS)
    if args.stage=='select':
        assert not SELECTION.exists() and not (OUT/'runs/confirmation').exists()
        summary=summarize(pd.read_csv(OUT/'development_ledgers.csv'));summary.to_csv(SOURCE/'capacity_development_summary.csv',index=False);rows=[]
        for weight in WEIGHTS:
            for endpoint in ['success_1pct','success_zero']:
                g=summary[(summary.weight==weight)&(summary.endpoint==endpoint)&summary.qualified].sort_values('fraction')
                x=None if g.empty else g.iloc[-1]
                rows.append(dict(weight=weight,endpoint=endpoint,selected_fraction=None if x is None else float(x.fraction),selected_capacity_kw=None if x is None else float(x.capacity_kw),development_successes=None if x is None else int(x.successes)))
        tasks=[]
        for seed in range(p['confirmation_seeds'][0],p['confirmation_seeds'][1]+1):
            for weight in WEIGHTS:
                values=set(p['confirmation_comparators'])|{x['selected_fraction'] for x in rows if x['weight']==weight and x['selected_fraction'] is not None}
                tasks.extend(task(seed,'confirmation',weight,f) for f in sorted(values))
        r.m.save(SELECTION,dict(frozen_at_utc=datetime.now(timezone.utc).isoformat(),protocol_sha256=r.m.sha(LOCK),development_sha256=r.m.sha(OUT/'development_ledgers.csv'),confirmation_not_yet_run=True,selections=rows,confirmation_tasks=tasks))
        print(pd.DataFrame(rows).to_string(index=False),flush=True);return
    if args.stage=='analyse':
        data=pd.read_csv(OUT/'confirmation_ledgers.csv');summary=summarize(data);summary.to_csv(SOURCE/'capacity_confirmation_summary.csv',index=False)
        sel=json.loads(SELECTION.read_text());assert sel['protocol_sha256']==r.m.sha(LOCK)
        rows=[]
        for x in sel['selections']:
            y=dict(x)
            if x['selected_fraction'] is None:y.update(confirmation_successes=None,confirmation_lower=None,offerable=False)
            else:
                g=summary[(summary.weight==x['weight'])&(summary.endpoint==x['endpoint'])&np.isclose(summary.fraction,x['selected_fraction'])];assert len(g)==1
                y.update(confirmation_successes=int(g.successes.iloc[0]),confirmation_lower=float(g.wilson_lower.iloc[0]),offerable=bool(g.qualified.iloc[0]))
            rows.append(y)
        pd.DataFrame(rows).to_csv(SOURCE/'capacity_selected_confirmed.csv',index=False)
        data.groupby(['variant','fraction','week']).agg(trials=('seed','size'),successes_1pct=('success_1pct','sum'),successes_zero=('success_zero','sum')).reset_index().to_csv(SOURCE/'capacity_confirmation_by_week.csv',index=False)
        print(pd.DataFrame(rows).to_string(index=False),flush=True);return
    role=args.stage;lo,hi=p[role+'_seeds'];seeds=range(lo,hi+1)
    tasks=[task(s,role,w,f) for s in seeds for w in WEIGHTS for f in GRID] if role=='development' else json.loads(SELECTION.read_text())['confirmation_tasks']
    receipts=r.m.parallel(freeze_seed,[(role,s) for s in seeds],args.workers,'freeze '+role);r.m.save(OUT/f'{role}_baseline_receipts.json',receipts)
    results=r.m.parallel(evaluate,tasks,args.workers,role)
    pd.DataFrame([x['row'] for x in results]).sort_values(['variant','fraction','seed']).to_csv(OUT/f'{role}_ledgers.csv',index=False)
    print('Finished',role,len(results),flush=True)

if __name__=='__main__':main()
