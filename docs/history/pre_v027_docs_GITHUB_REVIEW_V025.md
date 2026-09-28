# Current manuscript and runnable figure review: v0.25

This is the current **2026-09-10 manuscript/SI v0.25**, Chinese **v19**, copied from the checked local release for GitHub access on 2026-09-11. It is a review snapshot, not a journal submission or a new set of experiments. No author identities, funding or licence have been supplied on the author's behalf.

Current [submission readiness](../manuscript/submission-readiness.md), [Chinese explanation](../manuscript/submission-readiness.zh.md) and [review freeze record](../manuscript/releases/v0.25-review-2026-09-11/README.md) supersede the archived 2026-09-06 readiness audit. Documentation updates do not change scientific commit `8c508b9`.

## Read the current paper

- [English main text](../manuscript/nature_communications_article.md)
- [English Supplementary Information](../manuscript/supplementary_information.md)
- [Main PDF: 17 pages, six figures](../manuscript/exports/AIDRBench_Nature_Communications_v0.25_content_revision.pdf)
- [SI PDF: 25 pages, five figures and 21 tables](../manuscript/exports/AIDRBench_Nature_Communications_v0.25_Supplementary_Information_content_revision.pdf)
- [Chinese main text](chinese_reader/v19/main_zh.md) · [Chinese SI](chinese_reader/v19/supplement_zh.md)
- [Six main figures](nature-mainline-figure-preview.md) · [Five supplementary figures](nature-supplementary-figure-preview.md)
- [Revision reasons and evidence boundaries](../manuscript/revisions/commitment_narrative_2026-09-10/RESULTS_AND_REASONS_ZH.md)

Figure 3c now compares count/resource-time weights in original/permuted hourly order. Figure 4 explains paired supply margins, strict feasibility and commitment decisions. The 63/80 historical cross-score is S3d; PV is S4. Historical selection explanations are in Supplementary Note 7. The paper retains pointwise, scenario-specific qualification and the distinction between zero misses in a successful series and a 95% overall success-probability target.

## Directly redraw all eleven figures

From the repository root, using Python 3.12 and a virtual environment:

```bash
python -m pip install -r requirements_figures_v025.txt
python scripts/redraw_figures_v025.py
```

The default output is `results/redraw_v025/`. Use `--output PATH` to change it. The runner reads included CSV/JSON tables, produces editable PDF/SVG plus PNG/TIFF, and never runs simulations or resamples trials. Four plotting files in `scripts/figures_v025/` use the verified full v14 plotting logic, reformatted to satisfy repository lint checks; the final PNGs are compared with the frozen release. The runner omits superseded plotting stages that need large hourly tables; final outputs are checked against the delivered eleven PNGs.

| Current figures | Plotting file | Editable input directory |
|---|---|---|
| Main 1, 2, 5 | `plot_results.py` | `manuscript/source_data/nature_workload_composition_v1/` |
| Main 6; Supplementary 5 | `plot_mechanisms.py` | `manuscript/source_data/nature_commitment_mechanisms_v1/` (also reads two structural summaries) |
| Main 3, 4; Supplementary 3, 4 | `plot_narrative.py` | `manuscript/source_data/nature_commitment_narrative_v1/` |
| Supplementary 1, 2 | `plot_supplement.py` | `manuscript/source_data/nature_workload_composition_v1/` |

Edit the CSV files in those directories to change plotted data. Figure 4c text is in `nature_commitment_narrative_v1/decision_steps.csv`. Its `PANEL_DATA_MAP.csv` gives panel filters, columns and uncertainty interpretation. Summary files duplicated between evidence generations retain their original values; use the directory associated with the final plotting file above when editing a current figure.

## What is included and what stays local

Included: current papers and Chinese readers, eleven PNG/PDF/SVG figures, four complete plotting scripts and their summary inputs, frozen protocols and compact outcome ledgers, selected method code for inspection, and numerical/reproducibility receipts. Main and SI text and PDFs preserve the checked v0.25 content. Absolute image links in Chinese readers and previews are converted to repository-relative links for GitHub.

The large raw production records, full hourly trajectories, frozen per-scenario recovery inputs, generated TIFFs and 13.39-GB archive are not part of this Git commit. Original source READMEs and historical audit receipts describe the complete local release; their references to omitted files are provenance, not claims that those files are present here. Figure regeneration needs none of them. Full simulation or PI replay would still require the complete local data package.

The local complete archive is `AIDRBench_All_Figures_2026-09-10_v14.zip`, SHA-256 `e7d2095b32e3ad8af8ca396d7260a494120e52357b52342c6b395c91785cb923`. It is preserved unchanged, rather than uploaded into Git.

`GITHUB_REVIEW_MANIFEST.csv` lists the current snapshot files and hashes. `docs/github_review_v025_validation.json` records the independent redraw and text checks performed on this GitHub checkout. Earlier benchmark documents and source code remain historical unless listed as current above. No new scientific simulations or subagent reviews were performed for this upload.
