# AIDRBench current editable release — v0.27

Updated 2026-09-28. Scientific manuscript: v0.27; main artwork: R8, 2026-09-17.

Start with [Windows editing instructions](WINDOWS_START_HERE.md) and [release scope](docs/GITHUB_V027.md).

| Current material | Location |
|---|---|
| Main/SI LaTeX, compiled PDFs and all included figure PDFs | [paper/v0.27/latex](paper/v0.27/latex) |
| English main and SI Markdown | [main](manuscript/nature_communications_article.md), [SI](manuscript/supplementary_information.md) |
| Chinese and bilingual readers | [paper/v0.27/chinese](paper/v0.27/chinese) |
| Six main figures, editable PPTX/SVG and per-panel CSV/Excel | [main figure pack](paper/v0.27/figures/main) |
| Ten supplementary figures, per-panel CSV/Excel and direct plotter | [SI figure pack](paper/v0.27/figures/supplement) |
| Compact scientific evidence | [manuscript/source_data](manuscript/source_data) |
| Library, configurations and tests | `src/aidrbench`, `configs`, `tests` |
| Submission preparation status | [English](manuscript/submission-readiness.md), [中文](manuscript/submission-readiness.zh.md) |

The September 17 LaTeX and drawing packs are retained with the SVG packaging adaptation below; their current embedded manifests verify. The added figure receipt indexes their existing hashes. The top-level release [manifest](paper/v0.27/MANIFEST.csv) binds the portable GitHub materials. After intentional edits, the original hashes describe the baseline, not the edited files.

Older exports, readers and figure folders remain for provenance and regression tests. Use the paths above for current editing. [The previous mainline record](docs/history/pre_v027_MAINLINE_FILES.md) is historical.

Do not spawn subagents unless explicitly requested. Local Python drawing is authorised. Keep author names, affiliations, funding, contributions, competing interests, licence and archival identifiers pending until supplied by the author.

GitHub packaging adaptation: main Figure 1 SVG references 15 byte-identical PNG/JPEG assets in its adjacent `Figure_1_assets` folder. Keep that folder with the SVG when copying it. The PDF, PNG, PowerPoint, vector geometry and scientific data are unchanged. This avoids a secret-scanning false match in inline JPEG encoding. `GITHUB_ADAPTATION.json` records original and current hashes; `ORIGINAL_FILE_MANIFEST.csv` preserves the earlier receipt.
