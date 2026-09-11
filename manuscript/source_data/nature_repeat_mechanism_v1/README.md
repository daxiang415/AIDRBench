# 重复调用机制扩展的完整数据

现成绘图表为 confirmation_summary.csv、paired_controller_contrasts.csv、selected_offers.csv、economic_primary.csv。直接重绘无需运行模拟或重新做统计。

development/confirmation_ledgers.csv 保存每个完整情景的结果与全时域账本；对应 events.csv 保存每次调用的各项判断。hourly_full/ 是全部原始列与配对基准的完整 Parquet；hourly_plot_csv/ 为可直接打开的完整逐小时绘图列；ready_hourly_curves.csv 已给出逐小时均值、中位数及第 5、95 百分位。百分位描述情景离散性，不是置信区间。

recovery_inputs/ 直接保存全部 2,000 套单情景输入，包含完整作业、期限、社区、基准和配置，不需要下载生产原始数据或重新抽样。protocol.json 与 selection.json 定义事件时刻、实际时长、请求及控制器。运行驱动显式覆盖配置中默认事件时长；每条轨迹再次核对实际时长。

controller_audit/ 保存全部窗口控制器的逐小时上限与是否进一步限功率。illustration_*.csv 为按公开规则选择的开发情景示例，仅用于解释机制，不参与新的确认统计。

开发种子 930000–930099，独立确认种子 970000–970299。每个种子的一整条四调用序列是一个独立统计单位。候选选值只用开发结果，确认失败不被删除。价格是声明参数下的条件性参与门槛，失败方案的价格不表示可以实际报价。
