# Hourly validation status

Updated: 2026-08-17. This note follows the root README v0.3 firm-flexibility
protocol and its interval-delivery protocol-v2 correction. The locked OOD test
seeds `30000..30499` have not been evaluated.

> Interface warning (2026-08-17): the current environment interface is
> `firm_v5` with PCC-normalized observations and `firm_threshold_v2` costs.
> Models under historical `firm_v1` through `firm_v4`, including the bounded
> `firm_v4` sanity runs documented below, are retained only as diagnostics and
> are incompatible with the current environment.

## Current firm_v5 environment status

The SHA-256-verified `data/calibration/rtx6000pro_4gpu_v1.yaml` artifact now
anchors GPU board power to 4× NVIDIA RTX PRO 6000 Blackwell Max-Q measurements.
Formal configs no longer accept the old `calibration_file` spelling or fallback
GPU parameters. The artifact remains `benchmark_anchored_synthetic`, rather
than fully `measured`, because the server exposes no BMC/PDU/RAPL power channel:
its 300 W node fixed overhead and `[150, 450] W` interval are explicit
assumptions. GPU flexibility conclusions may use the measured terms, while
wall-power and absolute hosting claims must retain this limitation.

- Current-hour released work enters both controlled and no-control queues
  before the observation is constructed.
- DR request and headroom use the flexible DC power range, rather than the much
  larger community peak, as their normalization scale.
- Deadline features are cumulative work due by each horizon divided by the
  capacity available before that horizon; the physical feasibility boundary is
  one.
- Recovery activity, remaining recovery time, event request, controlled and
  baseline backlog, running window peaks, relief, and rebound are observable.
- A proportional 2-node/1000 kW versus 4-node/2000 kW test produces identical
  63-dimensional trajectories and rewards for identical normalized actions.
- The scalar reward is an adapter over separately reported delivery,
  feasibility, deadline, rebound, window-relief, and terminal-backlog
  violations. Formal reward thresholds are checked against the locked
  certification criteria by `protocol-check`.
- PI, non-anticipative and hosting-capacity planning now retain workload class
  and use `fixed + sum(class_power × class_execution)` consistently with the
  online physical environment.
- Capacity certification fixes duration, notice and a repeated-event program;
  one episode is one Bernoulli trial and succeeds only if all of its events do.
  Isolated-event tables below are historical diagnostics, not the primary
  certificate definition.
- Local CI equivalence currently passes 173 tests, `ruff check .`, `mypy src`,
  and a HiGHS/CVXPY/Parquet clean-install smoke test. GitHub Actions is now
  configured to run the same gates remotely.

The rule-controller smoke output for the current interface is under
`results/smoke/firm_v4_reward_v2_rules_seed20000/`. It is a semantic check of
the cost decomposition, not a controller ranking. The intermediate
`firm_v2_reward_v1_*` and `firm_v3_reward_v2_*` smoke files predate the final
deadline-horizon semantics, so they are also historical diagnostics.

## Current firm_v4 bounded learning sanity check

DQN, PPO, and SAC were trained from scratch for approximately 10k environment
steps with training seed 101. The checkpoints live in the originally named
`results/smoke/firm_v4_reward_v2_rl_3k/` directories; each `training.json`
records the unambiguous cumulative step count (10,000 for DQN/SAC and 10,752
for PPO). This was a bounded interface diagnostic, not formal model selection.

The table reports means over validation seeds `20000..20002` (nine event
decisions per controller). No locked test seed was used.

| Controller | Mean delivery ratio | Mean deadline miss | Mean terminal excess | Joint successes |
| --- | ---: | ---: | ---: | ---: |
| DQN | 1.000 | 31.51% | 2.50% | 0 / 9 |
| PPO | 1.000 | 77.89% | 2.93% | 0 / 9 |
| SAC | 1.000 | 40.29% | 0.14% | 0 / 9 |

All three policies learned to curtail during events, but did so by deferring
too much work. This is evidence that the normalized observation and scalar
cost path are numerically usable; it is not evidence that any current RL policy
is service-feasible. Increasing the training budget or changing reward weights
without a preregistered validation comparison is not justified by this smoke
run.

Matched outputs, including separate cost trajectories and representative-week
figures, are under
`results/validation/firm_v4_reward_v2_10k_seed101/validation_seeds_20000_20002/`.

## Experimental firm_cmdp_v1 reward diagnostic

An experimental training-only primal-dual reward adapter was then evaluated
with the same seed 101, approximately 10k environment steps, and validation
seeds `20000..20002`. It preserves the `firm_v4` physical environment and the
`firm_threshold_v2` evaluator. The adapter rewards completed useful compute,
adds potential-based backlog/feasibility shaping, and maintains six separate
episode-updated constraint multipliers. It is not a replacement for the locked
firm-flexibility success criterion.

| Controller | Threshold-v2 deadline miss | CMDP-v1 deadline miss | CMDP-v1 terminal excess | CMDP-v1 joint successes |
| --- | ---: | ---: | ---: | ---: |
| DQN | 31.51% | 0.00% | 0.00% | 1 / 9 |
| PPO | 77.89% | 17.62% | 0.00% | 0 / 9 |
| SAC | 40.29% | 4.26% | 2.81% | 0 / 9 |

The useful-compute objective materially reduced the stop-work pathology. DQN
completed the same flexible work as no-control and eliminated deadline and
terminal-backlog violations. Its remaining eight event failures are caused by
rebound and/or sustained window-relief constraints. PPO still learned to stop
during events, while SAC retained small service violations. Therefore this is
evidence that the reward direction is better, not evidence that any policy is
certified or that more steps alone will solve the remaining constraint
coupling.

The 10k outputs are under
`results/validation/firm_cmdp_v1_10k_seed101/validation_seeds_20000_20002/`.
The 5k checkpoint comparison is under
`results/validation/firm_cmdp_v1_5k_seed101/validation_seeds_20000_20002/`;
it shows improving service metrics for PPO/SAC but no improvement in joint
success, so checkpoint selection must continue to use the independent joint
criterion.

### Recovery-window temporal-credit correction

The remaining DQN failures were consistent with a temporal-credit problem
rather than service infeasibility. In v1, rebound and window-relief costs
settle only at the end of a 12-hour recovery window. V2 added running-cost
potential shaping. V3 tested finite-horizon discount compensation, but did not
improve the joint criterion. V4 instead decomposes each running recovery
violation into signed hourly increments. For the protocol's non-overlapping windows,
the increments sum exactly to the settled physical cost before safety
clipping, while the dual update still uses only the settled evaluator cost.

All rows below use the same DQN implementation, training seed 101, 10k steps,
and validation seeds `20000..20002` (nine event decisions). They are reward
diagnostics, not model selection.

| Training reward | Joint successes | Rebound failures | Window failures | Deadline miss | Terminal excess |
| --- | ---: | ---: | ---: | ---: | ---: |
| `firm_cmdp_v1` | 1 / 9 | 6 / 9 | 4 / 9 | 0.00% | 0.00% |
| `firm_cmdp_v2` | 1 / 9 | 5 / 9 | 4 / 9 | 0.00% | 0.00% |
| `firm_cmdp_v3` | 1 / 9 | 5 / 9 | 5 / 9 | 0.00% | 0.00% |
| `firm_cmdp_v4` | 7 / 9 | 2 / 9 | 0 / 9 | 0.00% | 0.00% |

V4 also completes all `27474.72` flexible GPU-hours, matching no-control. Its
two failures are rebound ratios `0.3078` and `0.3104`, just above the frozen
`0.25` limit. This bounded result supports v4's temporal attribution, but one
training seed and three validation episodes are insufficient to change the
95% certification claim or justify locked-test use. The matched v4 output is
under
`results/validation/firm_cmdp_v4_10k_seed101/validation_seeds_20000_20002/`.

Protocol-v2 re-evaluation leaves this DQN result at `7/9`: its minimum hourly
delivery ratio is `1.0` in all three episodes, and the same two rebound
failures remain. The corrected output is under
`results/validation/firm_cmdp_v4_10k_seed101_interval_protocol_v2/validation_seeds_20000_20002/`.

### Continuous-action diagnostic

The environment already supports the continuous action $a_t\in[0,1]$. A
bounded SAC diagnostic used `firm_cmdp_v4`, training seed 101, 10k steps, and
the same validation seeds `20000..20002`. It delivered every DR request and
had no rebound failures, but over-curtailed instead of exploiting the finer
action resolution: mean peak reduction was `62.84 kW` for a mean requested
`10.85 kW`. It completed `25294.87` flexible GPU-hours, incurred a `4.85%`
deadline-miss rate and `3.08%` terminal excess, and achieved `0/9` joint
successes. The matched output is under
`results/validation/firm_cmdp_v4_sac_10k_seed101/validation_seeds_20000_20002/`.

This does not establish that continuous actions are intrinsically worse,
because SAC-versus-DQN also changes the learning algorithm. It does establish
that action resolution alone does not solve the control problem, so the
continuous policy is not the current default. A causal action-space ablation
would train the same PPO implementation on matched discrete and continuous
environments with identical seeds and budgets.

The SAC run was subsequently resumed with its replay buffer to a cumulative
100k steps, without changing the environment, reward configuration, or seed.
The same three validation episodes show non-monotonic degradation rather than
sample-limited convergence:

| SAC steps | Joint successes | Deadline miss | Terminal excess | Completed GPU-h |
| ---: | ---: | ---: | ---: | ---: |
| 10k | 0 / 9 | 4.85% | 3.08% | 25294.87 |
| 25k | 0 / 9 | 13.37% | 0.00% | 23800.80 |
| 50k | 0 / 9 | 10.17% | 0.00% | 24679.48 |
| 75k | 0 / 9 | 15.66% | 0.00% | 23172.06 |
| 100k | 0 / 9 | 38.65% | 3.17% | 15985.59 |

At 100k the mean continuous action fell to `0.56` even outside event and
recovery windows, while the deadline multiplier reached its configured maximum
of `20`. The current episode-level dual ascent therefore changes the SAC
objective faster than the policy stabilizes; more steps alone amplify the
failure. The 100k model is retained as a rejected diagnostic under
`results/smoke/firm_cmdp_v4_100k/sac_seed101/`, with matched validation output
under
`results/validation/firm_cmdp_v4_sac_100k_seed101/validation_seeds_20000_20002/`.

## Perfect-future firm-flexibility upper bound

The implemented full-horizon oracle uses exact time-expanded fluid-work
flows, the full future episode, and a mixed-integer representation of the
evaluator's event peak-delivery denominator. The firm reduction `R` is a
continuous decision variable maximized directly by HiGHS; it is not the top of
the `certify` grid. The model additionally caps `R` at the calibrated flexible
dynamic-power range, so a result equal to `68.86 kW` identifies that explicit
physical-model bound.

For this configuration, the old `certify` ceiling of `0.5 × DC peak` was
`76.69 kW`, already above both the old and corrected oracle results. Therefore
`67.05 kW` was not produced by that grid ceiling. The CLI default is
nevertheless changed to binary search over `[0.0, 1.0] × DC peak` so future
certificate reports cannot leave this ambiguity.

Protocol v2 closes an ambiguity in the original evaluator. It retains mean
event delivery of at least 95% and now also requires every hourly settlement
interval to deliver at least 95%. The old v4 oracle result used only mean
delivery and must not be used for an interval-settled capacity claim.

The bounded validation calculation below uses only seeds `20000..20002`; no
locked test seed was touched. This validation configuration auto-scales the
four-GPU calibration to 85 virtual nodes (340 GPUs), of which 170 GPUs are in
the flexible pool. Its modeled DC power is `84.51 kW` fixed plus at most
`68.86 kW` flexible dynamic power (`153.37 kW` total peak).

All events in the original three validation episodes happened to have a
two-hour duration. With three events per episode and the new interval
constraint, the results are:

| Episode seed | Continuous oracle bound | Fraction of flexible dynamic power | Min hourly delivery | Deadline miss |
| ---: | ---: | ---: | ---: | ---: |
| 20000 | 68.86 kW | 100.00% | 95.0001% | 0.0000% |
| 20001 | 68.86 kW | 100.00% | 95.0001% | 0.0000% |
| 20002 | 63.52 kW | 92.25% | 95.0001% | 0.0000% |
| Mean | 67.08 kW | 97.42% | 95.0001% | 0.0000% |

Therefore `63.52 kW`, not the earlier `67.05 kW`, is the largest common value
across this three-episode diagnostic. The earlier value exploited event-average
settlement and is retained only as a historical result. The corrected matched
output is under
`results/validation/full_horizon_oracle_interval_bound_v5/validation_seeds_20000_20002/`.

An isolated-event duration diagnostic (one event at hour 17) gives the
following per-episode continuous optima:

| Duration | Seed 20000 | Seed 20001 | Seed 20002 | Minimum over these seeds |
| ---: | ---: | ---: | ---: | ---: |
| 1 h | 68.86 kW | 68.86 kW | 68.86 kW | 68.86 kW |
| 2 h | 68.86 kW | 68.86 kW | 68.86 kW | 68.86 kW |
| 3 h | 68.86 kW | 68.86 kW | 68.86 kW | 68.86 kW |
| 4 h | 68.86 kW | 68.86 kW | 63.52 kW | 63.52 kW |

This small validation slice shows no duration limitation through three hours;
those entries equal the separately declared power-model cap, not a search-grid
boundary. The four-hour seed-20002 result is workload/service constrained.
Three seeds are insufficient for a `F_0.95(H)` certificate. The raw diagnostic
table is
`results/validation/full_horizon_oracle_interval_bound_v5/duration_curve_validation_seeds_20000_20002.csv`.

These are global optima only for the declared perfect-future, affine-power,
preemptible-fluid model. Integer GPU placement, gang scheduling,
non-preemption, checkpoint overhead, network contention, forecast error, and
hardware-model uncertainty can reduce deployable capacity. The oracle must not
be included as a fair competitor in online-controller rankings.

## Implemented validation safeguards

- Training, validation, and locked-test community profiles and episode-seed
  ranges are disjoint and checked by `aidrbench protocol-check`.
- Formal arrivals are independently regenerated from the stratified
  Alibaba-2026 sampler for each episode seed.
- DQN/SAC continuation saves and reloads `replay_buffer.pkl`; continuation is
  rejected when that file is absent.
- Training metadata records requested, actual segment, and cumulative steps.
- Benchmark output distinguishes hourly PCC-limit compliance from the joint
  firm-event decision and reports per-criterion failure counts.
- Episode-level rebound is the maximum of the correctly paired per-event
  rebound ratios. It is no longer divided by an unrelated episode-wide load
  reduction.

## Historical firm_v1 reward-v2 diagnostic

The first 10k experiment exposed a scale error: dividing a roughly 9 kW DR
shortfall by a 1000 kW community peak before squaring made no-control slightly
better than a responding threshold controller. Those models under
`results/validation/training_10k_v1/` are diagnostic artifacts and are not
valid candidates.

The corrected training reward uses requested-reduction tracking error, excess
backlog relative to the no-control queue, and requested-reduction-normalized
rebound. On validation seed 20000 this changed the no-control return to
`-120.00` and the responding threshold return to `-23.26`, so learning and the
intended DR objective now point in the same direction. Firm certification
remains an independent evaluator and is never replaced by reward.

## Historical firm_v1 seed-101 checkpoint selection

All numbers below use only validation seeds `20000..20009`. There are three DR
events per episode, or 30 event decisions in total.

| DQN checkpoint | Joint successes | Mean deadline miss | Mean terminal excess | Decision |
| --- | ---: | ---: | ---: | --- |
| 25k | 13 / 30 | 0.54% | 0.04% | formerly selected; now incompatible |
| 50k | 7 / 30 | 0.96% | 0.00% | rejected due to validation regression |

The formerly selected 25k checkpoint is
`results/smoke/reward_v2_3k/dqn_seed101/model.zip`; its paired replay buffer is
in the same directory. The rejected 50k checkpoint is retained under
`results/validation/reward_v2_50k_seed101/` as evidence of training drift.

This was checkpoint selection, not a paper result. It used one RL training seed,
only ten validation episodes, and does not reach the frozen 95% reliability
target. The main observed DQN failures are window-wide relief and rebound, with
some deadline failures.

## Calibrated firm_v5 reward diagnostics

The nominal calibration case was used to freeze all 100 validation seeds
`20000..20099`. The resulting virtual facility has 182 four-GPU nodes, a
200.321 kW modeled DC peak, and scenario artifacts bound to calibration SHA
`6f6c5aa776c90be6f8d1f1d41ee2457b321558257aed363ebe2cbd063433c996`.
No locked OOD seed was read.

Five DQN policies were first trained for 50k steps with the environment's
penalty-only `firm_threshold_v2` scalar reward. Every final model produced
`0/100` repeated-event joint successes. A sweep over all 50 periodic
checkpoints (5k through 50k for seeds 101 through 105) also produced zero event
successes on validation seeds `20000..20009`: delivery was usually met, but
every event failed the deadline criterion. No-control has zero deadline and
terminal-backlog failures on all 100 validation episodes, so this is a reward
and learned-policy failure rather than an infeasible workload distribution.

The training-only CMDP adapter retains the same physical environment and
independent certificate evaluator. Its bounded seed-101 comparison is:

| Training reward | Steps | Validation episodes | Joint successes | Successful events | Main failures |
| --- | ---: | ---: | ---: | ---: | --- |
| `firm_cmdp_v4` | 10k | 10 | 2 / 10 | 13 / 30 | rebound, window relief |
| `firm_cmdp_v4` | 20k | 10 | 2 / 10 | 12 / 30 | rebound, window relief |
| `firm_cmdp_v4` | 30k | 10 | 1 / 10 | 8 / 30 | rebound, window relief |
| `firm_cmdp_v5` | 10k | 10 | 7 / 10 | 26 / 30 | rebound |
| `firm_cmdp_v5` | 20k | 10 | 4 / 10 | 20 / 30 | rebound, window relief |
| `firm_cmdp_v5` | 10k | 100 | 31 / 100 | 197 / 300 | rebound, delivery, window relief |

`firm_cmdp_v5` differs only in its training signal: recovery-window rebound and
window-relief violations are charged at every violating hour instead of only
through their settled or incremental cost. On the full validation set it has
zero deadline and terminal-backlog failures, but 83 rebound, 20 delivery, and
17 window-relief event failures. Its one-sided 95% lower confidence bound for
joint success is 23.4%, so it is a useful diagnostic improvement, not a formal
reward or certificate candidate.

Matched ten-episode controller diagnostics reinforce the separation between
environment feasibility and controller quality. No-control, threshold,
EDF/valley, deterministic MPC, and robust MPC all have `0/10` joint successes
for different reasons. The full-horizon oracle meets every delivery, deadline,
window-relief, and terminal criterion, but its aggregate replay has 16 rebound
failures and only `1/10` joint successes. This replay gap is expected because
the optimization bound controls class-indexed execution while the online
environment exposes one aggregate execution fraction; the oracle remains a
planning upper bound, not a deployable controller.

## Next controlled steps

1. Treat `firm_cmdp_v5` as a diagnostic, not a selected reward. Preserve its
   service-safe useful-compute objective, but add a preregistered recovery
   safety margin or an explicitly labelled safety layer before more long runs.
2. Validate the revised candidate on all 100 validation episodes; do not use a
   ten-episode slice as evidence for 95% reliability.
3. Only after the reward and controller semantics are frozen, train seeds
   `101..105` and select among their 5k periodic checkpoints using validation
   data alone.
4. Keep any action projection or class-specific actuator as an explicitly
   labelled extension, because it changes the online controller's authority.
5. Freeze controller checkpoints, capacity, and reward sensitivity choices
   before the first 500-episode locked OOD certificate run.
