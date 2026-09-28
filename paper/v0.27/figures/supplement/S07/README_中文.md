# S7：有无储能时刚性与灵活调度的光伏接纳容量、弃光电量和电网购电量

当前投稿补充图；独立交接包 2026-09-17，数值与现有SI一致。 [PDF](AIDRBench_Supplementary_Figure_7.pdf) · [PNG](AIDRBench_Supplementary_Figure_7.png) · [可编辑SVG](AIDRBench_Supplementary_Figure_7.svg) · [直接取数Excel](S07_READY.xlsx)

以下每张CSV已经按当前面板选好行、完成图中换算。先按说明选X/Y列；不需要从旧源表再次筛选、聚合或计算。只修改视觉呈现时保留所有表中数值。

## S07a：有无储能分别展示的绝对光伏接纳容量。

[CSV](S07a.csv)，5行。

X=eligible_work_pct（按实际百分比数值位置），Y=rigid_hosting_kw/flexible_hosting_kw；连接已计算点。值为100个场景中的最小接纳容量，非均值或误差界。

原图轴名：X = Eligible work (%)；Y = PV hosting capacity (kW)。

| 图形/分组 | X列 | Y列 | 区间或堆叠起点 |
| --- | --- | --- | --- |
| rigid (points) | eligible_work_pct | rigid_hosting_kw | 无 |
| flexible (points) | eligible_work_pct | flexible_hosting_kw | 无 |

原图X刻度（位置→文字）：5→5；10→10；20→20；40→40*；60→60†

## S07b：有无储能分别展示的绝对光伏接纳容量。

[CSV](S07b.csv)，5行。

X=eligible_work_pct（按实际百分比数值位置），Y=rigid_hosting_kw/flexible_hosting_kw；连接已计算点。值为100个场景中的最小接纳容量，非均值或误差界。

原图轴名：X = Eligible work (%)；Y = PV hosting capacity (kW)。

| 图形/分组 | X列 | Y列 | 区间或堆叠起点 |
| --- | --- | --- | --- |
| rigid (points) | eligible_work_pct | rigid_hosting_kw | 无 |
| flexible (points) | eligible_work_pct | flexible_hosting_kw | 无 |

原图X刻度（位置→文字）：5→5；10→10；20→20；40→40*；60→60†

## S07c：固定500kW光伏下的平均弃光电量。

[CSV](S07c.csv)，5行。

X=eligible_work_pct；四个Y列为调度×储能组合。刚性虚线、灵活实线；有无储能用颜色区分。单位已换算为kwh。

原图轴名：X = Eligible work (%)；Y = Mean curtailed PV energy (kWh)。

| 图形/分组 | X列 | Y列 | 区间或堆叠起点 |
| --- | --- | --- | --- |
| rigid_no_BESS_kwh (points) | eligible_work_pct | rigid_no_BESS_kwh | 无 |
| flexible_no_BESS_kwh (points) | eligible_work_pct | flexible_no_BESS_kwh | 无 |
| rigid_with_BESS_kwh (points) | eligible_work_pct | rigid_with_BESS_kwh | 无 |
| flexible_with_BESS_kwh (points) | eligible_work_pct | flexible_with_BESS_kwh | 无 |

原图X刻度（位置→文字）：5→5；10→10；20→20；40→40*；60→60†

## S07d：固定500kW光伏下的平均电网购电量。

[CSV](S07d.csv)，5行。

X=eligible_work_pct；四个Y列为调度×储能组合。刚性虚线、灵活实线；有无储能用颜色区分。单位已换算为mwh。

原图轴名：X = Eligible work (%)；Y = Mean grid import (MWh)。

| 图形/分组 | X列 | Y列 | 区间或堆叠起点 |
| --- | --- | --- | --- |
| rigid_no_BESS_mwh (points) | eligible_work_pct | rigid_no_BESS_mwh | 无 |
| flexible_no_BESS_mwh (points) | eligible_work_pct | flexible_no_BESS_mwh | 无 |
| rigid_with_BESS_mwh (points) | eligible_work_pct | rigid_with_BESS_mwh | 无 |
| flexible_with_BESS_mwh (points) | eligible_work_pct | flexible_with_BESS_mwh | 无 |

原图X刻度（位置→文字）：5→5；10→10；20→20；40→40*；60→60†

## 当前完整图注

### Supplementary Figure 7 | Solar hosting capacity, curtailment and grid imports under rigid and flexible scheduling, with and without storage

**a,b,** Absolute PV hosting capacities without and with BESS, for rigid and flexible schedules. Each point is the minimum over 100 scenarios. **c,d,** Arithmetic mean curtailed PV energy and grid imports per modelled horizon for a fixed 500-kW PV installation, over the same 100 paired scenarios. Blue and green identify no BESS and BESS; dashed circles and solid squares identify rigid and flexible operation. Grid-import curves nearly coincide at the displayed scale; no uncertainty or significance is inferred from their separation. These absolute outcomes complement the paired gains and bootstrap intervals in Supplementary Fig. 4a,b. Lines connect evaluated eligibility fractions only. The 40% and 60% cases retain the additional business assumptions listed in Supplementary Table 2; configuration-dependent demand also changes across fractions, so within-case rigid–flexible comparisons isolate scheduling. All schedules use full information and zero missed work. Means and minima are descriptive summaries, and do not establish the delivery reliability of a causal controller; small storage contrasts remain limited by optimisation precision. All scenario values are retained in Source Data.

### 补充图 7 | 有无储能时刚性与灵活调度的光伏接纳容量、弃光电量和电网购电量

**a,b，** 无储能和有储能时，刚性与灵活调度的绝对光伏接纳容量。每个点为 100 个情景中的最小值。**c,d，** 固定 500 kW 光伏系统在每个模型时域内的弃光电量与电网购电量，采用相同 100 个配对情景的算术均值。蓝色与绿色分别表示无储能和有储能；虚线圆点与实线方点分别表示刚性和灵活运行。购电曲线在所示尺度下几乎重合，不能根据其分离程度推断不确定性或显著性。这些绝对结果补充了补充图 4a,b 的配对增益与自助法区间。连线仅连接已计算的参与比例。40% 和 60% 情景保留补充表 2 列出的额外业务假设；不同配置的用电需求也随比例改变，因此应在同一配置内用刚性—灵活配对比较识别调度影响。所有调度使用完整未来信息并要求零漏期。均值与最小值是描述性汇总，不能证明实时控制器的交付可靠性；微小储能差异仍受优化精度限制。源数据保留所有情景数值。

样式与轴范围可参照同目录 `axes_reference.json`；定量坐标核对见包根目录 `audit/PANEL_VERIFICATION.json`。

## 直接重绘本图

在本文件夹运行 `python redraw.py`，或在包根目录运行 `python DRAW_SUPPLEMENT.py --figures S7`。程序直接读取本文件夹的CSV；只改样式时修改包根目录的 `DRAW_SUPPLEMENT.py`。首次运行需按总说明安装依赖。输出存入包根目录 `MY_REDRAW`，保留参考图。

本目录PDF/PNG/SVG是论文采用的图稿。重绘程序提供同数据的可修改模板，字体、图例与布局可与参考图有差异。Excel是同一份数据的便利副本；若在Excel中改数，请将对应工作表另存为同名CSV后运行，程序不直接读取Excel。
