# 五档工作资格的完整绘图数据

主配置：f05、f10、f20、f40、f60 对应总投入工作中 5%、10%、20%、40%、60% 获准延后。前三档保持生产摘要的类别构成；40% 需要几乎全部批处理参与；60% 改变在线/离线业务构成。任何配置都没有延后在线推理。

## 直接绘图，不需重新计算

| 图 | 现成数据 |
|---|---|
| 主图 1 | source_audit.json、case_definitions.json、source_mix_by_class_priority.csv |
| 主图 2 | pi_boundaries.csv、single_confirm_summary.csv、notice_paired_comparisons.csv |
| 主图 3 | repeat_paired_comparisons.csv、repeat_dev_summary.csv、repeat_selected.csv |
| 主图 4 | renewable_paired_comparisons.csv、renewable_scenarios.csv |
| 主图 5 | control_pi_boundaries.csv、control_causal_summary.csv、economic_primary.csv |
| 主图 6 | economic_primary.csv、economic_price_sensitivity.csv |
| 补充图 1 | 框架示意图由绘图脚本中的声明流程生成，无虚构观测点 |
| 补充图 2 | calibration_run_means.csv、calibration_class_summary.csv |
| 补充图 3 | ready_hourly_curves.csv |
| 补充图 4 | control_causal_summary.csv、renewable_paired_comparisons.csv |
| 补充图 5 | economic_price_sensitivity.csv、reserve_life_sensitivity.csv |

## 全部底层结果

- `all_trial_event_outcomes.csv`：所有开发/确认试验的逐事件结果及全部失败原因；单次和重复调用使用相同电气/服务标准。
- `hourly_full/`：所有开发与确认试验的完整小时 Parquet，保留原记录的全部列，并添加配对无响应量与明确的额外队列指标。
- `hourly_plot_csv/`：同样完整的逐小时绘图列，CSV 可直接读取；数据没有按成功与否筛选。
- `hourly_partition_index.csv`：每组路径、场景数、行数和列数。
- `ready_hourly_curves.csv`：已经算好的均值、中位数、第 5/95 百分位。重复方案保留四次调用及全部清空尾段；其他曲线提供所有种子共同覆盖的事件对齐窗口，完整小时仍在上述文件中。
- `pi_scenarios.csv` 与 `control_pi_scenarios.csv`：所有逐情景规划最优值；`pi_boundaries.csv` 是由这些值计算的容忍下界。
- `single_confirmation_ledgers.csv`、`repeated_confirmation_ledgers.csv`、`control_confirmation_ledgers.csv`：完整情景经济量，不以成功筛选。
- `renewable_scenarios.csv`、`control_renewable_scenarios.csv`：全部优化结果，包括状态及服务检验；配对表区分均值效应与两个全情景最小值之差。
- `recovery_inputs/`：400 份未删除作业记录的共同模板、精确类别乘数、3,200 份原情景元数据及各自配置/基准；用于审核作业时序和恢复模拟，日常画图不需物化这些输入。

## 统计口径与单位

独立单位是 scenario_seed，不是一次调用、一条小时记录或一个重复试验次数。PI 下界针对 95% 可靠性，置信度至少 95%，100 个情景取第二顺序统计量。控制器成功率附单侧 95% Wilson 下界，300 个确认种子；各项资格是逐项结论。重复方案和四个新事件组合均要求四次全部通过。配对变化的自助区间按完整种子抽样。

`capacity_kw` / `offered_kw` 是指定配置的承诺功率。`operating_peak_kw` 是该配置的模型运行峰值。`accounting_scale_factor = 1000 / operating_peak_kw`，`accounting_offered_kw` 是按 1 MW 峰值比例换算后的承诺，不是 1 MW 技术认证。价格单位是每会计承诺 kW 每年的美元。`qualified` 仅表示所在表的单侧 Wilson 下界达到 0.95，经济表中具体指确认集标准。四小时原重复承诺均通过确认，但全部重复候选均未通过另行开展的开发选值规则；两项结果必须分开解读。`qualified=False` 时，条件成本不能当作合格报价。`repeated_original` 是原单次承诺用于重复方案；`repeated` 只在另有开发选出候选时存在。零选择容量意味着网格内无合格开发候选，不是真实容量等于零。

工作量 GPU-h、积压 GPU-h、等待暴露 GPU-h²、功率 kW、能量 kWh 分开记录。`compute_debt_kwh` 是历史命名的总受控队列能量，`excess_queue_energy_kwh` 才显式减去配对无响应值。`p05` / `p95` 是场景分布的描述性分位数，不是均值置信区间。`recovery_time_h` 为空表示窗口内未解决，不能填成零。

`nominal_flexibility_fraction` 等 PI 导出兼容列保留旧程序的报告比较值，并未约束优化器；当前图件不以该假定替代作业资格。原先 75% 配置和错误的一小时重复诊断没有混入当前数据。400 个完整模板含 100 开发和 300 确认种子；原始第三方完整生产发布从其官方来源获取，本包不将合成期限称为生产 SLA。

储能求解保留 HiGHS 1.15.1 默认相对 MIP 间隙 10⁻⁴，词典序锁定 10⁻⁵ kWh 并不代替最优性容差。微小的有储能利用率正负差异可能处在约 0.01 个百分点的数值分辨尺度内；保留原值但不解释为确定收益或物理损失。配对自助区间仅包括情景抽样，不包含优化误差。

公开归档 DOI 和作者选择的许可证仍待确认。文件校验见 FILE_MANIFEST.csv；全包另有 SHA256SUMS.txt。
