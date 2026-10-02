# Figure S3 · Repeated-response qualification

Offer screening, supply and deadline failures, and comparisons across week sequences.

[Reference PDF](AIDRBench_Supplementary_Figure_3.pdf) · [Preview](AIDRBench_Supplementary_Figure_3.png) · [Editable SVG](AIDRBench_Supplementary_Figure_3.svg) · [Plotting workbook](S03_READY.xlsx)

To redraw this figure, run `python redraw.py` from this directory, or `python tools/aidr.py redraw --figures S3` from the repository root. Install the [plotting dependencies](../../../../../docs/getting-started.md) first. Output is written to the supplementary pack's `MY_REDRAW/` directory, not over the reference files.

Preserve the tested offer grid and the reported qualification outcomes; do not smooth discrete test points.

The renderer reads the local CSV files, not the workbook. Use [series assignments](../PLOT_ASSIGNMENTS.csv) for X/Y and interval columns and [English captions](../FIGURE_LEGENDS_EN.md) for definitions and comparison conditions. The [editing guide](../README.md) explains data formats and how to insert an approved figure into the paper.
