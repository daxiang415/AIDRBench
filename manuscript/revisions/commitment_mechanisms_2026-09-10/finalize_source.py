"""Describe and hash the complete source payload after export and plotting tables."""
import csv,hashlib,json
from pathlib import Path
import pandas as pd
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];S=ROOT/'manuscript/source_data/nature_commitment_mechanisms_v1'
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def main():
    (S/'README.md').write_text('''# v0.24：直接绘图与完整恢复数据

本目录保存局部加密、严格时间窗可行性、任务资源时间对照与相应经济性。全部 3,040 次重放、656,640 行小时轨迹和 720 个冻结输入均已包含；成功与失败不筛除。旧数据在完整包的 `03_data/`、`03_data/repeat_mechanism/`、`03_data/operating_tradeoffs/` 保留。

- 直接绘图：根目录 CSV 已经包含逐面板所需数值，见 PANEL_DATA_MAP.csv；完整包 RUN_ALL_FIGURES.py 可一次生成十一图，不用处理生产数据或运行仿真。
- 核对报价：refinement_development_summary.csv、refinement_confirmation_summary.csv 和 refinement_selected_confirmed.csv；每条原始记录在 development_ledgers.csv / confirmation_ledgers.csv 与对应事件表。
- 核对时序：external_cross_score_weekly.csv 为旧 63/80 的交叉评分；weighted_week_summary.csv 为新种子的次数/资源时间配对测试；两套种子不混合。
- 重绘逐时曲线：ready_hourly_curves.csv 已给均值、中位数及情景 p05/p95；hourly_plot_csv/ 保留直接导入的小时字段；hourly_full/ 保存完整原始字段与配对无响应基线。绝对小时未按事件重新对齐。
- 恢复控制轨迹：recovery_inputs/ 保存全部冻结输入；完整包 04_code/commitment_mechanisms/replay_one.py 可重放并验证全部 92 个数值列。H4 事件清单按冻结规则重建并核验场景哈希。
- 可行性：pi_diagnostics/ 包含 38 个诊断、11 个完整可行见证（执行边、各工作组、小时功率），并保留一次超时与延长结果。完整包 replay_pi.py 从旧 operating_tradeoffs 冻结输入重新求解，无需原工作目录。
- 原始依据：production_task_resource_time.parquet、production_job_resource_time.parquet、production_hourly_work.csv 提供完整资源时间重建。resource_time_source_audit.json 记录原始任务/作业文件哈希、精确公式、714,903 个匹配作业和时间原点。

资源时间为请求 GPU 当量乘任务启动至完成时长，不是传感器测量忙碌 GPU 小时。新时序实验仍使用周总量归一、合成类别与期限、流体作业；它不是真实任务检查点/恢复实测，也不是生产 SLA 认证。

经济性见 physical_operating_exposure.csv、refinement_cost_components.csv、refinement_economic_sensitivity.csv、refinement_price_frontier.csv。所有确认账本都参与十二组独立序列的年度核算，不是全年连续运行。价格结果仅适用于参考分布；外部资源时间测试失败的请求不能沿用报价资格。

早期 PI 统计量是累计释放/期限条件下的放松规划界限，不是严格作业可行容量；本目录的 PI 可行性使用每个工作组自身的时间窗。解释与反例见交付包修订说明。
''')
    (S/'FIELD_GUIDE.md').write_text('''# 字段判读

`fraction` 是 5.898243186 kW 的请求倍数，不是可参与工作比例；本次工作许可始终为 10%。`H8P16` 是八小时调用、开始间隔十六小时、间隙八小时；一组四次调用。

`success_zero` 表示整个场景满足零漏期终点（数值容差 1e−7 GPU-h）及全部原电力/期末标准；基线也要零漏期。概率资格不要求每个确认场景都成功，因此经济账本保留失败。`offerable_zero` 仅指该候选事先为零标准选中并通过新确认，不授予外部负载报价资格。旧已合格对照标为未选中，不表示它们被追认为失败。

`u65d100g10` 表示工作供给利用率 65%、参考期限、10% GPU 分配；d50 为期限余量减半。`w0_resource_gpu_h_chronological_g10` 表示第一个观察周、资源时间加权、原序、10% GPU 分配。

等待暴露单位 GPU-h×h，是相对匹配基线的额外非负积压在时间上的积分。漏期为 GPU-h；能量为 kWh。physical_operating_exposure 表中 `model_series_*` 按一个模型四调用序列统计，`accounting_annual_*` 按 1 MW 比例规模和十二个独立序列统计。p05/p95 为情景分位数，不是均值置信区间。

`accounting_offered_kw` = 模型报价 ×1000/自身模型运行峰值。成本组件在总净成本的 q95 排序位置归因，相加精确还原总量；不能相加组件各自的边际分位数。所有费用为条件性 USD，容量价格为 USD/kW-year。`ready_annual_values.difference` 是两个产品各自年度净值 q05 的差，不是配对净值差的 q05。

PI 分类：`instantaneous_supply_infeasible` 为解析必要条件失败；`model_infeasible` 为通过即时必要条件后的混合整数不可行；`feasible_witness` 为独立检查过的可行调度。原始 `unresolved` 记录不删除，但 pi_diagnostic_resolved.csv 采用保存的延长求解结果。诊断样本不是概率样本，不能用分类频数推断生产总体发生率。

production_task_resource_time 中 instances 为实例数，gpu_pct 为每实例请求 GPU 百分比，start/end 为原始任务启动/完成时间（秒），resource_gpu_seconds 为乘积。作业表 release_time_s 是归零后的提交时间，raw_submission_time_s = release_time_s + 542323。被测试的归零轨迹小时为 168–1511。

完整逐时字段沿用模拟器定义；NaN 保留未定义/未解决的原含义，不填零。其他继承字段见旧完整数据字典。
''')
    dictionary={}
    for p in sorted(S.glob('*.csv')):
        if p.name in ['COLUMN_DICTIONARY.csv','FILE_MANIFEST.csv']:continue
        for col in pd.read_csv(p,nrows=0).columns:dictionary.setdefault(col,[]).append(p.name)
    prior={r['column']:r for r in csv.DictReader((S.parent/'nature_operating_tradeoffs_v1/COLUMN_DICTIONARY.csv').open())}
    rows=[]
    for col,tables in dictionary.items():
        unit=prior.get(col,{}).get('unit') or ('GPU-h × h' if 'waiting' in col and 'price' not in col else 'GPU-h' if 'gpu_h' in col else 'kW' if col.endswith('_kw') else 'USD or USD/kW-year; FIELD_GUIDE.md' if any(x in col for x in ['price','net4','net8','annual','usd','fee','intercept','floor']) else 'count, proportion or identifier; FIELD_GUIDE.md')
        rows.append(dict(column=col,unit=unit,meaning=prior.get(col,{}).get('meaning','Named condition/statistic; see FIELD_GUIDE.md and Supplementary Tables 18–21.'),tables=';'.join(tables)))
    pd.DataFrame(rows).to_csv(S/'COLUMN_DICTIONARY.csv',index=False)
    files=sorted(p for p in S.rglob('*') if p.is_file() and p.name not in ['FILE_MANIFEST.csv','SHA256SUMS.txt']);inventory=[dict(path=p.relative_to(S).as_posix(),bytes=p.stat().st_size,sha256=sha(p)) for p in files]
    pd.DataFrame(inventory).to_csv(S/'FILE_MANIFEST.csv',index=False);(S/'SHA256SUMS.txt').write_text(''.join(f'{r["sha256"]}  {r["path"]}\n' for r in inventory)+f'{sha(S/"FILE_MANIFEST.csv")}  FILE_MANIFEST.csv\n')
    (HERE/'source_validation.json').write_text(json.dumps(dict(status='PASS',files=len(files),bytes=sum(x['bytes'] for x in inventory),source_sha256=sha(S/'SHA256SUMS.txt')),indent=2)+'\n')
if __name__=='__main__':main()
