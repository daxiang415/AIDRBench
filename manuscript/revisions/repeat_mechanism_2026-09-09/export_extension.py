"""Complete inputs, trajectories, ledgers, event decisions and ready plot curves."""
from concurrent.futures import ProcessPoolExecutor,as_completed
import hashlib
import json
from pathlib import Path
import shutil
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import run_extension as x
from analyse_extension import SOURCE,GROUP

METRICS=['pcc_power_kw','baseline_pcc_power_kw','backlog_gpu_h','executed_gpu_h','arrival_gpu_h','missed_gpu_h',
    'paired_baseline_backlog_gpu_h','paired_baseline_executed_gpu_h','paired_baseline_missed_gpu_h',
    'paired_compute_debt_kwh','excess_backlog_gpu_h','incremental_power_kw','requested_reduction_kw','delivered_reduction_kw','cumulative_missed_gpu_h']


def export_group(item):
    role,key,records=item
    case,program,h,g,ctrl,fraction,k,kind=key
    name=f'{role}_{case}_{program}_{ctrl}_{fraction}_{kind}'.replace('.','p')
    path=SOURCE/'hourly_full'/f'{name}.parquet';path.parent.mkdir(exist_ok=True,parents=True)
    csv=SOURCE/'hourly_plot_csv'/f'{name}.csv';csv.parent.mkdir(exist_ok=True,parents=True)
    audit_path=SOURCE/'controller_audit'/f'{name}.parquet';audit_path.parent.mkdir(exist_ok=True,parents=True)
    writer=None;small=[];audits=[];rows=0
    try:
        for r in sorted(records,key=lambda r:r['seed']):
            assert x.m.sha(r['trace_path'])==r['trace_sha256']
            f=pd.read_parquet(r['trace_path']);base=pd.read_parquet(x.source_artifact(role,case,r['seed'])/'no_response_full.parquet')
            assert f.hour.equals(base.hour)
            for col in ['backlog_gpu_h','executed_gpu_h','missed_gpu_h']:
                f['paired_baseline_'+col]=base[col].to_numpy()
            f['paired_compute_debt_kwh']=f.compute_debt_kwh-base.compute_debt_kwh
            f['excess_backlog_gpu_h']=f.backlog_gpu_h-base.backlog_gpu_h
            f['incremental_power_kw']=f.pcc_power_kw-base.pcc_power_kw
            f['cumulative_missed_gpu_h']=f.missed_gpu_h.cumsum()
            f['case']=case;f['program']=program;f['scenario_seed']=r['seed'];f['method']=ctrl;f['offer_fraction']=fraction
            table=pa.Table.from_pandas(f,preserve_index=False)
            if writer is None:writer=pq.ParquetWriter(path,table.schema,compression='zstd')
            writer.write_table(table);rows+=len(f)
            small.append(f[['scenario_seed','hour','event_active','recovery_active']+METRICS])
            receipt=json.loads(Path(r['receipt_path']).read_text())
            audits.extend(a|dict(scenario_seed=r['seed']) for a in receipt['controller_audit'])
    finally:
        if writer:writer.close()
    d=pd.concat(small,ignore_index=True);d.to_csv(csv,index=False)
    if audits:pd.DataFrame(audits).to_parquet(audit_path,index=False)
    curves=[]
    for hour,part in d.groupby('hour'):
        assert len(part)==len(records)
        for metric in METRICS:
            a=part[metric].to_numpy()
            curves.append(dict(group=name,role=role,case=case,program=program,controller=ctrl,fraction=fraction,
                hour=int(hour),metric=metric,n=len(a),mean=float(np.mean(a)),median=float(np.median(a)),
                p05=float(np.quantile(a,.05)),p95=float(np.quantile(a,.95))))
    return dict(group=name,role=role,case=case,program=program,controller=ctrl,fraction=fraction,trials=len(records),rows=rows,
        full_parquet=path.relative_to(SOURCE).as_posix(),plot_csv=csv.relative_to(SOURCE).as_posix(),
        controller_audit=audit_path.relative_to(SOURCE).as_posix() if audits else None,
        columns=len(table.schema),curves=curves)


def export_inputs():
    target=SOURCE/'recovery_inputs';target.mkdir(parents=True,exist_ok=True);index=[]
    for role,start,stop in [('development',930000,930100),('confirmation',970000,970300)]:
        for case in ['f05','f10','f20','f40','f60']:
            for seed in range(start,stop):
                src=x.source_artifact(role,case,seed);dest=target/role/case/str(seed)
                meta=json.loads((src/'metadata.json').read_text())
                dest.mkdir(parents=True,exist_ok=True)
                for name in ['metadata.json',*meta['files'],'no_response_full.parquet']:
                    shutil.copyfile(src/name,dest/name)
                index.append(dict(role=role,case=case,seed=seed,directory=dest.relative_to(SOURCE).as_posix(),
                    scenario_hash=meta['scenario_hash'],metadata_sha256=x.m.sha(dest/'metadata.json')))
    pd.DataFrame(index).to_csv(SOURCE/'recovery_input_index.csv',index=False)
    return len(index)


def main():
    items=[]
    for role in ['development','confirmation']:
        d=pd.read_csv(SOURCE/f'{role}_ledgers.csv')
        for key,g in d.groupby(GROUP):items.append((role,key,g.to_dict('records')))
    result=[]
    with ProcessPoolExecutor(max_workers=8) as pool:
        for f in as_completed([pool.submit(export_group,item) for item in items]):
            result.append(f.result())
            if len(result)%10==0:print('Export groups',len(result),'/',len(items),flush=True)
    curves=[r for group in result for r in group.pop('curves')]
    pd.DataFrame(curves).to_csv(SOURCE/'ready_hourly_curves.csv',index=False)
    pd.DataFrame(result).sort_values('group').to_csv(SOURCE/'hourly_partition_index.csv',index=False)
    inputs=export_inputs()
    for name in ['protocol.json','selection.json']:
        shutil.copyfile(x.HERE/name,SOURCE/name)
    x.m.save(SOURCE/'export_receipt.json',dict(status='COMPLETE',input_scenarios=inputs,groups=len(result),
        hourly_rows=sum(r['rows'] for r in result),trials=sum(r['trials'] for r in result),
        all_original_hourly_columns_retained=True,all_trials_included=True,ready_curves=len(curves)))
    (SOURCE/'README.md').write_text('''# 重复调用机制扩展的完整数据

现成绘图表为 confirmation_summary.csv、paired_controller_contrasts.csv、selected_offers.csv、economic_primary.csv。直接重绘无需运行模拟或重新做统计。

development/confirmation_ledgers.csv 保存每个完整情景的结果与全时域账本；对应 events.csv 保存每次调用的各项判断。hourly_full/ 是全部原始列与配对基准的完整 Parquet；hourly_plot_csv/ 为可直接打开的完整逐小时绘图列；ready_hourly_curves.csv 已给出逐小时均值、中位数及第 5、95 百分位。百分位描述情景离散性，不是置信区间。

recovery_inputs/ 直接保存全部 2,000 套单情景输入，包含完整作业、期限、社区、基准和配置，不需要下载生产原始数据或重新抽样。protocol.json 与 selection.json 定义事件时刻、实际时长、请求及控制器。运行驱动显式覆盖配置中默认事件时长；每条轨迹再次核对实际时长。

controller_audit/ 保存全部窗口控制器的逐小时上限与是否进一步限功率。illustration_*.csv 为按公开规则选择的开发情景示例，仅用于解释机制，不参与新的确认统计。

开发种子 930000–930099，独立确认种子 970000–970299。每个种子的一整条四调用序列是一个独立统计单位。候选选值只用开发结果，确认失败不被删除。价格是声明参数下的条件性参与门槛，失败方案的价格不表示可以实际报价。
''')
    print('Complete inputs',inputs,'hourly rows',sum(r['rows'] for r in result),flush=True)


if __name__=='__main__':main()
