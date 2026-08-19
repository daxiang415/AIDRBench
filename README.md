# AIDRBench：Nature Communications 主线研究方案

> **文档定位**：本文件定义 AIDRBench 面向 *Nature Communications* 的主论文科学主线。它是系统与机制研究方案，不是控制算法论文，也不是强化学习 benchmark 论文。
> **核心原则**：先建立物理与统计意义上的灵活性边界，再解释计算债务、恢复反弹和社区接入价值；PI/NA 是规划边界，真正的可靠可交付容量还必须由一个冻结的因果调度实现，在独立 locked-ID 场景上认证。该要求不把论文变成控制器竞赛，也不需要 RL。

---

## 1. 一句话科学命题

**AI 数据中心的可移位负荷并不等于可向电网承诺的可靠灵活性。真正可交付的灵活性取决于任务期限、事件持续时间、提前通知、未来信息、既往调度历史以及恢复阶段产生的计算债务和功率反弹。**

论文要回答的不是：

> 哪一种控制器或强化学习算法表现最好？

而是：

> AI 工作负荷中名义上“可以延迟”的部分，到底有多少能够在服务质量、恢复和可靠性约束下转化为真实的电网资源；这种资源为何会随持续时间和连续调用而衰减；它能为社区电网和数据中心接入带来多大价值？

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

强化学习、CMDP、安全层和硬件在环控制可以保留在代码库中，但应作为后续控制论文或 Supplementary extension，而不是决定本篇 NC 主线。

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

## 4. 核心科学问题与假设

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

### Q4. AI 柔性能够增加多少数据中心接入容量？

**假设 H4**：在同一 PCC 或变压器容量下，柔性 AI 负荷可以提高可接入数据中心规模，但增益取决于社区峰值形态、光伏、储能和 deadline 分布。

### Q5. AI 柔性与 PV/BESS 是互补还是替代？

**假设 H5**：

- AI 柔性与 PV 在部分场景中互补，因为任务可在光伏富余时提前执行；
- AI 柔性与短时 BESS 可能部分替代，因为二者均可覆盖短峰值；
- 在长持续时间事件或恢复约束下，AI 柔性与 BESS 可能再次表现为互补。

### Q6. 硬件和工作负荷不确定性是否改变机制结论？

**假设 H6**：硬件功率参数会显著改变绝对 kW 和接入容量，但“名义灵活性高估、持续时间效应和计算债务耗尽”这些机制结论应在合理不确定性范围内保持稳定。

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

数据来源也必须准确表述：社区负荷为 NLR/NREL EULP 建模并经实测校验的 profile，不是本项目采集的社区电表数据；任务到达为 Alibaba GPU 2026 trace-calibrated synthetic process，deadline 由预声明 policy 生成；DR 事件来自配置的峰时窗口随机抽样，不是真实 utility dispatch 记录。

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

## Result 1 — 从硬件和任务推导可靠灵活性，而不是预设柔性比例

### 科学问题

固定比例 \(\alpha P_{\mathrm{DC,peak}}\) 与真实任务可行性之间存在多大差距？

### 分析内容

- 四 GPU 节点功率测量与 held-out validation；
- training 与 offline inference 的类别功率；
- 任务 arrival、GPU-hour 和 deadline 分布；
- 从任务队列到数据中心功率再到 PCC 的映射；
- 比较 \(F^{\mathrm{nominal}}\) 与 \(F_q^{\mathrm{PI}}\)。

### 预期结论

名义柔性不能直接作为电网资源；deadline 与功率结构会产生显著的物理可行性差距。

### 对应主图

**Figure 1：Measurement-to-flexibility framework**

- a：四 GPU 硬件测量与功率模型；
- b：任务 arrival–deadline–execution 关系；
- c：任务调度到 DC/PCC 功率；
- d：名义柔性与 job-derived boundary 的概念差异。

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

## Result 4 — AI 柔性增加社区数据中心接入容量

### 科学问题

在同一 PCC 容量下，任务柔性能够使社区多接入多少 AI 数据中心？

### 核心 2 × 2 × 2 设计

| 组合维度 | 水平 1 | 水平 2 |
|---|---|---|
| 数据中心 | rigid | workload-flexible |
| 光伏 | without PV | with PV |
| 储能 | without BESS | with BESS |

对每个组合求：

\[
C_{\mathrm{DC,max}}.
\]

并报告：

\[
\Delta C_{\mathrm{hosting}}
=
C_{\mathrm{flex}}-C_{\mathrm{rigid}},
\]

\[
M_{\mathrm{hosting}}
=
\frac{C_{\mathrm{flex}}}{C_{\mathrm{rigid}}}.
\]

### 预期结论

AI 柔性可以转化为真实接入容量，但价值高度依赖社区峰值时刻、光伏富余和储能时长。

### 对应主图

**Figure 4：Community hosting-capacity gain**

- a：八种 portfolio 的 hosting capacity；
- b：柔性带来的绝对增益；
- c：不同社区 headroom 下的接入容量地图；
- d：哪些受限社区能够被 AI 柔性“救回”。

---

## Result 5 — AI 柔性与 PV/BESS 的互补和替代边界

### 科学问题

AI workload flexibility 与 DER 是叠加价值，还是重复提供同一种服务？

定义 AI–BESS 交互项：

\[
I_{\mathrm{AI,BESS}}
=
\left(C_{\mathrm{flex+BESS}}-C_{\mathrm{rigid+BESS}}\right)
-
\left(C_{\mathrm{flex}}-C_{\mathrm{rigid}}\right).
\]

- \(I>0\)：互补；
- \(I<0\)：替代；
- \(I\approx0\)：近似独立。

上述标签只在场景级不确定性区间和预声明 equivalence margin 完成后使用；
单个 development scenario 的点估计只用于验证 2 × 2 × 2 求解路径。

对 PV 可定义相同交互项。

### 分析内容

- PV penetration；
- BESS power 和 duration；
- 数据中心占 PCC 比例；
- 社区峰值形态；
- 事件持续时间；
- deadline 严格程度。

### 对应主图

**Figure 5：Complementarity and substitution regimes**

- a：AI–PV 交互地图；
- b：AI–BESS 交互地图；
- c：duration 和 BESS duration 的交互；
- d：不同社区类型的 regime classification。

---

## Result 6 — 硬件与模型不确定性下的稳健性

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

### 预期结论

绝对 kW 和 hosting-capacity 数字存在区间，但名义高估、duration effect 和 compute-debt exhaustion 在合理参数范围内保持稳定。

### 对应主图

**Figure 6：Robustness and generalization**

- a：不同硬件功率 case 下的 firm frontier；
- b：主要效应的 uncertainty interval；
- c：不同 workload/deadline 场景的机制一致性；
- d：结论稳定区间与失效边界。

---

## 9. 方法与代码模块映射

| NC 主线任务 | 所需代码模块 | 是否属于主论文 |
|---|---|---:|
| 硬件功率校准 | calibration artifact、power model | 是 |
| 任务 arrival/deadline 建模 | workload sampler、deadline queue | 是 |
| Frozen scenario | scenario freeze、hash/provenance | 是 |
| PI frontier | perfect-information optimizer | 是 |
| 非前视 firm frontier | non-anticipative optimization | 是 |
| 单事件可靠容量 | frozen robust-MPC selection + locked-ID certification | 是 |
| 重复事件耗尽 | repeated-event stress test | 是 |
| Hosting capacity | PV/BESS/PCC optimization | 是 |
| 参数不确定性 | lower/nominal/upper uncertainty bounds | 是 |
| Rule/MPC smoke test | software validation | 否，最多补充材料 |
| DQN/PPO/SAC benchmark | online-control extension | 否 |
| CMDP v1–v5 reward | control-algorithm development | 否 |
| Hardware-in-the-loop | future extension | 否 |

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

以下内容移动到单独文档或后续论文：

- DQN、PPO、SAC；
- CMDP reward v1–v5；
- controller checkpoint selection；
- safety layer；
- aggregate action 与 class-specific actuation；
- HIL 和实时控制。

后续控制论文可以命名为：

> **Safe online realization of firm AI data-centre flexibility under compute-debt and rebound constraints**

---

## 13. 仓库文档建议

### `README.md`

只保留：

- 项目核心命题；
- 已实现功能；
- 可运行的主要 CLI；
- 当前协议和校准状态；
- 哪些结果是历史诊断；
- 指向各专题文档的链接。

### `docs/nature-communications-mainline.md`

保存本文件，定义 NC 主线。

### `docs/online-control-extension.md`

保存：

- rule/MPC/RL；
- CMDP reward；
- controller diagnostics；
- future safe-control paper。

### `docs/hourly-validation-status.md`

只记录真实运行状态：

- 哪些场景已冻结；
- 哪些 seed 已运行；
- 哪些模型已废弃；
- locked OOD 是否开启；
- failure decomposition。

### `docs/historical-results.md`

保存旧版 63.52 kW、68.86 kW、firm_v4 和早期 reward 结果，避免再次混入当前结论。

---

## 14. 主论文建议标题与贡献表述

### 工作标题

**Job-derived flexibility envelopes reveal compute-debt limits and community hosting value of AI data centres**

### 三句话贡献

> First, we replace exogenous flexible-load fractions with job-derived firm-flexibility envelopes that jointly account for interval delivery, workload deadlines, recovery and rebound.

> Second, we separate nominal, perfect-information and non-anticipative capacities to quantify physical and information losses, and translate reliable AI flexibility into community data-centre hosting capacity under photovoltaic and battery portfolios.

> Third, we reveal compute debt as the mechanism that makes AI flexibility exhaustible and recovery-dependent under repeated grid dispatch.

### 主结论应落在这里

\[
\boxed{
\text{AI workload flexibility is finite, state-dependent, duration-dependent and exhaustible.}
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
- 将 RL/CMDP 内容移到 control extension；
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

### Phase 4 — 计算社区 hosting capacity

- 2 × 2 × 2 portfolio；
- DC/PV/BESS response surface；
- complementarity/substitution analysis。

### Phase 5 — 稳健性和外推

- 硬件 lower/nominal/upper uncertainty bounds；
- PUE 和 node overhead；
- workload mix；
- deadline distribution；
- locked OOD communities。

### Phase 6 — 独立因果容量认证

- 在 validation frozen scenarios 上冻结 robust-MPC 参数与各 H、N、q 的候选容量；
- 在 500 个 locked-ID episodes 上一次性计算 Wilson 下界；
- 将 locked-OOD 作为单独的外推压力测试；
- 额外 controller/RL 比较保持可选，且不得改变主证书。

---

## 16. 完成标准

当以下条件满足时，主论文已经形成完整闭环，无需等待 RL 结果：

- [ ] 硬件校准和 workload-class 功率定义冻结；
- [ ] 名义、PI 和受限 NA 三层规划边界可重复计算；
- [ ] 固定因果策略在独立 locked-ID 上完成容量认证；
- [ ] duration–notice–reliability surface 完成；
- [ ] compute-debt exhaustion 机制得到量化；
- [ ] 2 × 2 × 2 hosting-capacity 分析完成；
- [ ] PV/BESS 互补与替代区域得到识别；
- [ ] 硬件和场景不确定性分析完成；
- [ ] 所有正式结果具有完整 provenance 和 hash；
- [ ] locked ID 与 locked OOD 分开，且都只在模型和分析方案冻结后运行；
- [ ] 控制器结果未被误写成文章的核心创新。

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
community hosting-capacity value under PV and BESS
                ↓
robustness across hardware, workload and community uncertainty
```

一句话概括：

> **这篇论文研究的是 AI 灵活性作为一种电网资源的物理边界、可靠边界、耗尽机制和系统价值，而不是研究如何训练一个更好的控制器。**
