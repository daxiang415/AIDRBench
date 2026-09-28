# S1：生产记录与功率测量进入响应资格检验、光伏分析和经济核算的流程

当前投稿补充图；独立交接包 2026-09-17，数值与现有SI一致。 [PDF](AIDRBench_Supplementary_Figure_1.pdf) · [PNG](AIDRBench_Supplementary_Figure_1.png) · [可编辑SVG](AIDRBench_Supplementary_Figure_1.svg) · [直接取数Excel](S01_READY.xlsx)

以下每张CSV已经按当前面板选好行、完成图中换算。先按说明选X/Y列；不需要从旧源表再次筛选、聚合或计算。只修改视觉呈现时保留所有表中数值。

## S01a：示意面板的原始文字和布局坐标。

[CSV](S01a.csv)，4行。

这是概念图，没有实测曲线或可统计的数值。text为原图文字；x_canvas/y_canvas仅为画布布局。直接修改同文件夹的SVG，可完整保留箭头、机架、方框与任务条。不要把示意长度当作测量值。

## S01b：示意面板的原始文字和布局坐标。

[CSV](S01b.csv)，4行。

这是概念图，没有实测曲线或可统计的数值。text为原图文字；x_canvas/y_canvas仅为画布布局。直接修改同文件夹的SVG，可完整保留箭头、机架、方框与任务条。不要把示意长度当作测量值。

## 当前完整图注

### Supplementary Figure 1 | From production records and power measurements to response qualification, solar analysis and economic accounting

**a,** Observed workload shares and the assumed permission to defer tasks determine the synthetic job templates and GPU allocation. An hourly queue then tracks arrivals, execution and deadlines, and the power model combines data-centre and community demand at the PCC. **b,** Development simulations select a request; a separate confirmation set tests it. Hourly operating records supply the participation-cost calculation. Solar and storage planning is a separate optimisation with full future information. Arrows indicate inputs passed between calculations.

### 补充图 1 | 生产记录与功率测量进入响应资格检验、光伏分析和经济核算的流程

**a，** 观测工作组成和设定的延期许可共同确定合成任务模板及 GPU 分配。逐小时队列记录任务到达、执行与期限，功率模型再把数据中心和社区需求合并到 PCC。**b，** 开发模拟先选择请求，再用独立确认集检验。逐小时运行记录用于计算参与成本。光伏与储能属于另一项掌握完整未来信息的规划优化。箭头表示不同计算之间传递的输入。

样式与轴范围可参照同目录 `axes_reference.json`；定量坐标核对见包根目录 `audit/PANEL_VERIFICATION.json`。

## 直接重绘本图

在本文件夹运行 `python redraw.py`，或在包根目录运行 `python DRAW_SUPPLEMENT.py --figures S1`。程序直接读取本文件夹的CSV；只改样式时修改包根目录的 `DRAW_SUPPLEMENT.py`。首次运行需按总说明安装依赖。输出存入包根目录 `MY_REDRAW`，保留参考图。

本目录PDF/PNG/SVG是论文采用的图稿。重绘程序提供同数据的可修改模板，字体、图例与布局可与参考图有差异。Excel是同一份数据的便利副本；若在Excel中改数，请将对应工作表另存为同名CSV后运行，程序不直接读取Excel。
