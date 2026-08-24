# Development environment

Use the project-specific Conda environment; do not install project packages in
`base`:

```bash
conda env create --file environment.yml
conda activate aidrbench
python -m pytest -q
ruff check .
mypy
```

For a dependency refresh, edit `pyproject.toml`, regenerate `uv.lock` and
`requirements.lock.txt`, then recreate or update the environment. Never
hand-edit either lock file.

The quick repository checks are:

```bash
./scripts/check_project.sh
aidrbench project-check
python -m aidrbench protocol-check \
  --manifest data/manifests/nature_mainline_protocol_v1.yaml
```

Downloaded raw data, generated Parquet files, and machine-specific results stay
outside Git. Their source metadata and SHA-256 manifests are tracked under
`data/manifests/`.

The exact formal repository boundary is recorded in `MAINLINE_FILES.md`.
RL training, hardware-in-the-loop actuation and cross-SKU GPU extrapolation are
outside this branch; their former implementations remain recoverable from Git
history.

AWS data access is isolated from the scientific Python stack because current
AWS CLI and pandas dependency constraints differ:

```bash
conda env create --file environment.data-tools.lock.yml
conda run --name aidrbench-data-tools aws --version
```
