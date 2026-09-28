"""Select before confirmation; retain full-grid and endpoint diagnostics."""
import argparse
from datetime import datetime, timezone
import json
import numpy as np
import pandas as pd
from scipy.stats import binomtest
import run_tradeoffs as r

GROUP=['variant','program','kind','fraction','capacity_kw']
ENDPOINTS=['success_1pct','success_zero','success_01pct']
SOURCE=r.ROOT/'manuscript/source_data/nature_operating_tradeoffs_v1'


def summarize(data):
    rows=[]
    for key,g in data.groupby(GROUP):
        base=dict(zip(GROUP,key))
        for endpoint in ENDPOINTS:
            n=len(g);k=int(g[endpoint].sum());lb=r.m.wilson_lower_bound(k,n,.95)
            rows.append(base|dict(endpoint=endpoint,trials=n,successes=k,success_fraction=k/n,wilson_lower=lb,qualified=lb>=.95,
                baseline_failures=int((~g.baseline_service_feasible).sum()),baseline_nonzero_miss=int((~g.baseline_zero_service).sum()),
                total_missed_gpu_h_mean=float(g.missed_gpu_h.mean()),total_missed_gpu_h_max=float(g.missed_gpu_h.max()),
                miss_rate_mean=float(g.miss_rate.mean()),waiting_exposure_mean=float(g.delay_exposure_gpu_h_h.mean()),
                instantaneous_supply_limited_trials=int((g.instantaneous_supply_shortfall_hours>0).sum()),
                **{f'failed_{name}':int(g[f'failure_{name}'].sum()) for name in r.CRITERIA_NAMES}))
    return pd.DataFrame(rows)


def select():
    path=r.HERE/'selection.json';assert not path.exists()
    assert not (r.OUT/'runs/confirmation').exists()
    data=pd.read_csv(r.OUT/'development_ledgers.csv')
    summary=summarize(data)
    rows=[]
    for (variant,program),g in summary[summary.kind=='repeated'].groupby(['variant','program']):
        for endpoint in ['success_1pct','success_zero']:
            options=g[(g.endpoint==endpoint)&g.qualified].sort_values('fraction')
            chosen=None if options.empty else options.iloc[-1]
            rows.append(dict(variant=variant,program=program,endpoint=endpoint,
                selected_fraction=None if chosen is None else float(chosen.fraction),
                selected_capacity_kw=None if chosen is None else float(chosen.capacity_kw),
                development_successes=None if chosen is None else int(chosen.successes),
                development_trials=100,development_lower=None if chosen is None else float(chosen.wilson_lower)))
    tasks=[]
    for seed in range(985000,985300):
        for v in r.VARIANTS:
            for p in r.programs(v['name']):
                fractions={1.}
                fractions.update(row['selected_fraction'] for row in rows if row['variant']==v['name'] and row['program']==p['name'] and row['selected_fraction'] is not None)
                for fraction in sorted(fractions):
                    tasks.append(dict(role='confirmation',variant=v['name'],seed=seed,program=p['name'],fraction=fraction,kind='repeated'))
            tasks.append(dict(role='confirmation',variant=v['name'],seed=seed,program='H8P16',fraction=1.,kind='fresh'))
    record=dict(frozen_at_utc=datetime.now(timezone.utc).isoformat(),protocol_sha256=r.m.sha(r.PROTOCOL),
        development_data_sha256=r.m.sha(r.OUT/'development_ledgers.csv'),selector_sha256=r.m.sha(__file__),
        confirmation_not_yet_run=True,selections=rows,confirmation_tasks=tasks)
    r.m.save(path,record)
    pd.DataFrame(rows).to_csv(SOURCE/'selected_offers.csv',index=False)
    summary.to_csv(SOURCE/'development_summary.csv',index=False)
    print(pd.DataFrame(rows).to_string(index=False));print('Confirmation tasks:',len(tasks),'selection hash',r.m.sha(path),flush=True)


def contrasts(data):
    full=data[(data.fraction==1.)&(data.kind=='repeated')]
    pairs=[]
    for v in r.VARIANTS:
        pairs.append(('period',v['name'],'H8P16',v['name'],'H8P24'))
    for u in ['50','65','80']:
        for p in ['H8P16','H8P24']:
            pairs.append(('deadline',f'u{u}d100g10',p,f'u{u}d50g10',p))
    for u in ['65','80']:
        for p in ['H8P16','H8P24']:
            pairs.append(('gpu_allocation',f'u{u}d50g10',p,f'u{u}d50g20',p))
    rows=[]
    for family,va,pa,vb,pb in pairs:
        a=full[(full.variant==va)&(full.program==pa)].set_index('seed').sort_index()
        b=full[(full.variant==vb)&(full.program==pb)].set_index('seed').sort_index()
        assert a.index.equals(b.index) and len(a)==300
        draws=np.random.default_rng(20260919).integers(0,len(a),size=(5000,len(a)))
        for endpoint in ['success_1pct','success_zero','missed_gpu_h','delay_exposure_gpu_h_h']:
            delta=b[endpoint].to_numpy(dtype=float)-a[endpoint].to_numpy(dtype=float)
            lo,hi=np.quantile(delta[draws].mean(axis=1),[.025,.975])
            binary=endpoint.startswith('success')
            gain=int((delta>0).sum());loss=int((delta<0).sum())
            pvalue=binomtest(gain,gain+loss,.5).pvalue if binary and gain+loss else 1. if binary else np.nan
            rows.append(dict(family=family,variant_a=va,program_a=pa,variant_b=vb,program_b=pb,endpoint=endpoint,
                n=300,mean_a=float(a[endpoint].mean()),mean_b=float(b[endpoint].mean()),difference=float(delta.mean()),ci_low=float(lo),ci_high=float(hi),exact_p=pvalue))
    table=pd.DataFrame(rows);mask=table.exact_p.notna();indices=table[mask].sort_values('exact_p').index
    previous=0.
    for rank,index in enumerate(indices):
        previous=max(previous,min(1.,float(table.loc[index,'exact_p'])*(len(indices)-rank)))
        table.loc[index,'holm_p_binary_family']=previous
    return table


def analyse():
    data=pd.read_csv(r.OUT/'confirmation_ledgers.csv')
    selection=json.loads((r.HERE/'selection.json').read_text())
    assert selection['protocol_sha256']==r.m.sha(r.PROTOCOL)
    summary=summarize(data)
    selected=[]
    for row in selection['selections']:
        out=dict(row)
        if row['selected_fraction'] is None:
            out.update(confirmation_successes=None,confirmation_lower=None,offerable=False)
        else:
            match=summary[(summary.variant==row['variant'])&(summary.program==row['program'])&(summary.endpoint==row['endpoint'])&(summary.kind=='repeated')&np.isclose(summary.fraction,row['selected_fraction'])]
            assert len(match)==1;value=match.iloc[0]
            out.update(confirmation_successes=int(value.successes),confirmation_lower=float(value.wilson_lower),offerable=bool(value.qualified))
        selected.append(out)
    # A necessary instantaneous supply deficit must imply a failed interval.
    assert not ((data.instantaneous_supply_shortfall_hours>0)&~data.failure_interval_delivery).any()
    summary.to_csv(SOURCE/'confirmation_summary.csv',index=False)
    pd.DataFrame(selected).to_csv(SOURCE/'selected_offers_confirmed.csv',index=False)
    contrasts(data).to_csv(SOURCE/'paired_structural_contrasts.csv',index=False)
    print(pd.DataFrame(selected).to_string(index=False),flush=True)


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('stage',choices=['select','analyse']);args=ap.parse_args()
    SOURCE.mkdir(parents=True,exist_ok=True)
    select() if args.stage=='select' else analyse()
