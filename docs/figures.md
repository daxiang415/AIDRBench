# Figures and source tables

Main figures for manuscript **v0.27**, artwork revision **R8**. The [paper](../paper/v0.27/latex/main.pdf) and [supplementary information](../paper/v0.27/latex/supplement.pdf) give the full captions, units, sample definitions and assumptions.

## Figure 1 · Study overview

Workload composition, power modelling and response qualification.

[![Study overview](../paper/v0.27/figures/main/01_FIGURES/AIDRBench_Figure_1.png)](../paper/v0.27/figures/main/01_FIGURES/AIDRBench_Figure_1.png)

[PDF](../paper/v0.27/figures/main/01_FIGURES/AIDRBench_Figure_1.pdf) · [Panel data](../paper/v0.27/figures/main/02_PANEL_DATA/F01/)

## Figure 2 · Flexibility assumptions

Response offers and delivery under the tested workload assumptions.

[![Flexibility assumptions](../paper/v0.27/figures/main/01_FIGURES/AIDRBench_Figure_2.png)](../paper/v0.27/figures/main/01_FIGURES/AIDRBench_Figure_2.png)

[PDF](../paper/v0.27/figures/main/01_FIGURES/AIDRBench_Figure_2.pdf) · [Panel data](../paper/v0.27/figures/main/02_PANEL_DATA/F02/)

## Figure 3 · Workload representation and qualification

Effects of workload representation and timing on response offers, confirmation and failure modes.

[![Workload representation and qualification](../paper/v0.27/figures/main/01_FIGURES/AIDRBench_Figure_3.png)](../paper/v0.27/figures/main/01_FIGURES/AIDRBench_Figure_3.png)

[PDF](../paper/v0.27/figures/main/01_FIGURES/AIDRBench_Figure_3.pdf) · [Panel data](../paper/v0.27/figures/main/02_PANEL_DATA/F03/)

## Figure 4 · Event and recovery

Paired outcomes and hourly trajectories across response and recovery windows.

[![Event and recovery](../paper/v0.27/figures/main/01_FIGURES/AIDRBench_Figure_4.png)](../paper/v0.27/figures/main/01_FIGURES/AIDRBench_Figure_4.png)

[PDF](../paper/v0.27/figures/main/01_FIGURES/AIDRBench_Figure_4.pdf) · [Panel data](../paper/v0.27/figures/main/02_PANEL_DATA/F04/)

## Figure 5 · Cost components

Cost assumptions and components associated with response participation.

[![Cost components](../paper/v0.27/figures/main/01_FIGURES/AIDRBench_Figure_5.png)](../paper/v0.27/figures/main/01_FIGURES/AIDRBench_Figure_5.png)

[PDF](../paper/v0.27/figures/main/01_FIGURES/AIDRBench_Figure_5.pdf) · [Panel data](../paper/v0.27/figures/main/02_PANEL_DATA/F05/)

## Figure 6 · Participation thresholds

Waiting distributions, compensation thresholds and response-product choices.

[![Participation thresholds](../paper/v0.27/figures/main/01_FIGURES/AIDRBench_Figure_6.png)](../paper/v0.27/figures/main/01_FIGURES/AIDRBench_Figure_6.png)

[PDF](../paper/v0.27/figures/main/01_FIGURES/AIDRBench_Figure_6.pdf) · [Panel data](../paper/v0.27/figures/main/02_PANEL_DATA/F06/)

## Supplementary figures

[S1–S10 and their source tables](../paper/v0.27/figures/supplement/README.md) · [Full captions](../paper/v0.27/figures/supplement/FIGURE_LEGENDS_EN.md)

## Reproduction

After [installation](getting-started.md), run from the repository root:

```bash
python tools/aidr.py main-figures
python tools/aidr.py redraw
```

The [main figure guide](../paper/v0.27/figures/main/README.md) describes panel generation and optional PDF export. The supplementary renderer uses the supplied CSV values and writes a separate set of figures; the reference artwork remains unchanged.
