"""Independent arithmetic, split, duration and ledger audit of final evidence."""
from pathlib import Path
import argparse
import hashlib
import json
import math
import numpy as np
import pandas as pd
from scipy.stats import binom,norm
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
OUT=ROOT/'results/nature_mainline/workload_composition_v4'
REP=OUT/'repeat_duration_corrected_v2'
SOURCE=ROOT/'manuscript/source_data/nature_workload_composition_v1'

def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def wilson(k,n):
    z=norm.ppf(.95);q=k/n
    return (q+z*z/(2*n)-z*math.sqrt(q*(1-q)/n+z*z/(4*n*n)))/(1+z*z/n)

def main(controllers_only=False):
    protocol=json.loads((HERE/'protocol_final.json').read_text())
    assert sha(HERE/'run_study_final.py')==protocol['runner_sha256']
    assert sha(ROOT/'configs/controller/nature_robust_mpc_v1.yaml')==protocol['controller_sha256']
    assert sha(HERE/'study_controller_v4.py')==protocol['controller_correction']['sha256']
    for name,digest in protocol['source_files'].items():assert sha(ROOT/name)==digest,name
    repeat_protocol=json.loads((HERE/'repeat_duration_protocol_v2.json').read_text())
    assert sha(HERE/'protocol_final.json')==repeat_protocol['parent_protocol_sha256']
    assert sha(HERE/'run_repeated_duration_v2.py')==repeat_protocol['runner_sha256']
    audit=json.loads((SOURCE/'source_audit.json').read_text());cases=json.loads((SOURCE/'case_definitions.json').read_text())
    assert audit['rows']==40522321 and abs(sum(audit['shares'].values())-1)<1e-12
    for c in cases:
        assert abs(sum(c['eligible_shares'].values())-c['fraction'])<1e-12
        assert c['eligible_shares']['online_inference']==0
        assert abs(sum(c['shares'].values())-1)<1e-12
    index=pd.read_csv(SOURCE/'scenario_index.csv');control=pd.read_csv(SOURCE/'control_scenario_index.csv')
    assert len(index)==2000 and len(control)==1200
    assert index.baseline_service_feasible.all() and control.baseline_service_feasible.all()
    pi=pd.read_csv(SOURCE/'pi_boundaries.csv')
    assert pi.tolerance_order_statistic_rank.eq(2).all()
    assert abs((1-binom.cdf(1,100,.05))-.9629187906726449)<1e-12
    counts={};examples=[];failures=[];records={}
    for stage in ['single_dev','single_confirm','repeat_dev','repeat_confirm','control_confirm']:
        folder=REP if stage.startswith('repeat') else OUT
        rows=json.loads((folder/f'{stage}_receipts.json').read_text());records[stage]=rows;counts[stage]=len(rows)
        isdev=stage.endswith('dev');expected=set(range(930000,930100) if isdev else range(960000,960300))
        assert {r['task']['seed'] for r in rows}==expected
        for r in rows:
            t=r['task'];assert r['success']==all(e['success'] for e in r['events'])
            for ei,e in enumerate(r['events']):
                assert e['duration_h']==t['duration_h'], (stage,t,e)
                assert abs(e['requested_reduction_kw']-t['capacity_kw'])<1e-12
                # Preserve the pre-existing 1e-9 arithmetic tolerance.
                tests=[e['delivery_ratio']+1e-9>=.95,e['minimum_interval_delivery_ratio']+1e-9>=.95,
                    e['deadline_miss_rate']-1e-9<=.01,e['rebound_ratio']-1e-9<=.25,
                    e['window_peak_relief_fraction']+1e-9>=.5,e['terminal_backlog_fraction']-1e-9<=.02]
                assert all(tests)==e['success'], (stage,t,e)
                if stage.startswith('repeat'):
                    sourceid=t.get('event_ids',[0,1,2,3])[ei]
                    assert e['start_hour']==63+sourceid*(t['duration_h']+(8 if t['duration_h']==4 else 12))
                for failure in e['failures']:failures.append(dict(stage=stage,case=t['case'],duration_h=t['duration_h'],tag=t['tag'],failure=failure))
        # Deterministic edge and failure samples, never used to select offers.
        groups={}
        for r in rows:
            t=r['task'];key=(t['case'],t['duration_h'],t['tag'],t.get('notice_h',0));groups.setdefault(key,[]).append(r)
        for key,group in groups.items():
            g=sorted(group,key=lambda r:r['task']['seed']);selected=[g[0],g[-1]]
            failed=next((r for r in g if not r['success']),None)
            if failed is not None:selected.append(failed)
            for r in selected:
                path=Path(r['trace_path']);assert sha(path)==r['trace_sha256']
                f=pd.read_parquet(path);t=r['task']
                b=pd.read_parquet(OUT/t['role']/t['case']/'scenarios/single'/f'hourly_seed_{t["seed"]}'/'no_response_full.parquet')
                assert len(f)==len(b)==216 and f.hour.equals(b.hour)
                core=['pcc_power_kw','dc_power_kw','executed_gpu_h','backlog_gpu_h','missed_gpu_h']
                assert np.isfinite(f[core].to_numpy()).all()
                first=r['events'][0]['start_hour'];mask=f.hour>=first;event=f.event_active.astype(bool)
                assert int(event.sum())==len(r['events'])*t['duration_h']
                # Signed energy and positive waiting; no per-event overlap summation.
                energy=float((f.loc[mask,'pcc_power_kw']-b.loc[mask,'pcc_power_kw']).sum())
                delay=float(np.maximum(f.loc[mask,'backlog_gpu_h']-b.loc[mask,'backlog_gpu_h'],0).sum())
                delivered=float(np.minimum(np.maximum(b.loc[event,'pcc_power_kw']-f.loc[event,'pcc_power_kw'],0),t['capacity_kw']).sum())
                for name,value in [('incremental_energy_kwh',energy),('delay_exposure_gpu_h_h',delay),('capped_delivered_energy_kwh',delivered)]:
                    assert math.isclose(value,r['ledger'][name],rel_tol=1e-10,abs_tol=1e-8),(stage,t,name,value,r['ledger'][name])
                examples.append(dict(stage=stage,case=t['case'],seed=t['seed'],tag=t['tag'],duration_h=t['duration_h'],trace_sha256=r['trace_sha256']))
    for stage in ['single','repeat']:
        folder=REP if stage=='repeat' else OUT
        summary=pd.read_csv(folder/f'{stage}_dev_summary.csv');selected=pd.read_csv(folder/f'{stage}_selected.csv')
        for r in summary.itertuples():assert abs(wilson(r.successes,r.trials)-r.wilson_lower)<1e-12
        for r in selected.itertuples():
            group=summary[(summary.case==r.case)&(summary.duration_h==r.duration_h)]
            ok=group[group.wilson_lower>=.95];expected=float(ok.capacity_kw.max()) if len(ok) else 0.
            assert abs(r.capacity_kw-expected)<1e-12
    if controllers_only:
        pd.DataFrame(failures).value_counts().rename('event_count').reset_index().to_csv(SOURCE/'failure_attribution_counts.csv',index=False)
        pd.DataFrame(examples).drop_duplicates().to_csv(HERE/'ledger_audit_examples.csv',index=False)
        result=dict(status='CONTROLLERS_PASS_RENEWABLE_PENDING',formal_controller_replays=counts,
            inspected_ledger_traces=len(examples),all_formal_event_durations_verified=True)
        (HERE/'controller_numerical_audit.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps(result,indent=2));return
    pv=pd.concat([pd.read_csv(SOURCE/'renewable_scenarios.csv'),pd.read_csv(SOURCE/'control_renewable_scenarios.csv')])
    reconciliation=json.loads((HERE/'numerical_reconciliation.json').read_text())
    assert reconciliation['status']=='PASS'
    assert sha(HERE/'solver_acceleration_protocol.json')==reconciliation['protocol_sha256']
    for choice in reconciliation['choices']:
        cache=OUT/'renewable'/choice['case']/f"{choice['seed']}.json"
        assert sha(cache)==choice['cache_sha256']
        if choice['source']=='multistart':
            receipt=ROOT/choice['receipt'];assert sha(receipt)==choice['receipt_sha256']
            numerical=json.loads(receipt.read_text());assert numerical['status']=='OPTIMAL_COMPLETE'
            assert numerical['rows']==json.loads(cache.read_text())
            for stage in numerical['stages']:
                assert stage['status']=='optimal'
                if stage['mip']:
                    assert stage['gap']<=1e-4+1e-10 or abs(stage['primal']-stage['dual'])<=1e-6+1e-9
    assert len(pv)==7200 and pv.status.eq('optimal').all()
    keys=['case','seed','bess_enabled','dc_operation','analysis']
    assert not pv.duplicated(keys).any()
    assert pv.groupby(['case','bess_enabled','dc_operation','analysis']).size().eq(100).all()
    assert pv.case.nunique()==9 and set(pv.seed)==set(range(960000,960100))
    assert pv.pcc_capacity_kw.eq(1100).all() and pv.dc_scale_of_reference_mix.eq(1).all()
    assert pv.maximum_pcc_import_kw.max()<=1100+1e-5
    assert pv.maximum_simultaneous_bess_charge_discharge_kw.abs().max()<1e-5
    assert pv.terminal_soc_deviation_kwh.abs().max()<1e-5
    assert pv[pv.analysis=='pv_hosting'].pv_utilisation_fraction.min()>=.95-1e-7
    assert pv[pv.analysis=='fixed_pv_operation'].pv_rated_kw.eq(500).all()
    assert pv.deadline_miss_gpu_h.abs().max()<1e-6
    assert np.isfinite(pv[['pv_rated_kw','pv_utilisation_fraction','deadline_miss_gpu_h']].to_numpy()).all()
    economics=pd.read_csv(SOURCE/'economic_primary.csv');assert np.isfinite(economics.risk_adjusted_capacity_payment_usd_kw_year).all()
    assert economics.risk_adjusted_capacity_payment_usd_kw_year.ge(0).all()
    exported=json.loads((SOURCE/'export_receipt.json').read_text());hourly_rows=0
    for path in (SOURCE/'hourly_full').glob('*.parquet'):
        f=pd.read_parquet(path,columns=['pcc_power_kw','dc_power_kw','executed_gpu_h','backlog_gpu_h','missed_gpu_h','paired_no_response_pcc_power_kw','paired_no_response_backlog_gpu_h'])
        assert np.isfinite(f.to_numpy()).all(),path
        hourly_rows+=len(f)
    assert hourly_rows==exported['full_hourly_rows']==sum(counts.values())*216
    pd.DataFrame(failures).value_counts().rename('event_count').reset_index().to_csv(SOURCE/'failure_attribution_counts.csv',index=False)
    pd.DataFrame(examples).drop_duplicates().to_csv(HERE/'ledger_audit_examples.csv',index=False)
    result=dict(status='PASS',primary_no_response_scenarios=len(index),control_no_response_scenarios=len(control),
        formal_controller_replays=counts,all_formal_event_durations_verified=True,
        inspected_ledger_traces=len(examples),renewable_optimisations=len(pv),
        finite_core_columns_verified_hourly_rows=hourly_rows,
        renewable_max_deadline_miss_gpu_h=float(pv.deadline_miss_gpu_h.abs().max()),
        numerical_alternate_groups_used=reconciliation['used_alternate_groups'],
        controller_sha256=sha(HERE/'study_controller_v4.py'),repeat_runner_sha256=sha(HERE/'run_repeated_duration_v2.py'),
        no_confirmatory_offer_reselection=True,old_one_hour_repeat_diagnostics_excluded=True)
    (HERE/'numerical_audit.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--controllers-only',action='store_true');a=ap.parse_args()
    main(controllers_only=a.controllers_only)
