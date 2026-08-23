# Results evidence allocation

The main text follows the shortest evidence chain needed to establish the central claim. Complete diagnostics, raw hardware traces and secondary sensitivity tables remain in the Supplementary Information or Source Data.

| Evidence | Function | Main-text use | Destination for full record |
|---|---|---|---|
| nominal 50% proxy versus q=0.95 PI tolerance boundary | core discovery | Result 1, headline comparison | Fig. 1 and Source Data |
| four-GPU class-aware power measurements | necessary support / provenance | one compact paragraph | Supplementary Note 1 and Supplementary Fig. 1 |
| PI, restricted NA and causal layers | necessary support | define distinct meanings once | Methods and Supplementary Note 3 |
| duration and reliability surfaces | core discovery | Result 2 | Fig. 2; full surfaces in SI |
| zero notice gain and headroom diagnostic | qualification / mechanism | retain because it changes interpretation | Fig. 2; node-level diagnostics in SI |
| repeated-event compute debt and joint success | core discovery | Result 3 | Fig. 3; full event table in SI |
| fixed-DC PV-hosting gain | core system consequence | Result 4 headline | Fig. 4 and Source Data |
| fixed-PV utilisation and curtailment changes | qualification | Result 4, explicitly bounded as small/profile-dependent | Fig. 4; all ten contrasts in SI |
| AI×PV and AI×BESS interactions | mechanism / application | one paragraph | Fig. 4; full 2×2×2 tables in SI |
| power, workload and criterion sensitivities | robustness / heterogeneity | concise ranges in Result 5 | Fig. 5 and SI |
| locked-ID certificate | necessary support | Result 5, including H=1 failure | Fig. 5; complete q×H×N table in SI |
| locked-OOD replay | conclusion-changing boundary | Result 5 | Fig. 5; complete outcomes in SI |
| 63-dimensional AIDRBench interface and reward variants | reproducibility detail / non-mainline extension | Methods sentence only; no reward results | Supplementary Note 2 |
| RL training and algorithm comparisons | outside the paper's main claim | excluded | online-control extension only |

## Primary statistics retained in the main text

- Nominal overstatement range relative to the 100.50 kW nominal proxy.
- Validation paired PV-hosting gains with Bonferroni 95% simultaneous confidence intervals.
- Validation fixed-PV energy and utilisation effects with bounded interpretation.
- Repeated-event ranges for event-4 compute-debt increment, residual delivery and joint success.
- Locked-ID success counts and one-sided 95% Wilson lower bounds for q=0.95.
- Locked-OOD q=0.95 success counts and the 0/18 certification outcome.

Secondary q levels, curtailment thresholds, all scenario-wise values, solver diagnostics and bootstrap distributions are routed to the Supplementary Information and Source Data.
