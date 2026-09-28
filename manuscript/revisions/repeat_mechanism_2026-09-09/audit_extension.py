"""Independent arithmetic checks on exported summaries and stratified trajectories."""
import json
import math
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import norm
import run_extension as x
from analyse_extension import SOURCE,GROUP,CRITERIA


def wilson(k,n):
    z=norm.ppf(.95);p=k/n
    return (p+z*z/(2*n)-z*math.sqrt(p*(1-p)/n+z*z/(4*n*n)))/(1+z*z/n)


def audit_trace(r):
    f=pd.read_parquet(r.trace_path)
    assert x.m.sha(r.trace_path)==r.trace_sha256
    rec=json.loads(Path(r.receipt_path).read_text())
    base=pd.read_parquet(x.source_artifact(r.role,r.case,r.seed)/'no_response_full.parquet')
    assert len(f)==len(base)==216 and np.array_equal(f.hour,base.hour)
    for col in ['arrival_gpu_h','community_power_kw','baseline_pcc_power_kw']:
        assert np.allclose(f[col],base[col],rtol=0,atol=1e-9)
    active=np.zeros(len(f),dtype=bool);all_decisions=[]
    for i,e in enumerate(rec['events']):
        start=63+i*(r.duration_h+r.gap_h);stop=start+r.duration_h
        assert e['start_hour']==start and e['duration_h']==r.duration_h and stop+24<=168
        ev=f.hour.between(start,stop-1);post=f.hour.between(stop,stop+23);window=f.hour.between(start,stop+23)
        active|=ev.to_numpy()
        delivered=np.minimum(np.maximum(base.pcc_power_kw[ev]-f.pcc_power_kw[ev],0),r.capacity_kw)
        rawpeak=float((base.pcc_power_kw[ev]-f.pcc_power_kw[ev]).clip(lower=0).max())
        values=dict(delivery_ratio=float(delivered.mean()/r.capacity_kw),minimum_interval_delivery_ratio=float(delivered.min()/r.capacity_kw),
            deadline_miss_rate=float(f.missed_gpu_h.sum()/f.arrival_gpu_h.sum()),
            rebound_ratio=float((f.pcc_power_kw[post]-base.pcc_power_kw[post]).clip(lower=0).max()/rawpeak) if rawpeak>1e-9 else 0.,
            window_peak_relief_fraction=float((base.pcc_power_kw[window].max()-f.pcc_power_kw[window].max())/r.capacity_kw),
            terminal_backlog_fraction=float(f.terminal_backlog_excess_gpu_h.iloc[-1]/f.arrival_gpu_h.sum()))
        for key,val in values.items():assert np.isclose(val,e[key],rtol=1e-9,atol=1e-9),(r.trace_path,key,val,e[key])
        tests=[values['delivery_ratio']>=.95-1e-9,values['minimum_interval_delivery_ratio']>=.95-1e-9,
            values['deadline_miss_rate']<=.01+1e-9,values['rebound_ratio']<=.25+1e-9,
            values['window_peak_relief_fraction']>=.5-1e-9,values['terminal_backlog_fraction']<=.02+1e-9]
        expected={name for name,ok in zip(CRITERIA,tests) if not ok}
        assert expected==set(e['failures']) and bool(all(tests))==e['success']
        all_decisions.append(all(tests))
    assert np.array_equal(active,f.event_active) and all(all_decisions)==bool(r.success)
    led=rec['ledger'];covered=f.hour>=63
    checks=dict(event_hours=float(active.sum()),contracted_energy_kwh=float(active.sum()*r.capacity_kw),
        capped_delivered_energy_kwh=float(np.minimum(np.maximum(base.pcc_power_kw[active]-f.pcc_power_kw[active],0),r.capacity_kw).sum()),
        incremental_energy_kwh=float((f.pcc_power_kw-base.pcc_power_kw)[covered].sum()),
        delay_exposure_gpu_h_h=float((f.backlog_gpu_h-base.backlog_gpu_h).clip(lower=0)[covered].sum()),
        deferred_work_gpu_h=float((base.executed_gpu_h-f.executed_gpu_h).clip(lower=0)[active].sum()),
        incremental_missed_gpu_h=float((f.missed_gpu_h-base.missed_gpu_h)[covered].sum()))
    for key,val in checks.items():assert np.isclose(val,led[key],rtol=1e-9,atol=1e-8),(key,val,led[key])
    return dict(role=r.role,case=r.case,program=r.program,controller=r.controller,fraction=r.fraction,seed=r.seed,events=4,hours=216)


def main():
    p=json.loads(x.PROTOCOL.read_text())
    for name,digest in p['code_sha256'].items():assert x.m.sha(x.ROOT/name)==digest,name
    selected=pd.read_csv(SOURCE/'selected_offers.csv');audits=[];summary_checks=0
    for role in ['development','confirmation']:
        d=pd.read_csv(SOURCE/f'{role}_ledgers.csv');s=pd.read_csv(SOURCE/f'{role}_summary.csv')
        expected_seeds=set(range(930000,930100)) if role=='development' else set(range(970000,970300))
        for key,g in d.groupby(GROUP):
            assert set(g.seed)==expected_seeds and len(g)==len(expected_seeds)
            z=s
            for col,val in zip(GROUP,key):z=z[z[col]==val]
            assert len(z)==1
            k=int(g.success.sum());n=len(g)
            assert int(z.iloc[0].successes)==k and abs(z.iloc[0].wilson_lower-wilson(k,n))<1e-12
            summary_checks+=1
            for _,row in g.sort_values('seed').iloc[[0,-1]].iterrows():audits.append(audit_trace(row))
    dev=pd.read_csv(SOURCE/'development_summary.csv')
    for r in selected.itertuples():
        g=dev[(dev.case==r.case)&(dev.program==r.program)&(dev.controller==r.controller)&dev.qualified]
        if pd.isna(r.selected_fraction):assert len(g)==0
        else:assert r.selected_fraction==float(g.fraction.max())
    pd.DataFrame(audits).to_csv(x.HERE/'trajectory_arithmetic_audit.csv',index=False)
    x.m.save(x.HERE/'numerical_audit.json',dict(status='PASS',summary_rows=summary_checks,
        stratified_full_trajectories=len(audits),events=sum(a['events'] for a in audits),
        checked_hours=sum(a['hours'] for a in audits),all_frozen_code_hashes_match=True,
        original_thresholds_unchanged=True,confirmation_selection_not_revised=True,
        scope='all counts and Wilson bounds; first and last seed in every complete group independently recomputed for all event criteria and core ledger terms'))
    print('PASS',summary_checks,'summaries;',len(audits),'complete trajectories')


if __name__=='__main__':main()
