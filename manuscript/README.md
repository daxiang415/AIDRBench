# Manuscript workspace

Target: **Nature Communications Article**.

The journal does not prescribe a Microsoft Word template for initial submission. This workspace follows the current official Article order and keeps inline figures for repository review:

1. Title and authors
2. Abstract
3. Introduction
4. Results
5. Discussion
6. Methods
7. Data Availability
8. Code Availability
9. References
10. Acknowledgements
11. Author Contributions
12. Competing Interests
13. Figure Legends

Official guidance:

- https://www.nature.com/ncomms/submit/article
- https://www.nature.com/ncomms/submit/how-to-submit
- https://www.nature.com/documents/ncomms-formatting-instructions.pdf

## Current files

- `nature_communications_article.md`: English working manuscript v0.5 with mechanism-led framing, the paired community-profile sensitivity and six main figures.
- `supplementary_information.md`: Supplementary Methods/Results working draft with evidence partitions, lock discipline, controller specification, certification rules, optimisation audits, full certificate tables and four generated supplementary figures.
- `terminology-ledger.md`: canonical terms that must remain stable across the manuscript and Supplementary Information.
- `results-evidence-allocation.md`: main-text versus Supplementary evidence decisions.
- `source_data/`: clean-commit, hash-verified CSV tables underlying all main figures and the numerical supplementary figures.
- `submission-readiness.md`: completed checks and the remaining author/archival metadata blockers.
- `references/verified-v1/`: screened DOI whitelist, reference-manager exports and manual official-source records.
- `exports/AIDRBench_Nature_Communications_v0.4_review.pdf`: previous 17-page A4 review PDF; it predates Figure 6 and must be regenerated from the v0.5 manuscript after a clean commit.
- `exports/AIDRBench_Nature_Communications_v0.4_review.tex`: portable LaTeX review source; compile from the repository root so the tracked figure paths resolve.
- `exports/AIDRBench_Nature_Communications_v0.4_review_preview.png`: first-page preview for GitHub review.
- `exports/AIDRBench_Nature_Communications_v0.3_Supplementary_Information.pdf`: current 16-page A4 Supplementary Information PDF with four figures and six numbered release tables.
- `exports/AIDRBench_Nature_Communications_v0.3_Supplementary_Information.tex`: portable Supplementary Information LaTeX source with repository-relative figure paths.
- `exports/AIDRBench_Nature_Communications_v0.3_Supplementary_Information_preview.png`: Supplementary Information first-page preview for GitHub review.

## Current status

- Title: 11 words (journal maximum: 15).
- Abstract: 143 whitespace-delimited words (current official Article maximum: 150; hyphenated compounds counted as one).
- Introduction + Results + Discussion: approximately 3,181 whitespace-delimited words (current official main-text maximum: 6,000, excluding Methods and figure legends).
- Methods: approximately 2,846 whitespace-delimited words (excluded from the 6,000-word main-text limit but still edited for reproducibility and concision).
- Supplementary Information: approximately 7,868 whitespace-delimited words, including tables and captions.
- Main figures: six, within the journal's maximum of ten display items.
- Supplementary figures: four generated at 183-mm width with editable SVG/PDF, 600-dpi TIFF, repository-preview PNG and per-figure source manifests.
- Quantitative Results and figure legends: drafted from hash-verified Source Data.
- Tracked Source Data: 29 main-figure tables (21,694 rows) plus calibration, observation and representative-trajectory tables for supplementary figures. The main bundle was regenerated from clean scientific commit `ba0dfb7de774d34b336c6cd25f062ed382c55825` and passes the release provenance gate.
- Literature citations: 34 references (approximately 938 whitespace-delimited words); 30 DOI records exported through the screened citation workflow and four official data/proceedings records maintained in a separate verified RIS file.
- Author metadata, funding, contributions, competing interests and archival DOI: author input required.

## Evidence-first drafting order

The draft is revised in this order: Results, Introduction, Discussion, Methods, title, Abstract. The v0.4 file is already arranged in publication order, but later edits should continue to originate from the Results evidence rather than from desired claims.
