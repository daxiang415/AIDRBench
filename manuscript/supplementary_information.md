<!--
Working supplement, version 0.25, 2026-09-10.
Workload weighting, hourly order and commitment decisions. Existing frozen experiments.
Author metadata remain pending.
-->

# Supplementary Information

## Workload timing limits reliable demand response from AI data centres

[AUTHOR NAMES]

## Reader guide

Read the commitment evidence in sequence: independent duration qualification (Table 18), matched workload weights and hourly order (Table 20), strict task-window diagnosis (Table 19), and physical operating exposure and conditional prices (Table 21). The remaining tables provide workload assumptions, structural controls and complete design provenance. Source Data retain frozen inputs, every successful and failed trajectory, direct plotting tables and replay code. Supplementary Note 7 distinguishes the historical designs from the reference products used in the main text.

| Question | Methods | Displays |
|---|---|---|
| Work composition and power | 1–3 | Fig. 1; Supplementary Fig. 2; Tables 1–3 |
| Single-event offers | 4–5 | Fig. 2; Table 4 |
| Reference repeated offers | 6 | Fig. 3a; Supplementary Fig. 3a,b; Table 18 |
| Workload weights and hourly order | 6 | Fig. 3c,d; Fig. 4a,b; Table 20 |
| Supply and strict-window diagnosis | 6 | Fig. 3b; Fig. 4; Table 19 |
| Structural and call-history controls | 6 | Supplementary Fig. 3c; Tables 5, 10–16 |
| PV, allocation and power controls | 7–8 | Fig. 5; Supplementary Fig. 4; Tables 6, 8 |
| Physical exposure and participation | 9 | Fig. 6; Supplementary Fig. 5; Table 21 |
| Price assumptions and design provenance | 9; Note 7 | Tables 7, 9, 12, 17; Supplementary Fig. 3d |

## Supplementary Notes

### 1. Eligibility is an operating permission

The source audit multiplies each released execution span's requested GPU-equivalents by its uncapped duration. It retains development, other and unknown work in the denominator. Counting records would assign 79.45% to offline inference, whereas requested resource time assigns 21.52%; these are different estimands. Low priority identifies a candidate class of work, not a production deadline or permission to postpone service. At 5–20% eligibility, the common permission multiplier preserves the relative contributions of low-priority training and offline inference. The 40% case expands permission beyond that pool, while 60% explicitly changes business composition. None is a measurement of deployed demand-response eligibility.

### 2. Planning and qualification answer different questions

The aggregate PI programme maximised R under cumulative class-release and class-deadline constraints. These are necessary aggregate conditions, but are a relaxation when job windows cross: work executed for an earlier, later-deadline job can satisfy a cumulative due-work inequality for a different job. Its retained optima therefore define relaxed planning envelopes, not generally job-feasible capacities. Their second order statistic among 100 scenarios is a 95%/95% tolerance statistic of that relaxed quantity, with achieved confidence 0.96292.<sup>33</sup> It does not guarantee feasible work scheduling. Controller offers instead use completed queue simulations on independent seeds; their joint delivery-and-service probability is assessed by a one-sided 95% Wilson lower bound, required to reach 0.95.<sup>34,35</sup> The strict-window feasibility diagnostics use each work group’s own release and deadline.

### 3. Service standards and call history must be tested together

Four calls in one evolving queue are not four independent observations. The matched fresh comparison runs each call alone at the same clock time, then asks whether all four isolated calls passed. Both conditions therefore have the same all-four-success endpoint. Their difference estimates the consequence of call history within the specified model and schedule. A development-selected repeated candidate receives its own independent test. If no tested candidate qualifies, this is a search-grid outcome, not evidence that all positive capacities are impossible. Complete hourly series, including failures and clearance after the last call, are retained.

The follow-up distinguishes electrical non-compliance from computing loss. The original observation selected the active window with the smallest achieved peak-relief fraction. That ranking need not select the smallest allowable power ceiling, so clipping only against its ceiling can violate another overlapping window. Keeping a ceiling for each observed call repairs this omission. The same-request paired comparison isolates this change within the MPC implementation; the greedy diagnostic asks whether the gain requires the MPC proposal. Stronger electrical guards can withhold capacity from urgent jobs, so deadline failures are reported separately. Qualified revised offers, rather than failure counts alone, provide the operational result.

The new structural test begins after that repair. Tightened deadlines and low instantaneous eligible power are separate failure mechanisms; a scenario may fail both. Zero total missed work is a stricter endpoint than a 1% allowance and receives its own development selection. In every new same-clock final-call contrast, the electrical outcome was identical with or without preceding calls. This prevents attributing all programme failure to damaged recovery. Chronological and permuted production submissions change temporal structure without changing class totals; neither ordering is asserted to be universally harder.

### 4. PV hosting and utilisation have different denominators

Hosting maximises PV nameplate at the unchanged GPU installation. The reported all-scenario boundary is the minimum of the 100 scenario capacities within each operating mode. Its gain is min(flexible) minus min(rigid), not the minimum or mean of paired differences. Fixed-PV utilisation instead divides locally used PV energy by available generation from a 500-kW installation. Its effect is reported in percentage points with paired bootstrap intervals. All current renewable programmes impose zero missed GPU-hours. They use full future information and a separately optimised dispatch; their benefit is not attributed to the causal demand-response controller.

### 5. Controls separate allocation from eligibility

The primary f-to-f GPU allocation rule maintains similar mean utilisation as eligibility changes. It does not make the five cases a pure one-factor experiment. At fixed 10% eligibility, the allocation controls move the flexible GPU fraction from 10% to 20% and 30%, retaining total work, hardware, releases and deadlines. The power controls retain the same allocation but change only unmeasured rigid-class active power to 150 or 225 W per GPU. Every control is tested at the original 10% configuration's selected requests; offers are not reselected after observing its results. The controls therefore compare planning potential and transfer of a fixed offer, not separately optimised controller capacities.

### 6. Cost thresholds are conditional participation screens

The physical ledger pairs each controlled trajectory with its own no-response baseline. Positive extra backlog accumulates waiting exposure; delayed work during events and permanently missed work remain separate quantities. Each hour is counted once across a repeated programme. Performance revenue credits only non-negative reduction capped at the request. Fixed annual site costs are applied once after proportional accounting at a 1-MW operating peak. A small offer can therefore have a high price per offered kilowatt even when its total delayed work is small. The 95th percentile of annual net cost is a risk-screening choice, not a confidence limit or observed tariff. Unqualified offers remain unqualified even if their conditional cost is low.

The new decomposition confirms that approximately 95% of the reference single-event threshold is a fixed-site allocation. Operating components are attributed at the rank of total net cost so that they add back exactly. A shared fee changes the value relative to opting out, but a common fee cancels between two participating products. Product choice must compare annual net values at stated duration-specific prices, with only independently qualified choices eligible. The figures retain zero/low fees and operating costs separately to expose these different decisions.

### 7. Design provenance and interpretation of superseded comparisons

Tables 14 and 17 retain the structural study’s coarse-grid selections and prices; Tables 18 and 21 report the locally refined reference products on new development and confirmation seeds. At 4.423682 kW, the zero-miss development count was 98/100 in the former study and 99/100 in the latter, crossing the fixed Wilson selection threshold. The resulting historical 4.42-to-2.95-kW selection change is not evidence of a stable physical capacity penalty. Both standards select 5.603331 and 4.423682 kW for the reference four- and eight-hour products in Table 18; their capacity ratio is 19/15, rather than the coarse-grid ratio of 1.5. The eight-hour selection is at the tested grid ceiling and does not bracket a continuous maximum.

The 986000-series chronological submission-count test is distinct from the 990000-series matched weight/order test. In the former, 4.423682 kW succeeds in 63/80 realisations under either service score, and all 17 failures encounter immediate shortage; 2.949122 kW succeeds in 80/80 under both (Supplementary Fig. 3d; Table 16). Thus, changing the score at a fixed request does not explain the difference between those requests. The matched 990000-series results in Table 20 compare weights and hourly order without pooling either series or selecting an external offer. The cumulative PI model retained in Figs. 2 and 5 and Tables 4 and 8 is a relaxation for crossing job windows (Note 2), whereas the strict-window diagnoses in Table 19 use work-group execution edges. This distinction does not alter the independent causal queue trajectories or the separate edge-based PV optimiser.

## Supplementary Methods

### 1. Source audit and permissions

The local jobs_summary.parquet contained 40,522,321 execution-span records. Streaming batches of one million rows were aggregated by workload class and priority, using requested GPU-equivalents times the original duration. The total was 254,980,926.33 requested GPU-h. The audit checked the stored raw work against this product and retained all classes. The source SHA-256 was `95c91a8035197e15f29e9c1d15a9147d07b2a6959b2bb08322cb9f033b029124`. The [production study](https://www.usenix.org/system/files/osdi26-li-suyi.pdf) and [official schema](https://github.com/alibaba/clusterdata/blob/master/cluster-trace-gpu-v2026/docs/schema.md) define the infrastructure scope and execution-span fields. The reported infrastructure excludes dedicated hyperscale foundation-model pretraining clusters.

Let s_c be the source resource-time share and l_c the low-priority batch share of class c, each relative to all offered work. For f ≤ L = Σl_c = 0.2202814, eligible work is l_c f/L. For L < f ≤ B = s_training + s_offline = 0.4094199, it is l_c + (s_c − l_c)(f − L)/(B − L). The 60% case transfers f − B = 0.1905801 from online to offline inference and makes all training and offline inference eligible. Other classes remain in the source denominator and are rigid. Full-precision shares are provided in case_definitions.json; rounding in Table 2 does not drive simulations.

### 2. Paired scenarios and baseline gate

Development used seeds 930000–930099 and confirmation used 960000–960299. Within each seed, a single 60%-case job template supplied the releases, deadlines and class records. Scaling only the class GPU-hours produced the remaining cases; record counts and timing were held identical. The template sampled existing low-priority training/offline job shapes, including for the explicitly hypothetical 40% and 60% cases. Total offered work was 374.4 GPU-h/h for 168 h, followed by 48 h without new arrivals. The flexible GPU count was round(576f), and rigid utilisation was 374.4(1 − f)/(576 − round(576f)). Every no-response scenario had to satisfy service and PCC limits before downstream analysis.

Training deadlines were 2–6 times runtime, clipped to 6–48 h; offline-inference deadlines were 1.5–4 times runtime, clipped to 2–24 h. These are synthetic service rules. Single events began at one of 24 hours between 63 and 140, sampled before testing; exact starts are stored with each scenario. Community demand used a 75:25 residential/office mixed-3A profile, scaled to an 800-kW peak. A common 1,100-kW import rating and no-export rule applied to all cases. Initial development baselines under a 1,000-kW rating exceeded it in three cases at seed 930096; the common rating was raised before PI optimisation or offer selection, and the initial gate results were preserved.

### 3. Power conversion, queues and observations

Each workload ran in one- and four-GPU conditions with three repeats. After a 5-s warm-up, read-only nvidia-smi telemetry sampled board power and utilisation every second for 20 s. Repeats 1–2 supplied calibration and repeat 3 was held out. For each four-GPU repeat, readings were averaged first over time within each GPU, then across GPUs. The resulting run means were the independent units. Student t 95% intervals used the two calibration means per active class; prediction error used only the held-out repeat (Supplementary Table 1).

Facility power retained the execution class,

\[
P^{\mathrm{DC}}_t=P_{\mathrm{fixed}}+\sum_c e_cX_{c,t},
\]

In this expression, \(X_{c,t}\) is flexible work executed in class c during interval t, measured in GPU-h. Its coefficient is \(e_c=\mathrm{PUE}(p_c-p_{\mathrm{idle}})/(1000\Delta t)\), in kW per GPU-h. Board powers p are measured in W and \(\Delta t=1\) h. Subtracting idle power ensures that scheduled work contributes only incremental active power. Fixed facility power contains rigid-pool draw, flexible-pool idle draw and node overhead, all multiplied by PUE = 1.20.

Jobs were stored by class and remaining deadline at one-hour resolution, up to 48 h. The labels {0, 1, 2, 3, 6, 12, 24, 48} h grouped this state for reporting and observation; they were not the queue's internal time resolution. Execution followed earliest deadline first, could not precede release and could not exceed cumulative arrivals. Work remaining when its deadline expired was counted as missed. Controlled and no-response queues received identical arrivals.

Idle board power was 13.935625 W per GPU and node overhead was assumed to be 300 W. Online, development, other and unknown work used 300.022174 W per active rigid GPU as an engineering proxy, with 150- and 225-W controls. Rigid power was fixed at its class-weighted mean. Online latency was not separately simulated, so preserving batch deadlines is not a measured online-serving SLO test. The controller retained the existing 63-feature firm_v5 observation interface; its six-hour forecasts and queue features were causally masked. The stored compute_debt_kwh field describes the whole controlled queue. Exported excess_queue_energy_kwh explicitly subtracts the matched no-response value.

### 4. Success criteria and statistics

Successful demand response required both electrical delivery and acceptable computing service. For each fixed capacity, duration, notice and controller, an episode received one binary outcome after all six criteria below were evaluated. Delivery was the non-negative reduction in point-of-common-coupling power relative to the matched baseline, capped at the request. A high mean could not compensate for an hour below the interval threshold. Peak relief was evaluated over the event and its 24-h recovery window.

| Criterion | Headline threshold | Operational interpretation |
|---|---:|---|
| Mean delivery | ≥0.95 | mean capped baseline-relative reduction across all event intervals divided by R |
| Minimum interval delivery | ≥0.95 | every event hour delivers at least 0.95R |
| Deadline-miss fraction | ≤0.01 | expired eligible GPU-hour work divided by total arriving eligible work |
| Rebound ratio | ≤0.25 | largest post-event excess PCC load divided by peak event reduction |
| Event-and-recovery peak relief | ≥0.50 | baseline peak minus controlled peak over the event plus 24-h recovery window, divided by R |
| Terminal-backlog fraction | ≤0.02 | positive controlled-minus-baseline backlog at the end of the 48-h tail divided by total eligible arrivals |

Failure attribution retained combined labels rather than assigning only the first failed criterion. Mean and interval failures could occur together, and delivery failures could coincide with rebound or window-relief failures. Recovery-time non-resolution was a separate diagnostic, not an additional certificate criterion.

The structural study additionally required zero total missed eligible work, allowing only 10<sup>−7</sup> GPU-h for numerical round-off. Both response and no-response trajectories had to satisfy that zero criterion; all electrical and terminal-backlog thresholds were unchanged. The 0.1% allowance was a secondary reported endpoint without offer selection. Baseline failures remained failures rather than exclusions. Earlier selected offers were also rescored at zero loss, explicitly as a retrospective check.

For 100 PI optima, binomial inversion selected the second order statistic at q = 0.95 and confidence 0.95. For controller testing, a one-sided 95% Wilson interval used z = 1.6448536. Development and confirmation applied the same lower-bound threshold of 0.95. Each condition contained 100 development or 300 confirmation seeds; extra notices and calls did not create additional independent seeds. Notice comparisons used exact paired McNemar tests with Holm correction across 20 contrasts. Repeated-minus-fresh differences used 10,000 paired bootstrap resamples of 300 seeds. Renewable mean differences used 10,000 paired resamples of 100 seeds. These intervals and qualifications are pointwise, apart from the declared notice-test correction.

### 5. Causal controller and development correction

The six-hour robust MPC retained its historical-arrival uncertainty envelope, objective weights and release-only queue information. Development exposed a dimensional mismatch in the former recovery guard: it allowed an overshoot of 0.25R, whereas rebound was evaluated relative to actual peak delivery, which could be as low as 0.95R. The revised guard uses 0.25 × 0.95R, along with the existing event-and-window-relief envelopes. When float32 conversion would cross an electrical limit, actions are rounded towards zero. All success criteria remain unchanged. Regression checks cover the delivered-power rebound denominator, event-boundary rounding and unchanged actions outside event/recovery windows. This is a new controller version, not a reinterpretation of the original locked certificate.

Each duration tested 50%, 75%, 90% and 100% of its development Relaxed PI statistic. The largest candidate meeting the development Wilson criterion was frozen before confirmation. After the final controller correction, 300 previously unexamined seeds were reserved for confirmation; earlier original-controller and intermediate development outputs were retained as diagnostics. No confirmation outcome was used to choose a smaller replacement offer.

### 6. Repeated programmes

For the original controller study (confirmation seeds 960000–960299): Four event starts were 63 + j(H + G), j = 0, 1, 2, 3, for (H,G) = (4,8) or (8,12) hours. Development tested 25%, 50%, 75% and 100% of the selected single-event offer without assuming monotonic success. Confirmation tested the prespecified original single offer repeated, plus four single-call counterfactuals at matching clock times. The protocol additionally provided for testing a development-selected repeated offer if one qualified; none did. The no-response reference was the same full-capacity schedule in every paired comparison. The experiment covers two declared programmes, not every recovery gap or a continuous-year guarantee.

For the follow-up, H and G were (4,8), (8,8), (8,12) and (8,16) h, with the same first start at hour 63. After a later call ends, the preceding 24-h recovery remains active for max(0, 24 − H − G) h. This overlap is zero for H = 8 h and G = 16 h, although changing G also changes the clock alignment of later calls. Final recovery ends no later than hour 167, before arrivals stop at hour 168. Every replay then retains the full 216-h horizon, including the clearance tail. No gap comparison isolates spacing from time-of-day effects.

For an observed call j, let B_j(t) be the greatest baseline PCC power observed so far in its event-and-recovery window, and R_j its request. The wrapper constrains the current proposal by every live ceiling B_j(t) − 0.5R_j. It also preserves the active-event delivery ceiling and the rebound ceiling baseline(t) + 0.25 × 0.95R_j during recovery. With fixed PCC demand F(t) and flexible full-allocation contribution A(t), the additional allocation cap is clip[(min_j(B_j(t) − 0.5R_j) − F(t))/A(t), 0, 1]. Actions are rounded towards the feasible side. The controller learns a call’s remaining duration only from the current observation and expires it after its 24-h recovery. Running baseline peaks can be lower than their eventual values, making this causal guard conservative. A target below F(t) cannot be made feasible by clipping, and electrical clipping alone does not guarantee job deadlines.

The extension reused 100 previously examined development seeds (930000–930099); four of these also informed an exploratory pilot. The frozen protocol then enumerated 10,100 development replays: five workload configurations, two MPC versions, four programmes, a full-only four-hour candidate and 50%, 75% and 100% eight-hour candidates, plus 100 full-request greedy diagnostics at 10% eligibility and (8,12). The largest candidate with one-sided 95% Wilson lower bound at least 0.95 was selected. The frozen selection scheduled 13,800 replays on 300 new confirmation seeds (970000–970299). For each configuration, method and programme, confirmation tested the selected offer or the full-request comparator if none was selected. Full-request comparisons for both MPC versions at (8,12) and the greedy diagnostic were additionally retained. No confirmation result was pooled with the earlier 960000–960299 set or used for reselection. Every full series, including all failures, was analysed.

The primary intervention contrast is the full-request original versus per-call-recovery MPC at 10% eligibility and (8,12). Paired success differences use 10,000 resamples of complete seeds; exact McNemar tests receive Holm correction across all controller contrasts reported in the source table. Non-exclusive failure families and paired rescue/loss counts are also retained. Qualification is pointwise for each frozen candidate. A selected candidate that fails confirmation would remain failed, with no test-set replacement. The illustrated trace is the lowest development seed for which the full-request original fails and the revised MPC passes; this transparent illustrative selection is separate from inference on all confirmation seeds.

At fixed 10% work eligibility and 576 GPUs, offered utilisation was total work divided by installed GPU-hours, set to 50%, 65% or 80%. Deadline slack was unchanged or halved with a one-hour floor; flexible GPU allocation was 10%, with 20% controls at 65% and 80% utilisation under tight deadlines. The final event started at hour 111 plus a seeded uniform integer from 0 to 23; preceding starts were spaced backwards by 16 or 24 h. All eight variants tested eight-hour calls, and the reference also tested four-hour calls at 16-h spacing. A fresh eight-hour final call at the same time removed the preceding calls. All recovery windows ended during 168 h of arrivals, followed by a 48-h clearance tail. Development seeds 984000–984099 and confirmation seeds 985000–985299 supplied 7,600 and 13,200 complete replays, respectively. Two pilot seeds were excluded.

For the external timing stress test, hourly submission counts from the Alibaba 2020 GPU trace<sup>28</sup> supplied eight consecutive 168-h blocks. Counts set the hourly weights of synthetic class-specific work, preserving each class total and reference deadlines. The paired alternative permuted complete hourly blocks within the same week. Ten synthetic realisations per week crossed both orderings and 10%/20% GPU allocations with five frozen programme–request combinations, giving 1,600 replays without retuning. Results are reported by observed week and descriptively across 80 realisations per condition; they are not 80 independent production weeks.

Structural contrasts resampled 300 complete paired scenario seeds 5,000 times. Exact McNemar tests were Holm-adjusted over the 36 binary structural contrasts; the 16 additional matched-target electrical contrasts formed a separate family. The zero-loss and 1% offer tests each retained the pointwise one-sided 95% Wilson lower-bound criterion of 0.95. Multiple successful selections do not create a simultaneous confidence guarantee. Submission-order comparisons retained the observed week as the external sampling unit and were not assigned binomial certificates from pooled synthetic realisations.

A necessary supply diagnostic compared each active hour’s matched baseline PCC power minus community load and idle-plus-rigid data-centre power with 0.95 times the request. If the former was smaller, even zero flexible execution could not meet the interval requirement. This lower-envelope test identifies immediate shortage but does not prove feasibility when passed. Deadline and terminal criteria were scored over the whole 216-h episode. Last-call electrical scoring excluded those global service quantities, matched the final clock exactly and used the fresh run’s reindexed event 0. All 16 paired differences were zero. Programme-wide criteria were not substituted for local electrical outcomes.

The timing input was the processed Alibaba 2020 job-submission table (714,903 GPU jobs), using trace hours 168–1511 inclusive. The eight 168-h weeks supplied hourly counts; each week’s class-specific synthetic total was normalised to the unchanged offered work. A whole-hour permutation preserved the marginal hourly volumes and the exact class–deadline totals. Seeds 986000 + 100w + r, for week w = 0,…,7 and realisation r = 0,…,9, generated paired inputs. Frozen tests used request fractions 0.5, 0.75 and 1 at eight-hour/16-h spacing, and 0.5 and 1 at eight-hour/24-h spacing. No external result selected a new fraction. Submission counts preserve one observed temporal feature; they do not supply real GPU-hour volumes, deadlines or job dependencies. All 320 timing input variants passed the baseline service gate.

Local refinement fixed the reference workload and controller and tested fractions 0.50–0.75 for H8P16 and 0.75–1.00 for H4P16, in steps of 0.05 of the unchanged 5.898243186-kW request. H denotes duration and P start spacing. Seeds 988000–988099 supplied development; endpoint-specific selections were frozen before seeds 989000–989299 supplied confirmation. Only selected candidates and prespecified coarse comparators entered confirmation, with no reselection. The grid ceiling for eight hours was selected under both standards, so the test did not bracket a continuous maximum. Earlier seeds were not pooled with these data.

Perfect-information diagnostics fixed each request and its four event clocks, baseline and 24-h recovery windows. Non-negative execution variables existed only between each class/release/deadline work group’s own release and deadline; execution, misses and terminal work conserved every group. Constraints retained GPU and PCC limits, 95% hourly and capped-mean delivery, 25% rebound relative to actual peak event reduction, 50% full-window peak relief and the original terminal allowance. Binary peak selectors represented the rebound denominator exactly. HiGHS solved the resulting mixed-integer feasibility problem. Thirty-three prespecified structural cases comprised five configurations, three previously used seeds and two service standards, plus three reference 4.42-kW checks; five affected external weeks supplied an additional first-shortage diagnostic each. These mechanism-selected cases were not prevalence samples. All 11 feasible witnesses passed independent work-group and electrical checks. A 90-s unresolved solve was retained and resolved as infeasible after extending only its time limit to 600 s. Full-information feasibility was not treated as causal realizability.

The resource-time transfer test reconstructed each processed job’s GPU-seconds as the sum of requested GPU-equivalents × task launch-to-completion duration across its terminated positive-resource tasks.<sup>28</sup> All 714,903 processed jobs matched the raw task reconstruction; multiplying total requested GPUs by job submission-to-completion time instead differed for 131,379 jobs. The test retained trace hours 168–1511, whose processed time origin is 542,323 s after the raw origin. Within each week, either job counts or submitted task resource-time set hourly weights; each class’s weekly work total was normalised to the reference total. Identical synthetic job classes, deadlines, community traces, event clocks and paired whole-hour permutations were used at each seed (990000 + 100w + r; eight weeks × ten realisations). Fixed 2.95- and 4.42-kW requests gave 640 complete replays. All 320 no-response input variants passed zero-loss service; no failed variant was excluded. Aggregate counts are descriptive. Allocated resource-time is not a sensor measurement of busy GPU time, and the test retains divisible work and synthetic service rules.

### 7. Renewable planning

Each configuration used its actual power model at scale one. PV hosting maximised rated PV capacity with curtailment ≤5%, zero deadline misses, terminal backlog ≤2%, imports ≤1,100 kW and no exports. Fixed-PV operation used 500 kW and lexicographic objectives: service, local PV use, grid import, then battery throughput. PV-use tolerance was 10<sup>−5</sup> kWh. BESS had 100-kW charge/discharge power, 200-kWh energy, charge and discharge efficiency 0.95, and initial/terminal state of charge 50%. Binary exclusivity prohibited simultaneous charge and discharge. The first 100 confirmation seeds were paired across rigid/flexible operation and both BESS conditions. All feasibility statuses and missed work were retained; an all-scenario capacity is not reported from a filtered subset.

HiGHS 1.15.1 retained its default relative MIP gap 10<sup>−4</sup> and absolute gap 10<sup>−6</sup>; only solver thread count was changed. The lexicographic lock on PV use is distinct from the primary optimisation gap. Small signed BESS utilisation contrasts can lie within this numerical resolution (roughly 0.01 percentage points when most PV is used). They are retained rather than clipped to zero, but are not interpreted as a physical loss or a resolved benefit. Bootstrap intervals describe scenario sampling only. The numerical-precision audit records the solver version and options.

### 8. Orthogonal sensitivity controls

Four controls around 10% eligibility were specified before their outcomes were examined: flexible GPU allocation 20% or 30%, and rigid-class active-power proxy 150 or 225 W. Other inputs, seed identities and event times were unchanged. Each control had 300 no-response gates, 100 PI scenarios at both durations, 300 fixed-offer tests at both durations, and 100 paired renewable scenarios. Its economic ledger used the same fixed requests. These selected controls and the five eligibility scenarios do not constitute a global sensitivity analysis over simultaneous variation in all model parameters.

### 9. Complete ledgers and economic sensitivity

From the first event through episode end, delay exposure was the sum of positive paired excess backlog times the one-hour interval. Incremental energy was the signed controlled-minus-baseline PCC energy. Deferred work summed positive execution shortfalls during event hours; it did not automatically imply lost work. Each repeated series contributed every hour once. The source tables retain incremental deadline misses and terminal backlog even when a programme fails.

Single-event annual draws sampled 50 complete confirmation episodes; repeated draws sampled 12 complete four-call series. Two thousand common bootstrap draws were used at each price setting. Physical quantities and the offer were multiplied by 1000 divided by each configuration's own operating peak; the US$25,000 annual site charge was then added once. The required payment was max(0, the 95th percentile of net annual cost divided by offered accounting kW). Prices were US$0.10/kWh for electricity, US$50/MWh for capped delivered energy and US$0.005/GPU-h/h for waiting. All 300 trajectories were retained regardless of success.

Reserve costs annualised 0.15 abstract reserved PCC-side kW per offered kW, at US$2,500 per reserved kW, 8% discount, four-year life, 10% salvage and 3% annual operation and maintenance. This is not a GPU procurement quotation or wear model. Separate assumed displaced-value exposures of US$0.25 and 0.50 per deferred GPU-h were evaluated; only the former is the main illustration. Sensitivity grids covered waiting prices 0, 0.001, 0.005 and 0.01; fixed site costs 10,000, 25,000 and 50,000; displaced values 0, 0.25, 0.5 and 1; missed-work prices 0, 0.25 and 1; and reserve lives 3–6 years. Contract-specific non-performance penalties were not priced. The original price-source register is retained in the archive; these inputs remain scenarios rather than observed operator accounts.

Recovery-extension costs use the same full-series ledger, twelve independent series per year and 2,000 common annual draws on the new confirmation set. All 300 series enter each calculation, irrespective of success. The crossed grid uses waiting prices 0, 0.005 and 0.01, annual site costs US$10,000, 25,000 and 50,000 and displaced values US$0, 0.25 and 0.50 per deferred GPU-h. Reserved-headroom costs retain the stated four-year reference assumptions. This extension does not rerun the original missed-work-price or reserve-life screens. Source tables identify development selection and independent qualification separately, so a low-cost failed comparator cannot be mistaken for an offerable choice.

The fee decomposition used common annual draws and the same linear-interpolation weights at the total net-cost 95th percentile for every component; it did not add marginal component quantiles. Additional screens crossed site fees US$0, 1,000, 2,500, 5,000, 10,000 and 25,000, waiting prices US$0, 0.005 and 0.01 per GPU-h/h, and missed-work prices US$0 and 1 per GPU-h. Sharing a US$25,000 fee among ten or five resources gave US$2,500 or 5,000 without a diversification benefit. For qualified product j with accounting capacity K_j and annual net operating cost O_j at its 95th percentile, the fifth-percentile net value was P_j K_j − O_j − F. Duration-price boundaries compared these values and the zero value of not participating. They are algebraic consequences of the stated ledgers and prices, not estimated market tariffs.

## Supplementary Figures

### Supplementary Figure 1 | Study inputs and evidence flow

![Supplementary Figure 1](../docs/figures/commitment_narrative_v1/artwork/AIDRBench_Supplementary_Figure_1.png)

**a,** Source composition and declared permission define a paired job template, hardware allocation and hourly deadline queues in the community PCC model. **b,** Development selects requests before independent confirmation; complete trajectories supply the cost ledger. PV and BESS optimisation is a separate full-information branch. Arrows describe model inputs and analysis dependencies, not estimated causal effects.

### Supplementary Figure 2 | Four-GPU board-power calibration

![Supplementary Figure 2](../docs/figures/commitment_narrative_v1/artwork/AIDRBench_Supplementary_Figure_2.png)

**a,** All 30 per-board run averages from one- and four-GPU training and offline inference. Filled points are fitting runs 1–2; open points are held-out run 3. Boards in one run are not independent replicates. **b,** Active-power estimates and 95% Student-t intervals from two independent four-GPU run means per class. Held-out overall MAE is 3.80 W/GPU. Node overhead and online-serving power were not measured by this calibration.

### Supplementary Figure 3 | Candidate resolution and structural context

![Supplementary Figure 3](../docs/figures/commitment_narrative_v1/artwork/AIDRBench_Supplementary_Figure_3.png)

**a,b,** Development one-sided 95% Wilson lower bounds for every four- and eight-hour local candidate (100 scenarios each, both service standards). The dashed line is the selection threshold of 0.95; the selected eight-hour grid ceiling is not a bracketed maximum. **c,** Full-request structural controls show instantaneous shortages and >1% deadline failures as potentially overlapping categories (300 scenarios). **d,** Chronological submission-count cross-scoring from the 986000-series study: stacked segments show successes and immediate shortages at 4.42 kW, and markers show 2.95-kW successes. Both service scores coincide at each request. Eight observed weeks have ten synthetic realisations each; counts are descriptive. Historical design interpretation is in Note 7; matched last-call outcomes, all of which coincide, remain in Table 15 and Source Data.

### Supplementary Figure 4 | PV benefits and fixed-request controls

![Supplementary Figure 4](../docs/figures/commitment_narrative_v1/artwork/AIDRBench_Supplementary_Figure_4.png)

**a,** Flexible minus rigid all-scenario PV hosting capacity across the five eligibility scenarios, with and without BESS; each capacity is the minimum over 100 scenarios. **b,** Paired gain in utilisation of a fixed 500-kW PV system; points are means and whiskers are 95% paired bootstrap intervals. The intervals cover sampling, not optimisation error; small storage contrasts remain unresolved at solver precision. **c,** Four- and eight-hour success at unchanged primary single-event requests across allocation and rigid-power controls, with one-sided 95% Wilson lower bounds from 300 scenarios. **d,** Corresponding gains in all-scenario PV hosting over 100 paired scenarios. Panels c,d retain 10% eligibility and vary only GPU allocation or the stated rigid-power proxy. PV schedules use full information and zero missed work; hosting differences are differences of minima, not mean effects or confidence intervals.

### Supplementary Figure 5 | Waiting valuation and access fees change product choice

![Supplementary Figure 5](../docs/figures/commitment_narrative_v1/artwork/AIDRBench_Supplementary_Figure_5.png)

**a,** Difference between product-specific fifth-percentile annual net values, eight minus four hours, at equal capacity prices with zero waiting price and zero access fee; zero marks indifference between participating products. **b,** Refined zero-loss product thresholds with zero or US$1/GPU-h missed-work valuation at reference waiting price and zero fee. The zero-loss qualification permits occasional failed scenarios, whose ledgers remain priced. **c,** Fifth-percentile annual net values at US$250 per kW-year, reference waiting price and zero, shared or full access fees. **d,** Eight-hour price required to match both four-hour participation and opting out at those access fees. All products use the new 300-seed confirmation ledgers, 10% eligibility, 65% offered utilisation, reference deadlines and 16-h start spacing. Annual accounting and energy prices match Fig. 6; fees are common across duration products and do not imply reliability pooling.

## Supplementary Tables

### Supplementary Table 1 | Power coefficients and measurement scope

| Input | Estimate | Evidence |
|---|---|---|
| Training active power | 259.08 W/GPU | 2 independent fitting runs; 1 held out |
| Offline inference active power | 300.02 W/GPU | 2 independent fitting runs; 1 held out |
| Idle power | 13.935625 W/GPU | Existing calibration |
| Node overhead | 300 W/node | Engineering assumption |
| PUE | 1.2 | Engineering assumption |
| Other rigid active power | 300.022174 W/GPU | Proxy; controls at 150 and 225 W |

### Supplementary Table 2 | Five workload configurations

| Eligible work (%) | Online work (%) | Eligible training (%) | Eligible offline (%) | Flexible GPUs | Operating peak (kW) |
|---|---|---|---|---|---|
| 5 | 54.50 | 0.26 | 4.74 | 29 | 189.94 |
| 10 | 54.50 | 0.52 | 9.48 | 58 | 193.44 |
| 20 | 54.50 | 1.03 | 18.97 | 115 | 200.10 |
| 40 | 54.50 | 18.51 | 21.49 | 230 | 212.16 |
| 60 | 35.44 | 19.42 | 40.58 | 346 | 226.17 |

All workload percentages use total offered GPU-hours as denominator. Total work is 374.4 GPU-h/h and installed hardware is 576 GPUs. The 40% case expands batch permission; 60% changes business composition. Mean utilisation is approximately 65% in each primary pool; operating peak is a model coefficient, not an observed event peak.

### Supplementary Table 3 | Evidence partitions and execution provenance

| Analysis | Independent seeds | Runs or results |
|---|---|---|
| Primary no-response gates | 100 development + 300 confirmation | 2000 |
| Single development | 100 | 4000 |
| Single confirmation | 300 | 9000 |
| Repeated development | 100 | 4000 |
| Repeated confirmation | 300 | 15000 |
| Fixed-request controls | 300 | 2400 |
| PI optima, including controls | 100 per partition and configuration | 2800 |
| Renewable comparisons, including controls | 100 | 7200 |
| Full controller hourly rows | Repeated rows are dependent | 7430400 |

| Recovery extension | Independent seeds per condition | Complete replays | Hourly rows |
|---|---|---|---|
| Development | 100 reused | 10,100 | 2,181,600 |
| Independent confirmation | 300 new | 13,800 | 2,980,800 |
| Total | Paired across conditions | 23,900 | 5,162,400 |

For the original controller study (confirmation seeds 960000–960299): Development seeds are 930000–930099; confirmation seeds are 960000–960299. Repeat-duration runtime checks verify all four- and eight-hour calls. Earlier one-hour repeat diagnostics are excluded. Protocols, controller and runner hashes, scenario identities, all trial outcomes and hourly manifests accompany Source Data. No run count should replace the number of independent seeds in statistical inference.

### Supplementary Table 4 | Relaxed planning statistics and independent single-event qualification

| Eligibility (%) | Duration (h) | Relaxed PI statistic (kW) | Offer (kW) | Success | Wilson lower | Qualifies |
|---|---|---|---|---|---|---|
| 5 | 4 | 2.89 | 2.95 | 295/300 | 0.9662 | Yes |
| 5 | 8 | 2.79 | 2.95 | 292/300 | 0.9533 | Yes |
| 10 | 4 | 5.78 | 5.90 | 295/300 | 0.9662 | Yes |
| 10 | 8 | 5.57 | 5.90 | 292/300 | 0.9533 | Yes |
| 20 | 4 | 11.56 | 11.80 | 295/300 | 0.9662 | Yes |
| 20 | 8 | 11.14 | 11.80 | 292/300 | 0.9533 | Yes |
| 40 | 4 | 21.75 | 22.19 | 295/300 | 0.9662 | Yes |
| 40 | 8 | 20.96 | 22.19 | 292/300 | 0.9533 | Yes |
| 60 | 4 | 33.31 | 34.00 | 295/300 | 0.9662 | Yes |
| 60 | 8 | 32.12 | 34.00 | 292/300 | 0.9533 | Yes |

PI uses 100 confirmation scenarios; controller testing uses 300. Each offer was fixed on development data. Notice 0, 2 and 6 h is retained separately in Source Data, together with all paired binary outcomes and Holm-adjusted exact McNemar tests. Qualification is pointwise at 95% reliability and 95% one-sided confidence.

### Supplementary Table 5 | Repeated programmes and matched fresh calls

| Eligibility (%) | Call/gap (h) | Fresh/repeated successes | Repeated − fresh (pp), 95% interval | Original repeated lower | Development-selected kW |
|---|---|---|---|---|---|
| 5 | 4/8 | 300/300 | 0.0 [0.0, 0.0] | 0.9911 | None |
| 5 | 8/12 | 297/268 | -9.7 [-13.0, -6.3] | 0.8604 | None |
| 10 | 4/8 | 300/300 | 0.0 [0.0, 0.0] | 0.9911 | None |
| 10 | 8/12 | 297/256 | -13.7 [-17.7, -9.7] | 0.8166 | None |
| 20 | 4/8 | 300/300 | 0.0 [0.0, 0.0] | 0.9911 | None |
| 20 | 8/12 | 297/250 | -15.7 [-19.7, -11.7] | 0.7950 | None |
| 40 | 4/8 | 300/300 | 0.0 [0.0, 0.0] | 0.9911 | None |
| 40 | 8/12 | 297/249 | -16.0 [-20.3, -12.0] | 0.7914 | None |
| 60 | 4/8 | 300/300 | 0.0 [0.0, 0.0] | 0.9911 | None |
| 60 | 8/12 | 297/241 | -18.7 [-23.0, -14.3] | 0.7629 | None |

For the original controller study (confirmation seeds 960000–960299): Each success count is out of 300 complete programmes and requires all four calls to pass. The comparison reuses the Table 4 single-event offer. A selected repeated offer is the largest qualifying development-grid candidate; its separate confirmation lower bound determines qualification. None denotes no qualifying development candidate, not zero true capacity. All original four-hour repeated offers passed confirmation (300/300; lower 0.9911), whereas the eight-hour originals did not. None passed the separate development selection rule. Paired intervals resample complete seeds.

### Supplementary Table 6 | PV hosting and fixed-PV utilisation

| Eligibility (%) | BESS | Rigid PV kW | Flexible PV kW | Boundary gain kW | Utilisation gain (pp), 95% interval |
|---|---|---|---|---|---|
| 5 | No | 604.21 | 607.03 | 2.82 | 0.0034 [0.0012, 0.0060] |
| 5 | Yes | 672.63 | 675.22 | 2.60 | -0.0002 [-0.0004, 0.0000] |
| 10 | No | 603.55 | 608.95 | 5.40 | 0.0057 [0.0019, 0.0106] |
| 10 | Yes | 672.39 | 677.61 | 5.22 | 0.0000 [-0.0000, 0.0001] |
| 20 | No | 601.56 | 611.92 | 10.36 | 0.0102 [0.0030, 0.0201] |
| 20 | Yes | 671.83 | 681.87 | 10.04 | 0.0000 [-0.0000, 0.0000] |
| 40 | No | 597.97 | 626.96 | 28.99 | 0.0249 [0.0074, 0.0476] |
| 40 | Yes | 669.34 | 697.34 | 28.00 | 0.0008 [-0.0000, 0.0024] |
| 60 | No | 593.74 | 632.69 | 38.95 | 0.0360 [0.0108, 0.0701] |
| 60 | Yes | 665.29 | 703.58 | 38.28 | 0.0072 [-0.0000, 0.0179] |

Each hosting capacity is the minimum over all 100 confirmation scenarios at ≤5% curtailment. Utilisation uses a fixed 500-kW PV installation; means and pointwise paired bootstrap intervals are in percentage points. All current renewable solutions are retained and checked for zero deadline misses. The corresponding conditional mean hosting effects are separately available in Source Data.

### Supplementary Table 7 | Single-event and complete-programme participation screens

| Eligibility (%) | Call (h) | Single slack | Single reserve | Single displacement | Repeated original, slack | Repeated confirmation passes |
|---|---|---|---|---|---|---|
| 5 | 4 | 1653.07 | 1769.22 | 1793.29 | 1768.26 | Yes |
| 5 | 8 | 1739.11 | 1855.26 | 2019.54 | 1881.22 | No |
| 10 | 4 | 863.26 | 979.40 | 1003.51 | 978.16 | Yes |
| 10 | 8 | 949.73 | 1065.88 | 1230.15 | 1091.58 | No |
| 20 | 4 | 468.04 | 584.19 | 608.28 | 582.75 | Yes |
| 20 | 8 | 556.08 | 672.23 | 836.42 | 696.75 | No |
| 40 | 4 | 320.26 | 436.41 | 476.98 | 468.71 | Yes |
| 40 | 8 | 435.52 | 551.67 | 747.71 | 639.18 | No |
| 60 | 4 | 235.38 | 351.53 | 386.32 | 366.09 | Yes |
| 60 | 8 | 342.36 | 458.51 | 643.43 | 518.89 | No |

For the original controller study (confirmation seeds 960000–960299): All payments are US$ per offered accounting kW-year at a proportional 1-MW operating peak. Single events use 50 independent calls/year; repeated programmes use 12 independent four-call series/year. The site charge is US$25,000 once yearly. The displacement illustration assumes US$0.25 per deferred GPU-h. The repeated-pass column applies the confirmation Wilson criterion only; the separate development rule selected no repeated candidate. Conditional costs do not change either outcome. All price-grid rows and failed-trajectory service losses are retained in Source Data.

### Supplementary Table 8 | Orthogonal allocation and rigid-power controls

| Control | Hours | Relaxed PI kW | Fixed offer kW | Success | Wilson lower | Slack payment |
|---|---|---|---|---|---|---|
| f10_g20 | 4 | 5.78 | 5.90 | 295/300 | 0.9662 | 948.10 |
| f10_g20 | 8 | 5.57 | 5.90 | 292/300 | 0.9533 | 1028.31 |
| f10_g30 | 4 | 5.78 | 5.90 | 295/300 | 0.9662 | 1031.87 |
| f10_g30 | 8 | 5.57 | 5.90 | 292/300 | 0.9533 | 1112.09 |
| f10_rigid150 | 4 | 5.78 | 5.90 | 295/300 | 0.9662 | 694.54 |
| f10_rigid150 | 8 | 5.57 | 5.90 | 292/300 | 0.9533 | 781.01 |
| f10_rigid225 | 4 | 5.78 | 5.90 | 295/300 | 0.9662 | 778.88 |
| f10_rigid225 | 8 | 5.57 | 5.90 | 292/300 | 0.9533 | 865.36 |

All controls retain 10% eligibility and the same work. g20/g30 change flexible GPU allocation to 20%/30%; rigid150/rigid225 change only unmeasured rigid-class active power to 150/225 W. Payment units and annual assumptions match Table 7. Full renewable and paired economic controls are provided in Source Data.

### Supplementary Table 9 | Monetary assumptions and sensitivity ranges

| Input | Reference | Evaluated values |
|---|---|---|
| Delay, US$/GPU-h/h | .005 | 0, .001, .005, .01 |
| Fixed site, US$/year | 25,000 | 0; 1,000; 2,500; 5,000; 10,000; 25,000; 50,000 |
| Displaced value, US$/deferred GPU-h | .25 | 0, .25, .5, 1 |
| Missed work, US$/GPU-h | 0 | 0, .25, 1 |
| Reserve economic life, years | 4 | 3, 4, 5, 6 |
| Electricity, US$/kWh | .10 | Held fixed |
| Delivered energy, US$/MWh | 50 | Held fixed |
| Independent annual draws | 2,000 | Common draws at each price |

The main economic comparison uses the reference prices and reports the 95th percentile of net annual cost. Delay/site/displacement prices are crossed; missed-work prices are varied at the reference delay/site setting with no displacement charge; reserve life is varied separately. These are scenario inputs, not empirical distributions or a joint global uncertainty model. No actual GPU procurement price, ageing hazard or contract-specific failure tariff is inferred.

### Supplementary Table 10 | Frozen repeated offers and new independent confirmation

| Eligibility (%) | H/G (h) | Controller | Selected fraction | kW | Successes | Wilson lower | Outcome |
|---|---|---|---|---|---|---|---|
| 5 | 4/8 | Per-call MPC | 100% | 2.95 | 300/300 | 0.9911 | Pass |
| 5 | 4/8 | Original | — | — | — | — | Not selected |
| 5 | 8/8 | Per-call MPC | 75% | 2.21 | 300/300 | 0.9911 | Pass |
| 5 | 8/8 | Original | — | — | — | — | Not selected |
| 5 | 8/12 | Per-call MPC | 75% | 2.21 | 300/300 | 0.9911 | Pass |
| 5 | 8/12 | Original | — | — | — | — | Not selected |
| 5 | 8/16 | Per-call MPC | 75% | 2.21 | 299/300 | 0.9852 | Pass |
| 5 | 8/16 | Original | 75% | 2.21 | 299/300 | 0.9852 | Pass |
| 10 | 4/8 | Per-call MPC | 100% | 5.90 | 300/300 | 0.9911 | Pass |
| 10 | 4/8 | Original | — | — | — | — | Not selected |
| 10 | 8/8 | Per-call MPC | 75% | 4.42 | 300/300 | 0.9911 | Pass |
| 10 | 8/8 | Original | — | — | — | — | Not selected |
| 10 | 8/12 | Per-call MPC | 75% | 4.42 | 300/300 | 0.9911 | Pass |
| 10 | 8/12 | Original | — | — | — | — | Not selected |
| 10 | 8/16 | Per-call MPC | 75% | 4.42 | 299/300 | 0.9852 | Pass |
| 10 | 8/16 | Original | 75% | 4.42 | 299/300 | 0.9852 | Pass |
| 20 | 4/8 | Per-call MPC | 100% | 11.80 | 300/300 | 0.9911 | Pass |
| 20 | 4/8 | Original | — | — | — | — | Not selected |
| 20 | 8/8 | Per-call MPC | 75% | 8.85 | 300/300 | 0.9911 | Pass |
| 20 | 8/8 | Original | — | — | — | — | Not selected |
| 20 | 8/12 | Per-call MPC | 75% | 8.85 | 300/300 | 0.9911 | Pass |
| 20 | 8/12 | Original | — | — | — | — | Not selected |
| 20 | 8/16 | Per-call MPC | 75% | 8.85 | 299/300 | 0.9852 | Pass |
| 20 | 8/16 | Original | 75% | 8.85 | 299/300 | 0.9852 | Pass |
| 40 | 4/8 | Per-call MPC | 100% | 22.19 | 300/300 | 0.9911 | Pass |
| 40 | 4/8 | Original | — | — | — | — | Not selected |
| 40 | 8/8 | Per-call MPC | 75% | 16.65 | 300/300 | 0.9911 | Pass |
| 40 | 8/8 | Original | — | — | — | — | Not selected |
| 40 | 8/12 | Per-call MPC | 75% | 16.65 | 300/300 | 0.9911 | Pass |
| 40 | 8/12 | Original | — | — | — | — | Not selected |
| 40 | 8/16 | Per-call MPC | 75% | 16.65 | 299/300 | 0.9852 | Pass |
| 40 | 8/16 | Original | 75% | 16.65 | 299/300 | 0.9852 | Pass |
| 60 | 4/8 | Per-call MPC | 100% | 34.00 | 300/300 | 0.9911 | Pass |
| 60 | 4/8 | Original | — | — | — | — | Not selected |
| 60 | 8/8 | Per-call MPC | 75% | 25.50 | 300/300 | 0.9911 | Pass |
| 60 | 8/8 | Original | — | — | — | — | Not selected |
| 60 | 8/12 | Per-call MPC | 75% | 25.50 | 300/300 | 0.9911 | Pass |
| 60 | 8/12 | Original | — | — | — | — | Not selected |
| 60 | 8/16 | Per-call MPC | 75% | 25.50 | 299/300 | 0.9852 | Pass |
| 60 | 8/16 | Original | 75% | 25.50 | 299/300 | 0.9852 | Pass |

The 40 method–programme–workload configurations yielded 25 development selections; 25/25 passed their new independent tests. Per-call MPC denotes MPC with a separate guard for every observed live recovery window. Each success requires all four calls to satisfy every criterion. Fractions are relative to the corresponding selected single-event offer. A dash means no qualifying development candidate, not zero capacity. Results use 100 development and 300 new confirmation seeds per condition; all bounds are pointwise.

### Supplementary Table 11 | Paired recovery intervention at the full eight-hour request

| Eligibility (%) | Revised controller | Original/revised successes | Difference (pp), 95% interval | Window-only rescues | New deadline failures | Holm P |
|---|---|---|---|---|---|---|
| 5 | Per-call MPC | 262/294 | 10.7 [7.3, 14.3] | 32 | 0 | 5.12e-09 |
| 10 | Per-call greedy | 252/294 | 14.0 [10.3, 18.0] | 42 | 0 | 5.91e-12 |
| 10 | Per-call MPC | 252/294 | 14.0 [10.3, 18.0] | 42 | 0 | 5.91e-12 |
| 20 | Per-call MPC | 243/294 | 17.0 [13.0, 21.3] | 51 | 0 | 1.24e-14 |
| 40 | Per-call MPC | 240/294 | 18.0 [13.7, 22.3] | 54 | 0 | 1.67e-15 |
| 60 | Per-call MPC | 224/294 | 23.3 [18.7, 28.0] | 70 | 0 | 2.71e-20 |

All contrasts use the same full request, eight-hour calls, twelve-hour gaps and 300 paired new seeds. The primary contrast is 10% eligibility with per-call MPC. Intervals resample complete seeds 10,000 times; exact McNemar P values are adjusted across all 16 reported controller contrasts, including unchanged comparisons in Source Data. Window-only rescues require original failure confined to window peak relief and revised success on all criteria. New deadline failures identify seeds without an original deadline failure but with one under the revised controller. These counts are paired classifications, not independent samples or a complete decomposition of every gain and loss.

### Supplementary Table 12 | Participation thresholds for development-selected repeated offers

| Eligibility (%) | H/G (h) | Controller | kW | Slack | Reserve | Displacement | Confirmation |
|---|---|---|---|---|---|---|---|
| 5 | 4/8 | Per-call MPC | 2.95 | 1774.02 | 1890.17 | 1909.23 | Pass |
| 5 | 8/8 | Per-call MPC | 2.21 | 2461.22 | 2577.37 | 2733.14 | Pass |
| 5 | 8/12 | Per-call MPC | 2.21 | 2424.90 | 2541.05 | 2697.67 | Pass |
| 5 | 8/16 | Per-call MPC | 2.21 | 2401.01 | 2517.16 | 2671.96 | Pass |
| 5 | 8/16 | Original | 2.21 | 2401.01 | 2517.16 | 2671.96 | Pass |
| 10 | 4/8 | Per-call MPC | 5.90 | 983.87 | 1100.02 | 1119.07 | Pass |
| 10 | 8/8 | Per-call MPC | 4.42 | 1408.00 | 1524.14 | 1679.89 | Pass |
| 10 | 8/12 | Per-call MPC | 4.42 | 1371.25 | 1487.40 | 1644.07 | Pass |
| 10 | 8/16 | Per-call MPC | 4.42 | 1348.78 | 1464.93 | 1619.66 | Pass |
| 10 | 8/16 | Original | 4.42 | 1348.78 | 1464.93 | 1619.66 | Pass |
| 20 | 4/8 | Per-call MPC | 11.80 | 588.41 | 704.56 | 723.65 | Pass |
| 20 | 8/8 | Per-call MPC | 8.85 | 881.08 | 997.23 | 1152.92 | Pass |
| 20 | 8/12 | Per-call MPC | 8.85 | 843.51 | 959.66 | 1116.47 | Pass |
| 20 | 8/16 | Per-call MPC | 8.85 | 823.39 | 939.53 | 1094.30 | Pass |
| 20 | 8/16 | Original | 8.85 | 823.39 | 939.53 | 1094.30 | Pass |
| 40 | 4/8 | Per-call MPC | 22.19 | 475.49 | 591.64 | 629.88 | Pass |
| 40 | 8/8 | Per-call MPC | 16.65 | 783.53 | 899.68 | 1104.54 | Pass |
| 40 | 8/12 | Per-call MPC | 16.65 | 764.19 | 880.33 | 1091.70 | Pass |
| 40 | 8/16 | Per-call MPC | 16.65 | 760.33 | 876.47 | 1075.55 | Pass |
| 40 | 8/16 | Original | 16.65 | 760.33 | 876.47 | 1075.55 | Pass |
| 60 | 4/8 | Per-call MPC | 34.00 | 372.58 | 488.73 | 520.16 | Pass |
| 60 | 8/8 | Per-call MPC | 25.50 | 628.07 | 744.21 | 931.51 | Pass |
| 60 | 8/12 | Per-call MPC | 25.50 | 602.82 | 718.96 | 910.81 | Pass |
| 60 | 8/16 | Per-call MPC | 25.50 | 599.38 | 715.53 | 898.97 | Pass |
| 60 | 8/16 | Original | 25.50 | 599.38 | 715.53 | 898.97 | Pass |

Payments are US$ per offered accounting kW-year, at a proportional 1-MW operating peak, twelve independent four-call series per year, US$25,000 annual site cost and US$0.005/GPU-h/h waiting price. Displacement assumes US$0.25 per deferred GPU-h; reserve uses the stated reference capital assumptions. Each estimate uses every complete confirmation trajectory and 2,000 common annual draws. Source Data additionally retain prices for unselected or failed full-request comparators and the crossed price grid. No continuous-year guarantee or observed operator profitability is inferred.

### Supplementary Table 13 | Retrospective zero-deadline-loss check

| Study | Case | Programme | Fraction | Selected | 1% success | Zero success | Zero lower |
|---|---|---|---|---|---|---|---|
| single | f05 | H4 | 1 | Yes | 295/300 | 295/300 | 0.9662 |
| single | f05 | H8 | 1 | Yes | 292/300 | 292/300 | 0.9533 |
| single | f10 | H4 | 1 | Yes | 295/300 | 295/300 | 0.9662 |
| single | f10 | H8 | 1 | Yes | 292/300 | 292/300 | 0.9533 |
| single | f20 | H4 | 1 | Yes | 295/300 | 295/300 | 0.9662 |
| single | f20 | H8 | 1 | Yes | 292/300 | 292/300 | 0.9533 |
| single | f40 | H4 | 1 | Yes | 295/300 | 295/300 | 0.9662 |
| single | f40 | H8 | 1 | Yes | 292/300 | 292/300 | 0.9533 |
| single | f60 | H4 | 1 | Yes | 295/300 | 295/300 | 0.9662 |
| single | f60 | H8 | 1 | Yes | 292/300 | 292/300 | 0.9533 |
| repeated | f05 | H4G8 | 1 | Yes | 300/300 | 300/300 | 0.9911 |
| repeated | f05 | H8G12 | 0.75 | Yes | 300/300 | 300/300 | 0.9911 |
| repeated | f05 | H8G12 | 1 | No | 294/300 | 289/300 | 0.9409 |
| repeated | f05 | H8G16 | 0.75 | Yes | 299/300 | 299/300 | 0.9852 |
| repeated | f05 | H8G8 | 0.75 | Yes | 300/300 | 300/300 | 0.9911 |
| repeated | f10 | H4G8 | 1 | Yes | 300/300 | 300/300 | 0.9911 |
| repeated | f10 | H8G12 | 0.75 | Yes | 300/300 | 300/300 | 0.9911 |
| repeated | f10 | H8G12 | 1 | No | 294/300 | 288/300 | 0.9369 |
| repeated | f10 | H8G16 | 0.75 | Yes | 299/300 | 299/300 | 0.9852 |
| repeated | f10 | H8G8 | 0.75 | Yes | 300/300 | 300/300 | 0.9911 |
| repeated | f20 | H4G8 | 1 | Yes | 300/300 | 300/300 | 0.9911 |
| repeated | f20 | H8G12 | 0.75 | Yes | 300/300 | 300/300 | 0.9911 |
| repeated | f20 | H8G12 | 1 | No | 294/300 | 289/300 | 0.9409 |
| repeated | f20 | H8G16 | 0.75 | Yes | 299/300 | 299/300 | 0.9852 |
| repeated | f20 | H8G8 | 0.75 | Yes | 300/300 | 300/300 | 0.9911 |
| repeated | f40 | H4G8 | 1 | Yes | 300/300 | 300/300 | 0.9911 |
| repeated | f40 | H8G12 | 0.75 | Yes | 300/300 | 300/300 | 0.9911 |
| repeated | f40 | H8G12 | 1 | No | 294/300 | 294/300 | 0.9618 |
| repeated | f40 | H8G16 | 0.75 | Yes | 299/300 | 299/300 | 0.9852 |
| repeated | f40 | H8G8 | 0.75 | Yes | 300/300 | 300/300 | 0.9911 |
| repeated | f60 | H4G8 | 1 | Yes | 300/300 | 300/300 | 0.9911 |
| repeated | f60 | H8G12 | 0.75 | Yes | 300/300 | 300/300 | 0.9911 |
| repeated | f60 | H8G12 | 1 | No | 294/300 | 293/300 | 0.9575 |
| repeated | f60 | H8G16 | 0.75 | Yes | 299/300 | 299/300 | 0.9852 |
| repeated | f60 | H8G8 | 0.75 | Yes | 300/300 | 300/300 | 0.9911 |

These are unchanged historical ledgers rescored at total missed work ≤1e−7 GPU-h, without reselection or new reliability samples. All 30 originally selected offers retain their success counts. The five unselected full H8G12 comparators remain comparators; the 10% case falls to 288/300 with lower bound 0.9369. Programme G denotes the gap after the event, unlike P (start spacing) in the new study. Yes/No identifies prior development selection.

### Supplementary Table 14 | Frozen structural selections and independent confirmation

| Variant | Programme | Loss rule | kW | Development | Confirmation | Lower |
|---|---|---|---|---|---|---|
| u50d100g10 | H8P16 | 1% | 2.95 | 100/100 | 300/300 | 0.9911 |
| u50d100g10 | H8P16 | zero | 2.95 | 100/100 | 300/300 | 0.9911 |
| u50d100g10 | H8P24 | 1% | 2.95 | 99/100 | 300/300 | 0.9911 |
| u50d100g10 | H8P24 | zero | 1.47 | 100/100 | 300/300 | 0.9911 |
| u50d50g10 | H8P16 | 1% | 1.47 | 100/100 | 300/300 | 0.9911 |
| u50d50g10 | H8P16 | zero | NS | — | — | — |
| u50d50g10 | H8P24 | 1% | NS | — | — | — |
| u50d50g10 | H8P24 | zero | NS | — | — | — |
| u65d100g10 | H4P16 | 1% | 4.42 | 100/100 | 300/300 | 0.9911 |
| u65d100g10 | H4P16 | zero | 4.42 | 100/100 | 300/300 | 0.9911 |
| u65d100g10 | H8P16 | 1% | 4.42 | 100/100 | 299/300 | 0.9852 |
| u65d100g10 | H8P16 | zero | 2.95 | 100/100 | 300/300 | 0.9911 |
| u65d100g10 | H8P24 | 1% | 2.95 | 100/100 | 300/300 | 0.9911 |
| u65d100g10 | H8P24 | zero | 2.95 | 100/100 | 300/300 | 0.9911 |
| u65d50g10 | H8P16 | 1% | 1.47 | 100/100 | 300/300 | 0.9911 |
| u65d50g10 | H8P16 | zero | 1.47 | 99/100 | 300/300 | 0.9911 |
| u65d50g10 | H8P24 | 1% | 1.47 | 100/100 | 300/300 | 0.9911 |
| u65d50g10 | H8P24 | zero | NS | — | — | — |
| u65d50g20 | H8P16 | 1% | 1.47 | 100/100 | 300/300 | 0.9911 |
| u65d50g20 | H8P16 | zero | NS | — | — | — |
| u65d50g20 | H8P24 | 1% | 1.47 | 100/100 | 300/300 | 0.9911 |
| u65d50g20 | H8P24 | zero | NS | — | — | — |
| u80d100g10 | H8P16 | 1% | 5.90 | 99/100 | 298/300 | 0.9801 |
| u80d100g10 | H8P16 | zero | 4.42 | 100/100 | 300/300 | 0.9911 |
| u80d100g10 | H8P24 | 1% | 4.42 | 100/100 | 300/300 | 0.9911 |
| u80d100g10 | H8P24 | zero | 2.95 | 100/100 | 300/300 | 0.9911 |
| u80d50g10 | H8P16 | 1% | 1.47 | 100/100 | 300/300 | 0.9911 |
| u80d50g10 | H8P16 | zero | 1.47 | 100/100 | 300/300 | 0.9911 |
| u80d50g10 | H8P24 | 1% | 1.47 | 100/100 | 300/300 | 0.9911 |
| u80d50g10 | H8P24 | zero | NS | — | — | — |
| u80d50g20 | H8P16 | 1% | 1.47 | 100/100 | 300/300 | 0.9911 |
| u80d50g20 | H8P16 | zero | 1.47 | 100/100 | 300/300 | 0.9911 |
| u80d50g20 | H8P24 | 1% | 1.47 | 100/100 | 300/300 | 0.9911 |
| u80d50g20 | H8P24 | zero | NS | — | — | — |

u is offered utilisation in percent; d100 is reference deadline slack and d50 is halved slack with a one-hour minimum; g is flexible GPU allocation in percent. Eligibility remains 10% and installed hardware remains 576 GPUs. H is duration and P is start spacing, so H8P16 has an 8-h gap. Fractions 0.25, 0.5, 0.75 and 1 multiply the fixed 5.898243186-kW request. All 26 positive endpoint-specific selections passed pointwise confirmation; eight decisions selected no candidate (NS), not zero physical capacity. Bounds are one-sided 95% Wilson limits from 300 new complete scenarios. All 3,200 development/confirmation input variants passed the no-response zero-service gate. The 1% and zero selections are separate and can coincide. These are the earlier coarse-grid selections. The reference four-hour/16-h and eight-hour/16-h products are subsequently refined with new seeds in Table 18.

### Supplementary Table 15 | Full-request structural diagnostics

| Variant | Programme | Success | Supply shortage | Deadline >1% | Mean missed GPU-h |
|---|---|---|---|---|---|
| u50d100g10 | H8P16 | 0/300 | 203 | 300 | 152.04 |
| u50d100g10 | H8P24 | 80/300 | 155 | 162 | 115.98 |
| u50d50g10 | H8P16 | 0/300 | 203 | 300 | 383.46 |
| u50d50g10 | H8P24 | 0/300 | 155 | 300 | 333.47 |
| u65d100g10 | H4P16 | 288/300 | 12 | 0 | 0.00 |
| u65d100g10 | H8P16 | 190/300 | 22 | 93 | 46.96 |
| u65d100g10 | H8P24 | 190/300 | 22 | 96 | 59.15 |
| u65d50g10 | H8P16 | 0/300 | 22 | 300 | 347.27 |
| u65d50g10 | H8P24 | 0/300 | 22 | 300 | 303.06 |
| u65d50g20 | H8P16 | 0/300 | 22 | 300 | 344.90 |
| u65d50g20 | H8P24 | 0/300 | 22 | 300 | 296.45 |
| u80d100g10 | H8P16 | 298/300 | 2 | 0 | 2.37 |
| u80d100g10 | H8P24 | 245/300 | 3 | 52 | 27.76 |
| u80d50g10 | H8P16 | 0/300 | 2 | 300 | 318.65 |
| u80d50g10 | H8P24 | 0/300 | 3 | 300 | 295.44 |
| u80d50g20 | H8P16 | 0/300 | 2 | 300 | 305.47 |
| u80d50g20 | H8P24 | 4/300 | 3 | 296 | 258.87 |

Every row uses the prespecified 5.90-kW comparator, independently of selection. Failure counts are non-exclusive and use 300 complete programmes. Supply shortage means at least one event hour fails the necessary zero-flexible-execution envelope; passing it does not guarantee feasibility. Mean missed work uses the entire episode. The corresponding same-clock final-call electrical outcomes coincide with the fresh-call outcomes in all 16 eight-hour comparisons. Full trial and event tables retain all failure combinations, including 0.1% and zero-loss secondary scores.

### Supplementary Table 16 | Observed-order and permuted-hour timing stress

| Order | GPU % | Programme | kW | 1% success | Zero success |
|---|---|---|---|---|---|
| chronological | 10 | H8P16 | 2.95 | 80/80 | 80/80 |
| chronological | 10 | H8P16 | 4.42 | 63/80 | 63/80 |
| chronological | 10 | H8P16 | 5.90 | 21/80 | 15/80 |
| chronological | 10 | H8P24 | 2.95 | 80/80 | 80/80 |
| chronological | 10 | H8P24 | 5.90 | 30/80 | 29/80 |
| chronological | 20 | H8P16 | 2.95 | 80/80 | 80/80 |
| chronological | 20 | H8P16 | 4.42 | 63/80 | 63/80 |
| chronological | 20 | H8P16 | 5.90 | 22/80 | 17/80 |
| chronological | 20 | H8P24 | 2.95 | 80/80 | 80/80 |
| chronological | 20 | H8P24 | 5.90 | 30/80 | 29/80 |
| permuted | 10 | H8P16 | 2.95 | 80/80 | 80/80 |
| permuted | 10 | H8P16 | 4.42 | 76/80 | 70/80 |
| permuted | 10 | H8P16 | 5.90 | 14/80 | 2/80 |
| permuted | 10 | H8P24 | 2.95 | 80/80 | 80/80 |
| permuted | 10 | H8P24 | 5.90 | 23/80 | 21/80 |
| permuted | 20 | H8P16 | 2.95 | 80/80 | 80/80 |
| permuted | 20 | H8P16 | 4.42 | 76/80 | 71/80 |
| permuted | 20 | H8P16 | 5.90 | 16/80 | 4/80 |
| permuted | 20 | H8P24 | 2.95 | 80/80 | 80/80 |
| permuted | 20 | H8P24 | 5.90 | 20/80 | 19/80 |

Chronological preserves hourly submission counts in eight observed weeks; permuted shuffles whole hours within each week. Each aggregate comprises ten synthetic realisations per week, not 80 independent production weeks. All observed-week results are supplied in temporal_week_summary.csv and Supplementary Fig. 3d displays the chronological primary requests. Work sizes, class allocation and deadlines remain synthetic. No external result retunes a request or establishes a new probability certificate; the direction of permutation effects varies with the request.

### Supplementary Table 17 | Qualified reference products and access-fee decomposition

| Programme | Selected rule | Model kW | Accounting kW | Operating US$/yr | No fee | Shared 2,500 | Full 25,000 |
|---|---|---|---|---|---|---|---|
| H4P16 | 1% + zero | 4.42 | 22.869 | 3991.53 | 174.54 | 283.86 | 1267.74 |
| H8P16 | zero | 2.95 | 15.246 | 4895.28 | 321.09 | 485.07 | 1960.89 |
| H8P16 | 1% | 4.42 | 22.869 | 7471.19 | 326.70 | 436.02 | 1419.90 |
| H8P24 | 1% + zero | 2.95 | 15.246 | 6124.52 | 401.72 | 565.70 | 2041.52 |

New reference workload: 10% eligibility, 65% offered utilisation, reference deadlines and corrected MPC. Twelve complete four-call series/year, 2,000 common annual draws, waiting US$0.005/GPU-h/h and missed-work price zero. The last three columns are US$ per offered accounting kW-year at a proportional 1-MW operating peak. Shared fees do not imply risk pooling. In the earlier single-event f10/H4 ledger, net operating exposure 43.3554 plus fixed allocation 819.9008 reproduces 863.2562 exactly; the fixed share is 94.9777%. All 30 earlier thresholds reconcile within 1e−9. Full component attribution, price grids, annual choices and duration-price boundaries are delivered as ready CSV tables; failed unselected comparators retain diagnostic costs only. This table prices the earlier coarse-grid selections. Table 21 and Figs. 6 and S5 price the later refined products using their own new confirmation ledgers.

### Supplementary Table 18 | Local candidate refinement and independent confirmation

| Program | kW | Dev 1% | Dev zero | Confirm 1% | Confirm zero | Selected |
|---|---|---|---|---|---|---|
| H4P16 | 4.4237 | 100/100 | 100/100 | 300/300 | 300/300 | No |
| H4P16 | 4.7186 | 100/100 | 100/100 | — | — | No |
| H4P16 | 5.0135 | 100/100 | 100/100 | — | — | No |
| H4P16 | 5.3084 | 100/100 | 100/100 | — | — | No |
| H4P16 | 5.6033 | 100/100 | 100/100 | 297/300 | 297/300 | Both |
| H4P16 | 5.8982 | 95/100 | 95/100 | — | — | No |
| H8P16 | 2.9491 | 100/100 | 100/100 | 300/300 | 300/300 | No |
| H8P16 | 3.2440 | 100/100 | 100/100 | — | — | No |
| H8P16 | 3.5389 | 100/100 | 100/100 | — | — | No |
| H8P16 | 3.8339 | 100/100 | 100/100 | — | — | No |
| H8P16 | 4.1288 | 100/100 | 100/100 | — | — | No |
| H8P16 | 4.4237 | 100/100 | 99/100 | 300/300 | 296/300 | Both |

Each grid step is 0.294912159 kW. Both standards selected 5.603331 kW (H4P16) and 4.423682 kW (H8P16). Their confirmation lower bounds are 0.975244 for both four-hour scores, and 0.991062 / 0.970633 for the eight-hour 1% / zero scores. Unselected coarse comparators were prespecified; a dash means not tested on confirmation. The eight-hour upper grid point does not establish a continuous maximum. No confirmatory outcome was used to reselect. These fresh seeds are distinct from Table 14.

### Supplementary Table 19 | Same-scenario exact-window feasibility diagnostics

| Variant | Request kW | Miss allowance | Cases | Supply impossible | Other infeasible | PI feasible | PI rescue |
|---|---|---|---|---|---|---|---|
| u50d100g10 | 5.8982 | 0 | 3 | 2 | 1 | 0 | 0 |
| u50d100g10 | 5.8982 | 1% | 3 | 2 | 1 | 0 | 0 |
| u65d100g10 | 4.4237 | 0 | 3 | 0 | 0 | 3 | 0 |
| u65d100g10 | 5.8982 | 0 | 3 | 2 | 0 | 1 | 1 |
| u65d100g10 | 5.8982 | 1% | 3 | 2 | 0 | 1 | 1 |
| u65d50g10 | 5.8982 | 0 | 3 | 2 | 1 | 0 | 0 |
| u65d50g10 | 5.8982 | 1% | 3 | 2 | 1 | 0 | 0 |
| u65d50g20 | 5.8982 | 0 | 3 | 2 | 1 | 0 | 0 |
| u65d50g20 | 5.8982 | 1% | 3 | 2 | 1 | 0 | 0 |
| u80d100g10 | 5.8982 | 0 | 3 | 0 | 0 | 3 | 0 |
| u80d100g10 | 5.8982 | 1% | 3 | 0 | 0 | 3 | 0 |
| Week 1 | 4.4237 | 0 | 1 | 1 | 0 | 0 | 0 |
| Week 2 | 4.4237 | 0 | 1 | 1 | 0 | 0 | 0 |
| Week 4 | 4.4237 | 0 | 1 | 1 | 0 | 0 | 0 |
| Week 6 | 4.4237 | 0 | 1 | 1 | 0 | 0 | 0 |
| Week 7 | 4.4237 | 0 | 1 | 1 | 0 | 0 | 0 |

Structural cases use seeds 985000–985002 and H8P16. Supply impossible is an analytical certificate; other infeasible is an infeasible HiGHS mixed-integer solve after passing the supply condition. PI rescue means the original causal outcome failed the same service standard while a verified exact-window schedule is feasible. The reference rescue occurs at seed 985002; halved deadlines at the same seed remain infeasible with either 10% or 20% GPU allocation. Five external rows are the first shortage in each affected week, not random samples. All 38 diagnoses are resolved; the first 90-s unresolved run is archived beside its 600-s extension. Exact constraints preserve individual release/deadline groups and the actual event-peak rebound denominator.

### Supplementary Table 20 | Matched submission-count and task-resource-time transfer

| Weight | Order | Request kW | Success 1% | Success zero | Shortage | Baseline failures |
|---|---|---|---|---|---|---|
| job_count | chronological | 2.9491 | 80/80 | 80/80 | 0 | 0 |
| job_count | chronological | 4.4237 | 61/80 | 60/80 | 19 | 0 |
| job_count | permuted | 2.9491 | 80/80 | 80/80 | 0 | 0 |
| job_count | permuted | 4.4237 | 72/80 | 66/80 | 8 | 0 |
| resource_gpu_h | chronological | 2.9491 | 31/80 | 31/80 | 49 | 0 |
| resource_gpu_h | chronological | 4.4237 | 0/80 | 0/80 | 80 | 0 |
| resource_gpu_h | permuted | 2.9491 | 55/80 | 54/80 | 25 | 0 |
| resource_gpu_h | permuted | 4.4237 | 11/80 | 9/80 | 69 | 0 |

Eight observed weeks × ten synthetic realisations per week; 80 is not a count of independent production weeks. All baseline variants had zero missed work. The eight-hour calls have 16-h start spacing. Weekly class totals, synthetic deadlines, community, phase and within-week permutation are matched across weights. Resource time is reconstructed from task resource allocations and launch/completion intervals, not job sojourn time. At 2.949122 kW under chronological resource-time weighting, weekly successes are 1, 6, 1, 0, 3, 0, 10 and 10. All 49 failures trigger immediate shortage; at 4.423682 kW all 80 do. The earlier 986000-series count test is separate: its 4.423682-kW request has 63/80 successes under either score, with weekly shortages 6, 2, 0, 2, 0, 3, 4 and 0. Full per-week cross-scores and every input are delivered.

### Supplementary Table 21 | Physical operating exposure and conditional refined-product costs

| Program | Model kW | Mean waiting GPU-h×h/series | Mean excess missed GPU-h/series | Annual q95 USD | USD/offered kW-year |
|---|---|---|---|---|---|
| H4P16 | 5.6033 | 16491.33 | 0.0000 | 5309.65 | 183.30 |
| H8P16 | 4.4237 | 24509.47 | 0.1996 | 7549.21 | 330.11 |

Means retain all 300 complete confirmation series, including zero-standard failures. Small numerical missed-work residuals are not operational failures at the 1e−7 tolerance. Eight-hour mean excess missed work is 0.1996 GPU-h/series even though the request meets the probabilistic zero-loss qualification. Costs use waiting US$0.005/GPU-h/h, no missed-work charge, no fixed fee, twelve independently sampled four-call series/year and proportional 1-MW accounting. Separate CSVs give all physical percentiles, price combinations and component attribution. The refined equal-value boundary is P8 = (19/15)P4 + 97.931286 when participating; the opt-out floor is P8 = 330.112105 at these prices. Waiting-price changes require recomputing the total-cost quantile rather than adding marginal component quantiles.
