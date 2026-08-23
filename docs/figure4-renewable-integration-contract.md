# Figure 4 renewable-integration contract

## Core conclusion

Job-feasible workload flexibility expands the curtailment-constrained community
DC–PV feasible set and increases the local use of a fixed PV installation, but
the fixed-PV operational gain is small and smaller with BESS in independent
validation, and neither result implies a universal reduction in PCC peak.

The validation headline evidence is a 44.85 kW paired mean PV-hosting gain
without BESS and 43.20 kW with BESS at 1× DC. At fixed 500 kW PV, the paired
PV-use gains are only 18.37 and 5.76 kWh, respectively; the with-BESS
simultaneous interval has a lower bound effectively at zero. Panel hierarchy
must reflect this difference in practical magnitude.

## Figure contract

- **Archetype:** asymmetric quantitative figure with one hero panel.
- **Target/output:** *Nature Communications* main figure; Python/matplotlib;
  180 mm wide; editable SVG/PDF plus 600-dpi TIFF and review PNG.
- **Independent unit:** frozen scenario; development and validation each
  contain 100 scenarios.
- **Uncertainty:** paired within-scenario mean contrasts with predeclared
  Bonferroni 95% family-wise simultaneous intervals.

## Panel map and evidence hierarchy

### a — Joint DC–PV hosting envelope (hero)

Show the validation 5%-curtailment envelope for rigid/flexible × BESS off/on.
Only 100/100 scenario-feasible points form the simultaneous envelope. Partially
feasible cells may be shown as open descriptive markers labelled `n/100`, but
must not be joined into the firm line or plotted as zero capacity.

### b — PV hosting gain at fixed 1× data centre

Show flexible-minus-rigid PV nameplate gain for BESS off/on in development and
independent validation. Display the paired simultaneous confidence intervals;
do not substitute a difference of ensemble minima for the paired estimand.

### c — Fixed 1× DC and 500 kW PV operation

Show the paired flexible-minus-rigid effects for PV curtailment, PV utilisation
and grid-import energy, stratified by BESS. Use metric-specific axes/units rather
than combining unlike quantities on one numerical scale. Retain the complete
PV available/used, renewable demand share, PCC peak, BESS throughput and service
metrics in Source Data and Results text.

### d — Existing AI–PV and AI–BESS interactions

Retain the independently validated fixed-PV/max-DC interactions as the
orthogonal feasible-set slice. The practical-equivalence band remains visible;
with-BESS AI×PV must remain labelled practically indeterminate.

## Source-data contract

- PV-hosting summary and paired contrasts for development and validation;
- fixed-capacity operation summary and paired contrasts for both splits;
- full scenario-level renewable results, including infeasible statuses;
- existing data-centre hosting summary and interaction contrasts.

No observation is removed for visual convenience. Aggregation may be used only
where the rule and independent unit are declared; all scenario rows remain in
the manuscript Source Data bundle.

## Reviewer-risk register

1. These are perfect-information renewable-planning bounds, not deployed causal
   renewable-integration effects.
2. A single-event locked-ID DR certificate cannot be transferred automatically
   to a PV planner or a different community/workload distribution.
3. Flexible fixed-PV schedules use the Model A permitted 1% deadline-miss
   budget; rigid baselines have zero miss. Both values must remain visible.
4. PV utilisation can rise while maximum PCC import fails to fall; energy and
   capacity claims must remain separate.
5. BESS charge and discharge are mutually exclusive; simultaneous dispatch
   residual and terminal SOC deviation are audited.
6. The 5% curtailment ceiling is a headline convention, accompanied by the
   predeclared 0%, 10% and 20% sensitivity rather than presented as universal.
