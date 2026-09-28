"""Repair the five portable supplementary-caption links before handing off v12."""
import csv
import json
import re
import shutil
import subprocess
import zipfile
import build_package as b

def main():
    assert b.TARGET.exists() and not (b.HERE/'FINAL_STATUS.md').exists(),'Only amend this task’s not-yet-delivered v12'
    before={r['path']:r for r in csv.DictReader((b.STAGE/'FILE_INVENTORY.csv').open())}
    b.refresh()
    count=0
    for folder in ['00_manuscript','01_main','02_supp']:
        for p in (b.STAGE/folder).rglob('*.md'):
            for target in re.findall(r'!\[[^]]*\]\(([^)]+)\)',p.read_text()):
                assert not target.startswith('/') and (p.parent/target).is_file(),(p,target);count+=1
    for target in re.findall(r'href="([^"]+)"',(b.STAGE/'OPEN_ME.html').read_text()):assert (b.STAGE/target).exists(),target
    check=dict(status='PASS',current_markdown_image_links=count,all_html_entry_links_exist=True,supplementary_caption_links_use_package_relative_paths=True)
    (b.HERE/'portable_link_validation.json').write_text(json.dumps(check,indent=2)+'\n');shutil.copyfile(b.HERE/'portable_link_validation.json',b.STAGE/'05_audit/operating_tradeoffs_v023/portable_link_validation.json')
    files=sorted(p for p in b.STAGE.rglob('*') if p.is_file() and p not in [b.STAGE/'FILE_INVENTORY.csv',b.STAGE/'SHA256SUMS.txt'])
    rows=[dict(path=p.relative_to(b.STAGE).as_posix(),bytes=p.stat().st_size,sha256=b.sha(p)) for p in files]
    with (b.STAGE/'FILE_INVENTORY.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=['path','bytes','sha256']);w.writeheader();w.writerows(rows)
    (b.STAGE/'SHA256SUMS.txt').write_text(''.join(f'{r["sha256"]}  {r["path"]}\n' for r in rows)+f'{b.sha(b.STAGE/"FILE_INVENTORY.csv")}  FILE_INVENTORY.csv\n')
    changed=[r['path'] for r in rows if r['path'] not in before or r['sha256']!=before[r['path']]['sha256']]+['FILE_INVENTORY.csv','SHA256SUMS.txt']
    temporary=b.TARGET.with_suffix('.amending.zip');assert not temporary.exists();shutil.copyfile(b.TARGET,temporary)
    subprocess.run(['zip','-q','-1',str(temporary),'-@'],input=''.join(b.STAGE.name+'/'+r+'\n' for r in changed),text=True,cwd=b.STAGE.parent,check=True)
    print('Checking updated captions, manifest and entire ZIP CRC',flush=True)
    with zipfile.ZipFile(temporary) as z:
        names=z.namelist();assert len(names)==len(set(names));assert set(names)=={b.STAGE.name+'/'+p.relative_to(b.STAGE).as_posix() for p in b.STAGE.rglob('*') if p.is_file()}
        for rel in changed:assert z.read(b.STAGE.name+'/'+rel)==(b.STAGE/rel).read_bytes(),rel
        assert z.testzip() is None
    temporary.replace(b.TARGET)
    report=json.loads((b.HERE/'package_validation.json').read_text());report.update(bytes=b.TARGET.stat().st_size,sha256=b.sha(b.TARGET),files=len(names),all_current_image_links_portable=True,caption_portability_amendment_files=len(changed))
    (b.HERE/'package_validation.json').write_text(json.dumps(report,indent=2)+'\n');b.TARGET.with_suffix('.zip.sha256').write_text(f'{report["sha256"]}  {b.TARGET.name}\n');print(json.dumps(report,indent=2),flush=True)

if __name__=='__main__':main()
