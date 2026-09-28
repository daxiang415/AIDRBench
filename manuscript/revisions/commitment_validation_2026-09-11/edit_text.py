"""Evidence-led v0.27 text and paragraph-aligned Chinese revision."""
import importlib.util,json,re
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
spec=importlib.util.spec_from_file_location('helpers',HERE.parent/'workload_composition_2026-09-09/integrate_content.py')
h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h);h.HERE=HERE
UPDATES={};AFTER={};BEFORE={}
def U(i,en,zh):UPDATES[i]=dict(en=en,zh=zh)
def A(i,key,en,zh):AFTER.setdefault(i,[]).append(dict(id=key,en=en,zh=zh))

U('M006',
'''Growing electricity demand from artificial intelligence makes dependable data-centre flexibility increasingly valuable to power systems. Yet a commitment validated with an incomplete workload description may promise more relief than an operator can deliver. Here we test this decision in a trace-informed model of 576 GPUs, with 10% of computing allowed to wait. Across eight observed weeks, a 2.95-kW repeated request passed every simulation when hourly work followed job counts. Weighting the same weekly work by task resource use left only two weeks with all simulations passing and two with none. New, independent simulations drawn from these eight weekly profiles supported an eight-hour repeated offer of 2.95 kW under count weighting and 1.47 kW under resource-time weighting. Both selected offers achieved 300/300 successes, exceeding a 95% success-probability target while requiring zero missed work in each successful series. The twofold difference concerns tested offers under a declared baseline and workload distribution. Supply and scheduling diagnostics explain when to reduce a request, improve control or compare compensation. Reliable contracts therefore require workload-sensitive qualification alongside explicit service and recovery obligations.''',
'''人工智能带来的用电需求增长，使可靠的数据中心柔性对电力系统日益重要。然而，使用不完整工作负载描述验证的承诺，可能超过运营者实际能够交付的减负量。我们在一个由轨迹数据支持、包含 576 块 GPU、允许 10% 计算工作等待的模型中检验这一决策。在八个观测周中，若每小时工作量按作业数量分配，2.95 kW 的重复请求在每周的全部模拟中均通过；若按任务资源使用量分配相同的周总工作量，则只有两周全部通过，另有两周全部失败。从这八个周负载曲线抽取的新独立模拟，分别支持次数加权下 2.95 kW、资源时间加权下 1.47 kW 的八小时重复报价。两个选定报价均达到 300/300 成功，在每个成功序列要求零漏期的同时，超过 95% 成功概率目标。两倍差异针对声明基线和工作负载分布下的已测试报价。供给与调度诊断进一步说明何时应降低请求、改进控制或比较补偿。因此，可靠合同需要结合工作负载开展资格验证，并明确服务与恢复义务。''')
U('M012',
'''Here we identify a commitment error caused by discarding task-size information, and quantify the change in a supported offer. AIDRBench combines trace-informed jobs, four-GPU board-power measurements and a modelled community electricity system. We deliberately compare two descriptions of the same weekly work: one retains submission counts; the other also retains requested GPU resources and task durations.<sup>28</sup> This controlled information ablation tests our workload-construction choice. Paired hourly permutations separate weighting from order and alignment, while new development and confirmation samples select and test offers for each description. Supply and strict task-window checks diagnose failures before complete operating ledgers compare qualified services. The contribution beyond availability envelopes<sup>19</sup> is an independently tested commitment decision linked to explicit task service, repeated recovery and a diagnosis of why a fixed request fails.''',
'''我们识别因舍弃任务规模信息而产生的承诺错误，并量化有证据支持的报价变化。AIDRBench 将轨迹支持的作业、四卡板级功率测量与社区电力模型结合。我们有意比较同一周总工作量的两种描述：一种保留提交次数，另一种还保留请求的 GPU 资源量和任务时长。<sup>28</sup> 这一受控信息消融检验的是我们自身的工作负载构造选择。配对小时置乱区分加权方式与顺序、对齐的影响；新的开发与确认样本分别为两种描述选择并检验报价。供给和严格任务时间窗检查先诊断失败，再使用完整运行账本比较合格服务。相对于可用性包络，<sup>19</sup> 本文的增量是独立检验承诺决策，将逐任务服务、重复恢复与固定请求失败原因明确连接起来。''')
U('M023',
'''The same selected power qualified at four and eight hours on the tested grid, with success decreasing from 295/300 to 292/300 in every configuration; one-sided 95% probability lower bounds were 0.9662 and 0.9533. Zero-, two- and six-hour notice gave identical paired success flags (Fig. 2b). This result belongs to the specified eager baseline, release constraints and controller; the baseline-dependent supply bound explains why notice cannot repair hours with insufficient reducible load.''',
'''在已测试网格上，四小时与八小时获得相同的合格功率，但每种配置的成功数均由 295/300 降至 292/300；单侧 95% 概率下界分别为 0.9662 和 0.9533。零、两和六小时提前通知的配对成功标记逐一相同（图 2b）。这一结果针对指定的即时处理基线、释放约束和控制器；依赖基线的供给上界解释了为什么提前通知无法修复可削减负荷不足的小时。''')
U('M023_timing',
'''Even half the reference single-event offer could fail after a change in workload representation. At 10% eligibility, a 2.95-kW request—50% of the 5.898243-kW single-event offer—passed all ten simulations in each of eight observed weeks under submission-count weighting. Under task-resource-time weighting, only two weeks passed all ten; two failed all ten and four had mixed outcomes (Fig. 3c,d). The descriptive total fell from 80/80 to 31/80. Weekly class totals, synthetic service rules, community profiles and event clocks were paired, and every no-response baseline met zero-miss service. This 2.95-kW stress request concerns the 10% configuration; the numerically equal single-event offer at 5% eligibility is a separate product.''',
'''改变工作负载表征后，连参考单次报价的一半都可能失败。在 10% 参与比例下，2.95 kW 请求即 5.898243 kW 单次报价的 50%；按提交次数加权时，八个观测周中每周十次模拟全部通过。按任务资源时间加权时，只有两周十次全部通过，另有两周十次全部失败，其余四周部分通过（图 3c,d）。描述性总计由 80/80 降至 31/80。周内各类工作总量、合成服务规则、社区曲线和调用时刻均配对，每个无响应基线都满足零漏期服务。这里的 2.95 kW 压力请求属于 10% 配置；5% 参与下数值相同的单次报价是另一种产品。''')
A('M025_order','M27_capacity',
'''Reducing the request restored qualification under the resource-time description. We selected offers on 100 new simulations and froze them before testing 300 further simulations, each independently drawing one of the eight fixed weekly profiles with equal probability. The count-weighted description selected 2.9491 kW and the resource-time description 1.4746 kW; each achieved 300/300 successes under both service standards, with a one-sided 95% lower bound of 0.9911 (Fig. 3a; Supplementary Fig. 9; Supplementary Table 22). At the unchanged 2.9491-kW comparator, resource-time success was 120/300, with all 180 failures encountering supply shortage. Thus the simplified description supported a tested offer twice as large. This ratio compares finite-grid offers conditional on the eight-week empirical distribution; it does not estimate a universal or continuous optimal-capacity ratio.''',
'''降低请求后，资源时间表征重新获得资格。我们使用 100 次新模拟选定报价，冻结后再检验另外 300 次模拟；每次独立、等概率抽取八个固定周曲线之一。次数表征选中 2.9491 kW，资源时间表征选中 1.4746 kW；两者在两种服务标准下均为 300/300 成功，单侧 95% 下界为 0.9911（图 3a；补充图 9；补充表 22）。保持 2.9491 kW 比较请求时，资源时间表征只有 120/300 成功，180 次失败均遇到供给不足。因此，简化描述支持的已测试报价是另一种描述的两倍。这个比例比较的是八周经验分布条件下的有限网格报价，不能解释为通用比例或连续最优容量之比。''')
U('M030',
'''The matched baseline makes a simple necessary supply condition available. In each event hour, baseline power above community and idle-plus-rigid demand must reach 95% of the request. A deficit makes that hour undeliverable even with all flexible execution stopped. This condition accounts for all 49 chronological resource-time failures at 2.95 kW and 25 failures after permutation (Fig. 4a,b). Full queue replay establishes that supply, rather than an additional recovery or scheduling violation, accounts for every failure in the original-order comparison. The screen is not sufficient in general: one of the 55 permuted cases without shortage still failed the zero-miss endpoint. Strict-window and causal tests address these remaining constraints.''',
'''匹配基线给出了一个简单的供给必要条件：每个事件小时，基线中高于社区负荷及空闲加刚性需求的功率，必须达到请求的 95%。出现缺口时，即使停止全部灵活执行，该小时也无法交付。该条件解释了原序资源时间表征在 2.95 kW 下的全部 49 次失败，以及置乱后的 25 次失败（图 4a,b）。完整队列重放表明，在原序比较中，供给不足已解释全部失败，无需额外归因为恢复或调度违约。但这一筛查一般并不充分：置乱后 55 个没有供给缺口的情景中，仍有一个未通过零漏期标准。严格时间窗与因果检验用于检查这些剩余约束。''')
U('M046',
'''The main finding is a quantitative commitment error: removing task resource requirements from an otherwise matched workload description supported a tested offer twice as large. Both offers subsequently passed independent confirmation, so the resource-time result specifies a usable lower commitment within the model. Weekly totals alone concealed the low-supply hours that invalidated the larger request. Paired permutation improved resource-time delivery without restoring count-weighted performance, separating workload weights from their hourly arrangement and alignment. These results extend availability-based contract descriptions<sup>19</sup> by testing the request through explicit task queues and repeated recovery, then separating physical impossibility from a controller's failure to realise a feasible schedule.''',
'''核心发现是一个可量化的承诺错误：在其他条件匹配时，去掉任务资源需求信息，会支持一个大两倍的已测试报价。两个报价随后均通过独立确认，因此资源时间结果给出了模型内可使用的较低承诺。仅匹配周总量会掩盖使较大请求失败的低供给小时。配对置乱改善了资源时间交付，却没有恢复到次数加权表现，从而区分工作量权重与其小时排列、对齐。相对于基于可用性的合同描述，<sup>19</sup> 这些结果通过明确的任务队列与重复恢复检验请求，并区分物理上不可实现与控制器未能实现可行调度。''')
A('M047','M27_baseline_discussion',
'''These findings depend on what a contract counts as delivery. Our counterfactual baseline immediately processes available work and retains the same rigid demand and powered GPU idle floor as the response trajectory. It therefore fixes each hour's maximum baseline-relative reduction. Notice cannot lift this ceiling, although it may improve service or recovery scheduling when supply is sufficient. Historical customer-baseline load or a fixed import ceiling defines a different obligation and can change the value of pre-positioning work. PJM's capacity framework distinguishes guaranteed load drop from a firm service level.<sup>43</sup> Our fixed-duration repeated reduction is closest in intent to a guaranteed-reduction commitment; its matched counterfactual baseline and recovery rules are explicit modelling choices, rather than an implementation of PJM settlement or baseline estimation.''',
'''这些发现取决于合同如何定义交付。本文的反事实基线立即处理已到达工作，并与响应轨迹保留相同的刚性需求和已通电 GPU 空闲功率，因此固定了每小时相对基线的最大减负量。提前通知无法抬高这一上限，但在供给充足时，仍可能改善服务或恢复调度。历史客户负荷基线或固定进口功率上限对应不同义务，也会改变提前安排工作的价值。PJM 容量框架区分保证负荷下降与固定服务水平。<sup>43</sup> 本文的定时长重复减负，在意图上最接近保证减负承诺；但匹配反事实基线及恢复规则是明确的模型选择，并未实现 PJM 的结算或基线估计方法。''')
U('M051',
'''The study represents a 576-GPU installation with 58 GPUs assigned to eligible work in the primary case. Its 193.44-kW operating peak includes 61.47 kW of node overhead and GPU idle demand, limiting the removable share before task timing is considered. This denominator and the 10% work permission distinguish the scenario from demonstrations with different participating workloads and hardware.<sup>3</sup> The trace supplies allocated task resource-time, while deadlines, permissions, divisible execution and recovery behaviour remain model assumptions. Hardware evidence calibrates board power rather than application pause–restart behaviour. Ignoring checkpoint overhead and indivisibility enlarges the scheduling possibilities at a fixed physical baseline; a causal controller's observed failure rate still cannot be treated as a lower bound on real-system failure. The eight-week empirical distribution, pointwise qualification and finite grids delimit the capacity comparison, and independent annual series delimit economic extrapolation.''',
'''本文表示一个 576 卡设施，主情景将其中 58 卡分配给可参与工作。193.44 kW 的运行峰值包含 61.47 kW 节点开销和 GPU 空闲需求，因此在考虑任务时序前，可移除功率比例已受到限制。这一分母和 10% 工作许可，使本情景区别于参与工作与硬件不同的现场演示。<sup>3</sup> 轨迹提供的是分配给任务的资源时间，期限、许可、可分割执行及恢复行为仍是模型假设。硬件证据校准板级功率，而非应用暂停—重启行为。在物理基线固定时，忽略检查点开销与不可分割性会扩大可调度范围；但因果控制器的观测失败率仍不能当作真实系统失败率的下界。八周经验分布、逐项资格检验与有限网格限定容量比较的范围，独立年度序列则限定经济外推。''')
U('M068',r'''\[
\begin{aligned}
P^{\mathrm{DC}}_t=\frac{\mathrm{PUE}}{1000}\Big[&N_{\mathrm{node}}p_{\mathrm{node}}+N_{\mathrm{GPU}}p_{\mathrm{idle}}\\
&+N_{\mathrm{rigid}}u_{\mathrm{rigid}}(\bar p_{\mathrm{rigid}}-p_{\mathrm{idle}})
+\sum_c(p_c-p_{\mathrm{idle}})\frac{X_{c,t}}{\Delta t}\Big].
\end{aligned}
\]''',r'''\[
\begin{aligned}
P^{\mathrm{DC}}_t=\frac{\mathrm{PUE}}{1000}\Big[&N_{\mathrm{node}}p_{\mathrm{node}}+N_{\mathrm{GPU}}p_{\mathrm{idle}}\\
&+N_{\mathrm{rigid}}u_{\mathrm{rigid}}(\bar p_{\mathrm{rigid}}-p_{\mathrm{idle}})
+\sum_c(p_c-p_{\mathrm{idle}})\frac{X_{c,t}}{\Delta t}\Big].
\end{aligned}
\]''')
A('M068','M27_power_terms',
'''where power p is in watts, X is executed flexible GPU-hours and Δt = 1 h. Node overhead applies to all 144 nodes and idle power to all 576 GPUs. The rigid pool contains 518 GPUs at utilisation 0.65050193; its class-weighted active power is 291.42199 W/GPU. The reference flexible mix has 297.90848 W/GPU active power. At PUE 1.2 and idle power 13.935625 W/GPU, the operating peak is 51.840000 + 9.632304 + 112.202165 + 19.764511 = 193.438980 kW: node overhead, all-GPU idle draw, rigid increment and full flexible-pool reference increment, respectively. Thus the compact form \\(P^{\\mathrm{DC}}_t=P_{\\mathrm{fixed}}+\\sum_c e_cX_{c,t}\\) uses \\(P_{\\mathrm{fixed}}=173.674469\\) kW and \\(e_c=\\mathrm{PUE}(p_c-p_{\\mathrm{idle}})/(1000\\Delta t)\\).''',
'''式中功率 p 的单位为 W，X 为已执行的灵活 GPU-h，Δt = 1 h。节点开销计入全部 144 个节点，空闲功率计入全部 576 块 GPU。刚性池包含 518 卡，利用率为 0.65050193，按工作类别加权的活动功率为 291.42199 W/GPU。参考灵活工作组合的活动功率为 297.90848 W/GPU。PUE 为 1.2、空闲功率为 13.935625 W/GPU 时，运行峰值为 51.840000 + 9.632304 + 112.202165 + 19.764511 = 193.438980 kW，依次对应节点开销、全部 GPU 空闲功率、刚性增量和满灵活池参考增量。因此，简写 \\(P^{\\mathrm{DC}}_t=P_{\\mathrm{fixed}}+\\sum_c e_cX_{c,t}\\) 中的 \\(P_{\\mathrm{fixed}}\\) 为 173.674469 kW，\\(e_c=\\mathrm{PUE}(p_c-p_{\\mathrm{idle}})/(1000\\Delta t)\\)。''')
U('M069',
'''Calibration used four NVIDIA RTX PRO 6000 Blackwell Max-Q GPUs connected by PCIe without NVLink. Active training and offline-inference board power averaged 259.08 and 300.02 W/GPU, and idle power averaged 13.94 W/GPU. Two independent runs per active class supplied the fit and a third was held out. Simultaneous GPU observations were averaged within each run; independent runs were the statistical units.''',
'''校准使用四块通过 PCIe 连接、没有 NVLink 的 NVIDIA RTX PRO 6000 Blackwell Max-Q GPU。训练和离线推理的活动板级功率分别平均为 259.08 和 300.02 W/GPU，空闲功率平均为 13.94 W/GPU。每个活动工作类使用两次独立运行拟合，第三次留出检验。同次运行中同时测得的 GPU 观测先取均值；统计单位为独立运行。''')
A('M070','M27_overhead',
'''Fixed-overhead sensitivity used 150, 300, 450 and 600 W/node (Supplementary Fig. 10; Supplementary Table 23). These change the operating peak to 167.52, 193.44, 219.36 and 245.28 kW. We added PUE × 144 × (p_node − 300)/1000 to both power trajectories of all 600 independently confirmed reference schedules and rescored event and PCC constraints. This exact affine check tests feasibility of unchanged schedules, without selecting new offers or rerunning the controller. Baseline-relative reductions, backlog and waiting are invariant; absolute PCC headroom and the per-MW accounting conversion change.''',
'''固定开销敏感性采用 150、300、450 和 600 W/node（补充图 10；补充表 23），运行峰值相应变为 167.52、193.44、219.36 和 245.28 kW。我们对全部 600 条独立确认参考调度的响应与基线功率同时加上 PUE × 144 × (p_node − 300)/1000，重新评分事件及接入点约束。这一精确仿射检查验证原调度的可行性，没有重新选择报价或运行控制器。相对基线的减负、积压和等待保持不变；绝对接入余量及每 MW 会计换算会改变。''')
U('M097',
'''Independent simulated scenarios were the statistical units for model qualification; calls within a scenario were scored jointly. Relaxed PI tolerance statistics, Wilson probability lower bounds and paired bootstrap intervals were pointwise. All 20 notice comparisons had zero discordant success pairs, so we report their outcome identity directly. Hardware intervals retained the independent-run analysis. Source Data contain individual outcomes, frozen selections, complete paired ledgers and plotting summaries, with hashes linking source, protocol and controller versions.''',
'''模型资格检验以独立模拟情景为统计单位，同一情景中的调用联合评分。放松 PI 容忍统计量、Wilson 概率下界和配对自助区间均为逐项结果。20 项提前通知比较的成功标记均没有不一致配对，因此直接报告结果逐一相同。硬件区间保留独立运行分析。源数据包含逐情景结果、冻结选择、完整配对账本及绘图汇总，哈希连接源数据、协议和控制器版本。''')
A('M024_workload_methods','M27_capacity_methods',
'''The follow-up capacity experiment conditioned on those eight fixed weekly profiles. For each new seed, an independent uniform draw selected one week; fresh job templates, community conditions and a random final-call phase were paired between count and resource-time weights. Four eight-hour calls started 16 h apart with zero notice. Development seeds 1010000–1010099 tested fractions 1/64, 1/32, 1/16, 1/8, 1/4, 3/8, 1/2, 3/4 and 1 of 5.898243186 kW. The largest candidate with a one-sided 95% Wilson lower bound ≥0.95 was frozen separately for each weight and service endpoint. Confirmation seeds 1011000–1011299 then tested the selected offers and a prespecified 1/2-request comparator, retaining baseline failures. The 1,800 development and 900 confirmation replays did not reuse the earlier 80 realisations for selection. Inference concerns simulated draws from the fixed eight-week empirical mixture; it does not treat them as newly observed production weeks.''',
'''后续容量实验以这八个固定周曲线为条件。每个新种子通过独立均匀抽样选择一周；新作业模板、社区条件及随机末次调用相位，在次数与资源时间权重之间配对。四次八小时调用的开始间隔为 16 h，提前通知为零。开发种子 1010000–1010099 检验 5.898243186 kW 的 1/64、1/32、1/16、1/8、1/4、3/8、1/2、3/4 和 1 倍。每种权重与服务标准分别冻结单侧 95% Wilson 下界 ≥0.95 的最大候选值。确认种子 1011000–1011299 随后检验选定报价及预先指定的 1/2 请求比较值，并保留基线失败。1,800 次开发及 900 次确认重放没有重用早先 80 个实现来选值。推断针对固定八周经验混合分布的模拟抽样，并未将其视为新观测到的生产周。''')
A('M27_capacity_methods','M27_scope_heading','### Scope and interpretation','### 范围与解释')
A('M27_capacity_methods','M27_scope',
'''Work eligibility is permission over offered GPU-hours; operating peak is the configured reference-mix facility denominator. A selected, confirmed offer is a finite-grid policy result for its stated distribution. Exact-window witnesses diagnose individual cases, whereas probabilistic qualification retains all sampled cases. Resource-time weights describe requested task allocation and duration; the count-only control deliberately removes that information and is not attributed to Caprara et al. or another published scheduler. Proportional 1-MW accounting rescales the model's ledgers and applies one site fee; no additional facility, geographic aggregation or diversification is simulated. Economic comparisons retain the workload distribution and products on which their offers were confirmed.''',
'''工作参与比例表示供给 GPU-h 中获得许可的部分；运行峰值采用配置的参考工作组合设施功率作为分母。选定并确认的报价，是声明分布下的有限网格策略结果。严格时间窗见证诊断个别情景，概率资格检验则保留全部抽样情景。资源时间权重描述任务请求的资源量和时长；次数对照有意去掉这些信息，并不归因于 Caprara 等或其他已发表调度方法。按比例的 1 MW 会计核算缩放模型账本，并计入一次场站费用；没有额外模拟其他设施、跨地域聚合或分散收益。经济比较保留其报价通过确认时的工作负载分布和产品。''')
U('M154','### Figure 3 | Workload representation changes the supported commitment','### 图 3 | 工作负载表征改变有证据支持的承诺')
U('M155',
'''**a,** Selected eight-hour repeated offers under count and resource-time weighting, confirmed on 300 independent draws from an equal mixture of eight fixed observed weeks. Each offer passes both service standards in 300/300 draws (one-sided 95% Wilson lower bound 0.9911); bars show capacities, not uncertainty limits. The twofold ratio concerns selected grid points. **b,** Zero-miss diagnoses at 5.90 kW for three prespecified seeds per structural configuration, distinguishing supply shortage, other strict-window infeasibility, PI feasibility with causal failure and causal success. **c,** Paired weight/order comparisons at 2.95 kW under both service standards. **d,** Original-order zero-miss success in each observed week. Panels c,d retain ten synthetic realisations per week and descriptive pooled counts; hourly permutation changes order and alignment with calls and community demand. Weekly class totals and service rules are matched, all baselines pass zero-miss service, and all 49 original-order resource-time failures encounter supply shortage. The reference-distribution duration products remain in Supplementary Fig. 9a.''',
'''**a，** 次数与资源时间加权下选定的八小时重复报价，使用从八个固定观测周的等权混合分布独立抽取的 300 次模拟确认。两个报价在两种服务标准下均为 300/300 成功，单侧 95% Wilson 下界为 0.9911；柱表示容量，不是不确定性界限。两倍比例针对选定网格点。**b，** 每种结构配置的三个预先指定种子在 5.90 kW 下的零漏期诊断，区分供给不足、其他严格时间窗不可行、PI 可行但因果失败以及因果成功。**c，** 两种服务标准下，2.95 kW 的配对权重及顺序比较。**d，** 每个观测周原始顺序下的零漏期成功数。c,d 保留每周十个合成实现，汇总计数为描述性结果；小时置乱同时改变顺序及与调用、社区负荷的对齐。周内各类工作总量和服务规则匹配，所有基线通过零漏期服务，原序资源时间表征的全部 49 次失败均遇到供给不足。参考分布的时长产品仍见补充图 9a。''')
A('M142','M27_ref43','43. PJM Interconnection. *Manual 18: PJM Capacity Market*, sections 4.3.2 and 8 (accessed 11 September 2026). https://www.pjm.com/-/media/DotCom/documents/manuals/m18','43. PJM Interconnection. *Manual 18: PJM Capacity Market*，第 4.3.2 节及第 8 节（2026 年 9 月 11 日访问）。https://www.pjm.com/-/media/DotCom/documents/manuals/m18')

def expand(rows):
    result=[]
    def append(row):
        row=dict(row)
        if row['id'] in UPDATES:row.update(UPDATES[row['id']])
        result.append(row)
        for add in AFTER.get(row['id'],[]):append(add)
    for row in rows:append(row)
    return result

def main():
    # Supplementary edits and numerical additions are generated only after audits finish.
    extra=json.loads((HERE/'supplement_edits.json').read_text())
    UPDATES.update(extra['replace'])
    for key,values in extra['after'].items():AFTER.setdefault(key,[]).extend(values)
    reader=ROOT/'docs/chinese_reader/v21';reader.mkdir(parents=True,exist_ok=True);(reader/'sources').mkdir(exist_ok=True)
    allrows={}
    for stem in ['main','supplement']:
        rows=json.loads((HERE/f'before/chinese_v20/{stem}_aligned_blocks.json').read_text())['blocks']
        allrows[stem]=expand(rows)
    # Locate older-reference qualifications explicitly after Figure 3a is replaced.
    for stem,rows in allrows.items():
        for row in rows:
            for lang in ['en','zh']:
                row[lang]=row[lang].replace('docs/figures/figure_completeness_v1/artwork/','docs/figures/commitment_validation_v1/artwork/')
            if row['id'] in ['M027','M157']:
                row['en']=row['en'].replace('Fig. 3a','Supplementary Fig. 9a');row['zh']=row['zh'].replace('图 3a','补充图 9a')
            if row['id']=='M153':
                row['en']=row['en'].replace('Complete paired outcomes and Holm-adjusted exact McNemar tests are provided.','All paired success flags are identical across notice conditions.')
                row['zh']=re.sub(r'[^。]*Holm[^。]*。','所有通知条件的配对成功标记逐一相同。',row['zh'])
    allrows['main']=h.renumber_references(allrows['main'])
    mapping=json.loads((HERE/'reference_number_map.json').read_text())
    def remap(m):
        raw=m[1]
        if not re.fullmatch(r'\d+(?:[–,-]\d+)*',raw):return m[0]
        numbers=[]
        for term in raw.split(','):
            ends=re.split('[–-]',term);numbers.extend(range(int(ends[0]),int(ends[-1])+1))
        return '<sup>'+','.join(str(mapping[str(n)]) for n in numbers)+'</sup>'
    for row in allrows['supplement']:
        for lang in ['en','zh']:row[lang]=re.sub(r'<sup>(.*?)</sup>',remap,row[lang])
    for stem,rows in allrows.items():
        name='nature_communications_article.md' if stem=='main' else 'supplementary_information.md'
        head=f'<!--\nWorking {stem}, version 0.27, 2026-09-11.\nIndependent workload-specific capacity confirmation; power and solver-precision audit.\nAuthor metadata remain pending.\n-->\n\n'
        doc=head+'\n\n'.join(r['en'] for r in rows)+'\n';target=ROOT/'manuscript'/name;target.write_text(doc)
        (reader/'sources'/f'{stem}_original.md').write_text(doc)
        cn=[];both=[]
        for row in rows:
            en,zh=h.reader_format(row['en']),h.reader_format(row['zh']);cn.append(zh)
            both.extend([zh] if en.startswith(('![','$$')) else [f'<!-- {row["id"]} -->\n{en}',zh])
        note='本稿逐段对应英文 v0.27（2026-09-11），包括新增的工作负载报价确认、功率分解及数值精度核查。\n\n'
        for suffix,parts in [('zh',cn),('bilingual',both)]: (reader/f'{stem}_{suffix}.md').write_text(note+'\n\n'.join(parts)+'\n')
        (reader/f'{stem}_aligned_blocks.json').write_text(json.dumps(dict(source_sha256=h.sha(target),blocks=rows),ensure_ascii=False,indent=2)+'\n')
    (reader/'README.md').write_text('# 中文阅读稿 v21\n\n对应英文 v0.27；正文与补充材料均逐段同步。\n\n- [正文中文](main_zh.md)\n- [补充中文](supplement_zh.md)\n- [正文中英](main_bilingual.md)\n- [补充中英](supplement_bilingual.md)\n')
    (HERE/'text_changes.json').write_text(json.dumps(dict(replace=UPDATES,after=AFTER),ensure_ascii=False,indent=2)+'\n')
    print('Wrote v0.27 and Chinese v21')
if __name__=='__main__':main()
