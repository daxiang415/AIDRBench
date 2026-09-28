"""Reproduce the complete execution-span composition without winsorising duration."""
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'manuscript/source_data/nature_workload_composition_v1'


def main():
    path = ROOT / 'data/processed/jobs_summary.parquet'
    columns = ['job_type_public', 'priority_class', 'gpu_request', 'duration_hours_raw',
               'requested_work_gpu_h_raw', 'requested_work_gpu_h', 'duration_winsorized']
    groups = []
    for batch in pq.ParquetFile(path).iter_batches(batch_size=1_000_000, columns=columns):
        d = batch.to_pandas()
        assert np.isfinite(d.requested_work_gpu_h_raw).all()
        assert (d.requested_work_gpu_h_raw >= 0).all()
        np.testing.assert_allclose(d.requested_work_gpu_h_raw,
                                   d.gpu_request*d.duration_hours_raw, rtol=1e-12, atol=1e-9)
        groups.append(d.groupby(['job_type_public','priority_class'], dropna=False).agg(
            records=('requested_work_gpu_h_raw','size'), gpu_h_raw=('requested_work_gpu_h_raw','sum'),
            gpu_h_winsorized=('requested_work_gpu_h','sum'), winsorized_records=('duration_winsorized','sum')))
    s = pd.concat(groups).groupby(level=[0,1]).sum()
    s['raw_gpu_h_share'] = s.gpu_h_raw / s.gpu_h_raw.sum()
    s['record_share'] = s.records / s.records.sum()
    OUT.mkdir(parents=True, exist_ok=True)
    s.reset_index().to_csv(OUT/'source_mix_by_class_priority.csv', index=False)
    byclass=s.groupby(level=0).sum()
    byclass.to_csv(OUT/'source_mix_by_class.csv')
    total=float(s.gpu_h_raw.sum())
    batch_classes=['training','offline_inference']
    record=dict(rows=int(s.records.sum()), requested_gpu_hours=total,
        source_sha256=hashlib.file_digest(path.open('rb'),'sha256').hexdigest(),
        shares=byclass.raw_gpu_h_share.to_dict(),
        lp_batch_shares={c:float(s.loc[(c,'lp'),'raw_gpu_h_share']) for c in batch_classes},
        lp_batch_total_share=float(sum(s.loc[(c,'lp'),'raw_gpu_h_share'] for c in batch_classes)),
        denominator='sum of requested GPU-equivalents times uncapped execution-span hours; not energy, useful work, or DR eligibility',
        source_scope='released execution-summary spans; not an industry sample or a replay of pod-hourly telemetry')
    (OUT/'source_audit.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps(record,indent=2))


if __name__=='__main__': main()
