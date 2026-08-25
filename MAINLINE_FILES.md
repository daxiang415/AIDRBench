# AIDRBench formal mainline

This branch contains one runnable research line: the *Nature Communications*
study of job-derived firm demand response and its community-PV consequences.
It is the repository index for deciding which files are authoritative.

## Authority order

When two descriptions differ, use this order:

1. `data/manifests/nature_mainline_protocol_v1.yaml` and hash-bound result receipts;
2. frozen scenario, calibration and source-data specifications;
3. `manuscript/nature_communications_article.md` and
   `manuscript/supplementary_information.md`;
4. `README.md` and explanatory documents.

Locked-ID and locked-OOD artifacts are immutable evidence. A narrative edit
must never silently change their meaning, controller hash or scenario hash.

## Formal scientific assets

- `README.md`: scientific question, estimands, hypotheses and experiment plan.
- `manuscript/`: the article, Supplementary Information, terminology ledger,
  evidence allocation and screened reference set.
- `configs/env/nature_mainline_*.yaml`: development, validation, locked-ID and
  locked-OOD environments.
- `configs/controller/nature_robust_mpc_v1.yaml`: the complete frozen causal
  controller specification.
- `configs/experiment/nature_*.yaml`, `configs/sensitivity/nature_*.yaml` and
  `configs/community/pv_bess.yaml`: exhaustion, hosting, renewable-integration
  and sparse sensitivity specifications.
- `configs/paper/nature_source_data_v1.yaml` and
  `configs/paper/nature_supplementary_figures_v1.yaml`: paper Source Data and
  supplementary-figure contracts.
- `data/calibration/`: measured four-GPU power evidence and the validated
  calibration artifact.
- `data/examples/nature_supplementary_validation_v1/`: the deterministic,
  non-locked validation example needed to regenerate Supplementary Figures 3–4.
- `data/manifests/nature_*.yaml`: preregistration and hash-bound execution
  receipts. Downloaded data and generated Parquet results remain outside Git.
- `src/aidrbench/`: the hourly environment, causal controllers, optimisation,
  certification, statistics and paper-export implementation.
- `tests/` and `.github/workflows/ci.yml`: independent executable checks.
- `docs/figures/nature_mainline_v1/` and
  `docs/figures/nature_supplementary_v1/`: web-review previews and output
  manifests generated from the verified inputs.

The generic `configs/env/hourly_{continuous,discrete}.yaml` fixtures are kept
only to exercise the public environment interface in unit tests. They are not
formal result configurations.

## Deliberately excluded

This mainline excludes reinforcement-learning training and rewards,
hardware-in-the-loop power actuation, legacy minute-level protocols, controller
leaderboards, and H100/H200 capacity extrapolation. None is needed to reproduce
the paper's claims. Earlier implementations remain available through Git
history rather than coexisting with the formal files.

## Minimum verification

```bash
python -m aidrbench project-check
python -m aidrbench protocol-check \
  --manifest data/manifests/nature_mainline_protocol_v1.yaml
ruff check .
mypy src
pytest
```

Paper source data and figures are regenerated with the commands in
`docs/paper-packaging.md`.
