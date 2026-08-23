# Figure 4 renewable-integration QA receipt

Date: 2026-08-23  
Backend: Python/matplotlib  
Final width: 180 mm (double column)  
Source Data manifest SHA-256:
`ef92306befe815026c8ce3271c912c78dcd8c58b5c84e161744edfb9ad92f3b2`

## Evidence and panel audit

| Panel | Unique claim | Summary / interval | Independent unit | Visual audit | Result |
|---|---|---|---|---|---|
| a | Workload flexibility shifts the joint DC–PV hosting boundary | 100-scenario simultaneous minimum at 5% maximum curtailment; open markers show partial `n/100` feasibility | frozen validation scenario | Four series are separable by colour, marker and line style; partial cells are not connected across missing firm points; labels clear the markers | pass |
| b | The 1×-DC paired PV-hosting gain replicates with and without BESS | paired mean with preregistered Bonferroni 95% simultaneous interval for development and validation | frozen scenario pair | legend moved to unused upper-left space; no point or interval is obscured | pass |
| c | Fixed-500-kW PV operating effects differ by metric and BESS context | paired flexible-minus-rigid effects for curtailment, utilisation and grid import, each on its own unit-specific axis | frozen validation scenario pair | zero references, two BESS strata and all intervals remain visible; no incompatible units share an axis | pass |
| d | Existing fixed-PV/max-DC interactions explain complementarity and substitution | paired difference-in-differences with Bonferroni simultaneous intervals and ± practical-equivalence band | frozen development or validation scenario pair | panel label and heading no longer collide; band does not mask estimates or intervals | pass |

The complete rendered figure was inspected at final physical size after the
panel-level audit. No label, legend, uncertainty interval or panel heading
collides with another plotted element. The hero panel remains visually dominant.

## Automated and export checks

- Static source preflight: 20 pass, 0 warn, 0 fail.
- PDF text audit: 64 text runs; minimum 5.8 pt; zero runs below 5 pt.
- SVG: editable text retained (64 `<text>` elements).
- PDF: editable vector export.
- TIFF: 4,251 × 3,630 pixels at 600 dpi.
- PNG review preview: 2,125 × 1,815 pixels at 300 dpi.
- Quantitative inputs: four hash-verified Source Data tables; no visual-only
  filtering of scenario rows.

## Output hashes

| Format | SHA-256 |
|---|---|
| SVG | `de0b56d8c839513d3e840c68feebba787e3ad94a3d405582648f0eb7d1193fa3` |
| PDF | `d319b1fb602136b9dc1d99f079ea6e103ea45f5a9e6a4aa2fc45ecde2c84b58e` |
| TIFF | `ef52340f8ebced40b4ee9e25c46793a0b9f9f7826124f853e604afbf40ec5cea` |
| PNG | `6dbd46b234f966c4f8778fc39d3c18d645e84e9e7f918e48e99a9c159f16dd58` |

## Claim boundary

Figure 4 reports perfect-information renewable-planning ensembles, not a
deployed causal effect. The fixed-PV validation gain is small, especially with
BESS; flexible schedules use the declared 1% deadline-miss budget, and the
figure does not claim a general reduction in PCC peak. A new community or
workload distribution requires local revalidation before transferring the PV
benefit.
