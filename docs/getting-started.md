# Getting started

Reading the PDFs requires no software setup. Figure redraws use the included plotting tables and run on a CPU. Replaying the complete study is a separate task with additional data requirements.

For PowerShell commands, use the [Windows guide](../WINDOWS_START_HERE.md). The examples below use Linux/macOS.

## Install for your task

```bash
git clone https://github.com/daxiang415/AIDRBench.git
cd AIDRBench
python3.12 -m venv .venv
.venv/bin/python -m pip install -c requirements-certificate.txt -e ".[paper]"
.venv/bin/python tools/aidr.py doctor
```

Python 3.12 is the recommended version and is used by the repository's CI configuration. A full Git clone is necessary for history-dependent tests. Download ZIP is sufficient for reading, editing and figure redraws.

Use the `.venv` interpreter consistently; no environment activation is required. The constraints file retains the certificate-runtime versions. The plotting installation does not install every optimisation or development dependency.

## Redraw a figure

```bash
.venv/bin/python tools/aidr.py redraw --figures S5
```

This reads the supplied panel CSV files and writes PDF, SVG and PNG to `paper/v0.27/figures/supplement/MY_REDRAW/`. It does not overwrite reference artwork. Select several figures with `--figures S3 S9`, omit the option for all ten, or add `--tiff` for TIFF output.

For corrected main-figure panels and their PowerPoint presentation:

```bash
.venv/bin/python tools/aidr.py main-figures
```

Output goes to `paper/v0.27/figures/main/rebuild/`. Add `--export-pdf` only when LibreOffice is installed. The existing reference PDFs do not need rebuilding just to read or use them.

See the [main](../paper/v0.27/figures/main/README.md) and [supplementary](../paper/v0.27/figures/supplement/README.md) editing guides for data formats and panel-specific cautions.

## Build the paper

Edit `paper/v0.27/latex/main.tex` and `supplement.tex`, then run:

```bash
.venv/bin/python tools/aidr.py paper --engine xelatex
```

XeLaTeX must be installed separately. Tectonic is also supported with `--engine tectonic`; an executable path is accepted. With no `--engine`, the existing build script searches for an installed engine. The build updates the two PDFs in the LaTeX folder.

Keep the `figures/` directory with the TeX files, including when uploading to Overleaf. References are already included in the TeX sources. Redrawing a figure does not insert it into the manuscript: copy the approved PDF into `latex/figures/` under the expected filename and then rebuild.

## Verify the download

```bash
python3.12 tools/aidr.py check --hashes
```

The check uses only the Python standard library. It verifies required paper files, figure links, Windows-compatible paths and recorded hashes. The original manifest and the explicit documentation-layout update jointly describe the current checkout. It is not a replay of the scientific experiments.

After intentional edits, hash mismatches are expected for the edited files. Review the Git diff rather than treating a mismatch as a reason to discard your work.

## Work with the research code

```bash
.venv/bin/python -m pip install -c requirements-certificate.txt -e ".[control,analysis,dev,paper]"
.venv/bin/python tools/aidr.py test
.venv/bin/python -m ruff check src tests
.venv/bin/python -m mypy src
```

The library is under `src/aidrbench/`, configurations under `configs/`, and study drivers under `manuscript/revisions/`. GPU power measurement requires the corresponding NVIDIA hardware and measurement environment; ordinary paper editing, redraws and code checks do not.

The public checkout contains compact evidence and plotting tables, not the complete production workload and recovery inputs. Read [the reproducibility scope](GITHUB_V027.md) before planning a full replay.

## Command reference

All commands run the existing project scripts using the interpreter that invoked `tools/aidr.py`. They resolve paths from the checkout rather than assuming the shell is in a particular directory.

| Command | Action |
| --- | --- |
| `doctor` | Inspect Python, checkout files, optional packages, Git history and TeX availability. |
| `check --hashes` | Verify the maintained file layout and recorded hashes. |
| `redraw --figures S5` | Redraw selected supplementary figures from CSV. |
| `main-figures` | Rebuild corrected main panels and PowerPoint. |
| `paper --engine xelatex` | Compile the main paper and supplement. |
| `test` | Run the existing pytest suite. |

Add `--dry-run` to any command other than `doctor` to print its underlying command without running it. The launcher never installs software, downloads production inputs or changes model parameters automatically.
