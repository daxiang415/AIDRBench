# Supplementary figure generation

Reference figures and panel-level data for S1–S10 of the v0.27 supplement.

## Reproduction

From the repository root, using an environment with the plotting dependencies installed:

```bash
python tools/aidr.py redraw --figures S5
python tools/aidr.py redraw --figures S3 S9 --tiff
```

Omit `--figures` to generate all ten. Output is written to `MY_REDRAW/` in this directory. The standalone command `python DRAW_SUPPLEMENT.py --figures S5` is available from this directory.

The renderer reads CSV files in `S01/`–`S10/`. Excel workbooks contain parallel copies of the tabulated values and are not input to the scripts. The workflow needs no GPU or original simulation trajectories.

## Data index

| Figure | Subject | Workbook |
| --- | --- | --- |
| S1 | Workload and power evidence entering the analysis | [S01_READY.xlsx](S01/S01_READY.xlsx) |
| S2 | GPU-board power calibration and held-out validation | [S02_READY.xlsx](S02/S02_READY.xlsx) |
| S3 | Repeated-response offer screening and failure modes | [S03_READY.xlsx](S03/S03_READY.xlsx) |
| S4 | Flexibility assumptions, PV outcomes and fixed-request delivery | [S04_READY.xlsx](S04/S04_READY.xlsx) |
| S5 | Waiting costs, missed deadlines and access fees | [S05_READY.xlsx](S05/S05_READY.xlsx) |
| S6 | Delivery and deadline outcomes under changed conditions | [S06_READY.xlsx](S06/S06_READY.xlsx) |
| S7 | PV hosting, curtailment and grid purchases with and without storage | [S07_READY.xlsx](S07/S07_READY.xlsx) |
| S8 | Hardware lifetime and participation-cost assumptions | [S08_READY.xlsx](S08/S08_READY.xlsx) |
| S9 | Offer selection and independent qualification across observed weeks | [S09_READY.xlsx](S09/S09_READY.xlsx) |
| S10 | Peak-power decomposition, node overhead and solver checks | [S10_READY.xlsx](S10/S10_READY.xlsx) |

[Reference figures](ALL_FIGURES.pdf) · [Combined workbook](ALL_PANEL_DATA.xlsx) · [Captions](FIGURE_LEGENDS_EN.md) · [Series assignments](PLOT_ASSIGNMENTS.csv)

## Column conventions

`PLOT_ASSIGNMENTS.csv` identifies X/Y columns, interval bounds, stack bases and heatmap columns. Values are already selected and converted for plotting.

`pct` denotes percent, `pp` percentage points, and `fraction` a value on a 0–1 scale. `error_minus` and `error_plus` are error-bar lengths; `lower` and `upper` are interval endpoints. A one-sided lower bound has no upper error.

S1 is a conceptual diagram. S6 contains four separate outcome-count matrices. S8's hardware lifetime is an economic assumption about reserved capacity, not a measurement of wear caused by demand response.

## Verification

The reference PDFs are the figures used in the supplement. The CSV renderer reproduces their tabulated values; its layout can differ from the reference artwork.

The `audit/` directory records coordinate and rendered-series checks. `VERIFY_DELIVERY.py` checks the maintained repository layout and hashes. Reproduction output is separate from the paper's reference figures.
