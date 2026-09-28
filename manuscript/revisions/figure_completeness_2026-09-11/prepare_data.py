"""Extract existing evidence into direct plot tables; no simulation or reselection."""
import hashlib
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / 'manuscript/source_data'
OUT = SOURCE / 'nature_figure_completeness_v1'


def main():
    OUT.mkdir(exist_ok=True)
    sources = {}

    def read(folder, name):
        p = SOURCE / folder / name
        sources[f'{folder}/{name}'] = hashlib.sha256(p.read_bytes()).hexdigest()
        return pd.read_parquet(p) if p.suffix == '.parquet' else pd.read_csv(p)

    def save(d, name):
        d.to_csv(OUT / name, index=False, float_format='%.15g')

    traces = []
    folder = 'nature_commitment_mechanisms_v1'
    index = read(folder, 'hourly_partition_index.csv')
    ledger = read(folder, 'confirmation_ledgers.csv')
    for program, fraction in [('H4P16', .95), ('H8P16', .75)]:
        row = index[(index.role == 'confirmation') & (index.program == program) & (index.fraction == fraction)]
        assert len(row) == 1
        d = read(folder, row.full_parquet.iloc[0])
        seed = int(d.scenario_seed.min())
        assert seed == 989000
        d = d[d.scenario_seed == seed].sort_values('hour')
        assert len(d) == 216 and list(d.hour) == list(range(216))
        keep = ['hour','scenario_seed','program','offer_fraction','event_active','event_id',
                'requested_reduction_kw','delivered_reduction_kw','pcc_power_kw','baseline_pcc_power_kw',
                'incremental_power_kw','backlog_gpu_h','paired_baseline_backlog_gpu_h',
                'excess_backlog_gpu_h','cumulative_missed_gpu_h','is_clearance_tail']
        traces.append(d[keep])
    save(pd.concat(traces), 'reference_operation_example.csv')
    selected = ledger[(ledger.seed == 989000) & (((ledger.program == 'H4P16') & (ledger.fraction == .95)) | ((ledger.program == 'H8P16') & (ledger.fraction == .75)))]
    save(selected, 'reference_operation_example_outcomes.csv')
    d = read('nature_operating_tradeoffs_v1', 'confirmation_summary.csv')
    d = d[(d.fraction == 1) & d.endpoint.isin(['success_1pct','success_zero']) & (d.program.isin(['H8P16','H8P24'])) & ((d.kind == 'repeated') | (d.program == 'H8P16'))]
    assert len(d) == 48 and (d.trials == 300).all() and (d.baseline_failures == 0).all()
    save(d, 'structural_full_request.csv')
    pv = read('nature_workload_composition_v1', 'renewable_scenarios.csv')
    assert len(pv) == 4000 and (pv.status == 'optimal').all()
    save(pv, 'pv_all_scenarios.csv')
    rows = []
    for keys, g in pv.groupby(['analysis','case','bess_enabled','dc_operation']):
        assert len(g) == 100
        for metric in ['pv_rated_kw','total_pv_curtailed_kwh','total_grid_import_kwh']:
            rows.append(dict(zip(['analysis','case','bess_enabled','dc_operation'],keys),metric=metric,n=100,
                             minimum=g[metric].min(),mean=g[metric].mean(),p05=g[metric].quantile(.05),p95=g[metric].quantile(.95)))
    save(pd.DataFrame(rows), 'pv_operating_summary.csv')
    for name in ['reserve_life_sensitivity.csv','economic_price_sensitivity.csv','economic_primary.csv']:
        d = read('nature_workload_composition_v1', name)
        save(d[(d.kind == 'single') & (d.case == 'f10')], name)
    # Small input tables are copied byte-for-byte, including the relocated decision text.
    for folder, name in [('nature_workload_composition_v1','source_audit.json'),('nature_workload_composition_v1','case_definitions.json'),
                         ('nature_commitment_narrative_v1','decision_steps.csv'),('nature_commitment_narrative_v1','paired_resource_supply_margins.csv'),
                         ('nature_commitment_narrative_v1','supply_hourly_example.csv')]:
        p = SOURCE / folder / name
        sources[f'{folder}/{name}'] = hashlib.sha256(p.read_bytes()).hexdigest()
        (OUT / name).write_bytes(p.read_bytes())
    (OUT / 'derivation_receipt.json').write_text(json.dumps(dict(
        version='0.26', simulation_rerun=False, offer_reselected=False,
        example_selection='lowest common frozen confirmation seed 989000, irrespective of outcome',
        pv_summary='100 paired scenarios per cell; minimum or arithmetic mean; quantiles descriptive',
        sources=sources), indent=2)+'\n')
    print(f'Wrote {len(list(OUT.iterdir()))} direct-input files to {OUT}')


if __name__ == '__main__':
    main()
