# Main figures: editing and panel data

Six reference figures for manuscript **v0.27**, main artwork **R8** (17 September 2026). The scientific data and reference artwork are unchanged by the documentation refresh.

| Directory | Contents |
| --- | --- |
| `01_FIGURES/` | Reference PDF, PNG and SVG files for Figures 1–6. |
| `02_PANEL_DATA/F01/`–`F06/` | Direct plotting tables in CSV and Excel. |
| `03_EDITABLE/` | Corrected editable PowerPoint and SVG sources. |
| `05_CODE/` | Scripts and plotting dependencies. |
| `06_AUDIT/` | Existing coordinate/data checks and export records. |

Browse the [figure gallery](../../../../docs/figures.md) before choosing a file to edit. Start from the corrected reference artwork, not the original received input in `04_ORIGINAL_INPUT/`.

## Rebuild

From the repository root, after installing the plotting dependencies:

```bash
python tools/aidr.py main-figures
```

This builds the corrected panels and PowerPoint in `rebuild/`. The output presentation is `rebuild/corrected/AIDRBench_Figures_R8_corrected.pptx`. For automatic PDF export, install LibreOffice and add `--export-pdf`; otherwise export from PowerPoint. The lower-level entry point remains `python RUN_REBUILD.py --panels-only` from this directory.

Eleven corrected panels are embedded vector SVG; the remaining panels retain native PowerPoint objects. An SVG panel is not a native Excel chart. Change its source script/CSV and replace the regenerated SVG when necessary.

## Preserve the interpretation

Use the direct panel tables; do not retype values from a screenshot or recalculate the reported statistics for a style-only edit. Figure 3b joins the nine tested points without smoothing. Figure 6a is an empirical step distribution. Figure 5's cost points do not have error bars. Figure 6b's net-value diamonds belong at their actual data coordinates, not at a manually chosen position above a bar.

Figure 4 retains the supplied hourly coordinates, event windows and recovery trajectory. Figure 1 is a conceptual overview; its displayed category shares retain the original rounding. Detailed definitions and captions are in the [paper](../../latex/main.pdf).

Figure 1's SVG requires the neighbouring `Figure_1_assets/` directory. Its PDF and PNG are standalone.

## Put an edited figure into the paper

Export a single-figure PDF, copy it to `paper/v0.27/latex/figures/` under the existing filename, and rebuild the paper. Neither the PowerPoint rebuild nor a CSV redraw performs this replacement automatically.

For a style-only change, preserve coordinates, samples, units, statistics and caption meaning. Keep the edited source alongside the exported PDF/SVG so the figure remains editable. Current checkout verification is `python tools/aidr.py check --hashes` from the repository root; earlier receipts remain historical records.
