# Figure S1 · Analysis workflow

Workload and power evidence entering response qualification, PV analysis and cost accounting.

[Reference PDF](AIDRBench_Supplementary_Figure_1.pdf) · [Preview](AIDRBench_Supplementary_Figure_1.png) · [Editable SVG](AIDRBench_Supplementary_Figure_1.svg) · [Plotting workbook](S01_READY.xlsx)

To redraw this figure, run `python redraw.py` from this directory, or `python tools/aidr.py redraw --figures S1` from the repository root. Install the [plotting dependencies](../../../../../docs/getting-started.md) first. Output is written to the supplementary pack's `MY_REDRAW/` directory, not over the reference files.

This is a conceptual diagram. Its CSV coordinates position labels; they are not experimental measurements.

The renderer reads the local CSV files, not the workbook. Use [series assignments](../PLOT_ASSIGNMENTS.csv) for X/Y and interval columns and [English captions](../FIGURE_LEGENDS_EN.md) for definitions and comparison conditions. The [editing guide](../README.md) explains data formats and how to insert an approved figure into the paper.
