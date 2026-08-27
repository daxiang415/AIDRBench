# Nature Communications submission-readiness audit

Audit date: 2026-08-28

## Scientifically complete

- One main question and one system consequence are consistently used across the protocol, README, manuscript and figures.
- The formal mainline contains no reinforcement-learning training or controller leaderboard.
- Nominal, perfect-information, restricted non-anticipative and independently tested causal evidence remain explicitly separated.
- Locked-ID and locked-OOD results are frozen and hash-bound; no locked outcome was reopened during the final sensitivity and figure work.
- Alibaba 2026, NREL community profiles and four-GPU calibration are bound to the formal protocol by local SHA-256 values.
- The zero-deadline-miss renewable sensitivity covers 1,600 optimal rows and preserves the headline hosting and PV-use results.
- The paired EULP 3A/3C/5A development sensitivity holds jobs, hardware and events fixed across 300 scenarios. It returns identical q = 0.95 firm-capacity surfaces and controller success counts across profiles, plus 1,200/1,200 optimal PV-hosting programmes and six positive Bonferroni-controlled paired contrasts.
- Six main figures and four supplementary figures are generated at 183-mm width with per-figure manifests.

## Journal-format audit

- Title: 11 words, below the 15-word Article limit.
- Abstract: 143 whitespace-delimited words, below the 150-word limit.
- Introduction + Results + Discussion: approximately 3,181 whitespace-delimited words, below the 6,000-word main-text limit that excludes Methods and figure legends.
- Main display items: six figures, below the maximum of ten.
- References: 34; DOI/reference-manager records are retained under `manuscript/references/verified-v1/`.
- Supplementary Information includes complete methods, certificate tables, sensitivity results and four generated figures; the main manuscript now contains six generated figures.

## Repository and reproducibility audit

- `uv lock --check`: passed.
- `ruff check .`: passed.
- `mypy src`: passed for 58 source files.
- `pytest`: 165 passed.
- Formal protocol with `--require-execution-ready`: valid; all 45 declared structure and execution checks passed.
- Source manifest: valid; every locally declared artifact and all three formal-mainline bindings matched.
- Main Source Data: 29 tables, 21,694 rows; the clean-commit export binds all six figures to one manifest and is tracked under `manuscript/source_data/`.
- Figure renderers: 20/20 static checks; PDF minimum text sizes were 5.8–6.2 pt for main figures and 6.1–6.5 pt for supplementary figures.

## Required before submission or archival

- Rebuild the manuscript review PDF so it includes Figure 6; the currently tracked v0.4 PDF predates the community-profile result.

1. Add author names, affiliations and corresponding-author email.
2. Add funding, facility acknowledgements and non-author contributions.
3. Provide CRediT author contributions and the competing-interests declaration.
4. Select a repository software license; `pyproject.toml` deliberately remains unset until the author decides.
5. Archive the full CSV/SVG/PDF/TIFF bundle generated from clean scientific commit `ba0dfb7de774d34b336c6cd25f062ed382c55825`.
6. Create an immutable GitHub release and Zenodo deposit; replace the Data Availability and Code Availability DOI placeholders.
7. Add final title-page metadata and complete the journal submission forms, reporting checklist and source-data upload mapping.

No additional scientific experiment is required for the current Model A claim set. Any extra workload trace, GPU architecture extrapolation, reinforcement-learning controller or repeated-event capacity re-selection would constitute a new analysis rather than submission cleanup.
