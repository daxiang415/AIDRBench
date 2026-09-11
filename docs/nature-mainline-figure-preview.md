# 当前 v0.25：Figure

采用当前正文图注；六主图、五补充图。全部数据和重绘入口见完整 v14 包。

### Figure 1 | Workload composition and declared permission to defer

**a,** Requested GPU-hour shares from all 40,522,321 released execution spans, using uncapped duration. The denominator includes online inference, offline inference, training, development, other and unknown work. These are descriptive source totals, not energy shares or an industry estimate. **b,** Training and offline-inference contributions to each eligibility scenario. At 5–20%, a common fraction of low-priority batch work is permitted to wait. The 40% case assumes nearly all batch work opts in; the 60% case replaces 19.058 percentage points of online work with offline work before granting eligibility. Online jobs are never deferred. Source Data retain class-by-priority totals and full-precision scenario definitions.

![Figure 1](figures/commitment_narrative_v1/artwork/AIDRBench_Figure_1.png)

### Figure 2 | Relaxed planning statistics and independently tested single offers

**a,** Relaxed PI tolerance statistics from 100 confirmation scenarios (95% reliability, at least 95% confidence; horizontal marks) and development-selected controller offers (circles; crosses would denote failure to qualify). The two statistics use different constructions and their relative ordering does not imply an information advantage. **b,** Success fractions at the same request under 0-, 2- and 6-h notice, with one-sided 95% Wilson lower limits and 300 independent seeds per condition. Dashed line, 95% qualification threshold. Blue and green identify four- and eight-hour events; shapes distinguish notice. Complete paired outcomes and Holm-adjusted exact McNemar tests are provided. In all ratio plots, * denotes nearly all-batch opt-in at 40%, and † denotes changed business composition at 60%. The retained PI values use aggregate release/deadline relaxations; they are not guaranteed work-group-feasible capacities (Methods).

![Figure 2](figures/commitment_narrative_v1/artwork/AIDRBench_Figure_2.png)

### Figure 3 | Separate qualification, feasibility and workload transfer

**a,** Independently confirmed offers at 10% eligibility, 65% offered utilisation, reference deadlines, 10% GPU allocation and four calls at 16-h start spacing. Points and lower whiskers are success fractions and one-sided 95% Wilson lower bounds (300 scenarios); capacity labels apply to both service standards. Zero missed work defines a successful series under the zero-miss criterion; qualification targets a 95% success probability. **b,** Zero-miss diagnoses at 5.90 kW for three prespecified seeds per configuration. Categories separate instantaneous shortage, other strict-window infeasibility, PI feasibility with causal failure and feasibility with causal success; these are mechanism cases, not population frequencies. **c,** Matched submission-count and task-resource-time tests at 2.95 kW in chronological and permuted hourly order, scored at both service standards. GPU-h labels denote task-resource-time weights. **d,** Chronological zero-miss success by observed week for both weights. Panels c,d include eight observed weeks and ten synthetic realisations per week; pooled counts are descriptive and have no binomial confidence bars. Each comparison preserves weekly class totals and uses matched service rules, community and event clocks. Permutation changes hourly order and alignment together. All no-response baselines pass zero-miss service; all 49 chronological resource-time failures encounter instantaneous shortage.

![Figure 3](figures/commitment_narrative_v1/artwork/AIDRBench_Figure_3.png)

### Figure 4 | Supply margins and the decisions behind a commitment

**a,** Paired minimum event-hour supply margins for all 80 task-resource-time realisations at 2.95 kW, comparing chronological and permuted orders. Margin is baseline PCC power minus community and fixed data-centre power minus 95% of the request, minimised over all four calls. Dashed zero lines separate scenarios with and without an instantaneous shortage; counts are descriptive, with no population-frequency inference. **b,** Available baseline reduction under chronological count and resource-time weighting for the lowest protocol seed (990000). The horizontal line is the 95% delivery requirement and shading marks the four calls. The displayed arrival horizon is 168 h; all 216 h remain in the data. Selection is by seed, not outcome. **c,** Evidence-to-decision sequence. A deficit identifies an impossible series, not automatic rejection of a probabilistic contract. Strict-window PI diagnoses distinguish infeasibility from a causal-control gap; an unresolved solve supplies no feasibility conclusion. Only a fixed causal offer that passes independent qualification enters the operating-price comparison. No supply screen or PI witness alone certifies causal reliability.

![Figure 4](figures/commitment_narrative_v1/artwork/AIDRBench_Figure_4.png)

### Figure 5 | Separate controls for GPU allocation and rigid-load power

**a,b,** Four- and eight-hour relaxed-PI tolerance statistics across flexible GPU allocations or unmeasured rigid-class active-power proxies, retaining 10% eligibility, the same 576-GPU installation and paired jobs. Each statistic uses 100 confirmation scenarios and aggregate release/deadline constraints; it does not guarantee work-group-feasible capacity. Lines join evaluated settings. **c,d,** Conditional four-hour single-event participation costs at the unchanged primary offer, using all 300 confirmation ledgers, 50 independent calls per annual draw and proportional 1-MW accounting. Crosses would indicate an unqualified offer. Costs are 95th-percentile annual-net-cost thresholds, not confidence limits. Fixed-request success and PV allocation controls appear in Supplementary Fig. 4c,d. Rigid power proxies are not measurements of online inference.

![Figure 5](figures/commitment_narrative_v1/artwork/AIDRBench_Figure_5.png)

### Figure 6 | Price the operating exposure of qualified commitments

**a,** Additional waiting exposure per complete four-call series for the refined four- and eight-hour products (300 confirmation scenarios each); points are means and whiskers are scenario 5th–95th percentiles, not confidence intervals. **b,** Net operating cost components at the total annual 95th-percentile rank, with no site fee and US$0.005/GPU-h/h waiting. **c,** Participation thresholds as waiting price varies. **d,** Minimum eight-hour capacity price that matches both the four-hour product and opting out, at three waiting prices. All panels use products qualified at a 95% success-probability target with zero missed work required for success: 5.60 and 4.42 model kW, reference deadlines and 16-h start spacing. Failed series remain in the ledgers. Monetary panels use proportional 1-MW accounting, twelve independent four-call series per year, US$0.10/kWh electricity, US$50/MWh capped delivered-energy revenue, zero missed-work price and 2,000 annual draws including failures. Price curves are conditional on the reference workload; they are not transferable offers for the failed resource-time tests.

![Figure 6](figures/commitment_narrative_v1/artwork/AIDRBench_Figure_6.png)
