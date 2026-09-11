# v0.24 figure QA

Backend: Python/matplotlib only. F3/F6/S3/S5 are new quantitative grids using existing project style, not copied data mappings. F2/F5 keep the original data and relabel the earlier PI relaxation. All other figure content is retained. No raster illustration generator, smoothing, fitted trend or simulated placeholder is used.

Every figure has editable PDF/SVG text, a 300 dpi PNG and 600 dpi TIFF. Figure PDFs are 183 mm wide; all eleven passed the 6 pt minimum glyph audit. The new source validator passes every check. Numeric-first legends and rotated tick anchors were corrected. Inspecting the assembled plots identified and fixed a long panel title; signed negative cost components are stacked rather than overlaid. A focused S5a range makes the zero-waiting equal-price crossing visible; the full price grid remains in its ready table.

| Panel | Scientific role | Summary/uncertainty | Data and visual check |
|---|---|---|---|
| F3a | Fresh duration qualification | Success fraction and one-sided 95% Wilson lower bound; n=300 each | All four endpoint selections shown; capacities label the products |
| F3b | Distinguish mechanisms | All 15 prespecified zero-loss/full-request diagnoses, three per configuration | Mutually exclusive display categories sum to three; not a prevalence estimate |
| F3c | Correct old score interpretation | Eight observed weeks, ten synthetic realisations each | Both scores agree; all 17 larger-request failures are shortage segments; no independent-week CI |
| F3d | Transfer changes with resource-time weights | All eight matched new weeks at fixed 2.95 kW | 80/80 versus 31/80; no weekly omission, all baselines feasible |
| F6a | Physical waiting exposure | Mean and scenario p05–p95, 300 trajectories | Includes failures; percentiles are not confidence intervals |
| F6b | Cost attribution | Components at total annual q95 | Positive/negative stacks plus net totals; tiny electricity term retained in table |
| F6c | Valuation sensitivity | All three tested waiting prices | Exact computed thresholds; joins guide the eye, no inferred optimum |
| F6d | Conditional duration decision | Analytic price frontier including opting out | Three waiting valuations, common axes, 0–750 displayed range; full table retained |
| S3a,b | Candidate resolution | One-sided development bounds, n=100 | Every local candidate retained; coincident curves have identical scores; no interpolation selection |
| S3c | Broader structural context | Two potentially overlapping failure counts per condition, n=300 | All six baseline GPU-allocation structural conditions displayed; other controls in SI/data |
| S3d | Call-history negative result | Paired final-call counts, n=300 | All six pairs coincide; isolated and repeated markers distinguish identical positions |
| S5a | Show a choice reversal | Difference between product-specific q05 net values | Zero waiting/zero fee, 0–75 USD/kW-year range; 25.57 crossing labelled; not q05 of paired difference |
| S5b | Retain failed trajectories in prices | Zero/US$1 per GPU-h missed-work valuations | Both refined products and prices retained |
| S5c | Entry versus opting out | Product-specific q05 net value | Zero/shared/full fees, both duration products, identical capacity price |
| S5d | Access-dependent entry floor | Analytic frontier | Full three fee curves; common fee preserves conditional product-ranking branch |

The full numerical tables, candidates, both service scores, all timing orders and all earlier structural comparisons remain in the package even where only the primary comparison is plotted. PANEL_DATA_MAP.csv states every panel filter and numeric column. Packaged redraw is checked against all eleven current PNG hashes, while controller replay independently checks complete numerical trajectories.
