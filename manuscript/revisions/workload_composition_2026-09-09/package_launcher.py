"""One command recreates all eleven current figures from supplied tables."""

import argparse
import subprocess
import sys
import venv
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--use-current-python",
        action="store_true",
        help="use already installed numpy/pandas/matplotlib",
    )
    ap.add_argument("--output", type=Path, default=ROOT / "REDRAW_OUTPUT")
    a = ap.parse_args()
    if a.use_current_python:
        python = Path(sys.executable)
    else:
        if sys.version_info < (3, 12):  # noqa: UP036 - standalone entry checks the user's Python
            raise SystemExit(
                "Please use Python 3.12 or later, or install plotting dependencies and add --use-current-python."
            )
        folder = ROOT / ".plot_venv"
        python = folder / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
        if not python.exists():
            venv.EnvBuilder(with_pip=True).create(folder)
        subprocess.run(
            [str(python), "-m", "pip", "install", "-r", str(ROOT / "requirements_plot.txt")],
            check=True,
        )
    for script in ["plot_results.py", "plot_supplement.py"]:
        subprocess.run(
            [
                str(python),
                str(ROOT / "04_code" / script),
                "--data",
                str(ROOT / "03_data"),
                "--output",
                str(a.output),
            ],
            check=True,
        )
    for stem, count in [("AIDRBench_Figure_", 6), ("AIDRBench_Supplementary_Figure_", 5)]:
        for n in range(1, count + 1):
            for ext in ["pdf", "svg", "png", "tiff"]:
                assert (a.output / f"{stem}{n}.{ext}").is_file()
    print("All 11 figures recreated:", a.output.resolve())


if __name__ == "__main__":
    main()
