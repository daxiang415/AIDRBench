# Manuscript Source Data

## Main figures

`nature_mainline_v1/` contains the 21 CSV tables underlying Figures 1–5 and the machine-readable export manifest. The bundle contains 17,386 rows and was exported from clean commit `f2f4dc699c067891b84601ec8bd9ddd8505f849c`; `software.git.working_tree_dirty` is `false`. The manifest SHA-256 is `7351fd609c9b23eb92a7e0e473f4279a61d3b5f59c7b9c913dd32fa6a40fd593`.

Each manifest table declares its figure and panel mapping, retained columns, row count, input hashes and output CSV hash. The figure renderer validates these hashes before plotting.

## Supplementary figures

`nature_supplementary_v1/` contains the measured calibration points for Supplementary Figure 2, the complete 63-feature observation contract for Supplementary Figure 3, and the hourly trajectory plus representative-episode metadata for Supplementary Figure 4. Supplementary Figure 1 is a source-bound schematic and has no numerical table. Per-figure source hashes are stored beside the GitHub previews under `docs/figures/nature_supplementary_v1/`.

These files are manuscript Source Data, not the redistributed raw Alibaba or NREL datasets. Third-party download locations and raw/preprocessed hashes are declared in `data/manifests/sources.yaml`.
