"""Preserve every raw field and provide ready-to-plot structural study tables."""
from concurrent.futures import ProcessPoolExecutor, as_completed
import json
from pathlib import Path
import shutil
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import run_tradeoffs as r

SOURCE=r.ROOT/'manuscript/source_data/nature_operating_tradeoffs_v1'
METRICS=['pcc_power_kw','baseline_pcc_power_kw','backlog_gpu_h','executed_gpu_h','arrival_gpu_h','missed_gpu_h',
    'paired_baseline_backlog_gpu_h','paired_baseline_executed_gpu_h','paired_baseline_missed_gpu_h',
    'excess_backlog_gpu_h','incremental_power_kw','cumulative_missed_gpu_h','requested_reduction_kw','delivered_reduction_kw']


def collect(role):
    rows=[];events=[]
    for path in sorted((r.OUT/'runs'/role).glob('*/*/*.json')):
        obj=json.loads(path.read_text());row=obj['row']|dict(trace_path=obj['trace_path'],trace_sha256=obj['trace_sha256'],
            scenario_path=obj['scenario_path'],scenario_hash=obj['scenario_hash'],receipt_path=str(path))
        rows.append(row)
        for e in obj['events']:
            local=set(e['failures'])-{'deadline_miss','terminal_backlog'}
            events.append({k:row[k] for k in ['role','variant','seed','program','kind','fraction','capacity_kw']}|
                {k:v for k,v in e.items() if k!='failures'}|dict(failures=','.join(e['failures']),local_electrical_success=not local,
                    is_target_call=(row['kind']=='fresh' or e['event_id']==3)))
    return pd.DataFrame(rows),pd.DataFrame(events)


def export_group(payload):
    key,records=payload
    role,variant,program,kind,fraction=key
    tag=f'{role}_{variant}_{program}_{kind}_f{fraction}'.replace('.','p')
    dest=SOURCE/'hourly_full'/f'{tag}.parquet';dest.parent.mkdir(exist_ok=True,parents=True)
    plot=SOURCE/'hourly_plot_csv'/f'{tag}.csv';plot.parent.mkdir(exist_ok=True,parents=True)
    audit=SOURCE/'controller_audit'/f'{tag}.parquet';audit.parent.mkdir(exist_ok=True,parents=True)
    small=[];audits=[];writer=None;rows=0
    try:
        for record in sorted(records,key=lambda x:x['seed']):
            assert r.m.sha(record['trace_path'])==record['trace_sha256']
            frame=pd.read_parquet(record['trace_path'])
            base=pd.read_parquet(r.scenario(role,variant,record['seed'])/'no_response_full.parquet')
            assert frame.hour.equals(base.hour) and len(frame)==216
            for col in ['backlog_gpu_h','executed_gpu_h','missed_gpu_h']:frame['paired_baseline_'+col]=base[col].to_numpy()
            frame['excess_backlog_gpu_h']=frame.backlog_gpu_h-base.backlog_gpu_h
            frame['incremental_power_kw']=frame.pcc_power_kw-base.pcc_power_kw
            frame['cumulative_missed_gpu_h']=frame.missed_gpu_h.cumsum()
            frame['scenario_seed']=record['seed'];frame['variant']=variant;frame['program']=program;frame['offer_fraction']=fraction;frame['study_role']=role
            table=pa.Table.from_pandas(frame,preserve_index=False)
            if writer is None:writer=pq.ParquetWriter(dest,table.schema,compression='zstd')
            writer.write_table(table);rows+=len(frame)
            small.append(frame[['scenario_seed','hour','event_active','recovery_active']+METRICS])
            obj=json.loads(Path(record['receipt_path']).read_text())
            audits.extend(a|dict(scenario_seed=record['seed']) for a in obj['controller_audit'])
    finally:
        if writer:writer.close()
    data=pd.concat(small,ignore_index=True);data.to_csv(plot,index=False)
    pd.DataFrame(audits).to_parquet(audit,index=False)
    curves=[]
    for hour,part in data.groupby('hour'):
        for metric in METRICS:
            a=part[metric].to_numpy();assert np.isfinite(a).all()
            curves.append(dict(role=role,variant=variant,program=program,kind=kind,fraction=fraction,hour=int(hour),metric=metric,
                n=len(a),mean=float(a.mean()),median=float(np.median(a)),p05=float(np.quantile(a,.05)),p95=float(np.quantile(a,.95))))
    return dict(group=tag,role=role,variant=variant,program=program,kind=kind,fraction=fraction,trials=len(records),rows=rows,
        full_parquet=dest.relative_to(SOURCE).as_posix(),plot_csv=plot.relative_to(SOURCE).as_posix(),controller_audit=audit.relative_to(SOURCE).as_posix(),curves=curves)


def inputs(data):
    rows=[]
    for (role,variant,seed),g in data.groupby(['role','variant','seed']):
        src=r.scenario(role,variant,int(seed));dest=SOURCE/'recovery_inputs'/role/variant/str(seed);dest.mkdir(parents=True,exist_ok=True)
        meta=json.loads((src/'metadata.json').read_text())
        for name in ['metadata.json',*meta['files'],'baseline_receipt.json','no_response_full.parquet']:shutil.copyfile(src/name,dest/name)
        rows.append(dict(role=role,variant=variant,seed=int(seed),directory=dest.relative_to(SOURCE).as_posix(),
            scenario_hash=meta['scenario_hash'],metadata_sha256=r.m.sha(dest/'metadata.json')))
    pd.DataFrame(rows).to_csv(SOURCE/'recovery_input_index.csv',index=False)
    return len(rows)


def main():
    frames=[];event_frames=[];items=[]
    for role in ['development','confirmation','temporal']:
        d,e=collect(role);assert len(d)>0
        d.to_csv(SOURCE/f'{role}_ledgers.csv',index=False);e.to_csv(SOURCE/f'{role}_events.csv',index=False)
        frames.append(d);event_frames.append(e)
        items += [(key,g.to_dict('records')) for key,g in d.groupby(['role','variant','program','kind','fraction'])]
    parts=[]
    with ProcessPoolExecutor(max_workers=8) as pool:
        for future in as_completed([pool.submit(export_group,item) for item in items]):
            parts.append(future.result())
            if len(parts)%10==0 or len(parts)==len(items):print('Exported groups',len(parts),'/',len(items),flush=True)
    curves=[row for part in parts for row in part.pop('curves')]
    pd.DataFrame(parts).sort_values('group').to_csv(SOURCE/'hourly_partition_index.csv',index=False)
    pd.DataFrame(curves).to_csv(SOURCE/'ready_hourly_curves.csv',index=False)
    count=inputs(pd.concat(frames,ignore_index=True))
    for name in ['protocol.json','selection.json','temporal_protocol.json']:shutil.copyfile(r.HERE/name,SOURCE/name)
    source_counts=r.ROOT/'results/nature_mainline/repeat_capacity_v1/production_timing/hourly_counts.csv'
    shutil.copyfile(source_counts,SOURCE/'production_hourly_counts.csv')
    report=dict(status='COMPLETE',input_scenarios=count,trials=sum(x['trials'] for x in parts),hourly_rows=sum(x['rows'] for x in parts),groups=len(parts),
        all_original_hourly_columns_preserved=True,ready_curves=len(curves),all_confirmed_and_failed_runs_included=True)
    r.m.save(SOURCE/'export_receipt.json',report);print(json.dumps(report,indent=2),flush=True)


if __name__=='__main__':main()
