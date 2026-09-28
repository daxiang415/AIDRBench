"""Audit new prices and write final decision rationale, source guides and entry points."""
import hashlib
import json
from pathlib import Path
import re
import numpy as np
import pandas as pd
import pyarrow.parquet as pq

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
DATA=ROOT/'manuscript/source_data/nature_repeat_mechanism_v1'


def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def main():
    # Independently implement the cost equation, without the analysis helper.
    ledgers=pd.read_csv(DATA/'confirmation_ledgers.csv');costs=pd.read_csv(DATA/'economic_sensitivity.csv')
    cache={};checked=0
    for r in costs.itertuples():
        key=(r.case,r.program,r.controller,r.fraction)
        if key not in cache:
            g=ledgers[(ledgers.case==r.case)&(ledgers.program==r.program)&(ledgers.controller==r.controller)&(ledgers.fraction==r.fraction)].sort_values('seed')
            assert len(g)==300;cache[key]=g
        g=cache[key];ix=np.random.default_rng(20260910).integers(0,300,size=(2000,12))
        net=.1*g.incremental_energy_kwh.to_numpy()+r.waiting_price*g.delay_exposure_gpu_h_h.to_numpy()-.05*g.capped_delivered_energy_kwh.to_numpy()+r.displaced_value*g.deferred_work_gpu_h.to_numpy()
        yearly=net[ix].sum(axis=1)*r.scale+r.site_cost
        expected=max(0,float(np.quantile(yearly,.95)/(r.scale*r.capacity_kw)))
        if r.regime=='reserved_headroom':
            growth=1.08**4;expected+=375*(1-.1/growth)*(.08*growth/(growth-1))+375*.03
        assert np.isclose(expected,r.payment_usd_kw_year,rtol=0,atol=1e-8)
        checked+=1
    (HERE/'economic_arithmetic_audit.json').write_text(json.dumps(dict(status='PASS',rows=checked,complete_confirmation_groups=len(cache),
        independent_price_equation=True,all_failed_trajectories_included=True,annual_draws=2000,series_per_draw=12),indent=2)+'\n')
    guide='''# 数据字段与直接绘图入口

本目录为 v0.21 的重复调用机制扩展；上一级原五档结果仍支撑单次事件、光伏与独立敏感性。所有统计量和绘图坐标已给出，无需预处理。

| 文件 | 直接用途 |
|---|---|
| confirmation_summary.csv | 图 3a：同请求成功率、Wilson 下界；所有失败类别计数 |
| selected_offers.csv | 图 3c、S3d：开发选值；空值是未选出，不是零容量 |
| paired_controller_contrasts.csv | 配对差异、95% 区间、挽救/损失计数及 Holm 校正 P |
| illustration_*.csv / illustration_windows.csv | 图 3b 的固定开发示例，完整小时值与每次窗口上限 |
| economic_primary.csv / economic_sensitivity.csv | 图 6c 和补充表：完整账本对应的报价门槛 |
| ready_hourly_curves.csv | 图 S3a,b：全部情景的小时均值、中位数及第 5/95 百分位 |
| development_summary.csv | 图 S3c：全额请求的开发失败类型；不与确认集合并 |
| hourly_partition_index.csv | 每个控制器/比例/情景组的完整 Parquet 与 CSV 相对路径 |
| recovery_input_index.csv | 每个冻结输入文件夹的相对路径与身份 |

case 为 f05/f10/f20/f40/f60，指允许延期的工作 GPU 小时比例。program 如 H8G12 表示八小时调用、两次调用之间空隙十二小时，共四次。controller 区分 original、all_window_mpc、all_window_greedy。fraction 是相对于既有单次事件承诺的请求比例，绝不是可延后工作比例。capacity_kw 为实际请求 kW。role 区分开发与确认。scenario_seed/seed 配对完整 216 小时情景，不把四次调用视为四个独立样本。

successes/trials 是整组成功次数/情景数；success_fraction 是观测比例；wilson_lower 是单侧 95% Wilson 成功概率下界；qualified 要求下界至少 0.95。每组必须四次调用全部满足六项原标准。failures_* 是至少一次该项失败的情景数，类别可重叠。failure_* 是逐情景或逐调用布尔标记。difference_pp 和 ci_*_pp 单位为百分点，后者是完整种子的配对 bootstrap 区间。Holm P 在全部 16 个控制器对比中校正；资格下界仍为逐项结果。

selected_by_development 与 confirmation_qualified 必须分开读取。offerable_selected_option 同时要求两者成立。全额八小时/十二小时间隔新控制器虽然在确认中达到 294/300，但开发未选中；不可用它覆盖已冻结的 75% 选值。

payment_usd_kw_year 是每个报价核算千瓦的年度补偿门槛：在自身运行峰值按比例扩大到 1 MW 后，年度净成本第 95 百分位除以对应报价千瓦。它不是实测报价，也不是均值置信限。annual_series=12，全部情景包括失败均进入共同年度抽样。waiting_price 是美元/GPU-h/h；site_cost 是美元/年；displaced_value 是美元/延后 GPU-h；regime 区分现有余量、预留容量与假设被挤出价值。

hourly_full/ 保存原始全部小时字段，并增加对应无响应基准、情景身份、超额积压和累计错过期限工作。基准由相同输入直接提供。paired_baseline_* 是基准数值，excess_backlog_gpu_h 是有响应减无响应排队工作，paired_compute_debt_kwh 是相同差值的能量口径。incremental_power_kw 为有响应减无响应 PCC 功率，可为负。cumulative_missed_gpu_h 先在每条轨迹内逐小时累加，再求分位数；低于 1% 期限损失标准并不意味着绝对损失为零。hourly_plot_csv/ 包含全部小时，不抽样；ready_hourly_curves.csv 的 mean/median/p05/p95 对 metric 所指列计算，百分位为情景分散性，不是均值的置信区间。

controller_audit/ 保存 observed_active_windows、target_pcc_kw、proposed_fraction、guarded_fraction、additional_cap_active、target_below_fixed_power。它们分别表示当前存续窗口数、合并功率上限、提议/最终分配、是否额外限幅、目标是否低于不可调功率。非事件/恢复时 target_pcc_kw 为空值（无附加限制）。部分按类别的到达/执行字段在无该类活动时为结构性空值；重跑验证同时比较数值与空值位置，不能把空值任意填零后声称原始结果一致。

冻结 selection.json 的 confirmation_not_yet_run 记录的是选值冻结当时的状态，不能作为当前执行状态；当前完成状态见 export_receipt.json 和论文修订目录 PROGRESS.json。trace_path/receipt_path 是原计算的溯源绝对路径；重画与恢复应使用本目录相对路径索引。全部代码、绘图入口和无需原始生产数据的单情景重跑示例随完整包交付。
'''
    (DATA/'FIELD_GUIDE.md').write_text(guide)
    legacy=pd.read_csv(ROOT/'manuscript/source_data/nature_workload_composition_v1/COLUMN_DICTIONARY.csv').set_index('column')
    locations={}
    for p in DATA.glob('*.csv'):
        if p.name in ['COLUMN_DICTIONARY.csv','FILE_MANIFEST.csv']:continue
        for col in pd.read_csv(p,nrows=0).columns:locations.setdefault(col,set()).add(p.name)
    for folder in ['hourly_full','controller_audit']:
        paths=list((DATA/folder).glob('*.parquet'))
        if paths:
            for col in pq.read_schema(paths[0]).names:locations.setdefault(col,set()).add(folder+'/*.parquet')
    meaning={
      'fraction':('fraction','Request / frozen single-event offer; not the fraction of eligible work'),
      'selected_fraction':('fraction','Largest development-qualified tested request fraction; missing means none'),
      'selected_capacity_kw':('kW','Frozen development-selected repeated request'),
      'offer_fraction':('fraction','Request / frozen single-event offer'),
      'payment_usd_kw_year':('US$/offered accounting kW/year','95th percentile of net annual cost divided by scaled offer'),
      'waiting_price':('US$/GPU-h/h','Declared waiting-exposure unit price'),
      'site_cost':('US$/year','Fixed site charge applied once after proportional scaling'),
      'displaced_value':('US$/deferred GPU-h','Assumed value exposure, not measured operator revenue'),
      'excess_backlog_gpu_h':('GPU-h','Controlled queue minus matched baseline queue'),
      'cumulative_missed_gpu_h':('GPU-h','Within-trajectory cumulative missed work'),
      'observed_active_windows':('count','Observed calls whose event/recovery windows have not expired'),
      'target_pcc_kw':('kW','Strictest current electrical ceiling; missing means no added ceiling'),
      'guarded_fraction':('fraction','Final allocation after all-window clipping and feasible-side rounding'),
      'proposed_fraction':('fraction','Allocation proposed before extra all-window clipping'),
      'additional_cap_active':('boolean','Final allocation is lower than the proposal by more than 1e-8'),
      'target_below_fixed_power':('boolean','Requested electrical ceiling is below fixed PCC demand'),
      'new_deadline_failures':('paired scenarios','Original passes deadline criterion; revised fails it'),
      'rescued_window_only_failures':('paired scenarios','Original only fails window relief; revised passes every criterion'),
      'holm_p_all_reported_contrasts':('probability','Exact paired McNemar P adjusted across all 16 controller contrasts'),
    }
    records=[]
    for col,files in sorted(locations.items()):
        if col in meaning:unit,description=meaning[col]
        elif col in legacy.index:unit,description=legacy.loc[col,['unit','meaning']]
        elif col.startswith('failures_'):unit,description='scenarios','Number of complete scenarios failing named criterion at least once; non-exclusive'
        elif col.startswith('failure_'):unit,description='boolean','Named criterion failure; see unchanged six thresholds in FIELD_GUIDE and protocol'
        elif col.endswith('_pp'):unit,description='percentage points','Paired success difference or interval endpoint, as named'
        elif col in ['mean','median','p05','p95']:unit,description='unit of metric column','Whole-scenario descriptive statistic at the given hour'
        else:unit,description='field-specific','See FIELD_GUIDE.md, literal field name and complete Supplementary Methods'
        records.append(dict(column=col,unit=unit,meaning=description,tables=';'.join(sorted(files))))
    pd.DataFrame(records).to_csv(DATA/'COLUMN_DICTIONARY.csv',index=False)
    files=sorted(p for p in DATA.rglob('*') if p.is_file() and p.name!='FILE_MANIFEST.csv')
    pd.DataFrame([dict(path=p.relative_to(DATA).as_posix(),bytes=p.stat().st_size,sha256=sha(p)) for p in files]).to_csv(DATA/'FILE_MANIFEST.csv',index=False)
    reasons='''# v0.21 新结果、解释与修订理由

本轮已经完成“失败机制—控制干预—候选选值—独立确认—参与成本”的补充研究。没有启动子智能体，没有填写作者或许可证信息，没有将开发结果冒充新的独立检验。研究是在已有结果指导下设计的后续实验；新确认集在控制器和选值冻结后运行。

## 1. 原来的解释需要纠正到什么程度

原来观察到重复调用成功率下降，并不足以说明数据中心已经耗尽可调能力。原控制器在多个事件及恢复窗口重叠时，只读取一个“已实现峰值减负比例最小”的窗口。这个窗口不一定给出最低的允许功率上限，因而可能遗漏另一个尚未结束窗口的约束。

两个窗口可分别要求功率不超过 600 和 580 kW。如果汇总状态选择了前者，仅按 600 kW 控制就仍可能违反后者。新包装器逐次记住已经发生的调用，同时保留各自的上限，取最严格者。实际算法还保留事件交付和反弹上限，并处理不可调需求与可行侧舍入。

这属于原控制实现的局限修正。论文不能把修正前的所有失败都解释成物理极限，也不能把这项修正本身包装成一种新的普适算法。新的因果控制仍然只看当前可见状态，不预先知道未来调用或到达。

## 2. 相同请求下，干预改变了什么

主要比较固定在 10% 工作资格、同一 5.898243 kW 请求、四次八小时调用、十二小时间隔。新确认集共有 300 个配对完整情景：

| 指标 | 原 MPC | 每次保留恢复约束的 MPC |
|---|---:|---:|
| 整组成功次数 | 252/300 | 294/300 |
| 观测成功率 | 84.0% | 98.0% |
| 单侧 95% Wilson 下界 | 0.8022 | 0.9618 |
| 仅窗口峰值减负不足的失败 | 42 | 0 |

配对提高 14.0 个百分点，95% 区间 10.3–18.0；全部 16 个控制器比较 Holm 校正后 P = 5.91 × 10⁻¹²。42 个改善情景原来均仅因窗口指标失败，没有原来成功而新方案失败的情景。相同恢复约束包住贪心提议策略，也达到 294/300，因此改善不应归功于 MPC 特有的优化能力。

新确认集中没有情景超过 1% 期限损失标准，但这不等于每个 GPU 小时都没有损失。新 MPC 的平均累计增量损失约 0.218 GPU-h，极端情景约 23.11 GPU-h，均保留在源数据和补充图中。该主比较下剩余六个失败涉及逐小时交付不足。

四种安排的开发对比也显示代价：在 10% 工作资格、八小时调用和八小时间隔下，全额请求的期限失败从 7/100 增加到 33/100，总成功次数从 80/100 降至 61/100。严格履行电力恢复义务可能挤压紧急作业，不能宣称新约束在任何安排下都提高成功率。

## 3. 实际支持哪些承诺

开发复用 100 个种子，八小时测试原承诺的 50%、75%、100%，四小时测试原承诺全额。以相同单侧 Wilson 下界至少 0.95 为选值规则。候选冻结后使用新种子 970000–970299；每个方案都有 300 条完整四调用序列，四次全部通过才计成功。

| 工作资格 | 四小时/八小时间隔，kW | 八小时/八、十二或十六小时间隔，kW |
|---|---:|---:|
| 5% | 2.95 | 2.21 |
| 10% | 5.90 | 4.42 |
| 20% | 11.80 | 8.85 |
| 40% | 22.19 | 16.65 |
| 60% | 34.00 | 25.50 |

表中均为逐次保留恢复约束的 MPC。四小时全额及八小时/八或十二小时间隔的 75% 方案为 300/300；八小时/十六小时间隔为 299/300，下界分别为 0.9911 和 0.9852。原 MPC 仅在八小时/十六小时间隔选出 75% 候选，同样为 299/300。总共 25 个开发候选全部通过各自的新确认检验；这是逐项保证，不是同时 95% 置信保证。

特别注意：八小时/十二小时间隔的新控制器全额请求，作为事先声明的比较方案，在新确认集也达到 294/300并通过逐项标准；但开发时为 96/100，没有通过选值规则。所以本文仍报告事先选出的 75% 承诺，不能在看完确认结果后提升到全额。75% 只是已测网格中的选值，不是证明了必须降额 25%，也不是最大可达容量。

40% 仍要求接近全部批处理工作参与，60% 仍改变业务构成；这些边界没有因控制器修正而消失。所有比例指工作延期权限，75% 则指相对于既有响应承诺的降额，两者不是同一个参数。

## 4. 经济性发生什么变化

10% 工作资格下，四小时 5.90 kW 重复承诺的参考参与门槛为 983.87 美元/报价核算 kW/年；八小时 4.42 kW 的三种间隔分别为 1408.00、1371.25 和 1348.78 美元。采用自身峰值按比例放大至 1 MW 的核算尺度，每年十二组独立四调用序列、25,000 美元固定场地成本，以及原电价和等待价格。门槛取年度净成本第 95 百分位，全部成功和失败轨迹均纳入。

这说明，可用承诺变小后，固定成本分摊至更少的报价千瓦，同时较长服务增加等待暴露。方案应将容量、调用安排、服务资格和成本一起报告。不能单独把某个失败方案的较低价格当作可出售报价；也不能将年度独立序列核算当作连续全年运行。新增价格网格共 1,288 行，涵盖等待价格、场地成本、被挤出价值和参考预留成本，均已独立重算核对。

## 5. 对创新性的实际影响

论文现在提供了具体的、可复核的运行选择，并解释了这些选择为什么有不同的服务后果和成本。这比只报告一个固定场景中反复失败更有决策意义。正文的核心证据仍是“工作许可必须贯穿容量、交付、系统收益与成本”，恢复干预补上了从失败观察走向可行运行方案的环节。

新近的 Li 预印本《Beyond Scalar Flexibility》已讨论合资格工作功率与可靠减负之间的区别，也明确认识到实际交付和恢复问题。论文已加入该文，避免把这种区分宣称为本文首次提出。本文的具体补充在于：用因果执行追踪明确多次调用安排中的窗口义务、期限结果、独立选值确认及完整成本。原实现修正不应单独计为主要创新点。

对照深圳城市需求侧资源与电力脱碳参考文章，可取之处是形成清楚的决策比较，而非机械追求同样规模或宣称某项实测是期刊硬门槛。本轮使证据链更完整，但不能仅凭多做这些运行就判断已经达到 Nature Communications 的接收标准。行业工作权限、期限、在线服务开销仍需运营者证据；本文数值是有明确边界的模型结果。

参考：Li, M.，预印本 https://arxiv.org/abs/2609.05406；Li 等深圳文章，https://doi.org/10.1038/s41467-026-76799-4。前者按预印本引用，不声称已同行评审。

## 6. 修改与复核

正文与补充材料为 v0.21，中文全文和中英对照为 v15。正文更新摘要、引言定位、重复调用结果、对应经济结果、讨论和方法；补充材料增加机制、统计、完整选值、失败归因和成本表 10–12，保留旧确认集的表 5、7 并明确标注。主图 3、主图 6、补充图 3 已重绘，其余八图原数据保留。

本轮完成 10,100 次开发和 13,800 次确认回放，保留 5,162,400 小时行与 2,000 套完整输入。核对全部 147 组计数与 Wilson 下界，并独立重算每组首尾种子共 294 条完整轨迹的 1,176 次调用及账本；新的三项控制器回归测试通过。直接重跑一个冻结情景的 216 小时、92 个数值字段与原结果完全一致，并核对结构性空值。图件、版面和交付包的最终检查结果分别记录在 figure_validation.json、pdf_validation.json 和 package_validation.json 中；以这些实际回执为准，不用人工“审核通过”替代检查。

完整交付包为 results/exports/AIDRBench_All_Figures_2026-09-09_v10.zip。包内一次命令直接重画全部 11 图，保存 CSV/Parquet、现成汇总、矢量图、原小时轨迹和直接回放示例。具体校验值和文件大小见 package_validation.json 及同名 .zip.sha256 文件。
'''
    assert checked==1288
    (HERE/'RESULTS_AND_REASONS_ZH.md').write_text(reasons)
    # Update current pointers while preserving the clearly labelled historical record.
    p=ROOT/'README.md';s=p.read_text();cut=s.index('## 历史研究设计')
    p.write_text('''# AIDRBench：工作资格、可靠需求响应与参与成本

当前正文与补充材料为 **v0.21**，中文阅读稿为 **v15**。五档工作资格分析新增了恢复控制干预、冻结的重复承诺选值、新确认集与相应成本。25 个开发候选均通过独立确认；结果以模型和声明的参与权限为条件。

- [正文中文全文](docs/chinese_reader/v15/main_zh.md) · [补充材料中文](docs/chinese_reader/v15/supplement_zh.md)
- [正文 PDF](manuscript/exports/AIDRBench_Nature_Communications_v0.21_content_revision.pdf) · [补充材料 PDF](manuscript/exports/AIDRBench_Nature_Communications_v0.21_Supplementary_Information_content_revision.pdf)
- [六幅主图](docs/nature-mainline-figure-preview.md) · [五幅补充图](docs/nature-supplementary-figure-preview.md)
- [全部图与完整数据包 v10](results/exports/AIDRBench_All_Figures_2026-09-09_v10.zip) · [新结果与解释](manuscript/revisions/repeat_mechanism_2026-09-09/RESULTS_AND_REASONS_ZH.md)
- [权威文件和恢复入口](MAINLINE_FILES.md) · [绘图与打包说明](docs/paper-packaging.md)

图 3、图 6、补充图 3 已更新，其余八图保留五档数据。包内提供全部 11 图的矢量文件、现成面板表、全部小时数据、冻结输入和直接回放例子。本轮未启动子智能体；作者信息、许可证与公开归档 DOI 仍待确认。

'''+s[cut:].replace('文首 v0.20','文首 v0.21',1))
    p=ROOT/'MAINLINE_FILES.md';s=p.read_text();cut=s.index('## Authority order')
    intro='''# AIDRBench formal mainline

## Current revision v0.21, 2026-09-09

The five declared workload configurations remain the common basis. The recovery extension distinguishes a controller omission from service limits and independently confirms 25 development-selected repeated offers. The original confirmation set remains separate from the new 970000–970299 set. Forty and sixty per cent eligibility retain their extra assumptions; 75% in the new repeat selection denotes a request fraction, not workload eligibility.

- English: `manuscript/nature_communications_article.md`, `manuscript/supplementary_information.md`.
- Chinese: `docs/chinese_reader/v15/`; current main/SI PDFs: v0.21 in `manuscript/exports/`.
- Inherited single-event, PV and controls: `manuscript/source_data/nature_workload_composition_v1/`.
- New repeated evidence: `manuscript/source_data/nature_repeat_mechanism_v1/`, 23,900 full replays, 5,162,400 hourly rows and 2,000 complete inputs.
- Current 6 + 5 figures: `docs/figures/repeat_mechanism_v1/artwork/`, PDF/SVG/PNG/TIFF.
- Complete handoff: `results/exports/AIDRBench_All_Figures_2026-09-09_v10.zip`.
- Rationale, frozen design and checks: `manuscript/revisions/repeat_mechanism_2026-09-09/`.

'''
    s=s[cut:]
    s=s.replace('For v0.20, use','For the new repeated intervention, use `protocol.json` and `selection.json` in `manuscript/revisions/repeat_mechanism_2026-09-09/`, followed by hash-bound results in `results/nature_mainline/repeat_mechanism_v1/` and current Source Data. The selection file records its frozen pre-confirmation state; current completion is recorded separately. For the inherited v0.20 evidence, use',1)
    s=s.replace('Valid repeated results are only in','The original v0.20 repeated results are in',1)
    s=s.replace('All current figures are generated by the two standalone Python plotters in `manuscript/revisions/workload_composition_2026-09-09/`; the redraw package uses their supplied CSV/JSON tables.','The two inherited Python plotters draw the unchanged figures; `manuscript/revisions/repeat_mechanism_2026-09-09/plot_extension.py` updates Figures 3, 6 and S3. The complete package launcher runs all three from supplied tables.',1)
    s=s.replace('## Current verification\n','## Current verification\n\nThe v0.21 extension has separate numerical, economic, text, figure, PDF, replay and complete-package receipts in its revision directory. All 147 summary groups and 294 stratified full trajectories were checked; all 1,288 new price rows were recomputed independently. Original checks below continue to describe the inherited five-scenario analysis.\n',1)
    p.write_text(intro+s)
    (ROOT/'docs/chinese_reader/README.md').write_text('''# 中文阅读稿

当前为 [v15](v15/README.md)，逐段对应英文正文及补充材料 v0.21。

- [正文中文全文](v15/main_zh.md)
- [补充材料中文全文](v15/supplement_zh.md)
- [正文中英对照](v15/main_bilingual.md)
- [补充材料中英对照](v15/supplement_bilingual.md)

恢复控制、独立选值确认、成本、方法和十二张补充表已同步。正文六图、补充五图。[完整绘图包 v10](../../results/exports/AIDRBench_All_Figures_2026-09-09_v10.zip) 含直接重绘表格、全部小时结果和冻结输入。v1–v14 为历史阅读稿。
''')
    for stem,filename,tag,count in [('main','nature_communications_article.md','Figure',6),('supplementary','supplementary_information.md','Supplementary Figure',5)]:
        text=(ROOT/'manuscript'/filename).read_text();parts=['# Current v0.21 scientific figures','Five workload configurations; Figures 3, 6 and S3 include the independently tested recovery extension. Complete editable artwork and data are in the v10 handoff.']
        for n in range(1,count+1):
            match=re.search(rf'^### {tag} {n} \| .*?(?=^### |^## |\Z)',text,re.M|re.S);assert match
            content=match[0].strip();heading,body=content.split('\n\n',1)
            body=re.sub(r'!\[[^]]*\]\([^)]+\)\s*','',body).strip()
            name=f'AIDRBench_{"Supplementary_" if count==5 else ""}Figure_{n}.png'
            parts.extend([heading.replace('### ','## ',1),f'![{tag} {n}](figures/repeat_mechanism_v1/artwork/{name})',body])
        (ROOT/f'docs/nature-{stem}-figure-preview.md' if stem=='supplementary' else ROOT/'docs/nature-mainline-figure-preview.md').write_text('\n\n'.join(parts)+'\n')
    p=ROOT/'manuscript/results-evidence-allocation.md';s=p.read_text();cut=s.index('## Historical allocation record')
    p.write_text('''# Current Results evidence allocation v0.21

The six result sections retain the five common workload configurations. The new extension explains recovery failures and independently tests operating choices. Earlier 75% workload benchmarks remain historical.

| Main section / figure | Evidence and role | Complete support |
|---|---|---|
| 1. Work permission | Source composition and explicit eligibility assumptions | Notes 1; Tables 1–3 |
| 2. Single offers | PI planning, development selection, independent confirmation | Note 2; Table 4 |
| 3. Recovery and repeated choices | Same-request intervention, greedy diagnostic, qualified programme choices | Note 3; Tables 5, 10–11; Fig. S3 |
| 4. PV | Unchanged zero-miss planning comparisons | Note 4; Table 6 |
| 5. Hardware allocation and rigid power | Fixed-request controls and their costs | Note 5; Table 8; Fig. S4 |
| 6. Participation | Qualified repeated choices linked to full-series cost | Note 6; Tables 7, 9, 12; Fig. S5 |

The original 960000 confirmation matched-fresh results and new 970000 controller comparisons remain distinct. The main result identifies a controller limitation rather than treating every failure as physical exhaustion. Twenty-five development-selected repeated offers passed new pointwise confirmation; passing full-request comparators do not replace frozen selections. Full candidate grids, non-exclusive failures, hourly quantities and price screens belong in SI/Source Data, not repeated lists in the Results.

'''+s[cut:])
    p=ROOT/'manuscript/terminology-ledger.md';s=p.read_text();needle='| compute debt |'
    extra='| per-call recovery guard | causal memory and electrical ceiling for every observed live event/recovery window | perfect foresight; proof of optimal recovery; guarantee of deadlines |\n| selected repeated offer | largest tested request passing development, then separately tested on fresh scenarios | a full-request comparator that passes confirmation without development selection |\n| request fraction | repeated request divided by the corresponding single-event offer | deferrable-work share; 75% workload eligibility |\n'
    if '| per-call recovery guard |' not in s:s=s.replace(needle,extra+needle,1)
    p.write_text(s)
    (ROOT/'docs/paper-packaging.md').write_text('''# 当前论文 v0.21 与完整绘图包 v10

[完整包](../results/exports/AIDRBench_All_Figures_2026-09-09_v10.zip) 包含正文、补充材料、中文稿 v15、全部 11 图、现成面板数据、完整小时轨迹与冻结输入。当前图 3、6、S3 使用新的恢复干预，其他八图保留原五档结果。

解压后运行 `python RUN_ALL_FIGURES.py`，已有绘图环境可加 `--use-current-python`。输出为全部 11 图的 PDF/SVG/PNG/TIFF，无需预处理数据或重新运行模型。修改新图用 `04_code/repeat_mechanism/plot_extension.py`，其他图用 `04_code/plot_results.py` 和 `plot_supplement.py`。每图目录有图注和数据映射。

`03_data/` 保存原五档完整数据，`03_data/repeat_mechanism/` 保存新 23,900 条回放、5,162,400 小时行和 2,000 套完整输入。统计曲线已在 `ready_hourly_curves.csv` 计算。`FIELD_GUIDE.md` 解释选值与确认、工作比例与请求比例，以及成本口径。绝对溯源路径无需可访问；直接绘图和回放使用包内相对索引。

单情景恢复与重跑命令见包内 README_FIRST.md，`replay_one.py` 从原样保存的作业、期限、社区和配置直接模拟，并对比完整小时文件。完整模拟器和依赖在 `04_code/aidrbench_project/`。

项目中先使用两个原绘图脚本在 `docs/figures/repeat_mechanism_v1/artwork/` 生成全套图，再运行新 `plot_extension.py --data manuscript/source_data/nature_repeat_mechanism_v1 --base-data manuscript/source_data/nature_workload_composition_v1 --output docs/figures/repeat_mechanism_v1/artwork` 替换三图；合并清单逻辑见交付 launcher。文稿与中文同步由新修订目录 `integrate_content.py` 从冻结的 v0.20 副本构建。两个 `scripts/render_*tex.py` 自动读取当前版本与图件，经 Tectonic 编译为 v0.21 PDF。

最终数值、经济、文本、图件、PDF 和完整包验证回执位于 `manuscript/revisions/repeat_mechanism_2026-09-09/`。作者信息、许可证、公开归档 DOI 仍待确认。本轮没有启动子智能体。
''')
    p=HERE/'figure_contract.md';s=p.read_text().replace('配对积压能量及累计未完成工作','配对排队 GPU 小时及累计错过期限工作');p.write_text(s)
    words={}
    text=(ROOT/'manuscript/nature_communications_article.md').read_text()
    for name,start,stop in [('abstract','## Abstract','## Introduction'),('introduction','## Introduction','## Results'),('results','## Results','## Discussion'),('discussion','## Discussion','## Methods'),('methods','## Methods','## Data Availability')]:
        block=text.split(start,1)[1].split(stop,1)[0];block=re.sub(r'!\[[^]]*\]\([^)]+\)','',block)
        words[name]=len(re.findall(r"\b[\w]+(?:[-’'][\w]+)*\b",block))
    (HERE/'section_word_counts.json').write_text(json.dumps(words,indent=2)+'\n')
    print('Price audit PASS:',checked,'rows; source guide and current entry points updated; words:',words)


if __name__=='__main__':main()
