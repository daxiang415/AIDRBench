"""Audit final numerical mappings, aligned prose, editable figures and portable PDFs."""
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import subprocess

import fitz
import numpy as np
import pandas as pd
from PIL import Image,ImageDraw

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
DEST=ROOT/'results/exports/AIDRBench_Submission_v0.26_2026-09-11'
TEMP=Path('/tmp/aidrbench_v026_portability')


def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def main():
    report={'version':'0.26','new_simulations':0,'new_offer_selection':False}
    before=(HERE/'before/nature_communications_article.md').read_text()
    after=(ROOT/'manuscript/nature_communications_article.md').read_text()
    for start,end in [('## Abstract','## Introduction'),('## References','## Acknowledgements')]:
        assert before.split(start)[1].split(end)[0]==after.split(start)[1].split(end)[0]
    si=(ROOT/'manuscript/supplementary_information.md').read_text()
    assert si.split('## Supplementary Tables')[1]==(HERE/'before/supplementary_information.md').read_text().split('## Supplementary Tables')[1]
    report['unchanged_evidence']={'all_21_SI_tables_byte_identical':True,'abstract_and_references_byte_identical':True}
    wc=lambda t:len(re.findall(r"\b[\w]+(?:[-’'][\w]+)*\b",t))
    report['words']={'abstract':wc(after.split('## Abstract\n')[1].split('## Introduction\n')[0]),'results':wc(after.split('## Results\n')[1].split('## Discussion\n')[0])}
    for stem,name in [('main','nature_communications_article.md'),('supplement','supplementary_information.md')]:
        d=json.loads((ROOT/f'docs/chinese_reader/v20/{stem}_aligned_blocks.json').read_text())
        assert d['source_sha256']==sha(ROOT/'manuscript'/name)
        assert len({b['id'] for b in d['blocks']})==len(d['blocks'])
        assert '\n\n'.join(b['en'] for b in d['blocks']) in (ROOT/'manuscript'/name).read_text()
        report[stem+'_aligned_blocks']=len(d['blocks'])
    data=ROOT/'manuscript/source_data/nature_figure_completeness_v1'
    trace=pd.read_csv(data/'reference_operation_example.csv')
    assert len(trace)==432 and trace.scenario_seed.unique().tolist()==[989000]
    assert np.allclose(trace.incremental_power_kw,trace.pcc_power_kw-trace.baseline_pcc_power_kw,atol=1e-9,rtol=0)
    assert np.allclose(trace.excess_backlog_gpu_h,np.maximum(trace.backlog_gpu_h-trace.paired_baseline_backlog_gpu_h,0),atol=1e-9,rtol=0)
    assert (pd.read_csv(data/'reference_operation_example_outcomes.csv').success_zero).all()
    structural=pd.read_csv(data/'structural_full_request.csv')
    assert len(structural)==48 and (structural.trials==300).all()
    raw=pd.read_csv(ROOT/'manuscript/source_data/nature_operating_tradeoffs_v1/confirmation_summary.csv')
    keys=['variant','program','kind','fraction','endpoint']
    a=structural.set_index(keys);b=raw.set_index(keys).loc[a.index]
    for col in ['successes','instantaneous_supply_limited_trials','failed_deadline_miss']:assert np.array_equal(a[col],b[col])
    pv=pd.read_csv(data/'pv_all_scenarios.csv');summary=pd.read_csv(data/'pv_operating_summary.csv')
    assert len(pv)==4000
    for row in summary.itertuples():
        g=pv[(pv.analysis==row.analysis)&(pv.case==row.case)&(pv.bess_enabled==row.bess_enabled)&(pv.dc_operation==row.dc_operation)][row.metric]
        assert len(g)==100 and np.isclose(g.mean(),row.mean,atol=1e-8,rtol=1e-12) and np.isclose(g.min(),row.minimum,atol=1e-8,rtol=1e-12)
    report['new_panels']={'illustrated_hours':432,'trace_power_and_backlog_identities':True,'structural_summary_rows':48,'all_heatmap_counts_match':True,'pv_scenario_rows':4000,'all_pv_summaries_recomputed_match':True,'monetary_inputs':'existing single-event sensitivity rows; no resampling'}
    art=ROOT/'docs/figures/figure_completeness_v1/artwork';figures={}
    for p in sorted(art.glob('*.pdf')):
        doc=fitz.open(p);spans=[s for b in doc[0].get_text('dict')['blocks'] for l in b.get('lines',[]) for s in l['spans']]
        assert all((doc[0].rect+(-.5,-.5,.5,.5)).contains(fitz.Rect(s['bbox'])) for s in spans)
        run=subprocess.run([str(ROOT/'.venv/bin/python'),'/home/user/.codex/skills/nature-figure/scripts/audit_pdf_text.py',str(p),'--min-pt','6','--json'],capture_output=True,text=True)
        assert run.returncode==0,(p,run.stdout)
        svg=p.with_suffix('.svg').read_text();assert '<text' in svg
        raster=Image.open(p.with_suffix('.tiff'));assert min(raster.info['dpi'])>=599
        figures[p.name]={'min_pt':min(s['size'] for s in spans),'width_mm':doc[0].rect.width/72*25.4,'editable_svg':True,'pdf_glyph_audit':json.loads(run.stdout),'tiff_dpi':[float(v) for v in raster.info['dpi']]}
    assert len(figures)==14;report['figures']=figures
    norm=lambda x:re.sub(r'[\s\-\u00ad]','',x)
    for kind,prefix,count in [('main','Figure ',6),('supplement','Supplementary Figure ',8)]:
        path=TEMP/'01_LaTeX'/f'{kind}.pdf';doc=fitz.open(path);toc=doc.get_toc()
        fg=[t for t in toc if t[1].startswith(prefix)];assert len(fg)==count
        for _,heading,n in fg:
            assert norm(heading) in norm(doc[n-1].get_text()) and doc[n-1].get_xobjects()
        if kind=='supplement':
            assert len([t for t in toc if t[1].startswith('Supplementary Table ')])==21
            for _,heading,n in toc:assert norm(heading) in norm(doc[n-1].get_text())
        for p in doc:
            for b in p.get_text('dict')['blocks']:
                for l in b.get('lines',[]):
                    for s in l['spans']:assert (p.rect+(-.5,-.5,.5,.5)).contains(fitz.Rect(s['bbox'])),s['text']
        log=(TEMP/'01_LaTeX'/f'{kind}.log').read_text()
        serious=[l for l in log.splitlines() if re.search(r'Overfull|Float too large|Missing character|undefined|^!',l)];assert not serious,serious
        out=DEST/'02_PDF'/f'AIDRBench_{kind.title()}_v0.26.pdf';shutil.copy2(path,out)
        shutil.copy2(TEMP/'01_LaTeX'/f'{kind}.log',DEST/'07_Provenance'/f'{kind}_compile.log')
        suffix='' if kind=='main' else '_Supplementary_Information'
        shutil.copy2(path,ROOT/f'manuscript/exports/AIDRBench_Nature_Communications_v0.26{suffix}_content_revision.pdf')
        sheet=Image.new('RGB',(1240,math.ceil(len(doc)/4)*455),'#e8ebef');draw=ImageDraw.Draw(sheet)
        for i,p in enumerate(doc):
            pix=p.get_pixmap(matrix=fitz.Matrix(.6,.6));im=Image.frombytes('RGB',[pix.width,pix.height],pix.samples);im.thumbnail((300,420));x=i%4*310+5;y=i//4*455+20;sheet.paste(im,(x,y));draw.text((x,y-15),f'{kind} page {i+1}',fill='black')
        sheet.save(DEST/'07_Provenance'/f'{kind}_pages.png')
        report[kind+'_pdf']={'pages':len(doc),'figure_bookmarks':fg,'serious_tex_warnings':[],'underfull_lines':[l for l in log.splitlines() if 'Underfull' in l],'sha256':sha(out)}
    transformations=json.loads((DEST/'07_Provenance/tex_transformations.json').read_text())
    for entry in transformations:
        text=(DEST/f'01_LaTeX/{entry["kind"]}.tex').read_text()
        for old,new in reversed(entry['layout_replacements']):text=text.replace(new,old)
        for marker,ins in reversed(entry['layout_insertions']):text=text.replace(ins+marker,marker)
        assert text.split('\\thispagestyle{fancy}\n',1)[1].replace('figures/','../../docs/figures/figure_completeness_v1/artwork/')==(ROOT/entry['source']).read_text().split('\\end{center}\n',1)[1]
    redraw=json.loads((TEMP/'redrawn/redraw_validation.json').read_text());assert redraw['figures']==14 and redraw['all_pngs_match_reference']
    for row in redraw['comparisons']:
        assert row['sha256']['png']==sha(art/f'AIDRBench_{row["figure"]}.png')
    report['portable_redraw']={'figures':14,'all_pngs_identical':True,'source':'independently extracted final plotting ZIP'}
    shutil.copy2(TEMP/'redrawn/redraw_validation.json',DEST/'07_Provenance/redraw_validation.json')
    run=subprocess.run([str(ROOT/'.venv/bin/python'),'/home/user/.codex/skills/nature-figure/scripts/validate_figure.py',str(HERE/'plot_completeness.py'),'--json'],capture_output=True,text=True)
    assert run.returncode==0;report['source_preflight']=json.loads(run.stdout)
    report['status']='PASS'
    for dest in [HERE/'verification.json',DEST/'07_Provenance/verification.json']:dest.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ['status','words','main_aligned_blocks','supplement_aligned_blocks','portable_redraw']},indent=2))


if __name__=='__main__':main()
