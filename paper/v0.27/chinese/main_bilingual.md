本稿对应英文 v0.27 与作者重绘整合图件 R8（2026-09-17）；正文科学结论不变，六张主图及图注样式说明同步。

<!-- M001 -->
# Reliable demand-response commitments from AI data centres under service constraints

# 服务约束下人工智能数据中心的可靠需求响应承诺

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
The expansion of artificial intelligence intensifies a central challenge of the energy transition: meeting rising electricity demand with reliable, low-carbon supply. Data-centre demand response could ease these pressures, but planners need reliable commitments that preserve computing service through repeated calls. Here we combine production records, power measurements and scheduling simulations in a model of 576 graphics processing units. At 10% deferrable work, retaining task sizes and durations instead of counting jobs reduces the independently confirmed eight-hour offer from 2.95 to 1.47 kW within the tested eight-week distribution. Checks of available load and task deadlines distinguish infeasible requests from failures that improved control could address. For separately qualified reference products, four- and eight-hour participation thresholds are US$183 and US$330 per committed kilowatt-year under illustrative waiting costs and zero fixed fees. These results connect capacity qualification to service selection, helping operators avoid infeasible commitments and compare compensation for reliable grid support.

人工智能的发展加剧了能源转型的一项核心挑战：如何在满足持续增长的用电需求的同时，实现低碳、可靠供电。数据中心需求响应有望缓解这一压力，但电网规划需要能够在多次调用中保障计算服务的可靠响应承诺。本研究将生产记录、功率测量和调度模拟结合于一个包含 576 块 GPU 的模型中。在允许 10% 计算工作延期的条件下，用任务规模和持续时间表征工作量，而非仅统计作业数量，使已测试八周分布内经独立确认的八小时报价由 2.95 kW 降至 1.47 kW。对可用负荷和任务期限的检查，能够区分不可交付的请求与仍可能通过改进控制解决的失败。对于另行通过交付资格检验的参考产品，在示意性等待成本、零固定费用的条件下，四小时和八小时服务的参与门槛分别为 183 和 330 美元/报价 kW·年。这些结果将容量资格检验与服务选择相联系，帮助运营者避免不可交付的承诺，并比较提供可靠电网支持所需的补偿。

<!-- M007 -->
## Introduction

## 引言

<!-- M008 -->
The global energy transition requires electricity systems to cut emissions while meeting rising demand from electrification and artificial intelligence (AI).<sup>1</sup> Data centres intensify this challenge where computing demand is concentrated and grows faster than power infrastructure can be built.<sup>1,2</sup> In these regions, limited electricity supply can constrain AI expansion, while grid planners must keep power reliable and affordable.<sup>2,3</sup> Shifting some computation to other times offers a way to make better use of existing infrastructure.<sup>3</sup> To support grid planning, data centres must repeatedly reduce power when requested, complete delayed tasks on time and keep costs acceptable. The reductions they can reliably promise therefore help determine their contribution to the energy transition.

全球能源转型要求电力系统在降低排放的同时，满足电气化与人工智能（AI）发展带来的新增需求。<sup>1</sup> 在计算需求集中、需求增长快于电力设施建设的地区，这一挑战尤为突出。<sup>1,2</sup> 电力供应不足可能限制这些地区的 AI 扩张，而电网规划者还必须保障供电可靠、价格可负担。<sup>2,3</sup> 将部分计算任务安排到其他时段，有助于更充分地利用现有电力设施。<sup>3</sup> 要为电网规划提供依据，数据中心必须能够按要求多次降低用电功率，同时按期完成推迟的任务，并将成本控制在可接受的范围内。因此，它们能可靠承诺多大的功率削减，是判断其能够为能源转型作出何种贡献的重要依据。

<!-- M009 -->
A field demonstration on 256 graphics processing units (GPUs) reduced power by 25% for three hours while meeting the tested service requirements.<sup>3</sup> Previous studies have shifted tasks between times or locations and controlled server power to reduce peaks and support demand response.<sup>4–8</sup> Related work schedules computing with cleaner electricity,<sup>9–12</sup> examines task pausing and GPU power limits,<sup>13,14</sup> and considers advance notice and grid connection.<sup>15–18</sup> A recent preprint relates reliable power reductions to the participating workload, response duration, reliability and the need to complete postponed work.<sup>19</sup> These advances raise a practical question: can simplifying task sizes and timing lead an operator to promise power reductions it cannot deliver?

一项在 256 块图形处理器（GPU）上开展的现场演示，在满足所测试服务要求的同时，将用电功率降低了 25%，持续三小时。<sup>3</sup> 已有研究通过改变任务的运行时间或地点，以及控制服务器功率，降低用电峰值并参与需求响应。<sup>4–8</sup> 相关工作还研究了如何让计算使用更清洁的电力，<sup>9–12</sup> 如何暂停任务和限制 GPU 功率，<sup>13,14</sup> 以及提前通知和电网接入的影响。<sup>15–18</sup> 一篇近期预印本进一步研究了可参与的工作量、响应时长、可靠性要求，以及补做推迟任务的需要，如何影响可靠的功率削减。<sup>19</sup> 这些进展引出一个实际问题：如果过度简化任务的规模和时间安排，运营者是否会向电网承诺实际上无法交付的功率削减？

<!-- M010 -->
Some computing must answer users immediately; some model training and predictions prepared for later use can wait within agreed deadlines. Production records distinguish these task types and their priorities,<sup>20</sup> but operators must decide which work may actually be delayed. At a fixed amount of deferrable work, hourly demand still depends on how many GPUs each task needs and how long it runs. Delaying tasks during a response also leaves work that must be completed before its deadline.<sup>6,13,21,22</sup> A centre can therefore have enough work over a week yet too little reducible load during a call or too little time afterwards.

有些计算必须立即回答用户；部分模型训练和不需要立即给出结果的预测任务，则可以在约定期限内推迟执行。生产记录能够区分这些任务类型及其优先级，<sup>20</sup> 但哪些任务实际允许推迟，仍须由运营者决定。即使允许推迟的总工作量相同，每小时的用电需求仍取决于每项任务需要多少块 GPU、运行多长时间。响应期间推迟的任务并没有消失，仍须在期限前完成。<sup>6,13,21,22</sup> 因此，一个数据中心即使整周有足够的计算工作，也可能在电网调用时没有足够可削减的负荷，或者在调用后没有足够时间补做任务。

<!-- M011 -->
Whether a centre can deliver a response and whether participation pays are separate questions. On a shared local electricity network, computing demand interacts with solar generation and battery storage.<sup>23–27</sup> Equipment that allows more solar generation to connect may not increase the power reduction available during grid calls. Delaying work also creates waiting costs, while missed deadlines and programme access can add expenses. We therefore first establish which commitments can be delivered and then compare the costs of the services that pass.

数据中心能否完成响应，以及参与是否划算，需要分别判断。在共用的本地电网上，计算用电还会与光伏发电和电池储能相互影响。<sup>23–27</sup> 某种设备配置可能允许接入更多光伏，却不一定增加电网调用时可削减的功率。推迟任务也会产生等待成本，未能按期完成任务和接入响应计划还可能增加费用。因此，我们先判断哪些承诺能够交付，再比较通过交付检验的服务各自需要付出多少成本。

<!-- M012 -->
Here we identify how omitting task-size information can cause an operator to overstate deliverable response. AIDRBench combines computing tasks modelled from production records, power measurements from four GPUs and a simulated local electricity network. We compare two descriptions of the same weekly work: job counts alone, or counts adjusted for requested GPUs and task duration.<sup>28</sup> We select capacities using one set of simulations and test them on a separate set. We then diagnose failures and compare participation costs for separately tested reference services. Building on previous capacity assessments,<sup>19</sup> we show when operators should reduce a request, reconsider scheduling or compare compensation among deliverable services.

本研究识别了忽略任务规模信息如何导致运营者高估能够交付的响应。AIDRBench 将依据生产记录构建的计算任务模型、四块 GPU 的功率测量以及本地电网模拟结合起来。我们用两种方式描述同一周的计算工作：一种只统计作业数量，另一种还考虑任务申请的 GPU 数量和运行时间。<sup>28</sup> 我们用一组模拟选择响应容量，再用另一组模拟检验。随后，我们分析失败原因，并对另行通过检验的参考服务比较参与成本。在已有容量评估研究的基础上，<sup>19</sup> 本研究进一步说明运营者何时应当降低响应请求、重新考虑调度方式，以及在能够交付的服务之间比较补偿条件。

<!-- M013 -->
## Results

## 结果

<!-- M014 -->
### Workload composition limits which computing can support a commitment

### 工作构成限制了哪些计算可以支持响应承诺

<!-- M015 -->
We first examined what fraction of computing could plausibly enter the deferrable pool. Across 40.52 million execution spans in the released Alibaba summary,<sup>20</sup> online inference accounted for 54.5% of requested GPU-hours, offline inference for 21.5% and training for 19.4% (Fig. 1b). Low-priority training and offline inference together accounted for 22.0%. These descriptive resource-time shares identify a candidate pool from which an operator might authorise a smaller amount of work to wait.

我们首先考察可能进入可延期工作池的计算比例。Alibaba 发布汇总中的 4,052 万个执行片段显示，<sup>20</sup> 在线推理占请求 GPU-h 的 54.5%，离线推理占 21.5%，训练占 19.4%（图 1b）。低优先级训练与离线推理合计占 22.0%。这些描述性的资源时间份额确定了候选池，运营者可从中授权较小部分工作等待。

<!-- M016 -->
The primary scenarios allowed 5%, 10% or 20% of total offered work to wait, preserving the observed class mix and varying permission within low-priority batch work. The 40% comparison required almost all training and offline inference to opt in. The 60% case additionally reassigned 19.1 percentage points of total work from online to offline inference (Supplementary Table 2). Online jobs remained ineligible; these larger fractions therefore describe additional business assumptions.

主要情景允许总供给工作量的 5%、10% 或 20% 等待，在保留观测类别构成的同时，改变低优先级批处理工作的许可比例。40% 对照要求几乎全部训练和离线推理参与。60% 情景还将总工作量的 19.1 个百分点从在线推理重新分配到离线推理（补充表 2）。在线作业始终不允许参与，因此更高比例代表额外的业务假设。

<!-- M017 -->
Each configuration retained 576 GPUs and 374.4 GPU-h of offered work per hour. Assigning approximately the same fraction of GPUs as eligible work kept mean utilisation near 65% in both pools. The primary comparison therefore changes permission together with supporting allocation; controls at 10% eligibility isolate allocation (Fig. 5). Four-GPU board-power calibration constrained the batch-work conversion, whereas rigid workloads used an engineering power proxy (Supplementary Fig. 2; Supplementary Tables 1–3).

各配置均保留 576 块 GPU，每小时供给 374.4 GPU-h 工作。向灵活池分配与可参与工作比例大致相同的 GPU，使两个池的平均利用率均接近 65%。因此，主要比较同时改变参与许可及其配套分配；10% 参与比例下的对照则单独考察分配（图 5）。四块 GPU 的板卡功率校准约束批处理工作的功率转换，刚性工作负载采用工程功率代理（补充图 2；补充表 1–3）。

![图 1](../figures/main/01_FIGURES/AIDRBench_Figure_1.png)

<!-- M021 -->
### Smaller eligible pools support smaller independently tested offers

### 较小的合格工作池支持较小的独立检验承诺

<!-- M022 -->
Development-selected single-event offers of 2.95, 5.90 and 11.80 kW qualified on 300 independent scenarios at 5%, 10% and 20% eligibility, respectively, corresponding to 1.6–5.9% of operating peak demand (Fig. 2a; Supplementary Table 4). The 40% and 60% comparisons qualified at 22.19 and 34.00 kW under their additional assumptions. The proportional low-share response follows the shared job-template scaling and allocation policy. Relaxed perfect-information (PI) tolerance statistics provide a planning comparison but do not guarantee individual work-group feasibility (Methods).

当参与比例分别为 5%、10% 和 20% 时，开发阶段选出的单次报价 2.95、5.90 和 11.80 kW 在 300 个独立情景上通过资格检验，对应运行峰值需求的 1.6%–5.9%（图 2a；补充表 4）。在额外业务假设下，40% 和 60% 对照的合格报价为 22.19 和 34.00 kW。低比例情景的比例关系来自共享作业模板的缩放和分配规则。放松的完美信息（PI）容忍统计量提供规划比较，但不保证各工作组可行（见方法）。

<!-- M023 -->
The same selected power qualified at four and eight hours on the tested grid, with success decreasing from 295/300 to 292/300 in every configuration; one-sided 95% probability lower bounds were 0.9662 and 0.9533. Zero-, two- and six-hour notice gave identical paired success flags (Fig. 2c). This result belongs to the specified eager baseline, release constraints and controller; the baseline-dependent supply bound explains why notice cannot repair hours with insufficient reducible load.

在已测试网格上，四小时与八小时获得相同的合格功率，但每种配置的成功数均由 295/300 降至 292/300；单侧 95% 概率下界分别为 0.9662 和 0.9533。零、两和六小时提前通知的配对成功标记逐一相同（图 2c）。这一结果针对指定的即时处理基线、释放约束和控制器；依赖基线的供给上界解释了为什么提前通知无法修复可削减负荷不足的小时。

![图 2](../figures/main/01_FIGURES/AIDRBench_Figure_2.png)

<!-- M025 -->
### Workload timing determines whether a repeated commitment transfers

### 工作量的时间分布决定重复承诺能否适用

<!-- M027 -->
At 10% work eligibility, we tested four calls using a controller that enforces every overlapping recovery obligation. In the reference configuration—65% offered utilisation, reference deadlines and a 10% GPU pool—the four- and eight-hour offers were 5.60 and 4.42 kW, both with 16-h start spacing. When successful series required zero missed work, independent confirmation gave 297/300 and 296/300 successes, with one-sided 95% probability lower bounds of 0.9752 and 0.9706 (Supplementary Fig. 9a). Both the 1% and zero-miss standards selected these capacities on the local grid (Supplementary Table 18). Their agreement provides no basis for applying a uniform capacity discount solely because the success criterion becomes stricter.

在 10% 工作允许参与时，我们使用落实每项重叠恢复义务的控制器测试四次调用。在参考配置下，即工作供给利用率 65%、参考期限和 10% GPU 池，四小时与八小时报价分别为 5.60 和 4.42 kW，调用开始间隔均为 16 h。当一次序列必须零漏期才能判为成功时，独立确认成功数分别为 297/300 和 296/300，单侧 95% 概率下界为 0.9752 和 0.9706（补充图 9a）。1% 与零漏期标准在局部网格上均选择这些容量（补充表 18）。两者一致的结果不支持仅因成功标准变严格，就施加统一的容量折减。

<!-- M023_timing -->
Even half the reference single-event offer could fail after a change in workload representation. At 10% eligibility, a 2.95-kW request—50% of the 5.898243-kW single-event offer—passed all ten simulations in each of eight observed weeks under submission-count weighting. Under task-resource-time weighting, only two weeks passed all ten; two failed all ten and four had mixed outcomes (Fig. 3d,e). The descriptive total fell from 80/80 to 31/80. Weekly class totals, synthetic service rules, community profiles and event clocks were paired, and every no-response baseline met zero-miss service. This 2.95-kW stress request concerns the 10% configuration; the numerically equal single-event offer at 5% eligibility is a separate product.

改变工作负载表征后，连参考单次报价的一半都可能失败。在 10% 参与比例下，2.95 kW 请求即 5.898243 kW 单次报价的 50%；按提交次数加权时，八个观测周中每周十次模拟全部通过。按任务资源时间加权时，只有两周十次全部通过，另有两周十次全部失败，其余四周部分通过（图 3d,e）。描述性总计由 80/80 降至 31/80。周内各类工作总量、合成服务规则、社区曲线和调用时刻均配对，每个无响应基线都满足零漏期服务。这里的 2.95 kW 压力请求属于 10% 配置；5% 参与下数值相同的单次报价是另一种产品。

<!-- M025_order -->
Permuting whole hourly blocks separated workload weighting from the effect of hourly order and alignment. Count-weighted success remained 80/80, whereas resource-time success rose to 55/80 at the 1% standard and 54/80 at zero misses (Fig. 3d). Hourly rearrangement improved this comparison but did not restore count-weighted performance. It changes alignment with both calls and community demand, so the improvement cannot be assigned to autocorrelation alone. At the larger 4.42-kW request, all 80 chronological resource-time realisations failed; full cross-scores are retained in Supplementary Table 20.

置乱完整小时块进一步区分了工作量权重与小时顺序及对齐的影响。次数加权仍成功 80/80，而资源时间加权在 1% 标准下提高至 55/80，在零漏期标准下提高至 54/80（图 3d）。小时重排改善了这一对照的结果，却未恢复到次数加权的表现。重排同时改变与调用和社区需求的对齐，因此不能将改善全部归因于自相关。在更大的 4.42 kW 请求下，80 个原序资源时间实现全部失败；完整交叉评分保留在补充表 20。

<!-- M27_capacity -->
Reducing the request restored qualification under the resource-time description. We selected offers on 100 new simulations and froze them before testing 300 further simulations, each independently drawing one of the eight fixed weekly profiles with equal probability. The count-weighted description selected 2.9491 kW and the resource-time description 1.4746 kW; each achieved 300/300 successes under both service standards, with a one-sided 95% lower bound of 0.9911 (Fig. 3a; Supplementary Fig. 9; Supplementary Table 22). At the unchanged 2.9491-kW comparator, resource-time success was 120/300, with all 180 failures encountering supply shortage. Thus the simplified description supported a tested offer twice as large. This ratio compares finite-grid offers conditional on the eight-week empirical distribution; it does not estimate a universal or continuous optimal-capacity ratio.

降低请求后，资源时间表征重新获得资格。我们使用 100 次新模拟选定报价，冻结后再检验另外 300 次模拟；每次独立、等概率抽取八个固定周曲线之一。次数表征选中 2.9491 kW，资源时间表征选中 1.4746 kW；两者在两种服务标准下均为 300/300 成功，单侧 95% 下界为 0.9911（图 3a；补充图 9；补充表 22）。保持 2.9491 kW 比较请求时，资源时间表征只有 120/300 成功，180 次失败均遇到供给不足。因此，简化描述支持的已测试报价是另一种描述的两倍。这个比例比较的是八周经验分布条件下的有限网格报价，不能解释为通用比例或连续最优容量之比。

![图 3](../figures/main/01_FIGURES/AIDRBench_Figure_3.png)

<!-- M029 -->
### Supply and feasibility checks identify what a failed request requires

### 供给与可行性检查识别失败请求需要怎样调整

<!-- M030 -->
The matched baseline makes a simple necessary supply condition available. In each event hour, baseline power above community and idle-plus-rigid demand must reach 95% of the request. A deficit makes that hour undeliverable even with all flexible execution stopped. This condition accounts for all 49 chronological resource-time failures at 2.95 kW and 25 failures after permutation (Fig. 4a,b). Full queue replay establishes that supply, rather than an additional recovery or scheduling violation, accounts for every failure in the original-order comparison. The screen is not sufficient in general: one of the 55 permuted cases without shortage still failed the zero-miss endpoint. Strict-window and causal tests address these remaining constraints.

匹配基线给出了一个简单的供给必要条件：每个事件小时，基线中高于社区负荷及空闲加刚性需求的功率，必须达到请求的 95%。出现缺口时，即使停止全部灵活执行，该小时也无法交付。该条件解释了原序资源时间表征在 2.95 kW 下的全部 49 次失败，以及置乱后的 25 次失败（图 4a,b）。完整队列重放表明，在原序比较中，供给不足已解释全部失败，无需额外归因为恢复或调度违约。但这一筛查一般并不充分：置乱后 55 个没有供给缺口的情景中，仍有一个未通过零漏期标准。严格时间窗与因果检验用于检查这些剩余约束。

<!-- M031 -->
Strict task-window feasibility then distinguished failures beyond that supply condition. At a fixed 5.90-kW request, a reference scenario that passed the supply screen failed under causal control but admitted a full-information schedule meeting all electrical obligations with zero missed work (Fig. 3c; Supplementary Table 19). Halving its deadline slack made the request infeasible under the same delivery and recovery criteria; doubling GPU allocation did not restore feasibility. Each variant used its own matched baseline. The feasible reference case leaves room for controller improvement, whereas proven infeasibility calls for changing the request or operating terms. Neither finding follows from the causal failure alone. The broader structural confirmation separates joint success from overlapping supply and deadline failures (Supplementary Fig. 6).

随后，严格任务时间窗可行性区分了即时供给条件之外的失败。在固定 5.90 kW 请求下，一个通过供给检查的参考情景在因果控制下失败，却存在满足全部电气义务且零漏期的完整信息调度（图 3c；补充表 19）。将其期限余量减半后，在相同交付和恢复判据下，请求变为不可行；将 GPU 分配加倍也没有恢复可行性。各变体采用各自匹配的基线。参考情景的可行解说明仍有改进控制器的空间，而已证明的不可行则要求改变请求或运行条款。这两种判断都不能仅从因果控制失败得出。 更广泛的结构确认将联合成功与可重叠的供给、期限失败分开报告（补充图 6）。

<!-- M025_decision -->
These checks define different decisions (Fig. 1c): revise requests that exceed supply or strict-window feasibility, investigate control where a feasible PI schedule exists, and qualify the causal policy independently before comparing prices. Qualification uses the complete success and failure sample. In the matched same-clock control, removing preceding calls left final-call electrical outcomes unchanged (Supplementary Table 15).

这些检查对应不同决策（图 1c）：请求超过供给或严格时间窗可行性时应调整请求；存在 PI 可行调度时应研究控制；比较价格前应独立检验因果策略资格。资格评估采用完整成功和失败样本。在匹配相同时刻的对照中，去掉前序调用后，末次调用的电气结果保持不变（补充表 15）。

<!-- M26_operation -->
At the qualified reference offers, the full response–recovery trajectory illustrates why an event cannot be assessed in isolation: deferred work accumulates during the calls and is processed afterwards (Fig. 4c,d). This seed-selected example complements, rather than replaces, the independent qualification counts.

在合格参考报价下，完整的响应—恢复轨迹说明为什么不能孤立评价事件：调用期间累积的延期工作，需要在之后处理（图 4c,d）。这一按种子编号选定的示例补充了独立资格计数，不能代替后者。

![图 4](../figures/main/01_FIGURES/AIDRBench_Figure_4.png)

<!-- M034 -->
### Allocation changes system value without necessarily increasing the offer

### 分配可以改变系统价值，而不一定提高报价

<!-- M035 -->
At fixed 10% work eligibility, increasing flexible GPU allocation from 10% to 20% or 30% left the tested 5.90-kW single-event offer at 295/300 four-hour and 292/300 eight-hour successes. The corresponding relaxed-PI tolerance statistics were also unchanged (Fig. 5a; Supplementary Fig. 4c). Reducing the rigid-class active-power proxy from 300 to 225 or 150 W per GPU preserved these baseline-relative responses but changed operating peak demand from 193.44 to 173.53 or 153.63 kW (Fig. 5b). Thus, eligible arrivals constrained this response, while rigid power remained relevant to facility demand and proportional cost accounting (Fig. 5c,d).

在固定 10% 工作允许参与时，将灵活 GPU 分配由 10% 提高至 20% 或 30%，所测试的 5.90 kW 单次报价仍保持四小时 295/300、八小时 292/300 成功。相应的放松 PI 容忍统计量也未改变（图 5a；补充图 4c）。将刚性类别活动功率代理从每 GPU 300 W 降至 225 或 150 W，未改变这些相对基线的响应，却使运行峰值需求从 193.44 kW 变为 173.53 或 153.63 kW（图 5b）。因此，可参与工作的到达约束了这一响应，而刚性功率仍影响设施需求与比例成本核算（图 5c,d）。

<!-- M036 -->
The same allocation could matter more for integrating photovoltaic (PV) generation, assessed with and without a battery energy storage system (BESS). At 10% eligibility, raising flexible GPU allocation from 10% to 20% increased the no-BESS PV hosting gain from 5.40 to 24.99 kW (Fig. 5e; Supplementary Fig. 4d). Strict repeat solves retained these gains. Utilisation of a fixed 500-kW PV system improved by only 0.0057 percentage points without BESS (95% paired interval, 0.0019–0.0106). This small LP result was unchanged by tighter feasibility tolerances, whereas the corresponding BESS gain was numerically zero (Supplementary Fig. 10c,d; Supplementary Table 24). Hosting and utilisation therefore measure different benefits; absolute hosting and energy outcomes appear in Supplementary Fig. 7.

同样的 GPU 配置对接入光伏发电（PV）可能更有价值；我们分别评估了配置和未配置电池储能系统（BESS）的情况。在 10% 参与比例下，将灵活 GPU 分配从 10% 提高至 20%，使无储能 PV 接纳增益由 5.40 增至 24.99 kW（图 5e；补充图 4d），严格重算保留了这些增益。固定 500 kW PV 系统的利用率在无储能时只提高 0.0057 个百分点，95% 配对区间为 0.0019–0.0106。收紧可行性容差后，这一微小的线性规划结果保持不变；相应储能情景的增益则在数值上为零（补充图 10c,d；补充表 24）。因此，接纳和利用率衡量不同收益；绝对接纳与电量结果见补充图 7。

![图 5](../figures/main/01_FIGURES/AIDRBench_Figure_5.png)

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
The price comparison applies to the qualified reference-distribution products. The lower resource-time offer requires its own operating ledger before those prices can be used for that workload. Waiting and missed-work valuations are varied explicitly, with single-event hardware and monetary sensitivity in Supplementary Fig. 8. Contract penalties, application checkpoint costs and hardware ageing remain unpriced, and annual accounting combines independent series.

价格比较针对参考分布中的合格产品。较低的资源时间报价，需要用自身运行账本核算后才能为该工作负载采用相应价格。等待与漏期估值均有明确敏感性分析，单次事件的硬件和货币假设见补充图 8。合同罚款、应用检查点成本及硬件老化仍未定价，年度核算采用独立序列组合。

![图 6](../figures/main/01_FIGURES/AIDRBench_Figure_6.png)

<!-- M045 -->
## Discussion

## 讨论

<!-- M046 -->
The main finding is a quantitative commitment error: removing task resource requirements from an otherwise matched workload description supported a tested offer twice as large. Both offers subsequently passed independent confirmation, so the resource-time result specifies a usable lower commitment within the model. Weekly totals alone concealed the low-supply hours that invalidated the larger request. Paired permutation improved resource-time delivery without restoring count-weighted performance, separating workload weights from their hourly arrangement and alignment. These results extend availability-based contract descriptions<sup>19</sup> by testing the request through explicit task queues and repeated recovery, then separating physical impossibility from a controller's failure to realise a feasible schedule.

核心发现是一个可量化的承诺错误：在其他条件匹配时，去掉任务资源需求信息，会支持一个大两倍的已测试报价。两个报价随后均通过独立确认，因此资源时间结果给出了模型内可使用的较低承诺。仅匹配周总量会掩盖使较大请求失败的低供给小时。配对置乱改善了资源时间交付，却没有恢复到次数加权表现，从而区分工作量权重与其小时排列、对齐。相对于基于可用性的合同描述，<sup>19</sup> 这些结果通过明确的任务队列与重复恢复检验请求，并区分物理上不可实现与控制器未能实现可行调度。

<!-- M047 -->
The diagnosis also determines what can usefully change. An instantaneous deficit rules out successful delivery in the affected hour. If that condition passes, strict task-window infeasibility and a feasible PI schedule with causal failure require different responses: revise operating terms in the first case, investigate control and information limits in the second. These scenario-level findings must then be assessed through the declared probabilistic qualification rule. More GPUs, a stricter service label or a low estimated price cannot substitute for that sequence of evidence.

诊断还决定哪些调整有意义。即时缺口排除了受影响小时成功交付的可能。若通过这一条件，严格任务时间窗不可行与 PI 可行但因果控制失败需要不同处理：前者需要修改运行条款，后者值得调查控制与信息限制。随后，这些情景层面的发现仍须通过声明的概率性资格规则进行评估。更多 GPU、更严格的服务标签或较低的估计价格，都不能替代这一证据顺序。

<!-- M27_baseline_discussion -->
These findings depend on what a contract counts as delivery. Our counterfactual baseline immediately processes available work and retains the same rigid demand and powered GPU idle floor as the response trajectory. It therefore fixes each hour's maximum baseline-relative reduction. Notice cannot lift this ceiling, although it may improve service or recovery scheduling when supply is sufficient. Historical customer-baseline load or a fixed import ceiling defines a different obligation and can change the value of pre-positioning work. PJM's capacity framework distinguishes guaranteed load drop from a firm service level.<sup>29</sup> Our fixed-duration repeated reduction is closest in intent to a guaranteed-reduction commitment; its matched counterfactual baseline and recovery rules are explicit modelling choices, rather than an implementation of PJM settlement or baseline estimation.

这些发现取决于合同如何定义交付。本文的反事实基线立即处理已到达工作，并与响应轨迹保留相同的刚性需求和已通电 GPU 空闲功率，因此固定了每小时相对基线的最大减负量。提前通知无法抬高这一上限，但在供给充足时，仍可能改善服务或恢复调度。历史客户负荷基线或固定进口功率上限对应不同义务，也会改变提前安排工作的价值。PJM 容量框架区分保证负荷下降与固定服务水平。<sup>29</sup> 本文的定时长重复减负，在意图上最接近保证减负承诺；但匹配反事实基线及恢复规则是明确的模型选择，并未实现 PJM 的结算或基线估计方法。

<!-- M049 -->
Economic assessment follows qualification and exposes quantities before assigning prices. Waiting and missed-work exposure remain inspectable independently of their valuations. The preferred duration can change when waiting is free, whereas a common access fee affects entry rather than the ranking of participating products. Comparing annual net values with non-participation avoids confusing a low unit-cost threshold with the most valuable contract. The capacity ratio and stated valuations determine the price boundary, whose use remains conditional on the workload for which delivery was qualified.

经济评估在资格检验之后开展，并先展示数量再赋予价格。等待与漏期工作暴露可以独立于估值检查。当等待免费时，偏好的时长可以改变；共同接入费则影响是否进入，而不改变参与产品间的排序。将年度净值与不参与比较，可以避免把较低单位成本门槛误当成最有价值的合同。容量比和指定估值决定价格边界，而这一边界仍只适用于已取得交付资格的工作负载。

<!-- M050 -->
For planners and operators, the useful output is a conditional commitment with a declared workload, baseline, service standard, capacity and call arrangement. Its delivery evidence and operating ledger must be re-evaluated when the timing structure changes. This is consistent with capacity assessment for other resources whose decisions are coupled over time.<sup>30,31</sup> A larger nominal flexible share, more recovery hardware or cheaper access cannot substitute for that assessment.

对规划者和运营者，有用的输出是明确工作负载、基线、服务标准、容量与调用安排的条件性承诺。当时间结构变化时，交付证据与运行账本需要重新评估。这与其他决策在时间上相互耦合的资源容量评估相一致。<sup>30,31</sup> 更高名义柔性比例、更多恢复硬件或更便宜的接入都不能代替这项评估。

<!-- M051 -->
The study represents a 576-GPU installation with 58 GPUs assigned to eligible work in the primary case. Its 193.44-kW operating peak includes 61.47 kW of node overhead and GPU idle demand, limiting the removable share before task timing is considered. This denominator and the 10% work permission distinguish the scenario from demonstrations with different participating workloads and hardware.<sup>3</sup> The trace supplies allocated task resource-time, while deadlines, permissions, divisible execution and recovery behaviour remain model assumptions. Hardware evidence calibrates board power rather than application pause–restart behaviour. Ignoring checkpoint overhead and indivisibility enlarges the scheduling possibilities at a fixed physical baseline; a causal controller's observed failure rate still cannot be treated as a lower bound on real-system failure. The eight-week empirical distribution, pointwise qualification and finite grids delimit the capacity comparison, and independent annual series delimit economic extrapolation.

本文表示一个 576 卡设施，主情景将其中 58 卡分配给可参与工作。193.44 kW 的运行峰值包含 61.47 kW 节点开销和 GPU 空闲需求，因此在考虑任务时序前，可移除功率比例已受到限制。这一分母和 10% 工作许可，使本情景区别于参与工作与硬件不同的现场演示。<sup>3</sup> 轨迹提供的是分配给任务的资源时间，期限、许可、可分割执行及恢复行为仍是模型假设。硬件证据校准板级功率，而非应用暂停—重启行为。在物理基线固定时，忽略检查点开销与不可分割性会扩大可调度范围；但因果控制器的观测失败率仍不能当作真实系统失败率的下界。八周经验分布、逐项资格检验与有限网格限定容量比较的范围，独立年度序列则限定经济外推。

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
The reliability target was 0.95. Each offer was conditional on the controller, workload distribution and call schedule. We selected the largest qualifying candidate on a finite development grid and tested it independently, using a pointwise probability lower bound.

可靠性目标为 0.95。每个报价均以控制器、工作负载分布和调用安排为条件。我们在有限开发网格上选取通过标准的最大候选值，再使用逐项概率下界开展独立检验。

<!-- M058 -->
This extension was specified after the earlier benchmark. One hundred development seeds (930000–930099) selected offers, and 300 previously unexamined confirmation seeds (960000–960299) tested them without reselection. The delivered-power recovery guard and feasible-side action rounding were corrected on development data before this controller version was confirmed. Protocol, source, controller and scenario hashes identify the evidence; original locked certificates remain separate historical results.

本扩展在此前基准之后制定。100 个开发种子（930000–930099）用于选承诺，300 个此前未查看的确认种子（960000–960299）在不重新选值的条件下检验。实际交付功率的恢复保护及可行侧动作舍入在开发数据上修正后，再对该控制器版本进行确认。协议、来源、控制器和情景哈希标识对应证据；原锁定证书作为独立历史结果保存。

<!-- M059 -->
### Community, jobs and event scenarios

### 社区、作业与事件情景

<!-- M060 -->
Community demand used the End-Use Load Profiles for the US Building Stock,<sup>32,33</sup> combining 75% detached-residence and 25% small-office demand in the mixed 3A profile. These are building-stock simulations calibrated against measurements. Fifteen-minute power was averaged to hourly intervals and scaled to an 800-kW background peak. All five configurations prohibited exports and limited imports to 1,100 kW at the point of common coupling (PCC), the community's connection to the upstream grid. This rating accommodates the unchanged 576-GPU installation across the changing workload mixes; three initial development baselines exceeded the earlier 1,000-kW rating, so the common site rating was amended before formal PI optimisation or controller selection. Those baseline records were retained.

社区需求采用美国建筑存量的终端用电曲线，<sup>32,33</sup> 在混合 3A 曲线中将 75% 独栋住宅需求与 25% 小型办公需求组合。这些曲线是经测量校准的建筑存量模拟。15 分钟功率平均为小时值，再缩放至 800 kW 背景峰值。五种配置均禁止向上级电网送电，并将社区与上级电网的连接点（公共耦合点，PCC）的输入功率上限设为 1,100 kW。该容量适应工作构成变化下保持不变的 576 张 GPU：初始开发基准中有三项超过此前的 1,000 kW 额定值，因此在正式 PI 优化和控制器选值前统一调整站点容量，并保留了这些基准记录。

<!-- M061 -->
Job shapes came from the Alibaba Serverless Infrastructure execution summary,<sup>20</sup> complementing an earlier public GPU trace.<sup>28</sup> The source mix used all 40,522,321 released spans, weighted by requested GPU-equivalents times uncapped duration and retaining every workload category. A reproducible, class-balanced 100,000-record subset supplied low-priority training and offline-inference job shapes only. This summary lacked production deadlines and the original temporal correlations.

作业形状来自 Alibaba Serverless Infrastructure 执行汇总，<sup>20</sup> 并以较早的公开 GPU 轨迹补充。<sup>28</sup> 源工作组合使用全部 40,522,321 个执行片段，以请求 GPU 当量乘未截断时长加权，保留所有工作类别。可复现、类别平衡的 100,000 条记录子集仅用于低优先级训练和离线推理的作业形状。该汇总缺少生产期限及原始时间相关性。

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
\begin{aligned}
P^{\mathrm{DC}}_t=\frac{\mathrm{PUE}}{1000}\Big[&N_{\mathrm{node}}p_{\mathrm{node}}+N_{\mathrm{GPU}}p_{\mathrm{idle}}\\
&+N_{\mathrm{rigid}}u_{\mathrm{rigid}}(\bar p_{\mathrm{rigid}}-p_{\mathrm{idle}})
+\sum_c(p_c-p_{\mathrm{idle}})\frac{X_{c,t}}{\Delta t}\Big].
\end{aligned}
$$

<!-- M27_power_terms -->
where power p is in watts, X is executed flexible GPU-hours and Δt = 1 h. Node overhead applies to all 144 nodes and idle power to all 576 GPUs. The rigid pool contains 518 GPUs at utilisation 0.65050193; its class-weighted active power is 291.42199 W/GPU. The reference flexible mix has 297.90848 W/GPU active power. At PUE 1.2 and idle power 13.935625 W/GPU, the operating peak is 51.840000 + 9.632304 + 112.202165 + 19.764511 = 193.438980 kW: node overhead, all-GPU idle draw, rigid increment and full flexible-pool reference increment, respectively. Thus the compact form $P^{\mathrm{DC}}_t=P_{\mathrm{fixed}}+\sum_c e_cX_{c,t}$ uses $P_{\mathrm{fixed}}=173.674469$ kW and $e_c=\mathrm{PUE}(p_c-p_{\mathrm{idle}})/(1000\Delta t)$.

式中功率 p 的单位为 W，X 为已执行的灵活 GPU-h，Δt = 1 h。节点开销计入全部 144 个节点，空闲功率计入全部 576 块 GPU。刚性池包含 518 卡，利用率为 0.65050193，按工作类别加权的活动功率为 291.42199 W/GPU。参考灵活工作组合的活动功率为 297.90848 W/GPU。PUE 为 1.2、空闲功率为 13.935625 W/GPU 时，运行峰值为 51.840000 + 9.632304 + 112.202165 + 19.764511 = 193.438980 kW，依次对应节点开销、全部 GPU 空闲功率、刚性增量和满灵活池参考增量。因此，简写 $P^{\mathrm{DC}}_t=P_{\mathrm{fixed}}+\sum_c e_cX_{c,t}$ 中的 $P_{\mathrm{fixed}}$ 为 173.674469 kW，$e_c=\mathrm{PUE}(p_c-p_{\mathrm{idle}})/(1000\Delta t)$。

<!-- M069 -->
Calibration used four NVIDIA RTX PRO 6000 Blackwell Max-Q GPUs connected by PCIe without NVLink. Active training and offline-inference board power averaged 259.08 and 300.02 W/GPU, and idle power averaged 13.94 W/GPU. Two independent runs per active class supplied the fit and a third was held out. Simultaneous GPU observations were averaged within each run; independent runs were the statistical units.

校准使用四块通过 PCIe 连接、没有 NVLink 的 NVIDIA RTX PRO 6000 Blackwell Max-Q GPU。训练和离线推理的活动板级功率分别平均为 259.08 和 300.02 W/GPU，空闲功率平均为 13.94 W/GPU。每个活动工作类使用两次独立运行拟合，第三次留出检验。同次运行中同时测得的 GPU 观测先取均值；统计单位为独立运行。

<!-- M070 -->
The model used PUE 1.2 and 300 W/node fixed overhead. Online, development, other and unknown rigid work used a 300.02-W active-GPU engineering proxy, with separate 150- and 225-W controls. Rigid demand remained at its class-weighted mean. Board measurements calibrated the batch-work conversion; request latency and burst-level rigid power require application-level evidence.

模型采用 PUE 1.2 和每节点 300 W 固定开销。在线推理、开发、其他和未知刚性工作采用 300.02 W/活动 GPU 的工程代理，并设置 150 和 225 W 独立对照。刚性需求保持在按类别加权的均值。板卡测量校准批工作功率换算；请求延迟及突发刚性功率需要应用层证据。

<!-- M27_overhead -->
Fixed-overhead sensitivity used 150, 300, 450 and 600 W/node (Supplementary Fig. 10; Supplementary Table 23). These change the operating peak to 167.52, 193.44, 219.36 and 245.28 kW. We added PUE × 144 × (p_node − 300)/1000 to both power trajectories of all 600 independently confirmed reference schedules and rescored event and PCC constraints. This exact affine check tests feasibility of unchanged schedules, without selecting new offers or rerunning the controller. Baseline-relative reductions, backlog and waiting are invariant; absolute PCC headroom and the per-MW accounting conversion change.

固定开销敏感性采用 150、300、450 和 600 W/node（补充图 10；补充表 23），运行峰值相应变为 167.52、193.44、219.36 和 245.28 kW。我们对全部 600 条独立确认参考调度的响应与基线功率同时加上 PUE × 144 × (p_node − 300)/1000，重新评分事件及接入点约束。这一精确仿射检查验证原调度的可行性，没有重新选择报价或运行控制器。相对基线的减负、积压和等待保持不变；绝对接入余量及每 MW 会计换算会改变。

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
The aggregate PI programme maximised R under cumulative class-release and class-deadline constraints. These are necessary aggregate conditions, but are a relaxation when job windows cross: work executed for an earlier, later-deadline job can satisfy a cumulative due-work inequality for a different job. Its retained optima therefore define relaxed planning envelopes, not generally job-feasible capacities. Their second order statistic among 100 scenarios is a 95%/95% tolerance statistic of that relaxed quantity, with achieved confidence 0.96292.<sup>34</sup> It does not guarantee feasible work scheduling. Controller offers instead use completed queue simulations on independent seeds; their joint delivery-and-service probability is assessed by a one-sided 95% Wilson lower bound, required to reach 0.95.<sup>35,36</sup> The strict-window feasibility diagnostics use each work group’s own release and deadline.

累计 PI 程序在累计类别释放量与累计类别到期量约束下最大化 R。这些是必要的汇总条件，但当作业时间窗交叉时构成放松：为一个较早释放、较晚到期的作业完成的工作，可能满足另一个作业的累计到期不等式。因此，保留的最优值给出放松模型的规划界限，并非一般都能满足实际作业时间窗的容量。100 个情景中的第二顺序统计量，是该放松量在 95%/95% 条件下的容忍统计量，实际达到的置信度为 0.96292。<sup>34</sup> 它不保证存在可行作业调度。控制器报价则来自独立种子上的完整队列模拟；交付与服务联合概率用单侧 95% Wilson 下界评价，要求达到 0.95。<sup>35,36</sup> 以下新增可行性诊断使用每个工作组自身的释放时间与期限。

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
The fixed-capacity programme used 500 kW of PV and lexicographically maximised local PV use, minimised grid import and then minimised battery throughput, retaining a 10<sup>−5</sup>-kWh lock at each preceding optimum. Rigid and flexible schedules were paired on 100 inputs; mean utilisation gains used 10,000 paired bootstrap resamples (seed 20260911). No-BESS models are continuous linear programmes, so a relative MIP gap does not set their precision. We repeated all 800 primary 10% PV optimisations and 200 no-BESS GPU20 hosting optimisations with HiGHS<sup>37</sup> relative and absolute MIP gaps 10<sup>−7</sup> and primal, dual and MIP feasibility tolerances 10<sup>−8</sup>. Each solve used one thread and a 120-s limit. All fixed-PV programmes resolved; 34 flexible BESS hosting problems reached the time limit. Their feasible and dual bounds, retained in full, did not affect the minimum hosting boundary over 100 scenarios. Primary-objective bounds separate numerical uncertainty from paired sampling intervals (Supplementary Table 24).

固定容量程序采用 500 kW PV，按字典序最大化本地 PV 利用、最小化电网购电、再最小化储能吞吐，对此前各级最优值保留 10<sup>−5</sup> kWh 锁定容差。刚性和灵活调度在 100 个输入上配对；平均利用率增益采用 10,000 次配对自助抽样，种子为 20260911。无储能模型是连续线性规划，因此其精度不由相对 MIP gap 决定。我们重算了主 10% 情景的全部 800 项 PV 优化，以及 GPU20 无储能接纳的 200 项优化；HiGHS<sup>37</sup> 的相对、绝对 MIP gap 均为 10<sup>−7</sup>，原始、对偶及 MIP 可行性容差均为 10<sup>−8</sup>。每次求解使用一个线程，时限为 120 s。所有固定 PV 程序均求解完成；34 项灵活储能接纳问题达到时限，其完整保留的可行解与对偶界不影响 100 个情景中的最小接纳边界。主目标界用于区分数值不确定性与配对抽样区间（补充表 24）。

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
Reference prices were US$50 per MWh of capped delivered energy, US$0.10 per kWh of incremental electricity and US$0.005 per GPU-h per hour of additional waiting. We solved for the capacity payment making the fifth percentile of 2,000 bootstrap annual net values non-negative. This was a decision statistic, not a confidence interval. Natural-slack participation incurred no reserve or displacement charge. The reserve case annualised 0.15 abstract reserved PCC-side kW per offered kW at US$2,500 per reserved kW, four-year life, 8% discount, 10% salvage and 3% annual operation and maintenance. The displacement case added an assumed US$0.25 per deferred GPU-h; this exposure was distinct from delay cost and was not a measured revenue loss. Connection benefits and checkpoint costs were unpriced; the reference missed-work price was zero. The model rescheduled work on the same powered GPUs and assumed no DR-induced change in useful life. Accordingly, no incremental hardware-degradation charge was assigned; the power calibration did not test this lifetime assumption, and existing-fleet depreciation was not charged again as an incremental response expense.

参考价格为：封顶后的交付电量每 MWh 50 美元，增量用电每 kWh 0.10 美元，额外等待每 GPU 小时每小时 0.005 美元。我们求使 2,000 次自助抽样年度净值的第 5 百分位不为负的容量补偿。这是决策统计量，而非置信区间。自然空闲参与不计预留或挤占收费。预留情景按每千瓦承诺对应 0.15 个抽象 PCC 侧预留千瓦进行年化：每预留千瓦投资 2,500 美元、寿命四年、折现率 8%、残值 10%、年运维 3%。挤占情景增加每推迟 GPU 小时 0.25 美元的假定价值暴露；这与延迟成本不同，也不是实测收入损失。 接入收益与检查点成本未定价，参考未完成工作价格为零。模型在同一批保持通电的 GPU 上调整任务执行时间，并假定需求响应不改变设备使用寿命。因此未另计响应造成的硬件退化成本；功率标定没有验证这一寿命假设，既有设备折旧也没有再次计为响应新增费用。

<!-- M091 -->
Enablement costs combined a site-wide annual charge with a variable per-kilowatt charge:

接入与使能成本由场站年度固定费用及按千瓦计的可变费用组成：

$$
C_{\mathrm{enable}}(K)=\mathbf 1[K>0]C_{\mathrm{fixed,site}}+c_{\mathrm{variable}}K.
$$

<!-- M093 -->
The reference fixed site charge was US$25,000 per year and the variable enablement charge was zero. Accounting multiplied offered power and physical ledger quantities by 1000 divided by each configuration’s operating peak, then applied the site charge once. Annual draws sampled 50 independent single events or 12 independent complete four-call series, retaining failures. The external-source register<sup>38–43</sup> contextualises the financial sensitivity ranges; Scope and interpretation defines the limits of this proportional accounting.

参考固定场站费用为每年 25,000 美元，可变接入费用为零。核算将报价功率和物理账本量乘以 1000 除以各配置运行峰值，再计入一次场站费用。年度抽样采用 50 个独立单次事件或 12 个独立完整四调用序列，并保留失败。外部来源登记<sup>38–43</sup> 为财务敏感性范围提供背景；“范围与解释”界定这种按比例核算的适用边界。

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
Independent simulated scenarios were the statistical units for model qualification; calls within a scenario were scored jointly. Relaxed PI tolerance statistics, Wilson probability lower bounds and paired bootstrap intervals were pointwise. All 20 notice comparisons had zero discordant success pairs, so we report their outcome identity directly. Hardware intervals retained the independent-run analysis. Source Data contain individual outcomes, frozen selections, complete paired ledgers and plotting summaries, with hashes linking source, protocol and controller versions.

模型资格检验以独立模拟情景为统计单位，同一情景中的调用联合评分。放松 PI 容忍统计量、Wilson 概率下界和配对自助区间均为逐项结果。20 项提前通知比较的成功标记均没有不一致配对，因此直接报告结果逐一相同。硬件区间保留独立运行分析。源数据包含逐情景结果、冻结选择、完整配对账本及绘图汇总，哈希连接源数据、协议和控制器版本。

<!-- M023_stats -->
Structural contrasts resampled 300 complete paired scenario seeds 5,000 times. Exact McNemar tests were Holm-adjusted over 36 binary structural contrasts; the 16 additional matched-target electrical contrasts formed a separate family. Both service endpoints used the pointwise one-sided 95% Wilson lower-bound criterion of 0.95. External workload summaries retained the observed week as their sampling unit; conditional empirical-mixture qualification is defined separately below.

结构比较对 300 个完整配对情景种子重采样 5,000 次。36 项二元结构比较采用精确 McNemar 检验和 Holm 校正；另外 16 项匹配末次调用的电气比较组成单独检验族。两种服务标准均采用逐项单侧 95% Wilson 下界达到 0.95 的标准。外部工作负载汇总以观测周为抽样单位；条件性经验混合分布资格检验在下文单独定义。

<!-- M024_refinement -->
Local refinement fixed the reference workload and controller and tested fractions 0.50–0.75 for H8P16 and 0.75–1.00 for H4P16, in steps of 0.05 of the unchanged 5.898243186-kW request. H denotes duration and P start spacing. Seeds 988000–988099 supplied development; endpoint-specific selections were frozen before seeds 989000–989299 supplied confirmation. Only selected candidates and prespecified coarse comparators entered confirmation, with no reselection. The grid ceiling for eight hours was selected under both standards, so the test did not bracket a continuous maximum. Earlier seeds were not pooled with these data.

局部加密固定参考工作负载与控制器，在原有 5.898243186 kW 请求基础上，H8P16 测试 0.50–0.75，H4P16 测试 0.75–1.00，步长均为 0.05。H 表示时长，P 表示开始间隔。开发使用种子 988000–988099；分终点的选择在确认种子 989000–989299 运行前冻结。确认只检验选中候选与预先指定的粗网格对照，之后不重新选值。两种标准均选中八小时网格上端，因此测试没有夹定连续最大值。早期种子未与本次数据合并。

<!-- M024_pi_methods -->
Perfect-information diagnostics fixed each request and its four event clocks, baseline and 24-h recovery windows. Non-negative execution variables existed only between each class/release/deadline work group’s own release and deadline; execution, misses and terminal work conserved every group. Constraints retained GPU and PCC limits, 95% hourly and capped-mean delivery, 25% rebound relative to actual peak event reduction, 50% full-window peak relief and the original terminal allowance. Binary peak selectors represented the rebound denominator exactly. HiGHS solved the resulting mixed-integer feasibility problem. Thirty-three prespecified structural cases comprised five configurations, three previously used seeds and two service standards, plus three reference 4.42-kW checks; five affected external weeks supplied an additional first-shortage diagnostic each. These mechanism-selected cases were not prevalence samples. All 11 feasible witnesses passed independent work-group and electrical checks. A 90-s unresolved solve was retained and resolved as infeasible after extending only its time limit to 600 s. Full-information feasibility was not treated as causal realizability.

完美信息诊断固定每个请求及其四个事件时刻、基线和 24 h 恢复窗。只有在每个类别—释放时间—期限工作组自身的允许时段内，才建立非负执行变量；执行、漏期及期末工作对每组守恒。约束保留 GPU 与 PCC 限制、95% 逐时及截顶平均交付、相对事件实际峰值减负的 25% 反弹、完整窗口 50% 峰值削减，以及原期末积压容忍度。二进制峰值选择变量精确表示反弹分母，由 HiGHS 求解相应混合整数可行性问题。预先指定的 33 个结构条件包括五种配置、三个已用种子、两个服务标准，以及三个参考 4.42 kW 检查；另从五个受影响的外部周各取首个短缺实现作诊断。这些按机制选择的条件不用于估计发生率。全部 11 个可行见证通过独立工作组与电力约束检查。一次 90 s 未解决的求解保留原记录，仅将时限延长至 600 s 后判为不可行。完美信息可行未被当作因果可实现。

<!-- M024_workload_methods -->
The resource-time transfer test reconstructed each processed job’s GPU-seconds as the sum of requested GPU-equivalents × task launch-to-completion duration across its terminated positive-resource tasks.<sup>28</sup> All 714,903 processed jobs matched the raw task reconstruction; multiplying total requested GPUs by job submission-to-completion time instead differed for 131,379 jobs. The test retained trace hours 168–1511, whose processed time origin is 542,323 s after the raw origin. Within each week, either job counts or submitted task resource-time set hourly weights; each class’s weekly work total was normalised to the reference total. Identical synthetic job classes, deadlines, community traces, event clocks and paired whole-hour permutations were used at each seed (990000 + 100w + r; eight weeks × ten realisations). Fixed 2.95- and 4.42-kW requests gave 640 complete replays. All 320 no-response input variants passed zero-loss service; no failed variant was excluded. Aggregate counts are descriptive. Allocated resource-time is not a sensor measurement of busy GPU time, and the test retains divisible work and synthetic service rules.

资源时间适用测试将每个处理后作业的 GPU 秒数，重建为其已完成且资源量为正的各任务之“请求 GPU 当量 × 任务启动至完成时长”之和。<sup>28</sup> 全部 714,903 个处理后作业均与原始任务重建一致；若改用总请求 GPU 数乘以作业提交至完成时长，则有 131,379 个作业不一致。测试保留轨迹小时 168–1511；处理后的时间原点相对原始原点偏移 542,323 s。各周分别采用任务次数或提交任务资源时间作为逐时权重，每个类别的周工作总量归一到参考总量。每个种子使用相同的合成任务类别、期限、社区轨迹、事件时刻及配对完整小时置乱（种子 990000 + 100w + r；八周各十次实现）。固定 2.95 与 4.42 kW 请求共形成 640 次完整重放。全部 320 个无响应输入变体通过零损失服务，无失败变体被排除。合计数为描述性结果。已分配资源时间不等于传感器测得的 GPU 忙碌时间，测试仍保留可分割工作与合成服务规则。

<!-- M27_capacity_methods -->
The follow-up capacity experiment conditioned on those eight fixed weekly profiles. For each new seed, an independent uniform draw selected one week; fresh job templates, community conditions and a random final-call phase were paired between count and resource-time weights. Four eight-hour calls started 16 h apart with zero notice. Development seeds 1010000–1010099 tested fractions 1/64, 1/32, 1/16, 1/8, 1/4, 3/8, 1/2, 3/4 and 1 of 5.898243186 kW. The largest candidate with a one-sided 95% Wilson lower bound ≥0.95 was frozen separately for each weight and service endpoint. Confirmation seeds 1011000–1011299 then tested the selected offers and a prespecified 1/2-request comparator, retaining baseline failures. The 1,800 development and 900 confirmation replays did not reuse the earlier 80 realisations for selection. Inference concerns simulated draws from the fixed eight-week empirical mixture; it does not treat them as newly observed production weeks.

后续容量实验以这八个固定周曲线为条件。每个新种子通过独立均匀抽样选择一周；新作业模板、社区条件及随机末次调用相位，在次数与资源时间权重之间配对。四次八小时调用的开始间隔为 16 h，提前通知为零。开发种子 1010000–1010099 检验 5.898243186 kW 的 1/64、1/32、1/16、1/8、1/4、3/8、1/2、3/4 和 1 倍。每种权重与服务标准分别冻结单侧 95% Wilson 下界 ≥0.95 的最大候选值。确认种子 1011000–1011299 随后检验选定报价及预先指定的 1/2 请求比较值，并保留基线失败。1,800 次开发及 900 次确认重放没有重用早先 80 个实现来选值。推断针对固定八周经验混合分布的模拟抽样，并未将其视为新观测到的生产周。

<!-- M27_scope_heading -->
### Scope and interpretation

### 范围与解释

<!-- M27_scope -->
Work eligibility is permission over offered GPU-hours; operating peak is the configured reference-mix facility denominator. A selected, confirmed offer is a finite-grid policy result for its stated distribution. Exact-window witnesses diagnose individual cases, whereas probabilistic qualification retains all sampled cases. Resource-time weights describe requested task allocation and duration; the count-only control deliberately removes that information and is not attributed to Caprara et al. or another published scheduler. Proportional 1-MW accounting rescales the model's ledgers and applies one site fee; no additional facility, geographic aggregation or diversification is simulated. Economic comparisons retain the workload distribution and products on which their offers were confirmed.

工作参与比例表示供给 GPU-h 中获得许可的部分；运行峰值采用配置的参考工作组合设施功率作为分母。选定并确认的报价，是声明分布下的有限网格策略结果。严格时间窗见证诊断个别情景，概率资格检验则保留全部抽样情景。资源时间权重描述任务请求的资源量和时长；次数对照有意去掉这些信息，并不归因于 Caprara 等或其他已发表调度方法。按比例的 1 MW 会计核算缩放模型账本，并计入一次场站费用；没有额外模拟其他设施、跨地域聚合或分散收益。经济比较保留其报价通过确认时的工作负载分布和产品。

<!-- M098 -->
## Data Availability

## 数据可用性

<!-- M099 -->
Community demand was obtained from the NREL End-Use Load Profiles through the OEDI building-stock data lake.<sup>32,33</sup> Workload records came from the official Alibaba cluster-trace-gpu-v2026 release,<sup>20</sup> with the 2020 GPU trace supplying the separate chronological submission test.<sup>28</sup> Retrieval locations, preprocessing records and original input hashes are listed in data/manifests/sources.yaml. Raw third-party releases are accessed from their original providers. The accompanying Source Data bundle contains the full class-composition audit, scenario and controller identities, development selection, all trial-level outcomes, complete development and confirmation trajectories and paired economic ledgers, renewable optimisation results, calibration inputs and ready-to-plot tables. CSV and Parquet files have data dictionaries and SHA-256 manifests. Earlier benchmark outputs are preserved in a separately labelled archive. Public archival deposition of this revised bundle remains pending at [ZENODO DOI TO BE ADDED]. Submission counts, processed submission-time records, frozen scenarios and all 22,400 new replays accompany the structural Source Data. The focused extension adds 3,040 full replays, 656,640 hourly rows, 38 resolved exact-window feasibility diagnoses and task-level resource-time reconstruction records.

社区需求来自 NREL 通过 OEDI 建筑存量数据湖提供的终端用电曲线。<sup>32,33</sup> 工作记录来自 Alibaba 官方 cluster-trace-gpu-v2026 发布。<sup>20</sup> 检索位置、预处理记录与原始输入哈希列于 data/manifests/sources.yaml；第三方原始发布从原提供方获取。随附源数据包包含完整类别构成审计、情景及控制器标识、开发选值、所有试验级结果、完整开发与确认轨迹与配对经济账本、可再生能源优化结果、校准输入和可直接绘图的表格。CSV 与 Parquet 配有数据字典及 SHA-256 清单。此前基准输出保存在单独标明的归档中。本修订包的公开归档存储仍待完成：[ZENODO DOI TO BE ADDED]。 新增独立时序检验采用 Alibaba 2020 GPU 轨迹的提交记录；其计数、处理后时间记录、冻结场景与全部 22,400 次新增重放均随源数据保存。<sup>28</sup> 集中补强另增加 3,040 次完整重放、656,640 行逐时数据、38 个已解决的严格时间窗可行性诊断，以及任务级资源时间重建记录。

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

<!-- M27_ref43 -->
29. PJM Interconnection. *Manual 18: PJM Capacity Market*, sections 4.3.2 and 8 (accessed 11 September 2026). https://www.pjm.com/-/media/DotCom/documents/manuals/m18

29. PJM Interconnection. *Manual 18: PJM Capacity Market*，第 4.3.2 节及第 8 节（2026 年 9 月 11 日访问）。https://www.pjm.com/-/media/DotCom/documents/manuals/m18

<!-- M127 -->
30. Zhou, Y., Mancarella, P. & Mutale, J. Framework for capacity credit assessment of electrical energy storage and demand response. *IET Gener. Transm. Distrib.* **10**, 2267–2276 (2016). https://doi.org/10.1049/iet-gtd.2015.0458

30. Zhou, Y., Mancarella, P. & Mutale, J. 电储能与需求响应的容量信用评估框架。 *IET Gener. Transm. Distrib.* **10**, 2267–2276 (2016). https://doi.org/10.1049/iet-gtd.2015.0458

<!-- M128 -->
31. Feng, J. et al. Evaluating demand response impacts on capacity credit of renewable distributed generation in smart distribution systems. *IEEE Access* **6**, 14307–14317 (2018). https://doi.org/10.1109/ACCESS.2017.2745198

31. Feng, J. et al. 评估需求响应对智能配电系统中可再生分布式发电容量信用的影响。 *IEEE Access* **6**, 14307–14317 (2018). https://doi.org/10.1109/ACCESS.2017.2745198

<!-- M129 -->
32. Wilson, E. et al. *End-Use Load Profiles for the U.S. Building Stock: Methodology and Results of Model Calibration, Validation, and Uncertainty Quantification*. NREL/TP-5500-80889 (National Renewable Energy Laboratory, 2022). https://doi.org/10.2172/1854582

32. Wilson, E. et al. *美国建筑存量的终端用能负荷曲线：模型校准、验证与不确定性量化的方法及结果*. NREL/TP-5500-80889 (National Renewable Energy Laboratory, 2022). https://doi.org/10.2172/1854582

<!-- M130 -->
33. Parker, A. et al. *ComStock Reference Documentation: Version 1*. NREL/TP-5500-83819 (National Renewable Energy Laboratory, 2023). https://doi.org/10.2172/1967948

33. Parker, A. et al. *ComStock 参考文档：版本 1*. NREL/TP-5500-83819 (National Renewable Energy Laboratory, 2023). https://doi.org/10.2172/1967948

<!-- M133 -->
34. Vangel, M. G. One-sided nonparametric tolerance limits. *Commun. Stat. Simul. Comput.* **23**, 1137–1154 (1994). https://doi.org/10.1080/03610919408813222

34. Vangel, M. G. 单侧非参数容忍限。 *Commun. Stat. Simul. Comput.* **23**, 1137–1154 (1994). https://doi.org/10.1080/03610919408813222

<!-- M134 -->
35. Wilson, E. B. Probable inference, the law of succession, and statistical inference. *J. Am. Stat. Assoc.* **22**, 209–212 (1927). https://doi.org/10.1080/01621459.1927.10502953

35. Wilson, E. B. 概率推断、后继法则与统计推断。 *J. Am. Stat. Assoc.* **22**, 209–212 (1927). https://doi.org/10.1080/01621459.1927.10502953

<!-- M135 -->
36. Brown, L. D., Cai, T. T. & DasGupta, A. Interval estimation for a binomial proportion. *Stat. Sci.* **16**, 101–133 (2001). https://doi.org/10.1214/ss/1009213286

36. Brown, L. D., Cai, T. T. & DasGupta, A. 二项比例的区间估计。 *Stat. Sci.* **16**, 101–133 (2001). https://doi.org/10.1214/ss/1009213286

<!-- M136 -->
37. Huangfu, Q. & Hall, J. A. J. Parallelizing the dual revised simplex method. *Math. Program. Comput.* **10**, 119–142 (2018). https://doi.org/10.1007/s12532-017-0130-5

37. Huangfu, Q. & Hall, J. A. J. 对偶修正单纯形法的并行化。 *Math. Program. Comput.* **10**, 119–142 (2018). https://doi.org/10.1007/s12532-017-0130-5

<!-- M137 -->
38. CoreWeave, Inc. *Annual Report (Form 10-K) for the Year Ended 31 December 2025*. US Securities and Exchange Commission (2026). https://www.sec.gov/Archives/edgar/data/1769628/000176962826000104/crwv-20251231.htm

38. CoreWeave, Inc. *截至 2025 年十二月 31 日的年度报告（Form 10-K）*. US Securities and Exchange Commission (2026). https://www.sec.gov/Archives/edgar/data/1769628/000176962826000104/crwv-20251231.htm

<!-- M138 -->
39. Amazon.com, Inc. *Annual Report (Form 10-K) for the Year Ended 31 December 2025*. US Securities and Exchange Commission (2026). https://www.sec.gov/Archives/edgar/data/1018724/000101872426000004/amzn-20251231.htm

39. Amazon.com, Inc. *截至 2025 年十二月 31 日的年度报告（Form 10-K）*. US Securities and Exchange Commission (2026). https://www.sec.gov/Archives/edgar/data/1018724/000101872426000004/amzn-20251231.htm

<!-- M139 -->
40. Microsoft Corporation. *Annual Report (Form 10-K) for the Fiscal Year Ended 30 June 2025*. US Securities and Exchange Commission (2025). https://www.sec.gov/Archives/edgar/data/789019/000095017025100235/msft-20250630.htm

40. Microsoft Corporation. *截至 2025 年六月 30 日财年的年度报告（Form 10-K）*. US Securities and Exchange Commission (2025). https://www.sec.gov/Archives/edgar/data/789019/000095017025100235/msft-20250630.htm

<!-- M140 -->
41. National Renewable Energy Laboratory. *2024 Annual Technology Baseline: Financial Cases and Methods* (NREL, 2024). https://atb.nrel.gov/electricity/2024/financial_cases_%26_methods

41. National Renewable Energy Laboratory. *2024 年度技术基线：财务情景与方法* (NREL, 2024). https://atb.nrel.gov/electricity/2024/financial_cases_%26_methods

<!-- M141 -->
42. Lawrence Berkeley National Laboratory. *Demand Response Advanced Controls Framework and Cost Assessment* (LBNL, 2017). https://eta-publications.lbl.gov/sites/default/files/demand_response_advanced_controls_framework_and_cost_assessment_final_published.pdf

42. Lawrence Berkeley National Laboratory. *需求响应先进控制框架与成本评估* (LBNL, 2017). https://eta-publications.lbl.gov/sites/default/files/demand_response_advanced_controls_framework_and_cost_assessment_final_published.pdf

<!-- M142 -->
43. PJM Interconnection. *2027/2028 Base Residual Auction Report* (PJM, 2025). https://www.pjm.com/-/media/DotCom/markets-ops/rpm/rpm-auction-info/2027-2028/2027-2028-bra-report.pdf

43. PJM Interconnection. *2027/2028 基础剩余拍卖报告* (PJM, 2025). https://www.pjm.com/-/media/DotCom/markets-ops/rpm/rpm-auction-info/2027-2028/2027-2028-bra-report.pdf

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
### Figure 1 | AI workload composition, deferred scheduling and assessment of demand-response commitments

### 图 1 | AI 工作负载构成、任务延期调度与需求响应承诺的评估流程

<!-- M151 -->
**a,** Conceptual overview linking workload representation, job-constrained scheduling and grid commitments. The task bars illustrate postponement and recovery without a numerical time scale. Online service remains immediate; operators decide which training and offline-inference work may wait. **b,** Requested GPU-hour shares from all 40,522,321 released execution spans, using uncapped duration and including all six workload classes. These descriptive source totals characterise computing work rather than electricity consumption. **c,** Evidence-to-decision sequence: reject requests exceeding supply or strict task-window feasibility, investigate control where a feasible full-information schedule exists, qualify the causal policy independently and then compare participation costs. Qualification retains successful and failed trials. An unresolved feasibility solve supplies no definitive decision. Source Data retain full-precision class and scenario definitions.

**a，** 总体概念图，将工作负载表征、受作业约束的调度与电网响应承诺连接起来。任务条带示意延期和恢复过程，不含定量时间刻度。在线服务仍须即时完成，运营者决定哪些训练和离线推理工作允许等待。**b，** 采用未截尾时长，汇总全部 40,522,321 个公开执行片段的请求 GPU-h 份额，包含六类工作。这些描述性份额反映计算工作组成，而非用电量组成。**c，** 判断流程：请求超过即时供给或严格任务时间窗的可行范围时应修改请求；完整未来信息下存在可行调度时，可进一步改进控制；对因果策略进行独立资格检验之后，再比较参与成本。资格检验保留全部成功和失败试验。尚未求解完成的可行性问题不能支持确定判断。源数据保留完整精度的类别与情景定义。

<!-- M152 -->
### Figure 2 | Single-event response capacity and reliability across workload eligibility, event duration and advance notice

### 图 2 | 不同工作延期比例、响应时长与提前通知条件下的单次响应容量和可靠性

<!-- M153 -->
**a,** Relaxed perfect-information (PI) tolerance statistics from 100 confirmation scenarios (95% reliability and at least 95% confidence; horizontal marks) and development-selected, independently confirmed single-event offers (circles, four hours; squares, eight hours). Their different constructions mean that their ordering does not imply an information advantage. **b,** The same offers divided by each configuration's operating peak. Four- and eight-hour markers coincide because their selected capacities are identical. **c,** A compact summary of all five eligibility settings and three notice periods: paired success flags are identical at 0-, 2- and 6-h notice, with 295/300 four-hour and 292/300 eight-hour successes in each setting. Values beside the counts are one-sided 95% Wilson probability lower bounds, evaluated separately for each condition. The target is 95% success. Orange and teal identify four- and eight-hour events in this figure. The PI comparison uses aggregate release/deadline relaxations and does not certify individual-task feasibility. Additional business assumptions at 40% (*) and 60% (†) are detailed in Supplementary Table 2.

**a，** 来自 100 个确认情景的放松完整信息（PI）容忍统计量（可靠性 95%、置信水平至少 95%，短横线），以及开发阶段选定并经独立确认的单次报价（圆点为四小时，方点为八小时）。两者构造不同，其数值高低不能解释为信息优势。**b，** 同一报价占各配置运行峰值的比例。两种时长选中的容量相同，因此四小时与八小时标记重合。**c，** 将五档工作许可与三种通知时间的结果紧凑汇总：在 0、2、6 h 通知下，配对成功标记逐一相同；每档四小时成功 295/300，八小时成功 292/300。计数旁的数值是逐条件计算的单侧 95% Wilson 成功概率下界，目标成功概率为 95%。本图中橙色与青绿色分别表示四小时和八小时。PI 对照使用聚合释放与期限约束的放松模型，不保证逐任务可行。40%（*）与 60%（†）的额外业务假设见补充表 2。

<!-- M154 -->
### Figure 3 | Repeated-response offers and delivery outcomes under submission-count weighting, task-resource-time weighting and hourly reordering

### 图 3 | 作业数量与任务资源时间加权、小时重排条件下的重复响应报价和交付结果

<!-- M155 -->
**a,** Selected eight-hour repeated offers confirmed on 300 independent draws from an equal mixture of eight fixed observed weeks. Both service standards pass in 300/300 draws for each selected offer (one-sided 95% Wilson lower bound 0.9911). Bar lengths encode capacity; the twofold ratio compares finite-grid selections. **b,** All nine development requests per workload representation, each evaluated on 100 model draws before confirmation. Lines join tested points; circles and solid lines allow at most 1% missed work, whereas squares and dashed lines require zero missed work. The horizontal line marks the 95% qualification target. **c,** Zero-miss diagnoses at 5.90 kW for three prespecified seeds per configuration, distinguishing immediate shortage, other strict-window infeasibility, PI feasibility with causal failure and feasibility under both tests. **d,** Paired weight/order comparisons at 2.95 kW under both service standards. **e,** Original-order zero-miss successes by observed week; each cell retains all ten synthetic realisations. Panels d,e report descriptive counts. Weekly class totals and service rules are paired, all baselines meet zero-miss service, and all 49 original-order resource-time failures encounter shortage. Permutation changes hourly order and alignment with calls and community demand. Reference-distribution duration products are assessed separately in Supplementary Fig. 9a.

**a，** 从八个固定真实周的等权混合中独立抽取 300 个模型情景，确认选定的八小时重复调用报价。每个选定报价在两种服务标准下均成功 300/300，单侧 95% Wilson 下界为 0.9911。条带长度表示容量；两倍之比仅比较有限网格内选中的报价。**b，** 每种工作负载表征的全部九个开发候选，每点在确认之前用 100 个模型抽样评估。连线连接已测试点；圆点实线允许至多 1% 漏期工作，方点虚线要求零漏期。水平线为 95% 资格目标。**c，** 固定 5.90 kW 请求，每种配置采用三个预先指定种子开展零漏期诊断，区分即时不足、其他严格时间窗不可行、PI 可行但因果控制失败，以及两种检查均可行。**d，** 在 2.95 kW 下，对工作量权重与小时顺序进行配对比较，同时显示两种服务标准。**e，** 原始顺序下各真实周的零漏期成功数，每格保留全部十次合成实现。d,e 为描述性计数。每周类别总工作量与服务规则配对，全部基线满足零漏期；原序资源时间表征的 49 次失败全部遇到供给不足。置乱同时改变小时顺序及其与调用、社区需求的对齐。参考分布下的时长产品另见补充图 9a。

<!-- M156 -->
### Figure 4 | Available-load shortages during repeated calls and power and backlog trajectories through recovery

### 图 4 | 重复调用期间的可削减负荷不足，以及响应后功率和任务积压的恢复过程

<!-- M157 -->
**a,** Paired minimum event-hour supply margins for all 80 task-resource-time realisations at 2.95 kW, comparing original and permuted orders. Margin is baseline PCC power minus community and idle-plus-rigid data-centre demand minus 95% of the request, minimised across all calls. Zero lines separate shortage and no-shortage cases; quadrant counts are descriptive. **b,** Available baseline reduction under chronological count and resource-time weighting for protocol seed 990000. The horizontal line is the 95% delivery requirement and shading marks four calls. All 216 h are retained in Source Data; the panel displays the 168-h arrival horizon. **c,d,** Aligned power difference from baseline and additional backlog over all 216 h for reference seed 989000, at qualified four- and eight-hour offers of 5.60 and 4.42 kW. Both products make four calls starting 16 h apart. Numbered shading shows the eight-hour windows; four-hour calls share their starts. Solid lines show operation and dotted lines show requests. Negative power reduction indicates recovery above baseline. The grey 168–216-h tail permits clearance; both illustrated series finish with zero missed work. Seeds were selected by identifier, without inspecting outcomes. Panels a,b and c,d use different workload distributions. These examples explain operation; independent reliability evidence is in Supplementary Fig. 9a.

**a，** 2.95 kW 请求下，全部 80 个任务资源时间实现的最小事件时段供给余量，比较原序与置乱顺序。余量为基线公共耦合点功率，减去社区负荷、数据中心空闲及刚性负荷，再减去请求的 95%，并对全部调用时段取最小值。虚线零轴区分是否供给不足，象限计数为描述性结果。**b，** 协议种子 990000 在原序次数与资源时间表征下的基线可削减功率。水平线表示 95% 交付要求，阴影标示四次调用。源数据保留全部 216 h，面板显示其中 168 h 的到达时域。**c,d，** 参考种子 989000 的全部 216 h 功率差与额外积压，上下时间轴对齐；四小时与八小时已合格报价分别为 5.60 和 4.42 kW，两种产品均调用四次，开始间隔 16 h。编号阴影显示八小时窗口，四小时调用在相同时刻开始。实线为运行结果，点虚线为请求；负的功率削减表示恢复阶段功率高于基线。168–216 h 灰色尾段用于清理工作，两条示例序列最终均零漏期。种子按编号选取，未检查结果后挑选。a,b 与 c,d 使用不同工作负载分布。这些示例解释运行过程，独立可靠性证据见补充图 9a。

<!-- M158 -->
### Figure 5 | Response planning, participation costs and solar hosting across GPU allocations and rigid-load power assumptions

### 图 5 | GPU 分配与刚性负荷功率假设下的响应规划、参与成本与光伏接纳

<!-- M159 -->
**a,b,** Four- and eight-hour relaxed-PI tolerance statistics across flexible GPU allocations or rigid-class active-power proxies, retaining 10% eligibility, 576 GPUs and paired jobs. Each statistic uses 100 confirmation scenarios and aggregate release/deadline constraints; it does not guarantee individual-task feasibility. The fixed 5.90-kW causal request has 295/300 four-hour and 292/300 eight-hour successes across these controls (Supplementary Fig. 4c). Labels in b report operating peaks. **c,d,** Conditional four-hour single-event participation thresholds at the unchanged offer, from all 300 confirmation ledgers, 50 independent calls per annual draw, a US$25,000 annual site fee and proportional 1-MW accounting. Points are 95th-percentile annual-net-cost thresholds. **e,** Flexible minus rigid PV hosting capacity as GPU allocation changes; each hosting capacity is the minimum across 100 paired full-information, zero-miss scenarios. These are differences of minima, rather than uncertainty intervals. Lines join evaluated settings. The 10% primary points and no-storage 20% allocation point use the strict repeat audit; remaining PV points retain their original settings (Supplementary Table 24). Rigid power proxies are engineering assumptions, not measurements of online inference.

**a,b，** 改变灵活 GPU 分配比例或刚性类别活动功率代理时，四小时与八小时的放松 PI 容忍统计量；保持 10% 工作许可、576 块 GPU 和配对作业。每个统计量使用 100 个确认情景及聚合释放、期限约束，不保证逐任务可行。在这些对照中，固定 5.90 kW 因果请求的四小时成功数为 295/300，八小时为 292/300（补充图 4c）。b 中标注运行峰值。**c,d，** 不变报价下的条件性四小时单次响应参与门槛，使用全部 300 条确认账本、每年 50 次独立调用、每年 25,000 美元场站费及按 1 MW 比例核算。点为年度净成本的第 95 百分位门槛。**e，** 改变 GPU 分配时，灵活调度减去刚性调度的光伏接纳容量；每个容量均为 100 个配对情景的最小值，调度掌握完整信息并要求零漏期。因此图中是最小值之差，而非不确定性区间。连线连接已计算设置。10% 主配置数据点和无储能 20% 分配点采用严格重算，其余光伏点保留原设置（补充表 24）。刚性功率代理属于工程假设，不是在线推理实测功率。

<!-- M160 -->
### Figure 6 | Additional waiting, participation costs and service choice for qualified four- and eight-hour repeated responses

### 图 6 | 四小时与八小时合格重复响应的额外等待、参与成本和服务选择

<!-- M161 -->
**a,** Empirical cumulative distributions of additional waiting exposure per four-call series for the two qualified reference products, using all 300 confirmation sequences per product, including failures. Dotted vertical lines mark means. No smoothing or density fitting is applied. **b,** Operating cost components at the total annual 95th-percentile rank, with zero site fee and US$0.005/GPU-h/h waiting; diamonds mark the net threshold. **c,** Participation thresholds at the three tested waiting prices. **d,** The product with the largest fifth-percentile annual net value, including non-participation, as the two capacity prices vary at US$0.005/GPU-h/h waiting and zero site fee. The dotted diagonal marks equal capacity prices. Region boundaries follow the frozen cost and capacity accounting, with ties along their shared edges. All panels concern reference products qualified at a 95% success-probability target and a zero-miss success criterion: 5.60 kW for four hours and 4.42 kW for eight hours, with 16-h start spacing. Monetary panels use proportional 1-MW accounting, twelve independent four-call series per year, US$0.10/kWh electricity, US$50/MWh capped delivered-energy revenue, zero missed-work price and 2,000 annual draws retaining failures. Prices remain conditional on this reference workload; they do not price the separate resource-time offers.

**a，** 两种已合格参考产品每个四调用序列的额外等待暴露经验累积分布。每种产品保留全部 300 条确认序列，包括失败，垂直点虚线标示均值。未进行平滑或密度拟合。**b，** 零场站费、等待估值为 0.005 美元/GPU-h/h 时，位于年度总成本第 95 百分位排序位置的运行成本分项；菱形表示净门槛。**c，** 三个已测试等待价格下的参与门槛。**d，** 在等待估值为 0.005 美元/GPU-h/h、零场站费时，改变两种容量价格，选择年度净值第五百分位最高的产品，同时允许不参与。点虚线对角线表示相同容量价格。区域边界由冻结的成本与容量核算推导，共同边界上的选项价值相同。全部面板针对参考分布产品：以 95% 成功概率为资格目标，以零漏期为成功要求，四小时报价 5.60 kW、八小时报价 4.42 kW，开始间隔均为 16 h。金额面板按 1 MW 比例核算，每年十二个独立四调用序列，电价 0.10 美元/kWh，封顶交付电量收入 50 美元/MWh，漏期工作价格为零，采用保留失败的 2,000 次年度抽样。这些价格取决于参考工作负载，不为另行确认的资源时间报价定价。
