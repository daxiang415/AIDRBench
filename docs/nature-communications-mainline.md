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

The absence of a notice effect is a potentially structural result under the
current fluid, preemptible workload model and is not a failure to repair.
Advance notice weakly expands the information set, so the preregistered claim
is `dF/dN >= 0`, not a strictly positive derivative. A positive notice gain is
conditional on eligible pre-execution work, pre-event spare capacity, binding
future service constraints, and an induced schedule change. Development-only
diagnostics measure those conditions without changing the locked scenarios or
adding model complexity to manufacture a positive result.

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

After validation scenarios are frozen, select one fixed causal candidate with
the complete, hash-locked robust-MPC specification. The formal route never
uses Python controller defaults:

```bash
python -m aidrbench certify frozen-select \
  --scenarios results/nature_mainline/validation_nominal \
  --controller-config configs/controller/nature_robust_mpc_v1.yaml \
  --durations 1 2 3 4 6 8 \
  --notices 0 2 6 \
  --search binary \
  --candidate-fractions 0.0 1.0 \
  --binary-iterations 10 \
  --reliability 0.95 \
  --confidence 0.95 \
  --workers 16 \
  --output results/nature_mainline/causal_selection_q95
```

The 0.95 target is the headline certificate. The same frozen search is
predeclared for the secondary q={0.90,0.99} targets in separate output
directories; these are interval-wise certificates, not a simultaneous
confidence statement for the full surface.

Only after the plan is frozen and locked-ID is explicitly authorized, evaluate
that fixed selection without another search:

```bash
python -m aidrbench certify frozen-test \
  --scenarios results/nature_mainline/locked_id_nominal \
  --selection results/nature_mainline/causal_selection_q95/causal_selection.json \
  --controller-config configs/controller/nature_robust_mpc_v1.yaml \
  --workers 16 \
  --output results/nature_mainline/causal_locked_id_q95
```

`causal_selection.json` records the normalized controller specification, its
SHA-256, the raw YAML SHA-256, the Git commit, and the hashes of every source
file on the formal controller/evaluator path. `frozen-test` recomputes all of
them and fails closed on any mismatch.

Because the selection pins the exact Git commit, the one-time locked-ID
authorization must be committed before `frozen-select`; selection and all
predeclared locked-ID replays then run from that same clean commit. Therefore
the current frozen-plan stage stops after validation scenario generation and
hash audit, and requests explicit author authorization before capacity
selection or locked access.

The 100 validation scenarios (seeds 20000--20099) have now been generated from
the frozen plan at commit `0659eb3` and passed payload-hash, seed, event-anchor,
random-stream and no-DR service audits. The aggregate receipt is
`data/manifests/nature_mainline_validation_scenarios_v1.yaml`. No controller
has been evaluated and no capacity has been selected on this set.

The preregistered notice-mechanism diagnostic reuses the completed nominal PI
and NA artifacts; it does not rerun the nominal NA grid and cannot read a
locked path:

```bash
python -m aidrbench optimize notice-diagnostics \
  --scenarios results/nature_mainline/development_v2_nominal \
  --pi-frontier results/nature_mainline/development_v2_pi_nominal/pi_frontier.parquet \
  --na-frontier results/nature_mainline/development_v2_na_nominal_q95_full/non_anticipative_frontier.parquet \
  --na-policies results/nature_mainline/development_v2_na_nominal_q95_full/non_anticipative_policies.parquet \
  --controller-config configs/controller/nature_robust_mpc_v1.yaml \
  --durations 4 8 --notices 0 6 --reliability 0.95 \
  --workers 4 \
  --output results/nature_mainline/development_notice_diagnostics_v2
```

This diagnostic does not select an MPC capacity on development. For each
duration it evaluates the frozen controller specification at the smaller of
the already-computed N=0 and N=6 restricted-NA capacities. On the 100 matched
development scenarios, PI and NA notice gains are both zero at H=4 and H=8.
The fixed-capacity robust-MPC success fraction is 0.92 at 44.00 kW and 41.19
kW, respectively, with interval delivery binding. At N=6 the scenarios still
contain a mean 1,829 GPU-hour causal upper bound on pre-executable work and 133
GPU-hours of no-control spare capacity, and the paired robust-MPC schedule
changes by about 1.3 GPU-hours per pre-event interval. Thus notice changes the
information nodes and dispatch but does not relax the binding delivery limit
in this development diagnostic. This is a mechanism result, not a locked-data
certificate.

The sparse sensitivity schema separates flexible arrival utilization, rigid
GPU utilization, and deadline slack. Every case must pass the no-DR service
gate before any sensitivity frontier is permitted:

```bash
python -m aidrbench scenario check-sensitivities \
  --specification configs/sensitivity/nature_sparse_factorial_v1.yaml \
  --seeds 10000 10001 10002 \
  --output results/nature_mainline/sensitivity_service_gate_v2
```

The success-definition sensitivity is a separate, predeclared
one-factor-at-a-time design rather than a Cartesian product. Mean and
minimum-interval delivery thresholds move together; deadline, rebound and
window-relief thresholds change one at a time. The command refuses to start
unless the hashed no-DR service gate above passed:

```bash
python -m aidrbench optimize criteria-sensitivity \
  --scenarios results/nature_mainline/development_v2_nominal \
  --specification configs/sensitivity/nature_success_criteria_oat_v1.yaml \
  --workers 16 \
  --output results/nature_mainline/development_criteria_sensitivity_v2
```

The hashed gate passed all 27 no-DR evaluations (nine sparse workload cases
and three development seeds) with zero baseline deadline misses and zero
terminal backlog. The complete criteria sensitivity then solved 1,800 optimal
PI programs (100 scenarios × two durations × nine cases). At q=0.95 and 95%
confidence, the reference capacities are 40.15 kW for H=4 h and 37.76 kW for
H=8 h. Relaxing the linked mean/interval delivery threshold from 0.95 to 0.90
raises them to 42.38 and 39.86 kW; tightening it to 0.98 lowers them to 38.92
and 36.60 kW. The predeclared deadline-miss, rebound and window-relief
variations do not change either capacity, although the optimizer changes the
schedule to satisfy the altered constraint. This identifies interval delivery
as the capacity-setting operational definition at these development points;
it is not a causal or locked certificate. A clean-tree repeat at commit
`9924ea8` reproduced every capacity/status value and the boundary artifact
byte-for-byte; raw frontier bytes differ only in solver timing columns.

The paired sparse-workload PI pipeline is implemented separately from the
success-definition analysis. It freezes the same 100 development seeds for
all nine workload cases, verifies the paired community/event/random-stream
hashes, and then evaluates H={4,8} at q=0.95. The service-gate and scenario
specification hashes are checked fail closed:

```bash
python -m aidrbench scenario freeze-sensitivities \
  --specification configs/sensitivity/nature_workload_pi_v1.yaml \
  --output results/nature_mainline/development_workload_scenarios_v1

python -m aidrbench optimize workload-sensitivity \
  --scenarios results/nature_mainline/development_workload_scenarios_v1 \
  --specification configs/sensitivity/nature_workload_pi_v1.yaml \
  --workers 16 \
  --output results/nature_mainline/development_workload_sensitivity_v1
```

The complete development run solved all 1,800 PI programs at commit
`45eeb58`. The 900 frozen scenarios also have zero no-DR baseline deadline
misses and zero terminal backlog. At q=0.95 and 95% confidence, increasing
flexible arrival utilization from 0.65 to 0.80 raises the H=4 and H=8
boundaries from 40.15 and 37.76 kW to 77.99 and 53.49 kW; decreasing it to
0.50 lowers them to 30.88 and 29.05 kW. The predeclared rigid-utilization and
deadline-slack changes do not alter these boundaries. Rigid load is additive
and therefore cancels in the baseline-relative single-event reduction metric;
it remains relevant to PCC headroom and hosting analyses. The deadline result
is limited to the tested sparse points and Model A service thresholds. These
are development PI bounds, not causal or generalization certificates.

Model A is frozen at Git commit `d03b44090b2c7ca6a5ae73bb2eb7a611f36a71e9`.
The separate repeated-event layer references that commit and the exact SHA-256
of the completed N=0 development capacity table. The complete 100-scenario
development experiment is generated and evaluated with:

```bash
python -m aidrbench scenario freeze-exhaustion \
  --specification configs/experiment/nature_exhaustion_v1.yaml \
  --seeds {10000..10099} \
  --output results/nature_mainline/development_exhaustion_v1

python -m aidrbench optimize exhaustion-diagnostics \
  --scenarios results/nature_mainline/development_exhaustion_v1 \
  --specification configs/experiment/nature_exhaustion_v1.yaml \
  --workers 32 \
  --output results/nature_mainline/development_exhaustion_diagnostics_v1
```

For every repeated event, the diagnostic also runs a fresh single-event
counterfactual at the same scenario and clock hour. This pairing prevents the
recovery-gap comparison from confusing history-dependent exhaustion with a
different community-load period. Delivery, rebound and window relief are
event-local; deadline misses and terminal backlog enter only joint-episode
service feasibility. The full development output contains 1,000 joint programs
and 4,000 paired event outcomes. Event-four mean paired compute-debt increments
are 0.58--1.37 MWh, while p05 residual delivery is 0.9897--1.0000. Joint success
ranges from 0.00 to 0.94. In particular, H=8/gap=24 h fails joint deadline
service in all 100 scenarios even though event-four p05 paired delivery remains
98.97%. Longer wall-clock gaps therefore do not guarantee recovery when the
gap contains insufficient spare compute headroom. This is a fixed-capacity
development mechanism diagnostic, not an exhaustion-capacity certificate.
All numeric outputs are finite, and a checkpoint-only rerun reproduced the five
aggregate artifacts byte-for-byte.

The existing hosting planner now exports both the declared eight portfolios
and unclassified AI–BESS/AI–PV point interactions. One full-horizon development
scenario takes about 42 seconds for all eight solves:

```bash
python -m aidrbench optimize hosting-capacity \
  --scenarios results/nature_mainline/development_v2_nominal/hourly_seed_10000 \
  --portfolio configs/community/pv_bess.yaml \
  --dc-operation matrix \
  --output results/nature_mainline/development_hosting_smoke_seed10000_v2
```

The point interactions must not be labelled complementarity, substitution or
equivalence until scenario-level uncertainty and an equivalence margin are
predeclared.

The ensemble route is preregistered in
`configs/experiment/nature_hosting_ensemble_v1.yaml`. It treats each frozen
scenario as the independent unit, checkpoints one eight-portfolio matrix per
scenario, and can resume without recomputing completed scenarios. Because
scenario schedules are separable conditional on a shared capacity scale, the
minimum of the 100 scenario-specific optima is exactly the simultaneous
ensemble-feasible capacity. The four flexible-minus-rigid gains and four
AI–DER interactions form one family of eight planned contrasts. Their mean
within-scenario effects use 10,000 deterministic bootstrap resamples and
Bonferroni-adjusted simultaneous intervals. The equivalence margin is fixed
before the ensemble run at 5% of the reference-mix operating peak.

```bash
python -m aidrbench optimize hosting-ensemble \
  --scenarios results/nature_mainline/development_v2_nominal \
  --specification configs/experiment/nature_hosting_ensemble_v1.yaml \
  --workers 8 \
  --output results/nature_mainline/development_hosting_ensemble_v1
```

`--workers` only parallelizes independent frozen scenarios. It does not alter
the optimization model, scenario order, statistical unit, or result schema.

The full nominal development run is complete: 100 frozen scenarios produced
800 optimal portfolio rows. Simultaneous ensemble-feasible capacity (rigid →
flexible) is 202.15 → 429.72 kW without PV/BESS, 278.60 → 592.93 kW with BESS
only, 212.44 → 451.60 kW with PV only, and 313.51 → 658.16 kW with both. Across
scenarios, all four paired AI hosting gains have Bonferroni 95% simultaneous
intervals above zero. With the preregistered 10.05 kW equivalence margin, the
AI–BESS interactions are substitution and the AI–PV interactions are
complementarity in both conditioning strata. This is a development-set
planning result and does not open or substitute for locked evaluation.

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

1. Run the fixed H={4,8}, N={0,6}, q=0.95 development diagnostic. Zero notice
   gain remains a valid structural result; do not add mechanisms to force a
   positive result. **Completed on development data.**
2. Freeze Model A after the diagnostic and retain the hash-locked robust-MPC
   route for the later independent operational certificate. **Frozen at
   `d03b440`.**
3. Scale the now-implemented paired repeated-event exhaustion pipeline from
   its three-seed smoke to the declared development/validation ensembles.
   **Completed on 100 nominal development scenarios; validation remains
   pending.**
4. Run the implemented 100-scenario 2 × 2 × 2 hosting ensemble. Its paired
   uncertainty, eight-contrast family and equivalence margin are now
   preregistered. **Completed on 100 nominal development scenarios; locked data
   remain closed.**
5. Run success-criterion and sparse-workload sensitivities, freeze all choices,
   then run validation, locked ID once, and locked OOD separately once.
   **Both development PI sensitivity analyses are complete; validation and
   both locked evaluations remain pending. The validation input set is frozen
   and audited, but causal selection remains deliberately unrun.**

Each locked config is technically guarded. Before its one permitted generation,
the protocol must be committed with `analysis_plan_status: frozen` and
the corresponding `locked_id_status` or `locked_ood_status` set to
`approved_for_one_time_run`. The CLI additionally requires
`--preregistration-manifest`, `--unlock-locked-ood`, and
`--acknowledge-one-time-locked-use`, a clean Git tree, and a new output path.
After success it records the protocol SHA/Git commit and marks the authorization
`consumed`.
