# Nature Communications mainline execution status

The complete scientific specification is the repository root `README.md`.
This document records the executable route without mixing in controller or RL
development.

## Current state

- The active protocol is
  `data/manifests/nature_mainline_protocol_v1.yaml`.
- The primary estimand is the single-event
  duration–notice–reliability surface with nominal, perfect-information (PI),
  and restricted non-anticipative (NA) capacity layers.
- Primary episodes contain exactly one event. Repeated events are a separate
  exhaustion experiment whose statistical unit is the joint episode.
- The reference virtual facility is fixed at 144 four-GPU nodes. Hardware
  lower/nominal/upper cases change the calibrated power parameters without
  silently resizing the facility.
- Only measured training and offline-inference classes appear in the mainline
  workload mix. Missing class power is fail-closed.
- The locked OOD seed range `30000..30499` remains declared but unrun.

## Readiness commands

```bash
python -m aidrbench protocol-check \
  --manifest data/manifests/nature_mainline_protocol_v1.yaml \
  --require-execution-ready

python -m aidrbench scenario freeze \
  --config configs/env/nature_mainline_development.yaml \
  --seeds 10000 \
  --output results/nature_mainline/development_scenarios

python -m aidrbench optimize pi-frontier \
  --scenarios results/nature_mainline/development_scenarios \
  --durations 1 2 3 4 6 8 \
  --reliabilities 0.90 0.95 0.99 \
  --confidence-level 0.95 \
  --nominal-flexibility-fraction 0.50 \
  --output results/nature_mainline/development_pi
```

Without `--require-execution-ready`, `protocol-check` validates only the
committed preregistration structure and is therefore suitable for a clean CI
checkout. Formal data-server runs must use the flag so missing/hash-mismatched
inputs or solver dependencies fail closed.

The one-scenario commands above are code-path smoke tests, not statistical
results. PI uses an exact-binomial nonparametric lower tolerance order
statistic. Fixed, independently selected candidates may use the declared
one-sided Wilson rule. A 100-episode set supports the 0.90 and 0.95 designs but
cannot establish 0.99 at 95% confidence; insufficient rows are `NaN` with
`estimable=false`, never zero-capacity claims. The locked 500-episode set is
sized for the final 0.99 design.

For the hardware uncertainty smoke, write each power case to a separate
directory:

```bash
python -m aidrbench scenario freeze \
  --config configs/env/nature_mainline_development.yaml \
  --calibration-power-case lower_ci \
  --seeds 10000 \
  --output results/nature_mainline/development_lower_ci
```

Use `nominal` and `upper_ci` analogously. Do not generate locked OOD scenarios
until the experiment design and result schemas are frozen.

## Remaining mainline work

1. Freeze the complete development scenarios for all three calibration cases.
2. Compute the PI surface and use development results to diagnose numerical or
   model defects only.
3. Complete the scalable NA solver route before attempting the full grid; the
   current joint MILP is a restricted scenario-based causal bound, not an
   out-of-sample controller certificate, and is too expensive for a blind full
   run.
4. Add the separate repeated-event exhaustion generator and residual
   flexibility summaries.
5. Run and aggregate the 2 × 2 × 2 hosting matrix and PV/BESS response surface.
6. Freeze all choices, then run validation and finally the locked OOD set once.

The locked config is technically guarded. Before its one permitted generation,
the protocol must be committed with `analysis_plan_status: frozen` and
`locked_ood_status: approved_for_one_time_run`. The CLI additionally requires
`--preregistration-manifest`, `--unlock-locked-ood`, and
`--acknowledge-one-time-locked-use`, a clean Git tree, and a new output path.
After success it records the protocol SHA/Git commit and marks the authorization
`consumed`.
