"""Retain old recovery archive and add an exact new-experiment repository overlay."""
import json,shutil,os
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
DEST=ROOT/'results/exports/AIDRBench_Submission_v0.27_2026-09-11'
def copy(src,dst):
    dst.parent.mkdir(parents=True,exist_ok=True)
    if src.is_dir():shutil.copytree(src,dst,dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__','*.pyc','before','.pytest_cache'))
    else:shutil.copy2(src,dst)
def main():
    full=DEST/'05_Full_Data';full.mkdir(exist_ok=True);old=ROOT/'results/exports/AIDRBench_Submission_v0.26_2026-09-11/05_Full_Data'
    archive=old/'AIDRBench_All_Figures_2026-09-10_v14.zip';new=full/archive.name
    if not new.exists():os.link(archive,new)
    copy(old/'historical_v4_with_v08_sources',full/'historical_v4_with_v08_sources')
    overlay=full/'new_v027_repository_overlay';overlay.mkdir(exist_ok=True)
    for rel in ['src','configs','pyproject.toml','README.md','data/calibration','data/processed/community_load.parquet','data/processed/jobs_summary_sampler.parquet','results/nature_mainline/workload_composition_v4/single_selected.csv','manuscript/source_data/nature_commitment_validation_v1','results/nature_mainline/commitment_validation_v1']:
        copy(ROOT/rel,overlay/rel)
    for name in ['commitment_validation_2026-09-11','workload_composition_2026-09-09','repeat_mechanism_2026-09-09','operating_tradeoffs_2026-09-09','commitment_mechanisms_2026-09-10']:
        copy(ROOT/'manuscript/revisions'/name,overlay/'manuscript/revisions'/name)
    for name in ['nature_workload_composition_v1','nature_commitment_mechanisms_v1']:
        folder=ROOT/'manuscript/source_data'/name
        for f in folder.iterdir():
            if f.suffix in ['.json','.csv'] and f.stat().st_size<15_000_000:copy(f,overlay/'manuscript/source_data'/name/f.name)
    for case in ['f10','f10_g20']:
        for seed in range(960000,960100):
            rel=f'results/nature_mainline/workload_composition_v4/confirmation/{case}/scenarios/single/hourly_seed_{seed}';copy(ROOT/rel,overlay/rel)
    copy(HERE/'replay_one.py',overlay/'REPLAY_ONE.py')
    (overlay/'REPLAY_README_ZH.md').write_text('''# 新增科学证据的恢复

此目录保留 v0.27 的完整 2,700 条重放、800 个冻结输入基线、PV 输入及 1,000 份求解记录，连同原样代码和运行依赖。直接绘图请使用交付包 04_Redraw_Ready；无需进入这里或处理原始轨迹。

在 Python 3.12 环境安装 `python -m pip install -e ".[control,analysis]"` 后，可运行 `python REPLAY_ONE.py --output /tmp/aidrbench-replay`。它把一个冻结确认情景复制到新输出目录，实际重放并核对服务、供给、等待和能耗数值，不修改原收据。可用 --weight、--seed、--fraction、--role 选择账本中存在的其他情景。

原收据保留生成时的绝对路径以维护原始哈希；请用恢复脚本创建新输出，避免直接批量修改冻结 JSON。8 周权重、开发/确认选择与完整逐时 parquet 均可直接读取。原先所有图和全量证据还保存在旁边的 v14 恢复 ZIP；更早 v0.8 图源位于 historical_v4_with_v08_sources。
''')
    (full/'README_ZH.md').write_text('# 完整证据\n\n- AIDRBench_All_Figures_2026-09-10_v14.zip：原完整数据与恢复代码，原样保留。\n- historical_v4_with_v08_sources：旧 v0.8 图源，仅历史用途。\n- new_v027_repository_overlay：本次新输入、全时序、PV 求解记录及代码；含可执行的单情景重放检查。\n\n当前全部图的免预处理数据和代码统一在交付包 04_Redraw_Ready。\n')
    print(overlay,flush=True)
if __name__=='__main__':main()
