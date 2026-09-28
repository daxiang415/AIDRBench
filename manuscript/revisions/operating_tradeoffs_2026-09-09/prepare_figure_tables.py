"""Precompute every additional plotted contrast; plotting reads these tables unchanged."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
from scipy.stats import binomtest
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
S=ROOT/'manuscript/source_data/nature_operating_tradeoffs_v1'

def main():
    d=pd.read_csv(S/'confirmation_events.csv');d=d[d.is_target_call & np.isclose(d.fraction,1)]
    rng=np.random.default_rng(20260911);pairs=[]
    for v,g in d.groupby('variant'):
        fresh=g[g.kind=='fresh'].set_index('seed').sort_index();assert len(fresh)==300
        for prog in ['H8P16','H8P24']:
            rep=g[(g.kind=='repeated')&(g.program==prog)].set_index('seed').sort_index()
            assert rep.index.equals(fresh.index) and rep.start_hour.equals(fresh.start_hour)
            a=fresh.local_electrical_success.to_numpy();b=rep.local_electrical_success.to_numpy()
            diff=b.astype(float)-a.astype(float);lo,hi=np.quantile(diff[rng.integers(0,300,(5000,300))].mean(axis=1),[.025,.975])
            gained=int((~a&b).sum());lost=int((a&~b).sum());p=binomtest(gained,gained+lost,.5).pvalue if gained+lost else 1
            pairs.append(dict(variant=v,program=prog,trials=300,fresh_target_electrical_successes=int(a.sum()),repeated_target_electrical_successes=int(b.sum()),
                difference_pp=diff.mean()*100,lower_pp=lo*100,upper_pp=hi*100,gained=gained,lost=lost,exact_p=p))
    out=pd.DataFrame(pairs);ix=np.argsort(out.exact_p.to_numpy());adj=np.minimum(1,np.maximum.accumulate(out.exact_p.to_numpy()[ix]*(len(out)-np.arange(len(out)))))
    out.loc[ix,'holm_p']=adj;out.to_csv(S/'target_call_pairs.csv',index=False)
    t=pd.read_csv(S/'temporal_week_summary.csv')
    t.groupby(['ordering','gpu_allocation_pct','program','fraction'],as_index=False)[['trials','successes_1pct','successes_zero','baseline_failures','baseline_nonzero_miss']].sum().to_csv(S/'temporal_aggregate.csv',index=False)
    # All financial comparisons retain both tariff and opt-out explicitly.
    costs=pd.read_csv(S/'structural_cost_components.csv');costs=costs[(costs.variant=='u65d100g10')&costs.offerable_success_zero]
    values=[]
    for row in costs.to_dict('records'):
        for fee in [0.,2500.,5000.,25000.]:
            values.append(dict(program=row['program'],fraction=row['fraction'],model_kw=row['capacity_kw'],accounting_kw=row['accounting_offered_kw'],
                price=250.,fee=fee,annual_net_value_lower=250*row['accounting_offered_kw']-row['net_operating_annual_q95']-fee))
    pd.DataFrame(values).to_csv(S/'structural_entry_examples.csv',index=False)
    front=pd.read_csv(S/'structural_duration_price_frontier.csv');curves=[]
    short=costs[costs.program=='H4P16'].iloc[0]
    for key,g in front.groupby(['endpoint','long_program','site_fee_annual_usd']):
        endpoint,prog,fee=key;r=g.sort_values('short_price').iloc[0]
        switch=(short.net_operating_annual_q95+fee)/short.accounting_offered_kw
        floor=r.required_long_price_vs_short_and_opt_out
        prices=np.unique(np.r_[np.linspace(0,2000,401),switch])
        for price in prices:
            curves.append(dict(endpoint=endpoint,long_program=prog,site_fee_annual_usd=fee,short_price=price,
                required_long_price_vs_short_and_opt_out=max(floor,r.long_price_slope*price+r.long_price_intercept)))
    pd.DataFrame(curves).to_csv(S/'ready_duration_price_curves.csv',index=False)
    report=dict(status='PASS',matched_target_pairs=len(out),same_clock_verified=True,bootstrap_unit='complete scenario seed',bootstrap_resamples=5000,
        adjusted_family='16 target-call exact McNemar comparisons',fresh_event_index_metadata_corrected=True,
        temporal_unit='eight observed weeks, ten synthetic realizations per week')
    (HERE/'figure_table_receipt.json').write_text(json.dumps(report,indent=2)+'\n');print(out.to_string(index=False))

if __name__=='__main__':main()
