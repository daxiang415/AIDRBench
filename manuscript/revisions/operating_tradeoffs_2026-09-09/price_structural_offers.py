"""Price each new candidate using its own full ledger and qualification scope."""
import json
import numpy as np
import pandas as pd
import run_tradeoffs as r
from decompose_costs import quantile_components

SOURCE=r.ROOT/'manuscript/source_data/nature_operating_tradeoffs_v1'


def main():
    data=pd.read_csv(r.OUT/'confirmation_ledgers.csv').query('kind == "repeated"')
    selections=pd.read_csv(SOURCE/'selected_offers_confirmed.csv')
    summary=pd.read_csv(SOURCE/'confirmation_summary.csv')
    rows=[];components=[]
    for (variant,program,fraction),g in data.groupby(['variant','program','fraction']):
        g=g.sort_values('seed');assert len(g)==300
        k=float(g.capacity_kw.iloc[0]);peak=float(g.operating_peak_kw.iloc[0]);scale=1000/peak;offer=k*scale
        flags={}
        for endpoint in ['success_1pct','success_zero']:
            chosen=selections[(selections.variant==variant)&(selections.program==program)&(selections.endpoint==endpoint)&np.isclose(selections.selected_fraction,fraction)]
            flags['offerable_'+endpoint]=bool(len(chosen) and chosen.offerable.iloc[0])
        tag=dict(variant=variant,program=program,fraction=fraction,capacity_kw=k,operating_peak_kw=peak,accounting_offered_kw=offer,**flags)
        draws=np.random.default_rng(20260910).integers(0,300,size=(2000,12))
        for waiting in [0.,.005,.01]:
            for loss in [0.,1.]:
                unit=np.column_stack([.1*g.incremental_energy_kwh,waiting*g.delay_exposure_gpu_h_h,-.05*g.capped_delivered_energy_kwh,loss*g.incremental_missed_gpu_h])
                annual=scale*unit[draws].sum(axis=1);parts=quantile_components(annual);total=float(parts.sum())
                if waiting==.005 and loss==0:
                    components.append(tag|dict(net_operating_annual_q95=total,net_operating_per_kw_q95=total/offer,
                        **dict(zip(['energy_annual_usd_at_total_q95','waiting_annual_usd_at_total_q95','delivery_credit_annual_usd_at_total_q95','missed_work_annual_usd_at_total_q95'],map(float,parts)))))
                for site in [0.,1000.,2500.,5000.,10000.,25000.]:
                    rows.append(tag|dict(annual_units=12,waiting_price=waiting,missed_work_price=loss,site_fee_annual_usd=site,
                        net_operating_annual_q95=total,fixed_fee_per_kw=site/offer,unfloored_payment_per_kw=(site+total)/offer,
                        payment_per_kw=max(0.,(site+total)/offer)))
    table=pd.DataFrame(rows)
    table.to_csv(SOURCE/'structural_economic_sensitivity.csv',index=False)
    table[(table.waiting_price==.005)&(table.missed_work_price==0)&table.site_fee_annual_usd.isin([0.,25000.])].to_csv(SOURCE/'structural_economic_primary.csv',index=False)
    components=pd.DataFrame(components);components.to_csv(SOURCE/'structural_cost_components.csv',index=False)
    frontier=[]
    for endpoint in ['success_1pct','success_zero']:
        qualified=components[(components.variant==r.REFERENCE_VARIANT)&components['offerable_'+endpoint]]
        short=qualified[qualified.program=='H4P16']
        if len(short)!=1:continue
        short=short.iloc[0]
        for _,long in qualified[qualified.program.str.startswith('H8')].iterrows():
            for short_price in [0.,50.,100.,250.,500.,750.,1000.,1500.,2000.]:
                slope=short.accounting_offered_kw/long.accounting_offered_kw
                intercept=(long.net_operating_annual_q95-short.net_operating_annual_q95)/long.accounting_offered_kw
                for site in [0.,2500.,25000.]:
                    short_value=short_price*short.accounting_offered_kw-short.net_operating_annual_q95-site
                    required=(max(0.,short_value)+long.net_operating_annual_q95+site)/long.accounting_offered_kw
                    frontier.append(dict(endpoint=endpoint,short_program=short.program,short_capacity_kw=short.capacity_kw,long_program=long.program,
                        long_capacity_kw=long.capacity_kw,short_price=short_price,site_fee_annual_usd=site,long_price_slope=slope,long_price_intercept=intercept,
                        required_long_price_if_participating=slope*short_price+intercept,required_long_price_vs_short_and_opt_out=required))
    pd.DataFrame(frontier).to_csv(SOURCE/'structural_duration_price_frontier.csv',index=False)
    r.m.save(r.HERE/'structural_economics_receipt.json',dict(status='COMPLETE',priced_candidates=len(components),sensitivity_rows=len(rows),duration_price_rows=len(frontier),
        complete_confirmation_ledgers_included=True,quantile_components_are_additive=True,offers_require_development_selection_and_confirmation=True))
    print(components[components.variant==r.REFERENCE_VARIANT].to_string(index=False),flush=True)


if __name__=='__main__':main()
