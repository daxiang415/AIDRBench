# Reproducibility environment receipt

Date verified: 2026-08-25

This receipt describes the environment used for the final repository QA, Source Data export and manuscript-figure generation. Formal scientific artifacts additionally retain their own input, scenario, controller, configuration and result hashes.

## Software

| Component | Version |
|---|---:|
| Python | 3.12.13 |
| NumPy | 2.5.2 |
| pandas | 2.3.3 |
| PyArrow | 21.0.0 |
| SciPy | 1.18.0 |
| CVXPY | 1.9.2 |
| HiGHS | 1.15.1 |
| Gymnasium | 1.3.0 |
| Matplotlib | 3.11.1 |

The complete dependency graph is pinned by `uv.lock` (SHA-256 `144f1f6af92d27d9b6051ae80430f7d135e4d0ec352aadd7ecc51cb4904c8a16`). The optimisation runner assigns one HiGHS thread to each scenario process and performs scenario-level parallelism outside the solver.

## Verification host

- Linux 6.8.0-110-generic, x86-64, glibc 2.39.
- AMD Ryzen Threadripper PRO 9975WX, 32 physical cores and 64 logical CPUs.
- GPU execution was not required for optimisation, certification, Source Data export or figure generation.
- The separate calibration artifact records four NVIDIA RTX PRO 6000 Blackwell Max-Q GPUs connected through PCI Express without NVLink. Its workload records identify CUDA 13.0 and retain raw telemetry hashes.

## Quality gates

- dependency lock check: passed;
- repository skeleton check: passed;
- Ruff: passed;
- Mypy strict mode over 56 source files: passed;
- Pytest: 160 passed;
- formal protocol structure and execution readiness: passed;
- source-manifest file hashes and formal-mainline bindings: passed;
- five main and four supplementary figures: static preflight passed, visual inspection completed and PDF text floor at least 5 pt.

The manuscript Source Data were re-exported from clean scientific commit `f2f4dc699c067891b84601ec8bd9ddd8505f849c`. The resulting manifest has SHA-256 `7351fd609c9b23eb92a7e0e473f4279a61d3b5f59c7b9c913dd32fa6a40fd593` and records `working_tree_dirty=false`. The release workflow must archive this bundle and the full-format figures together with the immutable Git tag and DOI.
