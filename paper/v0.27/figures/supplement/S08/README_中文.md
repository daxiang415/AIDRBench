# S8：硬件经济寿命、工作价值、等待成本与场站费用对单次响应参与门槛的影响

当前投稿补充图；独立交接包 2026-09-17，数值与现有SI一致。 [PDF](AIDRBench_Supplementary_Figure_8.pdf) · [PNG](AIDRBench_Supplementary_Figure_8.png) · [可编辑SVG](AIDRBench_Supplementary_Figure_8.svg) · [直接取数Excel](S08_READY.xlsx)

以下每张CSV已经按当前面板选好行、完成图中换算。先按说明选X/Y列；不需要从旧源表再次筛选、聚合或计算。只修改视觉呈现时保留所有表中数值。

## S08a：单次响应的预留经济寿命敏感性。

[CSV](S08a.csv)，4行。

X=x_plot，Y=两个threshold列；c横轴已乘1000，d横轴已除以1000，其余原单位。original_parameter_value仅供核对。点为成本门槛，不是统计区间。

原图轴名：X = Hardware economic life (years)；Y = Threshold (US$/offered kW/year)。

| 图形/分组 | X列 | Y列 | 区间或堆叠起点 |
| --- | --- | --- | --- |
| 4 h (points) | x_plot | threshold_4h_usd_per_kw_year | 无 |
| 8 h (points) | x_plot | threshold_8h_usd_per_kw_year | 无 |

## S08b：单次响应的被挤占工作价值敏感性。

[CSV](S08b.csv)，4行。

X=x_plot，Y=两个threshold列；c横轴已乘1000，d横轴已除以1000，其余原单位。original_parameter_value仅供核对。点为成本门槛，不是统计区间。

原图轴名：X = Displaced-work value (US$/GPU-h)；Y = Threshold (US$/offered kW/year)。

| 图形/分组 | X列 | Y列 | 区间或堆叠起点 |
| --- | --- | --- | --- |
| 4 h (points) | x_plot | threshold_4h_usd_per_kw_year | 无 |
| 8 h (points) | x_plot | threshold_8h_usd_per_kw_year | 无 |

## S08c：单次响应的等待价格敏感性。

[CSV](S08c.csv)，4行。

X=x_plot，Y=两个threshold列；c横轴已乘1000，d横轴已除以1000，其余原单位。original_parameter_value仅供核对。点为成本门槛，不是统计区间。

原图轴名：X = Waiting price (10⁻³ US$/GPU-h/h)；Y = Threshold (US$/offered kW/year)。

| 图形/分组 | X列 | Y列 | 区间或堆叠起点 |
| --- | --- | --- | --- |
| 4 h (points) | x_plot | threshold_4h_usd_per_kw_year | 无 |
| 8 h (points) | x_plot | threshold_8h_usd_per_kw_year | 无 |

## S08d：单次响应的固定场站费敏感性。

[CSV](S08d.csv)，3行。

X=x_plot，Y=两个threshold列；c横轴已乘1000，d横轴已除以1000，其余原单位。original_parameter_value仅供核对。点为成本门槛，不是统计区间。

原图轴名：X = Annual site fee (thousand US$)；Y = Threshold (US$/offered kW/year)。

| 图形/分组 | X列 | Y列 | 区间或堆叠起点 |
| --- | --- | --- | --- |
| 4 h (points) | x_plot | threshold_4h_usd_per_kw_year | 无 |
| 8 h (points) | x_plot | threshold_8h_usd_per_kw_year | 无 |

## 当前完整图注

### Supplementary Figure 8 | Single-event participation thresholds across hardware economic lifetime, work value, waiting costs and site fees

**a,** Reserved-headroom cost with a hardware economic life of three to six years. **b–d,** Effective displaced-work value, waiting valuation and fixed site fee varied separately without an added reserve cost. All panels retain the 10% eligibility single-event four- and eight-hour offers of 5.898243 kW, supported by 295/300 and 292/300 joint successes under the 1% missed-work standard. Annual accounting draws 50 independent complete event-and-recovery ledgers with replacement, scales proportionally to 1 MW and retains failures. Unvaried prices are US$0.005/GPU-h/h waiting, US$25,000/year site fee, zero displaced-work value and zero missed-work price; electricity and delivered-energy prices follow Table 9. Points are 95th-percentile annual-net-cost thresholds, not confidence limits. Lines join evaluated values without added observations. Economic life affects assumed reserve amortisation, not measured hardware ageing or failure. These single-event scenarios must not be substituted for the independently qualified repeated products and twelve-series accounting in Fig. 6. Source Data also retain the missed-work-price check, which does not visibly change these single-event thresholds.

### 补充图 8 | 硬件经济寿命、工作价值、等待成本与场站费用对单次响应参与门槛的影响

**a，** 硬件经济寿命为三至六年时的预留余量成本。**b–d，** 分别改变有效被替代工作价值、等待估值和固定场站费用，不另加预留成本。全部面板保持 10% 工作参与下四小时与八小时单次报价 5.898243 kW，在允许 1% 漏期的标准下分别由 295/300 和 292/300 联合成功支持。年度核算有放回抽取 50 条独立的完整事件—恢复账本，按比例缩放至 1 MW，并保留失败。未改变的价格为等待 0.005 美元/GPU-h/h、场站费用 25,000 美元/年、被替代工作价值为零、漏期工作价格为零；电价与交付电量价格见表 9。点为年度净成本的第 95 百分位门槛，不是置信界限。连线只连接已计算数值，不添加观测。经济寿命影响假定的预留成本摊销，不代表实测硬件老化或故障。这些单次事件情景不能替代图 6 的独立合格重复产品及十二序列年度核算。源数据还保留了漏期工作定价检查，其对这些单次门槛没有可见影响。

样式与轴范围可参照同目录 `axes_reference.json`；定量坐标核对见包根目录 `audit/PANEL_VERIFICATION.json`。

## 直接重绘本图

在本文件夹运行 `python redraw.py`，或在包根目录运行 `python DRAW_SUPPLEMENT.py --figures S8`。程序直接读取本文件夹的CSV；只改样式时修改包根目录的 `DRAW_SUPPLEMENT.py`。首次运行需按总说明安装依赖。输出存入包根目录 `MY_REDRAW`，保留参考图。

本目录PDF/PNG/SVG是论文采用的图稿。重绘程序提供同数据的可修改模板，字体、图例与布局可与参考图有差异。Excel是同一份数据的便利副本；若在Excel中改数，请将对应工作表另存为同名CSV后运行，程序不直接读取Excel。
