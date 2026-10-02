# Supplementary figures: S1–S10

Reference artwork and direct plotting data for the v0.27 supplement. Redrawing these figures needs Python and plotting dependencies, not the original simulation inputs or a GPU.

## Redraw from the repository root

```bash
python tools/aidr.py redraw --figures S5
python tools/aidr.py redraw --figures S3 S9 --tiff
```

Omit `--figures` to redraw all ten. The output goes to `MY_REDRAW/` in this directory, leaving the reference files untouched. The original entry point also works: `python DRAW_SUPPLEMENT.py --figures S5` from this directory.

The plotter reads the CSV files in `S01/`–`S10/`. Excel workbooks contain the same plotting values but are not read by the script. Export a changed worksheet to its corresponding CSV to use an intentional data change. For visual edits, keep the data unchanged.

## Find the right figure

| Figure | Subject | Direct plotting workbook |
| --- | --- | --- |
| S1 | Workload and power evidence entering the analysis | [S01_READY.xlsx](S01/S01_READY.xlsx) |
| S2 | GPU-board power calibration and held-out validation | [S02_READY.xlsx](S02/S02_READY.xlsx) |
| S3 | Repeated-response offer screening and failure modes | [S03_READY.xlsx](S03/S03_READY.xlsx) |
| S4 | Flexibility assumptions, PV outcomes and fixed-request delivery | [S04_READY.xlsx](S04/S04_READY.xlsx) |
| S5 | Waiting costs, missed deadlines and access fees | [S05_READY.xlsx](S05/S05_READY.xlsx) |
| S6 | Delivery and deadline outcomes under changed operating conditions | [S06_READY.xlsx](S06/S06_READY.xlsx) |
| S7 | PV hosting, curtailment and grid purchases with and without storage | [S07_READY.xlsx](S07/S07_READY.xlsx) |
| S8 | Hardware lifetime and cost assumptions in participation thresholds | [S08_READY.xlsx](S08/S08_READY.xlsx) |
| S9 | Offer selection and independent qualification across observed weeks | [S09_READY.xlsx](S09/S09_READY.xlsx) |
| S10 | Peak-power decomposition, node overhead and solver checks | [S10_READY.xlsx](S10/S10_READY.xlsx) |

[All reference figures](ALL_FIGURES.pdf) · [Combined workbook](ALL_PANEL_DATA.xlsx) · [English captions](FIGURE_LEGENDS_EN.md) · [Series assignments](PLOT_ASSIGNMENTS.csv)

## Read the data correctly

`PLOT_ASSIGNMENTS.csv` identifies each series' X/Y columns, interval bounds, stack bases or heatmap columns. The data are already selected and converted for plotting; do not recompute means, confidence intervals, percentages or annualised costs for a style-only edit.

`pct` means percent, `pp` means percentage points, and `fraction` is on a 0–1 scale. Do not multiply an already converted percentage by 100. `error_minus` and `error_plus` are error-bar lengths; `lower` and `upper` are interval endpoints. A one-sided lower bound has no upper error.

S1 is a conceptual diagram, not a measurement plot. S6's four matrices are separate outcome counts, not quantities to add together. S8's hardware lifetime is an economic assumption about reserved hardware headroom, not a measurement of wear caused by demand response.

## Reference artwork and verification

Reference PDFs are the figures used by the supplement. The CSV renderer provides a same-data redraw template; matching the original layout pixel for pixel is not its purpose. Edit the reference SVG directly when preserving its layout matters.

The existing `audit/` reports record the earlier coordinate and series checks. The maintained `VERIFY_DELIVERY.py` verifies the current repository layout and hashes. Original nested manifests remain receipts of the earlier delivery, including its original filenames.

To use an edited figure in the manuscript, replace its PDF in `paper/v0.27/latex/figures/` and rebuild. Return the editable source and script with the PDF/SVG; document any intentional numerical change separately.
