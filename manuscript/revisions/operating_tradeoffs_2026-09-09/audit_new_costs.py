"""Independent scalar-quantile check of every new price and product frontier."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
H=Path(__file__).resolve().parent;S=H.parents[2]/'manuscript/source_data/nature_operating_tradeoffs_v1'
def main():
    data=pd.read_csv(S/'confirmation_ledgers.csv');table=pd.read_csv(S/'structural_economic_sensitivity.csv');selected=pd.read_csv(S/'selected_offers_confirmed.csv')
    index=np.random.default_rng(20260910).integers(0,300,(2000,12));errors=[]
    for key,g in table.groupby(['variant','program','fraction']):
        v,p,f=key;ledger=data[(data.variant==v)&(data.program==p)&(data.kind=='repeated')&np.isclose(data.fraction,f)].sort_values('seed');assert len(ledger)==300
        scale=1000/ledger.operating_peak_kw.iloc[0];capacity=ledger.capacity_kw.iloc[0]*scale
        for row in g.itertuples():
            episode=(.1*ledger.incremental_energy_kwh+row.waiting_price*ledger.delay_exposure_gpu_h_h+row.missed_work_price*ledger.incremental_missed_gpu_h-.05*ledger.capped_delivered_energy_kwh).to_numpy()*scale
            operating=float(np.quantile(episode[index].sum(axis=1),.95,method='linear'))
            expected=max(0,(operating+row.site_fee_annual_usd)/capacity)
            errors.append(abs(row.payment_per_kw-expected));assert abs(row.net_operating_annual_q95-operating)<1e-7
            for endpoint in ['success_zero','success_1pct']:
                sel=selected[(selected.variant==v)&(selected.program==p)&(selected.endpoint==endpoint)]
                offerable=bool(len(sel)==1 and np.isclose(sel.selected_fraction.iloc[0],f) and sel.offerable.iloc[0])
                assert getattr(row,'offerable_'+endpoint)==offerable
        byprice=g.groupby(['waiting_price','missed_work_price'])
        for _,prices in byprice:
            z=prices.sort_values('site_fee_annual_usd');assert np.allclose(np.diff(z.unfloored_payment_per_kw),np.diff(z.site_fee_annual_usd)/capacity)
    assert max(errors)<1e-7
    costs=pd.read_csv(S/'structural_cost_components.csv');front=pd.read_csv(S/'structural_duration_price_frontier.csv')
    for r in front.itertuples():
        candidates=costs[(costs.variant=='u65d100g10')&costs['offerable_'+r.endpoint]]
        short=candidates[candidates.program==r.short_program].iloc[0];long=candidates[candidates.program==r.long_program].iloc[0]
        lhs=r.required_long_price_vs_short_and_opt_out*long.accounting_offered_kw-long.net_operating_annual_q95-r.site_fee_annual_usd
        rhs=max(0,r.short_price*short.accounting_offered_kw-short.net_operating_annual_q95-r.site_fee_annual_usd)
        assert abs(lhs-rhs)<1e-7
    report=dict(status='PASS',all_price_rows=len(table),all_candidate_ledgers=36,all_duration_frontier_rows=len(front),max_price_error=max(errors),selection_flags_independently_checked=True,fixed_fee_additivity_checked=True)
    (H/'new_economic_audit.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
