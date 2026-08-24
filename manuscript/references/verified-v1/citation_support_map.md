# Claim-to-source support map

This table records the first-pass literature support used in manuscript v0.2.
`Publisher/official abstract` means that the claim was checked against the
publisher page, official proceedings page or official technical-report record,
not inferred from title metadata alone.

| Manuscript claim | References | Verification | Scope boundary |
|---|---:|---|---|
| AI data-centre growth creates grid-planning and connection challenges | 1 | Author-hosted publication abstract | Used as sector context, not as a forecast adopted by Model A |
| A 256-GPU deployment sustained 25% power reduction for 3 h with tested QoS | 2 | Nature Energy publisher abstract | A deployment demonstration, not a universal firm-capacity value |
| Job scheduling, power capping and local generation can provide data-centre DR | 3–7, 13, 18, 19 | Publisher or institutional abstracts | Establishes feasibility and prior control formulations |
| Computing can be shifted temporally or spatially for carbon and renewable objectives | 8–12, 17 | Publisher or author abstracts | Does not by itself certify demand-response capacity |
| Recent work connects trace-derived or geo-distributed computing flexibility to DR and interconnection planning | 14–16 | Publisher or institutional abstracts | Closest comparator set; objectives and qualification layers differ |
| Demand response can increase renewable integration or PV hosting | 20–22 | Nature Portfolio publisher abstracts | Prior system models use different networks and resource abstractions |
| BESS provides time-coupled grid flexibility | 23 | Nature Energy publisher abstract | Supports the storage comparison, not the measured interaction sign |
| Coordinated demand-side resources can affect community/city energy-system outcomes | 24 | Nature Communications publisher record and accepted manuscript | Used as structural precedent for the system-consequence layer |
| Inter-temporal DR and recovery affect capacity credit | 25, 26 | Publisher abstract and full abstract | Supports reliability qualification; not the numerical AIDRBench certificate |
| EULP profiles are modelled building-stock loads calibrated and validated against empirical data | 27, 28 | Official NLR/NREL reports | Profiles are not project-owned feeder measurements |
| Alibaba traces contain heterogeneous production AI workloads at large cluster scale | 29, 30 | Official USENIX proceedings pages | AIDRBench samples trace-calibrated arrivals; it does not replay production deadlines |
| Nonparametric tolerance bounds and Wilson intervals support finite-sample reliability statements | 31–33 | Publisher or official journal records | Statistical-method support only |
| HiGHS solves the declared linear and mixed-integer programmes | 34 | Official solver citation page and journal metadata | Software-method attribution |

The numerical AIDRBench findings are supported by repository Source Data and
result receipts, not by these external references.
