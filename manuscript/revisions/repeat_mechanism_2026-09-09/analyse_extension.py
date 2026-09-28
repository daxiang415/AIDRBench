"""Whole-scenario contrasts, failure attribution and paired annual cost ledgers."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import binomtest
import run_extension as x

SOURCE=x.ROOT/'manuscript/source_data/nature_repeat_mechanism_v1'
CRITERIA=['mean_delivery','interval_delivery','deadline_miss','rebound','window_peak_relief','terminal_backlog']
GROUP=['case','program','duration_h','gap_h','controller','fraction','capacity_kw','kind']


def collect(role):
    rows=[];events=[]
    paths=sorted((x.OUT/role).glob('*/*.json'))
    for p in paths:
        r=json.loads(p.read_text());t=r['task'];base=t|dict(capacity_kw=r['capacity_kw'])
        failures={f for e in r['events'] for f in e['failures']}
        rows.append(base|dict(success=r['success'],**r['ledger'],scenario_hash=r['scenario_hash'],
            trace_path=r['trace_path'],trace_sha256=r['trace_sha256'],receipt_path=str(p),
            additional_cap_hours=sum(a['additional_cap_active'] for a in r['controller_audit']),
            below_fixed_power_hours=sum(a['target_below_fixed_power'] for a in r['controller_audit']),
            overlapping_guard_hours=sum(a['observed_active_windows']>1 and a['additional_cap_active'] for a in r['controller_audit']),
            **{f'failure_{f}':f in failures for f in CRITERIA},
            only_window_peak_failure=failures=={'window_peak_relief'}))
        for event in r['events']:
            events.append(base|{k:v for k,v in event.items() if k!='failures'}|
                {f'failure_{f}':f in event['failures'] for f in CRITERIA})
    return pd.DataFrame(rows),pd.DataFrame(events)


def summarize(df):
    rows=[]
    for key,g in df.groupby(GROUP):
        n=len(g);k=int(g.success.sum());lb=x.m.wilson_lower_bound(k,n,.95)
        rows.append(dict(zip(GROUP,key))|dict(successes=k,trials=n,success_fraction=k/n,wilson_lower=lb,qualified=lb>=.95,
            only_window_peak_failures=int(g.only_window_peak_failure.sum()),
            **{f'failures_{f}':int(g[f'failure_{f}'].sum()) for f in CRITERIA},
            mean_additional_cap_hours=float(g.additional_cap_hours.mean()),
            mean_overlapping_guard_hours=float(g.overlapping_guard_hours.mean()),
            mean_delay_exposure_gpu_h_h=float(g.delay_exposure_gpu_h_h.mean()),
            mean_incremental_missed_gpu_h=float(g.incremental_missed_gpu_h.mean()),
            max_incremental_missed_gpu_h=float(g.incremental_missed_gpu_h.max())))
    return pd.DataFrame(rows)


def paired_contrasts(df):
    rows=[]
    for (case,program,fraction),g in df.groupby(['case','program','fraction']):
        controls=set(g.controller)
        if 'original' not in controls:continue
        orig=g[g.controller=='original'].set_index('seed').sort_index()
        for ctrl in sorted(controls-{'original'}):
            revised=g[g.controller==ctrl].set_index('seed').sort_index()
            assert orig.index.equals(revised.index)
            assert orig.scenario_hash.equals(revised.scenario_hash)
            n=len(orig);delta=revised.success.to_numpy().astype(int)-orig.success.to_numpy().astype(int)
            rng=np.random.default_rng(20260912);idx=rng.integers(0,n,size=(10000,n))
            lo,hi=np.quantile(delta[idx].mean(axis=1)*100,[.025,.975])
            gain=int((delta>0).sum());loss=int((delta<0).sum())
            rows.append(dict(case=case,program=program,fraction=fraction,controller=ctrl,trials=n,
                original_successes=int(orig.success.sum()),revised_successes=int(revised.success.sum()),
                gained=gain,lost=loss,difference_pp=float(delta.mean()*100),ci_low_pp=float(lo),ci_high_pp=float(hi),
                exact_mcnemar_p=binomtest(gain,gain+loss,.5).pvalue if gain+loss else 1.,
                original_window_only_failures=int(orig.only_window_peak_failure.sum()),
                rescued_window_only_failures=int((orig.only_window_peak_failure & revised.success).sum()),
                new_deadline_failures=int((~orig.failure_deadline_miss & revised.failure_deadline_miss).sum())))
    p=pd.DataFrame(rows)
    order=np.argsort(p.exact_mcnemar_p.to_numpy());adjusted=np.empty(len(p));last=0.
    for rank,i in enumerate(order):
        last=max(last,min(1.,p.iloc[i].exact_mcnemar_p*(len(p)-rank)));adjusted[i]=last
    p['holm_p_all_reported_contrasts']=adjusted
    return p


def economics(df,selected):
    from aidrbench.economics.capital import annualized_reserve_cost
    index=pd.read_csv(x.ROOT/'manuscript/source_data/nature_workload_composition_v1/scenario_index.csv')
    prices=[]
    for key,g in df.groupby(GROUP):
        g=g.sort_values('seed');n=len(g);assert n==300
        tag=dict(zip(GROUP,key));k=float(tag['capacity_kw'])
        peak=float(index[index.case==tag['case']].operating_peak_kw.iloc[0]);scale=1000/peak
        sel=selected[(selected.case==tag['case'])&(selected.program==tag['program'])&(selected.controller==tag['controller'])]
        chosen=bool(len(sel) and pd.notna(sel.selected_fraction.iloc[0]) and abs(float(sel.selected_fraction.iloc[0])-tag['fraction'])<1e-12)
        lower=x.m.wilson_lower_bound(int(g.success.sum()),n,.95)
        rng=np.random.default_rng(20260910);draw=rng.integers(0,n,size=(2000,12))
        for waiting in [0.,.005,.01]:
            for fixed in [10000.,25000.,50000.]:
                for displaced in [0.,.25,.5]:
                    base=.1*g.incremental_energy_kwh.to_numpy()+waiting*g.delay_exposure_gpu_h_h.to_numpy()-.05*g.capped_delivered_energy_kwh.to_numpy()+displaced*g.deferred_work_gpu_h.to_numpy()
                    annual=scale*base[draw].sum(axis=1)+fixed
                    threshold=max(0.,float(np.quantile(annual,.95)/(scale*k)))
                    prices.append(tag|dict(regime='slack' if displaced==0 else f'displacement_{displaced}',
                        selected_by_development=chosen,confirmation_qualified=lower>=.95,offerable_selected_option=chosen and lower>=.95,
                        operating_peak_kw=peak,scale=scale,annual_series=12,waiting_price=waiting,site_cost=fixed,
                        displaced_value=displaced,payment_usd_kw_year=threshold))
                    if waiting==.005 and fixed==25000 and displaced==0:
                        add=annualized_reserve_cost(reserved_capacity_kw=.15,installed_cost_per_reserved_kw=2500,
                            discount_rate=.08,economic_life_years=4,salvage_fraction=.1,annual_om_fraction=.03)
                        prices.append(prices[-1]|dict(regime='reserved_headroom',payment_usd_kw_year=threshold+add))
    return pd.DataFrame(prices)


def illustration(development):
    # Prespecified, transparent illustrative selection among development seeds.
    g=development[(development.case=='f10')&(development.program=='H8G12')&(development.fraction==1)]
    pivot=g.pivot(index='seed',columns='controller',values='success')
    eligible=pivot.index[(~pivot.original)&pivot.all_window_mpc]
    if not len(eligible):return None
    seed=int(min(eligible));rows=[]
    for row in g[g.seed==seed].to_dict('records'):
        frame=pd.read_parquet(row['trace_path'])
        rec=json.loads(Path(row['receipt_path']).read_text())
        for event in rec['events']:
            start=event['start_hour'];stop=start+event['duration_h'];recstop=stop+24
            ix=(frame.hour>=start)&(frame.hour<recstop)
            part=frame.loc[ix]
            base_peak=float(part.baseline_pcc_power_kw.max())
            controlled_peak=float(part.pcc_power_kw.max())
            rows.append(dict(case='f10',seed=seed,controller=row['controller'],event_id=event['event_id'],start_hour=start,
                stop_hour=stop,recovery_stop_hour=recstop,baseline_peak_kw=base_peak,controlled_peak_kw=controlled_peak,
                allowed_window_peak_kw=base_peak-.5*row['capacity_kw'],window_peak_failure=bool(event['window_peak_relief_fraction']<.5-1e-9)))
        frame['method']=row['controller'];frame['seed']=seed
        frame.to_csv(SOURCE/f'illustration_{row["controller"]}.csv',index=False)
    pd.DataFrame(rows).to_csv(SOURCE/'illustration_windows.csv',index=False)
    return dict(seed=seed,selection='lowest development seed with original failure and all-window MPC success at f10/H8G12/full offer',not_statistical_unit_selection=True)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--development-only',action='store_true');a=ap.parse_args()
    SOURCE.mkdir(parents=True,exist_ok=True)
    development,de=collect('development');assert len(development)==10100
    development.to_csv(SOURCE/'development_ledgers.csv',index=False);de.to_csv(SOURCE/'development_events.csv',index=False)
    summarize(development).to_csv(SOURCE/'development_summary.csv',index=False)
    illustrative=illustration(development)
    if a.development_only:
        x.m.save(SOURCE/'illustration_selection.json',illustrative);return
    selection=json.loads((x.HERE/'selection.json').read_text())
    df,events=collect('confirmation');assert len(df)==len(selection['confirmation_tasks'])
    df.to_csv(SOURCE/'confirmation_ledgers.csv',index=False);events.to_csv(SOURCE/'confirmation_events.csv',index=False)
    summary=summarize(df);summary.to_csv(SOURCE/'confirmation_summary.csv',index=False)
    pairs=paired_contrasts(df);pairs.to_csv(SOURCE/'paired_controller_contrasts.csv',index=False)
    selected=pd.DataFrame(selection['selected']);selected.to_csv(SOURCE/'selected_offers.csv',index=False)
    econ=economics(df,selected);econ.to_csv(SOURCE/'economic_sensitivity.csv',index=False)
    econ[(econ.waiting_price==.005)&(econ.site_cost==25000)].to_csv(SOURCE/'economic_primary.csv',index=False)
    x.m.save(SOURCE/'illustration_selection.json',illustrative)
    x.m.save(x.HERE/'analysis_receipt.json',dict(development_replays=len(development),confirmation_replays=len(df),
        development_events=len(de),confirmation_events=len(events),summary_rows=len(summary),paired_contrasts=len(pairs),
        primary=pairs[(pairs.case=='f10')&(pairs.program=='H8G12')&(pairs.fraction==1)&(pairs.controller=='all_window_mpc')].to_dict('records'),
        illustrated_development_case=illustrative))
    print(summary.to_string(index=False));print(pairs.to_string(index=False))


if __name__=='__main__':main()
