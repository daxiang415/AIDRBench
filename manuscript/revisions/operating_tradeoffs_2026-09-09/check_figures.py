"""Export receipts, actual PDF glyph/bounds checks and panel preview contact sheet."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import fitz
from PIL import Image
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];ART=ROOT/'docs/figures/operating_tradeoffs_v1/artwork'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    changed=['Figure_3','Figure_6','Supplementary_Figure_3','Supplementary_Figure_5'];rows=[]
    for stem in changed:
        path=ART/f'AIDRBench_{stem}.pdf';doc=fitz.open(path);assert len(doc)==1;page=doc[0];sizes=[]
        for block in page.get_text('dict')['blocks']:
            for line in block.get('lines',[]):
                for span in line['spans']:
                    if not span['text'].strip():continue
                    sizes.append(span['size']);x0,y0,x1,y1=span['bbox']
                    assert x0>=-1 and y0>=-1 and x1<=page.rect.width+1 and y1<=page.rect.height+1,(stem,span)
        assert min(sizes)>=5
        out=subprocess.run([sys.executable,'/home/user/.codex/skills/nature-figure/scripts/audit_pdf_text.py',str(path),'--min-pt','5','--json'],capture_output=True,text=True)
        (HERE/f'{stem}_glyph_audit.json').write_text(out.stdout);assert out.returncode==0,out.stdout+out.stderr
        rows.append(dict(figure=stem,status='PASS',minimum_actual_font_pt=min(sizes),no_text_outside_page=True,width_mm=page.rect.width/72*25.4,height_mm=page.rect.height/72*25.4))
    for stem,n,prefix in [('source_manifest.json',6,'AIDRBench_Figure_'),('supplement_source_manifest.json',5,'AIDRBench_Supplementary_Figure_')]:
        outputs={}
        for i in range(1,n+1):
            for ext in ['pdf','svg','png','tiff']:
                p=ART/f'{prefix}{i}.{ext}';assert p.is_file();outputs[p.name]=dict(sha256=sha(p),bytes=p.stat().st_size)
        (ART/stem).write_text(json.dumps(dict(revision='v0.23',backend='Python',outputs=outputs,changed_figures=changed,source_tables='nature_operating_tradeoffs_v1'),indent=2)+'\n')
    canvas=Image.new('RGB',(1440,1450),'white')
    for i,stem in enumerate(changed):
        im=Image.open(ART/f'AIDRBench_{stem}.png');im.thumbnail((715,715));canvas.paste(im,((i%2)*720,(i//2)*725))
    canvas.save(HERE/'figure_contact.png');(HERE/'figure_validation.json').write_text(json.dumps(dict(status='PASS',figures=rows,total_artwork_files=44),indent=2)+'\n');print(json.dumps(rows,indent=2))
if __name__=='__main__':main()
