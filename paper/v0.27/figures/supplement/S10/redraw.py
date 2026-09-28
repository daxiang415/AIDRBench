from pathlib import Path
import subprocess
import sys
root=Path(__file__).resolve().parents[1]
subprocess.run([sys.executable,str(root/'DRAW_SUPPLEMENT.py'),'--figures','S10',*sys.argv[1:]],check=True)
