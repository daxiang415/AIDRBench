"""Compile the two self-contained documents with XeLaTeX or Tectonic."""
import argparse
import shutil
import subprocess
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine", help="xelatex, tectonic, or an executable path")
    args = parser.parse_args()
    engine = args.engine or shutil.which("xelatex") or shutil.which("tectonic")
    if not engine:
        raise SystemExit("Install XeLaTeX (TeX Live/MiKTeX) or Tectonic, then run BUILD.py again.")
    is_tectonic = "tectonic" in Path(engine).name.lower()
    folder = Path(__file__).resolve().parent
    for name in ("main.tex", "supplement.tex"):
        command = [engine, "--keep-logs", name] if is_tectonic else [engine, "-interaction=nonstopmode", "-halt-on-error", name]
        for _ in range(1 if is_tectonic else 2):
            subprocess.run(command, cwd=folder, check=True)
    print("Created main.pdf and supplement.pdf in", folder)

if __name__ == "__main__":
    main()
