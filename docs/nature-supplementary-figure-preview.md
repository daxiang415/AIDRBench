# 当前 v0.25：Supplementary Figure

采用当前正文图注；六主图、五补充图。全部数据和重绘入口见完整 v14 包。

### Supplementary Figure 1 | Study inputs and evidence flow

![Supplementary Figure 1](../docs/figures/commitment_narrative_v1/artwork/AIDRBench_Supplementary_Figure_1.png)

**a,** Source composition and declared permission define a paired job template, hardware allocation and hourly deadline queues in the community PCC model. **b,** Development selects requests before independent confirmation; complete trajectories supply the cost ledger. PV and BESS optimisation is a separate full-information branch. Arrows describe model inputs and analysis dependencies, not estimated causal effects.

![Supplementary Figure 1](figures/commitment_narrative_v1/artwork/AIDRBench_Supplementary_Figure_1.png)

### Supplementary Figure 2 | Four-GPU board-power calibration

![Supplementary Figure 2](../docs/figures/commitment_narrative_v1/artwork/AIDRBench_Supplementary_Figure_2.png)

**a,** All 30 per-board run averages from one- and four-GPU training and offline inference. Filled points are fitting runs 1–2; open points are held-out run 3. Boards in one run are not independent replicates. **b,** Active-power estimates and 95% Student-t intervals from two independent four-GPU run means per class. Held-out overall MAE is 3.80 W/GPU. Node overhead and online-serving power were not measured by this calibration.

![Supplementary Figure 2](figures/commitment_narrative_v1/artwork/AIDRBench_Supplementary_Figure_2.png)

### Supplementary Figure 3 | Candidate resolution and structural context

![Supplementary Figure 3](../docs/figures/commitment_narrative_v1/artwork/AIDRBench_Supplementary_Figure_3.png)

**a,b,** Development one-sided 95% Wilson lower bounds for every four- and eight-hour local candidate (100 scenarios each, both service standards). The dashed line is the selection threshold of 0.95; the selected eight-hour grid ceiling is not a bracketed maximum. **c,** Full-request structural controls show instantaneous shortages and >1% deadline failures as potentially overlapping categories (300 scenarios). **d,** Chronological submission-count cross-scoring from the 986000-series study: stacked segments show successes and immediate shortages at 4.42 kW, and markers show 2.95-kW successes. Both service scores coincide at each request. Eight observed weeks have ten synthetic realisations each; counts are descriptive. Historical design interpretation is in Note 7; matched last-call outcomes, all of which coincide, remain in Table 15 and Source Data.

![Supplementary Figure 3](figures/commitment_narrative_v1/artwork/AIDRBench_Supplementary_Figure_3.png)

### Supplementary Figure 4 | PV benefits and fixed-request controls

![Supplementary Figure 4](../docs/figures/commitment_narrative_v1/artwork/AIDRBench_Supplementary_Figure_4.png)

**a,** Flexible minus rigid all-scenario PV hosting capacity across the five eligibility scenarios, with and without BESS; each capacity is the minimum over 100 scenarios. **b,** Paired gain in utilisation of a fixed 500-kW PV system; points are means and whiskers are 95% paired bootstrap intervals. The intervals cover sampling, not optimisation error; small storage contrasts remain unresolved at solver precision. **c,** Four- and eight-hour success at unchanged primary single-event requests across allocation and rigid-power controls, with one-sided 95% Wilson lower bounds from 300 scenarios. **d,** Corresponding gains in all-scenario PV hosting over 100 paired scenarios. Panels c,d retain 10% eligibility and vary only GPU allocation or the stated rigid-power proxy. PV schedules use full information and zero missed work; hosting differences are differences of minima, not mean effects or confidence intervals.

![Supplementary Figure 4](figures/commitment_narrative_v1/artwork/AIDRBench_Supplementary_Figure_4.png)

### Supplementary Figure 5 | Waiting valuation and access fees change product choice

![Supplementary Figure 5](../docs/figures/commitment_narrative_v1/artwork/AIDRBench_Supplementary_Figure_5.png)

**a,** Difference between product-specific fifth-percentile annual net values, eight minus four hours, at equal capacity prices with zero waiting price and zero access fee; zero marks indifference between participating products. **b,** Refined zero-loss product thresholds with zero or US$1/GPU-h missed-work valuation at reference waiting price and zero fee. The zero-loss qualification permits occasional failed scenarios, whose ledgers remain priced. **c,** Fifth-percentile annual net values at US$250 per kW-year, reference waiting price and zero, shared or full access fees. **d,** Eight-hour price required to match both four-hour participation and opting out at those access fees. All products use the new 300-seed confirmation ledgers, 10% eligibility, 65% offered utilisation, reference deadlines and 16-h start spacing. Annual accounting and energy prices match Fig. 6; fees are common across duration products and do not imply reliability pooling.

![Supplementary Figure 5](figures/commitment_narrative_v1/artwork/AIDRBench_Supplementary_Figure_5.png)
