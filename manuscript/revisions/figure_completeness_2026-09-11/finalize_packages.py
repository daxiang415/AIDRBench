"""Freeze v0.26 deliverables and v15 complete recovery, with checked ZIP payloads."""
import csv
import hashlib
import html
import json
from pathlib import Path
import shutil
import zipfile

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
DEST=ROOT/'results/exports/AIDRBench_Submission_v0.26_2026-09-11'
EXPORT=DEST.parent


def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def inventory(folder,files):
    rows=[dict(path=p.relative_to(folder).as_posix(),bytes=p.stat().st_size,sha256=sha(p)) for p in files]
    with (folder/'FILE_MANIFEST.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['path','bytes','sha256']);w.writeheader();w.writerows(rows)
    (folder/'SHA256SUMS.txt').write_text(''.join(f'{r["sha256"]}  {r["path"]}\n' for r in rows))
    return rows


def create_zip(path,files,base,prefix=''):
    if path.exists():raise SystemExit(f'Refusing to overwrite frozen package: {path}')
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED,compresslevel=1,allowZip64=True) as z:
        for p in files:
            z.write(p,prefix+p.relative_to(base).as_posix(),compress_type=zipfile.ZIP_STORED if p.suffix=='.zip' else zipfile.ZIP_DEFLATED)
    with zipfile.ZipFile(path) as z:
        assert len(z.namelist())==len(set(z.namelist()))
        assert z.testzip() is None
        count=len(z.namelist())
    digest=sha(path);path.with_suffix('.zip.sha256').write_text(digest+'  '+path.name+'\n')
    print(f'PASS {path.name}: {path.stat().st_size:,} bytes / {count} entries',flush=True)
    return dict(file=path.name,bytes=path.stat().st_size,sha256=digest,entries=count,crc_pass=True)


def main():
    verification=json.loads((HERE/'verification.json').read_text());assert verification['status']=='PASS'
    full=DEST/'05_Full_Data';full.mkdir(exist_ok=True)
    previous=ROOT/'results/exports/AIDRBench_All_Figures_2026-09-10_v14.zip'
    saved=full/previous.name
    if not saved.exists():shutil.copyfile(previous,saved)
    assert sha(saved)=='e7d2095b32e3ad8af8ca396d7260a494120e52357b52342c6b395c91785cb923'
    print('Previous 13.39-GB recovery ZIP preserved and SHA-256 verified',flush=True)
    legacy=full/'historical_v4_with_v08_sources'
    if not legacy.exists():shutil.copytree(ROOT/'results/exports/AIDRBench_All_Figures_2026-09-08_v4',legacy)
    (full/'README_ZH.md').write_text('''# 历史数据与完整恢复

当前十四图使用外层 `04_Redraw_Ready/`。这里的旧文件均为溯源，不能覆盖外层现版。

- `AIDRBench_All_Figures_2026-09-10_v14.zip`：完整成功/失败轨迹、冻结输入、PI 诊断和研究复算入口；旧 v0.25 图文原样保留。需要科学复算时解压此 ZIP 后按其说明操作；当前绘图不用解压它。
- `historical_v4_with_v08_sources/`：原 v4 包完整副本，包含合作者 v0.8 图使用的主要源表及后续过渡期图文。它是多版本历史恢复材料，并不是一个独立的当前 v0.26 证据包。主要旧数据在 04_source/，图与面板映射在 01_main/、02_supp/。旧网页限制、版本号和内部相对路径按原样保留，仅用于恢复旧结果。

本层清单核对历史副本，外层清单核对当前提交与绘图文件。第三方原始发布数据仍按原提供方取得；不声称重新分发了整个原始生产数据库。
''')
    for p in HERE.glob('*.py'):shutil.copy2(p,DEST/'07_Provenance'/p.name)
    verifier='''"""Verify current material and, when present, the complete preserved data annex."""
import argparse,csv,hashlib
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--quick',action='store_true',help='Skip the large historical-data annex');a=p.parse_args()
root=Path(__file__).resolve().parent
folders=[root]
if (root/'05_Full_Data/FILE_MANIFEST.csv').is_file() and not a.quick:folders.append(root/'05_Full_Data')
count=0
for folder in folders:
 for r in csv.DictReader((folder/'FILE_MANIFEST.csv').open()):
  f=folder/r['path']
  assert f.is_file() and f.stat().st_size==int(r['bytes']),f
  with f.open('rb') as stream:assert hashlib.file_digest(stream,'sha256').hexdigest()==r['sha256'],f
  count+=1
print(f'PASS: {count} files checked'+(' (historical annex skipped)' if a.quick else ''))
'''
    (DEST/'VERIFY_DELIVERY.py').write_text(verifier)
    rows=[]
    for group,n in [('Figure',6),('Supplementary_Figure',8)]:
        for i in range(1,n+1):
            label=f'{group.replace("_"," ")} {i}';stem=f'AIDRBench_{group}_{i}'
            rows.append(f'<tr><td>{label}</td><td><a href="04_Redraw_Ready/artwork/{stem}.pdf">PDF</a> · <a href="04_Redraw_Ready/artwork/{stem}.svg">SVG</a> · <a href="04_Redraw_Ready/artwork/{stem}.png">PNG</a></td></tr>')
    (DEST/'00_OPEN_ME.html').write_text('<!doctype html><meta charset="utf-8"><title>AIDRBench v0.26</title><style>body{font:16px system-ui;max-width:1000px;margin:35px auto;line-height:1.7}td{padding:6px 22px;border-bottom:1px solid #ddd}a{color:#235a78}</style><h1>AIDRBench v0.26 / 绘图包 v15</h1><p>六张主图、八张补充图；当前已整理的数据直接重绘。</p><p><a href="00_START_HERE.md">使用说明</a> · <a href="07_Provenance/COAUTHOR_FIGURE_GUIDE_ZH.md">合作者图形对应表</a></p><p><a href="02_PDF/AIDRBench_Main_v0.26.pdf">正文 PDF</a> · <a href="02_PDF/AIDRBench_Supplement_v0.26.pdf">补充 PDF</a> · <a href="03_Chinese_MD/main_zh.md">正文中文</a> · <a href="03_Chinese_MD/supplement_zh.md">补充中文</a></p><table>'+''.join(rows)+'</table><p>作者资料仍保留占位。旧恢复材料在 05_Full_Data/（仅完整大包）；当前绘图只用 04_Redraw_Ready/。</p>')
    (DEST/'CURRENT_VERSION.json').write_text(json.dumps(dict(manuscript='0.26',chinese='v20',figure_package='v15',main_figures=6,supplementary_figures=8,supplementary_tables=21,main_pdf_pages=17,supplementary_pdf_pages=27,new_simulations=0,author_metadata_pending=True,prior_release_preserved=True,local_release_not_pushed=True),indent=2)+'\n')
    fullfiles=sorted(p for p in full.rglob('*') if p.is_file() and p.parent!=full or p.is_file() and p.name not in ['FILE_MANIFEST.csv','SHA256SUMS.txt'])
    # Explicit exclusion only for this layer's own inventories, not historical inventories.
    fullfiles=sorted(p for p in full.rglob('*') if p.is_file() and p not in [full/'FILE_MANIFEST.csv',full/'SHA256SUMS.txt'])
    fullrows=inventory(full,fullfiles)
    files=sorted(p for p in DEST.rglob('*') if p.is_file() and not p.is_relative_to(full) and p not in [DEST/'FILE_MANIFEST.csv',DEST/'SHA256SUMS.txt'])
    currentrows=inventory(DEST,files)
    files+= [DEST/'FILE_MANIFEST.csv',DEST/'SHA256SUMS.txt']
    archives=[]
    for folder,name in [('01_LaTeX','LaTeX'),('03_Chinese_MD','Chinese_MD')]:
        base=DEST/folder;archives.append(create_zip(EXPORT/f'AIDRBench_{name}_v0.26_2026-09-11.zip',sorted(p for p in base.rglob('*') if p.is_file()),base))
    # The drawing ZIP was independently extracted and executed before this freeze.
    draw=EXPORT/'AIDRBench_Redraw_Ready_v0.26_2026-09-11.zip'
    with zipfile.ZipFile(draw) as z:
        assert z.testzip() is None
        for info in z.infolist():assert hashlib.sha256(z.read(info)).hexdigest()==sha(DEST/'04_Redraw_Ready'/info.filename)
        archives.append(dict(file=draw.name,bytes=draw.stat().st_size,sha256=sha(draw),entries=len(z.infolist()),crc_pass=True,independently_redrawn=True))
    draw.with_suffix('.zip.sha256').write_text(sha(draw)+'  '+draw.name+'\n')
    archives.append(create_zip(EXPORT/'AIDRBench_Submission_v0.26_2026-09-11_CORE.zip',files,DEST,DEST.name+'/'))
    archives.append(create_zip(EXPORT/'AIDRBench_All_Figures_2026-09-11_v15.zip',files+sorted(p for p in full.rglob('*') if p.is_file()),DEST,'AIDRBench_Figures_v15/'))
    result=dict(status='PASS',current_manifest_files=len(currentrows),preserved_annex_files=len(fullrows),archives=archives,old_v14_sha256=sha(saved),all_archives_crc_verified=True)
    (HERE/'archive_validation.json').write_text(json.dumps(result,indent=2)+'\n')
    (EXPORT/'AIDRBench_v0.26_archive_validation.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2),flush=True)


if __name__=='__main__':main()
