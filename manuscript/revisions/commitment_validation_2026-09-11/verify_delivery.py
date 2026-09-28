"""Check final document alignment, numbered displays and independent redraw."""
import hashlib,json,re,shutil
from pathlib import Path
import fitz
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];DEST=ROOT/'results/exports/AIDRBench_Submission_v0.27_2026-09-11'
def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def norm(s):return re.sub(r'[\s\-\u00ad]','',s)
def main():
    evidence=json.loads((HERE/'evidence_verification.json').read_text());assert evidence['status']=='PASS'
    audit=json.loads((HERE/'figure_audit.json').read_text());assert len(audit)==16 and all(not x['outside'] and x['code']==0 and x['min_font_pt']>=6 for x in audit.values())
    redraw=json.loads(Path('/tmp/aidrbench_v027_redrawn/redraw_validation.json').read_text());assert redraw['figures']==16 and redraw['all_pngs_match_reference']
    for row in redraw['comparisons']:
        name='AIDRBench_'+row['figure']
        assert sha(DEST/f'04_Redraw_Ready/artwork/{name}.png')==row['sha256']['png']
        assert sha(DEST/f'01_LaTeX/figures/{name}.pdf')==sha(DEST/f'04_Redraw_Ready/artwork/{name}.pdf')
    reports={}
    for kind,stem,name,fgcount in [('main','main','nature_communications_article.md',6),('supplement','supplement','supplementary_information.md',10)]:
        original=(ROOT/'manuscript'/name).read_text();blocks=json.loads((ROOT/f'docs/chinese_reader/v21/{stem}_aligned_blocks.json').read_text())
        assert blocks['source_sha256']==sha(ROOT/'manuscript'/name)
        assert '\n\n'.join(x['en'] for x in blocks['blocks']) in original
        assert len(blocks['blocks'])==len({x['id'] for x in blocks['blocks']})
        assert (DEST/f'06_English_MD/{stem}.md').read_text()==original.replace('../docs/figures/commitment_validation_v1/artwork/','../03_Chinese_MD/images/')
        for suffix in ['zh','bilingual']:
            expected=(ROOT/f'docs/chinese_reader/v21/{stem}_{suffix}.md').read_text().replace(str(ROOT/'docs/figures/commitment_validation_v1/artwork')+'/','images/')
            assert (DEST/f'03_Chinese_MD/{stem}_{suffix}.md').read_text()==expected
        doc=fitz.open(DEST/f'01_LaTeX/{kind}.pdf');toc=doc.get_toc();prefix='Figure ' if kind=='main' else 'Supplementary Figure '
        figures=[x for x in toc if x[1].startswith(prefix)];assert len(figures)==fgcount
        for _,title,n in figures:
            assert doc[n-1].get_xobjects() and norm(title) in norm(doc[n-1].get_text())
        text='\n'.join(p.get_text() for p in doc)
        assert '193.438980' in text and '1.4746' in text and '0.991062' in text if kind=='supplement' else '1.47' in text and '300/300' in text
        outside=[]
        for i,page in enumerate(doc):
            for b in page.get_text('dict')['blocks']:
                for line in b.get('lines',[]):
                    for s in line['spans']:
                        if not (page.rect+(-1,-1,1,1)).contains(fitz.Rect(s['bbox'])):outside.append((i+1,s['text']))
        assert not outside,outside
        if kind=='supplement':
            tables=[x for x in toc if x[1].startswith('Supplementary Table ')];assert len(tables)==24
            table23=next(x for x in tables if x[1].startswith('Supplementary Table 23 '));page=doc[table23[2]-1]
            assert 'W/node' in page.get_text() and '167.52' in page.get_text()
        for p in (DEST/'03_Chinese_MD').glob('*.md'):
            for image in re.findall(r'!\[[^]]*\]\(([^)]+)\)',p.read_text()):assert not image.startswith('/') and (p.parent/image).is_file()
        reports[kind]=dict(pages=len(doc),figures=len(figures),all_numbered_figures_on_expected_pages=True,text_within_pages=True,Chinese_alignment=True)
        shutil.copy2(DEST/f'01_LaTeX/{kind}.pdf',DEST/f'02_PDF/AIDRBench_{"Main" if kind=="main" else "Supplement"}_v0.27.pdf')
    log=Path('/tmp/aidrbench_v027_tex.log').read_text();assert not any(x in log for x in ['Missing character','Overfull','error:'])
    tests=Path('/tmp/aidrbench_v027_tests.log').read_text();assert '18 passed' in tests and 'failed' not in tests
    result=dict(status='PASS',version='0.27',documents=reports,redraw=redraw,figure_files=16,relevant_tests_passed=18,numerical_evidence_audit=sha(HERE/'evidence_verification.json'),figure_text_audit=sha(HERE/'figure_audit.json'),new_source_hashes=json.loads((ROOT/'manuscript/source_data/nature_commitment_validation_v1/validation_audit.json').read_text())['sources'])
    (HERE/'delivery_verification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(reports,indent=2));print('Delivery checks PASS')
if __name__=='__main__':main()
