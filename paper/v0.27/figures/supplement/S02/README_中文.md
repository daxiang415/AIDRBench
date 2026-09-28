# S2：训练与离线推理的 GPU 板卡功率测量、参数拟合和留出验证

当前投稿补充图；独立交接包 2026-09-17，数值与现有SI一致。 [PDF](AIDRBench_Supplementary_Figure_2.pdf) · [PNG](AIDRBench_Supplementary_Figure_2.png) · [可编辑SVG](AIDRBench_Supplementary_Figure_2.svg) · [直接取数Excel](S02_READY.xlsx)

以下每张CSV已经按当前面板选好行、完成图中换算。先按说明选X/Y列；不需要从旧源表再次筛选、聚合或计算。只修改视觉呈现时保留所有表中数值。

## S02a：所有板卡级运行均值，保留拟合/留出标签与原图横向错位。

[CSV](S02a.csv)，30行。

X=x_position，Y=board_power_w；calibration_role列中fit实心、held_out空心。分类刻度0训练1GPU、1训练4GPU、2离线1GPU、3离线4GPU。没有误差条。

原图轴名：X = 无；Y = Board power (W/GPU)。

| 图形/分组 | X列 | Y列 | 区间或堆叠起点 |
| --- | --- | --- | --- |
| All board means (points) | x_position | board_power_w | 无 |

原图X刻度（位置→文字）：0→Train / 1 GPU；1→Train / 4 GPUs；2→Offline / 1 GPU；3→Offline / 4 GPUs

## S02b：功率系数及95% Student t区间。

[CSV](S02b.csv)，2行。

X=x_position，Y=estimate_w_per_gpu；上下误差长度分别为error_minus_w、error_plus_w。两次独立四GPU运行均值用于拟合；不是四块板卡作为独立重复。

原图轴名：X = 无；Y = Active coefficient (W/GPU)。

| 图形/分组 | X列 | Y列 | 区间或堆叠起点 |
| --- | --- | --- | --- |
| Active coefficients (errorbar) | x_position | estimate_w_per_gpu | 下端点 interval_lower_w_per_gpu；上端点 interval_upper_w_per_gpu |

原图X刻度（位置→文字）：0→Training；1→Offline inference

## 当前完整图注

### Supplementary Figure 2 | GPU board-power measurements, calibration and held-out validation for training and offline inference

**a,** All 30 per-board run averages from one- and four-GPU training and offline inference. Filled points are fitting runs 1–2; open points are held-out run 3. Boards in one run are not independent replicates. **b,** Active-power estimates and 95% Student-t intervals from two independent four-GPU run means per class. Held-out overall MAE is 3.80 W/GPU. Node overhead and online-serving power were not measured by this calibration.

### 补充图 2 | 训练与离线推理的 GPU 板卡功率测量、参数拟合和留出验证

**a，**单 GPU 与四 GPU 训练及离线推理的全部 30 个逐板卡运行均值。实心点为拟合运行 1–2，空心点为留出运行 3。同次运行中的板卡不是独立重复。**b，**各类两个独立四 GPU 运行均值所得的活动功率估计及 95% Student-t 区间。整体留出 MAE 为每 GPU 3.80 W。本校准未测量节点开销或在线服务功率。

样式与轴范围可参照同目录 `axes_reference.json`；定量坐标核对见包根目录 `audit/PANEL_VERIFICATION.json`。

## 直接重绘本图

在本文件夹运行 `python redraw.py`，或在包根目录运行 `python DRAW_SUPPLEMENT.py --figures S2`。程序直接读取本文件夹的CSV；只改样式时修改包根目录的 `DRAW_SUPPLEMENT.py`。首次运行需按总说明安装依赖。输出存入包根目录 `MY_REDRAW`，保留参考图。

本目录PDF/PNG/SVG是论文采用的图稿。重绘程序提供同数据的可修改模板，字体、图例与布局可与参考图有差异。Excel是同一份数据的便利副本；若在Excel中改数，请将对应工作表另存为同名CSV后运行，程序不直接读取Excel。
