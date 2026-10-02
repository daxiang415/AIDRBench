# Data and reproducibility

## Current scientific version

The manuscript is **v0.27**, with **R8 main artwork** dated 17 September 2026. The public Windows-compatible edition was prepared on 28 September 2026. The subsequent documentation refresh reorganises navigation and editing commands; it does not rerun experiments, select new offers or change statistical estimates.

## What is included

| Included here | Purpose |
| --- | --- |
| Main/supplement LaTeX and compiled PDFs | Read and edit the manuscript. |
| Six main figures and ten supplementary figures | Inspect the reference artwork. |
| Per-panel CSV/Excel tables, SVG and PowerPoint sources | Redraw and edit the figures. |
| Compact Source Data and calibration evidence | Inspect reported results and supporting measurements. |
| Library, configurations, tests and revision drivers | Inspect the implementation and run the supported checks. |

Bulk raw workloads, multi-GB hourly trajectories and full per-scenario recovery inputs are **not** included. Figure regeneration uses the supplied plotting tables; it does not establish that a fresh full-study replay has been performed. Full production-scale replay needs the separately held original inputs and the associated protocols.

## Three different checks

**Checkout verification** confirms that the expected files and their recorded hashes are present:

```bash
python tools/aidr.py check --hashes
```

**Figure regeneration** reads the included CSV tables and recreates their plotted series. Reference artwork and template layout can differ. The existing supplementary audit scripts compare captured quantitative series with their expected coordinates.

**Scientific replay** executes the original analyses with their required inputs. Regression tests include historical certificate replay and require a full Git clone. Use `requirements-certificate.txt` when installing the research dependencies; do not interpret a plotting-only installation as a complete replay environment.

## Manifests and historical records

`paper/v0.27/MANIFEST.csv` remains the original delivery receipt. `docs/checkout-layout.json` records the exact documentation replacements, retired reading copies and byte-preserving file renames in the maintained checkout. The checker applies this explicit update before verifying hashes; it does not exempt the scientific files from verification.

The original layout is retained on the `archive/v0.27-original-layout` branch at commit `66105ccaa5629f2d24c53c6d757922e139d54440`. Older nested delivery manifests describe that earlier packaging. The maintained supplementary `VERIFY_DELIVERY.py` delegates to the current checkout verifier.

Historical research records, embedded workbook notes and revision archives are retained as received. They may contain legacy language or paths. They are not current user documentation and should not be modified merely to make an old receipt pass.

The historical runtime under `manuscript/source_data/nature_economic_robustness_v1/frozen_runtime/` remains unchanged. It is bound to the result manifest; numerical regression tests separately exercise the current implementation.

## Figure packaging

Main Figure 1's SVG references 15 adjacent image assets in `Figure_1_assets/`. Keep those files together when copying the SVG. The reference PDF, PNG and PowerPoint remain unchanged. `GITHUB_ADAPTATION.json` and `ORIGINAL_FILE_MANIFEST.csv` document the earlier packaging adaptation.

The launcher writes redraws to the established output directories. It does not replace the paper's figure PDFs automatically. The English Markdown collaboration copies and submission LaTeX remain separate sources.

## Software and publication status

A software licence and archival identifier have not yet been finalised. Author details, funding, contributions and competing-interest declarations remain pending. No publication status or release DOI is asserted. See [submission preparation](../manuscript/submission-readiness.md).

For the current commands, use [Getting started](getting-started.md) or [Windows](../WINDOWS_START_HERE.md). The older [validation record](github_v027_validation.json) documents the earlier edition; the repository's Actions page contains subsequent CI runs.
