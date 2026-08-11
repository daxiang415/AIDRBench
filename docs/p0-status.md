# P0 status and deferred checks

This offline skeleton can be imported and tested without third-party packages.
The following README P0 completion checks are intentionally deferred because
they require network access, software installation, Docker images, or hardware
execution:

- install `uv`, create `uv.lock`, and run `uv sync`;
- run the CUDA Docker GPU smoke test;
- capture durable system and GPU power-default records;
- install and run pytest, Ruff, and mypy.

No Docker image or model is required for the current offline check. vLLM and an
open model are P2 calibration workloads and require separate approval.
