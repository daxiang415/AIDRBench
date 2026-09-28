"""Redraw all 14 final figures from portable ready tables, without simulation."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'MY_FIGURES')
    parser.add_argument('--verify',action='store_true',help='Compare PNGs with supplied reference; omit after intended edits.')
    args=parser.parse_args();out=args.output.resolve();out.mkdir(parents=True,exist_ok=True)
    data=ROOT/'manuscript/source_data';scripts=ROOT/'scripts/figures_v026'
    stages=[
        ('plot_results.py',['--data',data/'nature_workload_composition_v1','--through','5'],['Figure_2','Figure_5']),
        ('plot_supplement.py',['--data',data/'nature_workload_composition_v1','--through','2'],['Supplementary_Figure_1','Supplementary_Figure_2']),
        ('plot_mechanisms.py',['--data',data/'nature_commitment_mechanisms_v1','--previous-data',data/'nature_operating_tradeoffs_v1'],['Figure_6','Supplementary_Figure_5']),
        ('plot_narrative.py',['--data',data/'nature_commitment_narrative_v1'],['Figure_3','Supplementary_Figure_3','Supplementary_Figure_4']),
        ('plot_completeness.py',['--data',data/'nature_figure_completeness_v1'],['Figure_1','Figure_4','Supplementary_Figure_6','Supplementary_Figure_7','Supplementary_Figure_8']),
    ]
    rows=[];reference=ROOT/'artwork'
    # Legacy plotting functions may create intermediate panels. Only the explicitly
    # assigned final figures are copied out; each final number has exactly one owner.
    with tempfile.TemporaryDirectory(prefix='aidrbench-plot-') as temporary:
        for i,(script,options,names) in enumerate(stages):
            stage=Path(temporary)/str(i)
            subprocess.run([sys.executable,str(scripts/script),*map(str,options),'--output',str(stage)],check=True)
            for name in names:
                exports={}
                for ext in ['pdf','svg','png','tiff']:
                    p=stage/f'AIDRBench_{name}.{ext}';assert p.is_file(),p
                    dest=out/p.name;shutil.copy2(p,dest)
                    exports[ext]=hashlib.sha256(dest.read_bytes()).hexdigest()
                match=exports['png']==hashlib.sha256((reference/f'AIDRBench_{name}.png').read_bytes()).hexdigest()
                if args.verify and not match:raise RuntimeError(f'Figure differs from reference: {name}')
                rows.append(dict(figure=name,png_matches_reference=match,sha256=exports))
    assert len(rows)==14 and len({r['figure'] for r in rows})==14
    (out/'redraw_validation.json').write_text(json.dumps(dict(status='PASS',manuscript='v0.26',figures=14,new_simulations=0,all_pngs_match_reference=all(r['png_matches_reference'] for r in rows),comparisons=rows),indent=2)+'\n')
    print('Rendered six main and eight supplementary figures. PNG comparison:',all(r['png_matches_reference'] for r in rows))


if __name__=='__main__':main()
