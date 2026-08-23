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

The independently frozen validation exhaustion run is also complete at commit
`097ff89`. It used seeds 20000--20099 and retained the development Model A
commitments of 44.00 kW at H=4 and 41.19 kW at H=8 without validation-set
capacity reselection. All 1,000 checkpoint identities and payload hashes were
verified on replay; the resulting 4,000 event rows and four aggregate tables
contain no non-finite numeric values. Event-four paired compute-debt increments
are 0.55--1.38 MWh while paired residual flexibility remains
0.9910--1.0000. Joint four-event success ranges from 0.00 to 0.97. Only the
H=4, gap=8 h cell reaches an empirical fraction above 0.95, and its one-sided
95% Wilson lower bound is 0.927. Therefore none of these fixed single-event
commitments is reported as a q=0.95 repeated-event capacity certificate.
The validation evidence thus supports the narrower mechanism claim that compute
debt and service risk accumulate before paired instantaneous delivery materially
disappears. Per-cell results, descriptive development--validation concordance
and provenance are retained in
`data/manifests/nature_mainline_validation_exhaustion_results_v1.yaml`.

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

The same frozen 2 × 2 × 2 design was then preregistered and replayed on 100
independent validation scenarios (seeds 20000--20099) without portfolio or
analysis reselection. All 800 optimizations were optimal. The four paired AI
hosting-gain simultaneous intervals again excluded zero, and both AI--BESS
interactions retained the preregistered substitution classification. Both
AI--PV point estimates remained positive; without BESS the interval retained
practical complementarity, whereas with BESS the +8.36 kW estimate and
[1.05, 15.74] kW interval crossed the 10.05 kW practical margin. The latter is
therefore directionally positive but practically indeterminate. This is an
independent replication of a planning bound, not a locked or deployed causal
hosting-capacity certificate. The complete receipt is
`data/manifests/nature_mainline_validation_hosting_results_v1.yaml`.

That fixed-PV/max-DC result is retained as one slice of the joint feasible set,
but it cannot by itself answer the downstream renewable-integration question.
The complementary analysis fixes data-centre scale and either maximizes
curtailment-constrained PV nameplate capacity or evaluates a fixed PV
installation. Its design is frozen in
`data/manifests/nature_renewable_integration_protocol_v1.yaml`:

```bash
python -m aidrbench optimize renewable-integration \
  --scenarios results/nature_mainline/development_v2_nominal \
  --specification configs/experiment/nature_renewable_integration_development_v1.yaml \
  --workers 32 \
  --output results/nature_mainline/renewable_integration_development_v1

python -m aidrbench optimize renewable-integration \
  --scenarios results/nature_mainline/validation_nominal \
  --specification configs/experiment/nature_renewable_integration_validation_v1.yaml \
  --workers 32 \
  --output results/nature_mainline/renewable_integration_validation_v1
```

The headline PV-hosting definition limits curtailment to 5% of available PV
energy; 0%, 10% and 20% are fixed sensitivity levels. The joint envelope uses
0.5×, 1×, 2× and 3× the reference data-centre mix. The orthogonal operating
analysis fixes a 1× data centre and 500 kW PV, then maximizes local PV use,
minimizes grid imports and minimizes battery throughput lexicographically.
Battery charge and discharge are mutually exclusive MILP states, so storage
losses cannot be used as an artificial PV sink. Every output remains a
perfect-information renewable-planning bound, not a causal certificate; no
locked-ID or locked-OOD scenario is read.

Both preregistered ensembles are complete. At 1× reference data-centre scale
and a 5% curtailment ceiling, the independent validation simultaneous PV
capacity increased from 584.69 to 617.52 kW without BESS and from 653.39 to
686.77 kW with BESS. The paired mean workload-flexibility gains were 44.85 kW
(Bonferroni 95% simultaneous CI 41.68--48.08 kW) and 43.20 kW
(39.99--46.46 kW), respectively. At 3× scale both flexible conditions remained
feasible in 100/100 scenarios, whereas rigid operation was feasible in only
31/100 scenarios without BESS and 96/100 with BESS; those partially feasible
cells remain missing simultaneous-boundary values rather than zero-capacity
observations.

At fixed 1× data-centre scale and 500 kW PV, the validation PV-use gain was
18.37 kWh (3.73--40.03 kWh) without BESS and 5.76 kWh
(0.000003--15.86 kWh) with BESS. The corresponding PV-utilisation changes were
0.0720 and 0.0227 percentage points. Thus the direction replicated, but the
operating effect was small and nearly null at the lower simultaneous bound
with BESS. Flexible schedules used the declared 1% deadline-miss budget, and
the analysis did not establish a general PCC-peak reduction; PV use, grid
energy, capacity and service costs therefore remain separate outcomes. The
post-run integrity and hash receipt is
`data/manifests/nature_renewable_integration_results_v1.yaml`.

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

The one-time locked-ID replay was completed on commit `5889405` after frozen
selection at q={0.90,0.95,0.99}. All 500 scenario hashes and 2,000 payload-file
hashes passed audit. At headline q=0.95, the H={2,3,4,6,8} candidates were
certified for N={0,2,6}; the H=1 candidate (55.16 kW) achieved 477/500 successes
but a Wilson lower bound of 0.936 and is therefore not certified. Secondary
q=0.90 and q=0.99 certified 15/18 and 9/18 cells, respectively. These are
interval-wise decisions, not a simultaneous confidence claim for the whole
surface. The machine-readable receipt is
`data/manifests/nature_mainline_locked_id_results_v1.yaml`.

The separately authorized locked-OOD stress test is also complete. Its 500
scenarios changed both the community profile (`eulp_mixed_3c`) and arrival
process (`block`); all 2,000 payload hashes, the seed range, cross-set
non-overlap and no-DR service feasibility passed audit. The fixed q={0.90,
0.95,0.99} validation selections were replayed with the exact controller and
source provenance pinned to commit `5889405`. None of the 54 candidates
retained its target reliability (0/18 cells at each q). At headline q=0.95,
the per-duration success counts were 437, 433, 445, 425, 398 and 383 out of 500
for H={1,2,3,4,6,8}, respectively; delivery failures dominated. This is a
generalization boundary for the fixed Model A candidates, not an estimate that
OOD firm capacity is zero, because no selection or reselection was permitted on
locked OOD. The machine-readable receipt is
`data/manifests/nature_mainline_locked_ood_results_v1.yaml`.

The calibration lower/nominal/upper PI ensembles and the five-point PUE and
node-overhead sparse OAT analysis are complete. The latter ran on clean commit
`f305224` with nominal GPU power and a fixed 144-node facility in every case:

```bash
python -m aidrbench scenario check-infrastructure-sensitivities \
  --specification configs/sensitivity/nature_infrastructure_sparse_v1.yaml \
  --seeds 10000 10001 10002 \
  --output results/nature_mainline/infrastructure_service_gate_v1

python -m aidrbench scenario freeze-infrastructure-sensitivities \
  --specification configs/sensitivity/nature_infrastructure_pi_v1.yaml \
  --output results/nature_mainline/development_infrastructure_scenarios_v1

python -m aidrbench optimize infrastructure-sensitivity \
  --scenarios results/nature_mainline/development_infrastructure_scenarios_v1 \
  --specification configs/sensitivity/nature_infrastructure_pi_v1.yaml \
  --workers 32 \
  --output results/nature_mainline/development_infrastructure_sensitivity_v1
```

The preliminary 15-row gate and all 500 frozen case-scenarios passed no-DR
service checks; all 1,000 H={4,8} PI programs were optimal. PUE=1.10/1.30
scaled both absolute firm capacity and the operating peak by -8.33% and +8.33%,
leaving their ratio invariant. Moving node overhead from 300 W to 150/450 W
left baseline-relative firm kW unchanged but moved the operating peak by
-12.90% and +12.90%. Thus additive node overhead affects normalization and PCC
headroom even though it cancels from this single-event reduction metric. A
second 32-worker replay reproduced all substantive frontier columns exactly
and the firm-boundary artifact byte-for-byte. No locked scenario was read. The
post-run receipt is
`data/manifests/nature_mainline_infrastructure_sensitivity_results_v1.yaml`.

## Completed mainline evidence and remaining packaging work

1. Run the fixed H={4,8}, N={0,6}, q=0.95 development diagnostic. Zero notice
   gain remains a valid structural result; do not add mechanisms to force a
   positive result. **Completed on development data.**
2. Freeze Model A after the diagnostic and retain the hash-locked robust-MPC
   route for the later independent operational certificate. **Frozen at
   `d03b440`.**
3. Scale the now-implemented paired repeated-event exhaustion pipeline from
   its three-seed smoke to the declared development/validation ensembles.
   **Completed on 100 nominal development and 100 independent validation
   scenarios. Validation reused the fixed development Model A commitments
   without capacity reselection; all 1,000 checkpoint hashes and aggregate
   outputs passed replay and finite-value audits.**
4. Run the implemented 100-scenario 2 × 2 × 2 hosting ensemble. Its paired
   uncertainty, eight-contrast family and equivalence margin are now
   preregistered. **Completed on 100 nominal development scenarios and
   preregistered 100-scenario validation replication; locked data remain
   closed. The validation result retains positive AI hosting gain and BESS
   substitution but limits the with-BESS AI--PV interaction to a directionally
   positive, practically indeterminate effect.**
5. Run success-criterion and sparse-workload sensitivities, freeze all choices,
   then run validation, locked ID once, and locked OOD separately once.
   **Both development PI sensitivity analyses, frozen validation selections
   and the separately authorized 500-episode locked-ID and locked-OOD replays
   are complete. Both authorizations are consumed and all pass/fail cells are
   retained without OOD reselection.**
6. Complete infrastructure uncertainty without a Cartesian grid. **The
   five-point PUE/node-overhead OAT design completed on 100 paired development
   seeds; service, hash, solver and replay audits passed. The separate joint
   profile/arrival distribution shift is now bounded by the completed
   locked-OOD stress test.**

All five Results now have the numerical evidence required by the frozen
manuscript structure. Remaining work is source-data export, figure generation,
manuscript drafting and clean-environment verification; it is not an invitation
to add post hoc experiments or reopen locked selections.

Each locked config is technically guarded. Before its one permitted generation,
the protocol must be committed with `analysis_plan_status: frozen` and
the corresponding `locked_id_status` or `locked_ood_status` set to
`approved_for_one_time_run`. The CLI additionally requires
`--preregistration-manifest`, `--unlock-locked-ood`, and
`--acknowledge-one-time-locked-use`, a clean Git tree, and a new output path.
After success it records the protocol SHA/Git commit and marks the authorization
`consumed`.
