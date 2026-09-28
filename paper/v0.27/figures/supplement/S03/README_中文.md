# S3：重复响应报价的局部网格筛选、供给与期限失败，以及早期周序列对照

当前投稿补充图；独立交接包 2026-09-17，数值与现有SI一致。 [PDF](AIDRBench_Supplementary_Figure_3.pdf) · [PNG](AIDRBench_Supplementary_Figure_3.png) · [可编辑SVG](AIDRBench_Supplementary_Figure_3.svg) · [直接取数Excel](S03_READY.xlsx)

以下每张CSV已经按当前面板选好行、完成图中换算。先按说明选X/Y列；不需要从旧源表再次筛选、聚合或计算。只修改视觉呈现时保留所有表中数值。

## S03a：参考重复产品局部网格的开发评分。

[CSV](S03a.csv)，6行。

X=request_kw，Y=两列lower，分别为1%与零漏期标准；Y=.95参考线。100开发情景/点。该图不是图3a的八周容量。

原图轴名：X = Tested request (kW)；Y = Development Wilson lower bound。

| 图形/分组 | X列 | Y列 | 区间或堆叠起点 |
| --- | --- | --- | --- |
| success_1pct (points) | request_kw | success_1pct_lower | 无 |
| success_zero (points) | request_kw | success_zero_lower | 无 |

## S03b：参考重复产品局部网格的开发评分。

[CSV](S03b.csv)，6行。

X=request_kw，Y=两列lower，分别为1%与零漏期标准；Y=.95参考线。100开发情景/点。该图不是图3a的八周容量。

原图轴名：X = Tested request (kW)；Y = Development Wilson lower bound。

| 图形/分组 | X列 | Y列 | 区间或堆叠起点 |
| --- | --- | --- | --- |
| success_1pct (points) | request_kw | success_1pct_lower | 无 |
| success_zero (points) | request_kw | success_zero_lower | 无 |

## S03c：结构对照中即时不足与期限失败的百分比。

[CSV](S03c.csv)，6行。

两组柱：X=x_shortage/x_deadline，Y=shortage_pct/deadline_miss_pct；数值已从300案例计数换算为%。两类失败可以重叠，不做堆叠。

原图轴名：X = 无；Y = Scenarios affected (%)。

| 图形/分组 | X列 | Y列 | 区间或堆叠起点 |
| --- | --- | --- | --- |
| Immediate shortage (bar) | x_shortage | shortage_pct | 无 |
| Deadline failure (bar) | x_deadline | deadline_miss_pct | 无 |

原图X刻度（位置→文字）：0→50 / ref；1→50 / tight；2→65 / ref；3→65 / tight；4→80 / ref；5→80 / tight

## S03d：早期次数权重对照的逐周成功与供给不足。

[CSV](S03d.csv)，8行。

X=week_position，刻度=week_label；successes_at_4p42与shortage_at_4p42堆叠，后者起点shortage_bottom。successes_at_2p95为菱形点。

原图轴名：X = Observed week；Y = Realisations per week。

| 图形/分组 | X列 | Y列 | 区间或堆叠起点 |
| --- | --- | --- | --- |
| Success 4.42 (bar) | week_position | successes_at_4p42 | 无 |
| Shortage 4.42 (bar) | week_position | shortage_at_4p42 | 起点 shortage_bottom |
| Success 2.95 (points) | week_position | successes_at_2p95 | 无 |

## 当前完整图注

### Supplementary Figure 3 | Local offer-grid screening, supply and deadline failures, and the earlier weekly workload-transfer comparison

**a,b,** Development success-probability lower bounds for each four- and eight-hour request on the finer reference grid. Each point uses 100 scenarios under both service rules and a one-sided 95% Wilson bound. The dashed line is the 0.95 selection threshold. The largest tested eight-hour request is selected, leaving the continuous maximum undetermined. **c,** Counts of immediate supply shortage and more than 1% missed work in 300 full-request control scenarios; the two failures can occur together. **d,** The earlier 986000-series test using observed submission counts in their original hourly order. Bars separate success from immediate shortage at 4.42 kW; markers show successes at 2.95 kW. The two service rules give identical scores at each request. Each of eight observed weeks has ten synthetic realisations, so pooled counts are descriptive. Note 7 explains the earlier design. Table 15 and Source Data retain the identical paired final-call outcomes.

### 补充图 3 | 重复响应报价的局部网格筛选、供给与期限失败，以及早期周序列对照

**a,b，** 参考四小时和八小时请求在更细网格上的开发结果。每个点使用 100 个情景，按两种服务规则计算单侧 95% Wilson 成功概率下界；虚线为 0.95 选值门槛。八小时选中的是最高已测试请求，连续最大容量仍未确定。**c，** 全额请求下 300 个对照情景中，可削减负荷不足和超过 1% 工作漏期的次数；两种失败可能同时发生。**d，** 较早的 986000 系列检验，保留观测提交数的原始小时顺序。柱形区分 4.42 kW 下的成功与即时供给不足，标记显示 2.95 kW 下的成功数。每个请求按两种服务规则评分的结果相同。八个观测周各有十次合成实现，因此合并计数只作描述。说明 7 解释这一较早设计；表 15 和源数据保留了结果相同的末次调用配对对照。

样式与轴范围可参照同目录 `axes_reference.json`；定量坐标核对见包根目录 `audit/PANEL_VERIFICATION.json`。

## 直接重绘本图

在本文件夹运行 `python redraw.py`，或在包根目录运行 `python DRAW_SUPPLEMENT.py --figures S3`。程序直接读取本文件夹的CSV；只改样式时修改包根目录的 `DRAW_SUPPLEMENT.py`。首次运行需按总说明安装依赖。输出存入包根目录 `MY_REDRAW`，保留参考图。

本目录PDF/PNG/SVG是论文采用的图稿。重绘程序提供同数据的可修改模板，字体、图例与布局可与参考图有差异。Excel是同一份数据的便利副本；若在Excel中改数，请将对应工作表另存为同名CSV后运行，程序不直接读取Excel。
