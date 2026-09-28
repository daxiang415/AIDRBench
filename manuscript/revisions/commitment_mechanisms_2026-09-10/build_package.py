"""Portable v13 package; preserve the delivered v12 archive and every earlier dataset."""
import argparse,csv,hashlib,json,os,re,shutil,subprocess,zipfile
from importlib.metadata import version
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
OLD=ROOT/'results/exports/AIDRBench_Figures_v12';STAGE=OLD.with_name('AIDRBench_Figures_v13')
PREVIOUS=ROOT/'results/exports/AIDRBench_All_Figures_2026-09-10_v12.zip';TARGET=PREVIOUS.with_name('AIDRBench_All_Figures_2026-09-10_v13.zip')
SOURCE=ROOT/'manuscript/source_data/nature_commitment_mechanisms_v1';ART=ROOT/'docs/figures/commitment_mechanisms_v1/artwork'
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def prepare():
    assert not STAGE.exists() and not TARGET.exists()
    print('Copying complete previous stage',flush=True);shutil.copytree(OLD,STAGE)
    archive=STAGE/'90_archive/v023';archive.mkdir();shutil.move(str(STAGE/'00_manuscript'),archive/'00_manuscript')
    for name in ['README_FIRST.md','CURRENT_VERSION.json','OPEN_ME.html','RUN_ALL_FIGURES.py']:shutil.copyfile(STAGE/name,archive/name)
    for folder in ['01_main/F02','01_main/F03','01_main/F05','01_main/F06','02_supp/S03','02_supp/S05']:shutil.copytree(STAGE/folder,archive/folder)
    (archive/'04_code').mkdir();shutil.copyfile(STAGE/'04_code/plot_results.py',archive/'04_code/plot_results.py')
    print('Copying new complete data',flush=True);shutil.copytree(SOURCE,STAGE/'03_data/commitment_mechanisms')
    for folder in ['04_code/commitment_mechanisms','04_code/aidrbench_project/manuscript/revisions/commitment_mechanisms_2026-09-10','05_audit/commitment_mechanisms_v024']:(STAGE/folder).mkdir(parents=True)
    shutil.copyfile(HERE/'plot_base_relabelled.py',STAGE/'04_code/plot_results.py')
    launch=(OLD/'RUN_ALL_FIGURES.py').read_text();mark="    for manifest,prefix,n in "
    i=launch.index(mark);launch=launch[:i]+"    subprocess.run([str(python),str(ROOT/'04_code/commitment_mechanisms/plot_mechanisms.py'),'--data',str(ROOT/'03_data/commitment_mechanisms'),'--previous-data',str(ROOT/'03_data/operating_tradeoffs'),'--output',str(a.output)],check=True)\n"+launch[i:]
    (STAGE/'RUN_ALL_FIGURES.py').write_text(launch.replace("revision='v0.23'","revision='v0.24'"))
    refresh();print('Stage ready',flush=True)
def refresh():
    assert STAGE.exists();(STAGE/'00_manuscript/chinese').mkdir(parents=True,exist_ok=True);images={}
    dependencies=['numpy','pandas','matplotlib','pyarrow','scipy','gymnasium','PyYAML','pydantic','cvxpy','highspy','osqp','rich','typer','joblib','scikit-learn']
    (STAGE/'requirements_replay.txt').write_text('# Tested with Python 3.12; optional for plotting-only use.\n'+''.join(f'{name}=={version(name)}\n' for name in dependencies))
    shutil.copyfile(ROOT/'data/manifests/sources.yaml',STAGE/'04_code/aidrbench_project/data/manifests/sources.yaml')
    for group,tag,count in [('01_main/F','AIDRBench_Figure_',6),('02_supp/S','AIDRBench_Supplementary_Figure_',5)]:
        for n in range(1,count+1):
            images[f'{tag}{n}.png']=f'{group}{n:02d}/artwork/{tag}{n}.png'
            for ext in ['pdf','svg','png','tiff']:shutil.copyfile(ART/f'{tag}{n}.{ext}',STAGE/f'{group}{n:02d}/artwork/{tag}{n}.{ext}')
    def portable(t,folder):return re.sub(r'!\[([^]]*)\]\(([^)]+)\)',lambda m:f'![{m[1]}]({os.path.relpath(images[Path(m[2]).name],folder)})',t)
    docs=[(ROOT/'manuscript'/name).read_text() for name in ['nature_communications_article.md','supplementary_information.md']]
    for name,text in zip(['nature_communications_article.md','supplementary_information.md'],docs):(STAGE/'00_manuscript'/name).write_text(portable(text,'00_manuscript'))
    for p in (ROOT/'docs/chinese_reader/v18').glob('*.md'):(STAGE/'00_manuscript/chinese'/p.name).write_text(portable(p.read_text(),'00_manuscript/chinese'))
    for p in (ROOT/'manuscript/exports').glob('AIDRBench_Nature_Communications_v0.24*.pdf'):shutil.copyfile(p,STAGE/'00_manuscript'/p.name)
    results=[x.strip() for x in re.split(r'(?m)(?=^### )',docs[0].split('## Results\n')[1].split('## Discussion\n')[0]) if x.strip()];assert len(results)==6
    maps=list(csv.DictReader((SOURCE/'PANEL_DATA_MAP.csv').open()))
    for group,tag,count,doc in [('01_main/F','Figure',6,docs[0]),('02_supp/S','Supplementary Figure',5,docs[1])]:
        for n in range(1,count+1):
            folder=f'{group}{n:02d}';dest=STAGE/folder;fig=str(n) if tag=='Figure' else f'S{n}'
            legend=re.search(rf'^### {tag} {n} \| .*?(?=^### |^## |\Z)',doc,re.M|re.S);assert legend
            (dest/'FIGURE_LEGEND.md').write_text(portable(legend[0].strip(),folder)+'\n')
            if tag=='Figure':(dest/'MANUSCRIPT_CONTEXT.md').write_text(portable(results[n-1],folder)+'\n')
            rows=[r for r in maps if r['figure']==fig]
            if rows:
                ready=dest/'ready_data';ready.mkdir(exist_ok=True);mapped=[]
                for row in rows:
                    source=(SOURCE.parent/'nature_operating_tradeoffs_v1'/Path(row['table']).name) if row['table'].startswith('../') else SOURCE/row['table']
                    filename=('previous_' if row['table'].startswith('../') else '')+source.name;shutil.copyfile(source,ready/filename);mapped.append(row|dict(table='ready_data/'+filename,complete_data='../../03_data/commitment_mechanisms/'))
                with (dest/'PANEL_DATA_MAP.csv').open('w',newline='') as out:w=csv.DictWriter(out,fieldnames=list(mapped[0]));w.writeheader();w.writerows(mapped)
            (dest/'README.md').write_text(f'# 当前图 {fig}（v0.24）\n\n图注见 FIGURE_LEGEND.md。PANEL_DATA_MAP.csv 指向现成绘图表，保留全部数据无需预处理。根目录 RUN_ALL_FIGURES.py 直接重绘十一图。图 3、6、S3、S5 的新表在 ready_data/，代码为 04_code/commitment_mechanisms/plot_mechanisms.py；其他图继承完整源表，图 2、5 的旧 PI 现标为放松规划统计量。\n')
    (STAGE/'README_FIRST.md').write_text('''# AIDRBench 全图与完整恢复包 v13

当前英文正文/SI **v0.24**，中文 **v18**，六张主图、五张补充图、21 张补充表。图 3、6、S3、S5 重绘；图 2、5 更正旧 PI 的数学含义。其他数据与图完整保留。旧 v0.23 文稿和被替换图在 `90_archive/v023/`。

## 直接修改和绘图

1. 打开 `OPEN_ME.html` 查看图片、图注、论文及数据入口。
2. 每图目录 `01_main/F01`–`F06`、`02_supp/S01`–`S05` 有图片、图注及面板数据映射。新增四图 `ready_data/` 是直接绘图的 CSV，不需要清洗或模拟。
3. 一次重画全部图：`python RUN_ALL_FIGURES.py`。已有绘图库时：`python RUN_ALL_FIGURES.py --use-current-python --output MY_FIGURES`。脚本只读现成表，不重新计算实验或统计量。

## 完整数据与恢复

`03_data/`、`03_data/repeat_mechanism/`、`03_data/operating_tradeoffs/` 保留前版全部数据。新增 `03_data/commitment_mechanisms/` 含 3,040 次完整重放、656,640 小时行、720 个冻结输入、38 个可行性诊断及任务级资源时间重建。CSV 可直接绘图，Parquet 保存完整字段；成功与失败都保留。

重放一条新控制轨迹（使用 Python 3.12；首次安装以下研究依赖，绘图无需安装优化器）：

```bash
python -m pip install -r requirements_replay.txt
python 04_code/commitment_mechanisms/replay_one.py --data 03_data/commitment_mechanisms --output REPLAY_NEW
```

默认 989000、参考八小时、4.423682 kW；逐项核对全部 92 个数值列和缺失值位置。可使用 --role、--variant、--seed、--program、--fraction 选择账本内任一条件，包括 workload 角色的资源时间测试。

恢复严格时间窗 PI 对照：

```bash
python 04_code/commitment_mechanisms/replay_pi.py --data 03_data/commitment_mechanisms --previous-data 03_data/operating_tradeoffs --output REPLAY_PI
```

默认重现参考种子 985002 的“因果失败、PI 可行”。使用 --id 可选其他已交付诊断。可行解可能不唯一，核验分类与全部约束；旧绝对路径仅为来源记录，不是执行依赖。

## 本版结果

新参考四/八小时报价分别 5.60/4.42 kW，两种服务标准选值相同。按真实任务资源时间而非提交次数加权后，原序 2.95 kW 从 80/80 变为 31/80，4.42 kW 为 0/80，所有无响应基线可行。旧 PI 数值属于累计约束放松，不能解释为严格作业可行容量；新诊断使用严格工作组时间窗。价格以参考分布为条件，不能转用到外部失败工作负载。

`VERIFY_PACKAGE.py` 验证全包清单和校验和。逐项依据、结果更正、代码与验证记录在 `05_audit/commitment_mechanisms_v024/`。作者、基金、许可证与公开归档仍待用户确定。没有调用子智能体。
''')
    links=[]
    for group,tag,count in [('01_main/F','Figure',6),('02_supp/S','Supplementary Figure',5)]:
        for n in range(1,count+1):
            folder=f'{group}{n:02d}';base='AIDRBench_'+tag.replace(' ','_')+'_'+str(n)
            links.append(f'<tr><td>{tag} {n}</td><td><a href="{folder}/artwork/{base}.png">PNG</a> · <a href="{folder}/artwork/{base}.pdf">PDF</a> · <a href="{folder}/artwork/{base}.svg">SVG</a></td><td><a href="{folder}/PANEL_DATA_MAP.csv">现成绘图表映射</a> · <a href="{folder}/FIGURE_LEGEND.md">图注</a></td></tr>')
    (STAGE/'OPEN_ME.html').write_text('<!doctype html><meta charset="utf-8"><title>AIDRBench v0.24 / v13</title><style>body{font:16px system-ui;max-width:1000px;margin:40px auto;line-height:1.7}td,th{padding:8px 18px;text-align:left;border-bottom:1px solid #ddd}a{color:#235a78}</style><h1>AIDRBench 完整绘图包 v13</h1><p>正文/SI v0.24 · 中文 v18 · 六主图、五补充图、21 补充表</p><p><a href="00_manuscript/AIDRBench_Nature_Communications_v0.24_content_revision.pdf">正文 PDF</a> · <a href="00_manuscript/AIDRBench_Nature_Communications_v0.24_Supplementary_Information_content_revision.pdf">补充 PDF</a> · <a href="00_manuscript/chinese/main_zh.md">正文中文</a> · <a href="00_manuscript/chinese/supplement_zh.md">补充中文</a></p><p><a href="README_FIRST.md">使用说明</a> · <a href="03_data/commitment_mechanisms/README.md">完整新数据</a> · <a href="05_audit/commitment_mechanisms_v024/RESULTS_AND_REASONS_ZH.md">结果与依据</a></p><table>'+''.join(links)+'</table>')
    (STAGE/'CURRENT_VERSION.json').write_text(json.dumps(dict(manuscript='0.24',chinese_reader='v18',package='v13',main_figures=6,supplementary_figures=5,numbered_supplementary_tables=21,new_complete_replays=3040,new_hourly_rows=656640,new_frozen_inputs=720,pi_diagnostics=38,author_metadata_pending=True),indent=2)+'\n')
    for folder in ['04_code/commitment_mechanisms','04_code/aidrbench_project/manuscript/revisions/commitment_mechanisms_2026-09-10','05_audit/commitment_mechanisms_v024']:
        for p in HERE.iterdir():
            if p.is_file() and p.suffix in ['.py','.json','.md','.csv'] and p.name!='package_validation.json':shutil.copyfile(p,STAGE/folder/p.name)
    (STAGE/'04_code/README.md').write_text('当前 v0.24：根目录 RUN_ALL_FIGURES.py 先运行继承绘图脚本，再由 commitment_mechanisms/plot_mechanisms.py 替换图 3、6、S3、S5。plot_results.py 已把图 2、5 的早期 PI 数值改标为放松规划统计量。commitment_mechanisms/replay_one.py 和 replay_pi.py 可分别恢复新控制轨迹与严格 PI 诊断。所有完整历史脚本保留来源路径；直接绘图和这两个恢复入口使用包内相对路径。\n')
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
        for rel in sorted(expected):
            with z.open(STAGE.name+'/'+rel) as stream:assert hashlib.file_digest(stream,'sha256').hexdigest()==sha(STAGE/rel),rel
        assert z.testzip() is None
    tmp.replace(TARGET);result=dict(status='PASS',path=str(TARGET),staging=str(STAGE),bytes=TARGET.stat().st_size,sha256=sha(TARGET),files=len(expected),changed_entries=len(changed),all_entry_sha256_verified=True,zip_crc_pass=True,duplicate_entries=False,manuscript='v0.24',chinese='v18',current_figures=11,previous_release_preserved=True)
    (HERE/'package_validation.json').write_text(json.dumps(result,indent=2)+'\n');TARGET.with_suffix('.zip.sha256').write_text(f'{result["sha256"]}  {TARGET.name}\n');print(json.dumps(result,indent=2),flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('action',choices=['prepare','refresh','archive']);a=ap.parse_args();globals()[a.action]()
