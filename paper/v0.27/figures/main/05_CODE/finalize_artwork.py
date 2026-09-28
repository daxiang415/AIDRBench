"""Crop only exterior whitespace; keep the complete supplied panel composition."""
from pathlib import Path
import fitz,numpy as np,json,hashlib,os
from PIL import Image
w=Path(os.environ.get('AIDRBENCH_FIGURE_WORK',str(Path(__file__).resolve().parent)))
(w/'preview').mkdir(exist_ok=True)
art=w/'artwork';art.mkdir(exist_ok=True)
doc=fitz.open(w/'corrected/AIDRBench_Figures_R8_corrected.pdf');items=[];outputs={}
for i,p in enumerate(doc):
 pix=p.get_pixmap(matrix=fitz.Matrix(1,1));a=np.frombuffer(pix.samples,dtype=np.uint8).reshape(pix.height,pix.width,pix.n)
 mask=np.any(a[:,:,:3]<240,axis=2);ys,xs=np.where(mask)
 clip=fitz.Rect(max(0,xs.min()-12),max(0,ys.min()-12),min(p.rect.width,xs.max()+13),min(p.rect.height,ys.max()+13))
 dst=fitz.open();scale=(180/25.4*72)/clip.width;page=dst.new_page(width=clip.width*scale,height=clip.height*scale);page.show_pdf_page(page.rect,doc,i,clip=clip)
 name=f'AIDRBench_Figure_{i+1}';dst.save(art/(name+'.pdf'),garbage=4,deflate=True);page.get_pixmap(dpi=300).save(art/(name+'.png'))
 # SVG is supplementary editing format; preserve PDF as the typeset source.
 (art/(name+'.svg')).write_text(page.get_svg_image(text_as_path=False))
 spans=[s for b in page.get_text('dict')['blocks'] if 'lines'in b for l in b['lines'] for s in l['spans'] if s['text'].strip()]
 items.append({'figure':i+1,'crop_pt':list(clip),'source_page_pt':list(p.rect),'final_size_mm':[page.rect.width/72*25.4,page.rect.height/72*25.4],'min_text_pt':min(s['size'] for s in spans),'text_characters':len(page.get_text()),'exterior_blank_removed_pct':100*(1-clip.get_area()/p.rect.get_area())})
 for ext in ['pdf','png','svg']:
  f=art/(name+'.'+ext);outputs[f.name]={'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'bytes':f.stat().st_size}
(w/'corrected/crop_log.json').write_text(json.dumps(items,indent=2));(art/'source_manifest.json').write_text(json.dumps({'version':'v0.27 / R8','source':'figure0915.zip supplied by author; corrected from frozen v17.3 panel data','outputs':outputs},indent=2))
thumbs=[]
for i in range(6):
 im=Image.open(art/f'AIDRBench_Figure_{i+1}.png').convert('RGB');im.thumbnail((750,740));thumbs.append(im)
contact=Image.new('RGB',(2250,1520),'#eeeeee')
for i,im in enumerate(thumbs):contact.paste(im,((i%3)*750,(i//3)*760))
contact.save(w/'preview/contact_corrected.jpg')
print(json.dumps(items,indent=2))
