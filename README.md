# AIDRBench

**A trace-driven experimental platform for reliable, rebound-aware demand flexibility from AI data centers**
**面向 AI 数据中心可靠需求响应与计算债务评估的实验平台**

> 文档状态：实施规范（implementation specification）
> 版本：v0.3-firm-flexibility
> 日期：2026-08-12
> 目标服务器：Ubuntu 24.04，4 × NVIDIA RTX PRO 6000
> 默认控制步长：1 h；可选扩展：15 min
> 目标论文定位：以科学问题和可交付灵活性为主，平台与算法比较为验证工具

---

## 0. 一句话说明

AIDRBench 不以“PPO 是否优于规则控制”为最终科学问题，而是用于回答：

> **AI 数据中心在真实任务到达、异质期限和连续需求响应事件下，究竟能够向社区可靠承诺多少削峰能力；这种能力会不会因计算任务积压而耗尽，并在事件结束后形成新的反弹峰值。**

平台将训练、离线推理和批处理表示为带 release time、GPU demand、runtime 和 deadline 的可延迟计算；将在线推理、idle power 和其他服务关键负荷表示为刚性负荷。控制器按小时决定柔性计算的执行量，统一比较 No-control、Rule-based、EDF/valley filling、滚动优化/MPC、DQN、PPO 和 SAC。

本版本研究：

- 小时级或 15 min 级 temporal workload shifting；
- community/PCC peak shaving；
- job backlog、deadline、compute debt 和 repeated-event exhaustion；
- event-only reduction 与 post-event rebound；
- 从真实 trace 和四卡服务器测量中推导可交付灵活性；
- 不同控制器在相同数据、约束和评价协议下的表现。

本版本不研究：

- 秒级 frequency regulation；
- GPU DVFS、SM clock 或 power-cap tracking；
- 每秒 GPU 温度、风扇和热动态；
- 配电网节点电压、无功功率和潮流；
- 完整冷冻水、液冷或海水冷却动态；
- 新的安全强化学习理论。

四张 RTX PRO 6000 的作用是标定 AI workload 的平均运行功率、runtime、energy per job/GPU-hour 和暂停恢复开销，而不是作为秒级温控对象。

---

## 1. 科学命题与论文定位

### 1.1 中心命题

论文的中心命题应当是：

> **AI 数据中心的需求响应能力不是固定的“20% 或 30% 灵活负荷”，而是一种由当前任务队列、剩余 slack、历史调度和未来恢复需求共同决定的动态资源。它可以被连续事件耗尽，并可能以 compute debt 和 rebound 的形式把风险转移到事件之后。**

因此，平台的核心输出不是单次事件中的最大削减，而是：

1. 不同事件持续时间下的**可靠可交付灵活性**；
2. 连续事件后的**剩余灵活性**；
3. 任务积压恢复所需的时间；
4. 事件窗口与恢复窗口合并后的真实社区峰值缓解；
5. 静态 flexibility envelope 与 job-derived flexibility 之间的偏差。

### 1.2 论文层级

建议将工作分成两层：

**科学层：**

- 量化 static flexible fraction 是否系统性高估可交付削峰；
- 揭示 compute debt、rebound 和 repeated-event exhaustion；
- 提出可审计的 flexibility certificate；
- 给出跨 workload、社区负荷、deadline 和控制器的稳健结论。

**方法与平台层：**

- 构建 trace-driven Gymnasium 环境；
- 用公开 AI cluster trace 驱动任务到达；
- 用四卡服务器标定 energy model；
- 在统一协议下比较 Rule-based、MPC 和标准 RL；
- 提供可复现的数据处理、训练、评价和绘图命令。

Nature Communications 是目标之一，但不是由“平台 + PPO”自动保证。达到该目标需要中心结论具有跨算法、跨数据集和跨场景的普遍性，并通过严格的 out-of-sample 与不确定性分析支持。

### 1.3 第一篇论文不应如何表述

不建议：

> We propose a reinforcement-learning platform and show that PPO reduces the peak more than rule-based control.

建议：

> We quantify when AI workload flexibility can be contracted as reliable community demand response, and show how compute debt, deadline risk and rebound separate nominal peak reduction from deliverable peak relief.

算法比较是验证这一命题的工具，而不是论文唯一结论。

---

## 2. 现有研究边界与本项目的差异

不能声称“从未有人做过数据中心 workload shifting、需求响应、RL 平台或真实 GPU 灵活性实验”。至少需要明确面对以下相邻工作：

1. 数据中心通过 workload shifting 避开 coincident peak 至少在 2013 年已经被系统研究：
   `https://doi.org/10.1016/j.peva.2013.08.014`

2. SustainDC 已提供 workload scheduling、cooling 和 battery 的数据中心强化学习 benchmark：
   `https://proceedings.neurips.cc/paper_files/paper/2024/hash/b6676756f8a935e208f394a1ba47f0bc-Abstract-Datasets_and_Benchmarks_Track.html`

3. Nature Energy 已在 256-GPU 集群上展示软件编排驱动的 AI 数据中心电网交互能力：
   `https://www.nature.com/articles/s41560-025-01927-1`

4. 2026 年 Nature Communications 已在电力系统规划层使用 firm、pause 和 shift 等标准化 flexibility envelopes：
   `https://www.nature.com/articles/s41467-026-72324-9`

因此，本项目不以“首次提出灵活数据中心”或“首次将 RL 用于数据中心”为卖点。拟验证的差异是：

- 不预先给定固定 flexible fraction；
- 从真实 AI job queue 和服务器测量自下而上推导灵活性；
- 将 deadline miss、terminal backlog、rebound 和 repeated events 纳入同一个可交付性定义；
- 区分 nominal reduction、event-only performance 与 recovery-window-wide peak relief；
- 输出不同持续时间和可靠度下可审计的 flexibility certificate；
- 评估 static envelopes 对社区实际可获得削峰价值的偏差。

在完成系统综述和正式检索前，README 和论文中禁止使用“the first”之类绝对表述。可以使用更稳妥的写法：

> To our knowledge, existing planning envelopes and field demonstrations have not yet established a trace-derived, rebound-adjusted certificate of firm AI workload flexibility under heterogeneous deadlines and repeated demand-response events.

该表述在投稿前仍需通过系统检索重新核实。

---

## 3. 研究问题与可证伪假设

### RQ1：静态 flexibility fraction 是否高估真实可交付能力？

比较：

- static-20%；
- static-30%；
- static-40%；
- 从 job slack、GPU demand、runtime 和 deadline 推导的动态灵活性。

**H1：** 对较长 DR 持续时间、紧 deadline 和高到达强度，固定比例 envelope 会高估满足服务约束后的可交付削峰。

### RQ2：灵活性是否会被连续事件耗尽？

测试单次事件、同日连续事件、多日高峰和恢复时间不足的情景。

**H2：** 第一次事件积累的 compute debt 会降低后续事件的可交付容量；事件间隔越短，剩余灵活性越低。

### RQ3：单次事件表现最好的控制器是否也提供最可靠的长期灵活性？

比较 Rule-based、MPC 和 RL 在：

- event tracking；
- deadline miss；
- rebound；
- terminal backlog；
- out-of-distribution events；
- repeated-event firm flexibility

上的排名。

**H3：** 最大化单次 peak reduction 的控制器不一定具有最高的 reliable deliverable flexibility；部分策略只是把峰值和服务风险转移到事件之后。

### RQ4：四卡实测对 MW 级结论的影响有多大？

比较 fallback power assumptions、median hardware calibration 和 workload-specific calibration。

**H4：** 硬件标定会改变灵活性绝对值，但 compute debt、exhaustion 和 rebound 的主要机制在合理缩放下保持稳定。

所有假设都允许被数据否定。论文不能预设 RL 一定优于 MPC，也不能预设 static flexibility 一定被高估。

---

## 4. Demand response 问题和系统边界

社区和数据中心接在同一个公共连接点（PCC）后：

\[
P_t^{\mathrm{PCC}}
=
P_t^{\mathrm{community}}
-
P_t^{\mathrm{PV}}
+
P_t^{\mathrm{DC}}.
\]

社区、聚合商或合同给出小时级动态功率上限：

\[
P_t^{\mathrm{PCC}}\le \overline P_t^{\mathrm{PCC}}.
\]

也可以给出事件型削减要求：

\[
\Delta P_{e}^{\mathrm{req}},\qquad t\in \mathcal T_e.
\]

数据中心负荷分成：

\[
P_t^{\mathrm{DC}}
=
P_t^{\mathrm{rigid}}
+
P_t^{\mathrm{flex}}.
\]

其中：

- `rigid`：在线推理、idle、控制面、存储、网络和服务关键负荷；
- `flex`：训练、离线推理、批处理和其他可延迟计算。

控制器每个时间步决定本小时执行多少柔性计算：

\[
x_t=\text{executed flexible GPU-hours}.
\]

未执行的工作进入 backlog，不能消失。复杂性集中在 AI workload scheduling，而不是配电网潮流。

本项目可以声称：

- 降低 community PCC peak；
- 减少共享容量或合同容量超限；
- 提供 event-based demand response；
- 量化 AI workload 对社区 peak relief 的贡献。

本项目不能在 V0 中声称：

- 解决节点电压越限；
- 缓解特定线路拥塞；
- 提供 frequency regulation；
- 证明某一真实社区配电网可免扩容。

---

## 5. 核心科学量：compute debt、rebound 和 firm flexibility

### 5.1 Compute debt

令：

- \(A_t\)：本时段新到达的柔性计算量，GPU-h；
- \(X_t\)：本时段实际执行量，GPU-h；
- \(M_t\)：本时段因 deadline 失效的计算量，GPU-h；
- \(B_t\)：尚未完成的 backlog，GPU-h。

则：

\[
B_{t+1}=B_t+A_t-X_t-M_t.
\]

定义 compute debt energy：

\[
D_t^{\mathrm{comp}}
=
B_t\,\bar e_{\mathrm{GPU-h}},
\]

其中 \(\bar e_{\mathrm{GPU-h}}\) 由四卡服务器实测的 workload-energy 参数得到。该量不是额外消耗的能量，而是未来仍需兑现的计算能量义务。

### 5.2 事件内削减

对事件 \(e\)：

\[
\Delta P_{e,t}^{\mathrm{del}}
=
P_{t}^{\mathrm{PCC,baseline}}
-
P_{t}^{\mathrm{PCC,control}},
\qquad t\in\mathcal T_e.
\]

事件平均履约率：

\[
\eta_e^{\mathrm{delivery}}
=
\frac{\sum_{t\in\mathcal T_e}
\min(\Delta P_{e,t}^{\mathrm{del}},\Delta P_e^{\mathrm{req}})}
{|\mathcal T_e|\Delta P_e^{\mathrm{req}}}.
\]

只看该指标会奖励“事件内全停、事件后全补”的策略，因此不能作为唯一结果。

### 5.3 Rebound 与窗口级真实削峰

设事件后的恢复窗口为 \(\mathcal T_e^{\mathrm{post}}\)。定义最大反弹：

\[
P_e^{\mathrm{rebound}}
=
\max_{t\in\mathcal T_e^{\mathrm{post}}}
\left[
P_t^{\mathrm{PCC,control}}
-
P_t^{\mathrm{PCC,baseline}}
\right]_+.
\]

定义包含事件与恢复期的 window-wide peak relief：

\[
\Delta P_e^{\mathrm{window}}
=
\max_{t\in \mathcal W_e}P_t^{\mathrm{PCC,baseline}}
-
\max_{t\in \mathcal W_e}P_t^{\mathrm{PCC,control}},
\]

其中：

\[
\mathcal W_e=\mathcal T_e\cup\mathcal T_e^{\mathrm{post}}.
\]

若 \(\Delta P_e^{\mathrm{window}}\le0\)，说明控制器没有真正降低该窗口的社区峰值，只是移动了峰值。

### 5.4 可靠可交付灵活性

对控制器 \(\pi\)、事件持续时间 \(H\)、候选削减容量 \(c\) 和测试 episode \(\omega\)，定义成功事件：

\[
I_{\pi,\omega}(c,H)=1
\]

当且仅当同时满足：

1. \(\eta^{\mathrm{delivery}}\ge \eta_{\min}\)；
2. deadline miss rate \(\le \epsilon_M\)；
3. rebound ratio \(\le \epsilon_R\)；
4. window-wide peak relief \(\ge \eta_W c\)；
5. terminal backlog excess \(\le \epsilon_B\)；
6. 没有违反柔性 GPU 容量和任务守恒。

经验可靠可交付灵活性定义为：

\[
F_q^{\pi}(H)
=
\sup\left\{
 c:
\frac{1}{N}\sum_{\omega=1}^{N}I_{\pi,\omega}(c,H)\ge q
\right\}.
\]

默认可以报告：

- \(F_{0.90}(1\,\mathrm h)\)；
- \(F_{0.95}(2\,\mathrm h)\)；
- \(F_{0.95}(4\,\mathrm h)\)；
- \(F_{0.99}(1\,\mathrm h)\)。

正式论文不应仅使用样本成功率。候选容量只有在二项分布成功率的单侧置信下界达到 \(q\) 时才被认证。实现可采用 Wilson 或 Clopper-Pearson lower confidence bound，并在配置中固定置信水平。

### 5.5 灵活性耗尽和恢复

定义 fresh-state flexibility 为 \(F_q^{(0)}(H)\)，第 \(k\) 次事件前的 flexibility 为 \(F_q^{(k)}(H)\)。剩余灵活性比例：

\[
\rho_k^{\mathrm{res}}(H)
=
\frac{F_q^{(k)}(H)}{F_q^{(0)}(H)}.
\]

定义 exhaustion：

\[
E_k(H)=1-\rho_k^{\mathrm{res}}(H).
\]

恢复时间定义为事件结束后，backlog 和 slack distribution 回到 pre-event 基线容差范围所需时间：

\[
T_e^{\mathrm{recover}}
=
\min\{\tau:\ |B_{t_e+\tau}-B_e^{\mathrm{base}}|\le \epsilon\}.
\]

### 5.6 静态 envelope 偏差

对固定 flexibility fraction \(\alpha\)：

\[
F^{\mathrm{static}}(H)=\alpha P^{\mathrm{DC,peak}}.
\]

比较：

\[
\mathrm{Bias}_{\alpha}(H)
=
\frac{F^{\mathrm{static}}(H)-F_q(H)}{F_q(H)+\epsilon}.
\]

该指标用于检验规划研究中固定 pause/shift envelope 与 job-derived firm flexibility 之间是否存在系统性偏差。

---

## 6. 数据中心小时功率模型

将数据中心 IT 负荷分为刚性部分和柔性 GPU 池。

### 6.1 刚性部分

\[
P_t^{\mathrm{rigid,IT}}
=
P_t^{\mathrm{inference}}
+
P_t^{\mathrm{other,rigid}}.
\]

V0 可采用三种来源：

1. Alibaba 2026 中 `online_inference` 和高优先级 workload 的小时聚合；
2. 由 trace 分布生成的刚性日负荷曲线；
3. 简单的归一化固定曲线，作为环境开发 fallback。

刚性负荷不受 agent 控制。

### 6.2 柔性 GPU 池

设柔性池有 \(N_{\mathrm{flex}}\) 张 GPU，时间步为 \(\Delta t=1\) h。本小时执行 \(x_t\) GPU-h，则平均 active GPU 数为：

\[
n_t^{\mathrm{active}}=\frac{x_t}{\Delta t},
\qquad
0\le n_t^{\mathrm{active}}\le N_{\mathrm{flex}}.
\]

使用实测的 idle 和 active 平均功率：

\[
P_t^{\mathrm{flex,IT}}
=
N_{\mathrm{flex}}p^{\mathrm{idle}}
+n_t^{\mathrm{active}}
\left(p^{\mathrm{active}}-p^{\mathrm{idle}}\right).
\]

如果不同任务类型的平均功率不同：

\[
P_t^{\mathrm{flex,IT}}
=
N_{\mathrm{flex}}p^{\mathrm{idle}}
+
\sum_c n_{c,t}^{\mathrm{active}}
\left(p_c^{\mathrm{active}}-p^{\mathrm{idle}}\right).
\]

V0 为了保持一维动作，可以先使用 workload-mix 加权后的平均 \(p^{\mathrm{active}}\)。不同任务类别的独立调度放到 V1。

### 6.3 Facility power

\[
P_t^{\mathrm{DC}}
=
\mathrm{PUE}_t
\left(
P_t^{\mathrm{rigid,IT}}+P_t^{\mathrm{flex,IT}}
\right).
\]

V0 默认：

```yaml
pue:
  mode: constant
  value: 1.20
```

环境不需要温度状态。若以后研究气候相关冷却，可把 `PUE_t` 替换成按小时变化的外生序列，但仍不必改动 workload scheduler。

---

## 7. 柔性 workload 表示：deadline buckets

V0 不直接让 agent 从数千个 job 中做组合选择。所有柔性任务被转换成带 deadline 的 GPU-hour，并放入固定的 deadline buckets。

推荐 bucket：

```text
0 h       已到期，当前必须完成
1 h       1小时内到期
2 h       2小时内到期
3 h       3小时内到期
4–6 h
7–12 h
13–24 h
>24 h
```

环境内部始终用 earliest-deadline-first（EDF）从最紧迫 bucket 中扣除 agent 决定的执行量。agent 只决定总执行量，不决定任务排序。

### 7.1 每一步的 bucket 更新

1. 将新到达任务加入与其 slack 对应的 bucket；
2. agent 给出本小时执行量 \(x_t\)；
3. 按 EDF 顺序从 bucket 中扣除 \(x_t\)；
4. 未完成的 `0 h` bucket 记为 deadline miss；
5. 所有剩余 bucket 向前移动一档；
6. 进入下一小时。

伪代码：

```python
arrivals = scenario.arrivals[t]
buckets.add(arrivals)

requested_work = action_to_gpu_hours(action)
executed = buckets.serve_edf(min(requested_work, flex_capacity_gpu_h))

missed = buckets.expire_zero_bucket()
buckets.shift_one_hour()
```

### 7.2 为什么选择 fluid workload

V0 允许一个大任务被表示为跨小时执行的 GPU-hour，因此是 preemptive / fluid approximation。它的优点是：

- 环境非常稳定；
- MPC 可以写成 LP；
- RL 动作空间是一维；
- 易于检查计算守恒；
- 适合先验证社区调峰可行性。

V1 再加入：

- non-preemptive jobs；
- gang scheduling；
- checkpoint overhead；
- 多种 GPU 类型；
- job-level action masking。

---

### 7.3 两种内部模式：bucket mode 与 job-level mode

平台应同时保留两个后端：

**Bucket mode**

- 用于环境开发和大规模 RL 训练；
- 将待完成工作按 remaining slack 聚合；
- 状态维度固定，计算速度快；
- action 为本时段执行的 aggregate GPU-hours。

**Job-level mode**

- 用于正式外部验证和关键敏感性分析；
- 每个 job 至少包含 `release_time`, `gpu_request`, `runtime_h`, `deadline_h`, `priority`, `job_type`；
- 可配置 preemptible/non-preemptible；
- 可配置 gang scheduling、minimum run quantum 和 checkpoint overhead；
- agent 仍可输出 aggregate capacity，环境内部使用 EDF/slack-aware dispatcher 映射到具体 jobs。

正式论文至少应证明 bucket mode 的主要结论在 job-level mode 中不发生方向性反转。若两种模式排名不同，应将该差异作为结果报告，而不是只保留更有利的模式。

## 8. 时间分辨率和 episode

### 8.1 默认设置

```yaml
timestep_hours: 1
episode_days: 7
clearance_tail_hours: 48
forecast_horizon_hours: 6
max_deadline_hours: 48
```

推荐使用一周 episode，而不是单日 episode，原因是：

- 可以出现连续多次 DR；
- 能观察 backlog 累积；
- 能观察周内负荷模式；
- 能评估事件结束后的 rebound。

episode 末尾增加 24 h clearance tail，用于清理尚未完成的任务。主 KPI 只统计前 7 天，tail 仅避免利用 episode 边界逃避任务完成。

### 8.2 15 min 扩展

V1 可将 `timestep_hours` 改为 0.25，并把 Alibaba 小时任务量在小时内按随机或均匀方式细分。只有在以下情况下才值得做：

- 小时模型已稳定；
- 审稿人要求更细 DR 时间尺度；
- 有 15 min 社区负荷；
- 需要研究 15–60 min DR 事件。

第一版无需秒级环境。

---

## 9. 数据源

## 9.1 Alibaba Cluster Trace GPU v2026

官方仓库：

```text
https://github.com/alibaba/clusterdata/tree/master/cluster-trace-gpu-v2026
```

官方数据目录：

```text
https://tre-clusterdata.oss-cn-hangzhou.aliyuncs.com/cluster-trace-gpu-v2026/data/
```

该 release 提供约 6 个月的相对时间 trace，公开表包括：

| 文件 | 压缩大小 | V0 用途 |
|---|---:|---|
| `asi_opensource_job_execution_summary.zip` | 约 1.19 GB | GPU request、duration、priority、job/model type 分布 |
| `asi_opensource_pod_hourly.zip` | 约 351.8 GB | 真实的 day/hour 时间顺序、used GPU-hours、运行/等待状态 |
| `asi_opensource_server_hourly.zip` | 约 3.08 GB | 服务器和 GPU inventory；V0 非必需 |
| `asi_opensource_network_hourly.zip` | 约 204 MB | 网络研究；V0 不使用 |

关键字段：

```text
pod_id
workload_id
state_public
priority_class
job_type_public
model_type_public
gpu_request
used_gpu_hours
avg_gpu_sm_util
day
hour
duration_hours
```

公开 job type 包括：

```text
training
online_inference
offline_inference
dev
other
unknown
```

### 9.1.1 Lite 模式

只下载 `job_execution_summary`。它没有 day/hour，因此只能得到任务类型、GPU request 和 duration 分布，不能 replay 真实到达顺序。

Lite 模式应被描述为：

> **Alibaba-2026-calibrated synthetic arrivals**

而不是：

> **Alibaba 2026 chronological trace replay**

Lite 模式适合先搭环境、调算法和做单元测试。

### 9.1.2 Full-trace 模式

下载 `pod_hourly`，按 `pod_id` 聚合得到：

- first observed hour；
- last observed hour；
- total used GPU-hours；
- job type；
- priority；
- GPU request；
- model type。

Full-trace 模式可以构造真实相对日序列，是正式论文的推荐主结果。官方压缩包很大，下载前应确认存储空间；解压后的 Parquet 数据会显著大于压缩包。

### 9.1.3 V0 的 flexible / rigid 分类

主分析建议：

```yaml
flexible:
  job_type_public: [training, offline_inference]
  priority_class: [LP]

rigid:
  job_type_public: [online_inference]
  priority_class: [HP]

excluded_main_analysis:
  job_type_public: [dev, other, unknown]
```

敏感性分析再测试：

- `Other` priority 中有多少比例可以移动；
- training 是否全部可移动；
- offline inference 的 flexible share；
- dev workload 是否纳入。

Alibaba trace 不提供真实 deadline。所有 deadline 都是平台生成的场景参数，必须在论文中明确说明。

---

## 9.2 社区负荷

### 默认：可复现合成社区

仓库必须自带一个无需外部数据即可运行的社区负荷生成器，包含：

- base load；
- morning peak；
- evening peak；
- weekday/weekend variation；
- seasonal multiplier；
- Gaussian 或 block-bootstrap noise；
- optional PV。

合成数据用于：

- CI 单元测试；
- 快速训练；
- 开源用户零配置运行。

### 正式数据：NREL/OEDI End-Use Load Profiles

官方页面：

```text
https://data.openei.org/submissions/4520
```

公开 S3：

```text
s3://oedi-data-lake/nrel-pds-building-stock/end-use-load-profiles-for-us-building-stock/
```

该数据提供住宅和商业建筑的 15 min load profiles。正式论文可：

1. 选择一个气候区；
2. 抽取住宅、办公、零售或学校建筑；
3. 聚合成社区；
4. 从 15 min 重采样为 1 h；
5. 归一化到目标社区峰值。

查看数据目录：

```bash
aws s3 ls --no-sign-request \
  s3://oedi-data-lake/nrel-pds-building-stock/end-use-load-profiles-for-us-building-stock/
```

不建议第一周就下载整个数据湖。先使用仓库自带 synthetic community，把环境跑通后再接入一个选定区域的公开 profile。

### 日本扩展

以后可加入九州/JEPX 价格或日本区域负荷，但除非获得真实配电馈线数据，不应将结果表述为具体福冈配电网实证。

---

## 9.3 DR 信号

V0 不依赖复杂电力市场。仓库生成三类 DR 场景：

### Capacity-limit

```text
PCC total power must remain below a dynamic limit.
```

### Event-based reduction

```text
Start: 17:00
Duration: 2–4 h
Requested reduction: 10%–30% of uncontrolled DC peak
Notice: 0–6 h
```

### Price-only extension

低优先级扩展，用电价代替硬上限。价格不应成为第一篇论文唯一场景，因为价格响应无法直接评价 DR 是否履约。

---

## 9.4 四卡服务器标定数据

最小 workload classes：

| Class | 示例 | 主要映射 |
|---|---|---|
| `idle` | 模型未运行或空闲 GPU | flexible pool idle power |
| `offline_inference` | 批量 LLM 推理 | Alibaba offline inference |
| `training` | LoRA/QLoRA 或代表性训练 | Alibaba training |
| `optional_other` | diffusion / CV | 敏感性分析 |

每个 class 至少测试：

- 1 GPU；
- 2 GPU；
- 4 GPU；
- 3–5 个重复；
- 足够长的稳定运行区间。

最终输出 `workload_energy.csv`，而不是秒级 telemetry 文件作为环境输入。

---

## 9.5 NC 级稳健性所需的独立数据源

单一 Alibaba 2026 trace 可以完成平台主开发，但高水平投稿建议至少有两组独立 workload 数据和两组独立 community profiles：

### 9.5.1 Workload primary

- Alibaba Cluster Trace GPU v2026；
- six-month relative chronology；
- `job_type_public`, `priority_class`, `gpu_request`, `used_gpu_hours`, `avg_gpu_sm_util`, `schedule_delay_sec`；
- 不包含真实 deadline，因此 deadline 是显式情景参数。

### 9.5.2 Workload external validation

- Alibaba GPU v2020；或
- 另一个能够提供 GPU request、start/end 或 execution duration 的公开 trace。

外部验证不需要与主数据完全相同，但必须重新训练或直接 OOD 测试，并明确说明字段映射。

### 9.5.3 Community primary

- NREL/OEDI End-Use Load Profiles，15 min；
- 从住宅和商业建筑聚合为社区 profile；
- 可覆盖不同气候区、季节和建筑组合。

### 9.5.4 Community external validation

推荐二选一：

- Low Carbon London refactored smart-meter dataset，30 min；
- SimBench load profiles。

不得仅通过把同一条社区曲线乘以不同常数来声称跨地区泛化。

### 9.5.5 Minimum robustness matrix

```text
2 workload datasets
× 2 community datasets
× 4 seasons/load regimes
× 4 event durations
× 3 deadline regimes
× repeated-event and single-event scenarios
```

在计算量不足时，主 benchmark 可以使用完整矩阵的子集，但 reliable flexibility 的核心结论至少要在独立 workload 和独立 community profile 上复现。

---

## 10. 推荐目录结构

```text
AIDRBench/
├── README.md
├── pyproject.toml
├── uv.lock
├── configs/
│   ├── base.yaml
│   ├── env/
│   │   ├── hourly_continuous.yaml
│   │   └── hourly_discrete.yaml
│   ├── scenarios/
│   │   ├── synthetic_week.yaml
│   │   ├── alibaba_lite.yaml
│   │   └── alibaba_full.yaml
│   └── algorithms/
│       ├── dqn.yaml
│       ├── ppo.yaml
│       ├── sac.yaml
│       └── mpc.yaml
├── data/
│   ├── raw/
│   │   ├── alibaba2026/
│   │   ├── community/
│   │   └── hardware/
│   ├── interim/
│   └── processed/
│       ├── jobs.parquet
│       ├── arrivals_hourly.parquet
│       ├── rigid_load_hourly.parquet
│       ├── community_load_hourly.parquet
│       ├── workload_energy.csv
│       └── scenario_index.parquet
├── src/aidrbench/
│   ├── envs/
│   │   ├── community_ai_dr_env.py
│   │   ├── deadline_buckets.py
│   │   └── registration.py
│   ├── data/
│   │   ├── alibaba2026.py
│   │   ├── community.py
│   │   ├── deadlines.py
│   │   └── scaling.py
│   ├── models/
│   │   ├── power.py
│   │   └── workload.py
│   ├── controllers/
│   │   ├── no_control.py
│   │   ├── threshold.py
│   │   ├── edf_valley_fill.py
│   │   ├── mpc.py
│   │   └── rl.py
│   ├── evaluation/
│   │   ├── metrics.py
│   │   ├── runner.py
│   │   └── plots.py
│   └── cli.py
├── scripts/
│   ├── monitor_gpu_power.sh
│   └── run_all_baselines.sh
├── tests/
│   ├── test_env_checker.py
│   ├── test_compute_conservation.py
│   ├── test_deadline_buckets.py
│   ├── test_no_control.py
│   └── test_mpc_oracle.py
├── results/
└── logs/
```

---

## 11. 服务器安装

以下命令可以直接执行。

### 11.1 系统检查

```bash
nvidia-smi -L
nvidia-smi --query-gpu=name,memory.total,power.limit --format=csv
nvidia-smi topo -m
uname -a
lsb_release -a
```

保存：

```bash
mkdir -p logs/system
nvidia-smi -q > logs/system/nvidia_smi_q.txt
nvidia-smi topo -m > logs/system/nvidia_smi_topology.txt
```

### 11.2 基础软件

```bash
sudo apt update
sudo apt install -y \
  git curl wget unzip aria2 awscli tmux htop build-essential
```

安装 `uv`：

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source "$HOME/.local/bin/env"
uv --version
```

### 11.3 Python 环境

如果仓库还没有 `pyproject.toml`，先在仓库根目录执行：

```bash
uv init --package
```

然后创建并激活 Python 3.11 环境：

```bash
uv python install 3.11
uv venv --python 3.11
source .venv/bin/activate
```

推荐依赖：

```bash
uv add \
  "gymnasium==1.3.0" \
  "stable-baselines3==2.9.0" \
  "cvxpy==1.9.2" \
  numpy pandas scipy pyarrow polars duckdb pyyaml pydantic \
  matplotlib tensorboard tqdm rich typer highspy

uv add --dev pytest pytest-cov ruff mypy
```

执行后提交 `uv.lock`，保证服务器和论文复现使用相同版本。

RL 网络很小，训练可在 CPU 上运行，不应占用四张 GPU；四张 GPU 主要用于 workload energy calibration。

---

## 12. 下载 Alibaba 2026 数据

### 12.1 Lite 模式：先下载 1.19 GB summary

```bash
mkdir -p data/raw/alibaba2026
cd data/raw/alibaba2026

wget -c \
  https://tre-clusterdata.oss-cn-hangzhou.aliyuncs.com/cluster-trace-gpu-v2026/data/asi_opensource_job_execution_summary.zip

unzip -q asi_opensource_job_execution_summary.zip
cd ../../..
```

预期结构：

```text
data/raw/alibaba2026/
└── asi_opensource_job_execution_summary/
    └── part-000.parquet
```

### 12.2 Full-trace 模式：正式论文推荐

```bash
cd data/raw/alibaba2026

aria2c -c -x 16 -s 16 \
  https://tre-clusterdata.oss-cn-hangzhou.aliyuncs.com/cluster-trace-gpu-v2026/data/asi_opensource_pod_hourly.zip

unzip asi_opensource_pod_hourly.zip
cd ../../..
```

预期结构：

```text
data/raw/alibaba2026/
└── asi_opensource_pod_hourly/
    └── day=<day>/hour=<hour>/part-000.parquet
```

不要为了 V0 下载 `network_hourly`。`server_hourly` 只有在研究 GPU inventory 或集群拓扑时才需要。

---

## 13. Alibaba 2026 预处理

下面的 CLI 是本仓库需要实现的**目标接口**，不是现成的 Alibaba 命令。

### 13.1 Lite summary 处理

```bash
uv run aidrbench data preprocess-alibaba-summary \
  --input data/raw/alibaba2026/asi_opensource_job_execution_summary/part-000.parquet \
  --output data/processed/jobs_summary.parquet
```

核心计算：

```text
requested_work_gpu_h = gpu_request × duration_hours
```

该量是 requested GPU capacity-time proxy，不是实测完成的计算量。Lite 模式在环境中把它作为统一 work unit；Full-trace 模式优先使用 `sum(used_gpu_hours)` 表示观察到的 GPU-hours。

保留：

```text
pod_id
workload_id
gpu_spec_public
priority_class
job_type_public
model_type_public
gpu_request
duration_hours
requested_work_gpu_h
```

过滤建议：

```text
gpu_request > 0
duration_hours > 0
finite values only
```

不要直接删除极长任务。主分析可 winsorize 到 99.5 percentile，并把原始长尾作为敏感性分析。

### 13.2 Full trace 聚合

推荐用 DuckDB 直接扫描分区 Parquet，避免将全部数据载入内存。

示例 SQL：

```sql
CREATE OR REPLACE TABLE pod_jobs AS
SELECT
    pod_id,
    any_value(workload_id) AS workload_id,
    any_value(priority_class) AS priority_class,
    any_value(job_type_public) AS job_type_public,
    any_value(model_type_public) AS model_type_public,
    max(gpu_request) AS gpu_request,
    sum(used_gpu_hours) AS work_gpu_h,
    min(CAST(day AS INTEGER) * 24 + CAST(hour AS INTEGER)) AS first_hour,
    max(CAST(day AS INTEGER) * 24 + CAST(hour AS INTEGER)) AS last_hour,
    count(*) AS observed_hours
FROM read_parquet(
    'data/raw/alibaba2026/asi_opensource_pod_hourly/day=*/hour=*/part-*.parquet',
    hive_partitioning = true
)
WHERE gpu_request > 0
GROUP BY pod_id;
```

正式实现还应：

- 使用 `state_public` 区分 Running/Pending；
- 将 `first_hour` 明确表述为 first observed hour，而不是精确提交时间；
- 对同一 `workload_id` 的多个 pod 是否合并做敏感性分析；
- 与 execution summary 通过 `pod_id` 连接，用其 `duration_hours` 校验。

目标命令：

```bash
uv run aidrbench data preprocess-alibaba-full \
  --pod-root data/raw/alibaba2026/asi_opensource_pod_hourly \
  --summary data/raw/alibaba2026/asi_opensource_job_execution_summary/part-000.parquet \
  --output data/processed/jobs_full.parquet
```

### 13.3 从 jobs 构造小时 arrivals

Lite 模式：

- 从 summary 经验分布采样 `gpu_request`、`duration_hours`、job type 和 priority；
- 到达时间由可配置 non-homogeneous Poisson process 或 block process 生成；
- 每日总 GPU-h 由 `target_utilization` 控制。

Full 模式：

- `arrival_hour = first_hour`；
- `work_gpu_h = sum(used_gpu_hours)`；
- 按 trace 相对时间 replay；
- 再按目标虚拟数据中心规模做比例缩放。

输出：

```text
arrivals_hourly.parquet
```

推荐 schema：

```text
episode_id
timestamp_index
job_class
priority_class
model_type
arrival_gpu_h
slack_hours
source_mode
```

---

## 14. Deadline 生成

Alibaba 2026 不提供真实 deadline，因此 deadline 是场景假设，不是 trace observation。

推荐策略：

```yaml
deadline_policy:
  training:
    slack_multiplier_range: [2.0, 6.0]
    minimum_slack_h: 6
    maximum_slack_h: 48
  offline_inference:
    slack_multiplier_range: [1.5, 4.0]
    minimum_slack_h: 2
    maximum_slack_h: 24
```

对 job \(j\)：

\[
\text{slack}_j
=
\operatorname{clip}
\left(
\kappa_j d_j,
S_{\min,c},
S_{\max,c}
\right),
\]

其中 \(d_j\) 是 duration，\(\kappa_j\) 从类别对应范围采样。

主文必须报告：

- deadline 不是 Alibaba 原始字段；
- deadline policy；
- 采用的最小/最大 slack；
- 对 slack 的敏感性。

---

## 15. 从阿里超大集群缩放到虚拟社区数据中心

Alibaba trace 的规模远大于四卡节点和社区数据中心，不能原样使用。

V0 使用 fluid scaling：

\[
A_t^{\mathrm{target}}
=s A_t^{\mathrm{raw}},
\]

其中 \(s\) 由目标柔性池平均利用率决定：

\[
s
=
\frac{u_{\mathrm{target}}N_{\mathrm{flex}}\Delta t}
{\operatorname{mean}(A_t^{\mathrm{raw}})}.
\]

推荐默认：

```yaml
virtual_datacenter:
  gpus_per_node: 4
  node_count: auto
  target_dc_peak_share_of_community: 0.20
  flexible_gpu_fraction: 0.50
  target_flexible_utilization: 0.65
```

`node_count: auto` 的逻辑：选择节点数，使 uncontrolled data-center peak 约等于社区峰值的 20%。敏感性分析测试 10%、20%、30% 和 40%。

四卡服务器只标定单节点参数；论文结果可以模拟多个同质节点，但必须称为：

> **hardware-calibrated virtual data center**

不能称为 MW-scale field experiment。

---

## 16. 社区负荷和 DR scenario 生成

合成社区 smoke 数据：

```bash
conda run -n aidrbench aidrbench data make-synthetic-community \
  --days 30 \
  --resolution-seconds 900 \
  --peak-kw 1000 \
  --seed 2026 \
  --output data/processed/community_synthetic.parquet
```

已下载的 NREL EULP profile 预处理：

```bash
conda run -n aidrbench aidrbench data preprocess \
  --config configs/data/community_eulp.yaml
```

真实来源社区profile已经可以直接接入小时环境；环境选择一个profile、将15分钟功率按小时平均、统一缩放社区毛负荷与PV，并按seed抽取连续episode：

```bash
conda run -n aidrbench aidrbench rollout \
  --controller threshold \
  --scenario nrel_eulp_mixed_3a \
  --config configs/env/hourly_continuous_nrel_eulp.yaml \
  --seed 7 \
  --save results/nrel_eulp_mixed_3a_threshold
```

配置中的 `community.episode_start` 可固定窗口；省略时由episode seed可复现地抽样。`pv_enabled: false` 会保留社区毛负荷但将PV置零。

生成与小时环境严格对齐的独立DR manifest：

```bash
conda run -n aidrbench aidrbench data preprocess \
  --config configs/data/dr_events_hourly.yaml
```

运行“真实来源社区profile + 独立DR manifest”闭环场景：

```bash
conda run -n aidrbench aidrbench rollout \
  --controller threshold \
  --scenario nrel_eulp_manifest_hourly \
  --config configs/env/hourly_continuous_nrel_eulp_manifest.yaml \
  --seed 7 \
  --save results/nrel_eulp_manifest_threshold
```

小时环境要求manifest事件从整点开始、持续时间为整小时，并会拒绝旧的15/30分钟事件，避免静默改变事件能量。manifest中的 `reduction_fraction` 按可调数据中心动态峰值解释；若提供 `requested_reduction_kw` 列则优先采用绝对kW请求。旧manifest中的社区侧 `pcc_limit_kw` 不直接复用，因为它不包含加入PCC后的数据中心基线。

默认事件生成规则：

1. 在社区 top-20% load hours 中选择候选窗口；
2. 随机生成 2–4 h event；
3. 给出 0、2、4 或 6 h notice；
4. 每周 2–5 个事件；
5. 至少包含一组相邻两天连续事件；
6. event 后继续模拟至少 12 h，用于测 rebound。

---

## 17. 四卡 GPU workload-energy 标定

### 17.1 目标

只标定以下参数：

```text
p_idle_w_per_gpu
p_active_w_per_gpu by workload class
node_fixed_overhead_w
runtime / completed work
energy_kwh per run
```

不建立温度动态模型。

### 17.2 记录 GPU 功率

```bash
mkdir -p data/raw/hardware logs/hardware

nvidia-smi \
  --query-gpu=timestamp,index,name,power.draw,utilization.gpu \
  --format=csv,noheader,nounits \
  -l 1 \
  > logs/hardware/gpu_power_run001.csv
```

在另一个终端运行 benchmark。完成后停止 `nvidia-smi`。

1 s 采样只用于计算均值和积分能耗：

\[
E=\sum_k P_k\Delta t.
\]

### 17.3 推荐实验矩阵

| workload | GPU 数 | repeats | 输出 |
|---|---:|---:|---|
| idle | 1/2/4 | 5 | idle power |
| offline LLM inference | 1/2/4 | 5 | avg power, throughput, energy |
| LoRA/QLoRA training | 1/2/4 | 5 | avg power, runtime, energy |
| optional diffusion/CV | 1/2/4 | 3 | sensitivity |

环境只使用 run-level summary：

```text
workload_energy.csv
```

Schema：

```text
run_id
workload_class
model_name
active_gpu_count
runtime_seconds
completed_work_units
avg_gpu_power_w
avg_node_power_w
energy_kwh
measurement_source
repeat_id
```

### 17.4 没有整机功率计时

使用：

\[
P^{\mathrm{node}}
=
\sum_g P_g^{\mathrm{GPU}}
+P^{\mathrm{host,fixed}}.
\]

`P_host_fixed` 可由空闲整机功率、BMC/PSU telemetry 或保守参数估计。论文中需分别报告：

- GPU-only measured energy；
- modelled node/facility energy。

---

## 18. Gymnasium 环境定义

注册环境：

```text
AIDRBench-Continuous-v0
AIDRBench-Discrete-v0
AIDRBench-JobLevel-v0
```

Gymnasium API：

```python
obs, info = env.reset(seed=seed)
obs, reward, terminated, truncated, info = env.step(action)
```

### 18.1 Observation

当前接口版本为 `firm_v4`，使用63维、顺序固定的无量纲向量。环境的小时顺序为：

```text
本小时任务release并进入队列 → 构造observation → controller选择action → EDF执行与状态转移
```

因此 controller 在做决定前能够看到本小时已经 release 的工作。主要状态组为：

```text
4 calendar sin/cos features
community、PV、PCC limit、fixed DC power / community target peak
available flexible-power headroom / flexible DC power range
DR request / flexible DC power range
controlled、baseline、excess backlog / (hourly capacity × max deadline)
cumulative arrival utilization、controlled/baseline miss rate、terminal excess fraction
mean/p10 slack / max deadline
8 controlled deadline-feasibility ratios
8 excess-over-baseline deadline-feasibility ratios
event、notice、recovery和event-window状态
running baseline peak、controlled peak、window relief和rebound
previous action、previous PCC
H-step community forecast和flexible-power headroom forecast
```

对每个 deadline horizon $h$，核心队列状态定义为：

\[
u_t(h)=\frac{W_t(\le h)}{\min(h+1,H_{\max})C},
\]

其中bucket label 0表示本小时到期，$C$ 是每小时柔性GPU-h容量。`u=1`表示
截止前可用容量恰好用满，
`u>1`表示该deadline集合已经不可行。额外提供相对No-control baseline的
feasibility excess，避免把输入trace自身的自然拥塞误归因于controller。

除时间sin/cos、signed headroom和window relief外，特征均为非负；每一维具有
显式边界。它们不被强行压到同一个 `[0,1]` 区间，但正常约束边界约为1，极端值
在进入网络前截断到声明范围。按比例同时扩大社区峰值与虚拟集群节点数时，state
保持不变；这使同一接口可用于不同装机容量。完整顺序由
`env.observation_feature_names` 暴露，checkpoint记录`observation_version`和维度。

预测不是 perfect information。训练时可加入：

```yaml
forecast_error:
  community_load_std_fraction: 0.05
  event_start_error_hours: 0
  event_duration_error_hours: 0
  workload_arrival_forecast: none
```

主结果至少比较：

- no forecast；
- finite noisy forecast；
- perfect-future oracle。

### 18.2 Continuous action

\[
a_t\in[0,1].
\]

含义：本小时计划使用多少比例的柔性 GPU 容量：

\[
x_t=a_tN_{\mathrm{flex}}\Delta t.
\]

环境将其限制为不超过当前 backlog、物理容量和 job-level dispatch feasibility。

用于：

- PPO；
- SAC；
- continuous RBC；
- continuous MPC。

### 18.3 Discrete action

```text
0 → 0%
1 → 25%
2 → 50%
3 → 75%
4 → 100%
```

用于：

- DQN；
- PPO-discrete；
- rule-based 对照。

### 18.4 Step 顺序

```text
1. 读取当前社区负荷、PV、PCC limit 和 DR request
2. 加入本小时新到达的柔性 jobs/GPU-hours
3. 更新 repeated-event history 和 notice state
4. 构造包含本小时released work的observation
5. controller选择action并转成计划执行GPU-hours
6. 在 bucket mode 中按 EDF 完成 work；在 job mode 中 dispatch jobs
7. 计算 deadline miss、checkpoint overhead 和 unfinished work
8. 计算 active GPU 数、IT power、facility power 和 PCC power
9. 更新 compute debt、rebound 和 recovery state
10. 计算独立cost、标量reward和KPI
11. buckets/slack向前移动并返回next observation
```

### 18.5 Reward与独立cost接口

当前版本为 `firm_threshold_v2`。环境先输出独立物理量，再用冻结的认证阈值将
违反程度变成无量纲cost；不是直接试凑`20/50/2`等权重。

\[
v_D=\frac{[\eta_{\min}-\eta_t^{delivery}]_+}{1-\eta_{\min}},\qquad
v_M=\frac{[m_t-\epsilon_M]_+}{\epsilon_M},
\]

\[
v_R=\frac{[R_t-\epsilon_R]_+}{\epsilon_R},\qquad
v_W=\frac{[\eta_W-\eta_t^{window}]_+}{\eta_W},
\]

\[
v_T=\frac{[b_T-\epsilon_T]_+}{\epsilon_T}.
\]

这里使用冻结值`delivery≥0.95`、`deadline miss≤0.01`、`rebound≤0.25`、
`window relief≥0.50`、`terminal excess≤0.02`。满足条件时对应violation cost为0；
数值1表示又越过一个阈值尺度。

deadline尚未真正miss之前，另给dense feasibility cost：

\[
v_F=\max_h\left[
\frac{u_t(h)}{\max(1,u_t^{base}(h))}-1
\right]_+.
\]

标准DQN/PPO/SAC需要标量时，默认adapter使用Huber penalty：

\[
r_t=-\sum_{i\in\{D,F,M,R,W,T\}}\rho(v_i)
-0.05e_t^{excess\ backlog}
-0.001|a_t-a_{t-1}|.
\]

\[
\rho(v)=
\begin{cases}
\frac12v^2,&0\le v\le1,\\
v-\frac12,&v>1.
\end{cases}
\]

以一个阈值尺度为Huber转折点，使边界附近保持二次敏感度，但防止严重违规时的
平方爆炸破坏PPO/SAC数值条件。原始violation cost不做这种压缩，仍完整写入`info`。

cost结算时间与认证定义一致：delivery按每个事件小时结算，deadline feasibility
按每小时结算；rebound与window relief只在对应recovery window结束时各结算一次；
episode-wide deadline miss与terminal backlog只在episode结束时结算一次。运行中的
rebound/window violation仍作为state和`info`输出，但不会把同一事件失败按恢复窗口
长度重复计权。

六项主cost默认等权，是因为都已经按物理认证阈值归一化；backlog和switching只作
小幅dense shaping。环境同时在`info`中保留每个未加权cost和每个weighted cost，
以后可接Lagrangian/constrained RL，而不需要修改物理状态转移。

重要：`F_q(H)` 的认证必须由独立 evaluator 计算，不能直接等同于训练 reward。所有控制器使用同一 success criterion、同一 test episodes 和同一置信区间方法。

至少进行以下 reward 敏感性：

- no rebound penalty；
- no backlog penalty；
- low/high deadline penalty；
- equalized service constraints 后再比较 controller performance。

### 18.6 `info` 字段

```text
pcc_power_kw
dc_power_kw
community_power_kw
pcc_limit_kw
requested_reduction_kw
delivered_reduction_kw
delivery_ratio
limit_violation_kw
dr_tracking_error_fraction
reward_version
delivery_violation_cost
deadline_feasibility_violation_cost
deadline_miss_rate_so_far
deadline_violation_cost
rebound_violation_cost
window_relief_violation_cost
running_rebound_violation_cost
running_window_relief_violation_cost
completed_recovery_event_count
terminal_backlog_violation_cost
reward_penalty
executed_gpu_h
arrival_gpu_h
backlog_gpu_h
baseline_backlog_gpu_h
backlog_excess_gpu_h
compute_debt_kwh
missed_gpu_h
mean_slack_h
p10_slack_h
action_fraction
event_active
event_id
rebound_excess_kw
rebound_reference_kw
rebound_ratio_proxy
running_window_relief_fraction
running_rebound_ratio
hours_since_previous_event
recovery_active
recovery_remaining_hours
recovery_complete
terminal_backlog_excess_gpu_h
```

## 19. 必须实现的 baseline

## 19.1 No-control

每小时尽可能执行所有现有 backlog：

\[
x_t=\min(B_t+A_t,N_{\mathrm{flex}}\Delta t).
\]

它定义未参与 DR 的数据中心基线。

## 19.2 Threshold rule

```python
available_budget = pcc_limit - community_load - rigid_dc_power
if available_budget <= 0:
    action = 0.0
else:
    action = clip(available_budget / flexible_pool_peak_power, 0.0, 1.0)
```

## 19.3 EDF with urgency override

先计算未来一小时必须完成的 work：

```text
urgent_work = bucket_0 + bucket_1
```

即使社区处于高峰，也执行保证 deadline 所需的最低量。其余容量仅在低负荷时使用。

## 19.4 Valley filling rule

当未来预测负荷低于 rolling percentile 时提高 action，高于 percentile 时降低 action。

## 19.5 Rolling-horizon optimizer / MPC

这里的 MPC 是 receding-horizon workload scheduler，不是热过程控制。

每小时求解未来 \(H\) 小时：

\[
\min
\sum_{\tau=t}^{t+H-1}
\left[
\alpha z_\tau
+\beta B_\tau
+\gamma M_\tau
+\eta |x_\tau-x_{\tau-1}|
\right],
\]

满足：

\[
P_\tau^{\mathrm{PCC}}-\overline P_\tau^{\mathrm{PCC}}\le z_\tau,
\qquad z_\tau\ge0,
\]

以及 backlog、capacity 和 deadline bucket 动态。

推荐：

```yaml
mpc:
  horizon_hours: 24
  solver: HIGHS
  arrival_forecast: historical_mean
  community_forecast: noisy
```

额外实现 full-horizon oracle，使用完整未来信息，作为可达到性能的参考上界；oracle 不能与在线控制方法混为一谈。

## 19.6 RL algorithms

第一篇主算法：

| 算法 | 环境 | 角色 |
|---|---|---|
| DQN | Discrete | 离散 baseline |
| PPO | Continuous + Discrete | 主 RL baseline |
| SAC | Continuous | off-policy continuous baseline |
| A2C | optional | 补充，不必作为主结果 |

不要一开始加入十几个 RL 算法。平台论文更重要的是统一环境、数据和评价。

---

## 20. 目标 CLI

以下是仓库应实现的统一命令。README 中的命令是接口规范；在相应模块完成前不要假装命令已经可用。

### 20.1 检查环境

```bash
uv run aidrbench env check --config configs/env/hourly_continuous.yaml
```

内部执行：

```python
from gymnasium.utils.env_checker import check_env
check_env(env.unwrapped)
```

### 20.2 运行一个 episode

```bash
uv run aidrbench rollout \
  --controller no_control \
  --scenario synthetic_week_001 \
  --save results/smoke/no_control
```

```bash
uv run aidrbench rollout \
  --controller threshold \
  --scenario synthetic_week_001 \
  --save results/smoke/threshold
```

### 20.3 训练 RL

```bash
uv run aidrbench train \
  --algo dqn \
  --env discrete \
  --config configs/algorithms/dqn.yaml \
  --seed 1
```

```bash
uv run aidrbench train \
  --algo ppo \
  --env continuous \
  --config configs/algorithms/ppo.yaml \
  --seed 1
```

```bash
uv run aidrbench train \
  --algo sac \
  --env continuous \
  --config configs/algorithms/sac.yaml \
  --seed 1
```

### 20.4 运行 MPC

```bash
uv run aidrbench evaluate \
  --controller mpc \
  --split test \
  --config configs/algorithms/mpc.yaml \
  --save results/test/mpc
```

### 20.5 统一 benchmark

```bash
uv run aidrbench benchmark \
  --controllers no_control threshold edf_valley mpc dqn ppo sac \
  --split test \
  --seeds 1 2 3 4 5 \
  --save results/benchmark_v0
```

### 20.6 认证 reliable deliverable flexibility

对多个候选削减容量运行二分搜索或网格搜索：

```bash
uv run aidrbench certify \
  --controller ppo \
  --split test \
  --durations 1 2 4 6 \
  --reliability 0.95 \
  --confidence 0.95 \
  --min-delivery-ratio 0.95 \
  --max-deadline-miss-rate 0.01 \
  --max-rebound-ratio 0.25 \
  --min-window-peak-relief-fraction 0.50 \
  --max-terminal-backlog-fraction 0.02 \
  --episodes 500 \
  --search binary \
  --save results/certificates/ppo
```

输出至少包括：

```text
controller
workload_dataset
community_dataset
duration_h
reliability_target
certified_reduction_kw
certified_reduction_fraction
success_count
episode_count
success_rate
success_rate_lower_ci
mean_delivery_ratio
p95_deadline_miss_rate
p95_rebound_ratio
mean_window_peak_relief_kw
p05_window_peak_relief_fraction
p95_recovery_time_h
```

### 20.7 连续事件 stress test

```bash
uv run aidrbench stress-test \
  --controllers threshold mpc ppo sac \
  --events-per-day 1 2 3 \
  --inter-event-gap-hours 2 4 8 12 \
  --duration-hours 2 4 \
  --split test \
  --save results/repeated_events
```

输出 \(\rho_k^{\mathrm{res}}\)、exhaustion、recovery time 和 second-event failure rate。

### 20.8 比较 static 与 job-derived envelope

```bash
uv run aidrbench compare-envelopes \
  --static-fractions 0.20 0.30 0.40 \
  --certificates results/certificates \
  --save results/envelope_bias
```

### 20.9 画图

```bash
uv run aidrbench plot \
  --input results \
  --output results/figures
```

## 21. 配置文件示例

`configs/base.yaml`：

```yaml
seed: 2026

env:
  timestep_hours: 1.0
  episode_days: 7
  clearance_tail_hours: 48
  forecast_horizon_hours: 6
  action_mode: continuous
  backend_mode: bucket          # bucket | job_level

community:
  source: nrel_eulp
  path: data/processed/community_load.parquet
  profile_id: eulp_mixed_3a
  target_peak_kw: 1000
  pv_enabled: true

virtual_datacenter:
  gpus_per_node: 4
  node_count: auto
  target_dc_peak_share_of_community: 0.20
  flexible_gpu_fraction: 0.50
  target_flexible_utilization: 0.65
  pue: 1.20

workload:
  source: alibaba2026_full
  external_validation_source: alibaba2020
  flexible_job_types:
    - training
    - offline_inference
  flexible_priorities:
    - LP
  max_deadline_hours: 48
  deadline_buckets: [0, 1, 2, 3, 6, 12, 24, 48]
  dispatch_rule: edf
  preemptible_fraction: 0.75
  checkpoint_overhead_fraction: 0.00

hardware:
  calibration_file: data/processed/workload_energy.csv
  fallback_idle_power_w_per_gpu: 80
  fallback_active_power_w_per_gpu: 450
  fallback_node_overhead_w: 300

dr:
  mode: event_based
  events_per_week: [2, 5]
  event_duration_hours: [1, 2, 4, 6]
  reduction_fraction: [0.05, 0.40]
  notice_hours: [0, 2, 4, 6]
  repeated_events_enabled: true
  inter_event_gap_hours: [2, 4, 8, 12, 24]
  recovery_window_hours: 12

reward:
  version: firm_threshold_v2
  min_delivery_ratio: 0.95
  max_deadline_miss_rate: 0.01
  max_rebound_ratio: 0.25
  min_window_peak_relief_fraction: 0.50
  max_terminal_backlog_fraction: 0.02
  delivery_violation_weight: 1.0
  feasibility_violation_weight: 1.0
  deadline_violation_weight: 1.0
  rebound_violation_weight: 1.0
  window_violation_weight: 1.0
  terminal_violation_weight: 1.0
  excess_backlog_weight: 0.05
  switching_weight: 0.001

certification:
  reliability_target: 0.95
  confidence_level: 0.95
  min_delivery_ratio: 0.95
  max_deadline_miss_rate: 0.01
  max_rebound_ratio: 0.25
  min_window_peak_relief_fraction: 0.50
  max_terminal_backlog_fraction: 0.02
  candidate_reduction_fraction: [0.00, 0.50]
  search_method: binary
  test_episodes: 500

splits:
  train_fraction: 0.60
  validation_fraction: 0.20
  test_fraction: 0.20
```

上面的 fallback 功率只能用于 smoke test。正式实验必须由四卡服务器测量结果替换或至少以测量区间进行敏感性分析。

所有科学阈值必须在查看最终 test set 之前确定，或通过预注册式配置文件冻结。不能根据 test 结果调整 `max_rebound_ratio`、`max_miss_rate` 或 reliability target。

## 22. 数据切分

### 22.1 Full Alibaba trace

相对天数为 `day=0..184`。推荐 chronological split：

```text
train: day 0–110
validation: day 111–147
test: day 148–184
```

不要随机打散小时，否则同一 workload 周期可能同时进入训练和测试。

### 22.2 Lite synthetic arrivals

- train、validation、test 使用互不重叠的随机种子；
- test 包含训练未见过的 arrival intensity、deadline 和 DR 强度组合；
- 不能把同一生成 episode 同时用于调参和最终评价。

正式小时实验不直接在每次reset时载入4052万行summary。仓库先流式构建分层均匀经验采样池：

```bash
conda run -n aidrbench aidrbench data make-alibaba-lite-sampler \
  --input data/processed/jobs_summary.parquet \
  --output data/processed/jobs_summary_sampler.parquet \
  --job-classes training offline_inference \
  --priorities lp \
  --rows-per-stratum 50000 \
  --seed 2026
```

该采样池按 `job_type_public/priority_class` 分层等概率抽样，保留每条记录内部的GPU需求、duration和GPU-h联合关系。它只降低重复环境初始化的内存和I/O开销，不把Lite数据误称为时间序列。

正式协议检查：

```bash
conda run -n aidrbench aidrbench protocol-check \
  --manifest data/manifests/hourly_experiment_protocol_v1.yaml
```

协议固定：3A训练、5A验证、3C锁定OOD测试；episode seed范围分别为10000–19999、20000–20099和30000–30499。所有正式配置均从经验采样池按seed重新生成到达，禁止使用固定一周arrival文件做统计认证。

正式RL配置会在训练启动前自动验证协议和数据hash，并把协议hash、模型seed、首个episode seed及允许的episode seed范围写入 `training.json`：

```bash
conda run -n aidrbench aidrbench train \
  --algo ppo --env continuous \
  --config configs/algorithms/ppo_formal.yaml \
  --seed 101 --save results/training/formal/ppo_seed101
```

DQN和SAC分别使用 `dqn_formal.yaml`、`sac_formal.yaml`。超参数和checkpoint选择只能查看20000–20099验证seed；锁定配置之后才允许在30000–30499测试seed上运行最终benchmark和certificate。

DQN和SAC checkpoint由 `model.zip` 与同目录的 `replay_buffer.pkl` 共同组成；
缺少后者时训练命令会拒绝 off-policy 续训。`training.json` 同时区分
`requested_timesteps`、`actual_segment_timesteps` 和 `cumulative_timesteps`，因为
PPO 会按完整 rollout batch 向上取整。当前验证进度及 checkpoint 选择记录见
[`docs/hourly-validation-status.md`](docs/hourly-validation-status.md)。

正式算法配置每 5000 个实际环境步自动保存一个可恢复 checkpoint，例如
`checkpoints/step_000025000/`。DQN/SAC 的每个目录都包含配对 replay buffer，
用于在 validation split 上选择 checkpoint 并审计训练退化。

### 22.3 社区负荷

按连续周和季节切分。若使用年度 NREL profile，确保夏季/冬季均在 test set 中有代表场景。

### 22.4 外部数据集

- primary dataset 用于训练、调参和内部 test；
- external workload/community dataset 只用于最终 OOD 评价；
- zero-shot 结果必须先报告；
- 如做 external fine-tuning，应使用独立 adaptation split，不能使用 external final test；
- deadline generation policy 在不同 trace 间保持同一原则，并同时报告固定 policy 与重新标定 policy。

---

## 23. 评价指标与灵活性认证协议

### 23.1 社区与事件指标

- `pcc_peak_kw`；
- event-only peak reduction，kW 和 %；
- event delivery ratio；
- event-hour PCC-limit compliance rate（兼容字段 `dr_success_rate`）；
- joint firm-event success rate（`firm_event_success_rate`）；
- capacity violation hours；
- maximum violation，kW；
- energy above limit，kWh；
- requested vs delivered reduction；
- post-event rebound peak；
- rebound ratio；
- delivery、deadline、rebound、window relief 和 terminal backlog failure counts；
- window-wide peak relief；
- secondary peak occurrence time。

### 23.2 计算服务指标

- completed flexible GPU-hours；
- mean、p95、p99 delay；
- deadline miss GPU-hours；
- deadline miss rate；
- mean、p95 和 maximum backlog；
- compute debt energy；
- unfinished terminal backlog；
- recovery time；
- action switching frequency；
- optional checkpoint overhead。

### 23.3 能源指标

- total data-center energy；
- rigid/flexible energy；
- energy per completed GPU-hour；
- optional electricity cost；
- optional carbon emissions；
- measured-vs-modelled energy error。

负荷转移通常守恒计算工作，因此总能耗未必下降。不能将 peak shaving 自动解释为 energy saving。

### 23.4 Reliable flexibility 指标

对每个 controller、duration 和数据组合报告：

- `F_0.90(H)`；
- `F_0.95(H)`；
- `F_0.99(H)`；
- certified reduction as % of data-center peak；
- certified reduction as % of community peak；
- empirical success rate；
- one-sided lower confidence bound；
- failure decomposition：delivery、window relief、deadline、rebound、terminal backlog。

### 23.5 Repeated-event 指标

- first-event and second-event certified flexibility；
- residual flexibility ratio \(\rho_k^{\mathrm{res}}\)；
- exhaustion \(E_k\)；
- recovery time；
- second-event failure probability；
- compute debt immediately before each event；
- relation between queue slack and remaining flexibility。

### 23.6 Static envelope bias

比较 static-20/30/40% 与 job-derived certificate：

- absolute bias，kW；
- relative bias，%；
- false-commitment probability；
- dependence on event duration、deadline regime 和 arrival intensity。

### 23.7 统计协议

主结果建议：

- 至少 5 个 RL training seeds；
- 每个最终 controller 至少 500 个独立 test episodes 用于 certificate；
- chronological test split；
- paired episode comparison；
- bootstrap 95% CI 用于连续 KPI；
- binomial one-sided CI 用于 success probability；
- 多场景比较时报告 effect size，而不只报告 p-value；
- 不把多个小时当作独立样本，episode 或 event 才是统计单位。

### 23.8 Rebound 定义

设 DR 结束后 \(W\) 小时为 post-event window：

\[
P^{\mathrm{rebound}}
=
\max_{t\in W}
\left[
P_t^{\mathrm{PCC,control}}
-P_t^{\mathrm{PCC,no-control}}
\right]_+.
\]

定义 rebound ratio：

\[
R^{\mathrm{rebound}}
=
\frac{P^{\mathrm{rebound}}}
{\max_t\Delta P_t^{\mathrm{delivered}}+\epsilon}.
\]

必须同时报告 event-only peak reduction、rebound 和 window-wide peak relief；否则算法可能只是把峰值从 18:00 移到 22:00。

## 24. 论文主实验

### Experiment 1：平台与守恒 sanity check

- 无 flexible workload；
- 无 DR；
- 无限 PCC limit；
- 极低/极高 arrival；
- 计算守恒；
- bucket mode 与 job-level mode 对照。

### Experiment 2：Static envelope 与 job-derived flexibility

比较：

```text
static 20%
static 30%
static 40%
job-derived nominal flexibility
job-derived F_0.90(H)
job-derived F_0.95(H)
job-derived F_0.99(H)
```

事件持续时间：1、2、4、6 h。输出 bias 和 false-commitment probability。

### Experiment 3：控制器主比较

```text
No-control
Threshold RBC
EDF + valley filling
MPC
DQN
PPO
SAC
Full-future Oracle
```

所有在线方法使用相同 forecast information；Oracle 单独标记。主要比较不是总 reward，而是 certified flexibility、window-wide peak relief、deadline 和 rebound。

### Experiment 4：Compute debt 与连续事件

```text
1 event/day
2 events/day
3 events/day
inter-event gap = 2, 4, 8, 12, 24 h
event duration = 2, 4 h
```

输出：

- \(\rho_k^{\mathrm{res}}\)；
- exhaustion；
- recovery time；
- second-event failure probability；
- compute debt trajectory。

### Experiment 5：Deadline 与任务结构

```text
flexible share: 20%, 40%, 60%, 80%
deadline: short, medium, long
arrival intensity: 0.5×, 1.0×, 1.5×
preemptible fraction: 0%, 50%, 100%
checkpoint overhead: 0%, 2%, 5%
```

### Experiment 6：社区—数据中心规模比

```text
DC peak / community peak = 10%, 20%, 30%, 40%
```

同时报告 kW flexibility 和相对 community peak relief，防止规模归一化掩盖实际效应。

### Experiment 7：预测误差与通知时间

```text
community forecast error = 0%, 5%, 10%, 20%
arrival forecast = none / historical mean / perfect
event notice = 0, 2, 4, 6 h
event-duration uncertainty = 0, ±1 h
```

### Experiment 8：跨数据集和跨地区外部验证

最低要求：

```text
Alibaba 2026 → training/development
Alibaba 2020 or independent GPU trace → external workload test
NREL/OEDI community → primary community test
Low Carbon London or SimBench → external community test
```

不要在外部测试集上重新选择 reward 或超参数；可以单独报告 zero-shot 与 fine-tuned 两种结果。

### Experiment 9：小时 vs 15 min

在主平台稳定后做时间分辨率敏感性，检查：

- event delivery；
- deadline miss；
- rebound；
- controller ranking；
- certified flexibility

是否发生方向性变化。

### Experiment 10：硬件参数和规模外推

使用四卡测量构造：

- low-power calibration；
- median calibration；
- high-power calibration；
- workload-specific calibration。

进行 node aggregation 到虚拟 MW 级数据中心，并明确：

- 哪些量线性缩放；
- 哪些 overhead 非线性；
- 结论是 trace-driven simulation + four-GPU calibration，而不是 MW 级现场实证。

### Experiment 11：机制分析而非只报算法排名

对所有控制器分析：

- 事件前是否提前清理 backlog；
- 事件中保留多少最低执行量；
- 事件后恢复速度；
- 哪些 slack bucket 被优先执行；
- failure 来自 delivery、deadline 还是 rebound；
- state-conditioned flexibility 与 backlog/slack 的关系。

最终论文必须给出至少一个跨算法成立的机制性结论，而不是只展示某个 RL 的平均 reward 更高。

## 25. 公平比较规则

所有控制器必须使用：

- 相同 observation；
- 相同 action bounds；
- 相同 workload arrivals；
- 相同 community load；
- 相同 DR events；
- 相同硬件功率参数；
- 相同 deadline policy；
- 相同 episode tail；
- 相同 KPI 计算代码。

MPC 和 RL 的未来信息必须单独列明。Oracle 使用 perfect future，只作为参考；不能将 Oracle 与无未来信息的 RL 直接宣称为公平在线比较。

超参数只能用 validation set 选择。Test set 不得用于 reward weight 或 network architecture 调参。

---

## 26. 单元测试和物理一致性

### 26.1 计算守恒

对每个 episode：

\[
\sum_t A_t
=
\sum_t x_t
+
\sum_t M_t
+B_{\mathrm{terminal}}.
\]

允许数值误差小于设定 tolerance。

### 26.2 功率边界

```text
0 ≤ active_flexible_gpus ≤ N_flex
P_DC ≥ 0
P_PCC = P_community - P_PV + P_DC
```

### 26.3 行为测试

- `action=0` 不执行柔性任务；
- `action=1` 在有 backlog 时使用全部容量；
- 无 arrivals 时 backlog 不会增加；
- 无限 limit 时 No-control 应接近最小 delay；
- 零 flexible workload 时所有控制器输出相同 PCC；
- full-horizon oracle 的目标值不应差于 rolling MPC；
- clearance tail 后仍有 backlog 时必须计入 terminal penalty。

### 26.4 Gymnasium checker

```python
from gymnasium.utils.env_checker import check_env
check_env(env.unwrapped)
```

### 26.5 CI

```bash
uv run pytest -q
uv run ruff check .
uv run mypy src/aidrbench
```

---

## 27. 训练建议

### 27.1 DQN

- discrete 5-level action；
- replay buffer；
- observation normalization；
- 先用 synthetic scenarios 训练；
- 再在 Alibaba full-trace test 上评价。

### 27.2 PPO

- continuous action 作为主版本；
- 8–16 个并行环境；
- advantage normalization；
- 5 个随机种子；
- 训练曲线之外必须看 constraint metrics。

### 27.3 SAC

- continuous Box action；
- reward normalization；
- 注意 replay buffer 对多种 scenario 的覆盖；
- 与 PPO 比较 sample efficiency 和最终稳定性。

### 27.4 训练资源

环境为小时级数值仿真，通常 CPU 就足够。推荐：

```text
RL training: CPU
GPU 0–3: hardware calibration or other research
```

不要为了“发挥服务器潜力”强行用四张 GPU 训练很小的 MLP policy。

---

## 28. 四卡服务器验证

第一篇不需要把 RL policy 实时控制服务器 7 天。最低可接受验证分两层。

### Level A：参数标定

- 运行代表性 training/offline inference workload；
- 得到平均 power、runtime、energy；
- 拟合 `workload_energy.csv`；
- 在仿真中使用。

### Level B：schedule replay

选择若干 test schedule，按控制器给出的 active-GPU fraction 在真实四卡服务器上运行代表任务，验证：

- 预测 energy 与实测 energy；
- 计划执行 GPU-hours 与实际完成 work；
- 不同 schedule 的总能耗排序。

这可以运行 6–24 h 的缩放实验，不必实时复现完整社区一周。

论文表述：

> **The virtual data-center model was calibrated and independently validated using a four-GPU RTX PRO 6000 server.**

不要表述为：

> **A full community data center was controlled in the field.**

---

## 29. 预期论文图表

### Figure 1：概念和平台架构

- community load 与 AI data center；
- rigid/flexible workload；
- compute debt；
- event、recovery 和 rebound；
- Rule/MPC/RL 共用环境。

### Figure 2：从真实 trace 到 job-derived flexibility

- Alibaba job type、GPU request、duration、priority；
- deadline/slack construction；
- 4-GPU workload energy calibration；
- static 30% envelope 与 state-dependent envelope 对比。

### Figure 3：单次事件中的 nominal reduction 与真实 window relief

同一 test episode 显示：

- community load；
- no-control PCC；
- controlled PCC；
- PCC limit/DR request；
- backlog/compute debt；
- event-only reduction；
- post-event rebound。

### Figure 4：Reliable flexibility duration curve

横轴为 event duration，纵轴为 certified reduction：

```text
F_0.90(H)
F_0.95(H)
F_0.99(H)
static 20/30/40% envelopes
```

该图应成为正文主结果之一。

### Figure 5：灵活性耗尽和恢复

- first/second/third event；
- residual flexibility ratio；
- compute debt；
- recovery time；
- inter-event gap sensitivity。

### Figure 6：控制器比较

- certified flexibility；
- window-wide peak relief；
- deadline miss；
- rebound；
- OOD failure rate。

不建议仅画 reward bar chart。

### Figure 7：跨数据集泛化

- workload dataset；
- community dataset；
- season；
- DC/community scale；
- zero-shot vs fine-tuned。

### Table 1：环境和数据定义

状态、动作、时间步、约束、deadline generation、数据源和硬件标定。

### Table 2：主 benchmark

每个 controller 的平均 KPI、95% CI 和 certificate。

### Table 3：Failure decomposition

按 delivery、deadline、rebound 和 terminal backlog 分类。

### Table 4：硬件标定与外推

workload、GPU 数、平均功率、runtime、energy、重复次数和 uncertainty interval。

## 30. 可以和不可以做出的结论

### 可以说

- AI workload flexibility is state-dependent and duration-dependent under the specified traces and deadline policies；
- nominal event reduction can differ materially from rebound-adjusted community peak relief；
- compute debt can reduce the flexibility available for subsequent events；
- static flexibility envelopes can be tested against job-derived, statistically certified capacities；
- Rule-based、MPC 和标准 RL 可以在同一 benchmark 中公平比较；
- the workload-energy model is calibrated and independently checked on a four-GPU RTX PRO 6000 server；
- Alibaba 2026 informs workload type、priority、GPU request、used GPU-hours、utilization and relative chronology。

### 不能说

- Alibaba trace 包含真实 deadline；
- 四卡实验证明了 MW 级数据中心现场可行性；
- 环境解决了配电网节点电压或线路拥塞；
- 模型实测了完整 PUE/WUE；
- RL 一定优于 MPC；
- hourly scheduling 可提供 frequency regulation；
- 本平台是第一个数据中心 RL 或 demand-response 平台；
- empirical \(F_q\) 是无条件数学保证。

### Nature Communications 风格的主结论需要满足

- 结论跨至少两个 workload 数据源成立；
- 结论跨至少两个 community profile 来源成立；
- 结论不依赖单一 RL 算法；
- static-vs-job-derived 差异有明确效应量；
- repeated-event exhaustion 和 rebound 有机制解释；
- 统计认证在完全独立 test set 上完成；
- 数据、代码、scenario manifest 和评估协议可以复现。

如果结果显示 static envelope 并未明显高估，或者 MPC 与简单规则已经达到同样 certificate，也应如实报告；这仍然可能是重要结论。

## 31. 实施路线

### P0：仓库和环境，1–2 天

- 建立目录；
- 安装依赖；
- 注册空 Gymnasium env；
- 跑 `check_env`；
- 冻结数据和 metric schema。

### P1：纯 synthetic V0，3–5 天

- synthetic community；
- synthetic arrivals；
- deadline/slack buckets；
- compute debt；
- event + recovery window；
- No-control、Threshold 和 EDF；
- 守恒与 rebound 单元测试。

### P2：Alibaba Lite，3–7 天

- 下载 1.19 GB execution summary；
- 拟合 job type、duration、GPU request 和 priority 分布；
- 生成 trace-calibrated episodes；
- 跑 static envelope comparison。

### P3：MPC 和 RL，1–2 周

- rolling LP/MPC；
- DQN；
- PPO；
- SAC；
- validation-only tuning；
- standard benchmark。

### P4：Firm-flexibility evaluator，3–7 天

- implement success criterion；
- binary/grid search over requested reduction；
- binomial lower confidence bound；
- duration curve \(F_q(H)\)；
- repeated-event stress test；
- static envelope bias。

### P5：四卡标定，1 周

- idle；
- offline inference；
- fine-tuning/training；
- runtime、average power、energy；
- schedule replay；
- uncertainty interval。

### P6：Alibaba Full 和 job-level mode，视下载和存储情况

- 下载 pod-hourly；
- DuckDB/Polars 聚合；
- chronological train/val/test；
- job reconstruction proxies；
- bucket-vs-job validation。

### P7：外部数据集，1–2 周

- Alibaba 2020 或独立 GPU trace；
- second community dataset；
- zero-shot and fine-tuned evaluation。

### P8：正式论文实验，3–6 周

- 5 RL seeds；
- 500+ independent certification episodes；
- main mechanism plots；
- effect sizes and confidence intervals；
- figure/data/code audit；
- systematic prior-art update。

### Go/No-Go milestones

**Milestone A：** synthetic V0 能否稳定体现 compute debt 和 rebound？
若不能，先修环境，不训练 RL。

**Milestone B：** static envelope 与 job-derived certificate 是否存在可解释差异？
若差异极小，论文主线应改为“条件下 static envelope 足够准确”，而不是强行制造高估结论。

**Milestone C：** repeated events 是否产生可重复的 exhaustion？
若没有，应检查 deadline policy 和 scaling 是否合理，并如实报告。

**Milestone D：** 结论能否跨数据集复现？
若不能，论文应聚焦边界条件和失效机制，而不是宣称普遍性。

## 32. 最小 Quick Start

下面的 CLI 需要按本 README 实现。完成后，标准流程应是：

```bash
# 1. 安装
uv sync

# 2. 生成可运行的 synthetic 数据
uv run aidrbench data make-community \
  --source synthetic --days 365 --peak-kw 1000 --seed 2026

uv run aidrbench data make-arrivals \
  --source synthetic --days 365 --seed 2026

# 3. 构建场景
uv run aidrbench scenarios build \
  --config configs/scenarios/synthetic_week.yaml

# 4. 检查环境
uv run aidrbench env check \
  --config configs/env/hourly_continuous.yaml

# 5. 规则控制 smoke test
uv run aidrbench benchmark \
  --controllers no_control threshold edf_valley \
  --split test --seeds 1

# 6. 训练标准 RL
uv run aidrbench train --algo ppo --env continuous --seed 1
uv run aidrbench train --algo sac --env continuous --seed 1
uv run aidrbench train --algo dqn --env discrete --seed 1

# 7. 跑统一 benchmark
uv run aidrbench benchmark \
  --controllers no_control threshold edf_valley mpc dqn ppo sac \
  --split test --seeds 1 2 3 4 5 \
  --save results/benchmark_v0

# 8. 作图
uv run aidrbench plot \
  --input results/benchmark_v0 \
  --output results/benchmark_v0/figures
```

---

完成 standard benchmark 后，继续运行核心科学分析：

```bash
# 9. 认证不同持续时间下的 firm flexibility
uv run aidrbench certify \
  --controller mpc \
  --durations 1 2 4 6 \
  --reliability 0.95 \
  --episodes 500 \
  --save results/certificates/mpc

uv run aidrbench certify \
  --controller ppo \
  --durations 1 2 4 6 \
  --reliability 0.95 \
  --episodes 500 \
  --save results/certificates/ppo

# 10. 连续事件耗尽测试
uv run aidrbench stress-test \
  --controllers threshold mpc ppo sac \
  --events-per-day 1 2 3 \
  --inter-event-gap-hours 2 4 8 12 24 \
  --save results/repeated_events

# 11. static vs job-derived envelopes
uv run aidrbench compare-envelopes \
  --static-fractions 0.20 0.30 0.40 \
  --certificates results/certificates \
  --save results/envelope_bias
```

## 33. 数据、软件和相邻研究来源

### 33.1 Primary workload data

- Alibaba Cluster Trace Program
  `https://github.com/alibaba/clusterdata`

- Alibaba Cluster Trace GPU v2026
  `https://github.com/alibaba/clusterdata/tree/master/cluster-trace-gpu-v2026`

- Alibaba v2026 schema
  `https://github.com/alibaba/clusterdata/blob/master/cluster-trace-gpu-v2026/docs/schema.md`

- Alibaba v2026 data download
  `https://github.com/alibaba/clusterdata/blob/master/cluster-trace-gpu-v2026/docs/data_download.md`

- Alibaba GPU v2020 external workload validation
  `https://github.com/alibaba/clusterdata/tree/master/cluster-trace-gpu-v2020`

### 33.2 Community data

- NREL/NLR End-Use Load Profiles
  `https://www.nrel.gov/buildings/end-use-load-profiles`

- OEDI dataset record
  `https://data.openei.org/submissions/4520`

- Low Carbon London smart-meter data
  `https://data.london.gov.uk/dataset/smartmeter-energy-consumption-data-in-london-households-vqm0d/`

- Refactored Low Carbon London dataset
  `https://doi.org/10.4121/FBBE775B-48D8-469F-A39B-B64488BFD6FD`

- SimBench time-series data
  `https://simbench.de/en/download/datasets/`

### 33.3 Software

- Gymnasium custom environments
  `https://gymnasium.farama.org/main/introduction/create_custom_env/`

- Stable-Baselines3
  `https://stable-baselines3.readthedocs.io/`

- CVXPY
  `https://www.cvxpy.org/`

- HiGHS
  `https://highs.dev/`

- DuckDB
  `https://duckdb.org/`

- uv
  `https://docs.astral.sh/uv/`

### 33.4 必须讨论的相邻研究

- Data center demand response and coincident peak avoidance
  `https://doi.org/10.1016/j.peva.2013.08.014`

- SustainDC benchmark
  `https://proceedings.neurips.cc/paper_files/paper/2024/hash/b6676756f8a935e208f394a1ba47f0bc-Abstract-Datasets_and_Benchmarks_Track.html`

- AI data centres as grid-interactive assets
  `https://www.nature.com/articles/s41560-025-01927-1`

- Flexibility-aware planner-initiated siting of data centers
  `https://www.nature.com/articles/s41467-026-72324-9`

在投稿前应再次做系统检索，新增 2026 年后续工作，并检查所有数据和代码的 license、citation、redistribution 和 derived-data 要求。

## 34. V0 与论文级完成标准

### 34.1 V0 平台完成标准

- [x] `AIDRBench-Continuous-v0` 和 `AIDRBench-Discrete-v0` 通过 `check_env`；
- [x] 计算守恒测试通过；
- [x] deadline/slack bucket 测试通过；
- [x] synthetic community 和 arrivals 可由 seed 完全复现；
- [x] compute debt、event、recovery 和 rebound 逻辑通过单元测试；
- [x] Alibaba Lite preprocessing 可运行；
- [x] No-control、Threshold、EDF-valley 和 MPC 可运行；
- [x] DQN、PPO、SAC 可训练并保存；
- [x] 所有控制器使用相同 test scenarios；
- [x] 代表周图同时显示 PCC、limit、DC power、backlog 和 compute debt。

### 34.2 Firm-flexibility evaluator 完成标准

- [x] `certify` CLI 可运行；
- [x] 支持多个 event durations；
- [x] 支持 delivery、deadline、window-wide relief、rebound、terminal backlog 联合 success criterion；
- [x] 支持 one-sided binomial confidence bound；
- [x] 支持 static-20/30/40% comparison；
- [x] 支持 repeated-event stress test；
- [x] 输出 \(F_q(H)\)、residual flexibility 和 recovery time；
- [ ] certificate 在独立 test episodes 上计算。

### 34.3 硬件标定完成标准

- [ ] 至少 3 类 workload 完成四卡功率/能耗标定；
- [ ] 每个 workload 至少 5 次重复；
- [ ] 保存原始 telemetry 和 run-level summary；
- [ ] 明确 GPU-only 与 node-level measurement 边界；
- [ ] 完成至少一组 schedule replay；
- [ ] 论文明确区分 measured GPU/node energy 与 modelled facility power。

### 34.4 高水平投稿最低标准

- [ ] 两个 workload 数据源；
- [ ] 两个 community profile 来源；
- [ ] chronological train/validation/test；
- [ ] 5 个 RL seeds；
- [ ] 500 个以上独立 certification episodes，或有充分 power analysis 的替代数量；
- [ ] bucket-vs-job-level validation；
- [ ] repeated-event exhaustion；
- [ ] static-vs-job-derived envelope comparison；
- [ ] OOD community/workload test；
- [ ] paired uncertainty analysis；
- [ ] 代码、数据 manifest、scenario seeds 和 metric implementation 全部归档；
- [ ] 不作“first platform”、配电网潮流、frequency regulation 或 MW 级 field demonstration 的过度声明。

## 35. 后续版本

完成 V0 后再按顺序扩展：

### V1：15 min + job-level scheduling

- non-preemptive jobs；
- checkpoint overhead；
- gang scheduling；
- mixed discrete-continuous actions。

### V2：快速功率响应

- GPU power cap；
- throughput/power curve；
- 秒—分钟级控制；
- inference SLA。

此时才需要更细功率和性能数据。

### V3：安全强化学习

- constrained RL；
- action projection；
- deadline and capacity guarantees；
- sim-to-real adaptation。

### V4：电网或冷却扩展

- OpenDSS feeder；
- transformer model；
- time-varying PUE；
- liquid cooling；
- carbon-aware or renewable-aware scheduling。

这些扩展应建立在 V0 的 workload conservation、scenario interface 和 benchmark protocol 上，不应一开始全部塞进第一篇论文。
