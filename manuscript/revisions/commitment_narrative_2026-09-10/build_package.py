"""Prepare portable v14 and preserve the complete delivered v13 release."""
import argparse
import csv
import hashlib
import json
import os
import re
import shutil
import struct
import subprocess
import zipfile
from pathlib import Path

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
OLD=ROOT/'results/exports/AIDRBench_Figures_v13'
STAGE=OLD.with_name('AIDRBench_Figures_v14')
PREVIOUS=ROOT/'results/exports/AIDRBench_All_Figures_2026-09-10_v13.zip'
TARGET=PREVIOUS.with_name('AIDRBench_All_Figures_2026-09-10_v14.zip')
SOURCE=ROOT/'manuscript/source_data/nature_commitment_narrative_v1'
ART=ROOT/'docs/figures/commitment_narrative_v1/artwork'
CHANGED={'01_main/F03','01_main/F04','02_supp/S03','02_supp/S04'}

def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def prepare():
    assert not STAGE.exists() and not TARGET.exists()
    print('Copy complete existing data and recovery project',flush=True)
    shutil.copytree(OLD,STAGE)
    archive=STAGE/'90_archive/v024';archive.mkdir()
    for name in ['00_manuscript','01_main','02_supp']:shutil.move(str(STAGE/name),archive/name)
    for name in ['README_FIRST.md','CURRENT_VERSION.json','OPEN_ME.html','RUN_ALL_FIGURES.py']:shutil.copyfile(STAGE/name,archive/name)
    for group,count in [('01_main/F',6),('02_supp/S',5)]:
        for n in range(1,count+1):
            folder=f'{group}{n:02d}'
            if folder in CHANGED:(STAGE/folder/'artwork').mkdir(parents=True)
            else:shutil.copytree(archive/folder,STAGE/folder)
    shutil.copytree(SOURCE,STAGE/'03_data/commitment_narrative')
    for folder in ['04_code/commitment_narrative','05_audit/commitment_narrative_v025']:(STAGE/folder).mkdir(parents=True)
    launcher=(OLD/'RUN_ALL_FIGURES.py').read_text();mark='    for manifest,prefix,n in '
    i=launcher.index(mark)
    launcher=launcher[:i]+"    subprocess.run([str(python),str(ROOT/'04_code/commitment_narrative/plot_narrative.py'),'--data',str(ROOT/'03_data/commitment_narrative'),'--output',str(a.output)],check=True)\n"+launcher[i:]
    (STAGE/'RUN_ALL_FIGURES.py').write_text(launcher.replace("revision='v0.24'","revision='v0.25'"))
    refresh();print('Stage prepared',flush=True)

def refresh():
    assert STAGE.exists();(STAGE/'00_manuscript/chinese').mkdir(parents=True,exist_ok=True)
    images={}
    for group,prefix,count in [('01_main/F','AIDRBench_Figure_',6),('02_supp/S','AIDRBench_Supplementary_Figure_',5)]:
        for n in range(1,count+1):
            folder=f'{group}{n:02d}';images[f'{prefix}{n}.png']=f'{folder}/artwork/{prefix}{n}.png'
            for ext in ['pdf','svg','png','tiff']:shutil.copyfile(ART/f'{prefix}{n}.{ext}',STAGE/folder/'artwork'/f'{prefix}{n}.{ext}')
    def portable(text,folder):
        return re.sub(r'!\[([^]]*)\]\(([^)]+)\)',lambda m:f'![{m[1]}]({os.path.relpath(images[Path(m[2]).name],folder)})',text)
    docs=[(ROOT/'manuscript'/name).read_text() for name in ['nature_communications_article.md','supplementary_information.md']]
    for name,text in zip(['nature_communications_article.md','supplementary_information.md'],docs):(STAGE/'00_manuscript'/name).write_text(portable(text,'00_manuscript'))
    for p in (ROOT/'docs/chinese_reader/v19').glob('*.md'):(STAGE/'00_manuscript/chinese'/p.name).write_text(portable(p.read_text(),'00_manuscript/chinese'))
    for p in (ROOT/'manuscript/exports').glob('AIDRBench_Nature_Communications_v0.25*.pdf'):shutil.copyfile(p,STAGE/'00_manuscript'/p.name)
    maps=list(csv.DictReader((SOURCE/'PANEL_DATA_MAP.csv').open()))
    sections=[x.strip() for x in re.split(r'(?m)(?=^### )',docs[0].split('## Results\n')[1].split('## Discussion\n')[0]) if x.strip()];assert len(sections)==6
    for group,tag,count,doc in [('01_main/F','Figure',6,docs[0]),('02_supp/S','Supplementary Figure',5,docs[1])]:
        for n in range(1,count+1):
            folder=f'{group}{n:02d}';dest=STAGE/folder;fig=str(n) if tag=='Figure' else f'S{n}'
            legend=re.search(rf'^### {tag} {n} \| .*?(?=^### |^## |\Z)',doc,re.M|re.S);assert legend
            (dest/'FIGURE_LEGEND.md').write_text(portable(legend[0].strip(),folder)+'\n')
            if tag=='Figure':(dest/'MANUSCRIPT_CONTEXT.md').write_text(portable(sections[n-1],folder)+'\n')
            entries=[r for r in maps if r['figure']==fig]
            if entries:
                ready=dest/'ready_data';ready.mkdir(exist_ok=True);mapped=[]
                for row in entries:
                    shutil.copyfile(SOURCE/row['table'],ready/row['table'])
                    mapped.append(row|dict(table='ready_data/'+row['table'],plot_input='../../03_data/commitment_narrative/'+row['table'],complete_data='../../03_data/'))
                with (dest/'PANEL_DATA_MAP.csv').open('w',newline='') as f:
                    w=csv.DictWriter(f,fieldnames=list(mapped[0]));w.writeheader();w.writerows(mapped)
            (dest/'README.md').write_text(f'# 当前图 {fig}（v0.25）\n\nFIGURE_LEGEND.md 为当前图注，PANEL_DATA_MAP.csv 对应现成绘图表。根目录 RUN_ALL_FIGURES.py 直接重画十一图。新图 3、4、S3、S4 的 ready_data/ 是便于独立绘图的副本；修改内置脚本的数据时，请编辑映射中 plot_input 指向的 03_data/commitment_narrative/ 表。其余七图编辑原映射 data_file 对应文件。全部表都已可直接绘图，无需清洗。旧图及其数据入口在 90_archive/v024/。\n')
    (STAGE/'README_FIRST.md').write_text('''# AIDRBench 全图与完整恢复包 v14

当前英文正文/SI **v0.25**、中文 **v19**，六张主图、五张补充图、21 张补充表。采用已有冻结实验，不新增模拟或重新选择报价。

## 直接修改与绘图

1. 打开 `OPEN_ME.html` 查看论文、图和数据入口。
2. 每图目录 `01_main/F01`–`F06`、`02_supp/S01`–`S05` 有图片、图注及 `PANEL_DATA_MAP.csv`。使用内置代码改数据时，编辑映射中 `plot_input`（新四图）或 `data_file`（其余七图）指向的文件。新图的 `ready_data/` 是可直接交给其他软件绘制的完整 CSV 副本，内置脚本不会自动读取对副本的修改。
3. 全部重画：`python RUN_ALL_FIGURES.py`。使用已有绘图环境：`python RUN_ALL_FIGURES.py --use-current-python --output MY_FIGURES`。脚本只读现成表，不运行模拟或重新抽样。首次自动安装依赖需要网络，使用 Python 3.12。
4. 仅改本次四张图：`python 04_code/commitment_narrative/plot_narrative.py --data 03_data/commitment_narrative --output MY_FIGURES`。图 4c 的文字可以直接修改 `decision_steps.csv`。

图 3c 展示次数/资源时间 × 原序/置乱；图 4 展示供给余量与承诺决策。旧 63/80 交叉评分移到 S3d，PV 移到 S4。图 5 图注明确采用放松 PI 统计量。旧 v0.24 文稿及全部十一图保留在 `90_archive/v024/`。

## 完整数据与恢复

`03_data/` 保留五档工作负载和 PV 全部数据；`repeat_mechanism/`、`operating_tradeoffs/`、`commitment_mechanisms/` 保留之前完整实验、成功与失败、冻结输入、PI 见证和生产任务资源时间。新增 `commitment_narrative/` 是现成绘图表及由原轨迹核对得到的供给余量，包含两个请求的全部 640 条记录，不替代原始数据。

研究复算依赖和绘图依赖分开：

```bash
python -m pip install -r requirements_replay.txt
python 04_code/commitment_mechanisms/replay_one.py --data 03_data/commitment_mechanisms --output REPLAY_NEW
python 04_code/commitment_mechanisms/replay_pi.py --data 03_data/commitment_mechanisms --previous-data 03_data/operating_tradeoffs --output REPLAY_PI
```

因果入口逐列核对 216 小时的 92 个数值列与缺失位置。PI 入口核对相同约束下的分类与可行见证；调度可不唯一，求解可花费约十分钟。旧绝对路径仅为来源记录，不是这些入口的运行依赖。制图不需要运行这两项复算。

## 核查与范围

`VERIFY_PACKAGE.py` 检查清单中的全部文件。`05_audit/commitment_narrative_v025/` 记录图文对应、重绘和本版修改依据；此前完整轨迹和 PI 复算记录也保留。

零漏期是一条成功序列的判据，资格检验整体成功概率目标为 95%。置乱改变顺序与对齐，不能单独归因于自相关。一次缺口不自动否定概率性合同。旧 PI 放松不保证逐工作组可行。没有新增真实应用暂停恢复实测。作者、基金、许可证和公开归档仍待用户确认；未启动子智能体。
''')
    rows=[]
    for group,tag,count in [('01_main/F','Figure',6),('02_supp/S','Supplementary Figure',5)]:
        for n in range(1,count+1):
            folder=f'{group}{n:02d}';base='AIDRBench_'+tag.replace(' ','_')+'_'+str(n)
            rows.append(f'<tr><td>{tag} {n}</td><td><a href="{folder}/artwork/{base}.png">PNG</a> · <a href="{folder}/artwork/{base}.pdf">PDF</a> · <a href="{folder}/artwork/{base}.svg">SVG</a></td><td><a href="{folder}/PANEL_DATA_MAP.csv">绘图数据映射</a> · <a href="{folder}/FIGURE_LEGEND.md">图注</a></td></tr>')
    (STAGE/'OPEN_ME.html').write_text('<!doctype html><meta charset="utf-8"><title>AIDRBench v0.25 / v14</title><style>body{font:16px system-ui;max-width:1000px;margin:40px auto;line-height:1.7}td{padding:8px 18px;border-bottom:1px solid #ddd}a{color:#235a78}</style><h1>AIDRBench 全图与恢复包 v14</h1><p>正文/SI v0.25 · 中文 v19 · 六主图、五补充图、21 补充表</p><p><a href="00_manuscript/AIDRBench_Nature_Communications_v0.25_content_revision.pdf">正文 PDF</a> · <a href="00_manuscript/AIDRBench_Nature_Communications_v0.25_Supplementary_Information_content_revision.pdf">补充 PDF</a> · <a href="00_manuscript/chinese/main_zh.md">正文中文</a> · <a href="00_manuscript/chinese/supplement_zh.md">补充中文</a></p><p><a href="README_FIRST.md">使用说明</a> · <a href="05_audit/commitment_narrative_v025/RESULTS_AND_REASONS_ZH.md">本版修改依据</a></p><table>'+''.join(rows)+'</table>')
    (STAGE/'CURRENT_VERSION.json').write_text(json.dumps(dict(manuscript='0.25',chinese_reader='v19',package='v14',main_figures=6,supplementary_figures=5,numbered_supplementary_tables=21,new_simulations=0,new_offer_selection=False,complete_previous_data_preserved=True,author_metadata_pending=True),indent=2)+'\n')
    for folder in ['04_code/commitment_narrative','05_audit/commitment_narrative_v025']:
        for p in HERE.iterdir():
            if p.is_file() and p.suffix in ['.py','.md','.json','.csv'] and p.name not in ['package_validation.json','FINAL_STATUS.md']:shutil.copyfile(p,STAGE/folder/p.name)
    for folder in ['00_manuscript','01_main','02_supp']:
        for p in (STAGE/folder).rglob('*.md'):
            for dest in re.findall(r'!\[[^]]*\]\(([^)]+)\)',p.read_text()):assert not dest.startswith('/') and (p.parent/dest).is_file(),(p,dest)

def archive():
    assert not TARGET.exists();refresh()
    old={r['path']:r for r in csv.DictReader((OLD/'FILE_INVENTORY.csv').open())}
    print('Hash full staging inventory',flush=True)
    excluded={STAGE/'FILE_INVENTORY.csv',STAGE/'SHA256SUMS.txt'}
    files=sorted(p for p in STAGE.rglob('*') if p.is_file() and p not in excluded)
    rows=[dict(path=p.relative_to(STAGE).as_posix(),bytes=p.stat().st_size,sha256=sha(p)) for p in files]
    with (STAGE/'FILE_INVENTORY.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['path','bytes','sha256']);w.writeheader();w.writerows(rows)
    (STAGE/'SHA256SUMS.txt').write_text(''.join(f'{r["sha256"]}  {r["path"]}\n' for r in rows)+f'{sha(STAGE/"FILE_INVENTORY.csv")}  FILE_INVENTORY.csv\n')
    expected={p.relative_to(STAGE).as_posix() for p in STAGE.rglob('*') if p.is_file()}
    changed=[r['path'] for r in rows if r['path'] not in old or r['sha256']!=old[r['path']]['sha256']]+['FILE_INVENTORY.csv','SHA256SUMS.txt']
    tmp=TARGET.with_suffix('.building.zip');assert not tmp.exists()
    print('Reuse compressed original data and append revised material',flush=True);shutil.copyfile(PREVIOUS,tmp)
    notes=subprocess.run(['zipnote',str(tmp)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,check=True);assert not notes.stderr,notes.stderr[:1000]
    updated=[]
    for line in notes.stdout.splitlines():
        updated.append(line)
        if line.startswith('@ '+OLD.name+'/'):updated.append('@='+STAGE.name+line[len('@ '+OLD.name):])
    subprocess.run(['zipnote','-w',str(tmp)],input='\n'.join(updated)+'\n',text=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,check=True)
    with zipfile.ZipFile(tmp) as z:removed=[name for name in z.namelist() if name.removeprefix(STAGE.name+'/') not in expected]
    if removed:subprocess.run(['zip','-q','-d',str(tmp),*removed],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
    subprocess.run(['zip','-q','-1',str(tmp),'-@'],input=''.join(STAGE.name+'/'+p+'\n' for p in changed),text=True,cwd=STAGE.parent,check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
    fixes=0
    with zipfile.ZipFile(tmp) as z,tmp.open('r+b') as stream:
        for member in z.infolist():
            stream.seek(member.header_offset);header=stream.read(8);assert header[:4]==b'PK\x03\x04'
            local=struct.unpack_from('<H',header,4)[0]
            if local!=member.extract_version:
                assert local==20 and member.extract_version==45
                stream.seek(member.header_offset+4);stream.write(struct.pack('<H',45));fixes+=1
    print('Verify every member SHA-256, CRC and extraction header',flush=True)
    digests={r['path']:r['sha256'] for r in rows}|{p:sha(STAGE/p) for p in ['FILE_INVENTORY.csv','SHA256SUMS.txt']}
    with zipfile.ZipFile(tmp) as z,tmp.open('rb') as stream:
        names=z.namelist();assert len(names)==len(set(names));assert set(names)=={STAGE.name+'/'+p for p in expected}
        for member in z.infolist():
            stream.seek(member.header_offset+4);assert struct.unpack('<H',stream.read(2))[0]==member.extract_version
            # Reading to EOF also verifies the stored CRC.
            with z.open(member) as payload:assert hashlib.file_digest(payload,'sha256').hexdigest()==digests[member.filename.removeprefix(STAGE.name+'/')]
    tmp.replace(TARGET)
    result=dict(status='PASS',path=str(TARGET),bytes=TARGET.stat().st_size,sha256=sha(TARGET),files=len(expected),changed_entries=len(changed),all_entry_sha256_verified=True,zip_crc_pass=True,duplicate_entries=False,extraction_version_hints_consistent=True,normalized_local_headers=fixes,manuscript='v0.25',chinese='v19',current_figures=11,previous_release_preserved=True,new_simulations=0)
    (HERE/'package_validation.json').write_text(json.dumps(result,indent=2)+'\n');TARGET.with_suffix('.zip.sha256').write_text(f'{result["sha256"]}  {TARGET.name}\n');print(json.dumps(result,indent=2),flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('action',choices=['prepare','refresh','archive']);a=ap.parse_args();globals()[a.action]()
