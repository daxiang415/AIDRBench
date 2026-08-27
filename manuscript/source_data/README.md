# Manuscript Source Data

## Main figures

`nature_mainline_v1/` contains the 29 CSV tables underlying Figures 1–6 and the machine-readable export manifest. The bundle contains 21,694 rows. It was regenerated from clean scientific commit `ba0dfb7de774d34b336c6cd25f062ed382c55825`, records `software.git.working_tree_dirty=false`, and has manifest SHA-256 `90828abf3d0771916c2a8eaa85ce5835fcd06a2deec8a255acfd7f4992ad4ffc`.

Each manifest table declares its figure and panel mapping, retained columns, row count, input hashes and output CSV hash. The figure renderer validates these hashes before plotting.

## Supplementary figures

`nature_supplementary_v1/` contains the measured calibration points for Supplementary Figure 2, the complete 63-feature observation contract for Supplementary Figure 3, and the hourly trajectory plus representative-episode metadata for Supplementary Figure 4. Supplementary Figure 1 is a source-bound schematic and has no numerical table. Per-figure source hashes are stored beside the GitHub previews under `docs/figures/nature_supplementary_v1/`.

These files are manuscript Source Data, not the redistributed raw Alibaba or NREL datasets. Third-party download locations and raw/preprocessed hashes are declared in `data/manifests/sources.yaml`.
