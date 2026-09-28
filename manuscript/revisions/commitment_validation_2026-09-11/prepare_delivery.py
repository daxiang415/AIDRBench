"""Prepare v0.27 documents and a self-contained 16-figure redraw directory."""
import csv,hashlib,json,re,shutil,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
DEST=ROOT/'results/exports/AIDRBench_Submission_v0.27_2026-09-11'
OLD=ROOT/'results/exports/AIDRBench_Submission_v0.26_2026-09-11'
ART=ROOT/'docs/figures/commitment_validation_v1/artwork'

def main():
    if (DEST/'CURRENT_VERSION.json').exists() and '--refresh-documents' not in sys.argv:raise SystemExit('Refusing to overwrite an assembled v0.27')
    for d in ['01_LaTeX/figures','02_PDF','03_Chinese_MD/images','06_English_MD','07_Provenance']:(DEST/d).mkdir(parents=True,exist_ok=True)
    for kind,suffix in [('main',''),('supplement','_Supplementary_Information')]:
        src=ROOT/f'manuscript/exports/AIDRBench_Nature_Communications_v0.27{suffix}_content_revision.tex';s=src.read_text()
        s=re.sub(r'\\fancyhead\[L\]\{[^\n]+',lambda _:r'\fancyhead[L]{\small\sffamily '+('AI data centres and demand response' if kind=='main' else 'Supplementary Information')+'}',s)
        s=re.sub(r'\\fancyhead\[R\]\{[^\n]+',lambda _:r'\fancyhead[R]{}',s)
        s=re.sub(r'\\date\{Working[^\n]+',lambda _:r'\date{}',s)
        s,n=re.subn(r'\\begin\{center\}\\small\\bfseries\n(?:Six current data-driven figures; service, timing and cost evidence updated\. Author metadata pending\.|Current methods, supporting tables and 10 supplementary figures\. Author metadata pending\.)\n\\end\{center\}\n','',s);assert n==1
        s=s.replace('../../docs/figures/commitment_validation_v1/artwork/','figures/')
        if kind=='main':
            s=s.replace(r'\section*{Acknowledgements}','\\clearpage\n'+r'\section*{Acknowledgements}')
            s=s.replace(r'\subsection*{Figure 4 | Supply limits and the response–recovery trajectory}','\\clearpage\n'+r'\subsection*{Figure 4 | Supply limits and the response–recovery trajectory}')
        else:
            marker=r'\subsection{Supplementary Table 23 | Fixed node overhead and unchanged-schedule feasibility}'
            assert marker in s
            s=s.replace(marker,'\\clearpage\n'+marker)
        (DEST/f'01_LaTeX/{kind}.tex').write_text(s)
    for p in ART.iterdir():
        if p.suffix=='.pdf':shutil.copy2(p,DEST/'01_LaTeX/figures'/p.name)
        elif p.suffix=='.png':shutil.copy2(p,DEST/'03_Chinese_MD/images'/p.name)
    shutil.copy2(OLD/'01_LaTeX/BUILD.py',DEST/'01_LaTeX/BUILD.py')
    (DEST/'01_LaTeX/README.md').write_text('# LaTeX v0.27\n\nmain.tex and supplement.tex contain the current English text, six main and ten supplementary vector PDF figures. Compile with `python BUILD.py --engine tectonic` or XeLaTeX. All figure paths are relative. Author-provided metadata placeholders remain deliberately unfilled.\n')
    for p in (ROOT/'docs/chinese_reader/v21').glob('*.md'):
        (DEST/'03_Chinese_MD'/p.name).write_text(p.read_text().replace(str(ART)+'/','images/'))
    for name,stem in [('nature_communications_article.md','main'),('supplementary_information.md','supplement')]:
        (DEST/f'06_English_MD/{stem}.md').write_text((ROOT/'manuscript'/name).read_text().replace('../docs/figures/commitment_validation_v1/artwork/','../03_Chinese_MD/images/'))
    if '--refresh-documents' in sys.argv:return
    redraw=DEST/'04_Redraw_Ready';shutil.copytree(OLD/'04_Redraw_Ready',redraw)
    shutil.rmtree(redraw/'artwork');shutil.copytree(ART,redraw/'artwork')
    # Retain all inherited sources, then add only ready new evidence and audit tables.
    source=ROOT/'manuscript/source_data/nature_commitment_validation_v1';target=redraw/'manuscript/source_data/nature_commitment_validation_v1';shutil.copytree(source,target)
    (redraw/'scripts/figures_v026').rename(redraw/'scripts/figures_v027')
    shutil.copy2(HERE/'plot_validation.py',redraw/'scripts/figures_v027/plot_validation.py')
    script=(redraw/'scripts/redraw_figures_v026.py').read_text().replace('14','16').replace('v0.26','v0.27').replace('figures_v026','figures_v027').replace('eight supplementary','ten supplementary')
    script=script.replace("['Figure_3','Supplementary_Figure_3','Supplementary_Figure_4']","['Supplementary_Figure_3']")
    script=script.replace("['Figure_1','Figure_4','Supplementary_Figure_6','Supplementary_Figure_7','Supplementary_Figure_8']","['Figure_1','Figure_4','Supplementary_Figure_6','Supplementary_Figure_8']")
    script=script.replace('    ]\n    rows=[]',"        ('plot_narrative.py',['--data',data/'nature_commitment_validation_v1/plot_inputs'],['Supplementary_Figure_4']),\n        ('plot_completeness.py',['--data',data/'nature_commitment_validation_v1/completeness_inputs'],['Supplementary_Figure_7']),\n        ('plot_validation.py',['--data',data/'nature_commitment_validation_v1/plot_inputs'],['Figure_3','Supplementary_Figure_9','Supplementary_Figure_10']),\n    ]\n    rows=[]")
    (redraw/'scripts/redraw_figures_v027.py').write_text(script);(redraw/'scripts/redraw_figures_v026.py').unlink()
    (redraw/'RUN_ALL_FIGURES.py').write_text("import runpy\nfrom pathlib import Path\nif __name__ == '__main__':\n    runpy.run_path(str(Path(__file__).resolve().parent/'scripts/redraw_figures_v027.py'),run_name='__main__')\n")
    rows=list(csv.DictReader((redraw/'PANEL_DATA_MAP.csv').open()))
    for row in rows:
        row['input']=row['input'].replace('scripts/figures_v026/','scripts/figures_v027/')
        if row['figure']=='3':
            row['input']=row['input'].replace('nature_commitment_narrative_v1','nature_commitment_validation_v1/plot_inputs')
            if row['panels']=='a':row.update(input='manuscript/source_data/nature_commitment_validation_v1/plot_inputs/capacity_selected_confirmed.csv',selection_and_measure='selected H8P16 capacity by weight; each confirmed 300/300 on fixed eight-week empirical mixture')
        if row['figure']=='S4':row['input']=row['input'].replace('nature_commitment_narrative_v1','nature_commitment_validation_v1/plot_inputs')
        if row['figure']=='S7':row['input']=row['input'].replace('nature_figure_completeness_v1','nature_commitment_validation_v1/completeness_inputs')
    for fig,panel,table,meaning in [('S9','a','refinement_selected_confirmed.csv','reference duration products, separate workload distribution'),('S9','b','capacity_development_summary.csv','all 9 candidates, both service endpoints; n=100'),('S9','c','capacity_confirmation_summary.csv','selected offers plus prespecified comparator; n=300 conditional mixture draws'),('S10','a','power_reconciliation.json','exact four-term facility power decomposition'),('S10','b','fixed_overhead_summary.csv','5.898243 kW divided by overhead-specific operating peak'),('S10','c,d','pv_precision_pairs.csv','100 pairs; original and strict solver contrasts in percentage points')]:
        rows.append(dict(figure=fig,panels=panel,input='manuscript/source_data/nature_commitment_validation_v1/plot_inputs/'+table,selection_and_measure=meaning))
    with (redraw/'PANEL_DATA_MAP.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    by=redraw/'BY_FIGURE';shutil.rmtree(by);by.mkdir()
    texts={}
    for stem in ['main','supplement']:
        blocks=json.loads((ROOT/f'docs/chinese_reader/v21/{stem}_aligned_blocks.json').read_text())['blocks']
        for i,b in enumerate(blocks):
            m=re.match(r'### (Supplementary )?Figure (\d+) \|',b['en'])
            if m:
                key=('S' if m[1] else '')+m[2];cap=blocks[i+1] if stem=='main' else blocks[i+2];texts[key]=(b,cap)
    for fig in [str(i) for i in range(1,7)]+['S'+str(i) for i in range(1,11)]:
        folder=by/fig;folder.mkdir();b,cap=texts[fig]
        source_rows=[x for x in rows if x['figure']==fig]
        links='\n'.join('- ['+Path(x['input']).name+'](../../'+x['input']+') — '+x['panels']+': '+x['selection_and_measure'] for x in source_rows)
        (folder/'README.md').write_text(b['en']+'\n\n'+cap['en']+'\n\n'+b['zh']+'\n\n'+cap['zh']+'\n\n'+links+'\n')
    (redraw/'README.md').write_text('''# AIDRBench v0.27 — 直接重绘六张主图、十张补充图

所有绘图数值均已整理，不需要处理原始轨迹或重跑模拟。先安装 requirements.txt，然后执行：

```bash
python -m pip install -r requirements.txt
python RUN_ALL_FIGURES.py --verify
```

结果在 MY_FIGURES/，每图均导出可编辑文字 SVG、矢量 PDF、300 dpi PNG、600 dpi TIFF。修改配色和排版请编辑 scripts/figures_v027/ 中的相应脚本；有意修改后去掉 --verify。逐面板数据路径见 PANEL_DATA_MAP.csv，逐图中英文图注见 BY_FIGURE/。

图号变化：主图 3a 现在显示次数与资源时间加权的 2.95/1.47 kW 已验证报价；原主图 3a 的 5.60/4.42 kW 时长产品保留在 S9a。新 S9b,c 为报价开发与独立确认；新 S10 为功率及求解精度。S4、S7 更新主 10% PV 精度结果，其余图保留。两倍比较属于固定八周经验分布的有限网格报价，不能标注为通用最大容量倍数。800 kW 为社区负荷峰值，PCC 限额为 1,100 kW。

绘图数据始终保留已计算点，不添加中间观测。表中相同成功数有明确共享输入与模型条件。所有原始和严格求解值均保留，储能接纳的 34 个超时问题以数值界处理，没有删除。
''')
    shutil.copy2(OLD/'AUTHOR_INPUT_NEEDED.md',DEST/'AUTHOR_INPUT_NEEDED.md')
    (DEST/'CURRENT_VERSION.json').write_text(json.dumps(dict(manuscript='0.27',date='2026-09-11',chinese_reader='v21',main_figures=6,supplementary_figures=10,supplementary_tables=24,new_capacity_replays=2700,pv_precision_repeats=1000,author_metadata='pending_user'),indent=2)+'\n')
    (DEST/'00_START_HERE.md').write_text('''# AIDRBench v0.27 当前交付

- 01_LaTeX：英文正文、补充材料及全部矢量图；可独立编译。
- 02_PDF：当前正文和补充材料阅读版。
- 03_Chinese_MD：逐段中文及中英对照，图片用相对路径。
- 04_Redraw_Ready：全部 16 图、完整绘图数据和一键脚本。
- 05_Full_Data（完整包内）：原全量证据存档与本次新增逐时重放、冻结输入、求解日志。
- 06_English_MD：英文 Markdown。
- 07_Provenance：逐项回复、冻结协议、数值与排版检查。

版本新增：资源时间 1.47 kW 与次数 2.95 kW 报价各 300/300 确认；功率公式逐项对上 193.438980 kW；固定开销与 PV 精度核查。原主图 3a 移至 S9a，保留原有结果。作者、基金、贡献、声明、许可证和 DOI 仍待用户填写。
''')
    print(DEST)
if __name__=='__main__':main()
