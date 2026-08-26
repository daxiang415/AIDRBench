<!--
Working manuscript, version 0.4.
Nature Communications Article order follows the current journal guidance.
Inline figures are included for repository review and can be moved to separate files at submission.
Square-bracketed items require author input or a verified citation; they are not publication text.
-->

# Job constraints define firm data-centre demand response and photovoltaic hosting limits

## Authors

[AUTHOR NAMES AND AFFILIATIONS]

*Correspondence: [CORRESPONDING AUTHOR EMAIL]*

## Abstract

Deferrable computing is often treated as a flexible fraction of data-centre load, but grid commitments must survive job deadlines, repeated dispatch and uncertain operating conditions. We qualify firm demand-response capacity from trace-informed job distributions, hardware-anchored power measurements and explicit service constraints, then assess its community photovoltaic consequences. A nominal 100.50-kilowatt resource overstated the 95%-reliable perfect-information tolerance lower bound by 47.3–62.4% across one- to eight-hour events. Repeated calls accumulated 0.55–1.38 megawatt-hours of compute debt by the fourth event despite near-complete immediate delivery. Job-feasible planning expanded the all-scenario photovoltaic-hosting boundary by approximately 33 kilowatts, whereas gains in utilisation of installed photovoltaics remained below 0.1 percentage points. Independent in-distribution tests certified 15 of 18 fixed capacity cells, but none transferred under a joint out-of-distribution shift. Deferrable computing is therefore a finite, state-dependent and distribution-specific power commitment that requires job-derived qualification and independent local certification.

## Introduction

Artificial-intelligence (AI) computing is becoming a material source of electricity demand. Rapid growth can challenge generation adequacy, delay network connection and concentrate new demand in constrained regions.<sup>1</sup> Yet training and offline-inference jobs can often be paused, slowed or shifted within service limits. Demand response could therefore turn part of a new grid load into a controllable resource. A 256-GPU field demonstration recently sustained a 25% power reduction for three hours while maintaining its tested quality-of-service requirements.<sup>2</sup> This result establishes technical potential. Grid planning, however, needs the reduction that can be committed for a declared duration and reliability without transferring unacceptable risk to computing services.

Batch-workload scheduling, server power management, geographical migration and local generation can reduce peaks while protecting service.<sup>3–7</sup> Carbon-aware systems also shift computing across hours or sites to follow electricity-system emissions and renewable availability.<sup>8–11</sup> Pause-and-resume theory and GPU power-capping experiments expose the costs of switching, incomplete information and electrical actuation.<sup>12,13</sup> More recent trace and grid-planning studies estimate demand-response potential, notice value and interconnection consequences.<sup>14–17</sup> Together, these studies show several ways in which computing can respond to grid or environmental signals.

Power-system planning requires a distinct quantity: firm DR qualification. A static flexible percentage specifies neither event duration nor delivery reliability. An aggregate energy budget does not preserve releases, classes, processing requirements or deadlines. A selected controller reports one implementation, while an optimal full-information schedule reports a physical planning boundary. Neither alone establishes what a fixed causal scheduler will deliver on new episodes. Capacity must also be tied to a declared scenario distribution because workload arrivals and community conditions determine the states being tested. Without these distinctions, a planning model can mistake adjustable energy for dependable power or interpret statistical conservatism as an information disadvantage.

Firm qualification adds a further temporal boundary through dispatch history. Deferring work creates compute debt, a future processing obligation that can accumulate despite satisfactory immediate delivery.<sup>5,12,18,19</sup> A later call then begins from an endogenous service state rather than a fresh queue. Recovery depends on spare compute headroom and deadline structure, not elapsed time alone. Repeated-event reliability must consequently be assessed jointly across calls. This resource also acts within a wider energy system. At a community point of common coupling (PCC), job-constrained load interacts with photovoltaic (PV) generation and battery energy storage systems (BESS). These resources can relax overlapping network and renewable-integration constraints,<sup>20–24</sup> linking firm qualification to a joint data-centre–PV feasible boundary.

PV hosting and PV utilisation represent different consequences of that boundary. Hosting asks how much generation can be installed while satisfying network, curtailment and service constraints. Utilisation asks how much energy from an already installed system is consumed locally. Flexible computing may change the former without materially changing the latter, especially when storage already shifts surplus generation. A joint feasible-set analysis is therefore needed to distinguish resource expansion from operational energy effects and to test whether workload flexibility complements or substitutes for BESS.

Here we qualify firm demand-response capacity from trace-informed job distributions, hardware-anchored power measurements and explicit service constraints. We separate nominal flexibility, a perfect-information (PI) planning boundary, a restricted non-anticipative (NA) empirical boundary and an independently tested causal certificate. The distinction between a population-level PI tolerance lower bound and a finite-ensemble empirical PI/NA boundary is maintained throughout. Matched fresh-event counterfactuals expose compute-debt accumulation under repeated calls. Joint planning models then quantify PV hosting and distinguish it from utilisation of installed PV. Frozen development, validation, locked in-distribution (locked-ID) and locked out-of-distribution (locked-OOD) ensembles separate model development from reliability testing. Together, these analyses test how event design, history and distribution shape a credible grid offer and its system consequence. The central proposition is that deferrable computing is a finite, state-dependent and distribution-specific power commitment that must be qualified from jobs and independently certified.

## Results

### Nominal load flexibility overstates job-derived firm capacity

Job constraints reduced the q = 0.95 PI tolerance lower bound to 37.76–53.01 kW, far below the constant 100.50-kW nominal proxy (Fig. 1a,b). The bound declined from 26.4% of the 201.00-kW operating peak at 1 h to 18.8% at 8 h. The nominal proxy therefore overstated supported capacity by 47.3–62.4% across the tested durations. Because PI assumed full future information, this gap arose before any causal-controller limitation.

Four-GPU measurements anchored the conversion from job execution to board power without treating the measurement node as a utility-scale data-centre surrogate (Fig. 1c). Mean active power was 259.08 W per GPU for training and 300.02 W for offline inference. A held-out workload run had a mean absolute prediction error of 3.80 W. Independent-run intervals and idle-power evidence are reported in the Supplementary Information. The measurements supplied class-specific slopes and uncertainty cases, while node fixed overhead remained a separate engineering assumption.

The four evidence layers retained distinct meanings (Fig. 1d). Nominal flexibility was an assumption, PI was a full-information planning bound and restricted NA was a finite-ensemble empirical bound. Only the locked causal layer independently tested a fixed implementation. A class-aware cumulative formulation reproduced the job-edge PI formulation at all 18 diagnostic points (Supplementary Information), confirming the reformulation without promoting either planning bound to a certificate.

![Figure 1](../docs/figures/nature_mainline_v1/figure_1_nominal_job_derived_gap.png)

### Duration and reliability shape firm flexibility whereas notice alone may not

Longer events and stricter reliability reduced firm capacity, whereas notice did not increase capacity in the frozen Model A scenarios (Fig. 2). At q = 0.95, the empirical PI/NA boundary declined from 56.42 kW at 1 h to 41.19 kW at 8 h. Matched empirical PI and restricted NA were identical on the finite development ensemble, giving a descriptive information gap of 0.0 kW. The 56.42-kW empirical value exceeded the 53.01-kW formal PI tolerance lower bound at 1 h. This apparent ordering reflects different cross-scenario statistics, not an information advantage of NA over PI. The former permits a declared number of finite-ensemble failures, whereas the latter provides a population-level nonparametric tolerance statement.

Validation selection produced progressively smaller candidates as the reliability target increased from q = 0.90 to 0.99 (Fig. 2b). Their independent outcomes are reported below rather than folded into the selection surface. At q = 0.95, increasing notice from 0 to 2 or 6 h changed neither planning boundary at any duration. Positive notice gain was therefore neither assumed nor required.

Notice changed schedules but not the binding delivery constraint. At 6 h notice, 1,829 GPU-h of work was eligible for pre-execution, but only 133 GPU-h of spare pre-event capacity was available (Fig. 2c). Paired schedules differed by approximately 1.3 GPU-h per pre-event interval, confirming that the information was used. Scarce headroom nevertheless prevented pre-execution from increasing the firm reduction under the tested conditions.

![Figure 2](../docs/figures/nature_mainline_v1/figure_2_duration_reliability_notice.png)

### Compute debt limits repeated dispatch before power delivery collapses

Repeated dispatch accumulated compute debt even while immediate delivery remained close to a fresh-event counterfactual (Fig. 3). The four-event diagnostic fixed planning-level reductions of 44.00 kW for 4 h and 41.19 kW for 8 h before validation. These exceeded the later locked-ID causal candidates of 39.65 and 36.71 kW, respectively. Each event was paired with the same scenario and clock time without prior calls. By the fourth event, mean additional compute debt reached 0.55–1.38 MWh across durations and recovery gaps.

Immediate delivery concealed this deterioration in service state. The fifth-percentile fourth-event residual delivery remained 0.9910–1.0000 relative to the matched fresh event, while validation joint-episode success ranged from 0.00 to 0.97 (Fig. 3b–d). Thus, near-complete event-level power reduction did not imply that four calls remained jointly service-feasible.

Success was not monotonic in elapsed recovery time because longer gaps did not guarantee spare compute headroom. No repeated-event cell met q = 0.95 after finite-sample uncertainty; the best empirical cell had a one-sided 95% Wilson lower bound of 0.927. Given the higher planning-level commitments, this analysis is a mechanism diagnostic for state-dependent exhaustion, not a repeated-event capacity certificate.

![Figure 3](../docs/figures/nature_mainline_v1/figure_3_compute_debt_exhaustion.png)

### Job-feasible scheduling expands photovoltaic hosting without relying on deadline misses

Job-feasible planning expanded the joint data-centre–PV hosting boundary at every tested data-centre scale, with and without BESS (Fig. 4a). This perfect-information planning layer was separate from the locked causal certificate. The headline problem maximised PV nameplate capacity under a 5% curtailment limit, service constraints and PCC limits. At 3× data-centre capacity, flexible operation remained feasible in all 100 validation scenarios under both storage conditions. Rigid operation remained feasible in 31 scenarios without BESS and 96 with BESS.

At the reference 201-kW data centre, flexibility increased the PV capacity feasible in all 100 validation scenarios by 32.83 kW without BESS and 33.38 kW with BESS. These all-scenario gains are the headline hosting result. The distinct mean within-scenario gains were 44.85 and 43.20 kW, respectively (Fig. 4b; Supplementary Information). They describe average paired effects, not the minimum capacity shared by the ensemble. Neither estimand represents a causal effect of the locked controller.

The effect on utilisation of an already installed 500-kW PV system was much smaller. Flexibility increased PV utilisation by 0.0720 percentage points without BESS and 0.0227 percentage points with BESS (Fig. 4c). Repeating both programmes with no allowed deadline misses preserved the approximately 33-kW all-scenario hosting gains and the small PV-use effects (Supplementary Information). Grid-import changes could not be attributed entirely to PV consumption, and no general reduction in PCC peak was established.

An orthogonal 2 × 2 × 2 slice showed that the three resources were not additive. AI flexibility substituted for BESS, with interactions of −52.31 kW without PV and −88.54 kW with PV (Fig. 4d). It complemented PV without BESS (+44.59 kW), while the +8.36-kW interaction with BESS was indeterminate against the practical margin. Full simultaneous intervals are reported in the Supplementary Information.

![Figure 4](../docs/figures/nature_mainline_v1/figure_4_hosting_capacity_interactions.png)

### Independent evaluation defines robustness and generalisation boundaries

Predeclared sensitivity and locked evaluation showed that firm capacity was model-dependent and locally certifiable, not universally transferable (Fig. 5). Hardware uncertainty changed the absolute PI tolerance lower bound while preserving its decline with duration (Fig. 5a). Varying flexible-arrival utilisation shifted the 4-h bound by −9.26 to +37.84 kW and the 8-h bound by −8.71 to +15.73 kW (Fig. 5b). Other tested workload and service changes were inactive at these diagnostic points, which does not establish universal non-binding constraints.

For causal testing, every controller parameter and provenance hash was frozen before one-time replay on 500 locked-ID episodes. At q = 0.95, all candidates for 2–8-h events passed at every notice level, certifying 15 of 18 cells (Fig. 5c). Their capacities ranged from 36.71 to 45.74 kW, with one-sided 95% Wilson lower bounds of 0.964–0.985. The 55.16-kW, 1-h candidate failed because its lower bound was 0.936. Secondary reliability targets are reported in the Supplementary Information.

The same candidates were replayed without reselection after jointly changing the community profile and workload-arrival process. Success declined to 383–445 of 500 episodes across durations, and no q = 0.95 cell retained certification (Fig. 5c). This result does not imply zero OOD capacity because reselection on locked-OOD data was prohibited. It shows that a distribution-specific certificate requires local revalidation before transfer.

![Figure 5](../docs/figures/nature_mainline_v1/figure_5_robustness_generalization.png)

## Discussion

Deferrable computing is not a fixed flexible-load fraction. It is a finite power commitment whose magnitude depends on job state, event design, implementation and scenario distribution. In Model A, the nominal 50%-flexibility proxy overstated the q = 0.95 PI tolerance lower bound by 47.3–62.4%. This result complements the recent 256-GPU demonstration of a sustained 25% reduction.<sup>2</sup> That study established achievable response in one deployment. Our study asks how heterogeneous jobs become a duration- and reliability-indexed commitment before and after a causal scheduler is fixed. The distinction matters because a grid offer is a claim about future delivery, not a retrospective description of adjustable energy.

Firm DR qualification adds a missing layer to workload-aware demand response and carbon-aware scheduling.<sup>4–17</sup> The nominal-to-PI gap measures physical job constraints before controller design. The matched empirical PI/NA comparison isolates the declared information structure under one finite scenario ensemble. The population-level PI tolerance lower bound answers a different statistical question and should not be ranked numerically against that empirical boundary. Independent locked testing then asks whether a fixed causal implementation retains the selected reliability on unseen local episodes. This hierarchy changes the unit of comparison from an unconstrained flexible percentage to a qualified power commitment. Conflating its layers would treat an optimisation bound as dispatchable capacity or misattribute a physical workload limit to a controller.

This framing is complementary to recent trace-derived estimates of flexibility and notice value, and to grid models of deferral, migration and interconnection.<sup>14–17</sup> Those studies quantify operational potential or system value under their declared schedules. Firm qualification instead asks which part of that potential can be offered under an explicit delivery rule and independently verified reliability. The answer is not a universal property of installed power because the qualifying job population, event design and implementation all enter the estimand.

Compute debt links one dispatch to the state available for the next. Repeated events accumulated 0.55–1.38 MWh of additional deferred processing energy by the fourth call despite near-complete immediate delivery. Matched fresh-event counterfactuals separated this effect from changing background load and arrivals. The diagnostic used planning-level commitments above the later causal candidates, so it does not estimate repeated-event firm capacity. It instead shows how service state can deteriorate before power delivery visibly collapses. Pause-and-resume and power-capping studies represent transition costs within a scheduling decision,<sup>12,13</sup> whereas compute debt records the obligation carried between decisions. Recovery requires enough headroom to discharge that obligation before deadlines, making repeatability state-dependent rather than a function of elapsed time alone.

An isolated-event certificate averages over a declared fresh-state distribution. A repeated programme instead visits states produced by its own previous actions. Capacity for such a programme must therefore condition on prior dispatch, recovery policy or an equivalent debt state. Re-estimating that state-indexed certificate remains distinct from the present exhaustion diagnostic.

Advance notice similarly separates information from physical opportunity. Six hours of notice exposed eligible work and changed schedules, but scarce pre-event headroom left the delivery constraint unchanged. Zero notice gain is therefore a bounded structural result, not a universal claim that notice lacks value. Prior studies show that future information can alter workload timing and demand-response value.<sup>8,12,14,17</sup> Our diagnostics refine that expectation: eligible work, spare pre-event capacity and a relaxable binding constraint must coincide. Notice can change dispatch without changing firm capacity, so positive notice value is a conditional hypothesis rather than a defining property.

The community analysis reveals a system consequence at the joint data-centre–PV feasible boundary.<sup>20–24</sup> Perfect-information job scheduling expanded the all-scenario PV-hosting boundary by approximately 33 kW at the reference data-centre scale. The larger scenario-paired mean gain answered a different question about an average contrast. Prohibiting deadline misses preserved the all-scenario boundary gain, ruling out the service allowance as its source. By contrast, utilisation of an installed 500-kW PV system increased by less than 0.1 percentage points and approached zero with BESS. Flexibility therefore changed how much PV could satisfy the declared constraints more than it changed consumption from an installed system. Neither planning result is a causal effect of the locked controller.

The all-scenario boundary is deliberately stricter than the paired mean because it requires one capacity to remain feasible across the full validation ensemble. Keeping these estimands separate prevents an average planning benefit from being presented as a common guaranteed increment.

The resource interactions further show why flexible computing should enter a joint feasible set rather than be added as an independent benefit. Workload flexibility substituted for BESS when either resource relaxed the same network or curtailment constraint. This overlap does not make their physical capabilities interchangeable. Batteries exchange electrical energy independently of job arrivals but face power, energy, efficiency and state-of-charge limits.<sup>23</sup> Computing flexibility instead depends on releases, deadlines and future service. Its complementarity with PV also weakened after BESS entered the portfolio. The value of firm flexibility is therefore conditional on the other resources and constraints present at the PCC.

These findings motivate a practical qualification sequence consistent with capacity-credit principles for inter-temporal resources.<sup>25,26</sup> A data-centre operator should derive a duration–reliability surface from local jobs and power, select a causal scheduler on separate validation data, and certify the fixed offer independently. The commitment should specify duration, delivery, recovery and the reference distribution rather than a single flexible percentage. Repeated calls require a state variable such as compute debt or deadline-weighted backlog. The complete locked-OOD failure does not imply zero flexibility at the shifted site because candidate reselection was prohibited. It shows that a distribution-specific certificate does not travel automatically across communities, workload mixes or GPU fleets.

Several boundaries qualify the numerical results. Workloads were fluid and pre-emptible at 1-h resolution, and deadlines were generated from trace-derived job characteristics rather than replayed from production. The Alibaba sampler preserved selected job-characteristic distributions, not the full production timeline or pod-hourly correlations. Community demand came from modelled, measurement-validated profiles rather than project-owned feeder meters. Four-GPU experiments anchored board power but not whole-facility overhead, cooling or network power. Model A represents one community scale, workload mix and scheduling abstraction. Finer resolution, non-pre-emptible services, gang constraints and cross-site hardware tests may reshape the capacity surface. They do not remove the need to derive grid commitments from service-constrained jobs and certify them for the intended operating distribution.

## Methods

### Study design and evidence hierarchy

The study separated four capacity concepts. Nominal flexibility was defined as a fixed fraction of the reference-mix operating peak. The PI planning layer maximised power reduction with full knowledge of future jobs, community demand and event timing. Its formal population-level result was a nonparametric tolerance lower bound. The restricted NA empirical boundary imposed equality of decisions across scenario histories that were indistinguishable at the decision time. The causal certificate tested a validation-selected, fixed controller on an independent locked ensemble. These quantities were not alternative algorithms estimating one object: nominal capacity was an assumption, PI and NA were planning boundaries, and only locked-ID testing produced an independently evaluated operational certificate.

Model A and the analysis plan were frozen after the predeclared notice diagnostic and before validation or locked evaluation. Four non-overlapping seed ranges assigned 100 development episodes (10,000–10,099), 100 validation episodes (20,000–20,099), 500 locked-ID episodes (30,000–30,499) and 500 locked-OOD episodes (40,000–40,499). Development scenarios established mechanisms and sensitivity designs. Validation scenarios tested planning replication and selected causal capacity. Locked-ID scenarios were consumed once for in-distribution certification, and locked-OOD scenarios were consumed once for transfer stress testing without reselection. Scenario payloads, configurations and source artifacts were hashed before evaluation, and overlap between locked and non-locked scenario sets was prohibited.

The single-event analysis treated one episode as one Bernoulli trial. The repeated-event analysis treated the complete multi-event episode as the independent unit; individual events within the same episode were not treated as independent observations. Renewable-integration analyses used the frozen scenario as the paired unit. Hardware uncertainty was estimated across independent workload runs, not across GPUs observed within one run.

### Firm-capacity estimand

Let \(Z\) denote one frozen episode containing the initial queue state, community load, job arrivals and deadlines, hardware case and event time, sampled from a declared scenario distribution \(\mathcal D\). For a fixed policy \(\pi\), requested reduction \(R\), duration \(H\) and notice \(N\), the indicator \(I_\pi(R,H,N;Z)\) equalled one only when every delivery and service criterion below was satisfied. We defined distribution-specific firm capacity as

\[
F_q^{\pi}(H,N;\mathcal D)=
\sup\left\{R\geq0:\Pr_{Z\sim\mathcal D}
\left[I_\pi(R,H,N;Z)=1\right]\geq q\right\}.
\]

The reliability targets were \(q\in\{0.90,0.95,0.99\}\), with \(q=0.95\) designated as the headline. This definition makes capacity conditional on the policy and scenario distribution rather than an intrinsic fraction of installed load. Event-start backlog and deadline slack are components of \(Z\); after an earlier dispatch they become endogenous state variables. The single-event surface averaged over the declared fresh-event state distribution, whereas the repeated-event experiment held \(R\) fixed and measured how prior calls changed that state. It did not estimate a separate capacity for every possible backlog state.

The PI, restricted NA and causal layers differed in the admissible policy class used to evaluate the same success criteria. PI allowed scenario-specific full-horizon decisions and provided a physical planning boundary. Restricted NA coupled decisions across indistinguishable information histories in a finite scenario ensemble. The causal layer fixed one implementable robust-MPC specification before locked evaluation. Nominal flexibility was not an instance of \(F_q^{\pi}\), because it imposed no job, delivery or reliability test.

### Community, workload and event data

Community background demand was drawn from the End-Use Load Profiles for the US Building Stock,<sup>27,28</sup> using ResStock detached-residence and ComStock small-office aggregates in ASHRAE climate zones 3A, 3C and 5A. The source data comprise physics-based building-stock simulations calibrated and validated against measured utility and end-use data; they are not feeder measurements collected in this project. Fifteen-minute interval-ending power was averaged to 1-h intervals. Mixed profiles combined 75% residential and 25% small-office demand and were then scaled without changing temporal shape. Model A used the mixed 3A profile, an 800-kW community background peak and a 1,000-kW PCC import limit. The joint OOD set replaced the community profile with mixed 3C while retaining the frozen evaluation protocol.

AI batch arrivals were generated from a class-aware synthetic process informed by selected job characteristics in the 2026 Alibaba Serverless Infrastructure trace. The six-month source trace covers 155,410 heterogeneous GPUs and includes development, training, online-inference and offline-inference activity,<sup>29</sup> extending an earlier public Alibaba trace of 6,742 GPUs.<sup>30</sup> We used the official 40,522,321-row job-execution summary, normalised it once, and formed a reproducible 100,000-row bounded sampler with 50,000 low-priority training and 50,000 low-priority offline-inference records. This project-made “Lite” sampler reduced repeated experiment I/O; it was not a separate Alibaba release. An independent-reservoir audit found close central and 95th-percentile job-shape summaries but did not meet one tail-sensitive Wasserstein diagnostic, so full-distribution equivalence was not claimed (Supplementary Information). We used empirical job-size, runtime and GPU-demand distributions rather than replaying source timestamps. The execution summary did not provide the production deadlines required by the present service model; deadlines were therefore generated using the predeclared class-specific slack policy and were always labelled synthetic. The summary-based model also did not reproduce the temporal correlations available in the much larger pod-hourly archive.

The reference arrival process had total utilisation 0.65. Training and offline inference each contributed 50% of offered work; all training work and 50% of offline-inference work were eligible for deferral, and the virtual facility contained 144 four-GPU nodes. Training slack multipliers ranged from 2 to 6 with a 6–48-h bound, whereas offline-inference multipliers ranged from 1.5 to 4 with a 2–24-h bound. Each episode comprised seven dispatch days followed by a 48-h clearance tail. Single demand-response events began uniformly at one of the declared 15:00–20:00 local-clock candidates on episode days 3–6. Durations were 1, 2, 3, 4, 6 or 8 h, and notice was 0, 2 or 6 h. These events were controlled experimental scenarios, not observed utility dispatch records.

### Workload and power model

Each job was represented by a release time, workload class, GPU-hour requirement and deadline. Available work entered an earliest-deadline-first fluid queue. For class c and hour t, backlog evolved as

\[
B_{c,t+1}=B_{c,t}+A_{c,t}-X_{c,t}-M_{c,t},
\]

where A was newly released work, X was executed work and M was unfinished work expiring at its deadline. Schedules obeyed per-hour GPU capacity, work conservation, release and deadline constraints, a declared deadline-miss allowance and a terminal-backlog constraint. Rigid and flexible workload fractions were modelled separately, and optimisation retained class-specific execution variables. The fluid formulation allows work to be divided across hourly intervals and does not represent gang placement, checkpoint latency or non-pre-emptive execution. These omissions define the scheduling abstraction rather than an assumption that production jobs incur no such costs.

Data-centre power was

\[
P^{\mathrm{DC}}_t=P_{\mathrm{fixed}}+\sum_c e_cX_{c,t},
\]

where e_c was the class-specific incremental energy per executed GPU-hour after multiplying board-power increment by the declared PUE. Board-power parameters were fitted from four-GPU measurements and stored in a hash-verified calibration artifact. The measurement server contained four NVIDIA RTX PRO 6000 Blackwell Max-Q GPUs connected through PCIe without NVLink. Training and offline-inference active-power estimates were 259.08 and 300.02 W per GPU, respectively; idle power was 13.94 W per GPU. Two independent workload runs per active class were used for the fit, and a third workload run was held out for prediction assessment. GPUs within one simultaneous run were averaged and were not treated as independent replicates.

The nominal model used PUE 1.2 and an assumed node fixed overhead of 300 W. Fixed overhead represented the portion of node and facility demand not scaled by class-specific GPU-hour execution in the affine model; it was not measured by the board-power experiment. Lower and upper calibration cases propagated the run-level power intervals, and sparse sensitivity cases varied PUE and node overhead without resizing the 144-node facility. Reference-mix operating peak was calculated from the 50:50 workload composition and was kept distinct from a worst-class or nameplate peak. Thus, scaling the four-GPU measurements to Model A preserved measured per-GPU slopes while exposing infrastructure quantities as assumptions rather than presenting the server as a miniature physical replica of the community-scale facility.

### Hourly environment, baselines and compute debt

The environment used a 1-h time step. At each step, new arrivals were released before the control action, eligible work was scheduled, class-specific power was calculated, and queue deadlines advanced by one hour. The temporal resolution was fixed because queue buckets advance by one interval per step; configurations with another time-step duration were rejected. Each controlled episode was paired with a no-demand-response baseline generated from the same frozen community profile, job arrivals, deadlines and hardware case. Event delivery was therefore evaluated as a baseline-relative power reduction rather than against an unrelated historical profile.

Compute debt quantified the additional future dynamic energy obligation associated with deferred backlog relative to the paired baseline:

\[
D^{\mathrm{comp}}_t=\sum_c \Delta B_{c,t}\,\mathrm{PUE}\left(P^{\mathrm{active}}_c-P^{\mathrm{idle}}\right),
\]

where \(\Delta B_{c,t}\) was controlled backlog minus matched baseline backlog. Recovery and rebound were evaluated over the declared post-event window, and simulations included a tail period to evaluate terminal backlog.

### Demand-response delivery and service criteria

A candidate reduction R succeeded only if all declared criteria were met. Delivered reduction in hour t was the non-negative baseline-relative difference \(\Delta P_t=\max(0,P^{\mathrm{baseline}}_t-P^{\mathrm{control}}_t)\). Mean event delivery was \(\sum_{t\in E}\min(\Delta P_t,R)/(R|E|)\) and had to be at least 0.95. In addition, every event hour had to satisfy

\[
P^{\mathrm{control}}_t \leq P^{\mathrm{baseline}}_t-0.95R.
\]

The episode also had to satisfy limits on deadline misses, rebound, event-plus-recovery peak relief and terminal backlog. The headline configuration allowed a deadline-miss fraction of 0.01, a rebound ratio of 0.25, a recovery-window peak-relief fraction of 0.50 and terminal backlog no more than 0.02 of total offered work. Rebound was the maximum positive post-event controlled-minus-baseline PCC load divided by the peak event reduction over the 24-h recovery window. Mean delivery and minimum interval delivery were reported separately; event-average energy delivery was not used as a substitute for hourly compliance. These thresholds were an operational success definition fixed in the protocol, not coefficients tuned through a reward function.

### Perfect-information, non-anticipative and causal capacity

For each scenario, the PI programme maximised R subject to workload, power and service constraints. Cross-scenario PI firm capacity used an exact-binomial nonparametric lower-tolerance order statistic at reliability q and confidence 0.95.<sup>31</sup> Specifically, the selected order statistic was the largest reduction for which the exact one-sided binomial confidence statement supported at least a q fraction of the scenario population. If the scenario count was insufficient for a requested q, the value was marked not estimable rather than set to zero. The restricted NA programme enforced equal decisions for scenario histories sharing the same available information and reported an empirical finite-ensemble bound. A matched empirical PI order statistic using the same allowed failure count was used only for descriptive comparison with restricted NA; it did not replace the formal PI tolerance bound.

The causal implementation was a robust model-predictive controller with every parameter explicitly declared in a versioned configuration. It observed only released jobs, the current queue, a 6-h community forecast and demand-response requests that had entered the notice window. No controller training or reinforcement learning was used in the main study. Validation selection used a predeclared binary search over 0–100% of the reference reduction range for 10 iterations, separately for each duration, notice and reliability target. Selection records stored the normalised controller specification, raw configuration SHA-256, Git commit, source hashes and scenario hashes. Locked evaluation failed closed if any recorded artifact differed. A candidate was certified when the one-sided 95% Wilson lower confidence bound of success on 500 locked-ID episodes was at least q.<sup>32,33</sup> Confidence statements applied to each predeclared cell; simultaneous coverage over the complete capacity surface was not claimed.

### Repeated-event counterfactual design

Repeated-event episodes contained four events of duration 4 or 8 h separated by recovery gaps of 2, 4, 8, 12 or 24 h. Capacities were fixed from development results before validation. For each event, a fresh-event counterfactual used the same scenario and clock time but removed the influence of prior events. Residual flexibility was the delivered reduction in the repeated trajectory divided by delivery in this matched fresh event. Event-local delivery was reported separately from joint-episode success, which required every event and all episode-level service criteria to pass.

### Renewable-integration optimisation

Community PCC power was

\[
P^{\mathrm{PCC}}_t=L_t+P^{\mathrm{DC}}_t+P^{\mathrm{ch}}_t-P^{\mathrm{dis}}_t-G^{\mathrm{PV}}_t,
\]

and was constrained by the 1,000-kW PCC import limit; reverse power export was prohibited. PV generation was the available profile multiplied by an optimised or fixed nameplate rating, and curtailment was the difference between available and used PV energy. The PV-hosting programme fixed data-centre capacity and maximised PV nameplate capacity subject to a headline curtailed-energy fraction of at most 0.05, with 0, 0.10 and 0.20 evaluated as sensitivities. These renewable programmes used perfect-information workload scheduling, allowed at most 0.01 of offered GPU-hours to miss their generated deadlines, and required terminal backlog no greater than 0.02 of offered work. They were therefore planning bounds rather than replays of the locked causal controller. The reference BESS had 100-kW charge/discharge power, 200-kWh energy, 0.95 charge and discharge efficiencies, and initial and terminal state of charge fixed at 50%. Headline hosting used mutually exclusive charging and discharging in a mixed-integer formulation. A simultaneous PV capacity was reported only when all 100 scenarios were feasible; otherwise the number of feasible scenarios and the scenario-wise capacity range were reported without assigning zero capacity.

The fixed-operation analysis set data-centre capacity to the 201-kW reference and PV capacity to 500 kW. A lexicographic objective first preserved workload-service feasibility and then maximised local PV use within a 10<sup>−5</sup>-kWh objective tolerance. Outcomes included PV energy used and curtailed, PV utilisation, renewable demand share, grid import, PCC peak and BESS throughput. A separate 2 × 2 × 2 design maximised data-centre hosting under rigid or flexible workloads with PV and BESS switched on or off. Predeclared difference-in-differences contrasts quantified AI×PV and AI×BESS interactions. Optimisation used the HiGHS solver<sup>34</sup> with one solver thread per process; scenario-level programmes were parallelised outside the solver.

The post-run service sensitivity repeated the reference-scale 5%-curtailment hosting problem and fixed-500-kW-PV operation with the deadline-miss fraction fixed at zero. It used all 100 development and 100 validation scenarios, both BESS conditions and the same rigid/flexible definitions. Rigid zero-miss rows were reused only after their result hashes and zero-miss outcomes were verified; every flexible case was re-solved. This diagnostic did not read either locked set and was interpreted as supporting planning evidence rather than a new causal estimand.

### Sensitivity analyses

Except for the explicitly labelled renewable zero-miss replication across development and validation, sensitivities were evaluated on development scenarios and were excluded from locked candidate selection. Hardware cases propagated lower, nominal and upper active-power estimates. A nine-case sparse workload design varied flexible-arrival utilisation, rigid-GPU utilisation and deadline-slack scale; every case first passed a no-demand-response service-feasibility gate and was then evaluated at 4- and 8-h duration on the same 100 seeds. Success-criterion sensitivities changed delivery, deadline-miss, rebound and recovery-window-relief thresholds one factor at a time. Infrastructure sensitivities varied PUE and node fixed overhead while holding node count and the nominal GPU calibration case fixed. This sparse design was used to identify which declared assumptions changed the capacity boundary, not to search for a favourable model variant.

### Statistical analysis and reproducibility

Scenario-paired effects used a frozen scenario as the independent unit. Confidence intervals for the renewable-integration contrasts were obtained from 10,000 scenario-level bootstrap resamples with Bonferroni control over each predeclared family. Interaction labels used a practical equivalence margin of 10.05 kW, equal to 5% of the reference-mix operating peak. Repeated-event proportions and causal certificates used episodes as independent units; one-sided Wilson lower bounds were calculated for frozen candidates. All reported capacity boundaries retained solver-feasibility status and constraint residuals. No post hoc capacity reselection was performed on locked-ID or locked-OOD outcomes, and no locked outcome was used to revise Model A.

Every formal result recorded the Git commit, protocol version, scenario and input-data hashes, calibration-artifact hash, power case, seed range, solver settings, controller configuration and failure reasons. Source-data tables underlying all main figures and per-figure manifests bind the plotted values to these records. The final verification and manuscript export used Python 3.12.13 on Linux 6.8 (x86-64), with NumPy 2.5.2, pandas 2.3.3, PyArrow 21.0.0, SciPy 1.18.0, CVXPY 1.9.2, HiGHS 1.15.1 and Matplotlib 3.11.1. The complete environment is pinned by `uv.lock`; optimisation used one HiGHS thread per process, and scenario programmes were parallelised outside the solver.

## Data Availability

The NREL End-Use Load Profiles used for community demand are available through the OEDI building-stock data lake. The Alibaba 2026 job-execution summary used to inform the workload model is available from the official `cluster-trace-gpu-v2026` release. Exact download locations, retrieval records, preprocessing configurations and SHA-256 hashes for the original archive, the 40,522,321-row normalised table and the project-made 100,000-row sampler are recorded in `data/manifests/sources.yaml`. Raw third-party data are not redistributed by this repository. Frozen scenario manifests, processed Source Data underlying all figures, calibration artifacts and result receipts are included in the public repository or its immutable release archive and will also be deposited at [ZENODO DOI TO BE ADDED].

## Code Availability

The AIDRBench source code, versioned configurations and scripts used to generate the reported results are available at https://github.com/daxiang415/AIDRBench. The submission version will be archived with an immutable release and DOI at [ZENODO DOI TO BE ADDED].

## References

1. Lin, L. et al. Exploding AI power use: an opportunity to rethink grid planning and management. In *Proceedings of the 15th ACM International Conference on Future and Sustainable Energy Systems* 434–441 (ACM, 2024). https://doi.org/10.1145/3632775.3661959

2. Colangelo, P. et al. AI data centres as grid-interactive assets. *Nat. Energy* **11**, 254–261 (2026). https://doi.org/10.1038/s41560-025-01927-1

3. Wierman, A., Liu, Z., Liu, I. & Mohsenian-Rad, H. Opportunities and challenges for data center demand response. In *2014 International Green Computing Conference* 1–10 (IEEE, 2014). https://doi.org/10.1109/IGCC.2014.7039172

4. Li, J., Bao, Z. & Li, Z. Modeling demand response capability by Internet data centers processing batch computing jobs. *IEEE Trans. Smart Grid* **6**, 737–747 (2015). https://doi.org/10.1109/TSG.2014.2363583

5. Zhang, Y., Wilson, D. C., Paschalidis, I. Ch. & Coskun, A. K. HPC data center participation in demand response: an adaptive policy with QoS assurance. *IEEE Trans. Sustain. Comput.* **7**, 157–171 (2022). https://doi.org/10.1109/TSUSC.2021.3077254

6. Zhang, Y., Wilson, D. C., Paschalidis, I. Ch. & Coskun, A. K. A data center demand response policy for real-world workload scenarios in HPC. In *2021 Design, Automation & Test in Europe Conference & Exhibition* 282–287 (IEEE, 2021). https://doi.org/10.23919/DATE51398.2021.9474075

7. Liu, Z., Wierman, A., Chen, Y., Razon, B. & Chen, N. Data center demand response: avoiding the coincident peak via workload shifting and local generation. *Perform. Evaluation* **70**, 770–791 (2013). https://doi.org/10.1016/j.peva.2013.08.014

8. Radovanović, A. et al. Carbon-aware computing for datacenters. *IEEE Trans. Power Syst.* **38**, 1270–1280 (2023). https://doi.org/10.1109/TPWRS.2022.3173250

9. Riepin, I., Brown, T. & Zavala, V. M. Spatio-temporal load shifting for truly clean computing. *Adv. Appl. Energy* **17**, 100202 (2025). https://doi.org/10.1016/j.adapen.2024.100202

10. Zheng, J., Chien, A. A. & Suh, S. Mitigating curtailment and carbon emissions through load migration between data centers. *Joule* **4**, 2208–2222 (2020). https://doi.org/10.1016/j.joule.2020.08.001

11. Goiri, Í., Katsak, W., Le, K., Nguyen, T. D. & Bianchini, R. Parasol and GreenSwitch: managing datacenters powered by renewable energy. In *Proceedings of the Eighteenth International Conference on Architectural Support for Programming Languages and Operating Systems* 51–64 (ACM, 2013). https://doi.org/10.1145/2451116.2451123

12. Lechowicz, A. et al. The online pause and resume problem: optimal algorithms and an application to carbon-aware load shifting. *Proc. ACM Meas. Anal. Comput. Syst.* **7**, 1–32 (2023). https://doi.org/10.1145/3626776

13. Zhao, D. et al. Sustainable supercomputing for AI: GPU power capping at HPC scale. In *Proceedings of the 2023 ACM Symposium on Cloud Computing* 588–596 (ACM, 2023). https://doi.org/10.1145/3620678.3624793

14. Caprara, A., Yu, Y., Teng, F., Junyent-Ferré, A., Bullich-Massagué, E. & Aragüés-Peñalba, M. Data center workload flexibility for power system demand response: evidence from Alibaba traces. *Int. J. Electr. Power Energy Syst.* **178**, 111940 (2026). https://doi.org/10.1016/j.ijepes.2026.111940

15. Chen, Y. & Zheng, X. To defer or to shift? The role of AI data center flexibility on grid interconnection. In *Proceedings of the 2026 ACM Sustainability Week* 322–327 (ACM, 2026). https://doi.org/10.1145/3765611.3815593

16. Zhao, M., Wang, X. & Mo, J. Workload and energy management of geo-distributed datacenters considering demand response programs. *Sustain. Energy Technol. Assess.* **55**, 102851 (2023). https://doi.org/10.1016/j.seta.2022.102851

17. Wiesner, P., Behnke, I., Scheinert, D., Gontarska, K. & Thamsen, L. Let's wait awhile: how temporal workload shifting can reduce carbon emissions in the cloud. In *Proceedings of the 22nd International Middleware Conference* 260–272 (ACM, 2021). https://doi.org/10.1145/3464298.3493399

18. Cioara, T. et al. Optimized flexibility management enacting data centres participation in smart demand response programs. *Future Gener. Comput. Syst.* **78**, 330–342 (2018). https://doi.org/10.1016/j.future.2016.05.010

19. Wang, W., Abdolrashidi, A., Yu, N. & Wong, D. Frequency regulation service provision in data center with computational flexibility. *Appl. Energy* **251**, 113304 (2019). https://doi.org/10.1016/j.apenergy.2019.05.107

20. Su, T. et al. Grid-enhancing technologies for clean energy systems. *Nat. Rev. Clean Technol.* **1**, 16–31 (2025). https://doi.org/10.1038/s44359-024-00001-5

21. Loji, K., Sharma, S., Sharma, G. & Rawat, T. Multiobjective distribution system operation with demand response to optimize solar hosting capacity, voltage deviation index and network loss. *Sci. Rep.* **15**, 300 (2025). https://doi.org/10.1038/s41598-024-82379-7

22. Fu, Y., Bai, H., Cai, Y., Yang, W. & Li, Y. Optimal configuration method of demand-side flexible resources for enhancing renewable energy integration. *Sci. Rep.* **14**, 7658 (2024). https://doi.org/10.1038/s41598-024-58266-6

23. Davies, D. M. et al. Combined economic and technological evaluation of battery energy storage for grid applications. *Nat. Energy* **4**, 42–50 (2019). https://doi.org/10.1038/s41560-018-0290-1

24. Li, K. et al. Facilitating megacity electricity decarbonization via grid-interactive demand-side resource management. *Nat. Commun.* (2026). https://doi.org/10.1038/s41467-026-76799-4

25. Zhou, Y., Mancarella, P. & Mutale, J. Framework for capacity credit assessment of electrical energy storage and demand response. *IET Gener. Transm. Distrib.* **10**, 2267–2276 (2016). https://doi.org/10.1049/iet-gtd.2015.0458

26. Feng, J. et al. Evaluating demand response impacts on capacity credit of renewable distributed generation in smart distribution systems. *IEEE Access* **6**, 14307–14317 (2018). https://doi.org/10.1109/ACCESS.2017.2745198

27. Wilson, E. et al. *End-Use Load Profiles for the U.S. Building Stock: Methodology and Results of Model Calibration, Validation, and Uncertainty Quantification*. NREL/TP-5500-80889 (National Renewable Energy Laboratory, 2022). https://doi.org/10.2172/1854582

28. Parker, A. et al. *ComStock Reference Documentation: Version 1*. NREL/TP-5500-83819 (National Renewable Energy Laboratory, 2023). https://doi.org/10.2172/1967948

29. Li, S. et al. Heterogeneity at hyperscale: characterization and scheduling of large production AI clusters at Alibaba. In *20th USENIX Symposium on Operating Systems Design and Implementation* 2187–2203 (USENIX Association, 2026).

30. Weng, Q. et al. MLaaS in the wild: workload analysis and scheduling in large-scale heterogeneous GPU clusters. In *19th USENIX Symposium on Networked Systems Design and Implementation* 945–960 (USENIX Association, 2022).

31. Vangel, M. G. One-sided nonparametric tolerance limits. *Commun. Stat. Simul. Comput.* **23**, 1137–1154 (1994). https://doi.org/10.1080/03610919408813222

32. Wilson, E. B. Probable inference, the law of succession, and statistical inference. *J. Am. Stat. Assoc.* **22**, 209–212 (1927). https://doi.org/10.1080/01621459.1927.10502953

33. Brown, L. D., Cai, T. T. & DasGupta, A. Interval estimation for a binomial proportion. *Stat. Sci.* **16**, 101–133 (2001). https://doi.org/10.1214/ss/1009213286

34. Huangfu, Q. & Hall, J. A. J. Parallelizing the dual revised simplex method. *Math. Program. Comput.* **10**, 119–142 (2018). https://doi.org/10.1007/s12532-017-0130-5

## Acknowledgements

[AUTHOR INPUT NEEDED: funding, facilities and non-author contributions.]

## Author Contributions

[AUTHOR INPUT NEEDED: CRediT-aligned author contributions.]

## Competing Interests

[AUTHOR INPUT NEEDED: competing-interests declaration.]

## Figure Legends

### Figure 1 | Nominal flexibility versus the job-derived firm boundary

**a**, Conceptual progression from a fixed nominal flexible-load fraction to job-derived scheduling and a firm grid resource. **b**, Nominal 50% proxy and q = 0.95, 95%-confidence PI tolerance lower bounds for event durations of 1–8 h; shaded differences show nominal overstatement. **c**, GPU-board-power run means used to anchor the class-aware model. Points are GPU observations within a run and horizontal bars are run means; inferential intervals use independent run means as the statistical units. **d**, Evidence hierarchy used in the study. PI denotes perfect information and NA denotes restricted non-anticipative planning. PI values are planning bounds rather than independently certified capacities.

### Figure 2 | Duration, reliability and advance notice shape firm flexibility

**a**, Nominal proxy, q = 0.95 PI tolerance lower bound, matched empirical PI/NA boundary and validation-selected locked-ID candidate across event durations. The apparent empirical PI/NA value above the PI tolerance lower bound reflects different cross-scenario statistics, not an information advantage. The cross marks the q = 0.95, H = 1 h candidate that did not pass locked-ID certification. **b**, Validation-selected candidate capacity for reliability targets q = 0.90, 0.95 and 0.99; open points denote candidates that were not certified. **c**, Mean work eligible for pre-execution and no-control pre-event spare capacity at 6 h notice for 4- and 8-h events (100 development scenarios). Despite exposed eligible work, empirical PI and restricted NA notice gains were 0.0 kW.

### Figure 3 | Repeated dispatch accumulates compute debt before delivery collapses

**a**, Mean paired compute-debt increment by event ordinal for 4- and 8-h events; curves aggregate the declared recovery-gap conditions, with solid lines for validation and dashed lines for development. **b**, residual delivery relative to a same-scenario, same-clock-time fresh-event counterfactual. **c,d**, Joint-episode success for four-event episodes across duration and recovery gap in development (**c**) and validation (**d**), with 100 independent scenarios per cell. The study fixed capacity before validation and is a mechanism diagnostic rather than a repeated-event capacity certificate.

### Figure 4 | Workload flexibility expands community photovoltaic hosting

**a**, Validation joint data-centre–PV feasibility boundary at a maximum 5% PV-curtailment fraction for rigid and flexible workloads with and without BESS. Filled markers denote all 100 scenarios feasible; open markers are partially feasible and are labelled by their feasible-scenario count. **b**, scenario-paired PV-hosting gain at a 201-kW data centre in development and validation. **c**, validation flexible-minus-rigid changes in PV curtailment, PV utilisation and grid import for a fixed 500-kW PV system. **d**, validation difference-in-differences interactions between AI flexibility and BESS or PV; the grey band shows the ±10.05-kW practical margin. Error bars in **b–d** are Bonferroni 95% simultaneous confidence intervals from 10,000 scenario-level bootstrap resamples (n = 100 scenarios).

### Figure 5 | Sensitivity and independent evaluation define the generalisation boundary

**a**, q = 0.95 PI tolerance lower bound under lower, nominal and upper hardware-power cases. **b**, range of capacity changes from the reference for predeclared workload, success-criterion and infrastructure sensitivities at H = 4 and 8 h. **c**, one-sided 95% Wilson lower confidence bounds for q = 0.95 validation-selected candidates replayed on 500 locked-ID and 500 locked-OOD episodes per duration. The dashed line is the q = 0.95 certification threshold; the H = 1 h locked-ID candidate is not certified. Notice levels produced identical points and are shown once per duration. Locked-OOD replay did not re-estimate OOD capacity.
