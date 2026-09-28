"""Point working readers and figure previews at the evidence-centred version."""
import re
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
ART=ROOT/'docs/figures/commitment_narrative_v1/artwork'
PACKAGE=ROOT/'results/exports/AIDRBench_All_Figures_2026-09-10_v14.zip'

def main():
    for name,prefix,count,filename in [('nature_communications_article.md','Figure',6,'nature-mainline-figure-preview.md'),('supplementary_information.md','Supplementary Figure',5,'nature-supplementary-figure-preview.md')]:
        text=(ROOT/'manuscript'/name).read_text();parts=[f'# 当前 v0.25：{prefix}\n\n采用当前正文图注；六主图、五补充图。全部数据和重绘入口见完整 v14 包。']
        for n in range(1,count+1):
            m=re.search(rf'^### {prefix} {n} \| .*?(?=^### |^## |\Z)',text,re.M|re.S);assert m
            image_name='AIDRBench_'+prefix.replace(' ','_')+'_'+str(n)+'.png'
            parts.append(m[0].strip()+f'\n\n![{prefix} {n}]({ART/image_name})')
        (ROOT/'docs'/filename).write_text('\n\n'.join(parts)+'\n')
    readme=ROOT/'README.md';text=readme.read_text();history=text[text.index('## 历史研究设计与开发记录'):]
    readme.write_text('''# AIDRBench：工作负载表征与可靠响应承诺

当前英文正文与补充材料 **v0.25**，中文逐段稿 **v19**，完整绘图恢复包 **v14**。

- [正文中文](docs/chinese_reader/v19/main_zh.md) · [补充材料中文](docs/chinese_reader/v19/supplement_zh.md)
- [正文 PDF](manuscript/exports/AIDRBench_Nature_Communications_v0.25_content_revision.pdf) · [补充 PDF](manuscript/exports/AIDRBench_Nature_Communications_v0.25_Supplementary_Information_content_revision.pdf)
- [六张主图](docs/nature-mainline-figure-preview.md) · [五张补充图](docs/nature-supplementary-figure-preview.md)
- [完整绘图与恢复包](results/exports/AIDRBench_All_Figures_2026-09-10_v14.zip) · [修改理由与证据分配](manuscript/revisions/commitment_narrative_2026-09-10/RESULTS_AND_REASONS_ZH.md)
- [权威文件与恢复入口](MAINLINE_FILES.md)

本版使用既有冻结实验，不新增模拟，不重新选择报价。图 3c 纳入次数/任务资源时间 × 原序/小时置乱的配对对照；2.95 kW 请求的资源时间成功数从原序 31/80 变为置乱后 55/80（1% 标准）或 54/80（零漏期标准），次数权重在两种顺序均为 80/80。置乱改变顺序及其与调用、社区负荷的对齐，不能全部解释为自相关效应。

图 4 展示即时供给余量与承诺判断：先识别不可能成功的序列，再区分严格时间窗不可行和因果控制差距；固定因果报价通过独立资格检验后，才比较运行成本与不参与。一次序列失败不自动否定概率性合同。原主图 PV 结果移至 S4，旧交叉评分移至 S3d，历史解释集中在补充说明 7。

参考四/八小时报价仍为 5.60/4.42 kW；两种服务标准选值相同，零漏期确认 297/300、296/300。早期 PI 统一表述为放松规划统计量，不保证逐工作组可行。英文 SI 标题与正文一致。完整数据、原协议、历史文稿和复算能力保留。

没有启动子智能体；作者、基金、许可证与公开归档仍待用户决定。

'''+history)
    mainline=ROOT/'MAINLINE_FILES.md';old=mainline.read_text()
    if '## Current v0.25' not in old:
        mainline.write_text('''# AIDRBench formal mainline

## Current v0.25, 2026-09-10

- English main and SI: `manuscript/nature_communications_article.md`, `manuscript/supplementary_information.md`; identical paper title.
- Chinese: `docs/chinese_reader/v19/`, paragraph-aligned to v0.25.
- PDFs: v0.25 content_revision files in `manuscript/exports/`; six main and five supplementary figures, 21 numbered tables.
- Current artwork: `docs/figures/commitment_narrative_v1/artwork/`.
- Ready tables for reorganised F3/F4/S3/S4: `manuscript/source_data/nature_commitment_narrative_v1/`; no new simulations or selections.
- Complete handoff: `results/exports/AIDRBench_All_Figures_2026-09-10_v14.zip`; `RUN_ALL_FIGURES.py` redraws all eleven from tables.
- Revision, evidence allocation and verification: `manuscript/revisions/commitment_narrative_2026-09-10/`.

F3c foregrounds the crossed weight/order comparison. F4 shows paired supply margins, a prespecified trace example and the decision sequence. PV is in S4; the older 63/80 cross-score panel is S3d. Historical selection and PI corrections are consolidated in Supplementary Note 7. Old data, code and protocols remain frozen. The v14 package retains the complete v0.24 recovery data and portable replay entry points.

Interpretation: permutation changes order and alignment jointly; zero misses define a successful series, while qualification targets 95% overall success. A supply deficit rules out a successful affected series, not automatically a probabilistic offer. Strict PI feasibility is distinct from causal qualification and from economic participation.

Do not spawn subagents unless the user explicitly asks. Local Python drawing remains authorised. Author metadata, licence and public archive are not to be filled without user information.

## Archived v0.24 handoff and older records

The following paths describe earlier frozen versions, not the current reading copy.

'''+old.removeprefix('# AIDRBench formal mainline\n\n').replace('## Current v0.24, 2026-09-10','### v0.24, 2026-09-10',1))
    for rel in ['docs/chinese_reader/README.md','docs/paper-packaging.md','docs/all_figure_handoff/README_FIRST.md','docs/figure_recovery/README.md']:
        p=ROOT/rel;old=p.read_text()
        if not old.startswith('# 当前 v0.25'):
            p.write_text(f'# 当前 v0.25 / 中文 v19 / 绘图包 v14\n\n[正文中文]({ROOT/"docs/chinese_reader/v19/main_zh.md"}) · [补充中文]({ROOT/"docs/chinese_reader/v19/supplement_zh.md"}) · [完整绘图恢复包]({PACKAGE})\n\n六主图、五补充图，21 张补充表。图 3c 为配对置乱结果；图 4 为供给余量与承诺决策；PV 位于 S4。完整数据与复算入口保留，作者信息待定。\n\n## 以下为历史版本记录\n\n'+old)
    (ROOT/'manuscript/results-evidence-allocation.md').write_text((HERE/'DESIGN_ZH.md').read_text())
    ledger=ROOT/'manuscript/terminology-ledger.md';old=ledger.read_text()
    if not old.startswith('# v0.25 terminology'):
        ledger.write_text('''# v0.25 terminology clarification

| Canonical term | Meaning and boundary |
|---|---|
| Submission-count weights | Hourly job counts used to distribute a fixed weekly work total |
| Task-resource-time weights | Requested GPU-equivalents times task launch-to-completion duration, aggregated by submitted job |
| Hourly permutation | Reorders whole-hour blocks; changes temporal dependence and alignment with calls/community together |
| Instantaneous supply margin | Baseline PCC minus community minus fixed DC power minus 95% of the request |
| Relaxed-PI tolerance statistics | Statistics of aggregate release/deadline relaxation; no work-group feasibility guarantee |
| Zero-miss success criterion | A successful series must miss no work within the numerical tolerance; qualification still uses a 95% overall success target |

## Retained earlier terminology records

'''+old)
    print('Current indices and figure previews updated')

if __name__=='__main__':main()
