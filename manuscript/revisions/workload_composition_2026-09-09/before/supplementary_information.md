<!--
Working Supplementary Information, version 0.19, 2026-09-08.
Results clarified around workload choices, dispatch programmes, grid value and participation costs. No new calculations.
Existing artwork retained pending the author-planned redraw; author metadata pending.
-->

# Supplementary Information

## Job constraints and participation costs define firm data-centre demand response

[AUTHOR NAMES]

## Reader guide

These materials support the choices examined in the main text: which work may be deferred, which power and call schedule meet service requirements, what the local grid gains, and what compensation covers participation costs. Computing work is assigned to graphics processing units (GPUs). Six Supplementary Notes follow the six Results sections; ten Supplementary Methods sections provide the inputs, calculations and evaluation rules. Tables retain the full comparisons so that the main text can concentrate on the decisive results.

Three kinds of evidence should be read separately. Perfect-information (PI) and restricted non-anticipative (NA) schedules estimate planning capacity under their stated information assumptions. Independent tests assess whether a fixed controller can deliver a selected offer while meeting service requirements. Economic screening then asks what compensation would justify offering that certified capacity. The guide below links each main result to these supporting materials. PV denotes photovoltaic generation, BESS a battery energy storage system and PCC the point of common coupling to the upstream grid.

| Main-text result | Supplementary Methods | Supplementary Notes | Related displays |
|---|---|---|---|
| 1. Work eligibility, allocation and planning capacity | 1–4, 6, 9 | 1 | Supplementary Figs. 1–2; Tables 1–3, 10–11, 13–14 |
| 2. Duration, reliability and notice | 4–5, 9 | 2 | Note 2 table; Supplementary Table 12 |
| 3. Repeated calls, capacity and recovery | 3–4, 6, 10 | 3 | Supplementary Tables 15–18 |
| 4. PV hosting, utilisation and interactions | 6 | 4 | Supplementary Table 6 |
| 5. Independent testing and transfer | 1, 4–5, 9 | 5 | Supplementary Figs. 3–5; Tables 4–5 |
| 6. Participation costs | 7–10 | 6 | Supplementary Tables 7–9, 19 |

## Supplementary Notes

### 1. From eligible work to planning capacity

Work eligibility and GPU allocation answer different operational questions. Eligibility is the fraction of total work that may be postponed; allocation is the fraction of installed GPUs assigned to process that work. Neither is an assumed fraction of electrical demand that can always be removed. At fixed 40% flexible GPU allocation, increasing eligible work from 10% to 60% raised the four-hour PI lower bound from 4.54 to 36.36 kW. Supplementary Tables 10–11 report the share comparisons, Table 13 the joint grid and Table 14 paired interactions. The illustrative 50% power comparator did not constrain optimisation.

GPU allocation changed both processing headroom and the load that would have occurred without demand response. The no-response schedule executed released work as soon as capacity allowed, so each event inherited an allocation-dependent queue and reference load. Allocation effects were consequently small or absent in some feasible ranges and larger near processing constraints. Table 14 tests this dependence using paired mean interactions. These intervals describe mean scenario effects, not uncertainty around the PI lower-bound surface. Configurations that failed structural or baseline service checks delimit the valid comparisons within this model; their frequency is not a real-facility failure rate.

Power measurements provide the conversion from scheduled work to electrical demand. Four-GPU training averaged 259.08 W per GPU, compared with approximately 300 W during single-GPU training (Supplementary Fig. 2). Offline inference remained near 300 W in both conditions. Synchronisation and PCIe/NCCL communication are possible explanations for the training difference, but the experiment did not separate communication energy from kernel occupancy. The calibration applies to the measured topology rather than establishing a general scaling law for multiple GPUs.

The uncertainty in Supplementary Table 1 reflects the measurement design. Active-power intervals used two independent calibration runs per workload class. The held-out mean absolute error was 3.80 W overall, with 7.56 W for training and 0.03 W for inference. The small number of runs limits precision, particularly for training. Idle power was 13.94 W; the 6.74–18.68 W range describes variation among GPUs within one node-level run, not a confidence interval.

We also checked that the planning reformulation preserved the computed capacity. The job-edge and class-aware cumulative PI formulations agreed at all 18 diagnostic points.

The workload-sampler check assessed how much information was retained after reducing the full job summary to a smaller working dataset. We compared the formal 100,000-row sampler with an independent 100,000-row reservoir from the complete normalised summary, using seed 20,260,824. Across three numerical job characteristics, the largest Kolmogorov–Smirnov statistic was 0.00774. Maximum absolute relative errors were 1.69% for medians and 0.99% for 95th percentiles; categorical total variation was at most 0.00656.

The sampler nevertheless failed the full engineering acceptance check. Median-normalised Wasserstein distance reached 0.218 for offline-inference requested GPU-hours, above the 0.10 limit. This diagnostic was sensitive to the large tail relative to the small median. The sampler therefore supports the reported central and quantile summaries, while full-distribution agreement and production chronology remain unestablished.

### 2. Duration, reliability and advance notice

A longer event left less sustained power available from the same reference workload. The table separates two statistical questions. The PI tolerance lower bound gives a conservative capacity supported at reliability q = 0.95 with confidence 0.95, under full future information. The empirical columns instead compare PI and restricted non-anticipative (NA) scheduling at the same allowed sample failure count. Thus, 40.15 kW and 44.00 kW at four hours describe different estimands, not inconsistent estimates of one certificate. The NA restriction coupled decisions across indistinguishable histories; matching PI in this diagnostic does not certify a general causal controller.

Empirical PI and restricted NA coincided at all six durations and all three notice values. Their matched empirical difference was therefore zero. Comparing either empirical value directly with the tolerance lower bound would mix a sample comparison with a population-level uncertainty statement.

| Duration | PI tolerance lower bound, q = 0.95 (kW) | Empirical PI/NA, N = 0 h (kW) | N = 2 h (kW) | N = 6 h (kW) |
|---:|---:|---:|---:|---:|
| 1 h | 53.01 | 56.42 | 56.42 | 56.42 |
| 2 h | 44.46 | 53.49 | 53.49 | 53.49 |
| 3 h | 41.19 | 45.17 | 45.17 | 45.17 |
| 4 h | 40.15 | 44.00 | 44.00 | 44.00 |
| 6 h | 40.15 | 43.01 | 43.01 | 43.01 |
| 8 h | 37.76 | 41.19 | 41.19 | 41.19 |

The reference notice diagnostic asked whether earlier information could change the schedule enough to increase the response. Six-hour notice exposed a mean 1,829.34 GPU-h of work eligible for pre-execution, but mean spare capacity before the event was 133.05 GPU-h. For 4- and 8-h events, paired controller schedules changed by 1.33 and 1.30 GPU-h per pre-event interval, respectively. The planning capacity gain remained 0.0 kW at both durations.

At the fixed comparison requests, the controller succeeded in 92 of 100 development episodes for each duration. A diagnostic flagged every criterion with service margin ≤10<sup>−4</sup>, including near-threshold and failed criteria. Interval delivery accounted for 22 of 23 flags at 4 h and all 24 flags at 8 h. An episode could have several flags, so these counts describe criteria rather than failed episodes or active optimisation constraints. Earlier notice changed execution, but did not increase capacity in this reference comparison.

Reliability targets also changed the validation-selected offer, so different q surfaces did not test the same capacity. Independent outcomes for all three q values are retained in Supplementary Table 4 and discussed in Supplementary Note 5. Selection and certification remain separate from the planning comparison above.

The extended notice test examined whether this pattern persisted when work eligibility and GPU allocation changed. Development PI tolerance limits fixed a request for each of 32 service-feasible configurations at each of two durations. The frozen controller then faced 100 validation scenarios at each notice. All 128 paired comparisons of 2 or 6 h against 0 h had zero discordant success outcomes. Exact McNemar and Holm-adjusted P values were 1.0. These tests found no change in success at the fixed requests; they did not establish equivalence or search for the maximum causal capacity at each notice.

Saved hourly traces confirmed identical execution before each notice window and retained the schedule changes that followed. The 95%-deferrable stress case achieved 54/100 and 42/100 successes at the 4- and 8-h requests, respectively, at every notice. The 50%-work, 30%-GPU case achieved 100/100 at both requests and every notice (Supplementary Table 12). Both stress cases depended on the finite horizon, and this experiment produced no new locked certificate.

### 3. Choosing offers for repeated calls

The repeated-call studies separate an initial diagnostic from subsequent offer qualification. The diagnostic below used four calls with the queue carried forward, requesting 44.0003 kW for four-hour events and 41.1908 kW for eight-hour events. These were planning requests, above the later single-event certified offers. Development and validation each used 100 independent episodes per duration–gap combination. Figure 3 and this table show why event delivery and accumulated work must be examined together; they do not quantify the repeatability of the lower certified offers. That comparison is in Supplementary Table 15.

These requests exceeded the later single-event certified offers in Supplementary Table 4. The experiment therefore diagnoses repeated operation at the stated requests. The table reports success of the entire sequence, the fifth-percentile delivery ratio for the fourth call and its mean additional compute debt relative to matched fresh calls.

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

Fourth-call delivery remained close to the matched fresh-call response even when the whole sequence failed service or peak-relief requirements. Several combinations combined larger debts with lower joint success. Longer recovery gaps did not consistently improve success; each later call inherited a queue and deadline state shaped by earlier operation.

The best validation combination, 4-h calls separated by 8 h, succeeded in 0.97 of episodes. Its one-sided Wilson lower bound was 0.927, below q = 0.95. No tested combination met the certification rule. These outcomes establish the need to assess dispatch history at the tested commitments; smaller repeated-event offers were not qualified by this experiment. The later capacity extension below answers the distinct question of repeatability at previously certified offers.

#### Qualification at matched single-event offers

The extension used new development and confirmation seed ranges, separate from the original locked sets. Supplementary Table 15 reports all ten programmes, the same-clock fresh-programme comparison, the selected fraction and its confirmation result. The four-hour/eight-hour-gap original offer also passed its predeclared confirmation comparison. Its more conservative development-selected fraction therefore cannot be read as the maximum available capacity. The other original offers failed the four-call qualification criterion, although the relative contribution of history differed by programme. Across the ten original-offer programmes, mean additional fourth-call queue energy ranged from 0.509 to 1.320 MWh, while fifth-percentile delivery relative to the fresh call remained 0.9929–1.0000.

Nine positive candidates passed confirmation in 296–300 of 300 episodes. No positive candidate was selected for eight-hour calls with twenty-four-hour gaps, because all five development fractions failed. This records an unqualified tested grid under that setting, not zero physical flexibility. Confidence bounds are pointwise and do not assert joint coverage across programmes or offers.

#### Queue indicators did not improve the fixed predictive model

The contract-only model used duration–gap–offer–event-position cells. Adding excess queue energy, followed by deadline pressure and the fraction of queued work due within the event, increased confirmation Brier loss from 0.033252 to 0.033332 and 0.033502 (Supplementary Table 16). For the full state model minus the contract-only model, the paired change was +0.000250 (95% seed-cluster bootstrap interval, +0.000150 to +0.000339). Log loss and ROC AUC also worsened. These models predicted event-local electrical failure; they excluded episode-global deadline and terminal labels. The result does not establish that deadlines are irrelevant. It shows that these additional linear predictors did not improve this fixed model on the held-out sample.

Applying the same fitted models to production-timing cases without refitting did not reverse that conclusion in Brier loss. Chronological-case losses were 0.219717, 0.221827 and 0.221049 for the three models. These secondary scores are descriptive and were specified after aggregate production success counts had been observed. They provide no claim of a validated transferable state-to-capacity rule.

#### Arrival ordering and recovery boundaries

The production-timing comparison used eight disjoint observed weeks and ten synthetic job/community realisations per week. Every no-response case passed the physical PCC and service gate. The chronological and permuted variants retained identical total work, class totals, slack distributions and the marginal distribution of hourly work. Original-offer success was lower under chronological ordering in both tested durations (Supplementary Table 17). In paired four-hour cases, 39 passed only after permutation and seven passed only in chronological order; corresponding eight-hour counts were 26 and nine. Permutation changes serial dependence and alignment with event clocks together, so the comparison does not identify a pure autocorrelation effect.

For the horizon intervention, the original and extended simulations had the same first seven days of jobs and the same existing community observations. At 9.18 kW, both controlled trajectories were identical through the final event, but mean missed work subsequently changed from 1,395.06 GPU-h to numerical zero. All 300 extended cases also passed when the missed-work denominator was held at the original seven-day work, ruling out denominator dilution as the explanation. At 36.71 kW, 262/300 extended cases passed with either denominator. The controller’s recovery guard bounds power relative to the no-response baseline, which falls when arrivals stop. This exposes sensitivity to the experimental cutoff rather than establishing a universal failure of long recovery intervals (Supplementary Table 18).

### 4. PV hosting, utilisation and resource interactions

The planning decision was how much PV could be installed while all 100 validation scenarios remained feasible. At the reference 201-kW data-centre scale and a 5% curtailment limit, flexible scheduling added 32.83 kW without storage and 33.38 kW with storage. Allowing more curtailment raised the common feasible installation, and flexibility improved it at every tested threshold. This capacity metric is distinct from the additional energy used when installed PV is fixed.

A second comparison averaged the improvement within each scenario. Those paired mean gains were 44.85 and 43.20 kW, with simultaneous 95% intervals of 41.68–48.08 and 39.99–46.46 kW. They were larger because an average improvement need not be feasible in every scenario. The table reports the common capacities rather than these paired means; each common capacity uses all 100 validation scenarios.

| Maximum curtailment | Rigid, no BESS (kW) | Flexible, no BESS (kW) | Rigid, BESS (kW) | Flexible, BESS (kW) |
|---:|---:|---:|---:|---:|
| 0% | 353.87 | 444.51 | 445.39 | 511.68 |
| 5% | 584.69 | 617.52 | 653.39 | 686.77 |
| 10% | 674.84 | 709.34 | 739.73 | 770.78 |
| 20% | 838.58 | 885.17 | 909.14 | 954.46 |

At three times the reference data-centre size, rigid/no-storage and rigid/storage operation remained feasible in 31 and 96 scenarios. Both flexible portfolios were feasible in all 100. Infeasible scenarios were retained as missing from the common envelope, not assigned zero capacity. Solver checks found maximum simultaneous charge/discharge of 2.19 × 10<sup>−7</sup> kW, zero terminal charge-state deviation, curtailment residual 1.19 × 10<sup>−11</sup> and PCC residual 2.50 × 10<sup>−12</sup> kW.

Installing more PV and making better use of an existing installation are different benefits. With PV capacity fixed at 500 kW, flexible scheduling increased PV use by only 18.37 kWh without storage and 5.76 kWh with storage. Renewable demand share rose by 0.0577 and 0.0443 percentage points, while grid imports fell by 180.32 and 168.98 kWh. The import reductions therefore included changes beyond additional PV use, and PCC peak did not consistently decline.

The original comparison also allowed different service outcomes: flexible schedules used the full 1% missed-work allowance, whereas rigid schedules had no misses. All four portfolios ended with zero backlog. This motivated the zero-miss check below.

Requiring every job to meet its deadline tested whether the renewable benefits depended on the missed-work allowance. The check repeated reference-scale hosting at 5% curtailment and operation with 500-kW PV, across 100 development and 100 validation scenarios. Both workload modes and storage conditions were included. All 1,600 result rows were optimal and had zero observed missed GPU-hours.

Validation common-capacity gains remained 32.825 and 33.377 kW. Paired mean gains were 44.854 and 43.198 kW, changes of −0.000079 and −0.001031 kW from the original formulation. PV-use gains were 18.366443 and 5.764980 kWh, changing by less than 0.000006 kWh. The hosting and utilisation findings therefore persisted without deadline misses. This comparison used non-locked PI planning, rather than the independently tested controller.

Storage and workload flexibility could relieve some of the same constraints. In the factorial analysis of data-centre hosting capacity, AI×BESS interactions were −52.31 kW without PV and −88.54 kW with PV (Supplementary Table 6). Both exceeded the practical substitution margin in magnitude: adding storage reduced the incremental benefit of flexible computing. AI×PV was +44.59 kW without storage. With storage, its +8.36-kW estimate had a 1.05–15.74 kW simultaneous interval, which crossed the 10.05-kW practical threshold. The latter comparison supported a positive direction but not practically meaningful complementarity under the declared rule.

### 5. Independent certification, sensitivity and transfer

#### Independent testing of fixed offers

Independent testing asked whether the selected offers worked on episodes that had not been used to choose them. Locked in-distribution (locked-ID) testing certified 15 of 18 duration–notice combinations at q = 0.95, including every tested duration from 2 to 8 h (Supplementary Table 4). The 1-h candidate succeeded in 477/500 episodes, yet its Wilson lower bound was only 0.936. Its empirical success fraction therefore did not provide enough evidence for the 0.95 reliability requirement.

Across the 9,000 episode–combination replays, 186 failures consisted of 81 combined mean-and-interval delivery failures and 105 interval-only failures. No failure label involved deadline misses, rebound, window relief or terminal backlog. Recovery was not resolved within 24 h for 8,953 trajectories. That separate diagnostic was not a certification criterion, so unresolved recovery did not itself overturn a passing certificate.

Secondary targets certified 15/18 cells at q = 0.90 and 9/18 at q = 0.99. At q = 0.90, the 1-h offer failed with 454/500 successes and a 0.884 lower bound. At q = 0.99, 3-, 6- and 8-h offers passed, whereas the 4-h offer failed despite 498/500 successes and a 0.988 lower bound. Because validation selected a different capacity at each q, these outcomes were not tests of one common offer.

The transfer test kept each offer fixed while changing both workload arrivals and community demand to create out-of-distribution (OOD) conditions. For H = 1, 2, 3, 4, 6 and 8 h, the q = 0.95 candidates succeeded in 437, 433, 445, 425, 398 and 383 of 500 episodes, respectively. None retained certification at any notice (Supplementary Table 5). The q = 0.90 and 0.99 candidates also certified 0/18 combinations. These results concern transfer of the original offers; the experiment did not search for a smaller offer under the changed conditions.

Across the 18 q = 0.95 OOD cells, failure labels comprised 498 interval-only, 828 combined mean-and-interval, 93 delivery-and-rebound, three delivery-and-window-relief and 15 window-relief-only outcomes. These counts include the three notice replays, whose outcomes were identical within duration; they are not 18 independent capacity estimates. Both community shape and arrival process changed, so this experiment alone could not assign the loss to one component.

#### Sensitivity to physical and contractual assumptions

The physical sensitivities show which model assumptions changed planning capacity within the tested ranges. Reducing the arrival scaling coefficient from 0.65 to 0.50 changed the 4- and 8-h PI bounds by −9.26 and −8.71 kW. Raising it to 0.80 changed them by +37.84 and +15.73 kW. The tested rigid-utilisation and deadline-slack changes produced no additional effect at these points.

Power assumptions changed the conversion from work to kilowatts. Lower, nominal and upper power cases gave 37.81, 40.15 and 42.87 kW at 4 h, and 35.56, 37.76 and 40.32 kW at 8 h. Changing power usage effectiveness (PUE) from 1.20 to 1.10 or 1.30 scaled absolute capacity. Varying fixed overhead from 150 to 450 W changed the operating peak, but cancelled when controlled and baseline single-event power were subtracted.

Relaxing linked mean and interval delivery from 0.95 to 0.90 increased the 4- and 8-h bounds from 40.15/37.76 to 42.38/39.86 kW. Tightening delivery to 0.98 reduced them to 38.92/36.60 kW. Tested deadline-miss, rebound and window-relief threshold changes left these points unchanged. This local PI result did not justify removing those criteria from causal or repeated-event tests.

#### Community profiles and the transfer boundary

A separate comparison changed community demand alone, keeping jobs and hardware fixed (Supplementary Fig. 5). All three profiles gave the same PI tolerance bounds: 53.005, 44.464, 41.191, 40.147, 40.147 and 37.760 kW across the six durations. Individual-scenario differences were also zero from 3 h onward. Some shorter-duration optima differed, but not enough to change the tolerance order statistic.

Fixed development replays produced 98/100 successes at 39.651 kW for 4 h and 97/100 at 36.706 kW for 8 h. The respective Wilson lower bounds were 0.941 and 0.927. Window-relief quantiles varied across profiles, whereas delivery-based success remained unchanged. These non-locked diagnostics isolate the profile comparison; they do not replace the independent certificate.

Community shape nevertheless changed PV hosting in the paired development ensembles. All 1,200 renewable programmes were optimal with zero terminal backlog. The maximum missed-work fraction was 0.01000000000000016, reflecting numerical tolerance around 0.01. The table separates differences between cell minima from paired mean effects, with Bonferroni 95% bootstrap intervals for the latter. These development capacities should not be substituted for the validation values in Supplementary Note 4.

| Profile / BESS | All-scenario rigid / flexible PV capacity (kW) | Boundary gain (kW) | Paired mean gain (kW) | Simultaneous 95% interval (kW) |
|---|---:|---:|---:|---:|
| 3A / absent | 430.448 / 525.741 | 95.293 | 45.664 | 41.654–50.170 |
| 3A / present | 482.655 / 585.914 | 103.259 | 43.346 | 39.078–47.961 |
| 3C / absent | 603.524 / 667.040 | 63.516 | 42.879 | 39.967–46.093 |
| 3C / present | 668.560 / 726.905 | 58.345 | 42.353 | 39.365–45.674 |
| 5A / absent | 506.168 / 585.413 | 79.246 | 44.905 | 39.500–50.781 |
| 5A / present | 558.400 / 639.265 | 80.866 | 42.949 | 37.529–49.062 |

Boundary gains used unrounded source values, so subtracting displayed capacities can differ in the final digit. All six paired mean effects were positive, while absolute hosting and common-capacity increments varied across profiles. The comparison therefore isolates a difference in local system value without assigning the joint-OOD certification loss to community shape alone.

### 6. Economic thresholds and the physical costs behind them

#### Paired costs and accounting scale

The economic comparison followed the same event with and without demand response to identify incremental costs. The ledger contained 300 paired events and 33,414 interval rows: 100 validation scenarios for each 2-, 4- and 8-h offer. Successful replays numbered 95, 96 and 95, respectively. These counts describe the economic validation sample, rather than a new locked certification.

Revenue accounting credited only delivery up to the requested obligation. Capped delivery plus contractual shortfall reconciled to requested energy within numerical precision. Raw power reduction exceeded the cap in 280 events, so valuing the uncapped reduction would have overstated performance revenue under the declared payment rule.

Following work to episode end changed the apparent cost of providing response. For 4-h events, mean positive paired backlog area increased from 16,474.74 GPU-h² at recovery stop to 19,605.98 GPU-h² at episode end. Mean incremental energy changed from −257.533 to +0.343 kWh as postponed work was completed. Ending the accounts at the recovery window would therefore omit waiting time and overstate energy savings.

The observed burden was principally delayed completion. Mean deferred work was 305.06, 535.75 and 991.30 GPU-h for 2, 4 and 8 h. Across all events, incremental missed and terminal work remained below 10<sup>−6</sup> GPU-h. The largest positive missed increment was about 2.99 × 10<sup>−13</sup> GPU-h, and terminal excess was zero. These trajectories did not demonstrate permanent production or revenue loss; the separate displacement charge represents an assumed business exposure.

The scale comparison tests how the same reference ledger shares site-wide costs over different amounts of offered capacity. All payments in the table use offered kW as the denominator and are reported in real-2026 US$ per kW-year. At the proportional 1-MW facility accounting scale, the 39.651-kW reference four-hour offer becomes 197.266 offered accounting kW. Facility MW and offered kW are therefore different quantities. The conversion does not establish a new technical certificate or measured economies of scale.

When fixed site cost was included, its contribution fell from US$633.66 to US$6.34 per kW-year between the 0.2- and 20-MW scales. Excluding that cost left the threshold constant within each participation mode.

| Participation mode | 0.2 MW, including fixed site | 1 MW, including fixed site | 5 MW, including fixed site | 20 MW, including fixed site | Excluding fixed site at all scales |
|---|---:|---:|---:|---:|---:|
| Slack-backed | 753.53 | 246.60 | 145.21 | 126.20 | 119.87 |
| Reserved headroom | 869.68 | 362.75 | 261.36 | 242.35 | 236.02 |
| Throughput-displacing | 921.93 | 414.99 | 313.61 | 294.60 | 288.26 |

At 4 h and 1 MW, mean delay cost contributed US$123.62 per kW-year in every mode. Reserve capital added US$116.15 only for reserved headroom, and assumed displaced contribution added US$168.90 only for throughput displacement. Fixed site cost contributed US$126.73; energy, non-performance and performance-credit terms were small under the reference assumptions. This was a parameterised decomposition rather than measured operator accounts. Supplementary Table 9 retains all nine duration–mode reference thresholds. In each mode, longer events increased required compensation while certified power declined.

#### Sensitivity to delay prices and fixed costs

The assumed price of delay and the fixed site charge materially changed the compensation required (Supplementary Tables 7–8). At 4 h, 50 calls and 1 MW, raising delay price from zero to twice reference increased the slack-backed threshold from 117.04 to 376.19 US$ per kW-year. Corresponding ranges were 233.19–492.34 for reserved headroom and 287.50–544.55 for displacement, with site cost held at US$25,000 per year.

At the reference delay price, increasing site cost from zero to US$50,000 per year moved the slack-backed threshold from 119.87 to 373.33. Thresholds were non-decreasing in both costs. Before applying the zero floor, every site-cost contrast followed the exact \(\Delta F/K\) identity: the added annual site cost was spread over the same offered capacity.

Setting both costs to zero produced zero non-negative capacity payments in all 36 slack-backed duration–call-count–scale cells. The result retained performance compensation and zero variable-enablement, checkpoint and service-cost assumptions. It therefore did not imply costless response or universal profitability. The displacement charge remained an assumed business exposure, distinct from the observed delay and negligible incremental lost work.

#### Sensitivity to annual sampling

Increasing the number of annual draws checked numerical stability rather than uncertainty in real costs. The 200-draw reconstruction reproduced all nine reference thresholds within 4 × 10<sup>−10</sup> US$ per kW-year. With 10,000 draws, the three 4-h thresholds were 246.69, 362.83 and 414.98. The largest change across both expanded draw counts and all reference cases was 3.32, for 8-h slack-backed and reserved-headroom response at 2,000 draws (Supplementary Table 9). This numerical variation was smaller than the effects of the tested monetary assumptions.

#### Recovery throughput behind delayed work

The recovery mapping expresses delayed work as an equivalent processing requirement. The 95th-percentile event-end debt was 331.85, 583.00 and 1,047.55 GPU-h for 2, 4 and 8 h. Clearing the 4-h value over 24 h at efficiency 0.85 corresponds to 28.58 continuously available GPU equivalents. Rounding to whole four-GPU nodes gives 32 GPUs in eight nodes.

Using the declared class mix, 300-W node overhead and PUE 1.2 gives 13.35 kW of installed power and 9.94 kW of recovery-dynamic facility power. These quantities describe equivalent recovery throughput. They do not specify a hardware purchase, dedicated reserve or capital charge.

#### Costs of confirmed repeated programmes

Supplementary Table 19 follows each confirmed development-selected offer through its complete four-call trajectory. Positive excess backlog was integrated once from hour 63 to episode termination; overlapping recovery windows were not added as separate event ledgers. The reference comparison remained the original full-capacity no-response schedule, so the ledger represents the specified response-policy package relative to that schedule. It is not a comparison against a separately optimised no-call MPC policy.

At twelve series per year, the selected programmes required US$676.78–1,767.71 per offered kW-year at the proportional 1-MW accounting scale. The eight-hour/four-hour-gap offer was 33.04 reference kW at US$731.34 per kW-year; the eight-hour/twelve-hour-gap offer was 9.18 reference kW at US$1,767.71. Both capacity selection and the sequence ledger differ, so this comparison does not isolate a causal effect of gap length on price. A smaller offer spreads the same site charge over fewer kilowatts. The values describe tested options, not maximum reliable capacities or an optimal capacity–cost frontier.

The four-hour/twenty-four-hour-gap programme had mean incremental missed work of 3.70 GPU-h and a maximum of 486.07 GPU-h; its failed episode remained in the cost sample. Lost-work prices were applied separately without changing trajectories or qualification. All programmes ended with zero incremental backlog. Annualising whole series preserves history within each series but assumes independence between series; it does not establish continuous-year economics.

## Supplementary Methods

### 1. Scenario construction and evidence partitions

We used paired scenarios to separate the effects of scheduling from differences in the jobs or electricity demand being served. Alternative schedules received the same jobs, community demand and event timing (Supplementary Fig. 1). Each episode comprised seven dispatch days followed by a 48-h clearance tail. Jobs arrived only during the seven-day main horizon; the tail allowed remaining work, rebound and terminal backlog to be evaluated. The queue advanced deadlines in hourly steps, so the simulation time step was fixed at 1 h.

Community demand used NREL End-Use Load Profiles and retained its temporal shape after normalisation. Development, validation and locked in-distribution (locked-ID) episodes used the mixed 3A profile. The locked out-of-distribution (locked-OOD) set changed both the community profile to mixed 3C and arrivals from a non-homogeneous Poisson process to block arrivals. The reference configuration had an 800-kW background peak, a 1,000-kW point-of-common-coupling (PCC) import limit and 144 four-GPU nodes. Its reference-mix operating peak was 201.00 kW (Supplementary Table 2). This was a comparison system, not the nameplate design of a specific commercial facility.

Job characteristics came from the Alibaba GPU 2026 job-execution summary. The official 1.19-GB archive yielded 40,522,321 normalised rows. Streaming uniform random-key top-k sampling with seed 2026 produced 50,000 low-priority training and 50,000 low-priority offline-inference records. The resulting 100,000-row “Lite” sampler was made for this project to reduce repeated data access; it was not a separate Alibaba release. Episodes independently resampled job characteristics rather than replaying source timestamps or pod-hourly correlations.

Total arrival utilisation was 0.65, with equal training and offline-inference shares. All training and half of offline-inference work were deferrable, and the flexible GPU pool fraction was 0.60. Synthetic deadlines used training slack of 2–6 times runtime, bounded to 6–48 h, and inference slack of 1.5–4 times runtime, bounded to 2–24 h. The source summary did not contain production deadlines. Single events started at one of 24 candidates spanning 15:00–20:00 on days 3–6. Replay covered durations H = {1, 2, 3, 4, 6, 8} h and notice N = {0, 2, 6} h.

Different scenario partitions served different evidential roles. Development supported model construction and diagnostics. Validation replicated planning results and selected controller offers. Only the unused locked-ID episodes supplied the independent certificate. Locked-OOD episodes then tested the same fixed offers after a joint change in arrivals and community demand. Four disjoint seed ranges enforced these separations; neither locked set was used to search for a smaller capacity.

| Partition | Episode seeds | Independent episodes | Community profile | Arrival process | Permitted use |
|---|---:|---:|---|---|---|
| Development | 10,000–10,099 | 100 | `eulp_mixed_3a` | non-homogeneous Poisson | model construction, diagnostics and sensitivity design |
| Validation | 20,000–20,099 | 100 | `eulp_mixed_3a` | non-homogeneous Poisson | replication and causal-capacity selection |
| Locked ID | 30,000–30,499 | 500 | `eulp_mixed_3a` | non-homogeneous Poisson | one-time in-distribution certificate |
| Locked OOD | 40,000–40,499 | 500 | `eulp_mixed_3c` | block arrivals | one-time fixed-candidate transfer stress test |

Each episode seed generated independent child streams for community-window selection, arrivals and event placement. Reusing an episode across portfolios created a paired observation, not a new independent replicate. Canonical scenario hashes bound inputs to the horizon, forecast horizon, PCC limit and power-model fingerprint. Each locked set contained 500 unique scenario hashes and 2,000 verified payload files. Locked-ID had no overlap with validation; locked-OOD had no overlap with either validation or locked-ID. Both sets passed the no-response service audit with zero missed work and terminal backlog.

The protocol marked each locked set as consumed when opened and retained a post-run receipt. Locked-ID followed the freeze of the environment, criteria, controller and capacity-selection procedure; locked-OOD followed the locked-ID receipt. Neither set was used to re-estimate capacity. Supplementary Table 3 records the principal identifiers, and the source manifests retain the complete provenance.

### 2. GPU measurements and facility power conversion

The measurement node contained four NVIDIA RTX PRO 6000 Blackwell Max-Q Workstation Edition GPUs, each reporting a 300-W limit. The topology reported PCIe NODE paths and no NVLink connection. Clocks and power limits remained unchanged. Training used BF16 8192 × 8192 forward and backward matrix operations, with NCCL gradient all-reduce in the four-GPU condition. Offline inference used batched forward operations of the same precision and size without inter-GPU communication.

Each workload ran in one- and four-GPU conditions with three repeats. After a 5-s warm-up, read-only nvidia-smi telemetry sampled board power and utilisation every second for 20 s. Repeats 1–2 supplied calibration and repeat 3 was held out. For each four-GPU repeat, readings were averaged first over time within each GPU, then across GPUs. The resulting run means were the independent units. Student t 95% intervals used the two calibration means per active class; prediction error used only the held-out repeat (Supplementary Table 1).

CPU package telemetry required unavailable privileged register access, and no accessible baseboard management controller (BMC) or data-centre management interface (DCMI) channel provided whole-node power. CPU, memory, fan and conversion losses were therefore not measured at the wall. Node overhead was assumed to be 300 W and varied from 150 to 450 W. The calibration artifact was classified as benchmark_anchored_synthetic, with raw-input hashes, uncertainty definitions and held-out errors retained in the public record. Its SHA-256 is listed in Supplementary Table 3.

Facility power retained the execution class,

\[
P^{\mathrm{DC}}_t=P_{\mathrm{fixed}}+\sum_c e_cX_{c,t},
\]

In this expression, \(X_{c,t}\) is flexible work executed in class c during interval t, measured in GPU-h. Its coefficient is \(e_c=\mathrm{PUE}(p_c-p_{\mathrm{idle}})/(1000\Delta t)\), in kW per GPU-h. Board powers p are measured in W and \(\Delta t=1\) h. Subtracting idle power ensures that scheduled work contributes only incremental active power. Fixed facility power contains rigid-pool draw, flexible-pool idle draw and node overhead, all multiplied by PUE = 1.20.

The reference rigid draw used utilisation 0.40625. Class weights reflected eligible work: flexible work comprised 2/3 training and 1/3 inference, while rigid work was inference. Lower and upper calibration cases changed the coefficients while retaining 144 nodes. This additive conversion assumes the measured topology. It does not establish matching throughput or efficiency for H100, H200 or other GPU generations.

### 3. Queues, actions, observations and compute debt

Jobs were stored by class and remaining deadline at one-hour resolution, up to 48 h. The labels {0, 1, 2, 3, 6, 12, 24, 48} h grouped this state for reporting and observation; they were not the queue's internal time resolution. Execution followed earliest deadline first, could not precede release and could not exceed cumulative arrivals. Work remaining when its deadline expired was counted as missed. Controlled and no-response queues received identical arrivals.

The continuous action u in [0,1] selected the fraction of flexible GPU-hour capacity to execute during the current hour. The queue allocated that execution by deadline while retaining class identity for power accounting. A five-level action adapter {0, 0.25, 0.50, 0.75, 1.00} was available in the environment but was not used in the mainline analysis.

Each step added arrivals before selecting the action, executed work by deadline, recorded expiring work and aged the remaining buckets by one hour. Class-specific execution then determined data-centre power. Community load, PV and data-centre power determined PCC power, after which delivery, rebound, backlog, slack, compute debt and event history were updated. The paired no-response trajectory provided the baseline. Compute debt converted excess controlled backlog into future dynamic energy using active-minus-idle GPU power and PUE; idle-pool energy was excluded.

The observation interface specifies what the controller can know when choosing an action. The firm_v5 interface contains 63 float32 features in a fixed order (Supplementary Fig. 3). Power, backlog and time use their respective capacity, deadline-horizon and duration scales for normalisation. Values are clipped only at the declared feature bounds, and a Gymnasium Box check rejects any remaining out-of-range observation. The table lists each information group and its dimension.

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

The legacy state field named compute_debt_kwh stored the dynamic energy of the total controlled queue, rather than a baseline-subtracted quantity. Analyses of excess compute debt therefore explicitly subtract the matched no-response value; repeated-minus-fresh comparisons subtract the corresponding controlled-queue values, so their common no-response component cancels. This field was not a separate feature in the 63-element policy vector. Backlog, deadline-feasibility and slack features represented related service state. Offline planners optimised class-specific execution with release and deadline constraints. Battery actions belonged only to renewable planning. Supplementary Fig. 4 shows a deterministic validation example and does not supply certification evidence.

### 4. Delivery rules and statistical qualification

Successful demand response required both electrical delivery and acceptable computing service. For each fixed capacity, duration, notice and controller, an episode received one binary outcome after all six criteria below were evaluated. Delivery was the non-negative reduction in point-of-common-coupling power relative to the matched baseline, capped at the request. A high mean could not compensate for an hour below the interval threshold. Peak relief was evaluated over the event and its 24-h recovery window.

| Criterion | Headline threshold | Operational interpretation |
|---|---:|---|
| Mean delivery | ≥0.95 | mean capped baseline-relative reduction across all event intervals divided by R |
| Minimum interval delivery | ≥0.95 | every event hour delivers at least 0.95R |
| Deadline-miss fraction | ≤0.01 | expired GPU-hour work divided by offered work |
| Rebound ratio | ≤0.25 | largest post-event excess PCC load divided by peak event reduction |
| Event-and-recovery peak relief | ≥0.50 | baseline peak minus controlled peak over the event plus 24-h recovery window, divided by R |
| Terminal-backlog fraction | ≤0.02 | positive controlled-minus-baseline backlog at the end of the 48-h tail divided by total arrivals |

Failure attribution retained combined labels rather than assigning only the first failed criterion. Mean and interval failures could occur together, and delivery failures could coincide with rebound or window-relief failures. Recovery-time non-resolution was a separate diagnostic, not an additional certificate criterion.

Planning capacity and controller reliability required different statistical calculations. For PI planning, we first computed the maximum feasible reduction in each episode. An exact-binomial tolerance order statistic then supplied a lower limit intended to be exceeded by at least a fraction q of the scenario population, with confidence 0.95. Its rank was determined by binomial inversion. With 100 episodes, some reliability–confidence combinations were not estimable and were labelled accordingly.

The empirical PI/NA comparison omitted that population confidence requirement. Both schedules used the same allowed failure count in the sample, making their empirical capacities directly comparable. The nominal-versus-PI-tolerance comparison instead assessed an assumed power fraction against a planning limit that included sampling uncertainty.

Controller offers were selected before independent testing. For each q × H × N combination, ten binary-search iterations evaluated validation capacities over 0–100% of the declared reference range. A candidate was eligible when its empirical validation success fraction reached q, allowing a numerical tolerance of 10<sup>−12</sup>. The greatest eligible evaluated candidate was then frozen.

That candidate was certified only if the one-sided 95% Wilson lower bound from 500 locked-ID episodes reached q. Thus, an observed success fraction above q could still be insufficient once sampling uncertainty was considered. Confidence applied separately to each of the 54 reliability–duration–notice combinations, not jointly to all of them. Supplementary Note 5 and Tables 4–5 give the outcomes.

### 5. Frozen causal controller

The robust model-predictive controller solved a 6-h receding-horizon programme each hour and executed only its first decision. Inputs were the current queue, released work, a community/limit forecast and an arrival envelope estimated from the preceding 24 h. The envelope added one empirical standard deviation and imposed a minimum safety fraction of 0.15. Response limits beyond the notice boundary were masked. A separate power envelope capped execution during an event and its recovery window to protect delivery, rebound and window relief. It used a conservative worst-class power conversion and could restrict work recovery; it did not guarantee deadline feasibility. A threshold controller supplied the optimisation-infeasibility fallback.

| Controller field | Frozen value |
|---|---:|
| Planning horizon | 6 h |
| Solver / threads | HiGHS / 1 |
| Warm start | enabled |
| Deadline penalty | 1,000.0 |
| PCC-limit penalty | 20.0 |
| Backlog penalty | 0.2 |
| Backlog normalisation | 48 h |
| Switching penalty | 0.02 |
| Arrival-history window | 24 h |
| Arrival safety multiplier / floor | 1.0σ / 0.15 |
| Service envelope | enabled |
| Infeasibility fallback | threshold controller |
| Information structure | causal state plus 6-h environment forecast |

The controller was not trained and did not use reinforcement learning. Its YAML and normalised-specification hashes are retained in Supplementary Table 3. Validation selection also recorded the source commit, environment configuration, scenario hashes and controller-relevant code hashes. Locked replay reconstructed these records and stopped on any mismatch, including a changed implementation default.

### 6. Planning programmes and repeated-event design

The planning programmes asked how much flexibility could be used while a feasible computing schedule still existed. PI, restricted NA and renewable planners shared execution variables for each workload class. Cumulative execution could not exceed released work. Execution plus the permitted missed-work budget had to cover work whose deadline had passed, and available GPUs bounded total hourly execution. These constraints retained release timing, deadlines and class-specific power conversion. Supplementary Notes 1 and 4 report formulation and solver checks.

PV hosting fixed data-centre capacity and maximised PV nameplate capacity under curtailment, service and PCC limits. Hourly PV use plus curtailment equalled available PV; imports stayed between zero and 1,000 kW. The reference battery supplied 100-kW charge/discharge power and 200-kWh energy, with 0.95 efficiencies and initial and terminal charge states of 50%. A binary constraint prohibited simultaneous charging and discharging. A common hosting capacity was reported only when every scenario was feasible, using the minimum scenario-specific maximum. Average paired gains used within-scenario flexible-minus-rigid differences and were reported separately.

The fixed-operation programme used a 201-kW data centre and 500-kW PV system. Its lexicographic objective first preserved service feasibility, then maximised local PV use within a 10<sup>−5</sup>-kWh objective tolerance. The separate 2 × 2 × 2 design maximised data-centre hosting capacity with flexibility, PV and storage each on or off. Thus, its interactions concern data-centre capacity, whereas the fixed-data-centre programme concerns PV capacity. Paired renewable contrasts used 10,000 bootstrap resamples and Bonferroni familywise 95% intervals; interaction classification used a ±10.05-kW practical margin.

Simultaneous coverage was defined within separate contrast families. Reference-scale PV hosting used two storage-stratified gains; factorial data-centre hosting used four flexibility gains and four interactions. Fixed-PV operation used ten contrasts across five endpoints and two storage states, and the profile comparison used six profile-by-storage gains. Development and validation families were separate. These family sizes, 2, 8, 10 and 6, are recorded in the corresponding Source Data contrast files; they do not provide joint coverage across all renewable analyses.

Repeated-event episodes contained four calls of 4 or 8 h with recovery gaps of 2, 4, 8, 12 or 24 h. Requested capacities came from development and remained fixed in validation. Every event was paired with a fresh event under the same scenario and clock time, with previous calls removed. Residual delivery divided repeated-event delivery by that matched fresh-event value. Joint success required all four events and episode-level service criteria to pass. Each complete episode was one independent unit; its constituent events were not independent replicates.

### 7. Paired economic ledger and participation mechanisms

The economic analysis priced an offer that had already passed technical qualification. It used the full q = 0.95 certified capacity at zero notice for H = 2, 4 and 8 h. An operator could offer \(K_{\mathrm{cert}}\) or zero; the offer set \(\{0,K_{\mathrm{cert}}\}\) did not include uncertified fractions. Before replay, we checked the certificate, controller, calibration, scenario and source-code records. Monetary inputs were kept outside the physical-ledger hash contract, so changing a price did not change the underlying paired trajectories.

Each validation scenario was replayed with and without demand response under the certificate-pinned runtime. Hourly joins required matching scenario identity, exogenous inputs and baseline PCC power within 10<sup>−8</sup> kW. The same no-response trajectory could be reused within its scenario–duration group. Raw reduction and interval-capped contractual delivery were stored separately; only capped delivery entered performance revenue and shortfall penalties.

Costs were followed until episode termination so that delayed work and its later energy use remained in the accounts. The operational recovery diagnostic ended 24 h after the event. The economic ledger instead ran from event start through the 48-h clearance tail after the seven-day main horizon. Only these through-episode totals entered delay, missed-work, terminal-backlog and energy costs. Work unfinished at recovery stop could still be completed later, and its catch-up energy could offset an apparent early saving.

Three quantities describe different aspects of postponement. Event-deferred work was \(D_{\mathrm{defer}}=\sum_{t\in\mathcal E}[X_t^0-X_t^{\mathrm{DR}}]_+\), where X is executed flexible work in GPU-h and \([z]_+=\max(z,0)\). This sums the positive execution shortfall during the event.

Delay exposure was the accumulated positive excess backlog, \(A=\sum_{t\in\mathcal L}[B_t^{\mathrm{DR}}-B_t^0]_+\Delta t\). Backlog B has units GPU-h, and the ledger window \(\mathcal L\) extends from event start to episode end. A therefore has units GPU-h² and records both the amount of waiting work and how long it waits.

Event-end backlog debt is a single state difference at the final event interval. It is neither the accumulated execution shortfall nor the area under the backlog curve. Annual D and A were obtained by summing sampled event quantities before applying their respective prices.

The three participation mechanisms differ in how the operator makes computing resources available. Slack-backed response uses natural scheduling slack and carries no reserve or displacement charge. Reserved headroom annualises capital assigned to abstract PCC-side offered kilowatts. Throughput displacement values deferred GPU-hours at \(v_{\mathrm{eff}}=\alpha v_{\mathrm{GPUh}}\), where alpha is the assumed fraction exposed to displaced contribution.

The displacement coefficient prices possible lost contribution, while the backlog-area coefficient prices waiting. A value that already includes delay should not incur the delay charge again. For the same work, positive opportunity exposure was not combined with reserve capital or missed/terminal-work pricing. These accounting separations prevent charging twice for the same assumed burden.

Site enablement combined a fixed annual charge and a variable offered-capacity charge,

\[
C_{\mathrm{enable}}(K)=\mathbf 1[K>0]C_{\mathrm{fixed,site}}+c_{\mathrm{variable}}K.
\]

The reference fixed charge was US$25,000 per year and variable cost was zero. Proportional accounting scaled the 201.001-kW reference module to 0.2, 1, 5 and 20 MW. Offered capacity and physical quantities used the same multiplier, while site cost was applied once. This assumed identical modules scaling linearly without diversification. It did not determine hardware counts, topology, workload diversity or a new technical certificate for the larger facility.

Annual net value combined capacity and capped-performance revenue with energy and declared flexible-connection value, then subtracted the specified participation costs. These costs included enablement, reserve, opportunity, delay, service-level-agreement (SLA), checkpoint and non-performance terms. The mean break-even payment set expected net value to zero. The risk-adjusted payment instead set the fifth percentile of 200 scenario-bootstrap annual net-value draws to zero; it was a decision rule, not a confidence bound.

The reference case assumed 50 independent fresh events per year and US$50 per MWh of performance compensation. Counts of 1 and 12 tested lower exposure, whereas 100 and 250 were stress coordinates. Each sampled call began as a fresh event. The annualisation therefore did not simulate queues or compute debt carried between calls.

The table specifies the reference coordinate used in Figure 6 and Supplementary Tables 7–9 before changing a declared sensitivity axis. Currency values are real-2026 US$ and are illustrative research inputs. With K in offered PCC kW, reserve investment was \(I=fKc_R\) and its annual charge was \(C_{\mathrm{reserve}}=I\{[1-s/(1+r)^n]\mathrm{CRF}(r,n)+m\}\). Here, \(\mathrm{CRF}(r,n)=r(1+r)^n/[(1+r)^n-1]\), and m is the annual O&M fraction of initial investment. Displacement and delay charges were \(C_{\mathrm{opportunity}}=\alpha vD\) and \(C_{\mathrm{delay}}=dA\). No whole-fleet depreciation was charged.

| Ledger term | Reference coefficient and unit | Application |
|---|---|---|
| Capacity revenue | Payment per offered kW-year solved at break-even | All modes; revenue is payment × K |
| Performance revenue | 50 US$/MWh | All modes; interval-capped delivered kWh × 50/1000 |
| Energy value | 0.10 US$/kWh | All modes; negative paired incremental kWh × price, through episode end |
| Enablement | 25,000 US$/site-year; variable charge 0 US$/offered kW-year | All modes; fixed charge once per participating site |
| Reserve investment | f = 0.15; c_R = 2,500 US$/abstract reserved PCC kW | Reserved headroom only; f = 0 in other modes |
| Reserve annualisation | n = 4 years; r = 0.08; s = 0.10; m = 0.03/year | Capital recovery net of discounted salvage, plus O&M |
| Displaced contribution | alpha = 0.50; v = 0.50 US$/GPU-h; effective value 0.25 US$/GPU-h | Throughput displacement only; alpha = 0 in other modes |
| Delay | d = 0.005 US$/(GPU-h²) | All modes; price the positive paired backlog area |
| Non-performance | 100 US$/MWh shortfall; 0 US$/failed event | All modes; shortfall is requested minus capped delivered energy |
| Other reference terms | Connection value 0 US$/year; checkpoint 0 US$/event; missed and terminal work prices both 0 US$/GPU-h | Explicit zero assumptions; not evidence that these costs cannot occur |

Inputs are directly recorded in `source_data/nature_economic_v1/fig6_economic_parameter_provenance.csv`, using the delay_cost_grid, economic_lifetime_grid, energy_price_grid, market_payment_grid, opportunity_cost_grid and reserved_cost_grid rows. The configurations `configs/economics/cost_parameter_grid_v1.yaml` and `configs/economics/market_archetypes_v1.yaml` specify mode fractions and penalty coordinates. `source_data/nature_economic_v1/fig6_break_even_decomposition.csv` records the term-by-term outputs. Dividing annual reserve, displacement and delay costs by offered capacity reconstructs the corresponding mean contributions in Note 6; the risk-adjusted threshold instead uses the joint annual net-value quantile.

Capital life varied from three to six years at 8% discount and 10% salvage. Discount and salvage were separately varied around the four-year reference. External evidence was classified as a product observation, a range anchor or context only, with its allowed quantitative use recorded. Accounting life was not treated as physical GPU life, cloud price as contribution margin, server nameplate power as flexible PCC power, or different market payments as one tariff. The evidence register retains these distinctions and the monetary input provenance.

### 8. Cost sensitivity, annual sampling and recovery-throughput mapping

The post-hoc monetary analysis crossed delay and fixed-site multipliers {0, 0.5, 1, 2}. Reference prices were US$0.005 per GPU-hour of backlog per hour of waiting and US$25,000 per site-year. The cross covered three durations, three call counts {1, 12, 50}, three participation modes and four accounting scales, producing 1,728 rows. Other costs, financing, exposures and performance payments stayed fixed within each mode. Zero prices were lower-bound assumptions. This analysis reused the validation ledger and was neither preregistered nor an independent economic validation.

For delay coefficient d, fixed site cost F and accounting offer K, the non-negative capacity-payment threshold was

\[
c^*(d,F)=\max\left\{0,-Q_{0.05}\left[V_{\mathrm{annual}}(c=0;d,F)\right]/K\right\}.
\]

Cost comparisons reused the same annual scenario-index draws within each duration and call count. We took the fifth percentile of total annual net value, rather than summing quantiles of separate cost terms. Before applying the zero floor, increasing site cost by \(\Delta F\) raised the threshold by exactly \(\Delta F/K\). Signed thresholds were retained because flooring can hide that difference. Even when the required capacity payment was zero, the assumed US$50/MWh performance payment remained available.

The original 200 draws were retained to reconcile all nine published reference thresholds. Nested 2,000- and 10,000-draw sets used the same seed and included those original draws, at 50 calls and the 1-MW scale. They tested Monte Carlo sensitivity, not additional physical scenarios, uncertain prices or confidence-interval coverage. Incremental missed and terminal work were separately checked against 10<sup>−6</sup> GPU-h. Supplementary Tables 7–9 and source_data/nature_economic_robustness_v1 contain the resulting costs, reconciliation and service diagnostics.

A separate recovery diagnostic converted positive paired backlog at the final event interval into the throughput required for a declared recovery time G and efficiency eta,

\[
n_{\mathrm{GPU,eq}}=\frac{\max(B^{\mathrm{control}}_{H-1}-B^{\mathrm{noDR}}_{H-1},0)}{G\eta}.
\]

The mapping used debt quantiles 0.50 and 0.95, G = {2, 4, 8, 12, 24} h and eta = {0.70, 0.85, 1.00}. GPU equivalents were rounded upward to complete four-GPU nodes. Installed and recovery-dynamic power used measured board power, 150/300/450-W node overhead and PUE 1.2. The output was equivalent concurrent recovery throughput. It neither identified dedicated reserve nor assigned purchase cost or cross-generation performance.

### 9. Sensitivity design and implementation checks

Sensitivity checks were organised by the uncertainty they addressed. Technical tests used 100 paired development seeds to vary hardware power, workload utilisation, deadline slack, delivery criteria, PUE and node overhead. Every workload case first had to pass the no-response service check. The zero-miss renewable replication used development and validation scenarios, while monetary tests reused the economic validation ledger. These were selected ranges and combinations, not a global analysis of all parameters changing together. Neither extension reopened a locked set.

The post-hoc share experiment separated work eligibility from hardware allocation while keeping the computing installation and total work fixed. It reused 100 development and 100 validation parent scenarios. Deferrable-work shares were f = {0.10, 0.20, 0.30, 0.40, 0.50, 0.60}, and flexible GPU shares were g = {0.10, 0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90}. The primary grid thus contained 54 configurations; retaining earlier curves gave 64 distinct configurations overall. Neither locked set was reopened.

Total hardware remained 576 GPUs, and main-horizon work averaged 374.4 GPU-h/h, half training and half offline inference. Training eligibility was min(2f, 1), and inference eligibility was max(2f − 1, 0). This specified a training-first eligibility path, rather than a universal ordering of workload flexibility. Divisible work was scaled within class while retaining releases and deadlines; zero-work records were omitted. At fixed f, full arrival records were identical across GPU allocations. Community/PV trajectories and event anchors remained paired throughout the grid.

A configuration had to support ordinary computing service before its response capacity could be compared. In the primary grid, 22 configurations overloaded the separate rigid pool and required no simulation. Nine constructible configurations failed all 200 baseline checks, and 23 passed all 200. Failed configurations received no reported response capacity; Supplementary Table 13 distinguishes these missing values from zero.

Including retained earlier configurations gave 42 constructible cases, 8,400 condition–scenario baseline records and 32 service-feasible cases. Nine constructible primary configurations reused existing results and 23 were newly simulated. These counts document which comparisons the fixed-pool model permits. They do not estimate failure prevalence across data centres.

Changing GPU allocation redistributed a fixed hardware pool. The flexible pool contained round(576g) GPUs, and rigid utilisation was 374.4(1 − f)/[576 − round(576g)]. The flexible arrival scaling coefficient remained 0.65. Mean eligible work was therefore 374.4f GPU-h/h, while actual flexible-pool utilisation was 374.4f/round(576g). These workload and hardware quantities differ from the nominal 50% power comparator.

Integer GPU allocation also slightly changed the reference power accounting. Enforcing exact work conservation adjusted rigid utilisation from 0.40625 to 93.6/230 = 0.4069565 and operating peak from 201.00078 to 201.05657 kW. The original figure data were retained. The experiment fixed main-horizon work totals, rather than the total load in every hour. Rigid demand kept the model's constant-power representation during both the main horizon and the clearance tail.

Passing the baseline check over a finite episode did not by itself establish sustainable continuous operation. The gate applied the original deadline, terminal-backlog and PCC limits to all 200 episodes per configuration. At f = 0.50 and g = 0.30, mean flexible work was 187.2 GPU-h/h against 173 GPUs. At least 2,385.6 GPU-h of seven-day work therefore had to be processed during the clearance tail.

The earlier f = 0.95, g = 0.60 configuration similarly required at least 1,626.24 GPU-h beyond the main horizon. Both configurations are labelled as mean-overload stress cases. By contrast, the earlier f = 0.75, g = 0.40 configuration failed all 200 baseline checks, with a maximum deadline-miss rate of 6.95%.

For the 32 service-feasible configurations, PI calculations covered H = {1, 2, 3, 4, 6, 8} h in validation and H = {4, 8} h in development. All 25,600 scenario–duration solves were optimal. Each tolerance lower limit used the second-smallest of 100 optima at q = 0.95 and confidence 0.95. These limits applied pointwise to each configuration and duration, without simultaneous coverage of the entire grid.

We tested mean effects separately from those tolerance limits. One family of 474 Bonferroni 95% t intervals covered 186 contrasts against the original reference, 30 within the fixed-g = 0.40 work curve, 102 allocation comparisons at fixed work, 90 adjacent-work comparisons at fixed allocation and 66 adjacent-grid interactions. Duplicate coefficient vectors were counted once; comparisons requiring failed configurations were marked inapplicable.

Each interaction was [C(f_high,g_high) − C(f_low,g_high)] − [C(f_high,g_low) − C(f_low,g_low)]. Here C is a scenario's PI optimum. We computed the contrast within each paired scenario before averaging, so it measures whether the work-share effect changes with GPU allocation. These are mean scenario effects, not differences between tolerance limits (Supplementary Table 14).

Development tolerance limits fixed 64 requests before 19,200 validation controller runs. The request stayed identical across notices within each configuration and duration. Exact two-sided McNemar tests used Holm correction across 128 notice comparisons. All earlier scenario-level results were retained; multiplicity corrections were recomputed for the expanded families. Source Data preserve every optimum, baseline check, request and outcome. A further 12,800 paired schedule checks verified physical consistency and identical execution before notice.

The profile-only comparison used mixed 3A, 3C and 5A archetypes with 75% residential and 25% small-office demand, each scaled to an 800-kW peak. Jobs, deadlines, hardware, events and random streams remained paired. A preliminary three-seed check per profile gave zero misses and terminal backlog in all nine runs. The formal comparison froze 100 scenarios per profile and verified matching arrival hashes, event signatures and power-model hashes. It evaluated the PI duration surface, fixed 4- and 8-h controller candidates, and 1,200 renewable programmes. The profiles were modelled archetypes, not measured sites or a geographic sample.

Implementation tests checked the physical and information rules listed below. They establish consistency with Model A, rather than completeness as a production data-centre model. Supplementary Table 3 links the principal source artifacts to the reported results.

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

The repeated-event design assigned a distinct scenario hash to each duration–gap schedule within an episode seed. Replaying all 1,000 validation programmes resumed every checkpoint without recomputation and produced byte-identical aggregates. Renewable validation likewise resumed all 100 checkpoints with unchanged aggregates. These checks demonstrate deterministic reconstruction, not robustness to model uncertainty.

The reusable environment retained the firm_threshold_v2 reward, combining threshold-normalised delivery, service, rebound, backlog and switching penalties. It did not define any mainline planning result, and the fixed controller was not trained on it. DQN, PPO and SAC comparisons were outside the paper. Model A also excluded non-pre-emptive execution, gang placement, checkpoint latency, thermal control and cross-generation GPU extrapolation. Adding these mechanisms would require a new model, validation and locked scenarios rather than reinterpreting existing certificates.

### 10. Repeated-capacity extension and external timing stress

The extension was specified after the original manuscript analyses and was not part of their preregistration. The existing controller, calibration and certificates were retained. Development and confirmation used disjoint new seed ranges, 900,000–900,099 and 910,000–910,299, with the original development and validation community partitions respectively. Within a seed, all duration–gap programmes shared identical jobs, community values and no-response baseline values. Four event starts were 63 + j(H + G), j = 0, 1, 2, 3; H was 4 or 8 h and G was 2, 4, 8, 12 or 24 h. The development search tested five fractions without assuming success was monotone in the request. A candidate needed a one-sided 95% Wilson lower bound of at least 0.95 before selection. Its separate confirmation used the same criterion. The complete four-call episode, not an event or a replay, was the independent unit.

Original-offer repeated cases were paired with fresh calls at identical scenario seeds and clock times, with all other calls removed. Identical fresh clock-time counterfactuals were reused across programmes, yielding 8,100 distinct fresh replays in confirmation. Alongside 5,700 repeated replays, this gave 13,800 confirmation runs on 300 scenario seeds. Development contained 5,000 repeated replays on 100 seeds. These run counts do not increase the number of independent seeds. Paired confidence intervals used 2,000 bootstrap resamples of complete seed clusters. The bootstrap described the repeated-minus-fresh contrast; pointwise Wilson bounds determined qualification.

For prediction, contract cells combined duration, gap, offer fraction and event position. A logistic regression used one-hot encoded cells, L2 regularisation with C = 1, the lbfgs solver and at most 4,000 iterations. Two prespecified additions were baseline-subtracted pre-event queue energy, followed by deadline pressure and event-due fraction. Continuous predictors were standardised on development data only. Deadline pressure was the maximum cumulative queued work due within t hours divided by t times hourly flexible capacity, over t = 1,…,48. Event-due fraction was the share of queued work due within H hours. Models were fitted to 20,000 development event rows and scored on 12,000 original-offer confirmation rows. The binary target combined mean/interval delivery, rebound and window-relief failure; episode-global missed-work and terminal criteria were excluded to avoid assigning later episode failures to earlier decisions. Recovery windows could still overlap later calls, so local predictions concerned the declared programme rather than an isolated decision. The primary predictive comparison was the Brier-loss change for the full state model against contract cells alone, using 2,000 seed-cluster resamples with fitted predictions held fixed.

Production timing came from the release timestamps of the local Alibaba 2020 batch-job table (714,903 records), not the timestamp-free 2026 sampler. Hourly job counts from trace hours 168–1511 formed eight disjoint weeks; the initial week was excluded as a trace-start warm-up before controller outcomes were examined. Each count profile was normalised to mean one and used to rescale synthetic hourly flexible work while retaining the original class mix and synthetic deadline assignments. Ten seeds per week were 920,000 + 100w + r, w = 0,…,7 and r = 0,…,9. The configured template seed range mapped synthetic job generation to seeds 20,000–20,009, reusing the same ten job templates across weeks; the new seed identifiers governed frozen community selection and permutation. A paired permutation moved complete hourly job blocks using seed + 700,000, preserving weekly work and its hourly marginal distribution. Both durations used an eight-hour gap, at the original and selected quarter-sized offers, with same-clock fresh controls at the original offer. There were 1,920 controller replays across the 160 week–replicate–ordering scenarios. These are timing stresses, not original-job, production-SLA or measured-power replays. Results were reported by week and as descriptive paired counts, without treating ten realisations of one week as independent observed weeks.

The horizon sensitivity was triggered by development failures and specified before confirmation outcomes were inspected. It extended new arrivals to hour 215, followed by the same 48-h clearance tail. Original arrivals through hour 167 and all available original community observations were copied or checked for equality. Only the added arrivals came from the continuation of a synthetic nine-day template at the same seed. At 25% and 100% of the eight-hour offer with a twenty-four-hour gap, all 300 confirmation seeds were evaluated without reselection. The 25% seven-day comparator required 300 additional replays; the original-offer comparators reused confirmation results. A denominator check divided total missed work by the original seven-day offered work. The quarter-offer controlled trajectories were identical through all four calls. This intervention tests the arrival cutoff and associated recovery conditions, not year-round operation.

Complete-series economics used the 300 confirmation trajectories for each of the nine qualified selected offers, including failed episodes. Each hourly record contributed once. Delay, incremental energy, capped delivery, missed work and terminal backlog were retained separately, then converted to the declared prices. Annual draws sampled one or twelve entire series, with 2,000 draws and the site charge applied once after proportional scaling. The same draws were reused for lost-work prices of US$0, 0.25 and 1 per GPU-h. Unpriced contract-specific failure penalties, real procurement costs and hardware-recovery overhead remained outside this screen. Direct plotting tables retain episode rows and parameter values. Original execution files and hashes were preserved; a separate audit corrected a reporting-only baseline flag to compare no-response power with the physical PCC rating rather than the event contract limit.

## Supplementary Figures

### Supplementary Figure 1 | AIDRBench environment and evidence flow

![Supplementary Figure 1](../docs/figures/nature_supplementary_v1/supplementary_figure_1.png)

**Supplementary Fig. 1 | AIDRBench environment and evidence flow.** **a,** Community load and photovoltaic generation, the Alibaba 2026 job sampler, the declared demand-response event and the four-GPU calibration artifact are bound into a hash-identified hourly scenario. Released work enters deadline queues; the controller supplies an aggregate execution fraction; class-aware execution determines data-centre power and community point-of-common-coupling metrics. **b,** Evidence proceeds from the nominal proxy through perfect-information and restricted non-anticipative boundaries to the frozen causal robust model-predictive controller and independent locked testing. The resulting analyses quantify firm capacity, repeated-event compute debt, renewable hosting and the transfer boundary. Battery energy storage appears only in the renewable-planning branch and is not a hidden actuator in the demand-response certificate.

### Supplementary Figure 2 | Four-GPU power calibration

![Supplementary Figure 2](../docs/figures/nature_supplementary_v1/supplementary_figure_2.png)

**Supplementary Fig. 2 | Four-GPU board-power calibration.** **a,** Per-GPU means from one- and four-GPU training and offline-inference measurements. Filled points denote calibration repeats 1–2 and open points denote held-out repeat 3; short horizontal marks show within-run means for every measurement condition. GPUs within a run are repeated observations and are not treated as independent replicates. **b,** Nominal active board power per GPU and 95% Student-*t* intervals derived from independent four-GPU run means (*n* = 2 runs per workload class). The held-out mean absolute error was 3.80 W per GPU. The four devices communicated through PCI Express without NVLink. The 300-W node overhead is an engineering assumption tested separately and is not inferred from board-power telemetry.

### Supplementary Figure 3 | Normalised observation and information timing

![Supplementary Figure 3](../docs/figures/nature_supplementary_v1/supplementary_figure_3.png)

**Supplementary Fig. 3 | Normalised observation and causal information timing.** **a,** Allocation of the fixed 63-dimensional `firm_v5` policy interface across time, current power and request, workload-service state, history, previous-action and forecast groups. All policy features are bounded by the declared observation space before control. **b,** The demand-response request becomes visible only at its declared notice time. Current arrivals, queues, power and event state enter the policy observation; the six-hour forecast contains community conditions and available-flexibility envelopes, while future workload arrivals remain hidden. Class queues, compute debt, full outcomes and provenance are retained for audit but do not provide the causal controller with future information.

### Supplementary Figure 4 | Representative frozen episode transition

![Supplementary Figure 4](../docs/figures/nature_supplementary_v1/supplementary_figure_4.png)

**Supplementary Fig. 4 | Representative transition under the frozen causal controller.** A deterministic rule selected the minimum episode seed from the non-locked validation set (seed 20,000; scenario SHA-256 prefix `c53ae573b0`), rather than selecting an episode by outcome. The frozen robust model-predictive controller was replayed at the validation-selected 39.65-kW candidate for a four-hour event with zero-hour notice. **a,** Released and executed flexible work. **b,** Aggregate execution fraction. **c,** No-demand-response and controlled point-of-common-coupling power together with the event-dependent limit. **d,** Backlog and compute debt. Shading marks the event interval. This descriptive trajectory had a minimum interval delivery ratio of 0.971, zero deadline-missed work, zero terminal backlog and a maximum event-rebound ratio of 0.112; certification uses the full independent episode ensemble rather than this example.

### Supplementary Figure 5 | Community-profile sensitivity

![Supplementary Figure 5](../docs/figures/web_gpt_v1/AIDRBench_Figure_S5.png)

**Supplementary Fig. 5 | Capacity and system value across the tested community profiles.** **a,** The earliest 168 chronological hours of net demand for each EULP climate-zone archetype (3A, 3C and 5A), without smoothing. **b,** PI tolerance lower bounds at q = 0.95 across six durations, using 100 paired development scenarios per zone. The 5- and 7-h durations were not evaluated and are not interpolated. **c,** Development replay of fixed validation-selected controller candidates at 4 and 8 h, with 100 independent episodes per zone and duration. Filled markers show empirical success fractions; open markers show one-sided 95% Wilson lower bounds. **d,** PV-hosting capacity feasible across all 100 scenarios under rigid or flexible scheduling, with or without BESS. Jobs, hardware, events and seeds are paired across profiles. Panels b and c are non-locked development diagnostics; panel d is a PI planning result. The three profiles represent modelled archetypes, so their agreement in capacity does not establish invariance across all communities. Source data are provided as a Source Data file.

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
| Deadline observation/reporting labels | 0, 1, 2, 3, 6, 12, 24, 48 h |
| Event durations / notices | 1, 2, 3, 4, 6, 8 h / 0, 2, 6 h |
| Recovery window | 24 h |

### Supplementary Table 3 | Provenance and release artifacts

| Artifact | Frozen identifier |
|---|---|
| Model A freeze commit | `d03b44090b2c7ca6a5ae73bb2eb7a611f36a71e9` |
| Model A environment YAML | `c48e70b46f82da4eed80e58b040aa95091dbc03497456745b1c370817bd032e5` |
| Community processed data | `daa513e8a6597232c47c5c0554fcf6723e59e785c3fe3c85c058ae54c6f235f0` |
| Workload sampler | `67e5cc0878e246e9de547cc838c6b0e3df5a25fcd52f043624235873ca2a0d66` |
| Calibration artifact payload | `ef1e474a95b7139f6fd25b4deb733a81dfa0616c8245e101fcc62f437ffc5193` |
| Robust-MPC YAML | `73041f55b7ac4aab0a1f6fa799cfa94f0a8c71d6e6bb3a7f39eadda212839dcf` |
| Robust-MPC normalised specification | `ba530b8a622e5d621e6d005369a07db9db7a9e2e5cbf9aff4e73209d828abf02` |
| Locked-ID ordered scenario-hash list | `e66a22ccac87bb36fe772b075a091f829dfacb30223a4632bf6479835797aa72` |
| Locked-OOD ordered scenario-hash list | `81c04e622ac4f44232d662dbf3a6e8b3245bbb727c4d133274897a0f159ce3a9` |
| Renewable-integration protocol | `8e4d290cc4a7c36e11a7ef4bf46746c8622038172bb08e51ced81cf45c843e11` |
| Submission release / software archive | [TO BE ADDED: immutable release commit, environment lock hash and DOI] |

Hashes are SHA-256 unless the row is explicitly identified as a Git commit. The final release row must be completed after manuscript, source data and code have been frozen together.

### Supplementary Table 4 | Locked-ID causal certificate by reliability and duration

Capacities and outcomes were identical across N = 0, 2 and 6 h within each duration; each row therefore represents three predeclared notice cells. Certification used a one-sided 95% Wilson lower bound from 500 independent locked-ID episodes.

| q | H (h) | Fixed capacity (kW) | Successes / 500 | Wilson lower bound | Certified at every notice |
|---:|---:|---:|---:|---:|---|
| 0.90 | 1 | 60.261 | 454 | 0.884 | no |
| 0.90 | 2 | 50.839 | 473 | 0.927 | yes |
| 0.90 | 3 | 44.950 | 477 | 0.936 | yes |
| 0.90 | 4 | 44.165 | 462 | 0.902 | yes |
| 0.90 | 6 | 39.847 | 473 | 0.927 | yes |
| 0.90 | 8 | 39.847 | 465 | 0.909 | yes |
| 0.95 | 1 | 55.157 | 477 | 0.936 | no |
| 0.95 | 2 | 45.736 | 491 | 0.969 | yes |
| 0.95 | 3 | 39.651 | 497 | 0.985 | yes |
| 0.95 | 4 | 39.651 | 492 | 0.972 | yes |
| 0.95 | 6 | 37.884 | 489 | 0.964 | yes |
| 0.95 | 8 | 36.706 | 492 | 0.972 | yes |
| 0.99 | 1 | 49.072 | 493 | 0.974 | no |
| 0.99 | 2 | 39.258 | 497 | 0.985 | no |
| 0.99 | 3 | 34.351 | 499 | 0.991 | yes |
| 0.99 | 4 | 34.351 | 498 | 0.988 | no |
| 0.99 | 6 | 32.977 | 499 | 0.991 | yes |
| 0.99 | 8 | 32.977 | 499 | 0.991 | yes |

### Supplementary Table 5 | Locked-OOD replay of q = 0.95 candidates

The joint OOD shift replaced `eulp_mixed_3a`/non-homogeneous-Poisson inputs with `eulp_mixed_3c`/block arrivals. Fixed-candidate outcomes were identical across the three notice values within duration. No OOD capacity reselection was permitted.

| H (h) | Fixed capacity (kW) | Successes / 500 | Wilson lower bound | q = 0.95 certified |
|---:|---:|---:|---:|---|
| 1 | 55.157 | 437 | 0.848 | no |
| 2 | 45.736 | 433 | 0.839 | no |
| 3 | 39.651 | 445 | 0.865 | no |
| 4 | 39.651 | 425 | 0.822 | no |
| 6 | 37.884 | 398 | 0.765 | no |
| 8 | 36.706 | 383 | 0.733 | no |

### Supplementary Table 6 | Validation 2 × 2 × 2 data-centre hosting capacities and paired AI-flexibility effects

Simultaneous feasible data-centre capacity is the minimum scenario-feasible maximum over 100 frozen validation scenarios. Paired effects are means of within-scenario flexible-minus-rigid differences with Bonferroni 95% simultaneous intervals.

| PV | BESS | Rigid capacity (kW) | Flexible capacity (kW) | Paired AI effect (kW) | Simultaneous 95% interval (kW) |
|---|---|---:|---:|---:|---:|
| absent | absent | 361.44 | 668.33 | 326.02 | 319.33–332.81 |
| absent | present | 418.64 | 685.84 | 273.71 | 267.33–280.04 |
| present | absent | 460.58 | 869.53 | 370.61 | 362.74–378.28 |
| present | present | 556.03 | 875.10 | 282.07 | 273.84–290.47 |

The AI×BESS interactions were −52.31 kW without PV and −88.54 kW with PV. The AI×PV interactions were +44.59 kW without BESS and +8.36 kW with BESS. The last interval was positive but crossed the predeclared 10.05-kW practical-effect threshold and was therefore not labelled practically complementary.

### Supplementary Table 7 | Delay-price sensitivity of economic participation

Values are risk-adjusted non-negative break-even capacity payments in real-2026 US$ kW<sup>−1</sup> year<sup>−1</sup>. All rows use H = 4 h, 50 independent fresh calls per year, a 1-MW proportional accounting scale, US$25,000/year fixed site cost, US$50/MWh performance payment and 200 common annual draws. Delay prices are US$ per GPU-hour of backlog per hour of waiting. Other inputs remain at the original reference coordinate within each mechanism. These are post-hoc cost sensitivities, not observed operator prices.

| Participation mechanism | Delay price 0 | Delay price 0.0025 | Delay price 0.005 (reference) | Delay price 0.010 |
|---|---:|---:|---:|---:|
| Slack-backed | 117.04 | 181.80 | 246.60 | 376.19 |
| Reserved headroom | 233.19 | 297.95 | 362.75 | 492.34 |
| Throughput-displacing exposure | 287.50 | 350.27 | 414.99 | 544.55 |

Source Data: `source_data/nature_economic_robustness_v1/economic_cost_sensitivity.csv`.

### Supplementary Table 8 | Crossed delay and fixed-site costs for slack-backed participation

Threshold units and fixed operational coordinates are as in Supplementary Table 7. Annual fixed site cost is applied once, not once per reference module. A zero capacity-payment threshold retains performance compensation and the other declared lower-bound assumptions; it is not a zero-cost or zero-revenue claim.

| Annual fixed site cost (US$) | Delay price 0 | Delay price 0.0025 | Delay price 0.005 | Delay price 0.010 |
|---:|---:|---:|---:|---:|
| 0 | 0.00 | 55.07 | 119.87 | 249.46 |
| 12,500 | 53.68 | 118.44 | 183.23 | 312.82 |
| 25,000 | 117.04 | 181.80 | 246.60 | 376.19 |
| 50,000 | 243.78 | 308.54 | 373.33 | 502.92 |

Source Data: `source_data/nature_economic_robustness_v1/economic_cost_sensitivity.csv`. Signed pre-floor thresholds are retained in the same file for exact cost-contrast checks.

### Supplementary Table 9 | Numerical sensitivity to the number of annual draws

Values are risk-adjusted break-even capacity payments in real-2026 US$ kW<sup>−1</sup> year<sup>−1</sup> at the original costs, 50 fresh calls/year and the 1-MW accounting scale. The larger draw sets include the original 200 draws from the same seed. The 200-draw column reproduces Figure 6 and is not replaced after inspecting this diagnostic. This is a Monte Carlo sensitivity check, not an independent economic validation or a parameter-uncertainty interval.

| H (h) | Participation mechanism | 200 draws | 2,000 draws | 10,000 draws |
|---:|---|---:|---:|---:|
| 2 | Slack-backed | 164.67 | 164.66 | 164.53 |
| 2 | Reserved headroom | 280.82 | 280.81 | 280.68 |
| 2 | Throughput-displacing exposure | 247.77 | 247.69 | 247.55 |
| 4 | Slack-backed | 246.60 | 246.82 | 246.69 |
| 4 | Reserved headroom | 362.75 | 362.96 | 362.83 |
| 4 | Throughput-displacing exposure | 414.99 | 415.23 | 414.98 |
| 8 | Slack-backed | 437.21 | 440.53 | 439.70 |
| 8 | Reserved headroom | 553.36 | 556.68 | 555.85 |
| 8 | Throughput-displacing exposure | 774.37 | 777.65 | 776.77 |

Source Data: `source_data/nature_economic_robustness_v1/economic_bootstrap_stability.csv`. The reference reconciliation and incremental-service diagnostics are supplied separately in the same directory.

### Supplementary Table 10 | Deferrable-work share at fixed GPU allocation

This table varies the amount of deferrable work while holding GPU allocation fixed within each group. The first six rows use 40% flexible GPUs and cover 10–60% deferrable work. The remaining rows use the original 60% GPU allocation and retain all higher work fractions. Total GPUs and main-horizon work stay fixed. Flexible-pool utilisation is mean eligible work divided by flexible capacity.

Capacity entries are validation PI tolerance lower bounds at q = 0.95 and confidence 0.95, using 100 paired scenarios each. At 60% GPU allocation, 10–30% deferrable work overloads the separate rigid pool; dashes mark structural infeasibility without simulation. The 95%-work row instead overloads the flexible pool on average and depends on the clearance tail. These entries are planning evidence, not controller certificates. Source Data contain all six durations and individual scenarios.

| Deferrable work (%) | Flexible GPUs (%) | Flexible utilisation (%) | 1 h (kW) | 4 h (kW) | 8 h (kW) |
|---:|---:|---:|---:|---:|---:|
| 10 | 40 | 16.28 | 6.30 | 4.54 | 4.54 |
| 20 | 40 | 32.56 | 12.61 | 9.09 | 9.09 |
| 30 | 40 | 48.83 | 18.91 | 13.63 | 13.63 |
| 40 | 40 | 65.11 | 25.22 | 18.17 | 18.17 |
| 50 | 40 | 81.39 | 31.52 | 22.71 | 22.71 |
| 60 | 40 | 97.67 | 49.89 | 36.36 | 35.97 |
| 10 | 60 | 10.82 | — | — | — |
| 20 | 60 | 21.64 | — | — | — |
| 30 | 60 | 32.46 | — | — | — |
| 40 | 60 | 43.28 | 25.22 | 18.17 | 18.17 |
| 50 | 60 | 54.10 | 31.52 | 22.71 | 22.71 |
| 60 | 60 | 64.92 | 38.88 | 28.01 | 28.01 |
| 70 | 60 | 75.75 | 46.24 | 33.32 | 33.32 |
| 75 | 60 | 81.16 | 49.92 | 35.97 | 35.97 |
| 80 | 60 | 86.57 | 57.80 | 42.34 | 40.56 |
| 90 | 60 | 97.39 | 78.21 | 57.00 | 54.56 |
| 95 | 60 | 102.80 | 111.80 | 110.23 | 110.23 |

### Supplementary Table 11 | GPU allocation at fixed deferrable work

Deferrable work remained 75% of total main-horizon GPU-hours. PI entries use the same validation tolerance-limit definition as Supplementary Table 10. The 40% allocation failed the baseline gate and is retained as a failed configuration; dashes are unreported capacities, not zeros. A change in pool size also changes the no-response queue and the event-time baseline load. The 60% row is the common reference, not an additional independent experiment.

| Flexible GPUs (%) | No-response feasible (of 200) | Flexible-pool utilisation (%) | 4 h (kW) | 8 h (kW) |
|---:|---:|---:|---:|---:|
| 40 | 0 | 122.09 | — | — |
| 50 | 200 | 97.50 | 46.68 | 46.17 |
| 55 | 200 | 88.58 | 39.90 | 37.77 |
| 60 | 200 | 81.16 | 35.97 | 35.97 |
| 70 | 200 | 69.68 | 35.97 | 35.97 |
| 80 | 200 | 60.91 | 35.97 | 35.97 |

### Supplementary Table 12 | Fixed-request notice tests across work and GPU shares

Each cell reports successful joint delivery-and-service outcomes among 100 validation scenarios. A request was fixed from the corresponding development PI lower bound before notice evaluation and was identical across notices within each row. All three notices had identical paired success classifications. Counts are not maximum causal capacities or new locked certificates; pointwise Wilson bounds and all individual criteria are in Source Data. In particular, the 95%-deferrable condition depended on the finite clearance tail and its large PI-derived requests were poorly delivered by the frozen controller.

| Deferrable work (%) | Flexible GPUs (%) | Duration (h) | Fixed request (kW) | N = 0 h | N = 2 h | N = 6 h |
|---:|---:|---:|---:|---:|---:|---:|
| 10 | 10 | 4 | 5.07 | 96/100 | 96/100 | 96/100 |
| 10 | 10 | 8 | 4.77 | 98/100 | 98/100 | 98/100 |
| 10 | 20 | 4 | 5.07 | 96/100 | 96/100 | 96/100 |
| 10 | 20 | 8 | 4.77 | 98/100 | 98/100 | 98/100 |
| 10 | 30 | 4 | 5.07 | 96/100 | 96/100 | 96/100 |
| 10 | 30 | 8 | 4.77 | 98/100 | 98/100 | 98/100 |
| 10 | 40 | 4 | 5.07 | 96/100 | 96/100 | 96/100 |
| 10 | 40 | 8 | 4.77 | 98/100 | 98/100 | 98/100 |
| 20 | 20 | 4 | 10.14 | 96/100 | 96/100 | 96/100 |
| 20 | 20 | 8 | 9.54 | 98/100 | 98/100 | 98/100 |
| 20 | 30 | 4 | 10.14 | 96/100 | 96/100 | 96/100 |
| 20 | 30 | 8 | 9.54 | 98/100 | 98/100 | 98/100 |
| 20 | 40 | 4 | 10.14 | 96/100 | 96/100 | 96/100 |
| 20 | 40 | 8 | 9.54 | 98/100 | 98/100 | 98/100 |
| 30 | 20 | 4 | 21.64 | 97/100 | 97/100 | 97/100 |
| 30 | 20 | 8 | 16.39 | 99/100 | 99/100 | 99/100 |
| 30 | 30 | 4 | 15.21 | 96/100 | 96/100 | 96/100 |
| 30 | 30 | 8 | 14.31 | 98/100 | 98/100 | 98/100 |
| 30 | 40 | 4 | 15.21 | 96/100 | 96/100 | 96/100 |
| 30 | 40 | 8 | 14.31 | 98/100 | 98/100 | 98/100 |
| 30 | 50 | 4 | 15.21 | 96/100 | 96/100 | 96/100 |
| 30 | 50 | 8 | 14.31 | 98/100 | 98/100 | 98/100 |
| 40 | 30 | 4 | 20.28 | 97/100 | 97/100 | 97/100 |
| 40 | 30 | 8 | 19.08 | 99/100 | 99/100 | 99/100 |
| 40 | 40 | 4 | 20.28 | 96/100 | 96/100 | 96/100 |
| 40 | 40 | 8 | 19.08 | 98/100 | 98/100 | 98/100 |
| 40 | 50 | 4 | 20.28 | 96/100 | 96/100 | 96/100 |
| 40 | 50 | 8 | 19.08 | 98/100 | 98/100 | 98/100 |
| 40 | 60 | 4 | 20.28 | 96/100 | 96/100 | 96/100 |
| 40 | 60 | 8 | 19.08 | 98/100 | 98/100 | 98/100 |
| 50 | 30 | 4 | 50.89 | 100/100 | 100/100 | 100/100 |
| 50 | 30 | 8 | 50.89 | 100/100 | 100/100 | 100/100 |
| 50 | 40 | 4 | 25.35 | 96/100 | 96/100 | 96/100 |
| 50 | 40 | 8 | 23.85 | 98/100 | 98/100 | 98/100 |
| 50 | 50 | 4 | 25.35 | 96/100 | 96/100 | 96/100 |
| 50 | 50 | 8 | 23.85 | 98/100 | 98/100 | 98/100 |
| 50 | 60 | 4 | 25.35 | 96/100 | 96/100 | 96/100 |
| 50 | 60 | 8 | 23.85 | 98/100 | 98/100 | 98/100 |
| 60 | 40 | 4 | 44.49 | 97/100 | 97/100 | 97/100 |
| 60 | 40 | 8 | 33.69 | 99/100 | 99/100 | 99/100 |
| 60 | 50 | 4 | 31.27 | 96/100 | 96/100 | 96/100 |
| 60 | 50 | 8 | 29.41 | 97/100 | 97/100 | 97/100 |
| 60 | 60 | 4 | 31.27 | 95/100 | 95/100 | 95/100 |
| 60 | 60 | 8 | 29.41 | 96/100 | 96/100 | 96/100 |
| 60 | 70 | 4 | 31.27 | 96/100 | 96/100 | 96/100 |
| 60 | 70 | 8 | 29.41 | 97/100 | 97/100 | 97/100 |
| 70 | 60 | 4 | 37.19 | 92/100 | 92/100 | 92/100 |
| 70 | 60 | 8 | 34.98 | 96/100 | 96/100 | 96/100 |
| 75 | 50 | 4 | 57.12 | 97/100 | 97/100 | 97/100 |
| 75 | 50 | 8 | 43.25 | 97/100 | 97/100 | 97/100 |
| 75 | 55 | 4 | 43.01 | 96/100 | 96/100 | 96/100 |
| 75 | 55 | 8 | 37.76 | 98/100 | 98/100 | 98/100 |
| 75 | 60 | 4 | 40.15 | 94/100 | 94/100 | 94/100 |
| 75 | 60 | 8 | 37.76 | 95/100 | 95/100 | 95/100 |
| 75 | 70 | 4 | 40.15 | 93/100 | 93/100 | 93/100 |
| 75 | 70 | 8 | 37.76 | 97/100 | 97/100 | 97/100 |
| 75 | 80 | 4 | 40.15 | 93/100 | 93/100 | 93/100 |
| 75 | 80 | 8 | 37.76 | 96/100 | 96/100 | 96/100 |
| 80 | 60 | 4 | 43.11 | 93/100 | 93/100 | 93/100 |
| 80 | 60 | 8 | 40.54 | 94/100 | 94/100 | 94/100 |
| 90 | 60 | 4 | 69.74 | 96/100 | 96/100 | 96/100 |
| 90 | 60 | 8 | 52.82 | 97/100 | 97/100 | 97/100 |
| 95 | 60 | 4 | 111.22 | 54/100 | 54/100 | 54/100 |
| 95 | 60 | 8 | 110.73 | 42/100 | 42/100 | 42/100 |

### Supplementary Table 13 | Joint work-share and GPU-allocation grid

The two grids locate response capacity within all 54 primary work–GPU configurations. Reported values are validation PI tolerance lower bounds in kW, using 100 paired scenarios at q = 0.95 and confidence 0.95. R means the rigid pool was overloaded before simulation. S means baseline service failed in all 200 development and validation episodes, so no response capacity was reported. A dagger marks average flexible arrivals above pool capacity despite passing the finite-horizon service check.

R and S are missing capacity estimates, not zeros. Their counts describe the chosen configuration grid rather than a population failure probability. All six event durations are available in Source Data.

**4-h event**

| Work / GPU (%) | 10 | 20 | 30 | 40 | 50 | 60 | 70 | 80 | 90 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 10 | 4.54 | 4.54 | 4.54 | 4.54 | R | R | R | R | R |
| 20 | S | 9.09 | 9.09 | 9.09 | R | R | R | R | R |
| 30 | S | 17.69 | 13.63 | 13.63 | 13.63 | R | R | R | R |
| 40 | S | S | 19.92 | 18.17 | 18.17 | 18.17 | R | R | R |
| 50 | S | S | 50.89† | 22.71 | 22.71 | 22.71 | R | R | R |
| 60 | S | S | S | 36.36 | 28.01 | 28.01 | 28.01 | R | R |

**8-h event**

| Work / GPU (%) | 10 | 20 | 30 | 40 | 50 | 60 | 70 | 80 | 90 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 10 | 4.54 | 4.54 | 4.54 | 4.54 | R | R | R | R | R |
| 20 | S | 9.09 | 9.09 | 9.09 | R | R | R | R | R |
| 30 | S | 17.50 | 13.63 | 13.63 | 13.63 | R | R | R | R |
| 40 | S | S | 19.08 | 18.17 | 18.17 | 18.17 | R | R | R |
| 50 | S | S | 50.89† | 22.71 | 22.71 | 22.71 | R | R | R |
| 60 | S | S | S | 35.97 | 28.01 | 28.01 | 28.01 | R | R |

### Supplementary Table 14 | Paired interactions within the joint grid

These interactions ask whether increasing deferrable work has a different effect at neighbouring GPU allocations. All 11 service-eligible adjacent rectangles at H = 4 h are shown. Each estimate is a paired mean difference-in-differences of scenario PI optima, with a Bonferroni 95% t interval based on 100 pairs, 99 degrees of freedom and 474 contrasts. It is not a difference between tolerance lower bounds.

The dagger identifies comparisons including the mean-overload 50%-work, 30%-GPU configuration. Near-zero solver residuals are rounded; a displayed zero does not establish statistical equivalence. Source Data retain interactions at all durations and comparisons marked inapplicable.

| Work range | GPU range | Mean (kW) | Lower (kW) | Upper (kW) |
|---:|---:|---:|---:|---:|
| 10-20% | 20-30% | 0.00 | 0.00 | 0.00 |
| 10-20% | 30-40% | 0.00 | 0.00 | 0.00 |
| 20-30% | 20-30% | -10.51 | -12.35 | -8.67 |
| 20-30% | 30-40% | 0.00 | 0.00 | 0.00 |
| 30-40% | 30-40% | -5.37 | -8.66 | -2.08 |
| 30-40% | 40-50% | 0.00 | 0.00 | 0.00 |
| 40-50%† | 30-40% | -5.19 | -11.90 | 1.52 |
| 40-50% | 40-50% | -2.76 | -5.61 | 0.10 |
| 40-50% | 50-60% | 0.00 | 0.00 | 0.00 |
| 50-60% | 40-50% | -19.80 | -26.39 | -13.21 |
| 50-60% | 50-60% | -1.70 | -3.99 | 0.59 |

### Supplementary Table 15 | Repeated-offer confirmation and matched fresh programmes

| H / gap (h) | Original kW | Repeated success | Fresh all-four success | Selected kW (% original) | Selected success; Wilson lower |
|---|---|---|---|---|---|
| 4 / 2 | 39.65 | 257/300 | 276/300 | 9.91 (25%) | 300/300; 0.9911 |
| 4 / 4 | 39.65 | 280/300 | 285/300 | 9.91 (25%) | 300/300; 0.9911 |
| 4 / 8 | 39.65 | 299/300 | 299/300 | 9.91 (25%) | 300/300; 0.9911 |
| 4 / 12 | 39.65 | 283/300 | 287/300 | 9.91 (25%) | 300/300; 0.9911 |
| 4 / 24 | 39.65 | 258/300 | 285/300 | 29.74 (75%) | 299/300; 0.9852 |
| 8 / 2 | 36.71 | 276/300 | 277/300 | 33.04 (90%) | 296/300; 0.9706 |
| 8 / 4 | 36.71 | 279/300 | 285/300 | 33.04 (90%) | 296/300; 0.9706 |
| 8 / 8 | 36.71 | 223/300 | 280/300 | 9.18 (25%) | 300/300; 0.9911 |
| 8 / 12 | 36.71 | 213/300 | 290/300 | 9.18 (25%) | 300/300; 0.9911 |
| 8 / 24 | 36.71 | 0/300 | 264/300 | — | — |

Every programme used 300 matched confirmation seeds. Fresh all-four success is the conjunction of four isolated counterfactual runs with the same weekly inputs, not one physically reset programme. A dash denotes no positive development selection, not a certified zero offer. Original 4 h/8 h-gap capacity separately passed with a 0.9852 lower bound. Selected offers were not continuous maxima; all bounds are pointwise. Complete development grids, paired intervals and event-state rows are supplied as Source Data.

### Supplementary Table 16 | Held-out local-failure prediction

| Predictors | Brier loss | Log loss | ROC AUC |
|---|---|---|---|
| contract_only | 0.033252 | 0.138317 | 0.7721 |
| plus_queue_energy | 0.033332 | 0.140056 | 0.7573 |
| plus_deadlines | 0.033502 | 0.144310 | 0.7343 |

There were 20,000 training event rows from 100 development seeds (309 local failures) and 12,000 test event rows from 300 confirmation seeds (429 local failures). Lower Brier/log loss and higher AUC indicate better prediction. contract_only used contract cells; plus_queue_energy added baseline-relative queued energy; plus_deadlines additionally included deadline pressure and event-due fraction. The full-model Brier change was +0.000250 (95% paired cluster interval, +0.000150 to +0.000339).

### Supplementary Table 17 | Production-derived arrival ordering at an eight-hour recovery gap

| Ordering | H (h) | Offer fraction | Successes | Success (%) |
|---|---|---|---|---|
| chronological | 4 | 0.25 | 80/80 | 100.00 |
| chronological | 4 | 1.00 | 20/80 | 25.00 |
| chronological | 8 | 0.25 | 80/80 | 100.00 |
| chronological | 8 | 1.00 | 19/80 | 23.75 |
| permuted | 4 | 0.25 | 80/80 | 100.00 |
| permuted | 4 | 1.00 | 52/80 | 65.00 |
| permuted | 8 | 0.25 | 80/80 | 100.00 |
| permuted | 8 | 1.00 | 36/80 | 45.00 |

Each row contains ten model realisations of each of eight observed weeks. All 160 no-response week–replicate–ordering cases passed the physical and service gate. Fractions refer to the previously certified single-event offers, not facility load fractions. No new production-population certificate is inferred from these counts.

### Supplementary Table 18 | Moving the arrival cutoff without changing call times

| Offer (kW) | Seven-day success | Nine-day success | Nine-day, original denominator | Mean missed GPU-h: seven days | Mean missed GPU-h: nine days |
|---|---|---|---|---|---|
| 9.18 | 0/300 | 300/300 | 300/300 | 1395.06 | 0.00 |
| 36.71 | 0/300 | 262/300 | 262/300 | 2914.62 | 13.69 |

All cases used four eight-hour calls separated by twenty-four hours and the same 300 seeds. Both horizons retained a 48-h clearance tail. The original-denominator check used the original seven-day arrived work to calculate the missed-work fraction. At the quarter-sized offer, all controlled dispatch trajectories were identical through hour 167. This is a paired boundary sensitivity, not an offer-selection or annual-operation experiment.

### Supplementary Table 19 | Complete-series participation costs for confirmed selected offers

| H / gap (h) | Reference offer kW | 1-MW accounting offer kW | Sequence successes | Mean delay cost per reference series (US$) | Risk threshold (US$/kW-year) |
|---|---|---|---|---|---|
| 4 / 2 | 9.91 | 49.32 | 300/300 | 296.10 | 868.55 |
| 4 / 4 | 9.91 | 49.32 | 300/300 | 335.36 | 916.07 |
| 4 / 8 | 9.91 | 49.32 | 300/300 | 593.48 | 1233.74 |
| 4 / 12 | 9.91 | 49.32 | 300/300 | 648.02 | 1298.55 |
| 4 / 24 | 29.74 | 147.95 | 299/300 | 1242.40 | 676.78 |
| 8 / 2 | 33.04 | 164.36 | 296/300 | 1653.20 | 742.75 |
| 8 / 4 | 33.04 | 164.36 | 296/300 | 1625.88 | 731.34 |
| 8 / 8 | 9.18 | 45.65 | 300/300 | 871.74 | 1686.08 |
| 8 / 12 | 9.18 | 45.65 | 300/300 | 939.14 | 1767.71 |

The annual screen sampled twelve independent complete four-call series (48 calls) using 2,000 draws. Each series retained its queue history and was accounted once per hour. Prices were US$0.005/GPU-h² for delay, US$0.10/kWh for energy, US$50/MWh for capped delivery and US$25,000/site-year. This table applies zero missed-work price; the 0.25 and 1 US$/GPU-h sensitivities, one-series annual case and all 300 episode ledgers are supplied as Source Data. Failure-event penalties and unmeasured operator costs were not included. These are neither continuous-year simulations nor economically optimal offers.
