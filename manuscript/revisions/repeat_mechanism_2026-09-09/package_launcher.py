"""Redraw all eleven current figures directly from the supplied summary tables."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import venv

ROOT=Path(__file__).resolve().parent


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--use-current-python',action='store_true')
    ap.add_argument('--output',type=Path,default=ROOT/'REDRAW_OUTPUT')
    a=ap.parse_args()
    if a.use_current_python:python=Path(sys.executable)
    else:
        if sys.version_info<(3,12):raise SystemExit('Use Python 3.12+, or your installed plotting environment with --use-current-python.')
        folder=ROOT/'.plot_venv';python=folder/('Scripts/python.exe' if sys.platform=='win32' else 'bin/python')
        if not python.exists():venv.EnvBuilder(with_pip=True).create(folder)
        subprocess.run([str(python),'-m','pip','install','-r',str(ROOT/'requirements_plot.txt')],check=True)
    for script in ['plot_results.py','plot_supplement.py']:
        subprocess.run([str(python),str(ROOT/'04_code'/script),'--data',str(ROOT/'03_data'),'--output',str(a.output)],check=True)
    subprocess.run([str(python),str(ROOT/'04_code/repeat_mechanism/plot_extension.py'),
        '--data',str(ROOT/'03_data/repeat_mechanism'),'--base-data',str(ROOT/'03_data'),'--output',str(a.output)],check=True)
    extension=json.loads((a.output/'extension_source_manifest.json').read_text())
    for name in ['source_manifest.json','supplement_source_manifest.json']:
        p=a.output/name;d=json.loads(p.read_text());d['revision']='v0.21';d['extension_inputs']=extension['inputs']
        d['outputs']={k:extension['outputs'][k] for k in d['outputs']};p.write_text(json.dumps(d,indent=2)+'\n')
    for prefix,n in [('AIDRBench_Figure_',6),('AIDRBench_Supplementary_Figure_',5)]:
        for i in range(1,n+1):
            for ext in ['pdf','svg','png','tiff']:assert (a.output/f'{prefix}{i}.{ext}').is_file()
    print('All 11 current figures recreated:',a.output.resolve())


if __name__=='__main__':main()
