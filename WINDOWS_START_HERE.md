# Running AIDRBench on Windows

Use Python 3.12 and PowerShell. A full Git clone is required for tests that replay historical commits. GitHub's **Code → Download ZIP** is sufficient for reading the paper and reproducing figures from the supplied tables.

## Installation

```powershell
git clone https://github.com/daxiang415/AIDRBench.git
cd AIDRBench
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -c requirements-certificate.txt -e ".[control,analysis,dev,paper]"
.\.venv\Scripts\python.exe tools/aidr.py doctor
```

For figure reproduction only, replace `.[control,analysis,dev,paper]` with `.[paper]`. Use the virtual environment's interpreter directly; activation and PowerShell execution-policy changes are not required.

`doctor` reports available packages, checkout files, Git history and optional TeX tools. Missing optimisation or development packages are expected with a plotting-only installation. TeX is not needed to run the benchmark or reproduce figures.

## Verify the checkout

```powershell
.\.venv\Scripts\python.exe tools/aidr.py check --hashes
```

This compares files against the release and maintained-documentation manifests. It does not run the experiments. Intentional local changes produce hash mismatches.

## Reproduce figures

Generate one supplementary figure, or several:

```powershell
.\.venv\Scripts\python.exe tools/aidr.py redraw --figures S5
.\.venv\Scripts\python.exe tools/aidr.py redraw --figures S3 S9 --tiff
```

Omit `--figures` to generate all ten. Outputs are saved under `paper/v0.27/figures/supplement/MY_REDRAW/`. The scripts read CSV files; Excel workbooks are parallel copies of those values. Reference figures are not overwritten.

Rebuild the main figure panels and presentation:

```powershell
.\.venv\Scripts\python.exe tools/aidr.py main-figures
```

Outputs are saved under `paper/v0.27/figures/main/rebuild/`. Automatic PDF export additionally requires LibreOffice and `--export-pdf`. The existing reference PDFs can be viewed without either PowerPoint or LibreOffice.

See the [figure index](docs/figures.md) for data paths and captions.

## Run tests

With the full dependency set installed:

```powershell
.\.venv\Scripts\python.exe tools/aidr.py test
.\.venv\Scripts\python.exe -m ruff check src tests
.\.venv\Scripts\python.exe -m mypy src
```

The supplied plotting and test workflows run on a CPU. Hardware power-measurement scripts require the appropriate NVIDIA GPUs. Full experiment replay also needs the external inputs listed in [data availability](docs/GITHUB_V027.md).

## Troubleshooting

| Problem | Check |
| --- | --- |
| `py` is not recognised | Install Python with its Windows launcher, or use the full interpreter path. |
| A package cannot be imported | Use the same `.venv` interpreter for installation and execution. |
| A historical commit cannot be found | Use a full clone; run `git fetch --unshallow` for a shallow clone. |
| A hash check fails | Compare the affected file with `git diff` to distinguish local changes from an incomplete checkout. |
| Automatic main-figure PDF export fails | Check the LibreOffice installation; omit `--export-pdf` to generate panels and PowerPoint only. |
