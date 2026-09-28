"""Point current project readers at the audited v0.23 evidence and v12 handoff."""
from pathlib import Path
import json
import re
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
def main():
    package=ROOT/'results/exports/AIDRBench_All_Figures_2026-09-10_v12.zip';assert package.is_file()
    readme=ROOT/'README.md';old=readme.read_text();history=old[old.index('## 历史研究设计与开发记录'):].replace('当前结果以文首 v0.22','当前结果以文首 v0.23',1)
    readme.write_text('''# AIDRBench：工作资格、服务承诺与参与成本

当前正文与补充材料 **v0.23**，中文阅读稿 **v17**。新增分析从修正后的恢复控制器出发，检验服务标准、利用率、期限与生产提交时序；经济性明确拆开固定接入费与运行成本，比较合格时长产品及不参与选项。

- [正文中文全文](docs/chinese_reader/v17/main_zh.md) · [补充材料中文](docs/chinese_reader/v17/supplement_zh.md)
- [正文 PDF](manuscript/exports/AIDRBench_Nature_Communications_v0.23_content_revision.pdf) · [补充材料 PDF](manuscript/exports/AIDRBench_Nature_Communications_v0.23_Supplementary_Information_content_revision.pdf)
- [六张主图](docs/nature-mainline-figure-preview.md) · [五张补充图](docs/nature-supplementary-figure-preview.md)
- [全部图与完整数据包 v12](results/exports/AIDRBench_All_Figures_2026-09-10_v12.zip) · [新增结果、理由与边界](manuscript/revisions/operating_tradeoffs_2026-09-09/RESULTS_AND_REASONS_ZH.md)
- [权威文件和恢复入口](MAINLINE_FILES.md) · [绘图与打包说明](docs/paper-packaging.md)

参考结构条件下，八小时重复承诺由 1% 可参与工作期限容忍的 4.42 kW，变为零期限违约的 2.95 kW。生产原序检验分别为 63/80 和 80/80 个合成实现，统计单位仍是八个真实周。相同时刻的末次调用电力结果未受前三次调用影响，不能将整个方案失败全部归于恢复损害。原四小时单次成本门槛约 95% 来自固定费；零固定费后，合格四/八小时产品仍有不同运行成本。

图 3、6、S3、S5 已重绘；其余七张保留。新增 22,400 次完整重放、4,838,400 小时行与 3,520 套冻结输入完整交付。包内十一张图重绘 PNG 哈希全部一致，四条独立恢复路径的 92 个数值列逐项精确一致。没有启动子智能体；作者信息、许可证和公开归档 DOI 仍待作者确定。

'''+history)
    p=ROOT/'MAINLINE_FILES.md';history=p.read_text().split('## Archived baseline documentation: v0.19 and earlier',1)[1]
    p.write_text('''# AIDRBench formal mainline

## Current revision v0.23, 2026-09-10

The paper now tests operating choices after controller repair: zero versus 1% deadline loss, offered utilisation, deadline slack, matched final-call histories and observed production submission timing. Costs distinguish access fees from operating exposure and compare qualified duration products against opting out. Current Chinese reader: v17; complete handoff: v12.

- English: `manuscript/nature_communications_article.md`, `manuscript/supplementary_information.md`.
- Chinese: `docs/chinese_reader/v17/`; v0.23 main/SI PDFs in `manuscript/exports/` (15/21 pages, 6/5 figures, 17 numbered supplementary tables).
- New evidence: `manuscript/source_data/nature_operating_tradeoffs_v1/`, 22,400 full replays, 4,838,400 hourly rows and 3,520 frozen inputs.
- Inherited five-workload evidence: `manuscript/source_data/nature_workload_composition_v1/`.
- Earlier controller repair: `manuscript/source_data/nature_repeat_mechanism_v1/`, retained separately; 970000 seeds are not pooled with 985000 confirmation.
- Current artwork: `docs/figures/operating_tradeoffs_v1/artwork/`, all 11 in PDF/SVG/PNG/TIFF. Figures 3, 6, S3 and S5 changed.
- Complete handoff: `results/exports/AIDRBench_All_Figures_2026-09-10_v12.zip`.
- Frozen design, detailed Chinese rationale, text changes and verification: `manuscript/revisions/operating_tradeoffs_2026-09-09/`.

## Authority and recovery

For the new study, follow frozen `protocol.json`, `selection.json` and `temporal_protocol.json` in the operating-tradeoffs revision directory, then hash-bound outputs in `results/nature_mainline/operating_tradeoffs_v1/`, complete Source Data, manuscript and this index. Selection metadata record the historical pre-confirmation state; current completion is reported separately. The runner and selector hashes must not be changed retrospectively. The new protocols do not replace older locked benchmark certificates.

The existing `repeat_mechanism_2026-09-09/` protocol governs the earlier recovery intervention. Five-workload `protocol_final.json`, `secondary_protocol_final.json` and `repeat_duration_protocol_v2.json` govern inherited single-event, repeated and renewable comparisons. Do not rerun legacy `init` or confuse obsolete one-hour repeated diagnostics with the corrected four/eight-hour programmes. All older numerical claims retain their original scope.

The complete package runs four plotters from ready tables: the original main and supplementary plotters, the recovery extension, then `operating_tradeoffs/plot_tradeoffs.py`. New replay uses `04_code/operating_tradeoffs/replay_one.py`; it restores any delivered trial from relative package inputs and checks 92 numeric columns. Historical absolute paths identify provenance and are not required for direct plotting or replay.

## Collaboration preference

Do not start sub-agents or delegated reviews unless the user explicitly asks. Author names, affiliations, contributions, funding, licence and release DOI remain pending. Local Python plotting is authorised; historical Web-GPT-only contracts are superseded.

## Verification and scientific boundaries

All 26 positive endpoint-specific structural selections passed independent confirmation; eight combinations had no development candidate. All summary counts and Wilson bounds were recomputed, 560 full trajectories / 2,144 events independently audited and 3,200 structural inputs checked. All 1,296 new price rows and 108 duration-price boundaries passed independent arithmetic checks. Original 30 cost thresholds reconcile exactly. Eleven package-only redraw PNG hashes match, and four direct replay paths match every numeric field and missing-value mask. Final archive CRC, inventory and SHA-256 are recorded in `package_validation.json`.

Zero-miss refers to eligible-work deadlines at a 1e−7 GPU-h numerical tolerance. The eight observed timing weeks with ten synthetic realisations each are not 80 independent weeks or a production SLA replay. The matched final-call electrical result is unchanged by earlier calls. Fixed fees explain about 95% of the old reference single-event threshold; net operating costs still distinguish newly qualified products. No application checkpoint/restart, hardware ageing or continuous-year operation was measured.

## Archived baseline documentation: v0.19 and earlier'''+history)
    (ROOT/'docs/chinese_reader/README.md').write_text('''# 中文阅读稿

当前为 [v17](v17/README.md)，逐段对应英文正文和补充材料 v0.23。新增服务标准、结构与八周生产时序检验，以及固定/运行费用分解。

- [正文中文全文](v17/main_zh.md)
- [补充材料中文全文](v17/supplement_zh.md)
- [正文中英对照](v17/main_bilingual.md)
- [补充材料中英对照](v17/supplement_bilingual.md)

正文六图、补充五图和十七张表。[完整绘图包 v12](../../results/exports/AIDRBench_All_Figures_2026-09-10_v12.zip) 含全部现成绘图表、完整逐时结果与冻结输入。v1–v16 为历史阅读稿。
''')
    (ROOT/'docs/paper-packaging.md').write_text('''# 当前论文 v0.23 与完整绘图包 v12

[完整包](../results/exports/AIDRBench_All_Figures_2026-09-10_v12.zip) 包含英文正文、补充材料、中文 v17、全部十一张图、直接绘图表、完整小时数据和冻结输入。新图为 3、6、S3、S5，另七张保留；每张有 PNG/PDF/SVG/TIFF。

解压后运行 `python RUN_ALL_FIGURES.py`。已有依赖可加 `--use-current-python`。脚本读取已准备好的 CSV，不需重新处理生产数据或模拟。每张图目录有图注、正文解释及面板数据映射；新增四张另有 `ready_data/` 小表。

`03_data/operating_tradeoffs/` 含新增 22,400 次完整重放、4,838,400 小时行与 3,520 个冻结场景；`03_data/` 和 `03_data/repeat_mechanism/` 保留原完整五档数据与恢复干预。`README.md`、`FIELD_GUIDE.md`、`COLUMN_DICTIONARY.csv` 解释单位、判定及所有缩写。失败、无选择和未解析恢复时间均保留。

新增直接回放：`python 04_code/operating_tradeoffs/replay_one.py --data 03_data/operating_tradeoffs --output REPLAY_NEW`。默认运行一条新零违约参考情景，自动检查全部 92 个数值列；命令行可选择包内其他种子、方案、时序与孤立调用。完整模拟器在 `04_code/aidrbench_project/`，无需原目录即可绘图与单情景恢复。

四张替换图的源脚本为 `manuscript/revisions/operating_tradeoffs_2026-09-09/plot_tradeoffs.py`；完整 launcher 先运行原两个 plotter 与旧恢复扩展，再替换四图。新文稿由同目录 `integrate_content.py` 从冻结 v0.22 段落构建，两个 `scripts/render_*tex.py` 自动读取当前版本与图清单，再用 Tectonic 编译。

数值、经济、图文、PDF、全图重绘、四条回放与 ZIP 核查记录见新增修订目录。原 v11 ZIP 保留；新包 `90_archive/v022/` 保存旧论文及被替换图。作者与公开归档信息仍待作者确定；没有启动子智能体。
''')
    for stem,name,tag,n in [('main','nature-mainline-figure-preview.md','Figure',6),('supplement','nature-supplementary-figure-preview.md','Supplementary Figure',5)]:
        rows=json.loads((ROOT/f'docs/chinese_reader/v17/{stem}_aligned_blocks.json').read_text())['blocks'];parts=['# Current v0.23 manuscript figures','Figures 3, 6, S3 and S5 show the new service, timing and cost evidence. All eleven figures and complete data are in the v12 handoff.']
        for i in range(1,n+1):
            title=next(j for j,r in enumerate(rows) if r['en'].startswith(f'### {tag} {i} |'))
            caption=rows[title+1]['en'] if stem=='main' else rows[title+2]['en']
            image=f'![{tag} {i}](figures/operating_tradeoffs_v1/artwork/AIDRBench_{tag.replace(" ","_")}_{i}.png)'
            parts.extend([rows[title]['en'].replace('### ','## ',1),image,caption])
        (ROOT/'docs'/name).write_text('\n\n'.join(parts)+'\n')
    p=ROOT/'docs/all_figure_handoff/README_FIRST.md';old=p.read_text();historical=old[old.index('---'):]
    p.write_text('# 当前完整交付 v12\n\n[全部十一图、现成绘图表、完整小时轨迹与冻结输入](../../results/exports/AIDRBench_All_Figures_2026-09-10_v12.zip)。对应正文/SI v0.23、中文 v17。新增图 3、6、S3、S5 已完成，另七张保留。\n\n运行包根目录 RUN_ALL_FIGURES.py 即可直接重绘；恢复能力由包内 operating_tradeoffs/replay_one.py 和完整模拟器提供。新结果与判断理由见新增修订目录 RESULTS_AND_REASONS_ZH.md。下文仅保存历史交付记录。\n\n'+historical)
    p=ROOT/'docs/figure_recovery/README.md';old=p.read_text()
    if not old.startswith('# 历史图 6'):
        p.write_text('# 历史图 6 / S5 恢复记录\n\n当前完整恢复与重绘请用 [v12 全图包](../../results/exports/AIDRBench_All_Figures_2026-09-10_v12.zip)。用户已允许本地 Python 正式绘图；下文 Web-GPT-only 要求仅是历史状态，不适用于当前 v0.23。\n\n---\n\n'+old)
    p=ROOT/'manuscript/results-evidence-allocation.md';old=p.read_text();hist=old[old.index('## Historical allocation record'):]
    p.write_text('# Current Results evidence allocation v0.23\n\n'+(HERE/'CONTENT_PLAN.md').read_text().split('\n',1)[1]+'\n\nImplementation: the old repair headline was replaced with corrected-controller service standards, structural controls and production timing. Costs explicitly acknowledge the fixed-fee share, then compare qualified duration products after removing it. Negative aligned-target results, no-candidate cases and small PV effects remain visible. Exact replacements are in text_changes.json; current Figures 3/6 and Tables 13–17 carry the new evidence.\n\n'+hist)
    p=ROOT/'manuscript/terminology-ledger.md';old=p.read_text();new='''## v0.23 additions

| Term | Current meaning | Do not substitute |
|---|---|---|
| offered utilisation | offered GPU-hours / installed GPU-hour capacity; 50%, 65%, 80% scenario inputs | measured production GPU utilisation |
| zero deadline loss | ≤1e−7 GPU-h total missed eligible work, paired baseline also zero | measured quality guarantee or zero terminal-backlog requirement |
| start spacing P | time between successive event starts; H8P16 has an 8-h gap | gap G in historical H8G12 |
| matched target electrical outcome | final call alone versus final call after three previous calls at exactly the same clock | full-programme success or global task-service success |
| production timing transfer | eight observed submission-count weeks mapped to synthetic work/deadlines | actual production task or checkpoint/restart replay |
| shared access fee | fixed charge divided among five/ten resources without diversified risk | aggregate reliability certificate |
| net operating cost | ledger energy + waiting + stated loss exposure − capped delivery revenue, before site fee | actual profit, measured GPU ageing or market-calibrated cost |

'''
    if '## v0.23 additions' not in old:p.write_text(old+'\n\n'+new)
    print('Current indexes updated to v0.23 / v17 / v12')
if __name__=='__main__':main()
