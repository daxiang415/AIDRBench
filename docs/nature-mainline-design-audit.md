# Nature mainline design audit

Date: 2026-08-18

Scope: bounded, single-context design and statistics review of the active README,
protocol, calibration artifact, scenario generator, PI/NA optimizers, causal
controller interface, and locked evaluation route. This is not a mutually blind
multi-review and it is not a journal acceptance prediction.

## Evidence-chain matrix

| Claim | Estimand / output | Data source | Statistical unit | Selection set | Independent evidence |
|---|---|---|---|---|---|
| Static flexible fractions overstate task-feasible flexibility | nominal minus PI capacity | Alibaba-2026-trace-calibrated synthetic jobs; calibrated power model | frozen episode | development | locked-ID PI tolerance bound |
| Duration, notice and reliability shape usable capacity | H × N × q surface | random peak-window DR anchor, EULP-modeled community profile, synthetic deadline policy | one single-event episode | development / validation | locked-ID causal certificate |
| Non-anticipativity creates an information loss | matched empirical PI order statistic minus restricted scenario NA | same frozen ensemble and allowed-failure count | independent frozen episode inside one ensemble optimization point | development / validation | descriptive same-ensemble gap; no confidence-bound or certificate claim |
| A causal scheduler can deliver a committed capacity | robust-MPC fixed candidate | released jobs, queue state, short community forecast, announced DR request | one locked-ID episode | candidate selected on validation | one-sided Wilson lower bound on 500 disjoint locked-ID episodes |
| Repeated dispatch exhausts flexibility | residual capacity, compute debt and rebound versus event index/gap | separate repeated-event scenarios | joint multi-event episode | development / validation | locked-ID exhaustion set to be added before formal run |
| Flexibility raises community hosting capacity | maximum DC capacity under PCC/PV/BESS constraints | EULP-modeled community profiles plus class-aware DC power | frozen episode / declared portfolio | development | held temporal/profile sensitivities; currently pending |
| Results generalize to other GPUs | power-and-throughput-normalized sensitivity | measured RTX PRO 6000 power plus declared external hardware assumptions | independent hardware run for measurement | calibration fit / held-out | not yet supported for H100/H200 compute throughput |

## Resolved design blockers

1. Calibration no longer treats the four GPUs in one workload run as four
   independent repeats. Active-power intervals use two independent run means;
   the third run is held out. Idle and node-overhead ranges are explicitly
   labelled as within-run device range and engineering assumption range.
2. The primary event no longer occurs at a deterministic midnight hour. One
   event is sampled from predeclared 15:00–20:00 candidates on episode days
   3–6 using the independent event random stream.
3. Future DR limits are masked from the ordinary six-hour controller forecast
   until the event's declared notice window opens.
4. The main reliability test is `locked_id` with the same reference profile and
   arrival process; `locked_ood` separately changes climate profile and burst
   process and is interpreted only as extrapolation.
5. The README and protocol now distinguish nominal, PI, restricted NA, and an
   independently tested causal capacity. The causal route uses one frozen
   robust-MPC reference, not RL or a controller leaderboard.
6. The restricted-NA solver now uses a direct sparse cumulative-state model and
   reuses immutable scenario snapshots. The complete 100-scenario nominal
   duration × notice development grid is solved and hash-merged from three
   independently written notice partitions.

## Remaining blockers before formal locked runs

- Corrected matched development scenarios and PI frontiers are complete for all
  three calibration power cases. Pre-audit `development_*` artifacts remain
  historical and cannot be reused as formal evidence.
- The complete nominal NA development grid has a zero same-ensemble empirical
  information gap and no notice effect. This is not a confidence-bound result.
  Before claiming a notice mechanism, add preregistered tighter-deadline,
  higher-utilization, checkpoint/gang or non-preemptive sensitivities; do not
  hide the nominal null result.
- Run success-criterion sensitivities. The 0.95 delivery, 0.25 rebound, 0.50
  window-relief, 0.01 miss, and 0.02 terminal-backlog values are operational
  definitions, not fitted reward weights; all headline surfaces need the
  predeclared threshold sensitivity table.
- Expand community sensitivities beyond the mixed profile before claiming
  generality across residential/commercial community types.
- Add compute-throughput conversion by workload class before interpreting
  H100/H200 power profiles as equivalent compute capacity. Current external GPU
  profiles remain assumption-based sensitivity cases.
- Quantify the fluid scheduling approximation with gang/non-preemptive and
  checkpoint-overhead sensitivities.
- Add confidence intervals or resampling uncertainty for PV/BESS interaction
  terms and predeclare an equivalence margin for “approximately zero”.

## Run gate

Formal locked data stay closed until the analysis plan is frozen, code and data
hashes are committed, all validation selections are complete, and the relevant
one-time status is explicitly changed from `not_run` to
`approved_for_one_time_run`. Development runs may resume after corrected
scenarios are regenerated.
