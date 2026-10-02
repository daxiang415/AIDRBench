# Figure S8 · Economic assumptions

Participation thresholds under hardware-lifetime, workload-value, waiting-cost and site-cost assumptions.

[Reference PDF](AIDRBench_Supplementary_Figure_8.pdf) · [Preview](AIDRBench_Supplementary_Figure_8.png) · [Editable SVG](AIDRBench_Supplementary_Figure_8.svg) · [Plotting workbook](S08_READY.xlsx)

To redraw this figure, run `python redraw.py` from this directory, or `python tools/aidr.py redraw --figures S8` from the repository root. Install the [plotting dependencies](../../../../../docs/getting-started.md) first. Output is written to the supplementary pack's `MY_REDRAW/` directory, not over the reference files.

Hardware lifetime is an economic assumption about reserved capacity, not a measurement of GPU wear caused by demand response.

The renderer reads the local CSV files, not the workbook. Use [series assignments](../PLOT_ASSIGNMENTS.csv) for X/Y and interval columns and [English captions](../FIGURE_LEGENDS_EN.md) for definitions and comparison conditions. The [editing guide](../README.md) explains data formats and how to insert an approved figure into the paper.
