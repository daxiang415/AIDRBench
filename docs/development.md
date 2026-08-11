# Development environment

Use the project-specific Conda environment; do not install project packages in
`base`:

```bash
conda env create --file environment.lock.yml
conda activate aidrbench
python -m pytest -q
ruff check .
mypy
```

For a dependency refresh, edit `pyproject.toml`, regenerate `uv.lock` and
`requirements.lock.txt`, update the existing environment, then export the exact
Conda state to `environment.lock.yml`. Never hand-edit `uv.lock`.

The quick repository checks are:

```bash
./scripts/check_project.sh
aidrbench project-check
aidrbench show-actions
```

Downloaded raw data, generated Parquet files, and machine-specific results stay
outside Git. Their source metadata and SHA-256 manifests are tracked under
`data/manifests/`.

AWS data access is isolated from the scientific Python stack because current
AWS CLI and pandas dependency constraints differ:

```bash
conda env create --file environment.data-tools.lock.yml
conda run --name aidrbench-data-tools aws --version
```
