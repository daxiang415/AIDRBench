# 字段与判读

`variant=u65d100g10`：工作供给利用率 65%、参考期限余量、灵活 GPU 分配 10%。d50 表示余量减半且至少 1 h。全部新结构情景固定 10% 工作可参与；u 不是实测 GPU 利用率。时序变体包含观察周、chronological/permuted 和 GPU 分配。

`program=H8P16`：8 h 调用，开始间隔 16 h，结束至下次开始的间隙为 8 h。旧表 H8G12 的 G 则直接指间隙。`fraction` 是 5.898243186 kW 参考请求的倍数，不是可延后工作比例。

`kind=fresh`：仅保留相同时刻的最后一次调用；其事件重新编号为 0，`is_target_call=True`。`local_electrical_success` 不包含全局期限和期末积压，但保留逐时/平均交付、反弹和窗口峰值要求。总体 `success_*` 同时包括全局任务服务和无响应基线合格。

`success_zero`：总期限违约可参与工作 ≤1e−7 GPU-h，基线也必须满足，其他标准不变。`success_1pct` 和 `success_01pct` 分别为 1%、0.1%；0.1% 无选值。`qualified` 是该条件单侧 95% Wilson 下界 ≥0.95；`offerable` 另需该终点事先选中。`selected_fraction` 缺失表示开发未选出候选；NaN 不是 0。

`instantaneous_supply_limited_trials`：至少一个活动小时，即使灵活执行归零也不足以满足 95% 交付。它是必要条件诊断；0 次不足不证明全程可行。失败类别非互斥。

能量为 kWh；GPU 工作量为 GPU-h；`delay_exposure_gpu_h_h` 为额外非负队列在时间上的积分（GPU-h×h）。能量与期限违约的增量保留相对无响应基线的符号，等待量则先截为非负再求和。`capped_delivered_energy_kwh` 仅累计事件小时每小时截在 [0,请求] 的交付。

`phase` 决定末次调用开始为 111+phase；输入期 168 h、清空尾段 48 h。`hour` 为整个运行阶段的绝对小时。`controller_audit/` 保留动作建议、所有活动恢复窗口与最终上限，不是生产遥测。

`accounting_offered_kw` = 模型报价 × 1000/本配置运行峰值。`net_operating_annual_q95` 或 `net_operating_cost_annual_q95` 为共同年度抽样净运行成本的第 95 百分位；`*_at_total_q95` 各项加总准确还原它。`payment_per_kw` 为最终非负容量门槛，`unfloored_payment_per_kw` 保留未截断值。

`offerable_success_1pct/zero` 只在对应终点预先选中且通过确认时为真。`required_long_price_vs_short_and_opt_out` 包含不参与的零净值；`required_long_price_if_participating` 只比较两种参与方案。`ready_duration_price_curves.csv` 包含解析转折点与密集价格网格，曲线不依赖稀疏点间假设。

逐时完整字段保持模拟器原名、单位和 NaN 含义；例如未解析恢复时间仍为 NaN，不填零。原字段说明随完整主包 `03_data/COLUMN_DICTIONARY.csv`、`03_data/repeat_mechanism/FIELD_GUIDE.md` 与源代码共同保留。
