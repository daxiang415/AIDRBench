# Offline development

The P0 checks intentionally use only Python 3.12's standard library:

```bash
./scripts/check_project.sh
PYTHONPATH=src python3 -m aidrbench show-actions
```

When network access is explicitly approved in a later phase, install `uv`, run
`uv lock` and `uv sync --extra dev`, then use `uv run pytest -q`, Ruff, and mypy.
Do not hand-create `uv.lock`.
