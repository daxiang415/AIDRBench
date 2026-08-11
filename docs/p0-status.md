# P0 status

P0 was completed on 2026-08-11 using the isolated Conda environment
`aidrbench` (Python 3.12.13). The repository also keeps `uv.lock` and
`requirements.lock.txt` as Python dependency locks; Conda remains the runtime
environment requested for this machine.

Completed checks:

- the CUDA 13.3.1 container smoke test sees all four GPUs;
- read-only system, GPU topology, and default power-limit snapshots are stored
  under the ignored local directory `results/system/`;
- `pytest`, Ruff, mypy, and `scripts/check_project.sh` pass in the Conda
  environment;
- exact Conda package builds are recorded in `environment.lock.yml`;
- lockfile hashes and `conda list --explicit` are captured with the system
  evidence.

P0 does not mutate GPU settings. vLLM, AIPerf, power-cap calibration, and other
hardware experiments belong to P2 and require their own manifests.
