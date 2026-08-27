# Manuscript Source Data

## Main figures

`nature_mainline_v1/` contains the 29 CSV tables underlying Figures 1–6 and the machine-readable export manifest. The bundle contains 21,694 rows. The current development export records commit `0198ab8bacaec26eb8ed1b5ad82ff0adff380505` with `software.git.working_tree_dirty=true` because the new community-profile analysis and Figure 6 have not yet been committed; it must be regenerated from the resulting clean commit before archival release. The current manifest SHA-256 is `9e29f02448813df1836de55a1a0e4e67a7b5d8acee049435983b658847954505`.

Each manifest table declares its figure and panel mapping, retained columns, row count, input hashes and output CSV hash. The figure renderer validates these hashes before plotting.

## Supplementary figures

`nature_supplementary_v1/` contains the measured calibration points for Supplementary Figure 2, the complete 63-feature observation contract for Supplementary Figure 3, and the hourly trajectory plus representative-episode metadata for Supplementary Figure 4. Supplementary Figure 1 is a source-bound schematic and has no numerical table. Per-figure source hashes are stored beside the GitHub previews under `docs/figures/nature_supplementary_v1/`.

These files are manuscript Source Data, not the redistributed raw Alibaba or NREL datasets. Third-party download locations and raw/preprocessed hashes are declared in `data/manifests/sources.yaml`.
