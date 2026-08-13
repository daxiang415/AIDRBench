# Hourly validation status

Updated: 2026-08-13. This note follows the root README v0.3 firm-flexibility
protocol. The locked OOD test seeds `30000..30499` have not been evaluated.

> Interface warning (2026-08-13): the current environment interface is
> `firm_v4` with 63 observations and `firm_threshold_v2` costs. Models under
> historical `firm_v1`, `firm_v2`, or 41-dimensional result directories are
> retained only as diagnostics and are incompatible with the current
> environment. The bounded `firm_v4` sanity run documented below was trained
> from scratch on the current interface.

## Current firm_v4 environment status

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

## Next controlled steps

1. Treat the current 10k policies as failed service-feasibility diagnostics,
   not selected models.
2. Define the preregistered reward/constraint sensitivity comparison and
   training budget using validation data only. V3 action projection or
   constrained RL must remain an explicitly labelled extension, not a silent
   change to the V0 action semantics.
3. Use the implemented 5k periodic checkpoints and only validation seeds for
   selection across preregistered RL seeds `101..105`.
4. Freeze controller checkpoints and reward sensitivity choices before the
   first locked OOD benchmark or certificate run.
5. Run the 500-episode locked certificate only after the above freeze.
