# v0.25 figure and PDF checks

Four displays changed: main Figures 3 and 4, Supplementary Figures 3 and 4. The other seven artwork files retain the previous version's values and presentation. All eleven retain editable PDF/SVG text, 300-dpi PNG and 600-dpi TIFF exports. The source preflight reports 20 passes, no warnings or failures; the actual eleven figure PDFs meet the 6-pt glyph floor.

Visual inspection covered all four changed figures and their rendered manuscript pages. Figure 3c's long category labels were shortened to Counts/GPU-h, with resource-time defined in the caption. Figure 4c's left box border was moved inside the canvas. The final figures retain all points, service endpoints and control conditions specified in `PANEL_DATA_MAP.csv`. The very small BESS contrasts in S4 are retained and explicitly limited by solver precision.

Figure 4a contains all 80 matched realisations. The hourly illustration uses the prespecified lowest seed, 990000, and displays 168 hours from the supplied 216-hour series. The figure does not use hourly permutations as a proposed operating policy. The decision sequence distinguishes a failed series from rejection of a probabilistic offer and a full-information witness from an implemented causal controller.

The actual delivered launcher recreated all eleven figures from package tables. Each PNG is byte-identical to the current artwork; see `redraw_validation.json`. PDF byte identity was not used because creation metadata can differ. No new simulation or resampling was performed by the plotting script.

The current English main PDF has 17 pages and six figure bookmarks; the SI PDF has 25 pages, five figure bookmarks and 21 table bookmarks. Every SI bookmark was checked against the actual linked page. The Methods heading now starts with its first subsection; anchors are placed after heading page breaks. All pages were scanned for text extending beyond the page edges. Current core-figure pages, figure legends, SI navigation, Note 7 and final Tables 20–21 were visually reviewed. This was targeted visual QA, not a claim that every unchanged page received a new manual visual review.

The source title, English/Chinese blocks, Figure 5 legend and previews match. Supplementary Table 16 points to the relocated S3d cross-score, not the replacement Figure 3c. The evidence-level and selection-history corrections remain in Supplementary Note 7.

Result: PASS for the stated checks. These are reproducibility and presentation checks, not independent peer review or a prediction of journal acceptance. No subagents were used.
