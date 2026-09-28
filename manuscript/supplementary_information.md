<!--
Working supplement, version 0.27, title revision R3, figures revision R7, 2026-09-12.
Independent workload-specific capacity confirmation; power and solver-precision audit.
Supplementary prose clarified on 2026-09-12; numerical results and R7 artwork retained.
Author metadata remain pending.
-->

# Supplementary Information

## Reliable demand-response commitments from AI data centres under service constraints

[AUTHOR NAMES]

## Reader guide

The supplement explains how we constructed the workloads, tested power-reduction requests and calculated participation costs. An offer is the power reduction promised to the grid, in kW. Work eligibility specifies which computing work may wait; offer qualification tests whether a selected request meets both delivery and service requirements.

For the main findings, read Table 22 for the capacity supported by each workload representation, then Table 20 for the weight and hourly-order comparisons. Table 19 distinguishes insufficient available load, infeasible task schedules and failures of the tested controller. Table 21 prices the separately qualified reference products. Tables 23–24 check facility-power accounting and optimisation precision. Note 7 identifies earlier comparisons retained for reproducibility.

| Question | Methods | Displays |
|---|---|---|
| Which work may wait and how power is calculated | 1–3, 8 | Fig. 1; Supplementary Figs. 2, 10; Tables 1–3, 23 |
| How much a single call can request and whether notice helps | 4–5 | Fig. 2; Table 4 |
| Whether the reference workload supports repeated calls | 6 | Fig. 4c,d; Supplementary Fig. 9a; Table 18 |
| What to offer after changing the workload representation | 6 | Fig. 3a; Supplementary Fig. 9b,c; Table 22 |
| How task size and hourly order affect delivery | 6 | Fig. 3d,e; Fig. 4a,b; Table 20 |
| Whether failure comes from supply, deadlines or control | 6 | Fig. 3c; Fig. 4; Table 19 |
| How utilisation, deadlines and preceding calls affect delivery | 6 | Supplementary Figs. 3, 6; Tables 5, 10–16 |
| How GPU allocation affects solar benefits | 7–8 | Fig. 5; Supplementary Figs. 4, 7, 10; Tables 6, 8, 24 |
| How much extra waiting occurs and what payment is required | 9 | Fig. 6; Supplementary Figs. 5, 8; Tables 7, 9, 12, 17, 21 |

## Supplementary Notes

### 1. Which computing work may be deferred

We describe workload composition using requested GPU-equivalents multiplied by each execution span's full duration. Development, other and unknown jobs remain in the denominator. Offline inference accounts for 79.45% of records but 21.52% of requested resource-time: counting jobs and measuring their requested computing work answer different questions.

Low priority identifies a potential source of deferrable work, but the production records do not grant permission to delay it or specify production deadlines. The 5%–20% scenarios authorise the same fraction of low-priority training and offline inference, preserving their relative contributions. The 40% scenario includes additional batch work, and the 60% scenario also changes the business mix. These are stated operator-permission assumptions, rather than measured participation rates.

### 2. Planning estimates and independently tested offers

We use two different calculations. The aggregate perfect-information (PI) programme searches for the largest request R while enforcing cumulative arrivals and due work within each class. It assumes that future inputs are known. However, these aggregate constraints can credit work completed for an early-arriving, late-deadline job towards another job's earlier deadline. They therefore relax the requirement that every job execute within its own time window.

The retained PI values describe this relaxed planning model. Sorting the values from 100 scenarios and taking the second smallest gives the reported 95%/95% tolerance statistic, with achieved confidence 0.96292.<sup>34</sup> The two percentages specify scenario coverage and the confidence required for that coverage statement. That statistical statement concerns the relaxed quantity; it does not establish a feasible schedule for every job.

We test controller offers separately by replaying the complete queue on independent seeds. An offer qualifies when the one-sided 95% Wilson lower bound on joint delivery-and-service success reaches 0.95.<sup>35,36</sup> The strict feasibility checks additionally restrict each work group's execution to its own release-to-deadline window.

### 3. Testing all calls and the work left between them

A call leaves a queue that affects subsequent calls, so four calls in one evolving queue are evaluated as one sequence. The comparison runs each call separately at the same clock time and asks whether all four separate runs succeed. Both conditions therefore use the same all-four-success outcome. Their difference measures the effect of preceding calls under the specified workload and schedule.

Repeated offers selected during development receive a separate independent test. If no tested candidate qualifies, the result applies to that search grid. It does not exclude every positive request. Every replay retains failed sequences and the work-clearance period after the last call.

Overlapping recovery windows impose more than one power ceiling. The earlier controller tracked the live window with the smallest achieved peak-relief ratio, which need not have the lowest allowable power. Limiting power for that window could therefore violate another active window. The revised controller retains a ceiling for every observed call.

We compare the two MPC implementations at the same request and use a greedy-controller check to determine whether improvement depends on MPC's proposed actions. Deadline failures are reported separately because tighter power ceilings can also reduce the processing capacity available to urgent jobs. Operational conclusions use independently tested offers, alongside these failure diagnoses.

The utilisation, deadline and allocation tests start from the corrected controller. They distinguish an event-hour shortage of reducible load from insufficient time to complete jobs; both can occur in one scenario. Requiring zero missed work is stricter than allowing 1%, so offers are selected separately under each rule.

At matched final-call times, the tested electrical outcomes were identical with and without preceding calls. Thus, sequence failures cannot all be attributed to impaired recovery. Reordering the observed hourly submission blocks preserves class totals but changes their timing and alignment with calls; neither order is assumed to be universally harder.

### 4. Installed solar capacity and use of a fixed solar system

PV hosting capacity is the largest rated solar capacity allowed by the model while the GPU facility remains fixed. We optimise each of 100 scenarios and report the smallest capacity for each scheduling mode. The hosting gain is min(flexible) minus min(rigid), rather than the minimum or mean of paired gains.

PV utilisation instead fixes the solar system at 500 kW and divides locally used solar energy by available solar generation. We report the paired change in percentage points and its bootstrap interval. Both analyses require zero missed GPU-hours and use full future information with separately optimised schedules. Their gains therefore describe the planning model, not the causal demand-response controller.

### 5. Separating permission to defer work from GPU allocation

The primary scenarios increase the GPU allocation alongside the permitted-work share, keeping average utilisation similar in both pools. They consequently change both permission and allocation. To isolate allocation, we keep work eligibility at 10% and assign 10%, 20% or 30% of GPUs to the flexible pool. Total work, installed hardware, release times and deadlines remain matched.

Separate power controls retain the same allocation and set the unmeasured rigid-class active-power proxy to 150 or 225 W per GPU. All controls use the request previously selected for the reference 10% configuration. We assess planning statistics and whether that fixed request still succeeds, without selecting a new optimal controller offer for each control.

### 6. From operating records to a required participation payment

For each simulation we compare demand-response operation with the matched no-response run. The operating ledger records their hourly differences in waiting work, energy use, missed work and remaining backlog. Additional waiting exposure sums positive excess backlog over time. Work delayed during calls is kept distinct from work that misses its deadline, and each hour is counted once within a repeated sequence.

Delivery revenue credits only non-negative reductions capped at the requested amount. Work, energy and offered capacity are scaled in proportion to a 1-MW operating peak, after which the annual fixed site fee is added once. Dividing that fee by a small offered capacity can produce a high payment per offered kW. The participation threshold uses the 95th percentile of annual net cost as a stated risk criterion. A low calculated cost cannot make an unqualified request deliverable.

In the reference single-event case, the fixed site fee accounts for about 95% of the participation threshold. To separate that assumption from operating effects, we attribute costs at the same rank in the total-net-cost distribution. The components then add back to the reported total.

Sharing an access fee changes the comparison with not participating. A fee common to two participating products cancels when those products are compared with each other. We therefore show operating costs separately and compare qualified products under explicitly stated duration-specific prices and zero, low or shared fees.

### 7. How the retained earlier comparisons relate to the final results

Tables 14 and 17 retain requests selected on the earlier coarse grid and their associated costs. Tables 18 and 21 use a finer reference grid with new development and confirmation seeds. At 4.423682 kW, the earlier zero-miss development sample had 98/100 successes and the later sample had 99/100. These counts fall on opposite sides of the fixed Wilson selection threshold. The earlier selection of 2.95 instead of 4.42 kW therefore does not establish a stable physical penalty from the stricter service rule.

In Table 18, both service rules select 5.603331 kW for four hours and 4.423682 kW for eight hours. Their capacity ratio is 19/15; the earlier coarse-grid ratio was 1.5. The eight-hour selection is the highest tested candidate, so the continuous maximum remains undetermined.

The 986000-series test uses chronological submission counts. At 4.423682 kW it succeeds in 63/80 runs under either service rule, with all 17 failures encountering immediate shortage. At 2.949122 kW both rules give 80/80 successes (Supplementary Fig. 3d; Table 16). Thus, changing the service score at a fixed request does not explain the difference between those requests.

The 990000-series test in Table 20 instead pairs workload weights and hourly orders. Its results are kept separate from the earlier series and do not select a new workload-specific offer. Figures 2 and 5 and Tables 4 and 8 retain the aggregate PI relaxation described in Note 2. Table 19 uses execution variables restricted to each work group's own time window. This distinction leaves the independently replayed causal queues and the solar optimiser's separate execution variables unchanged.

## Supplementary Methods

### 1. Measuring workload composition and assigning deferral permission

The local jobs_summary.parquet contained 40,522,321 execution-span records. Streaming batches of one million rows were aggregated by workload class and priority, using requested GPU-equivalents times the original duration. The total was 254,980,926.33 requested GPU-h. The audit checked the stored raw work against this product and retained all classes. The source SHA-256 was `95c91a8035197e15f29e9c1d15a9147d07b2a6959b2bb08322cb9f033b029124`. The [production study](https://www.usenix.org/system/files/osdi26-li-suyi.pdf) and [official schema](https://github.com/alibaba/clusterdata/blob/master/cluster-trace-gpu-v2026/docs/schema.md) define the infrastructure scope and execution-span fields. The reported infrastructure excludes dedicated hyperscale foundation-model pretraining clusters.

We allocate deferral permission in stages. Let s_c be class c's share of all requested resource-time, and l_c its low-priority batch share with the same denominator. Low-priority training and offline inference together contribute L = Σl_c = 0.2202814. For f ≤ L, the permitted share in class c is l_c f/L.

Above L, permission extends proportionally to the remaining training and offline-inference work. With B = s_training + s_offline = 0.4094199 and L < f ≤ B, the permitted share is l_c + (s_c − l_c)(f − L)/(B − L). The 60% scenario additionally reallocates f − B = 0.1905801 from online to offline inference and permits all training and offline inference to wait. Other classes remain in the denominator and cannot be deferred. Simulations use the full-precision shares in case_definitions.json rather than the rounded entries in Table 2.

### 2. Matching task inputs and checking operation without demand response

The five configurations share task timing so that changes in eligibility do not introduce different arrival or deadline samples. Development uses seeds 930000–930099 and confirmation uses 960000–960299. Each seed creates a common template at the 60% setting; scaling class-specific GPU-hours produces the other configurations without changing record counts, release times or deadlines. The template samples the existing low-priority training and offline-inference job shapes, including for the explicitly assumed 40% and 60% cases.

Work arrives at 374.4 GPU-hours per hour for 168 h, followed by 48 h without new arrivals. The flexible pool contains round(576f) GPUs; rigid-pool utilisation is 374.4(1 − f)/(576 − round(576f)). Before subsequent analysis, the no-response run must satisfy both task-service requirements and the power limit at the point of common coupling (PCC).

Training deadlines were 2–6 times runtime, clipped to 6–48 h; offline-inference deadlines were 1.5–4 times runtime, clipped to 2–24 h. These are synthetic service rules. Single events began at one of 24 hours between 63 and 140, sampled before testing; exact starts are stored with each scenario. Community demand used a 75:25 residential/office mixed-3A profile, scaled to an 800-kW peak. A common 1,100-kW import rating and no-export rule applied to all cases. Initial development baselines under a 1,000-kW rating exceeded it in three cases at seed 930096; the common rating was raised before PI optimisation or offer selection, and the initial gate results were preserved.

### 3. Measuring GPU power and converting task execution into facility demand

Training and offline-inference loads each run on one GPU and on four GPUs, with three repeated runs per condition. After a 5-s warm-up, read-only nvidia-smi telemetry samples board power and utilisation once per second for 20 s. Runs 1–2 fit the power coefficients; run 3 is withheld to test prediction error.

Within a four-GPU run, we first average each board's time series and then average the four board means. This run mean, rather than each board or each telemetry sample, is the independent observation. Student-t 95% intervals use the two calibration-run means for each workload class. Prediction errors use only the held-out run (Supplementary Table 1).

Facility power retained the execution class,

\[
\begin{aligned}
P^{\mathrm{DC}}_t=\frac{\mathrm{PUE}}{1000}\Big[&N_{\mathrm{node}}p_{\mathrm{node}}+N_{\mathrm{GPU}}p_{\mathrm{idle}}\\
&+N_{\mathrm{rigid}}u_{\mathrm{rigid}}(\bar p_{\mathrm{rigid}}-p_{\mathrm{idle}})
+\sum_c(p_c-p_{\mathrm{idle}})\frac{X_{c,t}}{\Delta t}\Big].
\end{aligned}
\]

where power p is in watts, X is executed flexible GPU-hours and Δt = 1 h. Node overhead applies to all 144 nodes and idle power to all 576 GPUs. The rigid pool contains 518 GPUs at utilisation 0.65050193; its class-weighted active power is 291.42199 W/GPU. The reference flexible mix has 297.90848 W/GPU active power. At PUE 1.2 and idle power 13.935625 W/GPU, the operating peak is 51.840000 + 9.632304 + 112.202165 + 19.764511 = 193.438980 kW: node overhead, all-GPU idle draw, rigid increment and full flexible-pool reference increment, respectively. Thus the compact form \(P^{\mathrm{DC}}_t=P_{\mathrm{fixed}}+\sum_c e_cX_{c,t}\) uses \(P_{\mathrm{fixed}}=173.674469\) kW and \(e_c=\mathrm{PUE}(p_c-p_{\mathrm{idle}})/(1000\Delta t)\).

Jobs were stored by class and remaining deadline at one-hour resolution, up to 48 h. The labels {0, 1, 2, 3, 6, 12, 24, 48} h grouped this state for reporting and observation; they were not the queue's internal time resolution. Execution followed earliest deadline first, could not precede release and could not exceed cumulative arrivals. Work remaining when its deadline expired was counted as missed. Controlled and no-response queues received identical arrivals.

Idle board power is 13.935625 W/GPU, and node overhead is assumed to be 300 W. Online, development, other and unknown work use an engineering active-power proxy of 300.022174 W/GPU, with separate 150-W and 225-W controls. Rigid demand uses the class-weighted mean. Online response latency is not simulated, so the batch deadline check does not test online-service latency requirements.

The controller retains the 63-dimensional firm_v5 observation interface. Its six-hour forecast and queue features expose only causally available information. In saved outputs, compute_debt_kwh describes the whole controlled queue, whereas excess_queue_energy_kwh subtracts the paired no-response queue. Only the latter directly measures extra queued work relative to that baseline.

### 4. Deciding whether a response succeeds and whether an offer qualifies

A simulation succeeds only when it satisfies all six electrical-delivery and computing-service criteria below. Capacity, event duration, advance notice and controller are fixed before testing. Delivered power is the non-negative PCC reduction relative to the matched no-response run, capped at the request. Both average delivery and delivery in every event hour must pass. Peak relief is evaluated across the event and its following 24-h recovery window.

| Criterion | Headline threshold | Operational interpretation |
|---|---:|---|
| Mean delivery | ≥0.95 | mean capped baseline-relative reduction across all event intervals divided by R |
| Minimum interval delivery | ≥0.95 | every event hour delivers at least 0.95R |
| Deadline-miss fraction | ≤0.01 | expired eligible GPU-hour work divided by total arriving eligible work |
| Rebound ratio | ≤0.25 | largest post-event excess PCC load divided by peak event reduction |
| Event-and-recovery peak relief | ≥0.50 | baseline peak minus controlled peak over the event plus 24-h recovery window, divided by R |
| Terminal-backlog fraction | ≤0.02 | positive controlled-minus-baseline backlog at the end of the 48-h tail divided by total eligible arrivals |

We record every criterion that fails in a scenario. For example, low average delivery can occur together with an inadequate event hour, and either can accompany excessive rebound or insufficient window-wide peak relief. These categories can overlap. Failure to identify a recovery time within the window is retained as an additional diagnostic, not a seventh qualification criterion.

The utilisation, deadline and allocation tests also require zero missed eligible work, allowing only a numerical tolerance of 10<sup>−7</sup> GPU-h. Both response and no-response runs must meet this rule; electrical criteria and the terminal-backlog threshold are unchanged. A no-response baseline failure counts as failure and is retained. We also report a 0.1% missed-work threshold without using it for offer selection. Rescoring previously selected offers under the zero-miss rule is labelled retrospective because it adds no new qualification sample.

For the relaxed PI calculation, binomial inversion at q = 0.95 and confidence 0.95 selects the second-smallest of 100 optima. Controller tests use a one-sided 95% Wilson lower bound with z = 1.6448536. The same lower-bound threshold, 0.95, applies during development and confirmation. Each condition has 100 development or 300 confirmation seeds; extra notice settings and calls reuse those seeds rather than add independent observations.

All 20 notice comparisons have identical paired success flags, so we report that agreement directly. Repeated-minus-separate-call differences use 10,000 paired bootstrap resamples of 300 seeds. Renewable mean differences use 10,000 paired resamples of 100 seeds. Each interval or qualification statement applies to its specified comparison or offer, rather than simultaneously to every reported condition.

### 5. Controller information, recovery limits and single-offer selection

The robust model predictive controller (MPC) plans over six hours using its existing historical-arrival uncertainty range, objective weights and information on released jobs. Development identified a mismatch between its recovery cap and the scoring rule. The old cap allowed power to exceed baseline by 0.25R, but scoring divided rebound by the actual peak reduction, which could be only 0.95R.

The corrected cap uses 0.25 × 0.95R and retains the event-delivery and full-window peak-relief limits. If converting an action to float32 would cross an electrical limit, the action is rounded towards zero. Regression checks cover the rebound denominator, rounding at event boundaries and unchanged actions outside event and recovery windows. This correction creates a new controller version, evaluated independently of the original frozen results.

For each duration, development tests requests at 50%, 75%, 90% and 100% of the development relaxed-PI statistic. The largest candidate meeting the Wilson rule is fixed before confirmation. After the final controller correction, 300 previously unseen seeds test that fixed offer. Earlier controller outputs remain diagnostic records. Confirmation results are never used to replace a failed offer with a smaller one.

### 6. Repeated-call tests, workload comparisons and failure diagnosis

#### 6.1 Call timing and the comparison without preceding calls

H denotes event duration and G the gap from one event's end to the next event's start. In the original-controller study, four calls started at 63 + j(H + G), j = 0, 1, 2, 3, with (H,G) = (4,8) or (8,12) h. Development tested 25%, 50%, 75% and 100% of the selected single-event offer, without assuming monotonic success as the request increased.

Confirmation seeds 960000–960299 tested the original single-event offer repeated four times and four separate calls at the same clock times. Each comparison used the same full-capacity no-response schedule. The protocol also provided for independent confirmation of a repeated offer selected during development, but no candidate passed that development screen. This study evaluates two specified programmes; it does not establish performance for every recovery gap or continuous operation throughout a year.

The recovery-controller comparison uses (H,G) = (4,8), (8,8), (8,12) and (8,16) h, again starting at hour 63. Each call has a 24-h recovery window. When a later call ends, the preceding call's recovery constraint remains active for max(0, 24 − H − G) h. This overlap is zero at H = 8 h and G = 16 h.

Changing G also shifts later calls to different clock times. These comparisons therefore change both spacing and alignment with the workload. The final recovery ends by hour 167, before arrivals stop at hour 168. Every replay continues through all 216 h, including the period used to clear remaining work.

#### 6.2 Enforcing every recovery window that is still active

For call j, B_j(t) is the largest baseline PCC power observed so far within its event-and-recovery window, and R_j is the request. Before applying a proposed control action, the power-limit layer checks all active ceilings B_j(t) − 0.5R_j and uses the lowest. It also enforces event delivery and the recovery rebound ceiling baseline(t) + 0.25 × 0.95R_j.

Let F(t) be PCC demand excluding flexible execution, and A(t) the power added when the flexible pool receives its full allocation. The extra allocation cap is clip[(min_j(B_j(t) − 0.5R_j) − F(t))/A(t), 0, 1]. Here clip limits the calculated fraction to the allowed range. Actions are rounded towards the feasible side. The controller obtains remaining call duration from the current observation and removes a call only after its 24-h recovery ends.

The running baseline peak may still be below its eventual value, so this rule can be conservative. If the required ceiling is below F(t), stopping all flexible work cannot meet it. Conversely, satisfying a power ceiling does not establish that urgent jobs will meet their deadlines.

The extension reused 100 previously examined development seeds (930000–930099); four of these also informed an exploratory pilot. The frozen protocol then enumerated 10,100 development replays: five workload configurations, two MPC versions, four programmes, a full-only four-hour candidate and 50%, 75% and 100% eight-hour candidates, plus 100 full-request greedy diagnostics at 10% eligibility and (8,12). The largest candidate with one-sided 95% Wilson lower bound at least 0.95 was selected. The frozen selection scheduled 13,800 replays on 300 new confirmation seeds (970000–970299). For each configuration, method and programme, confirmation tested the selected offer or the full-request comparator if none was selected. Full-request comparisons for both MPC versions at (8,12) and the greedy diagnostic were additionally retained. No confirmation result was pooled with the earlier 960000–960299 set or used for reselection. Every full series, including all failures, was analysed.

The primary intervention contrast is the full-request original versus per-call-recovery MPC at 10% eligibility and (8,12). Paired success differences use 10,000 resamples of complete seeds; exact McNemar tests receive Holm correction across all controller contrasts reported in the source table. Non-exclusive failure families and paired rescue/loss counts are also retained. Qualification is pointwise for each frozen candidate. A selected candidate that fails confirmation would remain failed, with no test-set replacement. The illustrated trace is the lowest development seed for which the full-request original fails and the revised MPC passes; this transparent illustrative selection is separate from inference on all confirmation seeds.

#### 6.3 Changing utilisation, task deadlines and GPU allocation

These tests keep 10% work eligibility and 576 installed GPUs. Offered utilisation, defined as total work divided by installed GPU-hours, is 50%, 65% or 80%. Deadline slack is retained or halved, with a one-hour floor. The flexible pool receives 10% of GPUs; tight-deadline controls also allocate 20% at 65% and 80% utilisation.

The final call starts at hour 111 plus a seeded uniform integer from 0 to 23. Earlier calls are placed 16 or 24 h apart going backwards from that time. All eight variants test eight-hour calls; the reference also tests four-hour calls at 16-h start spacing. A separate run retains only the eight-hour final call at the same clock time. All recovery windows finish within the 168-h arrival period, followed by 48 h for clearance.

Development seeds 984000–984099 and confirmation seeds 985000–985299 produce 7,600 and 13,200 full replays, respectively. Two pilot seeds are excluded from these analyses.

Structural contrasts resampled 300 complete paired scenario seeds 5,000 times. Exact McNemar tests were Holm-adjusted over the 36 binary structural contrasts; the 16 additional matched-target electrical contrasts formed a separate family. The zero-miss and 1% offer tests each retained the pointwise one-sided 95% Wilson lower-bound criterion of 0.95. Multiple successful selections do not create a simultaneous confidence guarantee. Submission-order comparisons retained the observed week as the external sampling unit and were not assigned binomial certificates from pooled synthetic realisations.

The available-load check asks whether the baseline contains enough flexible power to deliver the request in every event hour. We subtract community demand and idle-plus-rigid data-centre demand from matched baseline PCC power, then compare the remainder with 0.95 times the request. A smaller remainder proves that stopping all flexible execution would still be insufficient. Passing this check leaves deadlines and other constraints to be tested.

Deadline and terminal-backlog criteria apply to the full 216-h episode. For the final-call comparison alone, we score only electrical conditions, align the clock time exactly and use event 0 in the separately run call. All 16 paired electrical differences are zero. This call-specific comparison is kept distinct from success of the entire sequence, which also includes task service.

#### 6.4 Using observed hourly submissions and changing their order

The first workload-timing test uses hourly submission counts from eight consecutive 168-h blocks of the Alibaba 2020 GPU trace.<sup>28</sup> Those counts determine how each week's synthetic class-specific work is distributed across hours. Weekly class totals and the reference deadlines remain fixed. A paired input reorders complete hourly blocks within the same week.

Ten synthetic realisations per week cross the two orders, 10%/20% GPU allocations and five prespecified programme–request combinations, giving 1,600 replays without retuning. Results are shown by observed week, with descriptive totals across 80 realisations per condition. The observed production records cover eight weeks, rather than 80 newly observed weeks.

The timing input was the processed Alibaba 2020 job-submission table (714,903 GPU jobs), using trace hours 168–1511 inclusive. The eight 168-h weeks supplied hourly counts; each week’s class-specific synthetic total was normalised to the unchanged offered work. A whole-hour permutation preserved the marginal hourly volumes and the exact class–deadline totals. Seeds 986000 + 100w + r, for week w = 0,…,7 and realisation r = 0,…,9, generated paired inputs. Frozen tests used request fractions 0.5, 0.75 and 1 at eight-hour/16-h spacing, and 0.5 and 1 at eight-hour/24-h spacing. No external result selected a new fraction. Submission counts preserve one observed temporal feature; they do not supply real GPU-hour volumes, deadlines or job dependencies. All 320 timing input variants passed the baseline service gate.

#### 6.5 Refining the reference four- and eight-hour offers

The reference workload and corrected controller are fixed while the request grid is made finer. H denotes event duration and P the interval between event starts. Relative to the unchanged 5.898243186-kW request, H8P16 tests fractions 0.50–0.75 and H4P16 tests 0.75–1.00, both in steps of 0.05.

Seeds 988000–988099 select an offer separately for each service criterion. Those choices are fixed before confirmation on seeds 989000–989299. Confirmation tests only the selected candidates and prespecified coarse-grid comparators; it does not select replacements. Both service criteria select the highest tested eight-hour candidate, so this grid does not locate the continuous maximum. Earlier seeds are kept separate.

#### 6.6 Checking whether any schedule can satisfy the request

The strict perfect-information test asks whether a feasible schedule exists when all future inputs are known. It fixes the request, four call times, baseline and 24-h recovery windows. Execution variables are allowed only between each class/release/deadline work group's own release and deadline. Executed, missed and terminal work must sum to each group's supplied work.

The model retains GPU and PCC limits, 95% hourly and capped-mean delivery, 25% rebound relative to actual peak event reduction, 50% full-window peak relief and the original terminal allowance. Binary peak selectors represent the rebound denominator exactly. HiGHS solves the resulting mixed-integer feasibility problem.

The 33 prespecified structural cases cover five configurations, three previously used seeds and two service standards, plus three reference 4.42-kW checks. Five affected external weeks each supply an additional first-shortage case. These selected cases diagnose mechanisms rather than estimate failure prevalence. All 11 feasible schedules pass independent work-group and electrical checks. One solve unresolved at 90 s is retained and classified as infeasible after extending only its time limit to 600 s. Existence of a full-information schedule does not establish that the causal controller can implement it.

#### 6.7 Comparing job counts with task resource-time

For each processed job, we reconstruct requested GPU-seconds by summing requested GPU-equivalents × launch-to-completion duration over its terminated tasks with positive resource requests.<sup>28</sup> This matches all 714,903 processed jobs. By contrast, multiplying the job's total requested GPUs by its submission-to-completion time disagrees for 131,379 jobs. Job duration includes waiting before execution and does not replace the sum of task-level resource-time.

The comparison uses trace hours 168–1511; the processed time origin is 542,323 s after the raw origin. Within each week, we allocate the same class-specific work total across hours using either submitted job counts or submitted task resource-time. Each seed uses matching synthetic job classes, deadlines, community demand, call times and whole-hour permutations. Seeds are 990000 + 100w + r, with eight weeks and ten realisations per week.

Fixed 2.95- and 4.42-kW requests produce 640 complete replays. All 320 no-response input variants pass zero-miss service, and none is excluded. Pooled counts remain descriptive. Requested resource-time measures allocated work rather than sensor-observed busy GPU time; task divisibility and synthetic service rules remain model assumptions.

#### 6.8 Selecting and independently testing an offer for each workload representation

This experiment asks which request each workload representation can support within the fixed eight-week dataset. Each new seed independently selects one week with equal probability. Fresh job templates, community conditions and a random final-call phase are paired between submission-count and task-resource-time weights. Four eight-hour calls start 16 h apart, with zero advance notice.

Development seeds 1010000–1010099 test 1/64, 1/32, 1/16, 1/8, 1/4, 3/8, 1/2, 3/4 and 1 times 5.898243186 kW. For each weighting and service criterion, the largest candidate with a one-sided 95% Wilson lower bound ≥0.95 is fixed. Confirmation seeds 1011000–1011299 then test that offer and a prespecified 1/2-request comparator, retaining any baseline failures.

The 1,800 development and 900 confirmation replays do not reuse the earlier 80 realisations to choose offers. The probability statements apply to independent model draws from the fixed eight-week empirical mixture, rather than additional observed production weeks.

### 7. Calculating solar hosting capacity and use of a fixed solar system

We use each configuration's own power model at its original facility size. The hosting calculation maximises rated PV capacity subject to the following limits: curtailment must be ≤5%, missed work zero, terminal backlog ≤2% and grid imports ≤1,100 kW, with no exports. A separate calculation fixes PV capacity at 500 kW. It prioritises service, then local solar use, grid imports and battery throughput, retaining a 10<sup>−5</sup>-kWh tolerance for solar use.

The battery has 100-kW charge/discharge power and 200-kWh energy capacity. Charge and discharge efficiency are each 0.95, and initial and final state of charge are both 50%. Binary constraints prevent simultaneous charging and discharging. The first 100 confirmation seeds are paired across rigid and flexible scheduling, with and without the battery. All solution statuses and missed work are retained when reporting the capacity supported across all scenarios.

For the fixed 500-kW system, objectives are solved in priority order: maximise local PV use, then minimise grid imports, then minimise battery throughput. Each later step keeps the preceding optimum within 10<sup>−5</sup> kWh. Rigid and flexible schedules share 100 inputs; mean utilisation gains use 10,000 paired bootstrap resamples with seed 20260911.

Without storage these models are continuous linear programmes, so a relative mixed-integer programming (MIP) gap does not determine their precision. The stricter numerical check repeats all 800 primary 10% PV optimisations and 200 no-storage GPU20 hosting optimisations. HiGHS<sup>37</sup> uses relative and absolute MIP gaps of 10<sup>−7</sup>, with primal, dual and MIP feasibility tolerances of 10<sup>−8</sup>. Each solve has one thread and a 120-s limit.

All fixed-PV problems finish. Of the flexible-storage hosting problems, 34 reach the time limit. Their feasible capacities and upper bounds are retained; none changes the minimum hosting boundary across the 100 scenarios. Table 24 reports these optimisation bounds separately from sampling uncertainty.

### 8. Changing GPU allocation, rigid power and fixed node overhead

Four controls are specified before their results are examined, all around the 10% eligible-work configuration. Two allocate 20% or 30% of GPUs to the flexible pool; two change the rigid-class active-power proxy to 150 or 225 W. Other inputs, seeds and event times are matched.

Each control includes 300 no-response service checks, 100 PI scenarios at each duration, 300 fixed-offer tests at each duration and 100 paired renewable scenarios. Costs use the same fixed requests. These controls isolate selected assumptions; together with the five eligible-work scenarios, they do not vary all model parameters jointly.

Node overhead is set to 150, 300, 450 or 600 W/node, giving operating peaks of 167.52, 193.44, 219.36 and 245.28 kW (Supplementary Fig. 10; Table 23). We retain all 600 independently confirmed reference schedules. For each overhead setting, PUE × 144 × (p_node − 300)/1000 is added to both response and no-response power, and electrical and PCC constraints are rescored.

This calculation tests whether the existing schedules remain feasible after the same constant power offset is added to both runs. It does not rerun the controller or select new offers. Baseline-relative reductions, task backlog and waiting remain unchanged; absolute PCC headroom and the conversion to a 1-MW accounting scale change.

### 9. Recording operating differences and calculating participation payments

We record hourly differences between response and matched no-response operation from the first event to the end of the simulation. Additional waiting exposure sums positive excess backlog multiplied by the one-hour time step. It measures how much work waits longer and for how long. Incremental energy is the signed difference in PCC electricity use, so energy reductions retain a negative sign.

Deferred work sums positive execution shortfalls during event hours. It is recorded separately from work that misses its deadline. Every hour appears once in a repeated-call sequence. Failed sequences remain in the records, including their extra missed work and terminal backlog.

One annual draw samples 50 complete confirmation episodes for single-event service, or 12 complete four-call sequences for repeated service. Every price setting uses the same 2,000 bootstrap draws. All 300 available trajectories enter the sampling pool, including failures.

Work, energy and offered capacity are multiplied by 1000 divided by the configuration's operating peak. This is proportional accounting at a 1-MW peak, not a new facility simulation. The US$25,000 annual site fee is then added once. For each draw we calculate annual net cost, sort those costs and use their 95th percentile. The required payment is max(0, that percentile divided by accounting offered kW).

Reference prices are US$0.10/kWh for electricity, US$50/MWh for delivered energy capped at the request, and US$0.005/GPU-h/h for additional waiting.

The reserve-cost scenario assumes 0.15 kW of reserved PCC capacity per offered kW. Annualisation uses US$2,500 per reserved kW, an 8% discount rate, four-year economic life, 10% salvage value and 3% annual operation and maintenance. This prices an assumed reserve allowance; it is not a GPU purchase or wear estimate.

We compare incremental costs of demand response and matched no-response operation using the same installed, powered GPU fleet over the same evaluation period. GPU quantity, depreciation method, expected useful life and salvage value are held fixed, so existing-fleet depreciation cancels in the paired comparison. Task delay, recovery-period operating differences and service losses are evaluated separately under the stated valuation assumptions. Long-term thermal cycling and hardware degradation are outside the model. The short-duration power measurements do not assess these effects on GPU lifetime. Economic results therefore remain conditional on assigning no additional hardware-degradation cost to demand response.

Displaced-work scenarios separately value deferred work at US$0.25 or 0.50/GPU-h, with 0.25 used as the main illustration. Sensitivity grids cover waiting prices 0, 0.001, 0.005 and 0.01; fixed site fees 10,000, 25,000 and 50,000; displaced-work values 0, 0.25, 0.5 and 1; missed-work prices 0, 0.25 and 1; and reserve lives of 3–6 years. Contract-specific non-performance penalties are not priced. The original price-source register is archived, and all these amounts remain scenario assumptions rather than observed operator accounts.

The recovery-controller comparison uses the same hourly cost definitions, with twelve independent four-call sequences per year and 2,000 common annual draws from the new confirmation set. All 300 sequences are retained. The crossed price grid combines waiting prices 0, 0.005 and 0.01, annual site fees US$10,000, 25,000 and 50,000, and displaced-work values US$0, 0.25 and 0.50 per deferred GPU-h.

Reserved-capacity costs retain the four-year reference assumptions. This comparison does not repeat the earlier missed-work-price or reserve-life screens. Source tables distinguish offers selected during development and passing independent qualification from failed or unselected comparators, even when a comparator has low calculated cost.

Cost components are evaluated at the same annual draws and the same interpolation weights used for the 95th percentile of total net cost. We do not add the separate 95th percentiles of individual components, which need not occur in the same annual draw.

The fee comparison combines annual site fees US$0, 1,000, 2,500, 5,000, 10,000 and 25,000; waiting prices US$0, 0.005 and 0.01/GPU-h/h; and missed-work prices US$0 and 1/GPU-h. Sharing a US$25,000 fee among ten or five resources gives US$2,500 or 5,000 per resource. This shares the fee only; no reliability or diversification benefit is added.

For qualified product j, K_j is its offered capacity after scaling and O_j its 95th-percentile annual net operating cost. At capacity price P_j and fixed fee F, its fifth-percentile annual net value is P_j K_j − O_j − F. We compare this value across qualified duration products and against zero for not participating. The price boundaries are calculated from these costs and assumptions, rather than estimated from market tariffs.

## Supplementary Figures

### Supplementary Figure 1 | From production records and power measurements to response qualification, solar analysis and economic accounting

![Supplementary Figure 1](../paper/v0.27/figures/supplement/S01/AIDRBench_Supplementary_Figure_1.png)

**a,** Observed workload shares and the assumed permission to defer tasks determine the synthetic job templates and GPU allocation. An hourly queue then tracks arrivals, execution and deadlines, and the power model combines data-centre and community demand at the PCC. **b,** Development simulations select a request; a separate confirmation set tests it. Hourly operating records supply the participation-cost calculation. Solar and storage planning is a separate optimisation with full future information. Arrows indicate inputs passed between calculations.

### Supplementary Figure 2 | GPU board-power measurements, calibration and held-out validation for training and offline inference

![Supplementary Figure 2](../paper/v0.27/figures/supplement/S02/AIDRBench_Supplementary_Figure_2.png)

**a,** All 30 per-board run averages from one- and four-GPU training and offline inference. Filled points are fitting runs 1–2; open points are held-out run 3. Boards in one run are not independent replicates. **b,** Active-power estimates and 95% Student-t intervals from two independent four-GPU run means per class. Held-out overall MAE is 3.80 W/GPU. Node overhead and online-serving power were not measured by this calibration.

### Supplementary Figure 3 | Local offer-grid screening, supply and deadline failures, and the earlier weekly workload-transfer comparison

![Supplementary Figure 3](../paper/v0.27/figures/supplement/S03/AIDRBench_Supplementary_Figure_3.png)

**a,b,** Development success-probability lower bounds for each four- and eight-hour request on the finer reference grid. Each point uses 100 scenarios under both service rules and a one-sided 95% Wilson bound. The dashed line is the 0.95 selection threshold. The largest tested eight-hour request is selected, leaving the continuous maximum undetermined. **c,** Counts of immediate supply shortage and more than 1% missed work in 300 full-request control scenarios; the two failures can occur together. **d,** The earlier 986000-series test using observed submission counts in their original hourly order. Bars separate success from immediate shortage at 4.42 kW; markers show successes at 2.95 kW. The two service rules give identical scores at each request. Each of eight observed weeks has ten synthetic realisations, so pooled counts are descriptive. Note 7 explains the earlier design. Table 15 and Source Data retain the identical paired final-call outcomes.

### Supplementary Figure 4 | Solar gains and fixed-request delivery across workload eligibility, GPU allocation and rigid-load power assumptions

![Supplementary Figure 4](../paper/v0.27/figures/supplement/S04/AIDRBench_Supplementary_Figure_4.png)

**a,** Flexible minus rigid all-scenario PV hosting capacity across the five eligibility scenarios, with and without BESS; each capacity is the minimum over 100 scenarios. **b,** Paired gain in utilisation of a fixed 500-kW PV system; points are means and whiskers are 95% paired bootstrap intervals. The intervals cover sampling, not optimisation error; small storage contrasts remain unresolved at solver precision. **c,** Four- and eight-hour success at unchanged primary single-event requests across allocation and rigid-power controls, with one-sided 95% Wilson lower bounds from 300 scenarios. **d,** Corresponding gains in all-scenario PV hosting over 100 paired scenarios. Panels c,d retain 10% eligibility and vary only GPU allocation or the stated rigid-power proxy. PV schedules use full information and zero missed work; hosting differences are differences of minima, not mean effects or confidence intervals. The 10% primary points and no-BESS GPU20 hosting point use the strict repeat audit; other points retain the original settings (Table 24).

### Supplementary Figure 5 | Four- versus eight-hour service choice under waiting and missed-work valuations and access fees

![Supplementary Figure 5](../paper/v0.27/figures/supplement/S05/AIDRBench_Supplementary_Figure_5.png)

**a,** Difference in fifth-percentile annual net value between the eight- and four-hour products when capacity prices are equal and waiting and access fees are zero. Zero marks equal value for the two participating products. **b,** Required compensation when missed work is valued at zero or US$1/GPU-h, with the reference waiting price and zero site fee. These refined offers were qualified using zero missed work as the success criterion, but qualification permits occasional failed scenarios; their costs remain included. **c,** Fifth-percentile annual net value at US$250/kW-year and the reference waiting price, with zero, shared or full access fees. **d,** Eight-hour price needed to be at least as valuable as both four-hour participation and not participating. All panels use 300 confirmation sequences, 10% eligible work, 65% offered utilisation, reference deadlines and 16-h start spacing. Annual accounting and energy prices follow Fig. 6. Fee sharing adds no assumption about pooled reliability.

### Supplementary Figure 6 | Response delivery and deadline compliance across utilisation, task deadlines, GPU allocation and call schedules

![Supplementary Figure 6](../paper/v0.27/figures/supplement/S06/AIDRBench_Supplementary_Figure_6.png)

**a,b,** Numbers of scenarios satisfying all delivery and service criteria when the missed-work limit is 1% or zero. **c,d,** Numbers encountering an event-hour supply shortage or more than 1% missed work. Each cell contains 300 confirmation scenarios at 10% work eligibility and the same 5.898243-kW, eight-hour request. Columns compare a separate final call at the matched clock time with four-call sequences starting 16 or 24 h apart. Rows change utilisation, deadline slack and flexible GPU allocation. Each setting has its own matched baseline, and all no-response runs pass service checks. Numerals are counts; blue or orange intensity increases from zero to 300. Failure types can overlap. The fixed request is a common stress test, not a separately selected offer for each row. Changing spacing also moves preceding calls to different times. Tables 14–15 and Source Data retain complete outcomes and selected-offer tests.

### Supplementary Figure 7 | Solar hosting capacity, curtailment and grid imports under rigid and flexible scheduling, with and without storage

![Supplementary Figure 7](../paper/v0.27/figures/supplement/S07/AIDRBench_Supplementary_Figure_7.png)

**a,b,** Absolute PV hosting capacities without and with BESS, for rigid and flexible schedules. Each point is the minimum over 100 scenarios. **c,d,** Arithmetic mean curtailed PV energy and grid imports per modelled horizon for a fixed 500-kW PV installation, over the same 100 paired scenarios. Blue and green identify no BESS and BESS; dashed circles and solid squares identify rigid and flexible operation. Grid-import curves nearly coincide at the displayed scale; no uncertainty or significance is inferred from their separation. These absolute outcomes complement the paired gains and bootstrap intervals in Supplementary Fig. 4a,b. Lines connect evaluated eligibility fractions only. The 40% and 60% cases retain the additional business assumptions listed in Supplementary Table 2; configuration-dependent demand also changes across fractions, so within-case rigid–flexible comparisons isolate scheduling. All schedules use full information and zero missed work. Means and minima are descriptive summaries, and do not establish the delivery reliability of a causal controller; small storage contrasts remain limited by optimisation precision. All scenario values are retained in Source Data.

### Supplementary Figure 8 | Single-event participation thresholds across hardware economic lifetime, work value, waiting costs and site fees

![Supplementary Figure 8](../paper/v0.27/figures/supplement/S08/AIDRBench_Supplementary_Figure_8.png)

**a,** Reserved-headroom cost with a hardware economic life of three to six years. **b–d,** Effective displaced-work value, waiting valuation and fixed site fee varied separately without an added reserve cost. All panels retain the 10% eligibility single-event four- and eight-hour offers of 5.898243 kW, supported by 295/300 and 292/300 joint successes under the 1% missed-work standard. Annual accounting draws 50 independent complete event-and-recovery ledgers with replacement, scales proportionally to 1 MW and retains failures. Unvaried prices are US$0.005/GPU-h/h waiting, US$25,000/year site fee, zero displaced-work value and zero missed-work price; electricity and delivered-energy prices follow Table 9. Points are 95th-percentile annual-net-cost thresholds, not confidence limits. Lines join evaluated values without added observations. Economic life affects assumed reserve amortisation, not measured hardware ageing or failure. These single-event scenarios must not be substituted for the independently qualified repeated products and twelve-series accounting in Fig. 6. Source Data also retain the missed-work-price check, which does not visibly change these single-event thresholds.

### Supplementary Figure 9 | Offer selection and independent delivery qualification under reference workloads and the eight-week empirical distribution

![Supplementary Figure 9](../paper/v0.27/figures/supplement/S09/AIDRBench_Supplementary_Figure_9.png)

**a,** Independent confirmation of the reference four- and eight-hour offers, 5.60 and 4.42 kW, with 300 scenarios each. **b,** Development lower bounds for all candidate requests under submission-count and task-resource-time weighting, using 100 new model draws per point. Solid circles use the 1% missed-work criterion and dashed squares use zero missed work. Both criteria select the same offer within each weighting scheme. **c,** Independent confirmation of those selected offers and the fixed 2.95-kW resource-time comparator, with 300 new draws each. Points show success fractions and lower whiskers the one-sided 95% Wilson bounds; the dashed line is the 0.95 qualification threshold. Panels b,c draw from an equal mixture of eight fixed observed weeks, with paired synthetic tasks and call phases. The calls last eight hours and start 16 h apart. Panel a uses a separate reference workload distribution; model draws in b,c do not add observed production weeks.

### Supplementary Figure 10 | Data-centre peak-power decomposition, fixed node-overhead sensitivity and solar solver-precision checks

![Supplementary Figure 10](../paper/v0.27/figures/supplement/S10/AIDRBench_Supplementary_Figure_10.png)

**a,** Exact components of the 193.438980-kW primary operating peak; PUE applies to all components. **b,** The unchanged 5.898243-kW single-event offer as a share of peak as node overhead varies. Points are deterministic accounting values, not replicate estimates. Re-scoring all 600 reference repeated schedules preserves their success flags at each overhead; Table 23 gives PCC headroom. **c,d,** Each point compares the original and strictly solved flexible-minus-rigid utilisation contrast for one of 100 paired primary scenarios, without and with BESS. The dashed diagonal marks equality, not a fitted model. c is a continuous LP and its tiny gain is unchanged; d resolves to numerical zero after tightening MIP and feasibility tolerances. The final lexicographic difference and primary objective bounds are reported separately in Table 24. No statistical inference is assigned to pointwise solver agreement.

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

| Work permitted to wait (%) | Online work (%) | Eligible training (%) | Eligible offline (%) | Flexible GPUs | Operating peak (kW) |
|---|---|---|---|---|---|
| 5 | 54.50 | 0.26 | 4.74 | 29 | 189.94 |
| 10 | 54.50 | 0.52 | 9.48 | 58 | 193.44 |
| 20 | 54.50 | 1.03 | 18.97 | 115 | 200.10 |
| 40 | 54.50 | 18.51 | 21.49 | 230 | 212.16 |
| 60 | 35.44 | 19.42 | 40.58 | 346 | 226.17 |

All workload percentages use total offered GPU-hours as denominator. Total work is 374.4 GPU-h/h and installed hardware is 576 GPUs. The 40% case expands batch permission; 60% changes business composition. Mean utilisation is approximately 65% in each primary pool; operating peak is a model coefficient, not an observed event peak.

### Supplementary Table 3 | Simulation seeds, run counts and hourly records for each analysis

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

| Permitted work (%) | Duration (h) | Relaxed PI statistic (kW) | Offer (kW) | Success | Wilson lower | Qualifies |
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

PI uses 100 confirmation scenarios; controller testing uses 300. Each offer was fixed on development data. Notice 0, 2 and 6 h is retained separately in Source Data, together with all paired binary outcomes, which coincide across notice settings. Qualification is pointwise at 95% reliability and 95% one-sided confidence.

### Supplementary Table 5 | Original-controller success for repeated calls and separate calls at matched times

| Permitted work (%) | Call/gap (h) | Fresh/repeated successes | Repeated − fresh (pp), 95% interval | Original repeated lower | Development-selected kW |
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

| Permitted work (%) | BESS | Rigid PV kW | Flexible PV kW | Boundary gain kW | Utilisation gain (pp), 95% interval |
|---|---|---|---|---|---|
| 5 | No | 604.21 | 607.03 | 2.82 | 0.0034 [0.0012, 0.0060] |
| 5 | Yes | 672.63 | 675.22 | 2.60 | -0.0002 [-0.0004, 0.0000] |
| 10 | No | 603.55 | 608.95 | 5.40 | 0.0057 [0.0019, 0.0106] |
| 10 | Yes | 672.39 | 677.61 | 5.22 | 0 (numerical; Table 24) |
| 20 | No | 601.56 | 611.92 | 10.36 | 0.0102 [0.0030, 0.0201] |
| 20 | Yes | 671.83 | 681.87 | 10.04 | 0.0000 [-0.0000, 0.0000] |
| 40 | No | 597.97 | 626.96 | 28.99 | 0.0249 [0.0074, 0.0476] |
| 40 | Yes | 669.34 | 697.34 | 28.00 | 0.0008 [-0.0000, 0.0024] |
| 60 | No | 593.74 | 632.69 | 38.95 | 0.0360 [0.0108, 0.0701] |
| 60 | Yes | 665.29 | 703.58 | 38.28 | 0.0072 [-0.0000, 0.0179] |

Each hosting capacity is the minimum over all 100 confirmation scenarios at ≤5% curtailment. Utilisation uses a fixed 500-kW PV installation; means and pointwise paired bootstrap intervals are in percentage points. All current renewable solutions are retained and checked for zero deadline misses. The corresponding conditional mean hosting effects are separately available in Source Data.

The 10% entries use the strict precision audit in Table 24; other eligibility cases retain their original solver settings. The no-BESS utilisation gain is an LP result, unchanged to 2.9 × 10<sup>−14</sup> percentage points in the paired contrast after tightening tolerances. In the primary BESS case, the optimal PV-use contrasts are zero to numerical precision; tiny final signed differences arise within the lexicographic lock.

### Supplementary Table 7 | Conditional participation payments for original single and repeated offers

| Permitted work (%) | Call (h) | Single slack | Single reserve | Single displacement | Repeated original, slack | Repeated confirmation passes |
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

### Supplementary Table 8 | Fixed-offer tests across GPU allocations and rigid-power assumptions

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

### Supplementary Table 10 | Repeated-offer selection and confirmation with individual recovery-window constraints

| Permitted work (%) | H/G (h) | Controller | Selected fraction | kW | Successes | Wilson lower | Outcome |
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

### Supplementary Table 11 | Paired effects of recovery constraints at the same full eight-hour request

| Permitted work (%) | Revised controller | Original/revised successes | Difference (pp), 95% interval | Window-only rescues | New deadline failures | Holm P |
|---|---|---|---|---|---|---|
| 5 | Per-call MPC | 262/294 | 10.7 [7.3, 14.3] | 32 | 0 | 5.12e-09 |
| 10 | Per-call greedy | 252/294 | 14.0 [10.3, 18.0] | 42 | 0 | 5.91e-12 |
| 10 | Per-call MPC | 252/294 | 14.0 [10.3, 18.0] | 42 | 0 | 5.91e-12 |
| 20 | Per-call MPC | 243/294 | 17.0 [13.0, 21.3] | 51 | 0 | 1.24e-14 |
| 40 | Per-call MPC | 240/294 | 18.0 [13.7, 22.3] | 54 | 0 | 1.67e-15 |
| 60 | Per-call MPC | 224/294 | 23.3 [18.7, 28.0] | 70 | 0 | 2.71e-20 |

All contrasts use the same full request, eight-hour calls, twelve-hour gaps and 300 paired new seeds. The primary contrast is 10% eligibility with per-call MPC. Intervals resample complete seeds 10,000 times; exact McNemar P values are adjusted across all 16 reported controller contrasts, including unchanged comparisons in Source Data. Window-only rescues require original failure confined to window peak relief and revised success on all criteria. New deadline failures identify seeds without an original deadline failure but with one under the revised controller. These counts are paired classifications, not independent samples or a complete decomposition of every gain and loss.

### Supplementary Table 12 | Required payments for selected repeated offers under alternative operating costs

| Permitted work (%) | H/G (h) | Controller | kW | Slack | Reserve | Displacement | Confirmation |
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

### Supplementary Table 13 | Rechecking existing offers under the zero-missed-work criterion

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

### Supplementary Table 14 | Coarse-grid selection and confirmation across utilisation, deadlines and GPU allocation

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

### Supplementary Table 15 | Supply shortages and deadline failures at a fixed full request

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

Every row uses the prespecified 5.90-kW comparator, independently of selection. Failure counts are non-exclusive and use 300 complete programmes. Supply shortage means at least one event hour fails the necessary zero-flexible-execution envelope; passing it does not guarantee feasibility. Mean missed work uses the entire episode. The corresponding same-clock final-call electrical outcomes coincide with the fresh-call outcomes in all 16 eight-hour comparisons. Full trial and event tables retain all failure combinations, including 0.1% and zero-miss secondary scores.

### Supplementary Table 16 | Repeated-call outcomes before and after reordering hourly submissions

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

Chronological preserves hourly submission counts in eight observed weeks; permuted shuffles whole hours within each week. Each aggregate comprises ten synthetic realisations per week, not 80 independent production weeks. All observed-week results are supplied in temporal_week_summary.csv and Supplementary Fig. 3d displays the chronological primary requests. Work sizes, class allocation and deadlines remain synthetic. No external result retunes a request or independently qualifies an offer; the direction of permutation effects varies with the request.

### Supplementary Table 17 | Operating costs and access-fee shares for the earlier reference offers

| Programme | Selected rule | Model kW | Accounting kW | Operating US$/yr | No fee | Shared 2,500 | Full 25,000 |
|---|---|---|---|---|---|---|---|
| H4P16 | 1% + zero | 4.42 | 22.869 | 3991.53 | 174.54 | 283.86 | 1267.74 |
| H8P16 | zero | 2.95 | 15.246 | 4895.28 | 321.09 | 485.07 | 1960.89 |
| H8P16 | 1% | 4.42 | 22.869 | 7471.19 | 326.70 | 436.02 | 1419.90 |
| H8P24 | 1% + zero | 2.95 | 15.246 | 6124.52 | 401.72 | 565.70 | 2041.52 |

New reference workload: 10% eligibility, 65% offered utilisation, reference deadlines and corrected MPC. Twelve complete four-call series/year, 2,000 common annual draws, waiting US$0.005/GPU-h/h and missed-work price zero. The last three columns are US$ per offered accounting kW-year at a proportional 1-MW operating peak. Shared fees do not imply risk pooling. In the earlier single-event f10/H4 ledger, net operating exposure 43.3554 plus fixed allocation 819.9008 reproduces 863.2562 exactly; the fixed share is 94.9777%. All 30 earlier thresholds reconcile within 1e−9. Full component attribution, price grids, annual choices and duration-price boundaries are delivered as ready CSV tables; failed unselected comparators retain diagnostic costs only. This table prices the earlier coarse-grid selections. Table 21 and Figs. 6 and S5 price the later refined products using their own new confirmation ledgers.

### Supplementary Table 18 | Finer-grid selection and independent confirmation of reference duration offers

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

### Supplementary Table 19 | Schedule feasibility under each work group’s release and deadline constraints

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

The structural cases use seeds 985000–985002 and H8P16. Immediate shortage means that baseline flexible power is analytically insufficient even if all flexible execution stops. Other infeasibility means the supply check passes but the HiGHS mixed-integer model finds no schedule satisfying the remaining constraints. PI rescue means the tested controller failed while an independently checked full-information schedule meets the same service rule.

In reference seed 985002, such a feasible schedule exists. Halving its deadline slack makes the request infeasible at either 10% or 20% GPU allocation. The five external rows use the first shortage in each affected week, rather than random cases. All 38 diagnoses are resolved. The original 90-s unresolved run and its 600-s continuation are both archived. Execution remains restricted to each release–deadline group, and rebound uses the actual event peak reduction.

### Supplementary Table 20 | Delivery under count and task-resource-time weights with matched weekly work

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

### Supplementary Table 21 | Additional waiting, missed work and required payments for qualified reference repeated offers

| Program | Model kW | Mean waiting GPU-h×h/series | Mean excess missed GPU-h/series | Annual q95 USD | USD/offered kW-year |
|---|---|---|---|---|---|
| H4P16 | 5.6033 | 16491.33 | 0.0000 | 5309.65 | 183.30 |
| H8P16 | 4.4237 | 24509.47 | 0.1996 | 7549.21 | 330.11 |

Means use all 300 confirmation sequences, including failures under the zero-miss criterion. Residual missed work within the 1e−7 GPU-h numerical tolerance does not count as operational failure. Qualification is probabilistic, so the eight-hour product can qualify while its full sample still has mean additional missed work of 0.1996 GPU-h per sequence.

Costs use US$0.005/GPU-h/h for waiting, zero missed-work charge, zero fixed fee and twelve independently sampled four-call sequences per year, scaled proportionally to a 1-MW operating peak. Separate CSV files retain physical quantiles, price combinations and cost components. At these prices, equal value between participating products occurs at P8 = (19/15)P4 + 97.931286. The eight-hour participation threshold relative to not participating is P8 = 330.112105. Changing the waiting price requires recalculating the total-cost quantile, rather than adding separate component quantiles.

### Supplementary Table 22 | Selected offers and new independent confirmation for each workload representation

| Weight | Role | Request (kW) | Development | Confirmation (both rules) | Lower (both rules) |
|---|---|---|---|---|---|
| Submission counts | Selected | 2.9491 | 100/100 | 300/300 | 0.991062 |
| Task resource-time | Selected | 1.4746 | 100/100 | 300/300 | 0.991062 |
| Task resource-time | Fixed comparator | 2.9491 | 53/100 | 120/300 | 0.354570 |

Four eight-hour calls, 16-h start spacing, zero notice, 10% eligible work and 58 flexible GPUs. All 800 count/resource-time input baselines pass zero-miss service. Development and confirmation seeds are disjoint; the latter never reselects an offer. Each model draw independently samples one of eight fixed weeks with equal probability. The ratio 2.0 compares independently confirmed finite-grid offers; the 180 failed comparator draws all encounter instantaneous shortage. All nine candidate values and outcomes are in Source Data.

### Supplementary Table 23 | Delivery outcomes and grid headroom after changing fixed node power

| W/node | Peak (kW) | 5.90 kW / peak (%) | 4 h zero successes | 8 h zero successes | Minimum PCC headroom (kW) |
|---|---|---|---|---|---|
| 150 | 167.52 | 3.52 | 297/300 | 296/300 | 297.25 |
| 300 | 193.44 | 3.05 | 297/300 | 296/300 | 271.33 |
| 450 | 219.36 | 2.69 | 297/300 | 296/300 | 245.41 |
| 600 | 245.28 | 2.40 | 297/300 | 296/300 | 219.49 |

The repeated schedules retain requests of 5.603331 kW for four hours and 4.423682 kW for eight hours. The 5.898243-kW column is a separate single-event accounting comparison. For each row, the same constant power offset is added to response and baseline trajectories for all 600 retained schedules, then the outcomes are rescored. This checks those schedules at the stated requests without new controller selection or independent trials. Original success and failure flags are unchanged. The PCC import rating remains 1,100 kW.

### Supplementary Table 24 | Solar results and optimisation bounds after tightening solver tolerances

| Quantity | Strict result | Numerical evidence |
|---|---|---|
| 10%, no BESS, hosting gain | 5.395897 kW | LP; all 200 solves optimal |
| 10%, BESS, hosting gain | 5.222051 kW | Minimum-bound interval width <0.000001 kW |
| GPU20, no BESS, hosting gain | 24.987573 kW | LP; all 200 solves optimal |
| 10%, no BESS, mean utilisation gain | 0.005716203 pp; 95% paired interval [0.001893867, 0.010571870] | Maximum paired change 2.84 × 10<sup>−14</sup> pp |
| 10%, BESS, mean utilisation gain | Numerical zero; final signed mean −7.09 × 10<sup>−10</sup> pp | Mean primary-objective contrast bounds [−8.53 × 10<sup>−16</sup>, 8.53 × 10<sup>−16</sup>] pp |

The strict settings use relative and absolute MIP gaps of 1e−7, primal/dual/MIP feasibility tolerances of 1e−8, one thread and 120 s per solve. All 400 fixed-PV and 400 no-storage hosting problems finish. Among 200 storage-hosting problems, 166 finish and 34 flexible cases reach the limit.

For maximisation, a feasible solution is a lower bound on the optimum and the dual bound is an upper bound. Taking the minimum of each bound over all 100 scenarios brackets the capacity supported across the scenarios. Every unfinished case has a feasible capacity above the solved limiting case, so all cases are retained. The primary-objective bounds assess uncertainty in PV-use differences; final utilisation also reflects the 1e−5-kWh tolerance used to preserve earlier objectives during later optimisation steps. Sampling intervals do not include this numerical uncertainty.
