<!--
Working manuscript, version 0.3.
Nature Communications Article order follows the current journal guidance.
Inline figures are included for repository review and can be moved to separate files at submission.
Square-bracketed items require author input or a verified citation; they are not publication text.
-->

# Job-derived flexibility limits firm demand response and expands photovoltaic hosting

## Authors

[AUTHOR NAMES AND AFFILIATIONS]

*Correspondence: [CORRESPONDING AUTHOR EMAIL]*

## Abstract

Rapid growth in artificial-intelligence computing is increasing pressure on electricity networks, yet deferrable computing may provide demand response. Static models that label data-centre load as flexible ignore job deadlines, recovery and delivery reliability. We derive firm capacity from trace-calibrated jobs, hardware-anchored power measurements and community energy constraints. A nominal 100.50-kilowatt resource exceeded the 95%-reliable perfect-information boundary by 47.3–62.4% across one- to eight-hour events. Repeated dispatch accumulated 0.55–1.38 megawatt-hours of compute debt by the fourth event. Job-feasible scheduling also increased photovoltaic capacity feasible across all 100 validation scenarios by 32.83–33.38 kilowatts, and a zero-deadline-miss sensitivity preserved these gains. Independent in-distribution testing certified 15 of 18 capacity cells, whereas none retained target reliability after a joint out-of-distribution shift. Here, we show that data-centre demand response is a finite, state- and distribution-dependent resource whose credible use requires workload-derived qualification and local validation.

## Introduction

Artificial-intelligence (AI) computing is becoming a material source of electricity demand. Rapid load growth can challenge generation adequacy, delay network connection and concentrate new demand in already constrained regions.<sup>1</sup> Yet the electrical load of an AI data centre is not indivisible. Training and offline-inference jobs can often be paused, slowed or shifted within service limits, creating an opportunity to operate the facility as a grid-interactive resource. A field demonstration on a 256-GPU cluster recently sustained a 25% reduction in data-centre power for three hours while maintaining the tested quality-of-service requirements.<sup>2</sup> This establishes technical potential, but power-system planning requires a further quantity: the reduction that can be committed for a specified duration and reliability without transferring unacceptable risk to computing services.

Data-centre demand response has consequently been studied through batch-workload scheduling, server power management, workload migration and local generation.<sup>3–7</sup> Operational systems have also shifted computing across hours or locations to follow electricity-system carbon signals and renewable availability.<sup>8–11</sup> These studies demonstrate that computational demand has temporal and spatial degrees of freedom, and that workload information can be converted into lower coincident peaks, lower emissions or demand-response delivery. Online pause-and-resume formulations further show that workload switching and incomplete future information impose real scheduling costs,<sup>12</sup> while GPU power-capping experiments show that electrical response can be obtained without treating accelerator power as fixed.<sup>13</sup>

Recent studies move closer to grid-facing quantification. Alibaba-trace analyses estimate the demand-response potential of deferrable computing and the value of notification time,<sup>14</sup> capacity-expansion models test how deferral and geographical shifting could change data-centre interconnection requirements,<sup>15</sup> and geo-distributed scheduling coordinates workloads, energy systems and demand-response programmes.<sup>16</sup> Temporal-shifting studies likewise show that deadlines and forecast error alter the emissions value of moving work across hours.<sup>17</sup> These results establish several routes through which computing flexibility can affect the grid. The complementary requirement addressed here is to qualify a site-level power commitment: how much reduction remains feasible for a declared duration and reliability, how a causal implementation is separated from a full-information planning bound, and how prior dispatch changes the state from which the next call begins.

However, the resource used in a grid study is often simpler than the computing system that must deliver it. A fixed flexible fraction of peak demand or an aggregate energy budget does not preserve each job's release time, processing requirement, workload class and deadline. Even workload-aware analyses commonly report the outcome of a selected controller or an optimal schedule under one event design rather than a statistically qualified capacity surface. Such a result cannot by itself distinguish three sources of apparent flexibility: a nominal assumption, a physical planning boundary available under full future information, and a capacity that a fixed causal scheduler can deliver on new episodes. A nominally flexible megawatt is therefore not necessarily a firm megawatt.

The temporal boundary extends beyond one call. Moving work out of an event does not remove it; it creates a future processing obligation that must be completed before its deadline. Repeated dispatch may consequently accumulate deferred work even when every immediate reduction appears satisfactory. Existing work has considered switching costs, quality-of-service constraints and flexible-resource management,<sup>5,12,18,19</sup> but the grid-facing implication of this deferred obligation remains under-characterised. In particular, elapsed time between events is not equivalent to recovery if the intervening hours contain insufficient compute headroom.

Power reduction is also only an intermediate outcome. At a community point of common coupling (PCC), flexible computing, photovoltaic (PV) generation and battery energy storage systems (BESS) act on the same time-coupled network constraints. Demand-side resources can increase renewable integration and PV hosting,<sup>20–22</sup> whereas storage provides a partially overlapping source of temporal flexibility.<sup>23</sup> Recent community-scale demand-side resource management has shown that coordinating heterogeneous flexible loads can change generation–demand mismatch and grid-upgrade pathways.<sup>24</sup> For AI data centres, the corresponding system question is whether the smaller job-feasible resource—not a nominal flexible fraction—expands the joint data-centre–PV feasibility boundary, increases use of installed PV, and complements or substitutes for BESS.

Here we derive firm demand-response capacity from trace-calibrated AI jobs, hardware-anchored power measurements and explicit service constraints, and evaluate its consequences in a community PCC–PV–BESS system. We distinguish nominal flexibility, a perfect-information (PI) planning boundary, a restricted non-anticipative (NA) planning boundary and an independently tested causal certificate. We then use matched fresh-event counterfactuals to quantify compute-debt accumulation under repeated calls, and joint planning models to measure PV hosting and utilisation. Frozen development, validation, locked in-distribution (locked-ID) and locked out-of-distribution (locked-OOD) ensembles separate mechanism development from final reliability testing. Together, these analyses determine how job constraints, event duration, reliability, advance notice and prior dispatch shape the grid resource that an AI data centre can credibly provide, and how that resource changes a community renewable-integration boundary.

## Results

### Nominal load flexibility overstates job-derived firm capacity

We first tested whether a fixed flexible-load fraction represented the power reduction supported by job-feasible schedules. The reference workload mix produced an operating peak of 201.00 kW, such that a nominal flexibility fraction of 50% implied a constant 100.50-kW resource (Fig. 1a,b). In contrast, the q = 0.95 PI lower-tolerance boundary derived from 100 frozen development scenarios was 53.01 kW for a 1-h event and declined to 44.46, 41.19, 40.15, 40.15 and 37.76 kW for events lasting 2, 3, 4, 6 and 8 h, respectively. Expressed relative to the reference operating peak, job-derived capacity therefore declined from 26.4% at 1 h to 18.8% at 8 h. The nominal proxy overstated this PI boundary by 47.50–62.74 kW, equivalent to 47.3–62.4% of the nominal resource. The gap persisted across every tested duration and arose before imposing an online-controller limitation.

The conversion from job execution to power was anchored by measurements on four NVIDIA RTX PRO 6000 Blackwell Max-Q GPUs connected through PCIe without NVLink (Fig. 1c). Mean active board power was 259.08 W per GPU for training and 300.02 W per GPU for offline inference; the corresponding 95% t intervals across two independent four-GPU runs were 225.81–292.35 W and 299.69–300.35 W. Idle board power was 13.94 W per GPU in one node-level run, and a held-out workload run had a mean absolute prediction error of 3.80 W. These measurements supplied class-specific power slopes and uncertainty cases; they did not make the four-GPU system a physical surrogate for a utility-scale data centre. Node fixed overhead remained an engineering assumption and was treated separately in sensitivity analysis.

We retained four evidentiary meanings throughout the analysis (Fig. 1d). Nominal flexibility was an assumption, the PI boundary was a full-information physical planning bound, the restricted NA boundary imposed a predeclared information structure on a finite scenario ensemble, and the causal certificate independently tested a fixed implementation. A compact class-aware cumulative scheduling formulation reproduced the earlier job-edge PI formulation at all 18 diagnostic points, with a maximum absolute capacity difference of 0.0 kW. This agreement verified the optimisation reformulation but did not convert a planning bound into a certified capacity.

![Figure 1](../docs/figures/nature_mainline_v1/figure_1_nominal_job_derived_gap.png)

### Duration and reliability shape firm flexibility whereas notice alone may not

We next quantified how event duration, advance notice and the reliability target shaped selectable capacity. On the same 100-scenario development ensemble, the q = 0.95 restricted NA capacity declined from 56.42 kW for a 1-h event to 41.19 kW for an 8-h event (Fig. 2a). The matched empirical PI order statistic was identical to the restricted NA value on this ensemble, giving a descriptive information gap of 0.0 kW under the declared policy class. This equality did not imply that the two estimands were statistically interchangeable: the formal PI tolerance boundary used an exact-binomial nonparametric order statistic, whereas the restricted NA value allowed a fixed number of empirical failures on the development scenarios.

Higher reliability targets further reduced candidate capacity (Fig. 2b). Validation selection at q = 0.90 produced larger candidates than q = 0.95, whereas q = 0.99 produced the smallest candidates. The independent outcomes of these candidates are reported below rather than being folded back into the selection surface. Across q = 0.95 development scenarios, increasing advance notice from 0 to 2 or 6 h changed neither the PI nor the restricted NA capacity at any tested duration. Thus, positive notice gain was not required by the model and was not imposed as a target result.

Mechanism diagnostics explained why additional information did not relax the binding constraint in the frozen Model A scenarios. At 6 h notice, a mean of 1,829 GPU-h of work was eligible for pre-execution before 4- and 8-h events, but the no-control schedule exposed only 133 GPU-h of pre-event spare capacity (Fig. 2c). Paired schedules differed by approximately 1.3 GPU-h per pre-event interval, confirming that the controller used the information. Nevertheless, the q = 0.95 fixed-capacity development success fraction remained 0.92 and the same interval-delivery constraints were binding with and without notice. Advance notice therefore changed schedules without increasing usable firm capacity under the tested workload and headroom conditions.

![Figure 2](../docs/figures/nature_mainline_v1/figure_2_duration_reliability_notice.png)

### Compute debt limits repeated dispatch before power delivery collapses

We tested repeated demand response using episodes containing four events and fixed the 4- and 8-h reductions at 44.00 and 41.19 kW, respectively, before independent validation. Each event was paired with a fresh-event counterfactual at the same scenario and clock time, separating exhaustion caused by prior dispatch from variation in background load and job arrivals. Compute debt increased with event ordinal in both development and validation ensembles (Fig. 3a). By the fourth event, the mean paired debt increment ranged from 0.55 to 1.38 MWh across event durations and recovery gaps.

Immediate power delivery changed much less than the accumulated computing obligation. The fifth-percentile event-4 residual delivery ratio remained between 0.9910 and 1.0000 relative to the matched fresh event (Fig. 3b). Joint-episode success nevertheless ranged from 0.00 to 0.94 in development and from 0.00 to 0.97 in validation (Fig. 3c,d). In the validation ensemble, for example, 4-h events separated by 8 h achieved 0.97 joint success, whereas 8-h events separated by 24 h achieved 0.00. The latter condition also accumulated the largest mean event-4 compute-debt increment.

Success was not monotonic in elapsed recovery time. Longer wall-clock gaps moved later events into different load and arrival conditions and did not guarantee that the intervening schedule contained spare compute headroom. Consequently, time between events was not itself a measure of recovery. None of the repeated-event cells met the predeclared q = 0.95 criterion after accounting for finite-sample uncertainty; even the empirical 0.97 validation cell had a one-sided 95% Wilson lower bound of 0.927. The repeated-event analysis therefore identifies a mechanism and exhaustion boundary, not a repeated-event firm-capacity certificate.

![Figure 3](../docs/figures/nature_mainline_v1/figure_3_compute_debt_exhaustion.png)

### Job-feasible scheduling expands photovoltaic hosting without relying on deadline misses

We placed job-feasible schedules in a perfect-information community PCC–PV–BESS planning model to determine whether workload flexibility changed renewable-integration limits. This planning layer was separate from the locked causal demand-response certificate. The headline PV-hosting problem maximised PV nameplate capacity while limiting curtailed PV energy to 5% of available generation, permitting at most 1% missed GPU-hours and enforcing PCC, terminal-backlog and storage constraints. Across 0.5×, 1×, 2× and 3× the reference data-centre capacity, flexible operation shifted the joint data-centre–PV feasibility boundary outwards with and without BESS (Fig. 4a). At 3× capacity, flexible operation was feasible in all 100 validation scenarios in both storage conditions, whereas rigid operation was feasible in 31 scenarios without BESS and 96 with BESS. Partially feasible cells were retained as descriptive points and were not assigned a zero simultaneous capacity.

At the reference 201-kW data centre, the PV capacity feasible in all 100 validation scenarios increased from 584.69 to 617.52 kW without BESS and from 653.39 to 686.77 kW with BESS: simultaneous-boundary gains of 32.83 and 33.38 kW, respectively. A distinct estimand—the mean of within-scenario flexible-minus-rigid differences—was 44.85 kW (Bonferroni 95% simultaneous confidence interval, 41.68–48.08 kW) without BESS and 43.20 kW (39.99–46.46 kW) with BESS (Fig. 4b). Corresponding development paired-mean gains were 45.66 and 43.35 kW. The close agreement between ensembles supported a planning-level increase in curtailment-constrained PV hosting; it did not establish that the locked causal controller would realise the same PV value.

We separately fixed the data centre at 201 kW and PV at 500 kW to test operation of an already installed system. In validation, flexible schedules increased PV use by 18.37 kWh without BESS (Bonferroni 95% simultaneous confidence interval, 3.73–40.03 kWh) and by 5.76 kWh with BESS (approximately 0–15.86 kWh), with equal reductions in curtailed PV energy (Fig. 4c). PV utilisation increased by 0.0720 and 0.0227 percentage points, respectively. These effects were smaller than in development, particularly with BESS, and flexible schedules used the declared 1% deadline-miss allowance. Repeating both renewable programmes with zero allowed deadline misses preserved the validation simultaneous-boundary gains at 32.825 and 33.377 kW and changed paired-mean hosting or PV-use effects by less than 0.002 kW or 0.000006 kWh, respectively (Supplementary Information). Grid-import reductions were larger than the PV-use changes, but they could not be attributed entirely to increased PV consumption, and the analysis did not establish a general reduction in PCC peak.

An orthogonal 2 × 2 × 2 slice maximised data-centre hosting for rigid or flexible workloads with PV and BESS switched on or off. Workload flexibility increased hosting in all four validation portfolios. The AI×BESS interaction was negative both without PV (−52.31 kW; simultaneous confidence interval, −55.42 to −49.52 kW) and with PV (−88.54 kW; −91.22 to −85.66 kW), indicating substitution under the predeclared 10.05-kW practical margin (Fig. 4d). The AI×PV interaction was complementary without BESS (+44.59 kW; 36.57–52.63 kW). With BESS, its mean remained positive (+8.36 kW; 1.05–15.74 kW) but the interval crossed the practical margin, leaving its magnitude indeterminate. Flexible demand, PV and storage therefore changed the same feasible boundary, but their contributions were not simply additive (Supplementary Table 6).

![Figure 4](../docs/figures/nature_mainline_v1/figure_4_hosting_capacity_interactions.png)

### Independent evaluation defines robustness and generalisation boundaries

We finally tested which conclusions persisted under predeclared model and data perturbations. Power-case sensitivity preserved the decline of PI capacity with duration, while changing its absolute scale (Fig. 5a). In the sparse workload design, lowering flexible-arrival utilisation from 0.65 to 0.50 reduced the q = 0.95 PI boundary by 9.26 kW for a 4-h event and 8.71 kW for an 8-h event; increasing it to 0.80 raised the boundaries by 37.84 and 15.73 kW, respectively (Fig. 5b). The predeclared rigid-utilisation and deadline-slack changes produced no additional capacity change at these diagnostic points. Among service-criterion sensitivities, changing the linked mean and interval delivery threshold shifted capacity, whereas the tested deadline-miss, rebound and recovery-window-relief thresholds did not. These are development planning sensitivities and do not identify universal non-binding constraints.

For causal testing, a fully specified robust model-predictive controller selected one candidate for each duration, notice and reliability cell on the validation ensemble. The specification, configuration, source hashes, scenario hashes and Git commit were frozen before a one-time replay on 500 non-overlapping locked-ID episodes. At q = 0.95, all candidates for H = 2, 3, 4, 6 and 8 h passed for N = 0, 2 and 6 h, yielding 15 certified cells among 18 declared cells (Fig. 5c). The selected capacities were 45.74, 39.65, 39.65, 37.88 and 36.71 kW, with one-sided 95% Wilson lower bounds of 0.969, 0.985, 0.972, 0.964 and 0.972. The H = 1 h candidate of 55.16 kW achieved 477 successes in 500 episodes, but its lower bound of 0.936 did not reach q = 0.95 and it was retained as not certified. The q = 0.90 and q = 0.99 secondary analyses certified 15 and 9 of 18 cells, respectively (Supplementary Table 4).

The same frozen candidates were then replayed, without reselection, on 500 locked-OOD episodes that jointly changed the community profile and workload-arrival process. At q = 0.95, success counts declined to 437, 433, 445, 425, 398 and 383 of 500 for 1-, 2-, 3-, 4-, 6- and 8-h events, and none of the 18 duration–notice cells retained the target reliability (Fig. 5c and Supplementary Table 5). The q = 0.90 and q = 0.99 candidates likewise produced no certified cells. This outcome does not establish that OOD firm capacity is zero, because capacity reselection on the locked-OOD set was prohibited. It instead defines a generalisation boundary: a capacity certified under the frozen Model A distribution requires local revalidation before transfer to a different community and workload distribution.

![Figure 5](../docs/figures/nature_mainline_v1/figure_5_robustness_generalization.png)

## Discussion

This study shows that AI data-centre demand response is better represented as a finite, job-constrained resource than as a fixed share of peak load. In the reference system, only 37.6–52.7% of the nominal 50%-flexibility resource was supported by the q = 0.95 PI boundary; equivalently, 47.3–62.4% of the nominal resource was unsupported, depending on event duration. This does not contradict direct demonstrations of substantial data-centre response. The recent 256-GPU field study established that a 25% reduction could be sustained for three hours in its tested system,<sup>2</sup> whereas our analysis asks how a heterogeneous job population should be translated into a duration- and reliability-indexed commitment before and after an online scheduler is fixed. The two results therefore answer different questions: one demonstrates achievable response in a particular deployment, while the other separates an assumed resource, a physical planning bound and an independently tested capacity certificate.

This separation is important for both power-system models and computing controllers. Workload-aware demand-response policies have shown that scheduling, server power caps and local generation can reduce peaks while protecting quality of service.<sup>4–7</sup> Carbon-aware systems similarly show that flexible work can follow favourable hours or locations.<sup>8–11</sup> Our results add a qualification layer to that literature. The nominal-to-PI gap arises before controller design and measures how job feasibility constrains the resource. The PI-to-NA comparison asks whether the declared information structure removes additional planning value. The causal certificate then asks whether a frozen implementable scheduler retains the selected reliability on unseen, in-distribution episodes. Conflating these layers would attribute physical workload limits to the controller or, conversely, treat an optimisation upper bound as dispatchable capacity.

The closest recent studies reinforce the need for this separation. Trace-derived analyses quantify how deferrable jobs and notification time can support demand response,<sup>14</sup> while grid-planning studies compare temporal deferral with spatial migration as routes to data-centre interconnection and system value.<sup>15,16</sup> Temporal carbon-aware studies quantify related deadline and forecast trade-offs.<sup>17</sup> The contribution here is complementary rather than a controller-performance claim: we define a capacity estimand indexed by duration, notice, reliability, implementation and scenario distribution; expose the deferred-work state left by previous calls; and carry the qualified resource into a community PV–BESS feasible set. This framing makes the unit of comparison a reliable power commitment rather than energy cost, emissions or an unconstrained flexible-load percentage.

Compute debt provides the mechanism connecting an individual dispatch to future service risk. Repeated events accumulated 0.55–1.38 MWh of additional deferred processing energy by the fourth call even though event-level power delivery remained close to a matched fresh-event counterfactual. Immediate delivery can therefore remain apparently healthy while the service state deteriorates. Pause-and-resume and power-capping studies account for transition costs and performance consequences within a scheduling decision,<sup>12,13</sup> whereas compute debt records the inter-event obligation left by that decision. A recovery interval is useful only if it contains sufficient compute headroom to discharge this obligation before future deadlines. This explains why longer elapsed gaps did not produce monotonic recovery in our experiments and why repeatability should be certified at the episode level rather than inferred from isolated-event success.

Advance notice illustrates the distinction between information and physical opportunity. Six hours of notice exposed a large volume of eligible work and changed pre-event schedules, but scarce headroom prevented enough of that work from being executed early to relax the interval-delivery constraint. The resulting zero notice gain is a bounded structural result, not evidence that notice is generally without value. Online scheduling theory and operational carbon-aware systems both show that future information can change when work is executed.<sup>8,12</sup> Our diagnostics identify an additional necessary condition for a capacity gain: eligible pre-executable work, spare pre-event compute capacity and the event's binding service constraint must align. Notice can alter a schedule without increasing the firm reduction.

The community analysis converts job-feasible flexibility into a separate planning-level power-system consequence. Demand response and other grid-enhancing technologies can increase renewable integration by changing the timing and location of binding constraints,<sup>20–22</sup> and community-scale coordination can reshape generation–demand mismatch and infrastructure requirements.<sup>24</sup> Under perfect-information scheduling and the declared 1% missed-GPU-hour allowance, flexible computing increased the all-scenario curtailment-constrained PV hosting boundary by approximately 33 kW at the 201-kW reference data centre; scenario-paired mean gains were approximately 43–45 kW. The same all-scenario boundary was retained when deadline misses were prohibited, excluding the service allowance as the source of the hosting gain. Flexibility's effect on utilisation of an already installed 500-kW PV system was much smaller and became near zero when BESS was available. Hosting and utilisation are therefore distinct estimands, and neither planning result is a causal effect of the locked demand-response controller.

The negative AI×BESS interaction further indicates that flexible computing and electrochemical storage can substitute for one another within the same PCC-constrained feasible set. This does not imply that the two resources are technologically interchangeable. Batteries can exchange electrical energy independently of job arrivals but face power, energy, efficiency and state-of-charge limits;<sup>23</sup> workload flexibility is constrained by releases, deadlines and future service. Their marginal values nevertheless overlap when either resource relaxes the same network or curtailment constraint. Planning studies should therefore model them jointly rather than add separately estimated flexibility values. The positive AI×PV interaction without BESS, and its smaller uncertain magnitude with BESS, provide a concrete example of how portfolio composition changes the value assigned to flexible computing.

These findings suggest a practical qualification sequence. Capacity-credit studies of storage and demand response already show that inter-temporal constraints, recovery and uncertain availability affect adequacy value.<sup>25,26</sup> For a data centre, the operator should first derive a duration–reliability surface from the site's workload and power model, then select a causal scheduler on a separate validation set, and finally certify the fixed offer on independent local episodes. Grid operators can procure the resulting capacity with an explicit event duration, delivery rule and recovery condition rather than a single flexible-load percentage. Repeated calls require a state variable such as compute debt or deadline-weighted backlog, and transfer to another community, workload mix or GPU fleet requires revalidation. The complete failure of the frozen q = 0.95 candidates under the declared joint OOD shift is not evidence that the shifted site has no flexibility; it shows that the original certificate does not travel automatically.

Several boundaries qualify the numerical results. Workloads were represented as fluid and pre-emptible at 1-h resolution; non-pre-emptive jobs, gang scheduling and checkpoint overhead could reduce or reshape the feasible envelope. Community demand came from modelled and measurement-validated building-stock profiles rather than project-owned feeder meters, and job arrivals were trace-calibrated rather than a literal replay of production deadlines. The four-GPU experiments anchored class-specific board power but did not measure whole-facility overhead, cooling dynamics or network power. Model A also represents one declared community scale, workload mixture and scheduling abstraction. Future work should test finer temporal resolution, hardware-in-the-loop dispatch, non-pre-emptible services and cross-site requalification. These extensions may change the magnitude and shape of capacity, but not the central requirement that AI data-centre demand response be derived from service-constrained jobs and validated as a local, state-dependent resource.

## Methods

### Study design and evidence hierarchy

The study separated four capacity concepts. Nominal flexibility was defined as a fixed fraction of the reference-mix operating peak. The PI boundary maximised power reduction with full knowledge of future jobs, community demand and event timing. The restricted NA boundary imposed equality of decisions across scenario histories that were indistinguishable at the decision time. The causal certificate tested a validation-selected, fixed controller on an independent locked ensemble. These quantities were not treated as alternative algorithms estimating the same object: nominal capacity was an assumption, PI and NA were planning boundaries, and only the locked-ID result was an independently evaluated operational certificate.

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

AI batch arrivals were generated from a class-aware synthetic process calibrated to the 2026 Alibaba Serverless Infrastructure trace. The six-month source trace covers 155,410 heterogeneous GPUs and includes development, training, online-inference and offline-inference activity,<sup>29</sup> extending an earlier public Alibaba trace of 6,742 GPUs.<sup>30</sup> We used the official 40,522,321-row job-execution summary, normalised it once, and formed a reproducible 100,000-row bounded sampler with 50,000 low-priority training and 50,000 low-priority offline-inference records. This project-made “Lite” sampler reduced repeated experiment I/O; it was not a separate Alibaba release. An independent-reservoir audit found close central and 95th-percentile job-shape summaries but did not meet one tail-sensitive Wasserstein diagnostic, so full-distribution equivalence was not claimed (Supplementary Information). We used empirical job-size, runtime and GPU-demand distributions rather than replaying source timestamps. The execution summary did not provide the production deadlines required by the present service model; deadlines were therefore generated using the predeclared class-specific slack policy and were always labelled synthetic. The summary-based model also did not reproduce the temporal correlations available in the much larger pod-hourly archive.

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

The NREL End-Use Load Profiles used for community demand are available through the OEDI building-stock data lake. The Alibaba 2026 job-execution summary used for workload calibration is available from the official `cluster-trace-gpu-v2026` release. Exact download locations, retrieval records, preprocessing configurations and SHA-256 hashes for the original archive, the 40,522,321-row normalised table and the project-made 100,000-row sampler are recorded in `data/manifests/sources.yaml`. Raw third-party data are not redistributed by this repository. Frozen scenario manifests, processed Source Data underlying the figures, calibration artifacts and result receipts will be deposited in [REPOSITORY AND DOI TO BE ADDED BEFORE SUBMISSION].

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

**a**, Conceptual progression from a fixed nominal flexible-load fraction to job-derived scheduling and a firm grid resource. **b**, Nominal 50% proxy and q = 0.95, 95%-confidence PI lower-tolerance capacities for event durations of 1–8 h; shaded differences show nominal overstatement. **c**, GPU-board-power run means used to anchor the class-aware model. Points are GPU observations within a run and horizontal bars are run means; inferential intervals use independent run means as the statistical units. **d**, Evidence hierarchy used in the study. PI denotes perfect information and NA denotes restricted non-anticipative planning. PI values are planning bounds rather than independently certified capacities.

### Figure 2 | Duration, reliability and advance notice shape firm flexibility

**a**, Nominal proxy, q = 0.95 PI tolerance boundary, restricted NA development boundary and validation-selected locked-ID candidate capacity across event durations. The cross marks the q = 0.95, H = 1 h candidate that did not pass locked-ID certification. **b**, Validation-selected candidate capacity for reliability targets q = 0.90, 0.95 and 0.99; open points denote candidates that were not certified. **c**, Mean work eligible for pre-execution and no-control pre-event spare capacity at 6 h notice for 4- and 8-h events (100 development scenarios). Despite exposed eligible work, PI and restricted NA notice gains were 0.0 kW.

### Figure 3 | Repeated dispatch accumulates compute debt before delivery collapses

**a**, Mean paired compute-debt increment by event ordinal for 4- and 8-h events; curves aggregate the declared recovery-gap conditions, with solid lines for validation and dashed lines for development. **b**, residual delivery relative to a same-scenario, same-clock-time fresh-event counterfactual. **c,d**, Joint-episode success for four-event episodes across duration and recovery gap in development (**c**) and validation (**d**), with 100 independent scenarios per cell. The study fixed capacity before validation and is a mechanism diagnostic rather than a repeated-event capacity certificate.

### Figure 4 | Workload flexibility expands community photovoltaic hosting

**a**, Validation joint data-centre–PV feasibility boundary at a maximum 5% PV-curtailment fraction for rigid and flexible workloads with and without BESS. Filled markers denote all 100 scenarios feasible; open markers are partially feasible and are labelled by their feasible-scenario count. **b**, scenario-paired PV-hosting gain at a 201-kW data centre in development and validation. **c**, validation flexible-minus-rigid changes in PV curtailment, PV utilisation and grid import for a fixed 500-kW PV system. **d**, validation difference-in-differences interactions between AI flexibility and BESS or PV; the grey band shows the ±10.05-kW practical margin. Error bars in **b–d** are Bonferroni 95% simultaneous confidence intervals from 10,000 scenario-level bootstrap resamples (n = 100 scenarios).

### Figure 5 | Sensitivity and independent evaluation define the generalisation boundary

**a**, q = 0.95 PI capacity under lower, nominal and upper hardware-power cases. **b**, range of capacity changes from the reference for predeclared workload, success-criterion and infrastructure sensitivities at H = 4 and 8 h. **c**, one-sided 95% Wilson lower confidence bounds for q = 0.95 validation-selected candidates replayed on 500 locked-ID and 500 locked-OOD episodes per duration. The dashed line is the q = 0.95 certification threshold; the H = 1 h locked-ID candidate is not certified. Notice levels produced identical points and are shown once per duration. Locked-OOD replay did not re-estimate OOD capacity.
