# AIDRBench：Job-derived firm DR 与社区光伏系统价值

> **文档定位**：本文件定义 AIDRBench 面向 *Nature Communications* 的主论文科学主线。它是系统与机制研究方案，不是控制算法论文，也不是强化学习 benchmark 论文。
> **核心原则**：全文只有一个主问题——AI 数据中心究竟能提供多少真实、可靠、可重复调用的需求响应；社区能够多安装和多利用多少光伏，是这部分 job-derived firm DR 的系统后果。PI/NA 是规划边界，真正的可靠可交付容量还必须由一个冻结的因果调度实现，在独立 locked-ID 场景上认证。该要求不把论文变成控制器竞赛，也不需要 RL。

正式仓库边界与权威文件顺序见 [`MAINLINE_FILES.md`](MAINLINE_FILES.md)。论文 Figure 1–5 可在 [`docs/nature-mainline-figure-preview.md`](docs/nature-mainline-figure-preview.md) 直接预览，Supplementary Figure 1–4 可在 [`docs/nature-supplementary-figure-preview.md`](docs/nature-supplementary-figure-preview.md) 预览；Source Data 与完整格式的可复现打包命令见 [`docs/paper-packaging.md`](docs/paper-packaging.md)。

---

## 1. 一句话科学命题

**AI 数据中心需求响应是一种受任务约束的有限资源；任务期限、可靠性要求和计算债务决定 firm DR capacity，而剩余的真实柔性进一步决定社区能够容纳并有效利用多少光伏。**

论文要回答的不是：

> 哪一种控制器或强化学习算法表现最好？

而是：

> AI 工作负荷中名义上“可以延迟”的部分，到底有多少能够在服务质量、恢复和可靠性约束下转化为真实的电网资源；这种资源为何会随持续时间和连续调用而衰减；经过这些筛选后，它能否扩大社区的 DC–PV 联合接入边界、提高已安装光伏的利用并减少弃光？

全文的因果链固定为：

\[
\text{deferrable AI jobs}
\rightarrow
\text{job-derived firm DR}
\rightarrow
\text{duration/reliability/debt limits}
\rightarrow
\text{community PV hosting and utilisation value}.
\]

---

## 2. 论文定位：是什么，不是什么

### 2.1 这篇论文是什么

这是一篇连接以下四个层次的系统科学研究：

1. **AI 任务层**：任务到达时间、GPU-hour 需求、工作负荷类别、运行时长和 deadline；
2. **数据中心层**：任务执行、刚性与柔性功率、积压、计算债务、恢复和反弹；
3. **社区能源层**：背景负荷、光伏、储能和 PCC/变压器容量约束；
4. **电网服务层**：可靠需求响应、灵活性耗尽和数据中心接入容量。

研究的最终产物不是某个控制器的 reward，而是一个具有物理和统计含义的：

\[
\boxed{F_q(H,N,\Theta)}
\]

其中：

- \(H\)：需求响应事件持续时间；
- \(N\)：提前通知时间；
- \(q\)：要求的可靠性水平；
- \(\Theta\)：工作负荷、deadline、历史调度、硬件功率和社区条件。

### 2.2 这篇论文不是什么

主论文不应被写成：

- DQN、PPO、SAC 的性能比较；
- 新 reward function 的算法论文；
- MPC 与 RL 的控制器竞赛；
- 一个只展示“AI 数据中心可以削峰”的案例研究；
- 一个把四卡服务器直接等同于 MW 级数据中心的硬件论文。

强化学习、CMDP、安全层和硬件在环控制不属于本篇 NC 主线，已从正式 `main` 移除；需要时可从 Git 历史恢复到独立分支，不与正式证据共存。

### 2.3 正式数据依据与 Alibaba 2026 Lite 的含义

正式 Model A 的任务形状来自 Alibaba `cluster-trace-gpu-v2026` 官方
`asi_opensource_job_execution_summary.zip`，不是 Alibaba 2020，也不是 BurstGPT。
本地链条为：1.19 GB 官方压缩包 → 40,522,321 行原始/标准化 Parquet → 本项目
生成的 100,000 行分层 sampler。所谓 `alibaba2026_lite` 是 AIDRBench 为减少重复
实验 I/O 制作的有界采样池，不是 Alibaba 发布的另一套数据；它按 seed 2026 从
低优先级 training 和 offline-inference 各抽取 50,000 行。正式协议使用该 sampler
生成 class-aware synthetic arrivals，并按预声明策略生成源数据中不存在的 deadline。

因此 Lite 保留的是任务规模、时长、类别和 GPU demand 的经验分布依据，不等于对
完整集群时间线的逐时重放，也不包含约 352 GB `pod_hourly` 档案中的时间相关性。
完整 URL、大小、预处理配置和从原始档案到正式输入的逐层 SHA-256 均记录在
[`data/manifests/sources.yaml`](data/manifests/sources.yaml)，并与正式 protocol 的
三个输入 fail closed 绑定。Alibaba 2020 与 BurstGPT 在该清单中明确标记为
`used_in_formal_mainline: false`。

一个使用不同 seed 的独立 100,000 行 reservoir 审计得到最大 KS=0.00774、median
相对误差 1.69%、95th-percentile 相对误差 0.99%，但按 reference median 归一化的
最大 Wasserstein distance 为 0.218，未通过 0.10 的工程诊断阈值。因此正式表述是
“中心与主要分位数接近，但未证明全分布或时间序列等价”，不能再写成“大数据与 Lite
没有区别”。完整审计收据见
[`data/manifests/alibaba2026_sampler_fidelity_results_v1.yaml`](data/manifests/alibaba2026_sampler_fidelity_results_v1.yaml)。

---

## 3. 现有研究缺口

许多电力系统研究将数据中心柔性写成峰值功率的固定比例：

\[
F^{\mathrm{nominal}}=\alpha P_{\mathrm{DC,peak}}.
\]

这种表示忽略了五个关键事实：

1. **任务不是任意可移的电量**：任务具有 release time、GPU-hour 需求和 deadline；
2. **持续时间会改变可行域**：能够削减 1 小时，不代表能够削减 6 小时；
3. **可靠性不是平均表现**：电网承诺要求在大量场景中稳定交付，而不是少数案例上的平均值；
4. **推迟计算不会消失**：未执行任务形成计算债务，并必须在之后恢复；
5. **灵活性具有历史依赖性**：第一次调度可能成功，但连续调用会消耗 deadline slack，并诱发恢复反弹。

同时，现有数据中心灵活性研究常停留在“可以削峰多少”，没有进一步回答：

- 这种灵活性是否能够增加数据中心的社区接入容量；
- 它和光伏、储能是互补还是替代；
- 硬件功率和 workload mix 的不确定性会否改变系统结论。

AIDRBench 的贡献应围绕这些缺口展开，而不是围绕算法排名展开。

---

## 4. 一个主问题及其系统后果

### 主问题：AI 数据中心实际能够提供多少 firm DR？

下列 Q1–Q3 不是三条并列研究主线，而是同一主问题的容量折损、状态依赖和重复调用机制。

### Q1. 名义可移负荷会高估多少可靠灵活性？

**假设 H1**：固定比例模型 \(F^{\mathrm{nominal}}\) 会系统性高估可交付容量，且高估程度随事件持续时间和可靠性要求增加而扩大。

### Q2. 持续时间、通知时间和可靠性如何共同决定灵活性？

**假设 H2**：可靠灵活性形成一个非线性的 duration–notice–reliability surface：

\[
F_q(H,N).
\]

预声明的弱单调关系为：

\[
\frac{\partial F_q}{\partial H}<0,
\qquad
\frac{\partial F_q}{\partial N}\ge 0,
\qquad
\frac{\partial F_q}{\partial q}<0.
\]

其中零 notice gain 是允许成立的结构性结果。严格正增益只是一项条件性假设：仅当通知窗口内同时存在可提前执行任务、可用空闲算力、后续服务约束具有约束力，并且因果调度确实改变执行轨迹时，才预期 \(F_q(H,N_2)>F_q(H,N_1)\)。不得通过不断增加模型复杂度来制造正结果。

### Q3. 为什么连续需求响应会耗尽 AI 灵活性？

**假设 H3**：第一次需求响应推迟任务后形成计算债务，降低后续 deadline slack，使后续事件的可持续容量下降，并增加恢复反弹：

\[
\text{DR dispatch}
\rightarrow
\text{compute debt}
\rightarrow
\text{reduced slack}
\rightarrow
\text{lower subsequent flexibility}
\rightarrow
\text{rebound}.
\]

### 系统后果：firm DR 如何改变社区光伏接入与利用？

### Q4a. 在固定数据中心容量下，社区能够多安装多少光伏？

**假设 H4a**：在相同 PCC、数据中心规模和服务约束下，workload-flexible 运行能够提高弃光约束下的 PV hosting capacity；该增益取决于社区负荷、PV 时序、BESS 和 deadline 分布。

### Q4b. 在固定光伏装机下，社区能够多利用多少光伏？

**假设 H4b**：在相同数据中心、PV、BESS、community profile 和 workload arrivals 下，workload-flexible 运行能够增加本地 PV 使用并减少弃光；但因数据中心同时增加总需求，grid-import energy 和 renewable demand share 必须单独报告，不能由“PV used 增加”直接推断。

### Q4c. AI 柔性与 PV/BESS 是互补还是替代？

**假设 H4c**：

- AI 柔性与 PV 在部分场景中互补，因为任务可在光伏富余时提前执行；
- AI 柔性与短时 BESS 可能部分替代，因为二者均可覆盖短峰值；
- 在长持续时间事件或恢复约束下，AI 柔性与 BESS 可能再次表现为互补。

固定 500 kW PV 时最大化 DC capacity 的既有 2 × 2 × 2 结果不删除；它与固定 DC 时最大化 PV capacity 的新结果是同一 joint DC–PV feasible set 的两个正交切片。

### Q5. 硬件和工作负荷不确定性是否改变机制结论？

**假设 H5**：硬件功率参数会显著改变绝对 kW 和接入容量，但“名义灵活性高估、持续时间效应和计算债务耗尽”这些机制结论应在合理不确定性范围内保持稳定。若 firm DR 不能迁移到新的社区 profile 与任务分布，其 PV hosting/utilisation benefit 也不得直接迁移。

---

## 5. 统一理论框架

主论文区分四层证据：名义假设、完美信息上界、受限场景 NA 边界，以及独立检验的因果容量证书。只固定一个因果实现用于验证，不进行控制器排名。

### 5.1 名义灵活性

\[
F^{\mathrm{nominal}}=\alpha P_{\mathrm{DC,peak}}.
\]

它代表电力系统模型中常用的静态规划假设，不考虑具体任务可行性。

### 5.2 完美信息可行边界

对场景 \(s\)，假设已知完整未来任务、负荷、PV 和事件信息，求得：

\[
F_s^{\mathrm{PI}}(H).
\]

这是当前任务和硬件模型下的物理上界。它回答：

> 在知道未来的理想条件下，任务约束本身最多允许削减多少？

为便于可靠性比较，可进一步定义跨场景的 clairvoyant firm boundary：

\[
F_q^{\mathrm{PI}}(H)
=
\max\left\{R:\Pr_s\left[F_s^{\mathrm{PI}}(H)\geq R\right]\geq q\right\}.
\]

实现时不能先在样本上选择 (R)，再把同一批样本套入 Bernoulli
置信区间。PI 分布边界使用 exact-binomial nonparametric lower tolerance
order statistic；样本量不足时报告 `estimable=false` 和 `NaN`，而不是把
容量写成 0 kW。

### 5.3 非前视可靠边界

现实决策不能看到完整未来。非前视优化要求在当时不可区分的场景中采取相同决策：

\[
x_{t,s}=x_{t,s'},
\qquad
\text{if }s\text{ and }s'\text{ are indistinguishable at time }t.
\]

理论目标是：

\[
F_q^{\mathrm{NA}}(H,N).
\]

当前优化器在有限场景集合 (S) 和预声明策略类 \(\mathcal P\) 上实际计算：

\[
F_{q,S}^{\mathrm{NA},\mathcal P}(H,N).
\]

它应表述为 **restricted scenario-based causal bound**，不能把在同一集合
上同时选择容量和失败场景所得的数值称为独立的可靠性认证，也不能把其
审计用 policy export 描述成可直接部署到 unseen locked scenario 的控制器。

它是有限场景与预声明策略类下的信息约束规划边界，而不是独立可靠性证书。它回答：

> 在给定场景集合和受限信息结构中，非前视约束会把 PI 上界压低多少？

为使这个差值具有同一统计口径，同时从集合 \(S\) 的逐场景 PI 容量定义
经验 order statistic：

\[
F_{q,S}^{\mathrm{PI,emp}}(H)
=
F_{(\lfloor(1-q)|S|\rfloor+1),S}^{\mathrm{PI}},
\]

其中右侧按容量升序排列。该值与 NA 使用相同场景、相同允许失败数，且
同样不带独立置信下界。正式 PI tolerance bound
\(F_q^{\mathrm{PI}}\) 仍单独报告，不能与经验 NA 数值直接相减后声称统计
置信度。

### 5.4 独立因果容量证书

固定一个不训练的因果 reference implementation（当前为 robust MPC），只使用当时已释放任务、当前队列、短时社区负荷预测以及已经进入 notice window 的 DR 请求。容量仅在 validation 集选择，然后在不重叠的 500 个 locked-ID episode 上一次性检验：

\[
F_q^{\mathrm{causal}}(H,N)
=
\max\{R:\underline p_{0.95}^{\mathrm{locked-ID}}(R)\ge q\}.
\]

这里的 Wilson 下界只用于预先冻结的候选容量。`locked_ood` 另行检验气候 profile 和 arrival process 外推，不用于定义主分布上的 q。

### 5.5 三个证据差距

#### 物理可行性差距

\[
\Delta_{\mathrm{physical}}
=
F^{\mathrm{nominal}}-F_q^{\mathrm{PI}}.
\]

它反映固定比例假设因为忽略任务 deadline、工作量守恒和恢复义务而产生的高估。

#### 信息与可靠性差距

\[
\Delta_{\mathrm{information},S}
=
F_{q,S}^{\mathrm{PI,emp}}-F_{q,S}^{\mathrm{NA},\mathcal P}.
\]

它是在同一有限场景集合和相同经验成功比例下，由预声明信息/策略限制
产生的描述性差距；独立统计单位是一个 frozen episode，不附带置信区间。
它不能用正式 PI tolerance bound 与同集合 NA 数值混算。

#### 实现与泛化差距

\[
\Delta_{\mathrm{implementation}}
=
F_{q,S}^{\mathrm{NA},\mathcal P}-F_q^{\mathrm{causal}}.
\]

该差距不用于比较算法优劣，而用于防止把同一场景集合上求得的 NA 数值误写成 unseen scenarios 上的可靠承诺。

### 5.6 控制算法扩展仍为可选

主线必须报告一个冻结的因果实现及其独立证书；额外的 threshold、MPC 或 RL 横向比较仍只属于 Supplementary/后续控制论文：

\[
\eta_{\mathrm{online}}
=
\frac{F_q^{\mathrm{MPC}}}{F_q^{\mathrm{NA}}}.
\]

它只用于说明理论边界具有一定在线可实现性。无需比较 DQN、PPO、SAC，更不能把在线控制器作为主创新。

---

## 6. 系统模型

### 6.1 AI 任务与队列

对工作负荷类别 \(c\)：

\[
B_{c,t+1}
=
B_{c,t}+A_{c,t}-X_{c,t}-M_{c,t},
\]

其中：

- \(A_{c,t}\)：新到达任务量；
- \(X_{c,t}\)：本时段执行量；
- \(M_{c,t}\)：因 deadline 到期而未完成的任务量；
- \(B_{c,t}\)：任务积压。

约束包括：

- release time；
- deadline；
- 每小时 GPU 执行容量；
- 任务工作量守恒；
- deadline miss 上限；
- terminal backlog 上限。

### 6.2 数据中心功率

使用工作负荷类别相关的功率模型：

\[
P_t^{\mathrm{DC}}
=
P_{\mathrm{fixed}}
+
\sum_c e_c X_{c,t},
\]

其中 \(e_c\) 来自四 GPU 服务器的硬件测量和校准。硬件 repeat 的统计单位是一次独立 workload run；同一次四卡运行中的四张卡只用于形成该 run 的均值，不能当作四个独立重复。当前 active-power 拟合只有两个独立 fit runs 和一个 held-out run，因此区间应被视为小样本不确定性，而不是高精度硬件定律；idle 仅有一个 node-level run，node fixed overhead 仍是工程假设范围。

数据来源也必须准确表述：社区负荷为 NLR/NREL EULP 建模并经实测校验的 profile，不是本项目采集的社区电表数据；任务到达为 Alibaba GPU 2026 trace-informed synthetic process，保留声明的任务特征分布但不重放生产时间线，deadline 由预声明 policy 生成；DR 事件来自配置的峰时窗口随机抽样，不是真实 utility dispatch 记录。

应同时区分：

- **reference-mix operating peak**：按参考 workload mix 得到的运行峰值；
- **worst-class/nameplate peak**：所有柔性 GPU 运行最高功率类别时的上界。

论文中的归一化容量应明确选择一种稳定定义，不能把二者混用。

### 6.3 计算债务

如果计算债务表示“延迟任务造成的额外未来能源义务”，应定义为增量功率：

\[
D_t^{\mathrm{comp}}
=
\sum_c
B_{c,t}\,
\mathrm{PUE}
\left(P_{c}^{\mathrm{active}}-P^{\mathrm{idle}}\right).
\]

如果使用 gross service energy，则必须明确改名，不能同时声称排除了 idle pool。

### 6.4 社区 PCC 功率

\[
P_t^{\mathrm{PCC}}
=
L_t
+P_t^{\mathrm{DC}}
+P_t^{\mathrm{ch}}
-P_t^{\mathrm{dis}}
-G_t^{\mathrm{PV}},
\]

并满足：

\[
P_t^{\mathrm{PCC}}
\leq
K^{\mathrm{PCC}}.
\]

其中：

- \(L_t\)：不含数据中心的社区背景负荷；
- \(G_t^{\mathrm{PV}}\)：本地使用的光伏功率；
- \(P_t^{\mathrm{ch}},P_t^{\mathrm{dis}}\)：储能充放电功率；
- \(K^{\mathrm{PCC}}\)：PCC 或变压器容量。

---

## 7. 可靠灵活性定义

### 7.1 主分析：单事件独立 episode

为了清楚识别 duration、notice 和 reliability 的作用，主 firm-capacity surface 使用：

> 每个 episode 只设置一个需求响应事件，每个 episode 是一个独立 Bernoulli trial。

候选容量 \(R\) 成功，必须同时满足：

1. 事件平均交付：

\[
\eta_e^{\mathrm{mean}}\geq0.95;
\]

2. 每个小时交付：

\[
P_t^{\mathrm{control}}
\leq
P_t^{\mathrm{baseline}}-0.95R,
\quad \forall t\in\mathcal E;
\]

3. deadline miss rate 不超过阈值；
4. rebound ratio 不超过阈值；
5. event-plus-recovery window 的峰值 relief 达到阈值；
6. terminal backlog 不超过阈值。

可靠容量定义为：

\[
F_q(H,N)
=
\max\left\{R:\underline p_{0.95}(R)\geq q\right\},
\]

其中 \(\underline p_{0.95}\) 是针对**预先固定候选容量**的一侧 Wilson
置信下界。若容量本身由同一批 PI 样本选择，则改用精确非参数 tolerance
bound；NA ensemble optimization 单独报告为受限场景边界。

### 7.2 重复事件：单独的耗尽机制实验

重复事件不应与主 duration surface 混在一起，而应作为独立 Result：

- 每个 episode 包含多个事件；
- 同一 episode 中所有事件成功，episode 才算成功；
- 事件行不能被当作独立统计样本；
- 主要变量为事件次数、事件间隔、恢复窗口和前次计算债务。

定义第 \(j\) 次事件的剩余灵活性：

\[
\rho_j
=
\frac{F_j}{F_1}.
\]

并研究：

\[
\rho_j=f(j,\text{gap},H,\text{deadline policy},D_{j-1}^{\mathrm{comp}}).
\]

---

## 8. Nature Communications 主文 Results 结构

## Result 1 — 名义可移负荷高估 job-derived firm capacity

### 科学问题

固定比例 \(\alpha P_{\mathrm{DC,peak}}\) 与真实任务可行性之间存在多大差距？

### 分析内容

- 首先比较 \(F^{\mathrm{nominal}}\) 与 \(F_q^{\mathrm{PI}}\)，报告任务约束造成的定量折损；
- 再用任务 arrival、GPU-hour、deadline 和类别功率解释该差距；
- 区分 nominal、PI、restricted NA 和 fixed causal realization 四层容量；
- 四 GPU 功率测量与 held-out validation 仅作为功率模型锚点，原始曲线进入 Supplementary。

### 当前定量结果

Model A 的 reference-mix operating peak 为 201.00 kW，因此预声明的 50%
nominal proxy 为 100.50 kW。100 个 development frozen scenarios 上，q=0.95、
95% confidence 的 exact-binomial PI tolerance lower bound 为：

| Duration | Nominal / kW | PI firm bound / kW | Nominal overstatement / kW | Overstatement / nominal |
|---:|---:|---:|---:|---:|
| 1 h | 100.50 | 53.01 | 47.50 | 47.3% |
| 2 h | 100.50 | 44.46 | 56.04 | 55.8% |
| 3 h | 100.50 | 41.19 | 59.31 | 59.0% |
| 4 h | 100.50 | 40.15 | 60.35 | 60.1% |
| 6 h | 100.50 | 40.15 | 60.35 | 60.1% |
| 8 h | 100.50 | 37.76 | 62.74 | 62.4% |

因此 nominal proxy 在测试持续时间内高估 job-derived PI bound 的幅度为
47.50--62.74 kW，即 nominal 的 47.3--62.4%。PI 是知道完整未来的物理规划
上界，尚且只有 nominal 的 37.6--52.7%；这使“不能把可移负荷比例直接当作
firm DR 容量”成为可量化结果，而不只是概念判断。完整输入与结果哈希见
[`data/manifests/nature_mainline_nominal_gap_results_v1.yaml`](data/manifests/nature_mainline_nominal_gap_results_v1.yaml)。

### 预期结论

名义柔性不能直接作为电网资源；deadline 与功率结构会产生显著的物理可行性差距。

### 对应主图

**Figure 1：Nominal-to-job-derived firm-capacity gap**

- a：名义容量与 job-derived PI tolerance lower bound 的定量差距；
- b：任务 arrival–deadline–execution 关系；
- c：任务调度到 DC/PCC 功率；
- d：nominal、PI、restricted NA 与 causal 四层证据关系。

---

## Result 2 — 持续时间、通知时间和可靠性共同塑造 firm-flexibility surface

### 科学问题

可靠灵活性如何随 \(H\)、\(N\) 和 \(q\) 变化？

### 分析内容

计算：

\[
F_q^{\mathrm{PI}}(H),
\qquad
F_{q,S}^{\mathrm{NA},\mathcal P}(H,N),
\qquad
F_q^{\mathrm{causal}}(H,N).
\]

核心网格：

- duration：1、2、3、4、6、8 h；
- notice：0、2、6 h；
- reliability：90%、95%、99%；
- workload utilization：低、参考、高；
- deadline policy：宽松、参考、严格。

### 预期结论

- 短事件受动态功率上限约束；
- 长事件逐渐转为 deadline 和总计算量约束；
- 提前通知的容量价值允许为零；只有在可提前执行工作、空闲算力和约束条件同时满足时，才可能通过预执行增加 slack；
- 更高可靠性要求显著压低可承诺容量。

### 对应主图

**Figure 2：Nominal-to-firm flexibility surface**

- a：不同 duration 下的 \(F^{\mathrm{nominal}}\)、\(F_q^{\mathrm{PI}}\)、\(F_{q,S}^{\mathrm{NA},\mathcal P}\) 与 \(F_q^{\mathrm{causal}}\)；
- b：duration–notice heatmap；
- c：不同 reliability 水平的 capacity curves；
- d：physical gap 与 information gap 分解。

---

## Result 3 — 计算债务导致灵活性耗尽和恢复反弹

### 科学问题

为什么第一次可以成功的需求响应，在连续调用后会失效？

### 分析内容

- 单次事件前后 backlog、deadline slack 和 compute debt；
- 不同事件间隔下的第二、第三、第四次可持续容量；
- 每次重复事件与同一 frozen scenario、同一时刻的 fresh single-event
  counterfactual 配对，避免把社区时段差异误判为历史耗尽；
- 恢复过程中的 PCC rebound；
- 计算债务与剩余灵活性的关联；
- event duration 与 recovery gap 的交互作用。

事件局部的 delivery、interval delivery、rebound 和 window relief 与联合
episode 的 deadline miss、terminal backlog 分开报告。joint-episode success
是重复事件主统计单位；固定容量下的配对交付比只是机制诊断，不得写成
event-wise firm-capacity certificate。

### 当前 development 与 validation 结果

100 个 nominal development scenarios 上的完整 H × recovery-gap 配对实验已
完成。到第 4 次事件，平均配对 compute-debt increment 为 0.58–1.37 MWh，
但相对同场景、同钟点 fresh event 的 p05 residual flexibility ratio 仍为
0.9897–1.0000。也就是说，当前 Model A 中首先积累的是计算债务和服务风险，
不是瞬时削峰功率的大幅消失。

joint-episode success 随 H/gap 在 0.00–0.94 之间变化。H=8、gap=24 h 时
四次事件几乎铺满 7 天主时域，100/100 episodes 都违反联合 deadline 服务
阈值，尽管第 4 次事件的 p05 配对交付仍为 fresh event 的 98.97%。因此结果
不能写成“恢复间隔越长必然恢复越好”：只有空档内存在可用计算余量时，时间
间隔才能偿还 compute debt。当前结果是 fixed-capacity mechanism diagnostic，
不是 repeated-event firm-capacity certificate，也尚未经过 locked evaluation。

独立 validation 规格随后在提交 `097ff89` 上按预注册 seeds 20000–20099
完成，固定沿用 development 的 H=4（44.00 kW）和 H=8（41.19 kW）承诺，
未在 validation 上重新选容量。100 个独立 seeds、10 个 H × gap programs
共得到 1,000 个联合 episode 和 4,000 个事件结果。第 4 次事件的配对
compute-debt increment 为 0.55–1.38 MWh，而 residual flexibility ratio 仍为
0.9910–1.0000；跨 gap 平均债务到第 4 次分别增至 H=4 的 0.75 MWh 和
H=8 的 1.14 MWh。四事件 joint success 为 0.00–0.97；只有 H=4、gap=8 h
的经验成功率达到 0.95，但其单侧 95% Wilson 下界为 0.927，因此没有任何单元
可被误写成 q=0.95 repeated-event 容量证书。该独立结果支持“服务债务先于
功率能力耗尽”的有限机制解释。逐单元结果、描述性 development–validation
一致性和完整哈希回执见
[`data/manifests/nature_mainline_validation_exhaustion_results_v1.yaml`](data/manifests/nature_mainline_validation_exhaustion_results_v1.yaml)。

### 预期结论

需求响应不是无成本地“删除”电量，而是将计算义务转移到未来；连续调用造成可量化的资源耗尽。

### 对应主图

**Figure 3：Compute-debt-driven exhaustion**

- a：代表性任务队列和功率轨迹；
- b：compute debt 随时间变化；
- c：第 \(j\) 次事件的 residual flexibility ratio；
- d：recovery gap–event count response surface；
- e：rebound 与计算债务的关系。

---

## Result 4 — Job-feasible flexibility reshapes the joint data-centre–PV hosting boundary

### 科学问题与证据逻辑

经过任务约束、可靠性和重复调用检验后，剩余的数据中心柔性对社区可再生能源
系统有什么价值？本节只回答两个相互衔接的后果：

1. **规划后果**：在固定 DC、PCC 和 BESS 下，社区能够多安装多少具有实际利用
   价值的 PV；
2. **运行后果**：在固定 DC 和 PV 装机下，社区能够多使用多少 PV、少弃多少光，
   并怎样改变购电、PCC 峰值和可再生能源占比。

这不是另起一条 PV benchmark 主线。所有 renewable-integration 结果都由同一
job-derived workload/service model 推导，是 DR 主问题的下游系统后果。

### Result 4.1 — 弃光约束下的 PV 接入容量

在给定 DC scale 与 BESS 条件下定义：

\[
P_{\mathrm{PV,host}}(\epsilon)=
\max P_{\mathrm{PV,rated}}
\quad\text{s.t.}\quad
\frac{E_{\mathrm{PV,curtailed}}}{E_{\mathrm{PV,available}}}\leq\epsilon.
\]

优化同时满足 PCC import 上限、禁止反向潮流、GPU-hour 守恒、deadline miss 与
terminal backlog 阈值以及 BESS terminal SOC。Headline 固定
\(\epsilon=5\%\)，并预声明 \(0\%\)、\(10\%\)、\(20\%\) 敏感性。Rigid 与
flexible 使用完全相同的 arrivals 和 community profile，比较：

\[
\Delta P_{\mathrm{PV}}^{\mathrm{DR}}
=P_{\mathrm{PV,host}}^{\mathrm{flexible}}
-P_{\mathrm{PV,host}}^{\mathrm{rigid}}.
\]

DC 取 reference mix 的 0.5、1、2、3 倍，形成四条 joint DC–PV hosting
envelopes：rigid/flexible × BESS off/on。独立单位仍为 frozen scenario；共同
可行 headline 是 100 个场景最优 PV capacity 的最小值，场景内
flexible–rigid contrasts 使用预声明的 Bonferroni simultaneous intervals。

**Development 结果（100 scenarios）**：在 1× DC 下，5% 弃光 headline 的
simultaneous PV capacity 为 430.45→525.74 kW（无 BESS）和
482.65→585.91 kW（有 BESS）。相应的场景内 paired mean gains 为 45.66 kW
（Bonferroni 95% simultaneous CI [42.24, 49.48]）和 43.35 kW
（[39.76, 47.32]）。这两个 estimands 不可混用：前者是两个 ensemble minima
的差，后者是先做场景内差值再取均值。

**独立 validation 复现（100 scenarios）**：1× DC 的 simultaneous PV capacity
为 584.69→617.52 kW（无 BESS）和 653.39→686.77 kW（有 BESS）；paired mean
gains 分别为 44.85 kW（[41.68, 48.08]）和 43.20 kW
（[39.99, 46.46]）。因此正的 PV-hosting gain 在两个 BESS strata 上独立复现，
但绝对 simultaneous capacity 随 validation community profiles 改变，不能把
development 的容量值直接迁移过去。

联合边界也揭示了 feasibility transition：2× DC 时 flexible 的两个 BESS
条件均为 100/100 可行，而 rigid 仅为 95/100 和 96/100；3× DC 时只有
flexible+BESS 达到 100/100。部分可行条件只作为描述性 `n/100` 点，不报告
simultaneous capacity。0/10/20% 弃光 sensitivity 均已保留，不能由 5%
headline 代替。

Validation 的 transition 更清楚：0.5×、1× 和 2× 的四种运行条件均为
100/100 可行；3× 时 flexible 在无/有 BESS 下仍为 100/100，而 rigid 仅为
31/100 和 96/100。这里的 `31/100` 与 `96/100` 是部分可行计数，不是 0 kW
capacity。3× validation simultaneous PV capacity 只对 flexible 条件定义，
分别为 1,120.85 kW 和 1,190.87 kW。

### Result 4.2 — 固定装机下的 PV 利用与弃光

固定 1× reference DC（约 201 kW）、500 kW PV、同一 BESS、community profile
和 workload arrivals，只改变 rigid/flexible 调度。采用显式词典序目标：先最大化
PV use，再最小化 grid import，最后最小化 BESS throughput；BESS 使用二进制
互斥约束，禁止通过同时充放电人为消纳 PV。必须同时报告：

- PV available、used 和 curtailed energy；
- PV utilisation fraction 与 renewable demand share；
- grid-import energy、maximum PCC import 和 near-limit hours；
- BESS charge/discharge throughput；
- deadline miss 与 terminal backlog。

不能只凭 PV used 增加就声称可再生能源占比提高，因为数据中心本身也增加总需求。

**Development 结果（固定 500 kW PV）**：平均 available PV 为约 27.40 MWh。
无 BESS 时 flexible 相比 rigid 多使用 182.69 kWh、少弃 182.69 kWh，PV
utilisation 增加 0.7335 percentage points，renewable demand share 增加
0.2612 points，grid import 减少 344.64 kWh；有 BESS 时相应变化为
+87.48 kWh、−87.48 kWh、+0.3518 points、+0.1505 points 和 −260.42 kWh。
10 个预声明 contrasts 的 simultaneous intervals 对上述五项方向均不跨零。

**Validation 复现（固定 500 kW PV）**：无 BESS 时 flexible 多使用 18.37 kWh
PV（[3.73, 40.03]）、少弃 18.37 kWh，utilisation 增加 0.0720 percentage
points（[0.0154, 0.1610]）；有 BESS 时只多使用 5.76 kWh
（[0.000003, 15.86]），utilisation 增加 0.0227 points，区间下界接近 0。
方向与 development 一致，但效应量显著变小，说明固定装机 PV benefit 强烈依赖
community profile 与既有 BESS，而不能只报告符号。Validation 的 renewable
demand share 分别增加 0.0577 和 0.0443 points；grid import 分别减少 180.32
和 168.98 kWh，但后者不能全部归因于时间转移，因为 flexible 解同时使用了允许的
1% deadline-miss budget。

该收益不能改写成“PCC peak 同时下降”：development mean maximum PCC import
反而从 618.08 增至 624.62 kW（无 BESS）和 625.17 kW（有 BESS）。此外，
flexible 解使用了允许的 1% deadline-miss budget，rigid baseline 为 0%；两者
terminal backlog 均为 0。主文必须把 energy benefit、capacity effect 和 service
budget 分开陈述。

为排除这一服务质量混杂，项目又在全部 100 个 development 和 100 个 validation
情景上，把 deadline miss 严格固定为 0，重新求解 reference-scale PV hosting 与固定
500 kW PV 两类问题。共 1,600 行结果全部 optimal，最大 deadline-missed work 为
0 GPU-h。Validation 的 all-scenario PV-hosting gain 仍为 32.825 kW（无 BESS）和
33.377 kW（有 BESS），与 1% 版本在报告精度内相同；paired mean hosting gain 的
变化小于 0.002 kW，固定 PV-use gain 的变化小于 0.000006 kWh。因此本文的 renewable
planning 结果并不是通过牺牲 deadline service 换来的。该检查仍然是 PI planning
sensitivity，不是 causal controller certificate，也未读取 locked-ID/OOD。

### Result 4.3 — 同一联合可行域的正交切片与资源交互

既有 2 × 2 × 2 结果固定 500 kW PV、最大化 DC capacity；新结果固定 DC、
最大化 PV capacity。二者是同一 feasible set
\(\mathcal{F}=\{(P_{\mathrm{DC}},P_{\mathrm{PV}})\}\) 的正交切片，原结果保留为
Figure 4 交互机制证据，不再单独承担 renewable-integration headline。

既有独立 validation 显示，AI×PV 在无 BESS 时为 +44.59 kW
（95% simultaneous CI [36.57, 52.63] kW）；有 BESS 时为 +8.36 kW
（[1.05, 15.74] kW），方向为正但实际幅度不确定。AI×BESS 在无/有 PV 时
分别为 −52.31 与 −88.54 kW，支持 workload flexibility 与电池部分替代。
完整旧切片回执见
[`data/manifests/nature_mainline_validation_hosting_results_v1.yaml`](data/manifests/nature_mainline_validation_hosting_results_v1.yaml)。

### 证据边界

新增 PV hosting/utilisation 是 development 与独立 validation planning-result
ensembles，不是 deployed causal effect，也不把单事件 locked-ID certificate
自动外推成 renewable-integration certificate。若社区 profile 与任务分布改变，
必须先重新验证当地 firm DR envelope，再解释 PV benefit。
完整设计与运行后哈希回执见
[`data/manifests/nature_renewable_integration_results_v1.yaml`](data/manifests/nature_renewable_integration_results_v1.yaml)。

### 对应主图

**Figure 4：Firm DR as a community renewable-integration resource**

- a：joint DC–PV hosting envelope（主面板）；
- b：固定约 201 kW DC 时的 curtailment-constrained PV capacity；
- c：固定 500 kW PV 时的 utilisation、curtailment 和 grid import；
- d：既有 AI×PV 与 AI×BESS interaction estimates。

---

## Result 5 — 独立评估定义稳健性与泛化边界

### 科学问题

绝对功率参数变化后，主要机制是否仍成立？

### 分析内容

- calibration lower / nominal / upper uncertainty bounds；
- node fixed overhead sensitivity；
- PUE sensitivity；
- workload mix sensitivity；
- deadline distribution sensitivity；
- reference-mix peak 与 worst-class peak；
- fluid scheduling 与更严格任务约束的敏感性。

### 当前 development 结果

Sparse workload schema 的 no-DR service gate 已在 9 个 cases × 3 个 seeds 上
完成，27/27 baseline evaluations 均为零 deadline miss 和零 terminal backlog。
配对的 sparse-workload PI 已在 9 个 cases × 100 个共同 development seeds、
H={4,8} 上完成，1,800/1,800 programs 为 `optimal`；全部 900 个冻结场景的
no-DR baseline 也均为零 deadline miss 和零 terminal backlog。

在 q=0.95、confidence=0.95 下，将 flexible arrival utilization 从 0.65
降低到 0.50，使 H=4/H=8 firm boundary 从 40.15/37.76 kW 降至
30.88/29.05 kW；提高到 0.80 后升至 77.99/53.49 kW。预声明的 rigid
utilization 和 deadline-slack 变化不改变边界，两个组合点也分别等于对应的
arrival-only case。rigid load 在相对 baseline 的单事件削减量中作为共同加性
项相消，但仍会影响 PCC headroom 与 hosting；deadline 零效应仅限 Model A
的这些稀疏测试点。结果均为 development PI bounds，不是 causal 或 locked
generalization certificate。
Success-criteria sensitivity 使用 one-factor-at-a-time 设计，而不是 3⁴ 笛卡尔
积；100 个 frozen scenarios、H={4,8} 和 9 个 criteria cases 共形成 1,800 个
`optimal` PI solves。

在 q=0.95、confidence=0.95 下，reference capacities 为 H=4 的 40.15 kW
和 H=8 的 37.76 kW。将 linked mean/minimum-interval delivery threshold 放宽到
0.90 后分别变为 42.38 和 39.86 kW，收紧到 0.98 后分别变为 38.92 和
36.60 kW。预声明的 deadline-miss、rebound 和 window-relief threshold 变化在
这两个点上不改变容量。这说明 delivery definition 是当前 development PI
容量的设置约束；结果不是 causal 或 locked certificate。精确数值和 SHA-256
记录在 `data/manifests/nature_mainline_development_results_v1.yaml`。

PUE 与 node fixed overhead 使用单独的 5 点 sparse OAT 设计，不与 GPU
active/idle power uncertainty 做笛卡尔积：reference 为 PUE=1.20、overhead=
300 W；另设 PUE=1.10/1.30 和 calibration artifact 中的 overhead=150/450 W。
所有 case 固定 144 个节点和 nominal GPU 功率，只改变一个基础设施因素。
正式分析已在干净提交 `f305224` 上完成：15/15 preliminary no-DR gate 与
500/500 frozen-scenario service audit 均通过，1,000/1,000 H={4,8} PI programs
均为 `optimal`。PUE=1.10/1.30 使绝对 firm capacity 相对 nominal 精确变化
−8.33%/+8.33%，但 capacity/operating-peak 比例不变。node overhead=150/450 W
不改变 baseline-relative firm kW，因为该固定加性项在 controlled 与 baseline
之差中相消；不过 operating peak 相对 nominal 变化 −12.90%/+12.90%，所以会
改变归一化 flexibility 与社区 headroom。该零效应只属于单事件相对削减指标，
不能外推为 hosting capacity 不受影响。完整回执见
[`data/manifests/nature_mainline_infrastructure_sensitivity_results_v1.yaml`](data/manifests/nature_mainline_infrastructure_sensitivity_results_v1.yaml)。

### 当前结论

绝对 kW 与归一化比例对硬件和基础设施参数的响应不同；duration ordering 在
当前 development sensitivity 中保持不变。独立 locked-OOD 检验进一步表明，
Model A 上 validation-selected 的固定候选不能直接外推到联合 community-profile
与 arrival-process shift；这限定了 causal certificate 的适用域，而不是重新估计
OOD 容量。

为避免把联合 OOD 结果误归因于“地理位置”，新增了严格配对的 community-profile
单因素 sensitivity：EULP 3A、3C、5A 三个气候区原型保持相同的任务 arrivals、
deadlines、硬件、事件流和随机种子，只替换社区负荷/PV 时序。3 cases × 3 seeds
的 no-DR gate 全部通过；随后 3 × 100 个 development frozen scenarios 的
q=0.95 PI 容量在 H={1,2,3,4,6,8} 上均为
{53.01,44.46,41.19,40.15,40.15,37.76} kW，三个 profile 的正式 tolerance
boundary 在数值精度内完全一致。固定 validation-selected robust-MPC candidate
在 H=4/H=8 上也分别都是 98/100 和 97/100 success。由此只能得出：在当前
Model A 中 community profile 单独变化不是 job-derived firm capacity 的 binding
因素；此前 locked-OOD 下降不能归因于 community shift alone，也不能在未做
arrival-only attribution experiment 时反称全部来自 arrival process。

相同 300 个 paired scenarios 的 reference-scale PV-hosting slice 也已完成：
rigid/flexible × BESS off/on 共 1,200/1,200 个 `optimal` programs。无 BESS
时 3A/3C/5A 的 all-scenario rigid→flexible boundary 分别为
430.45→525.74、603.52→667.04、506.17→585.41 kW；有 BESS 时为
482.65→585.91、668.56→726.91、558.40→639.27 kW。六个配对 mean gain
为 42.35–45.66 kW，Bonferroni 95% simultaneous intervals 均不跨 0。
因此 community profile 在本设计中不改变 job-derived firm capacity，却明显
改变绝对 PV-hosting boundary 及其 worst-scenario flexibility increment。这是
development PI planning sensitivity，不是具名地域的 causal effect。

### 对应主图

**Figure 5：Robustness, certification and generalization**

- a：不同硬件功率 case 下的 firm frontier；
- b：不同 workload/deadline 场景的机制一致性；
- c：validation-to-locked-ID 的独立容量认证；
- d：locked-OOD 下的失效边界。

**Figure 6：Community-profile sensitivity and system consequence**

- a：EULP 3A/3C/5A 气候区原型的代表性一周净社区负荷；
- b：严格配对的 q=0.95 PI firm-capacity curves；
- c：固定 robust-MPC candidate 的 development transfer diagnostic；
- d：相同 profile 下 rigid/flexible、BESS on/off 的 PV-hosting boundary。

Figure 6 不使用无法由数据支持的“城市地图”。三个 profile 是气候区负荷原型，
不是具名城市、地理编码数据中心或实测馈线；其中 firm/controller 结果是
development sensitivity，PV hosting 是 PI planning bound。

---

## 9. 方法与代码模块映射

| NC 主线任务 | 所需代码模块 | 是否属于主论文 |
|---|---|---:|
| 硬件功率校准 | calibration artifact、power model | 是 |
| 任务 arrival/deadline 建模 | Alibaba 2026 sampler、hourly deadline buckets | 是 |
| Frozen scenario | scenario freeze、hash/provenance | 是 |
| PI frontier | perfect-information optimizer | 是 |
| 非前视 firm frontier | non-anticipative optimization | 是 |
| 单事件可靠容量 | frozen robust-MPC selection + locked-ID certification | 是 |
| 重复事件耗尽 | repeated-event stress test | 是 |
| Hosting capacity | PV/BESS/PCC optimization | 是 |
| 参数不确定性 | lower/nominal/upper uncertainty bounds | 是 |
| Rule/MPC smoke test | software validation | 否，最多补充材料 |

**重要区分**：非前视优化给出受限场景规划边界；只有独立 locked-ID 上的固定因果候选才能称为容量证书。这一验证不等于控制器竞赛。

---

## 10. 实验设计

### 10.1 基准归一化系统

以 PCC 容量为基准：

\[
K^{\mathrm{PCC}}=1\ \mathrm{p.u.}
\]

参考组合：

```yaml
community:
  pcc_capacity_pu: 1.0

datacenter:
  peak_capacity_pu: 0.20

pv:
  rated_capacity_pu: 0.50

battery:
  power_capacity_pu: 0.10
  duration_hours: 2
```

该组合只用于解释，不应被描述为普遍物理事实。

### 10.2 Response-surface 参数

#### 数据中心

\[
\gamma_{\mathrm{DC}}
\in
\{0.05,0.10,0.20,0.30,0.40\}.
\]

#### 光伏

\[
\gamma_{\mathrm{PV}}
\in[0,1.0].
\]

#### 储能

\[
\gamma_{\mathrm{B,P}}
\in[0,0.20],
\qquad
h_{\mathrm{BESS}}
\in\{1,2,4\}\ \mathrm{h}.
\]

#### 需求响应

- duration：1、2、3、4、6、8 h；
- notice：0、2、6 h；
- reliability：90%、95%、99%；
- event count：1、2、3、4；
- recovery gap：2、4、8、12、24 h。

#### 工作负荷

- utilization：低、参考、高；
- deadline：宽松、参考、严格；
- training/offline-inference mix；
- arrival burstiness；
- hardware power case。

响应面不建议使用完整笛卡尔积。可以采用 sparse factorial design 或 Latin hypercube，并保留预先指定的核心情景矩阵。

---

## 11. 数据划分与统计原则

### 11.1 主论文不需要 RL training split

NC 主线的数据划分应围绕模型校准和最终评估，而不是围绕 controller training：

1. **Calibration fit set**：拟合功率参数；
2. **Calibration held-out set**：检验功率模型；
3. **Scenario development set**：确定模型和实验设计；
4. **Validation scenario set**：检查数值稳定性、冻结因果策略与候选容量；
5. **Locked-ID scenario set**：同一目标生成分布的最终可靠性证书，500 个 episode 支持 q=0.99 的预声明检验；
6. **Locked-OOD scenario set**：气候 profile 与 arrival process 改变后的稳健性和外推评估，不能替代 locked-ID 主证书。

### 11.2 统计单位

- 单事件主分析：一个 episode 是一个独立 trial；
- 重复事件分析：一个包含多个事件的 episode 是一个独立 trial；
- 同一 episode 内的多个事件不能作为独立样本；
- hardware repeat 应以独立 run 为统计单位，不能把同一次四卡运行中的四张 GPU 当成四个完全独立实验。

### 11.3 报告要求

每个正式结果记录：

```text
git commit
scenario hash
input-data hashes
calibration-artifact hash
hardware power case
protocol version
evaluation seed range
event duration and notice
reliability target
portfolio definition
fixed-candidate success count and confidence bound, or PI tolerance rank
failure reasons
solver and tolerances
```

---

## 12. 因果实现与控制器在这篇论文中的正确位置

### 12.1 主文

主文不需要完整控制器 benchmark，但需要一个冻结、可部署的因果 reference implementation 在独立 locked-ID 场景上验证可交付容量。当前预声明为 robust MPC；不训练、不调 reward、不参与算法排名。

正式控制器必须由 `configs/controller/nature_robust_mpc_v1.yaml` 完整定义。validation selection 固化规范化配置及其 SHA-256、原始 YAML SHA-256、Git commit 和控制/评估路径源码 hash；locked-ID replay 必须逐项重新验证，任意不一致均 fail closed。容量搜索使用预声明细网格或 binary search，不使用 0.1 fraction 粗网格作为容量结论。

### 12.2 Supplementary 可选内容

可以额外增加简短的在线实现对照：

- 一个 threshold rule；
- 一个因果 MPC；
- 相同场景和相同物理约束；
- 报告它们实现 \(F_q^{\mathrm{NA}}\) 的比例。

这一部分只回答：

> 理论定义的 firm frontier 是否完全脱离实际在线实现？

### 12.3 不进入本篇主线的内容

以下内容不进入正式 `main`，旧实现仅由 Git 历史保存：

- DQN、PPO、SAC；
- CMDP reward v1–v5；
- controller checkpoint selection；
- safety layer；
- aggregate action 与 class-specific actuation；
- HIL 和实时控制。

后续控制论文可以命名为：

> **Safe online realization of firm AI data-centre flexibility under compute-debt and rebound constraints**

---

## 13. 正式仓库边界

`main` 只包含可复现本篇论文所需的协议、校准证据、冻结场景逻辑、优化与因果认证、论文、Source Data 合同、图件和测试。精确索引见 [`MAINLINE_FILES.md`](MAINLINE_FILES.md)。

旧版 63.52 kW、68.86 kW、firm_v4、RL/CMDP、HIL 与跨 GPU 型号外推不再以并行文档或配置保留在工作树中，避免旧结论再次混入当前证据；它们仍可从 Git 历史审计和恢复。

---

## 14. 主论文建议标题与贡献表述

### 工作标题

**Job constraints define firm data-centre demand response and photovoltaic hosting limits**

### 三句话贡献

> First, we replace exogenous flexible-load fractions with job-derived firm-flexibility envelopes that jointly account for interval delivery, workload deadlines, recovery and rebound.

> Second, we separate a population-level perfect-information tolerance lower bound, an empirical non-anticipative planning boundary and a distribution-specific causal certificate.

> Third, we reveal compute debt as the mechanism of state-dependent repeatability and show that job-feasible planning reshapes the joint data-centre–PV hosting boundary.

### 主结论应落在这里

\[
\boxed{
\text{AI workload flexibility is a finite, state-dependent and distribution-specific power commitment.}
}
\]

而不是：

\[
\boxed{
\text{One RL algorithm outperforms another.}
}
\]

---

## 15. 建议的执行顺序

### Phase 0 — 冻结论文范围

- 明确本篇 NC 不以控制器为主线；
- 从正式主线移除 RL/CMDP/HIL 与跨 GPU 型号外推；
- 修正 README 与当前实现不一致的问题。

### Phase 1 — 冻结物理与数据模型

- 补齐所有 workload class 的功率参数；
- 区分 reference-mix peak 和 worst-class peak；
- 修正 compute-debt 定义；
- 完成 calibration uncertainty cases；
- 冻结数据、场景和 hash。

### Phase 2 — 计算单事件 firm-flexibility surface

- duration × notice × reliability；
- nominal、PI、NA 三层边界；
- workload utilization 和 deadline sensitivity。

### Phase 3 — 计算 repeated-event exhaustion

- event count；
- recovery gap；
- compute debt；
- residual flexibility；
- rebound。

Development 与 validation 使用独立规格。Validation 固定使用 development Model A
承诺，不在 validation 上重新选择 repeated-event 容量；规格绑定环境/controller
SHA-256 和完整 seeds 20000--20099。

### Phase 4 — 将 firm DR 映射为社区光伏系统价值

- joint DC–PV hosting envelope；
- curtailment-constrained PV hosting capacity；
- fixed-capacity PV utilisation、curtailment、grid import 与 PCC peak；
- 保留既有 2 × 2 × 2 DC-hosting slice，统一解释 PV/BESS interaction。

既有固定 PV、求最大 DC 的 development/validation 100-scenario 配对矩阵已经
完成。固定 DC、求最大 PV 与固定 DC/PV、求实际利用的正交分析使用冻结的
Model A 和独立 development/validation 规格运行；不读取 locked 数据，也不在
validation 上重新选择 DC/PV/BESS 条件。

### Phase 5 — 稳健性和外推

- 硬件 lower/nominal/upper uncertainty bounds；
- PUE 和 node overhead；
- workload mix；
- deadline distribution；
- locked OOD communities。

当前状态：power-case PI、success-criteria、sparse-workload 与 sparse
infrastructure PI sensitivities 已完成。100 个 validation scenarios 已通过集合级 hash/service
audit，并在提交 `5889405` 上完成 q={0.90,0.95,0.99} 的 frozen robust-MPC
capacity selection。随后一次性生成并评估了 500 个 locked-ID episodes；授权已
消费，500 个场景、2,000 个 payload 文件及 controller/source/git provenance
均通过哈希审计。headline q=0.95 在 H={2,3,4,6,8}、N={0,2,6} 的 15 个
单元达到一侧 95% Wilson 门槛；H=1 的 validation-selected 55.16 kW 候选为
477/500、Wilson 下界 0.936，不能称为 q=0.95 certified。q=0.90 与 q=0.99
分别有 15/18 和 9/18 个单元通过，作为 secondary sensitivity。三个 q 下同一
duration 的 N={0,2,6} 容量均相同，zero notice gain 被保留为结构性结果。
完整机器可读审计见 `data/manifests/nature_mainline_locked_id_results_v1.yaml`。

经单独明确授权后，500 个 locked-OOD episodes 已一次性生成，500 个场景、
2,000 个 payload 哈希、seed 范围、集合无重叠及 no-DR 服务可行性均通过审计。
为保持固定候选的 controller/source/Git provenance，三个 q 均在原 selection
提交 `5889405` 上重放。q={0.90,0.95,0.99} 的 validation-selected 候选在 OOD
上均为 0/18 certified cells；headline q=0.95 各 duration 的成功数为
H={1,2,3,4,6,8}: {437,433,445,425,398,383}/500，对应 Wilson 下界
0.733–0.865。主要失败来自 mean/interval delivery。同一 duration 下三个 notice
的结果仍完全相同。该结果说明主分布内证书没有在此联合分布偏移下保持，不能
表述为“OOD firm capacity 为零”，因为协议禁止在 locked-OOD 上重新选择容量。
完整回执见 `data/manifests/nature_mainline_locked_ood_results_v1.yaml`。

### Phase 6 — 独立因果容量认证

- 在 validation frozen scenarios 上冻结 robust-MPC 参数与各 H、N、q 的候选容量；
- 在 500 个 locked-ID episodes 上一次性计算 Wilson 下界；
- 将 locked-OOD 作为单独的外推压力测试；
- 额外 controller/RL 比较保持可选，且不得改变主证书。

正式流程先生成并审计 validation scenarios，但暂不选择容量。由于
`causal_selection.json` 会绑定精确 Git commit，locked-ID 的一次性授权必须先
提交；随后才在同一干净 commit 上依次完成 q=0.95 headline、q={0.90,0.99}
secondary validation selection 和预声明 locked replay。各单元格报告 interval-wise
Wilson 下界，不声称整张 surface 具有 simultaneous confidence。

---

## 16. 完成标准

当以下条件满足时，主论文已经形成完整闭环，无需等待 RL 结果：

- [x] 硬件校准和 workload-class 功率定义冻结；
- [x] 名义、PI 和受限 NA 三层规划边界可重复计算；
- [x] 固定因果候选在独立 locked-ID 上完成一次性检验并保留全部通过/失败结果；
- [x] duration–notice–reliability surface 完成评估（部分单元未通过认证门槛）；
- [x] development 与独立 validation compute-debt exhaustion 机制得到量化；
- [x] development 与独立 validation 2 × 2 × 2 hosting-capacity 分析完成；
- [x] development 的 joint DC–PV hosting envelope 与弃光约束 PV capacity 已完成；
- [x] 独立 validation 的 joint DC–PV hosting 与固定装机 PV utilisation 完成、审计并写入结果回执；
- [x] AI–BESS 替代关系在 validation 复现；AI–PV 的条件性边界被保留；
- [x] 硬件校准、PUE、node overhead 与 workload development sensitivity 完成；
- [x] locked-OOD 场景分布外推完成，固定候选未保留目标可靠性；
- [x] 所有主线数值结果具有结果回执、provenance 和 hash；
- [x] locked ID 与 locked OOD 分开，且都只在模型和分析方案冻结后运行；
- [x] 控制器结果未被误写成文章的核心创新。

---

## 17. 最终逻辑闭环

本篇 Nature Communications 的完整逻辑应为：

```text
AI task traces and hardware measurements
                ↓
job-level feasible execution schedules
                ↓
nominal → perfect-information → non-anticipative firm flexibility
                ↓
fixed causal realization → independent locked-ID certificate
                ↓
duration–notice–reliability surface
                ↓
compute debt, recovery and repeated-event exhaustion
                ↓
joint DC–PV hosting and fixed-capacity PV utilisation under BESS
                ↓
robustness across hardware, workload and community uncertainty
```

一句话概括：

> **这篇论文研究的是 AI 灵活性作为一种电网资源的物理边界、可靠边界、耗尽机制和系统价值，而不是研究如何训练一个更好的控制器。**
