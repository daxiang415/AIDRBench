"""Assemble portable v0.26 submission and drawing material; preserve prior releases."""
import csv
import hashlib
import json
import re
import shutil
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
DEST=ROOT/'results/exports/AIDRBench_Submission_v0.26_2026-09-11'
ART=ROOT/'docs/figures/figure_completeness_v1/artwork'
OLD=ROOT/'results/exports/AIDRBench_Submission_v0.25_2026-09-11'


def main():
    if DEST.exists():raise SystemExit('Refusing to overwrite an assembled release')
    DEST.mkdir()
    for f in ['01_LaTeX/figures','02_PDF','03_Chinese_MD/images','04_Redraw_Ready/artwork','06_English_MD','07_Provenance']:
        (DEST/f).mkdir(parents=True,exist_ok=True)
    transformations=[]
    for kind,suffix,count in [('main','',6),('supplement','_Supplementary_Information',8)]:
        source=ROOT/f'manuscript/exports/AIDRBench_Nature_Communications_v0.26{suffix}_content_revision.tex'
        old=source.read_text();new=old
        new=re.sub(r'\\fancyhead\[L\]\{[^\n]+',lambda _:r'\fancyhead[L]{\small\sffamily '+('AI data centres and demand response' if kind=='main' else 'Supplementary Information')+'}',new)
        new=re.sub(r'\\fancyhead\[R\]\{[^\n]+',lambda _:r'\fancyhead[R]{}',new)
        new=re.sub(r'\\date\{Working[^\n]+',lambda _:r'\date{}',new)
        new,n=re.subn(r'\\begin\{center\}\\small\\bfseries\n(?:Six current data-driven figures; service, timing and cost evidence updated\. Author metadata pending\.|Current methods, supporting tables and 8 supplementary figures\. Author metadata pending\.)\n\\end\{center\}\n','',new)
        assert n==1
        prefix='../../docs/figures/figure_completeness_v1/artwork/'
        assert new.count(prefix)==count
        new=new.replace(prefix,'figures/')
        assert old.split('\\end{center}\n',1)[1]==new.split('\\thispagestyle{fancy}\n',1)[1].replace('figures/',prefix)
        inserts=[];replaces=[]
        if kind=='main':
            inserts=[(r'\section*{Acknowledgements}','\\clearpage\n\\begingroup\n\\titlespacing*{\\section}{0pt}{6pt}{3pt}\n'),
                     ('\\clearpage\n\\section*{Figure Legends}','\\endgroup\n'),
                     (r'\subsection*{Figure 4 | Supply limits and the response–recovery trajectory}','\\clearpage\n')]
            replaces=[('\\endgroup\n\\clearpage\n\\section*{Figure Legends}','\\endgroup\n\\section*{Figure Legends}')]
        else:
            inserts=[(r'\subsection{Supplementary Table 4 | Relaxed planning statistics and independent single-event qualification}','\\begingroup\n\\titlespacing*{\\subsection}{0pt}{9pt}{3pt}\n\\setlength{\\parskip}{3pt}\n'),
                     ('\\clearpage\n\\subsection{Supplementary Table 7 | Single-event and complete-programme participation screens}','\\endgroup\n')]
        for marker,ins in inserts:assert new.count(marker)==1;new=new.replace(marker,ins+marker)
        for a,b in replaces:assert new.count(a)==1;new=new.replace(a,b)
        (DEST/f'01_LaTeX/{kind}.tex').write_text(new)
        transformations.append(dict(kind=kind,source=str(source.relative_to(ROOT)),source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),layout_insertions=inserts,layout_replacements=replaces,scientific_body_preserved=True))
    for p in ART.iterdir():
        if p.suffix not in ['.pdf','.svg','.png','.tiff']:continue
        shutil.copy2(p,DEST/'04_Redraw_Ready/artwork'/p.name)
        if p.suffix=='.pdf':shutil.copy2(p,DEST/'01_LaTeX/figures'/p.name)
        if p.suffix=='.png':shutil.copy2(p,DEST/'03_Chinese_MD/images'/p.name)
    for name in ['main_zh.md','main_bilingual.md','supplement_zh.md','supplement_bilingual.md']:
        txt=(ROOT/'docs/chinese_reader/v20'/name).read_text().replace(str(ART)+'/','images/')
        (DEST/'03_Chinese_MD'/name).write_text(txt)
    for name,kind in [('nature_communications_article.md','main'),('supplementary_information.md','supplement')]:
        (DEST/f'06_English_MD/{kind}.md').write_text((ROOT/'manuscript'/name).read_text().replace('../docs/figures/figure_completeness_v1/artwork/','../03_Chinese_MD/images/'))
    for folder in ['03_Chinese_MD','06_English_MD']:
        for p in (DEST/folder).glob('*.md'):
            for link in re.findall(r'!\[[^]]*\]\(([^)]+)\)',p.read_text()):assert not link.startswith('/') and (p.parent/link).is_file()
    redraw=DEST/'04_Redraw_Ready'
    checkout=Path('/tmp/aidrbench-github-v025-20260911')
    shutil.copytree(checkout/'manuscript/source_data',redraw/'manuscript/source_data')
    shutil.copytree(ROOT/'manuscript/source_data/nature_figure_completeness_v1',redraw/'manuscript/source_data/nature_figure_completeness_v1')
    shutil.copytree(checkout/'scripts/figures_v025',redraw/'scripts/figures_v026',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    shutil.copy2(HERE/'plot_completeness.py',redraw/'scripts/figures_v026/plot_completeness.py')
    shutil.copy2(HERE/'redraw_figures_v026.py',redraw/'scripts/redraw_figures_v026.py')
    shutil.copy2(checkout/'requirements_figures_v025.txt',redraw/'requirements.txt')
    (redraw/'RUN_ALL_FIGURES.py').write_text("import runpy\nfrom pathlib import Path\nif __name__ == '__main__':\n    runpy.run_path(str(Path(__file__).resolve().parent/'scripts/redraw_figures_v026.py'),run_name='__main__')\n")
    maps=[]
    def add(fig,panels,folder,table,meaning):
        maps.append(dict(figure=fig,panels=panels,input='manuscript/source_data/'+folder+'/'+table,selection_and_measure=meaning))
    comp='nature_figure_completeness_v1';mix='nature_workload_composition_v1';nar='nature_commitment_narrative_v1';mech='nature_commitment_mechanisms_v1'
    for panels,table,meaning in [('a','source_audit.json','shares: uncapped requested GPU-hour proportions'),('b','case_definitions.json','eligible_shares: training and offline inference'),('c','decision_steps.csv','step, criterion, decision; schematic, no sampling')]:add('1',panels,comp,table,meaning)
    add('2','a',mix,'pi_boundaries.csv','confirmation; H4/H8; relaxed PI tolerance statistic')
    add('2','a,b',mix,'single_confirm_summary.csv','five cases; notice 0/2/6; success and one-sided Wilson lower')
    for panels,table,meaning in [('a','refinement_selected_confirmed.csv','H4P16/H8P16; successes and confirmation_lower'),('b','ready_pi_categories.csv','prespecified diagnostic categories'),('c','timing_cross_summary.csv','fraction .5; two weights x two orders; descriptive pooled count'),('d','weighted_week_summary.csv','fraction .5 chronological; successes_zero by week')]:add('3',panels,nar,table,meaning)
    for panels,table,meaning in [('a','paired_resource_supply_margins.csv','chronological/permuted paired minimum margins'),('b','supply_hourly_example.csv','seed 990000; chronological hour <168; available_reduction_kw'),('c,d','reference_operation_example.csv','seed 989000; all 216 h; negative incremental_power_kw, excess_backlog_gpu_h')]:add('4',panels,comp,table,meaning)
    add('5','a,b',mix,'control_pi_boundaries.csv','10% work; GPU allocation and rigid-power controls; relaxed PI')
    add('5','c,d',mix,'economic_primary.csv','four-hour single-event/control conditional cost; frozen 95th annual percentile')
    for panels,table in [('a','physical_operating_exposure.csv'),('b','ready_operating_components.csv'),('c','refinement_economic_sensitivity.csv'),('d','ready_refinement_price_curves.csv')]:add('6',panels,mech,table,'reference qualified products: H4 fraction .95; H8 fraction .75; see full legend')
    maps.append(dict(figure='S1',panels='flow',input='scripts/figures_v026/plot_supplement.py',selection_and_measure='fixed evidence-flow schematic; source protocol definitions, not measured quantities'))
    for table in ['calibration_run_means.csv','calibration_class_summary.csv']:add('S2','a,b',mix,table,'four GPU board runs; fit/holdout labels retained')
    for panels,table in [('a,b','refinement_development_summary.csv'),('c','confirmation_summary.csv'),('d','external_cross_score_weekly.csv')]:add('S3',panels,nar,table,'same panel selection as v0.25; separate development and diagnostic provenance')
    for panels,table in [('a,b,d','renewable_paired_comparisons.csv'),('c','single_confirm_summary.csv'),('c','control_causal_summary.csv')]:add('S4',panels,nar,table,'PV differences/paired bootstrap; fixed single-offer controls')
    for panels,table in [('a,b','refinement_economic_sensitivity.csv'),('c,d','ready_annual_values.csv'),('c,d','refinement_price_frontier.csv')]:add('S5',panels,mech,table,'qualified repeated products; waiting prices and shared site fees')
    add('S6','a–d',comp,'structural_full_request.csv','fraction 1; H8; 8 variants x fresh/16h/24h; success_1pct/success_zero; overlapping failures')
    add('S7','a–d',comp,'pv_operating_summary.csv','a,b min pv_rated_kw for pv_hosting; c,d means for fixed_pv_operation')
    add('S7','all source rows',comp,'pv_all_scenarios.csv','all 4000 rows; 100 per configuration/operation/BESS/analysis cell')
    add('S8','a',comp,'reserve_life_sensitivity.csv','f10 single; economic_life_years vs annual threshold')
    add('S8','b–d',comp,'economic_price_sensitivity.csv','f10 single; one factor varied; baseline wait .005/site 25000/displacement 0/miss 0')
    for row in maps:assert (redraw/row['input']).is_file(),row
    with (redraw/'PANEL_DATA_MAP.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(maps[0]));w.writeheader();w.writerows(maps)
    for fig in ['1','2','3','4','5','6','S1','S2','S3','S4','S5','S6','S7','S8']:
        folder=redraw/'BY_FIGURE'/fig;folder.mkdir(parents=True)
        links=['# Figure '+fig,'','Data links point to the files actually read by the renderer.','']
        for row in maps:
            if row['figure']==fig:links.append(f'- {row["panels"]}: [{Path(row["input"]).name}](../../{row["input"]}) — {row["selection_and_measure"]}')
        (folder/'READY_DATA_LINKS.md').write_text('\n'.join(links)+'\n')
        number=fig.lstrip('S');tag='Supplementary Figure' if fig.startswith('S') else 'Figure'
        md=(DEST/'06_English_MD'/('supplement.md' if fig.startswith('S') else 'main.md')).read_text()
        caption=re.search(rf'^### {tag} {number} \| .*?(?=^### |^## |\Z)',md,re.M|re.S)[0]
        caption=re.sub(r'!\[[^]]*\]\([^)]*\)\n?','',caption)
        (folder/'LEGEND.md').write_text(caption)
    shutil.copy2(OLD/'01_LaTeX/BUILD.py',DEST/'01_LaTeX/BUILD.py')
    shutil.copy2(OLD/'AUTHOR_INPUT_NEEDED.md',DEST/'AUTHOR_INPUT_NEEDED.md')
    for p in HERE.glob('*.md'):shutil.copy2(p,DEST/'07_Provenance'/p.name)
    for p in HERE.glob('*.json'):shutil.copy2(p,DEST/'07_Provenance'/p.name)
    for p in ART.glob('*manifest.json'):shutil.copy2(p,DEST/'07_Provenance'/p.name)
    (DEST/'07_Provenance/tex_transformations.json').write_text(json.dumps(transformations,ensure_ascii=False,indent=2)+'\n')
    (DEST/'00_START_HERE.md').write_text('''# AIDRBench v0.26 投稿与绘图材料

本版为 6 张主图、8 张补充图、21 张补充表。英文 v0.26 / 中文 v20 / 绘图包 v15。

- `02_PDF/`：正文和补充 PDF。
- `01_LaTeX/`：可独立编译的 main.tex、supplement.tex 和全部矢量图。运行 `python BUILD.py`，需 XeLaTeX 或 Tectonic；字体/宏包由 TeX 环境提供。此为可编辑论文稿，不冒称官方模板。
- `03_Chinese_MD/`：正文、补充中文稿及逐段中英对照。保留同目录 images/。
- `04_Redraw_Ready/`：全部十四图的现成输入、代码、可编辑 PDF/SVG 以及 PNG/TIFF。
- `06_English_MD/`：英文 Markdown，与 LaTeX 科学内容对应。
- `07_Provenance/COAUTHOR_FIGURE_GUIDE_ZH.md`：合作者应先读的旧版→本版对应表。

图 1c 承接原图 4c 评估流程，图 4c,d 展示当前报价下的响应/恢复。新增 S6–S8 承接结构、PV 和经济性。旧 v0.25 及全部附件保留；没有新增模拟、重新挑选报价或代填作者信息。

作者/单位/基金/贡献/利益声明、许可证及归档信息仍需作者提供。请看 AUTHOR_INPUT_NEEDED.md。本包已整理好，但未自动提交期刊。

完整恢复另见 `AIDRBench_All_Figures_2026-09-11_v15.zip`：包含本版直接重绘目录、旧 v14 完整恢复 ZIP，以及明确标记为历史的 v0.8 绘图源表。重画当前十四图只用这里的直接重绘目录即可，不需要解压旧恢复包。
''')
    (redraw/'README_ZH.md').write_text('''# 直接修改全部十四张图

使用 Python 3.12，在本目录运行：

```bash
python -m pip install -r requirements.txt
python RUN_ALL_FIGURES.py --output MY_FIGURES
```

依赖安装好后可离线绘图，不清洗、不模拟、不重新抽样。原样核验可加 `--verify`；修改后不要加。

- 图 1、4、S6–S8：`scripts/figures_v026/plot_completeness.py`
- 图 2、5：`plot_results.py`
- 图 3、S3–S4：`plot_narrative.py`
- 图 6、S5：`plot_mechanisms.py`
- S1–S2：`plot_supplement.py`

统一入口只交付每个编号的最终图；内部历史中间面板不会流入输出目录。原版 artwork/ 保留 PDF/SVG 可编辑文字及 PNG/TIFF。CSV/JSON 已经整理好，见 PANEL_DATA_MAP.csv 和 BY_FIGURE/ 的数据链接。**修改映射指向的实际输入文件**。不要修改仅用于出处记录的历史路径。

本目录完整覆盖当前十四图的直接重画。完整研究轨迹与复算入口在 v15 大包保留的旧 v14 冻结恢复包中；旧 v0.8 参数扫描单列为历史数据，不是当前证据。软件许可证仍由作者决定。
''')
    (DEST/'01_LaTeX/README_ZH.md').write_text('# LaTeX\n\nmain.tex 为正文（六图），supplement.tex 为补充（八图、21 表），figures/ 为全部矢量 PDF。用 XeLaTeX 编译两遍，或运行 python BUILD.py 使用 XeLaTeX/Tectonic。上传 Overleaf 后选择 XeLaTeX，可分别切换两个主文件。无需项目外 BibTeX 文件，42 条参考文献已内嵌。\n')
    print(DEST)


if __name__=='__main__':main()
