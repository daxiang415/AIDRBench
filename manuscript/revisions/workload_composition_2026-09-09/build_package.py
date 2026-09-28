"""Current eleven-figure package, complete source tables and immutable v8 archive."""
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
SOURCE=ROOT/'manuscript/source_data/nature_workload_composition_v1'
ART=ROOT/'docs/figures/workload_composition_v1/artwork'
PREVIOUS=ROOT/'results/exports/AIDRBench_All_Figures_2026-09-08_v8.zip'
TARGET=ROOT/'results/exports/AIDRBench_All_Figures_2026-09-09_v9.zip'
PREFIX='AIDRBench_Figures_v9'

def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def main():
    staging=ROOT/'results/exports/AIDRBench_Figures_v9'
    assert not staging.exists(),'Use a fresh staging path, or explicitly archive the previous build.'
    staging.mkdir(parents=True)
    def add(name,source=None,text=None):
        dest=staging/name;dest.parent.mkdir(parents=True,exist_ok=True)
        if source is not None:shutil.copyfile(source,dest)
        else:dest.write_text(text)
    artwork={}
    maintext=(ROOT/'manuscript/nature_communications_article.md').read_text()
    supplement=(ROOT/'manuscript/supplementary_information.md').read_text()
    def portable(text,folder):
        return re.sub(r'!\[([^]]*)\]\(([^)]+)\)',lambda m:f'![{m[1]}]({os.path.relpath(artwork[Path(m[2]).name],folder)})',text)
    data_map={1:['source_audit.json','case_definitions.json','source_mix_by_class_priority.csv'],2:['pi_boundaries.csv','pi_scenarios.csv','single_confirm_summary.csv','notice_paired_comparisons.csv'],3:['repeat_paired_comparisons.csv','repeat_dev_summary.csv','repeated_confirmation_ledgers.csv'],4:['renewable_paired_comparisons.csv','renewable_scenarios.csv'],5:['control_pi_boundaries.csv','control_causal_summary.csv','economic_primary.csv'],6:['economic_primary.csv','economic_price_sensitivity.csv','single_confirmation_ledgers.csv','repeated_confirmation_ledgers.csv']}
    supp_map={1:['case_definitions.json','export_receipt.json'],2:['calibration_run_means.csv','calibration_class_summary.csv'],3:['ready_hourly_curves.csv','hourly_partition_index.csv'],4:['control_causal_summary.csv','renewable_paired_comparisons.csv'],5:['economic_price_sensitivity.csv','reserve_life_sensitivity.csv']}
    results=[s.strip() for s in re.split(r'(?m)(?=^### )',maintext.split('## Results\n')[1].split('## Discussion\n')[0]) if s.strip()]
    assert len(results)==6
    for group,count,prefix,tag,source,mapping in [('01_main',6,'AIDRBench_Figure_','Figure',maintext,data_map),('02_supp',5,'AIDRBench_Supplementary_Figure_','Supplementary Figure',supplement,supp_map)]:
        for n in range(1,count+1):
            folder=f'{group}/{"F" if group=="01_main" else "S"}{n:02d}'
            for ext in ['pdf','svg','png','tiff']:
                name=f'{prefix}{n}.{ext}';relative=f'{folder}/artwork/{name}';add(relative,source=ART/name);artwork[name]=relative
            match=re.search(rf'^### {tag} {n} \| .*?(?=^### |^## |\Z)',source,re.M|re.S);assert match,(tag,n)
            add(folder+'/FIGURE_LEGEND.md',text=portable(match[0].strip(),folder)+'\n')
            add(folder+'/PANEL_DATA_MAP.csv',text='data_file\n'+''.join('../../03_data/'+name+'\n' for name in mapping[n]))
            add(folder+'/README.md',text=f'# {tag} {n}\n\n图件在 artwork/，数值输入见 PANEL_DATA_MAP.csv。修改 ../../04_code/ 中对应绘图脚本或公共 03_data/ 表格，运行根目录 RUN_ALL_FIGURES.py 即可重绘。无需重新模拟或重新计算统计量。\n')
    for n,section in enumerate(results,1):
        folder=f'01_main/F{n:02d}';add(folder+'/MANUSCRIPT_CONTEXT.md',text=portable(section,folder)+'\n')
    for name in ['nature_communications_article.md','supplementary_information.md']:
        add('00_manuscript/'+name,text=portable((ROOT/'manuscript'/name).read_text(),'00_manuscript'))
    for p in (ROOT/'docs/chinese_reader/v14').glob('*.md'):add('00_manuscript/chinese/'+p.name,text=portable(p.read_text(),'00_manuscript/chinese'))
    for p in (ROOT/'manuscript/exports').glob('AIDRBench_Nature_Communications_v0.20*.pdf'):add('00_manuscript/'+p.name,source=p)
    for p in SOURCE.rglob('*'):
        if p.is_file():add('03_data/'+p.relative_to(SOURCE).as_posix(),source=p)
    for p in HERE.glob('*.py'):add('04_code/'+p.name,source=p)
    # Preserve the exact current simulator as well as the standalone plotters.
    for p in (ROOT/'src/aidrbench').rglob('*.py'):
        add('04_code/aidrbench_project/'+p.relative_to(ROOT).as_posix(),source=p)
    for name in ['pyproject.toml','uv.lock','README.md']:
        if (ROOT/name).is_file():add('04_code/aidrbench_project/'+name,source=ROOT/name)
    for folder in ['configs','data/calibration','data/manifests']:
        for p in (ROOT/folder).rglob('*'):
            if p.is_file() and p.suffix in ['.yaml','.yml','.json','.csv']:
                add('04_code/aidrbench_project/'+p.relative_to(ROOT).as_posix(),source=p)
    for p in HERE.iterdir():
        if p.is_file() and p.suffix in ['.py','.json']:
            add('04_code/aidrbench_project/manuscript/revisions/workload_composition_2026-09-09/'+p.name,source=p)
    add('04_code/README.md',text='''# 绘图与计算恢复

日常改图只使用这里的 plot_results.py、plot_supplement.py 和根目录 RUN_ALL_FIGURES.py。全部面板统计量已经给出。

restore_scenario.py 可从 03_data/recovery_inputs 恢复单个完整冻结情景，逐文件核对原始哈希。例如，在本目录运行：

```bash
python restore_scenario.py --data ../03_data --case f10 --seed 960000 --output RESTORED_f10_960000
```

aidrbench_project 保存当前完整 src/aidrbench、项目依赖、配置和本轮驱动。它用于审计或进一步模型研究；完整研究驱动仍使用原项目目录结构，需要将源数据放入对应位置并准备第三方输入。直接重画本包全部图不需要运行模型或恢复情景。
''')
    for p in HERE.glob('*.json'):add('05_audit/'+p.name,source=p)
    for p in HERE.glob('*.md'):add('05_audit/'+p.name,source=p)
    for p in HERE.glob('*audit*.csv'):add('05_audit/'+p.name,source=p)
    for name in ['source_manifest.json','supplement_source_manifest.json']:add('05_audit/'+name,source=ART/name)
    add('RUN_ALL_FIGURES.py',source=HERE/'package_launcher.py')
    add('requirements_plot.txt',text='numpy==2.5.2\npandas==2.3.3\nmatplotlib==3.11.1\npyarrow==21.0.0\n')
    add('90_archive/AIDRBench_All_Figures_2026-09-08_v8.zip',source=PREVIOUS)
    add('90_archive/README.md',text='此前 v0.19 全部正文、中文稿、11 图、完整绘图数据和旧的连续调用数据原封不动保存于 v8.zip。它们属于旧工作构成；当前正文不混用旧 75% 结果。\n')
    add('README_FIRST.md',text='''# 全部 11 图与完整绘图数据 v9

当前论文 v0.20，中文阅读稿 v14。5%、10%、20%、40%、60% 的主体下游计算已全部替换；40% 和 60% 的额外业务假设见论文和源数据。

1. 阅读全文：`00_manuscript/`；中文在 `00_manuscript/chinese/`。
2. 一次重绘全部 11 张图：推荐使用已验证的 Python 3.12，运行 `python RUN_ALL_FIGURES.py`。首次运行自动安装绘图库；输出位于 `REDRAW_OUTPUT/`。
3. 已有绘图环境：`python RUN_ALL_FIGURES.py --use-current-python`。
4. 修改样式：`04_code/plot_results.py`（主图 1–6）与 `04_code/plot_supplement.py`（补充图 1–5）。
5. 修改数据：直接读取 `03_data/` 现成 CSV/JSON；每张图文件夹有数据映射和图注。容量、置信下界、配对区间、经济门槛都已计算，不需要再运行模型。
6. 完整时序：`03_data/hourly_full/` 保留每个开发及确认试验的全部列；`hourly_plot_csv/` 提供完整逐小时绘图列；`ready_hourly_curves.csv` 已算好均值及分位数。
7. 校验包：`python VERIFY_PACKAGE.py`。旧版本全部材料保存在 `90_archive/v8.zip` 对应的原名文件中。

主图与补充图共 11 张，每张都有 PDF、SVG、PNG、TIFF。PDF/SVG 中的文字可编辑。原始第三方大型数据从其官方来源获取；本包已包含当前全部图的数据与可恢复代码。正式公开归档 DOI、作者信息及软件许可证仍待作者确认。
''')
    add('OPEN_ME.html',text='<!doctype html><meta charset="utf-8"><title>AIDRBench 全部 11 图 v9</title><h1>当前论文与全部绘图数据 v9</h1><p><a href="README_FIRST.md">使用说明与一键重绘</a> · <a href="00_manuscript/chinese/main_zh.md">正文中文</a> · <a href="00_manuscript/chinese/supplement_zh.md">补充材料中文</a> · <a href="03_data/README.md">完整数据说明</a></p>')
    add('CURRENT_VERSION.json',text=json.dumps(dict(package=9,manuscript='0.20',chinese_reader='v14',date='2026-09-09',figures=11,previous_package_sha256=sha(PREVIOUS)),indent=2)+'\n')
    image_links=0
    for folder in ['00_manuscript','01_main','02_supp']:
        for path in (staging/folder).rglob('*.md'):
            for target in re.findall(r'!\[[^]]*\]\(([^)]+)\)',path.read_text()):
                assert not Path(target).is_absolute(),(path,target)
                assert (path.parent/target).resolve().is_file(),(path,target)
                image_links+=1
    add('05_audit/portable_image_links.json',text=json.dumps(dict(status='PASS',checked_links=image_links,scope='all delivered manuscripts, Chinese readers, figure legends and contexts'),indent=2)+'\n')
    add('VERIFY_PACKAGE.py',text='''from pathlib import Path
import hashlib
p=Path(__file__).resolve().parent
rows=(p/'SHA256SUMS.txt').read_text().splitlines()
for row in rows:
 digest,name=row.split('  ',1)
 with (p/name).open('rb') as f:actual=hashlib.file_digest(f,'sha256').hexdigest()
 assert actual==digest,name
print('PASS:',len(rows),'files verified')
''')
    redraw=Path(tempfile.mkdtemp(prefix='aidrbench_v9_redraw_'))
    subprocess.run([sys.executable,str(staging/'RUN_ALL_FIGURES.py'),'--use-current-python','--output',str(redraw)],check=True)
    comparisons=[]
    for prefix,count in [('AIDRBench_Figure_',6),('AIDRBench_Supplementary_Figure_',5)]:
        for n in range(1,count+1):
            name=f'{prefix}{n}.png'
            assert sha(redraw/name)==sha(ART/name),f'Redraw differs: {name}'
            comparisons.append(dict(figure=name,identical_png_sha256=sha(redraw/name)))
    add('05_audit/redraw_validation.json',text=json.dumps(dict(status='PASS',source='delivered 03_data and 04_code only',all_eleven_png_byte_identical=True,figures=comparisons),indent=2)+'\n')
    files=sorted(p for p in staging.rglob('*') if p.is_file())
    buf=io.StringIO();w=csv.writer(buf);w.writerow(['path','bytes','sha256'])
    for p in files:w.writerow([p.relative_to(staging).as_posix(),p.stat().st_size,sha(p)])
    add('FILE_INVENTORY.csv',text=buf.getvalue())
    files=sorted(p for p in staging.rglob('*') if p.is_file())
    add('SHA256SUMS.txt',text=''.join(f'{sha(p)}  {p.relative_to(staging).as_posix()}\n' for p in files))
    temporary=TARGET.with_suffix('.building.zip')
    with zipfile.ZipFile(temporary,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in staging.rglob('*'):
            if p.is_file():z.write(p,PREFIX+'/'+p.relative_to(staging).as_posix(),compress_type=zipfile.ZIP_STORED if p.suffix=='.zip' else zipfile.ZIP_DEFLATED)
    temporary.replace(TARGET)
    with zipfile.ZipFile(TARGET) as z:assert z.testzip() is None
    subprocess.run([sys.executable,str(staging/'VERIFY_PACKAGE.py')],check=True)
    report=dict(status='PASS',path=str(TARGET),bytes=TARGET.stat().st_size,sha256=sha(TARGET),staging=str(staging),files=len(files)+1,redraw_test='PASS:11 current PNGs byte-identical using only delivered source/code',all_payload_checksums_pass=True,zip_crc_pass=True)
    (HERE/'package_validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))

if __name__=='__main__':main()
