# Figure S4 · Flexibility assumptions

PV outcomes and fixed-request delivery under changed workload and power assumptions.

[Reference PDF](AIDRBench_Supplementary_Figure_4.pdf) · [Preview](AIDRBench_Supplementary_Figure_4.png) · [Editable SVG](AIDRBench_Supplementary_Figure_4.svg) · [Plotting workbook](S04_READY.xlsx)

To redraw this figure, run `python redraw.py` from this directory, or `python tools/aidr.py redraw --figures S4` from the repository root. Install the [plotting dependencies](../../../../../docs/getting-started.md) first. Output is written to the supplementary pack's `MY_REDRAW/` directory, not over the reference files.

Keep the workload-share, GPU-allocation and rigid-power scenarios distinct.

The renderer reads the local CSV files, not the workbook. Use [series assignments](../PLOT_ASSIGNMENTS.csv) for X/Y and interval columns and [English captions](../FIGURE_LEGENDS_EN.md) for definitions and comparison conditions. The [editing guide](../README.md) explains data formats and how to insert an approved figure into the paper.
