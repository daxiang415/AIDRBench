"""Deliver all trial outcomes, full hourly Parquet and ready-to-plot CSV curves."""
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor,as_completed
import collections
import hashlib
import json
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import run_study_final as m

SOURCE=m.SOURCE
METRICS=['pcc_power_kw','dc_power_kw','arrival_gpu_h','executed_gpu_h','backlog_gpu_h','missed_gpu_h',
    'delivered_reduction_kw','requested_reduction_kw','compute_debt_kwh',
    'paired_no_response_pcc_power_kw','paired_no_response_dc_power_kw','paired_no_response_executed_gpu_h',
    'paired_no_response_backlog_gpu_h','paired_no_response_missed_gpu_h','paired_no_response_compute_debt_kwh',
    'excess_backlog_gpu_h','excess_queue_energy_kwh','incremental_power_kw']


def export_group(item):
    key,records=item;stage,case,program,tag,h,notice=key
    name=f'{stage}_{case}_{program}_{tag}_H{h}_N{notice}'.replace('.','p')
    full=SOURCE/'hourly_full'/f'{name}.parquet';csv=SOURCE/'hourly_plot_csv'/f'{name}.csv'
    full.parent.mkdir(parents=True,exist_ok=True);csv.parent.mkdir(parents=True,exist_ok=True)
    writer=None;small=[];rows=0
    try:
        for r in sorted(records,key=lambda r:r['task']['seed']):
            t=r['task'];frame=pd.read_parquet(r['trace_path'])
            assert m.sha(r['trace_path'])==r['trace_sha256']
            baseline=pd.read_parquet(m.artifact_path(t['role'],case,t['seed'])/'no_response_full.parquet')
            assert frame.hour.equals(baseline.hour)
            for c in ['pcc_power_kw','dc_power_kw','executed_gpu_h','backlog_gpu_h','missed_gpu_h','compute_debt_kwh']:
                frame['paired_no_response_'+c]=baseline[c].to_numpy()
            frame['case']=case;frame['scenario_seed']=t['seed'];frame['program']=program;frame['request_tag']=tag
            frame['duration_h']=h;frame['notice_h']=notice
            frame['event_relative_hour']=frame.hour-int(r['events'][0]['start_hour'])
            frame['excess_backlog_gpu_h']=frame.backlog_gpu_h-baseline.backlog_gpu_h
            frame['excess_queue_energy_kwh']=frame.compute_debt_kwh-baseline.compute_debt_kwh
            frame['incremental_power_kw']=frame.pcc_power_kw-baseline.pcc_power_kw
            table=pa.Table.from_pandas(frame,preserve_index=False)
            if writer is None:writer=pq.ParquetWriter(full,table.schema,compression='zstd')
            writer.write_table(table);rows+=len(frame)
            cols=['case','scenario_seed','program','request_tag','duration_h','notice_h','hour',
                'event_relative_hour','event_active','recovery_active']+METRICS
            cols=[c for c in cols if c in frame]
            small.append(frame[cols])
    finally:
        if writer is not None:writer.close()
    d=pd.concat(small,ignore_index=True);d.to_csv(csv,index=False)
    metrics=[c for c in METRICS if c in d]
    last_hour=152 if program!='single' and not tag.startswith('fresh') else 48
    aligned=d[d.event_relative_hour.between(-12,last_hour)]
    curves=[]
    for hour,g in aligned.groupby('event_relative_hour'):
        assert len(g)==len(records), (key,hour,len(g),len(records))
        for col in metrics:
            curves.append(dict(group=name,case=case,program=program,tag=tag,duration_h=h,notice_h=notice,
                event_relative_hour=int(hour),scenarios=len(g),metric=col,mean=float(g[col].mean()),
                p05=float(g[col].quantile(.05)),median=float(g[col].median()),p95=float(g[col].quantile(.95))))
    return dict(group=name,rows=rows,scenarios=len(records),full_parquet=str(full.relative_to(SOURCE)),
        plot_csv=str(csv.relative_to(SOURCE)),full_column_count=len(table.schema),plot_column_count=len(d.columns),curves=curves)


def main():
    outcomes=[];groups=collections.defaultdict(list);counts={}
    for stage in ['single_dev','single_confirm','repeat_dev','repeat_confirm','control_confirm']:
        folder=m.OUT/'repeat_duration_corrected_v2' if stage.startswith('repeat') else m.OUT
        records=json.loads((folder/f'{stage}_receipts.json').read_text());counts[stage]=len(records)
        for r in records:
            t=r['task']
            for e in r['events']:
                row={'stage':stage}|{k:v for k,v in t.items() if k!='event_ids'}|e
                row['failures']=';'.join(row['failures']);outcomes.append(row)
            key=(stage,t['case'],t.get('program','single'),t['tag'],t['duration_h'],t.get('notice_h',0))
            groups[key].append(r)
    pd.DataFrame(outcomes).to_csv(SOURCE/'all_trial_event_outcomes.csv',index=False)
    outputs=[]
    with ProcessPoolExecutor(max_workers=8) as pool:
        futures=[pool.submit(export_group,x) for x in groups.items()]
        for f in as_completed(futures):
            outputs.append(f.result());print(f'hourly export {len(outputs)}/{len(groups)}',flush=True)
    curves=[row for o in outputs for row in o.pop('curves')]
    pd.DataFrame(curves).to_csv(SOURCE/'ready_hourly_curves.csv',index=False)
    pd.DataFrame(outputs).sort_values('group').to_csv(SOURCE/'hourly_partition_index.csv',index=False)
    receipt=dict(status='complete',trial_counts=counts,formal_replays=sum(counts.values()),
        full_hourly_rows=sum(x['rows'] for x in outputs),hourly_groups=len(outputs),event_outcome_rows=len(outcomes),
        statistical_unit='scenario_seed; all calls within a programme remain dependent',
        completeness='all development and confirmation trial event outcomes and hourly trajectories, with all original columns plus paired baseline metrics; complete drawing summaries',
        preserved_local_simulation_results=str(m.OUT),
        old_75_percent_outputs='unchanged historical results; not input to new curves')
    (SOURCE/'export_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt,indent=2))


if __name__=='__main__':main()
