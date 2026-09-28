"""Verify delivered figures, one frozen replay, and current PDF navigation."""
import hashlib
import json
import re
import shutil
from pathlib import Path
import fitz

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
ART=ROOT/'docs/figures/commitment_narrative_v1/artwork'
REDRAW=Path('/tmp/aidrbench_v025_package_redraw')
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def main():
    pngs=sorted(ART.glob('*.png'));assert len(pngs)==11
    comparisons=[]
    for p in pngs:
        expected=sha(p);actual=sha(REDRAW/p.name);assert expected==actual,p.name
        comparisons.append(dict(file=p.name,sha256=expected,match=True))
    (HERE/'redraw_validation.json').write_text(json.dumps(dict(status='PASS',figures=11,all_png_sha256_identical=True,comparisons=comparisons,new_simulations=0),indent=2)+'\n')
    replay=Path('/tmp/aidrbench_v025_replay/replay_validation.json')
    result=json.loads(replay.read_text());assert result['status']=='PASS' and result['max_absolute_error']==0
    shutil.copyfile(replay,HERE/'replay_validation.json')
    report={'status':'PASS'}
    for stem,suffix,pages in [('main','',[4,5,16]),('supplement','_Supplementary_Information',[2,3,4,5,12,13,25])]:
        p=ROOT/f'manuscript/exports/AIDRBench_Nature_Communications_v0.25{suffix}_content_revision.pdf'
        d=fitz.open(p);outside=[]
        for i,page in enumerate(d):
            for b in page.get_text('dict')['blocks']:
                for line in b.get('lines',[]):
                    for span in line['spans']:
                        rect=fitz.Rect(span['bbox'])
                        if not (page.rect+(-0.5,-0.5,0.5,0.5)).contains(rect):outside.append(dict(page=i+1,text=span['text'],bbox=span['bbox']))
        assert not outside,outside
        toc=d.get_toc();figures=[t for t in toc if t[1].startswith('Figure ' if stem=='main' else 'Supplementary Figure ')]
        assert len(figures)==(6 if stem=='main' else 5)
        if stem=='supplement':
            assert len([t for t in toc if t[1].startswith('Supplementary Table ')])==21
            for _,heading,number in toc:
                # The linked page must contain the actual section heading, not a preceding table anchor.
                normal=lambda x:re.sub(r'[\s-]','',x)
                assert normal(heading) in normal(d[number-1].get_text()),(heading,number)
        for number in pages:d[number-1].get_pixmap(matrix=fitz.Matrix(1.4,1.4)).save(f'/tmp/aidrbench_v025_{stem}_{number}.png')
        report[stem]=dict(pages=len(d),sha256=sha(p),text_spans_outside_pages=outside,rendered_pages=pages,bookmarks=toc)
    (HERE/'pdf_validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(status='PASS',redrawn_figures=11,pngs_match=True,replay_rows=216,replay_numeric_columns=92,pdf_pages={s:report[s]['pages'] for s in ['main','supplement']},si_bookmark_destinations_verified=True),indent=2))

if __name__=='__main__':main()
