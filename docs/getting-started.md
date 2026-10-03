# Installation and verification

The examples below use Linux/macOS. PowerShell commands are in the [Windows guide](../WINDOWS_START_HERE.md).

## Installation

Use Python 3.12, the version used by CI, and a full Git clone:

```bash
git clone https://github.com/daxiang415/AIDRBench.git
cd AIDRBench
python3.12 -m venv .venv
.venv/bin/python -m pip install -c requirements-certificate.txt -e ".[control,analysis,dev,paper]"
.venv/bin/python tools/aidr.py doctor
```

The constraints file pins the certificate-runtime dependencies. A plotting-only installation can use `.[paper]`; it does not include the optimisation and development dependencies.

## Checkout verification

```bash
.venv/bin/python tools/aidr.py check --hashes
```

This standard-library check verifies required files, figure references, path compatibility and recorded hashes. The original release manifest is combined with the maintained documentation mapping. Local changes cause mismatches for the affected files.

## Software tests

```bash
.venv/bin/python tools/aidr.py test
.venv/bin/python -m ruff check src tests
.venv/bin/python -m mypy src
```

History-dependent certificate tests require a full Git clone. A ZIP download does not contain Git history.

The library is in `src/aidrbench/`, configurations in `configs/`, and study drivers in `manuscript/revisions/`. Tests and table-based figure generation run on a CPU; hardware power measurements require the corresponding GPUs.

## Figure reproduction

```bash
.venv/bin/python tools/aidr.py redraw --figures S5
.venv/bin/python tools/aidr.py main-figures
```

The first command reads supplementary panel CSV files and writes to `paper/v0.27/figures/supplement/MY_REDRAW/`. Omit `--figures S5` to generate all supplementary figures. Multiple selections and TIFF output are supported, for example `--figures S3 S9 --tiff`.

The second command rebuilds main panels and PowerPoint under `paper/v0.27/figures/main/rebuild/`. Automatic PDF export requires LibreOffice and `--export-pdf`.

These commands leave the reference artwork in place. Figure reproduction verifies the supplied plotting data, not a fresh execution of the underlying experiments. See the [figure index](figures.md) and [data availability](GITHUB_V027.md).

## Commands

| Command | Function |
| --- | --- |
| `doctor` | Report checkout files and optional dependencies |
| `check --hashes` | Verify the release and maintained-file hashes |
| `redraw --figures S5` | Generate selected supplementary figures from CSV |
| `main-figures` | Rebuild main panels and PowerPoint |
| `test` | Run pytest |

Add `--dry-run` to a command other than `doctor` to inspect the underlying invocation without executing it. Commands use the invoking Python interpreter and resolve script paths from the checkout.
