"""Independent arithmetic and primal-witness checks for the focused extension."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.optimize import linprog
from scipy.stats import norm
import refine_offers as f
import pi_diagnostic as pi

def wilson(k,n):
    z=norm.ppf(.95);p=k/n
    return (p+z*z/(2*n)-z*np.sqrt(p*(1-p)/n+z*z/(4*n*n)))/(1+z*z/n)

def audit():
    checks=[]
    for role in ['development','confirmation']:
        raw=pd.read_csv(f.OUT/f'{role}_ledgers.csv');summary=pd.read_csv(f.SOURCE/f'refinement_{role}_summary.csv')
        for row in summary.itertuples():
            g=raw[(raw.program==row.program)&np.isclose(raw.fraction,row.fraction)]
            assert row.trials==len(g) and row.successes==g[row.endpoint].sum() and abs(wilson(row.successes,row.trials)-row.wilson_lower)<1e-12
        checks.append(dict(check=role+'_counts_and_independent_Wilson',rows=len(raw),status='PASS'))
    runs=[]
    for role in ['development','confirmation','workload']:
        for path in (f.OUT/'runs'/role).glob('*/*/*.json'):
            receipt=json.loads(path.read_text());g=pd.read_parquet(receipt['trace_path']);row=receipt['row']
            assert f.r.m.sha(receipt['trace_path'])==receipt['trace_sha256'] and len(g)==216
            assert abs(g.missed_gpu_h.sum()-row['missed_gpu_h'])<1e-7
            assert abs(g.arrival_gpu_h.sum()-576*.65*.1*168)<1e-6
            assert not (row['success_zero'] and not row['success_1pct'])
            if row['instantaneous_supply_shortfall_hours']>0:assert row['failure_interval_delivery']
            runs.append(row)
    checks.append(dict(check='all_new_complete_trajectories',trials=len(runs),hourly_rows=216*len(runs),status='PASS'))
    witness_count=0;worst=0.
    for path in (f.OUT/'pi').glob('*/receipt.json'):
        obj=json.loads(path.read_text())
        if obj['classification']!='feasible_witness':continue
        task=obj['task'];s=pi.snapshot_at(task['scenario'],task['seed'],task['request_kw']);groups=pd.read_parquet(path.parent/'work_groups.parquet');e=pd.read_parquet(path.parent/'execution_edges.parquet');h=pd.read_parquet(path.parent/'hourly_witness.parquet')
        x=e.merge(groups.reset_index(names='group_index'),on='group_index',validate='many_to_one')
        assert ((x.hour>=x.release)&(x.hour<=x.deadline)).all() and (x.execution_gpu_h>=-1e-7).all()
        totals=e.groupby('group_index').execution_gpu_h.sum().reindex(range(len(groups)),fill_value=0).to_numpy()+groups.missed_gpu_h+groups.terminal_backlog_gpu_h
        residual=float(np.abs(totals-groups.work).max());assert residual<1e-7;worst=max(worst,residual)
        byhour=e.groupby('hour').execution_gpu_h.sum().reindex(range(216),fill_value=0);assert np.allclose(byhour,h.executed_gpu_h,atol=1e-7)
        assert byhour.max()<=s.capacity_gpu_h+1e-7 and groups.missed_gpu_h.sum()<=task['miss_rate']*s.total_arrival_gpu_h+1e-7
        power=np.array(s.community_power_kw)+s.fixed_dc_power_kw
        for cls,c in dict(s.dynamic_kw_per_gpu_h_by_class).items():power+=e.loc[e.job_class==cls].groupby('hour').execution_gpu_h.sum().reindex(range(216),fill_value=0).to_numpy()*c
        assert np.allclose(power,h.pcc_power_kw,atol=1e-7) and power.max()<=s.pcc_capacity_kw+1e-7
        B=np.array(s.baseline_pcc_power_kw);R=task['request_kw']
        for ev in s.events:
            active=slice(ev.start_hour,ev.stop_hour);rec=slice(ev.stop_hour,ev.recovery_stop_hour);window=slice(ev.start_hour,ev.recovery_stop_hour)
            d=np.maximum(B[active]-power[active],0.)
            assert np.minimum(d,R).mean()/R>=.95-1e-8 and d.min()/R>=.95-1e-8
            assert np.maximum(power[rec]-B[rec],0.).max()/d.max()<=.25+1e-8
            assert (B[window].max()-power[window].max())/R>=.5-1e-8
        witness_count+=1
    checks.append(dict(check='independent_job_edge_and_all_electrical_witness_constraints',witnesses=witness_count,worst_job_conservation_error=worst,status='PASS'))
    # Crossing windows invalidate the earlier cumulative-only equivalence claim.
    releases=np.array([2.,1.,0.]);dues=np.array([0.,1.,2.]);execution=np.array([2.,0.,1.])
    assert (execution.cumsum()<=releases.cumsum()).all() and (execution.cumsum()>=dues.cumsum()).all()
    # Edges A@0,A@1,A@2,B@1. A: release 0, due 2, work 2; B: release=due=1, work 1.
    A=np.array([[1,1,1,0],[0,0,0,1],[1,0,0,0],[0,1,0,1],[0,0,1,0]],float)
    proof=linprog(np.zeros(4),A_eq=A,b_eq=[2,1,2,0,1],bounds=(0,None),method='highs');assert proof.status==2
    checks.append(dict(check='crossing_release_deadline_counterexample',status='PASS',conclusion='cumulative-only PI optima are relaxation envelopes, not generally exact job-feasible capacities'))
    costs=pd.read_csv(f.SOURCE/'refinement_cost_components.csv')
    assert np.allclose(costs[['energy_annual_usd','waiting_annual_usd','delivery_credit_annual_usd','missed_work_annual_usd']].sum(axis=1),costs.net_operating_annual_q95,atol=1e-8)
    curves=pd.read_csv(f.SOURCE/'ready_refinement_price_curves.csv')
    expected=(np.maximum(0,curves.price_4h*curves.accounting_offer_4h-curves.operating_4h_annual-curves.site_fee_annual_usd)+curves.operating_8h_annual+curves.site_fee_annual_usd)/curves.accounting_offer_8h
    assert np.allclose(expected,curves.required_price_8h,atol=1e-8)
    checks.append(dict(check='cost_additivity_and_opt_out_boundary',status='PASS',curves=len(curves)))
    f.r.m.save(f.HERE/'numerical_audit.json',dict(status='PASS',checks=checks))
    print(json.dumps(checks,indent=2),flush=True)

if __name__=='__main__':audit()
