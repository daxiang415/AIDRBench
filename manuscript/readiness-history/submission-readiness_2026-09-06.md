# Nature Communications submission-readiness audit

Audit date: 2026-09-06

The returned Figure 6 and S5 artwork passed three independent reviews. The user
confirmed selecting GPT-6 in the web session; local tools did not directly observe
that session. Accepted original files and their hashes are retained in
`docs/figures/web_gpt_v1/`; review evidence is in `docs/web_gpt_return_review/`.
Main v0.7 (20 pages) and SI v0.6 (22 pages) `web_figure_review` PDFs now include
the unchanged vector figures at 183 mm and retain the author/release placeholders.
An isolated Python 3.12 environment with the returned pinned dependencies rebuilt
all eight figure files byte-for-byte and passed the complete supplied QA entry.
The web record used Python 3.13.5; this local check is a compatibility reproduction.
The manuscript's one-event threshold was corrected from 130.02 to 130.01 by
rounding the unchanged CSV value 130.014646367 to two decimal places.

The repaired checkout suite previously passed 245 tests without ignored production
files. Earlier content and local-draft PDFs remain historical artifacts. The user
has explicitly deferred author declarations and the software-license decision.

## Completed analyses within the declared claim scope

- One main question and one system consequence are consistently used across the protocol, README, manuscript and figures.
- The formal mainline contains no reinforcement-learning training or controller leaderboard.
- Nominal, perfect-information, restricted non-anticipative and independently tested causal evidence remain explicitly separated.
- Locked-ID and locked-OOD results are frozen and hash-bound; no locked outcome was reopened during the final sensitivity and figure work.
- Alibaba 2026, NREL community profiles and four-GPU calibration are bound to the formal protocol by local SHA-256 values.
- The zero-deadline-miss renewable sensitivity covers 1,600 optimal rows and preserves the headline hosting and PV-use results.
- The paired EULP 3A/3C/5A development sensitivity holds jobs, hardware and events fixed across 300 scenarios. It returns identical q = 0.95 firm-capacity surfaces and controller success counts across profiles, plus 1,200/1,200 optimal PV-hosting programmes and six positive Bonferroni-controlled paired contrasts.
- A paired economic ledger follows all service and energy effects through the episode-end clearance tail for the independently certified H = 2, 4 and 8 h capacities.
- The economic screen separates slack-backed, reserved-headroom and throughput-displacing participation; fixed site cost, variable enablement and effective displaced-compute value are explicit rather than bundled.
- The 0.2–20 MW rows are labelled proportional reference-module accounting sensitivities with no diversification and are never presented as scaled technical certificates.
- The post-hoc delay/site-cost cross contains 1,728 rows; 200/2,000/10,000 nested annual draws supply 27 sampling diagnostics. All nine original economic thresholds reproduce within 4e-10 USD/kW-year. Supplementary Tables 7–9 are checked against calculated values by regression tests.
- Incremental service diagnostics distinguish recovered delay from assumed displaced-compute contribution; no observed permanent throughput or operator revenue loss is inferred.
- The nominal/PI percentage gap is consistently stated as 47.3–62.4% below nominal, with the nominal denominator explicit.
- Main Figures 1–5 and Supplementary Figures S1–S4 retain reproducible local artwork. Main Figure 6 and Supplementary Figure S5 now use the accepted web-returned originals, backed by exact panel data and Web-GPT contracts.

## Journal-format audit

- Title: 10 words, below the 15-word Article limit.
- Abstract: 167 whitespace-delimited words, below the current 200-word Article limit.
- Introduction + Results + Discussion: approximately 4,018 whitespace-delimited words, below the journal's ideal 5,000-word main-text guidance excluding Abstract, Methods, References and figure legends.
- Methods: approximately 2,960 whitespace-delimited words, within the typical less-than-3,000-word guidance.
- Main display items: six figures, below the maximum of ten.
- References: 40; DOI/reference-manager records are retained under `manuscript/references/verified-v1/`, and official economic sources are additionally recorded in the machine-readable evidence register.
- Supplementary Information includes technical and economic methods, nine numbered tables, sensitivity results and the five-figure evidence plan; the additional economic sensitivity is explicitly post-hoc.

## Repository and reproducibility audit

- `uv lock --check`: passed.
- `ruff check .`: passed.
- `mypy src`: passed for 70 source files.
- Historical pre-portability-fix test run on 2026-09-05: 228 passed in 55.50 s, including 24 cost-robustness, provenance and manuscript-consistency checks. The current checkout suite has 245 passing tests; see the follow-up receipt above.
- Formal protocol with `--require-execution-ready`: valid; all 46 declared structure and execution checks passed.
- Source manifest: valid; every locally declared artifact and all three formal-mainline bindings matched.
- Main technical/system Source Data: 29 tables, 21,694 rows. Economic Source Data: 10 tables, 34,653 rows. Both manifests record clean commit `50dad4e37d725d9cae1e8313b9c7db51459aec9f`.
- Additional economic robustness Source Data: four tables, 1,767 rows. Its current manifest records exact input/code/output hashes and clean-source generation from `52d96a2565a02783b9322a5e1fe0fb8b4ec42816`. All four CSVs are unchanged; the earlier dirty-generation manifest remains in Git history. A complete final release is still required for archival.
- Formal economic and S5 artwork is outside the repository renderer path. Both original input packages and returned artwork passed hash, row-count, column-order, actual SVG geometry and independent visual checks.

## Required before submission or archival

- The two formal web artworks have been received and inserted. The current full-figure PDFs are ready for author review; the earlier artwork-pending PDFs are historical.

1. Add author names, affiliations and corresponding-author email.
2. Add funding, facility acknowledgements and non-author contributions.
3. Provide CRediT author contributions and the competing-interests declaration.
4. Select a repository software license; `pyproject.toml` deliberately remains unset until the author decides.
5. Archive the complete source-data, Web-GPT generation record and final SVG/PDF/TIFF bundle from one clean release commit.
6. Create an immutable GitHub release and Zenodo deposit; replace the Data Availability and Code Availability DOI placeholders.
7. Add final title-page metadata and complete the journal submission forms, reporting checklist and source-data upload mapping.

The economic update did not require a new technical replay or capacity selection. Current economic conclusions remain conditional parameterised screening; an observed operator-profitability claim would require operator cost and market-product evidence. The new monetary sensitivities address the identified delay/site-cost robustness gap, not every possible business uncertainty. Two-figure visual acceptance is complete. Clean-release provenance and author metadata remain open. Any additional workload trace, GPU-architecture extrapolation, reinforcement-learning controller or repeated-event capacity reselection would be a new analysis rather than submission cleanup.
