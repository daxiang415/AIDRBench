"""Cross-score existing trials and price the new independently selected offers."""
import json
import numpy as np
import pandas as pd
import refine_offers as f
from decompose_costs import quantile_components
r=f.r

def cross_score():
    old=pd.read_csv(f.ROOT/'manuscript/source_data/nature_operating_tradeoffs_v1/temporal_ledgers.csv')
    d=old[old.variant.str.contains('chronological_g10')&(old.program=='H8P16')&old.fraction.isin([.5,.75])].copy()
    d['week']=d.variant.str.extract(r'w(\d+)')[0].astype(int)
    assert (d.success_1pct==d.success_zero).all()
    assert ((~d.success_1pct)==(d.instantaneous_supply_shortfall_hours>0)).all()
    d.to_csv(f.SOURCE/'external_cross_scored_trials.csv',index=False)
    rows=[]
    for (week,frac),g in d.groupby(['week','fraction']):
        rows.append(dict(week=week,fraction=frac,capacity_kw=float(g.capacity_kw.iloc[0]),trials=len(g),successes_1pct=int(g.success_1pct.sum()),successes_zero=int(g.success_zero.sum()),instantaneous_shortage=int((g.instantaneous_supply_shortfall_hours>0).sum()),deadline_failures=int(g.failure_deadline_miss.sum())))
    pd.DataFrame(rows).to_csv(f.SOURCE/'external_cross_score_weekly.csv',index=False)

def economics():
    d=pd.read_csv(f.OUT/'confirmation_ledgers.csv');sel=pd.read_csv(f.SOURCE/'refinement_selected_confirmed.csv')
    costs=[];exposure=[];components=[]
    draws=np.random.default_rng(20260910).integers(0,300,size=(2000,12))
    for (p,frac),g in d.groupby(['program','fraction']):
        g=g.sort_values('seed');assert len(g)==300
        K=float(g.capacity_kw.iloc[0]);peak=float(g.operating_peak_kw.iloc[0]);scale=1000/peak;offer=scale*K
        flags={e:bool(((sel.program==p)&(sel.endpoint==e)&np.isclose(sel.selected_fraction,frac)&sel.offerable).any()) for e in ['success_1pct','success_zero']}
        base=dict(program=p,fraction=frac,capacity_kw=K,operating_peak_kw=peak,accounting_offered_kw=offer,offerable_1pct=flags['success_1pct'],offerable_zero=flags['success_zero'])
        for metric in ['delay_exposure_gpu_h_h','incremental_missed_gpu_h','incremental_energy_kwh','capped_delivered_energy_kwh','deferred_work_gpu_h']:
            values=g[metric].to_numpy();annual=scale*values[draws].sum(axis=1)
            exposure.append(base|dict(metric=metric,model_series_mean=float(values.mean()),model_series_p05=float(np.quantile(values,.05)),model_series_p95=float(np.quantile(values,.95)),accounting_annual_mean=float(annual.mean()),accounting_annual_p05=float(np.quantile(annual,.05)),accounting_annual_p95=float(np.quantile(annual,.95))))
        for wait in [0.,.005,.01]:
            for loss in [0.,1.]:
                unit=np.column_stack([.1*g.incremental_energy_kwh,wait*g.delay_exposure_gpu_h_h,-.05*g.capped_delivered_energy_kwh,loss*g.incremental_missed_gpu_h])
                annual=scale*unit[draws].sum(axis=1);parts=quantile_components(annual);net=float(parts.sum())
                if wait==.005 and loss==0:
                    components.append(base|dict(net_operating_annual_q95=net,net_operating_per_kw_q95=net/offer,energy_annual_usd=float(parts[0]),waiting_annual_usd=float(parts[1]),delivery_credit_annual_usd=float(parts[2]),missed_work_annual_usd=float(parts[3])))
                for fee in [0.,1000.,2500.,5000.,10000.,25000.]:
                    costs.append(base|dict(waiting_price=wait,missed_work_price=loss,site_fee_annual_usd=fee,net_operating_annual_q95=net,payment_per_kw=max(0.,(fee+net)/offer)))
    cost=pd.DataFrame(costs);cost.to_csv(f.SOURCE/'refinement_economic_sensitivity.csv',index=False)
    pd.DataFrame(exposure).to_csv(f.SOURCE/'physical_operating_exposure.csv',index=False)
    comp=pd.DataFrame(components);comp.to_csv(f.SOURCE/'refinement_cost_components.csv',index=False)
    front=[];curves=[];examples=[]
    for endpoint in ['1pct','zero']:
        for (wait,loss,fee),g in cost[cost['offerable_'+endpoint]].groupby(['waiting_price','missed_work_price','site_fee_annual_usd']):
            a=g[g.program=='H4P16'].iloc[0];b=g[g.program=='H8P16'].iloc[0];K4=a.accounting_offered_kw;K8=b.accounting_offered_kw;O4=a.net_operating_annual_q95;O8=b.net_operating_annual_q95
            tag=dict(endpoint=endpoint,waiting_price=wait,missed_work_price=loss,site_fee_annual_usd=fee,capacity_4h_kw=a.capacity_kw,capacity_8h_kw=b.capacity_kw,accounting_offer_4h=K4,accounting_offer_8h=K8,operating_4h_annual=O4,operating_8h_annual=O8,slope=K4/K8,intercept=(O8-O4)/K8,nonparticipation_floor=(O8+fee)/K8,four_hour_entry=(O4+fee)/K4)
            front.append(tag)
            if endpoint=='zero' and loss==0 and fee==0:
                x=np.unique(np.r_[np.arange(0.,1501.,5.),tag['four_hour_entry']])
                for price4 in x:curves.append(tag|dict(price_4h=price4,required_price_8h=(max(0.,price4*K4-O4-fee)+O8+fee)/K8))
            if wait==.005 and loss==0 and fee==0:
                for price in [250.,500.,750.]:examples.append(tag|dict(price_4h=price,price_8h=price,net_value_q05_4h=price*K4-O4-fee,net_value_q05_8h=price*K8-O8-fee))
    pd.DataFrame(front).to_csv(f.SOURCE/'refinement_price_frontier.csv',index=False);pd.DataFrame(curves).to_csv(f.SOURCE/'ready_refinement_price_curves.csv',index=False);pd.DataFrame(examples).to_csv(f.SOURCE/'refinement_entry_examples.csv',index=False)
    print(comp.to_string(index=False));print(pd.DataFrame(front).query('endpoint=="zero" and waiting_price==.005 and missed_work_price==0 and site_fee_annual_usd==0').to_string(index=False))

if __name__=='__main__':cross_score();economics()
