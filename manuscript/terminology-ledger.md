# AIDRBench manuscript terminology ledger

This ledger is normative for the Nature Communications manuscript. English prose uses British spelling (`data centre`, `utilisation`, `optimisation`), while code identifiers retain their repository spelling.

| Canonical term | First-use definition | Avoid or distinguish from |
|---|---|---|
| AI data centre | artificial-intelligence (AI) data centre | `datacenter`; a four-GPU workstation is only the measurement anchor |
| demand response (DR) | demand response (DR) | generic load shifting without a grid request |
| firm DR qualification | derivation and independent testing of a service-feasible power commitment for declared duration, reliability and scenario distribution | benchmark performance; proof that load is merely adjustable |
| nominal flexibility | a fixed fraction of operating peak assumed to be flexible | firm flexibility |
| firm demand-response capacity | a power reduction that meets predeclared delivery and service-reliability criteria | nominal flexible load; an untested candidate capacity |
| job-derived firm flexibility | firm flexibility derived from job release times, GPU-hour requirements, classes and deadlines | a fixed flexible-load percentage |
| PI tolerance lower bound | a population-level nonparametric lower bound on the perfect-information planning capacity | empirical PI/NA boundary; a deployable certificate |
| empirical PI/NA boundary | the matched finite-ensemble empirical PI order statistic and restricted NA bound, which coincide in Model A | PI tolerance lower bound; evidence that NA outperforms PI |
| restricted non-anticipative (NA) bound | a finite-ensemble empirical planning bound under a predeclared information structure | an independent reliability certificate |
| distribution-specific causal certificate | independent locked-scenario test of a validation-selected, fixed causal implementation under a declared distribution; `causal certificate` may be used after first definition | PI or NA planning bound; a transferable hardware constant |
| compute debt | additional future compute-energy obligation caused by deferring work relative to the matched no-DR baseline | backlog; rebound energy |
| state-dependent repeatability | repeated-call capability conditioned on the service state produced by prior dispatch and recovery | isolated-event success; elapsed recovery time alone |
| residual flexibility ratio | repeated-event delivery relative to a matched fresh-event counterfactual at the same scenario and clock time | absolute delivery ratio |
| joint-episode success | an episode satisfying delivery for every event and all global service constraints | mean event success |
| photovoltaic (PV) hosting capacity | maximum PV nameplate capacity satisfying the declared curtailment, PCC, storage and service constraints | data-centre hosting capacity |
| joint data-centre–PV feasible boundary | feasible combinations of data-centre and PV capacity under the declared workload, network, curtailment, storage and service constraints | a causal effect of the locked controller |
| simultaneous PV-hosting boundary | minimum scenario-wise feasible PV capacity across all declared scenarios | scenario-paired mean hosting gain |
| scenario-paired mean hosting gain | mean within-scenario flexible-minus-rigid PV-hosting contrast | difference between two ensemble minima |
| renewable planning result | perfect-information feasible-set result under the headline 1% missed-GPU-hour allowance, qualified by a zero-miss sensitivity | causal effect of the locked demand-response controller |
| PV utilisation | locally used PV energy divided by available PV energy | renewable demand share; grid-import reduction |
| battery energy storage system (BESS) | battery energy storage system (BESS) | generic storage |
| point of common coupling (PCC) | point of common coupling (PCC) between the community and upstream grid | data-centre power limit |
| development ensemble | scenarios used for mechanism development and design freezing | independent validation or locked evaluation |
| validation ensemble | independent scenarios used for frozen selection or replication before locked evaluation | locked-ID evaluation |
| locked-ID evaluation | one-time in-distribution replay of frozen candidates | validation selection |
| locked-OOD evaluation | one-time out-of-distribution replay without candidate reselection | an estimate that OOD capacity is zero |
| trace-informed workload model | workload arrivals sampled from Alibaba 2026-derived job characteristics without replaying production timestamps, deadlines or full temporal correlations | trace-calibrated production replay; full-distribution equivalence |
| AIDRBench | the reproducible research environment implementing scenario freezing, state transitions and evaluation | the headline scientific contribution |
