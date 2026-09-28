"""Independent accounting/criteria audit and completeness checks for the extension."""
from datetime import datetime
import json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import norm
import run_tradeoffs as r

SOURCE=r.ROOT/'manuscript/source_data/nature_operating_tradeoffs_v1'


def independent_lower(k,n):
    z=norm.ppf(.95);p=k/n
    return (p+z*z/(2*n)-z*np.sqrt(p*(1-p)/n+z*z/(4*n*n)))/(1+z*z/n)


def audit_trace(record):
    obj=json.loads(Path(record['receipt_path']).read_text())
    f=pd.read_parquet(obj['trace_path'])
    bpath=r.scenario(record['role'],record['variant'],int(record['seed']))
    b=pd.read_parquet(bpath/'no_response_full.parquet')
    baseline=json.loads((bpath/'baseline_receipt.json').read_text())
    a=r.m.load_frozen_hourly_scenario(obj['scenario_path'])
    assert a.scenario_hash==obj['scenario_hash'] and len(f)==216
    assert f.hour.tolist()==list(range(216)) and f.hour.equals(b.hour)
    residual=f.backlog_gpu_h.shift(1,fill_value=0)+f.arrival_gpu_h-f.executed_gpu_h-f.missed_gpu_h-f.backlog_gpu_h
    assert residual.abs().max()<1e-7
    assert abs(f.arrival_gpu_h.sum()-f.executed_gpu_h.sum()-f.missed_gpu_h.sum()-f.backlog_gpu_h.iloc[-1])<1e-7
    assert np.allclose(f.baseline_pcc_power_kw,b.baseline_pcc_power_kw,atol=1e-8,rtol=0)
    cap=record['capacity_kw'];start=min(e['start_hour'] for e in obj['events']);mask=f.hour>=start;active=f.event_active
    delivered=np.minimum(np.maximum(b.pcc_power_kw-f.pcc_power_kw,0)[active],cap)
    delay=np.maximum(f.backlog_gpu_h-b.backlog_gpu_h,0)
    ledger=dict(event_hours=float(active.sum()),contracted_energy_kwh=cap*float(active.sum()),capped_delivered_energy_kwh=float(delivered.sum()),
        shortfall_energy_kwh=cap*float(active.sum())-float(delivered.sum()),incremental_energy_kwh=float((f.pcc_power_kw-b.pcc_power_kw)[mask].sum()),
        delay_exposure_gpu_h_h=float(delay[mask].sum()),deferred_work_gpu_h=float(np.maximum(b.executed_gpu_h-f.executed_gpu_h,0)[active].sum()),
        incremental_missed_gpu_h=float((f.missed_gpu_h-b.missed_gpu_h)[mask].sum()),terminal_incremental_backlog_gpu_h=float(f.backlog_gpu_h.iloc[-1]-b.backlog_gpu_h.iloc[-1]),
        peak_excess_backlog_gpu_h=float(delay[mask].max()))
    for key,value in ledger.items():assert np.isclose(value,record[key],atol=1e-7,rtol=1e-9),(key,value,record[key])
    all_failed=set()
    for e in obj['events']:
        st=e['start_hour'];h=e['duration_h'];en=st+h
        event=f[f.hour.between(st,en-1)];window=f[f.hour.between(st,en+23)];post=f[f.hour.between(en,en+23)]
        assert len(event)==h and len(window)==h+24 and en+24<=168
        maximum_delivery=float(event.delivered_reduction_kw.clip(lower=0).max())
        rebound=float(np.maximum(post.pcc_power_kw-post.baseline_pcc_power_kw,0).max())
        metrics=dict(delivery_ratio=float(np.minimum(event.delivered_reduction_kw,cap).sum()/(cap*h)),
            minimum_interval_delivery_ratio=float(np.minimum(event.delivered_reduction_kw,cap).min()/cap),
            deadline_miss_rate=float(f.missed_gpu_h.sum()/f.arrival_gpu_h.sum()),
            rebound_peak_kw=rebound,rebound_ratio=rebound/maximum_delivery if maximum_delivery>1e-9 else 0.,
            window_peak_relief_kw=float(window.baseline_pcc_power_kw.max()-window.pcc_power_kw.max()),
            window_peak_relief_fraction=float((window.baseline_pcc_power_kw.max()-window.pcc_power_kw.max())/cap),
            terminal_backlog_fraction=float(f.terminal_backlog_excess_gpu_h.iloc[-1]/f.arrival_gpu_h.sum()))
        for key,value in metrics.items():assert np.isclose(value,e[key],atol=1e-7,rtol=1e-8),(key,value,e[key])
        failed=[]
        for key,name,limit,lower in [('delivery_ratio','mean_delivery',.95,True),('minimum_interval_delivery_ratio','interval_delivery',.95,True),
            ('deadline_miss_rate','deadline_miss',.01,False),('rebound_ratio','rebound',.25,False),('window_peak_relief_fraction','window_peak_relief',.5,True),('terminal_backlog_fraction','terminal_backlog',.02,False)]:
            if (metrics[key]+1e-9<limit) if lower else (metrics[key]-1e-9>limit):failed.append(name)
        assert set(failed)==set(e['failures']);all_failed.update(failed)
    success=not all_failed and baseline['baseline_service_feasible']
    zero=not(all_failed-{'deadline_miss'}) and f.missed_gpu_h.sum()<=1e-7 and baseline['baseline_zero_service'] and baseline['baseline_service_feasible']
    assert success==record['success_1pct'] and zero==record['success_zero']
    return dict(role=record['role'],variant=record['variant'],program=record['program'],kind=record['kind'],fraction=record['fraction'],seed=record['seed'],
        hours=216,events=len(obj['events']),max_conservation_error=float(residual.abs().max()),status='PASS')


def main():
    protocol=json.loads(r.PROTOCOL.read_text());selection=json.loads((r.HERE/'selection.json').read_text())
    assert protocol['runner_sha256']==r.m.sha(r.HERE/'run_tradeoffs.py')
    assert selection['protocol_sha256']==r.m.sha(r.PROTOCOL)
    assert selection['development_data_sha256']==r.m.sha(r.OUT/'development_ledgers.csv')
    assert selection['selector_sha256']==r.m.sha(r.HERE/'select_and_analyse.py')
    freeze_time=datetime.fromisoformat(selection['frozen_at_utc']).timestamp()
    checks=[];counts={}
    for role,expected in [('development',7600),('confirmation',len(selection['confirmation_tasks'])),('temporal',len(json.loads((r.HERE/'temporal_protocol.json').read_text())['tasks']))]:
        data=pd.read_csv(SOURCE/f'{role}_ledgers.csv');assert len(data)==expected
        keys=['variant','program','kind','fraction','seed'];assert not data.duplicated(keys).any()
        if role=='confirmation':
            planned=pd.DataFrame(selection['confirmation_tasks'])
            assert set(map(tuple,data[keys].to_numpy()))==set(map(tuple,planned[keys].to_numpy()))
            first=min(Path(x).stat().st_mtime for x in data.receipt_path)
            assert first>=freeze_time
        for key,g in data.groupby(['variant','program','kind','fraction']):
            g=g.sort_values('seed')
            for rec in g.iloc[[0,-1]].to_dict('records'):checks.append(audit_trace(rec))
        counts[role]=len(data)
    for role in ['development','confirmation']:
        data=pd.read_csv(SOURCE/f'{role}_ledgers.csv')
        table=pd.read_csv(SOURCE/f'{role}_summary.csv')
        for s in table.itertuples():
            part=data[(data.variant==s.variant)&(data.program==s.program)&(data.kind==s.kind)&np.isclose(data.fraction,s.fraction)]
            assert len(part)==s.trials and int(part[s.endpoint].sum())==s.successes
            assert abs(independent_lower(s.successes,s.trials)-s.wilson_lower)<1e-10
    # Confirm exact template and deadline transformations on all independent inputs.
    inputs=0
    for role,start,stop in [('development',984000,984100),('confirmation',985000,985300)]:
        for seed in range(start,stop):
            parent=pd.read_parquet(r.OUT/'inputs'/role/str(seed)/'template_f10.parquet')
            community_hash=None
            for v in r.VARIANTS:
                artifact=r.m.load_frozen_hourly_scenario(r.scenario(role,v['name'],seed))
                actual=artifact.arrivals
                assert np.allclose(actual.arrival_gpu_h,parent.arrival_gpu_h*v['utilization']/.65,atol=1e-8)
                assert np.array_equal(actual.slack_hours,np.maximum(1,np.floor(parent.slack_hours*v['slack_multiplier'])).astype(int))
                assert np.array_equal(actual.timestamp_index,parent.timestamp_index)
                h=artifact.metadata['files']['community.parquet']
                if community_hash is None:community_hash=h
                else:assert community_hash==h
                inputs+=1
    pd.DataFrame(checks).to_csv(r.HERE/'independent_trajectory_audit.csv',index=False)
    report=dict(status='PASS',trials=counts,complete_trajectories_independently_recomputed=len(checks),
        individual_events_independently_recomputed=sum(x['events'] for x in checks),
        structured_inputs_verified=inputs,template_release_times_preserved=True,paired_community_inputs_identical=True,
        maximum_hourly_conservation_error=max(x['max_conservation_error'] for x in checks),
        selection_frozen_before_confirmation=True,all_summary_counts_and_probability_bounds_recomputed=True)
    r.m.save(r.HERE/'numerical_audit.json',report);print(json.dumps(report,indent=2))


if __name__=='__main__':main()
