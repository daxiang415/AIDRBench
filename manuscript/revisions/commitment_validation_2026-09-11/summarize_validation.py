"""Audit new evidence and prepare plot tables, preserving all solver outcomes."""
import json,shutil,sys
from pathlib import Path
import numpy as np
import pandas as pd
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
sys.path.insert(0,str(HERE.parent/'workload_composition_2026-09-09'))
import run_study_final as m
SOURCE=ROOT/'manuscript/source_data/nature_commitment_validation_v1'
OUT=ROOT/'results/nature_mainline/commitment_validation_v1'

def main():
    rows=[json.loads(p.read_text()) for p in sorted((OUT/'pv_precision').glob('*.json'))];assert len(rows)==1000
    old=pd.concat([pd.read_csv(m.SOURCE/'renewable_scenarios.csv'),pd.read_csv(m.SOURCE/'control_renewable_scenarios.csv')])
    lookup=old.set_index(['case','seed','bess_enabled','dc_operation','analysis']);bound_rows=[]
    for x in rows:
        row=x['row'];s=x['solves'][0];assert s['objective'] is not None and s['num_primal_infeasibilities']==0
        low=s['objective'];up=max(low,-s['mip_dual_bound']) if s['mixed_integer'] else low
        if not s['mixed_integer']:assert s['status']=='optimal' and s['num_dual_infeasibilities']==0
        previous=lookup.loc[(row['case'],row['seed'],row['bess_enabled'],row['dc_operation'],row['analysis'])]
        assert isinstance(previous,pd.Series)
        unit=1. if row['analysis']=='pv_hosting' else 100/previous.total_pv_available_kwh
        bound_rows.append({k:row[k] for k in ['case','seed','bess_enabled','dc_operation','analysis','resolved']}|dict(primary_lower=low,primary_upper=up,reported_lower=low*unit,reported_upper=up*unit,
            previous_value=float(previous.pv_rated_kw if row['analysis']=='pv_hosting' else 100*previous.pv_utilisation_fraction),
            strict_value=float(row['pv_rated_kw'] if row['analysis']=='pv_hosting' else 100*row['pv_utilisation_fraction']) if row['resolved'] else None,
            primary_status=s['status'],primary_mip_gap=s['mip_gap'],primary_mixed_integer=s['mixed_integer']))
    bounds=pd.DataFrame(bound_rows);bounds.to_csv(SOURCE/'pv_primary_bounds.csv',index=False)
    summaries=[];pairrows=[]
    for (case,bess,analysis),g in bounds.groupby(['case','bess_enabled','analysis']):
        rig=g[g.dc_operation=='rigid'].set_index('seed').sort_index();flex=g[g.dc_operation=='flexible'].set_index('seed').sort_index();assert len(rig)==len(flex)==100 and rig.index.equals(flex.index)
        lower=flex.reported_lower-rig.reported_upper;upper=flex.reported_upper-rig.reported_lower
        for seed in rig.index:
            pairrows.append(dict(case=case,bess_enabled=bess,analysis=analysis,seed=int(seed),gain_lower=lower[seed],gain_upper=upper[seed],
                previous_gain=flex.previous_value[seed]-rig.previous_value[seed],strict_gain=flex.strict_value[seed]-rig.strict_value[seed]))
        if analysis=='pv_hosting':
            low=float(flex.reported_lower.min()-rig.reported_upper.min());high=float(flex.reported_upper.min()-rig.reported_lower.min())
            summary=dict(case=case,bess_enabled=bess,analysis=analysis,n=100,rigid_boundary_lower=float(rig.reported_lower.min()),rigid_boundary_upper=float(rig.reported_upper.min()),flexible_boundary_lower=float(flex.reported_lower.min()),flexible_boundary_upper=float(flex.reported_upper.min()),gain_lower=low,gain_upper=high,unresolved_solves=int((~g.resolved).sum()))
        else:
            assert g.resolved.all()
            diff=(flex.strict_value-rig.strict_value).to_numpy();draw=np.random.default_rng(20260911).integers(0,100,(10000,100));lo,hi=np.quantile(diff[draw].mean(axis=1),[.025,.975])
            summary=dict(case=case,bess_enabled=bess,analysis=analysis,n=100,mean_gain=float(diff.mean()),ci_low=float(lo),ci_high=float(hi),gain_lower=float(lower.mean()),gain_upper=float(upper.mean()),unresolved_solves=0,max_abs_change_from_previous_pp=float(np.max(np.abs(diff-(flex.previous_value-rig.previous_value).to_numpy()))))
        summaries.append(summary)
    pd.DataFrame(pairrows).to_csv(SOURCE/'pv_precision_pairs.csv',index=False)
    pd.DataFrame(summaries).to_csv(SOURCE/'pv_precision_summary.csv',index=False)
    # Preserve existing plotting inputs and change only the precisely re-evaluated cells.
    plot=SOURCE/'plot_inputs';plot.mkdir(exist_ok=True)
    nar=ROOT/'manuscript/source_data/nature_commitment_narrative_v1'
    for f in nar.iterdir():
        if f.suffix in ['.csv','.json']:shutil.copy2(f,plot/f.name)
    paired=pd.read_csv(plot/'renewable_paired_comparisons.csv')
    for s in summaries:
        mask=(paired.case==s['case'])&(paired.bess_enabled==s['bess_enabled'])&(paired.analysis==s['analysis']);assert mask.sum()==1
        if s['analysis']=='pv_hosting':
            assert s['gain_upper']-s['gain_lower']<.001
            paired.loc[mask,'difference_of_all_scenario_minima']=(s['gain_lower']+s['gain_upper'])/2
        else:
            for a,b in [('mean_paired_gain','mean_gain'),('gain_ci_low','ci_low'),('gain_ci_high','ci_high')]:paired.loc[mask,a]=s[b]
    paired.to_csv(plot/'renewable_paired_comparisons.csv',index=False)
    # Full experiment outputs and inputs stay separate from compact drawing tables.
    for role in ['development','confirmation']:
        shutil.copy2(OUT/f'{role}_ledgers.csv',SOURCE/f'capacity_{role}_ledgers.csv')
        shutil.copy2(OUT/f'{role}_baseline_receipts.json',SOURCE/f'capacity_{role}_baseline_receipts.json')
    for file in ['capacity_protocol.json','capacity_selection.json','pv_precision_protocol.json']:
        shutil.copy2(HERE/file,SOURCE/file)
    keys=['capacity_selected_confirmed.csv','capacity_confirmation_summary.csv','capacity_development_summary.csv','capacity_confirmation_by_week.csv','power_reconciliation.json','fixed_overhead_summary.csv','pv_precision_pairs.csv','pv_precision_summary.csv']
    for key in keys:shutil.copy2(SOURCE/key,plot/key)
    verify=json.loads((SOURCE/'fixed_overhead_audit.json').read_text());assert verify['all_success_flags_preserved'] and verify['minimum_pcc_margin_kw']>0
    r=dict(status='PASS',new_capacity_replays=2700,independent_confirmation_draws=300,source_observed_weeks=8,unit='conditional simulated draws from fixed empirical-week mixture',
        pv_repeat_optimizations=1000,pv_unresolved_hosting_solves=sum(not x['row']['resolved'] for x in rows),all_fixed_PV_solves_resolved=True,hosting_boundary_gains_bounded_within_kw=.001,
        overhead_witness_schedule_rescores=2400,power_sum_absolute_error_kw=abs(json.loads((SOURCE/'power_reconciliation.json').read_text())['component_sum_kw']-193.4389798490304),sources={name:m.sha(SOURCE/name) for name in keys})
    m.save(SOURCE/'validation_audit.json',r);print(pd.DataFrame(summaries).to_string(index=False));print(json.dumps(r,indent=2))
if __name__=='__main__':main()
