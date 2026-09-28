"""Version 10 complete redraw and replay handoff; staged before final checksums."""
import argparse
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
STAGE=ROOT/'results/exports/AIDRBench_Figures_v10'
TARGET=ROOT/'results/exports/AIDRBench_All_Figures_2026-09-09_v10.zip'
ART=ROOT/'docs/figures/repeat_mechanism_v1/artwork'
SOURCE=ROOT/'manuscript/source_data/nature_repeat_mechanism_v1'


def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def copy(p,q):q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,q)


def prepare():
    assert not STAGE.exists(),'Use the already prepared stage and --finish; do not overwrite it.'
    shutil.copytree(ROOT/'results/exports/AIDRBench_Figures_v9',STAGE)
    # Keep previous documents/audits clearly historical; all original numerical inputs remain.
    for folder in ['00_manuscript','05_audit']:
        dest=STAGE/'90_archive/v020'/folder;dest.parent.mkdir(parents=True,exist_ok=True)
        shutil.move(str(STAGE/folder),dest);(STAGE/folder).mkdir()
    for name in ['FILE_INVENTORY.csv','SHA256SUMS.txt']:
        (STAGE/name).unlink()  # only obsolete manifests in this newly created version-10 stage
    shutil.copytree(SOURCE,STAGE/'03_data/repeat_mechanism')
    for p in HERE.glob('*.py'):
        copy(p,STAGE/'04_code/repeat_mechanism'/p.name)
        copy(p,STAGE/'04_code/aidrbench_project/manuscript/revisions/repeat_mechanism_2026-09-09'/p.name)
    for name in ['protocol.json','selection.json','confirmation_launch.json']:
        copy(HERE/name,STAGE/'04_code/aidrbench_project/manuscript/revisions/repeat_mechanism_2026-09-09'/name)
    for name in ['render_review_tex.py','render_supplementary_tex.py','review_figure_inputs.py','web_figure_inputs.py']:
        copy(ROOT/'scripts'/name,STAGE/'04_code/aidrbench_project/scripts'/name)
    copy(HERE/'package_launcher.py',STAGE/'RUN_ALL_FIGURES.py')
    print('Prepared complete stage',STAGE,flush=True)


def finish():
    assert STAGE.is_dir()
    for p in SOURCE.iterdir():
        if p.is_file():copy(p,STAGE/'03_data/repeat_mechanism'/p.name)
    for folder in ['01_main','02_supp']:
        dest=STAGE/'90_archive/v020'/folder
        if not dest.exists():shutil.copytree(ROOT/'results/exports/AIDRBench_Figures_v9'/folder,dest)
    artwork={}
    for prefix,count,folder in [('AIDRBench_Figure_',6,'01_main/F'),('AIDRBench_Supplementary_Figure_',5,'02_supp/S')]:
        for n in range(1,count+1):
            for ext in ['pdf','svg','png','tiff']:
                name=f'{prefix}{n}.{ext}';relative=f'{folder}{n:02d}/artwork/{name}'
                copy(ART/name,STAGE/relative);artwork[name]=relative
    def portable(text,folder):
        return re.sub(r'!\[([^]]*)\]\(([^)]+)\)',lambda m:f'![{m[1]}]({os.path.relpath(artwork[Path(m[2]).name],folder)})',text)
    main=(ROOT/'manuscript/nature_communications_article.md').read_text()
    supplement=(ROOT/'manuscript/supplementary_information.md').read_text()
    for name in ['nature_communications_article.md','supplementary_information.md']:
        (STAGE/'00_manuscript'/name).write_text(portable((ROOT/'manuscript'/name).read_text(),'00_manuscript'))
    for p in (ROOT/'docs/chinese_reader/v15').glob('*.md'):
        dest=STAGE/'00_manuscript/chinese'/p.name;dest.parent.mkdir(exist_ok=True)
        dest.write_text(portable(p.read_text(),'00_manuscript/chinese'))
    for p in (ROOT/'manuscript/exports').glob('AIDRBench_Nature_Communications_v0.21*.pdf'):copy(p,STAGE/'00_manuscript'/p.name)
    sections=[x.strip() for x in re.split(r'(?m)(?=^### )',main.split('## Results\n')[1].split('## Discussion\n')[0]) if x.strip()]
    assert len(sections)==6
    for group,nfig,tag,doc in [('01_main/F',6,'Figure',main),('02_supp/S',5,'Supplementary Figure',supplement)]:
        for n in range(1,nfig+1):
            folder=f'{group}{n:02d}'
            match=re.search(rf'^### {tag} {n} \| .*?(?=^### |^## |\Z)',doc,re.M|re.S);assert match
            (STAGE/folder/'FIGURE_LEGEND.md').write_text(portable(match[0].strip(),folder)+'\n')
            if group=='01_main/F':(STAGE/folder/'MANUSCRIPT_CONTEXT.md').write_text(portable(sections[n-1],folder)+'\n')
    mappings={
      '01_main/F03':['confirmation_summary.csv','selected_offers.csv','paired_controller_contrasts.csv','illustration_original.csv','illustration_all_window_mpc.csv','illustration_windows.csv'],
      '01_main/F06':['economic_primary.csv','economic_sensitivity.csv','confirmation_ledgers.csv'],
      '02_supp/S03':['ready_hourly_curves.csv','development_summary.csv','selected_offers.csv','confirmation_summary.csv','hourly_partition_index.csv']}
    for folder,names in mappings.items():
        (STAGE/folder/'PANEL_DATA_MAP.csv').write_text('data_file\n'+''.join('../../03_data/repeat_mechanism/'+name+'\n' for name in names)+
            ('../../03_data/economic_primary.csv\n../../03_data/economic_price_sensitivity.csv\n' if folder.endswith('F06') else ''))
        (STAGE/folder/'README.md').write_text('# 当前 v0.21 图件\n\n图在 artwork/；现成数据表见 PANEL_DATA_MAP.csv；修改 ../../04_code/repeat_mechanism/plot_extension.py 并运行根目录 RUN_ALL_FIGURES.py 即可。图 6 的单次事件面板仍读取 03_data/ 原五档数据；重复调用面板读取 repeat_mechanism/ 新数据。无需预处理或重新统计。\n')
    for p in HERE.iterdir():
        if p.is_file() and p.suffix in ['.md','.json','.csv','.ris'] and p.name!='package_validation.json':copy(p,STAGE/'05_audit'/p.name)
    for p in ART.glob('*manifest.json'):copy(p,STAGE/'05_audit'/p.name)
    for p in HERE.glob('*.py'):
        copy(p,STAGE/'04_code/repeat_mechanism'/p.name)
        copy(p,STAGE/'04_code/aidrbench_project/manuscript/revisions/repeat_mechanism_2026-09-09'/p.name)
    for name in ['render_review_tex.py','render_supplementary_tex.py']:copy(ROOT/'scripts'/name,STAGE/'04_code/aidrbench_project/scripts'/name)
    copy(HERE/'package_launcher.py',STAGE/'RUN_ALL_FIGURES.py')
    (STAGE/'README_FIRST.md').write_text('''# 全部 11 图、完整数据与直接重绘包 v10

当前论文 v0.21；中文阅读稿 v15。主图 3、主图 6、补充图 3 已加入新的恢复控制和独立确认结果，其他八图保留五档工作资格计算。

1. 阅读全文：00_manuscript/；中文全文与中英对照在 chinese/。正文 PDF 含六图，补充 PDF 含五图和十二张表。
2. 直接重画：使用 Python 3.12，运行 `python RUN_ALL_FIGURES.py`，首次自动安装绘图库；已有环境用 `python RUN_ALL_FIGURES.py --use-current-python`。
3. 输出：REDRAW_OUTPUT/，全部 11 张图各有 PDF、SVG、PNG、TIFF。PDF/SVG 保留矢量和文字。
4. 改图 3、6、S3：编辑 04_code/repeat_mechanism/plot_extension.py；其他图编辑 04_code/plot_results.py 或 plot_supplement.py。
5. 改数值：每图的 PANEL_DATA_MAP.csv 指向现成面板表。均值、分位数、容量、成功率下界和经济门槛均已计算，不需要处理生产轨迹或重新模拟。
6. 完整数据：03_data/ 保留前版全部五档数据；03_data/repeat_mechanism/ 另有本轮 23,900 条完整回放、5,162,400 小时行、全部六项判定及 2,000 套完整冻结输入。hourly_full/ 保留全部字段，hourly_plot_csv/ 可直接打开；ready_hourly_curves.csv 已给出均值和分位数。
7. 完整计算恢复：下述 replay_one.py 可直接从包内输入重跑一条已交付情景，并自动与包内完整小时数据逐列比较。不需要下载原始生产数据或抽样作业。进一步研究可使用 04_code/aidrbench_project/ 的完整模拟器与冻结驱动。
8. 历史：90_archive/v020/ 保存旧文稿与审核；原 v8 压缩包保留旧研究。当前结果从本目录入口读取。

## 验证和运行一条完整情景

绘图环境只需 requirements_plot.txt。运行模型时按 04_code/aidrbench_project/pyproject.toml 安装项目依赖：

```bash
python -m pip install -e 04_code/aidrbench_project
python 04_code/repeat_mechanism/replay_one.py --data 03_data/repeat_mechanism --output REPLAY_f10_970000 --controller-config 04_code/aidrbench_project/configs/controller/nature_robust_mpc_v1.yaml
python VERIFY_PACKAGE.py
```

默认重跑 10% 工作资格、8 小时调用/12 小时间隔、75% 承诺、逐次恢复约束 MPC。输出目录须是新目录，以免覆盖此前回放。其他选项可通过 --help 查看，已有组合以 confirmation_ledgers.csv 为准。原绝对 trace_path/receipt_path 字段保留计算来源；实际包内轨迹按 hourly_partition_index.csv 和 scenario_seed 读取。

本文结果仍以模型和声明价格为条件。作者信息、许可证和公开归档 DOI 保持待定。本轮未启动子智能体。
''')
    (STAGE/'04_code/README.md').write_text('直接重画全部图见根目录 README_FIRST.md。图 3、6、S3 使用 repeat_mechanism/plot_extension.py，其他图使用本目录原 plot_results.py 和 plot_supplement.py。根目录脚本先读取旧五档表，再用新表替换三张更新图，最终输出始终为 v0.21。\n\n完整冻结情景的直接回放见 repeat_mechanism/replay_one.py，原五档输入恢复工具 restore_scenario.py 仍保留。aidrbench_project/ 含模拟器、依赖、配置、原研究驱动及本轮恢复干预；全研究驱动依赖项目路径和原第三方资源，直接绘图和单情景回放不需要它们。\n')
    (STAGE/'CURRENT_VERSION.json').write_text(json.dumps(dict(manuscript='0.21',chinese_reader='v15',package='v10',main_figures=6,supplementary_figures=5,
        revised_figures=['3','6','S3'],new_replays=23900,new_hourly_rows=5162400,source_tables_ready=True,author_metadata_pending=True),indent=2)+'\n')
    gallery=[]
    for prefix,count,folder in [('AIDRBench_Figure_',6,'01_main/F'),('AIDRBench_Supplementary_Figure_',5,'02_supp/S')]:
        for n in range(1,count+1):gallery.append(f'<section><h2>{"主图" if count==6 else "补充图"} {n}</h2><img src="{folder}{n:02d}/artwork/{prefix}{n}.png" style="max-width:100%"></section>')
    (STAGE/'OPEN_ME.html').write_text('<!doctype html><meta charset="utf-8"><title>AIDRBench v0.21 · 完整绘图包 v10</title><style>body{max-width:1000px;margin:36px auto;font-family:sans-serif}section{margin:45px 0}</style><h1>论文 v0.21 · 全部 11 图</h1><p>直接重绘和改图方法见 README_FIRST.md。中文全文在 00_manuscript/chinese/。</p>'+''.join(gallery))
    redraw=Path(tempfile.mkdtemp(prefix='aidrbench_v10_redraw_'))
    subprocess.run([sys.executable,str(STAGE/'RUN_ALL_FIGURES.py'),'--use-current-python','--output',str(redraw)],check=True)
    comparisons=[]
    for name in artwork:
        if name.endswith('.png'):
            assert sha(redraw/name)==sha(ART/name),name
            comparisons.append(dict(figure=name,sha256=sha(redraw/name)))
    (STAGE/'05_audit/redraw_validation.json').write_text(json.dumps(dict(status='PASS',all_eleven_png_byte_identical=True,source='delivered tables and scripts only',figures=comparisons),indent=2)+'\n')
    replay=Path(tempfile.mkdtemp(prefix='aidrbench_v10_replay_'))
    env=dict(os.environ);env.pop('PYTHONPATH',None)
    subprocess.run([sys.executable,str(STAGE/'04_code/repeat_mechanism/replay_one.py'),'--data',str(STAGE/'03_data/repeat_mechanism'),
        '--output',str(replay),'--controller-config',str(STAGE/'04_code/aidrbench_project/configs/controller/nature_robust_mpc_v1.yaml')],check=True,cwd=replay,env=env)
    copy(replay/'replay_validation.json',STAGE/'05_audit/delivered_replay_validation.json')
    for p in STAGE.rglob('*.md'):
        if '90_archive' in p.parts:continue
        for m in re.finditer(r'!\[[^]]*\]\(([^)]+)\)',p.read_text()):assert (p.parent/m[1]).resolve().is_file(),(p,m[1])
    # Python may create bytecode during verification; it is not part of the handoff.
    for p in list(STAGE.rglob('*.pyc')):p.unlink()
    files=sorted(p for p in STAGE.rglob('*') if p.is_file() and p.name not in ['FILE_INVENTORY.csv','SHA256SUMS.txt'])
    buf=io.StringIO();writer=csv.writer(buf);writer.writerow(['path','bytes','sha256'])
    for p in files:writer.writerow([p.relative_to(STAGE).as_posix(),p.stat().st_size,sha(p)])
    (STAGE/'FILE_INVENTORY.csv').write_text(buf.getvalue());files.append(STAGE/'FILE_INVENTORY.csv')
    (STAGE/'SHA256SUMS.txt').write_text(''.join(f'{sha(p)}  {p.relative_to(STAGE).as_posix()}\n' for p in sorted(files)))
    subprocess.run([sys.executable,str(STAGE/'VERIFY_PACKAGE.py')],check=True)
    temporary=TARGET.with_suffix('.building.zip')
    if TARGET.exists() and shutil.which('zip'):
        # A final artwork/layout correction need only replace changed entries.
        # Compare content hashes rather than timestamps; Info-ZIP replaces entries.
        with zipfile.ZipFile(TARGET) as z:
            old_inventory=list(csv.DictReader(io.StringIO(z.read(STAGE.name+'/FILE_INVENTORY.csv').decode())))
            old_hashes={r['path']:r['sha256'] for r in old_inventory}
        new_inventory=list(csv.DictReader(io.StringIO((STAGE/'FILE_INVENTORY.csv').read_text())))
        changes=[r['path'] for r in new_inventory if old_hashes.get(r['path'])!=r['sha256']]
        changes+=['FILE_INVENTORY.csv','SHA256SUMS.txt']
        shutil.copyfile(TARGET,temporary)
        subprocess.run(['zip','-q',str(temporary),*[STAGE.name+'/'+name for name in changes]],check=True,cwd=STAGE.parent)
        print('Replaced changed archive entries:',len(changes),flush=True)
    else:
        with zipfile.ZipFile(temporary,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
            for p in sorted(STAGE.rglob('*')):
                if p.is_file():z.write(p,STAGE.name+'/'+p.relative_to(STAGE).as_posix(),compress_type=zipfile.ZIP_STORED if p.suffix=='.zip' else zipfile.ZIP_DEFLATED)
    with zipfile.ZipFile(temporary) as z:
        assert len(z.namelist())==len(set(z.namelist()))
        assert set(z.namelist())=={STAGE.name+'/'+p.relative_to(STAGE).as_posix() for p in STAGE.rglob('*') if p.is_file()}
        assert z.testzip() is None
    temporary.replace(TARGET)
    report=dict(status='PASS',path=str(TARGET),bytes=TARGET.stat().st_size,sha256=sha(TARGET),staging=str(STAGE),
        files=len(files)+1,all_eleven_redraws_identical=True,delivered_replay_pass=True,all_payload_checksums_pass=True,zip_crc_pass=True)
    TARGET.with_suffix('.zip.sha256').write_text(f'{report["sha256"]}  {TARGET.name}\n')
    (HERE/'package_validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2),flush=True)


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--prepare',action='store_true');ap.add_argument('--finish',action='store_true');a=ap.parse_args()
    if a.prepare:prepare()
    if a.finish:finish()
