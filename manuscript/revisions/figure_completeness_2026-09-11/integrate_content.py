"""Synchronise v0.26 figure references, captions and aligned Chinese readers."""
import hashlib
import importlib.util
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
READER=ROOT/'docs/chinese_reader/v20'
spec=importlib.util.spec_from_file_location('reader_helpers',HERE.parent/'workload_composition_2026-09-09/integrate_content.py')
h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)

SUPPLEMENT = [
('S26_6_title','### Supplementary Figure 6 | Joint service and delivery across structural conditions','### 补充图 6 | 不同结构条件下的服务与交付联合结果'),
('S26_6_image','![Supplementary Figure 6](../docs/figures/figure_completeness_v1/artwork/AIDRBench_Supplementary_Figure_6.png)','![补充图 6](../docs/figures/figure_completeness_v1/artwork/AIDRBench_Supplementary_Figure_6.png)'),
('S26_6_caption',
'**a,b,** Joint successes with at most 1% missed work or zero missed work. **c,d,** Scenarios encountering instantaneous supply shortage or more than 1% missed work. Every cell contains 300 frozen confirmation scenarios at 10% eligibility and the same 5.898243-kW eight-hour stress request. Columns compare a fresh call at the matched final-call time with four-call series at 16- or 24-h start spacing. Rows vary offered utilisation, reference deadline-slack multiplier and flexible GPU allocation; each setting uses its own matched baseline. All no-response baselines pass service checks. Numerals give counts; blue or orange intensity increases from zero to 300. Failure categories overlap and do not sum to total failure. A fixed stress request is not a separately selected qualified offer for each row. Changing spacing also moves earlier call times and does not isolate an interval effect. Full outcomes and selected-offer results remain in Tables 14–15 and Source Data.',
'**a,b，** 允许至多 1% 漏期工作或要求零漏期时的联合成功数。**c,d，** 遇到即时供给不足或超过 1% 漏期工作的情景数。每格包含 300 个冻结确认情景，工作参与比例为 10%，采用相同的 5.898243 kW、八小时压力请求。列分别表示在匹配末次调用时刻的单次新调用，以及开始间隔为 16 h 或 24 h 的四调用序列。行改变供给利用率、参考期限松弛倍数和灵活 GPU 分配；每个设置使用自身匹配基线。所有无响应基线均通过服务检查。数字为计数，蓝色或橙色深浅随零至 300 递增。失败类别可重叠，不能相加为总失败数。固定压力请求不等于每行分别选定的合格报价。改变间隔也会移动前序调用时刻，因此不能单独识别间隔效应。完整结果和选定报价仍见表 14–15 与源数据。'),
('S26_7_title','### Supplementary Figure 7 | PV hosting and operation on their absolute scales','### 补充图 7 | 绝对尺度下的光伏接纳与运行'),
('S26_7_image','![Supplementary Figure 7](../docs/figures/figure_completeness_v1/artwork/AIDRBench_Supplementary_Figure_7.png)','![补充图 7](../docs/figures/figure_completeness_v1/artwork/AIDRBench_Supplementary_Figure_7.png)'),
('S26_7_caption',
'**a,b,** Absolute PV hosting capacities without and with BESS, for rigid and flexible schedules. Each point is the minimum over 100 scenarios. **c,d,** Arithmetic mean curtailed PV energy and grid imports per modelled horizon for a fixed 500-kW PV installation, over the same 100 paired scenarios. Blue and green identify no BESS and BESS; dashed circles and solid squares identify rigid and flexible operation. Grid-import curves nearly coincide at the displayed scale; no uncertainty or significance is inferred from their separation. These absolute outcomes complement the paired gains and bootstrap intervals in Supplementary Fig. 4a,b. Lines connect evaluated eligibility fractions only. The 40% and 60% cases retain the additional business assumptions marked in Fig. 1; configuration-dependent demand also changes across fractions, so within-case rigid–flexible comparisons isolate scheduling. All schedules use full information and zero missed work. Means and minima are descriptive summaries, not causal reliability certificates; small storage contrasts remain limited by optimisation precision. All scenario values are retained in Source Data.',
'**a,b，** 无储能和有储能时，刚性与灵活调度的绝对光伏接纳容量。每个点为 100 个情景中的最小值。**c,d，** 固定 500 kW 光伏系统在每个模型时域内的弃光电量与电网购电量，采用相同 100 个配对情景的算术均值。蓝色与绿色分别表示无储能和有储能；虚线圆点与实线方点分别表示刚性和灵活运行。购电曲线在所示尺度下几乎重合，不能根据其分离程度推断不确定性或显著性。这些绝对结果补充了补充图 4a,b 的配对增益与自助法区间。连线仅连接已计算的参与比例。40% 和 60% 情景保留图 1 标注的额外业务假设；不同配置的用电需求也随比例改变，因此应在同一配置内用刚性—灵活配对比较识别调度影响。所有调度使用完整未来信息并要求零漏期。均值与最小值是描述性汇总，不是因果可靠性证书；微小储能差异仍受优化精度限制。源数据保留所有情景数值。'),
('S26_8_title','### Supplementary Figure 8 | Hardware and service-cost assumptions for single events','### 补充图 8 | 单次事件的硬件与服务成本假设'),
('S26_8_image','![Supplementary Figure 8](../docs/figures/figure_completeness_v1/artwork/AIDRBench_Supplementary_Figure_8.png)','![补充图 8](../docs/figures/figure_completeness_v1/artwork/AIDRBench_Supplementary_Figure_8.png)'),
('S26_8_caption',
'**a,** Reserved-headroom cost with a hardware economic life of three to six years. **b–d,** Effective displaced-work value, waiting valuation and fixed site fee varied separately without an added reserve cost. All panels retain the 10% eligibility single-event four- and eight-hour offers of 5.898243 kW, supported by 295/300 and 292/300 joint successes under the 1% missed-work standard. Annual accounting draws 50 independent complete event-and-recovery ledgers with replacement, scales proportionally to 1 MW and retains failures. Unvaried prices are US$0.005/GPU-h/h waiting, US$25,000/year site fee, zero displaced-work value and zero missed-work price; electricity and delivered-energy prices follow Table 9. Points are 95th-percentile annual-net-cost thresholds, not confidence limits. Lines join evaluated values without added observations. Economic life affects assumed reserve amortisation, not measured hardware ageing or failure. These single-event scenarios must not be substituted for the independently qualified repeated products and twelve-series accounting in Fig. 6. Source Data also retain the missed-work-price check, which does not visibly change these single-event thresholds.',
'**a，** 硬件经济寿命为三至六年时的预留余量成本。**b–d，** 分别改变有效被替代工作价值、等待估值和固定场站费用，不另加预留成本。全部面板保持 10% 工作参与下四小时与八小时单次报价 5.898243 kW，在允许 1% 漏期的标准下分别由 295/300 和 292/300 联合成功支持。年度核算有放回抽取 50 条独立的完整事件—恢复账本，按比例缩放至 1 MW，并保留失败。未改变的价格为等待 0.005 美元/GPU-h/h、场站费用 25,000 美元/年、被替代工作价值为零、漏期工作价格为零；电价与交付电量价格见表 9。点为年度净成本的第 95 百分位门槛，不是置信界限。连线只连接已计算数值，不添加观测。经济寿命影响假定的预留成本摊销，不代表实测硬件老化或故障。这些单次事件情景不能替代图 6 的独立合格重复产品及十二序列年度核算。源数据还保留了漏期工作定价检查，其对这些单次门槛没有可见影响。')]


def main():
    READER.mkdir(parents=True,exist_ok=True);(READER/'sources').mkdir(exist_ok=True)
    changes=[]
    for stem,name in [('main','nature_communications_article.md'),('supplement','supplementary_information.md')]:
        before=json.loads((HERE/'before'/f'{stem}_aligned_blocks.json').read_text())
        assert before['source_sha256']==h.sha(HERE/'before'/name)
        rows=[]
        for old in before['blocks']:
            row=dict(old);i=row['id']
            if i=='M150':row.update(en='### Figure 1 | Workload composition and commitment assessment',zh='### 图 1 | 工作负载构成与承诺评估')
            if i=='M151':
                row['en']+=' **c,** Evidence-to-decision sequence, from event-hour supply and strict-window feasibility to independent causal qualification and pricing. A supply deficit rules out a successful series, but qualification retains all successes and failures when assessing a probabilistic contract. A feasible PI witness is not a deployable controller or a causal reliability certificate; an unresolved solve supplies no feasibility conclusion.'
                row['zh']+=' **c，** 从事件时段供给和严格时间窗可行性，到独立因果资格检验与定价的证据—决策流程。供给不足排除该序列成功的可能，但概率性合同资格评估仍保留全部成功与失败。可行 PI 见证不是可部署控制器，也不是因果可靠性证书；未解决的求解不提供可行性结论。'
            if i=='M156':row.update(en='### Figure 4 | Supply limits and the response–recovery trajectory',zh='### 图 4 | 供给限制与响应—恢复轨迹')
            if i=='M157':
                row['en']=row['en'].split(' **c,**')[0]+' **c,d,** Full 216-h power difference from the paired baseline and additional backlog at the independently qualified reference offers of 5.60 kW (four hours) and 4.42 kW (eight hours), both with four calls at 16-h start spacing. The example is the lowest common confirmation seed, 989000, chosen by identifier without inspecting outcomes. Solid lines show operation, dotted lines in c show requests, and the grey 168–216-h interval is the clearance tail. Negative power differences denote recovery above baseline; positive backlog denotes additional waiting work. Both illustrated series finish with zero missed work. These single trajectories explain operation; the 300-scenario qualification evidence is in Fig. 3a. Panels a,b use the external workload tests, whereas c,d use the reference distribution; they are not the same experiment.'
                row['zh']=row['zh'].split('**c，**')[0].rstrip()+' **c,d，** 在独立合格参考报价下，相对配对基线的完整 216 h 功率差与额外积压：四小时为 5.60 kW，八小时为 4.42 kW，均为开始间隔 16 h 的四调用序列。示例采用最低共同确认种子 989000，按编号选择，未查看结果后挑选。实线为运行，c 中点线为请求，灰色 168–216 h 区域为清空尾段。负功率差表示恢复阶段功率高于基线；正积压表示额外等待工作。两个示例序列均以零漏期结束。单条轨迹用于解释运行；300 个情景的资格证据见图 3a。a,b 使用外部工作负载测试，c,d 使用参考分布，二者不是同一试验。'
            if i=='M025_decision':
                row['en']=row['en'].replace('Fig. 4c','Fig. 1c')
                row['zh']=row['zh'].replace('图 4c','图 1c')
            if stem=='main' and row['en'].startswith('Strict task-window feasibility'):
                row['en']+=' The broader structural confirmation separates joint success from overlapping supply and deadline failures (Supplementary Fig. 6).'
                row['zh']+=' 更广泛的结构确认将联合成功与可重叠的供给、期限失败分开报告（补充图 6）。'
            if stem=='main' and 'Hosting and utilisation therefore measure' in row['en']:
                row['en']=row['en'].replace('Hosting and utilisation therefore measure different benefits.','Hosting and utilisation therefore measure different benefits; absolute hosting, curtailment and grid imports are shown in Supplementary Fig. 7.')
                row['zh']=row['zh'].replace('接纳与利用率因此衡量不同收益。','接纳与利用率因此衡量不同收益；绝对接纳容量、弃光与电网购电见补充图 7。')
                if '补充图 7' not in row['zh']:row['zh']+=' 绝对接纳容量、弃光与电网购电见补充图 7。'
            if stem=='main' and 'Waiting and missed-work valuations are varied explicitly;' in row['en']:
                row['en']=row['en'].replace('Waiting and missed-work valuations are varied explicitly;','Waiting and missed-work valuations are varied explicitly, with single-event hardware and monetary sensitivity in Supplementary Fig. 8;')
                row['zh']+=' 单次事件的硬件与货币敏感性见补充图 8。'
            if i=='S20_006':
                row['en']=row['en'].replace('Fig. 3a; Supplementary Fig. 3a,b','Fig. 3a; Fig. 4c,d; Supplementary Fig. 3a,b').replace('Supplementary Fig. 3c; Tables','Supplementary Figs. 3c, 6; Tables').replace('Supplementary Fig. 4; Tables','Supplementary Figs. 4, 7; Tables').replace('Tables 7, 9, 12, 17;','Supplementary Fig. 8; Tables 7, 9, 12, 17;')
                row['zh']=row['zh'].replace('图 3a；补充图 3a,b','图 3a；图 4c,d；补充图 3a,b').replace('补充图 3c；表','补充图 3c、6；表').replace('补充图 4；表','补充图 4、7；表').replace('表 7、9、12、17；','补充图 8；表 7、9、12、17；')
            for lang in ['en','zh']:
                row[lang]=row[lang].replace('docs/figures/commitment_narrative_v1/artwork/','docs/figures/figure_completeness_v1/artwork/')
            if i=='S20_069':rows.extend(dict(id=i,en=en,zh=zh) for i,en,zh in SUPPLEMENT)
            rows.append(row)
            if i=='M025_decision':rows.append(dict(id='M26_operation',en='At the qualified reference offers, the full response–recovery trajectory illustrates why an event cannot be assessed in isolation: deferred work accumulates during the calls and is processed afterwards (Fig. 4c,d). This seed-selected example complements, rather than replaces, the independent qualification counts.',zh='在合格参考报价下，完整的响应—恢复轨迹说明为什么不能孤立评价事件：调用期间累积的延期工作，需要在之后处理（图 4c,d）。这一按种子编号选定的示例补充了独立资格计数，不能代替后者。'))
            if row!=old:changes.append(dict(id=i,before=old,after=row))
        head=f'<!--\nWorking {stem}, version 0.26, 2026-09-11.\nFigure completeness and operating evidence; no new simulations or offer reselection.\nAuthor metadata remain pending.\n-->\n\n'
        doc=head+'\n\n'.join(r['en'] for r in rows)+'\n'
        target=ROOT/'manuscript'/name;target.write_text(doc)
        (READER/'sources'/f'{stem}_original.md').write_text(doc)
        cn=[];both=[]
        for row in rows:
            en,zh=h.reader_format(row['en']),h.reader_format(row['zh']);cn.append(zh)
            both.extend([zh] if en.startswith(('![','$$')) else [f'<!-- {row["id"]} -->\n{en}',zh])
        note='本稿逐段对应英文正文与补充材料 v0.26（2026-09-11）。补回当前设定下的运行与敏感性图形；未新增模拟或重新选择报价。\n\n'
        for suffix,parts in [('zh',cn),('bilingual',both)]:
            (READER/f'{stem}_{suffix}.md').write_text(note+'\n\n'.join(parts)+'\n')
        (READER/f'{stem}_aligned_blocks.json').write_text(json.dumps(dict(source_sha256=h.sha(target),blocks=rows),ensure_ascii=False,indent=2)+'\n')
    (HERE/'text_changes.json').write_text(json.dumps(changes,ensure_ascii=False,indent=2)+'\n')
    (READER/'README.md').write_text('# 中文阅读稿 v20\n\n对应英文 v0.26：六张主图、八张补充图。\n\n- [正文中文](main_zh.md)\n- [补充材料中文](supplement_zh.md)\n- [正文中英对照](main_bilingual.md)\n- [补充中英对照](supplement_bilingual.md)\n')
    print('Updated EN v0.26 and Chinese v20; preserved v0.25 snapshots.')


if __name__=='__main__':main()
