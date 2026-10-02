# Figure S7 · PV and storage

PV hosting, curtailment and grid purchases for rigid and flexible scheduling, with and without storage.

[Reference PDF](AIDRBench_Supplementary_Figure_7.pdf) · [Preview](AIDRBench_Supplementary_Figure_7.png) · [Editable SVG](AIDRBench_Supplementary_Figure_7.svg) · [Plotting workbook](S07_READY.xlsx)

To redraw this figure, run `python redraw.py` from this directory, or `python tools/aidr.py redraw --figures S7` from the repository root. Install the [plotting dependencies](../../../../../docs/getting-started.md) first. Output is written to the supplementary pack's `MY_REDRAW/` directory, not over the reference files.

Retain the with-storage and without-storage comparisons and their original units.

The renderer reads the local CSV files, not the workbook. Use [series assignments](../PLOT_ASSIGNMENTS.csv) for X/Y and interval columns and [English captions](../FIGURE_LEGENDS_EN.md) for definitions and comparison conditions. The [editing guide](../README.md) explains data formats and how to insert an approved figure into the paper.
