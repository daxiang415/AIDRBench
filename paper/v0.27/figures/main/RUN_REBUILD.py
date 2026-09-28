"""Rebuild verified panels/PPTX, export with LibreOffice, and crop the six PDFs."""
from pathlib import Path
import os,runpy,shutil,subprocess,argparse
p=argparse.ArgumentParser();p.add_argument('--panels-only',action='store_true',help='Generate panels/PPTX; export to PDF manually later');args=p.parse_args()
base=Path(__file__).resolve().parent;work=base/'rebuild';work.mkdir(exist_ok=True)
os.environ['AIDRBENCH_FIGURE_WORK']=str(work)
os.environ['AIDRBENCH_FIGURE_DATA']=str(base/'02_PANEL_DATA')
os.environ['AIDRBENCH_SOURCE_PPTX']=str(base/'04_ORIGINAL_INPUT/author_original_0915.pptx')
runpy.run_path(str(base/'05_CODE/integrate_figures.py'),run_name='__main__')
if not args.panels_only:
    lo=shutil.which('libreoffice') or shutil.which('soffice')
    if not lo:raise SystemExit('Panels/PPTX generated. Install LibreOffice, or export the corrected PPTX as PDF into rebuild/corrected and then run 05_CODE/finalize_artwork.py with AIDRBENCH_FIGURE_WORK set to rebuild.')
    profile=(work/'lo_profile').as_uri()
    subprocess.run([lo,'-env:UserInstallation='+profile,'--headless','--convert-to','pdf','--outdir',str(work/'corrected'),str(work/'corrected/AIDRBench_Figures_R8_corrected.pptx')],check=True)
    runpy.run_path(str(base/'05_CODE/finalize_artwork.py'),run_name='__main__')
