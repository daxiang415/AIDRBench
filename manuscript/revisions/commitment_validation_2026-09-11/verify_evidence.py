"""Independent arithmetic, partition and artifact audit for the v0.27 additions."""
import hashlib,json,math,re
from pathlib import Path
from statistics import NormalDist
import numpy as np
import pandas as pd
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];SOURCE=ROOT/'manuscript/source_data/nature_commitment_validation_v1';OUT=ROOT/'results/nature_mainline/commitment_validation_v1'
def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def lower(s,n):
    z=NormalDist().inv_cdf(.95);p=s/n
    return (p+z*z/(2*n)-z*math.sqrt(p*(1-p)/n+z*z/(4*n*n)))/(1+z*z/n)
def main():
    p=json.loads((HERE/'capacity_protocol.json').read_text());selection=json.loads((HERE/'capacity_selection.json').read_text())
    assert p['runner_sha256']==sha(HERE/'capacity_validation.py')
    assert selection['protocol_sha256']==sha(HERE/'capacity_protocol.json') and selection['development_sha256']==sha(OUT/'development_ledgers.csv')
    assert p['frozen_at_utc']<selection['frozen_at_utc']
    assert p['source_weights_sha256']==sha(ROOT/'manuscript/source_data/nature_commitment_mechanisms_v1/production_hourly_work.csv')
    dev=pd.read_csv(OUT/'development_ledgers.csv');conf=pd.read_csv(OUT/'confirmation_ledgers.csv')
    assert len(dev)==1800 and len(conf)==900 and set(dev.seed).isdisjoint(conf.seed)
    assert set(dev.seed)==set(range(1010000,1010100)) and set(conf.seed)==set(range(1011000,1011300))
    for role,data in [('development',dev),('confirmation',conf)]:
        assert data.baseline_service_feasible.all() and data.baseline_zero_service.all()
        for row in data.itertuples():
            assert sha(row.trace_path)==row.trace_sha256
            frame=pd.read_parquet(row.trace_path);assert len(frame)==216 and abs(frame.arrival_gpu_h.sum()-6289.92)<1e-6
            assert row.week==int(np.random.default_rng(row.seed+2000000).integers(0,8))
        receipts=json.loads((OUT/f'{role}_baseline_receipts.json').read_text())
        for pair in receipts:
            assert len(pair)==2 and pair[0]['seed']==pair[1]['seed'] and pair[0]['week']==pair[1]['week']
            assert abs(pair[0]['total_arrival_gpu_h']-pair[1]['total_arrival_gpu_h'])<1e-8
            arrivals=[];communities=[]
            for x in pair:
                d=Path(x['source']);arrivals.append(pd.read_parquet(d/'arrivals.parquet').groupby('job_class').arrival_gpu_h.sum());communities.append(sha(d/'community.parquet'))
            assert np.allclose(arrivals[0],arrivals[1],atol=1e-7,rtol=0) and communities[0]==communities[1]
    for role,data in [('development',dev),('confirmation',conf)]:
        s=pd.read_csv(SOURCE/f'capacity_{role}_summary.csv')
        for x in s.itertuples():
            g=data[(data.variant==x.weight)&np.isclose(data.fraction,x.fraction)];assert len(g)==x.trials and int(g[x.endpoint].sum())==x.successes
            assert abs(lower(x.successes,x.trials)-x.wilson_lower)<1e-12
    s=pd.read_csv(SOURCE/'capacity_selected_confirmed.csv');assert s.offerable.all() and (s.confirmation_successes==300).all()
    capacities=s.groupby('weight').selected_capacity_kw.first();assert abs(capacities['job_count']/capacities['resource_gpu_h']-2)<1e-12
    old=pd.read_csv(ROOT/'manuscript/source_data/nature_commitment_mechanisms_v1/weighted_week_summary.csv');w=old[(old.weight=='resource_gpu_h')&(old.ordering=='chronological')&(old.fraction==.5)]
    assert w.successes_zero.tolist()==[1,6,1,0,3,0,10,10] and w.successes_zero.sum()==31
    power=json.loads((SOURCE/'power_reconciliation.json').read_text());assert abs(sum(power['facility_components'].values())-power['implemented_operating_peak_kw'])<1e-10
    ov=json.loads((SOURCE/'fixed_overhead_audit.json').read_text());assert ov['all_success_flags_preserved'] and ov['minimum_pcc_margin_kw']>219
    pv=pd.read_csv(SOURCE/'pv_primary_bounds.csv');assert len(pv)==1000 and (pv.reported_upper>=pv.reported_lower-1e-10).all()
    assert pv.query("analysis=='fixed_pv_operation'").resolved.all() and (~pv.resolved).sum()==34
    pe=pd.read_csv(SOURCE/'pv_precision_summary.csv');assert pe.query("case=='f10' and not bess_enabled and analysis=='fixed_pv_operation'").max_abs_change_from_previous_pp.iloc[0]<1e-12
    for stem,name in [('main','nature_communications_article.md'),('supplement','supplementary_information.md')]:
        d=json.loads((ROOT/f'docs/chinese_reader/v21/{stem}_aligned_blocks.json').read_text());assert d['source_sha256']==sha(ROOT/'manuscript'/name)
        assert len(d['blocks'])==len({b['id'] for b in d['blocks']})
        assert '\n\n'.join(b['en'] for b in d['blocks']) in (ROOT/'manuscript'/name).read_text()
    report=dict(status='PASS',complete_trace_hashes_checked=2700,paired_scenario_inputs_checked=800,weekly_class_totals_and_community_pairing=True,independent_Wilson_recomputation=True,finite_grid_selected_capacity_ratio=2.,observed_weeks=8,original_week_successes=w.successes_zero.tolist(),overhead_same_success_flags=True,PV_primary_bounds=1000,PV_unresolved_nonlimiting_hosting=34,Chinese_English_alignment=True)
    (HERE/'evidence_verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
