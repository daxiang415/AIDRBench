"""Version 0.21: evidence-led English and paragraph-aligned Chinese revision."""
import importlib.util
import json
import shutil
from pathlib import Path
import pandas as pd

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
DATA=ROOT/'manuscript/source_data/nature_repeat_mechanism_v1'
READER=ROOT/'docs/chinese_reader/v15'
spec=importlib.util.spec_from_file_location('previous_integration',HERE.parent/'workload_composition_2026-09-09/integrate_content.py')
old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old);old.HERE=HERE


def main():
    summary=pd.read_csv(DATA/'confirmation_summary.csv')
    selected=pd.read_csv(DATA/'selected_offers.csv')
    contrasts=pd.read_csv(DATA/'paired_controller_contrasts.csv')
    econ=pd.read_csv(DATA/'economic_primary.csv')
    edits={};after={}
    def edit(id,en,zh):edits[id]=dict(en=en,zh=zh)
    def add(id,new_id,en,zh):after.setdefault(id,[]).append(dict(id=new_id,en=en,zh=zh))
    def row(case,program,controller,fraction):
        g=summary[(summary.case==case)&(summary.program==program)&(summary.controller==controller)&(summary.fraction==fraction)]
        assert len(g)==1;return g.iloc[0]
    p=contrasts[(contrasts.case=='f10')&(contrasts.program=='H8G12')&(contrasts.controller=='all_window_mpc')&(contrasts.fraction==1)].iloc[0]
    o=row('f10','H8G12','original',1);r=row('f10','H8G12','all_window_mpc',1)
    selections=[]
    for s in selected.itertuples():
        if pd.notna(s.selected_fraction):selections.append(row(s.case,s.program,s.controller,s.selected_fraction))
    qualified=sum(bool(s.qualified) for s in selections)
    allnew=[s for s in selections if s.controller=='all_window_mpc']
    assert len(allnew)==20
    # Numerical prose is emitted only after the independent outcomes exist.
    assert all(s.qualified for s in allnew), 'Rewrite claims if a selected revised option fails confirmation'
    new_success_min=min(int(s.successes) for s in allnew)
    new_success_max=max(int(s.successes) for s in allnew)
    costs=econ[(econ.controller=='all_window_mpc')&econ.selected_by_development&(econ.regime=='slack')]
    f10costs=costs[costs.case=='f10'].set_index('program')
    k4=float(row('f10','H4G8','all_window_mpc',1).capacity_kw)
    k8=float(row('f10','H8G12','all_window_mpc',.75).capacity_kw)

    edit('M006',
      f'Artificial-intelligence data centres could support electricity grids by postponing computing, but online services limit how much work operators can allow to wait. Here we connect explicit workload permissions to response capacity, repeated delivery, photovoltaic integration and participation costs. A production resource-time audit identifies low-priority training and offline inference as a candidate pool, without equating priority with permission. With 5–20% of work eligible, independently tested single-event offers are 2.95–11.80 kW for modelled operating peaks of 190–200 kW. Repeated-call failures depend on both recovery control and service constraints. Preserving the power ceiling for every overlapping recovery window increased eight-hour programme success at 10% eligibility from {int(o.successes)}/300 to {int(r.successes)}/300 at the same request. A separate development selection and independent test qualified full four-hour offers and eight-hour offers at 75% of the single-event request across the five workload scenarios. Smaller commitments concentrate fixed participation costs on fewer kilowatts. Dependable flexibility therefore requires a declared workload permission, recovery policy and call schedule, together with compensation evaluated for that qualified offer.',
      f'人工智能数据中心可以通过推迟计算支持电网，但在线服务限制了运营者能够允许等待的工作量。本文将明确的工作延期权限与响应容量、重复交付、光伏接入和参与成本联系起来。生产资源时间审计将低优先级训练与离线推理识别为候选工作池，但不把低优先级等同于参与许可。在允许 5–20% 工作延后的情景中，独立检验的单次事件承诺为 2.95–11.80 kW，对应模型运行峰值 190–200 kW。重复调用失败同时取决于恢复控制和服务约束。在 10% 工作资格下，为每个重叠恢复窗口保留功率上限，使同一八小时响应请求的整组成功次数从 {int(o.successes)}/300 提高至 {int(r.successes)}/300。另行开展的开发选值与独立检验，在全部五档工作情景中支持四小时全额承诺，以及单次事件请求 75% 的八小时承诺。较小承诺使固定参与成本分摊到更少的千瓦上。因此，可靠灵活性需要明确工作延期权限、恢复策略与调用安排，并针对通过资格检验的承诺评估补偿。')
    edit('M009',
      'Research on data-centre flexibility has established how operators can reshape electricity demand while serving computing jobs. Batch scheduling, server power management and workload migration have been used to reduce peaks and participate in demand response.<sup>3–7</sup> Carbon-aware scheduling extends these controls to hours and locations with lower emissions or greater renewable availability.<sup>8–11</sup> Other studies address pause-and-resume decisions and GPU power capping.<sup>12,13</sup> Trace-based and planning studies connect workload flexibility to demand-response programmes, advance notice and grid interconnection.<sup>14–17</sup> A recent preprint further distinguishes eligible workload power from dependable relief, using duration, reliability and portfolio structure and explicitly recognising delivery and recovery requirements.<sup>41</sup> The remaining operational question is how a declared offer performs when causal control carries unfinished work and overlapping recovery obligations through successive calls.',
      '数据中心灵活性研究已经说明，运营者可以在服务计算作业的同时改变用电时序。批处理调度、服务器功率管理和工作负载迁移已被用于削峰和需求响应。<sup>3–7</sup> 碳感知调度进一步将工作安排到排放更低或可再生能源更充足的时段和地点。<sup>8–11</sup> 其他研究讨论了暂停与恢复决策以及 GPU 功率限制。<sup>12,13</sup> 基于轨迹的研究和规划研究把工作灵活性与需求响应项目、提前通知和电网接入联系起来。<sup>14–17</sup> 一篇近期预印本进一步依据持续时间、可靠性和资源组合结构区分了合资格工作功率与可靠减负，并明确认识到实际交付和恢复要求。<sup>41</sup> 仍需回答的运行问题是：当因果控制器将未完成工作及重叠恢复义务带入后续调用时，预先声明的功率承诺能够交付到什么程度。')
    edit('M012',
      'Here we assess data-centre power commitments across declared workload compositions, following each configuration through service qualification, repeated dispatch, PV integration and participation costs. We audit a production execution summary and construct scenarios in which 5%, 10% or 20% of offered work may wait. Higher-share comparisons at 40% and 60% expose the extra participation and business-composition assumptions needed for larger flexibility. AIDRBench combines trace-informed job shapes with four-GPU power measurements and a modelled community electricity system. Full-information schedules quantify planning potential, while independent causal-controller tests assess delivery. A recovery intervention then distinguishes failures caused by a controller limitation from remaining deadline pressure, and a frozen development-to-confirmation procedure tests revised repeated offers. The analysis connects workload permission to an independently tested operating choice and its downstream cost.',
      '本文针对明确声明的工作构成评估数据中心功率承诺，并将每档配置贯穿服务资格检验、重复调用、光伏接入和参与成本分析。我们审计生产执行汇总，构建允许 5%、10% 或 20% 到达工作等待的情景。40% 和 60% 的较高比例比较揭示了获取更大灵活性所需的额外参与许可与业务构成假设。AIDRBench 将基于轨迹的作业形态、四 GPU 功率测量和社区电力系统模型结合起来。完整信息调度用于量化规划潜力，独立的因果控制器检验用于评估实际交付。随后通过恢复控制干预，将控制器局限导致的失败与剩余的期限压力区分开，并通过冻结的开发选值—确认流程检验调整后的重复承诺。这样，工作延期权限便与经过独立检验的运行选择及其后续成本相连接。')
    edit('M025','### Recovery control changes which repeated offers qualify','### 恢复控制改变了能够通过检验的重复承诺')
    edit('M026',
      'The first repeated-call comparison showed why a single-event result cannot simply be reused. At 10% eligibility and a 5.90-kW request, four eight-hour calls with twelve-hour gaps succeeded in 256/300 original confirmation scenarios, compared with 297/300 when the four calls ran separately at the same clock times. The paired difference was −13.7 percentage points (95% interval, −17.7 to −9.7). However, a failure of the electrical recovery criterion is not evidence of lost computing work. Inspection revealed that the original controller retained only one binding recovery window. When windows overlapped, that window did not always impose the tightest allowable power ceiling (Fig. 3b).',
      '首次重复调用比较说明，单次事件结果不能直接复用。在 10% 工作资格和 5.90 kW 请求下，四次八小时调用、调用间隔十二小时，在原确认集上的整组成功次数为 256/300；若在相同钟点分别运行这四次调用，则为 297/300。配对差异为 −13.7 个百分点（95% 区间，−17.7 至 −9.7）。但电力恢复指标失败并不等于计算工作丢失。检查发现，原控制器只保留一个起约束作用的恢复窗口；多个窗口重叠时，这个窗口不一定给出最严格的允许功率上限（图 3b）。')
    edit('M027',
      f'We therefore retained every observed call’s recovery ceiling while keeping the request, workload, MPC policy and success criteria fixed. On 300 new paired scenarios, eight-hour programme success at 10% eligibility increased from {int(o.successes)}/300 to {int(r.successes)}/300: {p.difference_pp:.1f} percentage points (95% paired interval, {p.ci_low_pp:.1f} to {p.ci_high_pp:.1f}; Fig. 3a). All {int(p.rescued_window_only_failures)} rescued scenarios originally failed only window peak relief; no new scenario exceeded the deadline-miss criterion. The same guards around a greedy proposal also achieved 294/300, so the gain was not specific to MPC. Tighter recovery still has a service cost: with eight-hour gaps, full-request deadline failures increased from 7/100 to 33/100 in development (Supplementary Fig. 3; Supplementary Table 11).',
      f'因此，我们为每次已观察到的调用保留恢复功率上限，同时保持请求、工作负载、MPC 策略和成功标准不变。在 300 个新的配对情景中，10% 工作资格下的八小时整组成功次数从 {int(o.successes)}/300 增至 {int(r.successes)}/300，即提高 {p.difference_pp:.1f} 个百分点（95% 配对区间，{p.ci_low_pp:.1f} 至 {p.ci_high_pp:.1f}；图 3a）。挽救的 {int(p.rescued_window_only_failures)} 个情景原先均仅因窗口峰值减负不足而失败，没有新增情景超过错过期限比例标准。同样的约束用于贪心提议策略也达到 294/300，说明收益并非 MPC 特有。但更严格恢复仍有服务代价：在八小时间隔的开发比较中，全额请求的期限失败从 7/100 增至 33/100（补充图 3；补充表 11）。')
    add('M027','M027_choices',
      f'To identify usable programmes, we selected capacities on 100 development scenarios before testing them on the new confirmation set. The controller with per-call recovery qualified full four-hour offers with eight-hour gaps and 75% eight-hour offers with gaps of eight, twelve or sixteen hours in all five workload configurations ({new_success_min}–{new_success_max}/300 successes; Supplementary Table 10). At 10% eligibility, these choices provide {k4:.2f} and {k8:.2f} kW, respectively (Fig. 3c). The original controller selected an eight-hour candidate only at the sixteen-hour gap. These are qualified points on the tested grid, not maximum capacities or evidence that every programme needs a 25% reduction. Changing the gap also changes subsequent clock times.',
      f'为识别可用的调用安排，我们先在 100 个开发情景上选择容量，再用新的确认集检验。逐次保留恢复约束的控制器，在全部五档工作配置中均支持四小时调用、八小时间隔的全额承诺，以及八小时调用、八/十二/十六小时间隔的 75% 承诺（整组成功次数 {new_success_min}–{new_success_max}/300；补充表 10）。在 10% 工作资格下，对应承诺分别为 {k4:.2f} 和 {k8:.2f} kW（图 3c）。原控制器仅在十六小时间隔下选出了八小时候选。这些是所测网格中通过检验的选择，并非最大容量，也不说明所有调用安排都必须降额 25%。改变间隔也会改变后续调用的钟点。')
    choice=after['M027'][0]
    choice['en']=choice['en'].replace('The original controller selected', 'The full eight-hour request also passed the prespecified confirmation comparison, but had failed development selection; it was not promoted retrospectively. The original controller selected')
    choice['zh']=choice['zh'].replace('原控制器仅在', '八小时全额请求也通过了预设确认比较，但它此前未通过开发选值，因此没有被事后提升为选定承诺。原控制器仅在')
    edit('M043_series',
      f'The selected repeated offers connect recovery requirements to participation costs (Fig. 6c). At 10% eligibility, the full {k4:.2f}-kW four-hour programme requires US${f10costs.loc["H4G8"].payment_usd_kw_year:.0f} per offered accounting kW-year; the qualified {k8:.2f}-kW eight-hour programmes require US${f10costs.loc[["H8G8","H8G12","H8G16"]].payment_usd_kw_year.min():.0f}–{f10costs.loc[["H8G8","H8G12","H8G16"]].payment_usd_kw_year.max():.0f} under the same reference prices. All use twelve independent four-call series per year. Longer service and a smaller offer increase the required payment through waiting exposure and fixed-cost allocation. Complete ledgers count every hour once and retain failed trajectories. Non-performance penalties remain unpriced, and independent series do not represent a continuously operating year.',
      f'选出的重复承诺将恢复要求与参与成本联系起来（图 6c）。在 10% 工作资格下，四小时全额 {k4:.2f} kW 调用安排需要每个报价核算千瓦每年 {f10costs.loc["H4G8"].payment_usd_kw_year:.0f} 美元；在相同参考价格下，通过检验的八小时 {k8:.2f} kW 安排需要 {f10costs.loc[["H8G8","H8G12","H8G16"]].payment_usd_kw_year.min():.0f}–{f10costs.loc[["H8G8","H8G12","H8G16"]].payment_usd_kw_year.max():.0f} 美元。各安排均按每年十二组相互独立、每组四次调用核算。更长服务和较小承诺通过等待暴露及固定成本分摊提高所需补偿。完整账本对每小时只计一次，并保留失败轨迹。合同违约罚款仍未定价，独立序列也不等于连续运行的一整年。')
    edit('M047',
      'Repeated operation makes recovery policy part of the commitment. The intervention separates two causes that an aggregate failure rate would obscure: incomplete enforcement of overlapping electrical obligations and deadline pressure under tighter recovery control. Correcting the first is an implementation repair, not a new physical limit. Independent selection and confirmation then establish feasible operating choices rather than attributing every failure to compute debt. This complements trace-based estimates of eligible and dependable workload power,<sup>41</sup> by following causal execution, service failures and accounting through a specified multi-call programme. The tested 75% candidates do not establish a universal derating rule, and the model does not prove optimality.',
      '重复运行使恢复策略成为承诺的一部分。干预区分了总失败率会掩盖的两种原因：重叠电力义务没有被完整执行，以及更严格恢复控制下的作业期限压力。纠正前者是实现修正，并非发现了新的物理极限。随后通过独立选值和确认建立可行运行选择，而不是将所有失败都归因于计算债务。这通过追踪特定多次调用安排中的因果执行、服务失败和完整账目，补充了基于轨迹估计合资格工作功率及可靠功率的研究。<sup>41</sup> 所测 75% 候选不构成普适降额规则，模型也没有证明最优性。')
    edit('M051',
      'These numerical results remain conditional model evidence. Requested GPU-hours from one production infrastructure are not energy measurements or an industry workload census. Deferral permission and deadlines were assumed; hourly divisible jobs, constant rigid demand and a small board-power calibration do not reproduce online latency, checkpoint overhead or facility response. The 40% and 60% cases add unverified participation and business-composition assumptions. Recovery interventions were developed after inspecting earlier failures and then tested on fresh scenarios. The four-call programmes span only four declared schedules; annual costs sample independent series rather than a continuous year. Actual GPU procurement, ageing and contractual failure penalties require operator data. These limitations constrain numerical transfer while leaving the comparisons reproducible.',
      '这些数值结果仍是以模型假设为条件的证据。单一生产设施中的请求 GPU 小时并非实测电能，也不代表行业工作构成普查。延期权限和期限由情景设定；按小时可分割的作业、恒定刚性需求与小规模板卡功率标定不能复现在线时延、检查点开销或设施响应。40% 和 60% 情景增加了未经验证的参与和业务构成假设。恢复干预是在检查既有失败后开发的，随后才在新情景上检验。四次调用仅覆盖四种明确安排；年度成本抽样独立序列，并非连续全年运行。实际 GPU 采购、老化和合同违约罚款需要运营者数据。这些限制约束了数值外推，但各项比较仍可复现。')
    add('M058','M058_recovery',
      'The recovery-mechanism extension reused development seeds 930000–930099 after examining the preceding results; its design is therefore an informed follow-up. Controller, criteria and candidate grid were frozen before 300 new confirmation seeds (970000–970299) were run. Selection was then frozen before controlled confirmation. The extension contains 10,100 development and 13,800 confirmation replays across five workload configurations. These runs share scenario seeds across methods and requests; they do not increase the number of independent samples per condition.',
      '恢复机制扩展是在检查前述结果后，复用开发种子 930000–930099 开展的，因此属于已有证据指导的后续研究。控制器、标准和候选网格在运行 300 个新确认种子（970000–970299）前冻结；选值结果又在受控确认运行前冻结。扩展包含五档工作配置下的 10,100 次开发回放与 13,800 次确认回放。不同方法和请求共享情景种子，这些回放不会增加每种条件的独立样本数。')
    add('M081_r2','M081_mechanism',
      'The mechanism extension compared the unchanged controller with a wrapper preserving a separate ceiling for every currently observed event-and-recovery window. The wrapper learned calls from current observations and retained only elapsed baseline peaks; it did not inspect future calls or arrivals. It clipped the same MPC action to the strictest live ceiling and retained feasible-side rounding. A greedy full-allocation proposal under the same wrapper provided a diagnostic at 10% eligibility. Four-call programmes used (H,G) = (4,8), (8,8), (8,12) and (8,16) hours. Every final 24-h recovery ended within the 168-h arrival period. Four-hour development tested the original request; eight-hour development tested 50%, 75% and 100%. The largest candidate passing the one-sided Wilson lower-bound threshold of 0.95 was selected. Confirmation tested that candidate, or the prespecified full-request comparator when none qualified. Full-request comparisons for both MPC versions at (8,12), and the greedy diagnostic, were retained regardless of selection. Confirmation never selected a replacement.',
      '机制扩展将未改变的原控制器与一个控制包装器比较；后者为当前已观察到的每个事件及恢复窗口分别保留功率上限。包装器通过当前观测获知调用，只保存已经发生的基准峰值，不读取未来调用或未来到达。它将同一个 MPC 动作限制在所有存续窗口中最严格的上限内，并保留向可行侧舍入。在 10% 工作资格下，另将同一包装器用于始终提议全额分配的贪心策略，作为诊断。四次调用采用 (H,G) = (4,8)、(8,8)、(8,12) 和 (8,16) 小时。各安排最后一次调用的完整 24 小时恢复均在 168 小时到达期内结束。四小时开发检验原请求，八小时开发检验原请求的 50%、75% 和 100%，选择单侧 Wilson 下界达到 0.95 的最大候选。确认检验该候选；若没有候选合格，则检验预先声明的全额请求比较方案。两种 MPC 在 (8,12) 安排下的全额比较及贪心诊断不论选值结果如何均予保留。确认集不用于挑选替代承诺。')
    add('M097','M097_recovery',
      'The new controller comparison paired complete four-call scenario seeds. Its primary contrast was the full request at 10% eligibility with eight-hour calls and twelve-hour gaps. Paired bootstrap intervals used 10,000 whole-seed resamples; exact McNemar tests were Holm-adjusted across all reported controller contrasts. Failure families were non-exclusive. Offer qualification remained pointwise; passing multiple conditions does not provide simultaneous 95% confidence. New repeated-cost screens used the same complete-series accounting and 2,000 annual draws, crossing waiting prices 0, 0.005 and 0.01, site costs US$10,000, 25,000 and 50,000 and displaced values US$0, 0.25 and 0.50 per deferred GPU-h.',
      '新控制器比较以完整四调用情景种子配对。主要比较为 10% 工作资格、八小时调用和十二小时间隔下的全额请求。配对 bootstrap 区间采用 10,000 次完整种子重采样；精确 McNemar 检验对全部报告的控制器比较进行 Holm 校正。各失败类别可以重叠。承诺资格仍按逐项标准检验，多项通过不意味着具有同时 95% 置信保证。新的重复调用成本分析使用相同的完整序列核算和 2,000 次年度抽样，将等待价格 0、0.005、0.01，固定场地成本 10,000、25,000、50,000 美元，以及每延后 GPU 小时 0、0.25、0.50 美元的被挤出工作价值交叉组合。')
    edit('M154','### Figure 3 | Recovery mechanism and independently tested repeated offers','### 图 3 | 恢复机制与独立检验的重复承诺')
    edit('M155',
      '**a,** Full single-event requests reused for four eight-hour calls with twelve-hour gaps. Points show original MPC and MPC with per-call recovery on 300 new paired complete scenarios per workload configuration; whiskers are one-sided 95% Wilson lower limits. **b,** The lowest development seed for which the original programme failed and per-call recovery passed at 10% eligibility (seed 930012). The zoom shows a recovery peak relative to the illustrated call’s event-and-recovery baseline peak. The dashed ceiling requires relief of half the request. This selected development example explains the mechanism and does not estimate its frequency. **c,** Development-selected offers at 10% eligibility, by call duration and gap; a cross would mark independent confirmation failure. None selected denotes the outcome of the tested grid, not zero physical capacity. All four calls must satisfy every unchanged electrical and service criterion. Full selections and failure counts are in Supplementary Tables 10 and 11.',
      '**a，** 将单次事件全额请求用于四次八小时调用、十二小时间隔。点表示各工作配置下原 MPC 与逐次保留恢复约束的 MPC 在 300 个新配对完整情景中的成功率；误差线为单侧 95% Wilson 下界。**b，** 10% 工作资格下，原安排失败而逐次恢复约束方案成功的最小开发种子（930012）。局部图将恢复峰值相对于所示调用的事件及恢复期基准峰值表示；虚线功率上限要求至少削减请求的一半。这个按规则选择的开发示例用于解释机制，不能估计出现频率。**c，** 10% 工作资格下，按调用时长和间隔列出开发选出的承诺；如独立确认失败，则标叉。“未选出”表示测试网格中的选值结果，不代表物理容量为零。四次调用均须满足全部未改变的电力和服务标准。完整选值和失败计数见补充表 10、11。')
    edit('M161',
      '**a,b,** Required annual capacity payment per offered accounting kilowatt for four- and eight-hour single events, with 50 independent calls per year. Existing slack, reserved headroom and an assumed US$0.25 per deferred GPU-h displaced-value exposure use the same physical ledger. **c,** Development-selected repeated offers for MPC with per-call recovery, at twelve independent four-call series per year. Shape and colour identify call duration and gap. Symbols denote passage of the independent pointwise confirmation criterion; crosses would denote failure. **d,** Delay-price sensitivity at 10% eligibility. All panels use 1-MW proportional accounting, one US$25,000 annual site charge and 2,000 common annual draws. Thresholds make the fifth percentile of annual net value non-negative. Complete trajectories, including failures, enter every price calculation. Contract-specific failure penalties are unpriced; series independence does not simulate a continuous year.',
      '**a,b，** 四小时和八小时单次事件每个报价核算千瓦所需的年度容量补偿，每年抽样 50 次独立调用。现有余量、预留容量以及假设每延后 GPU 小时 0.25 美元的被挤出价值暴露使用同一物理账本。**c，** 逐次保留恢复约束的 MPC 经开发选出的重复承诺，每年抽样十二组独立的四调用序列。形状和颜色表示时长与间隔。符号表示通过独立、逐项确认标准；如未通过则标叉。**d，** 10% 工作资格下的等待价格敏感性。所有面板采用 1 MW 比例核算、每年仅一次 25,000 美元场地费用和 2,000 次共同年度抽样。门槛使年度净值第五百分位不低于零。每次定价均使用包括失败在内的完整轨迹。合同特定违约罚款未定价，独立序列不等于连续全年模拟。')
    # Supplement: replace stale global statements and retain the older matched-fresh evidence.
    edit('S20_005',
      'The six notes follow the main results. Methods describe the five workload configurations and the subsequent recovery intervention; twelve tables provide their numerical evidence. Tables 5 and 7 retain the original controller’s matched-fresh comparison and accounts, whereas Tables 10–12 report the new selection, independent confirmation, mechanism contrasts and costs. All input scenarios, trial outcomes, complete hourly trajectories, controller-window audits and ready-to-plot summaries accompany Source Data.',
      '六条说明对应正文结果。方法描述五档工作配置及随后开展的恢复干预；十二张表给出数值证据。表 5、7 保留原控制器的配对独立调用比较与账目；表 10–12 报告新的选值、独立确认、机制比较和成本。源数据包含全部输入情景、逐次结果、完整小时轨迹、控制器窗口审计和现成绘图汇总。')
    add('S20_013','S21_note3',
      'The follow-up distinguishes electrical non-compliance from computing loss. The original observation selected the active window with the smallest achieved peak-relief fraction. That ranking need not select the smallest allowable power ceiling, so clipping only against its ceiling can violate another overlapping window. Keeping a ceiling for each observed call repairs this omission. The same-request paired comparison isolates this change within the MPC implementation; the greedy diagnostic asks whether the gain requires the MPC proposal. Stronger electrical guards can withhold capacity from urgent jobs, so deadline failures are reported separately. Qualified revised offers, rather than failure counts alone, provide the operational result.',
      '后续研究区分电力不合格与计算损失。原观测选择已实现峰值减负比例最小的存续窗口，但按此排序不一定找到最低的允许功率上限，因此仅按所选窗口限功率可能违反另一个重叠窗口。为每次已观察到的调用保留上限能够纠正这个遗漏。同请求配对比较在 MPC 实现内部识别这一改变；贪心诊断则检查收益是否依赖 MPC 提议动作。更强的电力约束可能减少紧急作业可用的计算容量，因此期限失败单独报告。运行结论来自通过检验的新承诺，而不仅是失败计数。')
    add('S20_043','S21_recovery_methods',
      'For the follow-up, H and G were (4,8), (8,8), (8,12) and (8,16) h, with the same first start at hour 63. After a later call ends, the preceding 24-h recovery remains active for max(0, 24 − H − G) h. This overlap is zero for H = 8 h and G = 16 h, although changing G also changes the clock alignment of later calls. Final recovery ends no later than hour 167, before arrivals stop at hour 168. Every replay then retains the full 216-h horizon, including the clearance tail. No gap comparison isolates spacing from time-of-day effects.',
      '后续研究采用 (H,G) = (4,8)、(8,8)、(8,12) 和 (8,16) 小时，首次调用仍从第 63 小时开始。后一次调用结束后，前一次的 24 小时恢复仍持续 max(0, 24 − H − G) 小时；当 H = 8、G = 16 小时时，这段重叠为零。不过改变 G 也会改变后续调用的钟点。最终恢复最晚在第 167 小时结束，早于第 168 小时到达停止。每次回放仍保留完整 216 小时时域，包括清空尾段。间隔比较并未将间隔本身与时刻效应分离。')
    add('S20_043','S21_recovery_guard',
      'For an observed call j, let B_j(t) be the greatest baseline PCC power observed so far in its event-and-recovery window, and R_j its request. The wrapper constrains the current proposal by every live ceiling B_j(t) − 0.5R_j. It also preserves the active-event delivery ceiling and the rebound ceiling baseline(t) + 0.25 × 0.95R_j during recovery. With fixed PCC demand F(t) and flexible full-allocation contribution A(t), the additional allocation cap is clip[(min_j(B_j(t) − 0.5R_j) − F(t))/A(t), 0, 1]. Actions are rounded towards the feasible side. The controller learns a call’s remaining duration only from the current observation and expires it after its 24-h recovery. Running baseline peaks can be lower than their eventual values, making this causal guard conservative. A target below F(t) cannot be made feasible by clipping, and electrical clipping alone does not guarantee job deadlines.',
      '对于已观察到的调用 j，以 B_j(t) 表示其事件及恢复窗口内截至当前已观察到的最大基准 PCC 功率，R_j 表示请求。包装器对当前提议动作同时施加所有存续上限 B_j(t) − 0.5R_j，并保留事件交付上限，以及恢复期间的反弹上限 baseline(t) + 0.25 × 0.95R_j。若固定 PCC 需求为 F(t)，灵活工作全额分配时的功率贡献为 A(t)，则新增分配上限为 clip[(min_j(B_j(t) − 0.5R_j) − F(t))/A(t), 0, 1]。动作向可行侧舍入。控制器仅通过当前观测获知调用的剩余时长，并在 24 小时恢复结束后删除该调用。运行中的基准峰值可能低于最终峰值，使这一因果约束偏保守。若目标低于 F(t)，限幅不能使其可行；电力限幅本身也不保证作业期限。')
    add('S20_043','S21_recovery_design',
      'The extension reused 100 previously examined development seeds (930000–930099); four of these also informed an exploratory pilot. The frozen protocol then enumerated 10,100 development replays: five workload configurations, two MPC versions, four programmes, a full-only four-hour candidate and 50%, 75% and 100% eight-hour candidates, plus 100 full-request greedy diagnostics at 10% eligibility and (8,12). The largest candidate with one-sided 95% Wilson lower bound at least 0.95 was selected. The frozen selection scheduled 13,800 replays on 300 new confirmation seeds (970000–970299). For each configuration, method and programme, confirmation tested the selected offer or the full-request comparator if none was selected. Full-request comparisons for both MPC versions at (8,12) and the greedy diagnostic were additionally retained. No confirmation result was pooled with the earlier 960000–960299 set or used for reselection. Every full series, including all failures, was analysed.',
      '扩展复用了 100 个已检查过的开发种子（930000–930099），其中四个还用于探索性试跑。随后冻结的协议列出了 10,100 次开发回放：五档工作配置、两种 MPC、四种调用安排，四小时仅检验全额候选，八小时检验 50%、75%、100% 候选，另加 10% 工作资格、(8,12) 安排下的 100 次全额贪心诊断。选择单侧 95% Wilson 下界至少为 0.95 的最大候选。冻结选值安排了 300 个新确认种子（970000–970299）上的 13,800 次回放。每个配置、方法和安排确认所选承诺；若未选出候选则确认全额比较方案。另外保留两种 MPC 在 (8,12) 下的全额比较和贪心诊断。确认结果不与此前 960000–960299 集合合并，也不用于重新选值。包括全部失败在内的每条完整序列均纳入分析。')
    add('S20_043','S21_recovery_stats',
      'The primary intervention contrast is the full-request original versus per-call-recovery MPC at 10% eligibility and (8,12). Paired success differences use 10,000 resamples of complete seeds; exact McNemar tests receive Holm correction across all controller contrasts reported in the source table. Non-exclusive failure families and paired rescue/loss counts are also retained. Qualification is pointwise for each frozen candidate. A selected candidate that fails confirmation would remain failed, with no test-set replacement. The illustrated trace is the lowest development seed for which the full-request original fails and the revised MPC passes; this transparent illustrative selection is separate from inference on all confirmation seeds.',
      '主要干预比较为 10% 工作资格、(8,12) 安排下的全额原 MPC 与逐次恢复约束 MPC。配对成功率差异采用 10,000 次完整种子重采样；精确 McNemar 检验在源表报告的全部控制器比较中进行 Holm 校正。同时保留可以重叠的失败类别，以及配对挽救和损失计数。每个冻结候选分别进行资格检验；若确认失败，则保留失败结论，不从测试集中另选替代容量。示例轨迹按规则选择全额原方案失败而新 MPC 成功的最小开发种子。这种透明的说明性选择与使用全部确认种子的统计推断分开。')
    edit('S20_060','### Supplementary Figure 3 | Recovery control, unfinished work and offer qualification','### 补充图 3 | 恢复控制、未完成工作与承诺资格')
    edit('S20_062',
      '**a,b,** Excess queued GPU-hours and cumulative missed GPU-hours at the full request, 10% eligibility, eight-hour calls and twelve-hour gaps, for original MPC, MPC with per-call recovery and the greedy diagnostic with the same guards. Curves are means and bands descriptive 5th–95th scenario percentiles across all 300 new confirmation seeds, including failures; bands are not confidence intervals. Cumulative misses are summed within each trajectory before the percentiles are calculated. Event hours are shaded. **c,** Deadline and window-peak failure counts at the full request for all four programmes on 100 development seeds at 10% eligibility. Failure categories can overlap. **d,** Development-selected fractions for all five workload configurations, two MPC versions and four programmes. A tick denotes passage of independent confirmation; a cross would denote failure; a dash means no candidate passed development. Selected fractions are tested grid points, not maximum capacities.',
      '**a,b，** 全额请求、10% 工作资格、八小时调用和十二小时间隔下，原 MPC、逐次恢复约束 MPC 及使用同样约束的贪心诊断的超额排队 GPU 小时与累计错过期限 GPU 小时。曲线为全部 300 个新确认种子的均值，色带为描述性的第 5–95 情景百分位，包含失败情景，不能解读为置信区间。先在每条轨迹内累计错过期限工作，再计算百分位。阴影表示调用时段。**c，** 10% 工作资格、全额请求下，四种安排在 100 个开发种子中的期限失败和窗口峰值失败计数，失败类别可以重叠。**d，** 五档工作配置、两种 MPC 和四种安排中经开发选出的比例。勾号表示通过独立确认，叉号表示失败，横线表示没有候选通过开发。选出的比例是已测网格点，不是最大容量。')
    add('S20_076','S21_provenance',
      '| Recovery extension | Independent seeds per condition | Complete replays | Hourly rows |\n|---|---|---|---|\n| Development | 100 reused | 10,100 | 2,181,600 |\n| Independent confirmation | 300 new | 13,800 | 2,980,800 |\n| Total | Paired across conditions | 23,900 | 5,162,400 |',
      '| 恢复扩展 | 每条件独立种子 | 完整回放数 | 小时行数 |\n|---|---|---|---|\n| 开发 | 复用 100 个 | 10,100 | 2,181,600 |\n| 独立确认 | 新增 300 个 | 13,800 | 2,980,800 |\n| 合计 | 条件间配对 | 23,900 | 5,162,400 |')
    # Older tables are kept and explicitly scoped, never silently overwritten with new seeds.
    for id in ['S20_043','S20_077','S20_083','S20_089']:
        if id not in edits:
            source=json.loads((ROOT/'docs/chinese_reader/v14/supplement_aligned_blocks.json').read_text())['blocks']
            v=next(z for z in source if z['id']==id)
            edit(id,'For the original controller study (confirmation seeds 960000–960299): '+v['en'],
                    '对于原控制器研究（确认种子 960000–960299）：'+v['zh'])
    add('S20_052','S21_economics',
      'Recovery-extension costs use the same full-series ledger, twelve independent series per year and 2,000 common annual draws on the new confirmation set. All 300 series enter each calculation, irrespective of success. The crossed grid uses waiting prices 0, 0.005 and 0.01, annual site costs US$10,000, 25,000 and 50,000 and displaced values US$0, 0.25 and 0.50 per deferred GPU-h. Reserved-headroom costs retain the stated four-year reference assumptions. This extension does not rerun the original missed-work-price or reserve-life screens. Source tables identify development selection and independent qualification separately, so a low-cost failed comparator cannot be mistaken for an offerable choice.',
      '恢复扩展使用相同的完整序列账本，每年十二组独立序列，并在新确认集上进行 2,000 次共同年度抽样。每次计算都纳入全部 300 组序列，无论成功与否。交叉网格采用等待价格 0、0.005、0.01，年度场地成本 10,000、25,000、50,000 美元，以及每延后 GPU 小时 0、0.25、0.50 美元的被挤出价值。预留容量保留所述四年参考假设。本扩展未重新运行原有的错过期限工作价格或预留寿命分析。源表分别标明开发选值与独立资格，避免将价格低的失败比较方案误认为可报价选择。')
    # Compact supplementary decision tables, with the full grids available as source tables.
    names={'original':'Original','all_window_mpc':'Per-call MPC','all_window_greedy':'Per-call greedy'}
    def make_table(headers,rows):return '| '+' | '.join(headers)+' |\n|'+ '|'.join(['---']*len(headers))+'|\n'+'\n'.join('| '+' | '.join(map(str,r))+' |' for r in rows)
    t10=[]
    for s in selected.sort_values(['case','duration_h','gap_h','controller']).itertuples():
        rsel=None if pd.isna(s.selected_fraction) else row(s.case,s.program,s.controller,s.selected_fraction)
        t10.append([int(s.case[1:]),s.program[1:].replace('G','/'),names[s.controller],
            '—' if rsel is None else f'{s.selected_fraction:.0%}',
            '—' if rsel is None else f'{s.selected_capacity_kw:.2f}',
            '—' if rsel is None else f'{int(rsel.successes)}/300',
            '—' if rsel is None else f'{rsel.wilson_lower:.4f}',
            'Not selected' if rsel is None else ('Pass' if rsel.qualified else 'Fail')])
    t11=[]
    for s in contrasts[(contrasts.program=='H8G12')&(contrasts.fraction==1)].sort_values(['case','controller']).itertuples():
        z=row(s.case,s.program,s.controller,1)
        t11.append([int(s.case[1:]),names[s.controller],f'{s.original_successes}/{s.revised_successes}',
            f'{s.difference_pp:.1f} [{s.ci_low_pp:.1f}, {s.ci_high_pp:.1f}]',
            s.rescued_window_only_failures,s.new_deadline_failures,f'{s.holm_p_all_reported_contrasts:.3g}'])
    t12=[]
    for s in selected.dropna(subset=['selected_fraction']).sort_values(['case','duration_h','gap_h','controller']).itertuples():
        g=econ[(econ.case==s.case)&(econ.program==s.program)&(econ.controller==s.controller)&(econ.fraction==s.selected_fraction)].set_index('regime')
        z=row(s.case,s.program,s.controller,s.selected_fraction)
        t12.append([int(s.case[1:]),s.program[1:].replace('G','/'),names[s.controller],f'{s.selected_capacity_kw:.2f}',
            f'{g.loc["slack"].payment_usd_kw_year:.2f}',f'{g.loc["reserved_headroom"].payment_usd_kw_year:.2f}',
            f'{g.loc["displacement_0.25"].payment_usd_kw_year:.2f}','Pass' if z.qualified else 'Fail'])
    extra=[]
    def extra_row(id,en,zh):extra.append(dict(id=id,en=en,zh=zh))
    extra_row('S21_T10','### Supplementary Table 10 | Frozen repeated offers and new independent confirmation','### 补充表 10 | 冻结的重复承诺与新的独立确认')
    extra_row('S21_T10_data',make_table(['Eligibility (%)','H/G (h)','Controller','Selected fraction','kW','Successes','Wilson lower','Outcome'],t10),make_table(['工作资格 (%)','H/G (h)','控制器','选出比例','kW','成功次数','Wilson 下界','结果'],t10))
    extra_row('S21_T10_note',f'The 40 method–programme–workload configurations yielded 25 development selections; {qualified}/25 passed their new independent tests. Per-call MPC denotes MPC with a separate guard for every observed live recovery window. Each success requires all four calls to satisfy every criterion. Fractions are relative to the corresponding selected single-event offer. A dash means no qualifying development candidate, not zero capacity. Results use 100 development and 300 new confirmation seeds per condition; all bounds are pointwise.',f'40 个方法—调用安排—工作配置组合产生 25 个开发候选，其中 {qualified}/25 通过新的独立检验。Per-call MPC 表示为每个已观察到的存续恢复窗口分别保留约束的 MPC。每次成功要求四次调用均满足全部标准。比例相对于对应的单次事件承诺。横线表示未选出合格开发候选，不代表容量为零。每种条件使用 100 个开发种子和 300 个新确认种子；下界均为逐项结果。')
    extra_row('S21_T11','### Supplementary Table 11 | Paired recovery intervention at the full eight-hour request','### 补充表 11 | 八小时全额请求下的配对恢复干预')
    extra_row('S21_T11_data',make_table(['Eligibility (%)','Revised controller','Original/revised successes','Difference (pp), 95% interval','Window-only rescues','New deadline failures','Holm P'],t11),make_table(['工作资格 (%)','新控制器','原/新成功次数','差异 (百分点)，95% 区间','仅窗口失败被挽救数','新增期限失败数','Holm P'],t11))
    extra_row('S21_T11_note',f'All contrasts use the same full request, eight-hour calls, twelve-hour gaps and 300 paired new seeds. The primary contrast is 10% eligibility with per-call MPC. Intervals resample complete seeds 10,000 times; exact McNemar P values are adjusted across all {len(contrasts)} reported controller contrasts, including unchanged comparisons in Source Data. Window-only rescues require original failure confined to window peak relief and revised success on all criteria. New deadline failures identify seeds without an original deadline failure but with one under the revised controller. These counts are paired classifications, not independent samples or a complete decomposition of every gain and loss.',f'全部比较使用相同全额请求、八小时调用、十二小时间隔和 300 个新配对种子。主要比较为 10% 工作资格下的逐次恢复约束 MPC。区间采用 10,000 次完整种子重采样；精确 McNemar P 值在报告的全部 {len(contrasts)} 个控制器比较中校正，包括源数据中没有差异的比较。仅窗口失败被挽救数要求原方案仅因窗口峰值减负不足失败，而新方案全部标准通过。新增期限失败表示原方案没有期限失败而新控制器有期限失败的种子。这些计数是配对分类，不是独立样本，也不是所有收益与损失的完整互斥分解。')
    extra_row('S21_T12','### Supplementary Table 12 | Participation thresholds for development-selected repeated offers','### 补充表 12 | 开发选出的重复承诺的参与门槛')
    extra_row('S21_T12_data',make_table(['Eligibility (%)','H/G (h)','Controller','kW','Slack','Reserve','Displacement','Confirmation'],t12),make_table(['工作资格 (%)','H/G (h)','控制器','kW','现有余量','预留容量','挤出价值','确认'],t12))
    extra_row('S21_T12_note','Payments are US$ per offered accounting kW-year, at a proportional 1-MW operating peak, twelve independent four-call series per year, US$25,000 annual site cost and US$0.005/GPU-h/h waiting price. Displacement assumes US$0.25 per deferred GPU-h; reserve uses the stated reference capital assumptions. Each estimate uses every complete confirmation trajectory and 2,000 common annual draws. Source Data additionally retain prices for unselected or failed full-request comparators and the crossed price grid. No continuous-year guarantee or observed operator profitability is inferred.','补偿单位为每个报价核算千瓦每年美元，采用 1 MW 运行峰值比例核算、每年十二组独立四调用序列、25,000 美元年度场地成本和每 GPU 小时每小时 0.005 美元等待价格。被挤出价值假设为每延后 GPU 小时 0.25 美元；预留容量使用所述参考资本假设。每项估计均使用全部完整确认轨迹和 2,000 次共同年度抽样。源数据另保留未选出或失败的全额比较方案价格，以及交叉价格网格。这不代表连续全年保证或实测运营者盈利。')

    # Preserve the source snapshot once, then rebuild repeatably from it.
    before=HERE/'before/reader_v14';before.mkdir(parents=True,exist_ok=True)
    for stem in ['main','supplement']:
        target=before/f'{stem}_aligned_blocks.json'
        if not target.exists():shutil.copyfile(ROOT/f'docs/chinese_reader/v14/{stem}_aligned_blocks.json',target)
    READER.mkdir(parents=True,exist_ok=True);(READER/'sources').mkdir(exist_ok=True)
    report={};changed=[]
    for stem,filename in [('main','nature_communications_article.md'),('supplement','supplementary_information.md')]:
        original=json.loads((before/f'{stem}_aligned_blocks.json').read_text())
        assert original['source_sha256']==old.sha(HERE/'before/manuscript'/filename)
        rows=[]
        for b in original['blocks']:
            r=dict(b)
            if r['id'] in edits:r.update(edits[r['id']]);changed.append(dict(id=r['id'],old=b,new=r))
            for lang in ['en','zh']:r[lang]=r[lang].replace('docs/figures/workload_composition_v1/artwork/','docs/figures/repeat_mechanism_v1/artwork/')
            rows.append(r);rows.extend(after.get(r['id'],[]))
        if stem=='supplement':rows.extend(extra)
        else:
            reference_start=next(i for i,r in enumerate(rows) if r['en']=='## References')
            reference_end=next(i for i in range(reference_start+1,len(rows)) if rows[i]['en'].startswith('## '))
            ref='41. Li, M. Beyond Scalar Flexibility: From Eligible AI Workloads to Dependable Load Relief. Preprint at https://arxiv.org/abs/2609.05406 (2026).'
            rows.insert(reference_end,dict(id='M_ref41',en=ref,zh=ref));rows=old.renumber_references(rows)
        for r in rows:assert len(r['en'].split('\n\n'))==len(r['zh'].split('\n\n')),(r['id'],'alignment')
        assert len({r['id'] for r in rows})==len(rows)
        header='<!--\nWorking '+('manuscript' if stem=='main' else 'Supplementary Information')+', version 0.21, 2026-09-09.\nIndependent recovery-controller intervention, frozen repeated-offer selection and complete paired accounting.\nAuthor metadata remain pending.\n-->\n\n'
        text=header+'\n\n'.join(r['en'] for r in rows)+'\n';path=ROOT/'manuscript'/filename;path.write_text(text)
        (READER/'sources'/f'{stem}_original.md').write_text(text)
        note='本稿逐段对应正文与补充材料 v0.21（2026-09-09）。恢复控制扩展使用新的独立确认集；图 3、图 6 和补充图 3 已更新。\n\n'
        zh=[];both=[]
        for r in rows:
            en,cn=old.reader_format(r['en']),old.reader_format(r['zh']);zh.append(cn)
            both.extend([cn] if en.startswith(('![','$$')) else [f'<!-- {r["id"]} -->\n{en}',cn])
        (READER/f'{stem}_zh.md').write_text(note+'\n\n'.join(zh)+'\n')
        (READER/f'{stem}_bilingual.md').write_text(note+'\n\n'.join(both)+'\n')
        (READER/f'{stem}_aligned_blocks.json').write_text(json.dumps(dict(source_sha256=old.sha(path),blocks=rows),ensure_ascii=False,indent=2)+'\n')
        report[stem]=dict(blocks=len(rows),source_sha256=old.sha(path))
    assert set(edits)=={r['id'] for r in changed}
    (HERE/'text_changes.json').write_text(json.dumps(changed,ensure_ascii=False,indent=2)+'\n')
    (HERE/'reader_build.json').write_text(json.dumps(report,indent=2)+'\n')
    (READER/'README.md').write_text('# 中文阅读稿 v15\n\n对应正文与补充材料 v0.21。原始对照与新的恢复干预清楚分开，完整更新选值、独立确认、成本、方法、图注和十二张补充表。\n\n- [正文中文全文](main_zh.md)\n- [补充材料中文全文](supplement_zh.md)\n- [正文中英对照](main_bilingual.md)\n- [补充材料中英对照](supplement_bilingual.md)\n\n作者信息仍待确认。本轮没有启动子智能体。\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
