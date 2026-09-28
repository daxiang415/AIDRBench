# Editable GitHub version v0.27

Prepared 2026-09-28 from the checked 2026-09-17 v0.27/R8 delivery. Start with [the Windows guide](../WINDOWS_START_HERE.md).

Included: self-contained main/SI LaTeX and PDFs, current English and Chinese Markdown, six main and ten supplementary figures, both editing packs, all direct plotting tables, compact Source Data, current library/configuration/test code and seven research-driver directories supporting the final analyses.

Portable directories are `paper/v0.27/latex`, `paper/v0.27/figures/main` and `paper/v0.27/figures/supplement`. A Windows-aware main-figure launcher accompanies the frozen files. Current reading-copy image links are repository-relative; local rendering outputs are ignored by Git.

The scientific version is v0.27; R8 names its main-artwork revision. No new experiments, offer selection or statistical estimation were performed. Author and archive placeholders remain unfilled at the author's request.

`manuscript/source_data/nature_economic_robustness_v1/frozen_runtime` holds the historical files bound by that result manifest. Numerical regression tests separately require the current implementation to reproduce its published tables. Small original figure input ZIPs and an historical SI are retained for regression tests; they are not current figure-editing entry points.

Bulk raw datasets, multi-GB hourly trajectories and per-scenario recovery inputs are excluded. Original research protocols may refer to those inputs. The current figure workflows use only included data. Full Git history is required for certificate-commit replay tests; use `git clone` for the complete development suite. Download ZIP suffices for paper/figure editing.

The GitHub edition's [manifest](../paper/v0.27/MANIFEST.csv) records editable release files. The [validation record](github_v027_validation.json) distinguishes local checks from GitHub Windows/Linux CI.

GitHub packaging adaptation: main Figure 1 SVG references 15 byte-identical PNG/JPEG assets in its adjacent `Figure_1_assets` folder. Keep that folder with the SVG when copying it. The PDF, PNG, PowerPoint, vector geometry and scientific data are unchanged. This avoids a secret-scanning false match in inline JPEG encoding. `GITHUB_ADAPTATION.json` records original and current hashes; `ORIGINAL_FILE_MANIFEST.csv` preserves the earlier receipt.

Certificate replay uses `requirements-certificate.txt`, derived from the historical certificate lockfile. Archive extraction explicitly disables Git newline conversion so Windows and Linux validate the same source bytes. Neither change relaxes source hashes or dependency checks.
