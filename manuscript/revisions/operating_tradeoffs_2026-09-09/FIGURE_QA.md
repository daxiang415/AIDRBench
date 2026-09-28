# Quantitative figure audit, v0.23

Python/matplotlib was used throughout. These are statistical plots from preserved model outputs, not AI-generated illustrations. Figures 3, 6, S3 and S5 were replaced; the other seven PNG/PDF/SVG/TIFF assets retain their preceding bytes. No data were edited during plotting.

| Panel | Unique purpose | Summary / uncertainty | Unit of replication | Visual and scope check |
|---|---|---|---|---|
| 3a | Service-standard choice | Selected grid kW; no invented kW confidence interval. Probability bounds in Table 14. | 100 development / 300 new confirmation scenarios per condition | Separate colours; NS does not equal zero; axes and legend clear |
| 3b | Immediate supply versus deadline pressure | Non-exclusive realised counts / 300; descriptive diagnostic, not an estimated maximum-capacity distribution | Complete scenarios, not hours | Necessary shortage distinguished from service failure; comparable 0–100% scale |
| 3c | Production-timing transfer | Eight raw weekly counts, 10 synthetic realisations each; no pooled binomial certificate | Observed week | Both orderings shown; 2.95-kW zero criterion clearly distinguished; legend above data |
| 6a | Fixed-cost attribution | Components attributed at total-cost q95; no marginal-quantile summation | 2,000 annual ledger draws, conditional accounting | Positive stack reconciles exact total; 40/60 assumptions retained |
| 6b | Zero/shared access fees | Deterministic fee transforms of qualified ledger thresholds; no inferential error bars | Same complete-series annual draws | All three products explicitly identified; start spacing distinguished from gap |
| 6c | Operating differences without fixed fees | q95 operating cost / selected accounting kW | Same as 6b | Zero origin; values directly labelled; does not claim hardware wear |
| 6d | Duration tariff and opt-out | Algebraic decision boundary, dense ready table includes exact switching point | Conditional prices, no sampling units | Both service endpoints, capacity ratios and equal-price reference visible |
| S3a | Historical implementation correction | Success / 300 with one-sided 95% Wilson lower limits | Earlier 970000 seeds, separate from new tests | Greedy only at 10% as actually tested; correction not physical evidence |
| S3b | Same-clock last-call falsification | Fresh/repeated observed proportions coincide for every paired seed; complete difference table has zero differences and intervals | 300 new matched scenarios | Symbols overlap intentionally; global service measures excluded from local electrical result |
| S3c | Complete selection grid | All selected powers and confirmation counts; no-candidate entries retained | Endpoint-specific 100/300 splits | Eight rows × four columns, no suppressed negative selections |
| S5a | Waiting-cost sensitivity | Repricing complete qualified ledgers, no added uncertainty decoration | Same 2,000 annual draws | Full zero-to-double price range; lower threshold floored at zero |
| S5b | Loss valuation | Costs at both stated loss prices, all trajectories included | Complete ledgers | Unqualified full request explicitly diagnostic, not a purchasable offer |
| S5c | Entry versus conditional ranking | Fifth-percentile annual net value at fixed illustrative product prices | Conditional accounting draws | Zero opt-out reference; same fee applied once to each option |
| S5d | Shared-fee duration decision | Exact algebraic boundary including opt-out | Conditional prices | Fee scenarios labelled; shared fee is not pooled reliability |

Each panel and the assembled images were inspected. An initial long title and panel-label placement were shortened/moved to fit the page. Legend colours were explicitly assigned. Dense price curves include their algebraic switching points rather than approximating a corner between sparse price scenarios. There are no text runs outside the exported PDF page; minimum actual size is 6 pt (Figure 3: 6.3 pt, Figure 6: 6.2 pt). Editable text is preserved in vector formats. Width is 183 mm; heights range from 159 to 185 mm. PNG is 300 dpi and TIFF is 600 dpi.

The source validator has no FAIL findings. Remaining WARNs concern literal USD dollar signs (math parsing is explicitly off and actual glyph sizes pass), numeric-start legend text, and rotated labels (visually checked). These deterministic checks do not substitute for the scientific audit.

All eleven figures were regenerated using only delivered plotting code and ready tables from a working directory outside the repository. Every PNG SHA-256 matches the delivered artwork. Four complete direct-replay paths—reference, four-hour, isolated last call, and chronological 24-h-spaced timing—match all 92 numeric columns and NaN/infinity masks exactly. See `package_redraw_validation.json` and `package_replay_validation.json`.
