# S10：数据中心峰值功率分解、节点固定开销敏感性与光伏求解精度核验

当前投稿补充图；独立交接包 2026-09-17，数值与现有SI一致。 [PDF](AIDRBench_Supplementary_Figure_10.pdf) · [PNG](AIDRBench_Supplementary_Figure_10.png) · [可编辑SVG](AIDRBench_Supplementary_Figure_10.svg) · [直接取数Excel](S10_READY.xlsx)

以下每张CSV已经按当前面板选好行、完成图中换算。先按说明选X/Y列；不需要从旧源表再次筛选、聚合或计算。只修改视觉呈现时保留所有表中数值。

## S10a：包含PUE的设施峰值功率分项。

[CSV](S10a.csv)，4行。

横向柱：X=facility_power_kw，Y=y_position，按component从上到下。四项合计193.44kW附近的完整精度峰值。

原图轴名：X = Facility power including PUE (kW)；Y = 无。

| 图形/分组 | X列 | Y列 | 区间或堆叠起点 |
| --- | --- | --- | --- |
| Power components (barh) | facility_power_kw | y_position | 无 |

原图Y刻度（位置→文字）：0→Node overhead；1→All-GPU idle；2→Rigid increment；3→Flexible increment

## S10b：节点固定开销改变峰值及同一报价的占比。

[CSV](S10b.csv)，4行。

X=node_overhead_w，Y=single_offer_pct_peak（已为%），operating_peak_kw用于标签；无误差条。

原图轴名：X = Fixed overhead (W/node)；Y = 5.90-kW offer / operating peak (%)。

| 图形/分组 | X列 | Y列 | 区间或堆叠起点 |
| --- | --- | --- | --- |
| Overhead sensitivity (points) | node_overhead_w | single_offer_pct_peak | 无 |

## S10c：常规与严格求解的100组PV利用率增量对照。

[CSV](S10c.csv)，100行。

X=original_utilisation_gain_pp，Y=strict_utilisation_gain_pp，均为百分点；每行一对，全部100点保留。画Y=X虚线，不强行把接近零的值截为零。

原图轴名：X = Original utilisation gain (pp)；Y = Strict utilisation gain (pp)。

| 图形/分组 | X列 | Y列 | 区间或堆叠起点 |
| --- | --- | --- | --- |
| Precision pairs (points) | original_utilisation_gain_pp | strict_utilisation_gain_pp | 无 |

## S10d：常规与严格求解的100组PV利用率增量对照。

[CSV](S10d.csv)，100行。

X=original_utilisation_gain_pp，Y=strict_utilisation_gain_pp，均为百分点；每行一对，全部100点保留。画Y=X虚线，不强行把接近零的值截为零。

原图轴名：X = Original utilisation gain (pp)；Y = Strict utilisation gain (pp)。

| 图形/分组 | X列 | Y列 | 区间或堆叠起点 |
| --- | --- | --- | --- |
| Precision pairs (points) | original_utilisation_gain_pp | strict_utilisation_gain_pp | 无 |

## 当前完整图注

### Supplementary Figure 10 | Data-centre peak-power decomposition, fixed node-overhead sensitivity and solar solver-precision checks

**a,** Exact components of the 193.438980-kW primary operating peak; PUE applies to all components. **b,** The unchanged 5.898243-kW single-event offer as a share of peak as node overhead varies. Points are deterministic accounting values, not replicate estimates. Re-scoring all 600 reference repeated schedules preserves their success flags at each overhead; Table 23 gives PCC headroom. **c,d,** Each point compares the original and strictly solved flexible-minus-rigid utilisation contrast for one of 100 paired primary scenarios, without and with BESS. The dashed diagonal marks equality, not a fitted model. c is a continuous LP and its tiny gain is unchanged; d resolves to numerical zero after tightening MIP and feasibility tolerances. The final lexicographic difference and primary objective bounds are reported separately in Table 24. No statistical inference is assigned to pointwise solver agreement.

### 补充图 10 | 数据中心峰值功率分解、节点固定开销敏感性与光伏求解精度核验

**a，** 主情景 193.438980 kW 运行峰值的精确分项，全部分项均计入 PUE。**b，** 节点开销变化时，保持 5.898243 kW 单次报价的峰值占比。点为确定性核算值，不是重复估计。对全部 600 条参考重复调度重新评分后，各档开销均保留原成功标记；表 23 给出接入余量。**c,d，** 每个点比较一个主情景的原始与严格求解“灵活减刚性”利用率差异，无储能和有储能各 100 个配对情景。虚线表示相等，而非拟合模型。c 是连续线性规划，其微小增益保持不变；d 在收紧 MIP 和可行性容差后归于数值零。最终分步优化结果的差异与主目标界在表 24 分别报告。逐点求解一致性不赋予统计推断。

样式与轴范围可参照同目录 `axes_reference.json`；定量坐标核对见包根目录 `audit/PANEL_VERIFICATION.json`。

## 直接重绘本图

在本文件夹运行 `python redraw.py`，或在包根目录运行 `python DRAW_SUPPLEMENT.py --figures S10`。程序直接读取本文件夹的CSV；只改样式时修改包根目录的 `DRAW_SUPPLEMENT.py`。首次运行需按总说明安装依赖。输出存入包根目录 `MY_REDRAW`，保留参考图。

本目录PDF/PNG/SVG是论文采用的图稿。重绘程序提供同数据的可修改模板，字体、图例与布局可与参考图有差异。Excel是同一份数据的便利副本；若在Excel中改数，请将对应工作表另存为同名CSV后运行，程序不直接读取Excel。
