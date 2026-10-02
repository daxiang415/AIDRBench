# Using AIDRBench on Windows

Start with the [paper](paper/v0.27/latex/main.pdf), [figure gallery](docs/figures.md), or the workflow below. Paper editing and figure redraws do not need a GPU or the original Linux server.

## Download

For reading and figure editing, choose **Code → Download ZIP** on GitHub and extract the archive to a short path such as `C:\research\AIDRBench`.

For development, clone with Git or GitHub Desktop. A full clone preserves the history needed by the certificate-replay tests; a ZIP does not.

```powershell
git clone https://github.com/daxiang415/AIDRBench.git
cd AIDRBench
```

Run the following commands in PowerShell from the repository root.

## Set up Python

Install Python 3.12, then create a virtual environment:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -c requirements-certificate.txt -e ".[paper]"
.\.venv\Scripts\python.exe tools/aidr.py doctor
```

These commands use the environment's interpreter directly, so PowerShell execution-policy changes and activation scripts are unnecessary. `doctor` checks the checkout, lists missing optional dependencies and reports available TeX tools. Missing development dependencies are expected with a plotting-only installation.

## Redraw supplementary figures

```powershell
.\.venv\Scripts\python.exe tools/aidr.py redraw --figures S5
```

Omit `--figures S5` for all ten figures, or use `--figures S3 S9` for a selection. Add `--tiff` for TIFF output. Results go to `paper/v0.27/figures/supplement/MY_REDRAW/`; the reference figures are untouched.

The plotter reads CSV, not Excel. The Excel workbooks contain the same plotting values; a workbook edit does not update a CSV automatically. Redraws use the supplied values, not new simulations, and their layout need not match the reference artwork pixel for pixel.

## Edit main figures

Open the editable PowerPoint/SVG files in [the main figure pack](paper/v0.27/figures/main/README.md). The panel tables are in `02_PANEL_DATA/F01` through `F06`.

```powershell
.\.venv\Scripts\python.exe tools/aidr.py main-figures
```

This rebuilds the corrected panels and PowerPoint under `paper/v0.27/figures/main/rebuild/`. LibreOffice is not required for this step. To export the rebuilt presentation to PDF automatically, install LibreOffice and add `--export-pdf`.

Some corrected PowerPoint panels are embedded SVG, not native Excel charts. Edit their CSV/script and replace the SVG when changing those panels. Keep `Figure_1_assets/` beside Figure 1 when copying its SVG.

## Edit and build the paper

Edit `paper/v0.27/latex/main.tex` and `supplement.tex`. Install MiKTeX/TeX Live with XeLaTeX, or install Tectonic:

```powershell
.\.venv\Scripts\python.exe tools/aidr.py paper --engine xelatex
```

The build updates `main.pdf` and `supplement.pdf` in the LaTeX directory. Alternatively, upload the entire `paper/v0.27/latex/` directory to Overleaf and select XeLaTeX. Keep its `figures/` subdirectory. References are included in the TeX sources.

A redraw does **not** automatically replace a paper figure. Copy the approved single-figure PDF into `paper/v0.27/latex/figures/`, retain its expected filename, then rebuild. The English Markdown collaboration copies and the LaTeX sources are separate files; edits do not synchronise automatically.

## Check the checkout or develop the code

The file/hash check uses only the Python standard library:

```powershell
py -3.12 tools/aidr.py check --hashes
```

For the research test suite, use a full Git clone and install the development dependencies:

```powershell
.\.venv\Scripts\python.exe -m pip install -c requirements-certificate.txt -e ".[control,analysis,dev,paper]"
.\.venv\Scripts\python.exe tools/aidr.py test
.\.venv\Scripts\python.exe -m ruff check src tests
.\.venv\Scripts\python.exe -m mypy src
```

Intentional edits change hashes; a mismatch after editing is not evidence that the original download was corrupt. Compare your changes with Git before updating any recorded hashes. Full study replay requires separately held production inputs; see [data and reproducibility](docs/GITHUB_V027.md).

## Common problems

| Symptom | What to check |
| --- | --- |
| `py` is not recognised | Install Python 3.12 with its Windows launcher, or use the full path to that interpreter. |
| A package cannot be imported | Run the installation command with the same `.venv` interpreter used for the task. |
| TeX cannot be found | Install XeLaTeX/Tectonic and reopen PowerShell, or pass the full executable path to `--engine`. |
| Certificate-replay tests cannot find a commit | Use a full Git clone. For a shallow clone, run `git fetch --unshallow`. |
| A figure changed but the paper did not | Replace the corresponding PDF in `latex/figures/` and rebuild the paper. |

To save edits, create a branch before working. Add only the files you intend to publish; do not add `.venv`, temporary redraw output or bulk raw data.

```powershell
git switch -c paper-edits
git status
git add paper/v0.27/latex/main.tex
git commit -m "Revise manuscript text"
git push -u origin paper-edits
```
