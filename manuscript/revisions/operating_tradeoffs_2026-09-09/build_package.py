"""Build a portable complete v12 handoff, preserving the v11 archive."""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import zipfile
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
OLD=ROOT/'results/exports/AIDRBench_Figures_v11';STAGE=OLD.with_name('AIDRBench_Figures_v12')
PREVIOUS=ROOT/'results/exports/AIDRBench_All_Figures_2026-09-09_v11.zip';TARGET=PREVIOUS.with_name('AIDRBench_All_Figures_2026-09-10_v12.zip')
ART=ROOT/'docs/figures/operating_tradeoffs_v1/artwork';SOURCE=ROOT/'manuscript/source_data/nature_operating_tradeoffs_v1'
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def prepare():
    assert not STAGE.exists() and not TARGET.exists(),'Preserve existing releases/stages.'
    print('Copy complete v11 into a separate v12 staging directory',flush=True);shutil.copytree(OLD,STAGE)
    archive=STAGE/'90_archive/v022';archive.mkdir();shutil.move(str(STAGE/'00_manuscript'),archive/'00_manuscript')
    for name in ['README_FIRST.md','CURRENT_VERSION.json','OPEN_ME.html','RUN_ALL_FIGURES.py']:shutil.copyfile(STAGE/name,archive/name)
    for group,n in [('01_main/F',3),('01_main/F',6),('02_supp/S',3),('02_supp/S',5)]:shutil.copytree(STAGE/f'{group}{n:02d}',archive/f'{group}{n:02d}')
    print('Copy complete new source data and frozen inputs',flush=True);shutil.copytree(SOURCE,STAGE/'03_data/operating_tradeoffs')
    code=STAGE/'04_code/operating_tradeoffs';code.mkdir()
    for p in HERE.iterdir():
        if p.suffix in ['.py','.json','.md'] and p.is_file():shutil.copyfile(p,code/p.name)
    proj=STAGE/'04_code/aidrbench_project';newrev=proj/'manuscript/revisions/operating_tradeoffs_2026-09-09';newrev.mkdir(parents=True)
    for p in HERE.iterdir():
        if p.suffix in ['.py','.json','.md'] and p.is_file():shutil.copyfile(p,newrev/p.name)
    shutil.copyfile(ROOT/'data/manifests/sources.yaml',proj/'data/manifests/sources.yaml')
    (STAGE/'04_code/README.md').write_text('当前 v0.23 全部绘图由根目录 RUN_ALL_FIGURES.py 完成。先运行原五档图，再运行恢复修复图，最后 operating_tradeoffs/plot_tradeoffs.py 替换图 3、6、S3、S5。所有绘图均直接读取包内已计算的表。\n\n新增直接回放：operating_tradeoffs/replay_one.py；原恢复扩展回放：repeat_mechanism/replay_one.py；更早工具仍保留。原完整研究驱动保存历史路径与哈希，直接绘图/单情景回放无需原生产数据。\n')
    launch=(OLD/'RUN_ALL_FIGURES.py').read_text()
    begin=launch.index('    extension=json.loads');end=launch.index("    for prefix,n in",begin)
    launch=launch[:begin]+'''    subprocess.run([str(python),str(ROOT/'04_code/operating_tradeoffs/plot_tradeoffs.py'),
        '--data',str(ROOT/'03_data/operating_tradeoffs'),'--previous-data',str(ROOT/'03_data/repeat_mechanism'),'--output',str(a.output)],check=True)
    for manifest,prefix,n in [('source_manifest.json','AIDRBench_Figure_',6),('supplement_source_manifest.json','AIDRBench_Supplementary_Figure_',5)]:
        outputs={}
        for i in range(1,n+1):
            for ext in ['pdf','svg','png','tiff']:
                p=a.output/f'{prefix}{i}.{ext}';outputs[p.name]=dict(sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size)
        (a.output/manifest).write_text(json.dumps(dict(revision='v0.23',outputs=outputs),indent=2)+'\\n')
''' +launch[end:]
    (STAGE/'RUN_ALL_FIGURES.py').write_text(launch)
    refresh()
    print('Stage ready for independent redraw and replay',flush=True)

def refresh():
    assert STAGE.exists();(STAGE/'00_manuscript/chinese').mkdir(parents=True,exist_ok=True)
    artwork={}
    for group,tag,count in [('01_main/F','AIDRBench_Figure_',6),('02_supp/S','AIDRBench_Supplementary_Figure_',5)]:
        for n in range(1,count+1):
            name=f'{tag}{n}.png';artwork[name]=f'{group}{n:02d}/artwork/{name}'
            for ext in ['pdf','svg','png','tiff']:shutil.copyfile(ART/f'{tag}{n}.{ext}',STAGE/f'{group}{n:02d}/artwork/{tag}{n}.{ext}')
    def portable(text,folder):return re.sub(r'!\[([^]]*)\]\(([^)]+)\)',lambda m:f'![{m[1]}]({os.path.relpath(artwork[Path(m[2]).name],folder)})',text)
    for name in ['nature_communications_article.md','supplementary_information.md']:(STAGE/'00_manuscript'/name).write_text(portable((ROOT/'manuscript'/name).read_text(),'00_manuscript'))
    for p in (ROOT/'docs/chinese_reader/v17').glob('*.md'):(STAGE/'00_manuscript/chinese'/p.name).write_text(portable(p.read_text(),'00_manuscript/chinese'))
    for p in (ROOT/'manuscript/exports').glob('AIDRBench_Nature_Communications_v0.23*.pdf'):shutil.copyfile(p,STAGE/'00_manuscript'/p.name)
    docs=[(ROOT/'manuscript'/name).read_text() for name in ['nature_communications_article.md','supplementary_information.md']]
    results=[s.strip() for s in re.split(r'(?m)(?=^### )',docs[0].split('## Results\n')[1].split('## Discussion\n')[0]) if s.strip()];assert len(results)==6
    with (SOURCE/'PANEL_DATA_MAP.csv').open() as f:maps=list(csv.DictReader(f))
    for group,tag,count,doc in [('01_main/F','Figure',6,docs[0]),('02_supp/S','Supplementary Figure',5,docs[1])]:
        for n in range(1,count+1):
            folder=f'{group}{n:02d}';dest=STAGE/folder;fig=str(n) if tag=='Figure' else f'S{n}'
            legend=re.search(rf'^### {tag} {n} \| .*?(?=^### |^## |\Z)',doc,re.M|re.S);assert legend
            (dest/'FIGURE_LEGEND.md').write_text(portable(legend[0].strip(),folder)+'\n')
            if tag=='Figure':(dest/'MANUSCRIPT_CONTEXT.md').write_text(portable(results[n-1],folder)+'\n')
            rows=[r for r in maps if r['figure']==fig]
            if rows:
                ready=dest/'ready_data';ready.mkdir(exist_ok=True);portable_rows=[]
                for r in rows:
                    p=(SOURCE/r['table']).resolve() if not r['table'].startswith('../') else SOURCE.parent/'nature_repeat_mechanism_v1'/Path(r['table']).name
                    filename=('previous_' if r['table'].startswith('../') else '')+p.name;shutil.copyfile(p,ready/filename)
                    portable_rows.append(r|dict(table='ready_data/'+filename,complete_data='../../03_data/operating_tradeoffs/'))
                with (dest/'PANEL_DATA_MAP.csv').open('w',newline='') as stream:
                    w=csv.DictWriter(stream,fieldnames=list(portable_rows[0]));w.writeheader();w.writerows(portable_rows)
                (dest/'README.md').write_text(f'# 当前图 {fig}\n\n直接打开 ready_data/ 中的 CSV 即可修改绘图；PANEL_DATA_MAP.csv 明确每个面板的筛选与纵轴列。完整原始字段、逐时数据和冻结输入在 ../../03_data/operating_tradeoffs/。图注见 FIGURE_LEGEND.md。根目录 RUN_ALL_FIGURES.py 会生成全部十一张图；本图绘图脚本为 04_code/operating_tradeoffs/plot_tradeoffs.py。\n')
    readme='''# AIDRBench 全图与完整恢复包 v12

当前正文/SI **v0.23（2026-09-10）**，中文阅读稿 **v17**。共六张主图、五张补充图，每张均有 PNG、PDF、SVG、TIFF。图 3、6、S3、S5 为本版重绘；其他七张保留当前证据。原 v0.22 文稿和被替换图保留在 `90_archive/v022/`。

## 最直接的使用方法

1. 打开 `OPEN_ME.html`，选择图片、正文、中文稿或数据目录。
2. 改某张图：进入 `01_main/F01`–`F06` 或 `02_supp/S01`–`S05`。当前图注和正文解释已更新；新增四张的 `ready_data/` 有直接绘图的 CSV，`PANEL_DATA_MAP.csv` 给出具体列与筛选。
3. 一次重画全部图：运行下面的脚本；只需要 Python 与绘图库，无需重新处理生产数据或运行模拟。默认脚本会建立绘图环境并安装 requirements_plot.txt；已有依赖时使用 --use-current-python。

```bash
python RUN_ALL_FIGURES.py
python RUN_ALL_FIGURES.py --use-current-python --output MY_FIGURES
```

## 全部数据在哪里

`03_data/` 保留前版完整五档研究；`03_data/repeat_mechanism/` 保留旧控制器修复与独立确认；`03_data/operating_tradeoffs/` 新增服务标准、结构、时序和费用拆分。新目录有 22,400 次完整重放、4,838,400 行逐时数据和 3,520 个冻结输入，包含成功与失败。CSV 为直接用表，Parquet 保留全部原始数值字段。读取逐时图无需计算汇总，ready_hourly_curves.csv 已准备好。

原始第三方大规模完整发布仍从提供者获取；所有**绘制本包图件所需的数据与本研究冻结输入**均已在包内。新增生产时序计数的处理后提交时间记录也已包含，不依赖网络下载。

## 直接恢复一条计算

```bash
python 04_code/operating_tradeoffs/replay_one.py --data 03_data/operating_tradeoffs --output REPLAY_NEW
```

默认重放新参考零违约候选（985000，H8P16，2.95 kW）。会自动对照已交付逐时记录的全部数值列及缺失值位置。可选择 --role、--variant、--seed、--program、--kind、--fraction，取值见 *_ledgers.csv。原回放工具仍在 04_code/repeat_mechanism/ 与 04_code/restore_scenario.py。

## 如何核对

`VERIFY_PACKAGE.py` 检查 FILE_INVENTORY.csv / SHA256SUMS.txt。新增科学依据见 `05_audit/operating_tradeoffs_v023/RESULTS_AND_REASONS_ZH.md`；数值、图文、PDF、全图重绘与回放记录保存在该目录。恢复代码只使用包内路径；冻结协议中的原绝对路径仅是历史标识。

这些结果是有条件的模型证据：真实提交时序并非真实任务暂停恢复验证；八个观察周×十次合成实现不等于八十个独立观察周。作者、基金、许可证和公开归档信息仍待作者确定，本包不代填。
'''
    (STAGE/'README_FIRST.md').write_text(readme)
    links=[]
    for group,tag,n in [('01_main/F','Figure',6),('02_supp/S','Supplementary Figure',5)]:
        for i in range(1,n+1):
            folder=f'{group}{i:02d}';base=f'AIDRBench_{tag.replace(" ","_")}_{i}'
            links.append(f'<tr><td>{tag} {i}</td><td><a href="{folder}/artwork/{base}.png">PNG</a> · <a href="{folder}/artwork/{base}.pdf">PDF</a> · <a href="{folder}/artwork/{base}.svg">SVG</a></td><td><a href="{folder}/PANEL_DATA_MAP.csv">面板数据映射</a> · <a href="{folder}/">图件目录</a></td></tr>')
    html='<!doctype html><meta charset="utf-8"><title>AIDRBench v0.23 / 完整包 v12</title><style>body{font:16px system-ui;max-width:1000px;margin:40px auto;line-height:1.7}td,th{padding:8px 18px;text-align:left;border-bottom:1px solid #ddd}a{color:#235a78}</style><h1>AIDRBench 完整绘图包 v12</h1><p>正文 v0.23 · 中文 v17 · 六张主图、五张补充图</p><p><a href="00_manuscript/AIDRBench_Nature_Communications_v0.23_content_revision.pdf">正文 PDF</a> · <a href="00_manuscript/AIDRBench_Nature_Communications_v0.23_Supplementary_Information_content_revision.pdf">补充 PDF</a> · <a href="00_manuscript/chinese/main_zh.md">中文全文</a> · <a href="00_manuscript/chinese/supplement_zh.md">中文补充材料</a></p><p><a href="README_FIRST.md">直接重绘与恢复说明</a> · <a href="03_data/operating_tradeoffs/README.md">新增完整数据说明</a> · <a href="05_audit/operating_tradeoffs_v023/RESULTS_AND_REASONS_ZH.md">结果与理由</a></p><table><tr><th>图</th><th>图片</th><th>数据</th></tr>'+''.join(links)+'</table>'
    (STAGE/'OPEN_ME.html').write_text(html)
    (STAGE/'CURRENT_VERSION.json').write_text(json.dumps(dict(manuscript='0.23',chinese_reader='v17',package='v12',main_figures=6,supplementary_figures=5,numbered_supplementary_tables=17,new_complete_replays=22400,new_hourly_rows=4838400,author_metadata_pending=True),indent=2)+'\n')
    checks=STAGE/'05_audit/operating_tradeoffs_v023';checks.mkdir(exist_ok=True)
    for p in HERE.iterdir():
        if p.is_file() and p.suffix in ['.py','.json','.md','.csv'] and p.name!='package_validation.json':shutil.copyfile(p,checks/p.name)
    for p in HERE.iterdir():
        if p.is_file() and p.suffix in ['.py','.md','.json'] and p.name!='package_validation.json':
            shutil.copyfile(p,STAGE/'04_code/operating_tradeoffs'/p.name)
            shutil.copyfile(p,STAGE/'04_code/aidrbench_project/manuscript/revisions/operating_tradeoffs_2026-09-09'/p.name)
    for folder in ['00_manuscript','01_main','02_supp']:
        for p in (STAGE/folder).rglob('*.md'):
            for dest in re.findall(r'!\[[^]]*\]\(([^)]+)\)',p.read_text()):assert not dest.startswith('/') and (p.parent/dest).is_file(),(p,dest)

def archive():
    assert not TARGET.exists(),'Do not overwrite a delivered release';refresh()
    old={r['path']:r for r in csv.DictReader((OLD/'FILE_INVENTORY.csv').open())}
    print('Hash complete portable package inventory',flush=True)
    files=sorted(p for p in STAGE.rglob('*') if p.is_file() and p not in [STAGE/'FILE_INVENTORY.csv',STAGE/'SHA256SUMS.txt'])
    rows=[dict(path=p.relative_to(STAGE).as_posix(),bytes=p.stat().st_size,sha256=sha(p)) for p in files]
    with (STAGE/'FILE_INVENTORY.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=['path','bytes','sha256']);w.writeheader();w.writerows(rows)
    (STAGE/'SHA256SUMS.txt').write_text(''.join(f'{r["sha256"]}  {r["path"]}\n' for r in rows)+f'{sha(STAGE/"FILE_INVENTORY.csv")}  FILE_INVENTORY.csv\n')
    changed=[r['path'] for r in rows if r['path'] not in old or r['sha256']!=old[r['path']]['sha256']]+['FILE_INVENTORY.csv','SHA256SUMS.txt']
    expected={p.relative_to(STAGE).as_posix() for p in STAGE.rglob('*') if p.is_file()};tmp=TARGET.with_suffix('.building.zip');assert not tmp.exists()
    print('Reuse previous compressed payload; append new full data',flush=True);shutil.copyfile(PREVIOUS,tmp)
    notes=subprocess.check_output(['zipnote',str(tmp)],text=True);updated=[]
    for line in notes.splitlines():
        updated.append(line)
        if line.startswith('@ '+OLD.name+'/'):updated.append('@='+STAGE.name+line[len('@ '+OLD.name):])
    subprocess.run(['zipnote','-w',str(tmp)],input='\n'.join(updated)+'\n',text=True,check=True)
    with zipfile.ZipFile(tmp) as z:removed=[name for name in z.namelist() if name.removeprefix(STAGE.name+'/') not in expected]
    if removed:subprocess.run(['zip','-q','-d',str(tmp),*removed],check=True)
    subprocess.run(['zip','-q','-1',str(tmp),'-@'],input=''.join(STAGE.name+'/'+p+'\n' for p in changed),text=True,cwd=STAGE.parent,check=True)
    print('Verify full ZIP contents and CRC',flush=True)
    with zipfile.ZipFile(tmp) as z:
        names=z.namelist();assert len(names)==len(set(names));assert set(names)=={STAGE.name+'/'+p for p in expected}
        for rel in changed:
            with z.open(STAGE.name+'/'+rel) as stream:assert hashlib.file_digest(stream,'sha256').hexdigest()==sha(STAGE/rel),rel
        assert z.testzip() is None
    tmp.replace(TARGET);result=dict(status='PASS',path=str(TARGET),staging=str(STAGE),bytes=TARGET.stat().st_size,sha256=sha(TARGET),files=len(expected),changed_entries=len(changed),zip_crc_pass=True,duplicate_entries=False,manuscript='v0.23',chinese='v17',current_figures=11,previous_release_preserved=True)
    (HERE/'package_validation.json').write_text(json.dumps(result,indent=2)+'\n');TARGET.with_suffix('.zip.sha256').write_text(f'{result["sha256"]}  {TARGET.name}\n');print(json.dumps(result,indent=2),flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('action',choices=['prepare','refresh','archive']);a=ap.parse_args();globals()[a.action]()
