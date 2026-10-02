# Figure S6 · Operating-condition sensitivity

Delivery and deadline outcomes under changed utilisation, deadlines, GPU allocation and event schedules.

[Reference PDF](AIDRBench_Supplementary_Figure_6.pdf) · [Preview](AIDRBench_Supplementary_Figure_6.png) · [Editable SVG](AIDRBench_Supplementary_Figure_6.svg) · [Plotting workbook](S06_READY.xlsx)

To redraw this figure, run `python redraw.py` from this directory, or `python tools/aidr.py redraw --figures S6` from the repository root. Install the [plotting dependencies](../../../../../docs/getting-started.md) first. Output is written to the supplementary pack's `MY_REDRAW/` directory, not over the reference files.

The four outcome matrices contain separate counts out of 300. Do not add the matrices together.

The renderer reads the local CSV files, not the workbook. Use [series assignments](../PLOT_ASSIGNMENTS.csv) for X/Y and interval columns and [English captions](../FIGURE_LEGENDS_EN.md) for definitions and comparison conditions. The [editing guide](../README.md) explains data formats and how to insert an approved figure into the paper.
