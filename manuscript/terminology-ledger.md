# v0.25 terminology clarification

| Canonical term | Meaning and boundary |
|---|---|
| Submission-count weights | Hourly job counts used to distribute a fixed weekly work total |
| Task-resource-time weights | Requested GPU-equivalents times task launch-to-completion duration, aggregated by submitted job |
| Hourly permutation | Reorders whole-hour blocks; changes temporal dependence and alignment with calls/community together |
| Instantaneous supply margin | Baseline PCC minus community minus fixed DC power minus 95% of the request |
| Relaxed-PI tolerance statistics | Statistics of aggregate release/deadline relaxation; no work-group feasibility guarantee |
| Zero-miss success criterion | A successful series must miss no work within the numerical tolerance; qualification still uses a 95% overall success target |

## Retained earlier terminology records

# v0.24 terminology correction

- Earlier PI values: relaxed planning statistics; not guaranteed feasible capacities for individual job windows.
- New PI diagnosis: fixed-request exact-window feasibility, not a causal certificate.
- Resource-time transfer: task allocation-time weighted, normalised observed-week submission structure; not sensor GPU activity or application validation.
- Zero-loss qualification: a probabilistic criterion on scenario-level zero missed work, not every confirmation trajectory being lossless.
- Current reference repeated offers: 5.603331 / 4.423682 kW at four/eight hours, 16-h start spacing.

## Earlier terminology history

# AIDRBench manuscript terminology ledger

This ledger is normative for the Nature Communications manuscript. English prose uses British spelling (`data centre`, `utilisation`, `optimisation`), while code identifiers retain their repository spelling.

| Canonical term | First-use definition | Avoid or distinguish from |
|---|---|---|
| AI data centre | artificial-intelligence (AI) data centre | `datacenter`; a four-GPU workstation is only the measurement anchor |
| demand response (DR) | demand response (DR) | generic load shifting without a grid request |
| firm DR qualification | derivation and independent testing of a service-feasible power commitment for declared duration, reliability and scenario distribution | benchmark performance; proof that load is merely adjustable |
| nominal flexibility | a fixed fraction of operating peak assumed to be flexible | firm flexibility |
| deferrable-work share | fraction of main-horizon GPU-hours permitted to move in time; f in the declared workload scenarios | nominal power fraction; GPU allocation |
| flexible GPU-pool share | fraction of physical GPUs assigned to schedulable work; g, with integer GPU counts retained | share of offered work; curtailable power fraction |
| arrival scaling coefficient | multiplier applied to total GPU count and eligible class shares when constructing arrivals | actual flexible-pool utilisation; the legacy code field is `flexible_arrival_utilization` |
| actual flexible-pool utilisation | mean eligible GPU-hours per hour divided by flexible GPU count | arrival scaling coefficient; finite-horizon feasibility does not imply sustainable continuous operation |
| firm demand-response capacity | a power reduction that meets predeclared delivery and service-reliability criteria | nominal flexible load; an untested candidate capacity |
| job-derived firm flexibility | firm flexibility derived from job release times, GPU-hour requirements, classes and deadlines | a fixed flexible-load percentage |
| PI tolerance lower bound | a population-level nonparametric lower bound on the perfect-information planning capacity | empirical PI/NA boundary; a deployable certificate |
| empirical PI/NA boundary | the matched finite-ensemble empirical PI order statistic and restricted NA bound, which coincide in Model A | PI tolerance lower bound; evidence that NA outperforms PI |
| restricted non-anticipative (NA) bound | a finite-ensemble empirical planning bound under a predeclared information structure | an independent reliability certificate |
| distribution-specific causal certificate | independent locked-scenario test of a validation-selected, fixed causal implementation under a declared distribution; `causal certificate` may be used after first definition | PI or NA planning bound; a transferable hardware constant |
| per-call recovery guard | causal memory and electrical ceiling for every observed live event/recovery window | perfect foresight; proof of optimal recovery; guarantee of deadlines |
| selected repeated offer | largest tested request passing development, then separately tested on fresh scenarios | a full-request comparator that passes confirmation without development selection |
| request fraction | repeated request divided by the corresponding single-event offer | deferrable-work share; 75% workload eligibility |
| compute debt | additional future compute-energy obligation caused by deferring work relative to the matched no-DR baseline | backlog; rebound energy |
| state-dependent repeatability | repeated-call capability conditioned on the service state produced by prior dispatch and recovery | isolated-event success; elapsed recovery time alone |
| residual flexibility ratio | repeated-event delivery relative to a matched fresh-event counterfactual at the same scenario and clock time | absolute delivery ratio |
| joint-episode success | an episode satisfying delivery for every event and all global service constraints | mean event success |
| photovoltaic (PV) hosting capacity | maximum PV nameplate capacity satisfying the declared curtailment, PCC, storage and service constraints | data-centre hosting capacity |
| joint data-centre–PV feasible boundary | feasible combinations of data-centre and PV capacity under the declared workload, network, curtailment, storage and service constraints | a causal effect of the locked controller |
| simultaneous PV-hosting boundary | minimum scenario-wise feasible PV capacity across all declared scenarios | scenario-paired mean hosting gain |
| scenario-paired mean hosting gain | mean within-scenario flexible-minus-rigid PV-hosting contrast | difference between two ensemble minima |
| renewable planning result | perfect-information feasible-set result with zero missed GPU-hours in v0.20; historical 1% programmes remain separate | causal effect of the locked demand-response controller |
| PV utilisation | locally used PV energy divided by available PV energy | renewable demand share; grid-import reduction |
| battery energy storage system (BESS) | battery energy storage system (BESS) | generic storage |
| point of common coupling (PCC) | point of common coupling (PCC) between the community and upstream grid | data-centre power limit |
| development ensemble | scenarios used for mechanism development and design freezing | independent validation or locked evaluation |
| validation ensemble | independent scenarios used for frozen selection or replication before locked evaluation | locked-ID evaluation |
| locked-ID evaluation | one-time in-distribution replay of frozen candidates | validation selection |
| locked-OOD evaluation | one-time out-of-distribution replay without candidate reselection | an estimate that OOD capacity is zero |
| economic participation | the operator decision to offer technically certified capacity when product-specific compensation covers the declared incremental participation cost | technical feasibility alone; generic profitability |
| economically offerable capacity | certified capacity whose declared annual net value is non-negative under the stated mean or risk-adjusted rule; (K_{\mathrm{econ}}\leq K_{\mathrm{cert}}) | a new technical certificate; an uncertified fractional offer |
| parameterised economic screening | sensitivity analysis over explicitly declared economic and market coordinates using a paired physical ledger | market-calibrated profitability; an operator forecast |
| proportional reference-module accounting sensitivity | linear replication of reference-module capacity and physical ledger quantities to a declared site power for cost allocation, without portfolio diversification | a technical certificate for a 0.2–20-MW facility; hardware extrapolation |
| risk-adjusted break-even capacity payment | capacity payment for which the fifth percentile of bootstrap annual net value equals zero under the declared fresh-event sampling model | an inferential confidence bound; an observed market tariff |
| effective displaced-compute value | (v_{\mathrm{eff}}=\alpha v_{\mathrm{GPUh}}), combining the exposed fraction and declared GPU-hour value exactly once | cloud list price; operator contribution margin; a second SLA penalty |
| fixed site-enablement cost | annual site-wide participation coordinate applied once whenever offered capacity is positive | a per-kW charge; sourced AI-data-centre operating expenditure |
| recovery-throughput-equivalent GPU count | event-end paired backlog debt divided by declared recovery hours and execution efficiency, optionally rounded to nodes | required or reserved GPUs; a purchase recommendation; H100/H200 extrapolation |
| trace-informed workload model | workload arrivals sampled from Alibaba 2026-derived job characteristics without replaying production timestamps, deadlines or full temporal correlations | trace-calibrated production replay; full-distribution equivalence |
| AIDRBench | the reproducible research environment implementing scenario freezing, state transitions and evaluation | the headline scientific contribution |

## v0.18 reporting clarification

- `compute_debt_kwh` in legacy raw state denotes total controlled queued dynamic energy. Excess compute debt explicitly subtracts the matched no-response queue energy; repeated-minus-fresh comparisons cancel that common baseline.
- Offer fraction in the repeated-capacity study is relative to the original certified kW offer. It is distinct from deferrable-work share and flexible GPU allocation.
- A qualified selected repeated offer is a tested grid point, not a continuous maximum or a necessary derating.
- Production-timing stress maps observed arrival counts onto synthetic jobs/deadlines; it is not measured production-service replay.
- A complete four-call series retains its queue history; annualisation assumes independent series and does not simulate a continuous year.

## v0.19 reader-facing distinctions

- Deferrable-work share describes permission to postpone work; flexible GPU allocation describes hardware assigned to process that work. Neither is an always-available power fraction.
- The PI tolerance bound describes full-information planning with sampling uncertainty; the empirical PI/NA result uses a specified sample failure allowance. Neither is itself a causal-controller certificate.
- Capacity-payment units use offered kW; proportional facility MW is a different accounting quantity.
- A comparison of two tested programmes does not isolate the causal effect of recovery gap when their selected offers and trajectories also differ.

## v0.20 statistical and workload scope

- Primary low shares are 5%, 10% and 20% of total offered GPU-hours. The 40% all-batch permission and 60% changed-composition comparisons are additional assumptions, not observed deferral permissions.
- GPU allocation matches eligibility in the primary policy; 10% eligibility controls isolate allocation and unmeasured rigid-power effects.
- Confirmation uses 300 previously unexamined seeds after development-based correction and selection. The economic `qualified` flag refers only to its pointwise confirmation Wilson criterion.
- All original four-hour repeated offers passed confirmation. None of the repeat-grid candidates passed the separate development selection rule. Report those outcomes separately; never reinterpret no selection as measured zero capacity.
- Full hourly exports preserve raw `compute_debt_kwh` and explicitly baseline-subtracted `excess_queue_energy_kwh` as different fields.


## v0.23 additions

| Term | Current meaning | Do not substitute |
|---|---|---|
| offered utilisation | offered GPU-hours / installed GPU-hour capacity; 50%, 65%, 80% scenario inputs | measured production GPU utilisation |
| zero deadline loss | ≤1e−7 GPU-h total missed eligible work, paired baseline also zero | measured quality guarantee or zero terminal-backlog requirement |
| start spacing P | time between successive event starts; H8P16 has an 8-h gap | gap G in historical H8G12 |
| matched target electrical outcome | final call alone versus final call after three previous calls at exactly the same clock | full-programme success or global task-service success |
| production timing transfer | eight observed submission-count weeks mapped to synthetic work/deadlines | actual production task or checkpoint/restart replay |
| shared access fee | fixed charge divided among five/ten resources without diversified risk | aggregate reliability certificate |
| net operating cost | ledger energy + waiting + stated loss exposure − capped delivery revenue, before site fee | actual profit, measured GPU ageing or market-calibrated cost |
