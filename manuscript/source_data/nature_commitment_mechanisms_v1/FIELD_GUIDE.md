# 字段判读

`fraction` 是 5.898243186 kW 的请求倍数，不是可参与工作比例；本次工作许可始终为 10%。`H8P16` 是八小时调用、开始间隔十六小时、间隙八小时；一组四次调用。

`success_zero` 表示整个场景满足零漏期终点（数值容差 1e−7 GPU-h）及全部原电力/期末标准；基线也要零漏期。概率资格不要求每个确认场景都成功，因此经济账本保留失败。`offerable_zero` 仅指该候选事先为零标准选中并通过新确认，不授予外部负载报价资格。旧已合格对照标为未选中，不表示它们被追认为失败。

`u65d100g10` 表示工作供给利用率 65%、参考期限、10% GPU 分配；d50 为期限余量减半。`w0_resource_gpu_h_chronological_g10` 表示第一个观察周、资源时间加权、原序、10% GPU 分配。

等待暴露单位 GPU-h×h，是相对匹配基线的额外非负积压在时间上的积分。漏期为 GPU-h；能量为 kWh。physical_operating_exposure 表中 `model_series_*` 按一个模型四调用序列统计，`accounting_annual_*` 按 1 MW 比例规模和十二个独立序列统计。p05/p95 为情景分位数，不是均值置信区间。

`accounting_offered_kw` = 模型报价 ×1000/自身模型运行峰值。成本组件在总净成本的 q95 排序位置归因，相加精确还原总量；不能相加组件各自的边际分位数。所有费用为条件性 USD，容量价格为 USD/kW-year。`ready_annual_values.difference` 是两个产品各自年度净值 q05 的差，不是配对净值差的 q05。

PI 分类：`instantaneous_supply_infeasible` 为解析必要条件失败；`model_infeasible` 为通过即时必要条件后的混合整数不可行；`feasible_witness` 为独立检查过的可行调度。原始 `unresolved` 记录不删除，但 pi_diagnostic_resolved.csv 采用保存的延长求解结果。诊断样本不是概率样本，不能用分类频数推断生产总体发生率。

production_task_resource_time 中 instances 为实例数，gpu_pct 为每实例请求 GPU 百分比，start/end 为原始任务启动/完成时间（秒），resource_gpu_seconds 为乘积。作业表 release_time_s 是归零后的提交时间，raw_submission_time_s = release_time_s + 542323。被测试的归零轨迹小时为 168–1511。

完整逐时字段沿用模拟器定义；NaN 保留未定义/未解决的原含义，不填零。其他继承字段见旧完整数据字典。
