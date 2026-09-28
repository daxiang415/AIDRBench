"""Exact affine fixed-overhead sensitivity of frozen, fully replayed schedules."""
import json,sys
from dataclasses import replace,asdict
from pathlib import Path
import numpy as np
import pandas as pd
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
sys.path.insert(0,str(HERE.parent/'operating_tradeoffs_2026-09-09'))
import run_tradeoffs as r
SOURCE=ROOT/'manuscript/source_data/nature_commitment_validation_v1'

def main():
    SOURCE.mkdir(parents=True,exist_ok=True)
    old=pd.read_csv(ROOT/'manuscript/source_data/nature_commitment_mechanisms_v1/confirmation_ledgers.csv')
    chosen=old[((old.program=='H4P16')&np.isclose(old.fraction,.95))|((old.program=='H8P16')&np.isclose(old.fraction,.75))]
    assert len(chosen)==600
    a=r.m.load_frozen_hourly_scenario(chosen.iloc[0].scenario_path)
    env=r.m.HourlyCommunityAIDemandResponseEnv(r.m._repeated_environment_document(a,notice_h=0,requested_reduction_kw=0));pm=env.power_model
    pue=pm.pue;n=pm.data_center.total_gpu_count;ng=pm.data_center.node_count;nr=pm.data_center.rigid_gpu_count;nf=pm.data_center.flexible_gpu_count
    parts=dict(node_overhead_kw=pue*ng*pm.node_fixed_overhead_w/1000,all_gpu_idle_kw=pue*n*pm.idle_power_w_per_gpu/1000,
        rigid_increment_kw=pue*nr*pm.rigid_gpu_utilization*(pm.rigid_active_power_w_per_gpu-pm.idle_power_w_per_gpu)/1000,
        flexible_reference_increment_kw=pue*nf*(pm.flexible_active_power_w_per_gpu-pm.idle_power_w_per_gpu)/1000)
    assert abs(sum(parts.values())-pm.reference_mix_operating_peak_kw)<1e-10
    r.m.save(SOURCE/'power_reconciliation.json',dict(parameters=asdict(pm),facility_components=parts,component_sum_kw=sum(parts.values()),implemented_operating_peak_kw=pm.reference_mix_operating_peak_kw,
        zero_flexible_execution_floor_kw=pm.predict_by_class({}).dc_power_kw,formula='PUE/1000 * [Nnodes*Pnode + NGPU*Pidle + Nrigid*urig*(Prigid-Pidle) + sum_c (Pactive,c-Pidle)*Xc/dt]',
        scope='reference-mix full-flexible-pool operating peak, not maximum across every possible class mix',source_scenario_hash=a.scenario_hash))
    rows=[]
    for item in chosen.itertuples():
        artifact=r.m.load_frozen_hourly_scenario(item.scenario_path)
        doc=r.m._repeated_environment_document(artifact,notice_h=0,requested_reduction_kw=item.capacity_kw)
        doc['dr']['event_duration_hours']=4 if item.program=='H4P16' else 8
        local=r.m.HourlyCommunityAIDemandResponseEnv(doc);local.reset(seed=item.seed)
        frame=pd.read_parquet(item.trace_path);assert r.m.sha(item.trace_path)==item.trace_sha256
        baseline_path=Path(item.scenario_path.replace('/H4P16/','/H8P16/'))
        receipt=json.loads((baseline_path/'baseline_receipt.json').read_text())
        baseline=pd.read_parquet(baseline_path/'no_response_full.parquet')
        for overhead in [150.,300.,450.,600.]:
            model=replace(pm,node_fixed_overhead_w=overhead)
            delta=(overhead-pm.node_fixed_overhead_w)*ng*pue/1000
            shifted=frame.copy()
            for col in ['pcc_power_kw','baseline_pcc_power_kw','dc_power_kw','baseline_dc_power_kw']:
                if col in shifted:shifted[col]+=delta
            events=r.m.derive_event_outcomes(shifted,local.event_manifest,recovery_tolerance_gpu_h=local.config.recovery_backlog_tolerance_fraction*model.flexible_capacity_gpu_h)
            shifted_baseline=baseline.copy()
            for col in ['pcc_power_kw','baseline_pcc_power_kw','dc_power_kw','baseline_dc_power_kw']:
                if col in shifted_baseline:shifted_baseline[col]+=delta
            rec=dict(receipt);rec['baseline_service_feasible']=r.m.baseline_service_gate(shifted_baseline,rec['baseline_miss_rate'],local.config.pcc_capacity_kw)
            scores=r.score(events,shifted,rec)
            pcc_margin=float(local.config.pcc_capacity_kw-shifted.pcc_power_kw.max())
            rows.append(dict(seed=item.seed,program=item.program,node_overhead_w=overhead,capacity_kw=item.capacity_kw,operating_peak_kw=model.reference_mix_operating_peak_kw,
                fixed_plus_idle_kw=(overhead*ng+n*pm.idle_power_w_per_gpu)*pue/1000,zero_flexible_floor_kw=model.predict_by_class({}).dc_power_kw,
                offer_pct_peak=100*item.capacity_kw/model.reference_mix_operating_peak_kw,offer_kw_per_mw=1000*item.capacity_kw/model.reference_mix_operating_peak_kw,
                single_offer_kw_per_mw=1000*r.REFERENCE/model.reference_mix_operating_peak_kw,single_offer_pct_peak=100*r.REFERENCE/model.reference_mix_operating_peak_kw,
                pcc_margin_kw=pcc_margin,baseline_pcc_margin_kw=float(local.config.pcc_capacity_kw-shifted_baseline.pcc_power_kw.max()),
                witness_success_1pct=scores['success_1pct'] and pcc_margin>=-1e-7,witness_success_zero=scores['success_zero'] and pcc_margin>=-1e-7,
                original_success_1pct=item.success_1pct,original_success_zero=item.success_zero))
    data=pd.DataFrame(rows);data.to_csv(SOURCE/'fixed_overhead_schedule_sensitivity.csv',index=False)
    summary=data.groupby(['program','node_overhead_w']).agg(trials=('seed','size'),successes_1pct=('witness_success_1pct','sum'),successes_zero=('witness_success_zero','sum'),operating_peak_kw=('operating_peak_kw','first'),capacity_kw=('capacity_kw','first'),offer_pct_peak=('offer_pct_peak','first'),offer_kw_per_mw=('offer_kw_per_mw','first'),single_offer_pct_peak=('single_offer_pct_peak','first'),single_offer_kw_per_mw=('single_offer_kw_per_mw','first'),fixed_plus_idle_kw=('fixed_plus_idle_kw','first'),minimum_pcc_margin_kw=('pcc_margin_kw','min'),minimum_baseline_pcc_margin_kw=('baseline_pcc_margin_kw','min')).reset_index()
    summary.to_csv(SOURCE/'fixed_overhead_summary.csv',index=False)
    r.m.save(SOURCE/'fixed_overhead_audit.json',dict(method='exact additive power transformation and event re-scoring of 600 frozen causal schedules; no controller re-optimization or offer selection',power_offset_formula='PUE*Nnodes*(Pnode-300)/1000',all_success_flags_preserved=bool((data.witness_success_1pct==data.original_success_1pct).all() and (data.witness_success_zero==data.original_success_zero).all()),minimum_pcc_margin_kw=float(data.pcc_margin_kw.min()),minimum_baseline_pcc_margin_kw=float(data.baseline_pcc_margin_kw.min()),scope='feasibility witnesses for unchanged schedules with all other assumptions fixed; different fixed fees and absolute PCC limits remain consequential',runner_sha256=r.m.sha(__file__)))
    print(json.dumps(parts,indent=2));print(summary.to_string(index=False))
if __name__=='__main__':main()
