"""Export complete scenario tables and prespecified downstream comparisons."""
from pathlib import Path
import argparse
import json
import shutil
import numpy as np
import pandas as pd
from scipy.stats import binomtest

from aidrbench.economics.capital import annualized_reserve_cost
from aidrbench.evaluation.firm_flexibility import wilson_lower_bound

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
OUT=ROOT/'results/nature_mainline/workload_composition_v4'
REPEAT=OUT/'repeat_duration_corrected_v2'
SOURCE=ROOT/'manuscript/source_data/nature_workload_composition_v1'


def read(name):return json.loads(((REPEAT if name.startswith('repeat') else OUT)/f'{name}_receipts.json').read_text())


def flatten(rows):
    return pd.DataFrame([r['task']|dict(success=r['success'],**r['ledger'],trace_path=r['trace_path'],
            trace_sha256=r['trace_sha256'],scenario_hash=r['scenario_hash']) for r in rows])


def main(controllers_only=False):
    index=pd.read_parquet(OUT/'scenario_index.parquet')
    index.to_csv(SOURCE/'scenario_index.csv',index=False)
    control_index=pd.read_csv(SOURCE/'control_scenario_index.csv')
    all_index=pd.concat([index,control_index],ignore_index=True)
    for name in ['pi_boundaries.csv','single_dev_summary.csv','single_selected.csv','single_confirm_summary.csv',
                 'repeat_dev_summary.csv','repeat_selected.csv','repeat_confirm_summary.csv','renewable_scenarios.csv']:
        if controllers_only and name=='renewable_scenarios.csv':continue
        shutil.copyfile((REPEAT if name.startswith('repeat') else OUT)/name,SOURCE/name)
    pd.read_parquet(OUT/'pi_scenarios.parquet').to_csv(SOURCE/'pi_scenarios.csv',index=False)
    single=flatten(read('single_confirm'));repeated=flatten(read('repeat_confirm'))
    single.to_csv(SOURCE/'single_confirmation_ledgers.csv',index=False)
    repeated.to_csv(SOURCE/'repeated_confirmation_ledgers.csv',index=False)
    # Notice comparisons retain identical case-specific offers and complete paired seeds.
    notice_rows=[]
    for (case,h),g in single.groupby(['case','duration_h']):
        pivot=g.pivot(index='seed',columns='notice_h',values='success').astype(bool)
        assert len(pivot)==300 and not pivot.isna().any().any()
        for notice in [2,6]:
            lost=int((pivot[0]&~pivot[notice]).sum());gained=int((~pivot[0]&pivot[notice]).sum())
            pv=binomtest(gained,gained+lost,.5).pvalue if gained+lost else 1.
            notice_rows.append(dict(case=case,duration_h=h,notice_h=notice,paired_scenarios=len(pivot),
                zero_notice_successes=int(pivot[0].sum()),notice_successes=int(pivot[notice].sum()),
                lost_successes=lost,gained_successes=gained,mcnemar_exact_p=pv))
    notice=pd.DataFrame(notice_rows);order=np.argsort(notice.mcnemar_exact_p.to_numpy())
    adjusted=np.empty(len(notice));running=0.
    for rank,i in enumerate(order):
        running=max(running,min(1.,notice.iloc[i].mcnemar_exact_p*(len(notice)-rank)));adjusted[i]=running
    notice['holm_p']=adjusted;notice.to_csv(SOURCE/'notice_paired_comparisons.csv',index=False)
    # Four fresh calls must ALL pass; each 4-call programme is one trial.
    pair_rows=[];economic_groups=[]
    chosen=pd.read_csv(REPEAT/'repeat_selected.csv')
    for (case,h,program),g in repeated.groupby(['case','duration_h','program']):
        fresh=g[g.tag.str.startswith('fresh')].pivot(index='seed',columns='tag',values='success')
        assert fresh.shape==(300,4)
        fresh=fresh.all(axis=1).sort_index()
        original=g[g.tag=='single_offer_repeated'].set_index('seed').sort_index()
        assert original.index.equals(fresh.index)
        diff=original.success.astype(int).to_numpy()-fresh.astype(int).to_numpy()
        rng=np.random.default_rng(20260909);draw=rng.integers(0,300,size=(10000,300))
        low,high=np.quantile(diff[draw].mean(axis=1)*100,[.025,.975])
        k=int(original.success.sum());kf=int(fresh.sum())
        cap=float(chosen[(chosen.case==case)&(chosen.duration_h==h)].iloc[0].capacity_kw)
        selected=g[g.tag=='selected_repeat'] if cap>0 and abs(cap-original.capacity_kw.iloc[0])>1e-12 else original.reset_index()
        if cap<=0:selected=g.iloc[:0]
        ks=int(selected.success.sum()) if len(selected) else 0
        row=dict(case=case,duration_h=h,program=program,trials=300,single_offer_kw=float(original.capacity_kw.iloc[0]),
            repeated_successes=k,fresh_joint_successes=kf,repeated_lower=wilson_lower_bound(k,300,.95),
            fresh_joint_lower=wilson_lower_bound(kf,300,.95),paired_success_difference_pp=float(diff.mean()*100),
            paired_difference_ci_low_pp=float(low),paired_difference_ci_high_pp=float(high),
            selected_repeat_kw=cap,selected_successes=ks,
            selected_wilson_lower=wilson_lower_bound(ks,300,.95) if cap>0 else 0.)
        pair_rows.append(row)
        economic_groups.append(('repeated_original',case,h,program,original.reset_index()))
        if len(selected):economic_groups.append(('repeated',case,h,program,selected))
    pd.DataFrame(pair_rows).to_csv(SOURCE/'repeat_paired_comparisons.csv',index=False)
    for (case,h),g in single[single.notice_h==0].groupby(['case','duration_h']):
        economic_groups.append(('single',case,h,'single',g))
    controls=flatten(read('control_confirm'))
    controls.to_csv(SOURCE/'control_confirmation_ledgers.csv',index=False)
    for (case,h),g in controls.groupby(['case','duration_h']):
        economic_groups.append(('single_control',case,h,'single',g))
    econ=[];price_sens=[];reserve_sens=[]
    for kind,case,h,program,g in economic_groups:
        g=g.sort_values('seed');assert len(g)==300
        k=float(g.capacity_kw.iloc[0]);assert g.capacity_kw.nunique()==1
        peak=float(all_index[all_index.case==case].operating_peak_kw.iloc[0]);scale=1000/peak
        number=50 if kind.startswith('single') else 12
        rng=np.random.default_rng(20260910);draw=rng.integers(0,len(g),size=(2000,number))
        qualified=wilson_lower_bound(int(g.success.sum()),len(g),.95)>=.95
        for delay_price in [0.,.001,.005,.01]:
            base=delay_price*g.delay_exposure_gpu_h_h.to_numpy()+.1*g.incremental_energy_kwh.to_numpy()-.05*g.capped_delivered_energy_kwh.to_numpy()
            for fixed in [10000.,25000.,50000.]:
                for value in [0.,.25,.5,1.]:
                    for missed_price in ([0.,.25,1.] if value==0. and fixed==25000. and delay_price==.005 else [0.]):
                        expense=base+value*g.deferred_work_gpu_h.to_numpy()+missed_price*np.maximum(g.incremental_missed_gpu_h.to_numpy(),0)
                        annual=scale*expense[draw].sum(axis=1)+fixed
                        threshold=float(np.quantile(annual,.95)/(k*scale))
                        row=dict(kind=kind,case=case,duration_h=h,program=program,offered_kw=k,operating_peak_kw=peak,
                            accounting_scale_factor=scale,accounting_offered_kw=k*scale,qualified=qualified,
                            qualification_scope='confirmation Wilson criterion; pointwise',
                            selected_by_repeated_development=(kind=='repeated'),
                            annual_independent_units=number,delay_price=delay_price,fixed_site_cost=fixed,
                            effective_displaced_value_usd_gpu_h=value,missed_work_price=missed_price,
                            risk_adjusted_capacity_payment_usd_kw_year=max(0.,threshold))
                        price_sens.append(row)
                        if delay_price==.005 and fixed==25000. and missed_price==0 and value in [0.,.25,.5]:
                            row=row.copy();row['regime']='slack' if value==0 else f'displacement_{value}'
                            row['mean_delay_exposure_gpu_h_h']=float(g.delay_exposure_gpu_h_h.mean())
                            row['mean_incremental_missed_gpu_h']=float(g.incremental_missed_gpu_h.mean())
                            row['max_incremental_missed_gpu_h']=float(g.incremental_missed_gpu_h.max())
                            row['capacity_payment_expected_break_even']=max(0.,float(annual.mean()/(k*scale)))
                            econ.append(row)
                            if value==0:
                                add=annualized_reserve_cost(reserved_capacity_kw=.15,installed_cost_per_reserved_kw=2500,
                                    discount_rate=.08,economic_life_years=4,salvage_fraction=.1,annual_om_fraction=.03)
                                econ.append(row|dict(regime='reserved_headroom',
                                    risk_adjusted_capacity_payment_usd_kw_year=max(0.,threshold+add),
                                    capacity_payment_expected_break_even=max(0.,float(annual.mean()/(k*scale))+add)))
                                for life in [3,4,5,6]:
                                    reserve_add=annualized_reserve_cost(reserved_capacity_kw=.15,installed_cost_per_reserved_kw=2500,
                                        discount_rate=.08,economic_life_years=life,salvage_fraction=.1,annual_om_fraction=.03)
                                    reserve_sens.append(row|dict(regime='reserved_headroom',economic_life_years=life,
                                        risk_adjusted_capacity_payment_usd_kw_year=max(0.,threshold+reserve_add)))
    pd.DataFrame(econ).to_csv(SOURCE/'economic_primary.csv',index=False)
    pd.DataFrame(price_sens).to_csv(SOURCE/'economic_price_sensitivity.csv',index=False)
    pd.DataFrame(reserve_sens).to_csv(SOURCE/'reserve_life_sensitivity.csv',index=False)
    if controllers_only:
        report=dict(status='controller_analysis_complete_renewable_pending',single_confirmation_replays=len(single),
            repeat_confirmation_replays=len(repeated),control_confirmation_replays=len(controls),
            selected_repeat_candidates=int((chosen.capacity_kw>0).sum()))
        (HERE/'controller_analysis_receipt.json').write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps(report,indent=2));return
    renewable=pd.concat([pd.read_csv(OUT/'renewable_scenarios.csv'),pd.read_csv(SOURCE/'control_renewable_scenarios.csv')],ignore_index=True);contrasts=[]
    for (case,bess,analysis),g in renewable.groupby(['case','bess_enabled','analysis']):
        metric='pv_rated_kw' if analysis=='pv_hosting' else 'pv_utilisation_fraction'
        pivot=g.pivot(index='seed',columns='dc_operation',values=metric)
        good=g.status.eq('optimal').all()
        assert len(pivot)==100
        diff=(pivot.flexible-pivot.rigid).to_numpy()
        factor=1. if analysis=='pv_hosting' else 100.
        rng=np.random.default_rng(20260911);draw=rng.integers(0,100,size=(10000,100))
        lo,hi=np.quantile(diff[draw].mean(axis=1)*factor,[.025,.975])
        contrasts.append(dict(case=case,bess_enabled=bess,analysis=analysis,all_scenarios_optimal=bool(good),
            scenarios=100,rigid_min=float(pivot.rigid.min()),flexible_min=float(pivot.flexible.min()),
            difference_of_all_scenario_minima=float(pivot.flexible.min()-pivot.rigid.min()),
            mean_paired_gain=float(diff.mean()*factor),gain_ci_low=float(lo),gain_ci_high=float(hi),
            gain_unit='kW' if analysis=='pv_hosting' else 'percentage_points',
            max_deadline_miss_gpu_h=float(g.deadline_miss_gpu_h.max())))
    pd.DataFrame(contrasts).to_csv(SOURCE/'renewable_paired_comparisons.csv',index=False)
    report=dict(status='analysis_export_complete',source_rows=40522321,
        formal_scenarios=len(index),baseline_all_feasible=bool(index.baseline_service_feasible.all()),
        single_confirmation_replays=len(single),repeat_confirmation_replays=len(repeated),
        renewable_optimisations=len(renewable),source_files=len(list(SOURCE.glob('*'))))
    (HERE/'analysis_receipt.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--controllers-only',action='store_true');args=ap.parse_args()
    main(controllers_only=args.controllers_only)
