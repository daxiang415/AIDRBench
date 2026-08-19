# Nature Communications mainline execution status

The complete scientific specification is the repository root `README.md`.
This document records the executable route without mixing in controller or RL
competition. One fixed causal implementation is required for independent
capacity certification.

## Current state

- The active protocol is
  `data/manifests/nature_mainline_protocol_v1.yaml`.
- The primary estimand is the single-event
  duration–notice–reliability surface with nominal, perfect-information (PI),
  restricted non-anticipative (NA), and independently certified causal layers.
- Primary episodes contain exactly one event. Repeated events are a separate
  exhaustion experiment whose statistical unit is the joint episode.
- A primary event is sampled from predeclared 15:00--20:00 candidate hours on
  episode days 3--6. Future event limits remain hidden until notice.
- The reference virtual facility is fixed at 144 four-GPU nodes. Hardware
  lower/nominal/upper uncertainty bounds change the calibrated power parameters without
  silently resizing the facility.
- Only measured training and offline-inference classes appear in the mainline
  workload mix. Missing class power is fail-closed.
- Active-power intervals use independent run means. Idle and node-overhead
  bounds are respectively a within-run device range and an engineering
  assumption range, not confidence intervals.
- Existing development scenarios produced before this audit are invalidated by
  the new calibration hash, event policy and temporal split; they are retained
  only as historical diagnostics.
- The corrected lower-bound, nominal and upper-bound development ensembles each
  contain 100 matched frozen scenarios under `results/nature_mainline`. Each
  spans 81 unique episode starts from 2018-01-02 through 2018-07-29 and covers
  all 24 declared event-start candidates. Community and arrival file hashes are
  matched across power cases. This is development evidence only.
- All three 600-point PI solves (100 scenarios × 6 durations) completed with
  every solver status `optimal`, finite reported values and duration-monotone
  per-scenario frontiers. HiGHS uses one thread per solve and 16 independent
  scenario workers; both settings are recorded in the PI manifest. A
  100-scenario set cannot estimate the predeclared 99% reliability target at
  95% confidence.
- A CVXPY shape-inference warning found during this run was traced to
  `cp.sum()` reducing an uninitialized NumPy buffer. The model now uses
  mathematically equivalent all-ones dot products; strict warning-as-error
  replay reproduces the six capacities exactly.
- PI and restricted NA now share a compact, class-aware cumulative
  release/deadline formulation for preemptible fluid work. On three real
  nominal development scenarios and all six durations, its 18 PI capacities
  matched the earlier job-edge formulation exactly (maximum absolute
  difference `0.0 kW`) while completing in 24.9 s with peak RSS below 0.7 GiB.
  This equivalence check is implementation evidence, not a validation result.

### Completed restricted NA development surface

The nominal 100-scenario development ensemble has now been solved at the
empirical 95% target (95 of 100 scenarios) for all 18 preregistered
duration–notice points. The table is the restricted NA capacity in kW; every
entry is `optimal` and equals the matched empirical PI order statistic on the
same scenarios and five allowed failures.

| Duration | 0 h notice | 2 h notice | 6 h notice |
| ---: | ---: | ---: | ---: |
| 1 h | 56.42 | 56.42 | 56.42 |
| 2 h | 53.49 | 53.49 | 53.49 |
| 3 h | 45.17 | 45.17 | 45.17 |
| 4 h | 44.00 | 44.00 | 44.00 |
| 6 h | 43.01 | 43.01 | 43.01 |
| 8 h | 41.19 | 41.19 | 41.19 |

Thus the same-ensemble descriptive information gap is `0.0 kW` at all 18
points. This is not a confidence-bounded certificate: for example, the 1 h
empirical PI/NA value is `56.42 kW`, whereas the separately reported 95%-reliable,
95%-confidence PI tolerance bound is `53.01 kW`. These statistics answer
different questions and must not be subtracted or interchanged.

The absence of a notice effect is a result under the current fluid, preemptible
workload model: the policy can curtail at event start without checkpoint,
startup or gang-scheduling delay, and existing deadline slack is sufficient.
It does not establish that notice is generally irrelevant. A manuscript claim
that notice changes firm flexibility now requires a preregistered development
sensitivity with tighter deadlines/utilization or explicit checkpoint and
non-preemptive constraints; the nominal result must remain visible even if
those sensitivities produce a non-zero effect.

The scalable route first fixes the matched PI upper bound and deterministic
low-PI failure set, then builds a direct sparse cumulative-state model. For
multi-hour events it uses the minimum guaranteed delivered peak as the rebound
reference, which is stricter than the original actual-peak rule. Feasibility at
the PI upper bound therefore proves feasibility for the original rule. A
20-scenario comparison at 1 h/4 h and 0 h/2 h notice reproduced the earlier
exact MILP capacities and successful sets exactly. The full result contains
777,600 class-aware policy rows with zero within-node action disagreement and
is stored under `results/nature_mainline/development_v2_na_nominal_q95_full`.
The three independently written notice partitions carry source artifact hashes
in the merged manifest. Each six-point partition completed in about 20 min
while run concurrently, with peak RSS between 1.5 and 1.7 GiB.

### Completed development PI sensitivity

The table reports exact nonparametric lower-tolerance capacities at 95%
reliability and 95% confidence. Parentheses are fractions of each power case's
reference-mix operating peak, not fractions of GPU nameplate power.

| Duration | Lower power bound | Nominal power | Upper power bound |
| ---: | ---: | ---: | ---: |
| 1 h | 49.91 kW (30.32%) | 53.01 kW (26.37%) | 56.60 kW (23.88%) |
| 2 h | 41.87 kW (25.44%) | 44.46 kW (22.12%) | 47.48 kW (20.03%) |
| 3 h | 38.79 kW (23.56%) | 41.19 kW (20.49%) | 43.98 kW (18.56%) |
| 4 h | 37.81 kW (22.97%) | 40.15 kW (19.97%) | 42.87 kW (18.09%) |
| 6 h | 37.81 kW (22.97%) | 40.15 kW (19.97%) | 42.87 kW (18.09%) |
| 8 h | 35.56 kW (21.60%) | 37.76 kW (18.79%) | 40.32 kW (17.01%) |

Absolute deliverable kW rises with the calibrated active-power slope, while
capacity as a fraction of the corresponding operating peak falls. Hardware
translation must therefore retain both the class-specific compute-throughput
model and the power model; watts alone do not justify H100/H200 equivalence.
- Locked-ID seeds `30000..30499` define the main certificate. Locked-OOD seeds
  `40000..40499` are a separate extrapolation test. Both remain unrun.

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
  --workers 8 \
  --output results/nature_mainline/development_pi
```

The restricted-NA grid may be written as independent notice partitions and
hash-merged, which limits the loss from an interrupted long run:

```bash
for notice in 0 2 6; do
  python -m aidrbench optimize non-anticipative-firm \
    --scenarios results/nature_mainline/development_v2_nominal \
    --durations 1 2 3 4 6 8 \
    --notice-hours "$notice" \
    --ensemble-success-fraction-target 0.95 \
    --matched-pi-frontier \
      results/nature_mainline/development_v2_pi_nominal/pi_frontier.parquet \
    --output "results/nature_mainline/development_v2_na_nominal_q95_n${notice}"
done

python -m aidrbench optimize merge-non-anticipative \
  --inputs \
    results/nature_mainline/development_v2_na_nominal_q95_n0 \
    results/nature_mainline/development_v2_na_nominal_q95_n2 \
    results/nature_mainline/development_v2_na_nominal_q95_n6 \
  --output results/nature_mainline/development_v2_na_nominal_q95_full
```

After validation scenarios are frozen, select one fixed causal candidate grid:

```bash
python -m aidrbench certify frozen-select \
  --scenarios results/nature_mainline/validation_nominal \
  --durations 1 2 3 4 6 8 \
  --notices 0 2 6 \
  --candidate-fractions 0.0 0.1 0.2 0.3 0.4 0.5 0.6 0.7 0.8 0.9 1.0 \
  --reliability 0.95 \
  --confidence 0.95 \
  --output results/nature_mainline/causal_selection_q95
```

Only after the plan is frozen and locked-ID is explicitly authorized, evaluate
that fixed selection without another search:

```bash
python -m aidrbench certify frozen-test \
  --scenarios results/nature_mainline/locked_id_nominal \
  --selection results/nature_mainline/causal_selection_q95/causal_selection.json \
  --output results/nature_mainline/causal_locked_id_q95
```

`--workers` only parallelizes independent frozen scenarios. It does not alter
the optimization model, scenario order, statistical unit, or result schema.

Without `--require-execution-ready`, `protocol-check` validates only the
committed preregistration structure and is therefore suitable for a clean CI
checkout. Formal data-server runs must use the flag so missing/hash-mismatched
inputs or solver dependencies fail closed.

The one-scenario commands above are code-path smoke tests, not statistical
results. PI uses an exact-binomial nonparametric lower tolerance order
statistic. Fixed, independently selected candidates may use the declared
one-sided Wilson rule. A 100-episode set supports the 0.90 and 0.95 designs but
cannot establish 0.99 at 95% confidence; insufficient rows are `NaN` with
`estimable=false`, never zero-capacity claims. The locked-ID 500-episode set is
sized for the final 0.99 design. Locked OOD does not substitute for this primary
test.

For the hardware uncertainty smoke, write each power case to a separate
directory:

```bash
python -m aidrbench scenario freeze \
  --config configs/env/nature_mainline_development.yaml \
  --calibration-power-case lower_bound \
  --seeds 10000 \
  --output results/nature_mainline/development_lower_bound
```

Use `nominal` and `upper_bound` analogously. Do not generate locked scenarios
until the experiment design and result schemas are frozen.

## Remaining mainline work

1. Run preregistered development sensitivities that can expose or bound the
   observed zero notice/information effect, then use the frozen robust-MPC route
   for the independent operational certificate.
2. Add the separate repeated-event exhaustion generator and residual
   flexibility summaries.
3. Run and aggregate the 2 × 2 × 2 hosting matrix and PV/BESS response surface.
4. Run success-criterion sensitivities, freeze all choices, then run validation,
   locked ID once, and locked OOD separately once.

Each locked config is technically guarded. Before its one permitted generation,
the protocol must be committed with `analysis_plan_status: frozen` and
the corresponding `locked_id_status` or `locked_ood_status` set to
`approved_for_one_time_run`. The CLI additionally requires
`--preregistration-manifest`, `--unlock-locked-ood`, and
`--acknowledge-one-time-locked-use`, a clean Git tree, and a new output path.
After success it records the protocol SHA/Git commit and marks the authorization
`consumed`.
