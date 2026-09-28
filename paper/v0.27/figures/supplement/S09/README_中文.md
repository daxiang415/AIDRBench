# S9：参考工作负载与八个观测周分布下的报价选择及独立交付资格检验

当前投稿补充图；独立交接包 2026-09-17，数值与现有SI一致。 [PDF](AIDRBench_Supplementary_Figure_9.pdf) · [PNG](AIDRBench_Supplementary_Figure_9.png) · [可编辑SVG](AIDRBench_Supplementary_Figure_9.svg) · [直接取数Excel](S09_READY.xlsx)

以下每张CSV已经按当前面板选好行、完成图中换算。先按说明选X/Y列；不需要从旧源表再次筛选、聚合或计算。只修改视觉呈现时保留所有表中数值。

## S09a：参考工作负载两种时长产品的独立确认。

[CSV](S09a.csv)，2行。

X=x_success_1pct/x_success_zero，Y=对应fraction；仅向下误差长度error_minus，上误差0。Y=.95参考线。capacity_kw是点上方容量标注。

原图轴名：X = 无；Y = Success fraction and lower bound。

| 图形/分组 | X列 | Y列 | 区间或堆叠起点 |
| --- | --- | --- | --- |
| success_1pct (errorbar) | x_success_1pct | success_1pct_fraction | 下端点 success_1pct_lower；上端点 success_1pct_fraction |
| success_zero (errorbar) | x_success_zero | success_zero_fraction | 下端点 success_zero_lower；上端点 success_zero_fraction |

原图X刻度（位置→文字）：0→Four hours；1→Eight hours

## S09b：八周经验分布上的开发网格。

[CSV](S09b.csv)，9行。

X=request_kw；四条Y为两个权重×两个成功标准的Wilson单侧下界。圆点实线1%，方点虚线零漏期。Y=.95参考线；仅连接已测试点。

原图轴名：X = Tested request (kW)；Y = Development Wilson lower bound。

| 图形/分组 | X列 | Y列 | 区间或堆叠起点 |
| --- | --- | --- | --- |
| job_count success_1pct (points) | request_kw | job_count_success_1pct_lower | 无 |
| job_count success_zero (points) | request_kw | job_count_success_zero_lower | 无 |
| resource_gpu_h success_1pct (points) | request_kw | resource_gpu_h_success_1pct_lower | 无 |
| resource_gpu_h success_zero (points) | request_kw | resource_gpu_h_success_zero_lower | 无 |

## S09c：八周经验分布上两种已选容量与固定比较请求的确认。

[CSV](S09c.csv)，3行。

X分别用两个x_标准列，Y=对应fraction，单侧误差如S09a。三类依次为次数2.95已选、资源时间1.47已选、资源时间2.95固定比较。

原图轴名：X = 无；Y = Success fraction and lower bound。

| 图形/分组 | X列 | Y列 | 区间或堆叠起点 |
| --- | --- | --- | --- |
| success_1pct (errorbar) | x_success_1pct | success_1pct_fraction | 下端点 success_1pct_lower；上端点 success_1pct_fraction |
| success_zero (errorbar) | x_success_zero | success_zero_fraction | 下端点 success_zero_lower；上端点 success_zero_fraction |

原图X刻度（位置→文字）：0→Counts: 2.95 kW / Selected；1→Resource-time: 1.47 kW / Selected；2→Resource-time: 2.95 kW / Fixed comparator

## 当前完整图注

### Supplementary Figure 9 | Offer selection and independent delivery qualification under reference workloads and the eight-week empirical distribution

**a,** Independent confirmation of the reference four- and eight-hour offers, 5.60 and 4.42 kW, with 300 scenarios each. **b,** Development lower bounds for all candidate requests under submission-count and task-resource-time weighting, using 100 new model draws per point. Solid circles use the 1% missed-work criterion and dashed squares use zero missed work. Both criteria select the same offer within each weighting scheme. **c,** Independent confirmation of those selected offers and the fixed 2.95-kW resource-time comparator, with 300 new draws each. Points show success fractions and lower whiskers the one-sided 95% Wilson bounds; the dashed line is the 0.95 qualification threshold. Panels b,c draw from an equal mixture of eight fixed observed weeks, with paired synthetic tasks and call phases. The calls last eight hours and start 16 h apart. Panel a uses a separate reference workload distribution; model draws in b,c do not add observed production weeks.

### 补充图 9 | 参考工作负载与八个观测周分布下的报价选择及独立交付资格检验

**a，** 参考四小时和八小时报价 5.60、4.42 kW 的独立确认，每种使用 300 个情景。**b，** 按提交数量和按任务资源时间加权时，全部候选请求在开发集上的概率下界，每个点使用 100 次新模型抽样。实线圆点采用 1% 漏期标准，虚线方点采用零漏期标准；同一加权方式下，两种标准选中的报价相同。**c，** 这些已选报价及资源时间加权下固定 2.95 kW 对照的独立确认，每组使用 300 次新抽样。点为成功比例，下方误差线为单侧 95% Wilson 下界，虚线为 0.95 资格门槛。b,c 从八个固定观测周的等权混合分布抽样，任务模板和调用时刻配对；调用持续八小时，开始间隔 16 h。a 使用另一种参考工作负载分布；b,c 的模型抽样没有增加实际观测周数。

样式与轴范围可参照同目录 `axes_reference.json`；定量坐标核对见包根目录 `audit/PANEL_VERIFICATION.json`。

## 直接重绘本图

在本文件夹运行 `python redraw.py`，或在包根目录运行 `python DRAW_SUPPLEMENT.py --figures S9`。程序直接读取本文件夹的CSV；只改样式时修改包根目录的 `DRAW_SUPPLEMENT.py`。首次运行需按总说明安装依赖。输出存入包根目录 `MY_REDRAW`，保留参考图。

本目录PDF/PNG/SVG是论文采用的图稿。重绘程序提供同数据的可修改模板，字体、图例与布局可与参考图有差异。Excel是同一份数据的便利副本；若在Excel中改数，请将对应工作表另存为同名CSV后运行，程序不直接读取Excel。
