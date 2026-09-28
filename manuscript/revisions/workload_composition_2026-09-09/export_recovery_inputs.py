"""Preserve complete paired input information without duplicating every job table."""
from pathlib import Path
import json
import shutil
import pandas as pd
import run_study_final as m

def main():
    target=m.SOURCE/'recovery_inputs';target.mkdir(parents=True,exist_ok=True)
    templates=[]
    for source in sorted((m.OUT/'templates').glob('*/*')):
        if not source.is_dir():continue
        relative=Path('templates')/source.parent.name/source.name
        dest=target/relative;dest.mkdir(parents=True,exist_ok=True)
        meta=json.loads((source/'metadata.json').read_text())
        for name in ['metadata.json',*meta['files']]:shutil.copyfile(source/name,dest/name)
        templates.append(dict(role=source.parent.name,seed=int(source.name.split('_')[-1]),template_directory=relative.as_posix(),template_scenario_hash=meta['scenario_hash']))
    assert len(templates)==400
    base=pd.read_parquet(m.OUT/'scenario_index.parquet');controls=pd.read_csv(m.SOURCE/'control_scenario_index.csv')
    controls['role']='confirmation';index=pd.concat([base,controls],ignore_index=True);records=[]
    for r in index.itertuples():
        source=m.artifact_path(r.role,r.case,r.seed)
        dest=target/'scenario_manifests'/r.role/r.case/f'{r.seed}.json';dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source/'metadata.json',dest)
        auxiliary=target/'scenario_files'/r.role/r.case/str(r.seed);auxiliary.mkdir(parents=True,exist_ok=True)
        for name in ['environment_config.yaml','baseline.parquet']:
            shutil.copyfile(source/name,auxiliary/name)
        f=float(r.case[1:3])/100
        c=m.case_definition(f);ref=m.case_definition(.6)
        record=dict(role=r.role,case=r.case,seed=r.seed,template_directory=f'templates/{r.role}/hourly_seed_{r.seed}',
            training_work_multiplier=c['eligible_shares']['training']/ref['eligible_shares']['training'],
            offline_work_multiplier=c['eligible_shares']['offline_inference']/ref['eligible_shares']['offline_inference'],
            original_scenario_hash=r.scenario_hash,manifest=dest.relative_to(target).as_posix(),
            scenario_files=auxiliary.relative_to(target).as_posix())
        # Work multipliers are identical for the allocation/power controls.
        records.append(record)
    pd.DataFrame(records).to_csv(target/'reconstruction_index.csv',index=False)
    pd.DataFrame(templates).to_csv(target/'template_index.csv',index=False)
    (target/'README.md').write_text('''# 完整输入的去重保存

这些文件用于核查作业释放/截止时间及恢复模拟；日常绘图直接使用外层 CSV，不需要先处理这里的文件。

400 份共同模板保存全部原始作业记录、释放与截止时间、社区小时曲线、基准表和配置。各配置仅按类别缩放模板工作量；`reconstruction_index.csv` 列出完整精度的两个乘数。分配/刚性功率对照保留相同作业。3,200 份原情景元数据完整保存在 `scenario_manifests/`；各自完整配置与规划基准保存在 `scenario_files/`。此去重布局避免重复保存同一作业形状九次；它没有删除作业记录。

控制器各次运行的实际小时结果和统计结果在外层全部保留。重复调用的实际时长由 `run_repeated_duration_v2.py` 明确设置并逐次验证；冻结基础配置的默认一小时时长不能替代运行任务的四/八小时时长。原配置内路径是原执行环境路径，保留用于来源审计；绘图脚本使用相对路径，不依赖这些绝对路径。`restore_scenario.py` 可用模板与乘数恢复指定情景，并逐文件核对原始 SHA-256；绘图不需要这一步。批量模拟需在随附 AIDRBench 源码环境中运行对应驱动，单情景恢复无需重新抽样生产数据。
''')
    (m.SOURCE/'recovery_inputs_receipt.json').write_text(json.dumps(dict(status='complete',templates=len(templates),scenario_manifests=len(records),all_job_records_retained=True,layout='shared complete templates plus exact class multipliers; direct plotting tables require no reconstruction'),indent=2)+'\n')
    print('Recovery inputs:',len(templates),'complete templates;',len(records),'scenario manifests')

if __name__=='__main__':main()
