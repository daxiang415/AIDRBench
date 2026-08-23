<!--
Working Supplementary Information, version 0.1.
Methods and principal result-detail sections are drafted; figures and release metadata retain explicit completion markers.
All terminology follows manuscript/terminology-ledger.md.
-->

# Supplementary Information

## Job-derived firm demand response expands community photovoltaic hosting and utilisation

[AUTHOR NAMES]

## Contents

1. Supplementary Methods
   - Hardware measurement and power-model calibration
   - Scaling from the four-GPU measurement node to Model A
   - AIDRBench environment and frozen scenario construction
   - Workload, action and observation interfaces
   - Hourly state transition, baseline counterfactual and metrics
   - Reward boundary and reproducibility controls
2. Supplementary Results
   - Calibration uncertainty and topology interpretation
   - Environment validation contracts
   - Capacity-layer and notice diagnostics
   - Repeated-event exhaustion
   - Renewable-integration and sensitivity analyses
3. Supplementary Figures
4. Supplementary Tables

## Supplementary Methods

### Hardware measurement and power-model calibration

The hardware measurements were designed to anchor class-specific GPU-board power in the hourly model, rather than to characterise thermal control or dynamic voltage and frequency scaling. The measurement node contained four NVIDIA RTX PRO 6000 Blackwell Max-Q Workstation Edition GPUs, each reporting a 300-W power limit. `nvidia-smi topo` reported PCIe `NODE` paths among the GPUs and no NVLink connection. No clocks or power limits were changed.

Training measurements used BF16 8192 × 8192 forward and backward matrix operations. The four-GPU training condition additionally applied a NCCL gradient all-reduce, thereby including the synchronisation and PCIe communication behaviour of a multi-GPU training step. Offline inference used BF16 8192 × 8192 batched forward operations without inter-GPU communication. Each workload was run in one- and four-GPU conditions with three repeats. A 5-s warm-up preceded a 20-s measurement window, during which read-only GPU-board power and utilisation were sampled from `nvidia-smi` at 1-s resolution.

Repeats 1 and 2 were used for calibration and repeat 3 was held out. For a four-GPU repeat, the board-power readings were first averaged within each GPU over time and then averaged across the four GPUs to form one independent run mean. The four GPUs within a synchronised run were not treated as four independent replicates. The two calibration run means were used to estimate each class-specific active-power mean and its Student t 95% confidence interval. The held-out repeat was used only to calculate prediction error.

The calibration artifact recorded an idle estimate of 13.94 W per GPU. Because idle power was measured in one node-level run, its 6.74–18.68 W interval is the range across GPUs within that run, not an inferential confidence interval. Four-GPU active-power estimates were 259.08 W per GPU for training (95% t interval, 225.81–292.35 W) and 300.02 W per GPU for offline inference (299.69–300.35 W). The combined held-out active-power mean absolute error was 3.80 W per GPU; class-specific errors were 7.56 W for training and 0.03 W for offline inference.

The node exposed no accessible baseboard-management-controller or data-centre-management-interface power channel, and CPU package telemetry required privileged model-specific-register access that was unavailable. CPU, memory, fan and conversion losses were therefore not measured at the wall. The node fixed-overhead term was explicitly set to 300 W per node and varied from 150 to 450 W in sensitivity analysis. For this reason, the artifact evidence class is `benchmark_anchored_synthetic`, not `measured`. The public artifact contains raw-input SHA-256 values, fitted parameters, uncertainty definitions and the held-out error, and has SHA-256 `ef1e474a95b7139f6fd25b4deb733a81dfa0616c8245e101fcc62f437ffc5193`.

### Scaling from the four-GPU measurement node to Model A

The formal Model A configuration contained 144 four-GPU nodes (576 GPUs), a 1,000-kW community PCC limit and an 800-kW normalised community background peak. The reference workload mix produced a data-centre operating peak of 201.00 kW. This configuration was a controlled normalisation for comparing job-feasible and nominal flexibility; it was not intended to represent the nameplate design of a particular commercial data centre.

The power model preserved workload class. For hour t,

\[
P^{\mathrm{DC}}_t=P_{\mathrm{fixed}}+\sum_c e_cX_{c,t},
\]

where \(X_{c,t}\) was executed GPU-hours of class c and \(e_c\) was its incremental energy coefficient derived from active minus idle board power and the declared power-usage effectiveness (PUE). The nominal configuration used PUE = 1.20. The fixed component included idle GPU power and the assumed node overhead. Hardware lower, nominal and upper cases substituted the corresponding calibration intervals without changing the number of nodes, so the sensitivity isolated power-model uncertainty rather than silently resizing the fleet.

This scaling assumes that a node with the same four-GPU topology retains the measured class-specific board-power response and that aggregate facility power is the sum of node contributions multiplied by PUE. It does not claim identical throughput, communication efficiency or utilisation for H100, H200 or another GPU generation. No cross-generation capacity extrapolation is included in the study.

### AIDRBench environment and frozen scenario construction

AIDRBench converted exogenous community, workload and demand-response inputs into auditable hourly state transitions, power trajectories and service outcomes. The environment served three purposes. First, the causal controller and offline planning programmes used the same workload-conservation, deadline and class-aware power definitions. Second, frozen scenarios ensured that alternative schedules were evaluated against identical community demand, job arrivals and event timing. Third, step-, event- and episode-level outputs exposed delivery, deadline, backlog, rebound and compute-debt metrics without relying on a training reward.

Each Model A episode contained a 7-day main horizon followed by a 48-h clearance tail. New jobs arrived only during the main horizon; the tail allowed deferred work, rebound and terminal backlog to be evaluated. The environment used a fixed 1-h time step and rejected non-hourly configurations because deadline buckets age by one bucket per step. A 6-h environment forecast was available to the frozen causal controller under the declared information structure.

Community demand came from the selected NLR/NREL End-Use Load Profile and retained its temporal shape after normalisation. Model A used the `eulp_mixed_3a` profile for development, validation and locked-ID evaluation. Locked-OOD evaluation changed the community profile to `eulp_mixed_3c` and simultaneously changed the workload-arrival process from a non-homogeneous Poisson process to a block process. The locked-OOD set replayed validation-selected candidates and was not used to estimate new capacities.

Job arrivals were independently resampled for each episode from an Alibaba GPU 2026 summary-calibrated sampler. The resulting arrival process was synthetic and distribution-calibrated; it was not a literal replay of the original cluster timeline. Model A used a target total utilisation of 0.65, equal training and offline-inference class shares, and class flexible fractions of 1.00 and 0.50, respectively. The declared flexible GPU pool fraction was 0.60. Training deadline slack ranged from 2× to 6× runtime, bounded to 6–48 h, while offline-inference slack ranged from 1.5× to 4× runtime, bounded to 2–24 h. These deadlines were generated by policy because the source summary did not contain production deadlines.

Single demand-response events were sampled from 24 declared start-hour candidates corresponding to 15:00–20:00 windows on episode days 3–6. Event duration and notice were replay overrides over H = {1, 2, 3, 4, 6, 8} h and N = {0, 2, 6} h. Community, workload and event randomness used independent child streams derived from the episode seed. The frozen scenario payload stored all exogenous inputs plus their hashes and rejected replay under an incompatible time horizon, forecast horizon, PCC capacity or power-model fingerprint.

### Workload and action interfaces

Released jobs entered class-aware, earliest-deadline-first fluid queues. Each queue retained GPU-hour work in the deadline buckets {0, 1, 2, 3, 6, 12, 24, 48} h. Work could not execute before release, cumulative execution could not exceed cumulative arrival, and expired unfinished work was recorded as deadline miss. The baseline and controlled queues received the same arrivals.

The online environment exposed an aggregate execution action \(u_t\in[0,1]\), interpreted as the fraction of flexible GPU-hour capacity executed in hour t. A five-level discrete adapter {0, 0.25, 0.50, 0.75, 1.00} remained available for controller-development experiments, but the Nature mainline used the continuous interface. The queue allocated the selected aggregate work across classes by earliest deadline, retaining class identity for the power calculation.

Offline PI, restricted NA and renewable-integration programmes did not optimise this aggregate action. They used class-aware execution variables \(x_{c,t}\) with cumulative release and deadline constraints. Equivalence diagnostics showed that the compact cumulative PI formulation matched the earlier job-edge formulation at all 18 tested points. BESS charging and discharging were decision variables only in the renewable-integration planner; the online Gymnasium action did not control the battery.

### Normalised policy observation

The `firm_v5` policy observation was a stable 63-dimensional `float32` vector. Feature names and bounds were generated by the environment and checked against a Gymnasium `Box` space after every construction. Power variables were divided by PCC capacity or the flexible-power range, backlog variables by flexible GPU capacity multiplied by the 48-h deadline horizon, and temporal variables by their declared duration. Values were clipped only to declared feature-specific bounds; a value outside the observation space raised a runtime error.

| Observation group | Dimensions | Normalisation and information content |
|---|---:|---|
| Hour and weekday | 4 | sine–cosine encodings |
| Current community, PV, PCC, fixed DC, available flexible power and event request | 6 | PCC capacity or flexible-power range |
| Controlled/baseline backlog, excess backlog, arrivals, miss, terminal excess and slack | 9 | capacity×deadline horizon, cumulative arrivals or maximum deadline |
| Controlled deadline feasibility | 8 | cumulative due work divided by available GPU-hour capacity before each deadline bucket |
| Excess deadline feasibility | 8 | positive controlled-minus-baseline feasibility excess |
| Event, notice, recovery and event history | 10 | declared event/recovery scales and 24-h history |
| Running peak, relief, rebound, previous action and previous PCC | 6 | PCC, request and action scales |
| Future community forecast | 6 | PCC capacity |
| Future available-flexibility forecast | 6 | flexible-power range with notice masking |
| **Total** | **63** | fixed ordering, bounds checked each step |

Explicit `compute_debt_kwh` was included in the auditable control state and `info` outputs, but it was not a separately named element of the 63-dimensional policy vector. The observation represented related state through controlled and excess backlog, deadline-feasibility ratios and slack. This distinction prevents the scientific compute-debt diagnostic from being misdescribed as a privileged controller input.

### Hourly state transition, baseline counterfactual and metrics

Each hourly transition followed a fixed order: (1) arrivals for the current hour were added to controlled and baseline queues before the action; (2) the controller or planner selected executable GPU-hours; (3) controlled work was allocated by earliest deadline; (4) unserved work due in the current bucket was counted as a deadline miss; (5) remaining buckets aged by one hour; (6) class-specific execution was converted to data-centre power and energy; (7) community, PV and data-centre power were combined into PCC power; and (8) delivery, rebound, peak, backlog, slack, compute-debt and event-history variables were updated for the next observation.

The no-DR baseline was a full-service causal counterfactual driven by the same arrivals and exogenous community trajectory. Event delivery was calculated from controlled minus baseline PCC power. Mean delivery and minimum interval delivery were recorded separately. The firm-success criterion required both mean delivery of at least 0.95 and at least 0.95 of the request in every event hour, in addition to deadline-miss, rebound, recovery-window peak-relief and terminal-backlog criteria.

Compute debt was the additional dynamic energy obligation associated with controlled backlog relative to the matched baseline. It excluded idle-pool energy by applying class-specific active-minus-idle power and PUE to the excess class backlog. Repeated-event outcomes additionally compared each event with a same-scenario, same-clock-time fresh-event counterfactual, so residual delivery was not confounded by moving the event to a different community or arrival condition.

### Reward boundary and reproducibility controls

The environment retained the `firm_threshold_v2` scalar reward for future online-control studies. It combined threshold-normalised penalties for delivery, deadline feasibility, deadline miss, rebound, recovery-window relief, terminal backlog, excess backlog and action switching. None of the main PI, restricted NA, repeated-event or renewable-planning results was defined by this reward. The robust model-predictive controller used in causal certification was not trained on it, and DQN, PPO and SAC results were excluded from the manuscript.

Formal scenarios, controller selection and evaluation were fail closed. The environment configuration required the calibration artifact and all workload-class power parameters. Frozen scenarios stored independent random-stream seeds, source and payload hashes, the observation version and the power-model fingerprint. Causal selection additionally stored the complete normalised robust-controller specification, raw YAML hash, Git commit and relevant source hashes. Locked replay stopped if any recorded item differed. Checkpointed ensemble programmes reloaded completed scenario outputs and regenerated byte-identical aggregate results.

## Supplementary Results

### Calibration uncertainty and topology interpretation

Single-GPU training remained near the 300-W board limit, whereas four-GPU training averaged 259.08 W per GPU. Offline inference remained near 300 W in both one- and four-GPU conditions. The training difference is consistent with the synchronised workload spending part of each step in PCIe/NCCL communication, but the calibration experiment was not designed to isolate communication energy from kernel occupancy. The measured value was therefore used as a topology-specific power anchor rather than as a general performance or scaling law.

The training confidence interval was wide because it was based on two independent fit runs, and the node-overhead range was an assumption rather than a measurement. The main PI sensitivity consequently substituted lower, nominal and upper active-power cases while leaving node count fixed. Absolute firm capacity changed with the dynamic power slope, whereas fixed node overhead changed the operating peak but cancelled from baseline-relative single-event reduction in kW. These sensitivities bound the declared Model A power representation; they do not support extrapolation to another GPU family.

### Environment validation contracts

Environment verification was organised around physical and information contracts rather than controller reward. Existing automated tests covered the following categories.

| Contract | Verified behaviour |
|---|---|
| Gymnasium interface | continuous and discrete actions; 63-dimensional observation within declared bounds |
| Work conservation | arrivals, execution, misses and terminal backlog reconcile |
| Deadline transition | arrivals precede actions; earliest-deadline-first execution; one-hour bucket ageing |
| Class-aware power | execution class changes dynamic power and compute-debt accounting |
| PCC identity | community net load plus data-centre power matches reported PCC power and limit |
| Notice masking | future event limits are hidden before the declared notice window |
| PI and NA information logic | PI notice invariance and NA weak monotonicity checks |
| Frozen replay | generated and replayed observations, rewards and metrics are identical |
| Calibration integrity | schema, unknown fields, artifact SHA-256 and required class parameters fail closed |
| Controller integrity | specification or source mismatch prevents locked evaluation |
| Optimisation stack | HiGHS, Parquet and clean-install smoke paths execute |
| Resume | exhaustion and hosting ensembles resume without changing aggregates |

These tests establish implementation consistency with the declared model. They do not demonstrate that the model captures every operational feature of a production data centre. In particular, 1-h fluid execution does not include non-pre-emptive job starts, gang placement, checkpoint overhead or rack-level network contention.

### Capacity layers and notice diagnostics

At q = 0.95 and 95% confidence, the nonparametric PI tolerance boundary declined from 53.01 to 37.76 kW as duration increased from 1 to 8 h. The 100-scenario restricted NA programme used the same allowed empirical failures as a matched empirical PI order statistic. Both returned 56.42, 53.49, 45.17, 44.00, 43.01 and 41.19 kW for durations of 1, 2, 3, 4, 6 and 8 h, respectively, at every tested notice. These development values do not carry an independent confidence lower bound and must not be subtracted from the formal PI tolerance boundary to estimate an information gap.

| Duration | PI tolerance, q = 0.95 (kW) | Restricted NA, N = 0 h (kW) | N = 2 h (kW) | N = 6 h (kW) |
|---:|---:|---:|---:|---:|
| 1 h | 53.01 | 56.42 | 56.42 | 56.42 |
| 2 h | 44.46 | 53.49 | 53.49 | 53.49 |
| 3 h | 41.19 | 45.17 | 45.17 | 45.17 |
| 4 h | 40.15 | 44.00 | 44.00 | 44.00 |
| 6 h | 40.15 | 43.01 | 43.01 | 43.01 |
| 8 h | 37.76 | 41.19 | 41.19 | 41.19 |

For H = 4 and 8 h, 6 h notice exposed a mean 1,829.34 GPU-h of work eligible for pre-execution, compared with 133.05 GPU-h of no-control pre-event spare capacity. The paired robust-controller schedules changed by 1.33 and 1.30 GPU-h per pre-event interval, respectively. Despite this schedule divergence, both PI and restricted NA notice gains were 0.0 kW. At the fixed comparison capacities, the causal controller succeeded in 92 of 100 development episodes for both durations; interval delivery accounted for 22 of 23 binding counts at H = 4 h and all 24 counts at H = 8 h. Thus the notice diagnostic identified a lack of usable pre-event headroom and an unchanged binding delivery constraint, rather than absence of eligible work.

Validation selection froze one candidate for each q × H × N cell before locked-ID replay. At q = 0.95, H = {2, 3, 4, 6, 8} h passed at all three notice values, whereas H = 1 h failed at all notices, yielding 15/18 certified cells. The H = 1 h candidate achieved 477/500 successes, but its one-sided 95% Wilson lower bound was 0.936 and therefore remained below q = 0.95. Secondary q = 0.90 and q = 0.99 analyses certified 15/18 and 9/18 cells, respectively. Candidate failures were attributed to linked mean/interval delivery; the other declared service criteria did not appear as locked-ID failure labels.

### Repeated-event exhaustion

Repeated-event capacities were fixed at 44.0003 kW for H = 4 h and 41.1908 kW for H = 8 h. Each of the 20 development and 20 validation cells contained 100 independent four-event episodes. The full validation pattern reproduced debt accumulation and non-monotonic joint success observed in development.

| Duration / recovery gap | Development joint success | Validation joint success | Validation event-4 residual delivery | Validation event-4 paired debt increment (kWh) |
|---|---:|---:|---:|---:|
| 4 h / 2 h | 0.75 | 0.78 | 1.0000 | 554.5 |
| 4 h / 4 h | 0.78 | 0.87 | 1.0000 | 656.8 |
| 4 h / 8 h | 0.94 | 0.97 | 1.0000 | 693.2 |
| 4 h / 12 h | 0.78 | 0.88 | 1.0000 | 852.0 |
| 4 h / 24 h | 0.61 | 0.77 | 0.9987 | 992.0 |
| 8 h / 2 h | 0.73 | 0.80 | 0.9910 | 1,058.4 |
| 8 h / 4 h | 0.85 | 0.83 | 0.9975 | 1,088.1 |
| 8 h / 8 h | 0.65 | 0.54 | 0.9963 | 1,166.1 |
| 8 h / 12 h | 0.79 | 0.68 | 0.9995 | 1,019.6 |
| 8 h / 24 h | 0.00 | 0.00 | 0.9933 | 1,381.8 |

Power delivery remained close to the matched fresh-event counterfactual even in cells with poor joint success. Failures could instead arise from window relief or episode-level service feasibility after multiple deferrals. The best validation cell, H = 4 h with an 8-h gap, had empirical joint success of 0.97 but a one-sided 95% Wilson lower bound of 0.927. No cell was therefore labelled a q = 0.95 repeated-event capacity certificate.

### Renewable integration and sensitivity analyses

At the fixed 201-kW data centre, allowing more PV curtailment increased simultaneous PV hosting in all portfolios. Flexible operation retained a positive capacity difference at every declared curtailment threshold. The headline 5% condition produced scenario-paired mean gains of 44.85 kW without BESS and 43.20 kW with BESS, with Bonferroni 95% simultaneous confidence intervals of 41.68–48.08 and 39.99–46.46 kW.

| Maximum curtailment | Rigid, no BESS (kW) | Flexible, no BESS (kW) | Rigid, BESS (kW) | Flexible, BESS (kW) |
|---:|---:|---:|---:|---:|
| 0% | 353.87 | 444.51 | 445.39 | 511.68 |
| 5% | 584.69 | 617.52 | 653.39 | 686.77 |
| 10% | 674.84 | 709.34 | 739.73 | 770.78 |
| 20% | 838.58 | 885.17 | 909.14 | 954.46 |

For the fixed 500-kW PV system, validation flexible-minus-rigid PV-use effects were 18.37 kWh without BESS and 5.76 kWh with BESS. Renewable demand share increased by 0.0577 and 0.0443 percentage points, while grid import decreased by 180.32 and 168.98 kWh. The larger grid-energy changes were not equal to the PV-use effects because workload rescheduling also changed energy timing and service use. Flexible schedules used the full declared 1% deadline-miss allowance, while rigid schedules had zero misses; all four conditions ended with zero terminal backlog. Maximum PCC import did not decline consistently under flexibility.

The validation 2 × 2 × 2 hosting analysis returned positive workload-flexibility effects in all PV/BESS portfolios. AI×BESS interactions were −52.31 kW without PV and −88.54 kW with PV, both beyond the ±10.05-kW practical margin in the substitution direction. The AI×PV interaction was +44.59 kW without BESS and therefore practically complementary. With BESS it was +8.36 kW with a 1.05–15.74 kW simultaneous confidence interval, so the direction was positive but the practical magnitude was indeterminate.

Predeclared sensitivity analyses identified workload arrival and dynamic power as the largest tested sources of variation in the PI boundary. Reducing flexible-arrival utilisation from 0.65 to 0.50 changed the H = 4 and 8 h capacities by −9.26 and −8.71 kW; increasing it to 0.80 changed them by +37.84 and +15.73 kW. Rigid-utilisation and deadline-slack perturbations produced no additional change at the tested points. At q = 0.95, lower/nominal/upper power cases produced 37.81/40.15/42.87 kW at H = 4 h and 35.56/37.76/40.32 kW at H = 8 h. Changing PUE from 1.20 to 1.10 or 1.30 scaled absolute capacity, while changing the fixed node overhead from 150 to 450 W did not change baseline-relative single-event firm kW.

Among success-criterion perturbations, relaxing linked mean and interval delivery from 0.95 to 0.90 increased H = 4 and 8 h PI capacity from 40.15 and 37.76 kW to 42.38 and 39.86 kW. Tightening delivery to 0.98 reduced them to 38.92 and 36.60 kW. Tested changes to deadline-miss, rebound and recovery-window-relief thresholds left these two development capacity points unchanged. This finding is local to the declared PI scenarios and is not evidence that those criteria can be removed from causal or repeated-event evaluation.

Locked-OOD replay jointly changed community profile and workload-arrival process. At q = 0.95, the H = 1, 2, 3, 4, 6 and 8 h candidates achieved 437, 433, 445, 425, 398 and 383 successes among 500 episodes, respectively; no duration passed at any notice. The q = 0.90 and q = 0.99 candidates also yielded 0/18 certified cells. Because candidate reselection was prohibited, this result establishes failure of transfer for the frozen Model A candidates, not zero available capacity in the OOD distribution.

## Supplementary Figures

### Supplementary Figure 1 | AIDRBench environment and evidence flow

[FIGURE TO BE GENERATED] Community profile, Alibaba-2026-calibrated job process, configured demand-response events and the calibration artifact enter a frozen hourly scenario. Aggregate online actions and class-aware planning variables feed equivalent workload, power and metric definitions. BESS is shown only on the renewable-planning branch.

### Supplementary Figure 2 | Four-GPU power calibration

[FIGURE TO BE GENERATED] One- and four-GPU run means for training and offline inference, calibration/held-out split, topology annotation and lower/nominal/upper artifact parameters. GPU points within a run are shown as repeated observations, while uncertainty uses independent run means.

### Supplementary Figure 3 | Normalised observation and information timing

[FIGURE TO BE GENERATED] Grouped 63-dimensional `firm_v5` observation, feature bounds and a timeline showing when arrivals, forecasts and demand-response requests become visible.

### Supplementary Figure 4 | Representative frozen episode transition

[FIGURE TO BE GENERATED] Arrivals, action, class-aware execution, queue state, PCC power, delivery, backlog and compute debt for one hash-identified scenario.

## Supplementary Tables

### Supplementary Table 1 | Hardware calibration parameters

| Parameter | Estimate | Uncertainty | Statistical unit |
|---|---:|---:|---|
| Idle board power | 13.94 W GPU⁻¹ | 6.74–18.68 W GPU⁻¹ within-run range | one node idle run |
| Training active board power | 259.08 W GPU⁻¹ | 225.81–292.35 W GPU⁻¹, 95% t interval | independent four-GPU run mean, n = 2 |
| Offline-inference active board power | 300.02 W GPU⁻¹ | 299.69–300.35 W GPU⁻¹, 95% t interval | independent four-GPU run mean, n = 2 |
| Node fixed overhead | 300 W node⁻¹ | assumed range 150–450 W node⁻¹ | engineering assumption |
| Held-out active-power MAE | 3.80 W GPU⁻¹ | one held-out run per class | held-out independent run |

### Supplementary Table 2 | Model A reference configuration

| Component | Declared value |
|---|---|
| Time resolution | 1 h |
| Main horizon / clearance tail | 7 days / 48 h |
| Forecast horizon | 6 h |
| PCC capacity / community peak | 1,000 kW / 800 kW |
| Data-centre fleet | 144 nodes × 4 GPUs |
| Reference-mix operating peak | 201.00 kW |
| Flexible GPU pool fraction | 0.60 |
| PUE / node overhead | 1.20 / 300 W node⁻¹ |
| Target workload utilisation | 0.65 |
| Workload classes | training 0.50; offline inference 0.50 |
| Class flexible fractions | training 1.00; offline inference 0.50 |
| Deadline buckets | 0, 1, 2, 3, 6, 12, 24, 48 h |
| Event durations / notices | 1, 2, 3, 4, 6, 8 h / 0, 2, 6 h |
| Recovery window | 24 h |

### Supplementary Table 3 | Provenance and release artifacts

[TO BE COMPLETED AT RELEASE: Git commit, scenario-set hashes, source-data manifest hash, calibration artifact hash, controller specification hash, software environment hash and Zenodo DOI.]
