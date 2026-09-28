"""Freeze the v0.27 documents and v16 full-data release after completed audits."""
import csv
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
DEST = ROOT / 'results/exports/AIDRBench_Submission_v0.27_2026-09-11'
EXPORT = DEST.parent
OLD_SHA = 'e7d2095b32e3ad8af8ca396d7260a494120e52357b52342c6b395c91785cb923'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def files_under(folder):
    return sorted(p for p in folder.rglob('*') if p.is_file()
                  and '__pycache__' not in p.parts and p.suffix != '.pyc')


def inventory(folder, files):
    rows = [dict(path=p.relative_to(folder).as_posix(), bytes=p.stat().st_size,
                 sha256=sha(p)) for p in files]
    with (folder / 'FILE_MANIFEST.csv').open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['path', 'bytes', 'sha256'])
        writer.writeheader()
        writer.writerows(rows)
    (folder / 'SHA256SUMS.txt').write_text(''.join(
        f'{r["sha256"]}  {r["path"]}\n' for r in rows))
    return rows


def create_zip(path, files, base, prefix=''):
    if path.exists():
        raise SystemExit(f'Refusing to overwrite a frozen archive: {path}')
    print(f'Writing {path.name} ({len(files):,} files)', flush=True)
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED,
                         compresslevel=1, allowZip64=True) as z:
        for p in files:
            z.write(p, prefix + p.relative_to(base).as_posix(),
                    compress_type=zipfile.ZIP_STORED if p.suffix == '.zip'
                    else zipfile.ZIP_DEFLATED)
    print(f'Checking CRC and SHA-256: {path.name}', flush=True)
    with zipfile.ZipFile(path) as z:
        assert len(z.namelist()) == len(set(z.namelist()))
        assert z.testzip() is None
        entries = len(z.infolist())
    digest = sha(path)
    path.with_suffix('.zip.sha256').write_text(digest + '  ' + path.name + '\n')
    row = dict(file=path.name, bytes=path.stat().st_size, entries=entries,
               sha256=digest, crc_pass=True)
    print(json.dumps(row), flush=True)
    return row


def main():
    assert json.loads((HERE / 'delivery_verification.json').read_text())['status'] == 'PASS'
    names = [f'AIDRBench_{kind}_v0.27_2026-09-11.zip'
             for kind in ['LaTeX', 'Chinese_MD', 'Redraw_Ready']]
    names += ['AIDRBench_Submission_v0.27_2026-09-11_CORE.zip',
              'AIDRBench_All_Figures_2026-09-11_v16.zip']
    assert not any((EXPORT / name).exists() for name in names), 'Release already exists'
    full = DEST / '05_Full_Data'
    assert sha(full / 'AIDRBench_All_Figures_2026-09-10_v14.zip') == OLD_SHA
    print('Preserved v14 full-data archive SHA-256: PASS', flush=True)

    # Refresh documentation only; frozen data, runners and artwork stay unchanged.
    redraw = DEST / '04_Redraw_Ready'
    (redraw / 'README_ZH.md').write_text((redraw / 'README.md').read_text() + '''
脚本对应：图 1、4、S6、S8 用 plot_completeness.py；图 2、5 用 plot_results.py；图 6、S5 用 plot_mechanisms.py；S1、S2 用 plot_supplement.py；S3、S4 用 plot_narrative.py；S7 用 plot_completeness.py 的本版精度输入；图 3、S9、S10 用 plot_validation.py。所有脚本位于 scripts/figures_v027/，统一入口会为各图传入正确数据目录。

完整历史证据及本次新增逐时数据在 v16 大包的 05_Full_Data/；当前绘图只需本目录。旧 v0.8 资料单列为历史恢复材料。软件许可证待作者决定。
''')
    shutil.copy2(HERE / 'FIGURE_CONTRACT_ZH.md', redraw / 'FIGURE_CONTRACT_ZH.md')
    for p in HERE.iterdir():
        if p.is_file() and p.name not in ['archive_validation.json', 'FINAL_STATUS.md']:
            shutil.copy2(p, DEST / '07_Provenance' / p.name)
    current = json.loads((DEST / 'CURRENT_VERSION.json').read_text())
    current.update(figure_package='v16', main_pdf_pages=18, supplementary_pdf_pages=31,
                   prior_releases_preserved=True, publication_status='local_release; author_metadata_pending',
                   archive_validation='sibling AIDRBench_v0.27_archive_validation.json')
    (DEST / 'CURRENT_VERSION.json').write_text(json.dumps(current, indent=2) + '\n')
    (DEST / 'VERIFY_DELIVERY.py').write_text('''"""Verify portable current files and, when available, the full-data annex."""
import argparse, csv, hashlib
from pathlib import Path
parser = argparse.ArgumentParser()
parser.add_argument('--quick', action='store_true', help='Skip the large full-data annex')
args = parser.parse_args()
root = Path(__file__).resolve().parent
folders = [root]
if not args.quick and (root/'05_Full_Data/FILE_MANIFEST.csv').is_file():
    folders.append(root/'05_Full_Data')
count = 0
for folder in folders:
    for row in csv.DictReader((folder/'FILE_MANIFEST.csv').open()):
        path = folder/row['path']
        assert path.is_file() and path.stat().st_size == int(row['bytes']), path
        with path.open('rb') as stream:
            assert hashlib.file_digest(stream, 'sha256').hexdigest() == row['sha256'], path
        count += 1
print(f'PASS: {count} files checked; full-data annex ' +
      ('checked' if len(folders) == 2 else 'not included in this check'))
''')
    links = []
    for group, n in [('Figure', 6), ('Supplementary_Figure', 10)]:
        for i in range(1, n + 1):
            stem = f'AIDRBench_{group}_{i}'
            links.append('<tr><td>' + group.replace('_', ' ') + f' {i}</td><td>' +
                         ' · '.join(f'<a href="04_Redraw_Ready/artwork/{stem}.{ext}">{ext.upper()}</a>'
                                    for ext in ['pdf', 'svg', 'png']) + '</td></tr>')
    (DEST / '00_OPEN_ME.html').write_text('''<!doctype html><meta charset="utf-8">
<title>AIDRBench v0.27</title><style>body{font:16px system-ui;max-width:1000px;margin:35px auto;line-height:1.7}td{padding:6px 22px;border-bottom:1px solid #ddd}a{color:#235a78}</style>
<h1>AIDRBench v0.27 / 绘图包 v16</h1><p>六张主图、十张补充图、二十四张补充表。当前数据已整理，可直接重绘。</p>
<p><a href="00_START_HERE.md">使用说明</a> · <a href="07_Provenance/RESPONSE_ZH.md">逐项修改和判断依据</a> · <a href="04_Redraw_Ready/FIGURE_CONTRACT_ZH.md">合作者图形对应表</a></p>
<p><a href="02_PDF/AIDRBench_Main_v0.27.pdf">正文 PDF</a> · <a href="02_PDF/AIDRBench_Supplement_v0.27.pdf">补充 PDF</a> · <a href="03_Chinese_MD/main_zh.md">正文中文</a> · <a href="03_Chinese_MD/supplement_zh.md">补充中文</a></p>
<table>''' + ''.join(links) + '''</table><p>作者资料仍待填写。完整数据在 05_Full_Data/（仅大包）；绘图只需 04_Redraw_Ready/。</p>''')
    (DEST / '00_START_HERE.md').write_text((DEST / '00_START_HERE.md').read_text() + '''
本版压缩包：CORE 包含除 05_Full_Data 外的当前材料；Redraw_Ready 是可直接交给绘图合作者的小包；v16 是包含全部旧证据和新证据的完整恢复包。LaTeX 和 Chinese_MD 另有独立包。运行 `python VERIFY_DELIVERY.py --quick` 核对当前材料，完整大包去掉 `--quick` 可连同全量数据核对。文件校验清单不包含运行后产生的 Python 缓存。
''')
    fullrows = inventory(full, [p for p in files_under(full)
                               if p not in [full/'FILE_MANIFEST.csv', full/'SHA256SUMS.txt']])
    corefiles = [p for p in files_under(DEST) if not p.is_relative_to(full)
                 and p not in [DEST/'FILE_MANIFEST.csv', DEST/'SHA256SUMS.txt']]
    corerows = inventory(DEST, corefiles)
    corefiles += [DEST/'FILE_MANIFEST.csv', DEST/'SHA256SUMS.txt']
    archives = []
    for folder, name in [('01_LaTeX', 'LaTeX'), ('03_Chinese_MD', 'Chinese_MD'),
                         ('04_Redraw_Ready', 'Redraw_Ready')]:
        base = DEST / folder
        archives.append(create_zip(EXPORT/f'AIDRBench_{name}_v0.27_2026-09-11.zip',
                                   files_under(base), base, folder + '/'))
    archives.append(create_zip(EXPORT/names[-2], corefiles, DEST, DEST.name + '/'))
    archives.append(create_zip(EXPORT/names[-1], corefiles + files_under(full),
                               DEST, 'AIDRBench_Figures_v16/'))
    result = dict(status='PASS', version='0.27', current_manifest_files=len(corerows),
                  full_data_manifest_files=len(fullrows), archives=archives,
                  preserved_v14_sha256=OLD_SHA, all_archives_crc_verified=True,
                  cache_files_excluded=True)
    text = json.dumps(result, indent=2) + '\n'
    (HERE / 'archive_validation.json').write_text(text)
    (EXPORT / 'AIDRBench_v0.27_archive_validation.json').write_text(text)
    print(text, flush=True)


if __name__ == '__main__':
    main()
