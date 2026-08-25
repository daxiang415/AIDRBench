# AIDRBench manuscript terminology ledger

This ledger is normative for the Nature Communications manuscript. English prose uses British spelling (`data centre`, `utilisation`, `optimisation`), while code identifiers retain their repository spelling.

| Canonical term | First-use definition | Avoid or distinguish from |
|---|---|---|
| AI data centre | artificial-intelligence (AI) data centre | `datacenter`; a four-GPU workstation is only the measurement anchor |
| demand response (DR) | demand response (DR) | generic load shifting without a grid request |
| nominal flexibility | a fixed fraction of operating peak assumed to be flexible | firm flexibility |
| firm demand-response capacity | a power reduction that meets predeclared delivery and service-reliability criteria | nominal flexible load; an untested candidate capacity |
| job-derived firm flexibility | firm flexibility derived from job release times, GPU-hour requirements, classes and deadlines | a fixed flexible-load percentage |
| perfect-information (PI) boundary | a planning upper bound with full future information | a deployable or causal certificate |
| restricted non-anticipative (NA) bound | a scenario-based planning bound under a predeclared information structure | an independent reliability certificate |
| causal certificate | independent locked-scenario test of a validation-selected, fixed causal implementation | PI or NA planning bound |
| compute debt | additional future compute-energy obligation caused by deferring work relative to the matched no-DR baseline | backlog; rebound energy |
| residual flexibility ratio | repeated-event delivery relative to a matched fresh-event counterfactual at the same scenario and clock time | absolute delivery ratio |
| joint-episode success | an episode satisfying delivery for every event and all global service constraints | mean event success |
| photovoltaic (PV) hosting capacity | maximum PV nameplate capacity satisfying the declared curtailment, PCC, storage and service constraints | data-centre hosting capacity |
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
| AIDRBench | the reproducible research environment implementing scenario freezing, state transitions and evaluation | the headline scientific contribution |
