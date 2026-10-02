# Current files

Scientific manuscript: **v0.27**. Main artwork: **R8**, 17 September 2026.

| Material | Location |
| --- | --- |
| Main paper | [PDF](paper/v0.27/latex/main.pdf) · [LaTeX](paper/v0.27/latex/main.tex) |
| Supplement | [PDF](paper/v0.27/latex/supplement.pdf) · [LaTeX](paper/v0.27/latex/supplement.tex) |
| English collaboration copies | [Main](manuscript/nature_communications_article.md) · [supplement](manuscript/supplementary_information.md) |
| Main figures and panel data | [Main figure guide](paper/v0.27/figures/main/README.md) |
| Supplementary figures and panel data | [Supplementary figure guide](paper/v0.27/figures/supplement/README.md) |
| Compact scientific evidence | [Source Data](manuscript/source_data/) |
| Benchmark implementation | [Library](src/aidrbench/) · [configurations](configs/) · [tests](tests/) |
| Research protocols and drivers | [Revision records](manuscript/revisions/) |
| Setup and commands | [Getting started](docs/getting-started.md) · [Windows](WINDOWS_START_HERE.md) |
| Release boundaries | [Data and reproducibility](docs/GITHUB_V027.md) |
| Submission preparation | [Status](manuscript/submission-readiness.md) |

Edit the LaTeX files for the typeset manuscript. The Markdown collaboration copies do not synchronise with them automatically. A figure redraw must be copied into `paper/v0.27/latex/figures/` before rebuilding the paper.

Figure 1's SVG uses adjacent files in `Figure_1_assets/`; retain that directory when copying the SVG. Its PDF and PNG can be used independently.

The original delivery manifest is retained, with explicit documentation changes recorded in `docs/checkout-layout.json`. `python tools/aidr.py check --hashes` verifies the maintained checkout, including unchanged scientific files and the current documentation hashes. Historical exports and receipts are provenance records, not current editing instructions.
