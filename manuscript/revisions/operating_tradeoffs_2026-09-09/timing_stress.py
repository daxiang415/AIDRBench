"""Transport fixed offers to eight observed arrival-count weeks; no refitting."""
from datetime import datetime, timezone
import argparse
import copy
import json
from pathlib import Path
import shutil
import numpy as np
import pandas as pd
import run_tradeoffs as r

SOURCE=r.ROOT/'manuscript/source_data/nature_operating_tradeoffs_v1'
COUNTS=r.ROOT/'results/nature_mainline/repeat_capacity_v1/production_timing/hourly_counts.csv'
LOCK=r.HERE/'temporal_protocol.json'


def freeze_week_rep(payload):
    week,rep=payload;seed=986000+week*100+rep
    root=r.OUT/'temporal_templates'/str(seed);root.mkdir(parents=True,exist_ok=True)
    doc,_=r.m.make_document(.6,'confirmation',seed)
    env=r.m.HourlyCommunityAIDemandResponseEnv(doc);env.reset(seed=seed)
    template=env._arrivals.copy()
    shape=pd.read_csv(COUNTS).query('week_index == @week').job_count.to_numpy(dtype=float)
    shape/=shape.mean()
    case=r.m.case_definition(.1)
    for cls in ['training','offline_inference']:
        mask=template.job_class==cls
        marginal=template[mask].groupby('timestamp_index').arrival_gpu_h.sum().reindex(range(168),fill_value=0.)
        assert (marginal>0).all(), 'Retain all hours; do not silently impute empty class blocks'
        target=shape*(374.4*case['eligible_shares'][cls])
        template.loc[mask,'arrival_gpu_h']*=template.loc[mask,'timestamp_index'].map(dict(enumerate(target/marginal.to_numpy())))
    template=template[template.arrival_gpu_h>0].copy()
    template['source_mode']='alibaba2020_chronological_count_intensity_with_synthetic_class_work_and_deadlines'
    permutation=np.random.default_rng(seed+700000).permutation(168)
    records=[];paired={}
    for ordering in ['chronological','permuted']:
        jobs=template.copy()
        if ordering=='permuted':jobs['timestamp_index']=permutation[jobs.timestamp_index.to_numpy(dtype=int)]
        jobs=jobs.sort_values(['timestamp_index','job_class','slack_hours']).reset_index(drop=True)
        paired[ordering]=jobs
        input_path=root/f'{ordering}_arrivals.parquet';jobs.to_parquet(input_path,index=False)
        for g in [.1,.2]:
            name=f'w{week}_{ordering}_g{int(g*100)}'
            path=r.scenario('temporal',name,seed)
            if (path/'baseline_receipt.json').exists():
                records.append(json.loads((path/'baseline_receipt.json').read_text()));continue
            d,_=r.m.make_document(.1,'confirmation',seed)
            d['virtual_datacenter']['flexible_gpu_fraction']=g
            d['virtual_datacenter']['rigid_gpu_utilization']=374.4*.9/(576-round(576*g))
            d['workload']['flexible_arrival_utilization']=.65*.1/g
            d['workload']['arrivals_path']=str(input_path)
            for key in ['event_start_hour_choices','event_duration_choices','event_notice_choices','event_reduction_fraction_range']:d['dr'].pop(key,None)
            d['dr'].update(source='configured',events_path=None,event_start_hours=r.starts(seed,16),event_duration_hours=8,event_notice_hours=0,event_reduction_kw=1.,event_start_jitter_hours=0)
            r.m.freeze_hourly_scenario(d,seed=seed,output_directory=path.parent)
            parent=r.m.load_frozen_hourly_scenario(path)
            baseline_env=r.m.HourlyCommunityAIDemandResponseEnv(r.m._repeated_environment_document(parent,notice_h=0,requested_reduction_kw=0))
            baseline,summary=r.m.rollout_hourly_episode(baseline_env,r.m.make_hourly_controller('no_control'),seed=seed)
            baseline=baseline.drop(columns=['controller_action_time_ms']);baseline.to_parquet(path/'no_response_full.parquet',index=False)
            receipt=dict(name=name,role='temporal',seed=seed,week=week,replicate=rep,ordering=ordering,gpu_share=g,utilization=.65,slack_multiplier=1.,
                baseline_missed_gpu_h=float(baseline.missed_gpu_h.sum()),baseline_miss_rate=float(summary['deadline_miss_rate']),
                baseline_service_feasible=r.m.baseline_service_gate(baseline,float(summary['deadline_miss_rate']),baseline_env.config.pcc_capacity_kw),
                baseline_zero_service=float(baseline.missed_gpu_h.sum())<=1e-7,operating_peak_kw=baseline_env.power_model.reference_mix_operating_peak_kw,
                flexible_gpu_count=round(576*g),phase=r.starts(seed,16)[-1]-111,total_arrival_gpu_h=float(parent.arrivals.arrival_gpu_h.sum()),
                source=str(path),scenario_hash=parent.scenario_hash,baseline_sha256=r.m.sha(path/'no_response_full.parquet'))
            for p in r.programs(name):
                dest=r.scenario('temporal',name,seed,p['name'])
                if dest==path:continue
                dest.mkdir(parents=True,exist_ok=True);meta=copy.deepcopy(parent.metadata)
                for filename in meta['files']:shutil.copyfile(path/filename,dest/filename)
                meta['events']=[dict(event_id=i,source_event_id=f'temporal_{i}',start_hour=s,stop_hour=s+p['h'],requested_reduction_kw=1.,notice_hours=0.) for i,s in enumerate(r.starts(seed,p['period']))]
                meta.pop('scenario_hash');meta['scenario_hash']=r.m.digest(meta);r.m.save(dest/'metadata.json',meta)
                r.m.load_frozen_hourly_scenario(dest)
            r.m.save(path/'baseline_receipt.json',receipt);records.append(receipt)
    for fields in [['job_class'],['job_class','slack_hours']]:
        a=paired['chronological'].groupby(fields).arrival_gpu_h.sum();b=paired['permuted'].groupby(fields).arrival_gpu_h.sum()
        assert np.allclose(a,b,atol=1e-8)
    a=paired['chronological'].groupby('timestamp_index').arrival_gpu_h.sum().reindex(range(168),fill_value=0.)
    b=paired['permuted'].groupby('timestamp_index').arrival_gpu_h.sum().reindex(range(168),fill_value=0.)
    assert np.allclose(np.sort(a),np.sort(b),atol=1e-8)
    return records


def main():
    ap=argparse.ArgumentParser();ap.add_argument('stage',choices=['freeze_protocol','run']);ap.add_argument('--workers',type=int,default=32);args=ap.parse_args()
    if args.stage=='freeze_protocol':
        assert not LOCK.exists() and not (r.OUT/'runs/temporal').exists()
        selected=json.loads((r.HERE/'selection.json').read_text())['selections']
        fractions={p:sorted({1.}|{float(s['selected_fraction']) for s in selected if s['variant']==r.REFERENCE_VARIANT and s['program']==p and s['selected_fraction'] is not None}) for p in ['H8P16','H8P24']}
        tasks=[]
        for week in range(8):
            for rep in range(10):
                seed=986000+week*100+rep
                for ordering in ['chronological','permuted']:
                    for g in [10,20]:
                        for program,values in fractions.items():
                            for fraction in values:
                                tasks.append(dict(role='temporal',variant=f'w{week}_{ordering}_g{g}',seed=seed,program=program,fraction=fraction,kind='repeated'))
        record=dict(frozen_at_utc=datetime.now(timezone.utc).isoformat(),selection_sha256=r.m.sha(r.HERE/'selection.json'),
            script_sha256=r.m.sha(__file__),runner_sha256=r.m.sha(r.HERE/'run_tradeoffs.py'),count_source_sha256=r.m.sha(COUNTS),
            source='Alibaba 2020 job release counts; eight observed non-overlapping weeks, ten synthetic realizations per week',
            mapping='class-normalized observed hourly count intensity; paired permutation of whole hourly job blocks',
            boundary='no measured deadlines, power, or production-SLA replay; no 80-independent-week or reliability-certificate claim',
            fractions=fractions,tasks=tasks)
        r.m.save(LOCK,record);print('Frozen temporal protocol',len(tasks),'tasks');return
    p=json.loads(LOCK.read_text());assert p['script_sha256']==r.m.sha(__file__) and p['count_source_sha256']==r.m.sha(COUNTS)
    receipts=r.m.parallel(freeze_week_rep,[(w,i) for w in range(8) for i in range(10)],args.workers,'temporal freeze')
    r.m.save(r.OUT/'temporal_baseline_receipts.json',receipts)
    results=r.m.parallel(r.evaluate,p['tasks'],args.workers,'temporal')
    data=pd.DataFrame([x['row'] for x in results])
    fields=data.variant.str.extract(r'w(?P<week>\d+)_(?P<ordering>chronological|permuted)_g(?P<gpu_allocation_pct>\d+)')
    data=pd.concat([data,fields],axis=1);data.week=data.week.astype(int);data.gpu_allocation_pct=data.gpu_allocation_pct.astype(int)
    data=data.sort_values(['week','ordering','gpu_allocation_pct','program','fraction','seed'])
    data.to_csv(r.OUT/'temporal_ledgers.csv',index=False)
    summaries=[]
    for key,g in data.groupby(['week','ordering','gpu_allocation_pct','program','fraction']):
        summaries.append(dict(zip(['week','ordering','gpu_allocation_pct','program','fraction'],key))|dict(trials=len(g),successes_1pct=int(g.success_1pct.sum()),successes_zero=int(g.success_zero.sum()),
            baseline_failures=int((~g.baseline_service_feasible).sum()),baseline_nonzero_miss=int((~g.baseline_zero_service).sum()),
            mean_missed_gpu_h=float(g.missed_gpu_h.mean()),mean_waiting_exposure=float(g.delay_exposure_gpu_h_h.mean()),
            instantaneous_supply_limited_trials=int((g.instantaneous_supply_shortfall_hours>0).sum())))
    pd.DataFrame(summaries).to_csv(SOURCE/'temporal_week_summary.csv',index=False)
    print(data.groupby(['ordering','gpu_allocation_pct','program','fraction'])[['success_1pct','success_zero','baseline_service_feasible']].sum().to_string(),flush=True)


if __name__=='__main__':main()
