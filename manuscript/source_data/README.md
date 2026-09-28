# Manuscript Source Data

## Main figures

`nature_mainline_v1/` contains the 29 CSV tables underlying main Figures 1–5 and Supplementary Figure S5, together with the machine-readable export manifest. The stable `fig6_community_profile_*` table identifiers preserve compatibility with the pre-migration bundle, but their declared publication target is now S5; the main Figure 6 identifier belongs to the separate economic Source Data contract. The bundle contains 21,694 rows.

Each manifest table declares its figure and panel mapping, retained columns, row count, input hashes and output CSV hash. The figure renderer validates these hashes before plotting.

`nature_economic_v1/` contains the 10-table, 34,653-row contract for Main
Figure 6. Four CSVs are the exact panel inputs: 24 rows for fixed-site scale,
13 rows for mechanism sensitivity, 36 rows for signed decomposition and 9 rows
for duration. The remaining tables expose the technical/economic boundary,
300-event paired ledger, 33,414-row interval ledger, parameter provenance,
37-row external-evidence register and 810-row recovery-throughput mapping.
Formal Figure 6 artwork is produced only by Web-GPT from the checksum-verified
package `results/exports/AIDRBench_Figure6_WebGPT_v2.zip`; repository-side
plotting must not substitute another aggregation.

## Additional economic robustness (Supplementary Tables 7–9)

`nature_economic_robustness_v1/` contains four additional CSVs (1,767 rows):
1,728 crossed delay/site-cost coordinates, 27 nested-bootstrap diagnostics,
three duration-level incremental-service diagnostics and nine exact-reference
reconciliations. These are explicitly post-hoc development sensitivities on
the existing paired ledger, not new technical or independent economic
certificates. The original Figure 6 tables and drawing package are unchanged.
The separate manifest records input, executable-source and output hashes and
clean-source generation from `52d96a2565a02783b9322a5e1fe0fb8b4ec42816`.
The four CSVs remain byte-identical to the initial dirty-worktree bundle,
whose original manifest is retained in that commit. This provenance update
does not constitute the final journal or DOI release. See
`docs/release_completion/v2.md` for the generation receipt and audit trail,
and `docs/economic_participation/cost_robustness_2026-09-05.md` for methods.

## Supplementary figures

`nature_supplementary_v1/` contains the measured calibration points for Supplementary Figure 2, the complete 63-feature observation contract for Supplementary Figure 3, and the hourly trajectory plus representative-episode metadata for Supplementary Figure 4. Supplementary Figure 1 is a source-bound schematic and has no numerical table. Supplementary Figure S5 reads its four hash-verified source tables from `nature_mainline_v1/` and is exported as four one-to-one plot files named `figure_s5_panel_a.csv` through `figure_s5_panel_d.csv`; its final artwork is assembled by Web-GPT rather than the local renderer. Per-figure source hashes are stored beside the GitHub previews under `docs/figures/nature_supplementary_v1/`.

These files are manuscript Source Data, not the redistributed raw Alibaba or NREL datasets. Third-party download locations and raw/preprocessed hashes are declared in `data/manifests/sources.yaml`.
