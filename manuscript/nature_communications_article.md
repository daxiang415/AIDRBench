<!--
Working manuscript, version 0.1.
Nature Communications Article order follows the current journal guidance.
Inline figures are included for repository review and can be moved to separate files at submission.
Square-bracketed items require author input or a verified citation; they are not publication text.
-->

# Job-derived firm demand response expands community photovoltaic hosting and utilisation

## Authors

[AUTHOR NAMES AND AFFILIATIONS]

*Correspondence: [CORRESPONDING AUTHOR EMAIL]*

## Abstract

Rapid growth in artificial-intelligence computing is increasing pressure on electricity networks, but deferrable computing may also provide demand response. Static representations that label a fixed fraction of data-centre load as flexible ignore job deadlines, recovery obligations and delivery reliability. Here we derive firm demand-response capacity from trace-calibrated jobs, hardware-anchored power measurements and community energy constraints. A nominal 50% flexible-load assumption yielded 100.50 kW, whereas the 95%-reliable perfect-information boundary declined from 53.01 kW for a 1-h event to 37.76 kW for an 8-h event, an overstatement of 47.3–62.4%. Repeated dispatch accumulated 0.55–1.38 MWh of compute debt by the fourth event while power delivery remained near its fresh-event level. At a 201-kW data centre, job-feasible flexibility increased photovoltaic hosting by 44.85 kW without battery storage and 43.20 kW with storage, although fixed-photovoltaic utilisation gains were small. Independent in-distribution testing certified 15 of 18 declared capacity cells, whereas none retained target reliability under a joint out-of-distribution shift. These results establish data-centre demand response as a finite, state- and distribution-dependent grid resource that requires local validation.

## Introduction

Artificial-intelligence (AI) computing is becoming a material source of electricity demand, creating new challenges for generation adequacy, network connection and local power-system operation. The same facilities also contain training and offline-inference jobs whose execution can, in principle, be shifted in time. This combination has motivated proposals to treat AI data centres as demand-responsive resources rather than inflexible loads. However, the grid value of such flexibility depends on how much power can be reduced at a requested time without transferring unacceptable risk to computing services. [CITATIONS: AI electricity-demand growth; data-centre interconnection constraints; demand-response value.]

Existing energy-system studies commonly represent data-centre flexibility as a fixed fraction of peak demand or as an aggregate energy budget. Such representations are convenient for planning but do not preserve the release time, processing requirement, workload class or deadline of each job. They also obscure the fact that shifting work out of a demand-response event creates a future processing obligation. A nominally flexible megawatt is therefore not necessarily a megawatt that can be committed for a specified duration and reliability. [CITATIONS: data-centre load-shifting models; workload-aware scheduling; firm demand-response qualification.]

Two further gaps limit system-level interpretation. First, a successful isolated curtailment does not establish that the same response can be called repeatedly: deferred work can accumulate as compute debt even while immediate power delivery remains satisfactory. Second, power reduction alone does not quantify value to a local energy system. The relevant downstream questions are whether job-feasible flexibility expands the joint data-centre–photovoltaic (PV) feasibility boundary, increases use of installed PV, and complements or substitutes for a battery energy storage system (BESS). [CITATIONS: rebound and recovery in demand response; PV hosting capacity; flexible demand and storage interactions.]

Here we derive firm demand-response capacity from trace-calibrated AI jobs and evaluate its consequences in a community point-of-common-coupling (PCC)–PV–BESS system. We distinguish nominal flexibility, a perfect-information (PI) planning boundary, a restricted non-anticipative (NA) planning boundary and an independently tested causal certificate. We then use matched fresh-event counterfactuals to quantify compute-debt accumulation under repeated calls, and use joint planning models to measure PV hosting and utilisation. Frozen development, validation, locked in-distribution (locked-ID) and locked out-of-distribution (locked-OOD) ensembles separate mechanism development from final reliability testing. Together, these analyses test how job constraints, event duration, reliability, advance notice and prior dispatch determine the grid resource that an AI data centre can credibly provide.

## Results

### Nominal load flexibility overstates job-derived firm capacity

We first tested whether a fixed flexible-load fraction represented the power reduction supported by job-feasible schedules. The reference workload mix produced an operating peak of 201.00 kW, such that a nominal flexibility fraction of 50% implied a constant 100.50-kW resource (Fig. 1a,b). In contrast, the q = 0.95 PI lower-tolerance boundary derived from 100 frozen development scenarios was 53.01 kW for a 1-h event and declined to 44.46, 41.19, 40.15, 40.15 and 37.76 kW for events lasting 2, 3, 4, 6 and 8 h, respectively. The nominal proxy therefore overstated the job-derived PI boundary by 47.50–62.74 kW, equivalent to 47.3–62.4% of the nominal resource. The gap persisted across every tested duration and arose before imposing an online-controller limitation.

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

### Firm demand response expands community photovoltaic hosting and utilisation

We placed the job-feasible schedules in a community PCC–PV–BESS planning model to determine whether the remaining flexibility changed renewable-integration limits. The headline PV-hosting problem maximised PV nameplate capacity while limiting curtailed PV energy to 5% of available generation and enforcing PCC, workload-service and storage constraints. Across 0.5×, 1×, 2× and 3× the reference data-centre capacity, flexible operation shifted the joint data-centre–PV feasibility boundary outwards with and without BESS (Fig. 4a). At 3× capacity, flexible operation was feasible in all 100 validation scenarios in both storage conditions, whereas rigid operation was feasible in 31 scenarios without BESS and 96 with BESS. Partially feasible cells were retained as descriptive points and were not assigned a zero simultaneous capacity.

At the reference 201-kW data centre, the PV capacity feasible in all 100 validation scenarios increased from 584.69 to 617.52 kW without BESS and from 653.39 to 686.77 kW with BESS. Scenario-paired mean gains were 44.85 kW (Bonferroni 95% simultaneous confidence interval, 41.68–48.08 kW) without BESS and 43.20 kW (39.99–46.46 kW) with BESS (Fig. 4b). Corresponding development gains were 45.66 and 43.35 kW. The close agreement between ensembles supported a robust planning-level increase in curtailment-constrained PV hosting while preserving the distinction between an ensemble planning result and a deployed causal effect.

We separately fixed the data centre at 201 kW and PV at 500 kW to test operation of an already installed system. In validation, flexible schedules increased PV use by 18.37 kWh without BESS (Bonferroni 95% simultaneous confidence interval, 3.73–40.03 kWh) and by 5.76 kWh with BESS (approximately 0–15.86 kWh), with equal reductions in curtailed PV energy (Fig. 4c). PV utilisation increased by 0.0720 and 0.0227 percentage points, respectively. These effects were smaller than in development, particularly with BESS, and flexible schedules used the declared 1% deadline-miss allowance. Grid-import reductions were larger than the PV-use changes, but they could not be attributed entirely to increased PV consumption, and the analysis did not establish a general reduction in PCC peak.

An orthogonal 2 × 2 × 2 slice maximised data-centre hosting for rigid or flexible workloads with PV and BESS switched on or off. Workload flexibility increased hosting in all four validation portfolios. The AI×BESS interaction was negative both without PV (−52.31 kW; simultaneous confidence interval, −55.42 to −49.52 kW) and with PV (−88.54 kW; −91.22 to −85.66 kW), indicating substitution under the predeclared 10.05-kW practical margin (Fig. 4d). The AI×PV interaction was complementary without BESS (+44.59 kW; 36.57–52.63 kW). With BESS, its mean remained positive (+8.36 kW; 1.05–15.74 kW) but the interval crossed the practical margin, leaving its magnitude indeterminate. Flexible demand, PV and storage therefore changed the same feasible boundary, but their contributions were not simply additive.

![Figure 4](../docs/figures/nature_mainline_v1/figure_4_hosting_capacity_interactions.png)

### Independent evaluation defines robustness and generalisation boundaries

We finally tested which conclusions persisted under predeclared model and data perturbations. Power-case sensitivity preserved the decline of PI capacity with duration, while changing its absolute scale (Fig. 5a). In the sparse workload design, lowering flexible-arrival utilisation from 0.65 to 0.50 reduced the q = 0.95 PI boundary by 9.26 kW for a 4-h event and 8.71 kW for an 8-h event; increasing it to 0.80 raised the boundaries by 37.84 and 15.73 kW, respectively (Fig. 5b). The predeclared rigid-utilisation and deadline-slack changes produced no additional capacity change at these diagnostic points. Among service-criterion sensitivities, changing the linked mean and interval delivery threshold shifted capacity, whereas the tested deadline-miss, rebound and recovery-window-relief thresholds did not. These are development planning sensitivities and do not identify universal non-binding constraints.

For causal testing, a fully specified robust model-predictive controller selected one candidate for each duration, notice and reliability cell on the validation ensemble. The specification, configuration, source hashes, scenario hashes and Git commit were frozen before a one-time replay on 500 non-overlapping locked-ID episodes. At q = 0.95, all candidates for H = 2, 3, 4, 6 and 8 h passed for N = 0, 2 and 6 h, yielding 15 certified cells among 18 declared cells (Fig. 5c). The selected capacities were 45.74, 39.65, 39.65, 37.88 and 36.71 kW, with one-sided 95% Wilson lower bounds of 0.969, 0.985, 0.972, 0.964 and 0.972. The H = 1 h candidate of 55.16 kW achieved 477 successes in 500 episodes, but its lower bound of 0.936 did not reach q = 0.95 and it was retained as not certified. The q = 0.90 and q = 0.99 secondary analyses certified 15 and 9 of 18 cells, respectively.

The same frozen candidates were then replayed, without reselection, on 500 locked-OOD episodes that jointly changed the community profile and workload-arrival process. At q = 0.95, success counts declined to 437, 433, 445, 425, 398 and 383 of 500 for 1-, 2-, 3-, 4-, 6- and 8-h events, and none of the 18 duration–notice cells retained the target reliability (Fig. 5c). The q = 0.90 and q = 0.99 candidates likewise produced no certified cells. This outcome does not establish that OOD firm capacity is zero, because capacity reselection on the locked-OOD set was prohibited. It instead defines a generalisation boundary: a capacity certified under the frozen Model A distribution requires local revalidation before transfer to a different community and workload distribution.

![Figure 5](../docs/figures/nature_mainline_v1/figure_5_robustness_generalization.png)

## Discussion

This study shows that AI data-centre demand response is better represented as a finite, job-constrained resource than as a fixed share of peak load. In the reference system, a nominal 50% flexibility assumption overstated the q = 0.95 PI boundary by 47.3–62.4%, depending on event duration. The gap emerged from workload feasibility rather than from controller performance, and independent testing further separated selectable planning capacity from capacity that could be certified for a fixed causal implementation. These distinctions matter whenever a power-system model assigns a reliability value to flexible computing.

The results also identify compute debt as a mechanism connecting an individual dispatch to future service risk. Repeated events accumulated a substantial deferred computing obligation even while event-level power delivery remained close to a matched fresh-event counterfactual. This explains why immediate delivery metrics can overstate repeatability and why recovery cannot be inferred from elapsed time alone. A useful recovery interval must contain enough spare compute headroom to repay deferred work; otherwise the obligation is merely shifted into a different operating period.

Advance notice illustrates the same distinction between information and physical opportunity. Six hours of notice exposed a large volume of eligible work and changed pre-event schedules, but scarce headroom prevented that work from being executed early enough to relax the interval-delivery constraint. The zero notice gain observed here is therefore a bounded structural result, not evidence that notice is generally without value. Positive gain should be expected only when eligible work, pre-event headroom and the future binding constraint align. [CITATIONS: value of advance notice and anticipatory demand scheduling.]

The community analysis translates the remaining flexibility into two different renewable-integration outcomes. Job-feasible scheduling robustly expanded curtailment-constrained PV hosting in independent validation, whereas its effect on utilisation of an already installed 500-kW PV system was small and profile-dependent, especially when BESS was present. The negative AI×BESS interaction further indicates that flexible computing and storage can substitute for one another within the same PCC-constrained feasible set. Planning studies should therefore avoid adding independent flexibility values for workloads, PV and storage without modelling their joint constraints.

Several boundaries qualify these findings. Workloads were represented as fluid and pre-emptible at 1-h resolution; non-pre-emptive jobs, gang scheduling and checkpoint overhead could reduce or reshape the feasible envelope. Community demand came from modelled and measurement-validated building-stock profiles rather than project-owned feeder meters, and job arrivals were trace-calibrated rather than a literal replay of production deadlines. The four-GPU experiments anchored class-specific board power but did not measure whole-facility overhead. Most importantly, frozen candidates did not preserve reliability under the declared joint OOD shift. The present results therefore support local, distribution-specific qualification of data-centre demand response, not universal transfer across sites or GPU generations. Future work can test finer temporal resolution, non-pre-emptible workloads, hardware-in-the-loop operation and cross-site requalification without changing the central requirement that firm capacity be derived and independently validated.

## Methods

### Study design and evidence hierarchy

The study separated four capacity concepts. Nominal flexibility was defined as a fixed fraction of the reference-mix operating peak. The PI boundary maximised power reduction with full knowledge of future jobs, community demand and event timing. The restricted NA boundary imposed equality of decisions across scenario histories that were indistinguishable at the decision time. The causal certificate tested a validation-selected, fixed controller on an independent locked ensemble. Development scenarios were used to establish mechanisms and freeze the design; validation scenarios were used for independent planning replication and candidate selection; locked-ID scenarios were used once for in-distribution certification; and locked-OOD scenarios were used once for transfer stress testing without reselection.

The single-event analysis treated one episode as one Bernoulli trial. The repeated-event analysis treated the complete multi-event episode as the independent unit; individual events within the same episode were not treated as independent observations. Hardware uncertainty was estimated across independent workload runs, not across GPUs observed within one run.

### Community, workload and event data

Community background demand was drawn from National Laboratory of the Rockies/National Renewable Energy Laboratory End-Use Load Profiles for ResStock detached residences and ComStock small offices in ASHRAE climate zones 3A, 3C and 5A. These profiles are physics-based building-stock aggregates calibrated and validated against measured data; they are not direct feeder measurements collected in this project. Profiles retained their temporal shape and were normalised to the declared community peak.

AI batch arrivals were generated from a class-aware synthetic process calibrated to the Alibaba GPU cluster trace. The source trace supplied empirical job sizes, runtimes and GPU demand, but did not contain production deadlines. Deadlines were therefore generated using a predeclared slack policy and were always labelled synthetic. Training and offline-inference classes were preserved separately. Demand-response events were sampled from configured peak-time windows with declared durations, notices and reduction requests; they were experimental scenarios rather than observed utility dispatch records.

### Workload and power model

Each job was represented by a release time, workload class, GPU-hour requirement and deadline. Available work entered an earliest-deadline-first fluid queue. For class c and hour t, backlog evolved as

\[
B_{c,t+1}=B_{c,t}+A_{c,t}-X_{c,t}-M_{c,t},
\]

where A was newly released work, X was executed work and M was unfinished work expiring at its deadline. Schedules obeyed per-hour GPU capacity, work conservation, release and deadline constraints, a declared deadline-miss allowance and a terminal-backlog constraint. Rigid and flexible workload fractions were modelled separately, and optimisation retained class-specific execution variables.

Data-centre power was

\[
P^{\mathrm{DC}}_t=P_{\mathrm{fixed}}+\sum_c e_cX_{c,t},
\]

where e_c was the class-specific incremental energy per executed GPU-hour. Board-power parameters were fitted from four-GPU measurements and stored in a hash-verified calibration artifact. Training and offline-inference active-power estimates were 259.08 and 300.02 W per GPU, respectively; idle power was 13.94 W per GPU. The nominal model used power-usage effectiveness of 1.2 and an assumed node fixed overhead of 300 W, with declared lower and upper cases evaluated separately. Reference-mix operating peak was calculated from the reference workload composition and was kept distinct from a worst-class nameplate peak.

### Hourly environment, baselines and compute debt

The environment used a 1-h time step. At each step, new arrivals were released before the control action, eligible work was scheduled, class-specific power was calculated, and queue deadlines advanced by one hour. Each controlled episode was paired with a no-demand-response baseline generated from the same frozen exogenous inputs. Event delivery was therefore evaluated as a baseline-relative power reduction rather than against an unrelated historical profile.

Compute debt quantified the additional future dynamic energy obligation associated with deferred backlog relative to the paired baseline:

\[
D^{\mathrm{comp}}_t=\sum_c \Delta B_{c,t}\,\mathrm{PUE}\left(P^{\mathrm{active}}_c-P^{\mathrm{idle}}\right),
\]

where \(\Delta B_{c,t}\) was controlled backlog minus matched baseline backlog. Recovery and rebound were evaluated over the declared post-event window, and simulations included a tail period to evaluate terminal backlog.

### Demand-response delivery and service criteria

A candidate reduction R succeeded only if all declared criteria were met. Mean event delivery had to be at least 0.95, and every event hour had to satisfy

\[
P^{\mathrm{control}}_t \leq P^{\mathrm{baseline}}_t-0.95R.
\]

The episode also had to satisfy limits on deadline misses, rebound, event-plus-recovery peak relief and terminal backlog. The headline configuration allowed a deadline-miss fraction of 0.01, a rebound ratio of 0.25 and a recovery-window peak-relief fraction of 0.50. Mean delivery and minimum interval delivery were reported separately; event-average energy delivery was not used as a substitute for hourly compliance.

### Perfect-information, non-anticipative and causal capacity

For each scenario, the PI programme maximised R subject to workload, power and service constraints. Cross-scenario PI firm capacity used an exact-binomial nonparametric lower-tolerance order statistic at reliability q and confidence 0.95. If the scenario count was insufficient for a requested q, the value was marked not estimable rather than set to zero. The restricted NA programme enforced equal decisions for scenario histories sharing the same available information and reported an empirical finite-ensemble bound. A matched empirical PI order statistic using the same allowed failure count was used only for descriptive comparison with restricted NA.

The causal implementation was a robust model-predictive controller with every parameter explicitly declared in a versioned configuration. It observed only released jobs, the current queue, short-horizon community forecasts and demand-response requests inside the notice window. Validation selection used a predeclared fine search to freeze one candidate per duration, notice and reliability target. Selection records stored the normalised controller specification, configuration SHA-256, Git commit, source hashes and scenario hashes. Locked evaluation failed closed if any recorded artifact differed. A candidate was certified when the one-sided 95% Wilson lower confidence bound of success on 500 locked-ID episodes was at least q.

### Repeated-event counterfactual design

Repeated-event episodes contained four events of duration 4 or 8 h separated by recovery gaps of 2, 4, 8, 12 or 24 h. Capacities were fixed from development results before validation. For each event, a fresh-event counterfactual used the same scenario and clock time but removed the influence of prior events. Residual flexibility was the delivered reduction in the repeated trajectory divided by delivery in this matched fresh event. Event-local delivery was reported separately from joint-episode success, which required every event and all episode-level service criteria to pass.

### Renewable-integration optimisation

Community PCC power was

\[
P^{\mathrm{PCC}}_t=L_t+P^{\mathrm{DC}}_t+P^{\mathrm{ch}}_t-P^{\mathrm{dis}}_t-G^{\mathrm{PV}}_t,
\]

and was constrained by the declared PCC capacity. The PV-hosting programme fixed data-centre capacity and maximised PV nameplate capacity subject to a headline curtailment fraction of at most 0.05, with 0, 0.10 and 0.20 evaluated as sensitivities. BESS operation enforced energy and power limits, mutually exclusive charging and discharging, and terminal state of charge. A simultaneous PV capacity was reported only when all 100 scenarios were feasible; otherwise the number of feasible scenarios and the scenario-wise range were reported without assigning zero capacity.

The fixed-operation analysis set data-centre capacity to the 201-kW reference and PV capacity to 500 kW. A lexicographic objective first preserved workload service feasibility and then maximised local PV use. Outcomes included PV energy used and curtailed, PV utilisation, renewable demand share, grid import, PCC peak and BESS throughput. A separate 2 × 2 × 2 design maximised data-centre hosting under rigid or flexible workloads with PV and BESS switched on or off. Predeclared difference-in-differences contrasts quantified AI×PV and AI×BESS interactions.

### Statistical analysis and reproducibility

Scenario-paired effects used a frozen scenario as the independent unit. Confidence intervals for the renewable-integration contrasts were obtained from 10,000 scenario-level bootstrap resamples with Bonferroni control over each predeclared family. Interaction labels used a practical equivalence margin of 10.05 kW. Repeated-event proportions and causal certificates used episodes as independent units; one-sided Wilson lower bounds were calculated for frozen candidates. No post hoc capacity reselection was performed on locked-ID or locked-OOD outcomes.

Every formal result recorded the Git commit, protocol version, scenario and input-data hashes, calibration-artifact hash, power case, seed range, solver settings, controller configuration and failure reasons. Source-data tables underlying all main figures and per-figure manifests bind the plotted values to these records. [AUTHOR INPUT NEEDED: final software versions and computing environment for submission Methods.]

## Data Availability

The community profiles and AI workload traces used to parameterise the study are available from their original public repositories; exact source locations and SHA-256 hashes are recorded in `data/manifests/sources.yaml`. Raw third-party data are not redistributed by this repository. Frozen scenario manifests, processed source data underlying the figures and result receipts will be deposited in [REPOSITORY AND DOI TO BE ADDED BEFORE SUBMISSION].

## Code Availability

The AIDRBench source code, versioned configurations and scripts used to generate the reported results are available at https://github.com/daxiang415/AIDRBench. The submission version will be archived with an immutable release and DOI at [ZENODO DOI TO BE ADDED].

## References

[REFERENCES TO BE ADDED AFTER CLAIM-BY-CLAIM LITERATURE VERIFICATION.]

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
