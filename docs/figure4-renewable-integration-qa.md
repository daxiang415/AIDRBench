# Figure 4 renewable-integration QA receipt

Date: 2026-08-25

Backend: Python/matplotlib

Final width: 183 mm (double column)

Source Data manifest SHA-256:
`0cda495b49a22357454d97ca66153579ed9d89e4957540ca86d63b45bce3ef13`

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
- TIFF: 4,322 × 3,630 pixels at 600 dpi.
- PNG review preview: 2,161 × 1,815 pixels at 300 dpi.
- Quantitative inputs: four hash-verified Source Data tables; no visual-only
  filtering of scenario rows.

## Output hashes

| Format | SHA-256 |
|---|---|
| SVG | `7b11fcb2d64a6c9c5644e9a65c942f738ae11e372a35bb077d443a3c5bba8208` |
| PDF | `c5d3c1de0cab5b15243e94f142b391b1e2255e3df53154cb89cc6bede91761cc` |
| TIFF | `eda64cb0b0e59db0b0e372175d7b027fb6fa4c7dc47bb3bf866c15b5f0ad178a` |
| PNG | `fd7b22c427517b3e12558881bb895d4c713e45b98d0d295b8d1ac36e1d2f7025` |

## Claim boundary

Figure 4 reports perfect-information renewable-planning ensembles, not a
deployed causal effect. The fixed-PV validation gain is small, especially with
BESS; headline flexible schedules use the declared 1% deadline-miss budget,
and the figure does not claim a general reduction in PCC peak. A separate
zero-deadline-miss sensitivity preserves the validation hosting boundary and
PV-use gains at the reported precision. A new community or
workload distribution requires local revalidation before transferring the PV
benefit.
