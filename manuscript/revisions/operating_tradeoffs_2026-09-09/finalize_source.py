"""Document source tables and hash the complete delivered extension."""
import csv
import hashlib
import json
from pathlib import Path
import pandas as pd
import pyarrow.parquet as pq
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];S=ROOT/'manuscript/source_data/nature_operating_tradeoffs_v1'
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def main():
    readme='''# v0.23：直接绘图与完整恢复数据

这一目录是新增研究的完整数据，不需要重新下载生产数据、抽样作业或计算统计量后才能绘图。原有其余七张图和旧控制器证据在主绘图包的原始 `03_data/` 与 `03_data/repeat_mechanism/` 中完整保留。

- 直接修改图：使用根目录 CSV 汇总表。每列都是实际绘图值或可明确筛选的条件；`PANEL_DATA_MAP.csv` 给出面板与表格对应。`plot_tradeoffs.py` 只读取这些表。
- 自行重绘时间曲线：`ready_hourly_curves.csv` 已给出每个绝对小时的均值、中位数、5%/95% 情景分位数。随机事件时刻尚未重新对齐，不能把绝对小时曲线误称为事件对齐曲线。
- 修改统计汇总：`development_ledgers.csv`、`confirmation_ledgers.csv`、`temporal_ledgers.csv` 及对应 `*_events.csv` 保留所有成功和失败。`hourly_plot_csv/` 按条件提供可直接导入的逐时绘图列。
- 完整原始模型轨迹：`hourly_full/` 保存所有原始数值字段（仅剔除不可重复的运算耗时），另附配对基线、成本差值和定位字段。共 22,400 次重放、4,838,400 行，均为 216 小时。
- 直接恢复计算：`recovery_inputs/` 中有 3,520 个完整冻结场景、无响应基线及哈希；主包 `04_code/operating_tradeoffs/replay_one.py` 可直接回放任何已交付条件。H4/P24 等事件清单从保存的时刻规则重建并验证原场景哈希，不改变实际工作输入。
- 生产提交依据：`production_submission_times.parquet` 是已处理的 714,903 个 GPU 作业提交记录；`production_hourly_counts.csv` 保存计数。真实时序不等于真实 GPU 小时、业务许可、期限或服务协议。

开发 7,600 次、独立确认 13,200 次、生产时序 1,600 次。两个试运行种子不用于这些统计。开发候选和确认任务已事先冻结，详见 `protocol.json`、`selection.json` 和 `temporal_protocol.json`；其中绝对路径与原代码哈希是历史证据，不是直接绘图的路径依赖。直接重放工具使用包内相对路径。

统计单位：结构确认每条件 300 个独立情景；四次调用不是四个独立样本。真实时序是八个观察周、每周十次合成实现，80 个实现不是 80 个独立观察周。空选择不得解释成零物理容量，未选择对照不得凭确认表现追认为所选报价。

费用：所有金额为条件性 USD 核算，容量价格以每核算报价 kW-year 计。年度净运行成本含电费、等待与期限违约估值，减交付收入。场站固定费另列。净成本分位贡献使用同一总成本排序位置，不能将各项独立分位数相加。无固定费不等于无运行成本；共享费用不等于组合可靠性。契约不履约罚款仍未定价。

`FILE_MANIFEST.csv` 和 `SHA256SUMS.txt` 可验证每个文件。请先复制一份再改数据，以保留当前数值的来源。
'''
    (S/'README.md').write_text(readme)
    guide='''# 字段与判读

`variant=u65d100g10`：工作供给利用率 65%、参考期限余量、灵活 GPU 分配 10%。d50 表示余量减半且至少 1 h。全部新结构情景固定 10% 工作可参与；u 不是实测 GPU 利用率。时序变体包含观察周、chronological/permuted 和 GPU 分配。

`program=H8P16`：8 h 调用，开始间隔 16 h，结束至下次开始的间隙为 8 h。旧表 H8G12 的 G 则直接指间隙。`fraction` 是 5.898243186 kW 参考请求的倍数，不是可延后工作比例。

`kind=fresh`：仅保留相同时刻的最后一次调用；其事件重新编号为 0，`is_target_call=True`。`local_electrical_success` 不包含全局期限和期末积压，但保留逐时/平均交付、反弹和窗口峰值要求。总体 `success_*` 同时包括全局任务服务和无响应基线合格。

`success_zero`：总期限违约可参与工作 ≤1e−7 GPU-h，基线也必须满足，其他标准不变。`success_1pct` 和 `success_01pct` 分别为 1%、0.1%；0.1% 无选值。`qualified` 是该条件单侧 95% Wilson 下界 ≥0.95；`offerable` 另需该终点事先选中。`selected_fraction` 缺失表示开发未选出候选；NaN 不是 0。

`instantaneous_supply_limited_trials`：至少一个活动小时，即使灵活执行归零也不足以满足 95% 交付。它是必要条件诊断；0 次不足不证明全程可行。失败类别非互斥。

能量为 kWh；GPU 工作量为 GPU-h；`delay_exposure_gpu_h_h` 为额外非负队列在时间上的积分（GPU-h×h）。能量与期限违约的增量保留相对无响应基线的符号，等待量则先截为非负再求和。`capped_delivered_energy_kwh` 仅累计事件小时每小时截在 [0,请求] 的交付。

`phase` 决定末次调用开始为 111+phase；输入期 168 h、清空尾段 48 h。`hour` 为整个运行阶段的绝对小时。`controller_audit/` 保留动作建议、所有活动恢复窗口与最终上限，不是生产遥测。

`accounting_offered_kw` = 模型报价 × 1000/本配置运行峰值。`net_operating_annual_q95` 或 `net_operating_cost_annual_q95` 为共同年度抽样净运行成本的第 95 百分位；`*_at_total_q95` 各项加总准确还原它。`payment_per_kw` 为最终非负容量门槛，`unfloored_payment_per_kw` 保留未截断值。

`offerable_success_1pct/zero` 只在对应终点预先选中且通过确认时为真。`required_long_price_vs_short_and_opt_out` 包含不参与的零净值；`required_long_price_if_participating` 只比较两种参与方案。`ready_duration_price_curves.csv` 包含解析转折点与密集价格网格，曲线不依赖稀疏点间假设。

逐时完整字段保持模拟器原名、单位和 NaN 含义；例如未解析恢复时间仍为 NaN，不填零。原字段说明随完整主包 `03_data/COLUMN_DICTIONARY.csv`、`03_data/repeat_mechanism/FIELD_GUIDE.md` 与源代码共同保留。
'''
    (S/'FIELD_GUIDE.md').write_text(guide)
    maps=[('3','a','selected_offers_confirmed.csv','H8P16; g10; six utilisation/deadline settings','selected_capacity_kw; endpoint; confirmation_lower'),
      ('3','b','confirmation_summary.csv','repeated; H8P16; fraction=1; success_1pct; g10','instantaneous_supply_limited_trials; failed_deadline_miss; trials'),
      ('3','c','temporal_week_summary.csv','g10; H8P16; fractions .5 and .75','week; ordering; successes_1pct; successes_zero'),
      ('6','a','cost_components.csv','single; H4; all five cases','net_operating_cost_per_kw_q95; fixed_fee_per_kw'),
      ('6','b','structural_economic_sensitivity.csv','u65d100g10; zero-selected; reference waiting/loss prices','site_fee_annual_usd; payment_per_kw'),
      ('6','c','structural_economic_primary.csv','same zero-selected products; fee=0','payment_per_kw'),
      ('6','d','ready_duration_price_curves.csv','H8P16; fee=0; both endpoints','short_price; required_long_price_vs_short_and_opt_out'),
      ('S3','a','../repeat_mechanism/confirmation_summary.csv','H8G12; fraction=1; old controllers','success_fraction; wilson_lower'),
      ('S3','b','target_call_pairs.csv','H8P16; g10','fresh_target_electrical_successes; repeated_target_electrical_successes'),
      ('S3','c','selected_offers_confirmed.csv','all H8 selections','selected_capacity_kw; confirmation_successes'),
      ('S5','a','structural_economic_sensitivity.csv','u65d100g10; zero-selected; fee=0; missed price=0','waiting_price; payment_per_kw'),
      ('S5','b','structural_economic_sensitivity.csv','u65d100g10; H8P16; fee=0; reference waiting','missed_work_price; payment_per_kw; offerable flags'),
      ('S5','c','structural_entry_examples.csv','reference zero-selected; equal price=250','fee; annual_net_value_lower'),
      ('S5','d','ready_duration_price_curves.csv','H8P16; zero; three fees','short_price; required_long_price_vs_short_and_opt_out')]
    pd.DataFrame(maps,columns=['figure','panel','table','filter','ready_value_columns']).to_csv(S/'PANEL_DATA_MAP.csv',index=False)
    dictionary={}
    for p in sorted(S.glob('*.csv')):
        if p.name in ['COLUMN_DICTIONARY.csv','FILE_MANIFEST.csv']:continue
        for col in pd.read_csv(p,nrows=0).columns:dictionary.setdefault(col,[]).append(p.name)
    inherited={}
    for folder in ['nature_workload_composition_v1','nature_repeat_mechanism_v1']:
        p=S.parent/folder/'COLUMN_DICTIONARY.csv'
        for row in csv.DictReader(p.open()):inherited[row['column']]=row
    rows=[]
    for col,tabs in dictionary.items():
        prior=inherited.get(col,{})
        unit=prior.get('unit') or ('GPU-h × h' if 'exposure' in col else 'GPU-h' if 'gpu_h' in col else 'kWh' if 'kwh' in col else 'kW' if col.endswith('_kw') else 'percentage points' if col.endswith('_pp') else 'USD or USD/kW-year; see field guide' if any(x in col for x in ['price','payment','annual','fee','usd']) else 'named condition/count/proportion; see field guide')
        rows.append(dict(column=col,unit=unit,meaning=prior.get('meaning','Explicitly named condition or statistic; FIELD_GUIDE.md and current Supplementary Methods define denominator, units and selection scope.'),tables=';'.join(tabs)))
    pd.DataFrame(rows).to_csv(S/'COLUMN_DICTIONARY.csv',index=False)
    files=sorted(p for p in S.rglob('*') if p.is_file() and p.name not in ['FILE_MANIFEST.csv','SHA256SUMS.txt'])
    inventory=[dict(path=p.relative_to(S).as_posix(),bytes=p.stat().st_size,sha256=sha(p)) for p in files]
    pd.DataFrame(inventory).to_csv(S/'FILE_MANIFEST.csv',index=False)
    (S/'SHA256SUMS.txt').write_text(''.join(f'{r["sha256"]}  {r["path"]}\n' for r in inventory)+f'{sha(S/"FILE_MANIFEST.csv")}  FILE_MANIFEST.csv\n')
    report=dict(status='PASS',files=len(files),bytes=sum(r['bytes'] for r in inventory),source=str(S),ready_panels=len(maps));(HERE/'source_validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
