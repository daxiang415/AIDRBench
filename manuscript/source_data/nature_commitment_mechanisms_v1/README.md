# v0.24：直接绘图与完整恢复数据

本目录保存局部加密、严格时间窗可行性、任务资源时间对照与相应经济性。全部 3,040 次重放、656,640 行小时轨迹和 720 个冻结输入均已包含；成功与失败不筛除。旧数据在完整包的 `03_data/`、`03_data/repeat_mechanism/`、`03_data/operating_tradeoffs/` 保留。

- 直接绘图：根目录 CSV 已经包含逐面板所需数值，见 PANEL_DATA_MAP.csv；完整包 RUN_ALL_FIGURES.py 可一次生成十一图，不用处理生产数据或运行仿真。
- 核对报价：refinement_development_summary.csv、refinement_confirmation_summary.csv 和 refinement_selected_confirmed.csv；每条原始记录在 development_ledgers.csv / confirmation_ledgers.csv 与对应事件表。
- 核对时序：external_cross_score_weekly.csv 为旧 63/80 的交叉评分；weighted_week_summary.csv 为新种子的次数/资源时间配对测试；两套种子不混合。
- 重绘逐时曲线：ready_hourly_curves.csv 已给均值、中位数及情景 p05/p95；hourly_plot_csv/ 保留直接导入的小时字段；hourly_full/ 保存完整原始字段与配对无响应基线。绝对小时未按事件重新对齐。
- 恢复控制轨迹：recovery_inputs/ 保存全部冻结输入；完整包 04_code/commitment_mechanisms/replay_one.py 可重放并验证全部 92 个数值列。H4 事件清单按冻结规则重建并核验场景哈希。
- 可行性：pi_diagnostics/ 包含 38 个诊断、11 个完整可行见证（执行边、各工作组、小时功率），并保留一次超时与延长结果。完整包 replay_pi.py 从旧 operating_tradeoffs 冻结输入重新求解，无需原工作目录。
- 原始依据：production_task_resource_time.parquet、production_job_resource_time.parquet、production_hourly_work.csv 提供完整资源时间重建。resource_time_source_audit.json 记录原始任务/作业文件哈希、精确公式、714,903 个匹配作业和时间原点。

资源时间为请求 GPU 当量乘任务启动至完成时长，不是传感器测量忙碌 GPU 小时。新时序实验仍使用周总量归一、合成类别与期限、流体作业；它不是真实任务检查点/恢复实测，也不是生产 SLA 认证。

经济性见 physical_operating_exposure.csv、refinement_cost_components.csv、refinement_economic_sensitivity.csv、refinement_price_frontier.csv。所有确认账本都参与十二组独立序列的年度核算，不是全年连续运行。价格结果仅适用于参考分布；外部资源时间测试失败的请求不能沿用报价资格。

早期 PI 统计量是累计释放/期限条件下的放松规划界限，不是严格作业可行容量；本目录的 PI 可行性使用每个工作组自身的时间窗。解释与反例见交付包修订说明。
