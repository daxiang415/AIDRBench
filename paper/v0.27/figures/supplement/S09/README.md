# Figure S9 · Observed-week qualification

Offer selection and independent delivery qualification across the reference workload and observed weeks.

[Reference PDF](AIDRBench_Supplementary_Figure_9.pdf) · [Preview](AIDRBench_Supplementary_Figure_9.png) · [Editable SVG](AIDRBench_Supplementary_Figure_9.svg) · [Plotting workbook](S09_READY.xlsx)

To redraw this figure, run `python redraw.py` from this directory, or `python tools/aidr.py redraw --figures S9` from the repository root. Install the [plotting dependencies](../../../../../docs/getting-started.md) first. Output is written to the supplementary pack's `MY_REDRAW/` directory, not over the reference files.

Keep development selection separate from independent confirmation; preserve the reported confidence-bound definitions.

The renderer reads the local CSV files, not the workbook. Use [series assignments](../PLOT_ASSIGNMENTS.csv) for X/Y and interval columns and [English captions](../FIGURE_LEGENDS_EN.md) for definitions and comparison conditions. The [editing guide](../README.md) explains data formats and how to insert an approved figure into the paper.
