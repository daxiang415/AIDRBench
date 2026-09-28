"""Exact fee/operating decomposition using the already delivered paired ledgers."""
import json
from pathlib import Path
import sys
import numpy as np
import pandas as pd

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
SOURCE=ROOT/'manuscript/source_data/nature_operating_tradeoffs_v1'
BASE=ROOT/'manuscript/source_data/nature_workload_composition_v1'
REPEAT=ROOT/'manuscript/source_data/nature_repeat_mechanism_v1'


def quantile_components(components, q=.95):
    total=components.sum(axis=1)
    order=np.argsort(total,kind='stable')
    pos=(len(total)-1)*q;i=int(np.floor(pos));j=int(np.ceil(pos));w=pos-i
    parts=(1-w)*components[order[i]]+w*components[order[j]]
    assert np.isclose(parts.sum(),np.quantile(total,q),atol=1e-8)
    return parts


def groups():
    index=pd.read_csv(BASE/'scenario_index.csv')
    peaks=index.groupby('case').operating_peak_kw.first().to_dict()
    d=pd.read_csv(BASE/'single_confirmation_ledgers.csv').query('notice_h == 0')
    expected=pd.read_csv(BASE/'economic_primary.csv')
    for (case,h),g in d.groupby(['case','duration_h']):
        row=expected[(expected.case==case)&(expected.duration_h==h)&(expected.kind=='single')&(expected.regime=='slack')]
        assert len(row)==1
        yield dict(kind='single',case=case,program=f'H{h}',duration_h=int(h),capacity_kw=float(g.capacity_kw.iloc[0]),operating_peak_kw=peaks[case],annual_units=50,reference_payment=float(row.risk_adjusted_capacity_payment_usd_kw_year.iloc[0])),g
    d=pd.read_csv(REPEAT/'confirmation_ledgers.csv')
    expected=pd.read_csv(REPEAT/'economic_primary.csv')
    selected=expected[(expected.controller=='all_window_mpc')&(expected.regime=='slack')&expected.offerable_selected_option]
    for _,row in selected.iterrows():
        g=d[(d.case==row.case)&(d.program==row.program)&(d.controller==row.controller)&np.isclose(d.fraction,row.fraction)]
        yield dict(kind='repeated',case=row.case,program=row.program,duration_h=int(row.duration_h),capacity_kw=float(row.capacity_kw),operating_peak_kw=peaks[row.case],annual_units=12,reference_payment=float(row.payment_usd_kw_year)),g


def main():
    components=[];fees=[];choices=[];audit=[];valuation=[]
    for tag,g in groups():
        g=g.sort_values('seed');assert len(g)==300
        scale=1000/tag['operating_peak_kw'];offered=tag['capacity_kw']*scale
        draw=np.random.default_rng(20260910).integers(0,len(g),size=(2000,tag['annual_units']))
        for wait in [0.,.005,.01]:
            for loss in [0.,1.]:
                per_unit=np.column_stack([.1*g.incremental_energy_kwh,wait*g.delay_exposure_gpu_h_h,
                    -.05*g.capped_delivered_energy_kwh,loss*g.incremental_missed_gpu_h])
                annual=scale*per_unit[draw].sum(axis=1)
                qparts=quantile_components(annual);qtotal=float(qparts.sum())
                costs=dict(zip(['energy','waiting','delivery_revenue_credit','missed_work'],qparts))
                metadata=tag|dict(waiting_price=wait,missed_work_price=loss,accounting_offered_kw=offered,scale=scale)
                if wait==.005 and loss==0:
                    value=max(0.,(qtotal+25000)/offered)
                    assert np.isclose(value,tag['reference_payment'],atol=1e-8),(tag,value)
                    audit.append(tag|dict(recomputed=value,absolute_error=abs(value-tag['reference_payment'])))
                    components.append(metadata|{f'{k}_annual_usd_at_total_q95':float(v) for k,v in costs.items()}|
                        {f'{k}_annual_usd_mean':float(v) for k,v in zip(costs,annual.mean(axis=0))}|
                        dict(net_operating_cost_annual_q95=qtotal,net_operating_cost_per_kw_q95=qtotal/offered,
                            fixed_fee_per_kw=25000/offered,reference_total_payment_per_kw=value,
                            fixed_fee_fraction_of_unfloored_total=25000/(qtotal+25000)))
                for fixed in [0.,1000.,2500.,5000.,10000.,25000.]:
                    raw=(qtotal+fixed)/offered
                    fees.append(metadata|dict(site_fee_annual_usd=fixed,net_operating_annual_q95=qtotal,
                        fixed_fee_per_kw=fixed/offered,unfloored_payment_per_kw=raw,payment_per_kw=max(0.,raw),
                        fee_sharing_equivalent_resources=25000/fixed if fixed else None))
                    if wait==.005 and loss==0:
                        for price in [0.,50.,100.,250.,500.,750.,1000.,1500.,2000.,3000.]:
                            valuation.append(metadata|dict(site_fee_annual_usd=fixed,capacity_price_usd_kw_year=price,
                                annual_net_value_lower=price*offered-qtotal-fixed))
    v=pd.DataFrame(valuation)
    for key,g in v.groupby(['kind','case','site_fee_annual_usd','capacity_price_usd_kw_year']):
        best=g.sort_values(['annual_net_value_lower','program'],ascending=[False,True]).iloc[0]
        choices.append(dict(zip(['kind','case','site_fee_annual_usd','capacity_price_usd_kw_year'],key))|
            dict(best_program_if_participating=best.program,participation=bool(best.annual_net_value_lower>=0),
                chosen_program_including_opt_out=best.program if best.annual_net_value_lower>=0 else 'do_not_participate',
                best_annual_net_value_lower=float(best.annual_net_value_lower),net_value_including_opt_out=max(0.,float(best.annual_net_value_lower))))
    c=pd.DataFrame(choices)
    for _,g in c.groupby(['kind','case','capacity_price_usd_kw_year']):
        assert g.best_program_if_participating.nunique()==1
    # Different duration products need not earn the same capacity price.
    # Solve the required long-duration price algebraically; do not invent a tariff.
    frontiers=[]
    component_frame=pd.DataFrame(components)
    for case,g in component_frame[component_frame.kind=='repeated'].groupby('case'):
        short=g[g.program=='H4G8'].iloc[0]
        for _,long in g[g.duration_h==8].iterrows():
            for short_price in [0.,50.,100.,250.,500.,1000.]:
                conditional=(short_price*short.accounting_offered_kw+long.net_operating_cost_annual_q95-short.net_operating_cost_annual_q95)/long.accounting_offered_kw
                for fee in [0.,2500.,25000.]:
                    short_value=short_price*short.accounting_offered_kw-short.net_operating_cost_annual_q95-fee
                    required=(max(0.,short_value)+long.net_operating_cost_annual_q95+fee)/long.accounting_offered_kw
                    frontiers.append(dict(case=case,long_program=long.program,short_price=short_price,site_fee_annual_usd=fee,
                        required_long_price_if_participating=conditional,
                        required_long_price_vs_short_and_opt_out=required,
                        long_price_slope=short.accounting_offered_kw/long.accounting_offered_kw,
                        long_price_intercept=(long.net_operating_cost_annual_q95-short.net_operating_cost_annual_q95)/long.accounting_offered_kw))
    SOURCE.mkdir(parents=True,exist_ok=True)
    for name,data in [('cost_components',components),('low_shared_fee_sensitivity',fees),('programme_value',valuation),('programme_choices',choices),('cost_reconciliation',audit),('duration_price_frontier',frontiers)]:
        pd.DataFrame(data).to_csv(SOURCE/f'{name}.csv',index=False)
    report=dict(status='PASS',reference_thresholds_reproduced=len(audit),max_absolute_error=max(a['absolute_error'] for a in audit),
        cost_component_rows=len(components),fee_sensitivity_rows=len(fees),net_value_rows=len(valuation),choice_rows=len(choices),
        fixed_fee_invariant_conditional_programme_order=True,duration_price_frontier_rows=len(frontiers),
        quantile_decomposition='shared total-cost rank interpolation, not sum of marginal quantiles',
        annual_scope='50 independent single calls or 12 independent four-call series; no continuously simulated year',
        monetary_scope='declared accounting scenarios; fee sharing does not certify aggregate reliability')
    (HERE/'economic_decomposition_audit.json').write_text(json.dumps(report,indent=2)+'\n')
    print(pd.DataFrame(components).query('case == "f10"')[['kind','program','net_operating_cost_per_kw_q95','fixed_fee_per_kw','reference_total_payment_per_kw','fixed_fee_fraction_of_unfloored_total']].to_string(index=False))
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
