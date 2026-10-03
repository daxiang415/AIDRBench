# Main figure generation

Reference figures and panel data for manuscript **v0.27**, main artwork **R8**.

| Directory | Contents |
| --- | --- |
| `01_FIGURES/` | Reference PDF, PNG and SVG for Figures 1–6 |
| `02_PANEL_DATA/F01/`–`F06/` | Panel-level CSV and Excel tables |
| `03_EDITABLE/` | PowerPoint and SVG source artwork |
| `05_CODE/` | Plotting scripts and requirements |
| `06_AUDIT/` | Coordinate checks and export records |

The [figure index](../../../../docs/figures.md) links each figure to its panel tables. `04_ORIGINAL_INPUT/` contains earlier source artwork, not the reference results.

## Reproduction

After installing the plotting dependencies, run from the repository root:

```bash
python tools/aidr.py main-figures
```

This regenerates corrected panels and the presentation at `rebuild/corrected/AIDRBench_Figures_R8_corrected.pptx`. PDF export requires LibreOffice and `--export-pdf`. The standalone command `python RUN_REBUILD.py --panels-only` is also available from this directory.

Eleven corrected panels are embedded SVG; other panels retain native PowerPoint objects. The reconstruction therefore combines script-generated panels with the stored presentation layout.

## Plot definitions

Figure 3b connects the nine tested points without smoothing. Figure 6a uses an empirical step distribution. Figure 5's cost points do not have error bars; Figure 6b's net-value diamonds use their tabulated coordinates.

Figure 4 retains the hourly coordinates, event windows and recovery trajectories supplied in the panel tables. Figure 1's category shares use the rounding shown in the paper. Full definitions are in the [paper captions](../../latex/main.pdf).

The Figure 1 SVG requires its adjacent `Figure_1_assets/` directory. Its PDF and PNG are standalone. Reproduction outputs are written under `rebuild/` and do not replace the paper's reference figures.
