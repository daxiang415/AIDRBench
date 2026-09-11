# 数据字段与直接绘图入口

本目录为 v0.21 的重复调用机制扩展；上一级原五档结果仍支撑单次事件、光伏与独立敏感性。所有统计量和绘图坐标已给出，无需预处理。

| 文件 | 直接用途 |
|---|---|
| confirmation_summary.csv | 图 3a：同请求成功率、Wilson 下界；所有失败类别计数 |
| selected_offers.csv | 图 3c、S3d：开发选值；空值是未选出，不是零容量 |
| paired_controller_contrasts.csv | 配对差异、95% 区间、挽救/损失计数及 Holm 校正 P |
| illustration_*.csv / illustration_windows.csv | 图 3b 的固定开发示例，完整小时值与每次窗口上限 |
| economic_primary.csv / economic_sensitivity.csv | 图 6c 和补充表：完整账本对应的报价门槛 |
| ready_hourly_curves.csv | 图 S3a,b：全部情景的小时均值、中位数及第 5/95 百分位 |
| development_summary.csv | 图 S3c：全额请求的开发失败类型；不与确认集合并 |
| hourly_partition_index.csv | 每个控制器/比例/情景组的完整 Parquet 与 CSV 相对路径 |
| recovery_input_index.csv | 每个冻结输入文件夹的相对路径与身份 |

case 为 f05/f10/f20/f40/f60，指允许延期的工作 GPU 小时比例。program 如 H8G12 表示八小时调用、两次调用之间空隙十二小时，共四次。controller 区分 original、all_window_mpc、all_window_greedy。fraction 是相对于既有单次事件承诺的请求比例，绝不是可延后工作比例。capacity_kw 为实际请求 kW。role 区分开发与确认。scenario_seed/seed 配对完整 216 小时情景，不把四次调用视为四个独立样本。

successes/trials 是整组成功次数/情景数；success_fraction 是观测比例；wilson_lower 是单侧 95% Wilson 成功概率下界；qualified 要求下界至少 0.95。每组必须四次调用全部满足六项原标准。failures_* 是至少一次该项失败的情景数，类别可重叠。failure_* 是逐情景或逐调用布尔标记。difference_pp 和 ci_*_pp 单位为百分点，后者是完整种子的配对 bootstrap 区间。Holm P 在全部 16 个控制器对比中校正；资格下界仍为逐项结果。

selected_by_development 与 confirmation_qualified 必须分开读取。offerable_selected_option 同时要求两者成立。全额八小时/十二小时间隔新控制器虽然在确认中达到 294/300，但开发未选中；不可用它覆盖已冻结的 75% 选值。

payment_usd_kw_year 是每个报价核算千瓦的年度补偿门槛：在自身运行峰值按比例扩大到 1 MW 后，年度净成本第 95 百分位除以对应报价千瓦。它不是实测报价，也不是均值置信限。annual_series=12，全部情景包括失败均进入共同年度抽样。waiting_price 是美元/GPU-h/h；site_cost 是美元/年；displaced_value 是美元/延后 GPU-h；regime 区分现有余量、预留容量与假设被挤出价值。

hourly_full/ 保存原始全部小时字段，并增加对应无响应基准、情景身份、超额积压和累计错过期限工作。基准由相同输入直接提供。paired_baseline_* 是基准数值，excess_backlog_gpu_h 是有响应减无响应排队工作，paired_compute_debt_kwh 是相同差值的能量口径。incremental_power_kw 为有响应减无响应 PCC 功率，可为负。cumulative_missed_gpu_h 先在每条轨迹内逐小时累加，再求分位数；低于 1% 期限损失标准并不意味着绝对损失为零。hourly_plot_csv/ 包含全部小时，不抽样；ready_hourly_curves.csv 的 mean/median/p05/p95 对 metric 所指列计算，百分位为情景分散性，不是均值的置信区间。

controller_audit/ 保存 observed_active_windows、target_pcc_kw、proposed_fraction、guarded_fraction、additional_cap_active、target_below_fixed_power。它们分别表示当前存续窗口数、合并功率上限、提议/最终分配、是否额外限幅、目标是否低于不可调功率。非事件/恢复时 target_pcc_kw 为空值（无附加限制）。部分按类别的到达/执行字段在无该类活动时为结构性空值；重跑验证同时比较数值与空值位置，不能把空值任意填零后声称原始结果一致。

冻结 selection.json 的 confirmation_not_yet_run 记录的是选值冻结当时的状态，不能作为当前执行状态；当前完成状态见 export_receipt.json 和论文修订目录 PROGRESS.json。trace_path/receipt_path 是原计算的溯源绝对路径；重画与恢复应使用本目录相对路径索引。全部代码、绘图入口和无需原始生产数据的单情景重跑示例随完整包交付。
