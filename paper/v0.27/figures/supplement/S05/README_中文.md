# S5：等待与漏期成本估值、接入费用对四小时和八小时响应服务选择的影响

当前投稿补充图；独立交接包 2026-09-17，数值与现有SI一致。 [PDF](AIDRBench_Supplementary_Figure_5.pdf) · [PNG](AIDRBench_Supplementary_Figure_5.png) · [可编辑SVG](AIDRBench_Supplementary_Figure_5.svg) · [直接取数Excel](S05_READY.xlsx)

以下每张CSV已经按当前面板选好行、完成图中换算。先按说明选X/Y列；不需要从旧源表再次筛选、聚合或计算。只修改视觉呈现时保留所有表中数值。

## S05a：等待估值为零时两产品年净值之差。

[CSV](S05a.csv)，152行。

X=equal_capacity_price，Y=annual_value_8h_minus_4h_usd。保留程序输入的全部点；原图视窗X=0–75，Y=-330–220。Y=0与X≈25.57交点作说明。

原图轴名：X = Equal capacity price (USD / kW-year)；Y = Annual value: eight minus four hours (USD)。

| 图形/分组 | X列 | Y列 | 区间或堆叠起点 |
| --- | --- | --- | --- |
| Annual value difference (points) | equal_capacity_price | annual_value_8h_minus_4h_usd | 无 |

## S05b：漏期工作估值0/1 USD/GPU-h的重复产品门槛。

[CSV](S05b.csv)，2行。

两组柱，X和Y按missed_price_0/1对应。单位USD/报价kW·年；失败轨迹已保留。

原图轴名：X = 无；Y = Threshold (USD per offered kW-year)。

| 图形/分组 | X列 | Y列 | 区间或堆叠起点 |
| --- | --- | --- | --- |
| Missed-work price 0 (bar) | x_missed_price_0 | threshold_missed_price_0 | 无 |
| Missed-work price 1 (bar) | x_missed_price_1 | threshold_missed_price_1 | 无 |

原图X刻度（位置→文字）：0→Four hours / 5.60 kW；1→Eight hours / 4.42 kW

## S05c：三种固定费用下的年净值第五百分位。

[CSV](S05c.csv)，3行。

X=x_4h/x_8h，Y=两列net，已经除以1000，单位千美元。柱允许负值。

原图轴名：X = 无；Y = Annual net-value q05 (1,000 USD)。

| 图形/分组 | X列 | Y列 | 区间或堆叠起点 |
| --- | --- | --- | --- |
| 4 h (bar) | x_4h | net_4h_thousand_usd | 无 |
| 8 h (bar) | x_8h | net_8h_thousand_usd | 无 |

原图X刻度（位置→文字）：0→No fee；1→Shared / USD 2,500；2→Full / USD 25,000

## S05d_fee0：固定费用为0美元时的解析产品选择边界。

[CSV](S05d_fee0.csv)，302行。

X=price_4h，Y=required_price_8h；三份fee文件分别画一条线，已包含相应拐点，无需计算公式。原图X视窗0–1500。

原图轴名：X = Four-hour price (USD / kW-year)；Y = Required eight-hour price
(USD / kW-year)。

| 图形/分组 | X列 | Y列 | 区间或堆叠起点 |
| --- | --- | --- | --- |
| Fee 0 (points) | price_4h | required_price_8h | 无 |

## S05d_fee2500：固定费用为2500美元时的解析产品选择边界。

[CSV](S05d_fee2500.csv)，302行。

X=price_4h，Y=required_price_8h；三份fee文件分别画一条线，已包含相应拐点，无需计算公式。原图X视窗0–1500。

原图轴名：X = Four-hour price (USD / kW-year)；Y = Required eight-hour price
(USD / kW-year)。

| 图形/分组 | X列 | Y列 | 区间或堆叠起点 |
| --- | --- | --- | --- |
| Fee 2500 (points) | price_4h | required_price_8h | 无 |

## S05d_fee25000：固定费用为25000美元时的解析产品选择边界。

[CSV](S05d_fee25000.csv)，302行。

X=price_4h，Y=required_price_8h；三份fee文件分别画一条线，已包含相应拐点，无需计算公式。原图X视窗0–1500。

原图轴名：X = Four-hour price (USD / kW-year)；Y = Required eight-hour price
(USD / kW-year)。

| 图形/分组 | X列 | Y列 | 区间或堆叠起点 |
| --- | --- | --- | --- |
| Fee 25000 (points) | price_4h | required_price_8h | 无 |

## 当前完整图注

### Supplementary Figure 5 | Four- versus eight-hour service choice under waiting and missed-work valuations and access fees

**a,** Difference in fifth-percentile annual net value between the eight- and four-hour products when capacity prices are equal and waiting and access fees are zero. Zero marks equal value for the two participating products. **b,** Required compensation when missed work is valued at zero or US$1/GPU-h, with the reference waiting price and zero site fee. These refined offers were qualified using zero missed work as the success criterion, but qualification permits occasional failed scenarios; their costs remain included. **c,** Fifth-percentile annual net value at US$250/kW-year and the reference waiting price, with zero, shared or full access fees. **d,** Eight-hour price needed to be at least as valuable as both four-hour participation and not participating. All panels use 300 confirmation sequences, 10% eligible work, 65% offered utilisation, reference deadlines and 16-h start spacing. Annual accounting and energy prices follow Fig. 6. Fee sharing adds no assumption about pooled reliability.

### 补充图 5 | 等待与漏期成本估值、接入费用对四小时和八小时响应服务选择的影响

**a，** 容量价格相同、等待价格和接入费均为零时，八小时产品减去四小时产品的年度净收益第五百分位；零表示两种参与产品价值相同。**b，** 漏期工作按零或每 GPU-h 1 美元计价时的补偿门槛，采用参考等待价格、零场站费。这些细网格报价以零漏期作为成功要求通过资格检验，但仍可能出现少量失败情景，其成本继续计入。**c，** 容量价格为每 kW 每年 250 美元、采用参考等待价格时，零、共享或全额接入费下的年度净收益第五百分位。**d，** 八小时产品要同时不劣于“四小时参与”和“不参与”，至少需要多高的价格。全部面板使用 300 条确认序列，固定 10% 工作允许延期、65% 工作供给利用率、参考期限和 16 h 开始间隔。年度核算和能源价格同图 6；费用分摊没有附加聚合可靠性假设。

样式与轴范围可参照同目录 `axes_reference.json`；定量坐标核对见包根目录 `audit/PANEL_VERIFICATION.json`。

## 直接重绘本图

在本文件夹运行 `python redraw.py`，或在包根目录运行 `python DRAW_SUPPLEMENT.py --figures S5`。程序直接读取本文件夹的CSV；只改样式时修改包根目录的 `DRAW_SUPPLEMENT.py`。首次运行需按总说明安装依赖。输出存入包根目录 `MY_REDRAW`，保留参考图。

本目录PDF/PNG/SVG是论文采用的图稿。重绘程序提供同数据的可修改模板，字体、图例与布局可与参考图有差异。Excel是同一份数据的便利副本；若在Excel中改数，请将对应工作表另存为同名CSV后运行，程序不直接读取Excel。
