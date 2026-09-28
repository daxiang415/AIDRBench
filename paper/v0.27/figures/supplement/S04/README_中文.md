# S4：可延期工作比例、GPU 分配与刚性功率假设下的光伏收益和固定请求交付

当前投稿补充图；独立交接包 2026-09-17，数值与现有SI一致。 [PDF](AIDRBench_Supplementary_Figure_4.pdf) · [PNG](AIDRBench_Supplementary_Figure_4.png) · [可编辑SVG](AIDRBench_Supplementary_Figure_4.svg) · [直接取数Excel](S04_READY.xlsx)

以下每张CSV已经按当前面板选好行、完成图中换算。先按说明选X/Y列；不需要从旧源表再次筛选、聚合或计算。只修改视觉呈现时保留所有表中数值。

## S04a：五档工作许可下的PV接纳增量。

[CSV](S04a.csv)，5行。

分类X用x_no_BESS/x_with_BESS，刻度用x_position与x_label；Y=hosting_gain_kw。差值是两个最小接纳容量之差，不画误差条。

原图轴名：X = Eligible work (%)；Y = PV hosting gain (kW)。

| 图形/分组 | X列 | Y列 | 区间或堆叠起点 |
| --- | --- | --- | --- |
| no_BESS (points) | x_no_BESS | no_BESS_hosting_gain_kw | 无 |
| with_BESS (points) | x_with_BESS | with_BESS_hosting_gain_kw | 无 |

原图X刻度（位置→文字）：0→5；1→10；2→20；3→40*；4→60*

## S04b：固定500kW光伏系统利用率增量及配对95%区间。

[CSV](S04b.csv)，5行。

Y=mean_pp；误差长度使用error_minus_pp/error_plus_pp，已算好。单位百分点，不要再次乘100。X与S04a对应。

原图轴名：X = Eligible work (%)；Y = Utilisation gain (percentage points)。

| 图形/分组 | X列 | Y列 | 区间或堆叠起点 |
| --- | --- | --- | --- |
| no_BESS (errorbar) | x_no_BESS | no_BESS_mean_pp | 下端点 no_BESS_lower_pp；上端点 no_BESS_upper_pp |
| with_BESS (errorbar) | x_with_BESS | with_BESS_mean_pp | 下端点 with_BESS_lower_pp；上端点 with_BESS_upper_pp |

原图X刻度（位置→文字）：0→5；1→10；2→20；3→40*；4→60*

## S04c：固定10%工作许可下，不重新选报价的独立成功率。

[CSV](S04c.csv)，5行。

Y=success_4h_pct/success_8h_pct；仅向下的误差长度为error_minus，向上为0。参考线95%。X已包含两组的轻微错位。

原图轴名：X = 无；Y = Success (%)。

| 图形/分组 | X列 | Y列 | 区间或堆叠起点 |
| --- | --- | --- | --- |
| 4 h (errorbar) | x_4h | success_4h_pct | 下端点 lower_4h_pct；上端点 success_4h_pct |
| 8 h (errorbar) | x_8h | success_8h_pct | 下端点 lower_8h_pct；上端点 success_8h_pct |

原图X刻度（位置→文字）：0→Primary；1→GPUs / 20%；2→GPUs / 30%；3→Rigid / 150 W；4→Rigid / 225 W

## S04d：同一组硬件对照的PV接纳增量。

[CSV](S04d.csv)，5行。

分类横轴同S04c；Y=两列hosting_gain_kw，分别无储能/有储能。

原图轴名：X = 无；Y = PV hosting gain (kW)。

| 图形/分组 | X列 | Y列 | 区间或堆叠起点 |
| --- | --- | --- | --- |
| no_BESS (points) | x_no_BESS | no_BESS_hosting_gain_kw | 无 |
| with_BESS (points) | x_with_BESS | with_BESS_hosting_gain_kw | 无 |

原图X刻度（位置→文字）：0→Primary；1→GPUs / 20%；2→GPUs / 30%；3→Rigid / 150 W；4→Rigid / 225 W

## 当前完整图注

### Supplementary Figure 4 | Solar gains and fixed-request delivery across workload eligibility, GPU allocation and rigid-load power assumptions

**a,** Flexible minus rigid all-scenario PV hosting capacity across the five eligibility scenarios, with and without BESS; each capacity is the minimum over 100 scenarios. **b,** Paired gain in utilisation of a fixed 500-kW PV system; points are means and whiskers are 95% paired bootstrap intervals. The intervals cover sampling, not optimisation error; small storage contrasts remain unresolved at solver precision. **c,** Four- and eight-hour success at unchanged primary single-event requests across allocation and rigid-power controls, with one-sided 95% Wilson lower bounds from 300 scenarios. **d,** Corresponding gains in all-scenario PV hosting over 100 paired scenarios. Panels c,d retain 10% eligibility and vary only GPU allocation or the stated rigid-power proxy. PV schedules use full information and zero missed work; hosting differences are differences of minima, not mean effects or confidence intervals. The 10% primary points and no-BESS GPU20 hosting point use the strict repeat audit; other points retain the original settings (Table 24).

### 补充图 4 | 可延期工作比例、GPU 分配与刚性功率假设下的光伏收益和固定请求交付

**a，** 五档工作参与比例下，有无储能时灵活运行减刚性运行的全情景光伏接纳容量；各容量为 100 个情景中的最小值。**b，** 固定 500 kW 光伏系统利用率的配对增益；点为均值，误差线为 95% 配对自助法区间。区间涵盖抽样而非优化误差；微小储能差异在求解精度下仍未分辨。**c，** 分配与刚性功率对照在不变主要单次报价下的四小时与八小时成功情况，附 300 个情景的单侧 95% Wilson 下界。**d，** 相应的全情景光伏接纳增益，采用 100 个配对情景。c,d 保持 10% 工作参与，仅改变 GPU 分配或声明的刚性功率代理。光伏调度使用完整信息且零漏期；接纳差异是两个最小值之差，不是均值效应或置信区间。 主 10% 数据点和 GPU20 无储能接纳点采用严格重算；其他点保留原设置（表 24）。

样式与轴范围可参照同目录 `axes_reference.json`；定量坐标核对见包根目录 `audit/PANEL_VERIFICATION.json`。

## 直接重绘本图

在本文件夹运行 `python redraw.py`，或在包根目录运行 `python DRAW_SUPPLEMENT.py --figures S4`。程序直接读取本文件夹的CSV；只改样式时修改包根目录的 `DRAW_SUPPLEMENT.py`。首次运行需按总说明安装依赖。输出存入包根目录 `MY_REDRAW`，保留参考图。

本目录PDF/PNG/SVG是论文采用的图稿。重绘程序提供同数据的可修改模板，字体、图例与布局可与参考图有差异。Excel是同一份数据的便利副本；若在Excel中改数，请将对应工作表另存为同名CSV后运行，程序不直接读取Excel。
