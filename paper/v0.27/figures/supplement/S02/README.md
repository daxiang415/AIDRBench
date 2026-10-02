# Figure S2 · Power calibration

GPU-board power measurements, fitted relationships and held-out validation.

[Reference PDF](AIDRBench_Supplementary_Figure_2.pdf) · [Preview](AIDRBench_Supplementary_Figure_2.png) · [Editable SVG](AIDRBench_Supplementary_Figure_2.svg) · [Plotting workbook](S02_READY.xlsx)

To redraw this figure, run `python redraw.py` from this directory, or `python tools/aidr.py redraw --figures S2` from the repository root. Install the [plotting dependencies](../../../../../docs/getting-started.md) first. Output is written to the supplementary pack's `MY_REDRAW/` directory, not over the reference files.

Retain the measurement units and the distinction between fitting and held-out validation.

The renderer reads the local CSV files, not the workbook. Use [series assignments](../PLOT_ASSIGNMENTS.csv) for X/Y and interval columns and [English captions](../FIGURE_LEGENDS_EN.md) for definitions and comparison conditions. The [editing guide](../README.md) explains data formats and how to insert an approved figure into the paper.
