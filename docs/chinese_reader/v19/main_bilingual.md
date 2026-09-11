本稿逐段对应英文正文与补充材料 v0.25（2026-09-10）。现有证据按工作量权重、小时顺序与承诺决策重新组织；未新增模拟或重新选择报价。

<!-- M001 -->
# Workload timing limits reliable demand response from AI data centres

# 工作量的时间分布限制人工智能数据中心的可靠需求响应

<!-- M002 -->
## Authors

## 作者

<!-- M003 -->
[AUTHOR NAMES AND AFFILIATIONS]

[作者姓名与单位]

<!-- M004 -->
*Correspondence: [CORRESPONDING AUTHOR EMAIL]*

*通讯作者：[通讯作者邮箱]*

<!-- M005 -->
## Abstract

## 摘要

<!-- M006 -->
Artificial-intelligence data centres could help electricity grids accommodate growing demand by postponing computing, but a response commitment must remain deliverable as workloads change. Here we test how workload representation affects this commitment in a trace-informed scheduling and electricity model. At 10% work eligibility, independent tests support four- and eight-hour offers of 5.60 and 4.42 kW at a 95% success-probability target, with zero missed work required for a successful series. Yet a fixed 2.95-kW request succeeds in 80/80 submission-count-weighted realisations and only 31/80 task-resource-time-weighted realisations across eight observed weeks with matched weekly work totals. Permuting hourly blocks raises resource-time success to 55/80 with a 1% missed-work allowance and 54/80 with zero missed work. Workload weighting and hourly order with call alignment therefore expose distinct limits. Immediate supply checks and strict task-window feasibility tests separate impossible delivery from failures with a feasible full-information schedule. Operating ledgers then compare compensation only for independently qualified products. This assessment identifies when a workload change invalidates a model-supported commitment, when controller improvement remains possible and when a price comparison is meaningful.

人工智能数据中心可以通过推迟计算，帮助电网应对不断增长的需求，但响应承诺必须在工作负载变化后仍然可交付。本文在受生产轨迹约束的调度与电力模型中，检验工作负载的表征方式如何影响这种承诺。当 10% 工作允许参与时，独立测试支持四小时 5.60 kW 和八小时 4.42 kW 的报价，整体成功概率目标为 95%，且一次序列只有零漏期工作才能被判为成功。然而，在八个实际观察周中保持每周工作总量一致，固定 2.95 kW 请求按提交次数加权时成功 80/80，按任务资源时间加权时仅成功 31/80。置乱完整小时块后，资源时间测试在允许 1% 漏期工作时成功 55/80，在要求零漏期时成功 54/80。因此，工作量权重以及小时顺序与调用的对齐关系，揭示了不同层面的限制。即时供给检查与严格任务时间窗检验进一步区分无法交付的情形，以及完整未来信息下存在可行调度的控制失败。随后，运行账本只对通过独立资格检验的产品比较补偿。这一评估帮助识别工作负载变化何时使模型支持的承诺失效、何时仍有改进控制器的空间，以及何时才有意义开展价格比较。

<!-- M007 -->
## Introduction

## 引言

<!-- M008 -->
The global energy transition requires electricity systems to decarbonise supply while accommodating rising demand from electrification and artificial intelligence (AI).<sup>1</sup> Data centres intensify this challenge where large computing loads are concentrated and their expansion outpaces the development of power infrastructure.<sup>1,2</sup> In such regions, electricity availability can constrain AI deployment, while grid planners must accommodate new demand without compromising reliability or affordability.<sup>2,3</sup> Adjusting when computing consumes power offers a way to make better use of existing infrastructure.<sup>3</sup> For this flexibility to support grid planning, operators must be able to deliver repeated power reductions while meeting computing-service obligations at acceptable cost. Establishing dependable and economically viable commitments is therefore central to assessing how data centres can participate in the energy transition.

全球能源转型要求电力系统在推进供给脱碳的同时，承接电气化与人工智能（AI）发展带来的新增需求。<sup>1</sup> 在大型计算负荷集中、数据中心扩张快于电力基础设施建设的地区，这一挑战尤为突出。<sup>1,2</sup> 电力可获得性可能限制这些地区的 AI 部署，而电网规划者还必须在保障供电可靠性与可负担性的前提下接纳新增需求。<sup>2,3</sup> 调整计算任务的用电时序，为更充分地利用现有基础设施提供了一条路径。<sup>3</sup> 要让这种灵活性服务于电网规划，运营者必须能够以可接受的成本重复交付功率削减，同时履行计算服务义务。因此，建立可靠且具有经济可行性的响应承诺，是评估数据中心如何参与能源转型的关键。

<!-- M009 -->
A field demonstration on 256 graphics processing units (GPUs) reduced power by 25% for three hours while meeting the tested quality-of-service requirements.<sup>3</sup> Batch scheduling, server power management and workload migration have been used to reduce peaks and participate in demand response.<sup>4–8</sup> Carbon-aware scheduling extends these controls to hours and locations with lower emissions or greater renewable availability.<sup>9–12</sup> Other studies address pause-and-resume decisions and GPU power capping.<sup>13,14</sup> Trace-based and planning studies connect workload flexibility to demand-response programmes, advance notice and grid interconnection.<sup>15–18</sup> A recent preprint distinguishes eligible workload power from dependable relief through duration, reliability, portfolio structure and delivery and recovery requirements.<sup>19</sup> These advances motivate a more specific commitment question: can a request that passes a simplified workload test still fail when task-size variation and hourly order are represented more faithfully?

一项在 256 块图形处理器（GPU）上的现场演示，在满足所测试服务质量要求的同时，将功率降低了 25%，持续三小时。<sup>3</sup> 批处理调度、服务器功率管理与工作负载迁移已被用于降低峰值和参与需求响应。<sup>4–8</sup> 碳感知调度进一步将这些控制扩展到排放更低或可再生能源更充足的时段和地点。<sup>9–12</sup> 另一些研究讨论暂停与恢复决策以及 GPU 功率上限。<sup>13,14</sup> 基于轨迹和规划的研究也将工作负载灵活性与需求响应计划、提前通知和电网接入联系起来。<sup>15–18</sup> 一篇近期预印本通过持续时间、可靠性、组合结构以及交付和恢复要求，区分了可参与工作功率与可靠减负。<sup>19</sup> 这些进展引出一个更具体的承诺问题：当任务规模差异与小时顺序得到更充分的表征时，一个通过简化工作负载测试的请求是否仍会失败？

<!-- M010 -->
The workload mix sets which computing may participate. Online inference must respond to user requests, whereas some training and offline-inference work can wait within an agreed deadline. Production traces distinguish these classes and their scheduling priorities,<sup>20</sup> but priority is not permission to defer work for grid services. Even at fixed eligible work, job counts do not specify how much work arrives in each hour. Each job must fit between release and deadline, and postponement creates an additional processing obligation relative to operation without response, or compute debt.<sup>6,13,21,22</sup> Thus, low-supply hours and recovery requirements can invalidate a request even when average workload and installed hardware appear sufficient.

工作负载构成决定哪些计算可以参与。在线推理必须及时响应用户请求，而部分训练和离线推理可以在约定期限内等待。生产轨迹区分了这些类别及其调度优先级，<sup>20</sup> 但优先级不等于允许为了电网服务而推迟工作。即使可参与工作总量相同，作业次数也不能确定每个小时到达的工作量。每项作业仍必须在释放与期限之间完成；推迟执行会产生相对于无响应运行的额外处理义务，即计算债务。<sup>6,13,21,22</sup> 因此，即便平均工作量和已安装硬件看似充足，供给低谷与恢复要求仍可能使请求无法履行。

<!-- M011 -->
Delivery and value also require different evidence. At a community point of common coupling (PCC), data-centre demand interacts with photovoltaic (PV) generation and battery energy storage systems (BESS).<sup>23–27</sup> A hardware allocation that benefits PV hosting need not increase an independently tested response offer. For an operator, postponement creates waiting and service-loss exposure, while access charges affect whether participation is worthwhile. Valuing those quantities cannot make an undeliverable commitment feasible. A useful assessment must therefore establish what can be offered before comparing service products at stated prices.

交付能力与参与价值还需要不同的证据。在社区公共耦合点（PCC），数据中心需求与光伏（PV）发电和电池储能系统（BESS）相互作用。<sup>23–27</sup> 有利于光伏接纳的硬件分配，不一定提高通过独立检验的响应报价。对运营者而言，推迟执行产生等待与服务损失暴露，而接入费用影响参与是否值得。给这些数量定价，不能使无法交付的承诺变得可行。因此，有用的评估必须先明确能够提供什么，再在指定价格下比较服务产品。

<!-- M012 -->
Here we identify how a simplified workload representation can support the wrong commitment decision. AIDRBench combines trace-informed jobs, four-GPU board-power measurements and a modelled community electricity system. Production execution data inform plausible work-permission scenarios. We independently test causal-controller offers and compare matched submission-count and task-resource-time profiles in their observed and permuted hourly orders.<sup>28</sup> An instantaneous supply condition and same-scenario perfect-information feasibility checks then distinguish why requests fail. Finally, complete operating ledgers compare qualified duration products with non-participation. Together, the tests connect workload characterisation to decisions about the request, controller and compensation.

本文识别简化的工作负载表征如何支持错误的承诺决策。AIDRBench 结合受轨迹约束的作业、四块 GPU 的板卡功率测量与社区电力系统模型。生产执行数据为合理的工作参与许可情景提供依据。我们独立检验因果控制器的报价，并对提交次数和任务资源时间曲线开展配对比较，分别保留实际小时顺序或置乱该顺序。<sup>28</sup> 随后，即时供给条件与同场景完美信息可行性检验区分请求失败的原因。最后，完整运行账本将合格时长产品与不参与进行比较。这些测试共同将工作负载表征与请求、控制器和补偿决策联系起来。

<!-- M013 -->
## Results

## 结果

<!-- M014 -->
### Workload composition limits which computing can support a commitment

### 工作构成限制了哪些计算可以支持响应承诺

<!-- M015 -->
We first examined what fraction of computing could plausibly enter the deferrable pool. Across 40.52 million execution spans in the released Alibaba summary,<sup>20</sup> online inference accounted for 54.5% of requested GPU-hours, offline inference for 21.5% and training for 19.4% (Fig. 1a). Low-priority training and offline inference together accounted for 22.0%. These are descriptive resource-time shares, not measured energy shares or demand-response permissions. They provide a candidate pool from which an operator might authorise a smaller amount of work to wait.

我们首先检查有多少计算可能进入可延后工作池。在 Alibaba 公开摘要的 4,052 万个执行区段中，<sup>20</sup> 在线推理占申请 GPU 小时的 54.5%，离线推理占 21.5%，训练占 19.4%（图 1a）。低优先级训练与离线推理合计占 22.0%。这些是资源时间的描述性占比，不是实测能耗占比或需求响应授权；它们提供候选范围，运营商可能从中允许较少部分工作等待。

<!-- M016 -->
The primary scenarios allowed 5%, 10% or 20% of total offered work to wait, preserving the observed class mix and varying permission within low-priority batch work. The 40% comparison required almost all training and offline inference to opt in. The 60% case additionally reassigned 19.1 percentage points of total work from online to offline inference (Fig. 1b). Online jobs remained ineligible; these larger fractions therefore describe additional business assumptions.

主要情景允许总供给工作量的 5%、10% 或 20% 等待，在保留观测类别构成的同时，改变低优先级批处理工作的许可比例。40% 对照要求几乎全部训练和离线推理参与。60% 情景还将总工作量的 19.1 个百分点从在线推理重新分配到离线推理（图 1b）。在线作业始终不允许参与，因此更高比例代表额外的业务假设。

<!-- M017 -->
Each configuration retained 576 GPUs and 374.4 GPU-h of offered work per hour. Assigning approximately the same fraction of GPUs as eligible work kept mean utilisation near 65% in both pools. The primary comparison therefore changes permission together with supporting allocation; controls at 10% eligibility isolate allocation (Fig. 5). Four-GPU board-power calibration constrained the batch-work conversion, whereas rigid workloads used an engineering power proxy (Supplementary Fig. 2; Supplementary Tables 1–3).

各配置均保留 576 块 GPU，每小时供给 374.4 GPU-h 工作。向灵活池分配与可参与工作比例大致相同的 GPU，使两个池的平均利用率均接近 65%。因此，主要比较同时改变参与许可及其配套分配；10% 参与比例下的对照则单独考察分配（图 5）。四块 GPU 的板卡功率校准约束批处理工作的功率转换，刚性工作负载采用工程功率代理（补充图 2；补充表 1–3）。

![图 1](../../figures/commitment_narrative_v1/artwork/AIDRBench_Figure_1.png)

<!-- M021 -->
### Smaller eligible pools support smaller independently tested offers

### 较小的合格工作池支持较小的独立检验承诺

<!-- M022 -->
Development-selected single-event offers of 2.95, 5.90 and 11.80 kW qualified on 300 independent scenarios at 5%, 10% and 20% eligibility, respectively, corresponding to 1.6–5.9% of operating peak demand (Fig. 2a; Supplementary Table 4). The 40% and 60% comparisons qualified at 22.19 and 34.00 kW under their additional assumptions. The proportional low-share response follows the shared job-template scaling and allocation policy. Relaxed perfect-information (PI) tolerance statistics provide a planning comparison but do not guarantee individual work-group feasibility (Methods).

当参与比例分别为 5%、10% 和 20% 时，开发阶段选出的单次报价 2.95、5.90 和 11.80 kW 在 300 个独立情景上通过资格检验，对应运行峰值需求的 1.6%–5.9%（图 2a；补充表 4）。在额外业务假设下，40% 和 60% 对照的合格报价为 22.19 和 34.00 kW。低比例情景的比例关系来自共享作业模板的缩放和分配规则。放松的完美信息（PI）容忍统计量提供规划比较，但不保证各工作组可行（见方法）。

<!-- M023 -->
The same selected power qualified at four and eight hours on the tested grid, with success decreasing from 295/300 to 292/300 in every configuration; one-sided 95% probability lower bounds were 0.9662 and 0.9533. Zero-, two- and six-hour notice gave identical paired outcomes (Fig. 2b). Because jobs cannot execute before release and the baseline already processes available work eagerly, advance information created no extra pre-executable work in this setting.

在所测试网格中，相同选定功率均通过四小时与八小时资格检验，但各配置成功数均由 295/300 降至 292/300；单侧 95% 概率下界分别为 0.9662 和 0.9533。提前零、两和六小时通知得到相同的配对结果（图 2b）。由于作业不能在释放前执行，且基线已尽早处理可用工作，在这一设定下，提前信息并未增加可提前执行的工作。

![图 2](../../figures/commitment_narrative_v1/artwork/AIDRBench_Figure_2.png)

<!-- M025 -->
### Workload timing determines whether a repeated commitment transfers

### 工作量的时间分布决定重复承诺能否适用

<!-- M027 -->
At 10% work eligibility, we tested four calls using a controller that enforces every overlapping recovery obligation. In the reference configuration—65% offered utilisation, reference deadlines and a 10% GPU pool—the four- and eight-hour offers were 5.60 and 4.42 kW, both with 16-h start spacing. When successful series required zero missed work, independent confirmation gave 297/300 and 296/300 successes, with one-sided 95% probability lower bounds of 0.9752 and 0.9706 (Fig. 3a). Both the 1% and zero-miss standards selected these capacities on the local grid (Supplementary Table 18). Their agreement provides no basis for applying a uniform capacity discount solely because the success criterion becomes stricter.

在 10% 工作允许参与时，我们使用落实每项重叠恢复义务的控制器测试四次调用。在参考配置下，即工作供给利用率 65%、参考期限和 10% GPU 池，四小时与八小时报价分别为 5.60 和 4.42 kW，调用开始间隔均为 16 h。当一次序列必须零漏期才能判为成功时，独立确认成功数分别为 297/300 和 296/300，单侧 95% 概率下界为 0.9752 和 0.9706（图 3a）。1% 与零漏期标准在局部网格上均选择这些容量（补充表 18）。两者一致的结果不支持仅因成功标准变严格，就施加统一的容量折减。

<!-- M023_timing -->
These reference offers did not establish transfer to a different workload representation. In eight observed weeks, the fixed 2.95-kW request passed 80/80 chronological submission-count-weighted realisations but only 31/80 matched task-resource-time-weighted realisations (Fig. 3c,d). Weekly class totals, synthetic service rules, community profiles and event clocks were held fixed. All no-response baselines met zero-miss service. The 49 resource-time failures therefore arose under response commitments in otherwise service-feasible scenarios, rather than from more total eligible work or an infeasible baseline.

这些参考报价并不确立其对另一种工作负载表征的适用性。在八个实际观察周中，固定 2.95 kW 请求在原序提交次数加权下成功 80/80，在配对任务资源时间加权下仅成功 31/80（图 3c,d）。各类别周总工作量、合成服务规则、社区曲线与事件时刻均保持一致。全部无响应基线满足零漏期服务。因此，49 次资源时间失败发生于本来能够满足服务的情景加入响应承诺后，不能归因于总可参与工作量增加或基线本身不可行。

<!-- M025_order -->
Permuting whole hourly blocks separated workload weighting from the effect of hourly order and alignment. Count-weighted success remained 80/80, whereas resource-time success rose to 55/80 at the 1% standard and 54/80 at zero misses (Fig. 3c). Hourly rearrangement improved this comparison but did not restore count-weighted performance. It changes alignment with both calls and community demand, so the improvement cannot be assigned to autocorrelation alone. At the larger 4.42-kW request, all 80 chronological resource-time realisations failed; full cross-scores are retained in Supplementary Table 20.

置乱完整小时块进一步区分了工作量权重与小时顺序及对齐的影响。次数加权仍成功 80/80，而资源时间加权在 1% 标准下提高至 55/80，在零漏期标准下提高至 54/80（图 3c）。小时重排改善了这一对照的结果，却未恢复到次数加权的表现。重排同时改变与调用和社区需求的对齐，因此不能将改善全部归因于自相关。在更大的 4.42 kW 请求下，80 个原序资源时间实现全部失败；完整交叉评分保留在补充表 20。

![图 3](../../figures/commitment_narrative_v1/artwork/AIDRBench_Figure_3.png)

<!-- M029 -->
### Supply and feasibility checks identify what a failed request requires

### 供给与可行性检查识别失败请求需要怎样调整

<!-- M030 -->
An instantaneous supply screen explained the electrical failures. For each event hour, we compared the matched baseline power available above community and idle-plus-rigid demand with 95% of the request. A deficit makes successful delivery impossible in that hour, even if all flexible execution stops. All 49 chronological resource-time failures at 2.95 kW met this condition; after permutation, it affected 25 realisations (Fig. 4a,b). The paired changes included both removal and creation of shortages. A non-negative margin is necessary but insufficient: one of the 55 permuted resource-time realisations without shortage still failed the zero-miss endpoint.

即时供给检查解释了电力交付失败。对每个事件小时，我们将匹配基线中高于社区需求、空闲及刚性功耗的可削功率，与请求的 95% 比较。若存在缺口，即便停止全部灵活执行，该小时仍不可能成功交付。2.95 kW 原序资源时间测试的全部 49 次失败均满足这一条件；置乱后，该条件涉及 25 个实现（图 4a,b）。配对变化既包括消除缺口，也包括产生新的缺口。非负余量只是必要条件，并不足以保证成功：在置乱后没有即时不足的 55 个资源时间实现中，仍有一个未通过零漏期终点。

<!-- M031 -->
Strict task-window feasibility then distinguished failures beyond that supply condition. At a fixed 5.90-kW request, a reference scenario that passed the supply screen failed under causal control but admitted a full-information schedule meeting all electrical obligations with zero missed work (Fig. 3b; Supplementary Table 19). Halving its deadline slack made the request infeasible under the same delivery and recovery criteria; doubling GPU allocation did not restore feasibility. Each variant used its own matched baseline. The feasible reference case leaves room for controller improvement, whereas proven infeasibility calls for changing the request or operating terms. Neither finding follows from the causal failure alone.

随后，严格任务时间窗可行性区分了即时供给条件之外的失败。在固定 5.90 kW 请求下，一个通过供给检查的参考情景在因果控制下失败，却存在满足全部电气义务且零漏期的完整信息调度（图 3b；补充表 19）。将其期限余量减半后，在相同交付和恢复判据下，请求变为不可行；将 GPU 分配加倍也没有恢复可行性。各变体采用各自匹配的基线。参考情景的可行解说明仍有改进控制器的空间，而已证明的不可行则要求改变请求或运行条款。这两种判断都不能仅从因果控制失败得出。

<!-- M025_decision -->
These checks define different decisions (Fig. 4c). Supply deficits identify series that cannot succeed; strict-window tests diagnose whether the remaining constraints admit a schedule. A feasible PI schedule is a diagnostic opportunity, not a deployable controller. A fixed causal policy must still pass independent qualification for its declared scenario distribution before its operating ledger enters price comparison. A single failed series is not automatically a rejection of a probabilistic contract: qualification retains the complete success and failure sample. In the matched same-clock control, removing preceding calls left final-call electrical outcomes unchanged (Supplementary Table 15), further limiting explanations based only on accumulated call history.

这些检查对应不同决策（图 4c）。供给缺口识别不可能成功的序列；严格时间窗检验诊断其余约束下是否存在调度。PI 可行解提供诊断与改进机会，但不是可部署的控制器。固定因果策略仍须在声明的情景分布上通过独立资格检验，其运行账本才能进入价格比较。一次序列失败并不自动否定概率性合同：资格检验保留完整成功与失败样本。在配对同一时刻的对照中，移除先前调用并未改变末次调用的电力结果（补充表 15），这也限制了仅用累计调用历史解释失败的说法。

![图 4](../../figures/commitment_narrative_v1/artwork/AIDRBench_Figure_4.png)

<!-- M034 -->
### Allocation changes system value without necessarily increasing the offer

### 分配可以改变系统价值，而不一定提高报价

<!-- M035 -->
At fixed 10% work eligibility, increasing flexible GPU allocation from 10% to 20% or 30% left the tested 5.90-kW single-event offer at 295/300 four-hour and 292/300 eight-hour successes. The corresponding relaxed-PI tolerance statistics were also unchanged (Fig. 5a; Supplementary Fig. 4c). Reducing the rigid-class active-power proxy from 300 to 225 or 150 W per GPU preserved these baseline-relative responses but changed operating peak demand from 193.44 to 173.53 or 153.63 kW (Fig. 5b). Thus, eligible arrivals constrained this response, while rigid power remained relevant to facility demand and proportional cost accounting (Fig. 5c,d).

在固定 10% 工作允许参与时，将灵活 GPU 分配由 10% 提高至 20% 或 30%，所测试的 5.90 kW 单次报价仍保持四小时 295/300、八小时 292/300 成功。相应的放松 PI 容忍统计量也未改变（图 5a；补充图 4c）。将刚性类别活动功率代理从每 GPU 300 W 降至 225 或 150 W，未改变这些相对基线的响应，却使运行峰值需求从 193.44 kW 变为 173.53 或 153.63 kW（图 5b）。因此，可参与工作的到达约束了这一响应，而刚性功率仍影响设施需求与比例成本核算（图 5c,d）。

<!-- M036 -->
The same allocation could matter more for a different service. At 10% eligibility, raising the flexible GPU share from 10% to 20% increased the no-BESS PV hosting gain from 5.40 to 24.99 kW (Supplementary Fig. 4d). The primary 10% case nevertheless improved utilisation of a fixed 500-kW PV installation by only 0.0057 percentage points (95% paired interval, 0.0019–0.0106; Supplementary Fig. 4a,b). Hosting and utilisation therefore measure different benefits. All PV comparisons used separate full-information schedules; small storage contrasts remained limited by solver precision (Supplementary Table 6).

相同分配对另一种服务可能更重要。在 10% 工作参与比例下，将灵活 GPU 比例由 10% 提高至 20%，使无储能光伏接纳增量由 5.40 kW 增至 24.99 kW（补充图 4d）。然而，主要 10% 情景对固定 500 kW 光伏设施利用率的提高仅为 0.0057 个百分点（95% 配对区间 0.0019–0.0106；补充图 4a,b）。因此，接纳容量与利用率衡量不同收益。全部光伏比较采用独立的完整信息调度；微小储能差异仍受求解精度限制（补充表 6）。

![图 5](../../figures/commitment_narrative_v1/artwork/AIDRBench_Figure_5.png)

<!-- M039 -->
### Access fees and operating costs affect different participation decisions

### 接入费用与运行成本影响不同的参与决策

<!-- M040 -->
Once a duration product qualified, its operating exposure and access charges could be valued separately. In the 10% eligibility single-event case, the assumed US$25,000 annual site fee accounted for about 95% of the US$863.26 per offered kW-year threshold (Supplementary Table 17). To distinguish fee allocation from operating consequences, we compared complete response-and-recovery ledgers for the qualified repeated products. All amounts use proportional 1-MW accounting and retain failed confirmation trajectories.

时长产品通过资格检验后，其运行暴露与接入费用可以分别估值。在 10% 工作参与比例的单次事件情景中，假定每年 25,000 美元的场站费解释了每报价 kW·年 863.26 美元门槛的约 95%（补充表 17）。为区分费用分摊和实际运行后果，我们比较了合格重复产品完整的响应与恢复账本。全部金额按比例折算至 1 MW，并保留确认中的失败轨迹。

<!-- M041 -->
For the four- and eight-hour products qualified with a zero-miss success criterion, mean additional waiting exposure per four-call series was 16,491 and 24,509 GPU-h×h, respectively (Fig. 6a; Supplementary Table 21). At the illustrative waiting price of US$0.005/GPU-h/h and twelve independent series per year, the no-fixed-fee thresholds were US$183.30 and 330.11 per offered accounting kW-year (Fig. 6b,c). Their capacity difference and waiting exposure explain this conditional comparison; the valuations have not been measured as an operator’s willingness to accept.

对于采用零漏期成功判据通过资格检验的四小时与八小时产品，每组四次调用的平均额外等待暴露分别为 16,491 和 24,509 GPU-h×h（图 6a；补充表 21）。采用每 GPU-h 每小时 0.005 美元的示例等待价格，并假设每年十二组独立序列，无固定费用门槛分别为每报价核算 kW·年 183.30 和 330.11 美元（图 6b,c）。容量差异与等待暴露解释了这一条件性比较；这些估值尚不是运营者接受意愿的实测结果。

<!-- M042 -->
At equal illustrative capacity prices of US$250 per kW-year and zero site fee, the four-hour product’s fifth-percentile annual net value was US$1,932, compared with −US$1,832 for eight hours. Conditional on participation, equal value requires an eight-hour price of 1.267 times the four-hour price plus US$97.93 per kW-year; the full boundary also requires non-negative net value (Fig. 6d). The coefficient is the ratio of the selected capacities. When waiting has no incremental price, the equal-price ranking reverses below approximately US$25.57 per kW-year (Supplementary Fig. 5). A shared fee can change whether either option beats non-participation, but a common fee cancels between participating products.

在两种产品容量价格同为每 kW·年 250 美元、且场站费为零的示例下，四小时产品年度净值的第五百分位为 1,932 美元，八小时为 −1,832 美元。以参与为条件，两者价值相等要求八小时价格等于四小时价格的 1.267 倍，再加每 kW·年 97.93 美元；完整边界还要求净值非负（图 6d）。该系数等于所选容量之比。当等待没有增量价格时，相同价格下的排序在约每 kW·年 25.57 美元以下反转（补充图 5）。共享费用可以改变任一选择是否优于不参与，但共同费用在参与产品之间比较时抵消。

<!-- M043 -->
The economic result is a price-dependent choice among services qualified for the reference scenario distribution. The failed resource-time transfer prevents treating those prices as offers for the observed-week workload. Waiting and missed-work valuations are varied explicitly; contract penalties, application checkpoint costs and actual hardware ageing remain unpriced. Independent annual series provide a conditional accounting screen, rather than a continuous-year operating forecast.

经济性结果是在参考情景分布中合格的服务之间，随价格变化而改变的选择。资源时间测试中的适用失败，使这些价格不能直接作为所观察周工作负载的参与报价。等待和漏期估值均被明确改变；合同违约罚款、应用检查点成本与实际硬件老化仍未定价。独立年度序列提供条件性核算筛选，并非全年连续运行预测。

![图 6](../../figures/commitment_narrative_v1/artwork/AIDRBench_Figure_6.png)

<!-- M045 -->
## Discussion

## 讨论

<!-- M046 -->
The main finding is a failure of commitment transfer that a submission-count test did not reveal. Matching weekly work totals was insufficient when task resource-time exposed low-supply hours. Permuting hourly blocks improved delivery but left a substantial gap to count-weighted profiles. The comparison therefore separates the choice of workload weights from hourly order and alignment, while leaving their joint effect explicit. It identifies a concrete decision error: accepting a request on the basis of a simplified workload replay whose reducible-power supply does not represent the workload to which the commitment will apply. This connects production workload characterisation<sup>20,28</sup> to the operational commitment question raised by field demonstrations<sup>3</sup> and scheduling studies.<sup>5–19</sup>

主要发现是提交次数测试未能揭示的承诺迁移失败。当任务资源时间暴露出供给低谷时，每周工作总量匹配仍不足以确保交付。置乱小时块改善了交付，但与次数加权曲线相比仍存在明显差距。因此，这一比较区分了工作量权重选择与小时顺序及对齐，同时明确保留两者的共同影响。它识别一种具体决策错误：依据简化工作负载重放接受请求，而该重放中的可削功率供给并不能代表承诺实际适用的工作负载。这将生产工作负载表征<sup>20,28</sup>与现场演示<sup>3</sup>及调度研究<sup>5–19</sup>提出的运行承诺问题联系起来。

<!-- M047 -->
The diagnosis also determines what can usefully change. An instantaneous deficit rules out successful delivery in the affected hour. If that condition passes, strict task-window infeasibility and a feasible PI schedule with causal failure require different responses: revise operating terms in the first case, investigate control and information limits in the second. These scenario-level findings must then be assessed through the declared probabilistic qualification rule. More GPUs, a stricter service label or a low estimated price cannot substitute for that sequence of evidence.

诊断还决定哪些调整有意义。即时缺口排除了受影响小时成功交付的可能。若通过这一条件，严格任务时间窗不可行与 PI 可行但因果控制失败需要不同处理：前者需要修改运行条款，后者值得调查控制与信息限制。随后，这些情景层面的发现仍须通过声明的概率性资格规则进行评估。更多 GPU、更严格的服务标签或较低的估计价格，都不能替代这一证据顺序。

<!-- M049 -->
Economic assessment follows qualification and exposes quantities before assigning prices. Waiting and missed-work exposure remain inspectable independently of their valuations. The preferred duration can change when waiting is free, whereas a common access fee affects entry rather than the ranking of participating products. Comparing annual net values with non-participation avoids confusing a low unit-cost threshold with the most valuable contract. The capacity ratio and stated valuations determine the price boundary, whose use remains conditional on the workload for which delivery was qualified.

经济评估在资格检验之后开展，并先展示数量再赋予价格。等待与漏期工作暴露可以独立于估值检查。当等待免费时，偏好的时长可以改变；共同接入费则影响是否进入，而不改变参与产品间的排序。将年度净值与不参与比较，可以避免把较低单位成本门槛误当成最有价值的合同。容量比和指定估值决定价格边界，而这一边界仍只适用于已取得交付资格的工作负载。

<!-- M050 -->
For planners and operators, the useful output is a conditional commitment with a declared workload, baseline, service standard, capacity and call arrangement. Its delivery evidence and operating ledger must be re-evaluated when the timing structure changes. This is consistent with capacity assessment for other resources whose decisions are coupled over time.<sup>29,30</sup> A larger nominal flexible share, more recovery hardware or cheaper access cannot substitute for that assessment.

对规划者和运营者，有用的输出是明确工作负载、基线、服务标准、容量与调用安排的条件性承诺。当时间结构变化时，交付证据与运行账本需要重新评估。这与其他决策在时间上相互耦合的资源容量评估相一致。<sup>29,30</sup> 更高名义柔性比例、更多恢复硬件或更便宜的接入都不能代替这项评估。

<!-- M051 -->
The evidence is conditional on hourly divisible work, synthetic deadlines and permissions, a fixed rigid-load proxy and a small board-power calibration. Observed task resource-time preserves submitted workload-size heterogeneity but is not sensor-measured GPU activity or application pause–checkpoint–restart validation. Hour permutation changes temporal dependence and alignment with calls and community demand together. Eight observed weeks with ten synthetic realisations each are not 80 independent production weeks. Relaxed-PI tolerance statistics do not guarantee work-group feasibility; exact-window diagnostics establish scenario-level possibilities and impossibilities, not causal capacity. Qualification bounds are pointwise, candidate grids are finite and annual accounts combine independent series. These conditions delimit the commitment and price comparisons.

这些证据以小时级可分割工作、合成期限与许可、固定刚性负荷代理和小规模板卡功率校准为条件。观测任务资源时间保留了提交工作规模的异质性，但不等于传感器实测 GPU 活动，也不是应用暂停—检查点—恢复验证。小时置乱同时改变时间依赖及其与调用和社区需求的对齐。八个观察周各十次合成实现不等于八十个独立生产周。放松 PI 容忍统计量不保证工作组可行；严格时间窗诊断确立的是情景层面的可能与不可能，而非因果容量。资格概率界为逐项结果，候选网格有限，年度账本组合独立序列。这些条件界定了承诺与价格比较的适用范围。

<!-- M052 -->
## Methods

## 方法

<!-- M053 -->
### Study design and capacity definition

### 研究设计与容量定义

<!-- M054 -->
The primary comparison followed five declared workload-eligibility scenarios through perfect-information (PI) planning, independent causal-controller testing, repeated programmes, PV integration and participation costs. Eligibility was the share of offered GPU-hours permitted to wait. Capacity was evaluated against the same delivery and service criteria within each declared call programme.

主体比较围绕五档声明的工作资格情景，依次评估完全信息（PI）规划、独立因果控制器检验、重复方案、光伏配合及参与成本。资格指投入 GPU 小时中获准等待的份额。每个声明的调用方案均按相同交付与服务标准评估容量。

<!-- M055 -->
Let Z describe an episode's initial queue, community load, job arrivals and deadlines, hardware and event time, drawn from distribution $\mathcal D$. For fixed policy $\pi$, reduction R, duration H and notice N, $I_\pi(R,H,N;Z)=1$ if all delivery and service criteria are met. Firm capacity was defined as

设 Z 表示一个回合的初始队列、社区负荷、作业到达与截止时间、硬件及事件时刻，并来自分布 $\mathcal D$。对于固定策略 $\pi$、削减量 R、持续时间 H 和提前通知时间 N，若全部交付与服务标准均满足，则 $I_\pi(R,H,N;Z)=1$。可靠容量定义为

$$
F_q^{\pi}(H,N;\mathcal D)=
\sup\left\{R\geq0:\Pr_{Z\sim\mathcal D}
\left[I_\pi(R,H,N;Z)=1\right]\geq q\right\}.
$$

<!-- M057 -->
The primary reliability target was 0.95. Capacity was conditional on the controller, workload scenario and call schedule. We selected the largest qualifying candidate on a finite development grid and tested that candidate independently; this procedure does not estimate the continuous maximum of the capacity function. Pointwise probability lower bounds were used for individual offers, without a simultaneous guarantee over all configurations.

主体可靠性目标为 0.95。容量取决于控制器、工作负载情景和调用安排。我们在有限开发网格中选择通过门槛的最大候选，再独立检验该候选；这一过程不估计容量函数的连续最大值。各项承诺采用逐项概率下界，并未给出覆盖所有配置的联合保证。

<!-- M058 -->
This extension was specified after the earlier benchmark. One hundred development seeds (930000–930099) selected offers, and 300 previously unexamined confirmation seeds (960000–960299) tested them without reselection. The delivered-power recovery guard and feasible-side action rounding were corrected on development data before this controller version was confirmed. Protocol, source, controller and scenario hashes identify the evidence; original locked certificates remain separate historical results.

本扩展在此前基准之后制定。100 个开发种子（930000–930099）用于选承诺，300 个此前未查看的确认种子（960000–960299）在不重新选值的条件下检验。实际交付功率的恢复保护及可行侧动作舍入在开发数据上修正后，再对该控制器版本进行确认。协议、来源、控制器和情景哈希标识对应证据；原锁定证书作为独立历史结果保存。

<!-- M059 -->
### Community, jobs and event scenarios

### 社区、作业与事件情景

<!-- M060 -->
Community demand used the End-Use Load Profiles for the US Building Stock,<sup>31,32</sup> combining 75% detached-residence and 25% small-office demand in the mixed 3A profile. These are building-stock simulations calibrated against measurements. Fifteen-minute power was averaged to hourly intervals and scaled to an 800-kW background peak. All five configurations used a common 1,100-kW PCC import rating and prohibited exports. This rating accommodates the unchanged 576-GPU installation across the changing workload mixes; three initial development baselines exceeded the earlier 1,000-kW rating, so the common site rating was amended before formal PI optimisation or controller selection. Those baseline records were retained.

社区需求采用美国建筑存量的终端用电曲线，<sup>31,32</sup> 在混合 3A 曲线中将 75% 独栋住宅需求与 25% 小型办公需求组合。这些曲线是经测量校准的建筑存量模拟。15 分钟功率平均为小时值，再缩放至 800 kW 背景峰值。五档配置均采用相同的 1,100 kW 公共连接点（PCC）进口容量，并禁止反向送电。该容量适应工作构成变化下保持不变的 576 张 GPU：初始开发基准中有三项超过此前的 1,000 kW 额定值，因此在正式 PI 优化和控制器选值前统一调整站点容量，并保留了这些基准记录。

<!-- M061 -->
Job shapes came from the Alibaba Serverless Infrastructure execution summary,<sup>20</sup> complementing an earlier public GPU trace.<sup>28</sup> We audited all 40,522,321 released execution spans using requested GPU-equivalents multiplied by uncapped duration. This resource-time denominator retained every workload category; it measures neither energy nor permission to defer work. A reproducible, class-balanced 100,000-record subset supplied low-priority training and offline-inference job shapes. Its balanced record counts were not used to estimate the facility workload mix. Original temporal correlations and production deadlines were unavailable in this summary.

作业形状来自 Alibaba Serverless Infrastructure 执行摘要，<sup>20</sup> 并与较早公开的 GPU 轨迹相衔接。<sup>28</sup> 我们用申请的 GPU 等效数量乘以未截尾的持续时间，审核全部 40,522,321 条公开执行区段。该资源时间分母保留所有工作类别，既不代表能量，也不代表允许延后的资格。一个可复现、类别均衡的 100,000 条记录子集提供低优先级训练和离线推理的作业形状；均衡记录数量不用于估计设施工作构成。该摘要不能提供原始时间相关性或生产截止时间。

<!-- M062 -->
Each configuration contained 144 four-GPU nodes and offered 374.4 GPU-h per hour. Let s_c denote a class share and a_c its eligible fraction; total eligibility was $f = \sum_c s_c a_c$. At f = 0.05, 0.10 and 0.20, a common permission multiplier was applied to the observed low-priority training and offline-inference resource-time shares, which together comprised 0.22028 of the source total. At f = 0.40, additional non-low-priority batch work was assumed to opt in. At f = 0.60, the source mix was explicitly changed by replacing 0.19058 of total work from online to offline inference. Online inference remained ineligible in every case. Flexible GPUs were round(576f), giving approximately 65% mean utilisation in both pools; rigid utilisation used the actual integer remainder.

每种配置均含 144 个四 GPU 节点，每小时投入 374.4 GPU 小时的工作量。令 s_c 为类别占比，a_c 为该类别获准延后的比例，总资格为 $f = \sum_c s_c a_c$。当 f = 0.05、0.10、0.20 时，对原数据中的低优先级训练和离线推理资源时间占比应用同一个获准系数；这两类合计占原始总量的 0.22028。当 f = 0.40 时，假定更多非低优先级批处理也同意参与。当 f = 0.60 时，显式改变原业务构成，将占总工作量 0.19058 的在线推理替换为离线推理。所有情景中的在线推理都没有延后资格。灵活 GPU 数为 round(576f)，使两池平均利用率均约为 65%；刚性利用率按整数 GPU 的实际剩余数量计算。

<!-- M062_pairing -->
A common job template was generated once per seed. Class-specific GPU-hours were scaled across configurations while release times, deadlines, community values and the event anchor were checked for equality. Arrivals covered seven days, followed by a 48-h clearance tail. Training deadlines were sampled at 2–6 times runtime and clipped to 6–48 h; offline-inference deadlines were 1.5–4 times runtime and clipped to 2–24 h. The sampling specification and all five baseline-service checks are recorded in Supplementary Methods 1–3. These synthetic deadlines do not establish production service permissions.

每个种子只生成一次共同作业模板。各配置按类别缩放 GPU 小时，并检查释放时刻、截止时间、社区数值和事件锚点相同。到达工作覆盖七天，之后有 48 小时清空尾段。训练截止时间按运行时长的 2–6 倍抽样，并限制在 6–48 小时；离线推理为运行时长的 1.5–4 倍，限制在 2–24 小时。抽样规范和五档无响应服务检验见补充方法 1–3。这些合成截止时间不能证明生产环境授予了相应服务权限。

<!-- M063 -->
### Scheduling and power conversion

### 调度与功率换算

<!-- M064 -->
Each job had a release time, class, GPU-hour requirement and deadline. Released work entered an earliest-deadline-first fluid queue. For class c in hour t,

每项作业具有释放时刻、类别、GPU-h 需求和截止时间。已释放的工作进入按最早截止时间优先处理的流体队列。对类别 c 在小时 t，有

$$
B_{c,t+1}=B_{c,t}+A_{c,t}-X_{c,t}-M_{c,t},
$$

<!-- M066 -->
where B denotes backlog, A arrivals, X executed work and M unfinished work expiring at its deadline. Schedules respected hourly GPU capacity, work conservation, releases, deadlines, the allowed missed-work fraction and terminal backlog. Rigid and flexible work were represented separately. Work could be divided across hours; gang placement, non-pre-emptive execution and checkpoint latency were outside this abstraction. Each hourly step released arrivals before the control action, scheduled work, calculated power and advanced queue deadlines. Other time-step durations were rejected because the queue implementation advances one hourly bucket per step.

其中 B 为积压工作，A 为新到达工作，X 为已执行工作，M 为到达截止时间仍未完成而过期的工作。调度遵守每小时 GPU 容量、工作守恒、释放时刻、截止时间、允许的超期工作比例及终端积压约束。刚性与灵活工作分别表示。工作可以拆分到不同小时执行；成组放置、不可抢占执行及检查点延迟不在该抽象模型内。每个小时步骤先释放新作业，再执行控制动作、调度工作、计算功率并推进队列截止时间。由于队列实现每步推进一个小时桶，系统拒绝其他时间步长。

<!-- M067 -->
Data-centre power was calculated as

数据中心功率计算为

$$
P^{\mathrm{DC}}_t=P_{\mathrm{fixed}}+\sum_c e_cX_{c,t},
$$

<!-- M069 -->
where e_c is incremental energy per executed GPU-hour, obtained from class-specific active-minus-idle board power multiplied by power usage effectiveness (PUE). Calibration used four NVIDIA RTX PRO 6000 Blackwell Max-Q GPUs connected by PCIe without NVLink. Active training and offline-inference power averaged 259.08 and 300.02 W per GPU, and idle power averaged 13.94 W. Two independent runs per active class supplied the fit, and a third run was held out. Simultaneous GPU observations were averaged within each run; independent runs were the statistical units.

其中 e_c 为每执行一个 GPU-h 对应的增量能耗，由各类别的运行功率减去空闲板卡功率，再乘以电能利用效率指标（PUE）得到。校准使用四块 NVIDIA RTX PRO 6000 Blackwell Max-Q GPU，通过 PCIe 连接，不使用 NVLink。训练和离线推理的单 GPU 平均运行功率分别为 259.08 W 和 300.02 W，平均空闲功率为 13.94 W。每个运行类别使用两次独立运行拟合，第三次运行留出用于检验。同一次运行中同步观测的 GPU 先取平均，统计单位为独立运行。

<!-- M070 -->
The model assumed PUE 1.2 and 300 W of fixed overhead per node. Training and offline-inference active board power used the measured coefficients of 259.08 and 300.02 W per GPU. Online, development, other and unknown rigid workloads used 300.02 W per active GPU as an engineering proxy, with separate 150- and 225-W controls. These coefficients are not measurements of online serving. Rigid demand was held fixed at its class-weighted mean, so online request latency and burst-level power were not simulated. The hardware measurements constrain the batch-work power conversion, not the representativeness of the workload mix.

模型假设 PUE 为 1.2，每个节点固定开销为 300 W。训练与离线推理的活动板卡功率分别采用测得的每 GPU 259.08 W 和 300.02 W 系数。在线、开发、其他和未知刚性工作采用每个活动 GPU 300.02 W 的工程代理，并另设 150 W 和 225 W 对照。这些系数不是在线服务的实测功率。刚性需求固定为类别加权均值，因此没有模拟在线请求延迟或突发阶段功率。硬件测量约束的是批处理的功率换算，而非工作构成的代表性。

<!-- M071 -->
### Baselines, compute debt and successful delivery

### 基线、计算债务与成功交付

<!-- M072 -->
Every controlled episode had a no-demand-response baseline with the same community profile, jobs, deadlines and hardware. Compute debt measured the additional dynamic energy required to clear the controlled backlog relative to this baseline:

每个受控回合均配有一个社区曲线、作业、截止时间和硬件相同的不参与需求响应基线。计算债务衡量的是：相对于该基线，清空受控积压工作所需的额外动态能耗：

$$
D^{\mathrm{comp}}_t=\frac{\mathrm{PUE}}{1000}\sum_c\Delta B_{c,t}\left(p^{\mathrm{active}}_c-p^{\mathrm{idle}}\right).
$$

<!-- M074 -->
where $\Delta B_{c,t}$ is controlled minus baseline backlog in GPU-h, board powers are in W and compute debt is in kWh. Recovery and rebound were evaluated over the declared post-event window, with the clearance tail used to assess terminal backlog. For requested reduction R, delivered power was $\Delta P_t=\max(0,P^{\mathrm{baseline}}_t-P^{\mathrm{control}}_t)$. Mean event delivery, $\sum_{t\in E}\min(\Delta P_t,R)/(R|E|)$, had to reach 0.95, and every event hour also had to satisfy

其中 $\Delta B_{c,t}$ 为受控减基准积压，单位 GPU 小时；板卡功率单位为 W，计算债务单位为 kWh。在声明的事件后窗口评估恢复与反弹，清空尾段用于评估末期积压。对于请求削减 R，交付功率为 $\Delta P_t=\max(0,P^{\mathrm{baseline}}_t-P^{\mathrm{control}}_t)$。平均事件交付 $\sum_{t\in E}\min(\Delta P_t,R)/(R|E|)$ 必须达到 0.95，且每个事件小时还须满足

$$
P^{\mathrm{control}}_t \leq P^{\mathrm{baseline}}_t-0.95R.
$$

<!-- M076 -->
Success further required a deadline-miss fraction of eligible work no greater than 0.01, a rebound ratio no greater than 0.25, an event-plus-recovery peak-relief fraction of at least 0.50 and terminal backlog no greater than 0.02 of offered work. Rebound was the maximum positive controlled-minus-baseline PCC load in the 24-h recovery window, divided by peak event reduction. Mean and minimum interval delivery were reported separately. All criteria were fixed in the protocol; average delivered energy could not compensate for a failed hourly requirement.

成功还要求：超期工作比例不超过 0.01，反弹比不超过 0.25，事件及恢复窗口的峰值缓解比例至少为 0.50，终端积压不超过所提交工作量的 0.02。反弹定义为 24 h 恢复窗口内受控公共连接点负荷相对基线的最大正增量，除以事件期间的峰值削减量。平均交付和最小区间交付分别报告。全部标准均预先固定在协议中；平均交付电量不能补偿某个小时要求未达标。 期限违约率的分母为到达的可参与工作 GPU 小时量。

<!-- M023_zero_methods -->
The structural study additionally required zero total missed eligible work, allowing only 10<sup>−7</sup> GPU-h for numerical round-off. Both response and no-response trajectories had to satisfy that zero criterion; all electrical and terminal-backlog thresholds were unchanged. The 0.1% allowance was a secondary reported endpoint without offer selection. Baseline failures remained failures rather than exclusions. Earlier selected offers were also rescored at zero loss, explicitly as a retrospective check.

结构研究还检验了全部可参与工作的总期限违约量为零的要求，仅允许 10<sup>−7</sup> GPU-h 的数值舍入容差。响应与无响应轨迹都必须满足该零违约标准；电力与期末积压门槛保持不变。0.1% 容忍度作为次要报告终点，不用于选择报价。基线不合格计为失败，不予剔除。此前选出的报价也进行了零损失重评分，并明确标为回顾性核对。

<!-- M077 -->
### Relaxed planning and independent qualification

### 放松规划与独立资格检验

<!-- M078 -->
The aggregate PI programme maximised R under cumulative class-release and class-deadline constraints. These are necessary aggregate conditions, but are a relaxation when job windows cross: work executed for an earlier, later-deadline job can satisfy a cumulative due-work inequality for a different job. Its retained optima therefore define relaxed planning envelopes, not generally job-feasible capacities. Their second order statistic among 100 scenarios is a 95%/95% tolerance statistic of that relaxed quantity, with achieved confidence 0.96292.<sup>33</sup> It does not guarantee feasible work scheduling. Controller offers instead use completed queue simulations on independent seeds; their joint delivery-and-service probability is assessed by a one-sided 95% Wilson lower bound, required to reach 0.95.<sup>34,35</sup> The strict-window feasibility diagnostics use each work group’s own release and deadline.

累计 PI 程序在累计类别释放量与累计类别到期量约束下最大化 R。这些是必要的汇总条件，但当作业时间窗交叉时构成放松：为一个较早释放、较晚到期的作业完成的工作，可能满足另一个作业的累计到期不等式。因此，保留的最优值给出放松模型的规划界限，并非一般都能满足实际作业时间窗的容量。100 个情景中的第二顺序统计量，是该放松量在 95%/95% 条件下的容忍统计量，实际达到的置信度为 0.96292。<sup>33</sup> 它不保证存在可行作业调度。控制器报价则来自独立种子上的完整队列模拟；交付与服务联合概率用单侧 95% Wilson 下界评价，要求达到 0.95。<sup>34,35</sup> 以下新增可行性诊断使用每个工作组自身的释放时间与期限。

<!-- M079 -->
The causal controller retained the six-hour robust MPC, historical-arrival uncertainty envelope and objective weights of the earlier implementation. It observed only released jobs, current queue state and the declared forecast. Its event cap required at least 95% delivery. Because the rebound criterion divides recovery overshoot by actual peak delivered power, the corrected recovery cap used 0.25 × 0.95 × requested power rather than 0.25 × requested power. Continuous actions were rounded towards the feasible side when converted to float32. This electrical cap does not guarantee deadline feasibility. Candidates at 50%, 75%, 90% and 100% of the development Relaxed PI statistic were evaluated separately; no monotonicity between candidates was assumed.

因果控制器保留此前实现中的六小时鲁棒 MPC、历史到达量不确定性包络和目标权重，只观察已释放作业、当前队列状态及声明的预测。事件功率上限要求至少交付 95%。由于反弹指标以实际最大削减功率为分母，修正后的恢复上限采用 0.25 × 0.95 × 承诺功率，而非 0.25 × 承诺功率。连续动作转换为 float32 时向可行一侧舍入。这项电气上限不保证截止时间可行性。开发 放松 PI 统计量的 50%、75%、90% 和 100% 候选分别接受检验，不假定候选之间具有单调性。

<!-- M080 -->
### Repeated commitments and structural controls

### 重复承诺与结构对照

<!-- M081 -->
All new structural tests used the corrected MPC wrapper, which retains a separate ceiling for each observed event-and-recovery window and clips the proposal to the strictest live ceiling. It uses elapsed baseline peaks and current observations, without future jobs or unannounced calls. Earlier comparisons with the original implementation and guarded greedy policy are retained in Supplementary Methods 6. New candidates were 25%, 50%, 75% and 100% of the fixed 5.898243186-kW reference request. Selection was separate for the 1% and zero-miss endpoints and preceded independent confirmation; successful unselected comparators were not promoted.

全部新增结构检验使用修正后的 MPC 包装器：为每个已观测的事件及恢复窗口保留独立上限，并按当前最严格的上限截断建议动作。它仅使用已发生的基线峰值与当前观测，不读取未来作业或未通知的调用。原实现及加入相同保护的贪心策略比较保留在补充方法 6。新候选为固定参考请求 5.898243186 kW 的 25%、50%、75% 和 100%。1% 与零违约终点分别选择候选，随后独立确认；未被选中的对照即使确认成功，也不追认为已选报价。

<!-- M023_structural_methods -->
At fixed 10% work eligibility and 576 GPUs, offered utilisation was total work divided by installed GPU-hours, set to 50%, 65% or 80%. Deadline slack was unchanged or halved with a one-hour floor; flexible GPU allocation was 10%, with 20% controls at 65% and 80% utilisation under tight deadlines. The final event started at hour 111 plus a seeded uniform integer from 0 to 23; preceding starts were spaced backwards by 16 or 24 h. All eight variants tested eight-hour calls, and the reference also tested four-hour calls at 16-h spacing. A fresh eight-hour final call at the same time removed the preceding calls. All recovery windows ended during 168 h of arrivals, followed by a 48-h clearance tail. Development seeds 984000–984099 and confirmation seeds 985000–985299 supplied 7,600 and 13,200 complete replays, respectively. Two pilot seeds were excluded.

固定 10% 工作可参与和 576 个 GPU 后，将工作供给利用率定义为总工作量除以已安装 GPU 小时数，设为 50%、65% 或 80%。期限余量保持参考值或减半，下限为一小时；灵活 GPU 分配为 10%，并在 65% 和 80% 利用率的紧期限情景中增加 20% 分配对照。最后一次事件从第 111 小时加一个由种子确定、在 0–23 间均匀抽取的整数开始；此前事件依次向前相隔 16 或 24 h。八个变体均检验八小时调用，参考条件还检验 16 h 开始间隔的四小时调用。相同时刻的孤立八小时末次调用移除前三次事件。所有恢复窗口均在 168 h 到达阶段内结束，随后有 48 h 清空尾段。开发种子 984000–984099 与确认种子 985000–985299 分别产生 7,600 和 13,200 次完整重放；两个试运行种子不纳入分析。

<!-- M023_temporal_methods -->
For the external timing stress test, hourly submission counts from the Alibaba 2020 GPU trace<sup>28</sup> supplied eight consecutive 168-h blocks. Counts set the hourly weights of synthetic class-specific work, preserving each class total and reference deadlines. The paired alternative permuted complete hourly blocks within the same week. Ten synthetic realisations per week crossed both orderings and 10%/20% GPU allocations with five frozen programme–request combinations, giving 1,600 replays without retuning. Results are reported by observed week and descriptively across 80 realisations per condition; they are not 80 independent production weeks.

外部时序压力检验采用 Alibaba 2020 GPU 轨迹的每小时提交计数，<sup>28</sup> 提供连续八个 168 h 区块。计数决定各类别合成工作的逐小时权重，同时保留各类总工作量与参考期限。配对替代条件在同一周内置乱完整小时块。每周十次合成实现，交叉两种顺序、10%/20% GPU 分配与五个冻结的“方案—请求”组合，共 1,600 次重放，不重新调参。结果按真实周报告，并对每条件 80 次实现作描述性汇总；它们不等于 80 个独立生产周。

<!-- M082 -->
### Photovoltaic hosting and utilisation

### 光伏接纳容量与利用率

<!-- M083 -->
Community PCC power was

社区公共连接点功率为

$$
P^{\mathrm{PCC}}_t=L_t+P^{\mathrm{DC}}_t+P^{\mathrm{ch}}_t-P^{\mathrm{dis}}_t-G^{\mathrm{PV}}_t,
$$

<!-- M085 -->
with imports capped at 1,100 kW and exports prohibited. For each scenario we fixed the GPU installation and maximised PV nameplate subject to at most 5% curtailment, zero missed GPU-hours and at most 2% terminal backlog. BESS supplied 100-kW charge/discharge power and 200-kWh energy, with 0.95 charge and discharge efficiencies and initial and terminal state of charge of 50%. A mixed-integer formulation prohibited simultaneous charging and discharging. All-scenario hosting was the minimum scenario capacity, reported only if every scenario was feasible.

其中进口功率限制为 1,100 kW，并禁止反向送电。对每个情景，我们固定 GPU 设施规模，在弃光不超过 5%、未按期完成工作为零、末期积压不超过 2% 的条件下最大化光伏额定容量。储能充放电功率为 100 kW、容量为 200 kWh，充电和放电效率均为 0.95，初始与末期荷电状态均为 50%。混合整数公式禁止同时充放电。全情景光伏承载容量取各情景容量的最小值，且仅在所有情景均可行时报告。

<!-- M086 -->
The utilisation programme fixed PV at 500 kW and retained each configuration's own data-centre power model. Its lexicographic objective first preserved service feasibility and then maximised local PV use within a 10<sup>−5</sup>-kWh tolerance, followed by grid-import and battery-throughput objectives. Rigid and flexible operation were paired under both BESS conditions on the first 100 confirmation seeds. Mean utilisation contrasts used 10,000 paired bootstrap resamples and pointwise 95% intervals. HiGHS<sup>36</sup> used one thread per solve, with independent scenarios parallelised externally. Storage problems retained HiGHS 1.15.1 default relative MIP gap 10<sup>−4</sup> and absolute gap 10<sup>−6</sup>. The 10<sup>−5</sup>-kWh lexicographic lock is not the MIP optimality tolerance. Utilisation contrasts near the roughly 0.01-percentage-point scale associated with that relative gap are not interpreted as resolved storage benefits; paired sampling intervals exclude optimisation uncertainty.

利用率优化将光伏固定为 500 kW，并保留每种配置自身的数据中心功率模型。词典序目标先保持服务可行，再在 10<sup>−5</sup> kWh 容差内最大化本地光伏利用，之后优化电网进口和电池吞吐量。在前 100 个确认种子上，有/无储能两种条件下的刚性与灵活运行均配对比较。平均利用率差异使用 10,000 次配对自助重采样和逐项 95% 区间。HiGHS<sup>36</sup> 每次求解使用一个线程，并在不同情景之间并行。 储能问题保留 HiGHS 1.15.1 的默认相对 MIP 间隙 10<sup>−4</sup> 和绝对间隙 10<sup>−6</sup>。10<sup>−5</sup> kWh 的词典序锁定不等于 MIP 最优性容差。接近该相对间隙对应的约 0.01 个百分点尺度的利用率差异，不解释为已分辨的储能条件下收益；配对抽样区间不包含优化不确定性。

<!-- M087 -->
### Economic participation

### 经济参与

<!-- M088 -->
Economic screening used each configuration's development-selected, independently tested four- or eight-hour zero-notice offer. Controlled and no-response trajectories supplied paired energy, delay, deferred work and service outcomes from the first call through the 48-h clearance tail. Performance revenue used non-negative PCC reduction capped at the offer in each event hour. Annual net value retained the following accounting structure; inactive or unmeasured terms were stated explicitly rather than inferred from the hardware measurements:

经济筛选使用各配置在开发阶段选出、经独立检验的四小时或八小时零通知承诺。受控与无响应轨迹从首次调用开始，一直覆盖至 48 小时清空尾段结束，提供配对的能耗、延迟、推迟工作量及服务结果。履约收入按事件各小时非负的 PCC 削减量计算，并以上报承诺为限。年度净值保留下述核算结构；未启用或未测量的项目明确声明，而不从硬件测量中推断：

$$
V_{\mathrm{annual}}(K)=R_{\mathrm{capacity}}+R_{\mathrm{performance}}+V_{\mathrm{energy}}+V_{\mathrm{connection}}-C_{\mathrm{enable}}-C_{\mathrm{reserve}}-C_{\mathrm{opportunity}}-C_{\mathrm{delay}}-C_{\mathrm{SLA}}-C_{\mathrm{checkpoint}}-C_{\mathrm{penalty}}.
$$

<!-- M090 -->
Reference prices were US$50 per MWh of capped delivered energy, US$0.10 per kWh of incremental electricity and US$0.005 per GPU-h per hour of additional waiting. We solved for the capacity payment making the fifth percentile of 2,000 bootstrap annual net values non-negative. This was a decision statistic, not a confidence interval. Natural-slack participation incurred no reserve or displacement charge. The reserve case annualised 0.15 abstract reserved PCC-side kW per offered kW at US$2,500 per reserved kW, four-year life, 8% discount, 10% salvage and 3% annual operation and maintenance. The displacement case added an assumed US$0.25 per deferred GPU-h; this exposure was distinct from delay cost and was not a measured revenue loss. Connection benefits and checkpoint costs were unpriced; the reference missed-work price was zero. Existing-GPU depreciation was not inferred as an incremental response cost, and the reserve-capital scenario did not model wear or ageing.

参考价格为：封顶后的交付电量每 MWh 50 美元，增量用电每 kWh 0.10 美元，额外等待每 GPU 小时每小时 0.005 美元。我们求使 2,000 次自助抽样年度净值的第 5 百分位不为负的容量补偿。这是决策统计量，而非置信区间。自然空闲参与不计预留或挤占收费。预留情景按每千瓦承诺对应 0.15 个抽象 PCC 侧预留千瓦进行年化：每预留千瓦投资 2,500 美元、寿命四年、折现率 8%、残值 10%、年运维 3%。挤占情景增加每推迟 GPU 小时 0.25 美元的假定价值暴露；这与延迟成本不同，也不是实测收入损失。 接入收益与检查点成本未定价，参考未完成工作价格为零。没有将既有 GPU 折旧推断为增量响应成本，预留资本情景也不模拟磨损或老化。

<!-- M091 -->
Enablement costs combined a site-wide annual charge with a variable per-kilowatt charge:

接入与使能成本由场站年度固定费用及按千瓦计的可变费用组成：

$$
C_{\mathrm{enable}}(K)=\mathbf 1[K>0]C_{\mathrm{fixed,site}}+c_{\mathrm{variable}}K.
$$

<!-- M093 -->
The fixed site charge was US$25,000 per year and the variable enablement charge was zero. For 1-MW accounting, offered power and physical ledger quantities were multiplied by 1000 divided by the configuration's own operating peak, with the fixed charge applied once and no diversification assumed. This does not certify a 1-MW installation. Annual draws sampled 50 independent single events or 12 independent complete four-call series, retaining failed trajectories. Reserve life, delay price, displaced-value exposure, missed-work price and fixed site cost were sensitivity inputs, not operator estimates. The original external-source register<sup>37–42</sup> provides context for financial ranges, not validation of these scenario prices.

站点固定费用为每年 25,000 美元，可变启用费用为零。在 1 MW 会计尺度下，将承诺功率与物理账本量同乘以“1000 除以该配置自身运行峰值”，固定费用仅计一次，且不假定风险分散。这不构成对 1 MW 设施的认证。年度抽样选择 50 个独立单次事件，或 12 个独立完整四调用序列，并保留失败轨迹。预留寿命、延迟价格、挤占价值暴露、未完成工作价格和站点固定成本均为敏感性输入，而非运营商估计。原外部来源登记表<sup>37–42</sup> 为财务范围提供背景，并不验证这些情景价格。

<!-- M093_series_method -->
Repeated-programme costs were accumulated once per hour over the complete paired series. A programme that did not qualify was identified as such; its conditional cost did not create an eligible offer. Prices of US$0, 0.25 and 1 per missed GPU-h were separately evaluated, and contract-specific non-performance penalties were not priced. Independent annual draws do not reproduce a continuously operating year.

重复方案的成本沿完整配对序列逐小时累计，每小时只计一次。未通过资格检验的方案予以明确标识，其条件性成本不产生合格承诺。未完成工作每 GPU 小时 0、0.25 和 1 美元的价格单独评估，合同特定的不履约罚金未定价。独立年度抽样不复现全年连续运行。

<!-- M023_cost_method -->
The fee decomposition used common annual draws and the same linear-interpolation weights at the total net-cost 95th percentile for every component; it did not add marginal component quantiles. Additional screens crossed site fees US$0, 1,000, 2,500, 5,000, 10,000 and 25,000, waiting prices US$0, 0.005 and 0.01 per GPU-h/h, and missed-work prices US$0 and 1 per GPU-h. Sharing a US$25,000 fee among ten or five resources gave US$2,500 or 5,000 without a diversification benefit. For qualified product j with accounting capacity K_j and annual net operating cost O_j at its 95th percentile, the fifth-percentile net value was P_j K_j − O_j − F. Duration-price boundaries compared these values and the zero value of not participating. They are algebraic consequences of the stated ledgers and prices, not estimated market tariffs.

费用分解采用共同年度抽样，对每一成本项使用总净成本第 95 百分位对应的相同线性插值权重，不能相加各项自身的边际分位数。新增筛选交叉场站费用 0、1,000、2,500、5,000、10,000 和 25,000 美元，等待价格每 GPU-h 每小时 0、0.005 和 0.01 美元，以及每 GPU-h 期限违约工作价格 0 和 1 美元。25,000 美元由十个或五个资源分摊，分别为 2,500 或 5,000 美元，不附加分散风险收益。对合格产品 j，若核算容量为 K_j、年度净运行成本第 95 百分位为 O_j，其净值第五百分位为 P_j K_j − O_j − F。时长价格边界比较这些净值及不参与的零净值。它们是指定账本与价格的代数结果，不是估计的市场价格。

<!-- M094 -->
### Sensitivity analysis and statistical reporting

### 敏感性分析与统计报告

<!-- M095 -->
The five eligibility scenarios used a declared matching rule for GPU allocation and therefore are not a one-factor experiment across the whole range. Two additional controls kept 10% eligibility and the same jobs while assigning 20% or 30% of GPUs to the flexible pool. Two further controls changed only the unmeasured rigid-class active-power proxy to 150 or 225 W. Each control repeated PI planning, the same development-selected fixed requests, PV analysis and economic accounting. Confirmation never retuned the controller or selected new offers for these controls. Earlier broader parameter, regional and joint-share studies are retained with their original workload scope in the archived v0.19 Supplementary Information.

五档资格情景采用声明的 GPU 匹配分配规则，因此整个范围并不是单因素实验。两个额外对照保持 10% 资格和相同作业，只将 20% 或 30% 的 GPU 分配给灵活池。另两个对照只将未测刚性类别的活动功率代理改为 150 W 或 225 W。每项对照均重做 PI 规划、相同开发承诺的固定请求测试、光伏分析和经济核算。确认阶段不重新调节控制器，也不为这些对照选择新承诺。此前范围更广的参数、地域和联合比例研究在归档的 v0.19 补充材料中按其原始工作负载范围保留。

<!-- M096 -->
Economic sensitivities recomputed payments from the fixed paired ledgers with common annual draws, without changing physical trajectories or offer selection. They crossed delay prices, site costs and assumed displaced-compute values, and separately varied missed-work prices. Hardware procurement, actual online-service costs and a continuous-year market simulation were not inferred from these screens.

经济敏感性分析使用固定配对账本和共同年度抽样重新计算补偿，不改变物理轨迹或承诺选择。分析交叉变化延迟价格、站点成本和假定挤占算力价值，并单独变化未完成工作价格。这些筛选不用于推断硬件采购、实际在线服务成本或全年连续市场运行。

<!-- M097 -->
Independent scenarios were the statistical units; multiple calls within a scenario were not independent replicates. Relaxed PI tolerance statistics, Wilson probability lower bounds and paired bootstrap intervals were pointwise. Notice comparisons used exact paired McNemar tests with Holm correction across the 20 comparisons. Hardware intervals retained the original independent-run analysis. Source Data contain per-scenario outcomes, development selection tables, complete paired ledgers and ready-to-plot summaries; hashes link them to the source, protocol and controller versions.

独立情景是统计单位，同一情景中的多次调用不视为独立重复。放松 PI 容忍统计量、Wilson 概率下界及配对自助法区间均为逐项区间。通知比较采用配对精确 McNemar 检验，并对 20 项比较进行 Holm 校正。硬件区间保留原独立运行分析。源数据包含逐情景结果、开发选值表、完整配对账本和可直接绘图的汇总，哈希将其与来源、协议和控制器版本关联。

<!-- M023_stats -->
Structural contrasts resampled 300 complete paired scenario seeds 5,000 times. Exact McNemar tests were Holm-adjusted over the 36 binary structural contrasts; the 16 additional matched-target electrical contrasts formed a separate family. The zero-loss and 1% offer tests each retained the pointwise one-sided 95% Wilson lower-bound criterion of 0.95. Multiple successful selections do not create a simultaneous confidence guarantee. Submission-order comparisons retained the observed week as the external sampling unit and were not assigned binomial certificates from pooled synthetic realisations.

结构对照对 300 个完整配对情景种子进行 5,000 次重抽样。精确 McNemar 检验在 36 个二元结构对照之间使用 Holm 校正；额外 16 个末次调用电力对照构成单独的检验族。零损失与 1% 报价检验均保留逐点单侧 95% Wilson 概率下界不低于 0.95 的规则。多个选择成功不构成同时置信保证。提交顺序比较保留真实周作为外部抽样单位，不把合并的合成实现赋予二项资格证明。

<!-- M024_refinement -->
Local refinement fixed the reference workload and controller and tested fractions 0.50–0.75 for H8P16 and 0.75–1.00 for H4P16, in steps of 0.05 of the unchanged 5.898243186-kW request. H denotes duration and P start spacing. Seeds 988000–988099 supplied development; endpoint-specific selections were frozen before seeds 989000–989299 supplied confirmation. Only selected candidates and prespecified coarse comparators entered confirmation, with no reselection. The grid ceiling for eight hours was selected under both standards, so the test did not bracket a continuous maximum. Earlier seeds were not pooled with these data.

局部加密固定参考工作负载与控制器，在原有 5.898243186 kW 请求基础上，H8P16 测试 0.50–0.75，H4P16 测试 0.75–1.00，步长均为 0.05。H 表示时长，P 表示开始间隔。开发使用种子 988000–988099；分终点的选择在确认种子 989000–989299 运行前冻结。确认只检验选中候选与预先指定的粗网格对照，之后不重新选值。两种标准均选中八小时网格上端，因此测试没有夹定连续最大值。早期种子未与本次数据合并。

<!-- M024_pi_methods -->
Perfect-information diagnostics fixed each request and its four event clocks, baseline and 24-h recovery windows. Non-negative execution variables existed only between each class/release/deadline work group’s own release and deadline; execution, misses and terminal work conserved every group. Constraints retained GPU and PCC limits, 95% hourly and capped-mean delivery, 25% rebound relative to actual peak event reduction, 50% full-window peak relief and the original terminal allowance. Binary peak selectors represented the rebound denominator exactly. HiGHS solved the resulting mixed-integer feasibility problem. Thirty-three prespecified structural cases comprised five configurations, three previously used seeds and two service standards, plus three reference 4.42-kW checks; five affected external weeks supplied an additional first-shortage diagnostic each. These mechanism-selected cases were not prevalence samples. All 11 feasible witnesses passed independent work-group and electrical checks. A 90-s unresolved solve was retained and resolved as infeasible after extending only its time limit to 600 s. Full-information feasibility was not treated as causal realizability.

完美信息诊断固定每个请求及其四个事件时刻、基线和 24 h 恢复窗。只有在每个类别—释放时间—期限工作组自身的允许时段内，才建立非负执行变量；执行、漏期及期末工作对每组守恒。约束保留 GPU 与 PCC 限制、95% 逐时及截顶平均交付、相对事件实际峰值减负的 25% 反弹、完整窗口 50% 峰值削减，以及原期末积压容忍度。二进制峰值选择变量精确表示反弹分母，由 HiGHS 求解相应混合整数可行性问题。预先指定的 33 个结构条件包括五种配置、三个已用种子、两个服务标准，以及三个参考 4.42 kW 检查；另从五个受影响的外部周各取首个短缺实现作诊断。这些按机制选择的条件不用于估计发生率。全部 11 个可行见证通过独立工作组与电力约束检查。一次 90 s 未解决的求解保留原记录，仅将时限延长至 600 s 后判为不可行。完美信息可行未被当作因果可实现。

<!-- M024_workload_methods -->
The resource-time transfer test reconstructed each processed job’s GPU-seconds as the sum of requested GPU-equivalents × task launch-to-completion duration across its terminated positive-resource tasks.<sup>28</sup> All 714,903 processed jobs matched the raw task reconstruction; multiplying total requested GPUs by job submission-to-completion time instead differed for 131,379 jobs. The test retained trace hours 168–1511, whose processed time origin is 542,323 s after the raw origin. Within each week, either job counts or submitted task resource-time set hourly weights; each class’s weekly work total was normalised to the reference total. Identical synthetic job classes, deadlines, community traces, event clocks and paired whole-hour permutations were used at each seed (990000 + 100w + r; eight weeks × ten realisations). Fixed 2.95- and 4.42-kW requests gave 640 complete replays. All 320 no-response input variants passed zero-loss service; no failed variant was excluded. Aggregate counts are descriptive. Allocated resource-time is not a sensor measurement of busy GPU time, and the test retains divisible work and synthetic service rules.

资源时间适用测试将每个处理后作业的 GPU 秒数，重建为其已完成且资源量为正的各任务之“请求 GPU 当量 × 任务启动至完成时长”之和。<sup>28</sup> 全部 714,903 个处理后作业均与原始任务重建一致；若改用总请求 GPU 数乘以作业提交至完成时长，则有 131,379 个作业不一致。测试保留轨迹小时 168–1511；处理后的时间原点相对原始原点偏移 542,323 s。各周分别采用任务次数或提交任务资源时间作为逐时权重，每个类别的周工作总量归一到参考总量。每个种子使用相同的合成任务类别、期限、社区轨迹、事件时刻及配对完整小时置乱（种子 990000 + 100w + r；八周各十次实现）。固定 2.95 与 4.42 kW 请求共形成 640 次完整重放。全部 320 个无响应输入变体通过零损失服务，无失败变体被排除。合计数为描述性结果。已分配资源时间不等于传感器测得的 GPU 忙碌时间，测试仍保留可分割工作与合成服务规则。

<!-- M098 -->
## Data Availability

## 数据可用性

<!-- M099 -->
Community demand was obtained from the NREL End-Use Load Profiles through the OEDI building-stock data lake.<sup>31,32</sup> Workload records came from the official Alibaba cluster-trace-gpu-v2026 release,<sup>20</sup> with the 2020 GPU trace supplying the separate chronological submission test.<sup>28</sup> Retrieval locations, preprocessing records and original input hashes are listed in data/manifests/sources.yaml. Raw third-party releases are accessed from their original providers. The accompanying Source Data bundle contains the full class-composition audit, scenario and controller identities, development selection, all trial-level outcomes, complete development and confirmation trajectories and paired economic ledgers, renewable optimisation results, calibration inputs and ready-to-plot tables. CSV and Parquet files have data dictionaries and SHA-256 manifests. Earlier benchmark outputs are preserved in a separately labelled archive. Public archival deposition of this revised bundle remains pending at [ZENODO DOI TO BE ADDED]. Submission counts, processed submission-time records, frozen scenarios and all 22,400 new replays accompany the structural Source Data. The focused extension adds 3,040 full replays, 656,640 hourly rows, 38 resolved exact-window feasibility diagnoses and task-level resource-time reconstruction records.

社区需求来自 NREL 通过 OEDI 建筑存量数据湖提供的终端用电曲线。<sup>31,32</sup> 工作记录来自 Alibaba 官方 cluster-trace-gpu-v2026 发布。<sup>20</sup> 检索位置、预处理记录与原始输入哈希列于 data/manifests/sources.yaml；第三方原始发布从原提供方获取。随附源数据包包含完整类别构成审计、情景及控制器标识、开发选值、所有试验级结果、完整开发与确认轨迹与配对经济账本、可再生能源优化结果、校准输入和可直接绘图的表格。CSV 与 Parquet 配有数据字典及 SHA-256 清单。此前基准输出保存在单独标明的归档中。本修订包的公开归档存储仍待完成：[ZENODO DOI TO BE ADDED]。 新增独立时序检验采用 Alibaba 2020 GPU 轨迹的提交记录；其计数、处理后时间记录、冻结场景与全部 22,400 次新增重放均随源数据保存。<sup>28</sup> 集中补强另增加 3,040 次完整重放、656,640 行逐时数据、38 个已解决的严格时间窗可行性诊断，以及任务级资源时间重建记录。

<!-- M100 -->
## Code Availability

## 代码可用性

<!-- M101 -->
The AIDRBench project is hosted at https://github.com/daxiang415/AIDRBench. The accompanying revision bundle includes the exact study drivers, corrected-controller implementation, frozen protocols, analysis scripts and standalone Python redraw commands used here. Public archival release of the revised submission code and its software licence remain pending author confirmation; no new release DOI is claimed.

AIDRBench 项目位于 https://github.com/daxiang415/AIDRBench。随附修订包提供本研究所用的精确运行程序、修正控制器实现、冻结协议、分析脚本和独立 Python 重绘命令。修订投稿代码的公开归档发布及软件许可证仍待作者确认，未声称已获得新的发布 DOI。

<!-- M102 -->
## References

## 参考文献

<!-- M_ref42_IEA -->
1. International Energy Agency. *Energy and AI* (IEA, 2025). https://www.iea.org/reports/energy-and-ai

1. International Energy Agency. *Energy and AI* (IEA, 2025). https://www.iea.org/reports/energy-and-ai

<!-- M103 -->
2. Lin, L. et al. Exploding AI power use: an opportunity to rethink grid planning and management. In *Proceedings of the 15th ACM International Conference on Future and Sustainable Energy Systems* 434–441 (ACM, 2024). https://doi.org/10.1145/3632775.3661959

2. Lin, L. et al. AI 用电量激增：重新思考电网规划与管理的契机。 In *Proceedings of the 15th ACM International Conference on Future and Sustainable Energy Systems* 434–441 (ACM, 2024). https://doi.org/10.1145/3632775.3661959

<!-- M104 -->
3. Colangelo, P. et al. AI data centres as grid-interactive assets. *Nat. Energy* **11**, 254–261 (2026). https://doi.org/10.1038/s41560-025-01927-1

3. Colangelo, P. et al. 作为电网交互资产的 AI 数据中心。 *Nat. Energy* **11**, 254–261 (2026). https://doi.org/10.1038/s41560-025-01927-1

<!-- M105 -->
4. Wierman, A., Liu, Z., Liu, I. & Mohsenian-Rad, H. Opportunities and challenges for data center demand response. In *2014 International Green Computing Conference* 1–10 (IEEE, 2014). https://doi.org/10.1109/IGCC.2014.7039172

4. Wierman, A., Liu, Z., Liu, I. & Mohsenian-Rad, H. 数据中心需求响应的机遇与挑战。 In *2014 International Green Computing Conference* 1–10 (IEEE, 2014). https://doi.org/10.1109/IGCC.2014.7039172

<!-- M106 -->
5. Li, J., Bao, Z. & Li, Z. Modeling demand response capability by Internet data centers processing batch computing jobs. *IEEE Trans. Smart Grid* **6**, 737–747 (2015). https://doi.org/10.1109/TSG.2014.2363583

5. Li, J., Bao, Z. & Li, Z. 处理批量计算作业的互联网数据中心需求响应能力建模。 *IEEE Trans. Smart Grid* **6**, 737–747 (2015). https://doi.org/10.1109/TSG.2014.2363583

<!-- M107 -->
6. Zhang, Y., Wilson, D. C., Paschalidis, I. Ch. & Coskun, A. K. HPC data center participation in demand response: an adaptive policy with QoS assurance. *IEEE Trans. Sustain. Comput.* **7**, 157–171 (2022). https://doi.org/10.1109/TSUSC.2021.3077254

6. Zhang, Y., Wilson, D. C., Paschalidis, I. Ch. & Coskun, A. K. HPC 数据中心参与需求响应：具有 QoS 保障的自适应策略。 *IEEE Trans. Sustain. Comput.* **7**, 157–171 (2022). https://doi.org/10.1109/TSUSC.2021.3077254

<!-- M108 -->
7. Zhang, Y., Wilson, D. C., Paschalidis, I. Ch. & Coskun, A. K. A data center demand response policy for real-world workload scenarios in HPC. In *2021 Design, Automation & Test in Europe Conference & Exhibition* 282–287 (IEEE, 2021). https://doi.org/10.23919/DATE51398.2021.9474075

7. Zhang, Y., Wilson, D. C., Paschalidis, I. Ch. & Coskun, A. K. 面向 HPC 真实工作负载情景的数据中心需求响应策略。 In *2021 Design, Automation & Test in Europe Conference & Exhibition* 282–287 (IEEE, 2021). https://doi.org/10.23919/DATE51398.2021.9474075

<!-- M109 -->
8. Liu, Z., Wierman, A., Chen, Y., Razon, B. & Chen, N. Data center demand response: avoiding the coincident peak via workload shifting and local generation. *Perform. Evaluation* **70**, 770–791 (2013). https://doi.org/10.1016/j.peva.2013.08.014

8. Liu, Z., Wierman, A., Chen, Y., Razon, B. & Chen, N. 数据中心需求响应：通过工作负载转移与本地发电避免峰值重合。 *Perform. Evaluation* **70**, 770–791 (2013). https://doi.org/10.1016/j.peva.2013.08.014

<!-- M110 -->
9. Radovanović, A. et al. Carbon-aware computing for datacenters. *IEEE Trans. Power Syst.* **38**, 1270–1280 (2023). https://doi.org/10.1109/TPWRS.2022.3173250

9. Radovanović, A. et al. 面向数据中心的碳感知计算。 *IEEE Trans. Power Syst.* **38**, 1270–1280 (2023). https://doi.org/10.1109/TPWRS.2022.3173250

<!-- M111 -->
10. Riepin, I., Brown, T. & Zavala, V. M. Spatio-temporal load shifting for truly clean computing. *Adv. Appl. Energy* **17**, 100202 (2025). https://doi.org/10.1016/j.adapen.2024.100202

10. Riepin, I., Brown, T. & Zavala, V. M. 通过时空负荷转移实现真正的清洁计算。 *Adv. Appl. Energy* **17**, 100202 (2025). https://doi.org/10.1016/j.adapen.2024.100202

<!-- M112 -->
11. Zheng, J., Chien, A. A. & Suh, S. Mitigating curtailment and carbon emissions through load migration between data centers. *Joule* **4**, 2208–2222 (2020). https://doi.org/10.1016/j.joule.2020.08.001

11. Zheng, J., Chien, A. A. & Suh, S. 通过数据中心之间的负荷迁移减少弃电与碳排放。 *Joule* **4**, 2208–2222 (2020). https://doi.org/10.1016/j.joule.2020.08.001

<!-- M113 -->
12. Goiri, Í., Katsak, W., Le, K., Nguyen, T. D. & Bianchini, R. Parasol and GreenSwitch: managing datacenters powered by renewable energy. In *Proceedings of the Eighteenth International Conference on Architectural Support for Programming Languages and Operating Systems* 51–64 (ACM, 2013). https://doi.org/10.1145/2451116.2451123

12. Goiri, Í., Katsak, W., Le, K., Nguyen, T. D. & Bianchini, R. Parasol 与 GreenSwitch：可再生能源供电数据中心的管理。 In *Proceedings of the Eighteenth International Conference on Architectural Support for Programming Languages and Operating Systems* 51–64 (ACM, 2013). https://doi.org/10.1145/2451116.2451123

<!-- M114 -->
13. Lechowicz, A. et al. The online pause and resume problem: optimal algorithms and an application to carbon-aware load shifting. *Proc. ACM Meas. Anal. Comput. Syst.* **7**, 1–32 (2023). https://doi.org/10.1145/3626776

13. Lechowicz, A. et al. 在线暂停与恢复问题：最优算法及其在碳感知负荷转移中的应用。 *Proc. ACM Meas. Anal. Comput. Syst.* **7**, 1–32 (2023). https://doi.org/10.1145/3626776

<!-- M115 -->
14. Zhao, D. et al. Sustainable supercomputing for AI: GPU power capping at HPC scale. In *Proceedings of the 2023 ACM Symposium on Cloud Computing* 588–596 (ACM, 2023). https://doi.org/10.1145/3620678.3624793

14. Zhao, D. et al. 面向 AI 的可持续超级计算：HPC 规模下的 GPU 功率限额。 In *Proceedings of the 2023 ACM Symposium on Cloud Computing* 588–596 (ACM, 2023). https://doi.org/10.1145/3620678.3624793

<!-- M116 -->
15. Caprara, A., Yu, Y., Teng, F., Junyent-Ferré, A., Bullich-Massagué, E. & Aragüés-Peñalba, M. Data center workload flexibility for power system demand response: evidence from Alibaba traces. *Int. J. Electr. Power Energy Syst.* **178**, 111940 (2026). https://doi.org/10.1016/j.ijepes.2026.111940

15. Caprara, A., Yu, Y., Teng, F., Junyent-Ferré, A., Bullich-Massagué, E. & Aragüés-Peñalba, M. 面向电力系统需求响应的数据中心工作负载灵活性：来自 Alibaba 运行轨迹的证据。 *Int. J. Electr. Power Energy Syst.* **178**, 111940 (2026). https://doi.org/10.1016/j.ijepes.2026.111940

<!-- M117 -->
16. Chen, Y. & Zheng, X. To defer or to shift? The role of AI data center flexibility on grid interconnection. In *Proceedings of the 2026 ACM Sustainability Week* 322–327 (ACM, 2026). https://doi.org/10.1145/3765611.3815593

16. Chen, Y. & Zheng, X. 延后还是转移？AI 数据中心灵活性在并网中的作用。 In *Proceedings of the 2026 ACM Sustainability Week* 322–327 (ACM, 2026). https://doi.org/10.1145/3765611.3815593

<!-- M118 -->
17. Zhao, M., Wang, X. & Mo, J. Workload and energy management of geo-distributed datacenters considering demand response programs. *Sustain. Energy Technol. Assess.* **55**, 102851 (2023). https://doi.org/10.1016/j.seta.2022.102851

17. Zhao, M., Wang, X. & Mo, J. 考虑需求响应计划的地理分布式数据中心工作负载与能源管理。 *Sustain. Energy Technol. Assess.* **55**, 102851 (2023). https://doi.org/10.1016/j.seta.2022.102851

<!-- M119 -->
18. Wiesner, P., Behnke, I., Scheinert, D., Gontarska, K. & Thamsen, L. Let's wait awhile: how temporal workload shifting can reduce carbon emissions in the cloud. In *Proceedings of the 22nd International Middleware Conference* 260–272 (ACM, 2021). https://doi.org/10.1145/3464298.3493399

18. Wiesner, P., Behnke, I., Scheinert, D., Gontarska, K. & Thamsen, L. 稍等片刻：工作负载的时间转移如何降低云计算碳排放。 In *Proceedings of the 22nd International Middleware Conference* 260–272 (ACM, 2021). https://doi.org/10.1145/3464298.3493399

<!-- M_ref41 -->
19. Li, M. Beyond Scalar Flexibility: From Eligible AI Workloads to Dependable Load Relief. Preprint at https://arxiv.org/abs/2609.05406 (2026).

19. Li, M. Beyond Scalar Flexibility: From Eligible AI Workloads to Dependable Load Relief. Preprint at https://arxiv.org/abs/2609.05406 (2026).

<!-- M131 -->
20. Li, S. et al. Heterogeneity at hyperscale: characterization and scheduling of large production AI clusters at Alibaba. In *20th USENIX Symposium on Operating Systems Design and Implementation* 2187–2203 (USENIX Association, 2026).

20. Li, S. et al. 超大规模下的异构性：Alibaba 大型生产环境 AI 集群的特征分析与调度。 In *20th USENIX Symposium on Operating Systems Design and Implementation* 2187–2203 (USENIX Association, 2026).

<!-- M120 -->
21. Cioara, T. et al. Optimized flexibility management enacting data centres participation in smart demand response programs. *Future Gener. Comput. Syst.* **78**, 330–342 (2018). https://doi.org/10.1016/j.future.2016.05.010

21. Cioara, T. et al. 通过优化灵活性管理实现数据中心参与智能需求响应计划。 *Future Gener. Comput. Syst.* **78**, 330–342 (2018). https://doi.org/10.1016/j.future.2016.05.010

<!-- M121 -->
22. Wang, W., Abdolrashidi, A., Yu, N. & Wong, D. Frequency regulation service provision in data center with computational flexibility. *Appl. Energy* **251**, 113304 (2019). https://doi.org/10.1016/j.apenergy.2019.05.107

22. Wang, W., Abdolrashidi, A., Yu, N. & Wong, D. 利用计算灵活性提供调频服务的数据中心。 *Appl. Energy* **251**, 113304 (2019). https://doi.org/10.1016/j.apenergy.2019.05.107

<!-- M122 -->
23. Su, T. et al. Grid-enhancing technologies for clean energy systems. *Nat. Rev. Clean Technol.* **1**, 16–31 (2025). https://doi.org/10.1038/s44359-024-00001-5

23. Su, T. et al. 面向清洁能源系统的电网增强技术。 *Nat. Rev. Clean Technol.* **1**, 16–31 (2025). https://doi.org/10.1038/s44359-024-00001-5

<!-- M123 -->
24. Loji, K., Sharma, S., Sharma, G. & Rawat, T. Multiobjective distribution system operation with demand response to optimize solar hosting capacity, voltage deviation index and network loss. *Sci. Rep.* **15**, 300 (2025). https://doi.org/10.1038/s41598-024-82379-7

24. Loji, K., Sharma, S., Sharma, G. & Rawat, T. 利用需求响应优化太阳能接纳容量、电压偏差指标与网络损耗的多目标配电系统运行。 *Sci. Rep.* **15**, 300 (2025). https://doi.org/10.1038/s41598-024-82379-7

<!-- M124 -->
25. Fu, Y., Bai, H., Cai, Y., Yang, W. & Li, Y. Optimal configuration method of demand-side flexible resources for enhancing renewable energy integration. *Sci. Rep.* **14**, 7658 (2024). https://doi.org/10.1038/s41598-024-58266-6

25. Fu, Y., Bai, H., Cai, Y., Yang, W. & Li, Y. 促进可再生能源接入的需求侧灵活资源优化配置方法。 *Sci. Rep.* **14**, 7658 (2024). https://doi.org/10.1038/s41598-024-58266-6

<!-- M125 -->
26. Davies, D. M. et al. Combined economic and technological evaluation of battery energy storage for grid applications. *Nat. Energy* **4**, 42–50 (2019). https://doi.org/10.1038/s41560-018-0290-1

26. Davies, D. M. et al. 面向电网应用的电池储能经济与技术综合评估。 *Nat. Energy* **4**, 42–50 (2019). https://doi.org/10.1038/s41560-018-0290-1

<!-- M126 -->
27. Li, K. et al. Facilitating megacity electricity decarbonization via grid-interactive demand-side resource management. *Nat. Commun.* (2026). https://doi.org/10.1038/s41467-026-76799-4

27. Li, K. et al. 通过与电网交互的需求侧资源管理促进超大城市电力脱碳。 *Nat. Commun.* (2026). https://doi.org/10.1038/s41467-026-76799-4

<!-- M132 -->
28. Weng, Q. et al. MLaaS in the wild: workload analysis and scheduling in large-scale heterogeneous GPU clusters. In *19th USENIX Symposium on Networked Systems Design and Implementation* 945–960 (USENIX Association, 2022).

28. Weng, Q. et al. 真实环境中的 MLaaS：大规模异构 GPU 集群的工作负载分析与调度。 In *19th USENIX Symposium on Networked Systems Design and Implementation* 945–960 (USENIX Association, 2022).

<!-- M127 -->
29. Zhou, Y., Mancarella, P. & Mutale, J. Framework for capacity credit assessment of electrical energy storage and demand response. *IET Gener. Transm. Distrib.* **10**, 2267–2276 (2016). https://doi.org/10.1049/iet-gtd.2015.0458

29. Zhou, Y., Mancarella, P. & Mutale, J. 电储能与需求响应的容量信用评估框架。 *IET Gener. Transm. Distrib.* **10**, 2267–2276 (2016). https://doi.org/10.1049/iet-gtd.2015.0458

<!-- M128 -->
30. Feng, J. et al. Evaluating demand response impacts on capacity credit of renewable distributed generation in smart distribution systems. *IEEE Access* **6**, 14307–14317 (2018). https://doi.org/10.1109/ACCESS.2017.2745198

30. Feng, J. et al. 评估需求响应对智能配电系统中可再生分布式发电容量信用的影响。 *IEEE Access* **6**, 14307–14317 (2018). https://doi.org/10.1109/ACCESS.2017.2745198

<!-- M129 -->
31. Wilson, E. et al. *End-Use Load Profiles for the U.S. Building Stock: Methodology and Results of Model Calibration, Validation, and Uncertainty Quantification*. NREL/TP-5500-80889 (National Renewable Energy Laboratory, 2022). https://doi.org/10.2172/1854582

31. Wilson, E. et al. *美国建筑存量的终端用能负荷曲线：模型校准、验证与不确定性量化的方法及结果*. NREL/TP-5500-80889 (National Renewable Energy Laboratory, 2022). https://doi.org/10.2172/1854582

<!-- M130 -->
32. Parker, A. et al. *ComStock Reference Documentation: Version 1*. NREL/TP-5500-83819 (National Renewable Energy Laboratory, 2023). https://doi.org/10.2172/1967948

32. Parker, A. et al. *ComStock 参考文档：版本 1*. NREL/TP-5500-83819 (National Renewable Energy Laboratory, 2023). https://doi.org/10.2172/1967948

<!-- M133 -->
33. Vangel, M. G. One-sided nonparametric tolerance limits. *Commun. Stat. Simul. Comput.* **23**, 1137–1154 (1994). https://doi.org/10.1080/03610919408813222

33. Vangel, M. G. 单侧非参数容忍限。 *Commun. Stat. Simul. Comput.* **23**, 1137–1154 (1994). https://doi.org/10.1080/03610919408813222

<!-- M134 -->
34. Wilson, E. B. Probable inference, the law of succession, and statistical inference. *J. Am. Stat. Assoc.* **22**, 209–212 (1927). https://doi.org/10.1080/01621459.1927.10502953

34. Wilson, E. B. 概率推断、后继法则与统计推断。 *J. Am. Stat. Assoc.* **22**, 209–212 (1927). https://doi.org/10.1080/01621459.1927.10502953

<!-- M135 -->
35. Brown, L. D., Cai, T. T. & DasGupta, A. Interval estimation for a binomial proportion. *Stat. Sci.* **16**, 101–133 (2001). https://doi.org/10.1214/ss/1009213286

35. Brown, L. D., Cai, T. T. & DasGupta, A. 二项比例的区间估计。 *Stat. Sci.* **16**, 101–133 (2001). https://doi.org/10.1214/ss/1009213286

<!-- M136 -->
36. Huangfu, Q. & Hall, J. A. J. Parallelizing the dual revised simplex method. *Math. Program. Comput.* **10**, 119–142 (2018). https://doi.org/10.1007/s12532-017-0130-5

36. Huangfu, Q. & Hall, J. A. J. 对偶修正单纯形法的并行化。 *Math. Program. Comput.* **10**, 119–142 (2018). https://doi.org/10.1007/s12532-017-0130-5

<!-- M137 -->
37. CoreWeave, Inc. *Annual Report (Form 10-K) for the Year Ended 31 December 2025*. US Securities and Exchange Commission (2026). https://www.sec.gov/Archives/edgar/data/1769628/000176962826000104/crwv-20251231.htm

37. CoreWeave, Inc. *截至 2025 年十二月 31 日的年度报告（Form 10-K）*. US Securities and Exchange Commission (2026). https://www.sec.gov/Archives/edgar/data/1769628/000176962826000104/crwv-20251231.htm

<!-- M138 -->
38. Amazon.com, Inc. *Annual Report (Form 10-K) for the Year Ended 31 December 2025*. US Securities and Exchange Commission (2026). https://www.sec.gov/Archives/edgar/data/1018724/000101872426000004/amzn-20251231.htm

38. Amazon.com, Inc. *截至 2025 年十二月 31 日的年度报告（Form 10-K）*. US Securities and Exchange Commission (2026). https://www.sec.gov/Archives/edgar/data/1018724/000101872426000004/amzn-20251231.htm

<!-- M139 -->
39. Microsoft Corporation. *Annual Report (Form 10-K) for the Fiscal Year Ended 30 June 2025*. US Securities and Exchange Commission (2025). https://www.sec.gov/Archives/edgar/data/789019/000095017025100235/msft-20250630.htm

39. Microsoft Corporation. *截至 2025 年六月 30 日财年的年度报告（Form 10-K）*. US Securities and Exchange Commission (2025). https://www.sec.gov/Archives/edgar/data/789019/000095017025100235/msft-20250630.htm

<!-- M140 -->
40. National Renewable Energy Laboratory. *2024 Annual Technology Baseline: Financial Cases and Methods* (NREL, 2024). https://atb.nrel.gov/electricity/2024/financial_cases_%26_methods

40. National Renewable Energy Laboratory. *2024 年度技术基线：财务情景与方法* (NREL, 2024). https://atb.nrel.gov/electricity/2024/financial_cases_%26_methods

<!-- M141 -->
41. Lawrence Berkeley National Laboratory. *Demand Response Advanced Controls Framework and Cost Assessment* (LBNL, 2017). https://eta-publications.lbl.gov/sites/default/files/demand_response_advanced_controls_framework_and_cost_assessment_final_published.pdf

41. Lawrence Berkeley National Laboratory. *需求响应先进控制框架与成本评估* (LBNL, 2017). https://eta-publications.lbl.gov/sites/default/files/demand_response_advanced_controls_framework_and_cost_assessment_final_published.pdf

<!-- M142 -->
42. PJM Interconnection. *2027/2028 Base Residual Auction Report* (PJM, 2025). https://www.pjm.com/-/media/DotCom/markets-ops/rpm/rpm-auction-info/2027-2028/2027-2028-bra-report.pdf

42. PJM Interconnection. *2027/2028 基础剩余拍卖报告* (PJM, 2025). https://www.pjm.com/-/media/DotCom/markets-ops/rpm/rpm-auction-info/2027-2028/2027-2028-bra-report.pdf

<!-- M143 -->
## Acknowledgements

## 致谢

<!-- M144 -->
[AUTHOR INPUT NEEDED: funding, facilities and non-author contributions.]

[需作者补充：资助、设施及非作者贡献。]

<!-- M145 -->
## Author Contributions

## 作者贡献

<!-- M146 -->
[AUTHOR INPUT NEEDED: CRediT-aligned author contributions.]

[需作者补充：符合 CRediT 分类的作者贡献。]

<!-- M147 -->
## Competing Interests

## 利益冲突

<!-- M148 -->
[AUTHOR INPUT NEEDED: competing-interests declaration.]

[需作者补充：利益冲突声明。]

<!-- M149 -->
## Figure Legends

## 图注

<!-- M150 -->
### Figure 1 | Workload composition and declared permission to defer

### 图 1 | 工作构成与声明的延后权限

<!-- M151 -->
**a,** Requested GPU-hour shares from all 40,522,321 released execution spans, using uncapped duration. The denominator includes online inference, offline inference, training, development, other and unknown work. These are descriptive source totals, not energy shares or an industry estimate. **b,** Training and offline-inference contributions to each eligibility scenario. At 5–20%, a common fraction of low-priority batch work is permitted to wait. The 40% case assumes nearly all batch work opts in; the 60% case replaces 19.058 percentage points of online work with offline work before granting eligibility. Online jobs are never deferred. Source Data retain class-by-priority totals and full-precision scenario definitions.

**a，**采用未截尾时长统计全部 40,522,321 个公开执行区段的申请 GPU 小时份额。分母包含在线推理、离线推理、训练、开发、其他和未知工作。这是源数据总量的描述，不是能耗份额或行业估计。**b，**每档资格中训练与离线推理的贡献。5%–20% 对低优先级批处理采用共同获准等待比例；40% 假定几乎全部批处理同意参与；60% 先将总工作量的 19.058 个百分点由在线替换为离线，再授予资格。在线作业始终不延后。源数据保留类别与优先级交叉汇总及完整精度的情景定义。

<!-- M152 -->
### Figure 2 | Relaxed planning statistics and independently tested single offers

### 图 2 | 放松规划统计量与独立检验的单次报价

<!-- M153 -->
**a,** Relaxed PI tolerance statistics from 100 confirmation scenarios (95% reliability, at least 95% confidence; horizontal marks) and development-selected controller offers (circles; crosses would denote failure to qualify). The two statistics use different constructions and their relative ordering does not imply an information advantage. **b,** Success fractions at the same request under 0-, 2- and 6-h notice, with one-sided 95% Wilson lower limits and 300 independent seeds per condition. Dashed line, 95% qualification threshold. Blue and green identify four- and eight-hour events; shapes distinguish notice. Complete paired outcomes and Holm-adjusted exact McNemar tests are provided. In all ratio plots, * denotes nearly all-batch opt-in at 40%, and † denotes changed business composition at 60%. The retained PI values use aggregate release/deadline relaxations; they are not guaranteed work-group-feasible capacities (Methods).

**a，**由 100 个确认情景得到的 放松 PI 容忍统计量（可靠性 95%、置信度至少 95%；横标），以及开发选出的控制器承诺（圆点；若未通过资格则为叉号）。两项统计构造不同，其高低不表示信息优势。**b，**固定同一请求、提前 0、2、6 小时通知的成功比例，附单侧 95% Wilson 下界；每个条件含 300 个独立种子。虚线为 95% 资格门槛。蓝、绿分别表示四小时和八小时，形状区分通知。完整配对结果及 Holm 校正的精确 McNemar 检验见源数据。所有比例图中，* 表示 40% 需要几乎全部批处理同意参与，† 表示 60% 改变业务构成。 保留的 PI 值采用累计释放/期限放松条件，不保证满足工作组时间窗的容量（见方法）。

<!-- M154 -->
### Figure 3 | Separate qualification, feasibility and workload transfer

### 图 3 | 区分资格检验、可行性与工作负载适用性

<!-- M155 -->
**a,** Independently confirmed offers at 10% eligibility, 65% offered utilisation, reference deadlines, 10% GPU allocation and four calls at 16-h start spacing. Points and lower whiskers are success fractions and one-sided 95% Wilson lower bounds (300 scenarios); capacity labels apply to both service standards. Zero missed work defines a successful series under the zero-miss criterion; qualification targets a 95% success probability. **b,** Zero-miss diagnoses at 5.90 kW for three prespecified seeds per configuration. Categories separate instantaneous shortage, other strict-window infeasibility, PI feasibility with causal failure and feasibility with causal success; these are mechanism cases, not population frequencies. **c,** Matched submission-count and task-resource-time tests at 2.95 kW in chronological and permuted hourly order, scored at both service standards. GPU-h labels denote task-resource-time weights. **d,** Chronological zero-miss success by observed week for both weights. Panels c,d include eight observed weeks and ten synthetic realisations per week; pooled counts are descriptive and have no binomial confidence bars. Each comparison preserves weekly class totals and uses matched service rules, community and event clocks. Permutation changes hourly order and alignment together. All no-response baselines pass zero-miss service; all 49 chronological resource-time failures encounter instantaneous shortage.

**a，** 在 10% 工作允许参与、65% 工作供给利用率、参考期限、10% GPU 分配及四次调用开始间隔 16 h 条件下，独立确认的报价。点和下须为成功比例与单侧 95% Wilson 下界（300 个情景）；容量标签适用于两种服务标准。零漏期判据规定一次成功序列不得有漏期工作；资格检验的整体成功概率目标为 95%。**b，** 每个配置三个预先指定种子在 5.90 kW 下的零漏期诊断。类别区分即时不足、其他严格时间窗不可行、PI 可行但因果控制失败，以及 PI 可行且因果控制成功；这些是机制案例，不是总体频率。**c，** 固定 2.95 kW 的配对次数和任务资源时间测试，分别采用原序与置乱小时顺序，并按两种服务标准评分。GPU-h 标签表示任务资源时间权重。**d，** 两种权重在原序下逐观察周的零漏期成功数。c,d 包括八个观察周、每周十次合成实现；合并计数为描述性结果，不绘制二项置信条。各比较保留类别周工作总量并匹配服务规则、社区及事件时刻。置乱同时改变小时顺序和对齐。全部无响应基线通过零漏期服务；原序资源时间的全部 49 次失败均遇到即时不足。

<!-- M156 -->
### Figure 4 | Supply margins and the decisions behind a commitment

### 图 4 | 供给余量与承诺背后的决策

<!-- M157 -->
**a,** Paired minimum event-hour supply margins for all 80 task-resource-time realisations at 2.95 kW, comparing chronological and permuted orders. Margin is baseline PCC power minus community and fixed data-centre power minus 95% of the request, minimised over all four calls. Dashed zero lines separate scenarios with and without an instantaneous shortage; counts are descriptive, with no population-frequency inference. **b,** Available baseline reduction under chronological count and resource-time weighting for the lowest protocol seed (990000). The horizontal line is the 95% delivery requirement and shading marks the four calls. The displayed arrival horizon is 168 h; all 216 h remain in the data. Selection is by seed, not outcome. **c,** Evidence-to-decision sequence. A deficit identifies an impossible series, not automatic rejection of a probabilistic contract. Strict-window PI diagnoses distinguish infeasibility from a causal-control gap; an unresolved solve supplies no feasibility conclusion. Only a fixed causal offer that passes independent qualification enters the operating-price comparison. No supply screen or PI witness alone certifies causal reliability.

**a，** 固定 2.95 kW，全部 80 个任务资源时间实现的配对事件小时最小供给余量，比较原序与置乱。余量定义为基线 PCC 功率减去社区功率、固定数据中心功率及请求的 95%，再对全部四次调用取最小值。零虚线区分是否出现即时不足；计数为描述性结果，不推断总体频率。**b，** 最低协议种子 990000 在原序次数和资源时间权重下的基线可削功率。横线为 95% 交付要求，阴影表示四次调用。图示为 168 h 到达时域，全部 216 h 仍在数据中。按种子编号而非结果选取。**c，** 从证据到决策的顺序。缺口识别不可能成功的序列，并不自动拒绝概率性合同。严格时间窗 PI 诊断区分不可行与因果控制差距；未解决的求解不提供可行性结论。只有固定因果报价通过独立资格检验后，才进入运行价格比较。供给检查或 PI 见证本身均不能认证因果可靠性。

<!-- M158 -->
### Figure 5 | Separate controls for GPU allocation and rigid-load power

### 图 5 | GPU 分配与刚性功率的独立对照

<!-- M159 -->
**a,b,** Four- and eight-hour relaxed-PI tolerance statistics across flexible GPU allocations or unmeasured rigid-class active-power proxies, retaining 10% eligibility, the same 576-GPU installation and paired jobs. Each statistic uses 100 confirmation scenarios and aggregate release/deadline constraints; it does not guarantee work-group-feasible capacity. Lines join evaluated settings. **c,d,** Conditional four-hour single-event participation costs at the unchanged primary offer, using all 300 confirmation ledgers, 50 independent calls per annual draw and proportional 1-MW accounting. Crosses would indicate an unqualified offer. Costs are 95th-percentile annual-net-cost thresholds, not confidence limits. Fixed-request success and PV allocation controls appear in Supplementary Fig. 4c,d. Rigid power proxies are not measurements of online inference.

**a,b，** 四小时和八小时放松 PI 容忍统计量随灵活 GPU 分配或未测刚性类别活动功率代理的变化，保留 10% 工作允许参与、相同 576 块 GPU 与配对作业。每项统计量采用 100 个确认情景和累计释放／期限约束，不保证工作组可行容量。线连接已测试设定。**c,d，** 不变主要报价下的四小时单次事件条件参与成本，使用全部 300 条确认账本、每次年度抽样 50 个独立调用，并按比例折算至 1 MW。叉号表示未合格报价。成本是年度净成本第 95 百分位门槛，不是置信界。固定请求成功与光伏分配对照见补充图 4c,d。刚性功率代理不是在线推理测量值。

<!-- M160 -->
### Figure 6 | Price the operating exposure of qualified commitments

### 图 6 | 为合格承诺的运行暴露定价

<!-- M161 -->
**a,** Additional waiting exposure per complete four-call series for the refined four- and eight-hour products (300 confirmation scenarios each); points are means and whiskers are scenario 5th–95th percentiles, not confidence intervals. **b,** Net operating cost components at the total annual 95th-percentile rank, with no site fee and US$0.005/GPU-h/h waiting. **c,** Participation thresholds as waiting price varies. **d,** Minimum eight-hour capacity price that matches both the four-hour product and opting out, at three waiting prices. All panels use products qualified at a 95% success-probability target with zero missed work required for success: 5.60 and 4.42 model kW, reference deadlines and 16-h start spacing. Failed series remain in the ledgers. Monetary panels use proportional 1-MW accounting, twelve independent four-call series per year, US$0.10/kWh electricity, US$50/MWh capped delivered-energy revenue, zero missed-work price and 2,000 annual draws including failures. Price curves are conditional on the reference workload; they are not transferable offers for the failed resource-time tests.

**a，** 加密后的四小时与八小时产品每组完整四次调用的额外等待暴露（各 300 个确认情景）；点为均值，须为情景第 5–95 百分位，并非置信区间。**b，** 无场站费、等待价格每 GPU-h 每小时 0.005 美元时，总年度第 95 百分位排序位置对应的净运行成本组成。**c，** 随等待价格变化的参与门槛。**d，** 三种等待价格下，同时达到四小时产品与不参与价值的最低八小时容量价格。全部面板采用以 95% 成功概率为目标、且成功序列要求零漏期的合格产品，模型报价分别为 5.60 和 4.42 kW，使用参考期限及 16 h 开始间隔。失败序列仍保留在账本内。金额面板按比例折算至 1 MW，每年十二组独立四次调用，电价每 kWh 0.10 美元，截顶交付电量收入每 MWh 50 美元，漏期工作价格为零；2,000 次年度抽样包括失败。价格曲线以参考工作负载为条件，不能作为资源时间测试失败后的可转用报价。
