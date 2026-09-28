"""Run the frozen main-figure workflow, locating LibreOffice on Windows."""

from __future__ import annotations

import os
import runpy
import shutil
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    if os.name == "nt" and not (shutil.which("libreoffice") or shutil.which("soffice")):
        for variable in ("ProgramFiles", "ProgramFiles(x86)", "LOCALAPPDATA"):
            directory = os.environ.get(variable)
            if not directory:
                continue
            program = Path(directory) / "LibreOffice/program"
            if (program / "soffice.exe").is_file():
                os.environ["PATH"] = str(program) + os.pathsep + os.environ.get("PATH", "")
                break
    runpy.run_path(str(root / "paper/v0.27/figures/main/RUN_REBUILD.py"), run_name="__main__")


if __name__ == "__main__":
    main()
