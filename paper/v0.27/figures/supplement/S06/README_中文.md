# S6：利用率、任务期限、GPU 分配与调用安排变化下的响应交付和按期完成情况

当前投稿补充图；独立交接包 2026-09-17，数值与现有SI一致。 [PDF](AIDRBench_Supplementary_Figure_6.pdf) · [PNG](AIDRBench_Supplementary_Figure_6.png) · [可编辑SVG](AIDRBench_Supplementary_Figure_6.svg) · [直接取数Excel](S06_READY.xlsx)

以下每张CSV已经按当前面板选好行、完成图中换算。先按说明选X/Y列；不需要从旧源表再次筛选、聚合或计算。只修改视觉呈现时保留所有表中数值。

## S06a：1%标准联合成功，每格300场景中的计数。

[CSV](S06a.csv)，8行。

取后三列组成8×3矩阵，行标签row_label；色标0–300，显示整数。列依次为仅末次调用、16h起始间隔四次调用、24h起始间隔四次调用。

原图轴名：X = 无；Y = Utilisation (%) / deadline / GPU share (%)。

| 图形/分组 | X列 | Y列 | 区间或堆叠起点 |
| --- | --- | --- | --- |
| successes (matrix) | — | — | 热图列：fresh_last_call, repeated_16h, repeated_24h |

原图X刻度（位置→文字）：0→Fresh / last call；1→Four calls / 16-h starts；2→Four calls / 24-h starts

原图Y刻度（位置→文字）：0→50 / 1× / 10；1→50 / ½× / 10；2→65 / 1× / 10；3→65 / ½× / 10；4→65 / ½× / 20；5→80 / 1× / 10；6→80 / ½× / 10；7→80 / ½× / 20

## S06b：零漏期标准联合成功，每格300场景中的计数。

[CSV](S06b.csv)，8行。

取后三列组成8×3矩阵，行标签row_label；色标0–300，显示整数。列依次为仅末次调用、16h起始间隔四次调用、24h起始间隔四次调用。

原图轴名：X = 无；Y = Utilisation (%) / deadline / GPU share (%)。

| 图形/分组 | X列 | Y列 | 区间或堆叠起点 |
| --- | --- | --- | --- |
| successes (matrix) | — | — | 热图列：fresh_last_call, repeated_16h, repeated_24h |

原图X刻度（位置→文字）：0→Fresh / last call；1→Four calls / 16-h starts；2→Four calls / 24-h starts

原图Y刻度（位置→文字）：0→50 / 1× / 10；1→50 / ½× / 10；2→65 / 1× / 10；3→65 / ½× / 10；4→65 / ½× / 20；5→80 / 1× / 10；6→80 / ½× / 10；7→80 / ½× / 20

## S06c：即时供给不足，每格300场景中的计数。

[CSV](S06c.csv)，8行。

取后三列组成8×3矩阵，行标签row_label；色标0–300，显示整数。列依次为仅末次调用、16h起始间隔四次调用、24h起始间隔四次调用。

原图轴名：X = 无；Y = Utilisation (%) / deadline / GPU share (%)。

| 图形/分组 | X列 | Y列 | 区间或堆叠起点 |
| --- | --- | --- | --- |
| instantaneous_supply_limited_trials (matrix) | — | — | 热图列：fresh_last_call, repeated_16h, repeated_24h |

原图X刻度（位置→文字）：0→Fresh / last call；1→Four calls / 16-h starts；2→Four calls / 24-h starts

原图Y刻度（位置→文字）：0→50 / 1× / 10；1→50 / ½× / 10；2→65 / 1× / 10；3→65 / ½× / 10；4→65 / ½× / 20；5→80 / 1× / 10；6→80 / ½× / 10；7→80 / ½× / 20

## S06d：超过1%漏期，每格300场景中的计数。

[CSV](S06d.csv)，8行。

取后三列组成8×3矩阵，行标签row_label；色标0–300，显示整数。列依次为仅末次调用、16h起始间隔四次调用、24h起始间隔四次调用。

原图轴名：X = 无；Y = Utilisation (%) / deadline / GPU share (%)。

| 图形/分组 | X列 | Y列 | 区间或堆叠起点 |
| --- | --- | --- | --- |
| failed_deadline_miss (matrix) | — | — | 热图列：fresh_last_call, repeated_16h, repeated_24h |

原图X刻度（位置→文字）：0→Fresh / last call；1→Four calls / 16-h starts；2→Four calls / 24-h starts

原图Y刻度（位置→文字）：0→50 / 1× / 10；1→50 / ½× / 10；2→65 / 1× / 10；3→65 / ½× / 10；4→65 / ½× / 20；5→80 / 1× / 10；6→80 / ½× / 10；7→80 / ½× / 20

## 当前完整图注

### Supplementary Figure 6 | Response delivery and deadline compliance across utilisation, task deadlines, GPU allocation and call schedules

**a,b,** Numbers of scenarios satisfying all delivery and service criteria when the missed-work limit is 1% or zero. **c,d,** Numbers encountering an event-hour supply shortage or more than 1% missed work. Each cell contains 300 confirmation scenarios at 10% work eligibility and the same 5.898243-kW, eight-hour request. Columns compare a separate final call at the matched clock time with four-call sequences starting 16 or 24 h apart. Rows change utilisation, deadline slack and flexible GPU allocation. Each setting has its own matched baseline, and all no-response runs pass service checks. Numerals are counts; blue or orange intensity increases from zero to 300. Failure types can overlap. The fixed request is a common stress test, not a separately selected offer for each row. Changing spacing also moves preceding calls to different times. Tables 14–15 and Source Data retain complete outcomes and selected-offer tests.

### 补充图 6 | 利用率、任务期限、GPU 分配与调用安排变化下的响应交付和按期完成情况

**a,b，** 漏期上限为 1% 或零时，同时满足全部交付和服务条件的情景数。**c,d，** 至少一个调用小时供给不足，或超过 1% 工作漏期的情景数。每格包含 300 个确认情景，固定 10% 工作允许延期和同一个 5.898243 kW、八小时请求。各列比较相同钟点的单独末次调用，以及开始间隔为 16 或 24 h 的四次连续调用。各行改变利用率、期限余量和灵活池 GPU 分配；每种设置使用自身的配对基线，全部无响应运行都通过服务检查。格内数字为计数，蓝色或橙色随零至 300 加深。不同失败可以重叠。同一个固定请求用于施加共同压力，不是逐行重新选出的合格报价。改变间隔还会改变前序调用钟点。表 14–15 和源数据保留完整结果及已选报价的检验。

样式与轴范围可参照同目录 `axes_reference.json`；定量坐标核对见包根目录 `audit/PANEL_VERIFICATION.json`。

## 直接重绘本图

在本文件夹运行 `python redraw.py`，或在包根目录运行 `python DRAW_SUPPLEMENT.py --figures S6`。程序直接读取本文件夹的CSV；只改样式时修改包根目录的 `DRAW_SUPPLEMENT.py`。首次运行需按总说明安装依赖。输出存入包根目录 `MY_REDRAW`，保留参考图。

本目录PDF/PNG/SVG是论文采用的图稿。重绘程序提供同数据的可修改模板，字体、图例与布局可与参考图有差异。Excel是同一份数据的便利副本；若在Excel中改数，请将对应工作表另存为同名CSV后运行，程序不直接读取Excel。
