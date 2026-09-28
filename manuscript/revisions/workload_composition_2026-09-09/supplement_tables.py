"""Append all current supplementary figures and numerical tables without hand entry."""
from pathlib import Path
import json
import pandas as pd
from figure_legends import SUPPLEMENT
from build_supplement import SOURCE,CASES

def append(rows,p,table):
    def read(name):return pd.read_csv(SOURCE/name)
    def heading(n,en,zh):p(f'### Supplementary Table {n} | {en}',f'### 补充表 {n} | {zh}')
    def f(x,n=2):return f'{float(x):.{n}f}'
    p('## Supplementary Figures','## 补充图')
    for n,(en,zh,legend,zhlegend) in enumerate(SUPPLEMENT,1):
        p(f'### Supplementary Figure {n} | {en}',f'### 补充图 {n} | {zh}')
        path=f'../docs/figures/workload_composition_v1/artwork/AIDRBench_Supplementary_Figure_{n}.png'
        p(f'![Supplementary Figure {n}]({path})',f'![补充图 {n}]({path})')
        p(legend,zhlegend)
    p('## Supplementary Tables','## 补充表')
    heading(1,'Power coefficients and measurement scope','功率系数与测量范围')
    cal=read('calibration_class_summary.csv')
    table(['Input','Estimate','Evidence'],['输入','估计值','证据'],[
        ['Training active power',f(cal.iloc[0].estimate_w_per_gpu)+' W/GPU','2 independent fitting runs; 1 held out'],
        ['Offline inference active power',f(cal.iloc[1].estimate_w_per_gpu)+' W/GPU','2 independent fitting runs; 1 held out'],
        ['Idle power','13.935625 W/GPU','Existing calibration'],['Node overhead','300 W/node','Engineering assumption'],['PUE','1.2','Engineering assumption'],['Other rigid active power','300.022174 W/GPU','Proxy; controls at 150 and 225 W']],
        [['训练活动功率',f(cal.iloc[0].estimate_w_per_gpu)+' W/GPU','2 次独立拟合；1 次留出'],['离线推理活动功率',f(cal.iloc[1].estimate_w_per_gpu)+' W/GPU','2 次独立拟合；1 次留出'],['空闲功率','13.935625 W/GPU','既有校准'],['节点开销','300 W/节点','工程假设'],['PUE','1.2','工程假设'],['其他刚性活动功率','300.022174 W/GPU','代理；150、225 W 对照']])
    heading(2,'Five workload configurations','五档工作负载配置')
    defs=json.loads((SOURCE/'case_definitions.json').read_text());idx=read('scenario_index.csv')
    body=[]
    for c in defs:
        peak=idx[idx.case==c['name']].operating_peak_kw.iloc[0]
        body.append([f(c['fraction']*100,0),f(c['shares']['online_inference']*100),f(c['eligible_shares']['training']*100),f(c['eligible_shares']['offline_inference']*100),round(576*c['fraction']),f(peak)])
    table(['Eligible work (%)','Online work (%)','Eligible training (%)','Eligible offline (%)','Flexible GPUs','Operating peak (kW)'],['合格工作 (%)','在线工作 (%)','合格训练 (%)','合格离线 (%)','灵活 GPU 数','运行峰值 (kW)'],body)
    p('All workload percentages use total offered GPU-hours as denominator. Total work is 374.4 GPU-h/h and installed hardware is 576 GPUs. The 40% case expands batch permission; 60% changes business composition. Mean utilisation is approximately 65% in each primary pool; operating peak is a model coefficient, not an observed event peak.',
      '所有工作百分比均以总投入 GPU 小时为分母。总工作量为每小时 374.4 GPU 小时，硬件为 576 张 GPU。40% 扩大批处理授权，60% 改变业务构成。主体两池平均利用率均约 65%；运行峰值是模型系数，不是观察到的事件峰值。')
    heading(3,'Evidence partitions and execution provenance','证据划分与执行来源')
    receipt=json.loads((SOURCE/'export_receipt.json').read_text())
    table(['Analysis','Independent seeds','Runs or results'],['分析','独立种子','运行或结果数'],[
        ['Primary no-response gates','100 development + 300 confirmation',len(idx)],
        ['Single development','100',receipt['trial_counts']['single_dev']],['Single confirmation','300',receipt['trial_counts']['single_confirm']],
        ['Repeated development','100',receipt['trial_counts']['repeat_dev']],['Repeated confirmation','300',receipt['trial_counts']['repeat_confirm']],
        ['Fixed-request controls','300',receipt['trial_counts']['control_confirm']],['PI optima, including controls','100 per partition and configuration',2800],['Renewable comparisons, including controls','100',7200],['Full controller hourly rows','Repeated rows are dependent',receipt['full_hourly_rows']]])
    p('Development seeds are 930000–930099; confirmation seeds are 960000–960299. Repeat-duration runtime checks verify all four- and eight-hour calls. Earlier one-hour repeat diagnostics are excluded. Protocols, controller and runner hashes, scenario identities, all trial outcomes and hourly manifests accompany Source Data. No run count should replace the number of independent seeds in statistical inference.',
      '开发种子为 930000–930099，确认种子为 960000–960299。重复方案通过运行时检查核实所有四小时和八小时调用，更早的一小时重复诊断予以排除。源数据附协议、控制器及运行程序哈希、情景标识、全部试验结果与小时清单。统计推断不能用运行次数替代独立种子数。')
    heading(4,'Single-event planning bounds and independent qualification','单次规划下界与独立资格检验')
    pi=read('pi_boundaries.csv');single=read('single_confirm_summary.csv');body=[]
    for c in CASES:
        for h in [4,8]:
            bound=pi[(pi.case==c)&(pi.role=='confirmation')&(pi.duration_h==h)].iloc[0]
            s=single[(single.case==c)&(single.duration_h==h)&(single.notice_h==0)].iloc[0]
            body.append([int(c[1:]),h,f(bound.perfect_information_firm_capacity_kw),f(s.capacity_kw),f'{int(s.successes)}/300',f(s.wilson_lower,4),'Yes' if s.qualified else 'No'])
    table(['Eligibility (%)','Duration (h)','PI lower bound (kW)','Offer (kW)','Success','Wilson lower','Qualifies'],['资格 (%)','时长 (h)','PI 下界 (kW)','承诺 (kW)','成功','Wilson 下界','合格'],body)
    p('PI uses 100 confirmation scenarios; controller testing uses 300. Each offer was fixed on development data. Notice 0, 2 and 6 h is retained separately in Source Data, together with all paired binary outcomes and Holm-adjusted exact McNemar tests. Qualification is pointwise at 95% reliability and 95% one-sided confidence.',
      'PI 使用 100 个确认情景，控制器使用 300 个。各承诺在开发数据上固定。源数据分别保留 0、2、6 小时通知、全部配对二元结果及 Holm 校正的精确 McNemar 检验。资格是可靠性 95%、单侧置信度 95% 下的逐项结论。')
    heading(5,'Repeated programmes and matched fresh calls','重复方案及配对新事件')
    rep=read('repeat_paired_comparisons.csv');body=[]
    for c in CASES:
        for h in [4,8]:
            r=rep[(rep.case==c)&(rep.duration_h==h)].iloc[0]
            cap=f(r.selected_repeat_kw) if r.selected_repeat_kw>0 else 'None'
            body.append([int(c[1:]),f'{h}/{8 if h==4 else 12}',f'{int(r.fresh_joint_successes)}/{int(r.repeated_successes)}',f'{f(r.paired_success_difference_pp,1)} [{f(r.paired_difference_ci_low_pp,1)}, {f(r.paired_difference_ci_high_pp,1)}]',f(r.repeated_lower,4),cap])
    table(['Eligibility (%)','Call/gap (h)','Fresh/repeated successes','Repeated − fresh (pp), 95% interval','Original repeated lower','Development-selected kW'],['资格 (%)','调用/间隔 (h)','新事件/重复成功数','重复减新事件 (百分点)，95% 区间','原重复承诺下界','开发选出 kW'],body)
    p('Each success count is out of 300 complete programmes and requires all four calls to pass. The comparison reuses the Table 4 single-event offer. A selected repeated offer is the largest qualifying development-grid candidate; its separate confirmation lower bound determines qualification. None denotes no qualifying development candidate, not zero true capacity. All original four-hour repeated offers passed confirmation (300/300; lower 0.9911), whereas the eight-hour originals did not. None passed the separate development selection rule. Paired intervals resample complete seeds.',
      '各成功数分母均为 300 个完整方案，并要求四次全通过。比较复用表 4 的单次承诺。已选重复承诺是满足开发门槛的最大网格候选，其独立确认下界决定是否合格。None 表示开发无合格候选，不是实际容量为零。原四小时重复承诺均通过确认（300/300；下界 0.9911），八小时原承诺则未通过；另行开展的开发选值规则没有选中候选。配对区间按完整种子重采样。')
    heading(6,'PV hosting and fixed-PV utilisation','光伏承载与固定光伏利用率')
    pv=read('renewable_paired_comparisons.csv');body=[]
    for c in CASES:
        for b in [False,True]:
            g=pv[(pv.case==c)&(pv.bess_enabled==b)];host=g[g.analysis=='pv_hosting'].iloc[0];op=g[g.analysis=='fixed_pv_operation'].iloc[0]
            body.append([int(c[1:]),'Yes' if b else 'No',f(host.rigid_min),f(host.flexible_min),f(host.difference_of_all_scenario_minima),f'{f(op.mean_paired_gain,4)} [{f(op.gain_ci_low,4)}, {f(op.gain_ci_high,4)}]'])
    table(['Eligibility (%)','BESS','Rigid PV kW','Flexible PV kW','Boundary gain kW','Utilisation gain (pp), 95% interval'],['资格 (%)','储能','刚性光伏 kW','灵活光伏 kW','边界增量 kW','利用率增量 (百分点)，95% 区间'],body)
    p('Each hosting capacity is the minimum over all 100 confirmation scenarios at ≤5% curtailment. Utilisation uses a fixed 500-kW PV installation; means and pointwise paired bootstrap intervals are in percentage points. All current renewable solutions are retained and checked for zero deadline misses. The corresponding conditional mean hosting effects are separately available in Source Data.',
      '各承载容量为弃光 ≤5% 时全部 100 个确认情景的最小值。利用率采用固定 500 kW 光伏，均值及逐项配对自助区间以百分点计。保留全部当前可再生能源解，并核对截止时间损失为零。相应的条件平均承载效应另列于源数据。')
    heading(7,'Single-event and complete-programme participation screens','单次与完整方案参与筛选')
    econ=read('economic_primary.csv');body=[]
    for c in CASES:
        for h in [4,8]:
            g=econ[(econ.case==c)&(econ.duration_h==h)&(econ.kind=='single')].set_index('regime')
            r=econ[(econ.case==c)&(econ.duration_h==h)&(econ.kind=='repeated_original')&(econ.regime=='slack')].iloc[0]
            body.append([int(c[1:]),h,f(g.loc['slack'].risk_adjusted_capacity_payment_usd_kw_year),f(g.loc['reserved_headroom'].risk_adjusted_capacity_payment_usd_kw_year),f(g.loc['displacement_0.25'].risk_adjusted_capacity_payment_usd_kw_year),f(r.risk_adjusted_capacity_payment_usd_kw_year),'Yes' if r.qualified else 'No'])
    table(['Eligibility (%)','Call (h)','Single slack','Single reserve','Single displacement','Repeated original, slack','Repeated confirmation passes'],['资格 (%)','调用 (h)','单次空闲','单次预留','单次挤占','重复原承诺，空闲','重复确认通过'],body)
    p('All payments are US$ per offered accounting kW-year at a proportional 1-MW operating peak. Single events use 50 independent calls/year; repeated programmes use 12 independent four-call series/year. The site charge is US$25,000 once yearly. The displacement illustration assumes US$0.25 per deferred GPU-h. The repeated-pass column applies the confirmation Wilson criterion only; the separate development rule selected no repeated candidate. Conditional costs do not change either outcome. All price-grid rows and failed-trajectory service losses are retained in Source Data.',
      '所有补偿单位为每会计承诺 kW 每年的美元，按运行峰值比例缩放到 1 MW。单次为每年 50 个独立调用，重复为每年 12 个独立四调用序列，站点费每年只计一次 25,000 美元。挤占示例假设每推迟 GPU 小时 0.25 美元。重复通过列仅采用确认集 Wilson 标准，另行开展的开发规则没有选出重复候选。条件成本不改变这两项结果。全部价格网格及失败轨迹的服务损失均保留在源数据中。')
    heading(8,'Orthogonal allocation and rigid-power controls','正交分配与刚性功率对照')
    cb=read('control_pi_boundaries.csv');cs=read('control_causal_summary.csv');body=[]
    for c in ['f10_g20','f10_g30','f10_rigid150','f10_rigid225']:
        for h in [4,8]:
            b=cb[(cb.case==c)&(cb.duration_h==h)].iloc[0];s=cs[(cs.case==c)&(cs.duration_h==h)].iloc[0]
            price=econ[(econ.case==c)&(econ.duration_h==h)&(econ.regime=='slack')].iloc[0]
            body.append([c,h,f(b.perfect_information_firm_capacity_kw),f(s.capacity_kw),f'{int(s.successes)}/300',f(s.wilson_lower,4),f(price.risk_adjusted_capacity_payment_usd_kw_year)])
    table(['Control','Hours','PI lower kW','Fixed offer kW','Success','Wilson lower','Slack payment'],['对照','小时','PI 下界 kW','固定承诺 kW','成功','Wilson 下界','空闲补偿'],body)
    p('All controls retain 10% eligibility and the same work. g20/g30 change flexible GPU allocation to 20%/30%; rigid150/rigid225 change only unmeasured rigid-class active power to 150/225 W. Payment units and annual assumptions match Table 7. Full renewable and paired economic controls are provided in Source Data.',
      '全部对照保持 10% 资格和相同工作。g20/g30 将灵活 GPU 分配改为 20%/30%；rigid150/rigid225 仅把未测刚性类别活动功率改为 150/225 W。补偿单位及年度假设同表 7。完整可再生能源和配对经济对照见源数据。')
    heading(9,'Monetary assumptions and sensitivity ranges','货币假设与敏感性范围')
    table(['Input','Reference','Evaluated values'],['输入','参考值','检验值'],[
        ['Delay, US$/GPU-h/h','.005','0, .001, .005, .01'],['Fixed site, US$/year','25,000','10,000; 25,000; 50,000'],['Displaced value, US$/deferred GPU-h','.25','0, .25, .5, 1'],['Missed work, US$/GPU-h','0','0, .25, 1'],['Reserve economic life, years','4','3, 4, 5, 6'],['Electricity, US$/kWh','.10','Held fixed'],['Delivered energy, US$/MWh','50','Held fixed'],['Independent annual draws','2,000','Common draws at each price']])
    p('The main economic comparison uses the reference prices and reports the 95th percentile of net annual cost. Delay/site/displacement prices are crossed; missed-work prices are varied at the reference delay/site setting with no displacement charge; reserve life is varied separately. These are scenario inputs, not empirical distributions or a joint global uncertainty model. No actual GPU procurement price, ageing hazard or contract-specific failure tariff is inferred.',
      '主体经济比较采用参考价格，报告年度净成本第 95 百分位。延迟、站点和挤占价格交叉；未完成工作价格在参考延迟/站点设置且无挤占收费时变化；预留寿命另行变化。这些是情景输入，不是经验分布或联合全局不确定性模型，未据此推断真实 GPU 采购价、老化风险或合同特定违约价格。')
    return rows
