"""Prepare direct plot tables from immutable v0.24 results; no new simulation."""
import hashlib
import json
import shutil
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OLD = ROOT / 'manuscript/source_data/nature_commitment_mechanisms_v1'
BASE = ROOT / 'manuscript/source_data/nature_workload_composition_v1'
PREVIOUS = ROOT / 'manuscript/source_data/nature_operating_tradeoffs_v1'
OUT = ROOT / 'manuscript/source_data/nature_commitment_narrative_v1'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    copied = []
    for source, names in [
        (OLD, ['refinement_selected_confirmed.csv', 'ready_pi_categories.csv',
               'external_cross_score_weekly.csv', 'weighted_week_summary.csv',
               'refinement_development_summary.csv']),
        (BASE, ['single_confirm_summary.csv', 'control_causal_summary.csv',
                'renewable_paired_comparisons.csv']),
        (PREVIOUS, ['confirmation_summary.csv']),
    ]:
        for name in names:
            shutil.copyfile(source / name, OUT / name)
            copied.append(dict(table=name, source=str((source/name).relative_to(ROOT)), sha256=sha(source/name)))
    ledger = pd.read_csv(OLD / 'workload_ledgers.csv')
    rows, examples = [], []
    for r in ledger.itertuples():
        trace = pd.read_parquet(r.trace_path)
        assert sha(Path(r.trace_path)) == r.trace_sha256
        meta = json.loads((Path(r.scenario_path) / 'metadata.json').read_text())
        p = meta['power_model']['parameters']
        dc = p['data_center']; total = dc['node_count'] * dc['gpus_per_node']
        flexible = round(total * dc['flexible_gpu_fraction']); rigid = total-flexible
        fixed = p['pue'] * (total*p['idle_power_w_per_gpu'] + rigid*p['rigid_gpu_utilization']*(p['rigid_active_power_w_per_gpu']-p['idle_power_w_per_gpu']) + dc['node_count']*p['node_fixed_overhead_w']) / 1000
        # An absent class key is logged as NaN when that class executes no work.
        class_columns=[c for c in trace if c.startswith('executed_') and c!='executed_gpu_h' and c.endswith('_gpu_h')]
        np.testing.assert_allclose(trace[class_columns].fillna(0).sum(axis=1),trace.executed_gpu_h,atol=1e-8,rtol=0)
        variable = sum(trace['executed_'+name+'_gpu_h'].fillna(0) * p['pue']*(power-p['idle_power_w_per_gpu'])/1000 for name,power in p['flexible_active_power_w_per_gpu_by_class'] if 'executed_'+name+'_gpu_h' in trace)
        np.testing.assert_allclose(trace.dc_power_kw, fixed+variable, atol=1e-8, rtol=0)
        supply = trace.baseline_pcc_power_kw-trace.community_power_kw-fixed
        margin = supply-.95*r.capacity_kw
        minimum = float(margin[trace.event_active].min())
        deficit_hours = int((margin[trace.event_active] < -1e-7).sum())
        assert deficit_hours == r.instantaneous_supply_shortfall_hours
        np.testing.assert_allclose(max(0,-minimum),r.max_instantaneous_supply_shortfall_kw,atol=1e-10,rtol=0)
        week = (r.seed-990000)//100
        weight = 'resource_gpu_h' if 'resource_gpu_h' in r.variant else 'job_count'
        order = 'chronological' if 'chronological' in r.variant else 'permuted'
        rows.append(dict(week=week,seed=r.seed,weight=weight,ordering=order,fraction=r.fraction,request_kw=r.capacity_kw,minimum_margin_kw=minimum,shortage_hours=deficit_hours,success_1pct=r.success_1pct,success_zero=r.success_zero,baseline_zero_service=r.baseline_zero_service,trace_sha256=r.trace_sha256,scenario_hash=r.scenario_hash))
        if r.seed==990000 and r.fraction==.5:
            ex=trace[['hour','event_active','event_id','baseline_pcc_power_kw','community_power_kw']].copy()
            ex['weight']=weight;ex['ordering']=order;ex['request_kw']=r.capacity_kw;ex['fixed_dc_power_kw']=fixed;ex['available_reduction_kw']=supply;ex['supply_margin_kw']=margin
            examples.append(ex)
    trial=pd.DataFrame(rows);assert len(trial)==640 and trial.baseline_zero_service.all()
    trial.to_csv(OUT/'supply_margin_trials.csv',index=False)
    pd.concat(examples,ignore_index=True).to_csv(OUT/'supply_hourly_example.csv',index=False)
    summary=[]
    for (weight,order,frac),g in trial.groupby(['weight','ordering','fraction']):
        summary.append(dict(weight=weight,ordering=order,fraction=frac,trials=len(g),successes_1pct=int(g.success_1pct.sum()),successes_zero=int(g.success_zero.sum()),instantaneous_shortage=int((g.shortage_hours>0).sum())))
    summary=pd.DataFrame(summary);summary.to_csv(OUT/'timing_cross_summary.csv',index=False)
    original=pd.read_csv(OLD/'weighted_week_summary.csv').groupby(['weight','ordering','fraction'])[['trials','successes_1pct','successes_zero','instantaneous_shortage']].sum().sort_index()
    pd.testing.assert_frame_equal(summary.set_index(['weight','ordering','fraction']).sort_index()[original.columns],original)
    pairs=trial[(trial.weight=='resource_gpu_h') & (trial.fraction==.5)].pivot(index=['week','seed'],columns='ordering',values='minimum_margin_kw').reset_index()
    assert len(pairs)==80 and not pairs.isna().any().any()
    pairs.to_csv(OUT/'paired_resource_supply_margins.csv',index=False)
    cells={}
    for x in [False,True]:
        for y in [False,True]:
            cells[f'original_shortage_{x}_permuted_shortage_{y}']=int(((pairs.chronological.lt(-1e-7)==x)&(pairs.permuted.lt(-1e-7)==y)).sum())
    receipt=dict(status='PASS',new_simulations=0,recomputed_ledger_rows=640,example_seed=990000,example_selection='Lowest protocol seed; all four representations at fraction 0.5',copied_tables=copied,paired_supply_quadrants=cells,all_original_ledgers_unchanged=True)
    (HERE/'data_validation.json').write_text(json.dumps(receipt,indent=2)+'\n')
    (OUT/'derivation_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(summary.to_string(index=False));print(cells)


if __name__=='__main__':main()
