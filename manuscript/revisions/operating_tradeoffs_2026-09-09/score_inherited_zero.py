"""Rescore existing offers; do not treat this retrospective check as new testing."""
import json
import numpy as np
import pandas as pd
import run_tradeoffs as r

BASE=r.ROOT/'manuscript/source_data/nature_workload_composition_v1'
REP=r.ROOT/'manuscript/source_data/nature_repeat_mechanism_v1'
SOURCE=r.ROOT/'manuscript/source_data/nature_operating_tradeoffs_v1'


def main():
    index=pd.read_csv(BASE/'scenario_index.csv')
    totals=index.groupby('case').total_flexible_gpu_h.first().to_dict()
    baseline=index.groupby('case').baseline_deadline_miss_rate.max()
    assert (baseline*pd.Series(totals)<=1e-7).all()
    # Verify rather than assume the new repeated baselines and exact work totals.
    baseline_files=0
    for case in totals:
        for path in sorted((REP/'recovery_inputs/confirmation'/case).glob('*/no_response_full.parquet')):
            frame=pd.read_parquet(path,columns=['arrival_gpu_h','missed_gpu_h'])
            assert np.isclose(frame.arrival_gpu_h.sum(),totals[case],atol=1e-7)
            assert frame.missed_gpu_h.sum()<=1e-7
            baseline_files+=1
    assert baseline_files==1500
    d=pd.read_csv(BASE/'all_trial_event_outcomes.csv')
    d=d[(d.stage=='single_confirm')&(d.notice_h==0)].copy()
    assert len(d)==3000
    e=pd.read_csv(REP/'confirmation_events.csv')
    e=e[e.controller=='all_window_mpc'].copy()
    selected=pd.read_csv(REP/'selected_offers.csv')
    output=[]
    for kind,data,fields in [('single',d,['case','duration_h']),('repeated',e,['case','program','fraction'])]:
        for key,g in data.groupby(fields):
            tag=dict(zip(fields,key));case=tag['case']
            if kind=='single':is_selected=True
            else:
                s=selected[(selected.case==case)&(selected.program==tag['program'])&(selected.controller=='all_window_mpc')]
                is_selected=bool(len(s) and np.isclose(s.selected_fraction.iloc[0],tag['fraction']))
            rows=[]
            for seed,part in g.groupby('seed'):
                miss=float(part.deadline_miss_rate.max())*totals[case]
                success=bool(part.success.all())
                rows.append((success,success and miss<=1e-7,miss))
            n=len(rows);assert n==300
            k=sum(x[0] for x in rows);z=sum(x[1] for x in rows)
            output.append(dict(kind=kind,case=case,program=tag.get('program',f'H{tag.get("duration_h",8)}'),fraction=tag.get('fraction',1.),
                selected_in_original_development=is_selected,trials=n,successes_1pct=k,successes_zero=z,zero_wilson_lower=r.m.wilson_lower_bound(z,n,.95),
                zero_qualified=r.m.wilson_lower_bound(z,n,.95)>=.95,max_missed_gpu_h=max(x[2] for x in rows),
                zero_successes_are_subset_of_original_successes=True))
    table=pd.DataFrame(output);table.to_csv(SOURCE/'inherited_zero_deadline_check.csv',index=False)
    report=dict(status='PASS',rows=len(table),selected_offer_rows=int(table.selected_in_original_development.sum()),
        selected_joint_success_counts_unchanged=bool((table.query('selected_in_original_development').successes_1pct==table.query('selected_in_original_development').successes_zero).all()),
        scope='retrospective scoring of existing confirmation data; no new certification or capacity reselection',zero_tolerance_gpu_h=1e-7,
        new_repeated_baselines_individually_checked=baseline_files)
    (r.HERE/'inherited_zero_audit.json').write_text(json.dumps(report,indent=2)+'\n')
    print(table.query('case == "f10"').to_string(index=False));print(json.dumps(report,indent=2))


if __name__=='__main__':main()
